"""Scatter cushions and a folded throw on a seat, from the client's cushion schedule (2026-11-23).

Pure geometry (no Blender): world-space triangles for lofted cushions leaning on a sofa back, sized from each scheduled
product's format (SANELA 500 x 500 mm, LAGERPOPPEL 400 x 580 mm, MYRULL throw 1300 x 1700 mm folded in three).
Local frame as archpipe.furniture: u along the width, v from the back (-) to the front (+); theta is the generator's
anticlockwise rotation (villa_render.generator_rotation).
"""
from __future__ import annotations

import math

from .. import furniture as FG


def _rot(du, dv, theta_deg):
    c, s = math.cos(math.radians(theta_deg)), math.sin(math.radians(theta_deg))
    return du * c - dv * s, du * s + dv * c


def _world(verts_mm, tris, place):
    return [[place(*verts_mm[i]) for i in t] for t in tris]


def lumbar(w_mm, l_mm):
    """(width, height) of a scheduled cushion as it stands: an oblong one (400 x 580 mm LAGERPOPPEL) lies landscape as a lumbar
    cushion; a 580 mm portrait one stood 10 cm proud of the 0.89 m library sofa back (v34, 2026-11-23)."""
    return (max(w_mm, l_mm), min(w_mm, l_mm))


def _grid_shell(w_mm, l_mm, top, bottom, n=30, m=30):
    """Closed shell over a w x l (mm) rectangle: `top(x, y)` and `bottom(x, y)` are heights (mm) at point (x, y).
    Grid lines cluster toward the rim (cosine spacing) so a steep rolled edge is resolved. Returns (verts_mm, tris)."""
    xs = [w_mm / 2 * math.sin(math.pi / 2 * (2 * i / (n - 1) - 1)) for i in range(n)]
    ys = [l_mm / 2 * math.sin(math.pi / 2 * (2 * j / (m - 1) - 1)) for j in range(m)]
    verts, tris = [], []
    for z in (top, bottom):
        for x in xs:
            for y in ys:
                verts.append((x, y, z(x, y)))
    idx = lambda layer, i, j: layer * n * m + i * m + j
    for i in range(n - 1):
        for j in range(m - 1):
            a, b, c, d = idx(0, i, j), idx(0, i + 1, j), idx(0, i + 1, j + 1), idx(0, i, j + 1)
            tris += [(a, b, c), (a, c, d)]
            a, b, c, d = idx(1, i, j), idx(1, i + 1, j), idx(1, i + 1, j + 1), idx(1, i, j + 1)
            tris += [(a, c, b), (a, d, c)]
    rim = [(i, 0) for i in range(n - 1)] + [(n - 1, j) for j in range(m - 1)] + \
          [(i, m - 1) for i in range(n - 1, 0, -1)] + [(0, j) for j in range(m - 1, 0, -1)]
    for k, (i, j) in enumerate(rim):
        i2, j2 = rim[(k + 1) % len(rim)]
        a, b, c, d = idx(0, i, j), idx(0, i2, j2), idx(1, i2, j2), idx(1, i, j)
        tris += [(a, d, c), (a, c, b)]
    return verts, tris


def _noise(seed):
    """Smooth deterministic wrinkle field f(x_mm, y_mm) in [-1, 1] (sum of a few sines, no RNG state)."""
    r = [((seed * 2654435761 + k * 40503) % 1000) / 1000.0 for k in range(12)]
    waves = [(0.011 + 0.010 * r[0], 0.006 + 0.012 * r[1], 6.28 * r[2]), (0.007 + 0.012 * r[3], -0.012 + 0.010 * r[4], 6.28 * r[5]),
             (0.019 + 0.012 * r[6], 0.014 + 0.010 * r[7], 6.28 * r[8])]
    return lambda x, y: sum(math.sin(a * x + b * y + ph) for a, b, ph in waves) / len(waves) * 1.3


def pillow(w_mm, h_mm, thick_mm=140, seed=1):
    """An inflated scatter cushion: a closed shell whose thickness follows a rounded-rectangle profile (widest at the middle,
    rolling to the seam), pinched at the corners, with a soft centre dimple and small wrinkles. Replaces the seven-ring loft,
    whose flat plateau read as a board from the front. Local frame: x width, y height, z thickness from 0."""
    a, b = w_mm / 2, h_mm / 2
    wr = _noise(seed)

    def half(x, y):
        u, v = abs(x) / a, abs(y) / b
        prof = max(0.0, 1 - u ** 2.0) ** 0.5 * max(0.0, 1 - v ** 2.0) ** 0.5
        corner = 1 - 0.6 * (u * v) ** 1.5                                   # corners are pinched flat by the seam
        dimple = 1 - 0.28 * math.exp(-(u * u + v * v) / 0.25)              # the fill settles in the middle
        return thick_mm / 2 * prof * corner * dimple + 0.8 + 5.0 * wr(x, y) * prof
    c = thick_mm / 2

    def bow(x, y):                                                         # the cover bows: corners fall away from the crown
        return -26.0 * ((x / a) ** 2 * 0.6 + (y / b) ** 2 * 0.4) + 6.0 * wr(y, x)
    return _grid_shell(w_mm, h_mm, lambda x, y: c + half(x, y) + bow(x, y), lambda x, y: c - half(x, y) * 0.96 + bow(x, y))


