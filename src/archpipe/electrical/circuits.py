"""Circuit grouping (EA3), protection selection (EA8), cable sizing + voltage drop (EA5/EA6),
fault-loop / disconnection (EA7), phase balance (EA11) and the max-demand / feeder step (EA4)."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .. import contracts
from . import data, sizing, zones
from .demand import DemandItem, DemandResult, max_demand, phase_balance
from .model import Equipment, House
from .placement import SOCKET_KINDS, Device
from .sizing import Segment, SizeResult, TableSpec

LIGHTING_MAX_A = 10.0
LIGHTING_PF = 0.9
SOCKET_RADIAL_A = 16.0
KITCHEN_RADIAL_A = 20.0
MAX_SOCKETS_PER_RADIAL = 8
ROUTE_ALLOWANCE = 1.15
ROOF_SHARE_LIGHTING = 0.6
RHO_CU_MOHM_MM2_PER_M = 23.7     # Fig G29: R = 23.7 ohm.mm2/km / S  ==  23.7 mohm.mm2/m / S
CPC_NOTE = "CPC assumed equal in csa to the phase conductor (R1+R2 = 2 x phase)"
ELECTRONIC_LOAD_KINDS = {"lighting", "ac"}
CURVE_K = {"B": 5.0, "C": 10.0, "D": 20.0}     # upper end of the IEC 60898 magnetic range (Fig H28)


@dataclass
class CircuitSpec:
    id: str
    kind: str                  # lighting | socket | dedicated | elv
    name: str
    rooms: list[str]
    load_ids: list[str]
    ib_a: float
    in_a: float
    curve: str
    rcd_ma: float | None
    rcd_type: str
    cat: str                   # demand category
    watts: float = 0.0         # connected W (lighting: sum of zone W)
    phase: str = ""
    length_m: float = 0.0
    segments: list[Segment] = field(default_factory=list)
    spec: TableSpec | None = None
    size: SizeResult | None = None
    csa_mm2: float = 0.0
    vd_pct: float = 0.0        # this circuit only
    vd_total_pct: float = 0.0  # from the origin (feeder + circuit)
    vd_limit_pct: float = 5.0
    zs_ohm: float | None = None
    ze_used_ohm: float | None = None
    disconnect_s: float | None = None
    disconnect_limit_s: float | None = None
    protection_note: str = ""
    zone_ids: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class Design:
    house: House
    devices: list[Device]
    circuits: list[CircuitSpec]
    demand: DemandResult
    feeder: dict
    phase_loads: dict[str, float]
    ways: int
    board: str = "DB-GF"


def next_in(ib: float, minimum: float = 6.0) -> float:
    for a in data.table("breaker_ladder_a")["rows"]:
        if a >= ib - 1e-9 and a >= minimum:
            return float(a)
    raise ValueError(f"no breaker for {ib} A")


def _centroid(r):
    return ((r.rect[0] + r.rect[2]) / 2.0, (r.rect[1] + r.rect[3]) / 2.0)


def _route_m(h: House, room_id: str) -> float:
    cx, cy = _centroid(h.room(room_id))
    bx, by = h.supply.board_xy
    return (abs(cx - bx) + abs(cy - by)) / 1000.0 * ROUTE_ALLOWANCE + h.supply.drop_m


# ---- grouping ----------------------------------------------------------------------------------
def group_circuits(h: House, devs: list[Device]) -> list[CircuitSpec]:
    v = h.supply.v_phase
    out: list[CircuitSpec] = []
    # lighting: per room, zones packed first-fit into circuits of <= 10 A; a zone is never split
    for room in h.rooms:
        zs = [z for z in h.zones if z.room == room.id and z.layer != "emergency"]
        bins: list[list] = []
        for z in sorted(zs, key=lambda z: -z.watts):
            cur = z.watts / (v * LIGHTING_PF)
            for b in bins:
                if sum(q.watts for q in b) / (v * LIGHTING_PF) + cur <= LIGHTING_MAX_A + 1e-9:
                    b.append(z)
                    break
            else:
                bins.append([z])
        for b in bins:
            w = sum(q.watts for q in b)
            ib = w / (v * LIGHTING_PF)
            out.append(CircuitSpec("", "lighting", f"Lighting {room.id}", [room.id], [i for q in b for i in q.luminaire_ids],
                                   ib, next_in(ib, 6.0), "B", 30.0, "A", "lighting", watts=w, zone_ids=[q.id for q in b]))
    # sockets: radials per room (kitchen worktop on its own 20 A circuit), <= 8 socket-outlets each
    for room in h.rooms:
        socks = [d for d in devs if d.room == room.id and d.kind in SOCKET_KINDS]
        if not socks:
            continue
        groups = [("Worktop sockets", [d for d in socks if d.rule == "EA1-worktop-pitch"], KITCHEN_RADIAL_A),
                  ("Sockets", [d for d in socks if d.rule != "EA1-worktop-pitch"], SOCKET_RADIAL_A)] if room.kind == "kitchen" else \
                 [("Sockets", socks, SOCKET_RADIAL_A)]
        for nm, ds, a in groups:
            for i in range(0, len(ds), MAX_SOCKETS_PER_RADIAL):
                chunk = ds[i:i + MAX_SOCKETS_PER_RADIAL]
                out.append(CircuitSpec("", "socket", f"{nm} {room.id}", [room.id], [d.id for d in chunk], a, a, "B", 30.0, "A", "sockets"))
    # dedicated
    for e in h.equipment:
        ib = e.kw * 1000.0 / (v * e.pf)
        curve = "C" if e.kind in ("ac", "pump") else "B"
        out.append(CircuitSpec("", "dedicated", f"{e.kind} {e.id}", [e.room], [e.id], ib, next_in(ib), curve, 30.0, "A", e.cat, watts=e.kw * 1000.0))
    # ids: L/S/D numbering
    counters = {"lighting": 0, "socket": 0, "dedicated": 0}
    pfx = {"lighting": "L", "socket": "S", "dedicated": "D"}
    for c in out:
        counters[c.kind] += 1
        c.id = f"DB-GF/{pfx[c.kind]}{counters[c.kind]}"
    return out


# ---- phase balance (EA11) ------------------------------------------------------------------------
def assign_phases(circuits: list[CircuitSpec], phases: int) -> dict[str, float]:
    names = ["L1", "L2", "L3"][:phases]
    loads = {p: 0.0 for p in names}
    for c in sorted(circuits, key=lambda c: -c.ib_a):
        p = min(loads, key=loads.get)
        c.phase = p
        loads[p] += c.ib_a
    if phases == 3:   # local improvement: move one circuit if it reduces the spread
        improved = True
        while improved:
            improved = False
            spread = max(loads.values()) - min(loads.values())
            for c in circuits:
                for p in names:
                    if p == c.phase:
                        continue
                    trial = dict(loads)
                    trial[c.phase] -= c.ib_a
                    trial[p] += c.ib_a
                    if max(trial.values()) - min(trial.values()) < spread - 1e-9:
                        loads, c.phase, improved = trial, p, True
                        spread = max(loads.values()) - min(loads.values())
    return loads


# ---- sizing, vd, protection -----------------------------------------------------------------------
def _segments(h: House, c: CircuitSpec, n_lighting: int, n_other: int) -> tuple[list[Segment], TableSpec]:
    total = _route_m(h, c.rooms[0])
    c.length_m = round(total, 1)
    if c.kind == "lighting":
        segs = [Segment("roof void", total * ROOF_SHARE_LIGHTING, h.supply.roof_ambient_c, group_circuits=max(1, min(n_lighting, 6)), insulation_mm=0.0),
                Segment("wall drop", total * (1 - ROOF_SHARE_LIGHTING), 30.0, group_circuits=2)]
        return segs, TableSpec("whit_t47", col="in_insulation_2")
    grp = 1 if c.in_a >= 32.0 else max(1, min(n_other, 3))     # policy: a >= 32 A circuit runs in its own conduit
    segs = [Segment("wall/floor chase", total, 30.0, group_circuits=grp)]
    return segs, TableSpec("whit_t47", col="conduit_wall_2")


def size_feeder(h: House, dem: DemandResult, phase_loads: dict[str, float]) -> dict:
    s = h.supply
    tot = sum(phase_loads.values()) or 1.0
    line_a = dem.total_a * (max(phase_loads.values()) / tot) if s.phases == 3 else dem.total_a
    ib = line_a
    inn = s.main_breaker_a if s.main_breaker_a else next_in(ib)
    segs = [Segment("incomer", s.feeder_length_m, s.feeder_ambient_c, 1)]
    system = "3ph" if s.phases == 3 else "1ph"
    r = sizing.size_cable(ib, inn, segs, TableSpec("iec_b524", method="C"))
    v = sizing.vd_volts(r.csa_mm2, ib, s.feeder_length_m, system, "motor", source="g30") if r.ok else float("nan")
    pct = sizing.vd_percent(v, system, s.v_phase) if r.ok else float("nan")
    return {"ib_a": ib, "in_a": inn, "size": r, "vd_v": v, "vd_pct": pct, "system": system, "length_m": s.feeder_length_m,
            "vd_ph_v": sizing.phase_equivalent(v, system) if r.ok else float("nan")}


def design(h: House, devs: list[Device]) -> Design:
    s = h.supply
    cs = group_circuits(h, devs)
    loads = assign_phases(cs, s.phases)
    items = [DemandItem(c.id, c.cat, c.in_a if c.kind == "socket" else c.ib_a, socket_on_cooker=False) for c in cs]
    dem = max_demand(items, s.premises, s.v_phase)
    feeder = size_feeder(h, dem, loads)
    n_l = sum(1 for c in cs if c.kind == "lighting")
    n_o = len(cs) - n_l
    for c in cs:
        segs, spec = _segments(h, c, n_l, n_o)
        c.segments, c.spec = segs, spec
        kindvd = "light" if c.kind == "lighting" else "motor"
        c.vd_limit_pct = sizing.vd_limit_pct("lighting" if c.kind == "lighting" else "other")
        min_csa = 1.5 if c.kind == "lighting" else 2.5

        def ok_vd(csa, c=c, kindvd=kindvd):
            v = sizing.vd_volts(csa, c.ib_a, c.length_m, "1ph", kindvd)
            tot = feeder["vd_ph_v"] + v
            return 100.0 * tot / s.v_phase <= c.vd_limit_pct + 1e-9

        r = sizing.size_cable(c.ib_a, c.in_a, segs, spec, min_csa=min_csa, extra_ok=ok_vd if feeder["size"].ok else None)
        if not r.ok:     # table has no cell large enough (>16 mm2): conservative IEC B.52.4 three-loaded, method B2
            spec2 = TableSpec("iec_b524", method="B2")
            r = sizing.size_cable(c.ib_a, c.in_a, segs, spec2, min_csa=min_csa, extra_ok=ok_vd if feeder["size"].ok else None)
            c.notes.append("size from IEC B.52.4 (3 loaded, conservative) because the BS 7671:1992 table stops at 16 mm2")
            c.spec = spec2
        c.size = r
        c.csa_mm2 = r.csa_mm2 or 0.0
        if r.ok:
            v = sizing.vd_volts(c.csa_mm2, c.ib_a, c.length_m, "1ph", kindvd)
            c.vd_pct = 100.0 * v / s.v_phase
            c.vd_total_pct = c.vd_pct + (100.0 * feeder["vd_ph_v"] / s.v_phase if feeder["size"].ok else 0.0)
        _protection(h, c)
    ways = max(2, math.ceil(len(cs) / 0.8))
    ways += ways % 2
    return Design(h, devs, cs, dem, feeder, loads, ways)


def _protection(h: House, c: CircuitSpec) -> None:
    s = h.supply
    limit = None
    for row in data.table("disconnection_s")["rows"]:
        if row["uo_gt"] < s.v_phase <= row["uo_le"]:
            limit = row["tt"] if s.earthing == "TT" else row["tn"]
    c.disconnect_limit_s = limit
    if s.earthing == "TT":
        if s.ra_ohm is None or c.rcd_ma is None:
            c.protection_note = "RA not known"
            return
        c.zs_ohm = s.ra_ohm
        t5 = data.table("rcd_max_time_s_domestic_instantaneous")["rows"]["5"]
        c.disconnect_s = t5
        c.protection_note = f"RA {s.ra_ohm:g} ohm x IDn {c.rcd_ma:g} mA = {s.ra_ohm * c.rcd_ma / 1000.0:.2f} V (<= 50 V); RCD <= {t5} s at 5 x IDn"
    else:
        if s.ze_ohm is None or c.size is None or not c.size.ok:
            c.protection_note = "Ze not known"
            return
        r12 = RHO_CU_MOHM_MM2_PER_M * (1 / c.csa_mm2 + 1 / c.csa_mm2) * c.length_m / 1000.0
        c.zs_ohm = s.ze_ohm + r12
        c.ze_used_ohm = s.ze_ohm
        ia = CURVE_K[c.curve] * c.in_a
        c.disconnect_s = 0.1 if s.v_phase / c.zs_ohm >= ia else None     # instantaneous trip < 0.1 s (EIG F20)
        c.protection_note = f"Zs {c.zs_ohm:.3f} ohm, Uo/Zs {s.v_phase / c.zs_ohm:.0f} A vs {ia:g} A ({c.curve}); {CPC_NOTE}"


def to_contract(d: Design) -> list[contracts.Circuit]:
    out = []
    for c in d.circuits:
        out.append(contracts.Circuit(c.id, d.board, c.kind, tuple(c.load_ids), round(c.ib_a, 3), c.in_a, c.rcd_ma, c.csa_mm2,
                                     c.length_m, round(c.vd_total_pct, 3)))
    return out
