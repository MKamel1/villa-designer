"""Door-leaf animation tools (lane WT).

  leaves  <states.json> <out.json>     closed leaf faces (scene-base.json, as built) + hinge/sign/angle of every open interior door -> door_anim records
  analyse <path.json> <states.json> <id>   audit the route with all those leaves held open; lists the features each door hides (report['door_blocked'])
usage: scripts/wt_py.sh scripts/wt_doors.py analyse out/wt/villa8/path.json out/wt/villa8/door-states.json wt-villa8-doors-open
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'src')]
BASE = ROOT/'out/wt/scene-base.json'


def leaf_records(states):
    """door_anim records for every door that is open in `states` (open_interior_doors report): the leaf as built (closed) plus its pivot."""
    scene = json.loads(BASE.read_text()); by = {s['element']: s for s in states if s['state'] == 'open'}; out = []
    for m in scene['meshes']:
        if m.get('part_kind') != 'door-leaf' or not m['id'].startswith('door-leaf-'):
            continue
        el = (m.get('element_ids') or [m['id']])[0]
        if el in by:
            s = by[el]
            out.append(dict(element=el, leaf_id=m['id'], hinge=s['hinge'], signed_open_deg=float(s['angle_deg']*s['swing_sign']),
                            closed_faces=[[list(map(float, v)) for v in face] for face in m['faces']]))
    return out


def route_with_doors(path_file, states_file):
    p = json.loads(Path(path_file).read_text()); p['door_anim'] = leaf_records(json.loads(Path(states_file).read_text())); return p


if __name__ == '__main__' and sys.argv[1] == 'analyse':
    if True:
        from archpipe.flyaudit import audit
        p = route_with_doors(sys.argv[2], sys.argv[3]); tmp = ROOT/'out/wt/audits'/f'{sys.argv[4]}-route.json'; tmp.parent.mkdir(exist_ok=True, parents=True)
        tmp.write_text(json.dumps(p))
        rep, recs = audit.run(tmp, ROOT/'out/wt/villa4/scene.json', ROOT/'out/wt/audits', sys.argv[4], cache_dir=ROOT/'out/flyaudit', doors_open=True)
        d = rep['door_blocked']; print(d['blocked_features'], 'blocked,', d['features_hidden_some_frames'], 'hidden in some frames')
        for x in d['blocked']+d['partly']: print(x)


# ---- schedule ----------------------------------------------------------------------------------------------
MIN_OPEN_GAP_M = .25      # the fallback gap open_interior_doors accepts (policy door_route_gap_m: 0.35 then 0.25)
CLOSE_S, OPEN_S, HOLD_AFTER_S, MIN_BLOCKED_S, CLEARANCE_M, CLUSTER_GAP_S, EXIT_DIST_M = 2.0, 2.0, .5, 1.0, .3, 1.5, 1.2
ENTER_PAUSE_S, MIN_CLOSED_S = .5, 1.0
SWING_STEP_DEG = 5


def swing_options(rec, vm, track):
    """(hinge, signed angle) options for a leaf, best first: the leaf swept through every 5 deg from 15 deg to fully open touches no furniture, wall or column
    (leaf probe from 0.12 m out of the jamb), and fully open it stays >= 0.35 m from the walked route (the gap open_interior_doors asks for).
    The hinge side is not authored, so this picks the side that clears the path; the existing build's choice is tried first."""
    import numpy as np
    from archpipe import flythrough as FT
    from archpipe.door_anim import leaf_polygon
    from archpipe.concept import villa_furnish as F
    pts = np.array([v for face in rec['closed_faces'] for v in face]); lo, hi = pts.min(0), pts.max(0)
    lv = FT.level_at((lo[2]+hi[2])/2); along_x = (hi[0]-lo[0]) >= (hi[1]-lo[1])
    mid = ((lo[1]+hi[1])/2) if along_x else ((lo[0]+hi[0])/2)
    ends = [(lo[0], mid), (hi[0], mid)] if along_x else [(mid, lo[1]), (mid, hi[1])]
    obstacles = [FT._rect_to_poly(r, .02) for r in vm.pieces[lv]] + [FT._rect_to_poly(w) for w in F._walls(vm.spec, lv)+F._columns()]
    opts = []; open_deg = abs(rec['signed_open_deg'])
    for hinge in ends:
        for sign in (1, -1):
            r = dict(rec, hinge=list(hinge), signed_open_deg=open_deg*sign)
            from archpipe.door_anim import leaf_rect
            length, width, u, nrm = leaf_rect(r)
            ok = True
            for a in range(SWING_STEP_DEG*3, int(open_deg)+1, SWING_STEP_DEG):
                import math
                psi = math.radians(a*sign); c, s_ = math.cos(psi), math.sin(psi); rx, ry = u[0]*c-u[1]*s_, u[0]*s_+u[1]*c
                probe = FT._rect_poly(hinge[0]+rx*.12, hinge[1]+ry*.12, rx, ry, length-.12, width*.6)
                if any(FT._polys_overlap(probe, o) for o in obstacles): ok = False; break
            if not ok: continue
            poly = leaf_polygon(r, 1.); samples = np.vstack([poly, [np.asarray(hinge)+(poly[1]-poly[0]+poly[2]-poly[3])/2*t for t in np.linspace(0, 1, 9)]])
            gap = min(float(np.min(np.hypot(*(track[:, None, :]-samples[None]).transpose(2, 0, 1)))), 9.) if len(track) else 9.
            if gap >= MIN_OPEN_GAP_M: opts.append((gap, r))
    return opts


