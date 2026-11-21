"""Model validation rules (plan row I05; Revit's built-in warnings, replaced).

`check(elements, lay, sp)` returns findings `dict(rule, severity, element, message)`; severity is "error" (the model is
wrong) or "note" (stated, accepted). Rules:
  join       every wall end meets another wall, an infill, or a kept column; a corner-only touch is a gap
  overlap    two walls of one level overlap by more than a join's worth of area
  closure    every edge of every room is bounded by walls, infills, columns, a room separation or an opening, and the
             rest of the edge is shared with a room it is linked to (open plan)
  host       each door/window has a host wall of its level, lies within the wall's length, fits its height, and no two
             openings on one wall overlap
  ids        unique ids; every host, type_id and room reference resolves
Findings are measured (lengths in mm), never adjectives.
"""
from __future__ import annotations

import math

from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union

from ..contracts import DesignElement
from .geometry_net import wall_slab

JOIN_TOL = 0.006             # m: a wall end within this of another slab counts as touching
OVERLAP_M2 = 0.05            # m2: wall-on-wall overlap beyond a T/L join (a join overlaps at most t x t = 0.04)
CLOSURE_GAP_M = 0.02         # m: uncovered room-edge length accepted as numeric noise


def _f(rule, element, message, severity="error"):
    return dict(rule=rule, severity=severity, element=element, message=message)


def _infills(sp):
    out = []
    for f in list(sp.get("infills", [])) + ([sp["infill"]] if sp.get("infill") else []):
        xs = [p[0] for p in f["profile"]]
        out.append(box(min(xs), f["y0"], max(xs), f["y1"]))
    return out


def _walls_by_level(sp):
    return {lv: [w for w in sp["walls"] if w["level"] == lv] for lv in ("B", "GF")}


def _face_contact(a, b, t, end) -> bool:
    """True when two wall slabs overlap, or share a face of at least half a wall thickness, at this wall end (a
    corner-only touch is not a join)."""
    i = a.intersection(b)
    if i.is_empty or i.distance(end) > t / 2 + JOIN_TOL:
        return False
    return i.area > 1e-6 or (i.geom_type != "Point" and i.length >= 0.5 * t - 1e-9)


def joins(sp, columns_mm) -> list[dict]:
    cols = unary_union([box(*(v / 1000 for v in c)) for c in columns_mm])
    inf = unary_union(_infills(sp) or [box(0, 0, 0, 0)])
    out = []
    for lv, ws in _walls_by_level(sp).items():
        slabs = [wall_slab(w) for w in ws]
        for i, w in enumerate(ws):
            for end in ("0", "1"):
                p = Point(w["x" + end], w["y" + end])
                joined = any(j != i and _face_contact(slabs[i], s, w["thickness"], p) for j, s in enumerate(slabs))
                if not joined:
                    joined = cols.buffer(JOIN_TOL).intersects(p) or inf.buffer(JOIN_TOL).intersects(p)
                if not joined:
                    corner = [j for j, s in enumerate(slabs) if j != i and s.distance(slabs[i]) < 1e-6]
                    out.append(_f("join", f"wall-{lv}#{sp['walls'].index(w)}",
                                  f"end ({p.x:.3f}, {p.y:.3f}) touches no wall face"
                                  + (" (corner-only contact with wall #%d: a notch of %.0f mm)" % (
                                      sp['walls'].index(ws[corner[0]]), ws[corner[0]]["thickness"] * 1000) if corner else " (free end)")))
    return out


def overlaps(sp) -> list[dict]:
    out = []
    for lv, ws in _walls_by_level(sp).items():
        for i, a in enumerate(ws):
            for b in ws[i + 1:]:
                area = wall_slab(a).intersection(wall_slab(b)).area
                if area > OVERLAP_M2:
                    out.append(_f("overlap", f"wall-{lv}", f"walls #{sp['walls'].index(a)} and #{sp['walls'].index(b)} overlap by {area:.3f} m2"))
    return out


