"""Explicit lead-approved C4 resume; candidate geometry, never extract edits."""
from copy import deepcopy
import json
import math
from pathlib import Path

from .fitting_mounting import bounds, points
from .mounting import binding, Host, Finish, MountItem

APPROVALS = Path(__file__).resolve().parents[3] / 'knowledge/c4-bc-approvals.json'
HOSE_RADIUS_M = .006
HOSE_CLEARANCE_M = .002  # Authored design clearance, not a published standard.
EDGE_MARGIN_M = .005  # Authored back-plate edge margin.


def host_object(record):
    return Host(record['id'], record['kind'], tuple(record['structural_point']),
                tuple(record['normal']), Finish(**record['finish']), record.get('void_depth_m'))


def apply_approvals(scene, authority_path=APPROVALS):
    """Approve only the frozen schedule; reject geometry/host drift."""
    approved = {r['id']: r for r in json.loads(authority_path.read_text())['rows']}
    meshes = {m['id']: m for m in scene['meshes']}
    rows = {r['id']: r for r in scene['mounting_movements']}
    for mid, authority in approved.items():
        row = rows[mid]
        if row['host_id'] != authority['host_id'] or any(
                abs(a-b) > 1e-8 for key in ('old', 'new') for a,b in zip(row[key], authority[key])):
            raise ValueError(mid + ': approved schedule drift; new lead review required')
        meshes[mid]['faces'] = deepcopy(row['proposed_faces'])
        meshes[mid].get('mounting', {}).pop('approval', None)
        row['approval'] = 'APPROVED lead 2026-10-05; APPLIED'
    scene['lead_approved_count'] = scene.get('lead_approved_count',0)+len(approved)


def wall_safe_hose(start, end, host, radius=HOSE_RADIUS_M, clearance=HOSE_CLEARANCE_M):
    """Hang a spatial polyline from retained connections into the room.

    Endpoints must already clear the finished wall. Interior control points
    bow outward and down. Straight segments inherit the endpoint half-space
    clearance; the swept tube is checked independently from its vertices.
    """
    face = [host.structural_point[i]+host.normal[i]*host.finish.thickness_m for i in range(3)]
    def gap(p):
        return sum((p[i]-face[i])*host.normal[i] for i in range(3))
    if min(gap(start), gap(end)) < radius+clearance-1e-9:
        raise ValueError('Hose connection behind required finished-wall clearance')
    curve = [list(start)]
    for fraction, bow, drop in ((.25,.055,.19),(.5,.08,.43),(.75,.045,.26)):
        p = [(1-fraction)*start[i]+fraction*end[i]+bow*host.normal[i] for i in range(3)]
        p[2] -= drop
        curve.append(p)
    return curve+[list(end)]


def guest_fixes(scene, spec):
    from .villa_render import round_tube
    from .villa_lighting import LEVEL_Z
    meshes = {m['id']: m for m in scene['meshes']}
    hose = meshes['detail-gwc-hand-shower-hose']
    host = host_object(scene['mounting_hosts'][hose['mounting']['host_id']])
    head = meshes['detail-gwc-hand-shower-head']
    old_head = deepcopy(head)
    head['faces'] = [[[p[i]+.023*host.normal[i] for i in range(3)] for p in f] for f in head['faces']]
    finished = [host.structural_point[i]+host.normal[i]*host.finish.thickness_m for i in range(3)]
    head_projection = min(sum((p[i]-finished[i])*host.normal[i] for i in range(3)) for p in points(head))
    head['mounting'] = dict(binding(MountItem(head['id']),host,head_projection,'wall-hung'),
                            assembly_root='detail-gwc-hand-shower-slider', projection_basis='Lead-approved rigid handset correction')
    fitting = next(f for f in spec['bath_fittings'] if f['id']=='gwc-hand-shower')
    # Same authored connections after the approved rigid assembly translation.
    x,y,z = fitting['x'],fitting['y'],LEVEL_Z[fitting['level']]+fitting['z']
    shift = [host.normal[i]*host.finish.thickness_m for i in range(3)]
    start = [a+b for a,b in zip((x,y+.060,z+.14),shift)]
    start = [start[i]+.023*host.normal[i] for i in range(3)]
    end = [a+b for a,b in zip((x,y,z-.24),shift)]
    before = deepcopy(hose)
    curve = wall_safe_hose(start,end,host)
    hose['faces'] = [f for a,b in zip(curve,curve[1:]) for f in round_tube(a,b,HOSE_RADIUS_M,12)]
    face = [host.structural_point[i]+host.normal[i]*host.finish.thickness_m for i in range(3)]
    projection = min(sum((p[i]-face[i])*host.normal[i] for i in range(3)) for p in points(hose))
    hose['mounting'] = dict(binding(MountItem(hose['id']),host,projection,'wall-hung'),
                           assembly_root='detail-gwc-hand-shower-bracket-lower',
                           projection_basis='Regenerated hose supported by retained handset/riser connections')
    hose['hose_path'] = dict(points=curve,radius_m=HOSE_RADIUS_M,clearance_m=HOSE_CLEARANCE_M,
                             retained_endpoints=[start,end])
    sconce = meshes['lamp-SCONCE-guest-wc-03']
    old_sconce = deepcopy(sconce)
    record = scene['mounting_hosts'][sconce['mounting']['host_id']]
    # Back-plane vertices only: full body width is not the back-plate width.
    n = record['normal']; plane = sum(record['structural_point'][i]*n[i] for i in range(3))+record['finish']['thickness_m']
    # The procedural globe has no separate catalogue back plate. Retain its
    # full tangent envelope (120 mm) as a conservative fixing footprint,
    # rather than mistaking its one tangent vertex for a zero-width plate.
    back = points(sconce)
    wall_min = min(p[1] for f in record['source_faces'] for p in f)
    movement = max(0,wall_min+EDGE_MARGIN_M-min(p[1] for p in back))
    sconce['faces'] = [[[p[0],p[1]+movement,p[2]] for p in f] for f in sconce['faces']]
    bb = bounds(sconce)
    sconce['mounting']['fixing_footprint'] = [[plane,yy,zz] for yy in (bb[1],bb[4]) for zz in (bb[2],bb[5])]
    scene['guest_fix_evidence'] = dict(handset_translation_mm=23,handset_total_from_original_mm=46,
        handset_min_surface_clearance_mm=head_projection*1000, hose= hose['hose_path'],
        hose_min_surface_clearance_mm=projection*1000,sconce_slide_mm=movement*1000,edge_margin_mm=EDGE_MARGIN_M*1000,
        sconce_fixing_envelope='120 mm existing body tangent envelope; product back plate unverified')
    for mesh,old,reason in ((head,old_head,'Lead: additional rigid 23 mm handset correction after assembly approval'),
                            (hose,before,'Lead: regenerate spatial hose; retain connections'),
                            (sconce,old_sconce,'Lead: same-wall slide; 5 mm back-plate edge margin')):
        scene['mounting_movements'].append(dict(id=mesh['id'],package='guest-design-fixes',host_id=mesh['mounting']['host_id'],
            old=bounds(old),new=bounds(mesh),mm=round(max(math.dist(a,b) for a,b in zip(points(old),points(mesh)))*1000,6),
            why=reason,approval='APPROVED lead 2026-10-05; APPLIED',proposed_faces=deepcopy(mesh['faces'])))
