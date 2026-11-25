"""WT tour planner: a 360 in every room, walking that looks where it goes, the real flight, the garden thresholds.

Replaces the look-direction logic of `flythrough.sample_villa_path` (a Viterbi that pushed the camera away from
walls and so turned it back toward things) with an explicit yaw programme per phase:

* walk   heading = direction of the route `lookahead_m` ahead, smoothed; never backward by construction;
* turn   at the room's 360 point: arrive, sweep through the room's best view (hold), complete 360 degrees, end on
         the heading of the next leg, so the walk starts already facing where it goes;
* pan    at a garden threshold (inside the closed pane): face the glass, pan +-garden_pan_deg, face it again;
* stair  the real flight, climbed, with the camera pitched up the flight (vertical lens shift).

Output is a `flythrough-villa-path/1` record, so prepare/assembly/admission/exposure/render are unchanged.
All lengths metres, angles degrees anticlockwise from +x unless a name says radians.
"""
from __future__ import annotations
import json
import math
from pathlib import Path

import numpy as np

from . import flythrough as FT
from .flythrough import LEVEL_Z, CELL, level_at, stair_ground, stair_extent, digest, _opaque_grid, _smooth

ROOT = Path(__file__).resolve().parents[2]
ANGLES = np.arange(72)*2*math.pi/72


def tour_policy():
    p = dict(FT.villa_policy())
    p.update(json.loads((ROOT/'knowledge/flythrough/tour-policy.json').read_text()))
    return p


def tour_route():
    return json.loads((ROOT/'knowledge/flythrough/villa-tour.json').read_text())


def wrap(deg):
    return (deg+180.) % 360.-180.


def lens_rooms():
    return set(json.loads((ROOT/'knowledge/flythrough/lens-rooms.json').read_text())['rooms'])


def lens_profile(n, wide_spans, fps, base, wide, ease_s):
    """Focal length per frame: `wide` inside the frame spans, `base` further than `ease_s` seconds from any span, smoothstep between.

    Spans are (first, last) frame indices of the 360 turns in small rooms. The ease runs outside the span (on the walk
    arriving at it and the walk leaving it) so it is always under a moving or turning camera and never a cut."""
    lens = np.full(n, float(base))
    if not wide_spans:
        return lens
    i = np.arange(n)
    for a, b in wide_spans:
        d = np.maximum(np.maximum(a-i, i-b), 0)/fps          # seconds outside the span
        u = np.clip(1.-d/ease_s, 0., 1.)
        lens = np.minimum(lens, base-(base-wide)*(u*u*(3.-2.*u)))
    return lens


def smooth_series(v, width):
    """Centred moving average over `width` samples (edge-padded): a step in `v` becomes a ramp `width` samples long."""
    v = np.asarray(v, float); w = max(1, int(width)); pad = w//2
    k = np.ones(w)/w; x = np.concatenate([np.full(pad, v[0]), v, np.full(w-1-pad, v[-1])])
    return np.convolve(x, k, mode='valid')


def exposure_group_of(room, phase, station, dark_rooms):
    """The exposure group a frame is metered in: its garden pan, its dark room, else the house day group."""
    if phase == 'pan':
        return 'pan-'+str(station)
    if room in dark_rooms:
        return 'dark-'+room
    return 'interior'


# ---- the 360 point of a room ------------------------------------------------------------------------
def ray_depths(vm, grid, pts, angles=ANGLES, limit=8., step=.05):
    """First wall/column hit distance along each angle from each point; `limit` if none. pts (N,2) -> (N,len(angles))."""
    d = np.arange(step, limit+1e-9, step); out = np.empty((len(pts), len(angles)))
    for a in range(0, len(pts), 64):
        p = np.asarray(pts[a:a+64], float)
        ci = np.rint((p[:, 0, None, None]+np.cos(angles)[None, :, None]*d-vm.x0)/CELL).astype(int)
        cj = np.rint((p[:, 1, None, None]+np.sin(angles)[None, :, None]*d-vm.y0)/CELL).astype(int)
        inside = (ci >= 0) & (ci < vm.nx) & (cj >= 0) & (cj < vm.ny)
        hit = np.where(inside, grid[np.clip(ci, 0, vm.nx-1), np.clip(cj, 0, vm.ny-1)], True)
        out[a:a+64] = np.where(hit.any(2), d[hit.argmax(2)], limit)
    return out


def still_yaws():
    """room -> (yaw_deg, view id) from the still-render set: a still standing in the room first, else any that covers it."""
    stills = json.loads((ROOT/'knowledge/flythrough/tour-stills.json').read_text())
    return stills


def best_view_yaw(room, rect, stills, depth72, wall_floor=1.5):
    standing = [(k, v) for k, v in stills.items() if room in v['covers'] and rect[0] < v['pos'][0] < rect[2] and rect[1] < v['pos'][1] < rect[3]]
    covering = [(k, v) for k, v in stills.items() if room in v['covers']]
    for k, v in standing+covering:
        i = int(round(math.radians(v['yaw'])/(2*math.pi)*72)) % 72
        if depth72[i] >= wall_floor:      # the still's subject must not be a wall from our point
            return v['yaw'], k
    # no still, or its direction is blocked from the 360 point: deepest 74-degree wedge
    wedge = np.array([np.mean(np.minimum(depth72[(i+np.arange(-6, 7)) % 72], 6.)) for i in range(72)])
    return math.degrees(ANGLES[int(wedge.argmax())]), 'deepest-wedge'


def tour_point_records():
    f = ROOT/'knowledge/flythrough/tour-points.json'
    return json.loads(f.read_text())['points'] if f.is_file() else {}


