"""Builders: one function per kind of layout element. Each returns Obj(s) with an `ld-*` id and the layout footprint it must match."""
from __future__ import annotations

import math

import numpy as np
from shapely.geometry import MultiPolygon, Polygon, box as sbox
from shapely.ops import unary_union

from . import policy as P
from .geom import Obj, Part, box, cyl, prism, rbox, slanted_slat


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


def paving(oid, layout_id, rect, g, paths, pit):
    """Bedding slab (joint colour) + running-bond units; units are cut around path rects (built as the path) and the pit cover opening."""
    pv = P.PAVER
    x0, y0, x1, y1 = rect
    r = sbox(*rect)
    slab_geom = r
    if pit:
        h = P.PIT["hole"] / 2
        slab_geom = r.difference(sbox(pit[0] - h, pit[1] - h, pit[0] + h, pit[1] + h))
    top = g - pv["thick"]
    parts = [rbox("paving-joint", *q, top - pv["bedding"], top) for q in poly_rects(slab_geom)]
    cut = [sbox(*p) for p in paths]
    if pit:
        rr = pit[2] / 2 + P.PIT["gap"]
        cut.append(Polygon([(pit[0] + rr * math.cos(2 * math.pi * i / 24), pit[1] + rr * math.sin(2 * math.pi * i / 24)) for i in range(24)]))
    parts += units(rect, cut, g, pv["len"], pv["wid"], "x", "paving-unit")
    return Obj(oid, "paving", "unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material %s)" % "unit-paving",
               parts, layout_id=layout_id, footprint=rect, meta=dict(units=len(parts) - len(poly_rects(slab_geom))))


def units(rect, cuts, g, ulen, uwid, along, material):
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
    x0, y0, x1, y1 = rect
    pl = h - P.SEAT_TOP
    return Obj(oid, "bench", "built-in bench / seat wall, %d seats: masonry plinth + %d mm timber seat (heights from layout seat-wall spec; finish ASSUMED)" % (seats, int(P.SEAT_TOP * 1000)),
               [box("wall-render", x0, y0, g, x1, y1, g + pl), box("seat-timber", x0, y0, g + pl, x1, y1, g + h)], layout_id=layout_id, footprint=rect,
               meta=dict(seats=seats, height_m=h))


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


