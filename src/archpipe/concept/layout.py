"""A concept layout as rectangles, and its conversion to the L0 spec format.

A layout is plain data so it can be written, diffed and critiqued:

    {"id", "parti", "plot": {"width_m", "depth_m"},        # +y is north
     "levels": {"L00": 0.0, "L01": 3.3},                    # elevation, m
     "rooms": {id: {"level", "rect": [x0, y0, x1, y1], "occupancy", "name", "target_m2"}},
     "links": [[a, b], ...],        # doors the concept intends
     "vertical": [[a, b], ...],     # stair rooms joined across levels
     "entrance": id}

Walls are generated on the rectangle edges (centrelines), split at every
junction so no opening can land where another wall arrives. Windows are
placed on exterior segments of habitable and sanitary rooms; doors on the
longest shared segment of each intended link.
"""
from __future__ import annotations

import math
from pathlib import Path

import yaml

from .. import vocabulary as vocab

EXT, INT = 0.30, 0.10          # wall thickness, m (the demo spec's EXT300 / INT100 types)
DOOR, ENTRANCE_DOOR = 0.9, 1.0
WIN_H, WIN_SILL = 1.5, 0.8
LEVEL_HEIGHT = 3.0
EPS = 1e-6


def _inside(rect, x, y):
    x0, y0, x1, y1 = rect
    return x0 - EPS < x < x1 + EPS and y0 - EPS < y < y1 + EPS


def room_at(layout, level, x, y):
    for rid, r in layout["rooms"].items():
        if r["level"] == level and _inside(r["rect"], x, y):
            return rid
    return None


def segments(layout, level):
    """Atomic wall segments on one level: (start, end, room on the left, room on the right).

    Left/right are relative to start->end; None means outside the building."""
    rects = [r["rect"] for r in layout["rooms"].values() if r["level"] == level]
    lines = {}
    for x0, y0, x1, y1 in rects:
        for key, a, b in ((("h", y0), x0, x1), (("h", y1), x0, x1), (("v", x0), y0, y1), (("v", x1), y0, y1)):
            lines.setdefault((key[0], round(key[1], 6)), []).append((a, b))
    out = []
    for (axis, c), spans in sorted(lines.items()):
        cuts = sorted({round(v, 6) for s in spans for v in s})
        for a, b in zip(cuts, cuts[1:]):
            m = (a + b) / 2
            if not any(s0 - EPS <= a and b <= s1 + EPS for s0, s1 in spans):
                continue
            if axis == "h":
                start, end = (a, c), (b, c)
                left, right = room_at(layout, level, m, c + 0.01), room_at(layout, level, m, c - 0.01)
            else:
                start, end = (c, a), (c, b)
                left, right = room_at(layout, level, c - 0.01, m), room_at(layout, level, c + 0.01, m)
            if left is None and right is None:
                continue
            out.append((start, end, left, right))
    return out


def _len(seg):
    return math.dist(seg[0], seg[1])


def _facing(seg, room):
    """Compass direction a room's exterior segment faces (+y is north)."""
    (x0, y0), (x1, y1), left, _ = seg
    if y0 == y1:
        outward_up = left is None          # outside is on the left (above) of a left-to-right edge
        return "north" if outward_up == (x1 > x0) else "south"
    outward_left = left is None
    return "west" if outward_left == (y1 > y0) else "east"


def openings(layout, level):
    """Doors for intended links and windows for exterior walls, with the segment each sits on."""
    segs = segments(layout, level)
    doors, windows, unbuilt = [], [], []
    for a, b in layout["links"]:
        ra, rb = layout["rooms"].get(a), layout["rooms"].get(b)
        if not ra or not rb or ra["level"] != level or rb["level"] != level:
            continue
        shared = [s for s in segs if {s[2], s[3]} == {a, b}]
        best = max(shared, key=_len, default=None)
        if best is None or _len(best) < DOOR + 2 * (EXT / 2) + 0.05:
            unbuilt.append((a, b))
            continue
        doors.append({"segment": best, "width": DOOR, "rooms": (a, b)})
    ent = layout.get("entrance")
    if ent and layout["rooms"][ent]["level"] == level:
        ext = [s for s in segs if ent in (s[2], s[3]) and None in (s[2], s[3])]
        best = max(ext, key=_len, default=None)
        if best is not None and _len(best) >= ENTRANCE_DOOR + EXT + 0.05:
            doors.append({"segment": best, "width": ENTRANCE_DOOR, "rooms": (ent, None)})
        else:
            unbuilt.append((ent, "outside"))
    door_segs = {id(d["segment"]) for d in doors}
    for s in segs:
        room = s[2] or s[3]
        if None not in (s[2], s[3]) or id(s) in door_segs:
            continue
        occ = layout["rooms"][room]["occupancy"]
        if occ not in vocab.HABITABLE and occ not in vocab.SANITARY:
            continue
        clear = _len(s) - EXT - 0.4                        # reveals at both ends
        if clear < 0.6:
            continue
        area = _rect_area(layout["rooms"][room]["rect"])
        want = max(0.6, min(clear, 2.4, area / 8 / WIN_H + 0.3)) if occ in vocab.HABITABLE else min(clear, 0.8)
        windows.append({"segment": s, "width": round(want, 2), "room": room, "facing": _facing(s, room)})
    return doors, windows, unbuilt


