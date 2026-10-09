"""Measure twelve cached beds; construct explicit bounded scaled candidates.

Source assets and historical extracts stay immutable. Semantic mattress cuts
are generated face selections, reproduced in Blender without changing faces.
The scene is a diagnostic alternative, never a presentation integration.
"""
from pathlib import Path
import argparse
from copy import deepcopy
import gzip
import hashlib
import json
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from archpipe.beds import (scaled_bed_fit, scaled_model_fit, model_native_bounds,
                           model_mattress_bounds, review_selection, bed_room_review)
from archpipe.furniture_orientation import model_yaw
from archpipe.concept import villa_r11 as R, villa_furnish as F, revit_spec as RS
from bed_axis_evidence import components, native, bounds


def semantic_cut(geometry, recipes):
    """Partition actual faces by measured components; retain every face once."""
    result=deepcopy(geometry); selections={}; bindings={}
    source={m['name']:m for m in geometry['meshes']}
    used={}; new=[]
    for berth,recipe in recipes.items():
        name='measured-'+berth+'-mattress'; mesh=source[recipe['mesh']]
        groups=components(mesh['faces'])
        points=(groups[recipe['component_index']] if 'component_index' in recipe else
                next(g for g in groups if len(g)==recipe['expected_vertices']))
        if len(points)!=recipe['expected_vertices']:
            raise ValueError('measured mattress component changed')
        keys={tuple(round(float(v),5) for v in p) for p in points}
        indices=[]
        for i,face in enumerate(mesh['faces']):
            match=[tuple(round(float(v),5) for v in p) in keys for p in face]
            if any(match) and not all(match):raise ValueError('mattress cut would change a source face')
            if all(match):indices.append(i)
        if set(indices)&used.get(mesh['name'],set()):raise ValueError('overlapping mattress cuts')
        used.setdefault(mesh['name'],set()).update(indices)
        selections[name]=dict(source_mesh=mesh['name'],face_indices=indices)
        new.append(dict(mesh,name=name,faces=[mesh['faces'][i] for i in indices]))
        bindings[berth]=dict(parts=[name],head_at_max=False)
    result['meshes']=[dict(m,faces=[f for i,f in enumerate(m['faces']) if i not in used.get(m['name'],set())])
                      for m in geometry['meshes']]+new
    result['meshes']=[m for m in result['meshes'] if m['faces']]
    if sum(len(m['faces']) for m in result['meshes'])!=sum(len(m['faces']) for m in geometry['meshes']):
        raise ValueError('semantic cuts lost source faces')
    result['derivation']='generated semantic connected-component selections; every source face retained exactly once'
    return result,selections,bindings


def source_geometry(asset,folder,library):
    path=ROOT/'out/beds'/folder/'geometry'/(asset+'.json.gz')
    geometry=json.loads(gzip.decompress(path.read_bytes()))
    for name,digest in geometry['source_sha256'].items():
        source=(library/'props'/asset/name).resolve()
        if not source.is_relative_to((library/'props'/asset).resolve()) or hashlib.sha256(source.read_bytes()).hexdigest()!=digest:
            raise ValueError(asset+': stale source receipt '+name)
    return geometry


