"""Closed procedural dressing contents; all lengths and coordinates are metres.

World x runs along these wardrobe rails, y across their depth, z upwards.
Clothes hang with their broad shoulders across y and thickness along x.
Colours, packing, textile relief and unsourced drops are explicitly ASSUMED;
these are owned procedural appearances, not buyable product specifications.
"""
from __future__ import annotations

import math
import json
import hashlib
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from .physical_part import PartMeshList, geometry_errors, _rectangular_proxy
from .part_exemptions import annotate as annotate_part

DRESS_CARD = 'neufert-longhang-drop-1600: Neufert 2nd English ed. (1980), p.74 Fig.6'
TROUSER_CARD=json.loads((Path(__file__).resolve().parents[3]/'knowledge/garment-dimensions.json').read_text())['cards']['neufert-folded-trouser-drop-900']
DROP = {'dress': 1.53, 'abaya': 1.58, 'jacket': .85, 'shirt': .84, 'trousers': TROUSER_CARD['verified_value']/1000}
BASIS = {t: DRESS_CARD if t in ('dress', 'jacket') else
         'ASSUMED '+('abaya uses dress range in '+DRESS_CARD if t == 'abaya' else
                      'shirt rail-to-hem drop' if t == 'shirt' else 'folded trouser rail-to-hem drop') for t in DROP}
BASIS['trousers']='neufert-folded-trouser-drop-900: Neufert 2nd English ed. (1980), p.74 Fig.6, folded trousers 900 mm'
PITCH = .085  # ASSUMED 85 mm centres, intentionally less dense than published capacity.
THICKNESS = .058  # ASSUMED cloth envelope along rail, including fold relief.
PALETTES = {'hers': ('garment-ivory', 'garment-stone', 'garment-sage-soft', 'garment-charcoal'),
            'his': ('garment-navy', 'garment-charcoal', 'garment-stone', 'garment-olive')}


def bounds(mesh):
    points = [p for f in mesh['faces'] for p in f]
    return [min(p[i] for p in points) for i in range(3)] + [max(p[i] for p in points) for i in range(3)]


def loft(rings):
    """Close counterclockwise horizontal rings, listed from bottom to top."""
    faces = [rings[0][::-1], rings[-1]]
    for low, high in zip(rings, rings[1:]):
        for i in range(len(low)):
            j = (i+1) % len(low)
            faces.extend(([low[i], low[j], high[j]], [low[i], high[j], high[i]]))
    return faces


def rounded_ring(x, y, width, depth, z, radius):
    """Counterclockwise rounded rectangle, four segments at each corner."""
    if min(width,depth,radius)<=0:raise ValueError("rounded profile needs positive dimensions")
    radius=min(radius,.49*min(width,depth))
    points = []
    for cx, cy, angle in ((x+width/2-radius,y+depth/2-radius,0),
                          (x-width/2+radius,y+depth/2-radius,90),
                          (x-width/2+radius,y-depth/2+radius,180),
                          (x+width/2-radius,y-depth/2+radius,270)):
        for step in range(5):
            a = math.radians(angle+step*22.5)
            points.append([cx+radius*math.cos(a),cy+radius*math.sin(a),z])
    return points


def folded(x, y, z, width, depth=.28, height=.033):
    """One folded textile with rounded fold nose and pinched seam relief."""
    radius = min(.013,width/5,depth/5)
    return loft([rounded_ring(x,y,width*.96,depth*.96,z,radius),
                 rounded_ring(x,y,width,depth,z+height*.30,radius),
                 rounded_ring(x,y,width*.98,depth*.985,z+height*.48,radius),
                 rounded_ring(x,y,width,depth,z+height*.66,radius),
                 rounded_ring(x,y,width*.95,depth*.95,z+height,radius)])


