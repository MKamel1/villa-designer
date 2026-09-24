"""Ubuntu worker entry point. Invoked by scripts/workstation.py over SSH."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tarfile
import time


def command(argv, cwd, env, label, timeout=900):
    started = time.perf_counter()
    with (cwd/(label+'.log')).open('w') as log:
        completed = subprocess.run([str(v) for v in argv],cwd=cwd,env=env,
            stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
    if completed.returncode:
        raise RuntimeError(label+' failed; see '+str(cwd/(label+'.log')))
    return time.perf_counter()-started


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action',choices=['status','verify','batch','bedroom','benchmark','sweep','radiance'])
    ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--release',type=Path,required=True)
    ap.add_argument('--input',type=Path)
    ap.add_argument('--samples',type=int,default=256)
    ap.add_argument('--resolution',default='1600x1000')
    ap.add_argument('--workers',type=int,default=2)
    ap.add_argument('--views',nargs='+',default=['bed','window','overview'])
    a = ap.parse_args()
    root,release = a.root.resolve(),a.release.resolve()
    if not root.is_relative_to(Path.home()) or not release.is_relative_to(root/'releases'):
        ap.error('Worker paths must be inside the user-owned deployment')
    config = json.loads((root/'worker-environment.json').read_text())
    if os.path.abspath(sys.executable) != config['python']:
        os.execv(config['python'],[config['python'],__file__,*sys.argv[1:]])
    if not 1 <= a.workers <= 4 or not 32 <= a.samples <= 4096:
        ap.error('workers must be 1..4 and samples 32..4096')
    resolution = [int(v) for v in a.resolution.split('x')]
    if len(resolution)!=2 or any(v<128 or v>4096 for v in resolution):
        ap.error('Image dimensions must be between 128 and 4096 pixels')
    if not a.views or any(v not in ('bed','window','overview') for v in a.views):
        ap.error('Unknown camera view')
    sys.path[:0] = [str(release/'src'),str(release/'scripts')]
    from archpipe.worker import cached_job, identity, sha_file, process_lock
    installed = json.loads(Path(config['environment']).read_text())
    if installed['requirements_sha256'] != sha_file(release/'requirements-worker.txt'):
        raise RuntimeError('Worker dependency lock changed; run workstation.py setup')
    manifest = json.loads((release/'release.json').read_text())
    # Validate actual deployed files, not merely the deployment folder name.
    changed = [name for name,expected in manifest['files'].items()
               if not (release/name).is_file() or sha_file(release/name)!=expected]
    if changed:
        raise RuntimeError('Deployed release was modified: '+', '.join(changed[:5]))
    code = {name:value for name,value in manifest['files'].items()
            if name.endswith('.py') or name.startswith('requirements')}
    assets = {name:value for name,value in manifest['files'].items() if name.startswith('assets/')}
    env = {**os.environ,'PYTHONPATH':str(release/'src'),'PYTHONIOENCODING':'utf-8',
           'ARCHPIPE_IES_DIR':str(release/'assets/ies'),
           'OMP_NUM_THREADS':'8','OPENBLAS_NUM_THREADS':'8'}
    packages = subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True).splitlines()
    runtime = {'python':sys.version,'system':platform.platform(),'packages':packages,
        'blender_sha256':sha_file(config['blender']),
        'blender_version':subprocess.check_output([config['blender'],'--version'],text=True).splitlines()[0],
        'graphics':subprocess.check_output(['nvidia-smi','--query-gpu=name,driver_version','--format=csv,noheader'],text=True).strip(),
        'radiance':{p.name:sha_file(p) for p in sorted((Path(config['radiance'])/'bin').iterdir()) if p.is_file()},
        'radiance_library':{p.name:sha_file(p) for p in sorted((Path(config['radiance'])/'lib').iterdir())
                            if p.is_file() and p.suffix in ('.cal','.tab')},
        'code':identity(code),'assets':identity(assets)}
    if a.action == 'status':
        print(json.dumps({'passed':True,'runtime':runtime,'release':str(release),
                         'job_count':len(list((root/'jobs').glob('*/result.json')))},indent=2))
        return
    data = json.loads(a.input.read_text()) if a.input else None
    source_id = identity(data) if data else None
    if data:
        for light in data.get('lighting',[]):
            name = light.get('ies_file')
            if not name or Path(name).name != name or not (release/'assets/ies'/name).is_file():
                raise ValueError('Every light must name a deployed photometric asset')
            light['ies'] = str(release/'assets/ies'/name)
    blender_dir = release/'src/archpipe/blender'

    def action(kind, params, folder):
        model = folder/'model.json'
        if data:
            model.write_text(json.dumps(data))
        if kind == 'verify':
            # Run from the deployment so fixture-relative paths work.
            checks = []
            for name,argv in [('project',[sys.executable,release/'scripts/verify.py','--portable']),
                              ('regressions',[sys.executable,'-m','unittest','discover','-s',str(release/'tests'),'-p','test_*.py','-v'])]:
                with (folder/(name+'.log')).open('w') as log:
                    res = subprocess.run([str(v) for v in argv],cwd=release,env=env,
                        stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,timeout=300)
                checks.append({'name':name,'exit_code':res.returncode})
            (folder/'verification.json').write_text(json.dumps(checks,indent=2))
            if any(c['exit_code'] for c in checks):
                raise RuntimeError('Ubuntu verification failed; inspect project/regressions logs')
            return {'checks':checks,'scope':'Portable engines and recorded Revit fixtures; no live Revit on Ubuntu'}
        if kind in ('render','probe'):
            script = 'build_scene.py' if kind=='render' else 'measure_lux.py'
            output = folder/('render.png' if kind=='render' else 'lux.json')
            argv = [config['blender'],'-b','-t','8','--python-exit-code','1','-P',blender_dir/script,
                    '--','--extract',model,'--out',output,'--samples',str(params['samples'])]
            if kind == 'render':
                argv += ['--interior','--camera',params['camera'],'--res',params['resolution'],'--target-lux','160']
            else:
                argv += ['--res',str(params['resolution']),'--bounces',str(params['bounces']),
                         '--exr',str(folder/'probe.exr')]
                if params['device']=='gpu':
                    argv.append('--gpu')
            if kind=='render' or params.get('device')=='gpu':
                with process_lock(root/'locks/graphics.lock'):
                    seconds = command(argv,folder,env,kind)
            else:
                seconds = command(argv,folder,env,kind)
            if not output.is_file() or output.stat().st_size == 0:
                raise RuntimeError('Blender returned without the expected fresh artifact')
            result = {'output':str(output),'wall_seconds':seconds}
            if kind == 'probe':
                probe = json.loads(output.read_text())
                result.update(device=probe['device'],render_seconds=probe['render_seconds'],
                              average_lux=statistics.mean(p[2] for p in probe['points']))
                if params['device']=='gpu' and 'OPTIX' not in probe['device'] and 'CUDA' not in probe['device']:
                    raise RuntimeError('Requested graphics acceleration was not used')
            return result
        if kind == 'lighting':
            from lighting_report import build_scheme
            from archpipe.lighting import lux_grid
            scheme,problems = build_scheme(data,release/'assets/ies')
            if problems:
                raise ValueError(str(problems))
            scheme = [replace(l,output=params['output']) for l in scheme]
            grid = lux_grid(data['rooms'][0]['boundary'],scheme,spacing=params['spacing'])
            report = {'scenario':params,'built':False,'average_lux':grid.average,
                      'minimum_lux':grid.minimum,'maximum_lux':grid.maximum,
                      'point_source_warnings':grid.point_source_warnings(),
                      'limitation':'Direct light only; output multiplier is an unbuilt lighting alternative'}
            (folder/'lighting.json').write_text(json.dumps(report,indent=2))
            return report
        if kind == 'geometry':
            from archpipe.from_extract import convert
            from archpipe.rules import review
            from archpipe.review_extract import ROOM_CONTEXT_RULES
            project = convert(data).project
            pieces = tuple(replace(f,at=(f.at[0]+params['bed_shift_mm'],f.at[1]))
                           if f.id=='FN-BED' else f for f in project.furniture)
            candidate = replace(project,furniture=pieces)
            candidate.validate()
            findings = [asdict(f) for f in review(candidate) if f.rule not in ROOM_CONTEXT_RULES]
            report = {'scenario':params,'built':False,'scope':'room',
                      'design_passed':not any(f['severity'] in ('warning','violation') for f in findings),
                      'findings':findings,'not_assessed':sorted(ROOM_CONTEXT_RULES),
                      'limitation':'Unbuilt candidate evaluated in memory; saved Revit extract is unchanged'}
            (folder/'geometry.json').write_text(json.dumps(report,indent=2))
            return report
        if kind == 'radiance':
            from archpipe.radiance import simulate
            return simulate(data,folder,Path(config['radiance']),release/'assets/ies',workers=8)
        raise ValueError('Unknown worker operation')

    requests = []
    if a.action == 'verify':
        requests = [('verify',{})]
    elif a.action in ('batch','bedroom'):
        requests = [('render',{'camera':v,'samples':a.samples,'resolution':a.resolution}) for v in a.views]
        if a.action == 'bedroom':
            requests += [('probe',{'device':'gpu','resolution':128,'bounces':0,'samples':512}),
                         ('radiance',{'plane_mm':850,'spacing_mm':250,'ambient_bounces':4})]
    elif a.action == 'benchmark':
        requests = [('probe',{'device':device,'resolution':resolution,'bounces':bounces,
                             'samples':512,'trial':trial})
                    for resolution,bounces in [(128,0),(256,16)]
                    for trial in range(3) for device in ('cpu','gpu')]
    elif a.action == 'sweep':
        requests = [('lighting',{'output':v,'spacing':50}) for v in (0.6,0.7,0.8,0.9,1.0)]
        requests += [('geometry',{'bed_shift_mm':v}) for v in (-100,-50,0,50,100)]
    elif a.action == 'radiance':
        requests = [('radiance',{'plane_mm':850,'spacing_mm':250,'ambient_bounces':4})]
    def execute(item):
        kind,params = item
        # A documentation or unrelated engine edit must not discard an
        # expensive, otherwise identical render or physical benchmark.
        common = ('src/archpipe/worker.py','scripts/worker_entry.py','requirements-worker.txt')
        relevant = {n:v for n,v in code.items() if n in common or
                    (kind in ('render','probe') and n.startswith('src/archpipe/blender/')) or
                    (kind=='radiance' and n=='src/archpipe/radiance.py') or
                    kind in ('verify','lighting','geometry')}
        job_runtime = {**runtime,'code':identity(relevant)}
        job_manifest = {'schema':1,'kind':kind,'parameters':params,'model':source_id,'runtime':job_runtime}
        return cached_job(root,job_manifest,lambda folder:action(kind,params,folder))
    # Timing comparisons run in isolation; concurrent jobs would corrupt them.
    if a.action == 'benchmark':
        results = [execute(item) for item in requests]
    else:
        with ThreadPoolExecutor(max_workers=a.workers) as pool:
            results = list(pool.map(execute,requests))
    batch_id = identity([r['job_id'] for r in results])[:24]
    batch = root/'batches'/batch_id
    batch.mkdir(parents=True,exist_ok=True)
    report = {'batch_id':batch_id,'operation':a.action,'passed':all(r['passed'] for r in results),
              'reused':sum(r['reused'] for r in results),'jobs':results,'runtime':runtime}
    if a.action == 'benchmark' and report['passed']:
        comparison=[]
        for resolution,bounces in [(128,0),(256,16)]:
            group=[r for r in results if r['manifest']['parameters']['resolution']==resolution]
            cpu=[r['detail'] for r in group if r['manifest']['parameters']['device']=='cpu']
            gpu=[r['detail'] for r in group if r['manifest']['parameters']['device']=='gpu']
            c,g = statistics.median(v['wall_seconds'] for v in cpu),statistics.median(v['wall_seconds'] for v in gpu)
            c_lux,g_lux = statistics.median(v['average_lux'] for v in cpu),statistics.median(v['average_lux'] for v in gpu)
            discrepancy = abs(g_lux/c_lux-1)
            comparison.append({'resolution':resolution,'bounces':bounces,'trials':3,
                'processor_seconds':c,'graphics_seconds':g,'processor_to_graphics_speed_ratio':c/g,
                'average_lux_relative_difference':discrepancy,'recommended_device':'gpu' if g<c else 'cpu'})
            if discrepancy>0.05:
                report['passed']=False
        report['comparison']=comparison
    (batch/'report.json').write_text(json.dumps(report,indent=2))
    archive=batch/'results.tar.gz'
    with tarfile.open(archive,'w:gz') as tf:
        tf.add(batch/'report.json',arcname='report.json')
        for r in results:
            attempt=Path(r['attempt'])
            for p in sorted(attempt.rglob('*')):
                # Keep large numerical EXR probes remote; lux and logs are sufficient locally.
                if p.is_file() and p.suffix!='.exr':
                    tf.add(p,arcname=r['job_id'][:16]+'/'+p.relative_to(attempt).as_posix())
    report['bundle']=str(archive)
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