def tour_spaces():
    """id -> stop (turn = a full 360, arc = a partial look) chosen by scripts/wt_cover.py from surface coverage; villa-tour.json stations name them by `space`."""
    f = ROOT/'knowledge/flythrough/tour-spaces.json'
    return {t['id']: t for t in json.loads(f.read_text())['stations']} if f.is_file() else {}


def tour_points():
    """Authored 360 points chosen by scripts/tour_points.py with the audit's own measure (room -> (x, y))."""
    return {k: tuple(v['point']) for k, v in tour_point_records().items()}


def audited_best_yaw(still_yaw, yaw_table):
    """The still's heading when the audit finds that heading informative from the 360 point, else the not-bad heading with the longest sightline.

    yaw_table rows are [yaw_deg, bad, median_hit_m] for evenly spaced headings. Returns (yaw_deg, 'still'|'audit-longest-sightline')."""
    ys = np.array([r[0] for r in yaw_table], float); bad = np.array([r[1] for r in yaw_table], bool); med = np.array([r[2] for r in yaw_table], float)
    if still_yaw is not None:
        k = int(np.abs((ys-still_yaw+180.) % 360.-180.).argmin())
        if not bad[k]:
            return still_yaw, 'still'
    k = int(np.where(bad, -1e9, med).argmax()) if (~bad).any() else int(med.argmax())
    return float(ys[k]), 'audit-longest-sightline'


def room_points(vm, policy_=None, stills=None, proxies=None, bounds=None, fixed=None):
    """The 360 point of every room: max visible floor area and features with every direction at least 1.0 m from a wall.

    Candidates are free cells (standing policy plus evaluated furniture meshes) inside the room rectangle. Score =
    area visible over 72 rays (0.5 d^2 dtheta, d capped at 6 m, rays continue through door gaps) plus 1.5 per piece of
    the room's furniture in line of sight. Among points whose shortest wall ray is >= point_wall_clearance_m the best
    score wins; if none exists the room is `flagged` and the point with the longest shortest ray wins.
    """
    policy_ = policy_ or tour_policy(); stills = stills if stills is not None else still_yaws()
    need = policy_['point_wall_clearance_m']+.02; out = {}; proxies = proxies or {}; bounds = bounds or {}; fixed = {**(fixed or {}), **proxies}
    for lv in LEVEL_Z:
        grid = _opaque_grid(vm, lv); free = vm.free(lv); clear = vm.clearance_cells(lv)
        for room, r in vm.rooms[lv].items():
            rect = r['rect']
            cells = [(i, j) for i in range(vm.nx) for j in range(vm.ny)
                     if free[i, j] and rect[0] < vm.xy(i, j)[0] < rect[2] and rect[1] < vm.xy(i, j)[1] < rect[3]
                     and (room not in bounds or (bounds[room][0] < vm.xy(i, j)[0] < bounds[room][2] and bounds[room][1] < vm.xy(i, j)[1] < bounds[room][3]))]
            if room in fixed:       # authored point: the flight proxies (not walkable floor) and the audit-chosen points (tour-points.json)
                pts = np.array([fixed[room]], float)
            elif not cells:
                out[room] = dict(level=lv, point=None, reason='no free standing cell (not walkable)'); continue
            else:
                pts = np.array([vm.xy(*c) for c in cells]); room_clear = np.array([min(clear[c], 4) for c in cells])
            depth = ray_depths(vm, grid, pts)
            wall_min = depth.min(1)
            area = (.5*np.minimum(depth, 6.)**2*(2*math.pi/72)).sum(1)
            feats = [i for i in vm.items if i['level'] == lv and rect[0] < (vm.F.footprint(i)[0]+vm.F.footprint(i)[2])/2 < rect[2]
                     and rect[1] < (vm.F.footprint(i)[1]+vm.F.footprint(i)[3])/2 < rect[3]]
            seen = np.zeros(len(pts))
            for it in feats:
                x0, y0, x1, y1 = vm.F.footprint(it); cx, cy = (x0+x1)/2, (y0+y1)/2
                dx, dy = cx-pts[:, 0], cy-pts[:, 1]; dist = np.hypot(dx, dy)
                k = np.rint(np.arctan2(dy, dx)/(2*math.pi)*72).astype(int) % 72
                seen += (depth[np.arange(len(pts)), k] > dist-.3)
            score = area+1.5*seen+(.3*room_clear if room not in fixed else 0.)
            ok = wall_min >= need
            if ok.any():
                pick = int(np.where(ok, score, -1e9).argmax()); flagged = False
            else:
                pick = int(np.lexsort((score, wall_min))[-1]); flagged = True
            yaw, source = best_view_yaw(room, rect, stills, depth[pick])
            if room in fixed and 'yaw_table' in tour_point_records().get(room, {}):
                still = yaw if source != 'deepest-wedge' else None
                yaw, source = audited_best_yaw(still, tour_point_records()[room]['yaw_table'])
                source = source if source != 'still' else best_view_yaw(room, rect, stills, depth[pick])[1]
            out[room] = dict(level=lv, proxy=room in proxies, point=[float(pts[pick][0]), float(pts[pick][1])], wall_min_m=float(wall_min[pick]),
                             flagged_under_1m=flagged, visible_area_m2=float(area[pick]), features_visible=int(seen[pick]),
                             features_in_room=len(feats), best_yaw_deg=float(yaw), best_view=source,
                             room_min_dimension_m=float(min(rect[2]-rect[0], rect[3]-rect[1])))
    return out