def body(x, y, rail_z, garment_type):
    """Closed sleeved silhouette with subdivided, physically pleated skins.

    The front/back triangulation preserves the concave underarm and neckline;
    shared edge midpoints keep the relief surface watertight.
    """
    from .render_support import _ear_clip
    bottom,top=rail_z-DROP[garment_type],rail_z-.085
    if garment_type=='trousers':
        faces=[]
        for leg in (-1,1):
            rings=[]
            for fraction in (0,.025,.35,.68,.96,1):
                z=bottom+(top-.022-bottom)*fraction
                breadth=.112+.025*fraction
                ring=rounded_ring(x,y+leg*.078,THICKNESS*(.16+.44*math.sqrt(fraction)),breadth,z,.008)
                for point in ring:
                    point[0]+=.0015*math.sin((point[1]-y)*100)*math.sin(fraction*math.pi)
                rings.append(ring)
            faces+=loft(rings)
        faces+=folded(x,y,top-.022,THICKNESS,.292,.022)
        return faces
    long=garment_type in ('dress','abaya')
    sleeve=.52 if long else .39 if garment_type=='jacket' else .31
    waist=top-.48 if long else bottom+.20
    hem=.235 if long else .177
    outline=[(-hem,bottom),(hem,bottom),(.153,waist),(.153,top-.22),
             (.212,top-sleeve),(.265,top-sleeve+.015),(.230,top-.065),
             (.082,top),(.045,top-.035),(-.045,top-.035),(-.082,top),
             (-.230,top-.065),(-.265,top-sleeve+.015),(-.212,top-sleeve),
             (-.153,top-.22),(-.153,waist)]
    polygon=[[0,y+across,z] for across,z in outline]
    triangles=_ear_clip(polygon)
    # Three regular subdivisions leave shared boundary vertices for closure.
    for iteration in range(3):
        divided=[]
        for a,b,c in triangles:
            ab=[(a[k]+b[k])/2 for k in range(3)]
            bc=[(b[k]+c[k])/2 for k in range(3)]
            ca=[(c[k]+a[k])/2 for k in range(3)]
            divided.extend(((a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)))
        triangles=divided
    def surface(point,side):
        _,across,z=point
        drop_fraction=(top-z)/(top-bottom)
        envelope=max(0.,1-(abs(across-y)/.275)**1.5)
        bulk=.25+.75*math.sin(math.pi*drop_fraction)**.65
        relief=(.001+.002*envelope)*math.sin((across-y)*76+drop_fraction*1.3)
        half_thickness=.004+.022*envelope*bulk+relief
        return [x+side*half_thickness,across,z]
    faces=[]
    for tri in triangles:
        faces.append([surface(p,1) for p in tri])
        faces.append([surface(p,-1) for p in tri[::-1]])
    # Subdivide each boundary exactly as the skins, avoiding T-junctions.
    for a,b in zip(polygon,polygon[1:]+polygon[:1]):
        edge=[[a[k]+(b[k]-a[k])*j/8 for k in range(3)] for j in range(9)]
        for start,end in zip(edge,edge[1:]):
            faces.append([surface(end,1),surface(start,1),surface(start,-1),surface(end,-1)])
    return faces


@lru_cache(maxsize=4)
def _cached_build(input_sha256, encoded):
    data = json.loads(encoded)
    return _build(data['wardrobes'], data['floor'])


