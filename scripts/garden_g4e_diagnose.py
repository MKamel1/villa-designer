"""Bounded linear-only garden source-isolation probes, never presentation PNGs.

RGB means linear red, green and blue channels; lux is illuminance. Four
variants isolate sky, uplights and gravel bounce without editing input.
"""
import argparse,json,sys,fcntl
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))


def run(args):
    import bpy
    from mathutils import Vector
    from archpipe.blender import villa_scene as B,photoreal as P,build_scene
    d=json.loads(args.scene.read_text());args.output.mkdir(parents=True,exist_ok=True)
    view=next(v for v in d['views'] if v['state']=='exterior-dusk' and 'north-garden-evening' in v['id'])
    report=json.loads(Path('/home/omar/archpipe/villa-render/155b74a730c0d87aea2fcb8a/out/v41-north-garden-evening.json').read_text())
    def read(path):
        im=bpy.data.images.load(str(path),check_existing=False);p=np.asarray(im.pixels[:]).reshape(im.size[1],im.size[0],4)[:,:,:3];bpy.data.images.remove(im);return p
    retained=read('/home/omar/archpipe/villa-render/155b74a730c0d87aea2fcb8a/out/v41-north-garden-evening.exr')
    sky_pixels=read('/home/omar/archpipe/assets/library/hdri/belfast_sunset_puresky.exr')
    h=sky_pixels.shape[0];angles=np.linspace(0,np.pi,h,endpoint=False)+np.pi/(2*h)
    weights=np.maximum(np.cos(angles),0)*np.sin(angles)
    sky_rgb=np.sum(sky_pixels*weights[::-1,None,None],axis=(0,1))/max(sum(weights)*sky_pixels.shape[1],1e-9)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    meshes=[]
    for m in d['meshes']:
        p=np.asarray([p for f in m['faces'] for p in f]);lo=p.min(axis=0);hi=p.max(axis=0)
        if np.all(lo<np.array([7,-19,5])) and np.all(hi>np.array([-5,-32,-4])) and m['id'] not in view.get('hide_meshes',[]):meshes.append(m)
    names={m['material'] for m in meshes}|{n for m in meshes for n in m.get('face_materials',[])}
    warnings=[];materials={n:B.add_material(n,d['materials'][n],'/home/omar/archpipe/assets/library',warnings) for n in names}
    B.configure_glass(materials,{n:d['materials'][n] for n in names})
    objects=B.build_meshes(meshes,materials,d['materials'],warnings);B.build_climbers(meshes,objects,materials,warnings)
    # Apply production layer switching: all other luminous lenses are OFF.
    switched=B.layered_emissive_materials(meshes,objects,d['materials'])
    for node in switched.values():node.inputs['Strength'].default_value=0
    # Single-material emissive objects without layer cloning also remain off.
    for material in materials.values():
        for node in material.node_tree.nodes:
            if node.type=='EMISSION':node.inputs['Strength'].default_value=0
    lights=[B.add_light(l,str(args.ies)) for l in d['lights'] if l.get('garden_g4d')]
    B.configure_cycles(False);camera,_=B.configure_camera(view);s=bpy.context.scene;s.camera=camera
    s.render.resolution_x=320;s.render.resolution_y=216;s.render.resolution_percentage=100;s.cycles.samples=96;s.cycles.max_bounces=8
    s.render.image_settings.file_format='OPEN_EXR';s.render.image_settings.color_depth='32';s.view_settings.view_transform='Raw';s.view_settings.exposure=0
    bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get();frame=camera.data.view_frame(scene=s)
    # Blender frame corners are upper-right, lower-right, lower-left, upper-left.
    masks={k:np.zeros((216,320),dtype=bool) for k in ('foliage','gravel','wall','fixture','other')}
    by={m['id']:m for m in meshes}
    for y in range(216):
        for x in range(320):
            tx=(x+.5)/320;ty=(y+.5)/216
            p=frame[2].lerp(frame[1],tx).lerp(frame[3].lerp(frame[0],tx),ty)
            direction=camera.matrix_world.to_3x3()@p;direction.normalize()
            hit,loc,normal,index,obj,mat=s.ray_cast(deps,camera.location,direction)
            # Physical batching can rename an object; recover its actual source member.
            m=by.get(obj.name,{}) if hit else {}
            if hit and not m:
                members=[spec for spec in meshes if objects[spec['id']]==obj]
                m=members[0] if members else {}
            # Classify what the camera sees through clear glazing, rather
            # than assigning the entire interior-camera image to its pane.
            for _ in range(8):
                if not hit or d['materials'].get(m.get('material'),{}).get('kind')!='glass':break
                hit,loc,normal,index,obj,mat=s.ray_cast(deps,loc+direction*.003,direction)
                m=by.get(obj.name,{}) if hit else {}
                if hit and not m:
                    members=[spec for spec in meshes if objects[spec['id']]==obj]
                    m=members[0] if members else {}
            name=m.get('material','')
            key='foliage' if m.get('species') else 'gravel' if name=='north-pale-gravel' else 'fixture' if m.get('garden_g4d') else 'wall' if m.get('group') in ('shell','context') else 'other'
            masks[key][y,x]=True
    results={};linear_images={}
    def stats(p):
        return dict(mean_rgb=p.mean(axis=0).tolist(),mean_luminance=float(np.mean(p@np.array([.2126,.7152,.0722]))),p995_luminance=float(np.percentile(p@np.array([.2126,.7152,.0722]),99.5)))
    def summarize(p):return {k:dict(pixels=int(mask.sum()),**stats(p[mask])) for k,mask in masks.items() if mask.any()}
    powers=[l.data.energy for l in lights]
    gravel_nodes=[node for node in materials['north-pale-gravel'].node_tree.nodes if node.type=='BSDF_PRINCIPLED']
    for mode in ('combined','sky-only','uplights-only','sky-no-gravel-bounce'):
        for l,power in zip(lights,powers):l.data.energy=0 if mode.startswith('sky') else power
        P.hdri_world('/home/omar/archpipe/assets/library/hdri/belfast_sunset_puresky.exr',0 if mode=='uplights-only' else 30.)
        saved=[]
        if mode=='sky-no-gravel-bounce':
            for node in gravel_nodes:
                saved.append(tuple(node.inputs['Base Color'].default_value));node.inputs['Base Color'].default_value=(0,0,0,1)
        path=args.output/(mode+'.exr');s.render.filepath=str(path);bpy.ops.render.render(write_still=True)
        linear_images[mode]=read(path);results[mode]=summarize(linear_images[mode])
        for node,col in zip(gravel_nodes,saved):node.inputs['Base Color'].default_value=col
    weights=np.array([.2126,.7152,.0722])
    uplight_luminance=linear_images['uplights-only']@weights
    sky_luminance=linear_images['sky-only']@weights
    screen=dict(foliage_screen_fraction=float(masks['foliage'].mean()),
        uplight_dominant_foliage_screen_fraction=float((masks['foliage']&(uplight_luminance>sky_luminance)).mean()),
        definition='First-hit foliage through production glass; uplight-dominant means uplights-only luminance exceeds sky-only luminance at the same pixel; denominator is all 320 x 216 screen pixels. Diagnostic population comparison, no QA allowance or limit.')
    result=dict(screen_fraction=screen,diagnostic_only=True,resolution=[320,216],samples=96,bounces=8,meshes=len(meshes),warnings=warnings,
        retained_exr=stats(retained.reshape(-1,3)),retained_locked_exposure_stops=report['exposure_stops'],
        sky_horizontal_weighted_rgb=sky_rgb.tolist(),lamp_linear_rgb=list(build_scene.kelvin_to_rgb(2700)),
        source_isolation=results,view=view['camera'])
    (args.output/'diagnosis.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--scene',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--ies',type=Path,default=Path('out/garden-g4d/ies'))
    args=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
    with Path('/home/omar/archpipe/locks/graphics.lock').open('rb') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX);run(args)
