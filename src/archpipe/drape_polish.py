"""Owned, ASSUMED tailoring over intact cached gravity cloth.

Coordinates are metres: local x is front-to-back, y across shoulders, z up.
The source cache is never rewritten. Numerical screens establish construction,
not photographic realism. Policy dimensions were registered before measurement.
"""
from copy import deepcopy
from functools import lru_cache
import gzip
import json
import math
from pathlib import Path
import random
import numpy as np
from .imported_appearance import digest, encoded
from .scene_reproducibility import stable_seed, signed_volume

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT/'knowledge/drape-polish-policy.json'
CACHE_PATH = ROOT/'knowledge/drape-polish-cache.json.gz'


def policy():
    return json.loads(POLICY_PATH.read_text())


def binding(part):
    """Eight bounded fold variants avoid identical adjacent cache instances."""
    rule=policy()
    variant=stable_seed(dict(seed=rule['seed'],item=part['id']))%8 if part['part_kind']=='folded-fabric' else 0
    return encoded(dict(policy=rule,source_sha256=digest(Path(__file__).read_text()),variant=variant))


def _points(faces):
    return np.asarray([p for f in faces for p in f],dtype=float)


def _sheet(vertices, polygons, thickness):
    """Close a tailored sheet around averaged normals; retain each cut edge."""
    v=np.asarray(vertices,dtype=float);normals=np.zeros_like(v);edges={}
    for f in polygons:
        normal=np.cross(v[f[1]]-v[f[0]],v[f[2]]-v[f[0]])
        for i in f:normals[i]+=normal
        for a,b in zip(f,f[1:]+f[:1]):
            key=tuple(sorted((a,b)))
            if key in edges:edges[key]=None
            else:edges[key]=(a,b)
    lengths=np.linalg.norm(normals,axis=1)
    normals[lengths>0]/=lengths[lengths>0,None]
    front=v+normals*thickness/2;back=v-normals*thickness/2
    out=[[front[i].tolist() for i in f] for f in polygons]
    out += [[back[i].tolist() for i in reversed(f)] for f in polygons]
    out += [[front[a].tolist(),back[a].tolist(),back[b].tolist(),front[b].tolist()]
            for edge in edges.values() if edge is not None for a,b in [edge]]
    if signed_volume(out)<0:out=[f[::-1] for f in out]
    return out


def _patch(corners, thickness, roll=.0015, steps=8, attach=None):
    vertices=[];polys=[]
    for i in range(steps+1):
        u=i/steps
        for j in range(steps+1):
            v=j/steps
            q=[(1-u)*((1-v)*corners[0][k]+v*corners[1][k])+
               u*((1-v)*corners[3][k]+v*corners[2][k]) for k in range(3)]
            if attach is not None:
                surface=attach(q[1:])
                if surface is not None:q[0]=surface+.001
            q[0]+=roll*math.sin(math.pi*v)
            vertices.append(q)
    for i in range(steps):
        for j in range(steps):
            a=i*(steps+1)+j;polys.append([a,a+1,a+steps+2,a+steps+1])
    return _sheet(vertices,polys,thickness)


def _front_sampler(faces):
    """Interpolate exterior x on actual triangles projected onto y/z.

    Barycentric weights are the fractions of the triangle's three corners.
    Multiple projected hits use the greatest x, which is the front exterior.
    No hit means the tailoring lies outside the body cut, e.g. at its neck.
    """
    triangles=np.asarray([[f[0],f[i],f[i+1]] for f in faces for i in range(1,len(f)-1)])
    a=triangles[:,0];b=triangles[:,1]-a;c=triangles[:,2]-a
    determinant=b[:,1]*c[:,2]-b[:,2]*c[:,1]
    usable=abs(determinant)>1e-12
    a,b,c,determinant=a[usable],b[usable],c[usable],determinant[usable]
    def sample(yz):
        y,z=(np.asarray(yz)-a[:,1:]).T
        u=(y*c[:,2]-z*c[:,1])/determinant
        v=(b[:,1]*z-b[:,2]*y)/determinant
        inside=(u>=-1e-8)&(v>=-1e-8)&(u+v<=1+1e-8)
        if not inside.any():return None
        return float((a[:,0]+u*b[:,0]+v*c[:,0])[inside].max())
    return sample


