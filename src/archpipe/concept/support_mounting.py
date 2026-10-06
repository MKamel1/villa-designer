"""C4(e): finite support datums and rigid generated assembly relationships.

All coordinates are metres. Unknown finish build-ups retain modeled levels.
Only movements of at most five millimetres are applied; larger proposals
retain their original geometry and explicit pending contracts.
"""
from copy import deepcopy
from dataclasses import asdict
import math
import re

from .mounting import Host, Finish, MountItem, binding, SITE_KINDS, _on_polygon
from .fitting_mounting import points, bounds, normal, package, measured_host


def plant_support_face(scene, prop):
    """Measure the highest upward face at the plant's named support point.

    The support identifier names either the room's finished floor or an
    authored furniture assembly. Coordinates and elevations are metres.
    Diagnostic host copies are excluded: the physical source is authoritative.
    """
    support = prop.get('support_id')
    if support == 'finished-floor':
        sources = [m for m in scene['meshes'] if m['id'] == 'floor-' + prop['room']]
    elif support:
        sources = [m for m in scene['meshes'] if m['id'].startswith('furn-' + support + '-')
                   and m.get('room') == prop.get('room')]
    else:
        sources = []
    x, y, _ = prop['position']
    choices = [(source, face) for source in sources for face in source['faces']
               if normal(face)[2] > .999999 and
               _on_polygon((x, y, face[0][2]), face, (0, 0, 1))]
    if not choices:
        raise ValueError(prop['id'] + ': MISSING finite named plant support')
    return max(choices, key=lambda pair: pair[1][0][2])


def bind_plant_support(scene, prop):
    """Record the actual contact face, never the supporting assembly's root."""
    source, face = plant_support_face(scene, prop)
    floor = prop['support_id'] == 'finished-floor'
    host = datum(scene, source, face, (0, 0, 1), 'support-prop-' + prop['id'],
                 'floor' if floor else 'joinery-panel')
    prop['mounting'] = binding(MountItem(prop['id']), host, 0,
                               'floor-standing' if floor else 'surface-mounted')


def plant_support_findings(scene, placed=None):
    """Compare plant bases and recorded datums independently with live faces.

    The existing 1 mm model comparison tolerance is retained. Missing sources,
    contracts and host records fail closed, including removed or moved supports.
    """
    failures = []
    for prop in scene.get('props', []) if placed is None else placed:
        if not prop.get('indoor_plant'):
            continue
        try:
            source, face = plant_support_face(scene, prop)
        except ValueError as exc:
            failures.append(str(exc))
            continue
        level = face[0][2]
        if abs(prop['position'][2] - level) > .001:
            failures.append(prop['id'] + ' base is below or above its finished support')
        contract = prop.get('mounting', {})
        host = scene.get('mounting_hosts', {}).get(contract.get('host_id'), {})
        recorded = contract.get('finished_face', [])
        point = host.get('structural_point', [])
        if (host.get('source_mesh') != source['id'] or host.get('normal') not in ((0, 0, 1), [0, 0, 1])
                or len(recorded) != 3 or len(point) != 3 or
                abs(recorded[2] - level) > .001 or abs(point[2] - level) > .001):
            failures.append(prop['id'] + ': stale or MISSING recorded plant support datum')
    return failures


def datum(scene, source, face, outward, identifier, kind):
    host = Host(identifier, kind, tuple(face[0]), tuple(outward),
                Finish('modeled finished '+source['material']+'; build-up UNVERIFIED; level retained', 0))
    coplanar = [f for f in source['faces'] if all(abs(sum((p[i]-face[0][i])*outward[i]
                    for i in range(3))) < 1e-8 for p in f)]
    scene['mounting_hosts'][identifier] = dict(asdict(host), source_mesh=source['id'],
        source_faces=deepcopy(coplanar), source_material=source['material'], finish_status='UNVERIFIED')
    scene.setdefault('diagnostic_meshes', []).append(dict(id='host-face-'+identifier, material=source['material'],
        faces=deepcopy(coplanar), group='shell', room=source.get('room'), part_kind='finish-layer',
        diagnostic=True,
        label='Measured support datum: '+identifier, finished_host_id=identifier, visibility={'camera':False}))
    return host


