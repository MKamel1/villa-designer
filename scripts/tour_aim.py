"""Choose where the camera looks while walking, with the audit's own measure. Run with scripts/wt_py.sh (needs embreex).

For every walking segment of the un-aimed plan, every 0.25 s try headings within +-90 deg of the look-ahead heading AND within 70 deg (85 on the flight) of
the actual direction of travel (so the audit never calls it backward), classify each by the audit's wall_dominated / blocked rules at the
frame's own focal length, and take the path through them (dynamic programming) that is informative most often, stays near the look-ahead
heading (0.004 per degree) and turns the offset by at most 5 deg per 0.25 s. The segment starts on offset 0 so it leaves the 360 without a jump.
Result: knowledge/flythrough/tour-aim.json (offset in degrees against arc length), read by walkthrough_tour.plan_tour.
usage: scripts/wt_py.sh scripts/tour_aim.py [scene.json]
"""
import json, math, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'src'), str(ROOT/'scripts')]
from archpipe import walkthrough_tour as WT
from archpipe.flyaudit import core, audit
from wt_plan import vmap
from tour_points import classify_views

def closeup_boxes(geom, et):
    """(xmin, ymin, zmin, xmax, ymax, zmax) of every curtain stack (evaluated cloth bounds snapshot) and every column."""
    boxes = [tuple(c['bounds'][i] for i in (0, 1, 2, 3, 4, 5)) for c in json.loads((ROOT/'knowledge/flythrough/curtain-stacks.json').read_text())['stacks']]
    for i, n in enumerate(geom.elem_names):
        if n.startswith('column'):
            boxes.append(tuple(et['lo'][i])+tuple(et['hi'][i]))
    return np.array(boxes)


def closeup(boxes, p, yaw_deg, lens, near=.5, sensor=36.):
    """True when a curtain stack or column is within `near` m of the camera (plan) at eye height AND inside the horizontal field of view."""
    half = math.degrees(math.atan(.5*sensor/lens)); z = p[2]
    for x0, y0, z0, x1, y1, z1 in boxes:
        if not (z0 <= z <= z1): continue
        nx, ny = min(max(p[0], x0), x1), min(max(p[1], y0), y1)
        if math.hypot(nx-p[0], ny-p[1]) >= near: continue
        pts = [(nx, ny), (x0, y0), (x0, y1), (x1, y0), (x1, y1)]
        if any(abs(WT.wrap(math.degrees(math.atan2(q[1]-p[1], q[0]-p[0]))-yaw_deg)) < half for q in pts if math.hypot(q[0]-p[0], q[1]-p[1]) < near+1.5): return True
    return False


STRIDE = 6; STEP = 5; MAXOFF = 110; TRAVEL_LIMIT = 88; STAIR_TRAVEL_LIMIT = 88; PREFER = .004; CORRIDOR = .012; WINDOW = 12


def legs_of(frames):
    """contiguous runs of walking frames (not the flight): [(first, last, destination)]"""
    out = []; a = None
    for i, f in enumerate(frames):
        if f['phase'] in ('walk', 'stair'):
            if a is None: a = i
        elif a is not None:
            out.append((a, i-1)); a = None
    if a is not None: out.append((a, len(frames)-1))
    return out


