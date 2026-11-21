"""V10: reproduce a luminaire's published photometric figures from its own photometric file.

Two routes per published point, never sharing code with each other:
  engine      archpipe.lightcalc.direct (the code that sizes the villa lighting)
  independent a minimal IES reader and the inverse-square law written here
A point passes only when BOTH routes are within tolerance of the published value.
A product with no published point is `not_evaluated`, never `pass` (docs/quality/LANES.md rule 4).
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

from archpipe import photometry as ph
from archpipe.lightcalc.direct import Placement, direct_illuminance

LUMEN_TOL = 0.02     # V1/V10: integrated vs stated lumens
POINT_TOL = 0.05     # V10: every published point


# ------------------------------------------------------------ independent route
@dataclass(frozen=True)
class Table:
    gamma: tuple
    c: tuple
    cd: tuple            # cd[j][i]: C plane j, gamma i; absolute candela
    lumens_stated: float  # <0 in the file means absolute photometry


def read_ies(text: str) -> Table:
    """Minimal LM-63 type C reader (the type every product file here uses)."""
    lines = text.splitlines()
    i = next(k for k, s in enumerate(lines) if s.upper().startswith("TILT="))
    if lines[i].strip().upper() != "TILT=NONE":
        raise ValueError("TILT other than NONE is not supported")
    tok = " ".join(lines[i + 1:]).split()
    n, lumens, mult, nv, nh, ptype = int(tok[0]), float(tok[1]), float(tok[2]), int(tok[3]), int(tok[4]), int(tok[5])
    if ptype != 1:
        raise ValueError("only photometric type C")
    pos = 13  # 10 header numbers + ballast factor, ballast-lamp factor, watts
    gam = tuple(float(x) for x in tok[pos:pos + nv]); pos += nv
    cs = tuple(float(x) for x in tok[pos:pos + nh]); pos += nh
    cd = tuple(tuple(float(x) * mult for x in tok[pos + j * nv: pos + (j + 1) * nv]) for j in range(nh))
    return Table(gam, cs, cd, lumens * n if lumens > 0 else lumens)


def _plane_mean(t: Table, i: int) -> float:
    """Mean candela over azimuth at gamma index i, for the symmetry the C list implies."""
    if len(t.c) == 1:
        return t.cd[0][i]
    span = t.c[-1] - t.c[0]
    w = [(t.c[(j + 1) % len(t.c)] - t.c[j]) % 360 or 0 for j in range(len(t.c))] if span >= 359.999 else None
    if w is None:      # quadrant/half symmetry: plain trapezoid over the listed span
        a = sum((t.c[j + 1] - t.c[j]) * (t.cd[j][i] + t.cd[j + 1][i]) / 2 for j in range(len(t.c) - 1))
        return a / span
    a = sum((t.c[j + 1] - t.c[j]) * (t.cd[j][i] + t.cd[j + 1][i]) / 2 for j in range(len(t.c) - 1))
    return a / span


def flux_independent(t: Table) -> float:
    """Lumens = 2*pi * integral of mean-azimuth candela * sin(gamma) d(gamma), trapezoid on the file's own grid."""
    m = [_plane_mean(t, i) for i in range(len(t.gamma))]
    tot = 0.0
    for i in range(len(t.gamma) - 1):
        g0, g1 = math.radians(t.gamma[i]), math.radians(t.gamma[i + 1])
        # exact integral of sin over the cell, intensity linear in gamma
        s0, s1 = math.sin(g0), math.sin(g1)
        mid = (m[i] + m[i + 1]) / 2
        tot += mid * (math.cos(g0) - math.cos(g1))
    return 2 * math.pi * tot


