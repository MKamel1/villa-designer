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
             and (name.startswith(allowed) or name in ('requirements.txt','requirements-worker.txt','AGENTS.md','CLAUDE.md'))}
    ies = photometry.revit_ies_dir()
    if ies:
        files.update({'assets/ies/'+p.name:p.read_bytes() for p in ies.glob('*.ies')})
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


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action',choices=['setup','status','verify','batch','bedroom','benchmark','sweep','radiance'])
    ap.add_argument('--host',default='ai-workstation')
    ap.add_argument('--input',type=Path,default=ROOT/'out/bedroom-render.json')
    ap.add_argument('--samples',type=int,default=256)
    ap.add_argument('--resolution',default='1600x1000')
    ap.add_argument('--workers',type=int,default=2)
    ap.add_argument('--views',nargs='+',default=['bed','window','overview'])
    a = ap.parse_args()
    root,release,release_id = deploy(a.host)
    if a.action == 'setup':
        cmd = ['python3',release+'/ops/workstation/bootstrap.py','--release',release,'--root',root,'--radiance']
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
        print((result.stdout+result.stderr).decode(errors='replace')[-8000:])
        return result.returncode
    text = result.stdout.decode()
    # Worker output is structured JSON; artifacts are fetched as one archive.
    if a.action != 'setup':
        report = json.loads(text)
        (local/(a.action+'-latest.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
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
        if report.get('passed') is False:
            return 1
    else:
        print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