def _centre_x(point):
    # Retain central relaxed wrinkles while reducing unsupported lateral hem
    # swing in the sewn, air-filled pattern. This is a continuous rest-shape
    # rule for every top, not an envelope clamp.
    return point[0]*(.65-.25*(abs(point[1])/.265)**2)


def _half_depth(point, top, height, typ, rule):
    fraction=max(0,min(1,(top-point[2])/height))
    target=rule[typ+'_half_air_depth_m']
    transverse=1-.35*(abs(point[1])/.27)**2
    return (rule['shoulder_half_air_depth_m']+(target-rule['shoulder_half_air_depth_m'])*
            math.sin(math.pi*fraction)**.65)*transverse


def _tailor(data, template, rule):
    typ=data['garment_type'];skin=np.asarray(template['skin_vertices']);top=skin[:,2].max();height=np.ptp(skin[:,2])
    # The old generator appended two 12-by-12 turned patches, 336 faces each.
    # Verify their actual closed topology at admission before replacing them.
    shell=template['faces'][:-672]
    points=np.unique(_points(shell),axis=0)
    # Solidify moves each source vertex at most half the 0.8 mm thickness.
    # A small spatial index recovers the relaxed midsurface, independently of
    # face order; no world coordinates or appearance output are clamped.
    cell=.002;grid={}
    for i,p in enumerate(skin):grid.setdefault(tuple(np.floor(p[1:]/cell).astype(int)),[]).append(i)
    offsets=[(a,b) for a in (-1,0,1) for b in (-1,0,1)]
    nearest_indices={}
    for p in points:
        key=np.floor(p[1:]/cell).astype(int)
        candidates=[i for a,b in offsets for i in grid.get((key[0]+a,key[1]+b),[])]
        if not candidates:raise ValueError('cached shell is not adjacent to its relaxed midsurface')
        nearest_indices[tuple(p)]=min(candidates,key=lambda i:float(np.sum((skin[i,1:]-p[1:])**2)))
    # Recover the actual relaxed panel cells from the cache's closed 0.8 mm
    # fabric, deduplicating the two thickness surfaces. This keeps its cut,
    # wrinkles and front opening without rerunning or rewriting simulation.
    front={};back={}
    for f in shell:
        ids=list(dict.fromkeys(nearest_indices[tuple(p)] for p in f))
        if len(ids)<3:continue
        signs=[p[0]-skin[nearest_indices[tuple(p)],0] for p in f]
        if min(signs)>0:front.setdefault(tuple(sorted(ids)),ids)
        elif max(signs)<0:back.setdefault(tuple(sorted(ids)),ids)
    # The cached source lists consistently wound front/back cells before
    # solidification. Preserve that winding even where a relaxed fold turns
    # its local normal away from x; per-face normal flipping tears the seams.
    full=[ids[::-1] for ids in back.values()]
    n=len(skin)
    vertices=[[_centre_x(p)+side*_half_depth(p,top,height,typ,rule),p[1],p[2]]
              for side in (1,-1) for p in skin]
    polygons=list(front.values())+[[i+n for i in ids] for ids in back.values()]
    counts={};directions={}
    for f in full:
        for a,b in zip(f,f[1:]+f[:1]):
            key=tuple(sorted((a,b)));counts[key]=counts.get(key,0)+1;directions[key]=(a,b)
    sewn=[];inward=np.zeros_like(skin)
    sleeve_drop=.39 if typ=='jacket' else .31
    for edge,count in counts.items():
        if count!=1:continue
        a,b=directions[edge];middle=(skin[a]+skin[b])/2
        hem=middle[2]<.035
        neck=middle[2]>top-.095 and abs(middle[1])<.12
        cuff=abs(middle[1])>.18 and middle[2]<top-sleeve_drop+.045
        if hem or neck or cuff:continue
        sewn.append((a,b))
        tangent=skin[b,1:]-skin[a,1:]
        normal=np.array([-tangent[1],tangent[0]])/np.linalg.norm(tangent)
        inward[a,1:]+=normal;inward[b,1:]+=normal
    indices={}
    def rolled(i,step):
        if step==0:return i
        if step==8:return i+n
        key=(i,step)
        if key not in indices:
            t=step/8;p=skin[i];normal=inward[i,1:]/np.linalg.norm(inward[i,1:])
            indices[key]=len(vertices)
            vertices.append([_centre_x(p)+math.cos(math.pi*t)*_half_depth(p,top,height,typ,rule),
                             p[1]+normal[0]*.008*math.sin(math.pi*t),
                             p[2]+normal[1]*.008*math.sin(math.pi*t)])
        return indices[key]
    sections=[]
    for a,b in sewn:
        first=len(polygons)
        for step in range(8):polygons.append([rolled(b,step),rolled(a,step),rolled(a,step+1),rolled(b,step+1)])
        if min(skin[a,2],skin[b,2])>top-.080:sections.append(list(range(first,len(polygons))))
    faces=_sheet(vertices,polygons,data['policy']['thickness_m'])
    template['body_front_faces']=[0,len(front)]
    template['shoulder_return_sections']=sections
    sample_front=_front_sampler(faces[:len(front)])
    features={}
    def add(name,patch):
        start=len(faces);faces.extend(patch);features[name]=[start,len(faces)]
    thickness=data['policy']['thickness_m']
    # Horseshoe collar stand rises separately from the turned fall. Front
    # tips remain open; the back neck wraps around the two body panels.
    vertices=[];polys=[];steps=24
    for level in (0,1):
        for i in range(steps+1):
            angle=math.pi*.25+math.pi*1.5*i/steps
            vertices.append([.019*math.cos(angle),.057*math.sin(angle),top-.043+level*.018])
    for i in range(steps):polys.append([i,i+1,i+steps+2,i+steps+1])
    add('collar_stand',_sheet(vertices,polys,thickness))
    # Distinct rear fall and two front points, attached at the stand's upper
    # edge. Shirt points are shorter; jacket fall meets notched lapels.
    vertices=[];polys=[]
    for level in (0,1):
        for i in range(steps+1):
            angle=math.pi*.25+math.pi*1.5*i/steps
            vertices.append([(.019+level*.005)*math.cos(angle),(.057+level*.020)*math.sin(angle),top-.025-level*.033])
    for i in range(steps):polys.append([i,i+1,i+steps+2,i+steps+1])
    add('collar_fall',_sheet(vertices,polys,thickness))
    for side in (-1,1):
        corners=[[.014,side*.040,top-.025],[.017,side*.077,top-.058],
                 [.026,side*.050,top-.098],[.024,side*.021,top-.069]]
        add('collar_point_'+str(side),_patch(corners,thickness,roll=.001,attach=sample_front))
        if typ=='jacket':
            # A notch separates collar and lapel; the broad lapel rolls down
            # to the front opening instead of one long triangular neck flap.
            corners=[[.027,side*.024,top-.072],[.027,side*.082,top-.091],
                     [.027,side*.099,top-.135],[.027,side*.013,top-.270]]
            add('lapel_'+str(side),_patch(corners,thickness,roll=.001,attach=sample_front))
    # A separate narrow front band follows the relaxed panel rather than
    # drawing a straight line through folds. The opening stays in the cut.
    vertices=[];polys=[];steps=36
    for i in range(steps+1):
        z=top-.090-(height-.115)*i/steps
        for y in (.002,.018):
            near=skin[np.argmin(np.sum((skin[:,1:]-[y,z])**2,axis=1))]
            surface=sample_front([y,z])
            x=surface+.001 if surface is not None else _centre_x(near)+_half_depth([0,y,z],top,height,typ,rule)+.001
            vertices.append([x,y,z])
    for i in range(steps):a=2*i;polys.append([a,a+1,a+3,a+2])
    add('placket',_sheet(vertices,polys,thickness))
    # Small buttons are bounded closed cylinders, not shader dots.
    from .concept.garments import loft
    for z in np.arange(top-(.30 if typ=='jacket' else .14),top-height+.05,-.09):
        near=skin[np.argmin(np.sum((skin[:,1:]-[.010,z])**2,axis=1))]
        x=_centre_x(near)+_half_depth([0,.010,z],top,height,typ,rule)+.0015
        rings=[[[xx,.010+.002*math.cos(a),z+.002*math.sin(a)] for a in np.arange(10)*math.tau/10]
               for xx in (x,x+.0012)]
        button=loft(rings)
        if signed_volume(button)<0:button=[f[::-1] for f in button]
        faces.extend(button)
    template['faces']=faces
    template['skin_vertices']=[[_centre_x(p),p[1],p[2]] for p in skin]
    template['tailoring_features']=features


