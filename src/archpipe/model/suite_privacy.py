"""Parents' suite privacy on the BUILT design model (client 2026-11-26, docs/decisions/privacy-2026-11-26.md).

Criterion: with EVERY door of the suite open, no point outside the suite has a line of sight to the dressing room, the
en-suite (floor and doorway) or the route between them. A closed door is never the only protection.

2D plan test, eye height ignored, furniture ignored (worst case); walls from the model's GF wall elements, every door
cut to its opening. Door leaves are NOT sight-blocking in the pass/fail count (a leaf can be at any angle); `leaves=`
adds the 90-degree open leaves of named doors, used only to compare door handings (docs/lanes/DF-built.md).

    r = seeing(load("D1"))          # {"viewpoints": n, "seeing": [(x, y, label), ...], ...}
    assert not r["seeing"]
"""
from __future__ import annotations

import math

from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union
from shapely.prepared import prep

M = 1000.0
SUITE_DOORS = ("door-GF-corridor-suite-vestibule", "door-GF-suite-vestibule-parents-entry",
               "door-GF-parents-bed-parents-dressing", "door-GF-parents-dressing-ext-parents-ensuite")


def _els(els, kind, level="GF"):
    return [e for e in els if e.kind == kind and e.level == level]


def _wall_box(e):
    x, y = e.placement[0] / M, e.placement[1] / M
    L, t = e.size[0] / M, e.size[1] / M
    if abs(e.rotation_deg % 180) < 1e-6:
        return box(x - L / 2, y - t / 2, x + L / 2, y + t / 2)
    return box(x - t / 2, y - L / 2, x + t / 2, y + L / 2)


def door_opening(e):
    """The hole a door leaves in its wall (m): structural opening for a hinged door, the leaf width for a pocket door."""
    p = e.params
    w = (p.get("width_mm") if p.get("operation") == "pocket" else p.get("structural_opening_mm")) or e.size[0]
    x, y, t = e.placement[0] / M, e.placement[1] / M, e.size[1] / M + 0.002
    horizontal = (p.get("span") or ["h"])[0] == "h"
    return box(x - w / M / 2, y - t / 2, x + w / M / 2, y + t / 2) if horizontal else \
        box(x - t / 2, y - w / M / 2, x + t / 2, y + w / M / 2)


def leaf_open_90(e, els, thickness=0.04):
    """The leaf of a hinged door swung to 90 degrees into its `swing_into` room: from the hinge, `width` along the wall normal."""
    p = e.params
    room = next(r for r in els if r.id == "room-" + p["swing_into"])
    (hx, hy), w = (v / M for v in p["hinge_xy_mm"]), p["width_mm"] / M
    if (p.get("span") or ["h"])[0] == "h":
        nx, ny = 0.0, math.copysign(1.0, room.placement[1] / M - e.placement[1] / M)
    else:
        nx, ny = math.copysign(1.0, room.placement[0] / M - e.placement[0] / M), 0.0
    ex, ey = hx + nx * w, hy + ny * w
    return LineString([(hx, hy), (ex, ey)]).buffer(thickness / 2, cap_style="flat")


def solid(els, leaves=()):
    """Sight-blocking solid of the GF with every door open (plus the named doors' 90-degree leaves)."""
    walls = unary_union([_wall_box(e) for e in _els(els, "wall")])
    holes = unary_union([door_opening(e) for e in _els(els, "door")])
    extra = [leaf_open_90(e, els) for e in _els(els, "door") if e.id in leaves]
    return unary_union([walls.difference(holes), *extra])


def _clear(els, rid):
    r = next(e for e in els if e.id == "room-" + rid)
    (x0, y0), _, (x1, y1), _ = r.params["clear_rect_mm"]
    return x0 / M, y0 / M, x1 / M, y1 / M


def _grid(rect, step):
    x0, y0, x1, y1 = rect
    out, x = [], x0 + step / 2
    while x < x1:
        y = y0 + step / 2
        while y < y1:
            out.append((round(x, 3), round(y, 3)))
            y += step
        x += step
    return out


def targets(els, step=0.2):
    """Points that must stay unseen: dressing floor, its extension, en-suite floor, the en-suite doorway and the zone outside it."""
    pts = []
    for rid in ("parents-dressing", "parents-dressing-ext", "parents-ensuite"):
        pts += _grid(_clear(els, rid), step)
    ed = next(e for e in els if e.id == "door-GF-parents-dressing-ext-parents-ensuite")
    ex, ey, w = ed.placement[0] / M, ed.placement[1] / M, ed.size[0] / M
    pts += _grid((ex - w / 2, ey - 0.45, ex + w / 2, ey + 0.05), 0.1)          # doorway threshold and 0.45 m on the dressing side
    return pts


def viewpoints(els):
    """Where a person who is NOT in the suite can stand: the corridor (public side of the suite door), the stair landing and
    void, the gallery, the kids' rooms (through their doors) and the kids' and family-bath doorways."""
    out = []
    cx0, cy0, cx1, cy1 = _clear(els, "corridor")
    x = cx0 + 0.01
    while x <= cx1:                                  # every 0.25 m along the corridor, every 0.1 m across it
        out += [(round(x, 3), round(y, 3), "corridor") for y in _grid((cx0, cy0, cx1, cy1), 0.1) and
                [cy0 + 0.05 + 0.1 * k for k in range(int((cy1 - cy0) / 0.1))]]
        x += 0.25
    for rid, label in (("landing-gf", "stair landing"), ("stair-gf", "stair void"), ("gallery-end", "gallery"),
                       ("kids-a", "kids-a room"), ("kids-b", "kids-b room")):
        step = 0.5 if label.startswith("kids") else 0.4
        out += [(x, y, label) for x, y in _grid(_clear(els, rid), step)]
    for e in _els(els, "door"):
        rooms = e.params.get("rooms") or []
        for key, label in (("kids-a", "kids-a doorway"), ("kids-b", "kids-b doorway"), ("family-bath", "family-bath doorway"),
                           ("gallery-end", "family-bath doorway")):
            if key in rooms and "parents" not in "".join(rooms) and "suite" not in "".join(rooms):
                x, y = e.placement[0] / M, e.placement[1] / M
                out += [(x, y, label), (x, y + 0.1, label), (x, y - 0.1, label)]
    return out


def sees(blocker, a, b):
    """True if the segment a-b crosses no wall (touching a corner is allowed)."""
    return blocker.intersection(LineString([a, b])).length < 1e-6


def seeing(els, leaves=(), step=0.2):
    """Run the criterion. Returns viewpoints (count), the viewpoints that see a protected point and one example target each."""
    blocker = solid(els, leaves)
    pb = prep(blocker)
    T = targets(els, step)
    V = viewpoints(els)
    hits = []
    for v in V:
        for t in T:
            if not pb.intersects(LineString([v[:2], t])) or sees(blocker, v[:2], t):
                hits.append((v[0], v[1], v[2], t))
                break
    return dict(viewpoints=len(V), targets=len(T), seeing=hits)
