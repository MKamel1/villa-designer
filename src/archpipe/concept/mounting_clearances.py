"""Clearances from approved candidate meshes, retaining authored envelopes.

Lengths are metres internally, millimetres in the exported table. Door
checks use the existing conservative swing squares, not a new door model.
The route engine retains its 20 mm raster and circular 914 mm path body.
"""
from copy import deepcopy
import math

from . import villa_furnish as F, villa_r11 as R, revit_spec as RS
from .fitting_mounting import bounds
from .. import catalogue as cat

BATH_ROOMS = ('guest-wc','family-bath','parents-ensuite')


def measured_items(scene, lay):
    """Move authored sanitary envelopes by actual mesh displacement.

    Keep the larger of the authored envelope and actual assembled geometry,
    including the projecting fittings. Never rerun on the old furniture list.
    """
    items = deepcopy(F.layout(lay))
    for item in items:
        if item.get('wet_zone'):
            floors=[m for m in scene['meshes'] if m['id'].startswith('furn-'+item['id']+'-')]
            if len(floors)!=1:
                raise ValueError(item['id']+': expected one measured open wet-floor mesh')
            bb=bounds(floors[0]);item['cx']=(bb[0]+bb[3])/2;item['cy']=(bb[1]+bb[4])/2
            item['w'],item['d'] = ((bb[3]-bb[0],bb[4]-bb[1]) if item['rot'] in (0,180) else (bb[4]-bb[1],bb[3]-bb[0]))
    rows = {r['id']:r for r in scene['mounting_movements'] if r['package']=='b-bathroom'}
    for item in items:
        if item['type'] not in ('wc','washbasin','washbasin_double'):
            continue
        members = [m for m in scene['meshes'] if m['id'].startswith('furn-'+item['id']+'-')]
        row = next(rows[m['id']] for m in members)
        item['cx'] += row['new'][0]-row['old'][0]
        item['cy'] += row['new'][1]-row['old'][1]
        slide = scene.get('wc_slides', {}).get(item['id'], {})
        item['cx'] += slide.get('delta', [0,0,0])[0]
        item['cy'] += slide.get('delta', [0,0,0])[1]
        original = F.footprint(item)
        actual = [bounds(m) for m in members]
        rect = [min([original[0]]+[b[0] for b in actual]), min([original[1]]+[b[1] for b in actual]),
                max([original[2]]+[b[3] for b in actual]), max([original[3]]+[b[4] for b in actual])]
        item['cx'],item['cy'] = (rect[0]+rect[2])/2,(rect[1]+rect[3])/2
        item['w'],item['d'] = ((rect[2]-rect[0],rect[3]-rect[1]) if item['rot'] in (0,180)
                              else (rect[3]-rect[1],rect[2]-rect[0]))
    # Low fittings do not consume the floor approach, but all shower assembly
    # projections are kept as conservative route obstacles where they are
    # within a body's working-height range. Ceiling drops are above that.
    for mesh in scene['meshes']:
        if mesh.get('mounting_package')=='b-bathroom' and mesh['id'].startswith('detail-'):
            bb = bounds(mesh)
            room = mesh.get('room')
            if room not in BATH_ROOMS or mesh.get('part_kind') not in ('shower-head','shower-hose','riser-rail','rail-bracket'):
                continue
            lv = lay['rooms'][room]['level']
            items.append(dict(id=mesh['id'],room=room,level=lv,type='wc',rot=0,
                cx=(bb[0]+bb[3])/2,cy=(bb[1]+bb[4])/2,w=bb[3]-bb[0],d=bb[4]-bb[1],h=max(.3,bb[5]-bb[2]),
                mounting_obstacle=True))
        if mesh.get('finished_host_id') and mesh.get('room') in BATH_ROOMS:
            host=scene['mounting_hosts'][mesh['finished_host_id']]
            if host['kind']=='wall':
                b=bounds(mesh); source=bounds(dict(faces=host['source_faces']))
                r=[min(b[i],source[i]) for i in range(3)]+[max(b[i],source[i]) for i in range(3,6)]
                items.append(dict(id=mesh['id'],room=mesh['room'],level=lay['rooms'][mesh['room']]['level'],type='wc',rot=0,
                    cx=(r[0]+r[3])/2,cy=(r[1]+r[4])/2,w=r[3]-r[0],d=r[4]-r[1],h=r[5]-r[2],mounting_obstacle=True))
    return items