# ---- yaw programmes: rest-to-rest turns with eased rate ---------------------------------------------
def variable_turn(A, rate_fn, accel, dt=1/240.):
    """Rest-to-rest rotation through A degrees at the rate `rate_fn(theta)` (deg/s) wherever the yaw rate can follow it:
    the rate never changes faster than `accel` and the turn starts and ends at rest. -> (duration, theta(t))."""
    th = 0.; v = 0.; ts = [0.]; xs = [0.]; t = 0.
    while th < A-1e-6:
        goal = min(rate_fn(th), math.sqrt(2*accel*max(th, 1e-9)), math.sqrt(2*accel*max(A-th, 1e-9)))
        v += float(np.clip(goal-v, -accel*dt, accel*dt)); v = max(v, 1.)       # 1 deg/s floor so the turn always finishes
        th = min(A, th+v*dt); t += dt; ts.append(t); xs.append(th)
    ts = np.array(ts); xs = np.array(xs)
    return float(ts[-1]), (lambda tt: np.interp(np.asarray(tt, float), ts, xs))


def turn_curve(angle, rate, accel):
    """(duration, theta(t)) for a signed rest-to-rest rotation of `angle` degrees: trapezoid in yaw rate (triangle if short).

    `rate` may be a function of the angle turned so far (deg -> deg/s), see variable_turn."""
    A = abs(angle)
    if A < 1e-9:
        return 0., lambda t: np.zeros_like(np.asarray(t, float))
    if callable(rate):
        T, th = variable_turn(A, rate, accel); sg = math.copysign(1., angle)
        return T, (lambda t: sg*th(t))
    ramp = rate/accel
    if A >= rate*ramp:
        cruise = (A-rate*ramp)/rate; peak = rate
    else:
        peak = math.sqrt(A*accel); ramp = peak/accel; cruise = 0.
    T = 2*ramp+cruise; sgn = math.copysign(1., angle)

    def theta(t):
        t = np.clip(np.asarray(t, float), 0, T)
        up = .5*accel*t**2
        mid = .5*accel*ramp**2+peak*(t-ramp)
        dn = A-.5*accel*(T-t)**2
        return sgn*np.where(t < ramp, up, np.where(t < ramp+cruise, mid, dn))
    return T, theta


def programme(waypoints, holds, rate, accel):
    """Piecewise yaw: cumulative signed angles `waypoints` (first 0), `holds` seconds at each; returns (T, theta(t)).

    `rate` is one number or one per segment."""
    if callable(rate):      # rate(cumulative angle) -> deg/s; each segment sees its own start angle
        rates = [None]+[(lambda th, b=waypoints[k-1]: rate(b+th)) for k in range(1, len(waypoints))]
    else:
        rates = [rate]*len(waypoints) if np.isscalar(rate) else [None]+list(rate)
    parts = []   # (start time, duration, theta0, theta fn, kind)
    t0 = 0.
    if holds[0] > 0:
        parts.append((t0, holds[0], waypoints[0], None)); t0 += holds[0]
    for k in range(1, len(waypoints)):
        T, th = turn_curve(waypoints[k]-waypoints[k-1], rates[k], accel)
        parts.append((t0, T, waypoints[k-1], th)); t0 += T
        if holds[k] > 0:
            parts.append((t0, holds[k], waypoints[k], None)); t0 += holds[k]
    total = t0

    def theta(t):
        t = np.asarray(t, float); out = np.full(t.shape, float(waypoints[-1]))
        for s, d, base, th in parts:
            m = (t >= s) & (t < s+d)
            out[m] = base if th is None else base+th(t[m]-s)
        return out
    return total, theta


def spin_programme(y0, best, exit_, pol, final=False, yaw_table=None, fresh=None):
    """Hold the room's best view, finish a full 360, end on `exit_`. Angles are absolute degrees; returns (T, yaw(t), alpha).

    Sweeping direction sigma is the one that makes the extra turn to the exit heading shorter; the best view is passed
    at alpha degrees along the sweep (rest-to-rest, held `best_view_hold_s`), and the sweep ends at 360 + beta.
    """
    best_hold = pol['best_view_hold_s']; rate, accel = pol['turn_rate_deg_s'], pol['turn_accel_deg_s2']
    exit_ = best if final else exit_
    sigma = 1. if ((exit_-y0) % 360.) <= 180. else -1.
    alpha = (sigma*(best-y0)) % 360.
    beta = (sigma*(exit_-y0)) % 360.
    total_angle = 360.+beta
    wp = [0.]; hd = [0.]
    if fresh is not None and not fresh[int(round(best/30.)) % 12]:
        best_hold = min(best_hold, pol.get('stale_hold_s', .4))      # the best view adds no new surface in this route: a glance, not a hold
    if alpha > 10.:
        wp.append(alpha); hd.append(best_hold)
    else:
        hd[0] = best_hold
    wp.append(total_angle); hd.append(2.5 if final else 0.)
    if yaw_table and pol.get('turn_rate_wall_deg_s'):
        # sweep faster through the headings where the audit finds a wall-dominated frame, slower on the informative ones (both inside the client's 30-45 deg/s band)
        ys = np.array([r[0] for r in yaw_table], float); bad = np.array([r[1] for r in yaw_table], bool)
        grown = bad | np.roll(bad, 1) | np.roll(bad, -1)        # the frame has width: widen each bad heading by one table step
        def rate(theta):
            k = int(np.abs((y0+sigma*theta-ys+180.) % 360.-180.).argmin())
            stale = fresh is not None and not fresh[int(round(((y0+sigma*theta) % 360.)/30.)) % 12]       # nothing new there: sweep fast
            return pol['turn_rate_wall_deg_s'] if grown[k] or stale else pol['turn_rate_view_deg_s']
        T, th = programme(wp, hd, rate, accel)
    else:
        T, th = programme(wp, hd, rate, accel)
    return T, (lambda t: y0+sigma*th(t)), alpha


