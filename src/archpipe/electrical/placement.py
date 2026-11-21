"""Device placement rules per room type (EA1, policy cards) and device validation (EA2 zones, switch heights).

Rules are ours (status "policy", EL-POL-PLACEMENT) until an engineer's marked-up rooms are available for a
recall test. Bathroom zone rules are geometric (zones.py, IEC 60364-7-701 std).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import zones
from .model import Door, House, Room

SWITCH_Z = 1150.0           # within the 1.1-1.2 m band
SWITCH_BAND = (1100.0, 1200.0)
SWITCH_OFFSET_MM = 150.0    # from the door frame on the latch side
SOCKET_Z = 300.0
BEDSIDE_Z = 450.0
WORKTOP_SOCKET_Z = 1100.0
TV_Z = 400.0
AC_Z = 2200.0
BEDSIDE_OFFSET_MM = 300.0
WORKTOP_PITCH_MM = 1200.0
WALL_SOCKET_PITCH_MM = 3000.0

NON_SOCKET_KINDS = {"switch", "fcu", "isolator_ac", "cooker_unit", "data", "tv_sat", "shaver_unit", "socket_selv"}
SOCKET_KINDS = {"socket", "socket_usb"}


@dataclass
class Device:
    id: str
    kind: str                 # socket | socket_usb | switch | fcu | isolator_ac | cooker_unit | data | tv_sat | shaver_unit | socket_selv
    room: str
    x: float
    y: float
    z: float
    rule: str = ""
    serves: str = ""          # equipment id for dedicated spurs/isolators
    params: dict = field(default_factory=dict)


# ---- geometry helpers ------------------------------------------------------------------------
def _wall_point(r: Room, wall: str, along: float, inset: float = 0.0) -> tuple[float, float]:
    x0, y0, x1, y1 = r.rect
    if wall == "N":
        return (x0 + along, y1 - inset)
    if wall == "S":
        return (x0 + along, y0 + inset)
    if wall == "W":
        return (x0 + inset, y0 + along)
    return (x1 - inset, y0 + along)


def _wall_len(r: Room, wall: str) -> float:
    x0, y0, x1, y1 = r.rect
    return (x1 - x0) if wall in "NS" else (y1 - y0)


def switch_for_door(r: Room, d: Door) -> tuple[float, float]:
    """Switch inside the room on the latch side (opposite the hinge), 150 mm from the frame."""
    latch_end = d.offset_mm + d.width_mm if d.hinge == "start" else d.offset_mm
    direction = 1.0 if d.hinge == "start" else -1.0
    along = latch_end + direction * SWITCH_OFFSET_MM
    return _wall_point(r, d.wall, along, inset=0.0)


def _door_spans(h: House, r: Room) -> dict[str, list[tuple[float, float]]]:
    sp: dict[str, list[tuple[float, float]]] = {"N": [], "E": [], "S": [], "W": []}
    for d in h.doors:
        if d.room == r.id:
            sp[d.wall].append((d.offset_mm - 100.0, d.offset_mm + d.width_mm + 100.0))
    return sp


def _free_along(spans, a: float, b: float) -> bool:
    return all(b <= s0 or a >= s1 for s0, s1 in spans)


def _rect_edge_on_wall(rect, wall) -> tuple[float, float]:
    x0, y0, x1, y1 = rect
    return (x0, x1) if wall in "NS" else (y0, y1)


def place_devices(h: House) -> list[Device]:
    devs: list[Device] = []
    n = [0]

    def add(kind, room, x, y, z, rule, serves="", **params):
        n[0] += 1
        devs.append(Device(f"{kind[:3].upper()}-{room}-{n[0]:03d}", kind, room, x, y, z, rule, serves, params))

    for r in h.rooms:
        wets = zones.wet_areas(r, h.furniture) if r.kind == "bathroom" else []
        furn = [f for f in h.furniture if f.room == r.id]
        spans = _door_spans(h, r)
        # one switch per door at the latch side
        for d in h.doors:
            if d.room == r.id:
                x, y = switch_for_door(r, d)
                add("switch", r.id, x, y, SWITCH_Z, "EA1-switch-latch-side", door=d.id)
        if r.kind == "bathroom":
            _place_bathroom(h, r, wets, add)
            continue
        # equipment points (AC isolator high on the longest free wall, FCU/cooker unit spurs)
        for e in h.equipment:
            if e.room != r.id:
                continue
            if e.kind == "ac":
                wall = max("NESW", key=lambda w: _wall_len(r, w))
                x, y = _wall_point(r, wall, _wall_len(r, wall) / 2)
                add("isolator_ac", r.id, x, y, AC_Z, "EA1-ac-point", serves=e.id)
        # furniture driven points
        for f in furn:
            wall = f.wall or "N"
            if f.kind == "bed":
                lo, hi = _rect_edge_on_wall(f.rect, wall)
                for a in (lo - BEDSIDE_OFFSET_MM, hi + BEDSIDE_OFFSET_MM):
                    x, y = _wall_point(r, wall, a - (r.rect[0] if wall in "NS" else r.rect[1]))
                    add("socket", r.id, x, y, BEDSIDE_Z, "EA1-bedside-both-sides", furniture=f.id)
            elif f.kind == "desk":
                lo, hi = _rect_edge_on_wall(f.rect, wall)
                mid = (lo + hi) / 2 - (r.rect[0] if wall in "NS" else r.rect[1])
                for k in (-1, 1):
                    x, y = _wall_point(r, wall, mid + k * 300.0)
                    add("socket", r.id, x, y, SOCKET_Z + 800.0, "EA1-desk-cluster", furniture=f.id)
                    add("data", r.id, x, y, SOCKET_Z + 800.0, "EA1-desk-cluster", furniture=f.id)
            elif f.kind == "tv":
                lo, hi = _rect_edge_on_wall(f.rect, wall)
                mid = (lo + hi) / 2 - (r.rect[0] if wall in "NS" else r.rect[1])
                for k, kind in ((-1, "socket"), (0, "socket"), (1, "tv_sat"), (2, "data")):
                    x, y = _wall_point(r, wall, mid + (k - 0.5) * 200.0)
                    add(kind, r.id, x, y, TV_Z, "EA1-tv-cluster", furniture=f.id)
            elif f.kind == "sofa":
                lo, hi = _rect_edge_on_wall(f.rect, wall)
                off = (r.rect[0] if wall in "NS" else r.rect[1])
                for a in (lo - BEDSIDE_OFFSET_MM, hi + BEDSIDE_OFFSET_MM):
                    x, y = _wall_point(r, wall, a - off)
                    add("socket", r.id, x, y, SOCKET_Z, "EA1-sofa-ends", furniture=f.id)
            elif f.kind == "worktop":
                lo, hi = _rect_edge_on_wall(f.rect, wall)
                off = (r.rect[0] if wall in "NS" else r.rect[1])
                length = hi - lo
                cnt = max(1, math.ceil(length / WORKTOP_PITCH_MM))
                pitch = length / cnt
                for i in range(cnt):
                    x, y = _wall_point(r, wall, lo - off + pitch * (i + 0.5))
                    add("socket", r.id, x, y, WORKTOP_SOCKET_Z, "EA1-worktop-pitch", furniture=f.id, zone="worktop")
            elif f.kind in ("hob", "oven"):
                x, y = _wall_point(r, wall, (sum(_rect_edge_on_wall(f.rect, wall)) / 2) - (r.rect[0] if wall in "NS" else r.rect[1]) + 700.0)
                for e in h.equipment:
                    if e.room == r.id and e.kind == "cooker":
                        add("cooker_unit", r.id, x, y, WORKTOP_SOCKET_Z, "EA1-dedicated-cooker", serves=e.id)
                        break
            elif f.kind in ("washer", "dishwasher", "fridge"):
                x, y = _wall_point(r, wall, (sum(_rect_edge_on_wall(f.rect, wall)) / 2) - (r.rect[0] if wall in "NS" else r.rect[1]))
                eq = next((e.id for e in h.equipment if e.room == r.id and e.kind == f.kind), "")
                add("fcu" if eq else "socket", r.id, x, y, 600.0, "EA1-dedicated-appliance", serves=eq, furniture=f.id)
        # general sockets: at least one double per free wall stretch, pitch <= 3 m
        for wall in "NESW":
            L = _wall_len(r, wall)
            cnt = max(1, math.ceil(L / WALL_SOCKET_PITCH_MM))
            pitch = L / cnt
            for i in range(cnt):
                a = pitch * (i + 0.5)
                if not _free_along(spans[wall], a - 150, a + 150):
                    continue
                x, y = _wall_point(r, wall, a)
                # skip when a furniture-driven socket already stands within 600 mm
                if any(d.room == r.id and d.kind in SOCKET_KINDS and math.hypot(d.x - x, d.y - y) < 600 for d in devs):
                    continue
                if r.kind == "kitchen" and any(f.kind == "worktop" and f.wall == wall for f in furn):
                    continue
                add("socket", r.id, x, y, SOCKET_Z, "EA1-general-pitch")
    return devs


def _place_bathroom(h: House, r: Room, wets, add) -> None:
    """Bathroom: no sockets. Extractor/heater FCU and any shaver unit go outside zones 0-2 (first free candidate)."""
    for e in h.equipment:
        if e.room == r.id and e.kind in ("water_heater", "extractor"):
            for wall in "NESW":
                L = _wall_len(r, wall)
                for frac in (0.25, 0.5, 0.75):
                    x, y = _wall_point(r, wall, L * frac)
                    if zones.zone_at(x, y, 2300.0, wets) is None and zones.dist_to_zone1_mm(x, y, wets) > zones.Z2_EXTENT_MM:
                        add("fcu", r.id, x, y, 2300.0, "EA2-fcu-outside-zones", serves=e.id)
                        break
                else:
                    continue
                break


# ---- validation (EA2 and switch height) --------------------------------------------------------
@dataclass
class Violation:
    rule: str
    device: str
    room: str
    severity: str     # fail | warn
    message: str
    card: str


def validate_devices(h: House, devs: list[Device]) -> list[Violation]:
    out: list[Violation] = []
    rooms = {r.id: r for r in h.rooms}
    for d in devs:
        r = rooms[d.room]
        if d.kind == "switch" and not (SWITCH_BAND[0] <= d.z <= SWITCH_BAND[1]):
            out.append(Violation("EA1-switch-height", d.id, d.room, "fail", f"switch at {d.z:.0f} mm, band {SWITCH_BAND[0]:.0f}-{SWITCH_BAND[1]:.0f} mm", "EL-POL-PLACEMENT"))
        if r.kind != "bathroom":
            continue
        wets = zones.wet_areas(r, h.furniture)
        z = zones.zone_at(d.x, d.y, d.z, wets)
        if z is not None and d.kind in SOCKET_KINDS:
            out.append(Violation("EA2-socket-in-zone", d.id, d.room, "fail", f"socket-outlet in zone {z}", f"EL-701-ZONE{z}"))
        elif z is not None and d.kind == "shaver_unit" and z == 2:
            pass     # shaver supply unit (IEC 61558-2-5) is permitted in zone 2 only
        elif z is not None and d.kind in ("shaver_unit", "switch", "data", "tv_sat", "isolator_ac", "cooker_unit"):
            out.append(Violation("EA2-device-in-zone", d.id, d.room, "fail", f"{d.kind} in zone {z}", f"EL-701-ZONE{z}"))
        elif z is not None and d.kind == "fcu":
            out.append(Violation("EA2-device-in-zone", d.id, d.room, "fail", f"fixed-equipment FCU in zone {z}", f"EL-701-ZONE{z}"))
        if d.kind in SOCKET_KINDS and z is None:
            dist = zones.dist_to_zone1_mm(d.x, d.y, wets)
            if dist < zones.UK_SOCKET_EXCLUSION_MM:
                out.append(Violation("EA2-socket-2.5m-uk", d.id, d.room, "warn", f"socket {dist:.0f} mm from zone 1 (UK national rule: 2500 mm)", "EL-701-SOCKETS"))
    return out


# ---- provision minima (EA1) ---------------------------------------------------------------------
def provision_requirements(h: House, r: Room) -> list[tuple[str, int, str]]:
    """(device kind, minimum count, reason) for the room, from the furniture and room type."""
    req: list[tuple[str, int, str]] = [("switch", sum(1 for d in h.doors if d.room == r.id), "one switch per door")]
    for f in (f for f in h.furniture if f.room == r.id):
        if f.kind == "bed":
            req.append(("socket_bedside", 2, f"both sides of {f.id}"))
        elif f.kind == "desk":
            req += [("socket", 2, f"desk {f.id}"), ("data", 2, f"desk {f.id}")]
        elif f.kind == "tv":
            req += [("socket", 2, f"TV wall {f.id}"), ("tv_sat", 1, f"TV wall {f.id}"), ("data", 1, f"TV wall {f.id}")]
        elif f.kind == "worktop":
            req.append(("socket_worktop", max(1, math.ceil((_rect_edge_on_wall(f.rect, f.wall or 'N')[1] - _rect_edge_on_wall(f.rect, f.wall or 'N')[0]) / WORKTOP_PITCH_MM)), f"worktop {f.id} at <= 1.2 m pitch"))
    for e in h.equipment:
        if e.room == r.id and e.kind == "ac":
            req.append(("isolator_ac", 1, f"AC {e.id}"))
        if e.room == r.id and e.kind == "cooker":
            req.append(("cooker_unit", 1, f"cooker {e.id}"))
        if e.room == r.id and e.kind in ("washer", "dishwasher", "water_heater"):
            req.append(("fcu", 1, f"{e.kind} {e.id}"))
    return req


def provision_count(devs: list[Device], room: str, kind: str) -> int:
    if kind == "socket_bedside":
        return sum(1 for d in devs if d.room == room and d.rule == "EA1-bedside-both-sides")
    if kind == "socket_worktop":
        return sum(1 for d in devs if d.room == room and d.rule == "EA1-worktop-pitch")
    return sum(1 for d in devs if d.room == room and d.kind == kind)
