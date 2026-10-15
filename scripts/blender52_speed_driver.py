"""Run the pre-registered speed experiment from completed, bound scene copies."""
import fcntl,hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
from blender52_compare import image_metrics
from archpipe.render_qa import check
from villa_render import villa_qa_context
from PIL import Image

def main():
    base=ROOT/'out/blender52';protocol=json.loads((base/'protocol.json').read_text());scene=json.loads((base/'scene.json').read_text())
    views={v['id']:v for v in scene['views']};result=[]
    for version,folder,reference in [('4.5.14','reference45',True),('5.2.2','drafts52',False)]:
        receipt=json.loads((base/folder/'process.json').read_text())
        if receipt['exit_code']!=0 or not receipt['runtime_sources_unchanged']:raise RuntimeError('Unsuccessful source scene process: '+folder)
        for ident in protocol['speed_views']:
            blend=base/folder/(ident+'.blend');out=base/'speed'/version/ident;out.mkdir(parents=True,exist_ok=True)
            if (out/'process.json').exists():raise RuntimeError('Refusing to reuse unverified speed output '+str(out))
            exe=Path.home()/('opt/blender-'+version+'-linux-x64/blender')
            cmd=['nice','-n','10',str(exe),'-b',str(blend),'-t','8','--python-exit-code','1','-P',str(ROOT/'scripts/blender52_speed.py'),'--','--out',str(out)]
            if reference:cmd+=['--reference']
            with Path('/home/omar/archpipe/locks/graphics.lock').open('rb') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX)
                with (out/'process.log').open('w') as log:
                    start=time.time();r=subprocess.run(cmd,cwd=ROOT,env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),BLENDER_USER_CONFIG=str(out/'config'),BLENDER_USER_SCRIPTS=str(out/'scripts')),stdout=log,stderr=subprocess.STDOUT,timeout=1800)
            record=dict(command=cmd,exit_code=r.returncode,wall_seconds=time.time()-start,blend_sha256=hashlib.sha256(blend.read_bytes()).hexdigest(),executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest())
            (out/'process.json').write_text(json.dumps(record,indent=2))
            if r.returncode:raise RuntimeError(str(out/'process.log'))
            print('Completed speed ladder',version,ident,flush=True)
    for ident in protocol['speed_views']:
        ref=base/'speed/4.5.14'/ident;candidate=base/'speed/5.2.2'/ident
        before=json.loads((base/'reference45'/(ident+'.json')).read_text());after=json.loads((base/'drafts52'/(ident+'.json')).read_text())
        qa_reference=check(ref/'1024.png',villa_qa_context(scene,views[ident],before));rows=[]
        for timing in json.loads((candidate/'timings.json').read_text()):
            n=timing['samples'];qa=check(candidate/(str(n)+'.png'),villa_qa_context(scene,views[ident],after))
            metrics=image_metrics(Image.open(ref/'1024.png'),Image.open(candidate/(str(n)+'.png')))
            threshold=protocol['threshold'];passed=qa['passed'] and metrics['display_rgb_mae']<=threshold['display_rgb_mean_absolute_error_max'] and metrics['display_rgb_absolute_error_p95']<=threshold['display_rgb_absolute_error_p95_max']
            rows.append(dict(**timing,metrics=metrics,qa=qa,passes_registered_threshold=passed))
        result.append(dict(view=ident,reference_timing=json.loads((ref/'timings.json').read_text()),reference_qa=qa_reference,candidates=rows,first_passing_sample_count=next((r['samples'] for r in rows if r['passes_registered_threshold']),None)))
    (base/'speed/comparison.json').write_text(json.dumps(dict(protocol=protocol,views=result),indent=2))
if __name__=='__main__':main()
