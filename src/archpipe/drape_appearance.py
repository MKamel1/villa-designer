"""Hash-bound cloth appearances; physical garments never change.

Coordinates are metres: x along the rail, y across wardrobe depth, z up.
SHA-256 is the content hash algorithm. All appearance choices are ASSUMED.
Only a measured, closed cached shell may replace a garment in the renderer.
"""
from __future__ import annotations
from copy import deepcopy
from functools import lru_cache
import gzip
import hashlib
import inspect
import json
import math
from pathlib import Path
import numpy as np
from .imported_appearance import digest, encoded


def bounds(part):
    """Native-array extrema of actual live coordinates, without rounding."""
    if part.get('appearance_reference'):
        return list(part['render_bounds_m'])
    points=np.asarray([p for f in part['faces'] for p in f],dtype=float)
    return np.concatenate((points.min(0),points.max(0))).tolist()

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


def local_input(part, *, include_bounds=False):
    """Translation/name independent cache identity; no world-shape edits."""
    bb=bounds(part)
    origin=[(bb[0]+bb[3])/2,(bb[1]+bb[4])/2,bb[2]]
    faces=[[[round(p[k]-origin[k],7) for k in range(3)] for p in f] for f in part['faces']]
    data=dict(faces=faces,kind=part['part_kind'],garment_type=part.get('garment_type'),
              runtime=json.loads((ROOT/'knowledge/drape-runtime.json').read_text()),
              policy=policy(),generator_sha256=digest(GENERATOR_PATH.read_text()),
              dependencies_sha256=generator_dependencies())
    return (data,origin,bb) if include_bounds else (data,origin)


@lru_cache(maxsize=4)
def _dependency_hashes(source_bytes):
    from .scene_reproducibility import stable_seed
    from .concept.garments import rounded_ring,loft
    return {f.__name__:digest(inspect.getsource(f)) for f in (stable_seed,rounded_ring,loft)}


def generator_dependencies():
    """Bind actual imported pattern helpers, not unrelated module edits."""
    source_bytes=tuple(p.read_bytes() for p in (ROOT/'src/archpipe/scene_reproducibility.py',
        ROOT/'src/archpipe/concept/garments.py'))
    return dict(_dependency_hashes(source_bytes))


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
    process_value={k:v for k,v in template.items() if k not in ('independent_process_sha256','enclosure')}
    if proof != [digest(process_value)]*2:
        raise ValueError('independent-process proof is not bound to cached result')
    simulation=template['simulation']
    if data['kind']=='garment':
        for name,value in (('frames',data['policy']['frames']),('seed',data['policy']['seed']),
                           ('threads',1),('thickness_m',data['policy']['thickness_m']),
                           ('gravity',data['policy']['gravity_m_s2']),('blender',data['runtime']['blender_version'])):
            if simulation.get(name)!=value:raise ValueError('stale cloth simulation settings: '+name)
        row=dict(template,id=key,garment_type=data['garment_type'])
        errors=appearance_findings(row)
        if errors:raise ValueError('; '.join(errors))


@lru_cache(maxsize=32)
def _trusted_template(input_bytes, cache_bytes):
    """Reuse admission of exact immutable file bytes, never mutable records."""
    data=json.loads(input_bytes);key=digest(data);cache=_cache(cache_bytes)
    if cache.get('schema')!='drape-cloth-cache/1':raise ValueError('invalid drape cache schema')
    if key not in cache['entries']:raise ValueError('uncached cloth input; run scripts/drape_build.py')
    template=cache['entries'][key]
    _admit_template(input_bytes,encoded(template))
    # Keep face order while batching equal-arity runs for native-array
    # placement. This preserves exact values and avoids millions of Python
    # coordinate additions; mutable results are never returned from here.
    chunks=[];start=0;faces=template['faces']
    for i in range(1,len(faces)+1):
        if i==len(faces) or len(faces[i])!=len(faces[start]):
            chunk=np.asarray(faces[start:i],dtype=float);chunk.setflags(write=False)
            chunks.append(chunk);start=i
    skin=np.asarray(template['skin_vertices'],dtype=float);skin.setflags(write=False)
    return template,digest(template),chunks,skin


def _native_hash(lengths, arrays):
    """Bind face boundaries and exact little-endian 64-bit float values."""
    h=hashlib.sha256(b'archpipe-drape-faces/1\0')
    h.update(np.asarray(lengths,dtype='<u8').tobytes())
    for array in arrays:h.update(np.asarray(array,dtype='<f8').tobytes())
    return h.hexdigest()


@lru_cache(maxsize=256)
def _placed_hash(input_bytes,cache_bytes,origin):
    template,_,chunks,_=_trusted_template(input_bytes,cache_bytes)
    return _native_hash([len(f) for f in template['faces']],(chunk+origin for chunk in chunks))


