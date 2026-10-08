"""Balcony-suspended retreat. Coordinates/metres: x/y plot plane, z upward.

Local +y is the basket front; yaw is counterclockwise about +z in degrees.
All dimensions are authored appearance assumptions, never load certification.
"""
from math import cos, sin, pi, radians, atan2, degrees, hypot
from copy import deepcopy
import numpy as np

DECISION = 'client decision 2026-10-06; structural check pending'
OPEN = [dict(item='Balcony slab capacity for dynamic hanging point load', status='UNVERIFIED', owner='structural engineer'),
        dict(item='Anchor type and installation', status='UNVERIFIED', owner='structural engineer'),
        dict(item='Chair rated load', status='UNVERIFIED', owner='manufacturer')]


def design():
    return dict(id='landscape-north-swing', center=[2.40,-24.77], yaw_deg=90.,
                width_m=1.20, depth_m=1.00, height_m=1.20, ground_m=-3.,
                seat_height_m=.45, basket_bottom_m=-3.+.45-.30, soffit_m=-.2,
                eye_height_m=1.20, motion_allowance_m=.25, decision=DECISION,
                source='original project-authored procedural basket; no imported geometry',
                licence='Original project geometry; no third-party mesh licence applies; no standalone redistribution grant declared',
                appearance='ASSUMED look-alike-proxy, no manufacturer identity',
                size_basis='Comparable to measured sf_egg_chair basket 1.216 x 1.068 x 1.193 m; no stand',
                seat_basis='ASSUMED 0.45 m for feet near ground and relaxed sitting; not a cited standard',
                eye_basis='ASSUMED eye 1.20 m above court, 0.75 m above seat, for a seated adult screen',
                open_construction_items=deepcopy(OPEN))


def build(record=None):
    """Closed round cane members, open egg cage, soft seat/back, rope and plate."""
    d=deepcopy(record or design());cx,cy=d['center'];yaw=radians(d['yaw_deg'])
    d['suspension_length_m']=d['soffit_m']-(d['basket_bottom_m']+d['height_m'])
    bottom=d['basket_bottom_m'];width=d['width_m'];depth=d['depth_m'];height=d['height_m']
    def world(p):
        x,y,z=p;return [cx+x*cos(yaw)-y*sin(yaw),cy+x*sin(yaw)+y*cos(yaw),bottom+z]
    def tube(path,r=.009):
        faces=[];rings=[]
        for i,p in enumerate(path):
            axis=np.array(path[min(i+1,len(path)-1)])-np.array(path[max(i-1,0)])
            axis/=np.linalg.norm(axis);helper=np.array([0.,0.,1.]) if abs(axis[2])<.9 else np.array([1.,0.,0.])
            u=np.cross(axis,helper);u/=np.linalg.norm(u);v=np.cross(axis,u)
            rings.append([(np.array(p)+r*(u*cos(k*pi/4)+v*sin(k*pi/4))).tolist() for k in range(8)])
        faces.extend([rings[0][::-1],rings[-1]])
        faces.extend([[a[k],a[(k+1)%8],b[(k+1)%8],b[k]] for a,b in zip(rings,rings[1:]) for k in range(8)])
        return faces
    def shellpoint(theta,phi):
        return [width/2*sin(theta)*cos(phi),depth/2*sin(theta)*sin(phi),height/2*(1+cos(theta))]
    cage=[]
    # Back hemisphere and the oval opening rim: every rib joins both poles.
    for j in range(19):
        phi=pi+pi*j/18
        cage+=tube([shellpoint(pi*i/36,phi) for i in range(37)])
    for i in range(1,18):
        theta=pi*i/18
        cage+=tube([shellpoint(theta,pi+pi*j/48) for j in range(49)],.007)
    cage+=tube([shellpoint(pi*i/64,0) for i in range(65)]+[shellpoint(pi-pi*i/64,pi) for i in range(1,65)],.015)
    def ellipsoid(center,radii):
        faces=[]
        rings=[[[center[0]+radii[0]*sin(pi*i/18)*cos(2*pi*j/48),center[1]+radii[1]*sin(pi*i/18)*sin(2*pi*j/48),center[2]+radii[2]*cos(pi*i/18)] for j in range(48)] for i in range(1,18)]
        top=[center[0],center[1],center[2]+radii[2]];low=[center[0],center[1],center[2]-radii[2]]
        faces+=[[top,rings[0][j],rings[0][(j+1)%48]] for j in range(48)]
        faces+=[[low,rings[-1][(j+1)%48],rings[-1][j]] for j in range(48)]
        faces+=[[a[j],b[j],b[(j+1)%48],a[(j+1)%48]] for a,b in zip(rings,rings[1:]) for j in range(48)]
        return faces
    seat=d['ground_m']+d['seat_height_m']-bottom
    cushions=ellipsoid([0,0,seat-.065],[.43,.36,.065])+ellipsoid([0,-.27,.60],[.40,.10,.36])
    # Bearing members meet exact cage nodes and cushion surfaces.
    a=shellpoint(27*pi/36,pi);b=shellpoint(27*pi/36,2*pi)
    supports=tube([a,b],.015)
    supports+=tube([shellpoint(pi/2,3*pi/2),[0,-.37,.60]],.015)
    hook=height
    # Rope terminates inside basket pole and anchor plate, retaining contact.
    rope=tube([[0,0,hook-.01],[0,0,d['soffit_m']-bottom-.01]],.009)
    anchor=tube([[0,0,d['soffit_m']-bottom-.02],[0,0,d['soffit_m']-bottom]],.045)
    result=[]
    for suffix,faces,material,kind in [('basket',cage,'trellis','hanging-basket'),('cushions',cushions,'linen','swing-cushion'),('support',supports,'trellis','swing-bearing'),('rope',rope,'trellis','suspension-line'),('anchor',anchor,'alu-bronze','ceiling-anchor')]:
        result.append(dict(id=d['id']+'-'+suffix,group='furniture',part_kind=kind,material=material,
                           faces=[[world(p) for p in (f[0],f[k],f[k+1])] for f in faces for k in range(1,len(f)-1)],label=DECISION,
                           surface=False,occupied_side=None,hanging_swing=True,swing_record=deepcopy(d)))
    return result,d


