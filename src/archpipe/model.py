"""L0 spec: the single source of truth.

Deliberately BIM-shaped even though the v1 renderer is 2D only:
walls carry a *type* with layered composition, openings reference a
*host* wall, and rooms are closed boundary polygons. A later IFC or
Revit renderer needs exactly these; retrofitting them is painful.

All lengths are millimetres. Angles are degrees CCW from +X.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import yaml


class SpecError(ValueError):
    """Raised when a spec is structurally invalid. Message names the offender."""


Point = tuple[float, float]


@dataclass(frozen=True)
class MaterialLayer:
    material: str
    thickness: float


@dataclass(frozen=True)
class WallType:
    id: str
    thickness: float
    layers: tuple[MaterialLayer, ...]
    bearing: bool = False
    description: str = ""

    def validate(self) -> None:
        total = sum(l.thickness for l in self.layers)
        if self.layers and abs(total - self.thickness) > 0.5:
            raise SpecError(
                f"wall_type {self.id!r}: layer thicknesses sum to {total} "
                f"but declared thickness is {self.thickness}"
            )


@dataclass(frozen=True)
class Level:
    id: str
    name: str
    elevation: float
    height: float


@dataclass(frozen=True)
class Wall:
    id: str
    level: str
    type: str
    start: Point
    end: Point
    justify: str = "center"  # center | left | right, relative to start->end

    @property
    def length(self) -> float:
        return math.dist(self.start, self.end)

    @property
    def direction(self) -> Point:
        L = self.length
        if L == 0:
            raise SpecError(f"wall {self.id!r}: zero length")
        return ((self.end[0] - self.start[0]) / L, (self.end[1] - self.start[1]) / L)

    @property
    def normal(self) -> Point:
        """Left-hand normal: 90 degrees CCW from direction."""
        dx, dy = self.direction
        return (-dy, dx)

    def point_at(self, dist: float, offset: float = 0.0) -> Point:
        """Point `dist` along the wall axis, `offset` to the left of it."""
        dx, dy = self.direction
        nx, ny = self.normal
        return (
            self.start[0] + dx * dist + nx * offset,
            self.start[1] + dy * dist + ny * offset,
        )

    def face_offsets(self, thickness: float) -> tuple[float, float]:
        """(left, right) signed offsets of the two wall faces from the axis."""
        if self.justify == "center":
            return (thickness / 2, -thickness / 2)
        if self.justify == "left":
            return (0.0, -thickness)
        if self.justify == "right":
            return (thickness, 0.0)
        raise SpecError(f"wall {self.id!r}: bad justify {self.justify!r}")


@dataclass(frozen=True)
class Opening:
    id: str
    host: str          # wall id -- the BIM host relationship
    kind: str          # door | window
    width: float
    height: float
    at: float          # distance along host wall from start, to opening CENTRE
    sill: float = 0.0
    swing: str = "left"     # doors: which side the leaf swings toward
    family: str = ""

    def validate(self) -> None:
        if self.kind not in ("door", "window"):
            raise SpecError(f"opening {self.id!r}: unknown kind {self.kind!r}")
        if self.width <= 0:
            raise SpecError(f"opening {self.id!r}: width must be positive")


@dataclass(frozen=True)
class Room:
    id: str
    level: str
    name: str
    boundary: tuple[Point, ...]   # closed polygon, last point joins first
    occupancy: str = ""

    def validate(self) -> None:
        if len(self.boundary) < 3:
            raise SpecError(f"room {self.id!r}: boundary needs at least 3 points")

    @property
    def area_mm2(self) -> float:
        """Shoelace formula. Absolute, so winding order does not matter."""
        pts = self.boundary
        n = len(pts)
        s = sum(
            pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1]
            for i in range(n)
        )
        return abs(s) / 2

    @property
    def area_m2(self) -> float:
        return self.area_mm2 / 1_000_000

    @property
    def centroid(self) -> Point:
        pts = self.boundary
        return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


@dataclass(frozen=True)
class Furniture:
    """A placed piece. `type` keys into catalogue.CATALOGUE for its size
    and the clearance it needs; `size` overrides the catalogue footprint
    for a bespoke item."""
    id: str
    level: str
    type: str
    at: Point                  # centre of the footprint
    rotation: float = 0.0      # degrees CCW; 0 means local +Y points at +Y
    size: tuple[float, float] | None = None   # (width, depth) override
    room: str = ""             # optional, for reporting

    def corners(self, width: float, depth: float) -> tuple[Point, ...]:
        """Footprint corners, rotated about `at`."""
        return _rect(self.at, width, depth, self.rotation)

    def clearance_rect(self, side: str, width: float, depth: float,
                       amount: float) -> tuple[Point, ...] | None:
        """The clearance zone on one side, as a rotated rectangle."""
        if amount <= 0:
            return None
        if side in ("front", "back"):
            w, d = width, amount
            off = (depth + amount) / 2 * (1 if side == "front" else -1)
            centre = _offset(self.at, 0.0, off, self.rotation)
        elif side in ("left", "right"):
            w, d = amount, depth
            off = (width + amount) / 2 * (-1 if side == "left" else 1)
            centre = _offset(self.at, off, 0.0, self.rotation)
        else:
            raise SpecError(f"furniture {self.id!r}: unknown side {side!r}")
        return _rect(centre, w, d, self.rotation)


def _rect(centre: Point, w: float, d: float, rot_deg: float) -> tuple[Point, ...]:
    hw, hd = w / 2, d / 2
    return tuple(
        _offset(centre, dx, dy, rot_deg)
        for dx, dy in ((-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd))
    )


def _offset(origin: Point, dx: float, dy: float, rot_deg: float) -> Point:
    a = math.radians(rot_deg)
    ca, sa = math.cos(a), math.sin(a)
    return (origin[0] + dx * ca - dy * sa, origin[1] + dx * sa + dy * ca)


@dataclass
class Project:
    name: str
    units: str = "mm"
    standard: str = "iso13567"
    levels: tuple[Level, ...] = ()
    wall_types: tuple[WallType, ...] = ()
    walls: tuple[Wall, ...] = ()
    openings: tuple[Opening, ...] = ()
    rooms: tuple[Room, ...] = ()
    furniture: tuple[Furniture, ...] = ()

    # ---- lookups -------------------------------------------------------
    def wall_type(self, tid: str) -> WallType:
        for wt in self.wall_types:
            if wt.id == tid:
                return wt
        raise SpecError(f"unknown wall_type {tid!r}")

    def wall(self, wid: str) -> Wall:
        for w in self.walls:
            if w.id == wid:
                return w
        raise SpecError(f"unknown wall {wid!r}")

    def openings_of(self, wid: str) -> list[Opening]:
        return sorted((o for o in self.openings if o.host == wid), key=lambda o: o.at)

    def abutments(self, w: Wall) -> list[tuple[str, float, float]]:
        """Walls that land on `w`, as (wall id, position along w, half thickness).

        A wall abuts `w` when one of its endpoints sits on w's axis. Used to
        stop an opening being placed where another wall arrives -- a partition
        landing in the middle of a window is buildable only on paper.
        """
        dx, dy = w.direction
        nx, ny = w.normal
        w_half = self.wall_type(w.type).thickness / 2
        found: list[tuple[str, float, float]] = []
        for v in self.walls:
            if v.id == w.id or v.level != w.level:
                continue
            v_half = self.wall_type(v.type).thickness / 2
            for pt in (v.start, v.end):
                rx, ry = pt[0] - w.start[0], pt[1] - w.start[1]
                along = rx * dx + ry * dy
                perp = abs(rx * nx + ry * ny)
                if perp <= w_half + 1 and -1 <= along <= w.length + 1:
                    found.append((v.id, along, v_half))
        return found

    # ---- validation ----------------------------------------------------
    def validate(self) -> None:
        if self.units != "mm":
            raise SpecError(f"only mm is supported, got {self.units!r}")
        _dupes("level", [l.id for l in self.levels])
        _dupes("wall_type", [t.id for t in self.wall_types])
        _dupes("wall", [w.id for w in self.walls])
        _dupes("opening", [o.id for o in self.openings])
        _dupes("room", [r.id for r in self.rooms])
        _dupes("furniture", [f.id for f in self.furniture])

        level_ids = {l.id for l in self.levels}
        room_ids = {r.id for r in self.rooms}
        from .catalogue import CATALOGUE
        for f in self.furniture:
            if f.level not in level_ids:
                raise SpecError(f"furniture {f.id!r}: unknown level {f.level!r}")
            if f.room and f.room not in room_ids:
                raise SpecError(f"furniture {f.id!r}: unknown room {f.room!r}")
            if f.type not in CATALOGUE and f.size is None:
                raise SpecError(
                    f"furniture {f.id!r}: type {f.type!r} is not in the catalogue "
                    f"and no explicit size was given"
                )
        for t in self.wall_types:
            t.validate()
        for w in self.walls:
            if w.level not in level_ids:
                raise SpecError(f"wall {w.id!r}: unknown level {w.level!r}")
            self.wall_type(w.type)    # raises if missing
            w.direction               # raises on zero length
        for r in self.rooms:
            r.validate()
            if r.level not in level_ids:
                raise SpecError(f"room {r.id!r}: unknown level {r.level!r}")
        for o in self.openings:
            o.validate()
            host = self.wall(o.host)  # raises if missing
            half = o.width / 2
            if o.at - half < -0.5 or o.at + half > host.length + 0.5:
                raise SpecError(
                    f"opening {o.id!r}: spans {o.at - half:.0f}..{o.at + half:.0f} "
                    f"along host wall {host.id!r}, which is only {host.length:.0f} long"
                )
        for w in self.walls:
            ops = self.openings_of(w.id)
            for a, b in zip(ops, ops[1:]):
                if a.at + a.width / 2 > b.at - b.width / 2 + 0.5:
                    raise SpecError(
                        f"openings {a.id!r} and {b.id!r} overlap on wall {w.id!r}"
                    )
            # An opening may not swallow the point where another wall lands.
            for other_id, along, half in self.abutments(w):
                for o in ops:
                    if o.at - o.width / 2 < along + half and along - half < o.at + o.width / 2:
                        raise SpecError(
                            f"opening {o.id!r} on wall {w.id!r} clashes with wall "
                            f"{other_id!r}, which lands at {along:.0f} along it; "
                            f"the opening spans {o.at - o.width / 2:.0f}.."
                            f"{o.at + o.width / 2:.0f}"
                        )


def _dupes(kind: str, ids: list[str]) -> None:
    seen: set[str] = set()
    for i in ids:
        if i in seen:
            raise SpecError(f"duplicate {kind} id {i!r}")
        seen.add(i)


def _pt(v) -> Point:
    return (float(v[0]), float(v[1]))


def load(path: str | Path) -> Project:
    """Parse and validate a spec YAML file."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    meta = data.get("project", {})
    p = Project(
        name=meta.get("name", "Untitled"),
        units=meta.get("units", "mm"),
        standard=meta.get("standard", "iso13567"),
        levels=tuple(
            Level(l["id"], l.get("name", l["id"]), float(l.get("elevation", 0)),
                  float(l.get("height", 3000)))
            for l in data.get("levels", [])
        ),
        wall_types=tuple(
            WallType(
                t["id"], float(t["thickness"]),
                tuple(MaterialLayer(m["material"], float(m["thickness"]))
                      for m in t.get("layers", [])),
                bool(t.get("bearing", False)), t.get("description", ""),
            )
            for t in data.get("wall_types", [])
        ),
        walls=tuple(
            Wall(w["id"], w["level"], w["type"], _pt(w["start"]), _pt(w["end"]),
                 w.get("justify", "center"))
            for w in data.get("walls", [])
        ),
        openings=tuple(
            Opening(o["id"], o["host"], o["kind"], float(o["width"]),
                    float(o.get("height", 2100)), float(o["at"]),
                    float(o.get("sill", 0)), o.get("swing", "left"),
                    o.get("family", ""))
            for o in data.get("openings", [])
        ),
        rooms=tuple(
            Room(r["id"], r["level"], r["name"],
                 tuple(_pt(pt) for pt in r["boundary"]), r.get("occupancy", ""))
            for r in data.get("rooms", [])
        ),
        furniture=tuple(
            Furniture(
                f["id"], f["level"], f["type"], _pt(f["at"]),
                float(f.get("rotation", 0)),
                (float(f["size"][0]), float(f["size"][1])) if f.get("size") else None,
                f.get("room", ""),
            )
            for f in data.get("furniture", [])
        ),
    )
    p.validate()
    return p