@lru_cache(maxsize=32)
def _reference_geometry(input_bytes,cache_bytes):
    template,_,chunks,skin=_trusted_template(input_bytes,cache_bytes)
    low=np.min([chunk.min(axis=(0,1)) for chunk in chunks],axis=0)
    high=np.max([chunk.max(axis=(0,1)) for chunk in chunks],axis=0)
    return tuple(low),tuple(high)


def make_reference(part):
    """Compact render instance; physical and cached mesh values stay bound.

    Normal build admission measures template geometry once per exact input.
    Only renderer/evidence consumers expand world-coordinate face lists.
    A read-back reference must match all expected fields before its measured
    bounds can supply conservative collision screening.
    """
    data,origin,physical_bounds=local_input(part,include_bounds=True);input_bytes=encoded(data);cache_bytes=CACHE_PATH.read_bytes()
    template,template_hash,_,_=_trusted_template(input_bytes,cache_bytes)
    low,high=_reference_geometry(input_bytes,cache_bytes)
    render_bounds=[low[k]+origin[k] for k in range(3)]+[high[k]+origin[k] for k in range(3)]
    enclosure=_world_enclosure(template,render_bounds,physical_bounds)
    return dict(id=part['id'],mesh_class='draped appearance mesh',physical_part=False,
        appearance_reference=True,standin_id=part['id'],standin_sha256=digest(part),
        input_sha256=digest(data),template_sha256=template_hash,spacing_m=policy()['spacing_m'],
        material=part['material'],label='ASSUMED gravity-draped fabric and colour',
        garment_type=part.get('garment_type'),origin_m=origin,
        appearance_sha256=_placed_hash(input_bytes,cache_bytes,tuple(origin)),
        render_bounds_m=render_bounds,
        simulation=deepcopy(template['simulation']),enclosure=enclosure)


def _world_enclosure(template,render_bounds,physical_bounds):
    """Cache-key rounding never substitutes for actual physical extrema."""
    escape=max(0.,max(physical_bounds[k]-render_bounds[k] for k in range(3)),
        max(render_bounds[k+3]-physical_bounds[k+3] for k in range(3)))
    if escape>policy()['spacing_m']:raise ValueError('cloth outside actual physical envelope')
    return dict(template['enclosure'],maximum_escape_m=escape)


def make(part, cache=None):
    data,origin,physical_bounds=local_input(part,include_bounds=True);key=digest(data)
    if cache is None:
        input_bytes=encoded(data);cache_bytes=CACHE_PATH.read_bytes()
        template,template_hash,chunks,skin=_trusted_template(input_bytes,cache_bytes)
        placed_faces=[f for chunk in chunks for f in (chunk+origin).tolist()]
        placed_skin=(skin+origin).tolist()
        appearance_hash=_placed_hash(input_bytes,cache_bytes,tuple(origin))
    else:
        if cache.get('schema')!='drape-cloth-cache/1':raise ValueError('invalid drape cache schema')
        if key not in cache['entries']:raise ValueError(part['id']+': uncached cloth input; run scripts/drape_build.py')
        template=cache['entries'][key]
        _admit_template(encoded(data),encoded(template));template_hash=digest(template)
        placed_faces=[[[p[k]+origin[k] for k in range(3)] for p in f] for f in template['faces']]
        placed_skin=[[p[k]+origin[k] for k in range(3)] for p in template['skin_vertices']]
        appearance_hash=_native_hash([len(f) for f in placed_faces],
            [np.asarray([p for f in placed_faces for p in f],dtype=float)])
    row=dict(id=part['id'],mesh_class='draped appearance mesh',physical_part=False,
             standin_id=part['id'],standin_sha256=digest(part),input_sha256=key,
             template_sha256=template_hash,spacing_m=policy()['spacing_m'],
             material=part['material'],label='ASSUMED gravity-draped fabric and colour',
             garment_type=part.get('garment_type'),keep_object=True,bevel_m=0,subdivide=0,
             faces=placed_faces,skin_vertices=placed_skin,
             boundary_indices=list(template['boundary_indices']),simulation=deepcopy(template['simulation']),
             enclosure=deepcopy(template['enclosure']))
    row['appearance_sha256']=appearance_hash
    row['enclosure']=_world_enclosure(template,bounds(row),physical_bounds)
    return row


def bind_scene(scene):
    """Keep appearances outside the strictly admitted physical Parts list."""
    scene['draped_appearances']=[make_reference(p) for p in scene['meshes'] if eligible(p)]
    scene['drape_material_overrides']=_material_overrides(scene.get('materials',{}))
    scene['drape_policy_sha256']=digest(policy())
    scene['drape_preview_status']='PENDING lead neutral-preview acceptance; ASSUMED fabric/colours'
    return scene


def _material_overrides(materials):
    return {name:dict(cloth_weave_m=.0007,roughness=.8,
        appearance_basis='ASSUMED colour, weave and sheen') for name in materials if name.startswith('garment-')}