def envelope(meshes, record):
    """Actual basket/cushion bounds enlarged by the assumed motion allowance."""
    points=[p for m in meshes if m.get('part_kind') in ('hanging-basket','swing-cushion') for f in m['faces'] for p in f]
    margin=record['motion_allowance_m']
    return (min(p[0] for p in points)-margin,min(p[1] for p in points)-margin,
            max(p[0] for p in points)+margin,max(p[1] for p in points)+margin)


def placement_findings(meshes, record, obstacles):
    from . import villa_landscape as L
    rect=envelope(meshes,record);margin=record['motion_allowance_m'];basket=dict(id=record['id'],rect=(rect[0]+margin,rect[1]+margin,rect[2]-margin,rect[3]-margin))
    return L.swing_violations(basket,obstacles,record['motion_allowance_m'])


def corridor(opening_center, garden_center, half_angle_deg=18.):
    """Horizontal finite sightline cone; apex/opening and centre in metres.

    The assumed 18 degree half angle screens the central garden prospect,
    ending at garden-centre distance. It is not a universal view standard.
    """
    from shapely.geometry import Polygon
    ox,oy=opening_center;gx,gy=garden_center;a=atan2(gy-oy,gx-ox);length=hypot(gx-ox,gy-oy)
    return Polygon([(ox,oy)]+[(ox+length*cos(a+radians(t)),oy+length*sin(a+radians(t))) for t in np.linspace(-half_angle_deg,half_angle_deg,37)])


def view_findings(meshes, record, opening_centers, garden_center):
    from shapely.geometry import box
    r=envelope(meshes,record);margin=record['motion_allowance_m'];occupied=box(r[0]+margin,r[1]+margin,r[2]-margin,r[3]-margin)
    return [(record['id'],'lounge sightline cone') for center in opening_centers if corridor(center,garden_center).intersection(occupied).area>1e-6]


