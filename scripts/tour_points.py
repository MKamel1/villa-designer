"""Choose each room's 360 point with the audit's own measure. Run with the wta-venv python (needs embreex).

For every free standing cell of a room (0.3 m pitch) cast the audit's ray grid for 20 headings of a full turn at the room's lens
(16 mm for the rooms in lens-rooms.json, else 24) and classify each frame by the audit's rules. The point with the smallest share of
wall-dominated / blocked frames wins; ties go to the longer median sightline. Result: knowledge/flythrough/tour-points.json.
usage: PYTHONPATH=src python scripts/tour_points.py [scene.json]
"""
import json, math, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'src'), str(ROOT/'scripts')]
from archpipe import flythrough as FT, walkthrough_tour as WT
from archpipe.flyaudit import core, audit
from wt_plan import vmap

N_YAW = 24; PITCH = 1.35          # eye height above ground (policy eye_height_m)


def classify_views(geom, surface, th, views, cols=48, rows=27, chunk=48):
    """views: [(pos xyz, target xyz, lens_mm)] -> (bad flags, median hit distance) by the audit's wall_dominated / blocked rules."""
    bad = []; med = []; E = len(geom.elem_names)
    for a in range(0, len(views), chunk):
        part = views[a:a+chunk]
        D = np.concatenate([core.ray_dirs(np.asarray(p, float), np.asarray(t, float), cols, rows, l, 36., 9/16.) for p, t, l in part])
        O = np.concatenate([np.repeat(np.asarray(p, float)[None], cols*rows, 0) for p, _, _ in part])
        dist, tri, _, _ = geom.cast(O, D)
        for k in range(len(part)):
            sl = slice(k*cols*rows, (k+1)*cols*rows); d = dist[sl]; tr = tri[sl]; hit = tr >= 0; e = geom.tri_elem(tr)
            cnt = np.bincount(e[hit], minlength=E)
            near = (hit & (d < th['wall_dominated']['near_m'])).mean()
            cen = (hit & (d < th['blocked']['near_m'])).reshape(rows, cols)[rows//4:3*rows//4, cols//4:3*cols//4].mean()
            top = int(cnt.argmax()); topshare = float((cnt*surface).max()/(cols*rows)); md = float(np.median(d[hit])) if hit.any() else 99.
            plain_wall = geom.elem_names[top].startswith('wall')
            bad.append(bool((cen >= th['blocked']['min_near_share'] and not plain_wall) or near >= th['wall_dominated']['min_near_share'] or (
                topshare >= th['wall_dominated_v2']['min_single_surface_share'] and md < th['wall_dominated_v2']['max_median_dist_m']))); med.append(md)
    return np.array(bad), np.array(med)


def frame_bad(geom, surface, th, pos, yaws, lens, cols=48, rows=27):
    """One standing point, several headings (level camera)."""
    views = [(pos, pos+np.array([math.cos(y), math.sin(y), 0.]), lens) for y in yaws]
    return classify_views(geom, surface, th, views, cols, rows)


def main(scene='out/wt/villa4/scene.json'):
    th = core.thresholds(); route = WT.tour_route(); wide = WT.lens_rooms(); bounds = route.get('point_bounds', {}); skip = set(route.get('proxy_points', {}))
    layout, spec, vm = vmap(); rooms = audit.design_rooms()
    geom = audit.geometry_for(scene, ROOT/'out/flyaudit'); et = core.element_table(geom)
    surface = np.array([core.feature_kind(n, g) is not None for n, g in zip(geom.elem_names, et['grp'])])
    cur = {k: v['point'] for k, v in json.loads((ROOT/'out/wt/villa4/plan-only.json').read_text())['room_points'].items() if v.get('point')}
    yaws = np.arange(N_YAW)*2*math.pi/N_YAW; out = {}
    for room, r in rooms.items():
        if room in skip: continue
        lv = r['level']; free = vm.free(lv); x0, y0, x1, y1 = r['rect']; z = FT.LEVEL_Z[lv]+PITCH; lens = 16. if room in wide else 24.
        b = bounds.get(room)
        cells = [vm.xy(i, j) for i in range(0, vm.nx, 2) for j in range(0, vm.ny, 2) if free[i, j]
                 and x0 < vm.xy(i, j)[0] < x1 and y0 < vm.xy(i, j)[1] < y1 and (not b or (b[0] < vm.xy(i, j)[0] < b[2] and b[1] < vm.xy(i, j)[1] < b[3]))]
        if room in cur:
            def reach(c):
                try: vm.astar(lv, tuple(cur[room]), tuple(c)); return True
                except ValueError: return False
            cells = [c for c in cells if reach(c)]; cells.append(tuple(cur[room]))      # the planner must be able to walk there
        best = None; table = []
        for c in cells:
            bad, med = frame_bad(geom, surface, th, np.array([c[0], c[1], z]), yaws, lens)
            table.append((bad.mean(), -med.mean(), c, bad, med))
        table.sort(key=lambda t: (round(t[0], 2), t[1]))
        now = next((t for t in table if tuple(t[2]) == tuple(cur.get(room, ())) ), None)
        yaw_table = [[round(math.degrees(y)), bool(b), round(float(m), 2)] for y, b, m in zip(yaws, table[0][3], table[0][4])]
        w = table[0]; out[room] = dict(point=[round(w[2][0], 2), round(w[2][1], 2)], lens_mm=lens, bad_share=round(float(w[0]), 3), median_dist_m=round(float(-w[1]), 2),
                                       candidates=len(cells), yaw_table=yaw_table, current_point=cur.get(room), current_bad_share=None if now is None else round(float(now[0]), 3))
        print(room, out[room], flush=True)
    (ROOT/'knowledge/flythrough/tour-points.json').write_text(json.dumps(dict(schema='flythrough-tour-points/1', method=__doc__.split('\n')[0], points=out), indent=1))


if __name__ == '__main__':
    main(*sys.argv[1:])
