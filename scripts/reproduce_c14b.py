"""Bounded real Blender replay for C14 Batch B (no SSH or model authoring).

Three cameras use the frozen real bedroom extract and IES files. The version
mutation changes the fingerprint string, not the installed renderer; it proves
that a result recorded under another version cannot be resumed as this job.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from archpipe.safe_io import save_json, copy_file
from archpipe.stage_result import write_stage_result, enforce_clean_verdict
from archpipe.worker import cached_job, identity, sha_file
from worker_entry import job_manifest


def frozen_ies(fixture, destination):
    """Materialize exact photometric text when a portable release omits .ies suffixes."""
    values=json.loads((fixture/'ies-text.json').read_text())['files']
    paths={}
    for name, value in values.items():
        source=fixture/name
        if not source.is_file():
            destination.mkdir(parents=True,exist_ok=True)
            source=destination/name
            source.write_bytes(value['text'].encode('ascii'))
        if sha_file(source) != value['sha256']:
            raise RuntimeError('Frozen photometric bytes changed: '+name)
        paths[name]=source
    return paths


def photometry_probe(folder, blender):
    """Measure actual IES nodes on the real five-fixture input and missing-path sibling."""
    fixture=ROOT/'tests/fixtures/c14b'
    ies=frozen_ies(fixture,folder/'photometry')
    photometry_dir=next(iter(ies.values())).parent
    probe=folder/'photometry_probe.py'
    probe.write_text("""import sys, json
from pathlib import Path
import bpy
sys.path.insert(0, %r)
from build_scene import build_lights
source = Path(%r)
result = {}
for missing in (False, True):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    data = json.loads(source.read_text())
    for light in data['lighting']:
        light['ies'] = str(Path(%r) / ('missing.ies' if missing else light['ies_file']))
    lamps = build_lights(data)
    bound = sum(1 for obj in lamps if obj.data.use_nodes and any(n.type == 'TEX_IES' for n in obj.data.node_tree.nodes))
    result['missing' if missing else 'clean'] = {'on': bool(lamps), 'count': len(lamps), 'with_ies': bound}