def chairs_for(table_id, center, size, seats, g):
    cx, cy = center
    w, d = size
    off = P.CHAIR["off"]
    n_long = max(0, (seats - 2) // 2)
    out = []
    xs = [cx + (k - (n_long - 1) / 2) * (w / max(n_long, 1)) for k in range(n_long)]
    spots = []
    for x in xs:
        spots += [((x, cy + d / 2 + off), (0, -1)), ((x, cy - d / 2 - off), (0, 1))]
    if seats >= 2 and len(spots) < seats:
        spots += [((cx + w / 2 + off, cy), (-1, 0)), ((cx - w / 2 - off, cy), (1, 0))]
    for i, ((x, y), f) in enumerate(spots[:seats]):
        out.append(chair("ld-%s-chair-%d" % (table_id, i), x, y, f, g))
    return out


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


def pond(oid, layout_id, f, g):
    """Flush koi pond: rim at ground level, water below it (freeboard from the layout), safety shelf, submerged rigid grille, flush contrast lip."""
    p = P.POND
    x0, y0, x1, y1 = R(f["rect"])
    free = f.get("freeboard_mm", 150) / 1000
    depth = f.get("depth_mm", 1000) / 1000
    wl = g - free
    w_, sh = p["wall_t"], p["shelf_w"]
    shelf_top = wl - p["shelf_below_water"]
    fl = g - depth
    ix0, iy0, ix1, iy1 = x0 + w_, y0 + w_, x1 - w_, y1 - w_
    parts = [box("pond-concrete", x0, y0, fl - p["floor_t"], x1, y1, fl)]
    parts += [box("pond-concrete", x0, y0, fl, x1, iy0, g - p["lip_t"]), box("pond-concrete", x0, iy1, fl, x1, y1, g - p["lip_t"]),
              box("pond-concrete", x0, iy0, fl, ix0, iy1, g - p["lip_t"]), box("pond-concrete", ix1, iy0, fl, x1, iy1, g - p["lip_t"])]
    sx0, sy0, sx1, sy1 = ix0 + sh, iy0 + sh, ix1 - sh, iy1 - sh
    parts += [box("pond-concrete", ix0, iy0, fl, ix1, sy0, shelf_top), box("pond-concrete", ix0, sy1, fl, ix1, iy1, shelf_top),
              box("pond-concrete", ix0, sy0, fl, sx0, sy1, shelf_top), box("pond-concrete", sx1, sy0, fl, ix1, sy1, shelf_top)]
    lw = p["edge_lip"]
    lt = g - p["lip_t"]
    parts += [box("pond-edge", x0, y0, lt, x1, y0 + lw, g), box("pond-edge", x0, y1 - lw, lt, x1, y1, g),
              box("pond-edge", x0, y0 + lw, lt, x0 + lw, y1 - lw, g), box("pond-edge", x1 - lw, y0 + lw, lt, x1, y1 - lw, g)]
    basin = Obj(oid, "pond", "flush koi pond %.1f x %.1f m: rim at ground level, water %d mm below the rim, %d mm contrasting flush lip, safety shelf %d mm wide at %d mm below water "
                "(shelf width ASSUMED: GAP-POND-EDGE-SAFETY); layout edge slope 1:%s is not modelled (it needs %.1f m of run in a %.1f m wide pond)"
                % (x1 - x0, y1 - y0, int(free * 1000), int(lw * 1000), int(sh * 1000), int(p["shelf_below_water"] * 1000), f.get("edge_slope_run_per_rise"),
                   (f.get("edge_slope_run_per_rise") or 0) * (depth - free), min(x1 - x0, y1 - y0)),
                parts, layout_id=layout_id, footprint=(x0, y0, x1, y1), meta=dict(water_z=wl, shelf_top=shelf_top, floor_z=fl, depth_m=depth, freeboard_m=free))
    water = Obj(oid + "-water", "water", "pond water surface %d mm below the rim" % int(free * 1000), [box("water", ix0, iy0, wl - 0.02, ix1, iy1, wl)],
                rests_on=(oid,), footprint=(ix0, iy0, ix1, iy1), footprint_mode="bbox", meta=dict(z=wl))
    bars = []
    gp, gb = p["grille_pitch"], p["grille_bar"]
    gt = wl - p["grille_top_below_water"]
    k = 0
    while ix0 + gb + k * gp <= ix1 - gb + 1e-9 or k == 0:
        px = ix0 + k * gp
        bars.append(box("grille-steel", px, iy0, shelf_top, min(px + gb, ix1), iy1, gt)); k += 1
        if px + gb >= ix1: break
    bars.append(box("grille-steel", ix1 - gb, iy0, shelf_top, ix1, iy1, gt))
    k = 0
    while iy0 + k * gp < iy1 - gb:
        py = iy0 + k * gp
        bars.append(box("grille-steel", ix0, py, shelf_top, ix1, py + gb, gt)); k += 1
    bars.append(box("grille-steel", ix0, iy1 - gb, shelf_top, ix1, iy1, gt))
    grille = Obj(oid + "-grille", "grille", "rigid child-protection grille %d mm below the water surface, bars %d mm at %d mm (layout: rigid_grille; bar section/pitch ASSUMED; "
                 "no published load figure, GAP-POND-GRILLE-LOAD)" % (int(p["grille_top_below_water"] * 1000), int(gb * 1000), int(gp * 1000)), bars,
                 rests_on=(oid,), footprint=(ix0, iy0, ix1, iy1), footprint_mode="bbox", meta=dict(top_z=gt, below_water_m=p["grille_top_below_water"]))
    return [basin, water, grille]


def firepit(oid, layout_id, f, g):
    """Flush gas fire pit: liner box below the paving, burner with a flame (open state), flush cover disc (closed) or the cover set aside (open)."""
    p = P.PIT
    cx, cy = f["center"]
    d = f["diameter_m"]
    lip = (f.get("cover") or {}).get("lip_mm", 6.0) / 1000
    h = p["hole"] / 2
    t = p["liner_t"]
    fl = g - p["depth"]
    pv_top = g - P.PAVER["thick"]
    parts = [box("pit-steel", cx - h, cy - h, fl - 0.02, cx + h, cy + h, fl)]
    parts += [box("pit-steel", cx - h, cy - h, fl, cx + h, cy - h + t, pv_top), box("pit-steel", cx - h, cy + h - t, fl, cx + h, cy + h, pv_top),
              box("pit-steel", cx - h, cy - h + t, fl, cx - h + t, cy + h - t, pv_top), box("pit-steel", cx + h - t, cy - h + t, fl, cx + h, cy + h - t, pv_top)]
    parts += [cyl("lava-rock", cx, cy, 0.28, fl, fl + 0.10), cyl("burner", cx, cy, 0.30, fl + 0.10, fl + 0.13, r_top=0.30)]
    chamber = Obj(oid, "firepit", "flush gas fire pit chamber (gas, %s; liner/burner dimensions ASSUMED, product not chosen: LS-FIRE-PRODUCT)" % f.get("fuel", "gas"), parts, layout_id=layout_id,
                  footprint=(cx - d / 2, cy - d / 2, cx + d / 2, cy + d / 2), footprint_mode="within", meta=dict(cover=f.get("cover")))
    flame = Obj(oid + "-flame", "flame", "flame shown in the open state: an emissive cone (not simulated fire)", [cyl("flame", cx, cy, 0.18, fl + 0.13, fl + 0.13 + p["flame_h"], r_top=0.02, n=16)],
                rests_on=(oid,), footprint_mode=None, state="open")
    ctop = g + lip
    closed = Obj(oid + "-cover", "firepit-cover", "flush fire-pit cover, CLOSED: paving-faced disc %.0f mm proud (layout lip %d mm, load rating %s kN), 3 mm gap to the paving"
                 % (lip * 1000, int((f.get("cover") or {}).get("lip_mm", 6)), (f.get("cover") or {}).get("load_rating_kN")),
                 [cyl("cover-top", cx, cy, d / 2, ctop - p["cover_t"], ctop)], layout_id=layout_id,
                 footprint=(cx - d / 2, cy - d / 2, cx + d / 2, cy + d / 2), rests_on=("ground",), state="closed")
    ox = cx + 1.05
    opened = Obj(oid + "-cover", "firepit-cover", "flush fire-pit cover, OPEN: lifted off and set on the paving beside the pit", [cyl("cover-top", ox, cy, d / 2, g, g + p["cover_t"])],
                 layout_id=layout_id, footprint_mode=None, rests_on=("ground",), state="open")
    return [chamber, flame, closed, opened]
