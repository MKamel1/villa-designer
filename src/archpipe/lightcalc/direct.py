"""Analytic direct illuminance, luminance and obtrusive-light quantities from IES photometry.

This is the engine's independent closed-form path: it is used (a) as the
expected value against which the Radiance path is checked, and (b) for the
checks that need no inter-reflection (emergency path, obtrusive light,
luminance of a source toward an observer).

Frame convention (matches `photometry.Photometry` and Radiance `ies2rad`):
in the luminaire frame the nadir axis is -z, C0 is +x, C90 is +y. A placement
tilts the nadir axis onto `aim` and then spins about it; the rotation is built
the way `xform -rz spin -ry t -rz phi` applies it, so the analytic and Radiance
paths share one definition (a test aims a narrow beam and compares the two).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..photometry import Photometry

Vec = tuple[float, float, float]


def _norm(v: Vec) -> Vec:
    L = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
    if L == 0:
        raise ValueError("zero-length vector")
    return (v[0] / L, v[1] / L, v[2] / L)


def _dot(a: Vec, b: Vec) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _mat_vec(m, v):
    return tuple(sum(m[i][j] * v[j] for j in range(3)) for i in range(3))


def _mat_mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _rz(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return [[c, -s, 0], [s, c, 0], [0, 0, 1]]


def _ry(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return [[c, 0, s], [0, 1, 0], [-s, 0, c]]


def aim_angles(aim: Vec) -> tuple[float, float]:
    """(tilt from nadir, azimuth of the tilt) in degrees for an aim vector."""
    a = _norm(aim)
    tilt = math.degrees(math.acos(max(-1.0, min(1.0, -a[2]))))
    az = math.degrees(math.atan2(a[1], a[0])) if tilt > 1e-9 else 0.0
    return tilt, az


@dataclass(frozen=True)
class Placement:
    """One placed luminaire. Position in metres (world, z up)."""
    id: str
    photometry: Photometry
    position: Vec
    aim: Vec = (0.0, 0.0, -1.0)
    spin_deg: float = 0.0
    dim: float = 1.0                 # 0..1 output (linear dimming assumption)
    zone: str = "Z1"
    layer: str = "ambient"
    watts: float | None = None
    shr_max: float | None = None     # spacing-to-height limit from the luminaire's data
    meta: dict = field(default_factory=dict, compare=False, hash=False)

    def rotation(self):
        """3x3 matrix local->world: spin about local z, tilt onto aim."""
        tilt, az = aim_angles(self.aim)
        # xform: rotation order listed is applied to the object in that order.
        # tilt about y by -tilt moves the nadir (-z) toward +x for a positive tilt.
        return _mat_mul(_rz(az), _mat_mul(_ry(-tilt), _rz(self.spin_deg)))

    def local_direction(self, world_dir: Vec) -> Vec:
        r = self.rotation()
        rt = [[r[j][i] for j in range(3)] for i in range(3)]
        return _mat_vec(rt, world_dir)

    def intensity_toward(self, world_dir: Vec) -> float:
        """Candela toward a world direction (unit vector from the luminaire)."""
        d = _norm(world_dir)
        lx, ly, lz = self.local_direction(d)
        gamma = math.degrees(math.acos(max(-1.0, min(1.0, -lz))))
        c = math.degrees(math.atan2(ly, lx))
        return self.dim * self.photometry.intensity(gamma, c)


def direct_illuminance(placements: list[Placement], point: Vec, normal: Vec = (0, 0, 1),
                       *, mf: float = 1.0) -> float:
    """Direct illuminance (lx) at `point` on a surface with unit `normal`
    (inverse-square cosine law, point-source approximation)."""
    n = _norm(normal)
    total = 0.0
    for p in placements:
        v = (point[0] - p.position[0], point[1] - p.position[1], point[2] - p.position[2])
        d2 = _dot(v, v)
        if d2 == 0:
            continue
        d = math.sqrt(d2)
        u = (v[0] / d, v[1] / d, v[2] / d)             # luminaire -> point
        cos_inc = -_dot(u, n)                           # light arrives against the normal
        if cos_inc <= 0:
            continue
        total += p.intensity_toward(u) * cos_inc / d2
    return total * mf


def luminous_area_m2(ph: Photometry) -> float:
    """Plan luminous area from the IES opening (width x length); circular
    openings (negative dimensions in LM-63) are treated as discs."""
    w, l, _h = ph.luminous_dimensions_m()
    if w < 0 or l < 0:                   # LM-63: negative = circular/ellipsoidal
        return math.pi / 4.0 * abs(w) * abs(l if l != 0 else w)
    if l == 0:
        l = w
    return w * l


def luminance_toward(p: Placement, observer: Vec) -> tuple[float, float, float]:
    """(L cd/m2, projected area m2, distance m) of a downward-facing flat
    luminous opening toward an observer. L = I(direction) / A_projected, the
    definition used in CIE 117 for the mean luminance of the luminous part.
    The opening's face normal is the aim axis."""
    v = (observer[0] - p.position[0], observer[1] - p.position[1], observer[2] - p.position[2])
    d = math.sqrt(_dot(v, v))
    u = (v[0] / d, v[1] / d, v[2] / d)
    axis = _norm(p.aim)
    cos_t = _dot(u, axis)
    if cos_t <= 0:
        return 0.0, 0.0, d
    a_proj = luminous_area_m2(p.photometry) * cos_t
    if a_proj <= 0:
        raise ValueError(f"{p.id}: luminous opening has no area in the photometry; give one")
    return p.intensity_toward(u) / a_proj, a_proj, d


def upward_light_ratio(p: Placement, steps: int = 180, azimuths: int = 72) -> float:
    """ULR: share of the luminaire's emitted flux above the horizontal in its
    installed attitude (SLL Table 3.2 definition). Numerical integration."""
    up = 0.0
    tot = 0.0
    for i in range(steps):
        th = math.pi * (i + 0.5) / steps                 # polar angle from +z (up)
        for j in range(azimuths):
            ph = 2 * math.pi * (j + 0.5) / azimuths
            d = (math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th))
            w = math.sin(th) * (math.pi / steps) * (2 * math.pi / azimuths)
            f = p.intensity_toward(d) * w
            tot += f
            if d[2] > 0:
                up += f
    return up / tot if tot > 0 else 0.0
