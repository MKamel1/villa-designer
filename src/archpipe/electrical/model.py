"""Input model of the electrical engine: rooms, doors, furniture, luminaires, equipment, supply.

Geometry is axis-aligned rectangles in millimetres, y up (same units as the shared design model).
A villa adapter (archpipe.model.load("D1")) maps its elements onto these records; the test house
is defined in tests/electrical/fixtures/test_house.json.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ..contracts import LightingZone

Rect = tuple[float, float, float, float]   # x0, y0, x1, y1


@dataclass
class Room:
    id: str
    kind: str                 # living | bedroom | kitchen | bathroom | ...
    rect: Rect
    level: str = "GF"
    ceiling_mm: float = 2700.0


@dataclass
class Door:
    id: str
    room: str
    wall: str                 # N | E | S | W  (wall of the room the door sits in)
    offset_mm: float          # from the wall's start: W corner for N/S walls, S corner for E/W walls
    width_mm: float
    hinge: str = "start"      # start | end : which end of the opening carries the hinges; latch is the other end


@dataclass
class Furniture:
    id: str
    room: str
    kind: str                 # bed | desk | tv | sofa | worktop | hob | fridge | washer | dishwasher | shower | bath | basin
    rect: Rect
    wall: str = ""            # wall it stands against / head wall of a bed
    params: dict = field(default_factory=dict)


@dataclass
class Luminaire:
    id: str
    room: str
    watts: float
    zone: str = ""


@dataclass
class Equipment:
    id: str
    room: str
    kind: str                 # ac | water_heater | cooker | washer | dishwasher | pump | ev
    kw: float
    pf: float = 1.0
    cat: str = "standard"     # demand category (see demand.py)
    socket_on_cooker: bool = False


@dataclass
class Supply:
    v_phase: float = 220.0
    phases: int = 3
    earthing: str = "TT"            # TT | TN
    ra_ohm: float | None = None     # installation electrode resistance (TT); None = not measured
    ze_ohm: float | None = None     # external loop impedance (TN); None = not known
    board_xy: tuple[float, float] = (0.0, 0.0)
    feeder_length_m: float = 15.0
    feeder_ambient_c: float = 40.0
    roof_ambient_c: float = 50.0
    drop_m: float = 3.0
    main_breaker_a: float | None = None
    premises: str = "household"
    ra_note: str = ""               # provenance of ra_ohm (measured / assumed)


@dataclass
class House:
    name: str
    rooms: list[Room]
    doors: list[Door]
    furniture: list[Furniture]
    luminaires: list[Luminaire]
    zones: list[LightingZone]
    equipment: list[Equipment]
    supply: Supply

    def room(self, rid: str) -> Room:
        return next(r for r in self.rooms if r.id == rid)


def load_house(path: str | Path) -> House:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    t = lambda r: tuple(r)
    return House(
        name=d["name"],
        rooms=[Room(r["id"], r["kind"], t(r["rect"]), r.get("level", "GF"), r.get("ceiling_mm", 2700.0)) for r in d["rooms"]],
        doors=[Door(**x) for x in d["doors"]],
        furniture=[Furniture(f["id"], f["room"], f["kind"], t(f["rect"]), f.get("wall", ""), f.get("params", {})) for f in d["furniture"]],
        luminaires=[Luminaire(**x) for x in d["luminaires"]],
        zones=[LightingZone(z["id"], z["room"], z["layer"], tuple(z["luminaire_ids"]), z["watts"], z["dimming"]) for z in d["zones"]],
        equipment=[Equipment(**x) for x in d["equipment"]],
        supply=Supply(**{**d["supply"], "board_xy": tuple(d["supply"].get("board_xy", (0, 0)))}),
    )
