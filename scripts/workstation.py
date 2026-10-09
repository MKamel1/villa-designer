"""Deploy versioned source and run bounded, content-verified Ubuntu jobs."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from render_remote import _ssh, _push
from archpipe.stage_result import write_stage_result, enforce_clean_verdict
from archpipe.safe_io import save_json
from archpipe import photometry


def digest(data):
    return hashlib.sha256(data).hexdigest()


def remote_root(host):
    response = _ssh(host, 'printf %s "$HOME"')
    if response.returncode:
        raise RuntimeError(response.stderr.decode(errors='replace'))
    home = response.stdout.decode().strip()
    if not home.startswith('/') or '\n' in home:
        raise ValueError('Invalid remote home directory')
    return home+'/archpipe'


def package():
    names = subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
    allowed = ('src/','scripts/','tests/','spec/','ops/','docs/','.agents/','agents/')
    text_suffixes = {'.py','.md','.json','.yaml','.yml','.toml','.txt','.sh','.xml','.csv','.svg'}
    files = {name:(ROOT/name).read_bytes() for name in names if name and (ROOT/name).is_file()
             and Path(name).suffix.lower() in text_suffixes
             and (name.startswith(allowed) or name in ('requirements.txt','requirements-worker.txt','requirements-thermal.txt','AGENTS.md','CLAUDE.md'))}
    ies = photometry.revit_ies_dir()
    if ies:
        files.update({'assets/ies/'+p.name:p.read_bytes() for p in ies.glob('*.ies')})
    # Picked manufacturer products join the same flat IES namespace (photometry.find_ies).
    if photometry.PRODUCT_IES_DIR.is_dir():
        files.update({'assets/ies/'+p.name:p.read_bytes() for p in photometry.PRODUCT_IES_DIR.glob('*.ies')})
    records = {name:digest(data) for name,data in sorted(files.items())}
    release_id = digest(json.dumps(records,sort_keys=True).encode())[:24]
    files['release.json'] = json.dumps({'id':release_id,'files':records},sort_keys=True).encode()
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream,mode='w:gz') as tf:
        for name,data in sorted(files.items()):
            entry = tarfile.TarInfo(name)
            entry.size = len(data)
            tf.addfile(entry,io.BytesIO(data))
    return release_id,stream.getvalue()


def deploy(host):
    root = remote_root(host)
    release_id, archive = package()
    dest = root+'/releases/'+release_id
    command = ('mkdir -p '+shlex.quote(dest)+' && tar -xzf - -C '+shlex.quote(dest))
    existing = _ssh(host,'test -f '+shlex.quote(dest+'/release.json'))
    if existing.returncode:
        result = _ssh(host,command,stdin_bytes=archive)
        if result.returncode:
            raise RuntimeError(result.stderr.decode(errors='replace'))
    return root,dest,release_id


def thermal(host, root, release, job_path, epw_zip):
    """Run a thermal job (scripts/thermal_job.py) under the worker's thermal environment."""
    env = json.loads(_ssh(host, 'cat '+shlex.quote(root+'/worker-environment.json')).stdout)
    if not env.get('thermal_python') or not env.get('energyplus'):
        raise RuntimeError('Thermal toolchain missing on the worker: run `workstation.py setup`')
    data = epw_zip.read_bytes()
    wdir = root+'/weather/'+digest(data)[:16]
    unzip = ('mkdir -p '+shlex.quote(wdir)+' && cat > '+shlex.quote(wdir+'/w.zip')+' && python3 -c '
             + shlex.quote('import zipfile,sys;zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])')
             + ' '+shlex.quote(wdir+'/w.zip')+' '+shlex.quote(wdir))
    if _ssh(host, 'ls '+shlex.quote(wdir)+'/*.epw').returncode and _ssh(host, unzip, stdin_bytes=data).returncode:
        raise RuntimeError('Could not transfer the weather file')
    epw = _ssh(host, 'ls '+shlex.quote(wdir)+'/*.epw').stdout.decode().split()[0]
    job = job_path.read_bytes()
    job_id = digest(job+data)[:16]
    remote_job = root+'/inputs/thermal-'+job_id+'.json'
    _ssh(host, 'mkdir -p '+shlex.quote(root+'/inputs')+' && cat > '+shlex.quote(remote_job), stdin_bytes=job)
    cmd = [env['thermal_python'], release+'/scripts/thermal_job.py', '--input', remote_job, '--epw', epw,
           '--energyplus', env['energyplus'], '--out', root+'/thermal/'+job_id,
           '--radiance', env.get('radiance', '')]
    result = _ssh(host, shlex.join(cmd), timeout=7200)
    local = ROOT/'out/workstation'
    local.mkdir(parents=True, exist_ok=True)
    text = result.stdout.decode(errors='replace')
    if not text.strip():
        print(result.stderr.decode(errors='replace')[-6000:])
        return 2
    report = json.loads(text)
    name = 'thermal-'+json.loads(job).get('kind','job')+'-latest.json'
    save_json(local / name, report, indent=2)
    print(json.dumps({k: v for k, v in report.items() if k not in ('results', 'assumptions_default')}, indent=2)[:6000])
    print('report:', local/name)
    record = write_stage_result('workstation-thermal',
        record_path=local / 'thermal.stage-result.json', inputs=[job_path, epw_zip],
        outputs=[local / name], root=ROOT, code_paths=[__file__], exit_code=result.returncode,
        metadata={'release': release, 'worker_report': report})
    return enforce_clean_verdict(record, exit_code=result.returncode or 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action',choices=['setup','status','verify','batch','bedroom','benchmark','sweep','radiance','thermal'])
    ap.add_argument('--host',default='ai-workstation')
    ap.add_argument('--input',type=Path,default=ROOT/'out/bedroom-render.json')
    ap.add_argument('--samples',type=int,default=256)
    ap.add_argument('--resolution',default='1600x1000')
    ap.add_argument('--workers',type=int,default=2)
    ap.add_argument('--views',nargs='+',default=['bed','window','overview'])
    ap.add_argument('--job',type=Path,help='thermal: job JSON (kind climate|study|validate)')
    ap.add_argument('--epw-zip',type=Path,default=Path.home()/'archpipe-sources/cairo-epw/EGY_QH_Cairo.West.AP.623680_TMYx.zip')
    a = ap.parse_args()
    root,release,release_id = deploy(a.host)
    if a.action == 'thermal':
        return thermal(a.host, root, release, a.job, a.epw_zip)
    if a.action == 'setup':
        cmd = ['python3',release+'/ops/workstation/bootstrap.py','--release',release,'--root',root,'--radiance','--thermal']
    else:
        cmd = ['python3',release+'/scripts/worker_entry.py',a.action,'--root',root,'--release',release,
               '--samples',str(a.samples),'--resolution',a.resolution,'--workers',str(a.workers)]
        if a.action in ('batch','bedroom','benchmark','sweep','radiance'):
            data = a.input.read_bytes()
            input_id = digest(data)
            remote_input = root+'/inputs/'+input_id+'.json'
            if _ssh(a.host,'mkdir -p '+shlex.quote(root+'/inputs')).returncode:
                raise RuntimeError('Could not create input directory')
            result = _ssh(a.host,'cat > '+shlex.quote(remote_input),stdin_bytes=data)
            if result.returncode:
                raise RuntimeError('Could not transfer model input')
            cmd.extend(['--input',remote_input,'--views',*a.views])
    result = _ssh(a.host,shlex.join(cmd),timeout=2400)
    local = ROOT/'out/workstation'
    local.mkdir(parents=True,exist_ok=True)
    (local/(a.action+'-latest.log')).write_bytes(result.stdout+result.stderr)
    if result.returncode:
        # Failed workers still emit their persisted result on stdout.
        try:
            failed_report = json.loads(result.stdout)
        except (ValueError, UnicodeDecodeError):
            failed_report = None
        if failed_report is not None:
            save_json(local / (a.action + '-latest.json'), failed_report, indent=2)
        record = write_stage_result('workstation-' + a.action,
            record_path=local / (a.action + '.stage-result.json'),
            inputs=[a.input] if a.action in ('batch','bedroom','benchmark','sweep','radiance') else [],
            outputs=[local / (a.action + '-latest.log')] +
                    ([local / (a.action + '-latest.json')] if failed_report is not None else []),
            root=ROOT, code_paths=[__file__], exit_code=result.returncode,
            metadata={'release_id': release_id, 'worker_report': failed_report})
        print((result.stdout+result.stderr).decode(errors='replace')[-8000:])
        return enforce_clean_verdict(record, exit_code=result.returncode)
    text = result.stdout.decode()
    # Worker output is structured JSON; artifacts are fetched as one archive.
    if a.action != 'setup':
        report = json.loads(text)
        save_json(local / (a.action + '-latest.json'), report, indent=2)
        if report.get('bundle'):
            fetched = _ssh(a.host,'cat '+shlex.quote(report['bundle']))
            if fetched.returncode:
                raise RuntimeError('Could not fetch result bundle')
            destination = local/report['batch_id']
            destination.mkdir(exist_ok=True)
            with tarfile.open(fileobj=io.BytesIO(fetched.stdout)) as tf:
                tf.extractall(destination,filter='data')
            report['local_artifacts'] = str(destination)
        print(json.dumps({'operation':a.action,'passed':report.get('passed'),
            'batch_id':report.get('batch_id'),'jobs':len(report.get('jobs',[])),
            'reused':report.get('reused'),'report':str(local/(a.action+'-latest.json')),
            'artifacts':report.get('local_artifacts'),
            'failures':[{'job':r['job_id'][:16],'error':r.get('error')} for r in report.get('jobs',[]) if not r['passed']],
            'comparison':report.get('comparison')},indent=2))
    else:
        report = {}
        print(text)
    outputs = [local / (a.action + '-latest.log')]
    if a.action != 'setup':
        outputs.append(local / (a.action + '-latest.json'))
    if report.get('local_artifacts'):
        outputs += sorted(p for p in Path(report['local_artifacts']).rglob('*') if p.is_file())
    record = write_stage_result('workstation-' + a.action,
        record_path=local / (a.action + '.stage-result.json'),
        inputs=[a.input] if a.action in ('batch','bedroom','benchmark','sweep','radiance') else [],
        outputs=outputs, expected_outputs=[] if a.action == 'setup' else [local / (a.action + '-latest.json')],
        root=ROOT, code_paths=[__file__, ROOT / 'scripts/worker_entry.py'],
        exit_code=1 if report.get('passed') is False else 0,
        metadata={'release_id': release_id, 'worker_runtime': report.get('runtime'),
                  'jobs': [r.get('manifest') for r in report.get('jobs', [])]})
    return enforce_clean_verdict(record, message='Workstation operation failed')


if __name__ == '__main__':
    raise SystemExit(main())
