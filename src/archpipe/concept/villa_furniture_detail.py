"""Render geometry for the D1 pieces that `archpipe.furniture` has no builder for (sofas, armchairs, tables, chairs,
stools, kitchen runs and island, sideboard, TV unit, washbasin, WC, bath).

Render only: the Revit model keeps `villa_furnish3d`'s boxes, which carry the checked footprints. Every piece here
lies inside the same footprint and height as its box version (the envelope is checked on every vertex, as
`archpipe.furniture` does), so nothing a check measured moves. What changes is form: cushions, legs, fronts with
gaps and pulls, a worktop over a recessed plinth, a basin and a bath with a real bowl. Invented details (taps, pulls,
leg style) are ASSUMED stand-ins, stated in the scene notes; the product models replace them.

Frames: `villa_furnish3d`'s local frame (x across, +y the front, z up from the storey floor), built in millimetres
with `archpipe.furniture`'s verified primitives (outward winding), then mapped to world metres exactly as
`villa_furnish3d.to_world` maps boxes. Each rotation used is proper (determinant +1), so winding survives.
"""
from __future__ import annotations

from .. import furniture as G
from . import villa_furnish3d as F3

SEATS = {"sofa_2seat": 2, "sofa_3seat": 3, "sofa_4seat": 4, "armchair": 1, "recliner": 1}


class EnvelopeError(ValueError):
    pass


def _r(x0, x1, y0, y1, r):
    """A corner radius strictly below half the ring's short side: at exactly half, neighbouring corner arcs share an
    end point and the loft gets zero-area triangles (the render contract rejected 1,780 of them)."""
    return max(1.0, min(r, 0.45 * min(x1 - x0, y1 - y0)))


def _ring(x0, x1, y0, y1, z, r):
    return (x0, x1, y0, y1, z, _r(x0, x1, y0, y1, r))


def _bowl(x0, x1, y0, y1, z0, z1, r_out, rim, depth, inset_bottom, r_in, seg=6):
    """A closed vessel: outer wall up, a flat rim inward, the inner wall down to the bowl floor (whose top cap faces
    up). The loft's side quads face outward on the way up, up across the rim and into the bowl on the way down:
    all away from the solid."""
    rings = [_ring(x0, x1, y0, y1, z0, r_out), _ring(x0, x1, y0, y1, z1, r_out),
             _ring(x0 + rim, x1 - rim, y0 + rim, y1 - rim, z1, r_out - rim * 0.6),
             _ring(x0 + inset_bottom, x1 - inset_bottom, y0 + inset_bottom, y1 - inset_bottom, z1 - depth, r_in)]
    return G._loft_rings(rings, seg)


def _taper_leg(cx, cy, z0, z1, r0, r1, seg=5):
    """A round leg tapering from r1 at the top to r0 at the floor."""
    return G._loft_rings([_ring(cx - r0, cx + r0, cy - r0, cy + r0, z0, r0),
                          _ring(cx - r1, cx + r1, cy - r1, cy + r1, z1, r1)], seg)


def _slab(x0, x1, y0, y1, z0, z1, radius, bevel, seg=4):
    b = max(0.0, min(bevel, (z1 - z0) / 2.0 - 1e-6, (x1 - x0) / 2.0 - 1e-3, (y1 - y0) / 2.0 - 1e-3))
    return G._beveled_box(x0, x1, y0, y1, z0, z1, _r(x0 + b, x1 - b, y0 + b, y1 - b, radius) + b, bevel, seg)


