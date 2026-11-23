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


def leaning_cushion(cx, cy, theta, u0, v0, z0, w_mm, h_mm, alpha_deg=12.0, yaw_deg=0.0, thick_mm=140):
    """One cushion stood on its edge at (u0, v0, z0 = lowest edge height), top leaning back by alpha."""
    xa, xb, ya, yb = -w_mm / 2, w_mm / 2, -h_mm / 2, h_mm / 2
    # An inflated pillow, not a slab (the first rings were a flat plateau with chamfers and the critic read them as rigid
    # boards): seven rings whose inset follows a circular profile, widest at mid-thickness, rounded at the seams.
    rings = []
    for t in (0.0, 0.14, 0.3, 0.5, 0.7, 0.86, 1.0):
        inset = 62.0 * (1.0 - math.sqrt(max(0.0, 1.0 - (2 * t - 1) ** 2)))
        rings.append((xa + inset, xb - inset, ya + inset * 0.9, yb - inset * 0.9, thick_mm * t, 55.0))
    verts, tris = FG._loft_rings(rings, 8)
    al = math.radians(alpha_deg)
    ca, sa = math.cos(al), math.sin(al)

    def place(x, y, z):
        t, s = (y) / 1000.0, (z - thick_mm / 2) / 1000.0
        du, dv = _rot(-x / 1000.0, -sa * t + ca * s, yaw_deg)          # -x keeps the basis right-handed
        zz = z0 + ca * (t + h_mm / 2000.0) + sa * s
        wu, wv = _rot(u0 + du, v0 + dv, theta)
        return [cx + wu, cy + wv, zz]
    return _world(verts, tris, place)


def folded_throw(cx, cy, theta, u0, v0, z0, w_mm, l_mm, yaw_deg=0.0, thick_mm=70):
    """A throw folded in three and laid flat on the seat."""
    fw, fl = w_mm / 3.0, l_mm / 3.0
    xa, xb, ya, yb = -fw / 2, fw / 2, -fl / 2, fl / 2
    rings = [(xa + 12, xb - 12, ya + 12, yb - 12, 0, 22), (xa, xb, ya, yb, 14, 30),
             (xa, xb, ya, yb, thick_mm - 14, 30), (xa + 12, xb - 12, ya + 12, yb - 12, thick_mm, 22)]
    verts, tris = FG._loft_rings(rings, 8)

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