def nearest(scene, anchor, outward, sources, identifier, kind, maximum=.25):
    choices=[]
    for source in sources:
        for face in source['faces']:
            if sum(normal(face)[i]*outward[i] for i in range(3)) < .999999:
                continue
            gap=sum((anchor[i]-face[0][i])*outward[i] for i in range(3))
            projected=[anchor[i]-gap*outward[i] for i in range(3)]
            if abs(gap)<=maximum and _on_polygon(projected,face,outward):
                choices.append((abs(gap),source,face))
    if not choices:
        raise ValueError(identifier+': no finite intended support face')
    _,source,face=min(choices,key=lambda c:c[0])
    return datum(scene,source,face,outward,identifier,kind)


def floor_assembly(scene, members, host, identifier):
    """Root touches the floor; children retain the generated root projection."""
    root=min(members,key=lambda m:bounds(m)[2])
    fixing=bounds(root)[2]
    delta=[0,0,host.structural_point[2]-fixing]
    floor_bounds=bounds(dict(faces=scene['mounting_hosts'][host.id]['source_faces']))
    assembly_bounds=[min(bounds(m)[i] for m in members) for i in range(3)]+[max(bounds(m)[i] for m in members) for i in range(3,6)]
    for axis in (0,1):
        # A full-span assembly is placed from exact support edges, rather
        # than a rounded centre that shifts both ends outside their datums.
        if abs((assembly_bounds[axis+3]-assembly_bounds[axis])-(floor_bounds[axis+3]-floor_bounds[axis]))<1e-8:
            delta[axis]=(floor_bounds[axis]+floor_bounds[axis+3]-assembly_bounds[axis]-assembly_bounds[axis+3])/2
    for member in members:
        before=deepcopy(member)
        proposed=[[[p[i]+delta[i] for i in range(3)] for p in f] for f in member['faces']]
        projection=bounds(member)[2]-fixing
        contract=binding(MountItem(member['id']),host,0,'floor-standing')
        if member is not root:
            contract.update(geometry_role='assembly-child',assembly_root=root['id'],
                child_projection_m=projection, projection_basis='Generated assembly relative to its floor-bearing root')
        mm=math.sqrt(sum(d*d for d in delta))*1000
        applied=mm<=5+1e-9
        member['mounting']=contract
        member['mounting_package']='e-support'
        if applied: member['faces']=proposed
        else: contract['approval']='PENDING'
        scene['mounting_movements'].append(dict(id=member['id'],package='e-support',host_id=host.id,
            old=bounds(before),new=bounds(dict(faces=proposed)),mm=round(mm,6),
            why='Floor-bearing assembly; modeled finished level; build-up UNVERIFIED',
            approval='APPLIED <=5 mm' if applied else 'PENDING',proposed_faces=proposed))


def shelf_side(scene, bb, sources, identifier):
    choices=[]
    for outward in ((1,0,0),(-1,0,0)):
        anchor=[bb[0] if outward[0]>0 else bb[3],(bb[1]+bb[4])/2,(bb[2]+bb[5])/2]
        for source in sources:
            for face in source['faces']:
                if sum(normal(face)[i]*outward[i] for i in range(3))<.999999: continue
                gap=(anchor[0]-face[0][0])*outward[0]
                projected=[face[0][0],anchor[1],anchor[2]]
                if abs(gap)<.25 and _on_polygon(projected,face,outward):
                    choices.append((abs(gap),source,face,outward))
    if not choices: raise ValueError(identifier+': no finite shelf side panel')
    _,source,face,outward=min(choices,key=lambda c:c[0])
    return datum(scene,source,face,outward,identifier,'joinery-panel')


