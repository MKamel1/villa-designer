"""Bake portable tailoring separately; preserve the original gravity cache.

Two independent project-Python processes have different process hash salts.
Every source shape and every bounded folded variant is computed twice. Only
identical complete outputs are promoted, atomically, to the derived cache.
"""
import argparse
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from archpipe import drape_appearance as D, drape_polish as P
from archpipe.imported_appearance import digest,encoded


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker',type=Path)
    parser.add_argument('--scene',type=Path,help='Use eligible physical parts in this saved scene instead of the frozen source replay')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.worker:
        case=json.loads(args.worker.read_text());results={}
        for key,row in case.items():
            results[key]=P.apply(row['data'],row['original'],encoded(row['input']['polish']))
        args.output.write_bytes(encoded(results));return
    fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/drape-boards-before.json.gz').read_bytes()))
    parts=json.loads(args.scene.read_text())['meshes'] if args.scene else fixture['parts']
    cache=json.loads(gzip.decompress(D.CACHE_PATH.read_bytes()));sources={};inputs={}
    for part in parts:
        if not D.eligible(part):continue
        if part.get('garment_type') not in ('shirt','jacket',None):continue
        data,_=D.local_input(part);base_key=digest(data)
        if base_key in sources:continue
        sources[base_key]=True
        for variant in range(8) if part['part_kind']=='folded-fabric' else (0,):
            binding=json.loads(P.binding(part));binding['variant']=variant
            original=cache['entries'][base_key];D._admit_template(encoded(data),encoded(original))
            value=P.cache_input(data,original,encoded(binding));key=digest(value)
            inputs[key]=dict(data=data,original=original,input=value)
    out=ROOT/'out/drape-polish';out.mkdir(exist_ok=True,parents=True)
    source=out/'polish-inputs.json';source.write_bytes(encoded(inputs));paths=[];outputs=[]
    for i,salt in enumerate(('0','987654')):
        target=out/f'polish-process-{i+1}.json';paths.append(str(target.relative_to(ROOT)))
        subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker',str(source),'--output',str(target)],
                       cwd=ROOT,env=dict(os.environ,PYTHONHASHSEED=salt),check=True)
        outputs.append(json.loads(target.read_text()))
    if digest(outputs[0])!=digest(outputs[1]):raise ValueError('independent polish process mismatch')
    entries={key:dict(input=row['input'],template=outputs[0][key],process_sha256=[digest(output[key]) for output in outputs])
             for key,row in inputs.items()}
    pending=P.CACHE_PATH.with_suffix('.gz.tmp')
    pending.write_bytes(gzip.compress(encoded(dict(schema='drape-polish-cache/1',entries=entries)),mtime=0))
    pending.replace(P.CACHE_PATH)
    (out/'polish-determinism.json').write_text(json.dumps(dict(unique_inputs=len(entries),process_paths=paths,
        process_hash_salts=[0,987654],complete_output_sha256=[digest(o) for o in outputs],
        original_gravity_cache_sha256=__import__('hashlib').sha256(D.CACHE_PATH.read_bytes()).hexdigest()),indent=2)+'\n')
    print('portable polished inputs:',len(entries),flush=True)

if __name__=='__main__':main()