def distance_rect(a,b):
    return math.hypot(max(a[0]-b[2],b[0]-a[2],0),max(a[1]-b[3],b[1]-a[3],0))


def front_distance(item, obstacles, width=None):
    """First obstruction over the entire frontage, using axis-aligned bounds."""
    a = F.footprint(item)
    axis = 0 if F.DIRS[item['rot']]['front'][0] else 1
    side = 1-axis
    direction = F.DIRS[item['rot']]['front'][axis]
    front = a[axis+2] if direction>0 else a[axis]
    lo,hi = a[side],a[side+2]
    if width is not None:
        centre = (lo+hi)/2; lo,hi = centre-width/2,centre+width/2
    candidates=[]
    for name,b in obstacles:
        if min(hi,b[side+2])-max(lo,b[side])<=1e-9:
            continue
        near,far = ((b[axis]-front,b[axis+2]-front) if direction>0 else
                    (front-b[axis+2],front-b[axis]))
        if far>1e-9:
            candidates.append((max(0,near),name))
    return min(candidates,default=(None,'MISSING obstruction/room boundary'))


def wc_side_clearances(item, obstacles, room_rect):
    """AD M Diagram 2.5: 350 mm on one centreline side, 1000 on the other.

    Check alongside the pan and its 1100 mm front zone. Basins on the
    rear wall may encroach up to 300 mm (diagram key f); any excess remains
    an obstruction. Mirror the orientation rather than fixing a handedness.
    """
    a=F.footprint(item)
    axis=0 if F.DIRS[item['rot']]['front'][0] else 1; side=1-axis
    sign=F.DIRS[item['rot']]['front'][axis]
    back=a[axis] if sign>0 else a[axis+2]
    front=(a[axis+2] if sign>0 else a[axis])+sign*1.1
    lo,hi=sorted((back,front)); centre=(a[side]+a[side+2])/2
    gaps=[centre-room_rect[side],room_rect[side+2]-centre]
    limiters=['finished room boundary','finished room boundary']
    for name,b,typ in obstacles:
        test_lo,test_hi=lo,hi
        if typ.startswith('washbasin'):
            if sign>0: test_lo=back+.3
            else: test_hi=back-.3
        if min(test_hi,b[axis+2])-max(test_lo,b[axis])<=1e-9: continue
        for index,direction in enumerate((-1,1)):
            near,far=((centre-b[side+2],centre-b[side]) if direction<0 else
                      (b[side]-centre,b[side+2]-centre))
            if far>1e-9 and max(0,near)<gaps[index]:
                gaps[index]=max(0,near);limiters[index]=name
    choices=[(min(gaps[i]/.35,gaps[1-i]/1.),i) for i in (0,1)]
    _,narrow=max(choices)
    return [(gaps[narrow],.35,limiters[narrow]),(gaps[1-narrow],1.,limiters[1-narrow])]


def same_wall_slide_feasibility(wc, basin, shower, finished_rect):
    """Continuous necessary constraints, proving both possible along-wall orders.

    No numerical search granularity can hide a slide. If this necessary
    interval test is feasible, a full route/door/zone solver is still needed.
    """
    if wc['rot'] != -90 or basin['rot'] != -90 or shower['rot'] != 180:
        raise ValueError('Slide feasibility needs measured same-wall fixtures and opposing shower')
    wall=finished_rect[1]; shower_front=F.footprint(shower)[1]
    # WC wall-side 350 mm and basin approach half-width 350 mm.
    wc_interval=[wall+.35, shower_front-.762-wc['w']/2]
    basin_interval=[wall+.35, shower_front-.762-basin['w']/2]
    separation=wc['w']/2+.7/2  # WC body must miss the full basin strip.
    capacities=[basin_interval[1]-wc_interval[0],wc_interval[1]-basin_interval[0]]
    return dict(status='NO FEASIBLE SLIDE' if max(capacities)<separation-1e-9 else 'NEEDS FULL SOLVER',
        wc_old_centre=[wc['cx'],wc['cy']],basin_old_centre=[basin['cx'],basin['cy']],
        wc_new_centre=[wc['cx'],wc['cy']],basin_new_centre=[basin['cx'],basin['cy']],
        wc_centre_interval_m=wc_interval,basin_centre_interval_m=basin_interval,
        required_centre_separation_mm=round(separation*1000,3),
        max_separation_wc_below_basin_mm=round(capacities[0]*1000,3),
        max_separation_basin_below_wc_mm=round(capacities[1]*1000,3),
        reason='Both along-wall orders fail necessary carded constraints; full WC wide-side, door and route constraints can only reduce feasibility. No change applied.',
        authorities=['ukadm-wc-access-zone-1100; Diagram 2.5: 350/1000 mm sides',
                     'ukadm-basin-access-zone-1100; 700 mm width', 'nkba-shower-clear-floor-762'])


