"""Generate bounded source-bedding omissions and seat-driven chair candidates.

Source files, native extracts and historical receipts are immutable. A complete
connected component can be named; no face is cut or individually stretched.
"""
from copy import deepcopy
import gzip, hashlib, json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from prepare_beds_round5 import semantic_cut
from inventory_desks import inventory
from archpipe.furniture_fit import model_fit, review_selection, native_box, fit_factors, replacement_floor
from archpipe.beds import review_selection as bed_selection, slim_frame_fit, scaled_model_fit, model_native_bounds
from archpipe.furniture_orientation import model_yaw
OUT=ROOT/'out/furniture-oct11'
BACK_SOURCE='OSHA Computer Workstations eTool, Purchasing Guide, Chairs item 11; https://www.osha.gov/etools/computer-workstations/checklists/purchasing-guide (read 2026-10-11); backrest top at least 17.7 inches above compressed seat pan; no published upper limit'

def bed_without_source_covers(model):
    """Only partition the previously identified bedding; protect structural rows."""
    result=deepcopy(model)
    bedding=set(result['frame_slimming']['bedding_parts'])
    protected=set(result['frame_slimming']['frame_parts'])|{n for b in result['mattress_bindings'].values() for n in b['parts']}
    if bedding & protected or len(bedding)!=1:
        raise ValueError('source covers must be separable from every frame and mattress part')
    mesh=next(iter(bedding))
    recipes={name:dict(mesh=mesh,component_index=i,expected_vertices=count,name='source-'+name)
             for name,i,count in [('quilt',0,6331),('throw',1,4150),('pillow-left',2,1336),('pillow-right',3,1336)]}
    geometry,selections,_=semantic_cut(result['review_geometry'],recipes)
    if any(r['name']==mesh for r in geometry['meshes']):
        raise ValueError('unclassified or fused source bedding remains; omission refused')
    original={r['name']:r for r in result['review_geometry']['meshes'] if r['name'] in protected}
    if original!={r['name']:r for r in geometry['meshes'] if r['name'] in protected}:
        raise ValueError('bedding omission changed frame or mattress triangles')
    result['review_geometry']=geometry
    result['part_selections'].update(selections)
    result['omitted_meshes']=['source-quilt','source-throw']
    result['contents_review']=dict(status='bed-only',basis='Lead decision 2026-10-11: omit only complete connected source covers; all source frame/mattress faces unchanged; independent pillow room review',extras=list(result['omitted_meshes']),fused_extras=[])
    result['frame_slimming']['bedding_parts']=['source-pillow-left','source-pillow-right']
    result['frame_slimming']['scale_xy']=slim_frame_fit(result)['scale_xy']
    result['slim_fit']=slim_frame_fit(result)
    result['scaled_fit']=scaled_model_fit(result)
    result['native_bounds']=model_native_bounds(result)
    result['diagnostic_status']='2026-10-11 separable source covers omitted; current room, cloth and neutral gates pending'
    result['neutral_review']=dict(status='pending',source_sha256=geometry['source_sha256'],orientation_evidence=deepcopy(result['orientation_evidence']),selection=bed_selection(result))
    return result

def chair_candidate(geometry,recipe,omitted=(),front='+Z'):
    source=deepcopy(geometry)
    cut,selections,bindings=semantic_cut(source,{'seat':dict(recipe,name='measured-seat')})
    chair=dict(id='measured-chair',role='task_chair',asset=geometry['asset'],front_axis=front,
        review_geometry=cut,part_selections=selections,omitted_meshes=list(omitted),
        contents_review=dict(status='item-only',basis='Complete chair and connected seat from measured source geometry and neutral source views',extras=list(omitted),fused_extras=[]),
        furniture_fitting=dict(decision_date='2026-10-09',height_parts=bindings['seat']['parts'],footprint_m=[.44,.45],height_m=.46,height_basis='design',height_source='ASSUMED villa_furnish3d._chair defaults: seat 0.460 m; existing design input',
            back_height_range=dict(parts=[recipe['mesh']],datum='above-seat',min_m=17.7*.0254,max_m=None,basis='citation',source=BACK_SOURCE)))
    chair['measured_fit']=model_fit(chair)
    return chair

