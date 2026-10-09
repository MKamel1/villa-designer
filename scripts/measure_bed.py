"""Measure a cached bed through C2 intake; never approve a failed candidate.

Bounds are native glTF metres (X across, Y up, Z along). Triangle count
comes from the actual indexed geometry, not the website metadata. This
command writes evidence only and does not edit the manifest or layout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from archpipe.asset_intake import measure_gltf_bounds, validate_entry
from archpipe.asset_route_generator import asset_triangles


def measure(asset, model, manifest):
    entries=json.loads(manifest.read_text())['props']
    entry=next(e for e in entries if e['id']==asset)
    if entry['role']!='bed':
        raise ValueError('A measured bed intake requires role bed')
    gltf=json.loads(model.read_text())
    position_indices={p['attributes']['POSITION'] for m in gltf['meshes'] for p in m['primitives']}
    accessor_bounds=measure_gltf_bounds(model)
    triangles=asset_triangles(model)
    # The triangle reader converts glTF (X,Y,Z) to Blender (X,-Z,Y).
    # Undo that conversion for the reported native glTF bounds. Rotated
    # accessor boxes are conservative envelopes, not actual mesh extents.
    points=triangles.reshape(-1,3)[:,[0,2,1]].copy()
    points[:,2]*=-1
    bounds=dict(min=points.min(axis=0).tolist(),max=points.max(axis=0).tolist())
    files=[model]+[model.parent/b['uri'] for b in gltf['buffers']]
    images=[model.parent/i['uri'] for i in gltf.get('images',[]) if 'uri' in i]
    missing=[str(p.relative_to(model.parent)) for p in images if not p.is_file()]
    return dict(schema='bed-intake-measurement/1',asset=asset,source_url=entry['source_url'],
                author=entry['author'],licence=entry['licence'],credit=entry['credit'],
                bounds_m=bounds,accessor_envelope_m=accessor_bounds,
                bounds_basis='all indexed triangle vertices after every scene-node transform',
                up_axis=entry['up_axis'],front_axis=entry['front_axis'],
                units_normalised=entry.get('units_normalised'),
                triangle_count=len(triangles),
                vertex_count=sum(gltf['accessors'][i]['count'] for i in position_indices),
                sha256={str(p.relative_to(model.parent)):hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in files+images if p.is_file()},
                missing_textures=missing,intake_violations=validate_entry(entry,model),
                accepted_for_placement=False,
                status='measurement only; fixed footprint fit and neutral preview review still required')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--asset',required=True)
    parser.add_argument('--model',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,default=ROOT/'ops/workstation/library-manifest.json')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=measure(args.asset,args.model,args.manifest)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('asset','bounds_m','triangle_count','vertex_count','intake_violations','accepted_for_placement')}))


if __name__=='__main__':
    main()
