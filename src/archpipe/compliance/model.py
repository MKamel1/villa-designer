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
    net_w: float | None = None      # net clear dimensions (villa.net_dims), m
    net_d: float | None = None

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
    swing_direction: str = ""       # "outward" = away from the stair landing; "" or "inward" = into it


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
    riser_infill: dict | None = None            # {max_clear_opening_mm, ...} when the open risers carry an infill
    under_flight: dict | None = None            # {enclosed, treads_enclosed, cupboard_id} when the space is enclosed


@dataclass
class Guard:
    id: str
    where: str
    height_m: float | None
    kind: str = "guard"             # guard | handrail
    solid: bool = True              # drawn solid / glass, so no gaps for a sphere
    drop_m: float | None = None     # height of the fall it guards
    max_opening_mm: float | None = None   # largest gap in the infill (None: not stated)
    climbable: bool | None = None
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
    not_evaluated_gates: list = field(default_factory=list)   # (criterion, subject, reason)
    waivers: dict = field(default_factory=dict)     # (criterion, room id) -> reason: a recorded client waiver

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
    from ..concept import revit_spec as RS
    from ..concept import villa as V
    from ..concept import villa_parking as P
    from ..concept import villa_r11 as R

    out = Path(out_dir) if out_dir else default_out_dir()
    villa = out / "villa"
    lay = R.design("D1")
    spec = RS.build(lay)            # the CURRENT D1 spec (36 walls, 18 doors, 8 windows = the 2026-09-29 D1F read-back)
    m = DesignModel("D1")
    m.links = [tuple(l) for l in lay["links"]]
    rb = _optional(villa / "furnish-d1" / "revit" / "readback.json")
    rb_rooms = {r["id"]: r["area_m2"] for r in rb["options"][0]["rooms"]} if rb else {}
    rb_marks = {}
    if rb:
        for o in rb["options"][0]["doors"] + rb["options"][0]["windows"]:
            rb_marks[(round(o["x"], 3), round(o["y"], 3), o["level"])] = o.get("mark", "")
    ext = lay.get("extension")
    outline = {lv: V.boundary_segments(V.envelope(lv, ext)) for lv in V.LEVELS}
    for rid, r in lay["rooms"].items():
        w, d = V.net_dims(r["rect"], outline[r["level"]])
        net = rb_rooms.get(rid) or round(max(w, 0.0) * max(d, 0.0), 2)      # Revit net area, else net_dims estimate
        m.rooms[rid] = Room(rid, r["level"], tuple(r["rect"]), r["occupancy"], r.get("name", ""), area_m2=net,
                            part_of=r.get("part_of", ""), ext=bool(r.get("ext")), net_w=round(w, 3), net_d=round(d, 3))
    # the open kitchen and its island are one room
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
    # ---- openings (element id = the Revit mark where the read-back has it)
    for i, d in enumerate(spec["doors"]):
        ext_ = bool(d.get("garden")) or "yard" in d["rooms"] or "deck" in d["rooms"]
        mark = rb_marks.get((round(d["x"], 3), round(d["y"], 3), d["level"])) or "door-%02d" % i
        m.openings.append(Opening(mark, "door", d["level"], d["width"], d["height"], 0.0, tuple(d["rooms"]), ext_,
                                  d["x"], d["y"]))
    for i, w in enumerate(spec["windows"]):
        mark = rb_marks.get((round(w["x"], 3), round(w["y"], 3), w["level"])) or "win-%02d" % i
        m.openings.append(Opening(mark, "window", w["level"], w["width"], w["height"], w["sill"], (w["room"],), True,
                                  w["x"], w["y"]))
    # ---- stair as built (tread boxes only: the Revit stair is a DirectShape of treads, no riser boards)
    m.stair = Stair(spec["stair_name"], [list(b) for b in spec["stair"]], tuple(spec["gf_opening"]), -300.0,
                    top_landing=tuple(lay["rooms"]["landing-gf"]["rect"]),
                    bottom_landing=tuple(lay["rooms"]["hall-b"]["rect"]), has_risers=False)
    # ---- guards: the stair balustrades and the parking rails of the spec
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
        ("GF front terrace edge", "no guard at the terrace edge over the sunken north patio (3.0 m drop): the spec "
                                  "walls and rails and the D1F read-back have none (villa.py's TERRACE comment of a "
                                  "900 mm parapet is not in D1)"),
        ("patio edge beside the entrance steps", "the 1.8 m drop from the entrance steps (street level) to the sunken "
                                                 "patio has no guard in the spec or read-back"),
    ]
    m.not_evaluated_gates = [
        ("LS5", "basement garden doors lead to a place of safety",
         "the lounge, dining and living pass LS5 only through garden doors into the sunken yards (4 m fences); a way "
         "from the yard to the street (gate, steps or the car ramp) is neither modelled nor carded"),
        ("LS5", "dead-end hall and the single stair",
         "no sourced dead-end or travel-distance limit for a single dwelling is held (Approved Document B travel "
         "distances are not carded); reviewer step. GF exits: the core door at the stair top and the escape windows"),
    ]
    _prefer_l2_model(m)
    m.waivers[("LS5", "cinema")] = ("WAIVED by client (G1 2026-11-21): accepted risk, the cinema stays an inner room; "
                                    "mitigation is interlinked smoke detection in lounge and cinema (electrical lane)")
    dd = _optional(villa / "daylight" / "summary-r12.json")
    dayl = (dd or {}).get("options", {}).get("D1", {}).get("rooms", {})
    for r in m.rooms.values():
        if r.id in dayl:
            m.df[r.id] = dayl[r.id]["df"]
    m.sources = ["concept/revit_spec.build(concept/villa_r11.design('D1')): current spec (doors, windows, stair "
                 "treads, rails, balustrades). The designs-r12 read-back (2026-09-26) is older: it differs in the "
                 "GF layout, study windows, pocket door and parents' suite",
                 "furnish-d1/revit/readback.json (2026-09-29, D1F): Revit net room areas and element marks; counts "
                 "match the current spec (36 walls, 18 doors, 8 windows)",
                 "daylight/summary-r12.json D1 rooms: basement rooms only, from the 2026-09-26 spec",
                 "concept/villa_parking.clear_at: ramp and deck soffit"]
    if dd is None:
        m.sources.append("daylight summary NOT FOUND: daylight factors reported not_evaluated")
    return m


