"""G6 south garden construction, measured in metres (x/y plan, z height).

Botanical values come from the tracked palette. Timber, pruning, furniture
and container sizes are authored assumptions, never structural approval.
"""
from math import cos, sin, pi, hypot
from copy import deepcopy
import json
import numpy as np


def _tri(faces):
    return [[f[0],f[i],f[i+1]] for f in faces for i in range(1,len(f)-1)]


def tube(a,b,r=.006,count=8):
    """Closed round stem/branch between endpoints a and b, radius r."""
    a,b=np.asarray(a,dtype=float),np.asarray(b,dtype=float);axis=b-a;axis/=np.linalg.norm(axis)
    helper=np.array([0.,0.,1.]) if abs(axis[2])<.9 else np.array([1.,0.,0.])
    u=np.cross(axis,helper);u/=np.linalg.norm(u);v=np.cross(axis,u)
    rings=[[(p+r*(u*cos(i*2*pi/count)+v*sin(i*2*pi/count))).tolist() for i in range(count)] for p in (a,b)]
    low,high=rings
    return _tri([low[::-1],high]+[[low[i],low[(i+1)%count],high[(i+1)%count],high[i]] for i in range(count)])


def leaf(center,length,width,angle=0,tilt=0,count=8):
    """Closed pointed oval lamina; length/width are full dimensions."""
    c=np.asarray(center);u=np.array([cos(angle)*cos(tilt),sin(angle)*cos(tilt),sin(tilt)]);v=np.array([-sin(angle),cos(angle),0.]);n=np.cross(u,v)
    upper=[];lower=[]
    for i in range(count):
        a=2*pi*i/count;p=c+u*(length/2*cos(a))+v*(width/2*sin(a))
        upper.append((p+n*.0015).tolist());lower.append((p-n*.0015).tolist())
    return _tri([upper,lower[::-1]]+[[upper[i],lower[i],lower[(i+1)%count],upper[(i+1)%count]] for i in range(count)])


def _mesh(identifier,material,faces,kind,element,label,**fields):
    from . import villa_landscape as L
    m=L._mesh(identifier,'dressing' if element in ('climber','foliage','espalier') else 'furniture',material,faces,label,kind=kind)
    m.update(g6_element=element,**fields);return m


def _dome_geometry(dense=True):
    """Species-specific low mound, shared by south and east planting."""
    from .garden_g6b import mound
    growth=mound(dense)
    return growth.faces,growth.leaves


def _mound_template(dense):
    """Build-local immutable local geometry for the exact generator arguments."""
    from .garden_g6b import mound
    from .build_cache import immutable

    def compute():
        growth = mound(dense=dense)
        return (tuple(tuple(tuple(p) for p in face) for face in growth.faces),
                tuple(growth.leaves), tuple(growth.materials), json.dumps(growth.records))
    return immutable("g6-mound-template", dense, compute)


def _transform_faces(faces, points, origin, factors, offset):
    """Place each vertex with the original subtract, scale, then add order.

    points is the face-order flattened point array; origin is the local
    reference point, factors the three axis scales, offset the world position.
    Face lengths and winding are preserved, including non-triangle faces.
    """
    placed = (offset + (points-origin)*factors).tolist()
    result = []
    start = 0
    for face in faces:
        stop = start + len(face)
        result.append(placed[start:stop])
        start = stop
    return result


