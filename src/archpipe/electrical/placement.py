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
@dataclass
class Wall:
    """One wall of a room: a segment a->b with an inward unit normal. `along` is the distance from `a`.

    For N/S walls `a` is the western end (x grows along the wall); for E/W walls `a` is the southern end
    (y grows along the wall). Rectangles give N, E, S, W; other polygons give one wall per edge (>= 300 mm),
    named by the direction the edge faces (N, E, S, W; a second wall facing the same way is N2, N3, ...).
    """
    name: str
    a: tuple[float, float]
    b: tuple[float, float]
    n: tuple[float, float]

    @property
    def length(self) -> float:
        return math.hypot(self.b[0] - self.a[0], self.b[1] - self.a[1])

    @property
    def u(self) -> tuple[float, float]:
        L = self.length or 1.0
        return ((self.b[0] - self.a[0]) / L, (self.b[1] - self.a[1]) / L)

    def point(self, along: float, inset: float = 0.0) -> tuple[float, float]:
        ux, uy = self.u
        return (self.a[0] + ux * along + self.n[0] * inset, self.a[1] + uy * along + self.n[1] * inset)

    def along_of(self, x: float, y: float) -> float:
        ux, uy = self.u
        return (x - self.a[0]) * ux + (y - self.a[1]) * uy

    def depth_of(self, x: float, y: float) -> float:
        """Distance of a point from the wall line, measured into the room (negative = outside)."""
        return (x - self.a[0]) * self.n[0] + (y - self.a[1]) * self.n[1]

    def span(self, rect: Rect) -> tuple[float, float]:
        x0, y0, x1, y1 = rect
        al = [self.along_of(x, y) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
        return (min(al), max(al))

    def gap(self, rect: Rect) -> float:
        x0, y0, x1, y1 = rect
        return min(self.depth_of(x, y) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)))


def _is_rect_poly(poly) -> bool:
    if len(poly) != 4:
        return False
    xs = sorted({round(p[0], 3) for p in poly})
    ys = sorted({round(p[1], 3) for p in poly})
    return len(xs) == 2 and len(ys) == 2


def room_walls(r: Room) -> dict[str, Wall]:
    poly = list(r.poly)
    if not poly or _is_rect_poly(poly):
        x0, y0, x1, y1 = r.rect
        return {"N": Wall("N", (x0, y1), (x1, y1), (0.0, -1.0)), "E": Wall("E", (x1, y0), (x1, y1), (-1.0, 0.0)),
                "S": Wall("S", (x0, y0), (x1, y0), (0.0, 1.0)), "W": Wall("W", (x0, y0), (x0, y1), (1.0, 0.0))}
    area2 = sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))
    sgn = 1.0 if area2 > 0 else -1.0                      # CCW: inside is on the left of each edge
    raw = []
    for i in range(len(poly)):
        p, q = poly[i], poly[(i + 1) % len(poly)]
        L = math.hypot(q[0] - p[0], q[1] - p[1])
        if L < 300.0:
            continue
        ux, uy = (q[0] - p[0]) / L, (q[1] - p[1]) / L
        n = (-uy * sgn, ux * sgn)
        out = (-n[0], -n[1])
        d = ("E" if out[0] > 0 else "W") if abs(out[0]) >= abs(out[1]) else ("N" if out[1] > 0 else "S")
        a, b = p, q
        if (d in "NS" and b[0] < a[0]) or (d in "EW" and b[1] < a[1]):
            a, b = b, a
        raw.append((d, L, a, b, n))
    walls: dict[str, Wall] = {}
    seen: dict[str, int] = {}
    for d, L, a, b, n in sorted(raw, key=lambda t: -t[1]):
        seen[d] = seen.get(d, 0) + 1
        nm = d if seen[d] == 1 else f"{d}{seen[d]}"
        walls[nm] = Wall(nm, a, b, n)
    return walls


def polygon_area_mm2(r: Room) -> float:
    poly = list(r.poly) or [(r.rect[0], r.rect[1]), (r.rect[2], r.rect[1]), (r.rect[2], r.rect[3]), (r.rect[0], r.rect[3])]
    return abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))) / 2.0