def render_materials(scene):
    """Render-only shader values; never mutate physical or shared materials."""
    if needs_admission(scene):require_scene(scene)
    materials=deepcopy(scene.get('materials',{}))
    for name,values in scene.get('drape_material_overrides',{}).items():materials[name].update(values)
    return materials


def require_scene(scene):
    if any(p.get('mesh_class')=='draped appearance mesh' for p in scene['meshes']):
        raise ValueError('appearance cannot enter physical Parts')
    parts={p['id']:p for p in scene['meshes'] if eligible(p)}
    actual=scene.get('draped_appearances')
    if actual is None or len(actual)!=len(parts):raise ValueError('missing garment appearances')
    if scene.get('drape_policy_sha256')!=digest(policy()):raise ValueError('stale drape policy')
    if scene.get('drape_material_overrides')!=_material_overrides(scene.get('materials',{})):
        raise ValueError('missing or stale garment appearance shader binding')
    seen=set()
    for row in actual:
        if row['id'] in seen:raise ValueError('duplicate drape binding')
        seen.add(row['id'])
        if row.get('appearance_reference'):
            if row['id'] not in parts or row!=make_reference(parts[row['id']]):
                raise ValueError('stale or unbound drape cache reference: '+row['id'])
            continue
        if not row.get('faces'):
            raise ValueError('missing drape geometry or cache reference: '+row['id'])
        live_hash=_native_hash([len(f) for f in row['faces']],
            [np.asarray([p for f in row['faces'] for p in f],dtype=float)])
        if row.get('appearance_sha256')!=live_hash:
            raise ValueError('changed rendered cloth geometry: '+row['id'])
        if row['id'] not in parts or row!=make(parts[row['id']]):
            raise ValueError('stale or unbound drape appearance: '+row['id'])
        if row['enclosure']['maximum_escape_m']>policy()['spacing_m']:
            raise ValueError('cloth outside physical envelope: '+row['id'])
        if appearance_findings(row):raise ValueError('; '.join(appearance_findings(row)))
    errors=collision_findings(scene,actual)
    if errors:raise ValueError('; '.join(errors))
    return actual


def rendered_meshes(scene):
    rows=require_scene(scene)
    physical={p['id']:p for p in scene['meshes']}
    replacements={r['id']:make(physical[r['id']]) if r.get('appearance_reference') else r for r in rows}
    return [replacements.get(p['id'],p) for p in scene['meshes']]


def _occupied_centre(faces, centre):
    """Signed surface angles distinguish solid material from internal air.

    Each oriented polygon fan contributes its signed angle at the centre.
    Overlapping fan triangles cancel on concave/keyhole faces. A closed
    outward solid surrounds an interior point by four pi radians, and an
    exterior point by zero; pi is the circle circumference/diameter ratio.
    Half that total separates these states. Surface crossing is screened
    before this function, so a centre on a face never reaches this query.
    Ray parity with deduplicated unsigned hits loses that cancellation on
    multi-component joinery and misclassified the frozen real air cavities.
    """
    triangles=np.asarray([(f[0],f[i],f[i+1]) for f in faces for i in range(1,len(f)-1)],dtype=float)-centre
    a,b,c=triangles[:,0],triangles[:,1],triangles[:,2]
    lengths=[np.linalg.norm(v,axis=1) for v in (a,b,c)]
    numerator=np.einsum('ij,ij->i',a,np.cross(b,c))
    denominator=(lengths[0]*lengths[1]*lengths[2]+
        np.einsum('ij,ij->i',a,b)*lengths[2]+
        np.einsum('ij,ij->i',b,c)*lengths[0]+
        np.einsum('ij,ij->i',c,a)*lengths[1])
    return abs(math.fsum(2*np.arctan2(numerator,denominator)))>2*math.pi


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
    rendered_bounds={p['id']:bounds(p) for p in scene.get('draped_appearances',[])}
    rendered_bounds.update({p['id']:bounds(p) for p in appearances})
    boxes=[]
    for p in rows:
        box=bounds(p)
        if eligible(p) and p['id'] in rendered_bounds:
            rendered=rendered_bounds[p['id']]
            # Both physical clearance volumes and actual neighbouring cloth
            # remain authoritative. Two allowed expansions may meet in a
            # gap while neither touches the other's physical body.
            box=[min(box[k],rendered[k]) for k in range(3)]+[
                max(box[k+3],rendered[k+3]) for k in range(3)]
        boxes.append(box)
    lo=np.array([b[:3] for b in boxes]);hi=np.array([b[3:] for b in boxes])
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
            elif np.all(low>lo[i]+1e-7) and np.all(high<hi[i]-1e-7):
                # A shell wholly enclosed by a solid crosses none of its
                # faces. The signed closed-solid angle test distinguishes
                # occupied joinery from a wardrobe's internal air cavity.
                if _occupied_centre(other['faces'],(low+high)/2):
                    out.append(row['id']+': enclosed by joinery/door/obstacle '+other['id'])
    return sorted(set(out))
