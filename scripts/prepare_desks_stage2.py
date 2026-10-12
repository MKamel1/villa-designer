"""Measure downloaded candidates and propose whole-item fits; no activation."""
from copy import deepcopy
import gzip,json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from archpipe.furniture_fit import native_box, fit_factors, model_fit, review_selection
from archpipe.furniture_orientation import model_yaw
from archpipe.asset_intake import measure_gltf_bounds
from inventory_desks import inventory
from prepare_beds_round5 import semantic_cut

LIBRARY=Path('/home/omar/archpipe/assets/library/props')
OUTPUT=ROOT/'out/desks/stage2'
# Complete desktop slabs and complete seat component are identified from
# actual part bounds, connected components, and both neutral source views.
DESKTOPS={'sf_desk_01f6ba08':'Object_36_', 'sf_desk_1710e30f':'Object_1_',
    'sf_desk_2edb7c9c':'Object_1_', 'sf_desk_6dfafa3b':'Object_17_', 'sf_desk_6e47547c':'Object_6_'}
CHOICES={'study-desk':'sf_desk_1710e30f','study-adult-desk':'sf_desk_2edb7c9c',
 'cinema-desk':'sf_desk_6e47547c','ka-desk-1':'sf_desk_6e47547c','ka-desk-2':'sf_desk_6e47547c',
 'kb-desk':'sf_desk_6e47547c','pb-vanity':'sf_desk_1710e30f'}