def point_in_room(r: Room, x: float, y: float, tol: float = 1.0) -> bool:
    poly = list(r.poly) or [(r.rect[0], r.rect[1]), (r.rect[2], r.rect[1]), (r.rect[2], r.rect[3]), (r.rect[0], r.rect[3])]
    for i in range(len(poly)):                              # on the boundary counts as inside
        (ax, ay), (bx, by) = poly[i], poly[(i + 1) % len(poly)]
        L = math.hypot(bx - ax, by - ay) or 1.0
        t = max(0.0, min(1.0, ((x - ax) * (bx - ax) + (y - ay) * (by - ay)) / (L * L)))
        if math.hypot(x - (ax + t * (bx - ax)), y - (ay + t * (by - ay))) <= tol:
            return True
    inside = False
    for i in range(len(poly)):
        (ax, ay), (bx, by) = poly[i], poly[(i + 1) % len(poly)]
        if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
            inside = not inside
    return inside


def _seg_dist(px, py, ax, ay, bx, by) -> float:
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _on_segment(x: float, y: float, s: dict, end_tol: float = 50.0) -> bool:
    """On the wall: the projection falls inside the segment (end_tol overshoot) and the perpendicular distance is within the wall half-thickness + tolerance."""
    ax, ay, bx, by = s["x0"], s["y0"], s["x1"], s["y1"]
    L = math.hypot(bx - ax, by - ay)
    if L == 0:
        return False
    ux, uy = (bx - ax) / L, (by - ay) / L
    al = (x - ax) * ux + (y - ay) * uy
    perp = abs(-(x - ax) * uy + (y - ay) * ux)
    return -end_tol <= al <= L + end_tol and perp <= s["t"] / 2.0 + WALL_TOL_MM


CLEAR_MARGIN_MM = 100.0
WALL_TOL_MM = 200.0
SLIDE_STEP_MM = 150.0
SLIDE_MAX_MM = 1500.0


def clearance(h: House, level: str, x: float, y: float, z: float) -> tuple[bool, str]:
    """Wall-mounted device post-condition: on a wall element of its level and outside every window/door opening box."""
    if not h.wall_segs:
        return True, ""
    if not any(s["level"] == level and _on_segment(x, y, s) for s in h.wall_segs):
        return False, "not on a wall element (open-plan edge or no wall in the model)"
    for o in h.openings:
        if o["level"] == level and o["x0"] - CLEAR_MARGIN_MM <= x <= o["x1"] + CLEAR_MARGIN_MM and o["y0"] - CLEAR_MARGIN_MM <= y <= o["y1"] + CLEAR_MARGIN_MM \
                and o["z0"] - 50.0 <= z <= o["z1"] + 50.0:
            return False, f"inside {o['kind']} {o['id']}"
    return True, ""


def slide_on_wall(h: House, r: Room, x: float, y: float, z: float):
    """(x, y) of the nearest clear point along the wall nearest to (x, y), or None. Returns the input when it is already clear."""
    ok, why = clearance(h, r.level, x, y, z)
    if ok:
        return (x, y), ""
    walls = room_walls(r)
    W = min(walls.values(), key=lambda w: abs(w.depth_of(x, y)))
    a0 = W.along_of(x, y)
    k = 1
    while k * SLIDE_STEP_MM <= SLIDE_MAX_MM:
        for sgn in (1, -1):
            a = a0 + sgn * k * SLIDE_STEP_MM
            if 100.0 <= a <= W.length - 100.0:
                px, py = W.point(a)
                if clearance(h, r.level, px, py, z)[0]:
                    return (px, py), f"moved {k * SLIDE_STEP_MM:.0f} mm along the wall ({why})"
        k += 1
    return None, why


def _in_keepout(h: House, r: Room, x: float, y: float, margin: float = 100.0) -> str:
    for k in h.keepouts:
        if k["level"] == r.level and k["x0"] - margin <= x <= k["x1"] + margin and k["y0"] - margin <= y <= k["y1"] + margin:
            return f"inside {k['id']}"
    for f in h.furniture:
        if f.room == r.id and f.rect[0] - margin <= x <= f.rect[2] + margin and f.rect[1] - margin <= y <= f.rect[3] + margin:
            return f"inside furniture {f.id}"
    return ""


