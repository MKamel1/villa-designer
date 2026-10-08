"""G4d neutral inputs and independent acceptance; never presentation images."""
import argparse
import json
from pathlib import Path

from archpipe.concept import garden_g4d as G, villa_render as V, villa_lighting as L

OUT=Path('out/garden-g4d')


def save(name,value):
    (OUT/name).write_text(json.dumps(value,indent=2)+'\n')


def delivery_value(value):
    """Compare decoded deliveries; dataclass tuples serialize as JSON lists."""
    return json.loads(json.dumps(value))


def specimens():
    from archpipe.concept.physical_part import PartMeshList
    from archpipe.concept.villa_landscape import _box
    scene=json.loads((OUT/'before-scene.json').read_text())
    meshes,lights,records=G.fixtures(scene['meshes'])
    parts=PartMeshList(collect=False);parts.extend(meshes)
    assemblies=[]
    for name in (G.GRAVEL,G.STONE):
        faces=_box(0,0,0,.4,.4,.035)
        from archpipe.concept.garden_render_review import normal
        assemblies.append(dict(id=name,detail_swatch=True,meshes=[dict(id='swatch-'+name,group='ground',material=name,
            faces=faces,part_kind='stepping-stone',face_materials=['stone-substrate' if normal(f)[2]<-.7 else name for f in faces],
            label='ASSUMED diagnostic swatch only')]))
    plant=next(m for m in scene['meshes'] if m.get('species')=='Rhapis excelsa' and m.get('bed')=='north-accent')
    record=next(r for r in records if r['plant_id']==plant['id'])
    assembly=[plant]+[m for m in parts if m['fixture_id']==record['id']]
    x,y=plant['center'];z=plant['root_z_m']
    assembly.append(dict(id='swatch-under-palm',group='ground',material=G.GRAVEL,
        faces=[[[x-.6,y-.6,z],[x+.6,y-.6,z],[x+.6,y+.6,z],[x-.6,y+.6,z]]],
        part_kind='finish-layer',surface=True,occupied_side=[0,0,1],label='ASSUMED diagnostic gravel patch'))
    assemblies.append(dict(id='rhapis-uplight',meshes=assembly,lights=[l for l in lights if l['id']==record['id']],camera_direction=[2,-3,1.5]))
    save('specimens.json',dict(materials={**scene['materials'],**G.materials()},assemblies=assemblies))
    ies=OUT/'ies/generic/GARDEN-UP.ies';ies.parent.mkdir(parents=True,exist_ok=True)
    ies.write_text(L.generic_ies(G.FLUX_LM,G.BEAM_DEG,'ASSUMED GARDEN-UP'))


def acceptance():
    from garden_g6_preview import receipt_findings
    inputs=json.loads((OUT/'specimens.json').read_text())
    receipt=json.loads((OUT/'previews-reviewed/isolated-preview-evidence.json').read_text())
    preview_findings=receipt_findings(inputs,receipt)
    if preview_findings:raise ValueError('; '.join(preview_findings))
    from archpipe.concept import render_support as S
    from archpipe.concept.garden_render_review import plant_form_findings,downward_ground_findings,garden_camera_findings
    from archpipe.concept.mounting import scene_findings
    path,scene=V.write(OUT/'scene.json')
    result=dict(scene=str(path),plant_form=plant_form_findings(scene['meshes']),
        soffit_material=downward_ground_findings(scene),garden_camera=[f for v in scene['views'] for f in garden_camera_findings(v,scene)],
        unsupported=S.unsupported(scene),blocked_openings=S.blocked_openings(scene),
        mounting=scene_findings(scene),fixture_record=G.fixture_record(scene),material_basis=G.material_basis(scene),
        g4d=G.scene_findings(scene))
    save('acceptance.json',result)
    before=json.loads((OUT/'before-scene.json').read_text())
    after_by={m['id']:m for m in scene['meshes']}
    comparison=dict(existing_geometry_identical=all(m['faces']==after_by[m['id']]['faces'] for m in before['meshes']),
                    props_identical=before['props']==delivery_value(scene['props']),existing_views_identical=all(v==next(a for a in scene['views'] if a['id']==v['id']) for v in before['views']),
                    existing_lights_identical=all(l==next(a for a in scene['lights'] if a['id']==l['id']) for l in before['lights']),
                    changed_finishes=scene['garden_g4d']['changed_finishes'])
    save('fixed-design-comparison.json',comparison)
    glare=G.glare_evidence(scene['garden_g4d']['fixtures'],G.observers(scene))
    save('glare-evidence.json',glare)
    lights_by={l['id']:l for l in scene['lights']}
    palm=next(a for a in inputs['assemblies'] if a['id']=='rhapis-uplight')
    used={m['material'] for a in inputs['assemblies'] for m in a['meshes']} | {n for a in inputs['assemblies'] for m in a['meshes'] for n in m.get('face_materials',[])}
    authority=dict(receipt_findings=preview_findings,
        fixture_preview_faces_identical=all(m['faces']==after_by[m['id']]['faces'] for m in palm['meshes'] if m.get('garden_g4d')),
        fixture_preview_lights_identical=all(l==lights_by[l['id']] for l in palm['lights']),
        preview_materials_identical=all(inputs['materials'][n]==scene['materials'][n] for n in used),
        source_hash_current=scene['provenance']['source_hash']==V.source_provenance()['source_hash'])
    save('preview-authority-comparison.json',authority)
    from villa_render_views import camera_proximity_violations
    from archpipe.concept.garden_render_review import subject_frame_findings,subject_visibility_evidence
    view=next(v for v in scene['views'] if v['id']=='v41-north-garden-evening')
    camera_check=dict(camera_proximity=camera_proximity_violations(view,scene,{}),
        complete_frame=subject_frame_findings(view,scene),garden_camera=garden_camera_findings(view,scene),
        visibility=subject_visibility_evidence(view,scene),glare_pairs=len(glare),
        visible_lens_samples=sum(r['visible_lens_samples'] for r in glare),
        minimum_aperture_margin_m=min(r['minimum_aperture_radius_m']-G.APERTURE_M for r in glare if r['minimum_aperture_radius_m'] is not None))
    save('view-and-glare-check.json',camera_check)
    print(json.dumps(result,indent=2),flush=True)
    if (any(v for k,v in result.items() if k!='scene')
        or not all(comparison[k] for k in ('existing_geometry_identical','props_identical','existing_views_identical','existing_lights_identical'))
        or not all(v for k,v in authority.items() if k!='receipt_findings')
        or any(camera_check[k] for k in ('camera_proximity','complete_frame','garden_camera'))):
        raise SystemExit(1)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--specimens',action='store_true')
    args=parser.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    specimens() if args.specimens else acceptance()