def clump(identifier,species,center,ground,data,*,bed,layer,context=None):
    """Connected authored dome or lavender leaves, driven by palette envelope."""
    from . import villa_landscape as L
    row=L.require_species(species,data)
    key='procedural-mona-lavender' if species=="Plectranthus 'Mona Lavender'" else 'procedural-pittosporum'
    size=row['placement_assumptions'][key]
    if context:size=size.get('contexts',{}).get(context,size)
    height=.4 if species.startswith('Plectranthus') else .7 if context else .75 if layer=='back' else .65;spread=.35 if species.startswith('Plectranthus') else .65
    faces=[];leaf_indices=[];flower_indices=[]
    if not species.startswith('Plectranthus'):
        template=_mound_template(bool(context))
        faces,leaf_indices=template[0],list(template[1])
    for i in range(17 if species.startswith('Plectranthus') else 0):
        a=i*pi*(3-5**.5);radial=.12+.035*(i%4);z=.26+.035*(i%6)
        tip=(radial*cos(a),radial*sin(a),z)
        faces+=tube((0,0,0),tip,.008)
        for j in range(4):
            p=np.array(tip)*(.45+.18*j);p[:2]+=np.array([cos(a+j),sin(a+j)])*.035
            faces+=tube((0,0,0),p,.004)
            f=leaf(p,.13+.015*sin(i+j),.055+.008*cos(i+2*j),a+j*.7,.2+.25*sin(i+j));leaf_indices+=list(range(len(faces),len(faces)+len(f)));faces+=f
        if species.startswith('Plectranthus'):
            upper=(tip[0],tip[1],tip[2]+.12);faces+=tube(tip,upper,.003)
            for k in range(6):
                p=(upper[0]+.02*cos(k),upper[1]+.02*sin(k),upper[2]-.018*k)
                f=leaf(p,.035,.025,k);flower_indices+=list(range(len(faces),len(faces)+len(f)));faces+=f
    points=np.array([p for f in faces for p in f]);lo=points.min(axis=0);hi=points.max(axis=0)
    factors=np.array([spread/max((hi-lo)[:2])]*2+[height/(hi[2]-lo[2])]);origin=np.array([(lo[0]+hi[0])/2,(lo[1]+hi[1])/2,lo[2]])
    offset=np.array([*center,ground]);faces=_transform_faces(faces,points,origin,factors,offset)
    m=_mesh(identifier,'garden-foliage',faces,'plant-clump','centrepiece' if context else 'foliage',
        'ASSUMED clipped dome' if not species.startswith('Plectranthus') else 'ASSUMED lavender-flowered underplanting',
        species=species,center=list(center),root_z_m=ground,bed=bed,planting_layer=layer,
        spread_m=spread,appearance_key=key,leaf_face_indices=leaf_indices,explicit_geometry=True)
    if not species.startswith('Plectranthus'):
        m['face_materials']=list(template[2])
        m['leaf_records']=json.loads(template[3])
        m['plant_form']='dense-low-mound'
    if flower_indices:
        m['face_materials']=['g6-lavender-flower' if i in set(flower_indices) else 'garden-foliage' for i in range(len(faces))]
    return m


def wall_sun_evidence(study,ground=-3.):
    """Compare all boundary walls at equally spaced root sampling points.

    June, equinox and December hourly rays use the committed SunStudy;
    June mean ranks suitability, seasonal totals resolve ties reproducibly.
    """
    from .garden_sun import DATES
    from . import villa_landscape as L
    x0,y0,x1,y1=L.SOUTH;thickness=.25
    walls={'south':[(x1-thickness-.2,y0+1+i*(y1-y0-2)/4) for i in range(5)],
           'west':[(x0+1+i*(x1-x0-2)/4,y0+.2) for i in range(5)],
           'east':[(x0+1+i*(x1-x0-2)/4,y1-thickness-.2) for i in range(5)]}
    rows=[]
    for name,positions in walls.items():
        hours={d:[study.hours(x,y,ground,d) for x,y in positions] for d in DATES}
        means={d:sum(map(len,h))/len(h) for d,h in hours.items()}
        rows.append(dict(wall=name,points_m=[list(p) for p in positions],hours=hours,means=means))
    winner=max(rows,key=lambda row:(row['means'][DATES[0]],sum(row['means'].values()),row['wall']))
    return dict(selected_wall=winner['wall'],walls=rows,geometry_sha256=study.geometry_sha256,
                basis='Five equal root-level points per boundary wall; rank June mean then seasonal sum; hourly actual enclosure rays')