# ------------------------------------------------------------------ seating
def _sofa(W, D, H, seats, arm):
    x0, x1, yb, yf = -W / 2, W / 2, -D / 2, D / 2
    out = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            out.append(("leg", _taper_leg(sx * (W / 2 - 70), sy * (D / 2 - 70), 0, 60, 12, 18)))
    out.append(("base", _slab(x0 + 22, x1 - 22, yb + 18, yf - 18, 75, 220, 25, 12)))
    out.append(("plinth", G._box(x0 + 24, x1 - 24, yb + 25, yf - 25, 55, 78)))
    for a0 in (x0, x1 - arm):
        out.append(("arm", _slab(a0 - (15 if a0 > 0 else 0), a0 + arm + (15 if a0 < 0 else 0),
                                  yb, yf, 190, 620, 65, 55, seg=8)))
    out.append(("base", _slab(x0 + arm, x1 - arm, yb, yb + 60, 220, H - 60, 20, 10)))      # back frame
    inner0, inner1 = x0 + arm + 5, x1 - arm - 5
    cw = (inner1 - inner0) / seats
    seat_top = 440
    for k in range(seats):
        a, b = inner0 + k * cw + 4, inner0 + (k + 1) * cw - 4
        # Separate pillow-like volumes keep an 8 mm seam. The crown is a loft,
        # not a bevel on a flat box; its top ring is set in from every edge.
        out.append(("seat", G._loft_rings([
            _ring(a + 22, b - 22, yb + 205, yf - 23, 222, 50),
            _ring(a, b, yb + 188, yf - 5, 300, 65),
            _ring(a, b, yb + 188, yf - 5, 390, 65),
            _ring(a + 17, b - 17, yb + 205, yf - 22, seat_top - 12, 57),
            _ring(a + 70, b - 70, yb + 250, yf - 65, seat_top, 42)], 8)))
        # The back cushion inclines towards the rear at its top and has a
        # rounded, raised face. It remains within the checked sofa envelope.
        out.append(("back", G._loft_rings([
            _ring(a + 20, b - 20, yb + 88, yb + 250, 230, 45),
            _ring(a, b, yb + 65, yb + 267, 315, 60),
            _ring(a, b, yb + 46, yb + 248, H - 58, 60),
            _ring(a + 24, b - 24, yb + 58, yb + 228, H - 10, 48)], 8)))
    return out


def _chair(W, D, seat=460, back=850):
    """A dining / desk chair: tapered round legs, the rear pair running up as the back posts, an upholstered seat
    pad on a timber frame and a timber backrest. Front +y, back at -y."""
    x0, x1, yb, yf = -W / 2, W / 2, -D / 2, D / 2
    out = []
    for sx in (-1, 1):
        out.append(("leg", _taper_leg(sx * (W / 2 - 25), yf - 25, 0, seat - 40, 12, 17)))
        out.append(("back", _taper_leg(sx * (W / 2 - 25), yb + 22, 0, back - 10, 12, 17)))
    out.append(("leg", _slab(x0 + 10, x1 - 10, yb + 15, yf - 10, seat - 95, seat - 45, 15, 4)))  # seat frame
    out.append(("seat", _slab(x0 + 5, x1 - 5, yb + 10, yf, seat - 50, seat, 45, 18)))
    out.append(("back", _slab(x0 + 8, x1 - 8, yb + 5, yb + 35, back - 190, back, 25, 8)))
    return out


def _task_chair(W, D, seat=460, back=850):
    """ASSUMED ergonomic task chair: five castered spokes, gas lift, shaped seat and lumbar back."""
    import math
    r = min(W, D) / 2 - 24
    out = [("gas-lift", G._cylinder(0, 0, 65, seat - 35, 22, seg=16)),
           ("seat-mesh", _slab(-W / 2 + 8, W / 2 - 8, -D / 2 + 30, D / 2 - 12,
                               seat - 55, seat, 55, 18))]
    for k in range(5):
        a = 2 * math.pi * k / 5
        x, y = r * math.cos(a), r * math.sin(a)
        out.append(("spoke", G._box(min(0, x) - 13, max(0, x) + 13,
                                      min(0, y) - 13, max(0, y) + 13, 55, 75)))
        out.append(("caster", G._cylinder(x, y, 0, 58, 21, seg=12)))
    # The three loft rings put the widest padding at lumbar height.
    out.append(("back-mesh", G._loft_rings([
        _ring(-W / 2 + 22, W / 2 - 22, -D / 2 + 7, -D / 2 + 38, seat - 20, 12),
        _ring(-W / 2 + 14, W / 2 - 14, -D / 2 + 2, -D / 2 + 58, seat + 125, 16),
        _ring(-W / 2 + 25, W / 2 - 25, -D / 2 + 12, -D / 2 + 42, back, 12)], 5)))
    for sx in (-1, 1):
        x = sx * (W / 2 - 25)
        out.append(("armrest", G._box(x - 14, x + 14, -D / 2 + 60, D / 2 - 55,
                                        seat + 150, seat + 180)))
        out.append(("arm-post", G._box(x - 9, x + 9, 10, 28, seat - 55, seat + 150)))
    return out