# ---- walking legs -----------------------------------------------------------------------------------
def _bump(x, width):
    """1 at x=0 falling smoothly to 0 at |x|=width."""
    u = np.clip(1-np.abs(x)/width, 0, 1)
    return np.sin(u*math.pi/2)**2


def tour_sweep():
    p = ROOT/'knowledge/flythrough/tour-sweep.json'
    return json.loads(p.read_text()) if p.exists() else {'min_m2': 0., 'bins': {}}


def tour_aim():
    """leg key -> (s metres along the leg, yaw offset degrees from the look-ahead heading), chosen by scripts/tour_aim.py."""
    f = ROOT/'knowledge/flythrough/tour-aim.json'
    return {k: (np.array(v['s']), np.array(v['offset_deg'])) for k, v in json.loads(f.read_text())['legs'].items()} if f.is_file() else {}


def leg_key(P, dest):
    return f'{P[0][0]:.1f},{P[0][1]:.1f}>{dest}'


def walk_leg(P, stair_flag, pol, aim=None):
    """Walk a polyline of (x, y, ground) points from rest to rest.

    Returns dict(T, at(t) -> (x, y, ground, yaw_deg, stair, pitch_deg), heading_start, heading_end, length).
    Heading looks `lookahead_m` along the route (clamped to the last lookahead of it), smoothed; speed is
    limited by cruise, the stair speed, the walking yaw rate and the acceleration bound.
    """
    ds = .02; P = np.asarray(P, float)
    seg = np.sqrt((np.diff(P, axis=0)**2).sum(1)); L = float(seg.sum())
    n = max(2, int(math.ceil(L/ds))+1); s = np.linspace(0, L, n)
    cum = np.concatenate([[0.], np.cumsum(seg)])
    X = np.stack([np.interp(s, cum, P[:, k]) for k in range(3)], 1)
    sf = np.zeros(n, bool)
    for k, f in enumerate(stair_flag):
        sf |= (s >= cum[k]-1e-9) & (s <= cum[k+1]+1e-9) & bool(f)
    look = pol['lookahead_m']; head = np.zeros(n); last = 0.
    for i in range(n):
        if L-s[i] < look:
            k = int(np.searchsorted(s, max(0., L-look))); j = n-1
        else:
            k = i; j = int(np.searchsorted(s, s[i]+look))
        d = X[min(j, n-1), :2]-X[k, :2]
        head[i] = math.atan2(d[1], d[0]) if np.hypot(*d) > 1e-6 else last
        last = head[i]
    if aim is not None:      # audit-chosen offsets from the look-ahead heading, bounded by the tool to +-60 deg of the travel direction
        head = np.unwrap(head)+np.radians(np.interp(s, aim[0], aim[1]))*(1.-(sf & (X[:, 2] < -1.))) # the flight keeps its own look except the last 1 m of climb
    head = _smooth(np.unwrap(head), .5/ds)
    dyaw = np.abs(np.gradient(head, s)) if n > 2 else np.zeros(n)
    vmax = np.where(sf, pol['stair_speed_m_s'], pol['cruise_speed_m_s'])
    v = np.minimum(vmax, .9*math.radians(pol['walk_yaw_rate_deg_s'])/np.maximum(dyaw, 1e-9)); v = np.maximum(v, .15)
    a = pol['acceleration_m_s2']; v[0] = v[-1] = 0.
    dsi = np.diff(s)
    for _ in range(2):
        for i in range(1, n):
            v[i] = min(v[i], math.sqrt(v[i-1]**2+2*a*dsi[i-1]))
        for i in range(n-2, -1, -1):
            v[i] = min(v[i], math.sqrt(v[i+1]**2+2*a*dsi[i]))
    dt = 2*dsi/np.maximum(v[:-1]+v[1:], 1e-9)
    t = np.concatenate([[0.], np.cumsum(dt)]); T = float(t[-1])
    # pitch up the flight: eased in over 0.8 m from the foot and out over 0.8 m to the landing
    pitch = np.zeros(n)
    if sf.any():
        on = np.where(sf)[0]; s0, s1 = s[on[0]], s[on[-1]]
        pitch = pol['stair_pitch_up_deg']*np.clip(np.minimum((s-s0)/.8, (s1-s-pol.get('stair_pitch_zero_last_m', 0.))/pol.get('stair_pitch_out_m', .8)), 0, 1)
        pitch = np.where(sf, pitch, 0.)

    def at(tt):
        i = np.interp(np.asarray(tt, float), t, np.arange(n))
        i0 = np.floor(i).astype(int); i1 = np.minimum(i0+1, n-1); w = i-i0
        x = X[i0]*(1-w)[:, None]+X[i1]*w[:, None]
        yaw = np.degrees(head[i0]*(1-w)+head[i1]*w)
        return x[:, 0], x[:, 1], x[:, 2], yaw, sf[np.rint(i).astype(int)], pitch[np.rint(i).astype(int)]
    return dict(T=T, at=at, heading_start=math.degrees(head[0]), heading_end=math.degrees(head[-1]), length=L)


