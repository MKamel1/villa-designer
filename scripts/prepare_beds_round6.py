"""Generate slim-frame proposals from immutable round-5 models and twelve sources.

These are review proposals, including refused ones; never an activation receipt.
Source library bytes, layout, room cameras and historical extracts are read-only.
"""
from copy import deepcopy
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from archpipe.beds import (scaled_bed_fit, scaled_model_fit, slim_frame_fit,
                          model_mattress_bounds, review_selection)
from prepare_beds_round5 import source_geometry


def prepare(args):
    args.output.mkdir(parents=True,exist_ok=True)
    models=json.loads(args.models.read_text())
    scene=json.loads(args.scene.read_text())
    for model in models:
        source_geometry(model['asset'],'round2' if model['label']=='pb-bed' else 'round4',args.library)
        mattress={n for b in model['mattress_bindings'].values() for n in b['parts']}
        frame=([r['name'] for r in model['review_geometry']['meshes'] if r['name']=='Object_4']
               if model['label']=='pb-bed' else ['Bunk_cgt_bunk_bed_f_house_wood_0'])
        bedding=[r['name'] for r in model['review_geometry']['meshes'] if r['name'] not in mattress|set(frame)]
        model['frame_slimming']=dict(decision_date='2026-10-09',frame_parts=frame,bedding_parts=bedding,
            basis='Measured round-5 semantic cuts; Object_4 upholstery base, feet and head; bunk wood includes entire ladder. Remaining source meshes are bedding.')
        if model['required_berths']==2:
            top=next(c['mattress_top'] for c in scene['cloth'] if c['id']=='duvet-ka-bunk-upper')-model['position'][2]
            model['scaling'].update(height_berth='upper',mattress_top_m=top,
                height_source='ASSUMED unchanged design upper mattress top 1.402 m minus finished floor 0.002 m; round4 scene cloth')
        fit=scaled_model_fit(model)
        model['scale_xyz']=fit['scale_xyz']
        slim=slim_frame_fit(model)
        model['frame_slimming']['scale_xy']=slim['scale_xy']
        model['scaled_fit']=fit
        model['slim_fit']=slim
        model['resulting_mattresses_world_m']=model_mattress_bounds(model,world=True)
        model.pop('upper_height_shortfall_m',None)
        model['neutral_review']=dict(status='pending',source_sha256=model['review_geometry']['source_sha256'],
            orientation_evidence=deepcopy(model['orientation_evidence']),selection=review_selection(model))
        model['diagnostic_status']='round-6 proposed slim frame; refuses intake if factor below 0.5, room/height/visual gate closed'
        print(model['label'],'frame width/length',slim['width_factor'],slim['length_factor'],slim['reason'])
    (args.output/'models-proposed.json').write_text(json.dumps(models,separators=(',',':'))+'\n')
    # Imported neutral previews admit only geometrically eligible frame proposals.
    eligible=[m for m in models if m['slim_fit']['ok'] and m['scaled_fit']['ok']]
    (args.output/'models-previewable.json').write_text(json.dumps(eligible,separators=(',',':'))+'\n')
    # Re-screen ALL twelve for the fixed kids B mattress, regardless of original room.
    results=[]
    for folder,name in [('round2','round3'),('round4','round4')]:
        old=json.loads((ROOT/f'out/beds/{name}/recheck.json').read_text())['results']
        for row in old:
            geometry=source_geometry(row['asset'],folder,args.library)
            mattresses=row.get('actual_mattress_bounds_native_m',row.get('mattress_bounds_native_m'))
            bounds=row.get('actual_frame_bounds_native_m',row.get('real_frame_bounds_native_m'))
            front=row.get('dimension_front_axis') or ('-X' if 'cyberfox' in row['asset'] else '+X' if 'scandi' in row['asset'] else '+Z')
            fit=scaled_bed_fit(bounds,1.2,2.,front,length_axis=row.get('length_axis'),
                mattress_bounds=mattresses,mattress_top_m=.475,height_source='ASSUMED unchanged kids B top above finished floor',
                headboard_bounds=bounds,headboard_limit_m=1.8,headboard_limit_source='ASSUMED unchanged round-5 single-bed cap',
                required_berths=2 if mattresses and 'upper' in mattresses else 1)
            results.append(dict(asset=row['asset'],fit=fit,source_sha256=geometry['source_sha256'],
                frame_screen='Frame proportions do not reject mattress intake; frame fit follows only a passing complete mattress fit.'))
    (args.output/'kids-b-rescreen.json').write_text(json.dumps(dict(decision_date='2026-10-09',target_m=[1.2,2.],
        candidates=results,eligible_count=sum(r['fit']['ok'] for r in results)),indent=2)+'\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models',type=Path,default=ROOT/'out/beds/round5/models-pending.json')
    parser.add_argument('--scene',type=Path,default=ROOT/'out/beds/round4/scene.json')
    parser.add_argument('--library',type=Path,default=Path('/home/omar/archpipe/assets/library'))
    parser.add_argument('--output',type=Path,default=ROOT/'out/beds/round6')
    prepare(parser.parse_args())