GUARD_UNMODELLED = {"rail-gf-stair-void": "GF stair void edge", "rail-gf-terrace-edge": "GF front terrace edge",
                    "rail-patio-steps-edge": "patio edge beside the entrance steps"}


def _l2_elements(m: DesignModel):
    """L2 elements built from the current spec (spec_source.all_from_spec: fast, carries the G1 fields); the committed
    snapshot is the fallback."""
    try:
        from ..concept import revit_spec as RS
        from ..concept import villa_r11 as R
        from ..model import spec_source as SS
        lay = R.design("D1")
        return SS.all_from_spec(lay, RS.build(lay)), "archpipe.model.spec_source.all_from_spec (L2, current spec)"
    except Exception as exc:            # noqa: BLE001
        m.sources.append("L2 spec_source failed (%s: %s); trying the committed snapshot" % (type(exc).__name__, exc))
    from ..model import load as load_model
    return load_model("D1"), "archpipe.model.load('D1') snapshot (L2)"


def _prefer_l2_model(m: DesignModel) -> None:
    """Replace spec-derived openings, stair treads and guards with the L2 canonical model's elements (same values,
    stable element ids) and read the G1 fields; record the cross-check in `m.sources`. Anything missing stays
    fail-closed (the not-modelled rows remain)."""
    try:
        els, label = _l2_elements(m)
    except Exception as exc:            # noqa: BLE001 - the spec-derived values stay
        m.sources.append("L2 model not loaded (%s: %s); element ids are spec-derived" % (type(exc).__name__, exc))
        return
    ops, guards, stair, cupboard = [], [], None, None
    for e in els:
        p = e.params
        if e.kind in ("door", "window"):
            rooms = tuple(p.get("rooms") or (e.room,))
            ext = e.kind == "window" or "yard" in rooms or "deck" in rooms
            ops.append(Opening(e.id, e.kind, e.level, p["width_mm"] / 1000.0, p["height_mm"] / 1000.0,
                               p.get("sill_mm", 0.0) / 1000.0, rooms, ext, e.placement[0] / 1000.0,
                               e.placement[1] / 1000.0, swing_known=bool(p.get("swing_known")),
                               swing_direction=str(p.get("swing_direction") or "")))
        elif e.kind == "railing" and p.get("guard_height_mm") is not None:
            if e.id.startswith("rail-stair"):
                guards.append(Guard(e.id, p.get("side", ""), p["guard_height_mm"] / 1000.0,
                                    "handrail" if p.get("material") == "wood" else "guard",
                                    solid=bool(p.get("glazed")) or p.get("material") == "wood", level=e.level))
            else:
                mo = p.get("max_opening_mm")
                solid = bool(p.get("glazed")) or (mo is not None and mo < 100.0) or mo is None
                drop = p.get("drop_min_mm") if p.get("drop_min_mm") is not None else p.get("drop_mm")
                guards.append(Guard(e.id, p.get("what", ""), p["guard_height_mm"] / 1000.0, "guard", solid=solid,
                                    drop_m=(drop / 1000.0 if drop is not None else _rail_drop(p.get("what", ""))),
                                    level="street", max_opening_mm=mo, climbable=p.get("climbable")))
        elif e.kind == "stair":
            stair = e
        elif e.kind == "furniture" and e.id == "joinery-understair-cupboard":
            cupboard = e
    n_spec_doors = sum(1 for o in m.openings if o.kind == "door")
    n_doors = sum(1 for o in ops if o.kind == "door")
    if (n_doors, len(ops)) != (n_spec_doors, len(m.openings)):
        m.sources.append("L2 model opening counts differ from the spec (%d vs %d): spec-derived values kept"
                         % (len(ops), len(m.openings)))
        return
    m.openings = ops
    if guards:
        m.guards = guards
        present = {g.id for g in guards}
        gone = {GUARD_UNMODELLED[i] for i in GUARD_UNMODELLED if i in present}
        m.needed_but_unmodelled = [(s_, w) for s_, w in m.needed_but_unmodelled if s_ not in gone]
    if stair is not None and m.stair is not None:
        sp = stair.params
        if sp.get("tread_boxes_mm"):
            m.stair.treads = [list(b) for b in sp["tread_boxes_mm"]]
        m.stair.id = stair.id
        ri = sp.get("riser_infill")
        m.stair.riser_infill = ri if ri and ri.get("present") else None
        uf = sp.get("under_flight") or {}
        if uf.get("enclosed") and cupboard is not None and cupboard.params.get("enclosed"):
            m.stair.under_flight = {"enclosed": True, "treads_enclosed": cupboard.params.get("treads_enclosed"),
                                    "cupboard_id": cupboard.id}
    m.sources.insert(0, "%s: openings (with door swing), stair treads, riser infill, railings, under-stair cupboard "
                        "and element ids; counts agree with the spec" % label)


def _optional(path: Path):
    try:
        return _j(path)
    except (OSError, ValueError):
        return None


def _profile_height(profile) -> float | None:
    by_x: dict = {}
    for x, z in profile:
        by_x.setdefault(round(x, 3), []).append(z)
    hs = [max(v) - min(v) for v in by_x.values() if len(v) >= 2]
    return round(min(hs), 3) if hs else None


def _rail_drop(what: str) -> float | None:
    return 1.8 if "north patio" in what else None