def _stool(W, D, seat=650):
    r = min(W, D) / 2
    out = [("base", G._cylinder(0, 0, 0, 15, min(r - 5, 175), seg=32)),
           ("post", G._cylinder(0, 0, 15, seat - 60, 22, seg=16)),
           ("footrest", G._cylinder(0, 0, 250, 262, min(r - 40, 150), seg=32)),
           ("seat", _slab(-r + 5, r - 5, -r + 5, r - 5, seat - 60, seat, r - 5, 18, seg=8))]
    return out


# ------------------------------------------------------------------ tables
def _coffee_table(W, D, H):
    x0, x1, yb, yf = -W / 2, W / 2, -D / 2, D / 2
    out = [("top", _slab(x0, x1, yb, yf, H - 40, H, 30, 10))]
    for sx in (-1, 1):
        for sy in (-1, 1):
            out.append(("leg", _taper_leg(sx * (W / 2 - 70), sy * (D / 2 - 70), 0, H - 40, 12, 16)))
    out.append(("shelf", _slab(x0 + 55, x1 - 55, yb + 55, yf - 55, 120, 140, 12, 4)))
    return out


def _dining_table(W, D, H):
    x0, x1, yb, yf = -W / 2, W / 2, -D / 2, D / 2
    out = [("top", _slab(x0, x1, yb, yf, H - 40, H, 20, 8))]
    ins = 90
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * (W / 2 - ins), sy * (D / 2 - ins)
            out.append(("leg", G._loft_rings([_ring(cx - 22, cx + 22, cy - 22, cy + 22, 0, 4),
                                              _ring(cx - 35, cx + 35, cy - 35, cy + 35, H - 40, 4)], 2)))
    a = 22
    out += [("apron", G._box(x0 + ins, x1 - ins, yb + ins - a, yb + ins - a + 22, H - 120, H - 40)),
            ("apron", G._box(x0 + ins, x1 - ins, yf - ins + a - 22, yf - ins + a, H - 120, H - 40)),
            ("apron", G._box(x0 + ins - a, x0 + ins - a + 22, yb + ins, yf - ins, H - 120, H - 40)),
            ("apron", G._box(x1 - ins + a - 22, x1 - ins + a, yb + ins, yf - ins, H - 120, H - 40))]
    return out


def _desk(W, D, H):
    """ASSUMED work desk with a three-drawer pedestal facing local +y (the seated user)."""
    x0, x1, yb, yf = -W / 2, W / 2, -D / 2, D / 2
    ped = min(420, W * 0.29)
    out = [("top", _slab(x0, x1, yb, yf, H - 42, H, 16, 6)),
           ("modesty", G._box(x0 + ped + 25, x1 - 30, yb + 35, yb + 55, 210, H - 42)),
           ("cable-tray", G._box(x0 + ped + 40, x1 - 35, yb + 65, yb + 145, H - 145, H - 125)),
           ("pedestal", G._box(x0 + 20, x0 + ped, yb + 28, yf - 40, 35, H - 42)),
           ("leg", G._box(x1 - 55, x1 - 25, yb + 35, yb + 65, 0, H - 42)),
           ("leg", G._box(x1 - 55, x1 - 25, yf - 70, yf - 40, 0, H - 42))]
    out += [("drawer", g) if n == "front" else ("pull", g) for n, g in
            _fronts(x0 + 24, x0 + ped - 4, yf - 24, 50, H - 52, "desk", drawers=True)]
    return out


# ------------------------------------------------------------------ joinery
GAP, FRONT_T = 3.0, 19.0


def _fronts(a, b, y1, z0, z1, kind, drawers=False, handle="bar", n_doors=None):
    """Door or drawer fronts over the span a..b (x), front face at y1, with 3 mm gaps and slim pulls."""
    out = []
    y0 = y1 - FRONT_T
    if drawers:
        n = 3
        hs = [(z1 - z0) * f for f in (0.25, 0.35, 0.40)]
        z = z1
        for h in hs:
            out.append(("front", G._box(a + GAP / 2, b - GAP / 2, y0, y1, z - h + GAP / 2, z - GAP / 2)))
            if handle:
                mz = z - min(45, h / 2)
                c = (a + b) / 2
                out.append(("handle", G._box(c - 80, c + 80, y1 - 1, y1 + 0, mz - 6, mz + 6)
                            if handle == "flush" else _pull(c - 80, c + 80, y1, mz)))
            z -= h
        return out
    n = n_doors or (2 if b - a > 650 else 1)
    w = (b - a) / n
    for k in range(n):
        da, db = a + k * w, a + (k + 1) * w
        out.append(("front", G._box(da + GAP / 2, db - GAP / 2, y0, y1, z0 + GAP / 2, z1 - GAP / 2)))
        if handle:
            hx = db - 45 if (k % 2 == 0 and n > 1) or n == 1 else da + 45
            hz = z1 - 90 if z1 - z0 < 1200 else z0 + 1000
            out.append(("handle", _vpull(hx, y1, hz)))
    return out


