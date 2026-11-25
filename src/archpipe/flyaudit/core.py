"""Per-frame, per-room and whole-route walkthrough audit. Pure numpy over a `Geometry` (see geometry.py).

Thresholds live in knowledge/flyaudit/thresholds.json (pre-registered before any comparison); nothing here renders.
"""
from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
GARDEN_GROUPS = (3, 5)      # ground, context (see geometry.GROUPS): first hit here means "outside"


def thresholds():
    return json.loads((ROOT / 'knowledge/flyaudit/thresholds.json').read_text())


def room_at(rooms, level, x, y):
    for n, r in rooms.items():
        if r['level'] == level and r['rect'][0] < x < r['rect'][2] and r['rect'][1] < y < r['rect'][3]:
            return n
    return None


def ray_dirs(pos, tgt, cols, rows, lens, sensor, aspect_hw, shift=(0., 0.)):
    """Unit ray directions, shape (rows*cols, 3), for one camera (pinhole, pixel centres)."""
    f = np.asarray(tgt, float) - np.asarray(pos, float); f /= np.linalg.norm(f)
    right = np.cross(f, [0., 0., 1.]); right /= np.linalg.norm(right)
    up = np.cross(right, f)
    u = ((np.arange(cols) + .5) / cols - .5 - shift[0]) * sensor / lens
    v = (.5 - (np.arange(rows) + .5) / rows - shift[1]) * sensor / lens * aspect_hw
    uu, vv = np.meshgrid(u, v)
    d = f[None] + uu.reshape(-1, 1) * right[None] + vv.reshape(-1, 1) * up[None]
    return d / np.linalg.norm(d, axis=1, keepdims=True)


def motion(frames, fps, window_s):
    """Horizontal travel direction (unit, or zeros) and speed (m/s) per frame from positions +-window."""
    P = np.array([f['camera']['position'][:2] for f in frames]); n = len(P); w = max(1, int(round(window_s * fps)))
    i0, i1 = np.clip(np.arange(n) - w, 0, n - 1), np.clip(np.arange(n) + w, 0, n - 1)
    d = P[i1] - P[i0]; dist = np.linalg.norm(d, axis=1); span = np.maximum((i1 - i0) / fps, 1e-9)
    speed = dist / span
    dirn = np.where(dist[:, None] > 1e-9, d / np.maximum(dist[:, None], 1e-9), 0.)
    return dirn, speed


def element_table(geom):
    """Per element: group, room (majority), area, xy bbox."""
    E = len(geom.elem_names); t = geom.tris.astype(np.float64)
    area = .5 * np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1)
    A = np.bincount(geom.elem, weights=area, minlength=E)
    room = np.zeros(E, int); grp = np.zeros(E, int)
    R, G = len(geom.room_names), 6
    cnt = np.zeros((E, R)); np.add.at(cnt, (geom.elem, geom.room), 1)
    cnt[:, [i for i, n in enumerate(geom.room_names) if n == '']] -= .5      # prefer a named room on ties
    room = cnt.argmax(1)
    g = np.zeros((E, G)); np.add.at(g, (geom.elem, geom.grp), 1); grp = g.argmax(1)
    lo = np.full((E, 3), np.inf); hi = np.full((E, 3), -np.inf)
    pts = t.reshape(-1, 3); e3 = np.repeat(geom.elem, 3)
    for k in range(3):
        np.minimum.at(lo[:, k], e3, pts[:, k]); np.maximum.at(hi[:, k], e3, pts[:, k])
    return dict(area=A, room=[geom.room_names[i] for i in room], grp=grp, lo=lo, hi=hi)


