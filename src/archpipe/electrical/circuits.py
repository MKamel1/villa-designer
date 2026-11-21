"""Circuit grouping (EA3), protection selection (EA8), cable sizing + voltage drop (EA5/EA6),
fault-loop / disconnection (EA7), phase balance (EA11) and the max-demand / feeder step (EA4)."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .. import contracts
from . import data, sizing, zones
from .demand import DemandItem, DemandResult, max_demand, phase_balance
from .model import Board, Equipment, House
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
    board: str = ""
    points: list = field(default_factory=list)        # (x, y) load points used for the route length
    external: bool = False
    extra_m: float = 0.0
    vd_origin_pct: float = 0.0                        # drop from the origin to this circuit's board


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
    boards: list = field(default_factory=list)
    board_feeders: dict = field(default_factory=dict)   # sub-board id -> feeder dict (same keys as `feeder`)
    board_demand: dict = field(default_factory=dict)
    board_ways: dict = field(default_factory=dict)


def next_in(ib: float, minimum: float = 6.0) -> float:
    for a in data.table("breaker_ladder_a")["rows"]:
        if a >= ib - 1e-9 and a >= minimum:
            return float(a)
    raise ValueError(f"no breaker for {ib} A")


def _centroid(r):
    return ((r.rect[0] + r.rect[2]) / 2.0, (r.rect[1] + r.rect[3]) / 2.0)


def _board_of(h: House, room_id: str) -> Board:
    return h.board_for_level(h.room(room_id).level)


def _manhattan_m(a, b) -> float:
    return (abs(a[0] - b[0]) + abs(a[1] - b[1])) / 1000.0


def _chain_m(start, pts) -> float:
    """Nearest-neighbour chain from the board through every point (a radial visits all its outlets)."""
    left = list(pts)
    cur, tot = start, 0.0
    while left:
        nxt = min(left, key=lambda p: _manhattan_m(cur, p))
        tot += _manhattan_m(cur, nxt)
        cur = nxt
        left.remove(nxt)
    return tot


def _route_m(h: House, c: "CircuitSpec") -> float:
    """Board through every load point (nearest-neighbour chain): Manhattan distance x 1.15 + vertical drops (policy; no wall/slab routing yet)."""
    b = next(bb for bb in h.board_list() if bb.id == c.board)
    if c.points and h.boards:
        d = _chain_m(b.xy, c.points) + c.extra_m
    else:
        d = _manhattan_m(b.xy, _centroid(h.room(c.rooms[0])))
    return d * ROUTE_ALLOWANCE + h.supply.drop_m


def _room_order(h: House, ids: list[str]) -> list[str]:
    cen = {r.id: _centroid(r) for r in h.rooms}
    return sorted(ids, key=lambda i: (round(cen[i][0] / 4000.0), cen[i][1]))


# ---- grouping ----------------------------------------------------------------------------------
def group_circuits(h: House, devs: list[Device]) -> list[CircuitSpec]:
    v = h.supply.v_phase
    pol = h.policy
    out: list[CircuitSpec] = []
    lum_xy = {l.id: l.xy for l in h.luminaires if l.xy}
    cen = {r.id: _centroid(r) for r in h.rooms}

    def lighting_circuit(board, rooms, bin_):
        w = sum(q.watts for q in bin_)
        ib = w / (v * LIGHTING_PF)
        ids = [i for q in bin_ for i in q.luminaire_ids]
        pts = [cen[rm] for rm in rooms]       # one point per room served; +4 m of loop-in/loop-out per room below
        extra = 4.0 * len(rooms)
        nm = f"Lighting {rooms[0]}" if len(rooms) == 1 else f"Lighting {rooms[0]} +{len(rooms) - 1}"
        c = CircuitSpec("", "lighting", nm, rooms, ids, ib, next_in(ib, 6.0), "B", 30.0, "A", "lighting", watts=w,
                        zone_ids=[q.id for q in bin_], board=board, points=pts, extra_m=extra if h.boards else 0.0)
        out.append(c)

    # lighting: zones packed first-fit into circuits of <= 10 A; a zone is never split
    if pol.get("lighting_pack") == "level":
        cap = float(pol.get("lighting_target_a", LIGHTING_MAX_A))
        by_board: dict[str, list] = {}
        for room in h.rooms:
            for z in h.zones:
                if z.room == room.id and z.layer != "emergency":
                    by_board.setdefault(_board_of(h, room.id).id, []).append(z)
        for bid, zs in by_board.items():
            order = _room_order(h, sorted({z.room for z in zs}))
            zs = sorted(zs, key=lambda z: (order.index(z.room), z.layer, z.id))
            bins: list[list] = [[]]
            for z in zs:
                cur = z.watts / (v * LIGHTING_PF)
                if bins[-1] and sum(q.watts for q in bins[-1]) / (v * LIGHTING_PF) + cur > cap + 1e-9:
                    bins.append([])
                bins[-1].append(z)
            for b in bins:
                if b:
                    lighting_circuit(bid, list(dict.fromkeys(q.room for q in b)), b)
    else:
        for room in h.rooms:
            zs = [z for z in h.zones if z.room == room.id and z.layer != "emergency"]
            bins2: list[list] = []
            for z in sorted(zs, key=lambda z: -z.watts):
                cur = z.watts / (v * LIGHTING_PF)
                for b in bins2:
                    if sum(q.watts for q in b) / (v * LIGHTING_PF) + cur <= LIGHTING_MAX_A + 1e-9:
                        b.append(z)
                        break
                else:
                    bins2.append([z])
            for b in bins2:
                lighting_circuit(_board_of(h, room.id).id, [room.id], b)

    # sockets: radials (kitchen worktop on its own 20 A circuit), <= 8 socket-outlets each
    def socket_circuit(board, nm, rooms, ds, amps, external=False):
        out.append(CircuitSpec("", "socket", f"{nm} {rooms[0]}" + (f" +{len(rooms) - 1}" if len(rooms) > 1 else ""), rooms, [d.id for d in ds],
                               amps, amps, "B", 30.0, "A", "sockets", board=board, points=[(d.x, d.y) for d in ds], external=external))

    cluster = pol.get("socket_pack") == "cluster"
    pending: dict[str, list[tuple[str, list]]] = {}
    for room in h.rooms:
        socks = [d for d in devs if d.room == room.id and d.kind in SOCKET_KINDS]
        if not socks:
            continue
        ext = room.kind == "outdoor"
        bid = _board_of(h, room.id).id
        wt = [d for d in socks if d.rule == "EA1-worktop-pitch"]
        rest = [d for d in socks if d.rule != "EA1-worktop-pitch"]
        for i in range(0, len(wt), MAX_SOCKETS_PER_RADIAL):
            socket_circuit(bid, "Worktop sockets", [room.id], wt[i:i + MAX_SOCKETS_PER_RADIAL], KITCHEN_RADIAL_A)
        if ext:
            for i in range(0, len(rest), MAX_SOCKETS_PER_RADIAL):
                socket_circuit(bid, "Garden sockets", [room.id], rest[i:i + MAX_SOCKETS_PER_RADIAL], SOCKET_RADIAL_A, external=True)
        elif cluster:
            pending.setdefault(bid, []).append((room.id, rest))
        else:
            for i in range(0, len(rest), MAX_SOCKETS_PER_RADIAL):
                socket_circuit(bid, "Sockets", [room.id], rest[i:i + MAX_SOCKETS_PER_RADIAL], SOCKET_RADIAL_A)
    for bid, items in pending.items():                      # cluster: next-fit over rooms in plan order, <= 8 outlets and <= 2 rooms
        order = _room_order(h, [i for i, _ in items])
        items = sorted(items, key=lambda t: order.index(t[0]))
        cur_rooms: list[str] = []
        cur: list = []
        def flush():
            if cur:
                socket_circuit(bid, "Sockets", list(cur_rooms), list(cur), SOCKET_RADIAL_A)
        for rid, ds in items:
            for i in range(0, len(ds), MAX_SOCKETS_PER_RADIAL):
                chunk = ds[i:i + MAX_SOCKETS_PER_RADIAL]
                if cur and (len(cur) + len(chunk) > MAX_SOCKETS_PER_RADIAL or (rid not in cur_rooms and len(cur_rooms) >= 2)):
                    flush()
                    cur_rooms, cur = [], []
                if rid not in cur_rooms:
                    cur_rooms.append(rid)
                cur.extend(chunk)
        flush()
        cur_rooms, cur = [], []

    # dedicated
    for e in h.equipment:
        ib = e.kw * 1000.0 / (v * e.pf)
        curve = "C" if e.kind in ("ac", "pump", "gate") else "B"
        srv = next((d for d in devs if d.serves == e.id), None)
        pt = (srv.x, srv.y) if srv else (e.xy if e.xy else cen[e.room])
        bid = e.board or _board_of(h, e.room).id
        out.append(CircuitSpec("", "dedicated", f"{e.name or e.kind} {e.id}", [e.room], [e.id], ib, next_in(ib), curve, 30.0, "A", e.cat,
                               watts=e.kw * 1000.0, board=bid, points=[pt], external=e.external, extra_m=e.extra_length_m))
    # ids: L/S/D numbering per board
    counters: dict[tuple[str, str], int] = {}
    pfx = {"lighting": "L", "socket": "S", "dedicated": "D"}
    for c in out:
        counters[(c.board, c.kind)] = counters.get((c.board, c.kind), 0) + 1
        c.id = f"{c.board}/{pfx[c.kind]}{counters[(c.board, c.kind)]}"
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
    total = _route_m(h, c)
    c.length_m = round(total, 1)
    b = next(bb for bb in h.board_list() if bb.id == c.board)
    if c.external:
        c.notes.append("external run: buried armoured cable (SWA) assumed, method D2 (IEC B.52.4, 3 loaded, conservative); ground temperature and soil resistivity not surveyed")
        return [Segment("buried SWA", total, 30.0, group_circuits=1)], TableSpec("iec_b524", method="D2")
    if c.kind == "lighting":
        amb = b.ambient_c if h.boards else h.supply.roof_ambient_c
        segs = [Segment("roof void", total * ROOF_SHARE_LIGHTING, amb, group_circuits=max(1, min(n_lighting, 6)), insulation_mm=0.0),
                Segment("wall drop", total * (1 - ROOF_SHARE_LIGHTING), 30.0, group_circuits=2)]
        return segs, TableSpec("whit_t47", col="in_insulation_2")
    grp = 1 if c.in_a >= 32.0 else max(1, min(n_other, 3))     # policy: a >= 32 A circuit runs in its own conduit
    segs = [Segment("wall/floor chase", total, 30.0, group_circuits=grp)]
    return segs, TableSpec("whit_t47", col="conduit_wall_2")


def _size_feed(ib: float, inn: float, length_m: float, ambient_c: float, system: str, v_phase: float, name: str = "incomer") -> dict:
    segs = [Segment(name, length_m, ambient_c, 1)]
    r = sizing.size_cable(ib, inn, segs, TableSpec("iec_b524", method="C"))
    v = sizing.vd_volts(r.csa_mm2, ib, length_m, system, "motor", source="g30") if r.ok else float("nan")
    pct = sizing.vd_percent(v, system, v_phase) if r.ok else float("nan")
    return {"ib_a": ib, "in_a": inn, "size": r, "vd_v": v, "vd_pct": pct, "system": system, "length_m": length_m,
            "vd_ph_v": sizing.phase_equivalent(v, system) if r.ok else float("nan")}


def size_feeder(h: House, dem: DemandResult, phase_loads: dict[str, float]) -> dict:
    s = h.supply
    tot = sum(phase_loads.values()) or 1.0
    line_a = dem.total_a * (max(phase_loads.values()) / tot) if s.phases == 3 else dem.total_a
    ib = line_a
    inn = s.main_breaker_a if s.main_breaker_a else next_in(ib)
    return _size_feed(ib, inn, s.feeder_length_m, s.feeder_ambient_c, "3ph" if s.phases == 3 else "1ph", s.v_phase)


def design(h: House, devs: list[Device]) -> Design:
    s = h.supply
    cs = group_circuits(h, devs)
    loads = assign_phases(cs, s.phases)
    items = [DemandItem(c.id, c.cat, c.in_a if c.kind == "socket" else c.ib_a, socket_on_cooker=False) for c in cs]
    dem = max_demand(items, s.premises, s.v_phase)
    feeder = size_feeder(h, dem, loads)
    boards = h.board_list()
    main = h.main_board()
    # sub-board feeders: from the main board, sized on the sub-board's own diversified demand (worst-phase share)
    bfeed: dict[str, dict] = {}
    bdem: dict[str, DemandResult] = {}
    for b in boards:
        mine = [c for c in cs if c.board == b.id]
        bdem[b.id] = max_demand([DemandItem(c.id, c.cat, c.in_a if c.kind == "socket" else c.ib_a) for c in mine], s.premises, s.v_phase) if mine else DemandResult(0.0)
        if b.parent is None:
            continue
        pl = {p: sum(c.ib_a for c in mine if c.phase == p) for p in loads}
        tot = sum(pl.values()) or 1.0
        line_a = bdem[b.id].total_a * (max(pl.values()) / tot) if s.phases == 3 else bdem[b.id].total_a
        par = next(x for x in boards if x.id == b.parent)
        z0 = h.level_z_mm.get(par.level, 0.0)
        z1 = h.level_z_mm.get(b.level, 0.0)
        length = _manhattan_m(par.xy, b.xy) * ROUTE_ALLOWANCE + abs(z1 - z0) / 1000.0 + 2 * 1.5
        f = _size_feed(line_a, next_in(line_a), length, s.feeder_ambient_c, "3ph" if s.phases == 3 else "1ph", s.v_phase, "sub-board feeder")
        f["from"], f["to"], f["phase_loads"] = par.id, b.id, pl
        bfeed[b.id] = f
    n_l = {b.id: sum(1 for c in cs if c.kind == "lighting" and c.board == b.id) for b in boards}
    n_o = {b.id: sum(1 for c in cs if c.kind != "lighting" and c.board == b.id) for b in boards}
    for c in cs:
        segs, spec = _segments(h, c, n_l[c.board], n_o[c.board])
        c.segments, c.spec = segs, spec
        kindvd = "light" if c.kind == "lighting" else "motor"
        c.vd_limit_pct = sizing.vd_limit_pct("lighting" if c.kind == "lighting" else "other")
        min_csa = 1.5 if c.kind == "lighting" else 2.5
        base_ok = feeder["size"].ok and (c.board not in bfeed or bfeed[c.board]["size"].ok)
        base_v = (feeder["vd_ph_v"] + (bfeed[c.board]["vd_ph_v"] if c.board in bfeed else 0.0)) if base_ok else 0.0

        def ok_vd(csa, c=c, kindvd=kindvd, base_v=base_v):
            v = sizing.vd_volts(csa, c.ib_a, c.length_m, "1ph", kindvd)
            return 100.0 * (base_v + v) / s.v_phase <= c.vd_limit_pct + 1e-9

        r = sizing.size_cable(c.ib_a, c.in_a, segs, spec, min_csa=min_csa, extra_ok=ok_vd if base_ok else None)
        if not r.ok and spec.kind != "iec_b524":     # table has no cell large enough (>16 mm2): conservative IEC B.52.4 three-loaded, method B2
            spec2 = TableSpec("iec_b524", method="B2")
            r = sizing.size_cable(c.ib_a, c.in_a, segs, spec2, min_csa=min_csa, extra_ok=ok_vd if base_ok else None)
            c.notes.append("size from IEC B.52.4 (3 loaded, conservative) because the BS 7671:1992 table stops at 16 mm2")
            c.spec = spec2
        c.size = r
        c.csa_mm2 = r.csa_mm2 or 0.0
        if r.ok:
            v = sizing.vd_volts(c.csa_mm2, c.ib_a, c.length_m, "1ph", kindvd)
            c.vd_pct = 100.0 * v / s.v_phase
            c.vd_origin_pct = 100.0 * base_v / s.v_phase
            c.vd_total_pct = c.vd_pct + c.vd_origin_pct
        _protection(h, c)
    ways_by: dict[str, int] = {}
    for b in boards:
        n = sum(1 for c in cs if c.board == b.id) + sum(1 for x in bfeed.values() if x["from"] == b.id)
        w = max(2, math.ceil(n / 0.8))
        ways_by[b.id] = w + w % 2
    d = Design(h, devs, cs, dem, feeder, loads, ways_by[boards[0].id], board=boards[0].id)
    d.boards, d.board_feeders, d.board_demand, d.board_ways = boards, bfeed, bdem, ways_by
    return d


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
        out.append(contracts.Circuit(c.id, c.board or d.board, c.kind, tuple(c.load_ids), round(c.ib_a, 3), c.in_a, c.rcd_ma, c.csa_mm2,
                                     c.length_m, round(c.vd_total_pct, 3)))
    return out