def nearest_clear_wall_point(h: House, r: Room, x: float, y: float, z: float, max_mm: float = 4000.0):
    """Closest clear wall point (every 150 mm along every wall of the room) to (x, y) within max_mm, or None."""
    best = None
    for W in room_walls(r).values():
        a = 100.0
        while a <= W.length - 100.0:
            px, py = W.point(a)
            dist = math.hypot(px - x, py - y)
            if dist <= max_mm and (best is None or dist < best[0]) and clearance(h, r.level, px, py, z)[0]:
                best = (dist, px, py)
            a += SLIDE_STEP_MM
    return None if best is None else (best[1], best[2])


def clearance_violations(h: House, devs: list) -> list:
    """Independent post-condition on a finished device list (used by EA1)."""
    out = []
    rooms = {r.id: r for r in h.rooms}
    for d in devs:
        r = rooms.get(d.room)
        if r is None or r.kind == "outdoor" or d.params.get("free_standing"):
            continue
        ok, why = clearance(h, r.level, d.x, d.y, d.z)
        if not ok:
            out.append((d, why))
    return out


def _wall_len(r: Room, wall: str) -> float:
    return room_walls(r)[wall].length


def switch_for_door(r: Room, d: Door) -> tuple[float, float]:
    """Switch inside the room on the latch side (opposite the hinge), 150 mm from the frame, kept 100 mm off the corner."""
    w = room_walls(r)[d.wall]
    latch_end = d.offset_mm + d.width_mm if d.hinge == "start" else d.offset_mm
    direction = 1.0 if d.hinge == "start" else -1.0
    along = latch_end + direction * SWITCH_OFFSET_MM
    along = min(max(along, 100.0), w.length - 100.0)
    return w.point(along, 0.0)


def _door_spans(h: House, r: Room) -> dict[str, list[tuple[float, float]]]:
    sp: dict[str, list[tuple[float, float]]] = {k: [] for k in room_walls(r)}
    for d in h.doors:
        if d.room == r.id and d.wall in sp:
            sp[d.wall].append((d.offset_mm - 100.0, d.offset_mm + d.width_mm + 100.0))
    return sp


def _free_along(spans, a: float, b: float) -> bool:
    return all(b <= s0 or a >= s1 for s0, s1 in spans)


def _shared_edge_point(h: House, r: Room) -> tuple[float, float] | None:
    """Point on r's boundary where it opens onto a neighbour without a door (open-plan control point)."""
    mine = room_walls(r)
    best = None
    for oid in r.open_to:
        o = next((q for q in h.rooms if q.id == oid and q.level == r.level), None)
        if o is None:
            continue
        for w in mine.values():
            for ow in room_walls(o).values():
                if w.n[0] * ow.n[0] + w.n[1] * ow.n[1] > -0.99:
                    continue                                 # must face each other
                if abs(w.depth_of(*ow.a)) > 300.0:
                    continue                                 # not on the same line
                lo = max(0.0, min(w.along_of(*ow.a), w.along_of(*ow.b)))
                hi = min(w.length, max(w.along_of(*ow.a), w.along_of(*ow.b)))
                if hi - lo >= 600.0 and (best is None or hi - lo > best[0]):
                    best = (hi - lo, w, lo)
    if best is None:
        return None
    _, w, lo = best
    return w.point(lo + SWITCH_OFFSET_MM, 0.0)