def migrate(scene, lay):
    from . import villa_furnish as F, villa_lighting as VL
    original=list(scene['meshes'])
    from .exterior_mounting import yard_sources, mount_landscape, exterior_host
    yard_hosts=yard_sources(scene)
    movement_start=len(scene['mounting_movements'])
    scene['support_light_movements']=[]
    scene['support_associated_movements']=[]
    missing=[m for m in original if (m.get('part_kind') in SITE_KINDS or m['id'].startswith('furn-')) and not m.get('mounting')]
    scene['support_inventory_before']=[m['id'] for m in missing]
    furniture=F.layout(lay)
    groups={}
    wall_types={'tv_unit','screen'}
    for member in missing:
        if not member['id'].startswith('furn-'): continue
        # Longest authored identifier prevents a desk swallowing its chairs.
        candidates=[it for it in furniture if member['id'].startswith('furn-'+it['id']+'-')]
        key=max(candidates,key=lambda it:len(it['id']))['id'] if candidates else re.sub(r'-\d+$','',member['id'][5:])
        # Generated chair children have their own floor bearing.
        chair=re.search(r'^(.*-chair-\d+)-\d+$',member['id'][5:])
        if chair: key=chair.group(1)
        groups.setdefault(key,[]).append(member)
    for key,members in groups.items():
        root=min(members,key=lambda m:bounds(m)[2]); bb=bounds(root);room=root['room']
        anchor=[(bb[0]+bb[3])/2,(bb[1]+bb[4])/2,bb[2]]
        item=next((it for it in furniture if it['id']==key),None)
        if root.get('part_kind') in wall_types and item:
            front=F.DIRS[item['rot']]['front'];outward=(*front,0)
            if root.get('part_kind')=='screen':
                host=nearest(scene,anchor,outward,[m for m in original if m['group']=='shell'
                    and m.get('room')==room and m['material']=='taupe-fabric'],'support-'+key,'wall')
            else:
                host=measured_host(scene,tuple(anchor),outward,room,'support-'+key)
            # All television assembly pieces share the authored rear plane.
            fixing=min(sum(p[i]*outward[i] for i in range(3)) for m in members for p in points(m))
            package(scene,members,host,fixing,'e-support',root['id'])
        elif item and (item.get('wet_zone') or (room=='family-bath' and item['type']=='shower_walkin')):
            # The modeled open-shower finish and its drain retain their falls
            # and depth; use the actual finish top, not an invented floor stack.
            host=nearest(scene,anchor,(0,0,1),[m for m in original if m['id']=='floor-'+room],
                         'support-'+key,'floor')
            for member in members:
                if member is not root:
                    child_host=nearest(scene,[anchor[0],anchor[1],bounds(member)[2]],(0,0,1),[root],
                        'support-'+member['id'],'joinery-panel')
                    member['mounting']=binding(MountItem(member['id']),child_host,0,'surface-mounted')
                    member['mounting_package']='e-support'
                    continue
                depth=host.structural_point[2]-bounds(member)[2]
                record=scene['mounting_hosts'][host.id];record['void_depth_m']=depth
                member['mounting']=dict(binding(MountItem(member['id'],depth),
                    Host(host.id,host.kind,host.structural_point,host.normal,host.finish,depth),0,'recessed'),
                    installation_status='CONSTRUCTION REQUIREMENT: falls/waterproofing/manufacturer data required')
                member['mounting_package']='e-support'
        else:
            sources=[m for m in original if m['id']=='floor-'+room]
            if not sources and room=='stair-b': sources=[m for m in original + scene.get('diagnostic_meshes', []) if m['id']=='finish-stair-basement-floor-host']
            if room=='parents-dressing-ext':
                sources=[m for m in original if m['id'] in ('floor-parents-dressing-ext','floor-parents-dressing')]
            host=nearest(scene,anchor,(0,0,1),sources,'support-'+key,'floor')
            floor_assembly(scene,members,host,key)
            for source in original:
                if not source['id'].startswith('floor-'): continue
                faces=[f for f in source['faces'] if normal(f)[2]>.999999 and
                    all(abs(p[2]-host.structural_point[2])<1e-8 for p in f)]
                if faces:
                    scene.setdefault('diagnostic_meshes', []).append(dict(id=host.id+'-patch-'+source['id'],material=source['material'],
                        faces=deepcopy(faces),group='shell',room=source.get('room'),part_kind='finish-layer',
                        diagnostic=True,
                        label='Actual coplanar finished floor support patch',finished_host_id=host.id,visibility={'camera':False}))

    # Remaining site parts bind to their intended source, never to their own
    # bounds. Joinery sources include the moved candidate assemblies.
    for member in missing:
        if member.get('mounting'): continue
        mid=member['id'];bb=bounds(member);room=member.get('room')
        anchor=[(bb[0]+bb[3])/2,(bb[1]+bb[4])/2,(bb[2]+bb[5])/2]
        kind=member.get('part_kind');host_id='support-'+mid
        if kind=='curtain-track':
            from .ceiling_mounting import ceiling_host
            anchor[2]=bb[5];host=ceiling_host(scene,anchor,room,host_id)
            package(scene,[member],host,-bb[5],'e-support',mid)
            # Adjacent room soffits at the identical level form real support
            # patches; do not extend the selected polygon across a gap.
            for source in original:
                if source['group']!='shell' or source['material']!='ceiling-white': continue
                faces=[f for f in source['faces'] if normal(f)[2]<-.999999 and
                    all(abs(p[2]-host.structural_point[2])<1e-8 for p in f)]
                if faces:
                    scene.setdefault('diagnostic_meshes', []).append(dict(id=host_id+'-patch-'+source['id'],material=source['material'],
                        faces=deepcopy(faces),group='shell',room=source.get('room'),part_kind='finish-layer',
                        diagnostic=True,
                        label='Actual adjacent coplanar ceiling support',finished_host_id=host.id,visibility={'camera':False}))
            if room=='parents-bed' and bb[1]<F.clear_rect(lay,room)[1]:
                # Full track end overruns the actual ceiling; list a tangential
                # translation, without shortening or applying the correction.
                from . import villa_furnish as F
                shift=F.clear_rect(lay,room)[1]-bb[1]
                proposed=[[[p[0],p[1]+shift,p[2]] for p in f] for f in member['faces']]
                member['mounting']['approval']='PENDING'
                scene['mounting_movements'].append(dict(id=mid,package='e-support',host_id=host.id,
                    old=bb,new=bounds(dict(faces=proposed)),mm=round(shift*1000,6),
                    why='Curtain-track end overruns finite parents ceiling; same-ceiling tangential proposal',
                    approval='PENDING',proposed_faces=proposed))
        elif mid.startswith('landscape-'):
            mount_landscape(scene,member,yard_hosts)
        elif kind=='stair-stringer':
            host=nearest(scene,[anchor[0],anchor[1],bb[2]],(0,0,1),
                [m for m in original + scene.get('diagnostic_meshes', []) if m['id']=='finish-stair-basement-floor-host'],host_id,'floor')
            floor_assembly(scene,[member],host,mid)
        elif kind=='drain':
            wet=next(m for m in scene['meshes'] if m['id']=='furn-gwc-shower-0')
            level=max(p[2] for p in points(wet));face=[[bb[0],bb[1],level],[bb[3],bb[1],level],[bb[3],bb[4],level],[bb[0],bb[4],level]]
            # Select the actual full wet-floor top, not the drain footprint.
            face=next(f for f in wet['faces'] if normal(f)[2]>.999999)
            host=datum(scene,wet,face,(0,0,1),host_id,'floor')
            depth=level-bb[2];scene['mounting_hosts'][host.id]['void_depth_m']=depth
            host=Host(host.id,host.kind,host.structural_point,host.normal,host.finish,depth)
            member['mounting']=dict(binding(MountItem(mid,depth),host,0,'recessed'),
                installation_status='CONSTRUCTION REQUIREMENT: manufacturer installation data required')
            member['mounting_package']='e-support'
        elif kind=='fan-grille':
            host=exterior_host(scene,member,lay,host_id)
            fixing=min(sum(p[i]*host.normal[i] for i in range(3)) for p in points(member))
            package(scene,[member],host,fixing,'e-support',mid)
        elif kind in ('wall-panel','wall-marker') or 'hood-' in mid:
            outward=(0,-1,0) if mid=='detail-tv-fluting' or 'hood-' in mid else (0,1,0)
            if 'hood-' in mid: anchor[1]=bb[4]
            if kind=='wall-marker' and mid.startswith('marker-STEP-'):
                record=scene['mounting_hosts']['stair-party-wall']
                host=Host(record['id'],record['kind'],tuple(record['structural_point']),tuple(record['normal']),Finish(**record['finish']))
            else: host=measured_host(scene,anchor,outward,room,host_id)
            fixing=min(sum(p[i]*outward[i] for i in range(3)) for p in points(member))
            package(scene,[member],host,fixing,'e-support',mid)
            if kind=='wall-marker':
                member['mounting']['installation_status']='CONSTRUCTION REQUIREMENT: selected recessed housing depth and installation data MISSING; visible face only'
        else:
            sources=[m for m in scene['meshes'] if m['group']=='furniture' and m.get('room')==room and m['id'].startswith('furn-')]
            if kind in ('downlight-trim','light-lens'):
                sources=[m for m in sources if m['id']=='furn-library-daybed-0']
                outward=(0,0,-1);anchor[2]=bb[5]
            elif kind in ('lamp-head','lamp-arm') or 'coffee-' in mid:
                outward=(0,0,1);anchor[2]=bb[2] if kind!='lamp-head' else bb[2]-.44
                sources=[m for m in sources if m.get('part_kind') in ('desk','base_run')]
            elif kind=='appliance-housing': outward=(0,-1,0)
            else: outward=(0,1,0)
            # Lamp heads use the arm's table fixing as their assembly datum.
            members=[member]
            if kind=='downlight-trim':
                members=[member,next(m for m in missing if m['id']==mid.replace('fix-','lens-'))]
            if mid.startswith('dress-'):
                sources=[m for m in sources if m.get('part_kind')=='wardrobe']
                outward=(-1,0,0) if mid.endswith('bracket-right') else (1,0,0)
                anchor[0]=bb[3] if outward[0]<0 else bb[0]
            if kind=='lamp-head':
                arm=next(m for m in missing if m['id']==mid.replace('lamp-shade-','lamp-arm-'))
                members=[arm,member];ab=bounds(arm);anchor=[(ab[0]+ab[3])/2,(ab[1]+ab[4])/2,ab[2]]
            if mid.startswith('dress-') and kind=='shelf':
                host=shelf_side(scene,bb,sources,host_id);outward=host.normal
            else: host=nearest(scene,anchor,outward,sources,host_id,'joinery-panel')
            fixing=min(sum(p[i]*outward[i] for i in range(3)) for m in members for p in points(m))
            if kind=='hanging-rail':
                fixing=sum(host.structural_point[i]*outward[i] for i in range(3))
            package(scene,members,host,fixing,'e-support',members[0]['id'])
            if kind=='hanging-rail':
                member['mounting']['support_parts']=[mid+'-bracket-left',mid+'-bracket-right']
            if kind in ('downlight-trim','lamp-head'):
                row=scene['mounting_movements'][-len(members)]
                if row['approval']!='PENDING':
                    delta=[row['new'][i]-row['old'][i] for i in range(3)]
                    light_id=mid.replace('fix-','').replace('lamp-shade-','')
                    light=next(l for l in scene['lights'] if l['id']==light_id)
                    old=list(light['position']);light['position']=[old[i]+delta[i] for i in range(3)]
                    scene['support_light_movements'].append(dict(id=light_id,old=old,new=light['position'],delta=delta,
                        basis='Rigid movement with actual emitting assembly; photometric intensities unchanged; remeasurement required'))
            if kind=='downlight-trim':
                from .ceiling_requirements import product_depth
                product=product_depth('DLN');req=next(r for r in scene['ceiling_requirements'] if mid[4:] in r['fitting_ids'])
                record=scene['mounting_hosts'][host.id]
                record.update(void_depth_m=req['required_void_mm']/1000,void_status='requirement',
                    housing_source=product['source'],clearance_source=req['clearance_source'])
                member['mounting'].update(kind='recessed',geometry_role='recessed-trim',offset_m=0,
                    housing_depth_m=product['housing_depth_mm']/1000,resolution_status='requirement',
                    installation_clearance_m=req['clearance_mm']/1000)
    scene['notes'].append('C4(e) floor hosts retain modeled finished elevations; oak/underlay and other floor stacks UNVERIFIED. Support capacities and recessed marker housings require construction coordination.')
    for row in scene['mounting_movements'][movement_start:]: row['package']='e-support'
    scene['ceiling_deferred_joinery']=[]
    # Imported replacements and cloth must follow the same approved floor
    # correction as their collision meshes. Props follow their containing
    # furniture assembly, or the actual modeled floor below them.
    for model in scene.get('models',[]):
        members=[m for m in scene['meshes'] if m['id'].startswith(model['replaces'])]
        row=next((r for r in scene['mounting_movements'][movement_start:] if any(m['id']==r['id'] for m in members)
                  and r['approval']!='PENDING'),None)
        if row:
            delta=[row['new'][i]-row['old'][i] for i in range(3)]
            old=list(model['position']);model['position']=[old[i]+delta[i] for i in range(3)]
            model['mounting']=deepcopy(members[0]['mounting'])
            scene['support_associated_movements'].append(dict(id=model['id'],old=old,new=model['position'],delta=delta))
    for cloth in scene.get('cloth',[]):
        root_id=next((key for key in groups if key in cloth['id']),None)
        if root_id is None: continue
        row=next(r for r in scene['mounting_movements'][movement_start:] if r['id']==groups[root_id][0]['id'])
        if row['approval']=='PENDING': continue
        delta=row['new'][2]-row['old'][2]
        old=cloth['z_start'];cloth['z_start']+=delta
        if 'mattress_top' in cloth: cloth['mattress_top']+=delta
        cloth['mounting']=deepcopy(groups[root_id][0]['mounting'])
        scene['support_associated_movements'].append(dict(id=cloth['id'],old=old,new=cloth['z_start'],delta=[0,0,delta]))
    for prop in scene.get('props',[]):
        p=prop.get('position')
        if p is None or prop['id'].startswith('landscape-'): continue
        if prop.get('indoor_plant'):
            # Explicit plant supports replace containment-based assembly
            # inference, which copied a table's floor-bearing child contract.
            _, face = plant_support_face(scene, prop)
            delta = [0, 0, face[0][2] - p[2]]
            if abs(delta[2]) > .005 + 1e-9:
                raise ValueError(prop['id'] + ': plant support movement exceeds 5 mm; approval required')
            old = list(p)
            prop['position'] = [p[i] + delta[i] for i in range(3)]
            bind_plant_support(scene, prop)
            scene['support_associated_movements'].append(dict(id=prop['id'], old=old,
                new=prop['position'], delta=delta))
            continue
        choices=[]
        for key,members in groups.items():
            rows=[r for r in scene['mounting_movements'][movement_start:] if r['id'] in {m['id'] for m in members}]
            if not rows or any(r['approval']=='PENDING' for r in rows): continue
            old=[min(r['old'][i] for r in rows) for i in range(3)]+[max(r['old'][i] for r in rows) for i in range(3,6)]
            if old[0]<=p[0]<=old[3] and old[1]<=p[1]<=old[4] and old[2]<=p[2]<=old[5]+.02:
                choices.append((abs(p[2]-old[5]),rows[0],members[0]['mounting']))
        if choices:
            _,row,contract=min(choices,key=lambda c:c[0]);delta=[row['new'][i]-row['old'][i] for i in range(3)]
        else:
            floors=[m for m in original if m['id'].startswith('floor-') and bounds(m)[0]<=p[0]<=bounds(m)[3]
                    and bounds(m)[1]<=p[1]<=bounds(m)[4] and abs(bounds(m)[2]-p[2])<=.005]
            if not floors: continue
            source=min(floors,key=lambda m:abs(bounds(m)[2]-p[2]));delta=[0,0,bounds(source)[2]-p[2]]
            host=datum(scene,source,source['faces'][0],(0,0,1),'support-prop-'+prop['id'],'floor')
            contract=binding(MountItem(prop['id']),host,0,'floor-standing')
        old=list(p);prop['position']=[p[i]+delta[i] for i in range(3)];prop['mounting']=deepcopy(contract)
        scene['support_associated_movements'].append(dict(id=prop['id'],old=old,new=prop['position'],delta=delta))