print('C14 PHOTOMETRY ' + json.dumps(result))
""" % (str(ROOT/'src/archpipe/blender'), str(fixture/'bedroom-render.json'), str(photometry_dir)))
    completed=subprocess.run([blender,'-b','--python-exit-code','1','-P',str(probe)],
                             capture_output=True,text=True,check=True,timeout=60,cwd=ROOT)
    (folder/'photometry_probe.log').write_text(completed.stdout+completed.stderr)
    line=next(line for line in completed.stdout.splitlines() if line.startswith('C14 PHOTOMETRY '))
    measured=json.loads(line[len('C14 PHOTOMETRY '):])
    save_json(folder/'photometry-probe.json',measured,indent=2)
    return measured


def replay(folder, blender):
    folder=Path(folder); folder.mkdir(parents=True,exist_ok=True)
    fixture=ROOT/'tests/fixtures/c14b'
    frozen=fixture/'bedroom-render.json'
    model=json.loads(frozen.read_text())
    ies=frozen_ies(fixture,folder/'photometry')
    for light in model['lighting']:
        light['ies']=str(ies[light['ies_file']])
    runtime={'python':sys.version,'system':platform.platform(),
             'blender_version':subprocess.check_output([blender,'--version'],text=True).splitlines()[0],
             'blender_sha256':sha_file(blender),
             'assets':identity({name:sha_file(p) for name,p in ies.items()})}
    paths=[ROOT/'scripts/worker_entry.py',ROOT/'src/archpipe/worker.py',ROOT/'requirements-worker.txt']
    paths+=sorted((ROOT/'src/archpipe/blender').glob('*.py'))
    code={p.relative_to(ROOT).as_posix():sha_file(p) for p in paths}
    source_id=identity(model)
    inputs=[frozen]+sorted(ies.values())
    def action(params):
        def render(attempt):
            scene=attempt/'model.json'; save_json(scene,model,indent=2)
            output=attempt/'render.png'
            argv=[blender,'-b','-t','2','--python-exit-code','1','-P',str(ROOT/'src/archpipe/blender/build_scene.py'),
                  '--','--extract',str(scene),'--out',str(output),'--samples','32','--res','128x128',
                  '--interior','--camera',params['camera'],'--target-lux','160','--cpu']
            with (attempt/'render.log').open('w') as log:
                subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180,
                               cwd=ROOT,env={**os.environ,'PYTHONPATH':str(ROOT/'src')})
            if not output.is_file() or not output.stat().st_size:
                raise RuntimeError('Blender produced no image')
            record=write_stage_result('c14b-real-render',record_path=attempt/'render.stage-result.json',
                inputs=inputs,outputs=[scene,output,attempt/'render.log'],root=ROOT,code_paths=paths,
                metadata={'runtime':runtime,'parameters':params})
            enforce_clean_verdict(record)
            return {'output':str(output)}
        return render
    initial=[]
    for camera in ('bed','window','overview'):
        params={'camera':camera,'samples':32,'resolution':'128x128'}
        manifest=job_manifest('render',params,source_id,runtime,code)
        initial.append(cached_job(folder,manifest,action(params)))
    if not all(r['passed'] for r in initial):
        raise RuntimeError('Real Blender replay failed: '+str([(r.get('error'),r['attempt']) for r in initial if not r['passed']]))
    unrelated={**code,'docs/ROADMAP.md':'documentation mutation','src/archpipe/guidance.py':'unrelated engine mutation'}
    reused=[]
    for result in initial:
        params=result['manifest']['parameters']
        manifest=job_manifest('render',params,source_id,runtime,unrelated)
        reused.append(cached_job(folder,manifest,action(params)))
    first=initial[0]; params=first['manifest']['parameters']
    changed_runtime={**runtime,'blender_version':runtime['blender_version']+' [mutation]'}
    # Reconstruct the historical omitted-renderer identity using a real completed image.
    legacy = {'scene': source_id, 'ies': runtime['assets']}
    def legacy_action(version):
        def persist(attempt):
            copy_file(Path(first['attempt']) / 'render.png', attempt / 'render.png')
            return {'renderer_version': version}
        return persist
    legacy_first = cached_job(folder / 'legacy', legacy, legacy_action(runtime['blender_version']))
    legacy_stale = cached_job(folder / 'legacy', legacy, legacy_action(changed_runtime['blender_version']))
    changed=job_manifest('render',params,source_id,changed_runtime,code)
    mutation=cached_job(folder,changed,action(params))
    (Path(first['attempt'])/'render.png').write_bytes(b'corrupted cached image')
    repaired=cached_job(folder,first['manifest'],action(params))
    summary={'manifest':first['manifest'],'job_id':first['job_id'],'runtime':runtime,'code':code,
             'input_hashes':{p.name:sha_file(p) for p in inputs},
             'renderer_mutation_job_id':mutation['job_id'],
             'unchanged_reused':sum(r['reused'] for r in reused),
             'legacy_manifest': legacy, 'legacy_stale_reused': legacy_stale['reused'],
             'legacy_recorded_renderer': legacy_stale['detail']['renderer_version'],
             'requested_renderer_mutation': changed_runtime['blender_version'],
             'version_mutation_reused':mutation['reused'],'corrupt_output_reused':repaired['reused'],
             'passed':[r['passed'] for r in initial+reused+[mutation,repaired]],
             'real_attempts':[r['attempt'] for r in initial+[mutation,repaired]],
             'scope':'real native render; version string mutation uses the same installed Blender binary'}
    summary['photometry'] = photometry_probe(folder, blender)
    save_json(folder/'real-replay.json',summary,indent=2)
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender',required=True)
    parser.add_argument('--out',type=Path,default=ROOT/'out/c14b-real')
    args=parser.parse_args()
    result=replay(args.out,args.blender)
    print(json.dumps({k:v for k,v in result.items() if k not in ('code','manifest','runtime')},indent=2))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
