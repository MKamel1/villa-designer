"""Neutral diagnostics of the actual D1 fallback beds and measured rejection.

Run in Blender with --scene out/beds/scene.json --output out/beds/previews.
The existing room cameras, materials, mattress geometry and cloth settings
are preserved. Every isolated preview includes a 1.8 metre scale figure.
No design lights are built; material emission is disabled. These are
diagnostic images, never presentation images or product approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def require_neutral_cloth(receipts):
    """Diagnostic raw-model images may exist, but refusal cannot exit zero."""
    failures=[r['bed'] for r in receipts if isinstance(r.get('cloth_report'),dict)
              and r['cloth_report'].get('passed') is False]
    if failures:raise ValueError('neutral cloth preview refused: '+', '.join(failures))


def render(args):
    import bpy
    from mathutils import Vector
    sys.path.insert(0, str(ROOT/'src'))
    sys.path.insert(0, str(ROOT/'scripts'))
    from archpipe.blender import villa_scene as builder
    from garden_g6_preview import disable_material_emission, canonical_hash

    data=json.loads(args.scene.read_text())
    if args.scaled_models:
        scaled=json.loads(args.scaled_models.read_text())
        data['models']=[m for m in data['models'] if m.get('replaces') not in {s['replaces'] for s in scaled}]+scaled
    args.output.mkdir(parents=True,exist_ok=True)
    requests=[('pb-bed','parents-bed','v22-parents-day'),
              ('kb-bed','kids-b','v13-kids-b'),('ka-bunk','kids-a','v06-kids-room'),
              ('library-daybed','bar-alcove','v24-bar-alcove')]
    receipts=[]

    def setup(meshes):
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        warnings=[]
        names={m['material'] for m in meshes} | {n for m in meshes for n in m.get('face_materials',[])}
        materials={n:builder.add_material(n,data['materials'][n],str(args.library),warnings) for n in names}
        builder.configure_glass(materials,{n:data['materials'][n] for n in names})
        objects=builder.build_meshes(meshes,materials,data['materials'],warnings)
        scene=bpy.context.scene
        builder.configure_cycles(False)
        scene.cycles.samples=args.samples
        scene.cycles.use_denoising=True
        scene.render.threads_mode='FIXED'
        scene.render.threads=8
        scene.render.resolution_x=960
        scene.render.resolution_y=640
        scene.render.resolution_percentage=100
        scene.world.use_nodes=True
        scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.8,.8,.8,1)
        scene.world.node_tree.nodes['Background'].inputs[1].default_value=.8
        scene.view_settings.view_transform='AgX'
        scene.view_settings.exposure=0
        scene.render.image_settings.file_format='PNG'
        return scene,objects,materials,warnings

    def softbox(position,target,size=3,power=500):
        light=bpy.data.lights.new('recorded neutral diagnostic softbox','AREA')
        light.energy,light.size,light.color=power,size,(1,1,1)
        obj=bpy.data.objects.new(light.name,light)
        bpy.context.collection.objects.link(obj)
        obj.location=position
        obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
        return obj

    def figure(x,y,z):
        objects=[]
        # Head's top is exactly 1.8 m above feet. Smooth grey reference only.
        for location,scale in (((x,y,z+1.03),(.14,.09,.40)),
                               ((x-.08,y,z+.32),(.045,.055,.32)),
                               ((x+.08,y,z+.32),(.045,.055,.32)),
                               ((x-.20,y,z+1.05),(.045,.055,.30)),
                               ((x+.20,y,z+1.05),(.045,.055,.30)),
                               ((x,y,z+1.50),(.075,.075,.10)),
                               ((x-.15,y,z+1.28),(.08,.08,.09)),
                               ((x+.15,y,z+1.28),(.08,.08,.09)),
                               ((x,y,z+1.68),(.12,.12,.12))):
            bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,location=location)
            obj=bpy.context.object
            obj.scale=scale
            objects.append(obj)
        return objects

    def isolated(scene,objects,path,direction=(1.8,3,1.7),include_figure=True):
        bpy.context.view_layer.update()
        points=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
        from archpipe.beds import preview_datums, preview_clip_range, preview_neutral_light
        datums=preview_datums([list(p) for p in points])
        low,high=datums['bounds_m']
        cx,cy=(low[0]+high[0])/2,(low[1]+high[1])/2
        span=max(high[0]-low[0],high[1]-low[1],high[2]-low[2])
        aid=figure(low[0]-.45,high[1]-.3,low[2]) if include_figure else []
        bpy.ops.mesh.primitive_plane_add(size=max(20,span*3),location=(cx,cy,datums['floor_z_m']))
        camera_data=bpy.data.cameras.new('neutral isolated bed camera')
        camera_data.type='ORTHO'
        camera=bpy.data.objects.new(camera_data.name,camera_data)
        bpy.context.collection.objects.link(camera)
        target=Vector((cx,cy,low[2]+.85))
        camera.location=target+Vector(direction)*max(1,span)
        camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
        bpy.context.view_layer.update()
        right=camera.rotation_euler.to_matrix()@Vector((1,0,0))
        up=camera.rotation_euler.to_matrix()@Vector((0,1,0))
        points+=[o.matrix_world@Vector(c) for o in aid for c in o.bound_box]
        light_record=preview_neutral_light([list(p) for p in points])
        lamp=softbox(light_record['position_m'],light_record['target_m'],
                     light_record['size_m'],light_record['power_watts'])
        projected=[(p.dot(right),p.dot(up)) for p in points]
        xmin,xmax=min(p[0] for p in projected),max(p[0] for p in projected)
        ymin,ymax=min(p[1] for p in projected),max(p[1] for p in projected)
        camera.location+=right*((xmin+xmax)/2-camera.location.dot(right))
        camera.location+=up*((ymin+ymax)/2-camera.location.dot(up))
        clips=preview_clip_range([list(p) for p in points],list(camera.location),
                                 list(camera.location+camera.rotation_euler.to_matrix()@Vector((0,0,-1))))
        camera_data.clip_start=clips['clip_start_m']
        camera_data.clip_end=clips['clip_end_m']
        scene.render.resolution_y=720
        camera_data.ortho_scale=max(xmax-xmin,(ymax-ymin)*4/3)/.88
        scene.camera=camera
        scene.render.filepath=str(path)
        bpy.ops.render.render(write_still=True)
        return dict(image=str(path),scale_reference_height_m=1.8 if include_figure else None,
                    clipping=clips,scope='figure and bed' if include_figure else 'asset close-up; unchanged source size',
                    floor_z_m=datums['floor_z_m'],figure_foot_z_m=datums['figure_foot_z_m'],camera_location=list(camera.location),
                    staging_gap_m=datums['staging_gap_m'],
                    diagnostic_light=light_record,
                    ortho_scale_m=camera_data.ortho_scale,geometry_bounds_m=[low,high])

    if args.candidates:
        for candidate in json.loads(args.candidates.read_text()):
            path=Path(candidate['model']).resolve()
            scene,_,_,warnings=setup([])
            bpy.ops.import_scene.gltf(filepath=str(path))
            objects=[o for o in bpy.data.objects if o.type=='MESH']
            # Apply only one scale to the entire imported hierarchy.
            anchor=bpy.data.objects.new('candidate uniform-scale anchor',None)
            bpy.context.collection.objects.link(anchor)
            for root in [o for o in bpy.data.objects if o!=anchor and o.parent is None]:
                root.parent=anchor
            anchor.scale=(candidate['scale'],)*3
            bpy.context.view_layer.update()
            actual=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
            measured=[[min(p[i] for p in actual) for i in range(3)],
                      [max(p[i] for p in actual) for i in range(3)]]
            disable_material_emission({m.name:m for m in bpy.data.materials})
            images=[]
            for side,direction in [('plus-y',(1.8,3,1.7)),('minus-y',(-1.8,-3,1.7))]:
                before=set(bpy.data.objects)
                images.append(isolated(scene,objects,args.output/(candidate['id']+'-'+side+'.png'),direction))
                for o in set(bpy.data.objects)-before:
                    bpy.data.objects.remove(o,do_unlink=True)
                if candidate.get('close_up'):
                    before=set(bpy.data.objects)
                    images.append(isolated(scene,objects,args.output/(candidate['id']+'-'+side+'-close.png'),direction,False))
                    for o in set(bpy.data.objects)-before:
                        bpy.data.objects.remove(o,do_unlink=True)
            receipts.append(dict(candidate=candidate,images=images,actual_vertex_bounds_m=measured,
                source_gltf_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                source_materials_sha256=canonical_hash(json.loads(path.read_text()).get('materials',[])),
                emission_disabled=True,diagnostic_light='per-image measured-span staging; see images',review_status='pending'))
            (args.output/'evidence.json').write_text(json.dumps(receipts,indent=2)+'\n')
        return

    for mark,room,view_id in requests:
        if args.beds and mark not in args.beds:
            continue
        prefix='furn-'+mark+'-'
        bed_meshes=[m for m in data['meshes'] if m['id'].startswith(prefix)]
        meshes=[m for m in data['meshes'] if m['group'] in ('shell','context') or m.get('room')==room]
        scene,objects,materials,warnings=setup(meshes)
        # Other accepted room furniture imports retain their real textures.
        models=builder.import_models([m for m in data['models'] if m.get('room')==room],str(args.library),
                                     neutral_diagnostic=bool(args.scaled_models))
        cloth=[c for c in data['cloth'] if c['id'].startswith(('duvet-'+mark,'throw-'+mark))]
        for name in {c['material'] for c in cloth}-materials.keys():
            materials[name]=builder.add_material(name,data['materials'][name],str(args.library),warnings)
        try:
            cloth_report=builder.drape_cloth(cloth,materials,models)
            cloth_status='passed'
        except ValueError as error:
            if not args.scaled_models:raise
            cloth_report=dict(passed=False,refused=str(error))
            cloth_status='refused; raw imported bedding shown; candidate cannot activate'
            for obj in list(bpy.data.objects):
                if obj.name.startswith(('cloth-duvet-'+mark,'cloth-throw-'+mark)):
                    bpy.data.objects.remove(obj,do_unlink=True)
        disable_material_emission({m.name:m for m in bpy.data.materials})
        view=next(v for v in data['views'] if v['id']==view_id)
        for mid in view.get('hide_meshes',[]):
            if mid in objects:objects[mid].hide_render=True
        camera,_=builder.configure_camera(view)
        scene.camera=camera
        bed_points=[p for m in bed_meshes for f in m['faces'] for p in f]
        center=[(min(p[i] for p in bed_points)+max(p[i] for p in bed_points))/2 for i in range(3)]
        # One recorded neutral fill makes windowless context readable.
        fill=softbox((center[0],center[1],center[2]+1.5),center,2)
        context=args.output/(mark+'-room-neutral.png')
        scene.render.filepath=str(context)
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(camera,do_unlink=True)
        bpy.data.objects.remove(fill,do_unlink=True)
        replacement=next((m for m in models if m.get('replaces')==prefix and m.get('status')=='imported'),None)
        keep=(replacement['objects'] if replacement else [objects[m['id']] for m in bed_meshes])
        keep += [o for o in bpy.data.objects if o.name.startswith(('cloth-duvet-'+mark,'cloth-throw-'+mark))]
        for obj in bpy.data.objects:
            obj.hide_render=obj not in keep
        iso=isolated(scene,keep,args.output/(mark+'-isolated-neutral.png'))
        receipts.append(dict(bed=mark,status='scaled diagnostic candidate; pending review' if replacement else 'procedural fallback; imported replacement blocked',
            isolated=iso,context_image=str(context),existing_view=view_id,camera=view['camera'],
            source_geometry_sha256=canonical_hash(bed_meshes),
            source_materials_sha256=canonical_hash({n:data['materials'][n] for n in {m['material'] for m in bed_meshes}}),
            source_cloth_sha256=canonical_hash(cloth),cloth_report=cloth_report,cloth_status=cloth_status,
            scaled_model_selection=(replacement.get('neutral_review',{}).get('selection') if replacement else None),
            source_sha256=(replacement['review_geometry']['source_sha256'] if replacement else None),
            actual_imported_bounds_m=(replacement['bounds'] if replacement else None),
            emission_disabled=True,neutral_softbox_watts=500,warnings=warnings,
            context_scope='Actual architecture and room furniture; diagnostic props/curtains omitted',
            review_status='pending'))
        (args.output/'evidence.json').write_text(json.dumps(receipts,indent=2)+'\n')

    if args.rejected_model:
        path=args.rejected_model.resolve()
        scene,_,_,warnings=setup([])
        bpy.ops.import_scene.gltf(filepath=str(path))
        objects=[o for o in bpy.data.objects if o.type=='MESH']
        disable_material_emission({m.name:m for m in bpy.data.materials})
        iso=isolated(scene,objects,args.output/'chelsea-rejected-native-isolated-neutral.png')
        receipts.append(dict(bed='chelsea-rejected',status='REJECTED; native size, no distortion',
                             isolated=iso,source_gltf_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                             warnings=warnings,review_status='pending'))
        (args.output/'evidence.json').write_text(json.dumps(receipts,indent=2)+'\n')

    require_neutral_cloth(receipts)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=ROOT/'out/beds/previews')
    parser.add_argument('--library',type=Path,default=Path('/home/omar/archpipe/assets/library'))
    parser.add_argument('--samples',type=int,default=32)
    parser.add_argument('--beds',nargs='+')
    parser.add_argument('--rejected-model',type=Path)
    parser.add_argument('--candidates',type=Path,help='Measured candidate list for isolated review only')
    parser.add_argument('--scaled-models',type=Path,help='Pending measured scaled beds for neutral diagnostics only')
    parser.add_argument('--graphics-lock',type=Path,default=Path('/home/omar/archpipe/locks/graphics.lock'))
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:])
    import fcntl
    with args.graphics_lock.open('rb') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
        render(args)


if __name__=='__main__':
    main()
