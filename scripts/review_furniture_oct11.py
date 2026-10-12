"""Review omissions and seat-driven chairs against identical procedural rooms."""
from copy import deepcopy
from pathlib import Path
import json,gzip,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from archpipe.beds import bed_room_review
from archpipe.concept.furniture_stage2 import derived_seats
from archpipe.furniture_room_review import baseline_relative_review
OUT=ROOT/'out/furniture-oct11'
def compare(scene,context,models,marks):
    furniture=context['furniture']+derived_seats(context['furniture']);layout=context['layout'];spec=context['specification']
    marks=list(dict.fromkeys(marks+[m['label'].split('#')[0] for m in models if m['role']=='task_chair']))
    baseline=bed_room_review(scene,layout,spec,furniture,target_marks=marks,absolute=True)
    prefixes={m['replaces'] for m in models}
    trial=dict(scene,models=[m for m in scene['models'] if m.get('replaces') not in prefixes]+models,
        meshes=[r for r in scene['meshes'] if not any(r['id'].startswith(('cloth-duvet-'+m['label'],'cloth-throw-'+m['label'])) for m in models if m['role']=='bed')])
    candidate=bed_room_review(trial,layout,spec,furniture,target_marks=marks,absolute=True)
    return baseline_relative_review(baseline,candidate,target_prefixes=tuple(p for m in models for p in (m['label']+'::',m['id']+'::',m['replaces'],'dress-pillow-'+m['label']+'-','cloth-duvet-'+m['label'],'cloth-throw-'+m['label'])),fixed_items=[it['id'] for it in furniture if it['id'] not in [m['label'] for m in models]])
def main():
    scene=json.loads((OUT/'current-furniture-scene.json').read_text())
    context=json.loads(gzip.decompress((ROOT/'out/desks/stage2/live-authoring-context.json.gz').read_bytes()))
    scene['meshes']+=json.loads(gzip.decompress((ROOT/'out/beds/round7/baseline-previews/pb-bed-evaluated-cloth.json.gz').read_bytes()))
    for kind in ('bed','chairs'):
        models=json.loads((OUT/(kind+'-pending.json')).read_text());results={}
        for model in models:
            result=compare(scene,context,[model],[model['label']]);results[model['label']]=result
            print(kind,model['label'],result['ok'],result['findings'],flush=True)
            (OUT/(kind+'-room-comparison.json')).write_text(json.dumps(results,indent=2)+'\n')
        combined=compare(scene,context,models,[m['label'] for m in models])
        (OUT/(kind+'-combined.json')).write_text(json.dumps(combined,indent=2)+'\n')
        print('Combined',kind,combined['ok'],flush=True)
if __name__=='__main__':main()
