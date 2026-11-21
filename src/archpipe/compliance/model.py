"""A small, plain description of a design for the compliance checkers (lane L1).

The checkers read only this model, never Revit or the concept modules, so each can be proved on a fixture built
from named quantities. `load_d1` assembles it for design D1 from the most authoritative data held:

  * rooms, occupancy, links  : concept.villa_r11.design("D1") (the spec the Revit option was built from);
  * areas                    : designs-r12/readback.json (Revit read-back, net room areas);
  * doors, windows, stair, rails, balustrades : designs-r12/options-spec.json (the spec that was built; the
    read-back confirms counts: 18 doors, 8 windows, 3 rails, stair id);
  * daylight factor          : daylight/summary-r12.json (validated Radiance run on the same spec);
  * ramp / deck soffit       : concept.villa_parking.clear_at (the ramp profile the Revit ramp was built from).

If lane L2 publishes `out/model/d1-elements.json` it should replace the spec reads here; the checkers do not change.
Units: metres unless a name says `_mm`. z is relative to the GF finished floor (basement FFL = -3.0 m).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

HABITABLE = ("living", "dining", "bedroom", "study", "media")
NET_INSET = 0.15     # estimated net area = rect less 0.15 m each way (lounge: 21.97 vs Revit read-back 21.87 m2)
UTILITY = ("kitchen", "bathroom", "wc", "ensuite", "utility", "dressing", "store", "hall", "corridor", "stair",
           "landing", "entrance")


@dataclass
class Room:
    id: str
    level: str                      # "B" or "GF"
    rect: tuple                     # x0, y0, x1, y1 (m)
    occupancy: str
    name: str = ""
    area_m2: float | None = None    # net area from the Revit read-back when it has one
    part_of: str = ""               # an open-plan part of another room (merged for area and daylight)
    ext: bool = False               # in the east extension under the ramp / deck

    @property
    def group(self) -> str:
        return self.part_of or self.id

    @property
    def w(self) -> float:
        return abs(self.rect[2] - self.rect[0])

    @property
    def d(self) -> float:
        return abs(self.rect[3] - self.rect[1])

    @property
    def rect_area(self) -> float:
        return self.w * self.d


@dataclass
class Opening:
    id: str
    kind: str                       # "door" | "window"
    level: str
    width: float
    height: float
    sill: float = 0.0
    rooms: tuple = ()               # rooms either side (windows: the one room)
    exterior: bool = False          # glazed garden door / window to outside
    x: float = 0.0
    y: float = 0.0
    swing_known: bool = False


@dataclass
class Stair:
    id: str
    treads: list                    # boxes [x0, y0, z0, x1, y1, z1] in mm, as built (z: GF FFL = 0)
    gf_opening_m: tuple             # x0, y0, x1, y1 (m) of the slab opening
    slab_soffit_mm: float           # underside of the GF slab, mm (z)
    top_landing: tuple = ()         # rect (m) of the GF landing
    bottom_landing: tuple = ()      # rect (m) of the B landing
    has_risers: bool = False        # riser boards modelled
    gf_floor_z_mm: float = 0.0
    b_floor_z_mm: float = -3000.0


@dataclass
class Guard:
    id: str
    where: str
    height_m: float | None
    kind: str = "guard"             # guard | handrail
    solid: bool = True              # drawn solid / glass, so no gaps for a sphere
    drop_m: float | None = None     # height of the fall it guards
    level: str = ""


@dataclass
class DesignModel:
    id: str
    rooms: dict = field(default_factory=dict)
    openings: list = field(default_factory=list)
    stair: Stair | None = None
    guards: list = field(default_factory=list)
    clear: dict = field(default_factory=dict)       # room id -> list of clear heights (m) sampled over the floor
    beam_clear_m: float | None = None
    df: dict = field(default_factory=dict)          # room id -> mean daylight factor (%)
    needed_but_unmodelled: list = field(default_factory=list)   # (subject, what) pairs, reported not_evaluated
    sources: list = field(default_factory=list)
    links: list = field(default_factory=list)       # (room, room) pairs that connect

    def group_area(self, group: str) -> float:
        tot = 0.0
        for r in self.rooms.values():
            if r.group == group:
                tot += r.area_m2 if r.area_m2 else r.rect_area
        return tot

    def group_rooms(self, group: str) -> list:
        return [r for r in self.rooms.values() if r.group == group]


# --------------------------------------------------------------------------------------------------------------
def default_out_dir() -> Path:
    env = os.environ.get("ARCHPIPE_OUT")
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    for p in here.parents:
        if (p / "out" / "villa").is_dir():
            return p / "out"
    return Path(r"C:\Users\mmbka\arch-pipeline\out")


def _j(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_d1(out_dir: Path | str | None = None) -> DesignModel:
    from ..concept import villa_r11 as R
    from ..concept import villa_parking as P

    from ..concept import revit_spec as RS

    out = Path(out_dir) if out_dir else default_out_dir()
    villa = out / "villa"
    lay = R.design("D1")
    spec = RS.build(lay)            # the CURRENT D1 spec; the Sept-26 Revit read-back predates later client changes
    dayl = _j(villa / "daylight" / "summary-r12.json")["options"]["D1"]["rooms"]
    m = DesignModel("D1")
    m.links = [tuple(l) for l in lay["links"]]
    for rid, r in lay["rooms"].items():
        x0, y0, x1, y1 = r["rect"]
        net = max(0.0, abs(x1 - x0) - NET_INSET) * max(0.0, abs(y1 - y0) - NET_INSET)
        m.rooms[rid] = Room(rid, r["level"], tuple(r["rect"]), r["occupancy"], r.get("name", ""),
                            area_m2=round(net, 2), part_of=r.get("part_of", ""), ext=bool(r.get("ext")))
    # kitchen + its island are one open kitchen; the lounge, family corner and nook are one room
    m.rooms["kitchen-island"].part_of = "kitchen"
    # ---- clear heights: slab 3.00 - slab 0.20 - build-up 0.10 (villa.py), beams 0.60 deep (ASSUMED section)
    slab_clear, m.beam_clear_m = 2.70, 2.30
    for rid, r in m.rooms.items():
        if r.ext and r.rect[0] < P.RAMP_X1 + 1e-9:
            x0, x1 = r.rect[0], r.rect[2]
            m.clear[rid] = [P.clear_at(x0 + (i + 0.5) * (x1 - x0) / 200) for i in range(200)]
        elif r.ext:
            m.clear[rid] = [round(spec["parking2"]["deck"]["z_top"] - 0.35 + 3.0, 3)] * 5      # under the deck: 2.65
        else:
            m.clear[rid] = [slab_clear]
    # ---- openings
    for i, d in enumerate(spec["doors"]):
        ext = bool(d.get("garden")) or "yard" in d["rooms"] or "deck" in d["rooms"]
        m.openings.append(Opening("door-%02d" % i, "door", d["level"], d["width"], d["height"], 0.0,
                                  tuple(d["rooms"]), ext, d["x"], d["y"]))
    for i, w in enumerate(spec["windows"]):
        m.openings.append(Opening("win-%02d" % i, "window", w["level"], w["width"], w["height"], w["sill"],
                                  (w["room"],), True, w["x"], w["y"]))
    # ---- stair as built (tread boxes), as the Revit DirectShape was made
    op = spec["gf_opening"]
    m.stair = Stair(spec["stair_name"], [list(b) for b in spec["stair"]], tuple(op), -300.0,
                    top_landing=tuple(lay["rooms"]["landing-gf"]["rect"]),
                    bottom_landing=tuple(lay["rooms"]["hall-b"]["rect"]), has_risers=False)
    # ---- guards: the two stair balustrades and the three parking rails of the spec
    for b in spec.get("balustrades", []) or []:
        m.guards.append(Guard(b["id"], b.get("side", ""), b.get("height_above_nosing"),
                              "handrail" if b["id"] == "stair-wall-handrail" else "guard",
                              solid=(b.get("material") == "frameless laminated glass"), level=b.get("level", "")))
    for k, rl in enumerate(spec["rails"]):
        m.guards.append(Guard("rail-%d" % k, rl["what"], _profile_height(rl["profile"]), "guard", solid=True,
                              drop_m=_rail_drop(rl["what"]), level="street"))
    m.needed_but_unmodelled = [
        ("GF stair void edge", "no guard element for the GF slab opening (the route check villa.gf_route_width "
                               "assumes a 50 mm balustrade, but no height or type is in the spec or read-back)"),
        ("GF front terrace edge", "no guard at the terrace edge over the sunken north patio (3.0 m drop) in the "
                                  "spec rails or read-back"),
    ]
    for r in m.rooms.values():
        if r.id in dayl:
            m.df[r.id] = dayl[r.id]["df"]
    m.sources = ["concept/revit_spec.build(design('D1')) (current spec; Revit read-back 2026-09-26 predates it)",
                 "daylight/summary-r12.json (D1 rooms)", "concept/villa_r11.design('D1')",
                 "concept/villa_parking.clear_at"]
    return m


def _profile_height(profile) -> float | None:
    by_x: dict = {}
    for x, z in profile:
        by_x.setdefault(round(x, 3), []).append(z)
    hs = [max(v) - min(v) for v in by_x.values() if len(v) >= 2]
    return round(min(hs), 3) if hs else None


def _rail_drop(what: str) -> float | None:
    return 1.8 if "north patio" in what else None
