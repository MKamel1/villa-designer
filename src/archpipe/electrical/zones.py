"""Bathroom zones (EA2), IEC 60364-7-701 geometry as summarised by the SELECT/BS 7671 s.701 guide.

Zone 0: inside the bath/shower basin. Zone 1: above the basin to 2.25 m (or the highest fixed shower
head). Zone 2: 0.6 m beyond zone 1, 2.25 m high. A shower without a basin has zone 0 height 0.10 m and
zone 1 within 1.20 m of the fixed outlet, and no zone 2. Fixed partitions are ignored (conservative).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .model import Furniture, Rect, Room

ZONE_H_MM = 2250.0
Z2_EXTENT_MM = 600.0
NOBASIN_Z0_H_MM = 100.0
NOBASIN_Z1_R_MM = 1200.0
UK_SOCKET_EXCLUSION_MM = 2500.0
CARDS = ("EL-701-ZONE0", "EL-701-ZONE1", "EL-701-ZONE2")


@dataclass
class WetArea:
    """One bath or shower in a bathroom."""
    rect: Rect
    has_basin: bool = True
    outlet_xy: tuple[float, float] | None = None   # fixed water outlet (no-basin showers)
    head_h_mm: float = ZONE_H_MM                   # highest fixed shower head height
    rim_mm: float = 150.0                          # height of the basin rim: inside the footprint below it is zone 0

    @property
    def zone_h(self) -> float:
        return max(ZONE_H_MM, self.head_h_mm)


def wet_areas(room: Room, furniture: list[Furniture]) -> list[WetArea]:
    out = []
    for f in furniture:
        if f.room == room.id and f.kind in ("bath", "shower"):
            p = f.params
            out.append(WetArea(f.rect, p.get("has_basin", True), tuple(p["outlet_xy"]) if "outlet_xy" in p else None,
                               p.get("head_h_mm", ZONE_H_MM), p.get("rim_mm", 550.0 if f.kind == "bath" else 150.0)))
    return out


def _dist_to_rect(x: float, y: float, r: Rect) -> float:
    dx = max(r[0] - x, 0.0, x - r[2])
    dy = max(r[1] - y, 0.0, y - r[3])
    return math.hypot(dx, dy)


def _zone_basin(x, y, z, wet):
    d = _dist_to_rect(x, y, wet.rect)
    if z > wet.zone_h:
        return None
    if d == 0.0:
        # inside the basin footprint: zone 0 is the basin interior (below the rim), zone 1 above it
        return 0 if z <= wet.rim_mm else 1
    if d <= Z2_EXTENT_MM:
        return 2
    return None


def _zone_nobasin(x, y, z, wet):
    ox, oy = wet.outlet_xy if wet.outlet_xy else ((wet.rect[0] + wet.rect[2]) / 2, (wet.rect[1] + wet.rect[3]) / 2)
    d = math.hypot(x - ox, y - oy)
    if z > wet.zone_h:
        return None
    if d <= NOBASIN_Z1_R_MM:
        return 0 if z <= NOBASIN_Z0_H_MM else 1
    return None


def zone_at(x: float, y: float, z: float, wets: list[WetArea]) -> int | None:
    """Lowest-numbered (most restrictive) zone any wet area puts the point in."""
    zs = [(_zone_basin if w.has_basin else _zone_nobasin)(x, y, z, w) for w in wets]
    zs = [q for q in zs if q is not None]
    return min(zs) if zs else None


def dist_to_zone1_mm(x: float, y: float, wets: list[WetArea]) -> float:
    """Horizontal distance to the boundary of zone 1 (0 inside)."""
    best = 1e12
    for w in wets:
        if w.has_basin:
            best = min(best, _dist_to_rect(x, y, w.rect))
        else:
            ox, oy = w.outlet_xy if w.outlet_xy else ((w.rect[0] + w.rect[2]) / 2, (w.rect[1] + w.rect[3]) / 2)
            best = min(best, max(0.0, math.hypot(x - ox, y - oy) - NOBASIN_Z1_R_MM))
    return best