def _pull(x0, x1, y_face, z):
    """A slim horizontal bar pull, 10 mm high, standing on the front face. The front face is recessed by the
    worktop overhang / a 10-20 mm reveal, so the pull stays inside the piece's depth."""
    return G._box(x0, x1, y_face, y_face + 12, z - 5, z + 5)


def _vpull(x, y_face, z):
    return G._box(x - 5, x + 5, y_face, y_face + 12, z - 80, z + 80)


def _runs(it, W, D, H, island):
    """Kitchen base runs and the island: recessed plinth, carcasses, fronts, pulls, a 40 mm worktop overhanging
    25 mm; appliances as their fronts (hob glass, oven window, sink bowl and tap)."""
    x0, x1, yb, yf = -W / 2, W / 2, -D / 2, D / 2
    top = H if island else F3.COUNTER_TOP * 1000
    tall_wall = (not island) and H > (F3.COUNTER_TOP + 0.3) * 1000
    back = yb + (300 if island else 0)            # the island's seating side is a 300 mm knee recess
    face = yf - F3.OVERHANG * 1000                # carcass + fronts end here; the worktop overhangs to yf
    plinth = F3.PLINTH * 1000
    out = []
    mods = [(k, a * 1000, b * 1000) for k, a, b in F3._local_modules(it)]
    sink_holes = []
    for kind, a, b in mods:
        if kind in F3.TALL_MODULES and tall_wall:
            out.append((kind, G._box(a, b, yb, face - FRONT_T, 0, H)))
            if kind == "fridge":
                out += _fronts(a, b, face, plinth, H, kind, n_doors=1)
            elif kind == "oven":
                out += _fronts(a, b, face, plinth, 780, kind, drawers=True)
                out.append(("oven-glass", G._box(a + 20, b - 20, face - FRONT_T, face, 800, 1400)))
                out.append(("microwave-glass", G._box(a + 35, b - 35, face - FRONT_T, face, 1470, 1810)))
                out += _fronts(a, b, face, 1830, H, kind, n_doors=1)
            else:
                out += _fronts(a, b, face, plinth, H, kind, n_doors=1)
            continue
        out.append(("plinth", G._box(a, b, back + 50 if island else yb, face - 50, 0, plinth)))
        out.append((kind, G._box(a, b, back, face - FRONT_T, plinth, top - 40)))
        if kind == "dw" or kind == "washer":
            out += _fronts(a, b, face, plinth, top - 40, kind, n_doors=1, handle="bar")
        elif kind == "counter" and b - a <= 650:
            out += _fronts(a, b, face, plinth, top - 40, kind, drawers=True)
        else:
            out += _fronts(a, b, face, plinth, top - 40, kind)
        if kind == "hob":
            c = (a + b) / 2
            hw = min(290, (b - a) / 2 - 20)
            out.append(("hob", G._box(c - hw, c + hw, (yb + yf) / 2 - 250, (yb + yf) / 2 + 250, top, top + 6)))
        if kind == "sink":
            sink_holes.append((a, b))
        if tall_wall:
            wu0 = (F3.COUNTER_TOP + F3.SPLASH) * 1000
            out.append(("wall-units", G._box(a, b, yb, yb + 350 - FRONT_T, wu0, H)))
            out += [(n, g) for n, g in _fronts(a, b, yb + 350, wu0, H, "wall-units", handle=None)]
    # worktop, cut around each sink
    edges = [x0] + [v for a, b in sink_holes for v in (a + 60, b - 60)] + [x1]
    y_hole0, y_hole1 = (yb + yf) / 2 - 220, (yb + yf) / 2 + 220
    for k in range(0, len(edges), 2):
        out.append(("worktop", _slab(edges[k], edges[k + 1], yb, yf, top - 40, top, 3, 2)))
    for a, b in sink_holes:
        a2, b2 = a + 60, b - 60
        out.append(("worktop", G._box(a2, b2, yb, y_hole0, top - 40, top)))
        out.append(("worktop", G._box(a2, b2, y_hole1, yf, top - 40, top)))
        out.append(("sink", _bowl(a2, b2, y_hole0, y_hole1, top - 220, top - 1, 30, 12, 190, 30, 40)))
        tx, ty = (a + b) / 2, y_hole0 - 60
        out.append(("tap", G._cylinder(tx, ty, top, top + 330, 14, seg=16)))
        out.append(("tap", G._box(tx - 12, tx + 12, ty, ty + 200, top + 300, top + 330)))
    return out


