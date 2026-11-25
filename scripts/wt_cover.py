"""Coverage-driven choice of where the tour stops, and the redundancy of a route. Run with scripts/wt_py.sh (needs embreex).

Surface coverage = the 0.5 m cells (element, x, y, z) of walls, furniture, fixtures and dressing hit by the audit's ray grid
(floors and ceilings excluded: always in view). A cell is worth 0.25 m2 (policy proxy for area). Rooms own the cells whose hit point is inside their rectangle.

  select  : per level, greedy set cover over every free standing cell (0.4 m pitch) and 30-degree heading bin: a 360 (all 12 bins) is taken while it adds
            >= HUB_MIN_M2 of unseen surface; then arcs (<= 4 consecutive bins) while one adds >= ARC_MIN_M2. Writes knowledge/flythrough/tour-spaces.json.
  measure : walk a planned route's frames (every 0.25 s) and report, per second, the new surface it shows; a second is REDUNDANT when the camera shows
            < NEW_MIN_M2 of surface not seen before in the route. Prints total and redundant seconds per mode.
usage: scripts/wt_py.sh scripts/wt_cover.py select [scene.json]   |   scripts/wt_py.sh scripts/wt_cover.py measure path.json [scene.json]
"""
import collections, json, math, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'src'), str(ROOT/'scripts')]
from archpipe import flythrough as FT, walkthrough_tour as WT
from archpipe.flyaudit import core, audit
from wt_plan import vmap
from tour_points import classify_views

CELL = .5; AREA = .25; COLS, ROWS = 48, 27; BINS = 12; MAXD = 8.
HUB_MIN_M2 = 12.; HUB2_MIN_M2 = 60.; ARC_MIN_M2 = 6.; NEW_MIN_M2 = 1.; HUB_MIN_WIDTH_M = 2.0; DOOR_KEEP_M = .45; MIN_ROOM_SHARE = .8; PITCH_STEP = 4      # policy (ours)
EYE = 1.35