def place_devices(h: House) -> list[Device]:
    devs: list[Device] = list(h.extra_devices)
    n = [0]

    rooms_by_id = {r.id: r for r in h.rooms}

    def add(kind, room, x, y, z, rule, serves="", **params):
        if not params.get("free_standing"):
            pt, why = slide_on_wall(h, rooms_by_id[room], x, y, z)
            if pt is None and kind == "socket" and why.startswith("not on a wall") and rule not in ("EA1-bedside-both-sides", "EA1-worktop-pitch"):
                # open-plan edge with no wall: a floor box 600 mm inside the room instead of a wall socket
                W = min(room_walls(rooms_by_id[room]).values(), key=lambda w: abs(w.depth_of(x, y)))
                bx, by = x + W.n[0] * 600.0, y + W.n[1] * 600.0
                blocked = _in_keepout(h, rooms_by_id[room], bx, by)
                if blocked:
                    h.dropped.append(f"floor box ({rule}) in {room} at ({bx:.0f}, {by:.0f}) not placed: {blocked}")
                    return
                if point_in_room(rooms_by_id[room], bx, by):
                    n[0] += 1
                    params.update(free_standing=True, floor_box=True, relocated="floor box: no wall element on this edge")
                    devs.append(Device(f"SOC-{room}-{n[0]:03d}", kind, room, bx, by, 0.0, rule, serves, params))
                    return
            if pt is None:
                h.dropped.append(f"{kind} ({rule}) in {room} at ({x:.0f}, {y:.0f}, z {z:.0f}) not placed: {why}")
                return
            if why:
                params["relocated"] = why
            x, y = pt
        n[0] += 1
        devs.append(Device(f"{kind[:3].upper()}-{room}-{n[0]:03d}", kind, room, x, y, z, rule, serves, params))

    h.dropped.clear()
    for r in h.rooms:
        if r.kind == "outdoor":
            continue                     # site pseudo-rooms: devices come from House.extra_devices
        walls = room_walls(r)
        wets = zones.wet_areas(r, h.furniture)
        is_wet = r.kind == "bathroom" or bool(wets)
        furn = [f for f in h.furniture if f.room == r.id]
        spans = _door_spans(h, r)
        # one switch per door at the latch side
        small = polygon_area_mm2(r) / 1e6 < 2.0          # cupboard-sized room: switched from the neighbour
        my_doors = [d for d in h.doors if d.room == r.id and not d.garden and not small]
        for d in my_doors:
            x, y = switch_for_door(r, d)
            add("switch", r.id, x, y, SWITCH_Z, "EA1-switch-latch-side", door=d.id, hinge_known=d.hinge_known)
        if not my_doors and not is_wet:
            p = _shared_edge_point(h, r)
            if p is not None:
                q = nearest_clear_wall_point(h, r, p[0], p[1], SWITCH_Z) if h.wall_segs else p
                if q is not None:
                    add("switch", r.id, q[0], q[1], SWITCH_Z, "EA1-switch-open-plan",
                        opening="open edge with " + ",".join(r.open_to) + ("; control point moved to the nearest wall" if q != p else ""))
                else:
                    h.dropped.append(f"switch (EA1-switch-open-plan) in {r.id}: no clear wall point within 4 m of the opening")
        if is_wet:
            _place_bathroom(h, r, wets, add)
            continue
        # equipment points (AC isolator high on the longest free wall)
        for e in h.equipment:
            if e.room != r.id:
                continue
            if e.kind == "ac":
                wn = max(walls, key=lambda w: walls[w].length)
                x, y = walls[wn].point(walls[wn].length / 2)
                add("isolator_ac", r.id, x, y, AC_Z, "EA1-ac-point", serves=e.id)
        # furniture driven points
        for f in furn:
            wn = f.wall if f.wall in walls else max(walls, key=lambda w: walls[w].length)
            W = walls[wn]
            lo, hi = W.span(f.rect)
            if f.kind == "bed":
                for a in (lo - BEDSIDE_OFFSET_MM, hi + BEDSIDE_OFFSET_MM):
                    x, y = W.point(a)
                    add("socket", r.id, x, y, BEDSIDE_Z, "EA1-bedside-both-sides", furniture=f.id)
                if f.params.get("head_panel_lights"):
                    # R3 (client FINAL 2026-11-26): the reading lights are arms CLAMPED to the low head panel, and the head wall is glass above 0.90 m,
                    # so there is no wall socket or wall box beside them. Power route: the lighting circuit (the lamps' own) is brought to a SELV
                    # driver / junction in the sill wall BEHIND the panel (z 300, centred on the bed, reachable by lifting the panel off its cleats),
                    # and a 24 V DC lead runs inside the panel's rear cavity to a connector in each arm's clamp. See docs/lanes/DF-built.md.
                    x, y = W.point((lo + hi) / 2)
                    lamps = [l.id for l in h.luminaires if l.room == r.id and "WALL-READ" in l.id]
                    add("socket_selv", r.id, x, y, 300.0, "EA1-bed-head-supply", serves=lamps[0] if lamps else "", furniture=f.id,
                        lamps=lamps)
            elif f.kind == "desk":
                mid = (lo + hi) / 2
                for k in (-1, 1):
                    x, y = W.point(mid + k * 300.0)
                    z = SOCKET_Z + 800.0
                    # a desk or vanity under a window (sill below the 1100 mm desk-cluster height): drop the cluster 300 mm, under the sill, instead of
                    # sliding it 1.2 m along the wall or losing it (R3 moved the parents' vanity under window-7)
                    if not clearance(h, r.level, x, y, z)[0] and clearance(h, r.level, x, y, z - 300.0)[0]:
                        z -= 300.0
                    add("socket", r.id, x, y, z, "EA1-desk-cluster", furniture=f.id)
                    add("data", r.id, x, y, z, "EA1-desk-cluster", furniture=f.id)
            elif f.kind == "tv":
                mid = (lo + hi) / 2
                for k, kind in ((-1, "socket"), (0, "socket"), (1, "tv_sat"), (2, "data")):
                    x, y = W.point(mid + (k - 0.5) * 200.0)
                    add(kind, r.id, x, y, TV_Z, "EA1-tv-cluster", furniture=f.id)
            elif f.kind == "sofa":
                for a in (lo - BEDSIDE_OFFSET_MM, hi + BEDSIDE_OFFSET_MM):
                    x, y = W.point(a)
                    add("socket", r.id, x, y, SOCKET_Z, "EA1-sofa-ends", furniture=f.id)
            elif f.kind == "worktop":
                length = hi - lo
                cnt = max(1, math.ceil(length / WORKTOP_PITCH_MM))
                pitch = length / cnt
                for i in range(cnt):
                    x, y = W.point(lo + pitch * (i + 0.5))
                    add("socket", r.id, x, y, WORKTOP_SOCKET_Z, "EA1-worktop-pitch", furniture=f.id, zone="worktop")
            elif f.kind == "island":
                x0, y0, x1, y1 = f.rect
                long_x = (x1 - x0) >= (y1 - y0)
                pts = ((x0 + (x1 - x0) * 0.25, y0), (x0 + (x1 - x0) * 0.75, y0)) if long_x else ((x0, y0 + (y1 - y0) * 0.25), (x0, y0 + (y1 - y0) * 0.75))
                for x, y in pts:
                    add("socket", r.id, x, y, 900.0, "EA1-island-sockets", furniture=f.id, free_standing=True)
            elif f.kind in ("hob", "oven"):
                x, y = W.point((lo + hi) / 2 + 700.0)
                for e in h.equipment:
                    if e.room == r.id and e.kind == "cooker":
                        add("cooker_unit", r.id, x, y, WORKTOP_SOCKET_Z, "EA1-dedicated-cooker", serves=e.id)
                        break
            elif f.kind in ("washer", "dishwasher", "fridge"):
                x, y = W.point((lo + hi) / 2)
                eq = next((e.id for e in h.equipment if e.room == r.id and e.kind == f.kind), "")
                add("fcu" if eq else "socket", r.id, x, y, 600.0, "EA1-dedicated-appliance", serves=eq, furniture=f.id)
        # dedicated equipment with no furniture point: spur on the worktop/longest wall
        served = {d.serves for d in devs if d.room == r.id and d.serves}
        run = next((f for f in furn if f.kind == "worktop" and f.wall in walls), None)
        for e in h.equipment:
            if e.room != r.id or e.id in served or e.external or e.kind in ("ac", "water_heater", "extractor", "fire_alarm", "elv", "lighting"):
                continue
            slot = sum(1 for d in devs if d.room == r.id and d.rule in ("EA1-dedicated-appliance", "EA1-dedicated-cooker") and not d.params.get("furniture"))
            if run is not None:
                W = walls[run.wall]
                lo, hi = W.span(run.rect)
                x, y = W.point(min(max(lo + 300.0 + 600.0 * slot, 150.0), W.length - 150.0))
            else:
                W = walls[max(walls, key=lambda w: walls[w].length)]
                x, y = W.point(min(W.length / 2 + 600.0 * slot, W.length - 150.0))
            kind = "cooker_unit" if e.kind == "cooker" else "fcu"
            add(kind, r.id, x, y, 600.0 if e.kind != "cooker" else WORKTOP_SOCKET_Z, "EA1-dedicated-cooker" if e.kind == "cooker" else "EA1-dedicated-appliance", serves=e.id)
        # general sockets: at least one double per free wall stretch, pitch <= 3 m (none in cupboard-sized rooms)
        if (polygon_area_mm2(r) / 1e6) < 2.0 or r.kind == "stair":
            continue                     # cupboard-sized rooms and stairs get no general sockets
        for wn, W in walls.items():
            L = W.length
            cnt = max(1, math.ceil(L / WALL_SOCKET_PITCH_MM))
            pitch = L / cnt
            for i in range(cnt):
                a = pitch * (i + 0.5)
                if not _free_along(spans[wn], a - 150, a + 150):
                    continue
                x, y = W.point(a)
                # skip when a furniture-driven socket already stands within 600 mm
                if any(d.room == r.id and d.kind in SOCKET_KINDS and math.hypot(d.x - x, d.y - y) < 600 for d in devs):
                    continue
                if r.kind == "kitchen" and any(f.kind == "worktop" and f.wall == wn for f in furn):
                    continue
                add("socket", r.id, x, y, SOCKET_Z, "EA1-general-pitch")
    return devs


