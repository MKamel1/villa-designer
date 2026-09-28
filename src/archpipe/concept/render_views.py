"""Choose where a photographer stands for a view, from its INTENT (the room it shows and the pieces it must hold), not
from a hand-typed camera. Hand-typed cameras went stale as the design moved and some looked the wrong way (client
2026-09-27: "Some of the cameras are looking at the wrong direction and uninformative").

`choose(lay, room, subjects, lens_mm, eye_m)` searches standing points (in the room, 0.30 m off walls and columns,
0.15 m off furniture, or in one of the room's own door openings) and aims (every 5 deg), and returns the best by:
  1. every subject wholly in frame (hard: the views guard fails otherwise);
  2. how much of the room's design is in view (its furnished pieces, windows and glazed doors);
  3. depth: the distance to the far wall along the aim (a photographer looks across the long axis);
  4. standing near the room's edge (backed off, as a photographer does), never inside a piece.
Ties go to the point nearest the room's entrance side. Works for any layout: it reads rooms, walls, doors, windows
and furniture from the design, nothing from D1 by name.
"""
from __future__ import annotations

import math

from . import revit_spec as RS
from . import villa_furnish as F

STEP, YAW_STEP = 0.1, 5


def _near(q, x, y, c):
    return q[0] - c < x < q[2] + c and q[1] - c < y < q[3] + c


def _in_opening(sp, lv, x, y, room):
    for d in sp["doors"]:
        if d["level"] != lv or d.get("garden") or room not in (d.get("rooms") or []):
            continue
        h = F._door_axis(d) == "h"
        along, across = (x - d["x"], y - d["y"]) if h else (y - d["y"], x - d["x"])
        if abs(along) <= d["width"] / 2 - 0.25 and abs(across) <= 0.35:
            return True
    return False


def _angle(px, py, qx, qy, yaw):
    return (math.atan2(qy - py, qx - px) - yaw + math.pi) % (2 * math.pi) - math.pi


def choose(lay, room, subjects, lens_mm=24.0, sensor_mm=36.0, eye_m=1.35, sp=None):
    sp = sp or RS.build(lay)
    r = lay["rooms"][room]
    lv, rect = r["level"], r["rect"]
    walls = F._walls(sp, lv) + F._columns()
    items = [i for i in F.layout(lay) if i["level"] == lv]
    pieces = [F.footprint(i) for i in items]
    by_id = {i["id"]: i for i in items}
    subj = [c for s in subjects if s in by_id for q in [F.footprint(by_id[s])]
            for c in ((q[0], q[1]), (q[2], q[1]), (q[0], q[3]), (q[2], q[3]))]
    room_items = [((F.footprint(i)[0] + F.footprint(i)[2]) / 2, (F.footprint(i)[1] + F.footprint(i)[3]) / 2)
                  for i in items if i["room"] == room or _near(rect, (F.footprint(i)[0] + F.footprint(i)[2]) / 2,
                                                             (F.footprint(i)[1] + F.footprint(i)[3]) / 2, 0.0)]
    openings = [(w["x"], w["y"]) for w in sp["windows"] if w["level"] == lv and w.get("room") == room] + \
               [(d["x"], d["y"]) for d in sp["doors"] if d["level"] == lv and d.get("garden") and
                room in (d.get("rooms") or [])]
    half = math.atan(sensor_mm / 2 / lens_mm)
    diag = math.hypot(rect[2] - rect[0], rect[3] - rect[1])

    def in_door_band(x, y):
        """Within 0.35 m of the wall line of one of this room's doors, near its opening: the wall is cut there, so
        the wall-clearance test cannot see the door leaf (a camera 30 mm inside the ensuite stood in its leaf)."""
        for d in sp["doors"]:
            if d["level"] != lv or room not in (d.get("rooms") or []):
                continue
            h = F._door_axis(d) == "h"
            along, across = (x - d["x"], y - d["y"]) if h else (y - d["y"], x - d["x"])
            if abs(across) <= 0.35 and abs(along) <= d["width"] / 2 + 0.3:
                return True
        return False

    def ok(x, y):
        if any(_near(q, x, y, 0.15) for q in pieces):
            return False
        if in_door_band(x, y):
            return _in_opening(sp, lv, x, y, room)
        if _near(rect, x, y, 0.0):
            return not any(_near(q, x, y, 0.30) for q in walls)
        return False

    def depth(x, y, yaw):
        # distance along the aim to the room rectangle's far edge
        dx, dy = math.cos(yaw), math.sin(yaw)
        ts = []
        for edge, d_, p_ in ((rect[0], dx, x), (rect[2], dx, x), (rect[1], dy, y), (rect[3], dy, y)):
            if abs(d_) > 1e-9:
                t = (edge - p_) / d_
                if t > 0:
                    ts.append(t)
        return min(ts) if ts else 0.0

    best = None
    x = rect[0] - 0.3
    while x <= rect[2] + 0.3:
        y = rect[1] - 0.3
        while y <= rect[3] + 0.3:
            if ok(x, y):
                edge = min(abs(x - rect[0]), abs(x - rect[2]), abs(y - rect[1]), abs(y - rect[3]))
                for deg in range(0, 360, YAW_STEP):
                    yaw = math.radians(deg)
                    miss = sum(max(0.0, abs(_angle(x, y, qx, qy, yaw)) - half) for qx, qy in subj)
                    seen = sum(abs(_angle(x, y, qx, qy, yaw)) <= half for qx, qy in room_items)
                    wins = sum(abs(_angle(x, y, qx, qy, yaw)) <= half for qx, qy in openings)
                    score = (-10.0 * miss + (seen / max(1, len(room_items))) + 0.4 * min(wins, 1)
                             + 0.6 * depth(x, y, yaw) / max(diag, 1e-6) - 0.15 * edge)
                    if best is None or score > best[0]:
                        best = (score, x, y, yaw, miss)
            y += STEP
        x += STEP
    if best is None:
        raise ValueError("no standing point in " + room)
    score, x, y, yaw, miss = best
    widest = max((abs(_angle(x, y, qx, qy, yaw)) for qx, qy in subj), default=0.0)
    return {"position": [round(x, 3), round(y, 3)], "target": [round(x + 3 * math.cos(yaw), 3),
                                                                round(y + 3 * math.sin(yaw), 3)],
            "yaw_deg": round(math.degrees(yaw), 1), "widest_deg": round(math.degrees(widest), 1),
            "subjects_in_frame": miss == 0.0, "score": round(score, 3), "level": lv}
