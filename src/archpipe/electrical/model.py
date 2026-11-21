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
    poly: tuple = ()          # polygon vertices (x, y) mm, counter-clockwise or clockwise; empty = the rectangle `rect`
    name: str = ""
    open_to: tuple = ()       # ids of rooms this room opens onto without a door


@dataclass
class Door:
    id: str
    room: str
    wall: str                 # N | E | S | W  (wall of the room the door sits in)
    offset_mm: float          # from the wall's start: W corner for N/S walls, S corner for E/W walls
    width_mm: float
    hinge: str = "start"      # start | end : which end of the opening carries the hinges; latch is the other end
    hinge_known: bool = True  # False = not in the model: hinge chosen by policy (switch_policy) and flagged
    garden: bool = False      # glazed/sliding door to the garden (no room switch beside it)
    operation: str = "hinged"


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
    xy: tuple[float, float] | None = None
    layer: str = ""


@dataclass
class Equipment:
    id: str
    room: str
    kind: str                 # ac | water_heater | cooker | washer | dishwasher | pump | ev
    kw: float
    pf: float = 1.0
    cat: str = "standard"     # demand category (see demand.py)
    socket_on_cooker: bool = False
    name: str = ""
    external: bool = False    # outside the building: buried armoured cable (method D2)
    board: str = ""           # force a board (default: the sub-board of the room's level)
    xy: tuple[float, float] | None = None   # load position when it is not in a room (external equipment)
    status: str = ""          # "" | assumed | confirmed
    reason: str = ""
    extra_length_m: float = 0.0   # route length not visible from the points (e.g. a run to another level)


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
class Board:
    """A distribution board. parent None = main board (fed from the incomer)."""
    id: str
    level: str
    xy: tuple[float, float]
    parent: str | None = None
    room: str = ""
    ambient_c: float = 40.0        # ceiling-void / route ambient for the lighting runs of this board
    height_mm: float = 1500.0


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
    boards: list[Board] = field(default_factory=list)       # empty = one board DB-GF at supply.board_xy (test house)
    extra_devices: list = field(default_factory=list)        # placement.Device records added by an adapter (garden, gate, ...)
    policy: dict = field(default_factory=dict)               # lighting_pack / socket_pack / level_z_mm ...
    flags: list = field(default_factory=list)                # adapter notes (assumptions) carried to the reports
    level_z_mm: dict = field(default_factory=dict)           # level -> finished-floor z (mm)
    provisional_zones: bool = False                          # lighting zones derived here, not published by L6b
    wall_segs: list = field(default_factory=list)            # dicts level,x0,y0,x1,y1,t (wall centre lines); empty = no clearance check
    openings: list = field(default_factory=list)             # dicts id,kind,level,x0,y0,x1,y1,z0,z1 (windows, doors)
    dropped: list = field(default_factory=list)              # devices the placement could not site (reason strings)

    def board_list(self) -> list[Board]:
        return self.boards or [Board("DB-GF", "GF", tuple(self.supply.board_xy))]

    def board_for_level(self, level: str) -> Board:
        """Sub-board of a level; any other level (site, unknown) hangs on the main board."""
        bl = self.board_list()
        for b in bl:
            if b.parent is not None and b.level == level:
                return b
        return next((b for b in bl if b.parent is None), bl[0])

    def room(self, rid: str) -> Room:
        return next(r for r in self.rooms if r.id == rid)

    def main_board(self) -> Board:
        bl = self.board_list()
        return next((b for b in bl if b.parent is None), bl[0])


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
