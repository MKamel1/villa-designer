"""Rigid sanitary moves between measured finished hosts; metres throughout.

The baseline generator and frozen C4 approvals remain audit inputs. A current
placement replaces that baseline for review and native specification output.
No soil-stack position or concealed cistern geometry is inferred.
"""
from copy import deepcopy
from contextlib import contextmanager
from contextvars import ContextVar
import math

from .fitting_mounting import bounds, points, measured_host
from .mounting import MountItem, binding

_history=ContextVar('sanitary_mounting_history',default=False)


@contextmanager
def input_revision(historical):
    """Build frozen migration input while public layout/spec readers use current intent."""
    token=_history.set(historical)
    try: yield
    finally: _history.reset(token)


def historical_input():
    return _history.get()


def family_pose(lay, items):
    """Balance the south 350 mm side and north 1000 mm wet-zone margins.

    Finished wall projection is checked against the real C4 host at build.
    This is an authored layout choice, followed by the full clearance review.
    """
    from . import villa_furnish as F
    from .mounting import finish_from_record
    wc=next(i for i in items if i['id']=='fb-wc')
    shower=next(i for i in items if i['id']=='fb-shower')
    rect=F.clear_rect(lay,wc['room']);thickness=finish_from_record('marble-wall-thinset').thickness_m
    low=rect[1]+thickness+.35
    high=F.footprint(shower)[1]-1.
    return dict(cx=rect[2]-thickness-wc['d']/2,cy=(low+high)/2,rot=90,
        host_id='bath-fb-wc-east',drainage_note='services coordination pending')


def relocate(scene, item, host, centre, rotation):
    """Carry every generated sanitary member, then bind each to the new host.

    Centre is the conservative envelope centre in model x/y. Rotation is
    degrees about upward model z, with local front following villa_furnish.
    """
    members=[m for m in scene['meshes'] if m['id'].startswith('furn-'+item['id']+'-')]
    if not members: raise ValueError(item['id']+': no complete sanitary assembly')
    angle=math.radians(rotation-item['rot']); cosine,sine=math.cos(angle),math.sin(angle)
    root=members[0]['mounting']['assembly_root']
    face=[host.structural_point[i]+host.normal[i]*host.finish.thickness_m for i in range(3)]
    movements=[]
    for member in members:
        before=deepcopy(member)
        member['faces']=[[[centre[0]+cosine*(p[0]-item['cx'])-sine*(p[1]-item['cy']),
                           centre[1]+sine*(p[0]-item['cx'])+cosine*(p[1]-item['cy']),p[2]]
                          for p in polygon] for polygon in member['faces']]
        projection=min(sum((p[i]-face[i])*host.normal[i] for i in range(3)) for p in points(member))
        if projection < -1e-8: raise ValueError(member['id']+': relocated assembly penetrates finished host')
        member['mounting']=dict(binding(MountItem(member['id']),host,max(0,projection),'wall-hung'),
            assembly_root=root,projection_basis='Rigid complete sanitary assembly at measured finished face')
        movement=dict(id=member['id'],package='client-sanitary-relocation',host_id=host.id,
            old=bounds(before),new=bounds(member),
            mm=round(max(math.dist(a,b) for a,b in zip(points(before),points(member)))*1000,6),
            why='Client 2026-10-05: WC east wall; complete rigid assembly',
            approval='CLIENT AUTHORIZED; APPLIED',proposed_faces=deepcopy(member['faces']))
        scene['mounting_movements'].append(movement);movements.append(movement)
    placement=dict(cx=centre[0],cy=centre[1],rot=rotation,host_id=host.id,
        finished_face=face,drainage_note='services coordination pending')
    scene.setdefault('sanitary_placements',{})[item['id']]=placement
    from .attached_assembly import bind
    bind(scene,root,[m['id'] for m in members if m['id']!=root])
    return movements


def apply_family(scene, lay):
    """Client-selected opposite wall; centre balances the two side-zone margins."""
    from .mounting_clearances import measured_items
    from . import villa_furnish as F
    item=next(i for i in measured_items(scene,lay) if i['id']=='fb-wc')
    pose=family_pose(lay,F.layout(lay))
    centre_y=pose['cy']
    rect=F.clear_rect(lay,item['room'])
    host=measured_host(scene,[rect[2],centre_y,.7],(-1,0,0),item['room'],'bath-fb-wc-east')
    finished_x=host.structural_point[0]-host.finish.thickness_m
    centre=[finished_x-item['d']/2,centre_y]
    if abs(centre[0]-pose['cx'])>1e-8:
        raise ValueError('Family WC authored placement disagrees with measured C4 finished host')
    movements=relocate(scene,item,host,centre,90)
    # The client authorized the wall change and the recorded assembly build-up.
    row=scene['mounting_movements'][-len(movements)-1]
    if row['id']!='host-face-'+host.id: raise ValueError('Relocation host schedule changed')
    diagnostic=next(m for m in scene['diagnostic_meshes'] if m['id']==row['id'])
    diagnostic['faces']=deepcopy(row['proposed_faces']);row['approval']='CLIENT AUTHORIZED; APPLIED'
    scene['family_wc_relocation']=dict(old_centre=[item['cx'],item['cy']],new_centre=centre,
        old_rotation=item['rot'],new_rotation=90,members=[r['id'] for r in movements],
        host_id=host.id,drainage_note='services coordination pending',
        cistern='Concealed carrier/cistern installation and east-wall soil-stack coordination required; geometry unmodelled')