def _fold(data, template, rule, variant):
    from .concept.garments import rounded_ring,loft
    rng=random.Random(stable_seed(dict(input=data,seed=rule['seed'],variant=variant)))
    source=_points(data['faces']);low=source.min(0);high=source.max(0);w,d,h=high-low
    limits=[min(rule['fold_offset_maximum_m'],.02*dimension) for dimension in (w,d)]
    dx,dy=[rng.choice((-1,1))*rng.uniform(.4*limit,limit) for limit in limits]
    phase=rng.uniform(-math.pi,math.pi)
    turn_limit=min(.008,.02*min(w/d,d/w));turn=rng.uniform(-turn_limit,turn_limit)
    rings=[]
    for i in range(25):
        t=i/24;scale=.90+.065*math.sin(math.pi*t)**.5
        ring=rounded_ring(0,0,w*scale,d*scale,h*t,min(h*.25,w*.12,d*.12))
        for p in ring:
            x,y=p[:2]
            # Only the front has doubled free hems; the rear is a continuous
            # rolled fold. A perimeter-wide waist incorrectly resembles the
            # seam on an upholstered pad. This front-only indentation leaves
            # the back folded nose smooth and preserves every outer envelope.
            front_weight=((1-y/(d*scale/2))/2)**4
            y+=.0055*math.exp(-((t-.52)/.075)**2)*front_weight
            a=turn*t
            p[0]=x*math.cos(a)-y*math.sin(a)+dx*t
            p[1]=x*math.sin(a)+y*math.cos(a)+dy*t
            p[2]+=.0011*math.sin(x*47+y*31+phase)*math.sin(math.pi*t)
        rings.append(ring)
    faces=loft(rings)
    # Replace the planar top cap with supported concentric fabric rings.
    # Boundary vertices are shared exactly; only the interior sags downward.
    faces.pop(1)  # loft stores bottom and top caps before the side faces
    top_start=len(faces)
    boundary=rings[-1];previous=boundary;top_points=list(boundary)
    for shrink in (.75,.50,.25):
        ring=[]
        for p in boundary:
            x=dx+(p[0]-dx)*shrink;y=dy+(p[1]-dy)*shrink
            sag=rule['fold_sag_m']*(1-shrink**2)*(1+.25*math.sin(x*43+y*29+phase))
            # A restrained diagonal crease interrupts the pillow-like cap;
            # it vanishes at the supported outer edge. All sag is downward.
            sag+=.0015*math.exp(-((x/w+.12+.20*y/d)/.09)**2)*(1-shrink)
            ring.append([x,y,h-sag])
        for i in range(len(ring)):
            j=(i+1)%len(ring);faces.append([previous[i],previous[j],ring[j],ring[i]])
        top_points.extend(ring);previous=ring
    centre=[dx,dy,h-rule['fold_sag_m']*(1+.25*math.sin(phase))]
    for i in range(len(previous)):faces.append([previous[i],previous[(i+1)%len(previous)],centre])
    if signed_volume(faces)<0:faces=[f[::-1] for f in faces]
    template['fold_top_faces']=[top_start,len(faces)]
    # A separate turned thin front hem exposes a cut fabric edge. The top
    # pad's scalar sag and groove cannot express this doubled free edge.
    vertices=[];polygons=[];columns=12
    path=[(-.38*d,h-.0015),(-.43*d,h-.0007),(-.46*d,h-.0007),
          (-.48*d,h-.0013),(-.485*d,h-.0025),(-.48*d,h-.0045),(-.46*d,h-.0055)]
    for y,z in path:
        for i in range(columns+1):
            u=i/columns
            vertices.append([(u-.5)*w*.86+dx,y+dy,z-.0006*math.sin(math.pi*u)**2])
    for j in range(len(path)-1):
        for i in range(columns):
            a=j*(columns+1)+i;polygons.append([a,a+1,a+columns+2,a+columns+1])
    hem=_sheet(vertices,polygons,data['policy']['thickness_m'])
    template['fold_hem_faces']=[len(faces),len(faces)+len(hem)];faces.extend(hem)
    template['faces']=faces