def _place_bathroom(h: House, r: Room, wets, add) -> None:
    """Bathroom: no sockets. Extractor/heater FCU and any shaver unit go outside zones 0-2 (first free candidate)."""
    walls = room_walls(r)
    for e in h.equipment:
        if e.room == r.id and e.kind in ("water_heater", "extractor"):
            for wn, W in walls.items():
                L = W.length
                for frac in (0.25, 0.5, 0.75):
                    x, y = W.point(L * frac)
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
        wets = zones.wet_areas(r, h.furniture)
        if r.kind != "bathroom" and not wets:
            continue
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
    small = polygon_area_mm2(r) / 1e6 < 2.0
    req: list[tuple[str, int, str]] = [("switch", 0 if small else sum(1 for d in h.doors if d.room == r.id and not d.garden), "one switch per door")]
    walls = room_walls(r)
    for f in (f for f in h.furniture if f.room == r.id):
        if f.kind == "bed":
            req.append(("socket_bedside", 2, f"both sides of {f.id}"))
            if f.params.get("head_panel_lights"):
                req.append(("socket_selv", 1, f"bed-head SELV supply behind the head panel of {f.id} (reading-light arms)"))
        elif f.kind == "desk":
            req += [("socket", 2, f"desk {f.id}"), ("data", 2, f"desk {f.id}")]
        elif f.kind == "tv":
            req += [("socket", 2, f"TV wall {f.id}"), ("tv_sat", 1, f"TV wall {f.id}"), ("data", 1, f"TV wall {f.id}")]
        elif f.kind == "worktop":
            wn = f.wall if f.wall in walls else max(walls, key=lambda w: walls[w].length)
            lo, hi = walls[wn].span(f.rect)
            req.append(("socket_worktop", max(1, math.ceil((hi - lo) / WORKTOP_PITCH_MM)), f"worktop {f.id} at <= 1.2 m pitch"))
        elif f.kind == "island":
            req.append(("socket_island", 2, f"island {f.id}"))
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
    if kind == "socket_island":
        return sum(1 for d in devs if d.room == room and d.rule == "EA1-island-sockets")
    return sum(1 for d in devs if d.room == room and d.kind == kind)
