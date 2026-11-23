"""Builders: one function per kind of layout element. Each returns Obj(s) with an `ld-*` id and the layout footprint it must match."""
from __future__ import annotations

import math

import numpy as np
from shapely.geometry import MultiPolygon, Polygon, box as sbox
from shapely.ops import unary_union

from . import policy as P
from .geom import Obj, Part, box, cyl, extrude_profile, half_frustum, prism, rbox, shifted, slanted_slat


def R(r):
    x0, y0, x1, y1 = r
    return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def poly_rects(geom):
    """Decompose an axis-aligned polygon (holes allowed) into rectangles by grid cells merged along x."""
    geoms = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]
    out = []
    for g in geoms:
        if g.is_empty:
            continue
        xs = sorted({round(c[0], 6) for ring in [g.exterior, *g.interiors] for c in ring.coords})
        ys = sorted({round(c[1], 6) for ring in [g.exterior, *g.interiors] for c in ring.coords})
        for j in range(len(ys) - 1):
            run = None
            for i in range(len(xs) - 1):
                inside = g.contains(sbox(xs[i], ys[j], xs[i + 1], ys[j + 1]).centroid)
                if inside and run is None:
                    run = xs[i]
                if run is not None and (not inside):
                    out.append((run, ys[j], xs[i], ys[j + 1])); run = None
            if run is not None:
                out.append((run, ys[j], xs[-1], ys[j + 1]))
    return out


def surface(oid, kind, label, material, geom, z0, z1, **kw):
    """A flat patch for any axis-aligned polygon (several rectangles, one object)."""
    parts = [rbox(material, *r, z0, z1) for r in poly_rects(geom)]
    return Obj(oid, kind, label, parts, footprint_poly=geom, footprint_mode="poly", **kw)


def paving(oid, layout_id, rect, g, paths, pit, holes=()):
    """Bedding slab (joint colour) + running-bond units; units are cut around path rects (built as the path) and the pit cover opening."""
    pv = P.PAVER
    x0, y0, x1, y1 = rect
    r = sbox(*rect)
    slab_geom = r.difference(unary_union([sbox(*q) for q in holes])) if holes else r
    if pit:
        h = P.PIT["hole"] / 2
        slab_geom = slab_geom.difference(sbox(pit[0] - h, pit[1] - h, pit[0] + h, pit[1] + h))
    top = g - pv["thick"]
    parts = [rbox("paving-joint", *q, top - pv["bedding"], top) for q in poly_rects(slab_geom)]
    cut = [sbox(*p) for p in paths] + [sbox(*q) for q in holes]
    if pit:
        rr = pit[2] / 2 + P.PIT["gap"]
        cut.append(Polygon([(pit[0] + rr * math.cos(2 * math.pi * i / 24), pit[1] + rr * math.sin(2 * math.pi * i / 24)) for i in range(24)]))
    parts += units(rect, cut, g, pv["len"], pv["wid"], "x", "paving-unit")
    return Obj(oid, "paving", "unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material %s)" % "unit-paving",
               parts, layout_id=layout_id, footprint=rect, meta=dict(units=len(parts) - len(poly_rects(slab_geom))))


def units(rect, cuts, g, ulen, uwid, along, material, clip=None):
    """Running-bond unit patches inside rect minus cuts; returns Parts (4 mm inset each side = 8 mm joint)."""
    pv = P.PAVER
    x0, y0, x1, y1 = rect
    r = sbox(*rect)
    cut = unary_union(cuts) if cuts else None
    parts = []
    swap = along == "y"
    a0, a1, b0, b1 = (y0, y1, x0, x1) if swap else (x0, x1, y0, y1)
    row = 0
    b = b0
    while b < b1 - 1e-9:
        off = (ulen / 2) if row % 2 else 0.0
        a = a0 - off
        while a < a1 - 1e-9:
            u = sbox(b, a, b + uwid, a + ulen) if swap else sbox(a, b, a + ulen, b + uwid)
            u = u.intersection(r)
            if clip is not None:
                u = u.intersection(clip)
            if cut is not None:
                u = u.difference(cut)
            for g_ in (u.geoms if hasattr(u, "geoms") else [u]):
                if g_.is_empty or g_.area < 2e-4 or g_.geom_type != "Polygon":
                    continue
                g2 = g_.buffer(-pv["joint"] / 2, join_style=2)
                for q in (g2.geoms if hasattr(g2, "geoms") else [g2]):
                    if not q.is_empty and q.area > 1e-4 and q.geom_type == "Polygon" and not list(q.interiors):
                        parts.append(prism(material, list(q.exterior.coords)[:-1], g - pv["thick"], g))
            a += ulen
        b += uwid
        row += 1
    return parts


