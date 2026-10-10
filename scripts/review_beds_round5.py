"""Review pending scaled beds against the unchanged authored room geometry.

This is diagnostic evidence, not an integration gate waiver. C8 means the
project's geometry-topology review. Source extracts are never edited.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from archpipe.beds import bed_room_review, scaled_model_fit, model_mattress_bounds, slim_frame_fit, slim_frame_findings, model_review_meshes
from archpipe.concept import villa_r11 as R, villa_furnish as F, revit_spec as RS


def review(args):
    scene=json.loads(args.scene.read_text())
    models=json.loads(args.models.read_text())
    layout=R.design('D1');furniture=F.layout(layout);specification=RS.build(layout)
    results={}
    for model in models:
        trial=dict(scene,models=[m for m in scene.get('models',[])
            if m.get('replaces')!=model['replaces']]+[deepcopy(model)])
        result=bed_room_review(trial,layout,specification,furniture)
        fit=scaled_model_fit(model)
        actual=model_mattress_bounds(model,world=True)
        heights=[]
        for berth,box in actual.items():
            cloth_id='duvet-'+model['label']+('-upper' if berth=='upper' else '')
            target=next(c['mattress_top'] for c in scene['cloth'] if c['id']==cloth_id)
            heights.append(dict(berth=berth,achieved_m=box['max'][2],required_m=target,
                shortfall_m=target-box['max'][2],basis='ASSUMED unchanged procedural mattress top in source scene'))
        result.update(asset=model['asset'],scaled_fit=fit,mattress_heights=heights,
                      activation_allowed=result['ok'] and all(abs(r['shortfall_m'])<=1e-5 for r in heights))
        if model.get('frame_slimming'):
            slim=slim_frame_fit(model)
            failures=slim_frame_findings(model,model_review_meshes([model]))
            result.update(slim_fit=slim,slim_frame_findings=failures,
                activation_allowed=result['activation_allowed'] and slim['ok'] and not failures,
                geometry_status='Measured proposed transform; a refused frame factor is diagnostic only, never importable')
        results[model['id']]=result
        print(model['label'],len(result['findings']),'room findings; activation',result['activation_allowed'])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(results,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene',type=Path,default=ROOT/'out/beds/round4/scene.json')
    parser.add_argument('--models',type=Path,default=ROOT/'out/beds/round5/models-pending.json')
    parser.add_argument('--output',type=Path,default=ROOT/'out/beds/round5/c8-complete.json')
    review(parser.parse_args())
