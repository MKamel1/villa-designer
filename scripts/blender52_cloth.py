"""Evaluate all scene cloth templates without updating the production cache."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from archpipe import drape_appearance as D
from archpipe.imported_appearance import digest

def main():
    p=argparse.ArgumentParser();p.add_argument('--scene',type=Path,default=ROOT/'out/blender52/scene.json');a=p.parse_args()
    out=ROOT/'out/blender52/cloth';out.mkdir(parents=True,exist_ok=True)
    scene=json.loads(a.scene.read_text());inputs={}
    for part in scene['meshes']:
        if D.eligible(part):
            data,_=D.local_input(part);inputs.setdefault(digest(data),(data,part['id']))
    exe=Path('/home/omar/opt/blender-5.2.2-linux-x64/blender')
    sha=hashlib.sha256(exe.read_bytes()).hexdigest();rows=[]
    cache=json.loads(__import__('gzip').decompress(D.CACHE_PATH.read_bytes()))['entries']
    for key,(data,ident) in inputs.items():
        data=dict(data,runtime=dict(data['runtime'],blender_version='5.2.2 LTS',blender_sha256=sha))
        path=out/(key+'-input.json');path.write_text(json.dumps(data));records=[]
        for trial in (1,2):
            dest=out/(key+f'-process-{trial}.json');log=out/(key+f'-process-{trial}.log')
            if not dest.exists():
                command=['nice','-n','15',str(exe),'-b','-t','1','--python-exit-code','1','-P',str(D.GENERATOR_PATH),'--','--input',str(path),'--output',str(dest)]
                start=time.time()
                with log.open('w') as stream:
                    r=subprocess.run(command,cwd=ROOT,env=dict(os.environ,PYTHONHASHSEED='0' if trial==1 else '987654',PYTHONPATH=str(ROOT/'src'),BLENDER_USER_CONFIG=str(out/'config')),stdout=stream,stderr=subprocess.STDOUT)
                (out/(key+f'-process-{trial}-receipt.json')).write_text(json.dumps(dict(exit_code=r.returncode,seconds=time.time()-start,command=command)))
                if r.returncode:raise RuntimeError(str(log))
            records.append(json.loads(dest.read_text()))
        row=dict(id=ident,source_input_sha256=key,candidate_input_sha256=digest(data),reproducible=digest(records[0])==digest(records[1]),
                 candidate_mesh_sha256=records[0]['mesh_sha256'],baseline_mesh_sha256=cache[key]['mesh_sha256'],
                 equals_45=records[0]['mesh_sha256']==cache[key]['mesh_sha256'])
        rows.append(row);(out/'comparison.json').write_text(json.dumps(rows,indent=2));print(ident,row['reproducible'],row['equals_45'],flush=True)
    print('cloth inputs completed',len(rows),flush=True)
if __name__=='__main__':main()