def membership(et, names, rooms, pad=.25):
    """room -> element indices that belong to it. Walls/columns: thin elements touching the room's rectangle along
    >= 0.3 m. Everything else: bbox centre inside the rectangle. Level by z band; huge elements (>25 m2 footprint) skipped."""
    out = {}
    lo, hi = et['lo'], et['hi']
    for n, r in rooms.items():
        x0, y0, x1, y1 = r['rect']; z0 = -3. if r['level'] == 'B' else 0.
        zin = (hi[:, 2] > z0 + .3) & (lo[:, 2] < z0 + 3.0)
        cx, cy = (lo[:, 0] + hi[:, 0]) / 2, (lo[:, 1] + hi[:, 1]) / 2
        small = np.prod(hi[:, :2] - lo[:, :2], axis=1) < 25
        centre = (cx > x0) & (cx < x1) & (cy > y0) & (cy < y1) & small
        ox = np.minimum(hi[:, 0], x1 + pad) - np.maximum(lo[:, 0], x0 - pad)
        oy = np.minimum(hi[:, 1], y1 + pad) - np.maximum(lo[:, 1], y0 - pad)
        thin = np.minimum(hi[:, 0] - lo[:, 0], hi[:, 1] - lo[:, 1]) < .6
        touch = (ox > .3) & (oy > .3) & thin
        isw = np.array([nm.startswith(('wall-', 'column')) for nm in names])
        out[n] = [int(i) for i in np.flatnonzero(zin & np.where(isw, touch, centre))]
    return out


def feature_kind(name, grp):
    if name.startswith(('room-', 'ceiling', 'floor')):
        return None                       # floors and ceilings are always in view; not "features"
    if grp == 0:
        return 'wall' if name.startswith(('wall', 'column')) else 'shell'
    return {1: 'dressing', 2: 'fixture', 4: 'furniture'}.get(grp)


