"""Final lead-authorized C4 candidate corrections; no native integration."""
from copy import deepcopy
import json
import math
from pathlib import Path
from .fitting_mounting import bounds, points
from .attached_assembly import translate
from .mounting import Host, Finish, MountItem, binding


def trim_panel(panel, host, centre, margin):
    """Fit a width symmetrically about the bed if that centre is on its wall."""
    old = bounds(panel)
    # Only a source patch covering the full panel height can carry it.
    spans = [bounds(dict(faces=[face])) for face in host['source_faces']]
    spans = [b for b in spans if b[2] <= old[2]+1e-8 and b[5] >= old[5]-1e-8]
    span = min(spans, key=lambda b: abs((b[0]+b[3])/2-centre))
    left, right = span[0]+margin, span[3]-margin
    if left < centre < right:
        half = min(centre-left, right-centre, (old[3]-old[0])/2)
        low, high = centre-half, centre+half
        basis = 'Symmetric about unchanged bed centreline'
    else:
        low, high = max(left, old[0]), min(right, old[3])
        basis = 'Trim from overrunning side; centre outside finite support'
    if high <= low:
        raise ValueError('Panel has no finite wall span after margin')
    for face in panel['faces']:
        for point in face:
            point[0] = low+(point[0]-old[0])*(high-low)/(old[3]-old[0])
    return dict(old_width_mm=(old[3]-old[0])*1000, new_width_mm=(high-low)*1000,
                old_bounds=old, new_bounds=bounds(panel), wall_span=span,
                margin_mm=margin*1000, centre_x_m=centre, basis=basis)


def apply(scene, lay):
    authority = json.loads((Path(__file__).resolve().parents[3]/'knowledge/c4-final-approvals.json').read_text())
    render_meshes = {m['id']: m for m in scene['meshes']}
    diag_meshes = {m['id']: m for m in scene.get('diagnostic_meshes', [])}
    rows = {r['id']: r for r in scene['mounting_movements']}
    # Validate the whole approval package before applying any row.
    for approved in authority['rows']:
        mid = approved['id']
        if mid not in rows:
            raise KeyError(mid + ': approved row not in scene mounting movements')
        row = rows[mid]
        if row['host_id'] != approved['host_id'] or any(abs(a-b)>1e-8
                for key in ('old','new') for a,b in zip(row[key],approved[key])):
            raise ValueError(approved['id']+': final approved schedule drift')
    for approved in authority['rows']:
        mid = approved['id']
        row = rows[mid]
        if mid in render_meshes and mid in diag_meshes:
            raise ValueError(mid + ': present in both render meshes and diagnostics channel')
        if mid in render_meshes:
            target = render_meshes[mid]
        elif mid in diag_meshes:
            target = diag_meshes[mid]
        else:
            raise KeyError(mid + ': approval row id is in neither render meshes nor diagnostics channel')
        target['faces'] = deepcopy(row['proposed_faces'])
        target.get('mounting', {}).pop('approval', None)
        row['approval'] = 'APPROVED final lead 2026-10-05; APPLIED'
    from . import villa_furnish as F
    centre = next(it['cx'] for it in F.layout(lay) if it['id']=='pb-bed')
    panel = render_meshes['detail-headboard-slats']
    before_panel = deepcopy(panel)
    trimmed = trim_panel(panel, scene['mounting_hosts'][panel['mounting']['host_id']],
                         centre, authority['headboard_margin_m'])
    def record_final(member, before, why):
        scene['mounting_movements'].append(dict(id=member['id'], package='final-design-fixes',
            host_id=member['mounting']['host_id'], old=bounds(before), new=bounds(member),
            mm=round(max(math.dist(a,b) for a,b in zip(points(before),points(member)))*1000,6),
            why=why, approval=authority['approval']+'; APPLIED', proposed_faces=deepcopy(member['faces'])))
    record_final(panel, before_panel, 'Final lead authority: headboard finite-wall trim with declared margin')
    seated = []
    for root in list(render_meshes.values()):
        if not root['id'].startswith('appliance-coffee-') or not root['id'].endswith('-body'):
            continue
        members = [root]+[m for m in render_meshes.values() if m.get('associated_mounting_root')==root['id']]
        before_members = {m['id']:deepcopy(m) for m in members}
        record = scene['mounting_hosts'][root['mounting']['host_id']]
        host = Host(record['id'],record['kind'],tuple(record['structural_point']),
                    tuple(record['normal']),Finish(**record['finish']))
        normal = host.normal
        fixing = min(sum(p[i]*normal[i] for i in range(3)) for m in members for p in points(m))
        target = sum(host.structural_point[i]*normal[i] for i in range(3))+host.finish.thickness_m
        delta = [(target-fixing)*v for v in normal]
        carried = translate(scene,root['id'],delta)
        for member in members:
            projection = min(sum(p[i]*normal[i] for i in range(3)) for p in points(member))-target
            member['mounting'] = dict(binding(MountItem(member['id']),host,max(0,projection),
                'surface-mounted' if projection < 1e-9 else 'wall-hung'),
                assembly_root=root['id'],projection_basis='Generated part relative to lowest complete assembly fixing plane')
            record_final(member, before_members[member['id']], 'Final lead authority: seat lowest complete coffee assembly part')
        seated.append(dict(root_id=root['id'],delta=delta,members=carried,
                           fixing_basis='Lowest complete rigid assembly part; actual modeled worktop'))
    scene['c4_final'] = dict(applied=[r['id'] for r in authority['rows']],headboard=trimmed,coffee=seated)