def prepare(args):
    args.output.mkdir(parents=True,exist_ok=True)
    old3=json.loads((ROOT/'out/beds/round3/recheck.json').read_text())['results']
    old4=json.loads((ROOT/'out/beds/round4/recheck.json').read_text())['results']
    scene=json.loads(args.scene.read_text())
    items=F.layout(R.design('D1')); lookup={i['id']:i for i in items}
    targets={'pb-bed':[1.6,2.],'ka-bunk':[.9,2.],'kb-bed':[1.2,2.]}
    tops={k:next(c['mattress_top'] for c in scene['cloth'] if c['id']=='duvet-'+k) for k in targets}
    # Source-size checks are historical evidence. Recompute the new factors
    # from those unchanged measurements, including every refused candidate.
    intake=[]
    for old,folder in [(r,'round2') for r in old3]+[(r,'round4') for r in old4]:
        asset=old['asset']; geometry=source_geometry(asset,folder,args.library)
        bed=old.get('bed') or ('ka-bunk' if 'bunk' in asset else 'pb-bed' if 'cyberfox' in asset else 'kb-bed')
        frame=old.get('actual_frame_bounds_native_m',old.get('real_frame_bounds_native_m'))
        mattresses=old.get('actual_mattress_bounds_native_m',old.get('mattress_bounds_native_m'))
        front=old.get('dimension_front_axis') or ('-X' if 'cyberfox' in asset else '+X' if 'scandi' in asset else '+Z')
        fit=scaled_bed_fit(frame,*targets[bed],front,mattress_bounds=mattresses,
            mattress_top_m=tops[bed]-.002,height_source='ASSUMED existing procedural mattress top; round4 scene cloth receipt, floor 0.002 m',
            headboard_bounds=frame,headboard_limit_m=2.4 if bed=='ka-bunk' else 1.8,
            headboard_limit_source='ASSUMED review cap: single 1.8 m, bunk 2.4 m; existing authored heads 0.95/1.05/1.70 m; not a published standard',
            length_axis=old.get('length_axis'),required_berths=2 if bed=='ka-bunk' else 1)
        intake.append(dict(asset=asset,bed=bed,fit=fit,omitted_meshes=[],source_sha256=geometry['source_sha256']))
    chosen=[dict(asset='sf_bed_upholstered_cyberfox',folder='round2',bed='pb-bed',front='-X',
                 recipes={'lower':dict(mesh='Object_4',expected_vertices=126)},headboard=['Object_4']),
            dict(asset='sf_bed3_2cabd354',folder='round4',bed='ka-bunk',front='+Z',
                 recipes={key:dict(mesh='Bunk_cgt_bunk_bed_f_house_carpet_0',component_index=i,expected_vertices=361)
                          for key,i in [('lower',4),('upper',7)]},headboard=['Bunk_cgt_bunk_bed_f_house_wood_0'])]
    models=[]
    manifest={r['id']:r for r in json.loads((ROOT/'ops/workstation/library-manifest.json').read_text())['props']}
    for choice in chosen:
        asset,bed=choice['asset'],choice['bed']; piece=lookup[bed]
        geometry,selections,bindings=semantic_cut(source_geometry(asset,choice['folder'],args.library),choice['recipes'])
        yaw=model_yaw(piece['rot'],choice['front'])
        top=tops[bed]-.002
        model=dict(id='model-'+bed,asset=asset,role='bed',scale=1.,scale_xyz=[1.,1.,1.],
            position=[piece['cx'],piece['cy'],.002],rotation_deg=[0,0,yaw],layout_rotation_deg=float(piece['rot']),
            front_axis=choice['front'],length_axis=choice['front'][-1],replaces='furn-'+bed+'-',room=piece['room'],label=bed,
            planned_mattress_m=targets[bed],required_berths=piece.get('berths',1),mattress_bindings=bindings,
            part_selections=selections,review_geometry=geometry,unit_evidence=dict(unit='m',source='glTF 2.0 metres; downloaded files unmodified'),
            contents_review=dict(status='bed-only',basis='Round 2/4 full-size opposing neutral images and actual connected parts; no bedside tables, benches or rugs',extras=[],fused_extras=[]),
            omitted_meshes=[],footprint_w=F.footprint(piece)[2]-F.footprint(piece)[0],
            footprint_d=F.footprint(piece)[3]-F.footprint(piece)[1],reference_h=piece['h'],
            scaling=dict(decision_date='2026-10-09',mattress_top_m=top,
                height_source=f'ASSUMED design: unchanged procedural duvet-{bed} mattress_top {tops[bed]:.3f} m minus finished floor 0.002 m; villa_render.build bedding and furniture generator/detail',
                headboard_parts=choice['headboard'],headboard_limit_m=2.4 if bed=='ka-bunk' else 1.8,
                headboard_limit_source='ASSUMED diagnostic cap: single 1.8 m, bunk 2.4 m; generous compared with existing authored heads 0.95/1.05/1.70 m, below room ceiling; not a standard'))
        fit=scaled_model_fit(model)
        if not fit['ok']:raise ValueError(asset+': '+fit['reason'])
        model['scale_xyz']=fit['scale_xyz'];model['native_bounds']=model_native_bounds(model)
        model['orientation_evidence']=dict(front_axis=choice['front'],basis='Round 2/4 actual headboard/pillow component placement and opposing neutral previews; both bunk heads at source positive Blender Y')
        model['neutral_review']=dict(status='pending',source_sha256=geometry['source_sha256'],orientation_evidence=model['orientation_evidence'],selection=review_selection(model))
        model['attribution']={k:manifest[asset].get(k) for k in ('credit','author','licence','source_url')}
        model['scaled_fit']=fit;model['diagnostic_status']='proposed scaled candidate; neutral, C8 and cloth review required'
        model['resulting_mattresses_world_m']=model_mattress_bounds(model,world=True)
        if bed=='ka-bunk':
            upper=next(c['mattress_top'] for c in scene['cloth'] if c['id']=='duvet-ka-bunk-upper')
            model['upper_height_shortfall_m']=upper-model['resulting_mattresses_world_m']['upper']['max'][2]
        models.append(model)
    (args.output/'models-pending.json').write_text(json.dumps(models,separators=(',',':'))+'\n')
    (args.output/'intake.json').write_text(json.dumps(dict(decision_date='2026-10-09',candidates=intake),indent=2)+'\n')
    print('Measured all twelve sources; constructed',len(models),'scaled diagnostic candidates')
    for m in models:print(m['asset'],m['scaled_fit']['sx'],m['scaled_fit']['sy'],m['scaled_fit']['sz'],m.get('upper_height_shortfall_m'))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library',type=Path,default=Path('/home/omar/archpipe/assets/library'))
    parser.add_argument('--scene',type=Path,default=ROOT/'out/beds/round4/scene.json')
    parser.add_argument('--output',type=Path,default=ROOT/'out/beds/round5')
    prepare(parser.parse_args())
