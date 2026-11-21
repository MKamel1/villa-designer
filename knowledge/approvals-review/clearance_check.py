"""RA2: do the authored furniture items clash with the approved G1 / M elements? Independent of the room-review engine.

Usage: python clearance_check.py procedural-scene.json OUT.json
Checks every furniture item (plus derived chairs) against, on its own level: the understair cupboard (footprint and its
door swing), guard paths (buffered by the guard thickness), walls (spec rectangles, incl. the M corner extensions),
the lounge street door opening, and door swings with a declared `swing` (disc of arc_radius about the hinge).
Reports overlap (m) or the minimum gap. Positive control: the pre-resolution store (w=1.80) must report 0.54 m.
"""
import json, math, sys
from pathlib import Path
from archpipe.concept.villa_furnish import footprint
from archpipe.concept.furniture_stage2 import derived_seats

scene = json.loads(Path(sys.argv[1]).read_text()); ctx = scene['authoring_room_context']; sp = ctx['specification']
items = ctx['furniture'] + derived_seats(ctx['furniture'])


def rect_gap(a, b):  # >0 gap, <=0 penetration depth (max of axis overlaps)
    gx = max(a[0] - b[2], b[0] - a[2]); gy = max(a[1] - b[3], b[1] - a[3])
    return max(gx, gy) if (gx > 0 or gy > 0) is False else math.hypot(max(gx, 0), max(gy, 0)) if max(gx, gy) > 0 else max(gx, gy)


def seg_rect(p, q, half):  # bbox of a buffered axis-aligned segment
    return (min(p[0], q[0]) - half, min(p[1], q[1]) - half, max(p[0], q[0]) + half, max(p[1], q[1]) + half)


def disc_gap(c, r, f):
    dx = max(f[0] - c[0], 0, c[0] - f[2]); dy = max(f[1] - c[1], 0, c[1] - f[3])
    return math.hypot(dx, dy) - r


obst = []  # (level, name, rect or ('disc', c, r))
cup = sp['understair_cupboard']
obst.append((cup['level'], 'understair-cupboard', (cup['x0'], cup['y0'], cup['x1'], cup['y1'])))
for w in cup['walls']:
    if 'door' in w['id']:
        pass
cup_door = [w for w in cup['walls'] if 'door' in w['id']]
for g in sp['guards']:
    pts = g['path']
    for p, q in zip(pts, pts[1:]):
        obst.append((g['level'], g['id'], seg_rect(p, q, g.get('thickness_m', 0.05) / 2 + 0.02)))
for w in sp['walls']:  # exact axis extent, half thickness across (no end padding: corners are the neighbour wall's)
    t = w['thickness'] / 2; x0, x1 = sorted((w['x0'], w['x1'])); y0, y1 = sorted((w['y0'], w['y1']))
    obst.append((w['level'], 'wall', (x0, y0 - t, x1, y1 + t) if abs(w['y0'] - w['y1']) < 1e-6 else (x0 - t, y0, x1 + t, y1)))
door = sp['doors'][9]
orient, c, a, b = door['span']
obst.append((door['level'], 'lounge-door-opening (3.71 m) + 0.3 m approach', (c - 0.3, a, c + 0.3, b) if orient == 'v' else (a, c - 0.3, b, c + 0.3)))
for d in sp['doors']:
    if d.get('swing'):
        s = d['swing']; obst.append((d['level'], 'door-swing', ('disc', (s['hinge_x'], d['y']), s['arc_radius'])))

report = []
for it in items:
    fp = footprint(it)
    for lvl, name, o in obst:
        if lvl != it['level']:
            continue
        if name == 'wall' and it['type'] in ('rug',):
            continue
        gap = disc_gap(o[1], o[2], fp) if o[0] == 'disc' else rect_gap(fp, o)
        if gap < -1e-6 or (name != 'wall' and gap < 0.05):
            report.append(dict(item=it['id'], room=it['room'], against=name, gap_m=round(gap, 3)))
store = next(i for i in items if i['id'] == 'stair-flight-store')
sx0, sx1 = footprint(store)[0], footprint(store)[2]
old_store = dict(store, w=1.80, cx=store['cx'] + 0.3)
print('store x %.3f..%.3f; understair cupboard starts %.3f -> gap %.3f m' % (sx0, sx1, cup['x0'], cup['x0'] - sx1))
print('POSITIVE CONTROL w=1.80 store: x %.3f..%.3f -> overlap %.3f m' % (footprint(old_store)[0], footprint(old_store)[2], footprint(old_store)[2] - cup['x0']))
print('violations/near (<5 cm) items:', json.dumps(report, indent=1))
Path(sys.argv[2]).write_text(json.dumps(report, indent=1))