def _pergola(assumptions):
    from . import villa_landscape as L
    x0,y0,x1,y1=assumptions['pergola_rect_m'];g=L.GROUND;w=assumptions['post_width_m'];clear=assumptions['clear_height_m'];depth=assumptions['beam_depth_m']
    meshes=[];post_centers=[]
    for i,(x,y) in enumerate(((x0+w/2,y0+w/2),(x1-w/2,y0+w/2),(x0+w/2,y1-w/2),(x1-w/2,y1-w/2))):
        dx,dy=assumptions.get('post_insets_m',{}).get(str(i),(0.,0.))
        x+=dx;y+=dy
        m=_mesh('g6-pergola-post-%d'%i,'trellis',L._box(x-w/2,y-w/2,g,x+w/2,y+w/2,g+clear),'trellis','pergola','ASSUMED 120 mm timber post on at-grade footing; structural and soil capacity UNVERIFIED',pergola_role='post')
        meshes.append(m);post_centers.append([x,y])
    for i,y in enumerate((y0,y1-w)):
        meshes.append(_mesh('g6-pergola-beam-%d'%i,'trellis',L._box(x0,y,g+clear,x1,y+w,g+clear+depth),'trellis','pergola','ASSUMED timber beam bearing on posts',pergola_role='beam'))
    n=round((x1-x0-w)/assumptions['rafter_spacing_m'])
    for i in range(n+1):
        x=x0+(x1-x0-w)*i/n
        meshes.append(_mesh('g6-pergola-rafter-%d'%i,'trellis',L._box(x,y0,g+clear+depth,x+w,y1,g+clear+depth+assumptions['rafter_depth_m']),'trellis','pergola','ASSUMED open timber rafters; young established climber coverage 50-60 percent',pergola_role='rafter'))
    return meshes,post_centers


def _roof_climbers(assumptions,posts,data=None):
    from . import villa_landscape as L
    from .garden_g6b import vines
    return vines(assumptions,posts,L.GROUND,L._plant_data() if data is None else data)


