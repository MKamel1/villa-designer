"""Hit test: a model point on a level -> element ids, with distance, ambiguity and misses reported (never guessed).

Candidates are limited to what the sheet draws (its RV2 layers). Tiers, most specific first: object (door, window,
furniture, luminaire, ...), then wall, then room. The first tier with a candidate within tolerance decides. Exactly one
footprint containing the point wins; otherwise two or more within tolerance are AMBIGUOUS and listed.
"""
from __future__ import annotations

import math

from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box
from shapely.affinity import rotate
from shapely.ops import unary_union

from archpipe.drawings2d import orient
from archpipe.documents import plans

TOL_PAPER_MM = 3.0       # house policy: a pick within 3 mm of paper of a footprint counts (150 mm model at 1:50)
OBJECT = {"door", "window", "furniture", "luminaire", "fixture", "column", "stair", "railing"}
TIERS = (("object", OBJECT), ("wall", {"wall"}), ("room", {"room"}))
LAYER_KINDS = {"furniture": {"furniture"}, "luminaires": {"luminaire", "fixture"}}
BASE_KINDS = {"wall", "door", "window", "column", "stair", "railing", "room"}


def footprint(e):
    """Plan footprint in model mm (shapely), or None when the kind has none."""
    p, k = e.params, e.kind
    if k == "wall":
        return Polygon(plans._wall_poly(p))
    if k == "room":
        return Polygon(p["polygon_mm"])
    if k == "column":
        return box(p["x0_mm"], p["y0_mm"], p["x1_mm"], p["y1_mm"])
    if k == "stair":
        return unary_union([box(b[0], b[1], b[3], b[4]) for b in p["tread_boxes_mm"]])
    if k == "railing":
        if "path_mm" in p:
            pts = [(q[0], q[1]) for q in p["path_mm"]]
        elif all(len(q) == 2 for q in p["profile_mm"]):         # 2-value profiles (site edge rails) are relative to the placement
            pts = [(q[0] + e.placement[0], q[1] + e.placement[1]) for q in p["profile_mm"]]
        else:
            pts = [(q[0], q[1]) for q in p["profile_mm"]]
        return LineString(pts).buffer(50)
    if k in orient.LOCAL_FRAME_KINDS:     # size is (along, across) in the element's own frame, rotated about the placement
        r = box(e.placement[0] - e.size[0] / 2, e.placement[1] - e.size[1] / 2, e.placement[0] + e.size[0] / 2, e.placement[1] + e.size[1] / 2)
        return rotate(r, e.rotation_deg, origin=(e.placement[0], e.placement[1]))
    return None


def kinds_for(layers) -> set[str]:
    out = set(BASE_KINDS)
    for l in layers:
        out |= LAYER_KINDS.get(l, set())
    return out


def hit(els, level: str, x: float, y: float, scale: float, layers, tol_mm: float | None = None) -> dict:
    """Return {"status": linked|ambiguous|miss, "links": [...], "alternatives": [...], "reason": str}. Distances in model mm."""
    tol = tol_mm if tol_mm is not None else TOL_PAPER_MM * scale
    pt = Point(x, y)
    kinds = kinds_for(layers)
    cands = []
    for e in els:
        if e.level != level or e.kind not in kinds:
            continue
        fp = footprint(e)
        if fp is None:
            continue
        d = fp.distance(pt)
        if d <= tol:
            cands.append((e, d))
    base = {"tolerance_mm": round(tol, 1), "links": [], "alternatives": []}
    for tier, ks in TIERS:
        c = sorted(((e, d) for e, d in cands if e.kind in ks), key=lambda t: (t[1], t[0].id))
        if not c:
            continue
        inside = [t for t in c if t[1] == 0]
        row = lambda t: {"element_id": t[0].id, "kind": t[0].kind, "distance_mm": round(t[1], 1), "tier": tier}
        if len(inside) == 1 or (len(c) == 1):
            pick = inside[0] if len(inside) == 1 else c[0]
            context = [row(t) | {"tier": "context"} for t in cands if t[0].kind == "room" and tier != "room" and t[1] == 0]
            return base | {"status": "linked", "links": [row(pick)] + context,
                           "alternatives": [row(t) for t in c if t is not pick], "reason": "%s within tolerance" % tier}
        return base | {"status": "ambiguous", "alternatives": [row(t) for t in c],
                       "reason": "%d %s candidates within %.0f mm of the pick; none alone contains it" % (len(c), tier, tol)}
    return base | {"status": "miss", "reason": "no drawn element within %.0f mm of the pick (empty space)" % tol}


def bbox_model(e):
    """Model-mm bounds (x0, y0, x1, y1) of an element's plan footprint, or None."""
    fp = footprint(e)
    return fp.bounds if fp is not None else None


def hit_area(els, level: str, ring: list[tuple[float, float]], scale: float, layers) -> dict | None:
    """Area mark (rectangle, cloud, ink): object-tier elements whose centre is inside the ring. None when it encloses none
    (the caller then falls back to the point test at the mark's centre). One -> linked, several -> ambiguous."""
    poly = Polygon(ring)
    if not poly.is_valid or poly.area == 0:
        return None
    kinds = kinds_for(layers) & OBJECT
    c = []
    for e in els:
        fp = footprint(e) if e.level == level and e.kind in kinds else None
        if fp is not None and poly.contains(fp.representative_point()):
            c.append({"element_id": e.id, "kind": e.kind, "distance_mm": 0.0, "tier": "object"})
    if not c:
        return None
    base = {"tolerance_mm": 0.0, "links": [], "alternatives": []}
    if len(c) == 1:
        return base | {"status": "linked", "links": c, "reason": "the only object enclosed by the mark"}
    return base | {"status": "ambiguous", "alternatives": sorted(c, key=lambda r: r["element_id"]),
                   "reason": "%d objects enclosed by the mark" % len(c)}
