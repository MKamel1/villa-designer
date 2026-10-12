"""Compare the current procedural parents bed and retained slim-frame model."""
from copy import deepcopy
import json
import gzip
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from archpipe.beds import bed_room_review, slim_frame_fit, review_selection
from archpipe.furniture_room_review import baseline_relative_review
from archpipe.concept import villa_r11 as R, villa_furnish as F, revit_spec as RS

def main():
    output=ROOT/'out/beds/round7';output.mkdir(parents=True,exist_ok=True)
    scene=json.loads((ROOT/'out/desks/stage2/live-procedural-scene.json').read_text())
    models=json.loads((ROOT/'out/beds/round6/models-previewable.json').read_text())
    model=deepcopy(next(m for m in models if m['label']=='pb-bed'))
    context=json.loads(gzip.decompress((ROOT/'out/desks/stage2/live-authoring-context.json.gz').read_bytes()))
    layout=context['layout'];furniture=context['furniture'];specification=context['specification']
    mark=model['label'];scene=dict(scene,models=[m for m in scene['models'] if m.get('role')!='bed'])
    cloth_path=output/'baseline-previews'/('pb-bed-evaluated-cloth.json.gz')
    if not cloth_path.is_file():
        raise ValueError('baseline review requires current evaluated procedural soft goods from neutral preview')
    scene=dict(scene,meshes=scene['meshes']+json.loads(gzip.decompress(cloth_path.read_bytes())))
    baseline=bed_room_review(scene,layout,specification,furniture,target_marks=[mark],absolute=True)
    results={}
    for depth,side in ((.1,.05),(.05,.05),(.05,0.),(0.,0.)):
        model['frame_slimming'].update(head_depth_m=depth,side_extension_m=side)
        model['frame_slimming'].pop('scale_xy',None)
        model['frame_slimming']['scale_xy']=slim_frame_fit(model)['scale_xy']
        model['neutral_review']=dict(status='pending',source_sha256=model['review_geometry']['source_sha256'],
            orientation_evidence=deepcopy(model['orientation_evidence']),selection=review_selection(model))
        trial=dict(scene,models=scene['models']+[model],meshes=[r for r in scene['meshes']
            if not r['id'].startswith(('cloth-duvet-'+mark,'cloth-throw-'+mark))])
        candidate=bed_room_review(trial,layout,specification,furniture,
            target_marks=[mark],absolute=True)
        result=baseline_relative_review(baseline,candidate,
            target_prefixes=(mark+'::',model['id']+'::','furn-'+mark+'-','dress-pillow-'+mark+'-','cloth-duvet-'+mark,'cloth-throw-'+mark),
            fixed_items=[it['id'] for it in furniture if it['id']!=mark])
        results[f'{depth}/{side}']=result
        print('head extension',depth,'baseline/model findings',len(baseline['findings']),len(candidate['findings']),
              'relative failures',len(result['findings']),flush=True)
    (output/'room-comparison.json').write_text(json.dumps(results,indent=2)+'\n')
    (output/'models-pending.json').write_text(json.dumps([model],separators=(',',':'))+'\n')

if __name__=='__main__':main()