def build(data=None,assumptions=None,study=None):
    """Return meshes, botanical plants, route objects and a measured G6 plan."""
    from . import villa_landscape as L, villa_furniture_detail as FD
    from .garden_sun import default_study,active_study
    data=L._plant_data() if data is None else data
    assumptions=json.loads(L.PALETTE.read_text())['design_assumptions']['south_garden_g6'] if assumptions is None else assumptions
    study=(active_study.get() or default_study()) if study is None else study
    meshes,posts=_pergola(assumptions);plants=_roof_climbers(assumptions,posts,data);meshes+=plants
    g=L.GROUND;cx,cy=assumptions['bowl_center_m'];h=assumptions['bowl_height_m'];r=assumptions['bowl_diameter_m']/2
    # Continuous at-grade terrace: shell remains authoritative supporting ground.
    paving=L._mesh('g6-terrace','ground','stepping-stone',L._quad(L.SOUTH[0],L.SOUTH[1],27.4,-26.72,g),'ASSUMED terrace paving at court grade; 1.65 m east bypass beside pergola',kind='finish-layer',surface=True,occupied_side=(0,0,1));paving['g6_element']='pergola';meshes.append(paving)
    body,rim,soil=L._pot(cx,cy,g,.30,r,h,count=32)
    for suffix,faces,kind,mat in (('bowl',body,'planter','g6-bowl-glaze'),('rim',rim,'planter-rim','g6-bowl-glaze'),('soil',soil,'planter-soil','garden-soil')):
        meshes.append(_mesh('g6-centrepiece-'+suffix,mat,faces,kind,'centrepiece','Client approved single bowl exception 2026-10-06; ASSUMED low wide glazed ceramic, supplier product UNVERIFIED'))
    soil_z=g+h-.005
    dome=clump('g6-centrepiece-dome',"Pittosporum tobira 'Wheeler\'s Dwarf'",(cx,cy),soil_z,data,bed='south-bowl',layer='dome',context='bowl');meshes.append(dome);plants.append(dome)
    for i in range(5):
        a=i*2*pi/5;m=clump('g6-centrepiece-mona-%d'%i,"Plectranthus 'Mona Lavender'",(cx+.31*cos(a),cy+.31*sin(a)),soil_z,data,bed='south-bowl',layer='underplanting',context='bowl');meshes.append(m);plants.append(m)
    chairs=[]
    for piece in assumptions['furniture_pieces']:
        x,y=piece['center_m'];rotation=piece['rotation_deg']
        item=dict(id='g6-'+piece['id'],type='outdoor-chair',w=piece['width_m'],d=piece['depth_m'],h=.8,cx=x,cy=y,rot=rotation)
        from .garden_g6b import lounge_parts
        parts=FD.world_parts(item,g,lounge_parts(piece['width_m']*1000,piece['depth_m']*1000,piece['seats']));faces=[f for fs in parts.values() for f in fs]
        angle=rotation*pi/180
        mesh=_mesh('g6-seating-'+piece['id'],'trellis',faces,'outdoor-seating','furniture','ASSUMED procedural outdoor timber/cushion seating; %d seats; no manufacturer or rated weather-performance claim'%piece['seats'],facing=[-sin(angle),cos(angle)],seats=piece['seats'])
        slots=[]
        for name,fs in parts.items():slots += ['g6-outdoor-cushion' if name.endswith('cushion') else 'g6-outdoor-timber']*len(fs)
        mesh['face_materials']=slots;mesh['seating_parts']={name:list(range(sum(len(v) for n,v in list(parts.items())[:i]),sum(len(v) for n,v in list(parts.items())[:i+1]))) for i,(name,fs) in enumerate(parts.items())};meshes.append(mesh);chairs.append(mesh)
    evidence=wall_sun_evidence(study)
    if evidence['selected_wall']!='east':raise ValueError('G6 sunniest boundary changed; redraw loquat on measured winning wall')
    from .garden_g6b import espalier
    x0,x1=assumptions['espalier_run_m'];wall=L.SOUTH[3]-.25
    growth,trunk,tiers,wires=espalier(x0,x1,wall,g,assumptions['espalier_height_m'],assumptions['wire_tier_spacing_m'],L.require_species('Eriobotrya japonica',data))
    loquat=_mesh('g6-loquat-plant','garden-foliage',growth.faces,'plant-clump','espalier',
        'ASSUMED densely trained loquat; sourced leaf length, folded veined terminal clusters, horizontal tiers tied to unchanged wires',
        species='Eriobotrya japonica',center=trunk[:2].tolist(),root_z_m=g,bed='south-espalier',planting_layer='accent',spread_m=x1-x0,appearance_key='procedural-espalier',**growth.fields())
    meshes.append(loquat);plants.append(loquat)
    wire=_mesh('g6-loquat-wires','trellis',wires,'trellis','espalier','ASSUMED wall-fixed horizontal training wires; fixings and capacity UNVERIFIED',espalier_role='wire');meshes.append(wire)
    # Ground foliage three strata in one bed, plus root bed for espalier.
    beds={'south-foliage':(26.25,-29.65,28.25,-27.05),'south-espalier':(24.35,-21.12,27.05,wall)}
    for name,rect in beds.items():
        m=L._mesh('g6-bed-'+name,'ground','garden-soil',L._quad(*rect,g),'ASSUMED low ground-level soil bed; roots and drainage over basement UNVERIFIED',kind='soil-bed',surface=True,occupied_side=(0,0,1));m['g6_element']='foliage';meshes.append(m)
    for species,layer,x,ys in (("Pittosporum tobira 'Wheeler\'s Dwarf'",'mid',27.55,(-29.15,-28.48,-27.81)),('Fatsia japonica','back',26.8,(-29.15,-28.15,-27.15)),('Aspidistra elatior','front',26.38,(-29.10,-28.40,-27.70))):
        for i,y in enumerate(ys):
            if species.startswith('Pittosporum'):m=clump('g6-foliage-'+layer+'-%d'%i,species,(x,y),g,data,bed='south-foliage',layer=layer)
            elif species.startswith('Fatsia'):
                from .garden_shade import clump as shade_clump
                m=shade_clump('g6-foliage-'+layer+'-%d'%i,species,(x,y),g,data,bed='south-foliage',layer=layer)
            else:m=L._botanical_clump('g6-foliage-'+layer+'-%d'%i,species,(x,y),g,data,bed='south-foliage',layer=layer)
            m['g6_element']='foliage';meshes.append(m);plants.append(m)
    # Remaining rear boundary: evergreen masses in two measured part-sun drifts.
    # Low understory can share the tree's plan circle; pergola/espalier cannot.
    for name,ys in (('south-rear-a',(-26.1,-25.4,-24.7)),('south-rear-b',(-23.8,-23.1,-22.4))):
        rect=(26.95,min(ys)-.35,28.25,max(ys)+.35);beds[name]=rect
        bedmesh=L._mesh('g6-bed-'+name,'ground','garden-soil',L._quad(*rect,g),'ASSUMED ground-level boundary bed; young low understory beneath retained tree canopy where projected circles overlap; drainage/root detail UNVERIFIED',kind='soil-bed',surface=True,occupied_side=(0,0,1));bedmesh['g6_element']='foliage';meshes.append(bedmesh)
        for species,layer,x in (("Pittosporum tobira 'Wheeler\'s Dwarf'",'back',27.89),("Pittosporum tobira 'Wheeler\'s Dwarf'",'mid',27.34),("Plectranthus 'Mona Lavender'",'front',27.10)):
            for i,y in enumerate(ys):
                m=clump('g6-foliage-'+name+'-'+layer+'-%d'%i,species,(x,y),g,data,bed=name,layer=layer);meshes.append(m);plants.append(m)
    from .fitting_mounting import bounds
    objects=[dict(id=m['id'],g6_element='furniture',part_kind='outdoor-seating',rect=(bounds(m)[0],bounds(m)[1],bounds(m)[3],bounds(m)[4]),bottom_m=bounds(m)[2],top_m=bounds(m)[5]) for m in chairs]
    plan=dict(assumptions=deepcopy(assumptions),post_centers_m=posts,beds=beds,sun_evidence=evidence,wire_tiers_m=tiers,
              furniture_clearances=dict(route_width_m=.914,route_card='lts-path-width-oneway-900',inner_gap_is_not_walking_route=True,seats=sum(p['seats'] for p in assumptions['furniture_pieces'])))
    plan['planting_sun_hours']={p['id']:{day:study.hours(*p['center'],p['root_z_m'],day) for day in ('2026-06-21','2026-03-20','2026-12-21')} for p in plants}
    plan['shade_limits']='Aspidistra south strip has direct enclosure rays; adjacent foliage shade excluded, so source bright-indirect applicability UNRESOLVED; no deep-shade performance claim.'
    plan['understory_policy']='Low ground foliage may share the mature tree plan circle; pergola and loquat do not. Actual D2 walking geometry remains checked.'
    plan['roof_leaf_cover_fraction']=roof_cover(meshes,assumptions['pergola_rect_m'])
    return meshes,plants,objects,plan