def leaning_cushion(cx, cy, theta, u0, v0, z0, w_mm, h_mm, alpha_deg=12.0, yaw_deg=0.0, thick_mm=140):
    """One cushion stood on its edge at (u0, v0, z0 = lowest edge height), top leaning back by alpha."""
    verts, tris = pillow(w_mm, h_mm, thick_mm, seed=int(w_mm + 3 * h_mm + 1000 * u0 + 7 * alpha_deg))
    al = math.radians(alpha_deg)
    ca, sa = math.cos(al), math.sin(al)

    def place(x, y, z):
        t, s = (y + h_mm / 2) / 1000.0 - h_mm / 2000.0, (z - thick_mm / 2) / 1000.0
        du, dv = _rot(-x / 1000.0, -sa * t + ca * s, yaw_deg)          # -x keeps the basis right-handed
        zz = z0 + ca * (t + h_mm / 2000.0) + sa * s
        wu, wv = _rot(u0 + du, v0 + dv, theta)
        return [cx + wu, cy + wv, zz]
    return _world(verts, tris, place)


def draped_throw(w_mm, l_mm, seed=3):
    """A throw as loose cloth: one end lies flat on the seat, the rest bunches into soft ridges and one corner lifts and rolls.
    Thickness 14 mm; the cloth never goes below its z = 0 contact plane. Local frame as `pillow`."""
    a, b = w_mm / 2, l_mm / 2
    wr = _noise(seed)

    def top(x, y):
        u, v = x / a, y / b
        edge = max(0.0, 1 - max(abs(u), abs(v)) ** 4)                       # the rim rolls down onto the seat
        rim = math.sqrt(max(0.0, 1 - max(abs(u), abs(v)) ** 8))             # thick folded edge, rounded off
        ridge = 0.55 + 0.45 * math.sin(7.0 * (v + 0.3 * u) + 0.8)           # two or three soft folds across the length
        bunch = 40.0 * math.exp(-((v - 0.1) / 0.7) ** 2) * ridge
        return 1.5 + 26.0 * rim + edge * (bunch + 8.0 * wr(x, y))
    return _grid_shell(w_mm, l_mm, top, lambda x, y: 0.0, n=34, m=40)


def folded_throw(cx, cy, theta, u0, v0, z0, w_mm, l_mm, yaw_deg=0.0, thick_mm=70):
    """The scheduled throw (w x l mm) folded in three to a third of its length, then loosely draped: see `draped_throw`."""
    verts, tris = draped_throw(w_mm / 3.0 * 0.95, l_mm / 3.0 * 1.0, seed=int(w_mm + l_mm))

    def place(x, y, z):
        du, dv = _rot(x / 1000.0, y / 1000.0, yaw_deg)
        wu, wv = _rot(u0 + du, v0 + dv, theta)
        return [cx + wu, cy + wv, z0 + z / 1000.0]
    return _world(verts, tris, place)


def seat_dressing(item_xy, theta, width_m, depth_m, seat_top_m, back_v_m, arm_m, cushions, throw, throw_side=1,
                  alpha0=10.0, throw_v=None, throw_yaw=6.0):
    """[(kind, index, faces)] for one seat. `cushions` is [(w_mm, h_mm)], `throw` (w_mm, l_mm) or None.

    Cushions spread over the seat between the arms (outermost against the arms); the throw lies on the end seat.
    """
    cx, cy = item_xy
    inner = width_m / 2.0 - arm_m - 0.03
    out = []
    n = len(cushions)
    for k, (w_mm, h_mm) in enumerate(cushions):
        frac = 0.0 if n == 1 else (k / (n - 1)) * 2 - 1
        u0 = frac * (inner - w_mm / 2000.0)
        alpha = alpha0 + 4 * (k % 2)
        yaw = (-5, 4, -3)[k % 3]
        z0 = seat_top_m - 0.04      # sunk 40 mm into the seat cushion so the top stays near the back height
        v0 = back_v_m + 0.05 + 0.02 * (k % 2)
        out.append(("cushion", k, leaning_cushion(cx, cy, theta, u0, v0, z0, w_mm, h_mm, alpha, yaw)))
    if throw:
        fw, fl = throw[0] / 3.0, throw[1] / 3.0
        u0 = throw_side * (inner - fw / 2000.0 - 0.02)
        tv = back_v_m + 0.50 + fl / 2000.0 if throw_v is None else throw_v
        out.append(("throw", 0, folded_throw(cx, cy, theta, u0, tv, seat_top_m - 0.01,
                                              throw[0], throw[1], yaw_deg=(throw_yaw if throw_v is not None else 6) * throw_side)))
    return out
