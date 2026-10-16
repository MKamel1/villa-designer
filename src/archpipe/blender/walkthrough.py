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
from archpipe.flythrough import admit_path, frame_views, require_renderable, digest, clip_source_group, policy, static_material_eligible, static_coverage, retain_cache_materials


def save(path, value):
    save_bytes(path,(json.dumps(value,indent=2)+'\n').encode())


def evaluated_path_meshes(path):
    """Read actual runtime faces near the whole path; bounds only prune."""
    positions=np.array([f['camera']['position'] for f in path['frames']])
    low=positions.min(0)-.31;high=positions.max(0)+.31
    low[2],high[2]=-2.95,-1.2
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
                if np.all(pts.min(0)<=high) and np.all(pts.max(0)>=low):faces.append(pts.tolist())
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
    scene=json.loads((Path(args.root)/'scene.json').read_text())
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
    from archpipe.exposure_groups import RULE_SHA256,transport_digest
    out=Path(args.root)/'exposure';out.mkdir(parents=True,exist_ok=True)
    views=frame_views(path,scene);rows=[];meters={}
    for view in views:
        file=out/(view['id']+'.json')
        if file.exists():record=json.loads(file.read_text())
        else:
            row=source_probe(scene,context,view,out)
            camera,_,_=setup(scene,context,view)
            s=bpy.context.scene;s.render.resolution_x,s.render.resolution_y=policy()['final_resolution']
            s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast'
            ev,logavg=V.photoreal.camera_meter(bias_stops=-.4,look='AgX - Medium High Contrast')
            remove_camera(camera)
            record=dict(source=row,meter=dict(exposure_stops=ev,log_average=logavg),path_sha256=path['sha256'])
            save(file,record)
        if record['path_sha256']!=path['sha256']:raise ValueError('Stale frame source measurement')
        rows.append(record['source']);meters[view['id']]=record['meter']
        print('WALKTHROUGH exposure',len(rows),'/ 720',flush=True)
    lock=clip_source_group(rows)
    lock.update(exposure_stops=sorted(m['exposure_stops'] for m in meters.values())[len(meters)//2],
                group_meters=meters,source_measurements=rows,rule_sha256=RULE_SHA256,
                path_sha256=path['sha256'],transport_sha256=transport_digest(scene))
    lock['sha256']=digest(lock)
    save(out/'lock.json',lock)


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
    lock=json.loads((Path(args.root)/'exposure/lock.json').read_text())
    if lock['path_sha256']!=path['sha256'] or lock['sha256']!=digest({k:v for k,v in lock.items() if k!='sha256'}):
        raise ValueError('Clip camera lock binding changed')
    views=frame_views(path,scene)
    resolution=policy()['preview']['resolution'] if args.stage in ('draft','preview') else policy()['final_resolution']
    samples=32 if args.stage in ('draft','preview') else args.samples
    indices=[0,359,719] if args.stage=='draft' else [int(i) for i in args.frames.split(',')] if args.frames else range(720)
    position_output=static_position_output(out) if args.stage=='final' else None
    for index in indices:
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
        s.view_settings.exposure=lock['exposure_stops']
        wb=V.photoreal.white_balance(lock['white_balance_k'],illuminant=lock['white_balance_illuminant'])
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


def measure_static_coverage(args,path,scene,context):
    """Early real-scene diagnostic; no exposure selection or presentation."""
    out=Path(args.root)/'coverage';out.mkdir(exist_ok=True)
    node=static_position_output(out);views=frame_views(path,scene);rows=[]
    s=bpy.context.scene
    s.render.resolution_x,s.render.resolution_y=policy()['preview']['resolution']
    s.render.resolution_percentage=100;s.cycles.samples=4
    s.cycles.seed=0;s.cycles.use_animated_seed=False
    s.cycles.use_adaptive_sampling=False;s.cycles.use_denoising=False
    s.view_settings.view_transform='Standard';s.view_settings.look='None'
    s.view_settings.exposure=0;s.view_settings.use_white_balance=False
    s.render.image_settings.file_format='OPEN_EXR';s.render.image_settings.color_depth='32'
    for index in (0,359,719):
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
    parser.add_argument('--stage',choices=['preflight','assembly','coverage','exposure','draft','preview','sampling','reference','final'],required=True)
    parser.add_argument('--samples',type=int,default=64)
    parser.add_argument('--frames')
    parser.add_argument('--target-stage')
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
        V.render(json.loads((Path(args.root)/'scene.json').read_text()),args)
    else:
        path,scene,context=load_context(args)
        if args.stage=='coverage':measure_static_coverage(args,path,scene,context)
        elif args.stage=='exposure':measure(args,path,scene,context)
        else:render_frames(args,path,scene,context)


if __name__=='__main__':main()