def roof_cover(meshes,rect):
    """Union of actual roof lamina plan areas divided by full frame plan area."""
    from shapely.geometry import Polygon,box
    from shapely.ops import unary_union
    polys=[]
    for m in meshes:
        if m.get('g6_element')!='climber':continue
        for index in m['leaf_face_indices']:
            face=m['faces'][index]
            if max(q[2] for q in face)<m['root_z_m']+2.6:continue
            p=Polygon([q[:2] for q in face])
            if p.area>1e-10:polys.append(p)
    return unary_union(polys).intersection(box(*rect)).area/box(*rect).area


def findings(meshes,plan,tree_center=None,routes=None,ground=-3.):
    """Independent live geometry guards; no cached bounds establish contact."""
    from . import villa_landscape as L
    from .fitting_mounting import bounds
    tree_center=tree_center or json.loads(L.PALETTE.read_text())['design_assumptions']['south_tree_position']['center_m'];routes=L.PATHS if routes is None else routes
    from shapely.geometry import box,Point
    circle=Point(tree_center).buffer(2.3);out=[];frame=[m for m in meshes if m.get('g6_element')=='pergola' and m.get('pergola_role')]
    expected={'post':4,'beam':2,'rafter':8}
    for role,count in expected.items():
        got=sum(m.get('pergola_role')==role for m in frame)
        if got!=count:out.append(('pergola','expected %d %s members, found %d'%(count,role,got)))
    for m in frame:
        bb=bounds(m);rect=(bb[0],bb[1],bb[3],bb[4])
        if box(*rect).intersects(circle):out.append((m['id'],'pergola intersects retained mature tree circle'))
        if any(box(*rect).intersects(box(*r)) for r in routes.values()):out.append((m['id'],'pergola overlaps walking route plan envelope'))
        if m['pergola_role']=='post' and abs(bb[2]-ground)>1e-6:out.append((m['id'],'post is not at grade'))
        if m['pergola_role']=='beam':
            if abs(bb[2]-ground-plan['assumptions']['clear_height_m'])>1e-6:out.append((m['id'],'physical clear height differs from recorded assumption'))
            supported=[p for p in frame if p['pergola_role']=='post' and abs(bounds(p)[5]-bb[2])<1e-6 and box(*L._mesh_rect(p)).intersection(box(*rect)).area>1e-8]
            if len(supported)<2:out.append((m['id'],'beam lacks two physical post bearings'))
        if m['pergola_role']=='rafter':
            supported=[p for p in frame if p['pergola_role']=='beam' and abs(bounds(p)[5]-bb[2])<1e-6 and box(*L._mesh_rect(p)).intersection(box(*rect)).area>1e-8]
            if len(supported)<2:out.append((m['id'],'rafter lacks two physical beam bearings'))
    if abs(plan['assumptions']['clear_height_m']-2.6)>1e-6:out.append(('pergola','clear height record differs from authored assumption'))
    for m in meshes:
        if m.get('g6_element')=='climber':
            bb=bounds(m);p=plan['post_centers_m'][m['post_index']]
            if abs(bb[2]-ground)>1e-6 or abs(m['root_z_m']-ground)>1e-6 or hypot(m['center'][0]-p[0],m['center'][1]-p[1])>1e-6:out.append((m['id'],'climber root not grounded at a post'))
        if m.get('espalier_role')=='wire':
            bb=bounds(m)
            if abs(bb[4]-(L.SOUTH[3]-.25))>1e-6:out.append((m['id'],'espalier wires not on physical wall face'))
        if m.get('g6_element') in ('pergola','centrepiece','furniture','espalier','climber','foliage'):
            # Shared face vertices have the same yard classification.
            points={(p[0],p[1]) for f in m['faces'] for p in f}
            if any(not L.inside_yard(*p) for p in points):out.append((m['id'],'G6 geometry leaves yard'))
        if m.get('g6_element')=='espalier':
            rect=box(*L._mesh_rect(m))
            if rect.intersects(circle):out.append((m['id'],'espalier intersects mature tree circle'))
            if any(rect.intersects(box(*r)) for r in routes.values()):out.append((m['id'],'espalier overlaps walking route envelope'))
            if any(rect.intersection(box(*L._mesh_rect(p))).area>1e-8 for p in frame):out.append((m['id'],'espalier overlaps pergola'))
    if sum(m.get('espalier_role')=='wire' for m in meshes)!=1:out.append(('espalier','missing wall training wires'))
    if sum(m.get('species')=='Eriobotrya japonica' for m in meshes)!=1:out.append(('espalier','exactly one loquat required'))
    accesses={key:plan['assumptions'][key] for key in ('seating_access_rect_m','seating_cross_access_rect_m')}
    out += [(identifier,'seating access '+route) for identifier,route in L.route_violations([m for m in meshes if not m.get('surface')],accesses)]
    coverage=roof_cover(meshes,plan['assumptions']['pergola_rect_m'])
    if not .5<=coverage<=.6:out.append(('pergola','actual leaf union %.4f outside assumed 50-60 percent'%coverage))
    return out


