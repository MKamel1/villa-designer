"""Bounded same-wall WC slides; all carded fronts, sides, doors/routes rerun."""

from . import villa_furnish as F
from .fitting_mounting import bounds
from .mounting import finish_from_record
from .mounting_clearances import measured_items, wc_side_clearances, review


def continuous_candidates(item, obstacles, rect):
    """Find closest feasible side-zone centres from exact piecewise events.

    Each obstacle has a fixed interval along the wall. Side gaps change
    linearly between its edges. Required side gaps are 350 and 1000 mm,
    considered in both handednesses. Endpoints include every transition.
    Full fronts, wet separation, doors and routes require a later review.
    """
    axis=0 if F.DIRS[item['rot']]['front'][0] else 1
    side=1-axis
    old=item['cx'] if side==0 else item['cy']
    edges=[rect[side],rect[side+2]]
    for _,box,_ in obstacles: edges.extend((box[side],box[side+2]))
    events={old}
    for edge in edges:
        events.update((edge,edge-.35,edge+.35,edge-1,edge+1))
    candidates=[]
    for centre in sorted(events,key=lambda v:abs(v-old)):
        candidate=dict(item);candidate['cx' if side==0 else 'cy']=centre
        if all(gap+1e-9>=required for gap,required,_ in wc_side_clearances(candidate,obstacles,rect)):
            candidates.append(centre-old)
    return side,candidates


def _trial(scene, identifier, side, travel):
    """Own translated faces and trial slide state; all review inputs are read-only."""
    trial = dict(scene)
    delta = [0, 0, 0]
    delta[side] = travel
    trial['wc_slides'] = dict(scene['wc_slides'])
    trial['wc_slides'][identifier] = dict(delta=delta)
    members = [dict(m) for m in scene['meshes'] if m['id'].startswith('furn-'+identifier+'-')]
    for member in members:
        member['faces'] = [[[p[i]+delta[i] for i in range(3)] for p in f] for f in member['faces']]
    by = {m['id']: m for m in members}
    trial['meshes'] = [by.get(m['id'], m) for m in scene['meshes']]
    return trial, delta, members


def apply(scene, lay):
    scene['wc_slides']={}
    initial=review(scene,lay)
    scene['wc_slide_initial_rows']=initial['rows']
    decisions=[]
    for identifier in ('gwc-wc','pe-wc'):
        items=measured_items(scene,lay)
        item=next(it for it in items if it['id']==identifier);room=item['room']
        rect=list(F.clear_rect(lay,room));t=finish_from_record('marble-wall-thinset').thickness_m
        rect=[rect[0]+t,rect[1]+t,rect[2]-t,rect[3]-t]
        obstacles=[(it['id'],F.footprint(it),it['type']) for it in items
                   if it['room']==room and it['id']!=identifier and it['h']>=.3]
        # Finished rectangle supplies wall limits; actual fixed projections
        # and full measured conservative fixture envelopes remain obstacles.
        side,candidates=continuous_candidates(item,obstacles,rect)
        decision=dict(id=identifier,room=room,old_centre=[item['cx'],item['cy']],
                      new_centre=[item['cx'],item['cy']],status='NO FEASIBLE SLIDE',attempts=[])
        for travel in candidates:
            trial,delta,members=_trial(scene,identifier,side,travel)
            result=review(trial,lay)
            affected=[r for r in result['rows'] if r['room']==room]
            failures=[r for r in affected if r['status'] in ('FAIL','UNRESOLVED')]
            decision['attempts'].append(dict(travel_mm=round(abs(travel)*1000,6),failures=failures))
            if failures: continue
            # Tangential translation retains wall normal, height and geometry.
            by={m['id']:m for m in members}
            for member in scene['meshes']:
                if member['id'] not in by: continue
                old=bounds(member);member['faces']=by[member['id']]['faces']
                scene['mounting_movements'].append(dict(id=member['id'],package='wc-same-wall-slide',
                    host_id=member['mounting']['host_id'],old=old,new=bounds(member),mm=round(abs(travel)*1000,6),
                    why='Explicit lead authority: feasible same-wall WC slide; all room clearances rerun',
                    approval='AUTHORIZED SAME-WALL SLIDE; APPLIED',proposed_faces=member['faces']))
            scene['wc_slides'][identifier]=dict(delta=delta)
            decision.update(status='APPLIED',delta=delta,new_centre=[item['cx']+delta[0],item['cy']+delta[1]],rows=affected)
            break
        decisions.append(decision)
    scene['wc_slide_decisions']=decisions
