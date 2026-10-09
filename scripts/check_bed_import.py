"""Blender capability proof on the rejected Scandi asset, at its own envelope.

This is a mechanical test, never a D1 selection. Intake registration is mocked
only in this test harness: the actual candidate remains rejected in the manifest.
No source geometry, material, existing room camera or library file is changed.
"""
import fcntl
import gzip
import json
from pathlib import Path
import sys
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'scripts'))

def require_complete_proof(result):
    """Refuse partial success even when geometry/fallback probes passed."""
    if not result['cloth']['passed']:
        raise ValueError('mechanical cloth proof failed; see importer-proof.json: '+result['cloth']['refused'])

def run():
    import bpy
    from archpipe.blender import villa_scene as builder
    from archpipe.beds import model_review_meshes
    out=ROOT/'out/beds/round3'
    out.mkdir(parents=True,exist_ok=True)
    geometry=json.loads(gzip.decompress((ROOT/'out/beds/round2/geometry/sf_bed_scandi_bare.json.gz').read_bytes()))
    spec=dict(id='mechanical-scandi',asset='sf_bed_scandi_bare',role='bed',scale=1.,
        native_bounds=dict(min=[-2.164110,.017163,-1.304135],max=[2.283993,1.317586,1.225815]),
        length_axis='X',planned_mattress_m=[2.4124317169189453,4.241483449935913],
        footprint_w=4.241483449935913,footprint_d=2.4124317169189453,reference_h=1.300423,
        contents_review=dict(status='bed-only',basis='actual seven bed meshes inspected',extras=[]),
        position=[0,0,0],rotation_deg=[0,0,0],layout_rotation_deg=-90,front_axis='+X',
        replaces='furn-mechanical-scandi-',review_geometry=geometry,
        orientation_evidence=dict(front_axis='+X',basis='actual pillow at negative X'),
        neutral_review=dict(status='accepted',scope='retained source reviewed in round 2; mechanical harness only, not design approval'),
        mattress_bindings=dict(lower=dict(parts=['Object_14'],head_at_max=False)))
    library='/home/omar/archpipe/assets/library'
    spec['neutral_review'].update(source_sha256=geometry['source_sha256'],
                                orientation_evidence=spec['orientation_evidence'],
        selection=dict(omitted_meshes=[],mattress_bindings=spec['mattress_bindings'],unit_evidence=None))
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.mesh.primitive_cube_add(size=1)
    fallback=bpy.context.object;fallback.name=spec['replaces']+'mattress'
    with patch('archpipe.asset_intake.require_registered_asset'):
        imported=builder.import_models([spec],library)
    assert fallback.hide_render and fallback.get('replaced_by_model')==spec['id']
    actual=[list(o.matrix_world@v.co) for o in imported[0]['objects'] for v in o.data.vertices]
    review=[p for m in model_review_meshes([spec]) for f in m['faces'] for p in f]
    errors=[abs(min(p[i] for p in actual)-min(p[i] for p in review)) for i in range(3)]+[abs(max(p[i] for p in actual)-max(p[i] for p in review)) for i in range(3)]
    assert max(errors)<1e-5
    mat=bpy.data.materials.new('mechanical bedding');mat.diffuse_color=(.82,.81,.78,1)
    cloth=dict(id='duvet-mechanical-scandi',material='test',length_axis='x',
        colliders=[spec['replaces']],cut=dict(head_to_pin_m=.55,foot_overhang_m=.26,side_overhang_m=.26),
        frames=60,mass=.4,bending=.6,loft=.018,thickness=.05)
    try:
        records=builder.drape_cloth([cloth],{'test':mat},imported)
        cloth_result=dict(passed=True,records=records)
    except ValueError as error:
        cloth_result=dict(passed=False,refused=str(error))
    if cloth_result['passed']:
        # Neutral capability preview, prior to any deliberate fault injection.
        from mathutils import Vector
        from garden_g6_preview import disable_material_emission
        disable_material_emission({m.name:m for m in bpy.data.materials})
        builder.configure_cycles(False)
        scene=bpy.context.scene
        scene.cycles.samples=16
        scene.render.threads_mode='FIXED';scene.render.threads=8
        scene.render.resolution_x=960;scene.render.resolution_y=720;scene.render.resolution_percentage=100
        scene.world.use_nodes=True
        scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.8,.8,.8,1)
        scene.world.node_tree.nodes['Background'].inputs[1].default_value=.8
        scene.view_settings.view_transform='AgX';scene.view_settings.exposure=0
        bpy.ops.mesh.primitive_plane_add(size=20,location=(0,0,-.005))
        # Grey height reference: feet at zero; head top exactly 1.8 metres.
        bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=.12,depth=1.56,location=(-3,0,.78))
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=.12,location=(-3,0,1.68))
        light=bpy.data.lights.new('neutral diagnostic softbox','AREA');light.energy=500;light.size=3
        lamp=bpy.data.objects.new(light.name,light);bpy.context.collection.objects.link(lamp);lamp.location=(1,-2,4)
        lamp.rotation_euler=(Vector((0,0,.6))-lamp.location).to_track_quat('-Z','Y').to_euler()
        cam=bpy.data.cameras.new('mechanical cloth camera');cam.type='ORTHO';cam.ortho_scale=7.5
        camera=bpy.data.objects.new(cam.name,cam);bpy.context.collection.objects.link(camera);camera.location=(3,-4,3)
        camera.rotation_euler=(Vector((-.3,0,.8))-camera.location).to_track_quat('-Z','Y').to_euler()
        scene.camera=camera;scene.render.image_settings.file_format='PNG'
        scene.render.filepath=str(out/'mechanical-scandi-cloth-neutral.png')
        bpy.ops.render.render(write_still=True)
    # Explicit crossing, contained-sheet, clean-sheet and moved sibling probes
    # run against the actual imported mattress, including evaluated geometry.
    mattress=next(o for o in imported[0]['objects'] if o.get('source_part')=='Object_14')
    pts=[mattress.matrix_world@v.co for v in mattress.data.vertices]
    xmin,xmax=min(p.x for p in pts),max(p.x for p in pts)
    ymin,ymax=min(p.y for p in pts),max(p.y for p in pts)
    zmin,zmax=min(p.z for p in pts),max(p.z for p in pts)
    cx,cy=(xmin+xmax)/2,(ymin+ymax)/2
    probes={}
    for name,z in [('clean',zmax+.2),('contained',(zmin+zmax)/2)]:
        sheet=builder.photoreal._grid(name,.1,.1,2,2,(cx,cy),z)
        probes[name]=builder.cloth_model_clearance(sheet,[mattress])
        bpy.data.objects.remove(sheet,do_unlink=True)
    bpy.ops.mesh.primitive_plane_add(size=.5,location=(cx,cy,zmax))
    crossing=bpy.context.object;crossing.rotation_euler[1]=1.5707963267948966
    bpy.context.view_layer.update()
    probes['crossing']=builder.cloth_model_clearance(crossing,[mattress])
    world= mattress.matrix_world.copy()
    world.translation.x+=5
    mattress.matrix_world=world
    crossing.location.x+=5
    bpy.context.view_layer.update()
    probes['translated_crossing']=builder.cloth_model_clearance(crossing,[mattress])
    print('probe evidence',json.dumps(probes))
    print('cloth evidence',json.dumps(cloth_result))
    assert probes['clean']['intersections']==probes['clean']['inside_vertices']==0
    assert probes['contained']['inside_vertices']>0
    assert probes['crossing']['intersections']>0 and probes['translated_crossing']['intersections']>0
    # The absent-file branch runs without bypassing registration or geometry checks.
    missing=dict(spec,asset='deliberately-absent-model')
    missing_result=builder.import_models([missing],library)
    assert missing_result[0]['status']=='procedural-bed-fallback'
    assert not fallback.hide_render and fallback.get('asset_status')=='procedural-bed-fallback'
    result=dict(scope='mechanical capability only; Scandi remains rejected for D1',
        model_bounds=imported[0]['bounds'],portable_vs_blender_max_error_m=max(errors),
        cloth=cloth_result,clearance_probes=probes,missing_file_fallback='passed',
        source_sha256=geometry['source_sha256'])
    (out/'importer-proof.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('scope','portable_vs_blender_max_error_m','cloth','missing_file_fallback')}))
    require_complete_proof(result)

if __name__=='__main__':
    with Path('/home/omar/archpipe/locks/graphics.lock').open('rb') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
        run()