def mount(scene,lay=None):
    """Bind G6 timber assemblies and vines before generic C4 support migration.

    Four at-grade posts are the floor-bearing assembly root. The espalier
    wires use the exterior API's finite, physical fence inner face.
    """
    from .exterior_mounting import yard_sources,mount_landscape
    from .support_mounting import datum,floor_assembly
    from .fitting_mounting import normal,bounds
    from .mounting import _on_polygon
    members=[m for m in scene['meshes'] if m.get('g6_element') in ('pergola','climber') and m.get('part_kind')!='finish-layer']
    if members:
        root=next(m for m in members if m.get('pergola_role')=='post');bb=bounds(root);anchor=[(bb[0]+bb[3])/2,(bb[1]+bb[4])/2,bb[2]]
        choices=[(s,f) for s in scene['meshes'] if s.get('group') in ('shell','ground','context') for f in s['faces'] if normal(f)[2]>.999999 and abs(f[0][2]-bb[2])<1e-6 and _on_polygon(anchor,f,(0,0,1))]
        if not choices:raise ValueError('G6 pergola has no actual at-grade support')
        source,face=choices[0];host=datum(scene,source,face,(0,0,1),'support-g6-pergola','floor');floor_assembly(scene,members,host,'g6-pergola')
    wires=[m for m in scene['meshes'] if m.get('espalier_role')=='wire']
    if wires:
        sources=yard_sources(scene)
        for m in wires:mount_landscape(scene,m,sources,model_side='+y')


