"""Finite intended exterior supports. Metres; 300 mm is a design search limit."""
from copy import deepcopy
from .fitting_mounting import bounds, normal, points, package
from .mounting import _on_polygon
from .support_mounting import datum

MAXIMUM_TRAVEL_M = .300


def finite_face(member, sources, outward, maximum=MAXIMUM_TRAVEL_M):
    """Require the complete conservative tangent envelope on one actual face.

    The envelope includes slots/branches, so disconnected fixing vertices
    cannot conceal an unsupported span. No infinite plane is a candidate.
    """
    bb = bounds(member)
    axis = max(range(3), key=lambda i: abs(outward[i]))
    tangents = [i for i in range(3) if i != axis]
    fixing = min(sum(p[i]*outward[i] for i in range(3)) for p in points(member))
    choices = []
    for source in sources:
        for face in source['faces']:
            if sum(normal(face)[i]*outward[i] for i in range(3)) < .999999:
                continue
            plane = sum(face[0][i]*outward[i] for i in range(3))
            travel = abs(plane-fixing)
            # Four envelope corners prove full coverage only on a convex
            # face. Refuse a concave face rather than bridging a notch/hole.
            polygon=[(p[tangents[0]],p[tangents[1]]) for p in face]
            turns=[]
            for index,a in enumerate(polygon):
                b=polygon[(index+1)%len(polygon)];c=polygon[(index+2)%len(polygon)]
                turn=(b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0])
                if abs(turn)>1e-12:turns.append(turn)
            if not turns or (min(turns)<0<max(turns)):continue
            corners = []
            for a in (bb[tangents[0]], bb[tangents[0]+3]):
                for b in (bb[tangents[1]], bb[tangents[1]+3]):
                    p = list(face[0]); p[tangents[0]]=a; p[tangents[1]]=b
                    p[axis]=(plane-sum(p[i]*outward[i] for i in tangents))/outward[axis]
                    corners.append(p)
            if travel <= maximum+1e-9 and all(_on_polygon(p,face,outward) for p in corners):
                choices.append((travel,source,face))
    if not choices:
        raise ValueError(member['id']+': refused host: finite fixing envelope required within 300 mm')
    return min(choices,key=lambda row:row[0])[1:]


def yard_sources(scene):
    """Declare external yard edges; building edges remain building hosts.

    YARD is the modeled polygon. Three edges overlap modeled whole-plot
    fence solids; their inner faces retain the real 250 mm wall thickness.
    Shared-axis edges have no modeled wall solid: polygon edge is declared
    inner structural face, with wall construction explicitly unverified.
    """
    from .villa_landscape import YARD
    from .. import villa_env as E
    area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(YARD,YARD[1:]+YARD[:1]))
    result=[]
    for index,(a,b) in enumerate(zip(YARD,YARD[1:]+YARD[:1])):
        if index not in (0,1,5,6,7): continue
        dx,dy=b[0]-a[0],b[1]-a[1];length=(dx*dx+dy*dy)**.5
        sign=1 if area>0 else -1; inward=(-dy/length*sign,dx/length*sign,0)
        source_id={0:'fence-street',6:'fence-rear',7:'fence-east'}.get(index)
        if source_id:
            actual=next(m for m in scene['meshes'] if m.get('source_id')==source_id)
            face=next(f for f in actual['faces'] if sum(normal(f)[i]*inward[i] for i in range(3))>.999999)
            # Clip the actual solid face to this finite yard edge.
            axis=0 if abs(inward[0])>.5 else 1;other=1-axis
            lo,hi=sorted((a[other],b[other]))
            face=deepcopy(face)
            for p in face:p[other]=max(lo,min(hi,p[other]))
            material=actual['material'];thickness=E.FENCE_T/1000
            basis='Actual modeled fence inner face; yard edge is outer plot line'
        else:
            face=[[a[0],a[1],E.B/1000],[b[0],b[1],E.B/1000],
                  [b[0],b[1],(E.B+E.FENCE_H)/1000],[a[0],a[1],(E.B+E.FENCE_H)/1000]]
            if sum(normal(face)[i]*inward[i] for i in range(3))<0:face.reverse()
            material='paint-exterior-grey-green';thickness=None
            basis='No modeled wall solid: polygon edge declared inner structural face; wall/height construction UNVERIFIED'
        source=dict(id='yard-boundary-edge-'+str(index),faces=[face],material=material,
                    group='shell',part_kind='finish-layer',label=basis,visibility={'camera':False},
                    diagnostic=True,
                    yard_edge_index=index,wall_thickness_m=thickness,datum_basis=basis)
        scene.setdefault('diagnostic_meshes', []).append(source)
        host=datum(scene,source,face,inward,source['id'],'wall')
        scene['mounting_hosts'][host.id].update(wall_thickness_m=thickness,datum_basis=basis,
            maximum_authored_travel_m=MAXIMUM_TRAVEL_M,finish_basis='Modeled exterior paint/render; build-up UNVERIFIED; finished face = modeled face')
        result.append((source,host))
    return result


