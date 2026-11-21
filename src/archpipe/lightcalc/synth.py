"""Synthetic LM-63 photometry for reference cases (closed-form sources)."""
from __future__ import annotations

import math

from ..photometry import Photometry, parse


def _ies(name: str, verticals: list[float], candela: list[float], width: float = 0.0) -> str:
    lines = ["IESNA:LM-63-2002", f"[TEST] {name}", "TILT=NONE",
             f"1 -1 1 {len(verticals)} 1 1 2 {width} {width} 0", "1 1 10",
             " ".join(f"{v:g}" for v in verticals), "0",
             " ".join(f"{c:.6f}" for c in candela)]
    return "\n".join(lines) + "\n"


def isotropic_ies_text(candela: float) -> str:
    return _ies("isotropic point source", [0.0, 45.0, 90.0, 135.0, 180.0], [candela] * 5)


def cosine_ies_text(i0: float, step: float = 2.5) -> str:
    """I(theta) = i0 * cos(theta), theta from nadir, 0..90 deg (a 'diffuse' Lambertian point source)."""
    ang = [k * step for k in range(int(90 / step) + 1)]
    return _ies("cosine point source", ang, [i0 * math.cos(math.radians(a)) for a in ang])


def narrow_beam_ies_text(i0: float, half_deg: float = 10.0) -> str:
    """cos^n beam with half-intensity angle `half_deg`, downward hemisphere."""
    n = math.log(0.5) / math.log(math.cos(math.radians(half_deg)))
    ang = [float(a) for a in range(0, 91, 1)]
    return _ies("narrow beam", ang, [i0 * math.cos(math.radians(a)) ** n for a in ang])


def load_text(text: str, name: str) -> Photometry:
    return parse(text, name=name)
