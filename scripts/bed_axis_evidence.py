"""Reproduce semantic-axis evidence from unchanged extracted bed faces.

Native glTF axes: X and Z horizontal, Y up. Front means head-to-foot;
access is the outward approach to a bunk's open side or ladder. Bounds alone
cannot name a symmetric bunk's front. This script measures parts/components;
the neutral image review supplies their semantic interpretation.
"""
import argparse
import gzip
import json
from pathlib import Path
import numpy as np

def components(faces):
    # Weld coincident exported positions to reconnect UV/material seams.
    parent={}
    def root(k):
        parent.setdefault(k,k)
        while parent[k]!=k:
            parent[k]=parent[parent[k]];k=parent[k]
        return k
    points={}
    for face in faces:
        keys=[tuple(round(float(v),5) for v in p) for p in face]
        for key,p in zip(keys,face):
            points[key]=p;parent[root(key)]=root(keys[0])
    groups={}
    for key,p in points.items():groups.setdefault(root(key),[]).append(p)
    return list(groups.values())

def native(points):
    a=np.asarray(points,float)[:,[0,2,1]].copy();a[:,2]*=-1;return a

def bounds(points):
    return dict(min=points.min(0).tolist(),max=points.max(0).tolist())

def measure(path):
    geometry=json.loads(gzip.decompress(path.read_bytes()))
    parts=geometry['meshes'];allpoints=native([p for m in parts for f in m['faces'] for p in f]);low,high=allpoints.min(0),allpoints.max(0)
    result=dict(asset=geometry['asset'],source_sha256=geometry['source_sha256'],bounds_m=bounds(allpoints),
        upper_twenty_percent_bounds_m=bounds(allpoints[allpoints[:,1]>=low[1]+.8*(high[1]-low[1])]),
        end_bands={},parts=[],end_band_fraction=.10,weld_precision_native_m=.00001)
    for axis,i in [('X',0),('Z',2)]:
        width=(high[i]-low[i])*.10
        result['end_bands'][axis]=dict(low_end_max_height_m=float(allpoints[allpoints[:,i]<=low[i]+width,1].max()),high_end_max_height_m=float(allpoints[allpoints[:,i]>=high[i]-width,1].max()))
    for part in parts:
        row=dict(name=part['name'],materials=part['material_slots'],bounds_m=bounds(native([p for f in part['faces'] for p in f])))
        if any(word in part['name'].lower() for word in ('pillow','materass')):
            row['connected_components_m']=[bounds(native(p)) for p in components(part['faces']) if len(p)>10]
        result['parts'].append(row)
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--geometry',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    rows=[measure(p) for p in sorted(args.geometry.glob('*.json.gz'))];args.output.write_text(json.dumps(rows,indent=2)+'\n');print('measured',len(rows),'unchanged geometry receipts')