# ---- planning ---------------------------------------------------------------------------------------
def _walk_polyline(vm, lv, a, b, via=()):
    pts = [tuple(a)]
    for v in [tuple(q) for q in via]:
        if vm.line_free(lv, pts[-1], v, 1):
            pts.append(v)
        else:
            pts.extend(vm.door_cross(lv, vm.astar(lv, pts[-1], v))[1:])
    pts.extend(vm.door_cross(lv, vm.astar(lv, pts[-1], tuple(b)))[1:])
    # door_cross puts its exit node past the door; when the target lies before it the walk would overshoot and come back (the pantry: the camera
    # reversed for 0.3 s). Drop a vertex that makes a reversal of more than 120 degrees when the shortcut is free.
    k = len(pts)-2
    while k >= 1:
        a, v, c = (np.asarray(q, float) for q in (pts[k-1], pts[k], pts[k+1]))
        u, w = v-a, c-v
        if np.dot(u, w) < -.5*np.linalg.norm(u)*np.linalg.norm(w) and vm.line_free(lv, tuple(a), tuple(c), 1):
            del pts[k]
        k -= 1
    return pts


def _inward(vm, door, offsets):
    """Free standing point just inside a garden door on B (on the room side), with the unit direction facing the glass."""
    x, y = door
    for off in offsets:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            p = (x+dx*off, y+dy*off)
            if vm.room_at('B', *p) and vm.free('B')[vm.cell(*p)]:
                return p, math.degrees(math.atan2(-dy, -dx))
    raise ValueError(f'garden door {door} has no free standing point inside')


def _fresh(room):
    sw = tour_sweep(); b = sw['bins'].get(room)
    return None if b is None else [v >= sw['min_m2'] for v in b]