def exterior_host(scene, member, lay, identifier):
    """Outdoor side has no room; the inward side adjoins the authored room."""
    bb=bounds(member);anchor=[(bb[i]+bb[i+3])/2 for i in range(3)]
    eligible=[]
    for source in scene['meshes']:
        if source.get('source_id')!='villa-shell' or source['material']!='paint-exterior-grey-green':continue
        for face in source['faces']:
            outward=normal(face)
            if abs(outward[2])>1e-8:continue
            gap=sum((anchor[i]-face[0][i])*outward[i] for i in range(3))
            projected=[anchor[i]-gap*outward[i] for i in range(3)]
            def rooms_on_side(sign):
                probe=[projected[i]+sign*.300*outward[i] for i in range(3)]
                return [rid for rid,r in lay['rooms'].items() if r['level']==('B' if anchor[2]<0 else 'GF')
                        and r['rect'][0]<probe[0]<r['rect'][2] and r['rect'][1]<probe[1]<r['rect'][3]]
            inside=rooms_on_side(-1);outside=rooms_on_side(1)
            if member['room'] not in inside or outside:continue
            candidate=dict(source,faces=[face])
            try:selected,chosen=finite_face(member,[candidate],outward)
            except ValueError:continue
            eligible.append((abs(gap),selected,chosen,outward,inside))
    if not eligible:raise ValueError(identifier+': refused exterior host: finite coverage, 300 mm limit and room adjacency required')
    _,source,face,outward,inside=min(eligible,key=lambda row:row[0])
    host=datum(scene,source,face,outward,identifier,'wall')
    scene['mounting_hosts'][identifier].update(interior_rooms=inside,outdoor_rooms=[],
        side_basis='Room adjacency: inward has authored room, outward has no room',maximum_authored_travel_m=MAXIMUM_TRAVEL_M)
    return host


def mount_landscape(scene, member, sources, *, model_side=None):
    """Mount on an explicit model-side face, or the legacy garden-side suffix.

    A rear-garden espalier can use its east boundary without naming the
    entire assembly as the east yard. model_side is +x, -x, +y or -y.
    """
    from ..orientation import side_name
    direction=side_name(model_side) if model_side is not None else member['id'].rsplit('-',1)[1]
    outward={side_name('+x'):(-1,0,0),side_name('-x'):(1,0,0),side_name('+y'):(0,-1,0),side_name('-y'):(0,1,0)}[direction]
    source,face=finite_face(member,[s for s,h in sources],outward)
    host=next(h for s,h in sources if s['id']==source['id'])
    fixing=min(sum(p[i]*outward[i] for i in range(3)) for p in points(member))
    package(scene,[member],host,fixing,'e-support',member['id'])
    if scene['mounting_hosts'][host.id].get('wall_thickness_m') is None:
        member['mounting']['installation_status']='CONSTRUCTION REQUIREMENT: polygon inner-face datum only; no modeled boundary wall solid; wall thickness, height, fixing and capacity UNVERIFIED'