def _cabinet(W, D, H, kind, floating=False):
    """Sideboard / TV unit: a carcass on a recessed plinth (or wall-hung), fronts with gaps and slim pulls."""
    x0, x1, yb, yf = -W / 2, W / 2, -D / 2, D / 2
    z0 = 100 if floating else F3.PLINTH * 1000
    out = []
    if not floating:
        out.append(("plinth", G._box(x0 + 50, x1 - 50, yb, yf - 50, 0, z0)))
    face = yf - 12                               # pulls stand on the fronts, inside the depth
    out.append(("carcass", _slab(x0, x1, yb, face - FRONT_T, z0, H, 6, 3)))
    n = max(2, round(W / 600))
    w = W / n
    for k in range(n):
        a, b = x0 + k * w, x0 + (k + 1) * w
        if floating:
            out += _fronts(a + 15, b - 15, face, z0 + 15, H - 15, kind, n_doors=1, handle=None)
        else:
            out += _fronts(a + 15, b - 15, face, z0 + 15, H - 15, kind, n_doors=1)
    return out


# ------------------------------------------------------------------ sanitaryware
def _washbasin(W, D, H):
    """A wall-hung vanity (two drawers) under a one-piece ceramic basin top, deck tap behind the bowl."""
    x0, x1, yb, yf = -W / 2, W / 2, -D / 2, D / 2
    out = [("vanity", G._box(x0 + 5, x1 - 5, yb, yf - FRONT_T - 10, 350, H - 130))]
    out += [(n if n != "front" else "vanity", g) for n, g in
            _fronts(x0 + 5, x1 - 5, yf - 10, 350, H - 130, "vanity", n_doors=1, handle=None)]
    out.append(("basin", _bowl(x0, x1, yb, yf, H - 130, H, 20, 45, 120, 110, 90)))
    out.append(("tap", G._cylinder(0, yb + 35, H, H + 170, 13, seg=16)))
    out.append(("tap", G._box(-10, 10, yb + 35, yb + 170, H + 150, H + 170)))
    return out


def _wc(W, D, H):
    """A wall-hung pan with a closed lid; the flush plate as `villa_furnish3d` places it."""
    x0, x1, yb, yf = -W / 2, W / 2, -D / 2, D / 2
    rings = [_ring(x0 + 60, x1 - 60, yb, yf - 140, 120, 90), _ring(x0 + 10, x1 - 10, yb, yf - 20, H - 70, 170),
             _ring(x0, x1, yb, yf, H - 25, 190)]
    out = [("pan", G._loft_rings(rings, 6)),
           ("seat", _slab(x0 + 5, x1 - 5, yb + 40, yf - 5, H - 25, H, 185, 10, seg=6)),
           ("flush-plate", G._box(-120, 120, yb, yb + 20, 950, 1120))]
    return out


def _bath(W, D, H):
    x0, x1, yb, yf = -W / 2, W / 2, -D / 2, D / 2
    # The bath's local rear edge is against the solid wall. A deck mixer sits
    # on that rim, with its spout extending over the bowl; all horizontal
    # vertices remain inside the checked footprint.
    return [("bath", _bowl(x0, x1, yb, yf, 0, H, 70, 70, H - 110, 170, 260, seg=6)),
            ("tap", G._cylinder(0, yb + 42, H, H + 155, 18, seg=20)),
            ("tap", G._box(-12, 12, yb + 42, yb + 235, H + 135, H + 155)),
            ("tap", G._cylinder(0, yb + 235, H + 108, H + 145, 12, seg=16)),
            ("tap", G._cylinder(85, yb + 42, H, H + 45, 15, seg=16))]