def closure(lay, sp, columns_mm) -> list[dict]:
    cols = [box(*(v / 1000 for v in c)).buffer(JOIN_TOL) for c in columns_mm]
    inf = [i.buffer(JOIN_TOL) for i in _infills(sp)]
    seps = {lv: [LineString([(s["x0"], s["y0"]), (s["x1"], s["y1"])]).buffer(0.01) for s in sp["separations"] if s["level"] == lv] for lv in ("B", "GF")}
    openings = {lv: [] for lv in ("B", "GF")}
    for d in sp["doors"] + sp["windows"]:
        w = d["width"]
        span = d.get("span")
        horiz = span[0] == "h" if span else True
        a, b = ((d["x"] - w / 2, d["y"]), (d["x"] + w / 2, d["y"])) if horiz else ((d["x"], d["y"] - w / 2), (d["x"], d["y"] + w / 2))
        openings[d["level"]].append(LineString([a, b]).buffer(0.01))
    linked = {frozenset(l) for l in lay["links"]}
    out = []
    for rid, r in lay["rooms"].items():
        lv = r["level"]
        x0, y0, x1, y1 = r["rect"]
        cover = unary_union([wall_slab(w).buffer(JOIN_TOL) for w in sp["walls"] if w["level"] == lv] + cols + inf + seps[lv] + openings[lv])
        for name, ln in (("south", LineString([(x0, y0), (x1, y0)])), ("east", LineString([(x1, y0), (x1, y1)])),
                         ("north", LineString([(x1, y1), (x0, y1)])), ("west", LineString([(x0, y1), (x0, y0)]))):
            gap = ln.difference(cover)
            if gap.length <= CLOSURE_GAP_M:
                continue
            # the open part must be shared with a linked room (open plan) or lie on the villa's own plot edge handled by a door
            parts = [gap] if gap.geom_type == "LineString" else list(gap.geoms)
            for g in parts:
                if g.length <= CLOSURE_GAP_M:
                    continue
                mid = g.interpolate(0.5, normalized=True)
                other = next((oid for oid, o in lay["rooms"].items() if oid != rid and o["level"] == lv
                              and box(*o["rect"]).buffer(0.005).intersects(mid)), None)
                if other and frozenset((rid, other)) in linked:
                    continue
                out.append(_f("closure", f"room-{rid}", "%s edge is open for %.0f mm at (%.3f, %.3f)-(%.3f, %.3f): no wall, separation, "
                              "opening or linked room there" % (name, g.length * 1000, *g.coords[0], *g.coords[-1])))
    return out


def hosts(els: list[DesignElement]) -> list[dict]:
    byid = {e.id: e for e in els}
    out = []
    per_wall: dict[str, list] = {}
    for e in els:
        if e.kind not in ("door", "window"):
            continue
        if not e.host or e.host not in byid:
            out.append(_f("host", e.id, "no host wall within 150 mm"))
            continue
        w = byid[e.host]
        if w.level != e.level:
            out.append(_f("host", e.id, f"host {w.id} is on level {w.level}, opening on {e.level}"))
        wp = w.params
        ax, ay, bx, by = wp["x0_mm"], wp["y0_mm"], wp["x1_mm"], wp["y1_mm"]
        L = math.hypot(bx - ax, by - ay)
        t = ((e.placement[0] - ax) * (bx - ax) + (e.placement[1] - ay) * (by - ay)) / (L * L) * L
        half = e.params["width_mm"] / 2
        # sliding openings in an end wall may run to the wall end; others must sit inside it
        if t - half < -1.0 or t + half > L + 1.0:
            out.append(_f("host", e.id, "opening spans %.0f..%.0f mm along %s (length %.0f mm): outside its host wall" % (t - half, t + half, w.id, L)))
        sill = e.placement[2] if e.kind == "window" else 0.0
        if sill + e.params["height_mm"] > wp["height_mm"] + 1.0:
            out.append(_f("host", e.id, "head at %.0f mm is above the host wall top %.0f mm (%s)" % (sill + e.params["height_mm"], wp["height_mm"], w.id)))
        per_wall.setdefault(w.id, []).append((t - half, t + half, e.id, sill, sill + e.params["height_mm"]))
    for wid, ops in per_wall.items():
        for i, a in enumerate(ops):
            for b in ops[i + 1:]:
                if min(a[1], b[1]) - max(a[0], b[0]) > 1.0 and min(a[4], b[4]) - max(a[3], b[3]) > 1.0:
                    out.append(_f("host", a[2], f"overlaps {b[2]} on {wid}"))
    return out


def ids(els: list[DesignElement]) -> list[dict]:
    from .schema import TYPED
    seen, out = {}, []
    for e in els:
        seen[e.id] = seen.get(e.id, 0) + 1
    out += [_f("ids", i, f"duplicate id x{n}") for i, n in seen.items() if n > 1]
    types = {e.id for e in els if e.kind == "type"}
    rooms = {e.room for e in els if e.kind == "room"}
    for e in els:
        if e.kind in TYPED and "type_id" in e.params and e.params["type_id"] not in types:
            out.append(_f("ids", e.id, f"type {e.params['type_id']} is not an element"))
        if e.host and e.host not in seen:
            out.append(_f("ids", e.id, f"host {e.host} is not an element"))
        if e.kind in ("floor", "ceiling") and e.room not in rooms:
            out.append(_f("ids", e.id, f"room {e.room} is not a room element"))
    return out


def check(els: list[DesignElement], lay, sp, columns_mm) -> list[dict]:
    return joins(sp, columns_mm) + overlaps(sp) + closure(lay, sp, columns_mm) + hosts(els) + ids(els)
