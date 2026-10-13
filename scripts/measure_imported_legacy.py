"""Generate portable measured component bounds from immutable source imports.

Run in Blender with --python-exit-code 1. No source mesh or library is edited.
Coordinates are metres in Blender's converted local axes, before placement.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))


def spatial_leaves(faces, indices, limit):
    """Partition whole source faces by their centroid, with stable tie order.

    This bounded decomposition represents open structural members without
    filling the cavity of their connected frame. It never edits a face.
    """
    import numpy as np
    if len(indices) <= limit:
        return [indices]
    centres=np.asarray([np.asarray(faces[i]).mean(0) for i in indices])
    axis=int(np.argmax(centres.max(0)-centres.min(0)))
    ordered=sorted(indices,key=lambda i:(float(np.asarray(faces[i]).mean(0)[axis]),i))
    middle=len(ordered)//2
    return spatial_leaves(faces,ordered[:middle],limit)+spatial_leaves(faces,ordered[middle:],limit)


def measure(library, assets):
    import bpy
    import numpy as np
    from archpipe.imported_appearance import _component_bounds, digest
    policy=json.loads((ROOT/'knowledge/imported-component-policy.json').read_text())
    result = dict(schema='imported-component-measurements/1', assets={})
    for asset in assets:
        bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
        root = Path(library)/'props'/asset
        source = root/'model.gltf'
        gltf = json.loads(source.read_text())
        files = ['model.gltf']+[r['uri'] for r in gltf.get('buffers', [])+gltf.get('images', []) if r.get('uri') and not r['uri'].startswith('data:')]
        hashes = {f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in files}
        classification=policy['assets'].get(asset,{})
        if classification and classification['source_sha256'] != hashes['model.gltf']:
            raise ValueError(asset+': structural component classification source changed')
        bpy.ops.import_scene.gltf(filepath=str(source))
        bpy.context.view_layer.update()
        rows = []
        for obj in sorted((o for o in bpy.context.scene.objects if o.type=='MESH'),key=lambda o:o.name):
            vertices = np.asarray([list(obj.matrix_world@v.co) for v in obj.data.vertices])
            indices = [list(p.vertices) for p in obj.data.polygons]
            faces = [vertices[i].tolist() for i in indices]
            components=[]
            for selection,low,high in _component_bounds(faces):
                component_hash=digest(selection)
                refined=component_hash in classification.get('open_frame_components',[])
                groups=(spatial_leaves(faces,list(selection),policy['max_faces_per_open_frame_leaf']) if refined else [selection])
                for group in groups:
                    points=np.asarray([p for i in group for p in faces[i]])
                    components.append(dict(source_face_count=len(group),source_face_indices_sha256=digest(group),
                        source_component_indices_sha256=component_hash,
                        decomposition='spatial face groups for open structural frame' if refined else 'connected component',
                        low=points.min(0).tolist(),high=points.max(0).tolist()))
                if sorted(i for group in groups for i in group) != sorted(selection):
                    raise ValueError(asset+': physical partition dropped or duplicated source faces')
            # Independent measurement of every actual source vertex against
            # its own recorded enclosing bounds is retained with the receipt.
            rows.append(dict(name=obj.name, source_faces_sha256=digest(faces),
                             source_face_count=len(faces), components=components))
            print(asset,obj.name,len(faces),len(components),flush=True)
        result['assets'][asset] = dict(source_sha256=hashes,meshes=rows,component_policy_sha256=digest(policy))
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--library',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--assets',nargs='+',required=True)
    p.add_argument('--manifest',type=Path)
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    record=measure(args.library,args.assets)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_bytes(gzip.compress(json.dumps(record,sort_keys=True,separators=(',',':')).encode(),mtime=0))
    if args.manifest:
        from archpipe.imported_appearance import digest
        manifest=json.loads(args.manifest.read_text())
        for entry in manifest['props']:
            if entry['id'] in record['assets']:
                hashes=record['assets'][entry['id']]['source_sha256']
                entry['source_sha256']=hashes['model.gltf']
                entry['geometry_buffer_sha256']={k:v for k,v in hashes.items() if k.endswith('.bin')}
                entry['imported_component_geometry_sha256']=digest(record['assets'][entry['id']])
        args.manifest.write_text(json.dumps(manifest,indent=2)+'\n')