def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    model=json.loads((ROOT/'out/beds/round7/models-pending.json').read_text())[0]
    (OUT/'bed-before.json.gz').write_bytes(gzip.compress(json.dumps(model).encode(),mtime=0))
    bed=bed_without_source_covers(model)
    (OUT/'bed-pending.json').write_text(json.dumps([bed],separators=(',',':'))+'\n')
    intake=json.loads((ROOT/'out/desks/stage2/intake.json').read_text())
    candidates=[]
    for record in intake:
        asset=record['asset']
        if not any(k in record['name'].lower() for k in ('chair','lamy','flannigan')):continue
        geometry=json.loads(gzip.decompress((ROOT/'out/desks/stage2/geometry'/(asset+'.json.gz')).read_bytes()))
        recipes=[]
        if asset.endswith('531bff2f'):recipes=[(dict(mesh='Flanninga_Chair_0',component_index=0,expected_vertices=3769),[], '+Z')]
        elif asset.endswith('aee7ef03'):recipes=[(dict(mesh=name,component_index=0,expected_vertices=1026),[other],'+Z') for name,other in [('Object_4','Object_6'),('Object_6','Object_4')]]
        elif asset.endswith('c187de2b'):recipes=[(dict(mesh=geometry['meshes'][0]['name'],component_index=5,expected_vertices=272),[],'-Z')]
        if recipes:
            for recipe,omitted,front in recipes:
                chair=chair_candidate(geometry,recipe,omitted,front)
                fit=chair['measured_fit']
                record.setdefault('seat_rule_oct11',[]).append(dict(item=recipe['mesh'],fit=fit,omitted_meshes=omitted,seat_component=recipe))
                if fit['ok']:candidates.append(chair)
        else:
            record['seat_rule_oct11']=dict(plan_screens=record['fits'],reason=record.get('refusal'),status='refused: plan failure, incompatible chair type, or complete seat datum unavailable; no invented seat height')
    (OUT/'chair-intake.json').write_text(json.dumps(intake,indent=2)+'\n')
    # Same leather appearance for task chairs, independently measured one-chair
    # sibling. White/chrome is an alternate; keep existing kids palette refusal.
    choice=next(c for c in candidates if c['asset'].endswith('aee7ef03'))
    scene=json.loads((ROOT/'out/desks/stage2/live-procedural-scene.json').read_text())
    rows=inventory()['items'];models=[]
    for item in rows:
        if item['type']!='task_chair':continue
        model=deepcopy(choice);rot=item['rotation_deg'];w,d=item['planned_footprint_m'];label=item['id']
        prefix='furn-'+label.replace('#','-')+'-'
        model.update(id='model-'+label,label=label,room=item['room'],level=item['level'],replaces=prefix,
            position=item['centre_m']+[.002],rotation_deg=[0,0,model_yaw(rot,model['front_axis'])],layout_rotation_deg=rot,
            orientation_evidence=dict(front_axis=model['front_axis'],basis='Native back component at negative Z; full seat extends toward positive Z; opposing source neutral images'),
            unit_evidence=dict(unit='m',source='glTF 2.0 metres; no inferred source unit correction'),scale=1.,
            footprint_w=d if rot in (-90,90) else w,footprint_d=w if rot in (-90,90) else d,asset_kind='appearance',decimate_ratio=1.)
        model['credit']=next(r['credit'] for r in intake if r['asset']==model['asset'])
        model['replacement_mesh_ids']=[m['id'] for m in scene['meshes'] if m['id'].startswith(prefix)]
        model['position'][2]=replacement_floor(scene,model)
        model['scale_xyz']=model['measured_fit']['scale_xyz'];model['reference_h']=model['measured_fit']['overall_height_m']
        model['neutral_review']=dict(status='pending',source_sha256=model['review_geometry']['source_sha256'],selection=review_selection(model))
        models.append(model)
    (OUT/'chairs-pending.json').write_text(json.dumps(models,separators=(',',':'))+'\n')
    print('Prepared bed with source covers omitted and',len(models),'seat-scaled task chairs',flush=True)
    for r in intake:
        if isinstance(r.get('seat_rule_oct11'),list):print(r['asset'],[(x['fit']['ok'],x['fit'].get('back_height'),x['fit']['reason']) for x in r['seat_rule_oct11']],flush=True)
if __name__=='__main__':prepare()