def analyse_frames(geom, frames, settings, rooms, th, subjects=None, progress=None, surface=None):
    """Cast the ray grid for every `frame_stride`-th frame. -> (records, element stats, subject stats)."""
    fps = settings['fps']; stride = th['grid']['frame_stride']; cols, rows = th['grid']['cols'], th['grid']['rows']
    W, H = settings['final_resolution']; asp = H / W
    dirn, speed = motion(frames, fps, th['backward']['travel_window_s'])
    E = len(geom.elem_names); surface = np.ones(E, bool) if surface is None else surface; minr = th['seen']['min_rays_in_one_frame']
    rnames = list(rooms); RX = np.array([rooms[n]['rect'] for n in rnames]); RZ = np.array([-3. if rooms[n]['level'] == 'B' else 0. for n in rnames])
    st = dict(rooms=rnames, room_frames=np.zeros((len(rnames), E), int), room_min_d=np.full((len(rnames), E), np.inf), frames=np.zeros(E, int), min_d=np.full(E, np.inf), sum_d=np.zeros(E), max_share=np.zeros(E),
              first=np.full(E, -1))
    daylit = {}
    recs = []; sub = subjects or []
    sub_stats = {s['id']: dict(in_frustum=0, visible=0, frames_room=0, blockers={}, best=None) for s in sub}
    hfov = 2 * math.atan(.5 * 36 / 24)
    for fi in range(0, len(frames), stride):
        f = frames[fi]; c = f['camera']; pos = np.array(c['position']); tgt = np.array(c['target'])
        D = ray_dirs(pos, tgt, cols, rows, c['lens_mm'], c['sensor_mm'], asp, (c.get('shift_x', 0.), c.get('shift_y', 0.)))
        O = np.repeat(pos[None], len(D), 0)
        dist, tri, gdist, _ = geom.cast(O, D, doors=f.get('doors'))
        hit = tri >= 0
        e = geom.tri_elem(tri); g = np.where(hit, geom.grp[np.maximum(tri, 0)], -1)
        garden = f['segment'] != 'interior'
        near = hit & (dist < th['wall_dominated']['near_m'])
        grid = near.reshape(rows, cols)
        c0, c1, r0, r1 = cols // 4, 3 * cols // 4, rows // 4, 3 * rows // 4
        centre_near = (hit & (dist < th['blocked']['near_m'])).reshape(rows, cols)[r0:r1, c0:c1].mean()
        out = (~hit) | np.isin(g, GARDEN_GROUPS)
        # elements
        cnt = np.bincount(e[hit], minlength=E)
        seen = cnt >= minr
        st['frames'] += seen
        newly = seen & (st['first'] < 0); st['first'][newly] = fi
        np.minimum.at(st['min_d'], e[hit], dist[hit]); np.add.at(st['sum_d'], e[hit], dist[hit])
        st['max_share'] = np.maximum(st['max_share'], cnt / len(D))
        P = pos[None] + D * np.where(hit, dist, 0.)[:, None]
        inside = ((P[:, None, 0] > RX[None, :, 0] - .3) & (P[:, None, 0] < RX[None, :, 2] + .3) & (P[:, None, 1] > RX[None, :, 1] - .3)
                  & (P[:, None, 1] < RX[None, :, 3] + .3) & (P[:, None, 2] > RZ[None] - .2) & (P[:, None, 2] < RZ[None] + 3.2) & hit[:, None])
        for k in np.flatnonzero(inside.any(0)):
            m = inside[:, k]; ck = np.bincount(e[m], minlength=E)
            st['room_frames'][k] += ck >= minr
            np.minimum.at(st['room_min_d'][k], e[m], dist[m])
        top = np.argsort(-cnt)[:4]
        top_surface = float((cnt * surface).max() / len(D))
        # direction of travel
        fwd = tgt[:2] - pos[:2]; fwd /= max(np.linalg.norm(fwd), 1e-9)
        moving = speed[fi] >= th['backward']['min_speed_m_s']
        ang = math.degrees(math.acos(float(np.clip(fwd @ dirn[fi], -1, 1)))) if moving else None
        cam_room = room_at(rooms, f['level'], pos[0], pos[1])
        rec = dict(i=fi, t=round(fi / fps, 3), level=f['level'], room=cam_room, stair=f['stair'], garden=garden,
                   x=round(float(pos[0]), 3), y=round(float(pos[1]), 3), yaw=round(math.degrees(math.atan2(fwd[1], fwd[0])), 1),
                   near_share=round(float(near.mean()), 3), centre_near_share=round(float(centre_near), 3),
                   out_share=round(float(out.mean()), 3), glass_share=round(float((gdist < np.where(hit, dist, np.inf)).mean()), 3),
                   top_surface_share=round(top_surface, 3), void_share=round(float((~hit).mean()), 3),
                   median_dist=round(float(np.median(dist[hit])), 2) if hit.any() else None,
                   travel_angle=None if ang is None else round(ang, 1), speed=round(float(speed[fi]), 3),
                   top=[(geom.elem_names[k], round(float(cnt[k] / len(D)), 3)) for k in top if cnt[k]])
        recs.append(rec)
        # key subjects, only while the camera stands in (or at the doorway of) the subject's room
        for s in sub:
            if cam_room not in s['rooms']:
                continue
            ss = sub_stats[s['id']]; ss['frames_room'] += 1
            v = s['points'] - pos; d = np.linalg.norm(v, axis=1); u = v / d[:, None]
            cosang = u @ ((tgt - pos) / np.linalg.norm(tgt - pos))
            infr = cosang > math.cos(hfov / 2 * .9)      # inside ~90 % of the horizontal half-angle
            if not infr.any():
                continue
            ss['in_frustum'] += 1
            od, ot, _, _ = geom.cast(np.repeat(pos[None], int(infr.sum()), 0), u[infr], doors=f.get('doors'))
            te = geom.tri_elem(ot); ok = (od >= d[infr] - .05) | np.isin(te, s['elems'])
            frac = float(ok.mean())
            if frac >= .3:
                ss['visible'] += 1
                if ss['best'] is None or frac > ss['best'][0]:
                    ss['best'] = (frac, fi, float(np.median(d[infr])))
            else:
                for k in te[~ok]:
                    if k >= 0:
                        nm = geom.elem_names[k]; ss['blockers'][nm] = ss['blockers'].get(nm, 0) + 1
        if progress and fi % (stride * 500) == 0:
            progress(fi, len(frames))
    return recs, st, sub_stats