def plan_tour(vm, route=None, pol=None, aim=None):
    """Plan, sample at 24 fps and return the `flythrough-villa-path/1` record for the tour."""
    route = route or tour_route(); pol = dict(pol or tour_policy()); spec = vm.spec
    aim = tour_aim() if aim is None else aim
    pts = room_points(vm, pol, proxies={k: tuple(v) for k, v in route.get('proxy_points', {}).items()}, bounds=route.get('point_bounds'), fixed=tour_points())
    steps = []       # dicts: kind walk|turn|arc|pan, plus data
    spaces = tour_spaces()
    where = None; level = None
    top, bottom = route['stair']['top'], route['stair']['bottom']
    x0, x1 = stair_extent(spec)

    def stand(room, lv):
        info = pts[room]
        if info['point'] is None:
            raise ValueError(f'room {room} has no 360 point')
        return tuple(info['point']), info

    for st in route['stations']:
        if st.get('stair') == 'up':
            # walk-and-look: one continuous leg from where we stand, to the foot, up the real flight and off the top (the stair rooms are transit)
            appr = pol.get('stair_approach_m', 0.); foot = (x1+appr, bottom[1]); P = []
            if math.dist(where, foot) > .05:
                poly = _walk_polyline(vm, 'B', where, foot, st.get('via', ()))
                P = [(q[0], q[1], LEVEL_Z['B']) for q in poly]
            else:
                P = [(where[0], where[1], LEVEL_Z['B'])]
            nflat = len(P)-1
            if appr:
                P.append((x1, bottom[1], LEVEL_Z['B']))      # the approach to the first riser is judged as the flight (the cupboard toe under it projects past the riser)
            for x in np.arange(x1-.5, x0-.01, -.5):
                P.append((float(x), bottom[1], stair_ground(float(x), spec)))
            P.append((top[0], top[1], LEVEL_Z['GF']))
            flags = [False]*nflat+[True]*(len(P)-1-nflat)
            steps.append(dict(kind='walk', P=P, stair=flags, label='stair', room=None))
            where, level = tuple(top), 'GF'
            continue
        if st.get('garden'):
            p, face = _inward(vm, st['door'], pol['garden_inward_offsets_m'])
            if where is not None and math.dist(where, p) > .05:
                poly = _walk_polyline(vm, 'B', where, p, st.get('via', ()))
                steps.append(dict(kind='walk', P=[(q[0], q[1], LEVEL_Z['B']) for q in poly], stair=[False]*(len(poly)-1), label='walk', room=None))
            steps.append(dict(kind='pan', at=p, face=face, garden=st['garden'], level='B', room=vm.room_at('B', *p)))
            where, level = p, 'B'
            continue
        if st.get('start'):
            where, level = tuple(st['start']), 'B'; steps.append(dict(kind='start')); continue
        if st.get('space'):
            info = dict(spaces[st['space']]); room = info['id']; p = tuple(info['point']); lv = info['level']
        else:
            room = st['room']; p, info = stand(room, None); lv = info['level']
        if where is not None and math.dist(where, p) > .05:
            poly = _walk_polyline(vm, lv, where, p, st.get('via', ()))
            if steps and steps[-1]['kind'] == 'walk' and steps[-1]['label'] == 'stair':
                # off the top of the flight the walk continues into the room without a stop or a turn (walk-and-look)
                steps[-1]['P'] += [(q[0], q[1], LEVEL_Z[lv]) for q in poly[1:]]; steps[-1]['stair'] += [False]*(len(poly)-1)
            else:
                steps.append(dict(kind='walk', P=[(q[0], q[1], LEVEL_Z[lv]) for q in poly], stair=[False]*(len(poly)-1), label='walk', room=None))
        elif where is None:
            steps.append(dict(kind='start'))
        steps.append(dict(kind='arc' if info.get('kind') == 'arc' else 'turn', at=p, room=room, info=info, level=lv, pitch=st.get('pitch')))
        where, level = p, lv

    # the walk legs are fixed; resolve each turn's arrival and exit headings
    def dest_of(k):
        return next((n.get('room') or n.get('garden') for n in steps[k+1:] if n['kind'] in ('turn', 'arc', 'pan')), None)
    legs = [dict(s, key=leg_key(s['P'], dest_of(k)), leg=walk_leg(s['P'], s['stair'], pol, aim.get(leg_key(s['P'], dest_of(k)))))
            if s['kind'] == 'walk' else dict(s) for k, s in enumerate(steps)]
    for k, s in enumerate(legs):
        if s['kind'] not in ('turn', 'arc', 'pan'):
            continue
        prev = legs[k-1]['leg'] if k and legs[k-1]['kind'] == 'walk' else None
        nxt = legs[k+1]['leg'] if k+1 < len(legs) and legs[k+1]['kind'] == 'walk' else None
        s['y0'] = prev['heading_end'] if prev else (nxt['heading_start'] if nxt else 0.)
        s['exit'] = nxt['heading_start'] if nxt else None
        if s['kind'] == 'turn':
            best = s['info']['best_yaw_deg']
            T, yaw, alpha = spin_programme(s['y0'], best, s['exit'] if s['exit'] is not None else best, pol, final=s['exit'] is None, fresh=_fresh(s['room']), yaw_table=s['info'].get('yaw_table') or tour_point_records().get(s['room'], {}).get('yaw_table'))
            s.update(T=T, yawfn=yaw, alpha=alpha)
        elif s['kind'] == 'arc':
            # a partial look: go to the nearer end of the arc, sweep it at the view rate, hold, then turn to the exit heading
            a0, span = s['info']['arc']; a1 = a0+span; near0 = abs(wrap(a0-s['y0'])) <= abs(wrap(a1-s['y0']))
            st0, sg = (a0, 1.) if near0 else (a1, -1.); t1 = wrap(st0-s['y0']); end = st0+sg*span
            e = wrap(s['exit']-end) if s['exit'] is not None else 0.
            T, th = programme([0., t1, t1+sg*span, t1+sg*span+e], [0., 0., pol['arc_hold_s'], 0.], [pol['turn_rate_deg_s'], pol['turn_rate_view_deg_s'], pol['turn_rate_deg_s']], pol['turn_accel_deg_s2'])
            s.update(T=T, yawfn=(lambda t, th=th, y0=s['y0']: y0+th(t)))
        else:
            n = s['face']; t1 = wrap(n-s['y0']); pan = pol['garden_pan_deg']
            e = wrap(s['exit']-n) if s['exit'] is not None else 0.
            wp = [0., t1, t1+pan, t1-pan, t1, t1+e]; hd = [0., 0., .8, .8, 0., 0.]
            T, th = programme(wp, hd, [pol['turn_rate_deg_s'], pol['garden_pan_rate_deg_s'], pol['garden_pan_rate_deg_s'], pol['garden_pan_rate_deg_s'], pol['turn_rate_deg_s']], pol['turn_accel_deg_s2'])
            s.update(T=T, yawfn=(lambda t, th=th, y0=s['y0']: y0+th(t)))

    fps = pol['fps']; frames = []; cur = None

    def emit(n, T, sampler, **tags):
        for k in range(n):
            frames.append((sampler(k*T/n), tags))

    for k, s in enumerate(legs):
        if s['kind'] == 'start':
            continue
        if s['kind'] == 'walk':
            n = max(1, int(math.ceil(s['leg']['T']*fps))); leg = s['leg']; T = leg['T']
            dest = next((n.get('room') or n.get('garden') for n in legs[k+1:] if n['kind'] in ('turn', 'arc', 'pan')), None)
            X, Y, G, YW, SF, PI = leg['at'](np.arange(n)*T/n)
            for q in range(n):
                frames.append(((X[q], Y[q], G[q], float(YW[q]), bool(SF[q]), float(PI[q])), dict(phase='stair' if SF[q] else 'walk', station=None, heading_to=dest)))
            continue
        T = s['T']; n = max(1, int(math.ceil(T*fps)))
        x, y = s['at']; g = LEVEL_Z[s['level']]
        for q in range(n):
            t = q*T/n; yw = float(s['yawfn'](np.array([t]))[0])
            pitch = 0.
            if s['kind'] == 'turn' and s.get('pitch'):
                centre, amount, width = s['pitch']['yaw_deg'], s['pitch']['pitch_deg'], 55.
                pitch = float(amount*_bump(wrap(yw-centre), width))
            phase = 'pan' if s['kind'] == 'pan' else 'turn'
            frames.append(((x, y, g, yw, False, pitch), dict(phase=phase, station=s.get('room') or s.get('garden'))))
    # end state: the last station's final pose
    last = legs[-1]
    if last['kind'] in ('turn', 'arc', 'pan'):
        x, y = last['at']; frames.append(((x, y, LEVEL_Z[last['level']], float(last['yawfn'](np.array([last['T']]))[0]), False, 0.), dict(phase='hold', station=last.get('room') or last.get('garden'))))
    elif last['kind'] == 'walk':
        leg = last['leg']; x, y, g, yw, sf, pi = (v[0] for v in leg['at']([leg['T']]))
        frames.append(((x, y, g, float(yw), bool(sf), float(pi)), dict(phase='walk', station=None)))

    eye = pol['eye_height_m']; out = []; unwrapped = None
    wide_rooms = lens_rooms() if pol.get('wide_lens_mm') else set()
    spans = {}
    for i, (_, tag) in enumerate(frames):
        if tag['phase'] in ('turn', 'hold') and str(tag['station']).split('~')[0] in wide_rooms:
            a, b = spans.get(tag['station'], (i, i)); spans[tag['station']] = (min(a, i), max(b, i))
    pad = int(round(pol.get('wide_pad_s', 0.)*fps)); spans = {k: (max(0, a-pad), min(len(frames)-1, b+pad)) for k, (a, b) in spans.items()}
    lens = lens_profile(len(frames), list(spans.values()), fps, pol.get('base_lens_mm', 24), pol.get('wide_lens_mm', 24), pol.get('lens_ease_s', 1.25))
    dark = set(pol.get('dark_rooms', []))
    for i, ((x, y, g, yw, sf, pitch), tag) in enumerate(frames):
        yaw_deg = yw if unwrapped is None else unwrapped+wrap(yw-unwrapped)   # keep the yaw continuous across phases
        unwrapped = yaw_deg
        ym = math.radians(yaw_deg); z = g+eye; lvl = level_at(g)
        run = math.cos(math.radians(pitch)); room = vm.room_at(lvl, x, y) if not sf else None
        wide = bool(lens[i] < pol.get('base_lens_mm', 24)-1e-9)
        out.append(dict(index=i, seconds=i/fps, yaw_deg=float(yaw_deg), pitch_deg=float(pitch), ground_m=float(g), level=lvl, stair=bool(sf),
                        room=room, segment='interior', phase=tag['phase'], station=tag['station'], heading_to=tag.get('heading_to'),
                        exposure_group=exposure_group_of(room, tag['phase'], tag['station'], dark),
                        caption=pol.get('lens_caption') if wide else None,
                        camera=dict(position=[float(x), float(y), float(z)],
                                    target=[float(x+math.cos(ym)*run), float(y+math.sin(ym)*run), float(z+math.sin(math.radians(pitch)))],
                                    lens_mm=round(float(lens[i]), 4), sensor_mm=36, shift_x=0, shift_y=0)))
    pol['frames'] = len(out)
    stations = []
    for s in legs:
        if s['kind'] in ('turn', 'arc', 'pan'):
            f = [o['index'] for o in out if o['station'] == (s.get('room') or s.get('garden')) and o['phase'] in ('turn', 'pan')]
            info = s.get('info', {})
            stations.append(dict(room=s.get('room'), garden=s.get('garden'), kind=s['kind'], point=list(s['at']), first_frame=f[0], last_frame=f[-1],
                                 seconds=float(s['T']), alpha_deg=s.get('alpha'),
                                 wall_min_m=info.get('wall_min_m'), flagged_under_1m=info.get('flagged_under_1m'),
                                 best_view=info.get('best_view'), best_yaw_deg=info.get('best_yaw_deg'),
                                 visible_area_m2=info.get('visible_area_m2'), features_visible=info.get('features_visible')))
    record = dict(schema='flythrough-villa-path/1', settings=pol, frames=out,
                  distance_m=float(sum(s['leg']['length'] for s in legs if s['kind'] == 'walk')),
                  duration_s=len(out)/fps, stations=stations, route='tour',
                  room_points={k: v for k, v in pts.items()})
    record['sha256'] = digest(record)
    return record