def content_findings(meshes,props=(),objects=(),plan=None):
    """A G6 tag grants no general permission to restore old south contents."""
    allowed={
        'pergola':{'trellis','finish-layer'},'climber':{'climber'},
        'centrepiece':{'planter','planter-rim','planter-soil','plant-clump'},
        'furniture':{'outdoor-seating'},'espalier':{'plant-clump','trellis'},
        'foliage':{'plant-clump','soil-bed'},
    }
    species={"Petrea volubilis","Trachelospermum jasminoides","Pittosporum tobira 'Wheeler\'s Dwarf'","Plectranthus 'Mona Lavender'",'Eriobotrya japonica','Fatsia japonica','Aspidistra elatior','Rhapis excelsa'}
    out=[]
    for m in list(meshes)+list(props)+list(objects):
        element=m.get('g6_element')
        if not element:continue
        if not m['id'].startswith('landscape-g6-') or element not in allowed or m.get('part_kind') not in allowed.get(element,set()):out.append((m['id'],'unregistered G6 appearance identity or form'))
        if m.get('species') and m['species'] not in species:out.append((m['id'],'species not in approved G6 palette'))
        if m.get('part_kind')=='plant-clump' and not m.get('species'):out.append((m['id'],'G6 botanical appearance missing species identity'))
    return out


def scene_findings(scene):
    """Recompute G6 policy against authoritative geometry and ray-cast scene."""
    from .garden_sun import SunStudy
    plan=scene.get('landscape',{}).get('g6',scene.get('garden_g6'))
    meshes=[m for m in scene['meshes'] if m.get('g6_element')]
    if not meshes and plan is None:return []
    if plan is None:return [('G6','missing G6 authored plan')]
    if not meshes:return [('G6','missing all authored G6 geometry')]
    out=findings(meshes,plan)+content_findings(meshes,plan=plan)+appearance_findings(scene['meshes'])
    fresh=wall_sun_evidence(SunStudy(scene))
    if plan.get('sun_evidence')!=fresh:out.append(('espalier','wall sun evidence stale or not reproduced from actual scene'))
    if fresh['selected_wall']!=plan['assumptions']['espalier_wall']:out.append(('espalier','selected wall is not sunniest'))
    for m in meshes:
        if m.get('g6_element') in ('pergola','climber') and m.get('part_kind')!='finish-layer' and not m.get('mounting'):out.append((m['id'],'missing physical pergola mounting contract'))
        if m.get('espalier_role')=='wire':
            host=scene.get('mounting_hosts',{}).get(m.get('mounting',{}).get('host_id'),{})
            if host.get('yard_edge_index') is None and not host.get('source_mesh','').startswith('yard-boundary-edge-'):out.append((m['id'],'missing exterior finite-wall mounting contract'))
    return out