def seat_findings(scene, record):
    """Actual rays inside an assumed 70 degree horizontal seat cone.

    Targets are the stone and planting. Central +/-12 degrees rejects an
    majority opaque shell/column/furniture field; basket itself is excluded.
    """
    from .render_support import _triangles
    x,y=record['center'];eye=np.array([x,y,record['ground_m']+record['eye_height_m']]);yaw=radians(record['yaw_deg']);front=np.array([-sin(yaw),cos(yaw),0.])
    targets=[m for m in scene['meshes'] if m.get('part_kind') in ('feature-stone','plant-clump','climber')]
    seen=[]
    tris,owners=_triangles([m for m in scene['meshes'] if not m.get('hanging_swing') and not m.get('surface')]);physical=[m for m in scene['meshes'] if not m.get('hanging_swing') and not m.get('surface')]
    from .villa_landscape import NORTH_COURT
    lo=np.array([NORTH_COURT[0]-.3,NORTH_COURT[1]-.3,record['ground_m']-.1]);hi=np.array([NORTH_COURT[2]+.3,NORTH_COURT[3]+.3,record['soffit_m']+.1])
    nearby=np.all(tris.min(axis=1)<=hi,axis=1)&np.all(tris.max(axis=1)>=lo,axis=1)
    tris,owners=tris[nearby],owners[nearby]
    def first(direction):
        # Vectorised Moller-Trumbore ray intersection, returns physical mesh.
        e1=tris[:,1]-tris[:,0];e2=tris[:,2]-tris[:,0];h=np.cross(direction,e2);a=np.einsum('ij,ij->i',e1,h)
        valid=abs(a)>1e-9;inv=np.divide(1.,a,out=np.zeros_like(a),where=valid);s=eye-tris[:,0];u=inv*np.einsum('ij,ij->i',s,h);q=np.cross(s,e1);v=inv*(q@direction);t=inv*np.einsum('ij,ij->i',e2,q)
        good=valid&(u>=0)&(v>=0)&(u+v<=1)&(t>.03);idx=np.where(good)[0]
        return None if not len(idx) else physical[int(owners[idx[np.argmin(t[idx])]])]
    for target in targets:
        points=np.array([p for f in target['faces'] for p in f]);aim=(points.min(axis=0)+points.max(axis=0))/2-eye
        angle=degrees(np.arccos(np.clip(np.dot(front[:2],aim[:2])/np.linalg.norm(aim[:2]),-1,1)))
        if angle>35:continue
        # Sample actual target vertices plus centre; visible if any ray first hits it.
        for point in np.vstack([(points.min(axis=0)+points.max(axis=0))/2,points[::max(1,len(points)//12)]]):
            direction=point-eye;direction/=np.linalg.norm(direction);hit=first(direction)
            if hit and hit['id']==target['id']:seen.append(target);break
    failures=[]
    if not any(m.get('part_kind')=='feature-stone' for m in seen):failures.append((record['id'],'seat cone cannot see feature stone'))
    if not any(m.get('part_kind') in ('plant-clump','climber') for m in seen):failures.append((record['id'],'seat cone cannot see planting'))
    central=[]
    for angle in (-12,-6,0,6,12):
        for elevation in (-10,0,10):
            a=yaw+radians(angle);e=radians(elevation)
            hit=first(np.array([-sin(a)*cos(e),cos(a)*cos(e),sin(e)]))
            # The open planted trellis is garden content, not loose furniture.
            central.append(None if hit is None else dict(id=hit['id'],blocked=hit['group']=='shell' or (hit['group']=='furniture' and hit.get('part_kind')!='trellis')))
    blocked=sum(bool(h and h['blocked']) for h in central)
    # ASSUMED majority-field criterion: sparse background between leaves is
    # allowed, a wall/furniture occupying most of this central grid is refused.
    scene.setdefault('swing_view_evidence',{}).update(central_first_hits=central,blocked_fraction=blocked/len(central),visible_targets=[m['id'] for m in seen],eye_m=eye.tolist())
    if blocked/len(central)>.5:failures.append((record['id'],'seat central field filled by wall/column/furniture'))
    return failures


def mount(scene, lay):
    from .support_mounting import datum
    from .mounting import _on_polygon, binding, MountItem
    from .garden_render_review import normal
    parts=[m for m in scene['meshes'] if m.get('hanging_swing')]
    if not parts:return
    d=parts[0]['swing_record'];x,y=d['center'];z=d['soffit_m']
    choices=[(s,f) for s in scene['meshes'] if s.get('source_id')=='villa-shell' for f in s['faces'] if normal(f)[2]<-.999999 and abs(f[0][2]-z)<1e-8 and _on_polygon([x,y,z],f,(0,0,-1))]
    if not choices:raise ValueError('swing: no actual balcony soffit face')
    source,face=choices[0];host=datum(scene,source,face,(0,0,-1),'north-swing-balcony-soffit','ceiling')
    scene['north_swing']=deepcopy(d);
    from . import revit_spec as RS
    scene['north_swing']['opening_centers_m']=[(o['x'],o['y']) for o in RS.build(lay)['doors'] if o.get('garden') and 'lounge' in o.get('rooms',[])]
    scene['open_construction_items']=scene.get('open_construction_items',[])+deepcopy(OPEN)
    scene['mounting_hosts'][host.id]['source_faces']=[deepcopy(face)]
    for m in parts:
        top=max(p[2] for f in m['faces'] for p in f);m['mounting']=binding(MountItem(m['id']),host,z-top,'suspended')
        m['mounting']['installation_status']=DECISION+'; '+str(OPEN)


def scene_findings(scene):
    parts=[m for m in scene['meshes'] if m.get('hanging_swing')]
    if not parts:return [(scene['north_swing']['id'],'missing hanging chair')] if scene.get('north_swing') else []
    d=scene.get('north_swing',parts[0]['swing_record']);out=[]
    from .mounting import _on_polygon
    host=scene.get('mounting_hosts',{}).get('north-swing-balcony-soffit',{})
    source=next((m for m in scene['meshes'] if m['id']==host.get('source_mesh')),None)
    point=[*d['center'],d['soffit_m']]
    from .garden_render_review import normal
    if not source or not any(normal(f)[2]<-.999999 and abs(f[0][2]-point[2])<1e-8 and _on_polygon(point,f,(0,0,-1)) for f in source['faces']):out.append((d['id'],'missing live soffit support'))
    bykind={m['part_kind']:m for m in parts}
    required={'ceiling-anchor','suspension-line','hanging-basket','swing-cushion','swing-bearing'}
    if required-set(bykind):return out+[(d['id'],'missing suspension part '+str(sorted(required-set(bykind))))]
    anchor=bykind['ceiling-anchor']
    fixing=[p for f in anchor['faces'] for p in f if abs(p[2]-point[2])<1e-8]
    if not fixing or not source or not all(any(normal(f)[2]<-.999999 and abs(f[0][2]-p[2])<1e-8 and _on_polygon(p,f,(0,0,-1)) for f in source['faces']) for p in fixing):out.append((d['id'],'anchor footprint leaves live soffit'))
    for a,b in [('ceiling-anchor','suspension-line'),('suspension-line','hanging-basket'),('hanging-basket','swing-cushion')]:
        pa=np.array([p for f in bykind[a]['faces'] for p in f]);pb=np.array([p for f in bykind[b]['faces'] for p in f])
        if np.any(np.maximum(pa.min(axis=0),pb.min(axis=0))>np.minimum(pa.max(axis=0),pb.max(axis=0))+.001):out.append((d['id'],'disconnected '+a+' / '+b))
    from .villa_landscape import NORTH_COURT,walking_routes,_mesh_rect
    obstacles=[dict(id=m['id'],rect=_mesh_rect(m)) for m in scene['meshes'] if m.get('part_kind') in ('soil-bed','plant-clump','trellis','feature-stone') and not m.get('hanging_swing')]
    routes,_=walking_routes(scene['meshes'])
    obstacles+=[dict(id='route-'+k,rect=v) for k,v in routes.items()]
    # Actual shell triangles occupying the swing's vertical motion volume.
    from .render_support import _triangles,_tri_box_overlap
    r=envelope(parts,d);low=np.array([r[0],r[1],d['basket_bottom_m']]);high=np.array([r[2],r[3],d['basket_bottom_m']+d['height_m']])
    for m in scene['meshes']:
        if m['group']!='shell' or m.get('diagnostic'):continue
        triangles,_=_triangles([m]);near=np.all(triangles.min(axis=1)<=high,axis=1)&np.all(triangles.max(axis=1)>=low,axis=1)
        if near.any() and _tri_box_overlap(triangles[near],(low+high)/2,(high-low)/2).any():out.append((d['id'],'motion envelope hits '+m['id']))
    out+=placement_findings(parts,d,obstacles)
    # The lounge has one full-height glazed garden opening, shared window/door.
    openings=d.get('opening_centers_m',[])
    if not openings:out.append((d['id'],'missing measured lounge opening centre'))
    scene['north_swing']['lounge_view_cones']=[dict(apex_m=list(o),garden_center_m=[(NORTH_COURT[0]+NORTH_COURT[2])/2,(NORTH_COURT[1]+NORTH_COURT[3])/2],half_angle_deg=18.,status='ASSUMED central prospect') for o in openings]
    scene['north_swing']['seat_view_cone']=dict(eye_m=[*d['center'],d['ground_m']+d['eye_height_m']],front_xy=[-sin(radians(d['yaw_deg'])),cos(radians(d['yaw_deg']))],half_angle_deg=35.,central_half_angle_deg=12.,status='ASSUMED review field')
    out+=view_findings(parts,d,openings,[(NORTH_COURT[0]+NORTH_COURT[2])/2,(NORTH_COURT[1]+NORTH_COURT[3])/2])
    out+=seat_findings(scene,d)
    return out+cushion_findings(parts)


def cushion_findings(meshes):
    """Check cushion underside/rear points touch physical bearing solids.

    Actual underside/rear vertices must contact or lie within a closed bearing
    solid, using the existing 1 mm face comparison. Cage joints need contact.
    """
    from .render_support import _triangles, _point_triangle_distance
    parts={m['part_kind']:m for m in meshes if m.get('hanging_swing')}
    if not parts:return []
    support=parts.get('swing-bearing');cushion=parts['swing-cushion'];cage=parts['hanging-basket']
    if support is None:return [(cushion['id'],'missing physical cushion bearing')]
    tris,_=_triangles([support]);points=np.array([p for f in cushion['faces'] for p in f]);d=cushion['swing_record']
    x,y=d['center'];yaw=radians(d['yaw_deg']);bottom=d['basket_bottom_m']
    # Seat bottom and pillow back are independently generated physical points.
    seat=points[np.argmin(points[:,2])]
    front=np.array([-sin(yaw),cos(yaw)])
    back=points[np.argmin(points[:,:2]@front)]
    def contacts(point):
        if (_point_triangle_distance(point[None,:],tris)<=.001).any():return True
        # An underside point inside a closed bearing solid is physical
        # overlap. Odd ray parity avoids treating a nearby air gap as contact.
        direction=np.array([.371,.529,.763]);direction/=np.linalg.norm(direction)
        e1=tris[:,1]-tris[:,0];e2=tris[:,2]-tris[:,0];h=np.cross(direction,e2);a=np.einsum('ij,ij->i',e1,h)
        valid=abs(a)>1e-9;inv=np.divide(1.,a,out=np.zeros_like(a),where=valid);delta=point-tris[:,0];u=inv*np.einsum('ij,ij->i',delta,h);q=np.cross(delta,e1);v=inv*(q@direction);t=inv*np.einsum('ij,ij->i',e2,q)
        hits=t[valid&(u>=0)&(v>=0)&(u+v<=1)&(t>1e-8)]
        return len(np.unique(np.round(hits,9)))%2==1
    failures=[]
    for name,p in [('seat',seat),('back',back)]:
        if not contacts(p):failures.append((cushion['id'],name+' cushion lacks physical bearing'))
    ct,_=_triangles([cage]);sp=np.array([p for f in support['faces'] for p in f])
    # At least two spatially separate cage joints, tested on actual faces.
    hits=[]
    for p in np.unique(sp,axis=0):
        nearby=ct[np.all(ct.min(axis=1)<=p+.001,axis=1)&np.all(ct.max(axis=1)>=p-.001,axis=1)]
        if len(nearby) and (_point_triangle_distance(p[None,:],nearby)<.001).any():hits.append(p)
    if not hits or np.ptp(np.array(hits),axis=0).max()<.10:failures.append((support['id'],'bearing has no physical cage joints'))
    return failures