def path(oid, layout_id, rect, g, cls):
    """A route: units laid along its long axis (visibly different from the surrounding paving), resting on the paving bedding."""
    x0, y0, x1, y1 = rect
    along = "x" if (x1 - x0) >= (y1 - y0) else "y"
    parts = units(rect, [], g, P.PAVER["len"], P.PAVER["wid"], along, "path-unit")
    return Obj(oid, "path", "%s path, units laid along the route (ASSUMED pattern; width/class from the layout)" % cls, parts, layout_id=layout_id,
               footprint=rect, footprint_mode="within", meta=dict(klass=cls))


def bed(oid, layout_id, rect, g, role):
    return Obj(oid, "bed", "planting bed (%s), mulched soil flush with the ground" % role, [rbox("bed-soil", *rect, g - P.BED_DEPTH, g)],
               layout_id=layout_id, footprint=rect)


def wall(oid, layout_id, rect, h, g):
    return Obj(oid, "wall", "wall / fence %.1f m: %s" % (h, P.WALL_NOTE), [rbox("wall-render", *rect, g, g + h)], layout_id=layout_id, footprint=rect,
               meta=dict(height_m=h))


def trellis(oid, layout_id, rect, h, g):
    """2.1 m screen: posts, top and bottom rails, a batten lattice. Long axis x (y-long screens are rare: not built, raises)."""
    x0, y0, x1, y1 = rect
    if (x1 - x0) < (y1 - y0):
        raise NotImplementedError("screen %s is longer in y; only x-long trellis screens are built" % layout_id)
    L, t = x1 - x0, y1 - y0
    cy = (y0 + y1) / 2
    sp = P.SCREEN_POST
    n = max(2, math.ceil(L / 1.5) + 1)
    parts = []
    for i in range(n):
        px = x0 + (L - sp[0]) * i / (n - 1)
        parts.append(box("trellis-timber", px, y0, g, px + sp[0], y1, g + h))
    inner0, inner1 = x0 + sp[0], x1 - sp[0]
    parts.append(box("trellis-timber", inner0, cy - 0.025, g + h - 0.06, inner1, cy + 0.025, g + h))      # top rail
    parts.append(box("trellis-timber", inner0, cy - 0.025, g + 0.10, inner1, cy + 0.025, g + 0.16))      # bottom rail
    b = P.SCREEN_BATTEN
    z = g + 0.16
    while z + b < g + h - 0.06 - 1e-6:
        parts.append(box("trellis-timber", inner0, cy - b, z, inner1, cy, z + b)); z += P.SCREEN_PITCH
    k = max(1, int((inner1 - inner0) / P.SCREEN_PITCH))
    for i in range(k + 1):
        vx = inner0 + (inner1 - inner0 - b) * i / k
        parts.append(box("trellis-timber", vx, cy, g + 0.16, vx + b, cy + b, g + h - 0.06))
    return Obj(oid, "screen", "trellis screen %.1f m: timber posts at <=1.5 m, rails and %d mm batten lattice (ASSUMED detail) for climbers" % (h, int(P.SCREEN_PITCH * 1000)),
               parts, layout_id=layout_id, footprint=rect, meta=dict(height_m=h))


