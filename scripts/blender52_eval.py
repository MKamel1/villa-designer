"""Local, isolated evaluation driver using the workstation shared graphics lock.

Every invocation runs a fresh process, validates its executable and saves a
content-bound receipt. No production data or Blender preferences are written.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from archpipe.execution_context import Tool, project_context, write_record
sys.path.insert(0,str(ROOT/"scripts"))
from prove_reproducibility import optical_file_hashes

def require_gpu(device, devices):
    """Reject CPU fallback before recording GPU evaluation timings."""
    if device != 'GPU' or not any(d.get('use') and d.get('type') in ('OPTIX','CUDA','HIP','METAL','ONEAPI') for d in devices):
        raise RuntimeError('Evaluation requires an enabled GPU; refusing CPU timings')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--blender',type=Path,default=Path.home()/'opt/blender-4.5.14-linux-x64/blender')
    p.add_argument('--expected-version',default='4.5.14')
    p.add_argument('--scene',type=Path,default=ROOT/'out/blender52/scene.json')
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--ies-dir',type=Path,default=ROOT/'out/blender52/ies')
    p.add_argument('--views',default='all')
    p.add_argument('--samples',type=int,default=256)
    p.add_argument('--measure-lighting',action='store_true')
    p.add_argument('--denoiser',choices=['OPENIMAGEDENOISE','OPTIX'])
    p.add_argument('--match-color',type=Path)
    p.add_argument('--save-blend',action='store_true')
    p.add_argument('--batch',action='store_true',help='Reference exposures, saved speed scenes, then task measurements')
    a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    if (out/'process.json').exists():p.error('refusing to overwrite an existing evaluation')
    scene=json.loads(a.scene.read_text())
    optics=optical_file_hashes(scene,a.ies_dir)
    context=project_context(ROOT,Path(__file__).resolve(),'blender52-evaluation',inputs=[a.scene.resolve()],output=out,
                           tools=[Tool('blender',a.blender.resolve(),a.expected_version)])
    write_record(context,out/'execution-context.json')
    env=dict(os.environ,NO_COLOR='1',PYTHONPATH=str(ROOT/'src'),PYTHONHASHSEED='0',OMP_NUM_THREADS='8',
             OPENBLAS_NUM_THREADS='8',BLENDER52_JOB=str(out),
             BLENDER_USER_CONFIG=str(out/'user-config'),BLENDER_USER_SCRIPTS=str(out/'user-scripts'))
    if a.denoiser:env['BLENDER52_DENOISER']=a.denoiser
    if a.match_color:env['BLENDER52_MATCH_COLOR']=str(a.match_color.resolve())
    if a.save_blend:env['BLENDER52_SAVE_BLEND']=str(out/'villa-copy.blend')
    cmd=['nice','-n','10',str(a.blender.resolve()),'-b','-t','8','--python-exit-code','1','-P',
         str(ROOT/('scripts/blender52_batch_scene.py' if a.batch else 'scripts/blender52_scene.py')),'--','--scene',str(a.scene.resolve()),'--out',str(out),
         '--ies-dir',str(a.ies_dir.resolve()),'--library-root','/home/omar/archpipe/assets/library',
         '--views',a.views,'--samples',str(a.samples),'--res','960x640']
    if a.measure_lighting:cmd+=['--measure-lighting']
    start=time.time()
    with Path('/home/omar/archpipe/locks/graphics.lock').open('rb') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        source={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest()
                for f in list((ROOT/'src/archpipe').rglob('*.py'))+list((ROOT/'scripts').glob('blender52*.py'))}
        with (out/'process.log').open('w') as log:
            r=subprocess.run(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    record=dict(command=cmd,exit_code=r.returncode,wall_seconds=time.time()-start,
                scene_sha256=hashlib.sha256(a.scene.read_bytes()).hexdigest(),runtime_sources=source,
                photometry_sha256=optics,photometry_unchanged=optics==optical_file_hashes(scene,a.ies_dir),
                runtime_sources_unchanged=all(hashlib.sha256((ROOT/k).read_bytes()).hexdigest()==v for k,v in source.items()))
    (out/'process.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(dict(out=str(out),exit_code=r.returncode,seconds=record['wall_seconds'])),flush=True)
    return r.returncode
if __name__=='__main__':raise SystemExit(main())