def apply_lead_review(scene):
    """Apply frozen approved rows; obsolete inward grille datums are retired."""
    import json
    from pathlib import Path
    authority=json.loads((Path(__file__).resolve().parents[3]/'knowledge/c4-e-lead-approvals.json').read_text())
    from ..orientation import historical_aliases
    authority = historical_aliases(authority)
    retired={'host-face-support-detail-vent-'+room+'-grille' for room in ('guest-wc','dirty-kitchen')}
    rows = {r['id']: r for r in scene['mounting_movements']}
    render_meshes = {m['id']: m for m in scene['meshes']}
    diag_meshes = {m['id']: m for m in scene.get('diagnostic_meshes', [])}
    scene['e_lead_review'] = dict(applied=[], retired_inward_datums=sorted(retired), rejected=authority['rejected'])
    scene['e_approved_associated_movements'] = []
    scene['e_approved_light_movements'] = []
    for approved in authority['rows']:
        mid = approved['id']
        if mid in retired:
            if mid in rows: raise ValueError(mid + ': obsolete inward grille movement still exists')
            replacement = scene['mounting_hosts'][mid.removeprefix('host-face-')]
            if replacement.get('side_basis') is None: raise ValueError(mid + ': exterior replacement has no adjacency proof')
            continue
        if mid not in rows:
            raise KeyError(mid + ': approved row not in scene mounting movements')
        row = rows[mid]
        if row['host_id'] != approved['host_id'] or any(abs(a-b) > 1e-8 for key in ('old', 'new') for a, b in zip(row[key], approved[key])):
            raise ValueError(mid + ': approved schedule drift; new lead review required')
        if mid in render_meshes and mid in diag_meshes:
            raise ValueError(mid + ': present in both render meshes and diagnostics channel')
        delta = [row['new'][i] - row['old'][i] for i in range(3)]
        if mid in render_meshes:
            target = render_meshes[mid]
            from .attached_assembly import translate
            carried = translate(scene, mid, delta)
            target.get('mounting', {}).pop('approval', None)
            scene['e_approved_associated_movements'].extend(r for r in carried if r['id'] != mid)
        elif mid in diag_meshes:
            target = diag_meshes[mid]
            target['faces'] = deepcopy(row['proposed_faces'])
            target.get('mounting', {}).pop('approval', None)
        else:
            raise KeyError(mid + ': approval row id is in neither render meshes nor diagnostics channel')
        row['approval'] = 'APPROVED lead 2026-10-05; APPLIED'
        scene['e_lead_review']['applied'].append(mid)
        # Wall markers emit through their mesh material, with no analytical
        # light record. Cabinet strips have a separate analytical emitter.
        light_id = mid.removeprefix('detail-cabinet-led-') if mid.startswith('detail-cabinet-led-') else None
        if light_id:
            light = next(l for l in scene['lights'] if l['id'] == light_id)
            old = list(light['position']); light['position'] = [old[i] + delta[i] for i in range(3)]
            scene['e_approved_light_movements'].append(dict(id=light_id, root_id=mid, old=old, new=light['position'], delta=delta,
                basis='Emitter follows approved fitting geometry; intensity unchanged; independent remeasurement required'))
    # Room-labelled shell meshes split one real wall across materials. Attach
    # the hood to the actual coplanar wall patches, never their extension.
    mid = 'appliance-hood-dirty-canopy'
    record = scene['mounting_hosts'][render_meshes[mid]['mounting']['host_id']]
    outward=record['normal'];origin=record['structural_point'];depth=record['finish']['thickness_m']
    for source in list(scene['meshes']):
        if source.get('source_id')!='villa-shell' or source['material'] not in ('marble-bath','plaster-warm-white','porcelain-tile'):continue
        faces=[f for f in source['faces'] if sum(normal(f)[i]*outward[i] for i in range(3))>.999999
               and all(abs(sum((p[i]-origin[i])*outward[i] for i in range(3)))<1e-8 for p in f)]
        if not faces:continue
        scene.setdefault('diagnostic_meshes', []).append(dict(id='hood-support-patch-'+source['id'],faces=[[[p[i]+depth*outward[i] for i in range(3)] for p in f] for f in faces],
            group='shell',material=record['source_material'],part_kind='finish-layer',label='Actual coplanar wall support; approved plaster build-up',
            finished_host_id=record['id'],source_mesh=source['id'],source_faces=deepcopy(faces),visibility={'camera':False},diagnostic=True))
