"""Hash-bound cloth appearances; physical garments never change.

Coordinates are metres: x along the rail, y across wardrobe depth, z up.
SHA-256 is the content hash algorithm. All appearance choices are ASSUMED.
Only a measured, closed cached shell may replace a garment in the renderer.
"""
from __future__ import annotations
from copy import deepcopy
from functools import lru_cache
import gzip
import json
import math
from pathlib import Path
import numpy as np
from .imported_appearance import digest, encoded
from .concept.garments import bounds

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT/'knowledge/drape-appearance-policy.json'
CACHE_PATH = ROOT/'knowledge/drape-cloth-cache.json.gz'
GENERATOR_PATH = ROOT/'scripts/drape_cloth.py'


def policy():
    return json.loads(POLICY_PATH.read_text())


def eligible(part):
    return part.get('part_kind') in ('garment', 'folded-fabric')


def needs_admission(scene):
    return 'draped_appearances' in scene or any(eligible(p) or
        p.get('mesh_class')=='draped appearance mesh' for p in scene.get('meshes',[]))


def local_input(part):
    """Translation/name independent cache identity; no world-shape edits."""
    bb=bounds(part)
    origin=[(bb[0]+bb[3])/2,(bb[1]+bb[4])/2,bb[2]]
    faces=[[[round(p[k]-origin[k],7) for k in range(3)] for p in f] for f in part['faces']]
    data=dict(faces=faces,kind=part['part_kind'],garment_type=part.get('garment_type'),
              runtime=json.loads((ROOT/'knowledge/drape-runtime.json').read_text()),
              policy=policy(),generator_sha256=digest(GENERATOR_PATH.read_text()))
    return data,origin


@lru_cache(maxsize=2)
def _cache(data):
    return json.loads(gzip.decompress(data))


def measure(skin, boundary):
    """Independent morphology screens on the front skin, before thickening."""
    p=np.asarray(skin,dtype=float);lo=p[:,2].min();hi=p[:,2].max();height=hi-lo
    lower=p[p[:,2]<lo+.25*height];upper=p[p[:,2]>hi-.25*height]
    shift=np.linalg.norm(lower[:,:2].mean(0)-upper[:,:2].mean(0))
    angle=math.degrees(math.atan2(shift,upper[:,2].mean()-lower[:,2].mean()))
    band=p[np.abs(p[:,2]-(lo+hi)/2)<.010]
    relief=0.
    if len(band)>=6:
        across=band[:,1]-band[:,1].mean()
        design=np.column_stack((np.ones(len(band)),across,across**2))
        residual=band[:,0]-design@np.linalg.lstsq(design,band[:,0],rcond=None)[0]
        relief=float(np.ptp(residual))
    edge=p[np.asarray(boundary,dtype=int)];hem=edge[edge[:,2]<lo+.020,2]
    return dict(plumb_angle_deg=angle,fold_relief_m=relief,hem_range_m=float(np.ptp(hem)) if len(hem) else 0.)


def appearance_findings(row):
    if row.get('garment_type') is None:return []
    metrics=measure(row['skin_vertices'],row['boundary_indices']);rule=policy()
    out=[]
    for name,limit,minimum in (('plumb_angle_deg',rule['maximum_plumb_angle_deg'],False),
                               ('fold_relief_m',rule['minimum_fold_relief_m'],True),
                               ('hem_range_m',rule['minimum_hem_range_m'],True)):
        if (metrics[name]<limit if minimum else metrics[name]>limit):out.append(row['id']+': '+name+' fails ASSUMED appearance screen')
    return out


def frozen_appearance(part):
    """Read the real pre-fix front skin by value, never the current builder."""
    if part.get('garment_type')=='trousers':
        pts=np.unique(np.array([p for f in part['faces'] for p in f]),axis=0)
        cx=(pts[:,0].min()+pts[:,0].max())/2
        pts=pts[pts[:,0]>cx]
        return dict(part,skin_vertices=pts.tolist(),boundary_indices=list(range(len(pts))))
    first_edge=next(i for i,f in enumerate(part['faces']) if len(f)!=3)
    faces=part['faces'][:first_edge:2]
    pts=np.unique(np.array([p for f in faces for p in f]),axis=0)
    edges={}
    for face in faces:
        for a,b in zip(face,face[1:]+face[:1]):
            key=tuple(sorted((tuple(a),tuple(b))));edges[key]=edges.get(key,0)+1
    boundary={p for edge,n in edges.items() if n==1 for p in edge}
    return dict(part,skin_vertices=pts.tolist(),boundary_indices=[i for i,p in enumerate(pts) if tuple(p) in boundary])