def pergola(oid, layout_id, rect, h, g, avoid):
    """Aluminium pergola: corner posts (+ intermediate posts where the plan is free), two beams, louvre blades across them."""
    x0, y0, x1, y1 = rect
    lx, ly = x1 - x0, y1 - y0
    long_x = lx >= ly
    pp, (bw, bd) = P.POST, P.BEAM
    parts = []
    posts = []
    if long_x:
        for ey in ((y0, y0 + pp), (y1 - pp, y1)):
            xs = [x0, x1 - pp]
            n = max(0, math.ceil(lx / 3.0) - 1)
            xs += [x0 + (lx - pp) * k / (n + 1) for k in range(1, n + 1)]
            for px in xs:
                q = (px, ey[0], px + pp, ey[1])
                if (px in (x0, x1 - pp)) or not any(_hit(q, a) for a in avoid):
                    posts.append(q)
    else:
        for ex in ((x0, x0 + pp), (x1 - pp, x1)):
            ys = [y0, y1 - pp]
            n = max(0, math.ceil(ly / 3.0) - 1)
            ys += [y0 + (ly - pp) * k / (n + 1) for k in range(1, n + 1)]
            for py in ys:
                q = (ex[0], py, ex[1], py + pp)
                if (py in (y0, y1 - pp)) or not any(_hit(q, a) for a in avoid):
                    posts.append(q)
    top = g + h
    for q in posts:
        parts.append(rbox("pergola-alu", *q, g, top - bd))
    if long_x:
        beams = [(x0, y0, x1, y0 + bw), (x0, y1 - bw, x1, y1)]
        lo, hi, spans = x0, x1, (y0 + bw, y1 - bw)
    else:
        beams = [(x0, y0, x0 + bw, y1), (x1 - bw, y0, x1, y1)]
        lo, hi, spans = y0, y1, (x0 + bw, x1 - bw)
    for b in beams:
        parts.append(rbox("pergola-alu", *b, top - bd, top))
    lv = P.LOUVRE
    pos = lo + lv["pitch"] / 2 + 0.0
    nbl = 0
    while pos + lv["width"] / 2 <= hi:
        zc = top - bd / 2
        parts.append(_blade(spans[0], spans[1], pos, zc, lv, long_x))
        pos += lv["pitch"]; nbl += 1
    return Obj(oid, "pergola", "louvred aluminium pergola %.1f m high: %d posts, 2 beams, %d louvre blades at %d mm (ASSUMED sections; supplier to size beams)"
               % (h, len(posts), nbl, int(lv["pitch"] * 1000)), parts, layout_id=layout_id, footprint=rect,
               meta=dict(posts=len(posts), blades=nbl, height_m=h, beam_span_m=max(lx, ly)))


def _hit(a, b, m=0.05):
    return a[0] < b[2] + m and a[2] > b[0] - m and a[1] < b[3] + m and a[3] > b[1] - m


def _blade(s0, s1, pos, zc, lv, long_x):
    """Blade between the beams: beams run along x when the pergola is long in x, so blades run along y, and vice versa."""
    return slanted_slat("pergola-alu", s0, s1, pos, zc, lv["width"], lv["thick"], lv["tilt"], axis="y" if long_x else "x")