def main():
    OUTPUT.mkdir(parents=True,exist_ok=True);rows=inventory()['items'];models=[];intake=[];manifest=[]
    scene=json.loads((ROOT/'out/beds/round4/scene.json').read_text())
    geometries={}
    for folder in sorted(LIBRARY.glob('sf_desk_*')):
        provenance=json.loads((folder/'provenance.json').read_text())
        if provenance['licence']!='CC Attribution':raise ValueError('only downloaded CC Attribution assets admitted')
        geometry=json.loads(gzip.decompress((OUTPUT/'geometry'/(folder.name+'.json.gz')).read_bytes()))
        geometry['schema']='furniture-model-geometry/1';geometries[folder.name]=geometry
        bounds=native_box(geometry['meshes']);size=np.subtract(bounds['max'],bounds['min']).tolist()
        record=dict(asset=folder.name,name=provenance['name'],bounds_native_m=bounds,extent_native_m=size,
            triangles=sum(len(m['faces'])-0 for m in geometry['meshes']),source_sha256=geometry['source_sha256'],
            credit=(folder/'license.txt').read_text(),style_review='both neutral source views inspected',fits={})
        # Plan screens for every authored item are independent of semantic
        # height eligibility. No overall model top substitutes for seat height.
        is_desk=folder.name in DESKTOPS or folder.name in ('sf_desk_4548bc41','sf_desk_c5105496')
        front='-Z' if is_desk else '+Z'
        for item in rows:
            if (item['type']=='desk')!=is_desk:continue
            axis='X' if folder.name=='sf_desk_c5105496' else 'Z'
            fit=fit_factors(bounds,*item['planned_footprint_m'],front,length_axis=axis,height_bounds=bounds,
                height_m=item['heights_m'].get('desktop',item['heights_m'].get('back')),
                height_source='plan-only screen; overall top is not a semantic seat/desktop acceptance')
            record['fits'][item['id']]=dict(plan_ok=fit['ok'],sx=fit['sx'],sy=fit['sy'],plan_distortion=fit['plan_distortion'],reason=fit['reason'])
        if folder.name in DESKTOPS:
            desktop=next(m['name'] for m in geometry['meshes'] if m['name'].startswith(DESKTOPS[folder.name]))
            record['contents_review']=dict(status='item-only',basis='all imported meshes and both neutral views: desktop, drawer hardware and legs only',extras=[],fused_extras=[])
            record['height_parts']=[desktop]
        elif folder.name=='sf_desk_4548bc41':record['refusal']='desk plus fused storage/hutch; no complete item-only desktop isolated, source overall height 1.484 m'
        elif folder.name=='sf_desk_c5105496':record['refusal']='source plan factors below 0.5; glTF metres retained, no inferred centimetre conversion'
        elif folder.name in ('sf_desk_792bb7e8','sf_desk_aee7ef03'):
            # A separable extra must not inflate an item's footprint. Keep
            # the original geometry immutable and measure complete siblings
            # independently; a plan pass still cannot infer a seat datum.
            groups=([('chair',[m for m in geometry['meshes'] if m['name']!='defaultMaterial.022'],['defaultMaterial.022'])]
                if folder.name=='sf_desk_792bb7e8' else
                [(m['name'],[m],[other['name'] for other in geometry['meshes'] if other['name']!=m['name']]) for m in geometry['meshes']])
            record['item_only_rescreens']=[]
            for name,meshes,omitted in groups:
                item_bounds=native_box(meshes)
                item_fit=fit_factors(item_bounds,.44,.45,'+Z',length_axis='Z',height_bounds=item_bounds,
                    height_m=.85,height_source='plan-only; complete seat datum remains unresolved')
                record['item_only_rescreens'].append(dict(item=name,retained_meshes=[m['name'] for m in meshes],
                    omitted_meshes=omitted,bounds_native_m=item_bounds,
                    extent_native_m=np.subtract(item_bounds['max'],item_bounds['min']).tolist(),
                    plan_ok=item_fit['ok'],sx=item_fit['sx'],sy=item_fit['sy'],
                    plan_distortion=item_fit['plan_distortion'],plan_reason=item_fit['reason'],
                    height_status='refused: independently verified complete seat datum unavailable; back alone cannot approve'))
            record['refusal']='complete chair-only plan re-screen recorded; complete seat and back under one vertical transform remain unproved'
        else:record['refusal']='chair seat and authored back must both fit one vertical transform; no acceptance from footprint alone'
        intake.append(record)
        if folder.name in DESKTOPS:
            accessor=measure_gltf_bounds(folder/'model.gltf')
            manifest.append(dict(id=folder.name,role='desk',source_url=provenance['source'],url=provenance['source'],author=provenance['author'],licence=provenance['licence'],
                credit=record['credit'],bounds_m=accessor,measured_bounds_m=bounds,up_axis='+Y',front_axis=front,
                front_axis_source='drawer fronts on converted minimum Y; native +Z faces user, hence +Z; corrected below',
                units_normalised=dict(scale_factor=1.,reason='glTF metre convention; whole-item fit recorded separately'),
                expected_size_range=dict(min_m=[v*.5 for v in size],max_m=[v*2 for v in size],source='client furniture fit factors 0.5–2.0; measured item footprint and 15% rule enforced separately',basis='client-decision'),
                contents=dict(item_only=True),preview_image='props/'+folder.name+'/preview.png',status='measured-neutral-source; placement gated separately'))
    # All classe drawer fronts are converted minimum Y, native positive Z.
    # Desk front points toward the seated user: native +Z, not -Z.
    for entry in manifest:
        entry.update(front_axis='+Z',front_axis_source='actual drawer fronts at converted minimum Y (native positive Z), read from complete source parts and both neutral views')
    for item in rows:
        if item['id'] not in CHOICES:continue
        asset=CHOICES[item['id']];geometry=geometries[asset];record=next(r for r in intake if r['asset']==asset)
        front='+Z';w,d=item['planned_footprint_m'];rot=item['rotation_deg']
        model=dict(id='model-'+item['id'],label=item['id'],role='desk',asset=asset,room=item['room'],level=item['level'],
            replaces='furn-'+item['id']+'-',position=item['centre_m']+[.002 if item['level']=='G' else 3.252],
            rotation_deg=[0,0,model_yaw(rot,front)],layout_rotation_deg=rot,front_axis=front,scale=1.,
            footprint_w=d if rot in (-90,90) else w,footprint_d=w if rot in (-90,90) else d,
            unit_evidence=dict(unit='m',source='glTF 2.0 coordinate units; no source unit declaration overriding metres'),
            orientation_evidence=dict(front_axis=front,basis=manifest[0]['front_axis_source']),
            review_geometry=geometry,contents_review=record['contents_review'],omitted_meshes=[],
            furniture_fitting=dict(decision_date='2026-10-09',footprint_m=[w,d],height_parts=record['height_parts'],
                height_m=item['heights_m']['desktop'],height_basis='design',height_source=item['height_source']),
            credit=record['credit'],asset_kind='appearance',decimate_ratio=1.)
        model['replacement_mesh_ids']=[m['id'] for m in scene['meshes']
            if m['id'].startswith('furn-'+item['id']+'-') and not m['id'].startswith('furn-'+item['id']+'-chair-')]
        from archpipe.concept.revit_spec import LEVELS_Z
        model['position'][2]=LEVELS_Z[item['level']]+.002
        fit=model_fit(model);model.update(scale_xyz=fit['scale_xyz'],reference_h=fit['overall_height_m'],measured_fit=fit)
        model['neutral_review']=dict(status='pending',selection=review_selection(model),source_sha256=geometry['source_sha256'])
        record['fits'][item['id']]['whole_item']=fit
        if not fit['ok']:raise ValueError('chosen desk refused: '+str(fit))
        models.append(model)
    # Flannigan's complete connected seat is source component 0 (3,769
    # vertices); retain every other chair face as well. One vertical factor
    # from that seat gives 0.81129 m back, failing the authored 0.850 m.
    geometry=geometries['sf_desk_531bff2f']
    temporary=deepcopy(geometry);temporary['schema']='bed-model-geometry/1'
    cut,selections,bindings=semantic_cut(temporary,{'lower':dict(mesh='Flanninga_Chair_0',component_index=0,expected_vertices=3769)})
    chair=dict(id='flannigan-measured',role='task_chair',front_axis='+Z',review_geometry=cut,
        contents_review=dict(status='item-only',basis='one complete chair, neutral views and connected-seat readback',extras=[],fused_extras=[]),
        furniture_fitting=dict(decision_date='2026-10-09',footprint_m=[.44,.45],height_parts=bindings['lower']['parts'],
            height_m=.46,height_basis='design',height_source='ASSUMED villa_furnish3d._chair seat',
            height_constraints=dict(back=dict(parts=['Flanninga_Chair_0'],height_m=.85,height_basis='design',height_source='ASSUMED villa_furnish3d._chair back'))))
    cf=model_fit(chair)
    next(r for r in intake if r['asset']=='sf_desk_531bff2f').update(measured_seat_fit=cf,refusal=cf['reason'])
    (OUTPUT/'intake.json').write_text(json.dumps(intake,indent=2)+'\n')
    (OUTPUT/'models-pending.json').write_text(json.dumps(models,separators=(',',':'))+'\n')
    (OUTPUT/'manifest-new.json').write_text(json.dumps(manifest,indent=2)+'\n')
    for m in models:print(m['label'],m['measured_fit']['sx'],m['measured_fit']['sy'],m['measured_fit']['sz'])
    print('Flannigan',cf['reason'])
if __name__=='__main__':main()