def metrics(row):
    """Measure actual body surfaces and bound tailoring feature face ranges."""
    faces=row['faces'];p=_points(faces);typ=row.get('garment_type');out={}
    if typ in ('shirt','jacket'):
        skin=np.asarray(row['skin_vertices']);top=skin[:,2].max();height=np.ptp(skin[:,2]);cy=(skin[:,1].min()+skin[:,1].max())/2
        for name,a,b in (('torso_depth_m',.35,.60),('shoulder_depth_m',.10,.22)):
            band=p[(p[:,2]>top-b*height)&(p[:,2]<top-a*height)&(abs(p[:,1]-cy)<.10)]
            out[name]=float(np.quantile(band[:,0],.95)-np.quantile(band[:,0],.05)) if len(band) else 0.
        for name,axis in (('collar_stand',2),('collar_fall',2),('placket',1),('lapel_-1',1),('lapel_1',1)):
            span=row.get('tailoring_features',{}).get(name,[0,0]);feature=_points(faces[span[0]:span[1]])
            out[name+'_extent_m']=float(np.ptp(feature[:,axis])) if len(feature) else 0.
        curves=[]
        for section in row.get('shoulder_return_sections',[]):
            strips=[faces[i] for i in section]
            q=np.asarray([f[1] for f in strips]+[strips[-1][2]])
            chord=np.linspace(q[0,1:],q[-1,1:],len(q))
            curves.append(float(np.linalg.norm(q[:,1:]-chord,axis=1).max()))
        out['shoulder_return_curvature_m']=min(curves) if curves else 0.
        span=row.get('body_front_faces',[0,0]);body=faces[span[0]:span[1]]
        gaps=[]
        if body:
            sample=_front_sampler(body)
            for name,span in row.get('tailoring_features',{}).items():
                if not name.startswith(('lapel_','collar_point_')):continue
                # The first half of a feature comprises the outward surface;
                # omit its closed reverse skin and cut-edge caps.
                feature=faces[span[0]:span[1]]
                # Main quad patch has 8 by 8 outward faces.
                for f in feature[:64]:
                    centre=np.asarray(f).mean(0);surface=sample(centre[1:])
                    if surface is not None:gaps.append(centre[0]-surface)
        out['tailoring_exterior_offset_m']=min(gaps) if gaps else -1.
    elif typ is None:
        span=row.get('fold_top_faces',[0,0]);top=_points(faces[span[0]:span[1]])
        span=row.get('fold_hem_faces',[0,0]);hem=_points(faces[span[0]:span[1]])
        out['fold_hem_return_height_m']=float(np.ptp(hem[:,2])) if len(hem) else 0.
        out['fold_hem_return_depth_m']=float(np.ptp(hem[:,1])) if len(hem) else 0.
        out['fold_top_relief_m']=0.;out['fold_centroid_drift_m']=0.;out['fold_edge_contrast_m']=0.
        if len(top):
            design=np.column_stack((np.ones(len(top)),top[:,:2]-top[:,:2].mean(0)))
            out['fold_top_relief_m']=float(np.ptp(top[:,2]-design@np.linalg.lstsq(design,top[:,2],rcond=None)[0]))
        bottom=np.unique(p[np.abs(p[:,2]-p[:,2].min())<1e-8],axis=0)
        upper=np.unique(p[np.abs(p[:,2]-p[:,2].max())<1e-8],axis=0)
        if len(bottom) and len(upper):
            out['fold_centroid_drift_m']=float(np.linalg.norm(upper[:,:2].mean(0)-bottom[:,:2].mean(0)))
        low=p[:,2].min();height=np.ptp(p[:,2])
        bands=[p[(p[:,2]>=low+a*height)&(p[:,2]<=low+b*height)] for a,b in ((.32,.43),(.46,.56),(.58,.69))]
        if all(len(b) for b in bands):
            lower,middle,upper=bands
            front_inset=middle[:,1].min()-(lower[:,1].min()+upper[:,1].min())/2
            back_inset=(lower[:,1].max()+upper[:,1].max())/2-middle[:,1].max()
            out['fold_edge_contrast_m']=float(front_inset-back_inset)

    return out


