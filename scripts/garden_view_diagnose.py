"""Ray evidence for retained garden images, using actual exported meshes/props.

Pixel coordinates are normalised fractions, x rightwards and y downwards.
Distances are metres. Transparent hits are retained, then traced through;
world means that no physical geometry intersects the ray within 1000 metres.
This produces numerical evidence only, never a presentation image.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]

def main():
    import bpy
    from mathutils import Vector
    from bpy_extras.object_utils import world_to_camera_view
    sys.path.insert(0,str(ROOT/'src'))
    from archpipe.blender import villa_scene as B
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--scene',type=Path,required=True)
    ap.add_argument('--requests',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
    data=json.loads(args.scene.read_text());requests=json.loads(args.requests.read_text())
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    warnings=[];library='/home/omar/archpipe/assets/library'
    materials={name:B.add_material(name,spec,library,warnings) for name,spec in data['materials'].items()}
    objects=B.build_meshes(data['meshes'],materials,data['materials'],warnings)
    B.build_climbers(data['meshes'],objects,materials,warnings)
    imported=B.import_props(data['props'],library)
    # build_meshes concatenates authored faces in source-record order.
    owners={};offsets={}
    render_specs, _ = B.sibling('stone_union').prepare(data['meshes'])
    for mesh in render_specs:
        obj=objects[mesh['id']];lo=offsets.get(obj.name,0);hi=lo+len(mesh['faces'])
        owners.setdefault(obj.name,[]).append((lo,hi,mesh['id']))
        offsets[obj.name]=hi
    scene=bpy.context.scene;result=[]
    for request in requests:
        view=request['view'];camera,_=B.configure_camera(view);scene.camera=camera
        scene.render.resolution_x,scene.render.resolution_y=view['resolution']
        bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
        frame=camera.data.view_frame(scene=scene)
        left=min(p.x/-p.z for p in frame);right=max(p.x/-p.z for p in frame)
        bottom=min(p.y/-p.z for p in frame);top=max(p.y/-p.z for p in frame)
        records=[]
        for u,v in request['pixels']:
            direction=camera.matrix_world.to_quaternion() @ Vector((left+(right-left)*u,top+(bottom-top)*v,-1))
            direction.normalize();origin=camera.location.copy();hits=[]
            for bounce in range(12):
                ok,point,normal,index,obj,_=scene.ray_cast(deps,origin,direction,distance=1000)
                if not ok:
                    hits.append(dict(id='world',distance_m=None));break
                source=obj.original.name
                candidates=owners.get(source,[])
                mid=next((name for lo,hi,name in candidates if lo<=index<hi),source)
                if len(candidates)==1:mid=candidates[0][2]
                mat=obj.data.materials[obj.data.polygons[index].material_index] if index<len(obj.data.polygons) and obj.data.materials else None
                transparent=bool(mat and data['materials'].get(mat.name,{}).get('kind') in ('glass','translucent'))
                hits.append(dict(id=mid,object=source,face_index=index,material=mat.name if mat else None,point_m=list(point),normal=list(normal),distance_m=(point-camera.location).length,transparent=transparent))
                if not transparent:break
                origin=point+direction*.002
            records.append(dict(pixel=[u,v],hits=hits))
        result.append(dict(id=request['id'],camera=view['camera'],counts=dict(Counter(row['hits'][-1]['id'] for row in records)),first_counts=dict(Counter(row['hits'][0]['id'] for row in records)),samples=records,mask_pixels=request.get('mask_pixels'),total_pixels=request.get('total_pixels')))
        bpy.data.objects.remove(camera,do_unlink=True)
    args.output.write_text(json.dumps(dict(scene=str(args.scene),requests=str(args.requests),results=result,warnings=warnings),indent=2)+'\n')
    for row in result:print(row['id'],row['counts'],flush=True)

if __name__=='__main__':main()