# ------------------------------------------------------------------ dispatch
def local_parts(it):
    """[(part, (verts_mm, tris))] in the piece's local frame, or None where no detailed builder exists."""
    t = it["type"]
    W, D, H = it["w"] * 1000, it["d"] * 1000, it["h"] * 1000
    if t in SEATS:
        return _sofa(W, D, H, SEATS[t], 120 if SEATS[t] == 1 else 160)
    if t == "coffee_table":
        return _coffee_table(W, D, H)
    if t == "dining_6x":
        return _dining_table(W, D, H)
    if t == "desk":
        return _desk(W, D, H)
    if t in ("base_run", "island"):
        return _runs(it, W, D, H, t == "island")
    if t == "sideboard":
        return _cabinet(W, D, H, t)
    if t == "tv_unit":
        parts = _cabinet(W, D, H, t, floating=True)
        return parts
    if t in ("washbasin",):
        return _washbasin(W, D, H)
    if t == "wc":
        return _wc(W, D, H)
    if t == "bath":
        return _bath(W, D, H)
    return None


ABOVE_H = {"flush-plate", "tap", "hob"}      # may stand above h (as villa_furnish3d.ABOVE allows the flush plate)


def to_world_point(it, x, y, z, level_z):
    cx, cy, r = it["cx"], it["cy"], it["rot"]
    if r == 0:
        wx, wy = cx + x, cy + y
    elif r == 180:
        wx, wy = cx - x, cy - y
    elif r == -90:
        wx, wy = cx + y, cy - x
    else:
        wx, wy = cx - y, cy + x
    return [wx, wy, level_z + z]


def world_parts(it, level_z, parts=None):
    """{part: [triangle, ...]} in world metres, each vertex inside the piece's footprint and height (+1 mm)."""
    parts = parts if parts is not None else local_parts(it)
    W, D, H = it["w"] * 1000, it["d"] * 1000, it["h"] * 1000
    out = {}
    for name, (verts, tris) in parts:
        for x, y, z in verts:
            if not (-W / 2 - 1 <= x <= W / 2 + 1 and -D / 2 - 1 <= y <= D / 2 + 1 and -1 <= z and
                    (z <= H + 1 or name in ABOVE_H or name == "screen")):
                raise EnvelopeError("%s %s: vertex %s outside %.0f x %.0f x %.0f" % (it["id"], name, (x, y, z), W, D, H))
        wv = [to_world_point(it, x / 1000.0, y / 1000.0, z / 1000.0, level_z) for x, y, z in verts]
        out.setdefault(name, []).extend([[wv[a], wv[b], wv[c]] for a, b, c in tris])
    return out


def seat_item(f):
    """A chair or stool from `villa_furnish3d.spec` (world boxes) as a pseudo piece: centre, size and the rotation
    whose front faces away from its back (chairs)."""
    boxes = dict(zip(f["parts"], f["boxes"]))
    s = boxes["seat"]
    cx, cy = (s[0] + s[3]) / 2, (s[1] + s[4]) / 2
    sx, sy = s[3] - s[0], s[4] - s[1]
    rot = 0
    if "back" in boxes:
        b = boxes["back"]
        bx, by = (b[0] + b[3]) / 2 - cx, (b[1] + b[4]) / 2 - cy
        if abs(by) >= abs(bx):
            rot = 0 if by < 0 else 180
        else:
            rot = -90 if bx < 0 else 90
    w, d = (sx, sy) if rot in (0, 180) else (sy, sx)
    return {"id": f["mark"], "cx": cx, "cy": cy, "w": w, "d": d, "rot": rot,
            "h": max(b[5] for b in f["boxes"]), "seat_h": s[5]}


def seat_parts(f, level_z):
    it = seat_item(f)
    if f["type"] == "chair":
        chair = _task_chair if f["mark"].split("#")[0] in {
            "study-desk", "study-adult-desk", "ka-desk-1", "ka-desk-2", "kb-desk"} else _chair
        parts = chair(it["w"] * 1000, it["d"] * 1000, seat=it["seat_h"] * 1000, back=it["h"] * 1000)
    else:
        parts = _stool(it["w"] * 1000, it["d"] * 1000, seat=it["seat_h"] * 1000)
    return world_parts(it, level_z, parts)
