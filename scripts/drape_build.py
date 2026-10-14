"""Generate/reuse bounded cloth inputs and prove independent-process hashes.

The project's Python drives Blender; Blender never installs dependencies.
This writes only owned cache/evidence paths, never shared symlink data.
"""
import argparse
import gzip
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from archpipe import drape_appearance as D
from archpipe.imported_appearance import digest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender',type=Path,default=Path('/home/omar/opt/blender/blender'))
    parser.add_argument('--scene',type=Path,default=ROOT/'out/garments/final-scene.json')
    parser.add_argument('--prototype',action='store_true')
    args=parser.parse_args();out=ROOT/'out/drape';out.mkdir(exist_ok=True)
    import hashlib
    runtime=json.loads((ROOT/'knowledge/drape-runtime.json').read_text())
    if hashlib.sha256(args.blender.read_bytes()).hexdigest()!=runtime['blender_sha256']:
        raise ValueError('unpinned Blender executable')
    scene=json.loads(args.scene.read_text())
    entries={};records=[];by_key={}
    for part in scene['meshes']:
        if D.eligible(part):
            data,origin=D.local_input(part);by_key.setdefault(digest(data),(data,part))
    print('unique cloth inputs:',len(by_key),flush=True)
    if args.prototype and D.CACHE_PATH.exists():
        entries.update(json.loads(gzip.decompress(D.CACHE_PATH.read_bytes()))['entries'])
    for number,(key,(data,part)) in enumerate(by_key.items()):
        if args.prototype and part.get('garment_type')!='dress':continue
        input_path=out/(key+'-input.json');input_path.write_text(json.dumps(data))
        paths=[];template=None;process_hashes=[]
        for trial in (1,2):
            path=out/(key+f'-process-{trial}.json');paths.append(path)
            if not path.exists() or json.loads(path.read_text()).get('input_sha256')!=key:
                command=[str(args.blender),'-b','-t','1','--python-exit-code','1','-P',str(D.GENERATOR_PATH),'--',
                         '--input',str(input_path),'--output',str(path)]
                with (out/(key+f'-process-{trial}.log')).open('w') as log:
                    subprocess.run(command,check=True,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            current=json.loads(path.read_text())
            if current['input_sha256']!=key or current['mesh_sha256']!=digest(current['faces']):
                raise ValueError('corrupt cached process output '+str(path))
            process_hashes.append(digest(current))
            if template is not None and digest(current)!=digest(template):raise ValueError('independent-process cloth mismatch '+key)
            template=current
        template['independent_process_sha256']=process_hashes
        local=dict(part,faces=data['faces'])
        template['enclosure']=D.enclosure_measurement(template,local)
        from archpipe.concept.physical_part import geometry_errors
        errors=geometry_errors(template['faces'])
        if errors:raise ValueError(part['id']+': invalid closed cloth shell '+str(errors))
        row=dict(template,id=part['id'],garment_type=part.get('garment_type'))
        errors=D.appearance_findings(row)
        if errors:raise ValueError('; '.join(errors))
        if template['enclosure']['maximum_escape_m']>D.policy()['spacing_m']:
            raise ValueError(part['id']+': escaped envelope '+str(template['enclosure']))
        entries[key]=template
        metrics=D.measure(template['skin_vertices'],template['boundary_indices']) if part.get('garment_type') else None
        records.append(dict(input_sha256=key,physical_id=part['id'],mesh_sha256=template['mesh_sha256'],
                            process_paths=[str(p.relative_to(ROOT)) for p in paths],metrics=metrics,enclosure=template['enclosure']))
        print(number+1,part['id'],metrics,template['enclosure']['maximum_escape_m'],flush=True)
    pending=D.CACHE_PATH.with_suffix('.gz.tmp')
    pending.write_bytes(gzip.compress(json.dumps(dict(schema='drape-cloth-cache/1',entries=entries),sort_keys=True,separators=(',',':')).encode(),mtime=0))
    pending.replace(D.CACHE_PATH)
    (out/'determinism.json').write_text(json.dumps(dict(independent_processes=True,records=records),indent=2)+'\n')
    print('cache complete:',D.CACHE_PATH,flush=True)

if __name__=='__main__':main()
