"""Quantity arithmetic from the design model (millimetres in, SI out). No IFC dependency.

One implementation feeds both the IFC Qto sets and the QS take-off, so the two cannot disagree by construction;
`validate.py` and the take-off reconciliation then check them against the geometry independently.
"""
from __future__ import annotations

import math

from ..contracts import DesignElement
from . import common as C


def signed_area(pts) -> float:
    s = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        s += x0 * y1 - x1 * y0
    return s / 2.0


def perimeter(pts) -> float:
    return sum(math.dist(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts)))


def opening_area_mm2(op: DesignElement, wall_h: float) -> float:
    """Wall area removed by one hosted door/window (clipped to the wall height)."""
    p = op.params
    sill = float(p.get("sill_mm") or 0.0) if op.kind == "window" else 0.0
    return float(p["width_mm"]) * max(0.0, min(float(p["height_mm"]), wall_h - sill))


def hosted(elements: list[DesignElement]) -> dict[str, list[DesignElement]]:
    out: dict[str, list[DesignElement]] = {}
    for e in elements:
        if e.kind in ("door", "window"):
            out.setdefault(e.host, []).append(e)
    return out


def wall_q(w: DesignElement, ops: list[DesignElement]) -> dict:
    """Length, Width, Height (mm); areas m2; volumes m3. Side area = one face; openings deducted for the Net values."""
    L, t, h = C.wall_length(w), float(w.params["thickness_mm"]), float(w.params["height_mm"])
    gross = L * h
    net = gross - sum(opening_area_mm2(o, h) for o in ops)
    return dict(Length=L, Width=t, Height=h, GrossSideArea=gross / 1e6, NetSideArea=net / 1e6,
                GrossVolume=gross * t / 1e9, NetVolume=net * t / 1e9, OpeningArea=(gross - net) / 1e6)


def slab_q(e: DesignElement) -> dict:
    """GrossArea = plan area of the outline (a sloped ramp: its plan footprint); NetArea minus holes; Depth = thickness."""
    p = e.params
    t = float(p.get("thickness_mm") or e.size[2])
    if p.get("polygon_mm"):
        poly = [tuple(map(float, v)) for v in p["polygon_mm"]]
        gross = abs(signed_area(poly))
        holes = sum(abs(signed_area([tuple(map(float, v)) for v in h])) for h in p.get("holes_mm") or [])
        per = perimeter(poly)
        net = gross - holes
        vol = net * t
        L, W = (max(v[i] for v in poly) - min(v[i] for v in poly) for i in (0, 1))
    else:
        L, W = e.size[0], e.size[1]
        gross = net = L * W
        per = 2 * (L + W)
        if p.get("profile_xz_mm"):                       # sloped slab: volume from the section, plan area from the footprint
            top = [(float(x), float(z)) for x, z in p["profile_xz_mm"]]
            vol = abs(signed_area(top + [(x, z - t) for x, z in reversed(top)])) * W
        else:
            vol = gross * t
    return dict(Length=L, Width=W, Depth=t, Perimeter=per, GrossArea=gross / 1e6, NetArea=net / 1e6,
                GrossVolume=(gross * t if not p.get("profile_xz_mm") else vol) / 1e9, NetVolume=vol / 1e9)