# ---- the lens caption burned into the video ---------------------------------------------------------------
CAPTION_FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


def caption_geometry(width, height, text, font_px_per_height=.055):
    """(font size px, box x0, y0, x1, y1) for a lower-left caption: text height is 5.5 % of the frame height (15 px at 270, 59 px at 1080),
    margin 2.5 % of the height, so the same fraction of the picture at every resolution."""
    from PIL import ImageFont
    size = max(12, int(round(height*font_px_per_height))); font = ImageFont.truetype(CAPTION_FONT, size)
    l, t, r, b = font.getbbox(text); pad = max(4, size//3); m = int(round(height*.025))
    return size, m, height-m-(b-t)-2*pad, m+(r-l)+2*pad, height-m


def burn_caption(img, text):
    """Return a copy of a PIL image with `text` on a dark box at the lower left (white on 72 % black)."""
    from PIL import Image, ImageDraw, ImageFont
    im = img.convert('RGB'); W, H = im.size
    size, x0, y0, x1, y1 = caption_geometry(W, H, text); font = ImageFont.truetype(CAPTION_FONT, size)
    over = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(over)
    d.rounded_rectangle((x0, y0, x1, y1), radius=max(3, size//4), fill=(0, 0, 0, 184))
    l, t, r, b = font.getbbox(text); pad = max(4, size//3)
    d.text((x0+pad-l, y0+pad-t), text, font=font, fill=(255, 255, 255, 255))
    return Image.alpha_composite(im.convert('RGBA'), over).convert('RGB')


# ---- guards specific to the tour ----------------------------------------------------------------------
def direction_findings(frames, max_off_deg=75., ahead_m=1., min_speed=.3):
    """Walking frames whose camera points more than `max_off_deg` away from the route `ahead_m` further on.

    The route is the camera's own track over the next metre (or to the end of the walk phase); frames slower than
    `min_speed` (the start and end of a leg) are not judged. Looking backward is ~180, sideways ~90.
    """
    bad = []; n = len(frames)
    for i, a in enumerate(frames):
        if a['phase'] not in ('walk', 'stair') or i+1 >= n:
            continue
        p = a['camera']['position']; j = i+1; run = 0.
        while j < n and frames[j]['phase'] in ('walk', 'stair') and run < ahead_m:
            run += math.dist(frames[j-1]['camera']['position'][:2], frames[j]['camera']['position'][:2]); j += 1
        q = frames[j-1]['camera']['position']
        speed = math.dist(p[:2], frames[i+1]['camera']['position'][:2])*24
        if run < .3 or speed < min_speed:
            continue
        off = abs(wrap(a['yaw_deg']-math.degrees(math.atan2(q[1]-p[1], q[0]-p[0]))))
        if off > max_off_deg:
            bad.append((a['index'], off))
    return bad


def stair_findings(frames):
    """The flight is climbed continuously: ground rises by the flight height, monotonically, with the camera pitched up."""
    flight = [f for f in frames if f['stair']]
    if not flight:
        return ['no frame on the flight']
    z = [f['ground_m'] for f in flight]; bad = []
    if z[-1]-z[0] < 2.5:
        bad.append(f'flight climbs only {z[-1]-z[0]:.2f} m')
    if any(b < a-1e-6 for a, b in zip(z, z[1:])):
        bad.append('ground falls during the ascent')
    if max(f['pitch_deg'] for f in flight) < 5:
        bad.append('camera never looks up the flight')
    return bad


def coverage_findings(frames, rooms):
    """Every room has a full 360: the unwrapped yaw changes by >= 360 degrees inside its turn frames."""
    bad = []
    for room in rooms:
        fs = [f for f in frames if f['station'] == room and f['phase'] in ('turn', 'hold')]
        if not fs:
            bad.append(f'{room}: no turn'); continue
        yaw = [f['yaw_deg'] for f in fs]
        if max(yaw)-min(yaw) < 359.:
            bad.append(f'{room}: turn covers {max(yaw)-min(yaw):.0f} degrees')
    return bad


def lens_findings(frames, base=24., max_step_mm=.5, ease_s=None, fps=24):
    """Guards for the small-room lens: the focal length never steps (largest change per frame <= max_step_mm), changes only while the camera moves or turns,
    and the caption is on exactly when the lens is wider than `base`. Returns a list of strings (empty = clean)."""
    bad = []
    for a, b in zip(frames, frames[1:]):
        la, lb = a['camera']['lens_mm'], b['camera']['lens_mm']
        if abs(lb-la) > max_step_mm:
            bad.append(f"frame {b['index']}: lens steps {la:.2f} -> {lb:.2f} mm")
        still = a['camera']['position'] == b['camera']['position'] and a['yaw_deg'] == b['yaw_deg'] and a['pitch_deg'] == b['pitch_deg']
        if lb != la and still:
            bad.append(f"frame {b['index']}: lens changes while the camera is still")
    for f in frames:
        wide = f['camera']['lens_mm'] < base-1e-9
        if bool(f.get('caption')) != wide:
            bad.append(f"frame {f['index']}: caption {'on' if f.get('caption') else 'off'} at {f['camera']['lens_mm']:.2f} mm")
    if ease_s is not None:      # the ramp from base to the narrowest lens lasts about ease_s, never a cut
        lens = np.array([f['camera']['lens_mm'] for f in frames]); lo = lens.min()
        if lo < base-1e-9:
            full = (np.abs(np.diff(lens)) > 0).sum()
            if full < ease_s*fps*.8:
                bad.append(f'lens ramps are shorter than {ease_s} s')
    return bad


# ---- the non-informative-frame rule ---------------------------------------------------------------------
# Registered 2026-11-24 BEFORE any measurement (docs/lanes/WT.md, "Non-informative frame rule"); calibrated afterwards
# on the client-watched preview (out/wt/villa3), thresholds recorded in knowledge/flythrough/informative-rule.json.
def informative_rule():
    return json.loads((ROOT/'knowledge/flythrough/informative-rule.json').read_text())


def plane_fraction(points, normals, q=.1):
    """Largest share of hits lying on one plane: normals within ~6 degrees, plane offset within `q` (neighbour bins merge)."""
    points = np.asarray(points, float); normals = np.asarray(normals, float)
    if not len(points):
        return 0.
    off = (points*normals).sum(1)
    key = np.rint(normals/.1).astype(int)
    bins = {}
    for k, o in zip(map(tuple, key), np.floor(off/q).astype(int)):
        bins[(k, o)] = bins.get((k, o), 0)+1
    best = max(bins[(k, o)]+bins.get((k, o+1), 0) for (k, o) in bins)
    return best/len(points)


def frame_metrics(depth, points, normals, rule=None):
    """depth (N,), hit points (N,3), unit normals (N,3) of a grid of rays over the frame (misses carry depth = far)."""
    rule = rule or informative_rule(); depth = np.asarray(depth, float)
    near = float((depth < rule['near_m']).mean())
    plane = plane_fraction(points, normals)
    return dict(near_fraction=near, plane_fraction=plane, median_depth_m=float(np.median(depth)),
                non_informative=bool(near > rule['near_fraction_max'] or plane > rule['plane_fraction_max'] or near+plane >= rule['combined_max']))


def run_findings(rows, fps=24, max_seconds=1., waived=()):
    """Runs of consecutive non-informative frames longer than `max_seconds`. rows: [{index, non_informative}] sorted by index.

    Frames in `waived` (index set) end a run but are reported separately by the caller; the rule never hides them."""
    runs, start, last = [], None, None
    for r in rows:
        bad = r['non_informative'] and r['index'] not in waived
        if bad and start is None:
            start = r['index']
        if bad:
            last = r['index']
        if (not bad) and start is not None:
            runs.append((start, last)); start = None
    if start is not None:
        runs.append((start, last))
    return [dict(first=a, last=b, seconds=(b-a+1)/fps) for a, b in runs if (b-a+1)/fps > max_seconds]
