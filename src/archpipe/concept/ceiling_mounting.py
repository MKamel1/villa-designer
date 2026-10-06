"""Package d: finite finished ceilings and separately sourced construction void targets."""
from copy import deepcopy
from dataclasses import asdict
import math

from .fitting_mounting import normal, points, bounds, package
from .mounting import Host, Finish, _on_polygon, binding, MountItem
from . import villa_lighting as VL


def ceiling_host(scene, anchor, room, identifier):
    """Find the actual downward polygon over the fixing, including ramp soffits."""
    choices = []
    if '_ceiling_sources' not in scene:
        scene['_ceiling_sources'] = [(mesh,face,normal(face)) for mesh in scene['meshes']
            if not mesh.get('finished_host_id') and mesh['group'] in ('shell','context') and
            mesh['material'] in ('ceiling-white','concrete') for face in mesh['faces'] if normal(face)[2]<-.1]
    for mesh,face,n in scene['_ceiling_sources']:
            # Vertical ray through the anchor; no remote ceiling extension.
            dz = sum((face[0][i]-anchor[i])*n[i] for i in range(3))/n[2]
            hit = [anchor[0],anchor[1],anchor[2]+dz]
            if -.02 <= dz <= .6 and _on_polygon(hit,face,n):
                choices.append((abs(dz),mesh,face,n))
    if not choices:
        raise ValueError(identifier+': no measured finite finished ceiling')
    _,source,face,n = min(choices,key=lambda r:r[0])
    host = Host(identifier,'ceiling',tuple(face[0]),n,
                Finish('existing-exported-'+source['material']+'; finished datum; thickness unknown',0),None)
    coplanar = [f for f in source['faces'] if sum(normal(f)[i]*n[i] for i in range(3))>.999999
                and all(abs(sum((p[i]-face[0][i])*n[i] for i in range(3)))<1e-8 for p in f)]
    scene['mounting_hosts'][identifier] = dict(asdict(host),source_mesh=source['id'],source_faces=deepcopy(coplanar),
        source_material=source['material'],void_status='MISSING; UNVERIFIED finish-build-ups.json')
    scene['meshes'].append(dict(id='host-face-'+identifier,material=source['material'],group='shell',room=room,
        faces=deepcopy(coplanar),finished_host_id=identifier,visibility={'camera':False},part_kind='finish-layer',
        label='Measured finished ceiling fixing face: '+identifier+'; diagnostic only'))
    return host


def migrate(scene, lay):
    from .ceiling_requirements import requirements, product_depth
    lamps = VL.design(lay)
    scene['ceiling_requirements'] = requirements(lamps)
    by_lamp = {mid:row for row in scene['ceiling_requirements'] for mid in row['fitting_ids']}
    original = list(scene['meshes'])
    unresolved = []
    scene['ceiling_deferred_joinery'] = []
    for lamp in lamps:
        if lamp.kind not in ('DL','DLN','ADJ','WW','PEN-GLOBE','PEN-LIN','STORE-BATTEN'):
            continue
        if 'nook top' in lamp.why:
            scene['ceiling_deferred_joinery'].append(dict(id=lamp.id,reason='Recessed in actual joinery top; package e, not building ceiling'))
            continue
        members = [m for m in original if m['id'].endswith('-'+lamp.id) or
                   (lamp.kind=='PEN-LIN' and m['id'].startswith('wire-'+lamp.id+'-')) or
                   (lamp.kind=='STORE-BATTEN' and m['id'].startswith('batten-mount-'+lamp.id+'-'))]
        members = [m for m in members if not m.get('mounting')]
        if not members:
            continue
        recessed = lamp.kind in ('DL','DLN','ADJ','WW')
        if lamp.kind=='STORE-BATTEN':
            # Each bracket fixes to its own finite portion of the sloping
            # soffit. Only the upper fixing end is cut to that plane.
            for member in members:
                bb = bounds(member)
                anchor = ((bb[0]+bb[3])/2,(bb[1]+bb[4])/2,bb[5])
                host = ceiling_host(scene,anchor,lamp.room,'ceiling-'+member['id'])
                before = deepcopy(member)
                n = host.normal
                if member['id'].startswith('batten-mount-'):
                    proposed = deepcopy(member)
                    proposed['faces'] = [[list(p) for p in f] for f in member['faces']]
                    for f in proposed['faces']:
                        for p in f:
                            if abs(p[2]-bb[5])<1e-9:
                                p[2] += sum((host.structural_point[i]-p[i])*n[i] for i in range(3))/n[2]
                    offset,kind = 0,'surface-mounted'
                else:
                    proposed = deepcopy(member)
                    offset = min(sum((p[i]-host.structural_point[i])*n[i] for i in range(3)) for p in points(member))
                    kind = 'suspended'
                member['mounting'] = binding(MountItem(member['id']),host,offset,kind)
                member['mounting_package'] = 'd-ceiling'
                mm = max(math.dist(a,b) for a,b in zip(points(before),points(proposed)))*1000
                applied = mm<=5+1e-9
                if applied:
                    member['faces'] = proposed['faces']
                else:
                    member['mounting']['approval'] = 'PENDING'
                scene['mounting_movements'].append(dict(id=member['id'],package='d-ceiling',host_id=host.id,
                    old=bounds(before),new=bounds(proposed),mm=round(mm,6),why='Measured sloping soffit; fixing end only',
                    approval='APPLIED <=5 mm' if applied else 'PENDING',proposed_faces=proposed['faces']))
            continue
        root = next((m for m in members if m['id'].startswith(('fix-','canopy-','wire-'))),members[0])
        bb = bounds(root)
        anchor = ((bb[0]+bb[3])/2,(bb[1]+bb[4])/2,bb[5])
        host = ceiling_host(scene,anchor,lamp.room,'ceiling-'+lamp.id)
        fixing = min(sum(p[i]*host.normal[i] for i in range(3)) for p in points(root))
        package(scene,members,host,fixing,'d-ceiling',root['id'])
        if recessed:
            # The decorative trim is not a measured housing. Neither its
            # height nor the light emitter is evidence of housing depth.
            req = by_lamp[lamp.id]
            product = product_depth(lamp.kind)
            depth = product['housing_depth_mm']
            void = req['required_void_mm']
            record = scene['mounting_hosts'][host.id]
            record.update(void_depth_m=None if void is None else void/1000,
                void_status=req['status'], void_basis='construction requirement; not verified-as-built',
                ceiling_zone=req['zone'], required_void_mm=void,
                installation_clearance_m=req['clearance_mm']/1000,
                clearance_source=req['clearance_source'], housing_source=product['source'])
            root['mounting'].update(kind='recessed',offset_m=0,
                housing_depth_m=None if depth is None else depth/1000,
                geometry_role='recessed-trim', housing_source=product['source'],
                resolution_status=req['status'], installation_clearance_m=req['clearance_mm']/1000)
            if depth is None or void is None:
                unresolved.append(dict(id=root['id'],host_id=host.id,housing_depth_m=None,void_depth_m=None,
                    status='UNRESOLVED: housing depth or ceiling requirement MISSING'))
    scene['ceiling_unresolved'] = unresolved
    scene['ceiling_existing_bc'] = [m['id'] for m in original if m.get('mounting_package')=='b-bathroom' and
        scene['mounting_hosts'][m['mounting']['host_id']]['kind']=='ceiling']
    scene.pop('_ceiling_sources',None)