def classify(recs, th, no_daylight_rooms, version=2, key='cat'):
    """Mutates each record with `key` following the registered priority. v1 = thresholds.json as registered;
    v2 adds single-surface dominance to wall_dominated (see thresholds.json revisions)."""
    for r in recs:
        if r['travel_angle'] is not None and r['travel_angle'] > th['backward']['min_angle_deg']:
            cat = 'backward'
        elif r['centre_near_share'] >= th['blocked']['min_near_share'] and not (r['top'] and r['top'][0][0].startswith('wall')):
            cat = 'blocked'      # something other than a plain wall (furniture, door, pillar) is in the middle of the view
        elif r['near_share'] >= th['wall_dominated']['min_near_share'] or (
                version >= 2 and not r['garden'] and r['top_surface_share'] >= th['wall_dominated_v2']['min_single_surface_share']
                and (r['median_dist'] or 99) < th['wall_dominated_v2']['max_median_dist_m']):
            cat = 'wall_dominated'
        elif r['out_share'] >= th['outward']['min_out_share'] and not r['garden']:
            cat = 'outward'
        elif r['room'] in no_daylight_rooms and not r['garden']:
            cat = 'dark'
        else:
            cat = 'informative'
        r[key] = cat
    return recs


def add_modes(recs, fps, th):
    """walking (moving), sweeping (in-place rotation >= 8 deg/s: the 360s) or holding (still). A wall in a hold is worse than in a sweep."""
    dt = (recs[1]['i'] - recs[0]['i']) / fps if len(recs) > 1 else 1.
    for k, r in enumerate(recs):
        a, b = recs[max(0, k - 2)], recs[min(len(recs) - 1, k + 2)]
        dy = ((b['yaw'] - a['yaw'] + 180) % 360) - 180
        rate = abs(dy) / max(1e-9, (b['i'] - a['i']) / fps)
        r['yaw_rate'] = round(rate, 1)
        r['mode'] = 'walking' if r['speed'] >= th['backward']['min_speed_m_s'] else 'sweeping' if rate >= 8 else 'holding'
    return recs


def runs(recs, fps, stride, min_s, bad=('wall_dominated', 'backward', 'blocked')):
    """Consecutive bad frames lasting more than min_s."""
    out, cur = [], []
    def flush():
        if cur and len(cur) * stride / fps > min_s:
            cats = {}
            for r in cur:
                cats[r['cat']] = cats.get(r['cat'], 0) + 1
            modes = {m: sum(1 for r in cur if r['mode'] == m) for m in ('walking', 'sweeping', 'holding')}
            out.append(dict(start_frame=cur[0]['i'], end_frame=cur[-1]['i'], modes=modes, seconds=round(len(cur) * stride / fps, 2),
                            room=cur[0]['room'], level=cur[0]['level'], cats=cats))
    for r in recs:
        if r['cat'] in bad:
            cur.append(r)
        else:
            flush(); cur = []
    flush()
    return out


def full_360(recs, room, th, fps, stride, hfov_deg=73.74):
    """Best standing point for a 360: bearings covered by frames within the radius of one in-room frame."""
    rs = [r for r in recs if r['room'] == room]
    if not rs:
        return dict(coverage_deg=0, full=False, at=None)
    P = np.array([[r['x'], r['y']] for r in rs]); Y = np.array([r['yaw'] for r in rs])
    best = (0, None, 0)
    for k in range(0, len(rs), max(1, len(rs) // 150)):
        m = np.linalg.norm(P - P[k], axis=1) <= th['full_360']['standing_radius_m']
        bins = np.zeros(360, bool)
        for y in Y[m]:
            bins[(np.arange(int(round(y - hfov_deg / 2)), int(round(y + hfov_deg / 2)) + 1)) % 360] = True
        if bins.sum() > best[0]:
            best = (int(bins.sum()), [round(float(P[k][0]), 2), round(float(P[k][1]), 2)], int(m.sum()))
    return dict(coverage_deg=best[0], full=best[0] >= th['full_360']['min_coverage_deg'], at=best[1],
                seconds_at_spot=round(best[2] * stride / fps, 1))