def _rect_area(rect):
    return (rect[2] - rect[0]) * (rect[3] - rect[1])


def room_area(layout, rid):
    return _rect_area(layout["rooms"][rid]["rect"])


def to_spec(layout) -> dict:
    """The layout in the L0 spec format (millimetres), ready for model.load and rules.review."""
    mm = lambda v: int(round(v * 1000))
    levels = sorted(layout["levels"].items(), key=lambda kv: kv[1])
    spec = {"project": {"name": f"Concept {layout['id']} (generated, diagnostic)", "units": "mm", "standard": "iso13567"},
            "levels": [{"id": lid, "name": lid, "elevation": mm(e), "height": mm(LEVEL_HEIGHT)} for lid, e in levels],
            "wall_types": [
                {"id": "EXT300", "description": "External wall (concept placeholder)", "thickness": 300, "bearing": True,
                 "layers": [{"material": "blockwork", "thickness": 300}]},
                {"id": "INT100", "description": "Partition (concept placeholder)", "thickness": 100, "bearing": False,
                 "layers": [{"material": "gypsum_stud", "thickness": 100}]}],
            "walls": [], "openings": [], "rooms": []}
    for lid, _ in levels:
        segs = segments(layout, lid)
        ids = {}
        for i, s in enumerate(segs):
            wid = f"{lid}-W{i:03d}"
            ids[id(s)] = (wid, s)
            spec["walls"].append({"id": wid, "level": lid, "type": "EXT300" if None in (s[2], s[3]) else "INT100",
                                  "start": [mm(s[0][0]), mm(s[0][1])], "end": [mm(s[1][0]), mm(s[1][1])]})
        doors, windows, _ = openings(layout, lid)
        # openings() recomputes segments; match by geometry
        by_geom = {(s[0], s[1]): ids[id(s)][0] for s in segs}
        for j, d in enumerate(doors):
            s = d["segment"]
            spec["openings"].append({"id": f"{lid}-D{j:02d}", "host": by_geom[(s[0], s[1])], "kind": "door",
                                     "width": mm(d["width"]), "height": 2100, "at": mm(_len(s) / 2)})
        for j, w in enumerate(windows):
            s = w["segment"]
            spec["openings"].append({"id": f"{lid}-G{j:02d}", "host": by_geom[(s[0], s[1])], "kind": "window",
                                     "width": mm(w["width"]), "height": mm(WIN_H), "at": mm(_len(s) / 2),
                                     "sill": mm(WIN_SILL)})
        for rid, r in layout["rooms"].items():
            if r["level"] != lid:
                continue
            x0, y0, x1, y1 = r["rect"]
            ext = {side: any(None in (s[2], s[3]) and rid in (s[2], s[3]) and _on_side(s, r["rect"], side) for s in segs)
                   for side in "WSEN"}
            inset = {k: (EXT if v else INT) / 2 for k, v in ext.items()}
            b = [[x0 + inset["W"], y0 + inset["S"]], [x1 - inset["E"], y0 + inset["S"]],
                 [x1 - inset["E"], y1 - inset["N"]], [x0 + inset["W"], y1 - inset["N"]]]
            spec["rooms"].append({"id": rid, "level": lid, "name": r.get("name", rid), "occupancy": r["occupancy"],
                                  "boundary": [[mm(x), mm(y)] for x, y in b]})
    return spec


def _on_side(seg, rect, side):
    (sx0, sy0), (sx1, sy1) = seg[0], seg[1]
    x0, y0, x1, y1 = rect
    return {"W": sx0 == sx1 == x0, "E": sx0 == sx1 == x1, "S": sy0 == sy1 == y0, "N": sy0 == sy1 == y1}[side]


def write_spec(layout, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    head = ("# GENERATED by archpipe.concept (generator v1). Diagnostic concept, not a design.\n"
            "# Units mm; origin at the plot's south-west corner; +y is north.\n")
    path.write_text(head + yaml.safe_dump(to_spec(layout), sort_keys=False, default_flow_style=None), encoding="utf-8")
    return path
