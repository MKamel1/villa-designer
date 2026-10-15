"""Collect measured Blender evaluation evidence without changing source artifacts.

Differences are in display sRGB channel values on a zero-to-one scale unless
explicitly labelled linear luminance, chromaticity, millimetres or lux.
"""
import gzip
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
BASE=ROOT/'out/blender52'

def read(path):return json.loads(path.read_text())

def indexed_tasks(points):
    """Preserve every task by its zero-based recorded index, room and label.

    Room/label alone is not unique: kitchen and pillow tasks repeat it.
    """
    return {(index,p['room'],p['label']):p for index,p in enumerate(points)}

def controlled_cloth_attribution(before, after):
    """Refuse to call a changed initial pattern a solver-only comparison."""
    a=before['simulation'];b=after['simulation']
    if a['pattern_seed']!=b['pattern_seed']:
        raise ValueError('Changed initial pattern seed; solver attribution unavailable')
    procedural=all(s.get('method','').startswith('ASSUMED procedural') for s in (a,b))
    if not procedural and not all(s.get('initial_vertices_sha256') for s in (a,b)):
        raise ValueError('Missing initial vertices; solver attribution unavailable')
    if a.get('initial_vertices_sha256')!=b.get('initial_vertices_sha256'):
        raise ValueError('Changed initial vertices; solver attribution unavailable')
    return dict(initial_pattern_equal=True,output_geometry_equal=before['mesh_sha256']==after['mesh_sha256'])

def cloth():
    from archpipe.drape_appearance import enclosure_measurement, appearance_findings, policy
    cache=json.loads(gzip.decompress((ROOT/'knowledge/drape-cloth-cache.json.gz').read_bytes()))['entries']
    rows=[]
    for record in read(BASE/'cloth/geometry-comparison.json'):
        key=record['source_input_sha256'];before=cache[key]
        after=read(BASE/'cloth'/(key+'-process-1.json'))
        control=read(BASE/'cloth-controlled'/(key+'.json'))
        data=read(BASE/'cloth'/(key+'-input.json'))
        enclosure=enclosure_measurement(after,dict(faces=data['faces']))
        findings=appearance_findings(dict(after,id=record['id'],garment_type=data['garment_type']))
        rows.append(dict(record,controlled=controlled_cloth_attribution(before,control),
                    normal_rebake_enclosure=enclosure,
                    normal_rebake_enclosure_pass=enclosure['maximum_escape_m']<=policy()['spacing_m'],
                    normal_rebake_appearance_findings=findings))
    (BASE/'cloth/final-comparison.json').write_text(json.dumps(rows,indent=2));return rows

def imports():
    first=read(BASE/'reference45/imports.json');second=read(BASE/'drafts52/imports.json')
    before={r['id']:r for r in first};after={r['id']:r for r in second};rows=[]
    if set(before)!=set(after):raise ValueError('Different model inventories')
    for ident,a in before.items():
        b=after[ident]
        counts=lambda r:[dict(name=m['name'],vertices=m['vertices'],faces=m['faces']) for m in r['meshes']]
        geometry=a.get('review_geometry') or {}
        error=float(np.max(np.abs(np.asarray(a['bounds'])-np.asarray(b['bounds']))))
        rows.append(dict(id=ident,status_before=a['status'],status_after=b['status'],mesh_counts_equal=counts(a)==counts(b),
             vertices=sum(m['vertices'] for m in a['meshes']),faces=sum(m['faces'] for m in a['meshes']),
             placement_sha256=a['placement_sha256'],placement_hash_equal=a['placement_sha256']==b['placement_sha256'],
             bound_source_sha256=geometry.get('source_sha256'),review_geometry_equal=geometry==(b.get('review_geometry') or {}),
             max_bounds_difference_mm=error*1000,import_transform_max_error_m_before=a['import_transform_max_error_m'],
             import_transform_max_error_m_after=b['import_transform_max_error_m']))
    (BASE/'import-placement-comparison.json').write_text(json.dumps(rows,indent=2))
    return rows

def lighting():
    before=read(BASE/'reference45/lighting-measurements.json');after=read(BASE/'drafts52/lighting-measurements.json');historic=read(ROOT/'knowledge/repro-lighting-baseline.json')
    old=indexed_tasks(historic['points']);ref=indexed_tasks(before['points']);candidate=indexed_tasks(after['points'])
    if set(ref)!=set(candidate) or set(ref)!=set(old):raise ValueError('Different task inventories')
    rows=[]
    for k,a in ref.items():
        b=candidate[k];h=old[k]
        r=dict(index=k[0],room=k[1],label=k[2],required_lux=a['required_lux'],positions_equal=a['position']==b['position'],
             measurement_positions_equal=a.get('measurement_position')==b.get('measurement_position'),
             before_pass=a['meets_target'],after_pass=b['meets_target'],historic_pass=h['meets_target'])
        for mode in ('direct','total'):
            x=a[mode+'_lux'];y=b[mode+'_lux'];z=h[mode+'_lux']
            r[mode]=dict(before_lux=x,after_lux=y,historic_lux=z,delta_lux=y-x,relative_percent=100*(y-x)/x if x else None,historic_delta_lux=y-z,historic_relative_percent=100*(y-z)/z if z else None)
        rows.append(r)
    result=dict(points=rows,same_authored_scene=before['scene_receipt']['authored_scene_sha256']==after['scene_receipt']['authored_scene_sha256'],
                historic_authored_scene_equal=historic['scene_receipt']['authored_scene_sha256']==after['scene_receipt']['authored_scene_sha256'],
                historic_note=historic.get('baseline_note'),all_targets_before=before['all_targets_met'],all_targets_after=after['all_targets_met'],
                samples=[before['samples'],after['samples']],maintenance_factor=after['maintenance_factor'])
    (BASE/'lighting-comparison.json').write_text(json.dumps(result,indent=2));return result

def main():
    result={}
    for folder in ['reference45','drafts52']:
        receipt=read(BASE/folder/'process.json')
        if receipt['exit_code'] or not receipt['runtime_sources_unchanged'] or not receipt['photometry_unchanged']:
            raise ValueError('Invalid process receipt: '+folder)
    result['imports']=imports();result['lighting']=lighting();result['cloth']=cloth()
    (BASE/'evidence-summary.json').write_text(json.dumps(result,indent=2))
if __name__=='__main__':main()