def schedule(plan_file=None):
    import numpy as np
    from archpipe import flythrough as FT, walkthrough_tour as WT, door_anim as DA
    from archpipe.flyaudit import audit
    from wt_plan import vmap
    layout, spec, vm = vmap(); plan = WT.plan_tour(vm, doors=False); frames = plan['frames']
    states = json.loads((ROOT/'out/wt/villa8/door-states.json').read_text())
    recs = {r['element']: r for r in leaf_records(states)}; tmp = dict(plan, door_anim=list(recs.values()))
    f = ROOT/'out/wt/audits/wt-doors-open-route.json'; f.write_text(json.dumps(tmp))
    rep, _ = audit.run(f, ROOT/'out/wt/villa4/scene.json', ROOT/'out/wt/audits', 'wt-doors-open', cache_dir=ROOT/'out/flyaudit', doors_open=True, log=lambda *a: None)
    blocked = rep['door_blocked']; fps = 24; by = {}
    for x in blocked['blocked']+blocked['partly']:
        if x['n_door_blocked_frames'] >= MIN_BLOCKED_S*fps/2 or x['seconds_seen'] == 0:
            by.setdefault(x['door'], []).append(x)
    print('candidates', {k: [(x['feature'], x['n_door_blocked_frames'], x['seconds_seen']) for x in v] for k, v in by.items()})
    out = []; report = []
    for door, feats in by.items():
        fr = sorted({i for x in feats for i in x['door_blocked_frames'] if frames[i]['phase'] != 'walk'})      # a feature glimpsed while the camera walks past is not a view: the leaf closes for the turns and holds
        if not fr:
            report.append(dict(door=door, scheduled=False, reason='the leaf only hides the feature while the camera is walking', features=[x['feature'] for x in feats])); continue
        clusters = [[fr[0]]]
        for i in fr[1:]:
            (clusters[-1].append(i) if i-clusters[-1][-1] <= CLUSTER_GAP_S*fps else clusters.append([i]))
        cl = max(clusters, key=len); c0, c1 = cl[0], cl[-1]
        rec = recs[door]; lv = FT.level_at(rec['closed_faces'][0][0][2])
        track = np.array([f['camera']['position'][:2] for f in frames if f['level'] == lv and not f['stair']])
        centre = np.array(rec['hinge'])
        got = None
        room = frames[c0]['room']; entry = c0
        while entry > 0 and frames[entry-1]['room'] == room: entry -= 1       # first frame of this visit to the room: the leaf closes only after the camera is in
        leave = next((f['index'] for f in frames[c1:] if f['phase'] == 'walk'), len(frames))      # the camera starts walking out: the leaf must be fully open again by then
        for gap, r in sorted(swing_options(rec, vm, track), key=lambda t: (-(t[1]['hinge'] == rec['hinge'] and t[1]['signed_open_deg'] == rec['signed_open_deg']), -t[0])):
            cs = max(c0-int(CLOSE_S*fps), entry+int(ENTER_PAUSE_S*fps))
            while cs < c0+int(CLOSE_S*fps*.5):
                oe = min(leave, c1+int(HOLD_AFTER_S*fps)+int(OPEN_S*fps)); os_ = oe-int(OPEN_S*fps)
                sch = dict(close_start=cs, close_end=cs+int(CLOSE_S*fps), open_start=os_, open_end=oe)
                if os_ >= sch['close_end']+int(MIN_CLOSED_S*fps):
                    S = DA.state_series(sch, len(frames))
                    probe = {'frames': [dict(f, doors={door: round(float(S[f['index']]), 5)}) for f in frames[max(0, cs-24):oe+25]], 'door_anim': [r]}
                    if not DA.clearance_findings(probe, CLEARANCE_M):
                        got = (r, sch, gap, leave, cs-(c0-int(CLOSE_S*fps))); break
                cs += 2
            if got: break
        if not got:
            report.append(dict(door=door, scheduled=False, reason='no swing side clears the camera in every frame of the animation', blocked_frames=[c0, c1])); continue
        r, sch, gap, exit_frame, delay = got
        r = dict(r, note=f'hinge side is not authored; this side (hinge {r["hinge"]}, swing {"+" if r["signed_open_deg"] > 0 else "-"}) clears furniture and walls over the whole swing and keeps >= {CLEARANCE_M} m from the camera in every frame of the animation')
        out.append(dict(record=r, schedule=sch, features=[x['feature'] for x in feats]))
        report.append(dict(door=door, scheduled=True, features=[x['feature'] for x in feats], blocked_frames=[c0, c1], schedule=sch, delay_frames=delay, hold_after_last_blocked_frame_s=round((sch['open_end']-c1)/fps, 2), leave_frame=exit_frame, reopened_before_leaving=sch['open_end'] <= exit_frame, route_gap_open_m=round(gap, 2)))
    for r in report: print(r)
    (ROOT/'knowledge/flythrough/tour-doors.json').write_text(json.dumps(dict(schema='flythrough-tour-doors/1', camera_sha256=FT.digest([f['camera'] for f in frames]), clearance_m=CLEARANCE_M,
        rule=dict(min_blocked_s=MIN_BLOCKED_S, close_s=CLOSE_S, open_s=OPEN_S, hold_after_s=HOLD_AFTER_S, cluster_gap_s=CLUSTER_GAP_S, basis='policy (ours): a door is animated when a feature is in view but hidden by its leaf for >= 1 s or never seen; closes (eased smoothstep, 2 s) so it is closed when the feature comes into view, held 0.5 s after the last blocked frame, reopened in 2 s'),
        doors=out, report=report), indent=0))


if __name__ == '__main__' and sys.argv[1] == 'schedule':
    schedule()