def appearance_findings(meshes):
    """Physical form checks supplement mandatory human likeness review.

    All thresholds refer to authored form (recorded canopy, post radius,
    leaf sizes and cushion construction), never horticultural approval.
    """
    from . import villa_landscape as L
    from .fitting_mounting import bounds
    from math import atan2
    out=[];data=L._plant_data()
    for mesh in meshes:
        species=mesh.get('species','');faces=mesh.get('faces',[])
        if species not in data:continue
        if species=="Pittosporum tobira 'Wheeler\'s Dwarf'":
            # A single low shoot passed G6's minimum-height test. Require
            # real low foliage around the mound, rather than one token leaf.
            root=mesh.get('root_z_m');center=mesh.get('center');indices=mesh.get('leaf_face_indices',[])
            sectors=set()
            if root is not None and center:
                for i in indices:
                    p=np.mean(faces[i],axis=0)
                    if p[2]<=root+.20 and hypot(p[0]-center[0],p[1]-center[1])>.08:
                        sectors.add(int((atan2(p[1]-center[1],p[0]-center[0])+pi)*4/pi)%8)
            if len(sectors)!=8:out.append((mesh['id'],'dwarf mound lacks low foliage around all eight sides'))
            if indices and root is not None and center:
                tips=np.array([np.mean(faces[i],axis=0) for i in indices])
                height=tips[:,2].max()-root
                radial=np.linalg.norm(tips[:,:2]-center,axis=1)
                lower=radial[tips[:,2]<root+height*.35]
                upper=radial[tips[:,2]>root+height*.80]
                if not len(lower) or not len(upper) or np.quantile(upper,.95)>np.quantile(lower,.95)*.85:
                    out.append((mesh['id'],'dwarf mound crown does not round towards its apex'))
                records=mesh.get('leaf_records',[])
                if records:
                    centers=np.array([np.mean(np.array([faces[i] for i in r['face_indices']]).reshape(-1,3),axis=0) for r in records])
                    heights=centers[:,2];span=np.ptp(heights)
                    if span>0:
                        normalized=(heights-heights.min())/span
                        # Authored continuity screen: a 4% crown-height slice
                        # may not hold more than 9% of all leaves. Frozen real
                        # stacked crowns measured 11.9%; continuous tips 5.1%.
                        peak=max(np.mean((normalized>=t)&(normalized<t+.04)) for t in np.arange(0.,1.,.005))
                        if peak>.09:out.append((mesh['id'],'dwarf mound has stacked horizontal foliage rings'))
        if mesh.get('g6_element')=='climber':
            records=mesh.get('leaf_records',[]);limit=data[species]['render_form']['source_leaf_length_m']['range_m'][1]
            if not records:out.append((mesh['id'],'missing species-sized leaf records'))
            else:
                for record in records:
                    vertices=np.unique(np.array([faces[i] for i in record['face_indices']]).reshape(-1,3),axis=0)
                    diameter=np.linalg.norm(vertices[:,None]-vertices[None,:],axis=2).max()
                    if diameter>limit+1e-6:out.append((mesh['id'],'measured leaf exceeds sourced species size'));break
            bark=[p for i,f in enumerate(faces) if mesh.get('face_materials',[])[i]=='trellis' for p in f]
            root=mesh['root_z_m'];cx,cy=mesh['center']
            for low,high in ((.3,.8),(.9,1.4),(1.5,2.0),(2.1,2.5)):
                around={int((atan2(p[1]-cy,p[0]-cx)+pi)*2/pi)%4 for p in bark if root+low<p[2]<root+high and .075<hypot(p[0]-cx,p[1]-cy)<.115}
                if len(around)<4:out.append((mesh['id'],'stem does not visibly twine around its post'));break
            if species=='Petrea volubilis':
                flowers=[p[2] for i in mesh.get('flower_face_indices',[]) for p in faces[i]]
                if not flowers or min(flowers)>root+2.40 or sum(z<root+2.60 for z in flowers)/len(flowers)<.85:
                    out.append((mesh['id'],'missing hanging Petrea flower spray clear below beams'))
        if species=='Eriobotrya japonica':
            if not mesh.get('leaf_records'):out.append((mesh['id'],'missing clustered loquat leaf records'))
            if 'g6-leaf-vein' not in mesh.get('face_materials',[]):out.append((mesh['id'],'missing physical loquat veins'))
            if 'g6-wire-tie' not in mesh.get('face_materials',[]):out.append((mesh['id'],'missing tier training ties'))
    for mesh in meshes:
        if mesh.get('g6_element')!='furniture':continue
        parts=mesh.get('seating_parts',{})
        if not all(parts.get(k) for k in ('timber-arm','timber-seat-slat','timber-back-slat','seat-cushion','back-cushion')):
            out.append((mesh['id'],'outdoor seating lacks slats, armrests or separate seat/back cushions'));continue
        bb=bounds(mesh)
        if not .76<=bb[5]-bb[2]<=.84:out.append((mesh['id'],'outdoor seating height outside recorded 800 mm ±5 percent'))
        for key,minimum in (('seat-cushion',.09),('back-cushion',.30)):
            z=[p[2] for i in parts[key] for p in mesh['faces'][i]]
            if max(z)-min(z)<minimum:out.append((mesh['id'],'outdoor cushion is thinner than authored lounge form'))
    return out
