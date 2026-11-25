"""Walking-camera execution using the production villa assembly and QA context.

This entry point runs inside pinned Blender, through scripts/flythrough.py.
All positions are metres; camera yaw is degrees anticlockwise from positive x.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from archpipe.blender import villa_scene as V
from archpipe.safe_io import save_bytes
from archpipe.flythrough import is_villa_path, admit_path, frame_views, require_renderable, digest, clip_source_group, policy, static_material_eligible, static_coverage, retain_cache_materials


def save(path, value):
    save_bytes(path,(json.dumps(value,indent=2)+'\n').encode())


def evaluated_path_meshes(path):
    """Read actual runtime faces near the whole path; bounds only prune."""
    positions=np.array([f['camera']['position'] for f in path['frames']])
    low=positions.min(0)-.31;high=positions.max(0)+.31
    if is_villa_path(path):
        # whole villa: keep only faces inside 0.5 m cells around the walked envelope (floor to 2.2 m above it)
        low[2]=min(f['ground_m'] for f in path['frames'])-.05;high[2]=max(f['ground_m'] for f in path['frames'])+2.3
        occupied=set()
        for f in path['frames']:
            x,y,_=f['camera']['position'];g=f['ground_m']
            for i in range(int((x-.6)//.5),int((x+.6)//.5)+1):
                for j in range(int((y-.6)//.5),int((y+.6)//.5)+1):
                    for k in range(int((g-.1)//.5),int((g+2.3)//.5)+1):occupied.add((i,j,k))
        def near(pts):
            lo=np.floor(pts.min(0)/.5).astype(int);hi=np.floor(pts.max(0)/.5).astype(int)
            return any((i,j,k) in occupied for i in range(lo[0],hi[0]+1) for j in range(lo[1],hi[1]+1) for k in range(lo[2],hi[2]+1))
    else:
        low[2],high[2]=-2.95,-1.2
        near=lambda pts:True
    dependencies=bpy.context.evaluated_depsgraph_get()
    result=[]
    for obj in bpy.context.scene.objects:
        if obj.type!='MESH' or obj.hide_render:continue
        evaluated=obj.evaluated_get(dependencies)
        bounds=np.array([list(evaluated.matrix_world@Vector(p)) for p in evaluated.bound_box])
        if np.any(bounds.min(0)>high) or np.any(bounds.max(0)<low):continue
        mesh=evaluated.to_mesh()
        try:
            coordinates=np.array([list(evaluated.matrix_world@v.co) for v in mesh.vertices])
            faces=[]
            for polygon in mesh.polygons:
                pts=coordinates[list(polygon.vertices)]
                if np.all(pts.min(0)<=high) and np.all(pts.max(0)>=low) and near(pts):faces.append(pts.tolist())
            if faces:result.append(dict(id=obj.name,faces=faces))
        finally:evaluated.to_mesh_clear()
    return result


def prepare(scene_data,args,context):
    path=json.loads(Path(args.path).read_text())
    # Day-state curtains use the identical still-view visibility state.
    views=frame_views(path,scene_data)
    context['setup_view'](views[0])
    bpy.context.view_layer.update()
    measured=evaluated_path_meshes(path)
    save(Path(args.out)/'evaluated-path-meshes.json',measured)
    # Keep exact assembly object identities and physical QA receipts across stages.
    keys=('cloth_report','curtain_report','receipt','render_device','warnings','emissive_sources',
          'full_power')
    metadata={k:context[k] for k in keys}
    metadata.update(switched_emitters={k:context['objects'][k].data.materials[0].name for k in context['switched_emitters']},
                    objects={k:v.name for k,v in context['objects'].items()},
                    lights={k:v.name for k,v in context['lights'].items()},
                    materials={k:v.name for k,v in context['materials'].items()},
                    path_sha256=path['sha256'])
    retain_cache_materials(context['materials'])
    save(Path(args.out)/'assembly.json',metadata)
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(args.out)/'scene.blend'))
    print('WALKTHROUGH assembly measured; host-Python admission required before rendering',flush=True)


def load_context(args):
    assembly=Path(args.root)/'assembly'
    path=json.loads((Path(args.root)/'path.json').read_text())
    from archpipe.blender.element_ids import without_ids
    scene=without_ids(json.loads((Path(args.root)/'scene.json').read_text()))
    metadata=json.loads((assembly/'assembly.json').read_text())
    guards=json.loads((assembly/'guards.json').read_text())
    binding=json.loads((assembly/'admission.json').read_text())
    require_renderable(guards)
    if (binding['guards_sha256']!=digest(guards) or metadata['path_sha256']!=path['sha256']
            or binding['assembly_sha256']!=hashlib.sha256((assembly/'assembly.json').read_bytes()).hexdigest()
            or binding['blend_sha256']!=hashlib.sha256((assembly/'scene.blend').read_bytes()).hexdigest()):
        raise ValueError('Measured assembly/path binding changed')
    bpy.ops.wm.open_mainfile(filepath=str(assembly/'scene.blend'))
    metadata['mesh_by_id']={m['id']:m for m in scene['meshes']}
    metadata['switched_emitters']={k:bpy.data.materials[v].node_tree.nodes['Villa Emission'] for k,v in metadata['switched_emitters'].items()}
    metadata['objects']={k:bpy.data.objects[v] for k,v in metadata['objects'].items()}
    metadata['lights']={k:bpy.data.objects[v] for k,v in metadata['lights'].items()}
    metadata['materials']={k:bpy.data.materials[v] for k,v in metadata['materials'].items()}
    replayed=V.evaluated_scene_receipt(scene,{r['id']:metadata['objects'][r['id']] for r in metadata['curtain_report']})
    if replayed['evaluated_meshes_sha256']!=metadata['receipt']['evaluated_meshes_sha256']:
        raise ValueError('Cached Blender evaluated geometry changed')
    device=V.configure_cycles(False)
    if bpy.app.version[:3]!=(4,5,14):raise ValueError('Production Blender pin differs')
    return path,scene,metadata


def setup(scene,context,view):
    for spec in scene['lights']:
        obj=context['lights'][spec['id']]
        factor=(view.get('dimmers',{}).get(spec['layer'],1.)*spec.get('dimmer',1.)
                if spec['layer'] in view['layers_on'] else 0.)
        obj.data.energy=context['full_power'][spec['id']]*factor
        obj.hide_render=factor<=0
    emissive=V.set_emissive_view(context['emissive_sources'],context['mesh_by_id'],context['switched_emitters'],view)
    sun=view['sun']
    V.photoreal.daylight_world(sun['altitude_deg'],sun['azimuth_true_deg']-scene['north']['model_y_bearing_deg'])
    camera,pitch=V.configure_camera(view)
    return camera,pitch,emissive


def remove_camera(camera):
    data=camera.data
    bpy.data.objects.remove(camera,do_unlink=True)
    bpy.data.cameras.remove(data)


def source_probe(scene,context,view,out):
    from archpipe.exposure_groups import measurement,rule,lamp_population
    camera,_,_=setup(scene,context,view)
    s=bpy.context.scene;p=rule()['source_probe']
    s.render.resolution_x,s.render.resolution_y=p['resolution']
    s.render.resolution_percentage=100;s.cycles.samples=p['samples']
    s.cycles.use_adaptive_sampling=False;s.cycles.use_denoising=False
    s.cycles.max_bounces=p['max_bounces'];s.cycles.seed=p['seed']
    s.view_settings.view_transform='Standard';s.view_settings.look='None';s.view_settings.exposure=0
    s.view_settings.use_white_balance=False
    s.render.image_settings.file_format='OPEN_EXR';s.render.image_settings.color_depth='32'
    emission=[(n.inputs['Strength'],n.inputs['Strength'].default_value) for m in bpy.data.materials if m.use_nodes
              for n in m.node_tree.nodes if n.type=='EMISSION']
    for obj in context['lights'].values():obj.data.energy=0
    for socket,_ in emission:socket.default_value=0
    def probe(mode):
        file=out/(view['id']+'-'+mode+'.exr');s.render.filepath=str(file)
        started=time.monotonic();bpy.ops.render.render(write_still=True)
        image=bpy.data.images.load(str(file));pixels=np.array(image.pixels[:]).reshape(-1,4)[:,:3]
        bpy.data.images.remove(image)
        return np.maximum(0,pixels@np.array([.2126,.7152,.0722])).tolist(),time.monotonic()-started
    day,day_seconds=probe('daylight-only')
    for socket,value in emission:socket.default_value=value
    remove_camera(camera)
    camera,_,_=setup(scene,context,view)
    for n in s.world.node_tree.nodes:
        if n.type=='BACKGROUND':n.inputs['Strength'].default_value=0
    lamps,lamp_seconds=probe('lamps-only')
    row=measurement(lamps,day)
    row.update(lamp_population=lamp_population(scene,view,context['emissive_sources']),
               daylight_seconds=day_seconds,lamps_seconds=lamp_seconds)
    remove_camera(camera)
    return row


def measure(args,path,scene,context):
    """Source isolations plus camera meter per frame, then one lock per exposure group.

    Clip route: every frame, one lock. Villa route: each segment (interior, garden placeholder) is its own
    group with its own lock; only every Nth frame of a segment is metered (registered, default 24 = one per
    second) because 10,000 metered frames would cost more than the preview itself. --segments limits which
    groups are measured.
    """
    from archpipe.exposure_groups import RULE_SHA256,transport_digest
    out=Path(args.root)/'exposure';out.mkdir(parents=True,exist_ok=True)
    views=frame_views(path,scene);villa=is_villa_path(path)
    segments=sorted({group_of(f) for f in path['frames']})
    if args.segments:segments=[s for s in segments if s in args.segments.split(',')]
    every=path['settings'].get('interior_preview_every_nth_frame_for_exposure',1) if villa else 1
    for segment in segments:
        indices=[f['index'] for f in path['frames'] if group_of(f)==segment]
        if villa:
            step=max(1,min(every,len(indices)//6))      # a small group (a dark room, a garden pan) still gets at least six meter readings
            indices=indices[::step]+([indices[-1]] if indices[-1] not in indices[::step] else [])
        rows=[];meters={}
        for index in indices:
            view=views[index];file=out/(view['id']+'.json')
            if file.exists():record=json.loads(file.read_text())
            else:
                row=source_probe(scene,context,view,out)
                camera,_,_=setup(scene,context,view)
                s=bpy.context.scene;s.render.resolution_x,s.render.resolution_y=path['settings']['final_resolution']
                s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast'
                ev,logavg=V.photoreal.camera_meter(bias_stops=-.4,look='AgX - Medium High Contrast')
                remove_camera(camera)
                record=dict(source=row,meter=dict(exposure_stops=ev,log_average=logavg),path_sha256=path['sha256'])
                save(file,record)
            if record['path_sha256']!=path['sha256']:raise ValueError('Stale frame source measurement')
            rows.append(record['source']);meters[view['id']]=record['meter']
            print('WALKTHROUGH exposure',segment,len(rows),'/',len(indices),flush=True)
        lock=clip_source_group(rows,expected=None if villa else policy()['frames'])
        lock.update(exposure_stops=sorted(m['exposure_stops'] for m in meters.values())[len(meters)//2],
                    group_meters=meters,source_measurements=rows,rule_sha256=RULE_SHA256,segment=segment,
                    metered_frames=indices,path_sha256=path['sha256'],transport_sha256=transport_digest(scene))
        lock['sha256']=digest(lock)
        save(out/('lock.json' if not villa else f'lock-{segment}.json'),lock)


def group_of(frame):
    """The exposure group a frame is metered in: the tour names one per dark room and garden pan; older routes use the segment."""
    return frame.get('exposure_group') or frame.get('segment','interior')


def frame_exposure(args,path,every_ease_s=None):
    """Per frame (exposure stops, white balance K, tint) for the whole path: each frame's own group lock, with every step between groups
    turned into a ramp of `exposure_ease_s` by a moving average (smooth, no cut). Locks are loaded and bound-checked once per group."""
    from archpipe.walkthrough_tour import smooth_series
    locks={};ev=[];kelvin=[];tint=[]
    for f in path['frames']:
        g=group_of(f)
        if g not in locks:locks[g]=load_lock(args,path,f)
        l=locks[g];ev.append(l['exposure_stops']);kelvin.append(l['white_balance_k']);tint.append(0. if l['white_balance_illuminant']=='planckian' else 10.)
    ease=every_ease_s if every_ease_s is not None else path['settings'].get('exposure_ease_s',0.)
    w=int(round(ease*path['settings'].get('fps',24)))
    if w>1:ev,kelvin,tint=(smooth_series(v,w) for v in (ev,kelvin,tint))
    return np.array(ev),np.array(kelvin),np.array(tint),locks


def load_lock(args,path,frame):
    name='lock.json' if not is_villa_path(path) else f"lock-{group_of(frame)}.json"
    lock=json.loads((Path(args.root)/'exposure'/name).read_text())
    if lock['path_sha256']!=path['sha256'] or lock['sha256']!=digest({k:v for k,v in lock.items() if k!='sha256'}):
        raise ValueError('Clip camera lock binding changed')
    return lock


def static_position_output(out):
    """Diagnostic AOV (arbitrary output variable); beauty shaders are unchanged."""
    layer=bpy.context.view_layer
    for name,kind in [('walk-position','COLOR'),('walk-static','VALUE')]:
        if name not in layer.aovs:layer.aovs.add().name=name
        layer.aovs[name].type=kind
    for material in bpy.data.materials:
        if not material.use_nodes:continue
        nodes=material.node_tree.nodes;links=material.node_tree.links
        geometry=nodes.new('ShaderNodeNewGeometry')
        position=nodes.new('ShaderNodeOutputAOV');position.name='walk-position-output';position.aov_name='walk-position'
        links.new(geometry.outputs['Position'],position.inputs['Color'])
        mask=nodes.new('ShaderNodeOutputAOV');mask.aov_name='walk-static'
        descriptors=[]
        for node in nodes:
            record={'type':node.type}
            if node.type=='BSDF_PRINCIPLED':
                for key,socket in [('roughness','Roughness'),('metallic','Metallic'),('transmission','Transmission Weight'),('alpha','Alpha'),('emission_strength','Emission Strength')]:
                    record[key]=float(node.inputs[socket].default_value)
                    record[key+'_linked']=node.inputs[socket].is_linked
                record['emission_color_max']=max(node.inputs['Emission Color'].default_value[:3])
                record['emission_color_linked']=node.inputs['Emission Color'].is_linked
            descriptors.append(record)
        valid=static_material_eligible(descriptors)
        mask.inputs['Value'].default_value=float(valid)
    scene=bpy.context.scene;scene.use_nodes=True;tree=scene.node_tree
    tree.nodes.clear()
    source=tree.nodes.new('CompositorNodeRLayers')
    alpha=tree.nodes.new('CompositorNodeSetAlpha')
    tree.links.new(source.outputs['walk-position'],alpha.inputs['Image'])
    tree.links.new(source.outputs['walk-static'],alpha.inputs['Alpha'])
    output=tree.nodes.new('CompositorNodeOutputFile');output.base_path=str(out)
    output.format.file_format='OPEN_EXR';output.format.color_depth='32';output.format.color_mode='RGBA'
    tree.links.new(alpha.outputs['Image'],output.inputs[0])
    composite=tree.nodes.new('CompositorNodeComposite');tree.links.new(source.outputs['Image'],composite.inputs['Image'])
    return output


def render_frames(args,path,scene,context):
    out=Path(args.root)/args.stage
    if args.stage=='sampling':out/=str(args.samples)
    out.mkdir(parents=True,exist_ok=True)
    views=frame_views(path,scene)
    resolution=path['settings']['preview']['resolution'] if args.stage in ('draft','preview') else path['settings']['final_resolution']
    samples=path['settings']['preview'].get('samples',32) if args.stage in ('draft','preview') else args.samples
    n=len(path['frames'])
    default=[f['index'] for f in path['frames'] if f.get('segment','interior') in (args.segments.split(',') if args.segments else ['interior','garden-placeholder'])]
    indices=[0,(n-1)//2,n-1] if args.stage=='draft' else [int(i) for i in args.frames.split(',')] if args.frames else default
    position_output=static_position_output(out) if args.stage=='final' else None
    ev,kelvin,tint,_=frame_exposure(args,path)
    for index in indices:
        lock=load_lock(args,path,path['frames'][index])
        view=views[index];png=out/(view['id']+'.png');receipt_file=png.with_suffix('.json')
        identity=digest(dict(path=path['sha256'],lock=lock['sha256'],resolution=resolution,samples=samples))
        if receipt_file.exists():
            receipt=json.loads(receipt_file.read_text())
            if (receipt.get('identity')==identity and png.exists() and receipt['png_sha256']==hashlib.sha256(png.read_bytes()).hexdigest()
                    and (args.stage!='final' or ((out/(view['id']+'-positions.npz')).exists()
                    and receipt.get('positions_sha256')==hashlib.sha256((out/(view['id']+'-positions.npz')).read_bytes()).hexdigest()))):
                continue
        camera,pitch,emissive=setup(scene,context,view)
        s=bpy.context.scene;s.render.resolution_x,s.render.resolution_y=resolution;s.render.resolution_percentage=100
        s.cycles.samples=samples;s.cycles.max_bounces=16;s.cycles.use_adaptive_sampling=False;s.cycles.use_denoising=True
        s.cycles.seed=0;s.cycles.use_animated_seed=False
        s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast'
        s.view_settings.exposure=float(ev[index])
        wb=V.photoreal.white_balance(float(kelvin[index]),illuminant=lock['white_balance_illuminant']);s.view_settings.white_balance_tint=float(tint[index])
        s.render.image_settings.file_format='PNG';s.render.image_settings.color_depth='8';s.render.filepath=str(png)
        if position_output:position_output.file_slots[0].path=view['id']+'-position-'
        bpy.context.view_layer.update();started=time.monotonic();bpy.ops.render.render(write_still=True)
        elapsed=time.monotonic()-started
        record=dict(identity=identity,index=index,path_sha256=path['sha256'],lock_sha256=lock['sha256'],
                    samples=samples,resolution=resolution,render_seconds=elapsed,render_device=context['render_device'],
                    exposure_stops=float(s.view_settings.exposure),white_balance_k=float(s.view_settings.white_balance_temperature),
                    white_balance_tint=float(s.view_settings.white_balance_tint),white_balance_illuminant=lock['white_balance_illuminant'],
                    exposure_group=lock['group'],blender_version=bpy.app.version_string,
                    camera_pitch_deg=pitch,white_balance_applied=wb,
                    subjects=V.subjects(view,scene["meshes"],context["objects"]),
                    lights_on_count=sum(not o.hide_render for o in context['lights'].values()),emissive_sources=emissive,
                    qa_scene=V.frame_qa_scene(scene,view,camera,context['objects'],context['materials'],context['cloth_report']),
                    png_sha256=hashlib.sha256(png.read_bytes()).hexdigest())
        if position_output:
            position_file=next(out.glob(view['id']+'-position-*.exr'))
            image=bpy.data.images.load(str(position_file));values=np.array(image.pixels[:],dtype=np.float32).reshape(resolution[1],resolution[0],4)[::-1].copy()
            bpy.data.images.remove(image)
            np.savez_compressed(out/(view['id']+'-positions.npz'),positions=values)
            record['positions_sha256']=hashlib.sha256((out/(view['id']+'-positions.npz')).read_bytes()).hexdigest()
            position_file.unlink()
        save(receipt_file,record);remove_camera(camera)
        print('WALKTHROUGH wrote',png,elapsed,flush=True)


def place_camera(obj,c):
    """Same placement as villa_scene.configure_camera, applied to an existing camera (level camera, vertical lens shift)."""
    obj.location=c['position']
    direction=Vector(c['target'])-Vector(c['position']);horizontal=Vector((direction.x,direction.y,0))
    obj.rotation_euler=horizontal.to_track_quat('-Z','Y').to_euler()
    obj.data.lens=c.get('lens_mm',obj.data.lens)       # per frame: the 16 mm small-room 360s and the eased focal length between them
    obj.data.shift_y=c.get('shift_y',0)+direction.z/max(horizontal.length,1e-9)*obj.data.lens/obj.data.sensor_width


def depth_samples(camera,grid,far=40.):
    """First-hit depth, point and normal over a grid of rays through the frame; glazing is transparent (we look through it)."""
    from archpipe.walkthrough_tour import informative_rule
    deps=bpy.context.evaluated_depsgraph_get();scene=bpy.context.scene
    W,H=grid;cam=camera.data;mw=camera.matrix_world;R=mw.to_3x3();origin=mw.translation
    aspect=scene.render.resolution_y/scene.render.resolution_x
    xs=(np.arange(W)+.5)/W-.5;ys=((np.arange(H)+.5)/H-.5)*aspect+cam.shift_y
    depth=[];pts=[];nor=[]
    for y in ys:
        for x in xs:
            d=(R@Vector((x*cam.sensor_width,y*cam.sensor_width,-cam.lens))).normalized()
            o=origin.copy();travelled=0.;hit_ok=False
            for _ in range(4):
                hit,loc,n,face,obj,_ = scene.ray_cast(deps,o,d,distance=far-travelled)
                if not hit:break
                travelled+=(loc-o).length
                ev=obj.evaluated_get(deps).data if obj.type=='MESH' else None      # the face index belongs to the evaluated mesh
                slot=ev.polygons[face].material_index if ev is not None and 0<=face<len(ev.polygons) else -1
                mat=ev.materials[slot] if ev is not None and 0<=slot<len(ev.materials) else None
                if obj.hide_render or 'glass' in obj.name.lower() or (mat is not None and 'glass' in mat.name.lower()):   # ray_cast ignores hide_render: the hidden closed curtains were hit at 0.6 m
                    o=loc+d*1e-3;travelled+=1e-3;continue
                hit_ok=True;break
            depth.append(travelled if hit_ok else far);pts.append(list(loc) if hit_ok else [0,0,0]);nor.append(list(n) if hit_ok else [0,0,1])
    ok=np.array([d<far for d in depth])
    return np.array(depth),np.array(pts)[ok],np.array(nor)[ok],ok


def workbench(args,path,scene,context):
    """Fast geometry preview of every frame: Workbench solid shading with cavity, 640x360 JPEG, plus the depth-grid metrics
    behind the non-informative-frame rule. --metrics-only skips the images (used to calibrate on an earlier path)."""
    from archpipe.walkthrough_tour import frame_metrics,informative_rule
    out=Path(args.root)/'workbench'/(args.out_name or path['sha256'][:10]);out.mkdir(parents=True,exist_ok=True)
    s=bpy.context.scene;rule=informative_rule()
    s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x,s.render.resolution_y=640,360;s.render.resolution_percentage=100
    sh=s.display.shading;sh.type='SOLID';sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_cavity=True;sh.cavity_type='BOTH'
    sh.cavity_ridge_factor=1.;sh.cavity_valley_factor=1.5;sh.show_object_outline=False
    s.display.render_aa='FXAA';s.view_settings.view_transform='Standard';s.view_settings.look='None';s.view_settings.exposure=0
    s.render.film_transparent=False;s.render.image_settings.file_format='JPEG';s.render.image_settings.quality=85
    views=frame_views(path,scene)
    indices=[int(i) for i in args.frames.split(',')] if args.frames else [f['index'] for f in path['frames']]
    camera,_=V.configure_camera(views[indices[0]])
    metrics_file=out/'metrics.json';rows={r['index']:r for r in json.loads(metrics_file.read_text())} if metrics_file.exists() else {}
    cull=None
    if args.cull>0:
        objs=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.hide_render]
        boxes=np.array([[list(o.matrix_world@Vector(c)) for c in o.bound_box] for o in objs]);lo=boxes.min(1);hi=boxes.max(1)
        cull=(objs,lo,hi,np.zeros(len(objs),bool));print('WALKTHROUGH culling',len(objs),'objects',flush=True)
    started=time.monotonic();done=0
    for index in indices:
        jpg=out/f'frame-{index:05d}.jpg'
        need_image=not args.metrics_only and not jpg.exists() and not args.animation
        if index in rows and not need_image:continue
        place_camera(camera,views[index]['camera'])
        if not args.animation:
            for rec,objs in door_objects(path,context):pose_door(rec,objs,path['frames'][index].get('doors',{}).get(rec['element'],1.))
        bpy.context.view_layer.update()
        t0=time.monotonic()
        if index not in rows:
            depth,pts,nor,ok=depth_samples(camera,rule['grid'])
            m=frame_metrics(depth,pts,nor,rule);m['index']=index;rows[index]=m
        if cull and need_image:
            objs,lo,hi,hidden=cull;c=np.array(views[index]['camera']['position']);g=path['frames'][index]['ground_m']
            far=((lo[:,0]>c[0]+args.cull)|(hi[:,0]<c[0]-args.cull)|(lo[:,1]>c[1]+args.cull)|(hi[:,1]<c[1]-args.cull)
                 |(hi[:,2]<g-3.6)|(lo[:,2]>g+6.6))
            for k in np.where(far!=hidden)[0]:objs[k].hide_render=bool(far[k])
            hidden[:]=far
        t1=time.monotonic()
        if need_image:
            s.render.filepath=str(jpg)
            if args.opengl:bpy.ops.render.opengl(write_still=True,view_context=False)
            else:bpy.ops.render.render(write_still=True)
        done+=1
        if done<=12 or done%500==0:print('WALKTHROUGH timing',index,'rays',round(t1-t0,2),'render',round(time.monotonic()-t1,2),flush=True)
        if done%500==0:
            save(metrics_file,[rows[k] for k in sorted(rows)]);print('WALKTHROUGH workbench',done,'/',len(indices),round(time.monotonic()-started),'s',flush=True)
    if args.animation and not args.metrics_only:
        # one animation render: the engine and its scene copy persist across frames (a fresh render per frame re-exports the whole scene, ~6 s)
        todo=[i for i in indices if not (out/f'frame-{i:05d}.jpg').exists()]
        if todo:
            camera.animation_data_clear()
            for i in todo:
                place_camera(camera,views[i]['camera'])
                for prop in ('location','rotation_euler'):camera.keyframe_insert(prop,frame=i)
                camera.data.keyframe_insert('shift_y',frame=i);camera.data.keyframe_insert('lens',frame=i)
            for fc in list(camera.animation_data.action.fcurves)+list(camera.data.animation_data.action.fcurves):
                for kp in fc.keyframe_points:kp.interpolation='CONSTANT'
            key_doors(path,door_objects(path,context),todo)
            run=todo[0];first=todo[0]
            s.frame_start=min(todo);s.frame_end=max(todo);s.frame_step=1
            s.render.filepath=str(out/'frame-#####');t2=time.monotonic()
            if len(todo)==s.frame_end-s.frame_start+1:bpy.ops.render.render(animation=True)
            else:
                # sparse (resume): render each maximal run
                runs=[];a=b=todo[0]
                for i in todo[1:]:
                    if i==b+1:b=i
                    else:runs.append((a,b));a=b=i
                runs.append((a,b))
                for a,b in runs:
                    s.frame_start,s.frame_end=a,b;bpy.ops.render.render(animation=True)
            print('WALKTHROUGH animation',len(todo),'frames',round(time.monotonic()-t2,1),'s',flush=True)
    save(metrics_file,[rows[k] for k in sorted(rows)])
    print('WALKTHROUGH workbench done',len(indices),round(time.monotonic()-started),'s',flush=True)


def door_objects(path,context):
    """[(record, [leaf object, handle object])] of the path's animated door leaves; the leaf and its split-off handle turn together about the hinge.
    The leaf is never hidden or removed: only its transform is keyframed."""
    out=[]
    for rec in path.get('door_anim',[]):
        objs=[context['objects'][rec['leaf_id']]]
        handle=context['objects'].get('door-handle-'+rec['element'])
        if handle is not None:objs.append(handle)
        for o in objs:
            if o.hide_render or o.hide_viewport:raise ValueError('animated door part is hidden: '+o.name)
        out.append((rec,objs))
    return out


def pose_door(rec,objs,state):
    """Turn the leaf (built in its open pose) about the hinge: angle = -signed_open*(1-state), so state 1 is open as built and 0 is closed as authored."""
    psi=-math.radians(rec['signed_open_deg'])*(1.-state);c,sn=math.cos(psi),math.sin(psi);hx,hy=rec['hinge']
    for o in objs:
        o.rotation_mode='XYZ';o.rotation_euler=(0.,0.,psi);o.location=(hx-(hx*c-hy*sn),hy-(hx*sn+hy*c),0.)


def key_doors(path,doors,indices):
    for i in indices:
        for rec,objs in doors:
            pose_door(rec,objs,path['frames'][i].get('doors',{}).get(rec['element'],1.))
            for o in objs:
                for prop in ('location','rotation_euler'):o.keyframe_insert(prop,frame=i)
    for rec,objs in doors:
        for o in objs:
            if o.animation_data and o.animation_data.action:
                for fc in o.animation_data.action.fcurves:
                    for kp in fc.keyframe_points:kp.interpolation='CONSTANT'


def lookdev(args,path,scene,context):
    """Low-sample Cycles preview as ONE animation render per arithmetic run of frames.

    The interior exposure lock, lights and emissives are identical for every frame, and a render call per frame
    re-exports the whole scene (3-6 s of a 2 s render), so the camera is keyframed and the engine keeps its scene
    (persistent data). Same Cycles settings, lock, seed and tone map as `render_frames`; per-frame receipts are
    written afterwards (path hash, PNG hash, mean render seconds). No per-frame render_qa here: a draft."""
    out=Path(args.root)/'lookdev';out.mkdir(parents=True,exist_ok=True)
    views=frame_views(path,scene);resolution=path['settings']['preview']['resolution'];samples=path['settings']['preview'].get('samples',16)
    indices=[int(i) for i in args.frames.split(',')] if args.frames else [f['index'] for f in path['frames']]
    todo=[i for i in indices if not (out/f'frame-{i:04d}.png').exists()]
    if not todo:print('WALKTHROUGH lookdev nothing to do',flush=True);return
    ev,kelvin,tint,locks=frame_exposure(args,path)
    camera,pitch,emissive=setup(scene,context,views[todo[0]])
    s=bpy.context.scene;s.render.resolution_x,s.render.resolution_y=resolution;s.render.resolution_percentage=100
    s.cycles.samples=samples;s.cycles.max_bounces=16;s.cycles.use_adaptive_sampling=False;s.cycles.use_denoising=True
    s.cycles.seed=0;s.cycles.use_animated_seed=False;s.render.use_persistent_data=True
    s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast'
    V.photoreal.white_balance(5500.,illuminant='daylight')
    s.render.image_settings.file_format='PNG';s.render.image_settings.color_depth='8'
    camera.animation_data_clear();s.animation_data_clear() if s.animation_data else None
    vs=s.view_settings
    for i in todo:
        place_camera(camera,views[i]['camera'])
        for prop in ('location','rotation_euler'):camera.keyframe_insert(prop,frame=i)
        camera.data.keyframe_insert('shift_y',frame=i);camera.data.keyframe_insert('lens',frame=i)
        vs.exposure=float(ev[i]);vs.white_balance_temperature=float(kelvin[i]);vs.white_balance_tint=float(tint[i])      # eased between groups (frame_exposure)
        for prop in ('exposure','white_balance_temperature','white_balance_tint'):vs.keyframe_insert(prop,frame=i)
    fcs=list(camera.animation_data.action.fcurves)+list(camera.data.animation_data.action.fcurves)+list(s.animation_data.action.fcurves)
    for fc in fcs:
        for kp in fc.keyframe_points:kp.interpolation='CONSTANT'
    key_doors(path,door_objects(path,context),todo)      # animated door leaves: pose per rendered frame
    runs=[];a=b=todo[0];step=None
    for i in todo[1:]:
        if step is None and i>b:step=i-b
        if step is not None and i==b+step:b=i
        else:runs.append((a,b,step or 1));a=b=i;step=None
    runs.append((a,b,step or 1))
    s.render.filepath=str(out/'frame-####');started=time.monotonic()
    for a,b,step in runs:
        s.frame_start,s.frame_end,s.frame_step=a,b,step;bpy.ops.render.render(animation=True)
        print('WALKTHROUGH lookdev run',a,b,step,round(time.monotonic()-started),'s',flush=True)
    each=(time.monotonic()-started)/len(todo)
    for i in todo:
        png=out/f'frame-{i:04d}.png'
        lock=locks[group_of(path['frames'][i])]
        save(png.with_suffix('.json'),dict(path_sha256=path['sha256'],lock_sha256=lock['sha256'],exposure_group=group_of(path['frames'][i]),exposure_stops=float(ev[i]),white_balance_k=float(kelvin[i]),lens_mm=views[i]['camera']['lens_mm'],samples=samples,resolution=resolution,
             render_seconds=each,png_sha256=hashlib.sha256(png.read_bytes()).hexdigest(),index=i,render_device=context['render_device']))
    print('WALKTHROUGH lookdev done',len(todo),'frames',round(each,2),'s/frame',flush=True)


def measure_static_coverage(args,path,scene,context):
    """Early real-scene diagnostic; no exposure selection or presentation."""
    out=Path(args.root)/'coverage';out.mkdir(exist_ok=True)
    node=static_position_output(out);views=frame_views(path,scene);rows=[]
    s=bpy.context.scene
    s.render.resolution_x,s.render.resolution_y=path['settings']['preview']['resolution']
    s.render.resolution_percentage=100;s.cycles.samples=4
    s.cycles.seed=0;s.cycles.use_animated_seed=False
    s.cycles.use_adaptive_sampling=False;s.cycles.use_denoising=False
    s.view_settings.view_transform='Standard';s.view_settings.look='None'
    s.view_settings.exposure=0;s.view_settings.use_white_balance=False
    s.render.image_settings.file_format='OPEN_EXR';s.render.image_settings.color_depth='32'
    for index in (0,(len(views)-1)//2,len(views)-1):
        camera,_,_=setup(scene,context,views[index])
        name=f'frame-{index:04d}'
        node.file_slots[0].path=name+'-positions-'
        s.render.filepath=str(out/(name+'-diagnostic.exr'))
        bpy.ops.render.render(write_still=True)
        file=next(out.glob(name+'-positions-*.exr'))
        image=bpy.data.images.load(str(file))
        values=np.array(image.pixels[:]).reshape(-1,4)
        bpy.data.images.remove(image)
        rows.append(dict(index=index,**static_coverage(int((values[:,3]>.999).sum()),len(values))))
        remove_camera(camera)
    result=dict(passed=all(r['passed'] for r in rows),frames=rows,
                path_sha256=path['sha256'],policy_sha256=digest(policy()),
                evaluated_meshes_sha256=context['receipt']['evaluated_meshes_sha256'],
                scope='necessary early static-surface coverage only; all final adjacent pairs still required')
    result['sha256']=digest(result);save(out/'summary.json',result)
    if not result['passed']:raise ValueError('Real camera lacks static opaque measurement coverage')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',required=True)
    parser.add_argument('--stage',choices=['preflight','assembly','coverage','exposure','draft','preview','workbench','lookdev','sampling','reference','final'],required=True)
    parser.add_argument('--samples',type=int,default=64)
    parser.add_argument('--frames');parser.add_argument('--segments')
    parser.add_argument('--target-stage');parser.add_argument('--metrics-only',action='store_true');parser.add_argument('--out-name');parser.add_argument('--opengl',action='store_true');parser.add_argument('--cull',type=float,default=0.);parser.add_argument('--animation',action='store_true')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    if bpy.app.version[:3]!=(4,5,14):raise ValueError('Production pin is Blender 4.5.14')
    if args.stage=='preflight':
        root=Path(args.root)
        if args.target_stage=='assembly':
            path=json.loads((root/'path.json').read_text())
            scene=json.loads((root/'scene.json').read_text())
        else:
            path,scene,context=load_context(args)
        views=frame_views(path,scene)
        V.configure_camera(views[0])
        static_position_output(root/'preflight-diagnostics')
        device=V.configure_cycles(False)
        save(root/('preflight-'+args.target_stage+'.json'),dict(passed=True,
             blender=bpy.app.version_string,render_device=device,path_sha256=path['sha256'],
             frames=len(views),sun=views[0]['sun'],cache_readback=args.target_stage!='assembly'))
        return
    if args.stage=='assembly':
        args.out=str(Path(args.root)/'assembly');Path(args.out).mkdir(parents=True,exist_ok=True)
        args.path=str(Path(args.root)/'path.json');args.ies_dir=str(Path(args.root)/'ies')
        args.library_root=None;args.cpu=False;args.views='all';args.calibrate=False
        args.measure_lighting=False;args.measure_exposure_groups=False;args.walkthrough_callback=prepare
        from archpipe.blender.element_ids import without_ids
        V.render(without_ids(json.loads((Path(args.root)/'scene.json').read_text())),args)
    else:
        path,scene,context=load_context(args)
        if args.stage=='coverage':measure_static_coverage(args,path,scene,context)
        elif args.stage=='exposure':measure(args,path,scene,context)
        elif args.stage=='workbench':workbench(args,path,scene,context)
        elif args.stage=='lookdev':lookdev(args,path,scene,context)
        else:render_frames(args,path,scene,context)


if __name__=='__main__':main()
