"""Extract actual imported bed parts for portable review and mattress binding.

Run in Blender. Geometry is in metres in Blender's converted glTF axes,
without placement scaling or design edits. The receipt binds model/buffer/
texture bytes to every imported vertex and polygon. Never edits an asset.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys


def main():
    import bpy
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
    from archpipe.blender.scene_reset import clear_objects, scene_meshes
    from mathutils import Vector
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models',nargs='+',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    args.output.mkdir(parents=True,exist_ok=True)
    for path in args.models:
        clear_objects(bpy)
        bpy.ops.import_scene.gltf(filepath=str(path.resolve()))
        bpy.context.view_layer.update()
        meshes=[]
        for obj in scene_meshes(bpy):
            points=[list(obj.matrix_world@v.co) for v in obj.data.vertices]
            faces=[[points[i] for i in p.vertices] for p in obj.data.polygons]
            low=[min(p[i] for p in points) for i in range(3)]
            high=[max(p[i] for p in points) for i in range(3)]
            meshes.append(dict(name=obj.name,faces=faces,bounds_m=[low,high],
                material_slots=[m.name if m else None for m in obj.data.materials]))
        gltf=json.loads(path.read_text())
        files=[path]+[path.parent/r['uri'] for r in gltf['buffers']+gltf.get('images',[]) if 'uri' in r]
        hashes={str(p.relative_to(path.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        geometry=dict(schema='bed-model-geometry/1',asset=path.parent.name,
            coordinates='Blender converted glTF metres, X across, Y horizontal, Z up',
            source_sha256=hashes,meshes=meshes)
        dest=args.output/(path.parent.name+'.json.gz')
        dest.write_bytes(gzip.compress(json.dumps(geometry,separators=(',',':')).encode(),mtime=0))
        summary=dict(asset=path.parent.name,source_sha256=hashes,
            parts=[{k:m[k] for k in ('name','bounds_m','material_slots')} for m in meshes])
        (args.output/(path.parent.name+'-parts.json')).write_text(json.dumps(summary,indent=2)+'\n')
        print(path.parent.name,'parts',len(meshes),'receipt_bytes',dest.stat().st_size)

if __name__=='__main__':main()
