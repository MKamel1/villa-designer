"""Same-card procedural versus actual-model fixed-room comparisons."""
from pathlib import Path
import gzip,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from archpipe.beds import bed_room_review
from archpipe.furniture_room_review import baseline_relative_review
from archpipe.concept import villa_r11 as R,villa_furnish as F,revit_spec as RS

def main():
    output=ROOT/'out/desks/stage2';scene=json.loads((output/'live-procedural-scene.json').read_text())
    context=json.loads(gzip.decompress((output/'live-authoring-context.json.gz').read_bytes()))
    models=json.loads((output/'models-pending.json').read_text());layout=context['layout'];furniture=context['furniture'];sp=context['specification']
    results={}
    for model in models:
        mark=model['label'];baseline_scene=dict(scene,models=[m for m in scene['models'] if m.get('replaces')!=model['replaces']])
        baseline=bed_room_review(baseline_scene,layout,sp,furniture,target_marks=[mark],absolute=True)
        candidate=bed_room_review(dict(baseline_scene,models=baseline_scene['models']+[model]),layout,sp,furniture,target_marks=[mark],absolute=True)
        result=baseline_relative_review(baseline,candidate,target_prefixes=(mark+'::',model['id']+'::')+tuple(model['replacement_mesh_ids']),fixed_items=[it['id'] for it in furniture if it['id']!=mark])
        result.update(asset=model['asset'],planned_footprint_m=model['furniture_fitting']['footprint_m'])
        results[mark]=result
        (output/'room-comparison.json').write_text(json.dumps(results,indent=2)+'\n')
        print(mark,'baseline/model findings',len(baseline['findings']),len(candidate['findings']),'relative failures',len(result['findings']),flush=True)
    # Every chosen replacement must also work together, retaining all fixed
    # furniture and all fallback chairs. Compare the same target scope.
    marks=[m['label'] for m in models]
    baseline=bed_room_review(scene,layout,sp,furniture,target_marks=marks,absolute=True)
    candidate=bed_room_review(dict(scene,models=scene['models']+models),layout,sp,furniture,target_marks=marks,absolute=True)
    combined=baseline_relative_review(baseline,candidate,target_prefixes=tuple(p for m in models for p in (m['label']+'::',m['id']+'::',*m['replacement_mesh_ids'])),fixed_items=[it['id'] for it in furniture if it['id'] not in marks])
    (output/'combined-room-comparison.json').write_text(json.dumps(combined,indent=2)+'\n')
    print('combined',combined['ok'],len(combined['findings']),flush=True)
if __name__=='__main__':main()