def bench(oid, layout_id, rect, g, seats, h):
    """Built-in seat wall: a rendered plinth under a hardwood slat seat (slats along the long side, gaps between them), so it reads as a bench, not a plank on a box."""
    x0, y0, x1, y1 = rect
    pl = h - P.SEAT_TOP
    S = P.SEAT_SLAT
    along_x = (x1 - x0) >= (y1 - y0)
    lo, hi = (y0, y1) if along_x else (x0, x1)
    n = max(1, int((hi - lo + S["gap"]) // (S["w"] + S["gap"])))
    w = ((hi - lo) - S["gap"] * (n - 1)) / n
    slats = []
    for i in range(n):
        a = lo + i * (w + S["gap"])
        slats.append(box("seat-timber", x0, a, g + pl, x1, a + w, g + h) if along_x else box("seat-timber", a, y0, g + pl, a + w, y1, g + h))
    return Obj(oid, "bench", "built-in bench / seat wall, %d seats: rendered masonry plinth + %d hardwood slats %d mm with %d mm gaps (heights from layout seat-wall spec; finish ASSUMED)"
               % (seats, n, round(w * 1000), round(S["gap"] * 1000)), [box("wall-render", x0, y0, g, x1, y1, g + pl), *slats], layout_id=layout_id, footprint=rect,
               meta=dict(seats=seats, height_m=h))


def coping(oid, wall_id, rect, h, g):
    """Wall cap: a stone coping slab over the wall head, overhanging 40 mm each side (ASSUMED), resting on the wall."""
    C = P.COPING
    x0, y0, x1, y1 = rect
    return Obj(oid, "coping", "wall coping, %d mm stone cap with %d mm overhang (ASSUMED detail; the layout gives the wall only)" % (C["thick"] * 1000, C["overhang"] * 1000),
               [box("wall-coping", x0 - C["overhang"], y0 - C["overhang"], g + h, x1 + C["overhang"], y1 + C["overhang"], g + h + C["thick"])], rests_on=(wall_id,), footprint_mode=None)


def edging(oid, bed_id, rect, g):
    """Steel bed edging round a planting bed: 4 mm strip, 15 mm proud of the ground, set inside the bed rect."""
    E_ = P.EDGING
    x0, y0, x1, y1 = rect
    t = E_["t"]
    z0, z1 = g - E_["below"], g + E_["above"]
    parts = [box("bed-edging", x0, y0, z0, x1, y0 + t, z1), box("bed-edging", x0, y1 - t, z0, x1, y1, z1),
             box("bed-edging", x0, y0 + t, z0, x0 + t, y1 - t, z1), box("bed-edging", x1 - t, y0 + t, z0, x1, y1 - t, z1)]
    return Obj(oid, "edging", "steel bed edging, %d mm, %d mm proud of the ground (ASSUMED detail)" % (E_["t"] * 1000, E_["above"] * 1000), parts, rests_on=(bed_id,), footprint_mode=None)


def _rot(pts, yaw):
    c, s = round(math.cos(yaw)), round(math.sin(yaw))
    return [(x * c - y * s, x * s + y * c) for x, y in pts]


def table(oid, layout_id, center, size, g, seats):
    t = P.TABLE
    cx, cy = center
    w, d = size
    parts = [box("table-timber", cx - w / 2, cy - d / 2, g + t["h"] - t["top"], cx + w / 2, cy + d / 2, g + t["h"])]
    for sx in (-1, 1):
        for sy in (-1, 1):
            px, py = cx + sx * (w / 2 - t["inset"]), cy + sy * (d / 2 - t["inset"])
            parts.append(box("table-timber", px - t["leg"] / 2, py - t["leg"] / 2, g, px + t["leg"] / 2, py + t["leg"] / 2, g + t["h"] - t["top"]))
    return Obj(oid, "table", "generic dining table %.1f x %.1f m for %d: SIMPLE GEOMETRY, not a product (no free outdoor table in the library)" % (w, d, seats), parts,
               layout_id=layout_id, footprint=(cx - w / 2, cy - d / 2, cx + w / 2, cy + d / 2), meta=dict(seats=seats))


def chair(oid, cx, cy, face, g):
    """Generic chair, `face` = unit (dx,dy) it looks along; its back is on the opposite side."""
    c = P.CHAIR
    s = c["seat"] / 2
    yaw = math.atan2(face[1], face[0])
    loc = lambda x0, y0, x1, y1: [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    def b(material, x0, y0, z0, x1, y1, z1):
        pts = [(cx + px, cy + py) for px, py in _rot(loc(x0, y0, x1, y1), yaw)]
        return prism(material, pts, g + z0, g + z1)
    parts = [b("chair-timber", -s, -s, c["seat_h"] - 0.04, s, s, c["seat_h"]), b("chair-timber", -s, -s, c["seat_h"], -s + 0.03, s, c["back_h"])]
    for lx in (-s, s - 0.03):
        for ly in (-s, s - 0.03):
            parts.append(b("chair-timber", lx, ly, 0, lx + 0.03, ly + 0.03, c["seat_h"] - 0.04))
    return Obj(oid, "chair", "generic dining chair: SIMPLE GEOMETRY, not a product (the library's only dining chair is an indoor bouclé upholstered chair)", parts,
               footprint_mode=None)


def chair_spots(center, size, seats, off=None):
    """[((x, y), (face dx, dy))] of the chairs round a table: long sides first, then the ends."""
    cx, cy = center
    w, d = size
    off = P.CHAIR["off"] if off is None else off
    n_long = max(0, (seats - 2) // 2)
    xs = [cx + (k - (n_long - 1) / 2) * (w / max(n_long, 1)) for k in range(n_long)]
    spots = []
    for x in xs:
        spots += [((x, cy + d / 2 + off), (0, -1)), ((x, cy - d / 2 - off), (0, 1))]
    if seats >= 2 and len(spots) < seats:
        spots += [((cx + w / 2 + off, cy), (-1, 0)), ((cx - w / 2 - off, cy), (1, 0))]
    return spots[:seats]


def chairs_for(table_id, center, size, seats, g):
    return [chair("ld-%s-chair-%d" % (table_id, i), x, y, f, g) for i, ((x, y), f) in enumerate(chair_spots(center, size, seats))]


def bbq(oid, layout_id, rect, g):
    x0, y0, x1, y1 = rect
    cx, cy, r = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2
    parts = [cyl("bbq-steel", cx, cy, r, g + P.BBQ["bowl_z0"], g + P.BBQ["bowl_z1"], r_top=r * 0.8),
             cyl("bbq-steel", cx, cy, r * 0.8, g + P.BBQ["bowl_z1"], g + P.BBQ["bowl_z1"] + 0.12, r_top=r * 0.3)]
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.5
        lx, ly = cx + 0.7 * r * math.cos(a), cy + 0.7 * r * math.sin(a)
        parts.append(cyl("bbq-steel", lx, ly, 0.015, g, g + P.BBQ["bowl_z0"], n=8))
    return Obj(oid, "bbq", "portable BBQ stand: generic kettle, SIMPLE GEOMETRY, not a product (brief: portable, hard surface under it)", parts, layout_id=layout_id, footprint=R(rect))


def pot(oid, layout_id, rect, g):
    x0, y0, x1, y1 = rect
    cx, cy, r = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2
    return Obj(oid, "pot", "terracotta pot (ASSUMED %.2f m high; brief: terracotta pots)" % P.POT["h"], [cyl("terracotta", cx, cy, P.POT["r_bottom"], g, g + P.POT["h"], r_top=r)],
               layout_id=layout_id, footprint=R(rect))


def pond_axes(f):
    """-> (across, entry_is_max): section runs across the SHORT plan side; the entry margin is the low side unless the layout says high."""
    x0, y0, x1, y1 = R(f["rect"])
    across = "y" if (y1 - y0) <= (x1 - x0) else "x"
    es = ((f.get("section") or {}).get("entry_side") or "low").lower()
    return across, ("high" in es and "low" not in es)


def pond_profile(f, g):
    """Water cross-section [(s, z)] from the layout `section` (s from the entry edge). Entry slope waterline -> shelf, shelf, 900 mm trench, far wall."""
    x0, y0, x1, y1 = R(f["rect"])
    across, _ = pond_axes(f)
    W = (y1 - y0) if across == "y" else (x1 - x0)
    sec = f.get("section") or {}
    free = sec.get("freeboard_mm", f.get("freeboard_mm", 150)) / 1000
    wl = g - free
    sd = sec.get("shelf_below_water_mm", 150) / 1000
    e = sec.get("entry_run_m", 0.0)
    sh = sec.get("shelf_m", 0.25)
    td = sec.get("trench_below_water_mm", (f.get("depth_mm", 1000) - free * 1000)) / 1000
    if e + sh >= W:
        raise ValueError("pond %s: entry %.2f + shelf %.2f m leave no trench in a %.2f m section" % (f["id"], e, sh, W))
    return W, wl, [(0.0, wl), (e, wl - sd), (e + sh, wl - sd), (e + sh, wl - td), (W, wl - td), (W, wl)], dict(entry_run=e, shelf=sh, shelf_depth=sd, trench_depth=td, freeboard=free)


def pond(oid, layout_id, f, g):
    """Flush koi pond built from the layout section: vertical freeboard face, 1:4 entry slope to a shelf, a trench, a rigid grille 40 mm under the water,
    and a flush contrasting lip. The water is a closed solid (so the renderer can tint it by depth), the liner is the solid under the profile."""
    p = P.POND
    x0, y0, x1, y1 = R(f["rect"])
    W, wl, wp, d = pond_profile(f, g)
    across, entry_max = pond_axes(f)
    a0, a1 = (x0, x1) if across == "y" else (y0, y1)
    lo = (y0 if across == "y" else x0)
    hi = (y1 if across == "y" else x1)
    origin, flip = (hi, True) if entry_max else (lo, False)
    fl = wl - d["trench_depth"]
    wt, ct = p["wall_t"], p["floor_t"]
    ztop = g - p["coping_h"]                     # shell top, under the coping
    def ex(mat, prof, u0, u1):
        return extrude_profile(mat, prof, u0, u1, across=across, origin=origin, flip=flip)
    def slab(mat, s0, s1, u0, u1, z0, z1):      # box in (s, u, z): s across the section, u along the pond
        return ex(mat, [(s0, z0), (s1, z0), (s1, z1), (s0, z1)], u0, u1)
    liner_prof = [wp[0], wp[1], wp[2], wp[3], wp[4], (W, fl - ct), (0.0, fl - ct)]
    parts = [ex("pond-liner", liner_prof, a0, a1)]
    parts += [slab("pond-liner", -wt, 0.0, a0 - wt, a1 + wt, fl - ct, ztop), slab("pond-liner", W, W + wt, a0 - wt, a1 + wt, fl - ct, ztop),
              slab("pond-liner", -wt, W + wt, a0 - wt, a0, fl - ct, ztop), slab("pond-liner", -wt, W + wt, a1, a1 + wt, fl - ct, ztop)]
    lw = p["edge_lip"]
    bear = 0.04                                   # the wall carries a bearing ledge under the coping, above the water (ASSUMED detail)
    zl = ztop - bear
    parts += [slab("pond-liner", 0.0, bear, a0, a1, zl, ztop), slab("pond-liner", W - bear, W, a0, a1, zl, ztop),
              slab("pond-liner", bear, W - bear, a0, a0 + bear, zl, ztop), slab("pond-liner", bear, W - bear, a1 - bear, a1, zl, ztop)]
    lip_parts = [slab("pond-edge", 0.0, lw, a0, a1, ztop, g), slab("pond-edge", W - lw, W, a0, a1, ztop, g),
                 slab("pond-edge", lw, W - lw, a0, a0 + lw, ztop, g), slab("pond-edge", lw, W - lw, a1 - lw, a1, ztop, g)]
    basin = Obj(oid, "pond", "flush koi pond %.1f x %.1f m from the layout section: %.0f mm freeboard, entry slope 1:%.0f over %.2f m to a %.2f m shelf at %.0f mm below water, "
                "%.2f m trench at %.0f mm; 100 mm liner walls and floor ASSUMED construction" % (x1 - x0, y1 - y0, d["freeboard"] * 1000, d["entry_run"] / d["shelf_depth"] if d["shelf_depth"] else 0,
                d["entry_run"], d["shelf"], d["shelf_depth"] * 1000, W - d["entry_run"] - d["shelf"], d["trench_depth"] * 1000),
                parts, layout_id=layout_id, footprint=None, footprint_mode=None,
                meta=dict(water_z=wl, floor_z=fl, across=across, entry_max=entry_max, section=d, W=W, rect=(x0, y0, x1, y1), declared=f.get("section"), ground_z=g))
    lip = Obj(oid + "-lip", "pond-lip", "flush contrasting lip: %d mm wide coping inside the pond rect, top at ground level, overhanging the water edge (layout: flush, contrasting)" % int(lw * 1000), lip_parts, rests_on=(oid,), footprint_mode=None,
              meta=dict(top_z=g, width_m=lw))
    water = Obj(oid + "-water", "water", "pond water surface %d mm below the rim, depth-tinted closed solid" % int(d["freeboard"] * 1000), [ex("water", wp, a0, a1)],
                rests_on=(oid,), layout_id=layout_id, footprint=(x0, y0, x1, y1), footprint_mode="bbox", meta=dict(z=wl))
    gt = wl - p["grille_top_below_water"]
    gb, gp, gth = p["grille_bar"], p["grille_pitch"], p["grille_t"]
    sg = d["entry_run"] * p["grille_top_below_water"] / d["shelf_depth"] + 0.002          # where the entry slope reaches the grille level
    bars = []
    k = 0
    while sg + k * gp + gb <= W + 1e-9:
        bars.append(slab("grille-steel", sg + k * gp, sg + k * gp + gb, a0, a1, gt - gth, gt)); k += 1
    bars.append(slab("grille-steel", W - gb, W, a0, a1, gt - gth, gt))
    u = a0
    while u + gb <= a1 + 1e-9:
        bars.append(slab("grille-steel", sg, W, u, u + gb, gt - gth, gt)); u += gp
    bars.append(slab("grille-steel", sg, W, a1 - gb, a1, gt - gth, gt))
    se = d["entry_run"] + d["shelf"]
    bars.append(slab("grille-steel", se - 0.03, se, a0, a1, wl - d["shelf_depth"], gt - gth))      # rib: the grille rests on the shelf edge
    grille = Obj(oid + "-grille", "grille", "rigid child-protection grille %d mm below the water surface, mesh bars %d x %d mm at %d mm pitch (POLICY), resting on a rib on the shelf and on the walls "
                 "(layout: rigid_grille; bar section and pitch are POLICY, no published aperture or load figure, GAP-POND-GRILLE-LOAD)" % (int(p["grille_top_below_water"] * 1000), int(gb * 1000), int(gth * 1000), int(gp * 1000)),
                 bars, rests_on=(oid, oid + "-water"), footprint_mode=None, meta=dict(top_z=gt, below_water_m=p["grille_top_below_water"], s0=sg))
    return [basin, lip, water, grille]


def pond_point(f, s, u, g=None):
    """Plan (x, y) of section position s (from the entry edge) and along-pond fraction u in 0..1."""
    x0, y0, x1, y1 = R(f["rect"])
    across, entry_max = pond_axes(f)
    a0, a1 = (x0, x1) if across == "y" else (y0, y1)
    lo, hi = (y0, y1) if across == "y" else (x0, x1)
    sv = hi - s if entry_max else lo + s
    uv = a0 + u * (a1 - a0)
    return (uv, sv) if across == "y" else (sv, uv)


def _half_poly(cx, cy, r, axis, sign, n=24):
    a0 = {("y", 1): 0.0, ("y", -1): math.pi, ("x", 1): -math.pi / 2, ("x", -1): math.pi / 2}[(axis, sign)]
    return Polygon([(cx + r * math.cos(a0 + math.pi * i / n), cy + r * math.sin(a0 + math.pi * i / n)) for i in range(n + 1)])


def _full_poly(cx, cy, r, n=24):
    return Polygon([(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)])


def cover_parts(cx, cy, d, ctop, grids, half):
    """Fire-pit cover that CONTINUES THE PAVER PATTERN: a thin steel plate carrying the same 0.6 x 0.3 running-bond units, each piece on the grid of the paving (or path)
    rect it lies in (`grids` = [(rect, along)] ordered by overlap), clipped to the disc (or the half disc on our side of the boundary)."""
    p, pv = P.PIT, P.PAVER
    poly = _half_poly(cx, cy, d / 2, *half) if half else _full_poly(cx, cy, d / 2)
    pl = list(poly.exterior.coords)[:-1]
    parts = [prism("paving-joint", pl, ctop - p["cover_t"], ctop - pv["thick"])]
    left = poly
    for rect, along in grids:
        piece = left.intersection(sbox(*rect))
        if piece.is_empty or piece.area < 1e-5:
            continue
        parts += units(rect, [], ctop, pv["len"], pv["wid"], along, "paving-unit", clip=piece)
        left = left.difference(sbox(*rect))
    return parts


def firepit(oid, layout_id, f, g, half=None, grids=(), tag=""):
    """Flush gas fire pit: liner box below the paving, burner with a flame (open state), flush paver-pattern cover (closed) or the cover set aside (open).
    `half` = (axis, sign): build only that half (the pit straddles the shared boundary; the other half is the neighbour's and is never part of our scene)."""
    p = P.PIT
    cx, cy = f["center"]
    d = f["diameter_m"]
    lip = (f.get("cover") or {}).get("lip_mm", 6.0) / 1000
    h = p["hole"] / 2
    t = p["liner_t"]
    fl = g - p["depth"]
    pv_top = g - P.PAVER["thick"]
    ax, sg = half if half else ("y", 1)
    def hb(material, x0, y0, z0, x1, y1, z1):        # box clipped to the kept half
        if half:
            if ax == "y":
                y0, y1 = (max(y0, cy), y1) if sg > 0 else (y0, min(y1, cy))
            else:
                x0, x1 = (max(x0, cx), x1) if sg > 0 else (x0, min(x1, cx))
            if x1 - x0 <= 1e-9 or y1 - y0 <= 1e-9:
                return None
        return box(material, x0, y0, z0, x1, y1, z1)
    def hc(material, r, z0, z1, r_top=None, n=24):
        return half_frustum(material, cx, cy, r, z0, z1, r_top, ax, sg, n) if half else cyl(material, cx, cy, r, z0, z1, n=n, r_top=r_top)
    parts = [hb("pit-steel", cx - h, cy - h, fl - 0.02, cx + h, cy + h, fl),
             hb("pit-steel", cx - h, cy - h, fl, cx + h, cy - h + t, pv_top), hb("pit-steel", cx - h, cy + h - t, fl, cx + h, cy + h, pv_top),
             hb("pit-steel", cx - h, cy - h + t, fl, cx - h + t, cy + h - t, pv_top), hb("pit-steel", cx + h - t, cy - h + t, fl, cx + h, cy + h - t, pv_top)]
    parts = [q for q in parts if q is not None]
    parts += [hc("lava-rock", 0.28, fl, fl + 0.10), hc("burner", 0.30, fl + 0.10, fl + 0.13)]
    where = "ours half only (the pit straddles the shared west line; the neighbour's half is not part of this scene)" if half else "whole pit"
    chamber = Obj(oid, "firepit", "flush gas fire pit chamber (gas, %s; %s; liner/burner dimensions ASSUMED, product not chosen: LS-FIRE-PRODUCT)" % (f.get("fuel", "gas"), where), parts, layout_id=layout_id,
                  footprint=(cx - d / 2, cy - d / 2, cx + d / 2, cy + d / 2), footprint_mode="within", meta=dict(cover=f.get("cover"), half=half))
    flame = Obj(oid + "-flame", "flame", "flame shown in the open state: an emissive cone (not simulated fire)", [hc("flame", 0.18, fl + 0.13, fl + 0.13 + p["flame_h"], 0.02, 16)],
                rests_on=(oid,), footprint_mode=None, state="open")
    gr = list(grids) or [((cx - 1.5, cy - 1.5, cx + 1.5, cy + 1.5), "x")]
    cov = dict(rests_on=("ground",), layout_id=layout_id)
    closed = Obj(oid + "-cover", "firepit-cover", "flush fire-pit cover, CLOSED: paver-pattern top continuing the paving grid, %.0f mm proud (layout lip %d mm, load rating %s kN), 3 mm gap to the paving%s"
                 % (lip * 1000, int((f.get("cover") or {}).get("lip_mm", 6)), (f.get("cover") or {}).get("load_rating_kN"), "; our half" if half else ""),
                 cover_parts(cx, cy, d, g + lip, gr, half), footprint=(cx - d / 2, cy - d / 2, cx + d / 2, cy + d / 2), footprint_mode="within", state="closed", **cov)
    dx = 1.05
    opened = Obj(oid + "-cover", "firepit-cover", "flush fire-pit cover, OPEN: lifted off and set on the paving beside the pit (paver-pattern face up)",
                 [shifted(q, dx=dx, dz=P.PIT["cover_t"] - lip) for q in cover_parts(cx, cy, d, g + lip, gr, half)], footprint_mode=None, state="open", **cov)
    return [chamber, flame, closed, opened]


def root_barrier(oid, layout_id, center, rect, radius, g, depth):
    """Root barrier: a thin vertical sheet ringing a tree, top flush with the ground, `depth` m deep (ASSUMED 0.9 m: no published depth is claimed).
    Ring = the declared / enclosing bed rect inset 30 mm, else a polygon of `radius` (default 1.0 m) round the trunk."""
    b = P.ROOT_BARRIER
    t = b["t"]
    z0, z1 = g - depth, g
    if rect is not None:
        x0, y0, x1, y1 = rect
        x0, y0, x1, y1 = x0 + 0.03, y0 + 0.03, x1 - 0.03, y1 - 0.03
        parts = [box("root-barrier", x0, y0, z0, x1, y0 + t, z1), box("root-barrier", x0, y1 - t, z0, x1, y1, z1),
                 box("root-barrier", x0, y0 + t, z0, x0 + t, y1 - t, z1), box("root-barrier", x1 - t, y0 + t, z0, x1, y1 - t, z1)]
        what = "ringing the bed %.1f x %.1f m" % (x1 - x0, y1 - y0)
    else:
        r = radius or 1.0
        cx, cy = center
        n = 16
        pts = [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
        parts = []
        for i in range(n):
            (ax, ay), (bx, by) = pts[i], pts[(i + 1) % n]
            nx_, ny_ = by - ay, -(bx - ax)
            ln = math.hypot(nx_, ny_)
            nx_, ny_ = nx_ / ln * t, ny_ / ln * t
            parts.append(prism("root-barrier", [(ax, ay), (bx, by), (bx + nx_, by + ny_), (ax + nx_, ay + ny_)], z0, z1))
        what = "ring of radius %.1f m round the trunk" % r
    return Obj(oid, "root-barrier", "root barrier sheet %.1f m deep, %d mm, top flush with the ground, %s (depth and thickness ASSUMED; the layout declares the barrier, not its section)" % (depth, int(t * 1000), what),
               parts, layout_id=layout_id, footprint_mode=None, meta=dict(depth_m=depth, top_z=z1))