class Cover:
    def __init__(self, scene='out/wt/villa4/scene.json'):
        self.geom = audit.geometry_for(scene, ROOT/'out/flyaudit'); et = core.element_table(self.geom)
        self.surface = np.array([core.feature_kind(n, g) is not None for n, g in zip(self.geom.elem_names, et['grp'])])
        self.th = core.thresholds(); self.rooms = audit.design_rooms(); self.et = et
        self.RX = np.array([r['rect'] for r in self.rooms.values()]); self.names = list(self.rooms)
        self.RZ = np.array([-3. if r['level'] == 'B' else 0. for r in self.rooms.values()])

    def keys(self, views, informative_only=True):
        """views [(pos, target, lens_mm)] -> list of int64 arrays of cell keys (surface cells hit within MAXD). A view the audit calls wall_dominated or
        blocked (classify_views, same rule) shows nothing worth counting, so its cells are not coverage (informative_only)."""
        out = []; th = self.th; E = len(self.geom.elem_names); N = COLS*ROWS
        for a in range(0, len(views), 48):
            part = views[a:a+48]
            D = np.concatenate([core.ray_dirs(np.asarray(p, float), np.asarray(t, float), COLS, ROWS, l, 36., 9/16.) for p, t, l in part])
            O = np.concatenate([np.repeat(np.asarray(p, float)[None], N, 0) for p, _, _ in part])
            dist, tri, _, _ = self.geom.cast(O, D)
            e = self.geom.tri_elem(tri)
            for k in range(len(part)):
                sl = slice(k*N, (k+1)*N); d = dist[sl]; ee = e[sl]; hit = tri[sl] >= 0
                if informative_only:
                    cnt = np.bincount(ee[hit], minlength=E); near = (hit & (d < th['wall_dominated']['near_m'])).mean()
                    cen = (hit & (d < th['blocked']['near_m'])).reshape(ROWS, COLS)[ROWS//4:3*ROWS//4, COLS//4:3*COLS//4].mean()
                    top = int(cnt.argmax()); md = float(np.median(d[hit])) if hit.any() else 99.
                    bad = (cen >= th['blocked']['min_near_share'] and not self.geom.elem_names[top].startswith('wall')) or near >= th['wall_dominated']['min_near_share'] or (
                        (cnt*self.surface).max()/N >= th['wall_dominated_v2']['min_single_surface_share'] and md < th['wall_dominated_v2']['max_median_dist_m'])
                    if bad:
                        out.append(np.zeros(0, np.int64)); continue
                ok = hit & (d < MAXD); ok &= self.surface[np.maximum(ee, 0)]
                P = O[sl][ok]+D[sl][ok]*d[ok, None]; c = np.floor(P/CELL).astype(np.int64)
                out.append(np.unique(((ee[ok].astype(np.int64)*4096+(c[:, 0]+2048))*4096+(c[:, 1]+2048))*64+(c[:, 2]+32)))
        return out

    def room_of_cells(self, keys, pts_xy=None):
        c = keys % 64-32; y = (keys//64) % 4096-2048; x = (keys//64//4096) % 4096-2048
        return x, y, c


    def owner(self, keys):
        """room index per cell key (-1 none): the first room rectangle (+0.3 m) holding the cell centre, by level height."""
        x, y, c = self.room_of_cells(keys); cx = (x+.5)*CELL; cy = (y+.5)*CELL; zc = (c+.5)*CELL; out = np.full(len(keys), -1)
        for r in range(len(self.names)):
            x0, y0, x1, y1 = self.RX[r]; z0 = self.RZ[r]
            out[(out < 0) & (cx > x0-.3) & (cx < x1+.3) & (cy > y0-.3) & (cy < y1+.3) & (zc > z0-.2) & (zc < z0+3.2)] = r
        return out

    def room_report(self, seen_keys):
        res = json.loads((ROOT/'knowledge/flythrough/tour-spaces.json').read_text())['residual']; k = np.array(sorted(seen_keys), np.int64); o = self.owner(k); rep = {}
        for r, nm in enumerate(self.names):
            cov = res[nm]['coverable_m2']; got = float((o == r).sum())*AREA; rep[nm] = dict(coverable_m2=cov, seen_m2=round(min(got, cov), 1), share=round(min(got, cov)/cov, 2) if cov else None)
        return rep


def candidates(vm, layout, spec, rooms, pitch_step=PITCH_STEP):
    from archpipe.concept.render_views import standing_point_clear
    standing = {lv: vm.F._walls(vm.spec, lv)+vm.F._columns() for lv in FT.LEVEL_Z}; out = []
    for room, r in rooms.items():
        lv = r['level']; free = vm.free(lv); x0, y0, x1, y1 = r['rect']
        if room in ('stair-b', 'stair-gf'): continue      # the stair rooms are transit (walk-and-look), never a stop
        for i in range(0, vm.nx, pitch_step):
            for j in range(0, vm.ny, pitch_step):
                if free[i, j]:
                    x, y = vm.xy(i, j)
                    if x0+.3 < x < x1-.3 and y0+.3 < y < y1-.3 and standing_point_clear(layout, spec, room, x, y, vm.pieces[lv], standing[lv]):
                        out.append((room, lv, (x, y)))
    return out


def select(scene='out/wt/villa4/scene.json'):
    C = Cover(scene); layout, spec, vm = vmap(); wide = WT.lens_rooms(); route = WT.tour_route()
    cands = candidates(vm, layout, spec, C.rooms)
    doors = [(C.et['lo'][i], C.et['hi'][i]) for i, n in enumerate(C.geom.elem_names) if n.startswith('door-') and C.et['hi'][i][2]-C.et['lo'][i][2] > 1.5]
    near_door = lambda xy: any(lo[0]-DOOR_KEEP_M < xy[0] < hi[0]+DOOR_KEEP_M and lo[1]-DOOR_KEEP_M < xy[1] < hi[1]+DOOR_KEEP_M for lo, hi in doors)
    bans = json.loads((ROOT/'knowledge/flythrough/tour-spaces-bans.json').read_text())['doors']
    banned = [(C.et['lo'][i], C.et['hi'][i], bans[n]) for i, n in enumerate(C.geom.elem_names) if n in bans]
    cands = [c for c in cands if not near_door(c[2]) and not any(lo[0]-k < c[2][0] < hi[0]+k and lo[1]-k < c[2][1] < hi[1]+k for lo, hi, k in banned)]      # nothing stops in a doorway: the leaf swings there and the door-open search finds no free swing (kids-a, villa6 admission)
    ref = {'B': tuple(WT.tour_points()['entry-b']), 'GF': tuple(route['stair']['top'])}
    def reach(c):
        try: vm.astar(c[1], ref[c[1]], tuple(c[2])); return True
        except ValueError: return False
    cands = [c for c in cands if reach(c) or c[0] == 'parents-dressing']      # the planner must be able to walk there (the dressing room via its authored pinch route)
    print('candidates', len(cands), flush=True)
    yaws = np.arange(BINS)*2*math.pi/BINS; views = []; meta = []
    for room, lv, (x, y) in cands:
        z = FT.LEVEL_Z[lv]+EYE; lens = 16. if room in wide else 24.
        for yw in yaws:
            views.append((np.array([x, y, z]), np.array([x+math.cos(yw), y+math.sin(yw), z]), lens))
    K = C.keys(views); n = len(cands)
    per = [[K[c*BINS+b] for b in range(BINS)] for c in range(n)]
    allk = np.unique(np.concatenate(K)); idx = {int(k): i for i, k in enumerate(allk)}      # dense ids
    dense = lambda a: np.searchsorted(allk, a)
    per = [[dense(a) for a in row] for row in per]
    x, y, _ = C.room_of_cells(allk)
    cx = (x+.5)*CELL; cy = (y+.5)*CELL; zc = (allk % 64-32+.5)*CELL
    owner = np.full(len(allk), -1)
    for r, (nm, R) in enumerate(C.rooms.items()):
        x0, y0, x1, y1 = R['rect']; z0 = -3. if R['level'] == 'B' else 0.
        m = (cx > x0-.3) & (cx < x1+.3) & (cy > y0-.3) & (cy < y1+.3) & (zc > z0-.2) & (zc < z0+3.2) & (owner < 0)
        owner[m] = r
    print('coverable cells', len(allk), 'owned', int((owner >= 0).sum()), flush=True)
    picks = []; covered = np.zeros(len(allk), bool)
    for lv in ('B', 'GF'):
        sel = [c for c in range(n) if cands[c][1] == lv]
        lvl_cells = np.array([C.rooms[list(C.rooms)[o]]['level'] == lv if o >= 0 else False for o in owner])
        def gain(ids): return float((~covered[ids]).sum())*AREA
        # hubs: full 360s. A point that can see an existing hub (line of sight at eye height) is in that hub's space: the space gets one 360, a second only if it adds >= HUB2_MIN_M2
        hubs = []
        def sees(a, b):
            pa = np.array([*cands[a][2], z0]); pb = np.array([*cands[b][2], z0]); v = pb-pa; d = float(np.linalg.norm(v))
            dist, tri, _, _ = C.geom.cast(pa[None], (v/d)[None]); return tri[0] < 0 or dist[0] >= d-.05
        z0 = FT.LEVEL_Z[lv]+EYE; link = {}
        for c in sel: link[c] = []
        while True:
            g = []
            for c in sel:
                R = C.rooms[cands[c][0]]['rect']
                if c in hubs or min(R[2]-R[0], R[3]-R[1]) < HUB_MIN_WIDTH_M: continue      # a corridor, hall or landing is transit: arcs only
                gg = gain(np.unique(np.concatenate(per[c]))); n_same = len(link[c])
                if n_same == 0 and gg >= HUB_MIN_M2 or n_same == 1 and gg >= HUB2_MIN_M2: g.append((gg, c))
            if not g: break
            best, c = max(g); hubs.append(c)
            for k in sel:
                if sees(k, c): link[k] = link[k]+[c]
            ids = np.unique(np.concatenate(per[c])); bg = [gain(per[c][b]) for b in range(BINS)]
            picks.append(dict(kind='turn', level=lv, room=cands[c][0], point=list(cands[c][2]), gain_m2=best, cand=c, bin_gain=bg)); covered[ids] = True
            print('HUB', lv, cands[c][0], [round(v, 2) for v in cands[c][2]], round(best, 1), flush=True)
        while True:
            best = (0., None)
            for c in sel:
                for b0 in range(BINS):
                    for L in (1, 2, 3, 4):
                        bins = [(b0+k) % BINS for k in range(L)]
                        if len(per[c][bins[0]]) == 0 or len(per[c][bins[-1]]) == 0: continue      # an arc starts and ends on informative headings (a wall-dominated bin shows nothing and costs time)
                        ids = np.unique(np.concatenate([per[c][b] for b in bins])); g_ = gain(ids)/(1+.15*L+.5*sum(len(per[c][b]) == 0 for b in bins))       # a longer arc costs time: favour short ones
                        if g_ > best[0]: best = (g_, (c, b0, L, ids))
            if best[0] < ARC_MIN_M2 or best[1] is None: break
            c, b0, L, ids = best[1]; real = gain(ids)
            picks.append(dict(kind='arc', level=lv, room=cands[c][0], point=list(cands[c][2]), gain_m2=real, cand=c, b0=b0, nbins=L)); covered[ids] = True
            print('ARC', lv, cands[c][0], [round(v, 2) for v in cands[c][2]], 'bins', b0, L, round(real, 1), flush=True)
    # residual per room (stated)
    resid = {}
    for r, nm in enumerate(C.names):
        m = owner == r; resid[nm] = dict(coverable_m2=round(float(m.sum())*AREA, 1), seen_m2=round(float((m & covered).sum())*AREA, 1))
    # classify every hub heading with the audit's measure (24 headings) for the variable turn rate and the best view
    th = C.th; E = len(C.geom.elem_names)
    stations = []
    for p in picks:
        z = FT.LEVEL_Z[p['level']]+EYE; lens = 16. if p['room'] in wide else 24.
        pos = np.array([p['point'][0], p['point'][1], z]); ys = np.arange(24)*2*math.pi/24
        bad, med = classify_views(C.geom, C.surface, th, [(pos, pos+np.array([math.cos(a), math.sin(a), 0.]), lens) for a in ys])
        tab = [[round(math.degrees(a)), bool(b), round(float(m), 2)] for a, b, m in zip(ys, bad, med)]
        k = sum(1 for t in stations if t['room'] == p['room'])
        grid = WT._opaque_grid(vm, p['level']); wall_min = float(WT.ray_depths(vm, grid, np.array([p['point']]))[0].min())
        rec = dict(wall_min_m=round(wall_min, 3), flagged_under_1m=wall_min < 1.02, id=p['room'] if p['kind'] == 'turn' and not any(t['id'] == p['room'] for t in stations) else f"{p['room']}~{'t' if p['kind'] == 'turn' else 'a'}{k+1}", kind=p['kind'], level=p['level'], room=p['room'], point=[round(v, 3) for v in p['point']], gain_m2=round(p['gain_m2'], 1), lens_mm=lens, yaw_table=tab)
        if p['kind'] == 'turn':
            bg = np.array(p['bin_gain']); good = np.array([not tab[2*b][1] for b in range(BINS)])
            b = int(np.where(good, bg, -1).argmax()); rec['best_yaw_deg'] = b*30.; rec['best_view'] = 'coverage'
        else:
            rec['arc'] = [p['b0']*30.-15., p['nbins']*30.]
        stations.append(rec)
    (ROOT/'knowledge/flythrough/tour-spaces.json').write_text(json.dumps(dict(schema='flythrough-tour-spaces/1', method=__doc__.split('\n')[0], policy=dict(
        cell_m=CELL, cell_area_m2=AREA, hub_min_m2=HUB_MIN_M2, hub2_min_m2=HUB2_MIN_M2, hub_min_room_width_m=HUB_MIN_WIDTH_M, arc_min_m2=ARC_MIN_M2, bins=BINS, candidate_pitch_m=.1*PITCH_STEP), stations=stations, residual=resid), indent=1))
    print(len(stations), 'stations;', sum(s['kind'] == 'turn' for s in stations), 'hubs')


def measure(path, scene='out/wt/villa4/scene.json', fps=24, stride=6):
    C = Cover(scene); d = json.loads(Path(path).read_text()); fr = d['frames']; idx = list(range(0, len(fr), stride))
    views = []
    for i in idx:
        c = fr[i]['camera']; views.append((np.array(c['position']), np.array(c['target']), c['lens_mm']))
    K = C.keys(views); seen = set(); new = np.zeros(len(idx))
    for k, a in enumerate(K):
        s = set(a.tolist()); new[k] = len(s-seen)*AREA; seen |= s
    w = int(round(fps/stride)); red = np.array([new[max(0, k-w//2):k+w//2+1].sum() < NEW_MIN_M2*(min(len(idx), k+w//2+1)-max(0, k-w//2))/w for k in range(len(idx))])
    sec = stride/fps; mode = collections.Counter(); modeall = collections.Counter()
    for k, i in enumerate(idx):
        m = fr[i]['phase']; modeall[m] += sec; mode[m] += sec*red[k]
    out = dict(duration_s=round(len(fr)/fps, 1), redundant_s=round(float(red.sum()*sec), 1), unique_surface_m2=round(len(seen)*AREA, 1),
               by_phase={k: dict(total=round(modeall[k], 1), redundant=round(mode[k], 1)) for k in modeall})
    print(json.dumps(out)); return out, red, idx


def refine(scene='out/wt/villa4/scene.json', max_iter=24):
    """Plan the route, give every stop its in-route new surface (what its frames show that no earlier frame of the route showed) and drop stops below
    their minimum (hub HUB_MIN_M2, arc ARC_MIN_M2); repeat until none is dropped. Rewrites the station list of villa-tour.json, records the drops."""
    C = Cover(scene); layout, spec, vm = vmap(); dropped = []; protected = set(); last = None
    for it in range(max_iter):
        route = WT.tour_route(); path = WT.plan_tour(vm); fr = path['frames']; stride = 6
        views = [(np.array(f['camera']['position']), np.array(f['camera']['target']), f['camera']['lens_mm']) for f in fr[::stride]]
        K = [set(a.tolist()) for a in C.keys(views)]; seen = set(); new_by = collections.defaultdict(float)
        for k, a in enumerate(K):
            st = fr[k*stride]['station']; new_by[st] += len(a-seen)*AREA; seen |= a
        short = [r for r, v in C.room_report(seen).items() if v['share'] is not None and v['share'] < MIN_ROOM_SHARE]
        elems = lambda keys: {int(k) for k in np.unique(np.array(sorted(keys), np.int64)//(4096*4096*64))} if keys else set()
        movable = np.array([i for i, n in enumerate(C.geom.elem_names) if n.startswith(('furn-', 'fixture-'))])       # furniture and sanitary fixtures (not the small luminaires): each one seen in the unpruned route stays seen
        now = elems(seen) & {int(e) for e in movable}
        if it == 0: full_feats = set(now)
        short += ['feature:'+C.geom.elem_names[e] for e in sorted(full_feats-now)]
        if last and short and not set(short) <= last['short_before']:       # the last drop left a room under-covered: put it back and keep that stop
            route['stations'].insert(last['at'], last['entry']); protected.add(last['id']); dropped.pop()
            (ROOT/'knowledge/flythrough/villa-tour.json').write_text(json.dumps(route, indent=1)); print('restore', last['id'], 'rooms short', short, flush=True); last = None; continue
        drop = [s['room'] for s in path['stations'] if s['kind'] in ('turn', 'arc') and s['room'] not in protected and new_by[s['room']] < (HUB_MIN_M2 if s['kind'] == 'turn' else ARC_MIN_M2)]
        print('iter', it, 'frames', len(fr), 'dur', round(len(fr)/24, 1), 'stops', sum(s['kind'] != 'pan' for s in path['stations']), 'drop', drop, flush=True)
        if not drop: break
        weakest = min(drop, key=lambda r: new_by[r]); dropped.append(dict(id=weakest, in_route_new_m2=round(new_by[weakest], 1)))
        at = next(i for i, s in enumerate(route['stations']) if s.get('space') == weakest)
        last = dict(id=weakest, at=at, entry=route['stations'][at], short_before=set(short)); del route['stations'][at]
        (ROOT/'knowledge/flythrough/villa-tour.json').write_text(json.dumps(route, indent=1))
    rooms = C.room_report(seen); print({k: v['share'] for k, v in rooms.items()})
    rep = {s['room']: round(new_by[s['room']], 1) for s in path['stations'] if s['kind'] in ('turn', 'arc')}
    (ROOT/'knowledge/flythrough/tour-prune.json').write_text(json.dumps(dict(schema='flythrough-tour-prune/1', rule=f'a stop is kept when its frames add >= {HUB_MIN_M2} m2 (360) / {ARC_MIN_M2} m2 (arc) of surface not shown by any earlier frame of the route; weakest dropped first, route re-measured',
                                                                              dropped=dropped, protected=sorted(protected), kept_in_route_new_m2=rep, room_coverage=rooms), indent=1))


if __name__ == '__main__':
    cmd = sys.argv[1]
    {'select': select, 'measure': measure, 'refine': refine}[cmd](*sys.argv[2:])