def review(scene,lay=None):
    lay = lay or R.design('D1'); sp=RS.build(lay)
    items = measured_items(scene,lay)
    rows=[]
    def add(room,check,achieved,required,authority,detail=''):
        rows.append(dict(room=room,check=check,achieved_mm=None if achieved is None else round(achieved*1000,3),
            required_mm=None if required is None else round(required*1000,3),
            status='UNRESOLVED' if achieved is None or required is None else 'PASS' if achieved+1e-9>=required else 'FAIL',
            authority=authority,detail=detail))
    for room in BATH_ROOMS:
        lv=lay['rooms'][room]['level']
        walls=[('structural wall',r) for r in F._walls(sp,lv)]+[('column',r) for r in F._columns()]
        # Actual finished shell wall polygons: a thin obstacle at each room face.
        for mesh in scene['meshes']:
            if mesh.get('finished_host_id') and mesh.get('room')==room:
                host=scene['mounting_hosts'][mesh['finished_host_id']]
                if host['kind']=='wall':
                    bb=bounds(mesh); walls.append(('finished face '+mesh['id'],(bb[0],bb[1],bb[3],bb[4])))
        room_items=[it for it in items if it['room']==room]
        from .mounting import finish_from_record
        thickness=finish_from_record('marble-wall-thinset').thickness_m
        rect=F.clear_rect(lay,room)
        finished_rect=[rect[0]+thickness,rect[1]+thickness,rect[2]-thickness,rect[3]-thickness]
        for it in room_items:
            if it.get('mounting_obstacle') or it['type'] not in ('wc','washbasin','washbasin_double','bath','shower_walkin'):
                continue
            obstacles=walls+[(o['id'],F.footprint(o)) for o in room_items if o is not it and o['h']>=.3]
            width=.7 if it['type'].startswith('washbasin') else None
            achieved,limiter=front_distance(it,obstacles,width)
            required=cat.get(it['type']).clearance['front']/1000
            add(room,it['id']+' front approach',achieved,required,cat.get(it['type']).source,
                'limiter: '+limiter+('; 700 mm basin approach width' if width else ''))
            if it['type']=='wc':
                side_obstacles=[(name,b,'wall') for name,b in walls]+[(o['id'],F.footprint(o),o['type']) for o in room_items if o is not it and o['h']>=.3]
                for achieved,required,limiter in wc_side_clearances(it,side_obstacles,finished_rect):
                    add(room,it['id']+' centreline side '+str(int(required*1000)),achieved,required,
                        'card ukadm-wc-access-zone-1100; Diagram 2.5 printed p.20; 350/1000 mm sides',
                        'limiter: '+limiter+'; mirrored handedness; basin rear encroachment capped at 300 mm')
        if room=='family-bath':
            by={i['id']:i for i in room_items}
            feasibility=same_wall_slide_feasibility(by['fb-wc'],by['fb-basin'],by['fb-shower'],finished_rect)
        # All door swing regions touching this room, all floor-height items.
        rr=lay['rooms'][room]['rect']
        for zone in F._door_zones(sp,lay,lv):
            if room not in zone['door'].split('/') or not F._ov(zone['rect'],rr):
                continue
            distances=[(distance_rect(zone['rect'],F.footprint(it)),it['id'],F._ov(zone['rect'],F.footprint(it)))
                       for it in room_items if it['h']>=.3]
            distance,limiter,overlap=min(distances)
            add(room,'door swing '+zone['door'], -min(zone['rect'][2]-zone['rect'][0],zone['rect'][3]-zone['rect'][1]) if overlap else distance,
                0,'Existing project conservative door swing square; no overlap', 'limiter: '+limiter)
        # Rerun the full existing route algorithm with measured obstacles.
        level_items=[it for it in items if it['level']==lv]
        before_body=F.BODY; before_trace=F.TRACE
        try:
            F.TRACE={}
            failures=F.route_problems(lay,sp,level_items,lv,room_ids={room})
            affected=[p for p,_ in failures if '('+room+')' in p or '('+room+'+' in p or '+'+room+')' in p]
            # Measure achievable width in 10 mm increments using the same
            # route nodes and 20 mm spatial raster; capped at 1500 mm.
            low,high=0,150
            while low<high:
                mid=(low+high+1)//2; F.BODY=mid*.01
                fs=F.route_problems(lay,sp,level_items,lv,room_ids={room})
                if any('('+room+')' in p or '('+room+'+' in p or '+'+room+')' in p for p,_ in fs):
                    high=mid-1
                else: low=mid
            add(room,'door-to-all-fixtures route',low*.01,before_body,'card mitton-path-of-travel-min; printed p.68',
                '20 mm raster; achieved lower bound to 10 mm; '+('; '.join(affected) or 'all nodes reached'))
        finally:
            F.BODY=before_body; F.TRACE=before_trace
    guest=[it for it in items if it['room']=='guest-wc']
    wet=next(it for it in guest if it['id']=='gwc-shower'); wet_rect=F.footprint(wet)
    # Account for the east wall finish inside the authored floor rectangle.
    hosts=[h for h in scene['mounting_hosts'].values() if h['id']=='detail-gwc-hand-shower']
    wall=hosts[0]; finished_x=wall['structural_point'][0]+wall['normal'][0]*wall['finish']['thickness_m']
    wet_depth=min(wet_rect[2],finished_x)-wet_rect[0]
    add('guest-wc','open wet-zone depth',wet_depth,.8,'Lead authored 800 mm wet-zone design intent', 'after finished wall projection')
    add('guest-wc','open wet-zone carded minimum',wet_depth,.762,'card nkba-shower-clear-floor-762')
    add('guest-wc','open wet-zone length',wet_rect[3]-wet_rect[1],1.219,'Authored 1219 mm wet-zone length (assumption)')
    for it in guest:
        if it['id'] in ('gwc-wc','gwc-basin'):
            add('guest-wc',it['id']+' separation from wet floor',distance_rect(wet_rect,F.footprint(it)),0,
                'Client open-shower layout: no sanitary-body overlap with authored wet floor',
                'No verified splash-distance requirement; geometric separation only')
            if rows[-1]['achieved_mm']<=0:
                rows[-1]['status']='FAIL'
            if it['id']=='gwc-wc':
                axis_gap=wet_rect[0]-F.footprint(it)[2]
                add('guest-wc','gwc-wc horizontal wet-floor separation',axis_gap,0,
                    'Lead requirement: positive separation; model x direction', 'Expected about 95 mm; Euclidean separation reported separately')
                if axis_gap<=0: rows[-1]['status']='FAIL'
    drain=next(m for m in scene['meshes'] if m['id']=='detail-gwc-linear-drain'); bb=bounds(drain)
    clear=min(bb[0]-wet_rect[0],min(wet_rect[2],finished_x)-bb[3],bb[1]-wet_rect[1],wet_rect[3]-bb[4])
    add('guest-wc','drain within finished wet floor',clear,0,'Project containment: entire drain within finished wet floor')
    for it in guest:
        if it['id'] in ('gwc-wc','gwc-basin'):
            add('guest-wc','drain to '+it['id'],distance_rect((bb[0],bb[1],bb[3],bb[4]),F.footprint(it)),0,
                'Project non-intersection; no verified maintenance clearance')
    add('guest-wc','drain service/installation clearance',None,None,'MISSING manufacturer/plumbing requirement',
        'No invented minimum; containment and non-intersection do not prove drain service clearance')
    rows[-1]['status']='CONSTRUCTION REQUIREMENT'
    rows[-1]['authority']='Lead construction requirement: manufacturer installation data required'
    return dict(rows=rows,failures=[r for r in rows if r['status']=='FAIL'],
                unresolved=[r for r in rows if r['status']=='UNRESOLVED'],
                requirements=[r for r in rows if r['status']=='CONSTRUCTION REQUIREMENT'],
                family_slide_feasibility=feasibility)