def build(wardrobes, floor):
    """Cache exact authored inputs/recipe/policy; each caller owns its geometry."""
    from . import part_exemptions
    encoded = json.dumps(dict(wardrobes=wardrobes, floor=floor,
        recipe=dict(drop=DROP, basis=BASIS, pitch=PITCH, thickness=THICKNESS, palettes=PALETTES),
        exemptions_sha256=hashlib.sha256(part_exemptions.RECORD.read_bytes()).hexdigest()),
        sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    return deepcopy(_cached_build(hashlib.sha256(encoded).hexdigest(), encoded))


def _build(wardrobes, floor):
    """Build every module with packing fixed before geometry, never clamped."""
    from . import villa_furnish as F
    from .villa_render import box_faces, round_tube
    meshes=PartMeshList(); modules=[]

    def emit(identifier, mat, faces, kind, wardrobe, module, role, support=None, **extra):
        record=annotate_part(dict(id=identifier,material=mat,faces=faces,part_kind=kind,
            group='dressing',room=wardrobe['room'],label='ASSUMED '+wardrobe['partner']+' '+role,
            wardrobe_id=wardrobe['id'],contents_module=module,contents_role=role,
            basis='owned procedural appearance; ASSUMED colours and form',
            bevel_m=.0005 if kind in ('garment','folded-fabric','shoe') else 0,
            subdivide=0,keep_object=True,**extra))
        if support:
            record['contents_support']=support
            if any(m['id']==support for m in meshes):
                record['associated_mounting_root']=support
        meshes.append(record)
        return identifier

    for wardrobe in wardrobes:
        if wardrobe['rot'] not in (0,180):
            raise ValueError('dressing contents require measured x-axis rail')
        q=F.footprint(wardrobe); cy=(q[1]+q[3])/2; owner=wardrobe['partner']
        palette=PALETTES[owner]; source='furn-'+wardrobe['id']+'-0'
        for index,(kind,a,b) in enumerate(F.module_spans(wardrobe)):
            lo,hi=a+.025,b-.025
            prefix=f'dress-{owner}-{kind}-{index}'
            module=dict(id=prefix,wardrobe_id=wardrobe['id'],kind=kind,
                        interior=[lo,q[1]+.025,floor+.10,hi,q[3]-.025,floor+2.082],slots=[])
            modules.append(module)
            def add(suffix,mat,faces,part_kind,role,support=None,**kw):
                return emit(prefix+'-'+suffix,mat,faces,part_kind,wardrobe,prefix,role,support,**kw)
            if kind in ('long-hang','double-hang'):
                for j,height in enumerate((1.98,) if kind=='long-hang' else (1.08,2.02)):
                    z=floor+height; rail=add(f'rail-{j}','brass',round_tube((lo,cy,z),(hi,cy,z),.012),
                        'hanging-rail','rail',source)
                    back=q[1]+.020 if wardrobe['rot']==0 else q[3]-.020
                    for end,xx in (('left',lo),('right',hi)):
                        add(f'rail-{j}-bracket-{end}','brass',round_tube((xx,cy,z),(xx,back,z),.004,8),
                            'rail-bracket','bracket',source,contents_joint=rail)
                    rail_record=next(m for m in meshes if m['id']==rail)
                    rail_record['contents_support']=rail+'-bracket-left'
                    rail_record['contents_support_parts']=[rail+'-bracket-left',rail+'-bracket-right']
                    count=math.floor((hi-lo-.020-THICKNESS)/PITCH)+1
                    if count<1:raise ValueError(prefix+': no physical garment fits')
                    positions=[(lo+hi)/2+(n-(count-1)/2)*PITCH for n in range(count)]
                    slot=dict(id=rail,role='rail',types=['dress','abaya'] if kind=='long-hang' else
                              ['trousers'] if j==0 else ['shirt','jacket'],count=count,
                              pitch_m=PITCH,pitch_basis='ASSUMED 85 mm centres; physical envelope 58 mm',
                              measured_length_m=hi-lo)
                    module['slots'].append(slot)
                    for n,x in enumerate(positions):
                        typ=slot['types'][n%len(slot['types'])]; gid=f'garment-{j}-{n}'
                        hanger_id=prefix+'-'+gid+'-hanger'
                        # Each shoulder member lies ABOVE the actual textile
                        # top edge; the old triangle's bottom bar cut the body.
                        hanger=[]
                        if typ=='trousers':
                            segments=[((x,cy-.16,z-.082),(x,cy+.16,z-.082)),
                                      ((x,cy,z-.082),(x,cy,z-.045))]
                        else:
                            # Offset the sloping shoulder datum by the wire
                            # radius along its outward normal, giving contact.
                            slope=.065/.148
                            rise=.003*math.sqrt(1+slope*slope)
                            segments=[((x,cy-.23,z-.150+rise),(x,cy-.082,z-.085+rise)),
                                      ((x,cy-.082,z-.082),(x,cy+.082,z-.082)),
                                      ((x,cy+.082,z-.085+rise),(x,cy+.23,z-.150+rise)),
                                      ((x,cy,z-.082),(x,cy,z-.045))]
                        for start,end in segments:hanger+=round_tube(start,end,.003,8)
                        # Neck/saddle connects frame to the rail's top without penetrating it.
                        path=[(x,cy,z-.045),(x,cy+.019,z-.018),(x,cy+.019,z+.004),
                              (x,cy+.014,z+.015),(x,cy,z+.015)]
                        for start,end in zip(path,path[1:]):hanger+=round_tube(start,end,.003,8)
                        add(gid+'-hanger','brass',hanger,'hanger','hanger',rail)
                        add(gid,palette[n%len(palette)],body(x,cy,z,typ),'garment','hanging '+typ,
                            hanger_id,garment_type=typ,rail_id=rail,rail_drop_m=DROP[typ],drop_basis=BASIS[typ])
            elif kind=='drawers':
                # One tray and actual contents behind EVERY authored drawer front.
                for j,label in enumerate(wardrobe['drawers']):
                    z=floor+.11+j*.25; front_y=q[3]-.018 if wardrobe['rot']==0 else q[1]
                    front=add(f'front-{j}','greige-lacquer',box_faces(lo,front_y,z,hi,front_y+.018,z+.23),
                              'door-leaf','drawer front',source)
                    tray=add(f'tray-{j}','walnut-grain-x',box_faces(lo,q[1]+(.020 if wardrobe['rot']==0 else .018),z,hi,q[3]-(.018 if wardrobe['rot']==0 else .020),z+.012),
                             'shelf','drawer tray',source)
                    next(m for m in meshes if m['id']==front)['contents_support']=tray
                    # Four thin tray walls meet the base; front is a separate physical part.
                    for end,xx in enumerate((lo,hi-.008)):
                        add(f'tray-{j}-side-{end}','walnut-grain-x',box_faces(xx,q[1]+.025,z+.012,
                            xx+.008,q[3]-.025,z+.15),'cabinet-carcass','drawer side',tray)
                    rear_y=q[1]+.025 if wardrobe['rot']==0 else q[3]-.033
                    add(f'tray-{j}-back','walnut-grain-x',box_faces(lo+.008,rear_y,z+.012,hi-.008,rear_y+.008,z+.15),
                        'cabinet-carcass','drawer back',tray)
                    width=(hi-lo-.048)/2
                    for c in range(2):
                        x=lo+.020+width/2+c*(width+.008)
                        prev=tray
                        for layer in range(2):
                            prev=add(f'content-{j}-{c}-{layer}',palette[(j+c)%4],
                                folded(x,cy,z+.012+layer*.033,width,.25), 'folded-fabric',label,prev,
                                drawer_front_id=front)
                    if label in ('lingerie','headscarves','socks','underwear'):
                        add(f'insert-{j}','walnut-grain-x',box_faces((lo+hi)/2-.003,cy-.14,z+.012,
                            (lo+hi)/2+.003,cy+.14,z+.10),'cabinet-carcass','drawer insert',tray)
                    module['slots'].append(dict(id=front,role='drawer',type=label))
            else:
                for j in range(4):
                    z=floor+.34+j*.42
                    shelf=add(f'shelf-{j}','walnut-grain-x',box_faces(lo,q[1]+.02,z,hi,q[3]-.02,z+.018),
                              'shelf','shelf',source)
                    module['slots'].append(dict(id=shelf,role='shelf'))
                    prev=shelf
                    for layer in range(3):
                        # Compact folded knit hats, scarves, trousers or sportswear fit real bay width.
                        role='folded knit hat' if kind=='hat-shelf' and j%2==0 else 'folded '+('scarf' if kind=='hat-shelf' else 'trousers' if kind=='trousers-pullout' else 'sportswear')
                        prev=add(f'stack-{j}-{layer}',palette[(j+layer)%4],
                            folded((lo+hi)/2,cy,z+.018+layer*.033,hi-lo-.020),
                            'folded-fabric',role,prev)
        # Actual upper shelf at 2.1 m, with lidded boxes ABOVE it (old boxes crossed joinery).
        prefix=f'dress-{owner}-top'
        for index,(kind,a,b) in enumerate(F.module_spans(wardrobe)):
            top_shelf=emit(prefix+f'-shelf-{index}','walnut-grain-x',
                box_faces(a+.025,q[1]+.020,floor+2.082,b-.025,q[3]-.020,floor+2.1),
                'shelf',wardrobe,prefix,'top shelf',source)
            width=b-a-.070; x=(a+b)/2; za=floor+2.1
            box_id=emit(f'dress-{owner}-top-box-{index}','linen',
                folded(x,cy,za,width,.35,.13),'storage-box',wardrobe,prefix,'lidded top box',top_shelf)
            emit(box_id+'-lid','garment-stone',folded(x,cy,za+.13,width+.008,.358,.016),
                 'storage-box',wardrobe,prefix,'box lid',box_id)
        # Rounded shoes, seated on the actual 100 mm plinth, inside hanging bay.
        _,a,b=next(span for span in F.module_spans(wardrobe) if span[0] in ('long-hang','double-hang'))
        for foot in range(2):
            x=(a+b)/2+(foot-.5)*.11; z=floor+.10
            sole=loft([rounded_ring(x,cy,.081,.248,z,.035),
                       rounded_ring(x,cy,.083,.25,z+.014,.035)])
            upper=[rounded_ring(x,cy,.081,.245,z+.014,.034),
                   rounded_ring(x,cy-.012,.079,.205,z+.038,.033),
                   rounded_ring(x,cy-.065,.064,.095,z+.078,.030),
                   rounded_ring(x,cy-.065,.042,.066,z+.078,.020),
                   rounded_ring(x,cy-.065,.032,.052,z+.025,.015)]
            # Downward inner walls and an upward cavity floor make the
            # loafer opening visible while keeping the leather shell closed.
            faces=sole+loft(upper)
            emit(f'dress-{owner}-shoe-0-{foot}','leather-brown',faces,'shoe',wardrobe,
                 f'dress-{owner}-{F.module_spans(wardrobe)[0][0]}-0','shoe',source)
    return list(meshes),modules


def horizontal_profile_findings(mesh):
    """Reject crossing edges in actual horizontal caps, not just closed edges."""
    failures=[]
    def orientation(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    for face in mesh['faces']:
        if len(face)<4 or max(p[2] for p in face)-min(p[2] for p in face)>1e-9:continue
        for i,(a,b) in enumerate(zip(face,face[1:]+face[:1])):
            for j in range(i+2,len(face)):
                if i==0 and j==len(face)-1:continue
                c,d=face[j],face[(j+1)%len(face)]
                if orientation(a,b,c)*orientation(a,b,d)<-1e-20 and orientation(c,d,a)*orientation(c,d,b)<-1e-20:
                    failures.append(mesh['id']+': self-crossing horizontal physical profile')
                    break
            if failures:break
        if failures:break
    return failures


def contact_gap(first, second):
    """Minimum actual vertex-to-face separation in metres, not box overlap."""
    import numpy as np
    from .render_support import _triangle_faces, _point_triangle_distance
    points=np.unique(np.array([p for f in first['faces'] for p in f]),axis=0)
    return float(_point_triangle_distance(points,_triangle_faces(second['faces'])).min())


def hanger_penetrations(hanger, garment):
    """Closed-solid ray parity: reject metal inside cloth, allow contact.

    The ray points along x with small y/z components to avoid aligned edges.
    Coincident triangle hits count once. One tenth of a micrometre is numerical
    surface precision, not a design clearance or a relaxed contact tolerance.
    """
    import numpy as np
    from .render_support import _triangle_faces
    points=np.unique(np.array([p for f in hanger['faces'] for p in f]),axis=0)
    bb=bounds(garment)
    points=points[np.all(points>np.array(bb[:3])+1e-7,axis=1)&np.all(points<np.array(bb[3:])-1e-7,axis=1)]
    if not len(points):return []
    triangles=_triangle_faces(garment['faces'])
    a=triangles[:,0];edge1=triangles[:,1]-a;edge2=triangles[:,2]-a
    ray=np.array([1.,.217,.173]);cross=np.cross(ray,edge2)
    determinant=np.einsum('ij,ij->i',edge1,cross)
    valid=np.abs(determinant)>1e-10
    inverse=np.divide(1,determinant,out=np.zeros_like(determinant),where=valid)
    delta=points[:,None,:]-a
    along1=np.einsum('ptj,tj->pt',delta,cross)*inverse
    crossed=np.cross(delta,edge1)
    along2=np.einsum('ptj,j->pt',crossed,ray)*inverse
    distance=np.einsum('ptj,tj->pt',crossed,edge2)*inverse
    hits=valid&(along1>=-1e-9)&(along2>=-1e-9)&(along1+along2<=1+1e-9)
    inside=[]
    for index,point in enumerate(points):
        values=distance[index,hits[index]]
        if np.any(np.abs(values)<1e-7):continue
        forward=set(np.round(values[values>1e-7],8))
        if len(forward)%2:inside.append(point.tolist())
    return inside


def profile_findings(mesh):
    """ASSUMED cloth morphology: hems thin out instead of extruded planks."""
    bb=bounds(mesh);z=bb[2]+.020;values=[]
    for face in mesh['faces']:
        for a,b in zip(face,face[1:]+face[:1]):
            if min(a[2],b[2])<=z<=max(a[2],b[2]) and abs(a[2]-b[2])>1e-9:
                fraction=(z-a[2])/(b[2]-a[2]);values.append(a[0]+fraction*(b[0]-a[0]))
    hem=max(values)-min(values) if values else float('inf')
    return [mesh['id']+': constant thick garment profile (ASSUMED hem <=32 mm)'] if hem>.032 or bb[3]-bb[0]<.040 else []


def sleeve_findings(mesh):
    """ASSUMED anatomy screen: shoulder breadth and a visible underarm cut.

    World y is shoulder breadth. A cross-section takes every live face edge
    through a horizontal level; no declared ring count can replace the cut.
    """
    typ=mesh.get('garment_type')
    if typ not in ('dress','abaya','shirt','jacket'):return []
    top=bounds(mesh)[5]
    def section(z):
        values=[]
        for face in mesh['faces']:
            for a,b in zip(face,face[1:]+face[:1]):
                if min(a[2],b[2])<=z<=max(a[2],b[2]) and abs(a[2]-b[2])>1e-9:
                    fraction=(z-a[2])/(b[2]-a[2]);values.append(a[1]+fraction*(b[1]-a[1]))
        return max(values)-min(values) if values else 0
    shoulder=section(top-.080)
    underarm=section(top-(.58 if typ in ('dress','abaya') else .45 if typ=='jacket' else .36))
    return [mesh['id']+': lacks physical sleeves/underarm (ASSUMED morphology screen)'] if shoulder<.40 or shoulder-underarm<.060 else []


def contents_findings(wardrobes, meshes):
    """Independent physical occupancy check, deriving slots from authored modules.

    Names are only support references. Missing semantic roles, empty slots,
    proxy geometry, moved supports, overlapping contents and escaped modules
    refuse. Ten millimetres is the existing C4 touching tolerance; this is a
    contact screen, not a structural-capacity or animated-drawer claim.
    """
    from . import villa_furnish as F
    from .render_support import _islands
    by_id={m['id']:m for m in meshes}; out=[]
    contents=[m for m in meshes if m.get('wardrobe_id')]
    for wardrobe in wardrobes:
        owned=[m for m in contents if m['wardrobe_id']==wardrobe['id']]
        if not owned:
            out.append(wardrobe['id']+': missing physical contents (empty/proxy dressing)')
            continue
        q=F.footprint(wardrobe)
        for index,(kind,a,b) in enumerate(F.module_spans(wardrobe)):
            module=f"dress-{wardrobe['partner']}-{kind}-{index}"
            rows=[m for m in owned if m.get('contents_module')==module]
            rails=[m for m in rows if m.get('contents_role')=='rail']
            fronts=[m for m in rows if m.get('contents_role')=='drawer front']
            shelves=[m for m in rows if m.get('contents_role')=='shelf']
            expected=1 if kind=='long-hang' else 2 if kind=='double-hang' else 0
            if len(rails)!=expected:out.append(module+': missing rail contents slot')
            for rail_index, rail in enumerate(sorted(rails,key=lambda m:bounds(m)[2])):
                joints = [m for m in rows if m.get('contents_joint') == rail['id']]
                declared = rail.get('contents_support_parts', [])
                if (len(declared) != 2 or len(set(declared)) != 2 or len(joints) != 2 or
                        set(declared) != {m['id'] for m in joints} or
                        any(m.get('part_kind') != 'rail-bracket' for m in joints)):
                    out.append(rail['id']+': missing declared rail brackets')
                hanging=[m for m in rows if m.get('rail_id')==rail['id']]
                if not hanging:out.append(rail['id']+': empty rail')
                types={'dress','abaya'} if kind=='long-hang' else {'trousers'} if rail_index==0 else {'shirt','jacket'}
                for garment in hanging:
                    if garment.get('garment_type') not in types:out.append(garment['id']+': wrong rail garment type')
                    bb=bounds(garment);rb=bounds(rail);drop=(rb[2]+rb[5])/2-bb[2]
                    if abs(drop-garment.get('rail_drop_m',-1))>.001 or not garment.get('drop_basis'):
                        out.append(garment['id']+': missing or stale hanging length evidence')
            if kind=='drawers':
                if len(fronts)!=len(wardrobe['drawers']):out.append(module+': missing drawer front')
                for front in fronts:
                    if not any(m.get('drawer_front_id')==front['id'] for m in rows):out.append(front['id']+': empty drawer')
            if kind not in ('long-hang','double-hang','drawers'):
                if len(shelves)!=4:out.append(module+': missing shelf')
                for shelf in shelves:
                    if not any(m.get('contents_support')==shelf['id'] and m['part_kind']=='folded-fabric' for m in rows):
                        out.append(shelf['id']+': empty/proxy shelf')
            for row in rows:
                bb=bounds(row)
                if bb[0]<a-.001 or bb[3]>b+.001 or bb[1]<q[1]-.001 or bb[4]>q[3]+.001:
                    out.append(row['id']+': outside measured module')
        boxes=[m for m in owned if m.get('contents_role')=='lidded top box']
        if len(boxes)!=len(wardrobe['modules']):out.append(wardrobe['id']+': missing top box')
        if len([m for m in owned if m.get('contents_role')=='shoe'])<2:out.append(wardrobe['id']+': missing shoe pair')
    boxes={m['id']:bounds(m) for m in meshes if m.get('faces')}
    for row in contents:
        mid=row['id'];bb=boxes[mid];support=by_id.get(row.get('contents_support'))
        if geometry_errors(row['faces']) or (_rectangular_proxy(row['faces']) and row['part_kind'] in ('garment','folded-fabric','shoe')) or row.get('proxy_exemption'):
            out.append(mid+': nonphysical/proxy contents')
        out.extend(horizontal_profile_findings(row))
        if row.get('part_kind')=='garment':
            out.extend(sleeve_findings(row));out.extend(profile_findings(row))
        if row.get('local_axes') not in (['x','y','z'],('x','y','z')) or 'ASSUMED' not in row.get('label',''):
            out.append(mid+': missing axes or appearance assumption')
        if not support:
            out.append(mid+': missing named support');continue
        # Inspect actual connected support pieces, never a wardrobe's whole box.
        if support.get('physical_components') and len(support['faces'])==6*len(support['physical_components']):
            support_boxes=[bounds(dict(faces=support['faces'][i:i+6])) for i in range(0,len(support['faces']),6)]
        else:
            support_boxes=[bounds(dict(faces=f)) for f in _islands(support['faces'])]
        if not any(all(bb[i]<=s[i+3]+.010 and bb[i+3]>=s[i]-.010 for i in range(3)) for s in support_boxes):
            out.append(mid+': separated from named support')
        if row.get('part_kind')=='hanger' and support.get('part_kind')=='hanging-rail':
            if contact_gap(row,support)>1e-7:out.append(mid+': hanger saddle floats above actual rail')
        if row.get('part_kind')=='garment' and support.get('part_kind')=='hanger':
            if hanger_penetrations(support,row):out.append(mid+': hanger penetrates textile solid')
        # Follow the named chain to construction; cycles cannot support themselves.
        seen={mid};link=support
        while link.get('wardrobe_id'):
            if link['id'] in seen:
                out.append(mid+': circular support');break
            seen.add(link['id']);link=by_id.get(link.get('contents_support'))
            if link is None:
                out.append(mid+': broken support chain');break
    # Conservative solid envelopes: all independent contents must be separated.
    # Fitted support interfaces are checked above and intentionally share contact.
    for i,row in enumerate(contents):
        for other in contents[i+1:]:
            if (row.get('contents_support')==other['id'] or other.get('contents_support')==row['id'] or
                    row.get('contents_joint')==other['id'] or other.get('contents_joint')==row['id']):
                continue
            a,b=boxes[row['id']],boxes[other['id']]
            if all(min(a[k+3],b[k+3])-max(a[k],b[k])>1e-6 for k in range(3)):
                out.append(row['id']+' intersects '+other['id'])
    # Structural boards are known six-face closed boxes in the authored
    # wardrobe export. Inspect each separately; the whole assembly box is void.
    for wardrobe in wardrobes:
        source=by_id.get('furn-'+wardrobe['id']+'-0')
        if source is None:
            out.append(wardrobe['id']+': missing physical joinery');continue
        names=source.get('physical_components',[])
        if len(source['faces'])!=6*len(names):
            out.append(source['id']+': unsupported joinery component representation');continue
        boards=[bounds(dict(faces=source['faces'][i*6:i*6+6])) for i,name in enumerate(names)
                if name in ('plinth','divider','back')]
        for row in contents:
            if row['wardrobe_id']!=wardrobe['id']:continue
            bb=boxes[row['id']]
            for board in boards:
                if all(min(bb[k+3],board[k+3])-max(bb[k],board[k])>1e-6 for k in range(3)):
                    out.append(row['id']+': intersects physical joinery')
    return sorted(set(out))


def retire_historical_approval(scene, approved):
    """Retire only frozen old bracket approvals for the new contents contract.

    Historical callers keep all earlier approvals. A current rebuilt scene
    cannot contain their old movement rows; new solids receive fresh bindings.
    Exact row equality prevents this from becoming an arbitrary skip list.
    """
    if scene.get('garment_contents_version')!='closed/1':return False
    import json
    from pathlib import Path
    data=json.loads((Path(__file__).resolve().parents[3]/'knowledge/garment-mounting-retirements.json').read_text())
    matches=[r for r in data['rows'] if r['id']==approved['id']]
    if not matches:return False
    if matches[0]!=approved:raise ValueError(approved['id']+': historical retirement provenance drift')
    if any(r['id']==approved['id'] for r in scene['mounting_movements']):
        raise ValueError(approved['id']+': old mounting row survives contents rebuild')
    retired = scene.setdefault('garment_retired_approvals',[])
    if approved['id'] not in retired:
        retired.append(approved['id'])
    return True


def historical_replacements(scene, old):
    """Require an exact retired proxy and all its strict physical replacements."""
    if scene.get('garment_contents_version') != 'closed/1':
        return None
    data = json.loads((Path(__file__).resolve().parents[3]/'knowledge/garment-part-retirements.json').read_text())
    record = next((r for r in data['rows'] if r['before']['id'] == old['id']), None)
    if record is None:
        return None
    if record['before'] != old:
        raise ValueError(old['id']+': historical contents retirement provenance drift')
    by_id = {m['id']:m for m in scene['meshes']}
    if old['id'] in by_id:
        raise ValueError(old['id']+': historical contents proxy survives rebuild')
    replacements = [by_id.get(identifier) for identifier in record['replacement_ids']]
    if any(m is None or m['part_kind'] != record['replacement_kind'] or m.get('proxy_exemption')
           for m in replacements):
        raise ValueError(old['id']+': missing strict contents replacement')
    PartMeshList().extend(replacements)
    return replacements


def integrate(scene):
    """Rebuild contents on live floor-bound joinery after historical migrations."""
    from .mounting import Host, Finish, MountItem, binding
    wardrobes=scene['dressing_wardrobes']; by={m['id']:m for m in scene['meshes']}
    roots=[by['furn-'+w['id']+'-0'] for w in wardrobes]
    levels=[scene['mounting_hosts'][r['mounting']['host_id']]['structural_point'][2] for r in roots]
    if max(levels)-min(levels)>.001:raise ValueError('dressing joinery floors disagree')
    meshes,modules=build(wardrobes,levels[0]);scene['garment_modules']=modules
    for row in meshes:
        root=by['furn-'+row['wardrobe_id']+'-0']
        record=scene['mounting_hosts'][root['mounting']['host_id']]
        host=Host(record['id'],record['kind'],tuple(record['structural_point']),tuple(record['normal']),Finish(**record['finish']))
        projection=bounds(row)[2]-levels[0]
        row['mounting']=dict(binding(MountItem(row['id']),host,0,'floor-standing'),
            geometry_role='assembly-child',assembly_root=root['id'],child_projection_m=projection,
            projection_basis='Measured live floor-bearing wardrobe; explicit contents_support chain independently checked')
        row['mounting_package']='garments-live-joinery'
        if row.get('contents_role') == 'rail':
            row['mounting']['support_parts'] = list(row['contents_support_parts'])
        scene['meshes'].append(row)
    scene['garment_support_status']='Geometric contact only; fixings and structural capacities ASSUMED pending joinery coordination'