def beam_full_angle_independent(t: Table) -> float:
    """Full angle (deg) at 50 % of the nadir intensity, mean of C0 and C90 planes (CIE/IES 'beam angle')."""
    def half(plane: int) -> float:
        row = t.cd[plane]
        i0 = row[0]
        for k in range(1, len(row)):
            if row[k] <= 0.5 * i0:
                a, b = row[k - 1], row[k]
                return t.gamma[k - 1] + (t.gamma[k] - t.gamma[k - 1]) * (a - 0.5 * i0) / (a - b)
        return t.gamma[-1]
    planes = [0]
    if len(t.c) > 1:
        planes.append(min(range(len(t.c)), key=lambda j: abs(t.c[j] - 90)))
    return 2 * sum(half(p) for p in planes) / len(planes)


# ------------------------------------------------------------------ published points
@dataclass(frozen=True)
class Point:
    """A figure the manufacturer publishes. kind: lux_axis (value lx at distance_m on axis),
    beam_diameter (m at distance_m, 50 % of axis lux), imax (cd), lumens (lm), beam_angle (deg)."""
    kind: str
    value: float
    distance_m: float | None = None
    source: str = ""


def _engine_lux_axis(p: ph.Photometry, d: float) -> float:
    return direct_illuminance([Placement("v10", p, (0.0, 0.0, d))], (0.0, 0.0, 0.0))


def reproduce(point: Point, ies_text: str, p: ph.Photometry, tol: float = POINT_TOL) -> dict:
    t = read_ies(ies_text)
    if point.kind == "lux_axis":
        eng, ind = _engine_lux_axis(p, point.distance_m), t.cd[0][0] / point.distance_m ** 2
    elif point.kind == "beam_diameter":
        eng = 2 * point.distance_m * math.tan(math.radians(_engine_beam(p) / 2))
        ind = 2 * point.distance_m * math.tan(math.radians(beam_full_angle_independent(t) / 2))
    elif point.kind == "imax":
        eng, ind = p.peak_candela, max(max(r) for r in t.cd)
    elif point.kind == "lumens":
        eng, ind = p.integrated_flux(), flux_independent(t)
    elif point.kind == "beam_angle":
        eng, ind = _engine_beam(p), beam_full_angle_independent(t)
    else:
        raise ValueError(point.kind)
    err = [abs(x - point.value) / point.value for x in (eng, ind)]
    return dict(kind=point.kind, distance_m=point.distance_m, published=point.value, engine=round(eng, 4),
                independent=round(ind, 4), worst_error=round(max(err), 4), tolerance=tol,
                status="pass" if max(err) <= tol else "fail", source=point.source)


def _engine_beam(p: ph.Photometry) -> float:
    i0 = p.intensity(0, 0)
    halves = []
    for h in (0.0, 90.0):
        g = 0.0
        while g < 90.0 and p.intensity(g, h) > 0.5 * i0:
            g += 0.05
        halves.append(g)
    return 2 * sum(halves) / 2


def check_lumens(ies_text: str, stated: float, tol: float = LUMEN_TOL) -> dict:
    """File lumens integrated two ways vs one stated figure (datasheet or product name)."""
    t = read_ies(ies_text)
    p = ph.parse(ies_text)
    a, b = flux_independent(t), p.integrated_flux()
    err = max(abs(a - stated), abs(b - stated)) / stated
    return dict(stated=stated, independent=round(a, 1), archpipe=round(b, 1), worst_error=round(err, 4),
                tolerance=tol, status="pass" if err <= tol else "fail")


def check_product(ies_path: Path, *, stated_lumens: float | None, points: list[Point]) -> dict:
    text = Path(ies_path).read_text(encoding="latin-1")
    p = ph.parse(text)
    out = {"lumens": check_lumens(text, stated_lumens) if stated_lumens else
           dict(status="not_evaluated", reason="no datasheet lumen figure")}
    out["points"] = [reproduce(pt, text, p) for pt in points]
    states = [out["lumens"]["status"]] + [r["status"] for r in out["points"]]
    out["status"] = ("fail" if "fail" in states else "not_evaluated" if not points else "pass")
    return out