def enclosure_measurement(appearance,part):
    """Exact containment in the physical part's tight measured box envelope.

    The envelope has the physical vertices' extrema; spacing is the sole
    permitted expansion. Every rendered face is linear and there are no
    geometry modifiers, so containing every vertex also contains every face.
    This does not assert that cloth lies inside the proxy solid's material.
    """
    points=np.asarray([p for f in appearance['faces'] for p in f])
    bb=bounds(part)
    escape=np.maximum(np.asarray(bb[:3])-points,points-np.asarray(bb[3:])).max()
    return dict(maximum_escape_m=max(0.,float(escape)),vertex_count=len(points),
                envelope='tight measured world-axis bounds of the physical part; no design enlargement')



@lru_cache(maxsize=32)
def _admit_template(input_bytes,template_bytes):
    """Validate every new cache value once; mutations invalidate admission."""
    from .concept.physical_part import geometry_errors
    data=json.loads(input_bytes);template=json.loads(template_bytes);key=digest(data)
    if template['input_sha256']!=key or template['mesh_sha256']!=digest(template['faces']):
        raise ValueError('corrupt cloth cache')
    errors=geometry_errors(template['faces'])
    if errors:raise ValueError('invalid closed appearance shell: '+str(errors))
    measurement=enclosure_measurement(template,dict(faces=data['faces']))
    if template['enclosure']!=measurement or measurement['maximum_escape_m']>policy()['spacing_m']:
        raise ValueError('stale or escaped enclosure measurement')
    proof=template.get('independent_process_sha256',[])
    if len(proof)!=2 or len(set(proof))!=1 or any(len(v)!=64 or any(c not in '0123456789abcdef' for c in v) for v in proof):
        raise ValueError('missing independent-process determinism proof')
    simulation=template['simulation']
    if data['kind']=='garment':
        for name,value in (('frames',data['policy']['frames']),('seed',data['policy']['seed']),
                           ('threads',1),('thickness_m',data['policy']['thickness_m']),
                           ('gravity',data['policy']['gravity_m_s2']),('blender',data['runtime']['blender_version'])):
            if simulation.get(name)!=value:raise ValueError('stale cloth simulation settings: '+name)
        row=dict(template,id=key,garment_type=data['garment_type'])
        errors=appearance_findings(row)
        if errors:raise ValueError('; '.join(errors))


def make(part, cache=None):
    data,origin=local_input(part);key=digest(data)
    cache=_cache(CACHE_PATH.read_bytes()) if cache is None else cache
    if cache.get('schema')!='drape-cloth-cache/1':raise ValueError('invalid drape cache schema')
    if key not in cache['entries']:raise ValueError(part['id']+': uncached cloth input; run scripts/drape_build.py')
    template=cache['entries'][key]
    _admit_template(encoded(data),encoded(template))
    row=dict(id=part['id'],mesh_class='draped appearance mesh',physical_part=False,
             standin_id=part['id'],standin_sha256=digest(part),input_sha256=key,
             template_sha256=digest(template),spacing_m=policy()['spacing_m'],
             material=part['material'],label='ASSUMED gravity-draped fabric and colour',
             garment_type=part.get('garment_type'),keep_object=True,bevel_m=0,subdivide=0,
             faces=[[[p[k]+origin[k] for k in range(3)] for p in f] for f in template['faces']],
             skin_vertices=[[p[k]+origin[k] for k in range(3)] for p in template['skin_vertices']],
             boundary_indices=list(template['boundary_indices']),simulation=deepcopy(template['simulation']),
             enclosure=deepcopy(template['enclosure']))
    row['appearance_sha256']=digest(row['faces'])
    return row