def findings(row):
    rule=policy();typ=row.get('garment_type');m=metrics(row);out=[]
    requirements=[]
    if typ in ('shirt','jacket'):
        requirements=[('torso_depth_m','minimum_torso_depth_m'),('shoulder_depth_m','minimum_shoulder_depth_m'),
                      ('collar_stand_extent_m','minimum_collar_stand_height_m'),('collar_fall_extent_m','minimum_collar_fall_height_m'),
                      ('placket_extent_m','minimum_placket_width_m'),
                      ('shoulder_return_curvature_m','minimum_shoulder_return_curvature_m'),
                      ('tailoring_exterior_offset_m','minimum_tailoring_exterior_offset_m')]
        if typ=='jacket':requirements += [(name+'_extent_m','minimum_lapel_width_m') for name in ('lapel_-1','lapel_1')]
    elif typ is None:
        requirements=[('fold_top_relief_m','minimum_fold_top_relief_m'),('fold_centroid_drift_m','minimum_fold_centroid_drift_m'),('fold_edge_contrast_m','minimum_fold_edge_contrast_m'),
                      ('fold_hem_return_height_m','minimum_fold_hem_return_height_m'),('fold_hem_return_depth_m','minimum_fold_hem_return_depth_m')]
    for name,limit in requirements:
        if m[name]<rule[limit]:out.append(name+' fails ASSUMED polish screen')
    return out


