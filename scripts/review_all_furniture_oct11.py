"""Joint relative room review, keeping all individually reviewed replacements."""
from pathlib import Path
import json,gzip,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from archpipe.concept.furniture_stage2 import digest
from archpipe.furniture_fit import review_selection
from archpipe.beds import review_selection as bed_selection
from review_furniture_oct11 import compare
OUT=ROOT/'out/furniture-oct11'
def inputs():
 context=json.loads(gzip.decompress((ROOT/'out/desks/stage2/live-authoring-context.json.gz').read_bytes()))
 current=json.loads((OUT/'current-furniture-scene.json').read_text())
 old=json.loads(gzip.decompress((ROOT/'knowledge/furniture-stage2.json.gz').read_bytes()))
 desks=[dict(m,review_geometry=old['geometry'][m['asset']]) for m in old['models'] if m['role']=='desk']
 models=desks+json.loads((OUT/'chairs-pending.json').read_text())+json.loads((OUT/'bed-pending.json').read_text())
 current['meshes']+=json.loads(gzip.decompress((ROOT/'out/beds/round7/baseline-previews/pb-bed-evaluated-cloth.json.gz').read_bytes()))
 signature=digest(dict(scene=current,context=context,selections=[bed_selection(m) if m['role']=='bed' else review_selection(m) for m in models]))
 return current,context,models,signature
def main():
 current,context,models,signature=inputs()
 result=compare(current,context,models,[m['label'] for m in models]);result['inputs_sha256']=signature
 (OUT/'all-replacements-combined.json').write_text(json.dumps(result,indent=2)+'\n')
 print('Joint replacements',result['ok'],'failures',len(result['findings']),flush=True)
 if not result['ok']:raise ValueError('combined room review closed')
if __name__=='__main__':main()