def main(scene='out/wt/villa4/scene.json'):
    th = core.thresholds(); layout, spec, vm = vmap(); geom = audit.geometry_for(scene, ROOT/'out/flyaudit'); et = core.element_table(geom)
    surface = np.array([core.feature_kind(n, g) is not None for n, g in zip(geom.elem_names, et['grp'])])
    boxes = closeup_boxes(geom, et); pol = WT.tour_policy(); axes = {}
    path = WT.plan_tour(vm, aim={}, doors=False); fr = path['frames']; offs = np.arange(-MAXOFF, MAXOFF+1, STEP); out = {}; total_bad0 = total_bad1 = total_n = 0
    P = np.array([f['camera']['position'] for f in fr])
    for a, b in legs_of(fr):
        idx = list(range(a, b+1, STRIDE)); idx = idx if idx[-1] == b else idx+[b]
        if len(idx) < 3: continue
        s = np.concatenate([[0.], np.cumsum(np.linalg.norm(np.diff(P[a:b+1, :2], axis=0), axis=1))])
        views = []; ok = np.zeros((len(idx), len(offs)), bool); travs = []
        for k, i in enumerate(idx):
            j0, j1 = max(a, i-WINDOW), min(b, i+WINDOW); d = P[j1, :2]-P[j0, :2]
            trav = math.degrees(math.atan2(d[1], d[0])) if np.hypot(*d) > .02 else fr[i]['yaw_deg']
            travs.append(trav)
            for m, o in enumerate(offs):
                yaw = fr[i]['yaw_deg']+o
                ok[k, m] = abs(WT.wrap(yaw-trav)) <= (STAIR_TRAVEL_LIMIT if fr[i]['stair'] else TRAVEL_LIMIT) and (o == 0 or not fr[i]['stair'] or fr[i]['ground_m'] > -1.)      # the flight keeps its own look (pitched up) except its last 1 m of climb, where it steps off the top
                y = math.radians(yaw); p = P[i]
                views.append((p, p+np.array([math.cos(y), math.sin(y), 0.]), fr[i]['camera']['lens_mm']))
        bad, med = classify_views(geom, surface, th, views); bad = bad.reshape(len(idx), len(offs)); med = med.reshape(len(idx), len(offs))
        axis = np.zeros((len(idx), len(offs)))
        for k, i in enumerate(idx):
            for m, o in enumerate(offs):
                if closeup(boxes, P[i], fr[i]['yaw_deg']+o, fr[i]['camera']['lens_mm'], pol['closeup_m']): bad[k, m] = True
            room = fr[i]['room']
            if room in pol.get('corridor_rooms', ()):
                r = vm.rooms[fr[i]['level']][room]['rect']; ends = (0., 180.) if (r[2]-r[0]) >= (r[3]-r[1]) else (90., 270.)
                near = [e for e in ends if abs(WT.wrap(e-travs[k])) <= 75.]     # only an end the camera is travelling toward (never turn back on the way: that is 'backward')
                if near: axis[k] = [min(abs(WT.wrap(fr[i]['yaw_deg']+o-e)) for e in near) for o in offs]      # degrees off the corridor's length
        cost = bad*1. + PREFER*np.abs(offs)[None] + CORRIDOR*axis; cost = np.where(ok, cost, 1e6); zero = int(np.where(offs == 0)[0][0])
        cost[0, :] = np.where(np.arange(len(offs)) == zero, cost[0, zero], 1e6)
        best = np.full(cost.shape, np.inf); back = np.zeros(cost.shape, int); best[0] = cost[0]
        for k in range(1, len(idx)):
            for m in range(len(offs)):
                lo, hi = max(0, m-2), min(len(offs), m+3); c = best[k-1, lo:hi]; q = int(c.argmin())
                best[k, m] = cost[k, m]+c[q]+.01*abs(lo+q-m); back[k, m] = lo+q
        m = int(best[-1].argmin()); chosen = [m]
        for k in range(len(idx)-1, 0, -1):
            m = back[k, m]; chosen.append(m)
        chosen = chosen[::-1]; off = offs[chosen]
        dest = fr[a]['heading_to']; P0 = fr[a]['camera']['position']
        key = WT.leg_key([P0], dest)
        out[key] = dict(s=[round(float(s[i-a]), 3) for i in idx], offset_deg=[int(o) for o in off], first_frame=a, last_frame=b)
        total_bad0 += int(bad[np.arange(len(idx)), zero].sum()); total_bad1 += int(bad[np.arange(len(idx)), chosen].sum()); total_n += len(idx)
        print(key, 'samples', len(idx), 'bad at 0 offset', int(bad[np.arange(len(idx)), zero].sum()), '-> chosen', int(bad[np.arange(len(idx)), chosen].sum()), 'max |offset|', int(np.abs(off).max()), flush=True)
    print('walk samples', total_n, 'bad before', total_bad0, 'after', total_bad1)
    (ROOT/'knowledge/flythrough/tour-aim.json').write_text(json.dumps(dict(schema='flythrough-tour-aim/1', method=__doc__.split('\n')[0], legs=out), indent=0))


if __name__ == '__main__':
    main(*sys.argv[1:])