def apply(data, original, binding_bytes):
    """Build a separate closed appearance; never mutate the cloth cache."""
    value=json.loads(binding_bytes);rule=value['policy'];typ=data['garment_type']
    if typ not in ('shirt','jacket') and data['kind']!='folded-fabric':return original
    template=deepcopy(original)
    if data['kind']=='folded-fabric':_fold(data,template,rule,value['variant'])
    else:_tailor(data,template,rule)
    raw=_points(original['faces'])
    template['source_enclosure_bounds_m']=np.concatenate((raw.min(0),raw.max(0))).tolist()
    template['polish']=value
    template['mesh_sha256']=digest(template['faces'])
    from .concept.physical_part import geometry_errors
    from .drape_appearance import enclosure_measurement,appearance_findings
    errors=geometry_errors(template['faces'])+findings(dict(template,garment_type=typ))
    if typ:errors+=appearance_findings(dict(template,id='polish',garment_type=typ))
    template['enclosure']=enclosure_measurement(template,dict(faces=data['faces']))
    if template['enclosure']['maximum_escape_m']>rule['maximum_envelope_escape_m']:
        errors.append('polish conflicts with exact physical envelope: '+str(template['enclosure']['maximum_escape_m'])+' m')
    if errors:raise ValueError('; '.join(errors))
    return template