def bind_scene(scene):
    """Keep appearances outside the strictly admitted physical Parts list."""
    cache=_cache(CACHE_PATH.read_bytes())
    scene['draped_appearances']=[make(p,cache) for p in scene['meshes'] if eligible(p)]
    for name,mat in scene.get('materials',{}).items():
        if name.startswith('garment-'):
            mat.update(cloth_weave_m=.0007,roughness=.8,appearance_basis='ASSUMED colour, weave and sheen')
    scene['drape_policy_sha256']=digest(policy())
    scene['drape_preview_status']='PENDING lead neutral-preview acceptance; ASSUMED fabric/colours'
    return scene


def require_scene(scene):
    if any(p.get('mesh_class')=='draped appearance mesh' for p in scene['meshes']):
        raise ValueError('appearance cannot enter physical Parts')
    parts={p['id']:p for p in scene['meshes'] if eligible(p)}
    actual=scene.get('draped_appearances')
    if actual is None or len(actual)!=len(parts):raise ValueError('missing garment appearances')
    if scene.get('drape_policy_sha256')!=digest(policy()):raise ValueError('stale drape policy')
    cache=_cache(CACHE_PATH.read_bytes())
    seen=set()
    for row in actual:
        if row['id'] in seen:raise ValueError('duplicate drape binding')
        seen.add(row['id'])
        if row['id'] not in parts or digest(row)!=digest(make(parts[row['id']],cache)):
            raise ValueError('stale or unbound drape appearance: '+row['id'])
        if row['enclosure']['maximum_escape_m']>policy()['spacing_m']:
            raise ValueError('cloth outside physical envelope: '+row['id'])
        if appearance_findings(row):raise ValueError('; '.join(appearance_findings(row)))
    errors=collision_findings(scene,actual)
    if errors:raise ValueError('; '.join(errors))
    return actual


def rendered_meshes(scene):
    rows=require_scene(scene)
    replacements={r['id']:r for r in rows}
    return [replacements.get(p['id'],p) for p in scene['meshes']]


def collision_findings(scene, appearances=None):
    """Refuse even conservative shell-box contact with forbidden surfaces.

    Only its named physical support can contact a textile. Joinery component
    boxes are measured separately; an assembly box is not occupied material.
    Comparing conservative envelopes refuses some safe cases deliberately.
    One tenth of a micrometre is arithmetic precision, not design clearance.
    """
    from .concept.render_support import _triangle_faces, _tri_box_overlap
    appearances=scene['draped_appearances'] if appearances is None else appearances
    rows=scene['meshes'];physical={p['id']:p for p in rows}
    boxes=[bounds(p) for p in rows];lo=np.array([b[:3] for b in boxes]);hi=np.array([b[3:] for b in boxes])
    out=[]
    for row in appearances:
        part=physical[row['id']];box=bounds(row)
        low=np.array(box[:3]);high=np.array(box[3:])
        candidates=np.where(np.all(lo<=high+1e-7,axis=1)&np.all(hi>=low-1e-7,axis=1))[0]
        for i in candidates:
            other=rows[i]
            if other['id']==row['id']:continue
            supported=(other['id']==part.get('contents_support') or
                       other.get('contents_support')==row['id'])
            if supported:
                if eligible(other) and np.all(np.minimum(high,hi[i])-np.maximum(low,lo[i])>1e-7):
                    out.append(row['id']+': penetrates named textile support '+other['id'])
                continue
            # Conservative neighbour volume test detects enclosed appearance,
            # not just crossing faces. All eligible physical envelopes are
            # authoritative collision volumes, even if their skins are concave.
            if eligible(other) and np.all(np.minimum(high,hi[i])-np.maximum(low,lo[i])>=-1e-7):
                out.append(row['id']+': touches neighbour '+other['id']);continue
            triangles=_triangle_faces(other['faces'])
            if _tri_box_overlap(triangles,(low+high)/2,(high-low)/2+1e-7).any():
                out.append(row['id']+': touches joinery/door/obstacle '+other['id'])
    return sorted(set(out))