def hanging_gaps(parts, appearances):
    """Conservative x-envelope gaps between hanging items sharing a rail.

    A garment names its hanger, which names the unchanged rail. Values are
    metres. Separate rails and shelf stacks are not hanging neighbours.
    """
    from .drape_appearance import bounds
    by={p['id']:p for p in parts};groups={}
    for row in appearances:
        physical=by.get(row['id'],{})
        if physical.get('part_kind')!='garment':continue
        hanger=by.get(physical.get('contents_support'),{})
        rail=hanger.get('contents_support')
        if rail is not None:groups.setdefault(rail,[]).append(row)
    results=[]
    for rows in groups.values():
        ordered=sorted(((bounds(p),p['id']) for p in rows),key=lambda q:q[0][0])
        for (a,aid),(b,bid) in zip(ordered,ordered[1:]):
            results.append(dict(first=aid,second=bid,gap_m=b[0]-a[3]))
    return results


def gap_findings(parts, appearances):
    minimum=policy()['minimum_hanging_gap_m']
    return [r['first']+': hanging neighbour gap '+str(r['gap_m'])+' m below ASSUMED '+str(minimum)+' m'
            for r in hanging_gaps(parts,appearances) if r['gap_m']<minimum]


def cache_input(data, original, binding_bytes):
    return dict(base_input_sha256=digest(data),base_template_sha256=digest(original),polish=json.loads(binding_bytes))


@lru_cache(maxsize=2)
def _cache(raw):
    return json.loads(gzip.decompress(raw))


@lru_cache(maxsize=128)
def _admit(entry_bytes, input_bytes):
    from .concept.physical_part import geometry_errors
    from .drape_appearance import enclosure_measurement, appearance_findings
    entry=json.loads(entry_bytes);data=json.loads(input_bytes);template=entry['template']
    if entry['process_sha256'] != [digest(template)]*2:
        raise ValueError('unbound polish independent-process proof')
    if template['mesh_sha256']!=digest(template['faces']):raise ValueError('corrupt polished mesh')
    errors=geometry_errors(template['faces'])+findings(dict(template,garment_type=data['garment_type']))
    if data['garment_type']:errors+=appearance_findings(dict(template,id='cached polish',garment_type=data['garment_type']))
    measured=enclosure_measurement(template,dict(faces=data['faces']))
    if measured!=template['enclosure'] or measured['maximum_escape_m']>policy()['maximum_envelope_escape_m']:
        errors.append('cached polish conflicts with exact physical envelope')
    if errors:raise ValueError('; '.join(errors))


def cached(data, original, binding_bytes, cache_bytes):
    """Read exact portable construction output; never regenerate in Blender.

    Normal recomputation differed at 33 coordinates by approximately one
    quintillionth of a metre between the two NumPy runtimes. Hash identity
    must bind one stored mesh, including those least significant bits.
    """
    if data['garment_type'] not in ('shirt','jacket') and data['kind']!='folded-fabric':return original
    value=cache_input(data,original,binding_bytes);key=digest(value)
    cache=_cache(cache_bytes)
    if cache.get('schema')!='drape-polish-cache/1' or key not in cache['entries']:
        raise ValueError('uncached garment polish; run scripts/drape_polish_build.py')
    entry=cache['entries'][key]
    if entry['input']!=value:raise ValueError('stale polish input binding')
    template=entry['template']
    raw=_points(original['faces'])
    source_bounds=np.concatenate((raw.min(0),raw.max(0))).tolist()
    if template.get('source_enclosure_bounds_m')!=source_bounds or template.get('polish')!=value['polish']:
        raise ValueError('unbound polish source enclosure or construction')
    _admit(encoded(entry),encoded(data))
    return template


def cache_binding(part):
    # Include the actual derived file bytes in the caller's value-keyed cache.
    # Editing/replacing a file cannot reuse prior mutable-object admission.
    return binding(part),CACHE_PATH.read_bytes()
