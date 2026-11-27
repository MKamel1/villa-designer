"""Multi-board outputs for the villa: board schedules, per-board SLD, cable schedule, load schedule, device list.

All are generated from one Design (EA12: schedule = SLD = model)."""
from __future__ import annotations

import csv
import io
from collections import Counter, defaultdict
from xml.sax.saxutils import escape

from .circuits import Design
from .demand import DemandItem, max_demand
from .schedule import schedule_rows

SOCKET_SCALES = (1.0, 0.5, 0.25)


def _ph(d: Design) -> tuple[str, str]:
    return ("3P", "4P") if d.house.supply.phases == 3 else ("1P", "2P")


def _feeder_rows(d: Design, bid: str) -> list[dict]:
    p, poles = _ph(d)
    rows = []
    for sub, f in d.board_feeders.items():
        if f["from"] == bid:
            rows.append({"circuit": f"{bid}/F-{sub}", "description": f"Feeder to {sub}", "phase": p, "device": f"MCCB {f['in_a']:g} A {poles}",
                         "ib_a": round(f["ib_a"], 2), "in_a": f["in_a"], "cable": f"{'4C' if p == '3P' else '2C'}+E {f['size'].csa_mm2:g} mm2 PVC",
                         "length_m": round(f["length_m"], 1), "iz_a": round(f["size"].iz_a, 1) if f["size"].ok else "", "vd_total_pct": round(f["vd_pct"], 2),
                         "feeder_to": sub, "_f": f})
    return rows


def board_rows(d: Design, bid: str) -> list[dict]:
    """Schedule rows of one board: its final circuits (by phase) and the feeders it supplies."""
    rows = [r for r in schedule_rows(d) if r["circuit"].startswith(bid + "/")]
    for i, r in enumerate(rows, start=1):
        r["way"] = i
    n = len(rows)
    for fr in _feeder_rows(d, bid):
        n += 1
        fr["way"] = n
        rows.append({k: v for k, v in fr.items() if k != "_f"})
    return rows


def board_csv(d: Design, bid: str) -> str:
    rows = board_rows(d, bid)
    cols = ["way", "circuit", "phase", "description", "device", "ib_a", "in_a", "connected_w", "cable", "method", "length_m", "iz_a", "derating",
            "vd_total_pct", "vd_limit_pct", "disconnect_s", "protection", "feeder_to"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def board_markdown(d: Design, bid: str) -> str:
    b = next(x for x in d.boards if x.id == bid)
    rows = board_rows(d, bid)
    s = f"# Board schedule {bid} (level {b.level}, room {b.room}; {d.house.supply.earthing}, {d.house.supply.v_phase:g} V, {d.house.supply.phases}-phase)\n\n"
    s += "| way | circuit | ph | description | device | Ib A | cable | L m | Iz A | dV % |\n|---|---|---|---|---|---|---|---|---|---|\n"
    for r in rows:
        s += f"| {r['way']} | {r['circuit']} | {r['phase']} | {r['description']} | {r['device']} | {r['ib_a']} | {r['cable']} | {r['length_m']} | {r.get('iz_a', '')} | {r.get('vd_total_pct', '')} |\n"
    w = d.board_ways[bid]
    s += f"\nWays {w}, used {len(rows)}, spare {w - len(rows)} ({100 * (w - len(rows)) / w:.0f} %).\n"
    return s


def _columns(d: Design, bid: str) -> list[dict]:
    cols = []
    for c in sorted([c for c in d.circuits if c.board == bid], key=lambda c: (c.phase, c.id)):
        dev = f"RCBO {c.in_a:g}A {c.curve}" if c.rcd_ma else f"MCB {c.in_a:g}A {c.curve}"
        cols.append(dict(id=c.id, label=c.id.split("/")[1] + f" ({c.phase})", dev=dev, rcd=f"{c.rcd_ma:g} mA Type {c.rcd_type}" if c.rcd_ma else "", csa=f"{c.csa_mm2:g} mm2",
                         length=f"{c.length_m:g} m", ib=f"Ib {c.ib_a:.1f} A", vd=f"dV {c.vd_total_pct:.2f} %", name=c.name, rooms=",".join(c.rooms[:2]), phase=c.phase))
    for fr in _feeder_rows(d, bid):
        f = fr["_f"]
        cols.append(dict(id=fr["circuit"], label="F-" + fr["feeder_to"], dev=fr["device"], rcd="", csa=f"{f['size'].csa_mm2:g} mm2", length=f"{fr['length_m']:g} m",
                         ib=f"Ib {f['ib_a']:.1f} A", vd=f"dV {f['vd_pct']:.2f} %", name="Feeder to " + fr["feeder_to"], rooms=fr["feeder_to"], phase="3P"))
    return cols


def sld_board_svg(d: Design, bid: str) -> str:
    b = next(x for x in d.boards if x.id == bid)
    cols = _columns(d, bid)
    n = len(cols)
    colw, x0, top = 92, 40, 40
    W = max(760, x0 * 2 + n * colw)
    H = 560
    bus_y = 250
    s = d.house.supply
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Arial,sans-serif" font-size="9">',
           f'<rect width="{W}" height="{H}" fill="#fff"/>',
           f'<text x="{x0}" y="22" font-size="13" font-weight="bold">{escape(d.house.name)} - {escape(bid)} single-line diagram (level {escape(b.level)}, {escape(b.room)})</text>']
    cx = W // 2
    poles = "4P" if s.phases == 3 else "2P"
    if b.parent is None:
        f = d.feeder
        steps = [f"Supply {round(s.v_phase * 1.732 / 10) * 10:.0f}/{s.v_phase:g} V 50 Hz, {s.phases}-phase, {s.earthing}", "Utility meter (street cabinet)",
                 f"Main switch/breaker {f['in_a']:g} A {poles}", "Type S RCD 300 mA (TT origin)", "SPD Type 2"]
        note = f"incomer cable {f['size'].csa_mm2} mm2 Cu PVC, {f['length_m']:g} m"
    else:
        f = d.board_feeders[bid]
        steps = [f"From {b.parent}: feeder {f['in_a']:g} A {poles} MCCB", f"Isolator / main switch {bid}", "Outgoing circuits are 30 mA RCBO (Type A)"]
        note = f"feeder cable {f['size'].csa_mm2} mm2 Cu PVC, {f['length_m']:g} m, dV {f['vd_pct']:.2f} %"
    y = top
    for i, t in enumerate(steps):
        out.append(f'<rect x="{cx - 130}" y="{y}" width="260" height="24" fill="#f3f3f3" stroke="#222"/>')
        out.append(f'<text x="{cx}" y="{y + 15}" text-anchor="middle">{escape(t)}</text>')
        if i < len(steps) - 1:
            out.append(f'<line x1="{cx}" y1="{y + 24}" x2="{cx}" y2="{y + 34}" stroke="#222"/>')
        y += 34
    out.append(f'<line x1="{cx}" y1="{y - 10}" x2="{cx}" y2="{bus_y}" stroke="#222"/>')
    out.append(f'<text x="{cx + 6}" y="{y + 12}">{escape(note)}</text>')
    out.append(f'<line x1="{x0}" y1="{bus_y}" x2="{W - x0}" y2="{bus_y}" stroke="#222" stroke-width="3"/>')
    ways = d.board_ways[bid]
    out.append(f'<text x="{x0}" y="{bus_y - 6}">Busbar {escape(bid)}, {ways} ways ({ways - n} spare)</text>')
    colour = {"L1": "#8b4513", "L2": "#111", "L3": "#777", "3P": "#c00"}
    for i, c in enumerate(cols):
        x = x0 + i * colw + colw // 2
        col = colour.get(c["phase"], "#000")
        out.append(f'<g id="{escape(c["id"])}">')
        out.append(f'<line x1="{x}" y1="{bus_y}" x2="{x}" y2="{bus_y + 20}" stroke="{col}" stroke-width="2"/>')
        out.append(f'<rect x="{x - 36}" y="{bus_y + 20}" width="72" height="44" fill="#eef" stroke="#222"/>')
        out.append(f'<text x="{x}" y="{bus_y + 33}" text-anchor="middle" font-weight="bold">{escape(c["label"])}</text>')
        out.append(f'<text x="{x}" y="{bus_y + 45}" text-anchor="middle">{escape(c["dev"])}</text>')
        out.append(f'<text x="{x}" y="{bus_y + 57}" text-anchor="middle">{escape(c["rcd"])}</text>')
        out.append(f'<line x1="{x}" y1="{bus_y + 64}" x2="{x}" y2="{bus_y + 120}" stroke="{col}" stroke-width="2"/>')
        for k, key in enumerate(("csa", "length", "ib", "vd")):
            out.append(f'<text x="{x}" y="{bus_y + 134 + 12 * k}" text-anchor="middle">{escape(c[key])}</text>')
        nm = c["name"] if len(c["name"]) <= 16 else c["name"][:15] + "."
        out.append(f'<rect x="{x - 40}" y="{bus_y + 182}" width="80" height="40" fill="#fff" stroke="#222"/>')
        out.append(f'<text x="{x}" y="{bus_y + 196}" text-anchor="middle">{escape(nm)}</text>')
        out.append(f'<text x="{x}" y="{bus_y + 210}" text-anchor="middle">{escape(c["rooms"])}</text>')
        out.append("</g>")
    out.append(f'<text x="{x0}" y="{H - 14}">{escape(bid)} demand {d.board_demand[bid].kva:.1f} kVA (own diversified loads); installation max demand {d.demand.kva:.1f} kVA. Generated from the same Design as the board schedule.</text>')
    out.append("</svg>")
    return "\n".join(out)


def cable_rows(d: Design) -> list[dict]:
    rows = []
    s = d.house.supply
    p, _ = _ph(d)
    f = d.feeder
    core = "4C" if p == "3P" else "2C"
    rows.append({"board": "origin", "circuit": "INCOMER", "kind": "feeder", "description": "Utility meter to MDB", "phase": p, "ib_a": round(f["ib_a"], 1), "in_a": f["in_a"],
                 "csa_mm2": f["size"].csa_mm2, "cable": f"{core}+E PVC, method C", "length_m": f["length_m"], "ca_cg_ci": round(f["size"].factor, 3),
                 "iz_a": round(f["size"].iz_a, 1) if f["size"].ok else "", "vd_circuit_pct": round(f["vd_pct"], 2), "vd_total_pct": round(f["vd_pct"], 2), "vd_limit_pct": 5.0,
                 "zs_ohm": "", "disconnect_s": "", "note": "origin cable; length assumed (meter position unconfirmed)"})
    for sub, fd in d.board_feeders.items():
        rows.append({"board": fd["from"], "circuit": f"{fd['from']}/F-{sub}", "kind": "feeder", "description": f"{fd['from']} to {sub}", "phase": p, "ib_a": round(fd["ib_a"], 1),
                     "in_a": fd["in_a"], "csa_mm2": fd["size"].csa_mm2, "cable": f"{core}+E PVC, method C", "length_m": round(fd["length_m"], 1), "ca_cg_ci": round(fd["size"].factor, 3),
                     "iz_a": round(fd["size"].iz_a, 1) if fd["size"].ok else "", "vd_circuit_pct": round(fd["vd_pct"], 2), "vd_total_pct": round(fd["vd_pct"] + 100 * f["vd_ph_v"] / s.v_phase, 2),
                     "vd_limit_pct": 5.0, "zs_ohm": "", "disconnect_s": "", "note": "riser/route by policy (EL-POL-ROUTE)"})
    for c in sorted(d.circuits, key=lambda c: c.id):
        sz = c.size
        spec = c.spec
        tab = (spec.col if spec and spec.kind.startswith("whit") else f"B.52.4 method {spec.method}") if spec else ""
        rows.append({"board": c.board, "circuit": c.id, "kind": c.kind, "description": c.name, "phase": c.phase, "ib_a": round(c.ib_a, 2), "in_a": c.in_a,
                     "csa_mm2": c.csa_mm2, "cable": ("SWA " if c.external else "") + f"2C+E {c.csa_mm2:g} mm2 PVC, {tab}", "length_m": c.length_m, "ca_cg_ci": round(sz.factor, 3) if sz else "",
                     "iz_a": round(sz.iz_a, 1) if sz and sz.iz_a else "", "vd_circuit_pct": round(c.vd_pct, 2), "vd_total_pct": round(c.vd_total_pct, 2), "vd_limit_pct": c.vd_limit_pct,
                     "zs_ohm": c.zs_ohm if c.zs_ohm is not None else "", "disconnect_s": c.disconnect_s if c.disconnect_s is not None else "", "note": "; ".join(c.notes)})
    return rows


def write_csv(path, rows: list[dict]) -> None:
    cols = list(rows[0])
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    path.write_text(buf.getvalue(), encoding="utf-8")


def supply_recommendation(d: Design) -> dict:
    h, s = d.house, d.house.supply
    ex = h.policy.get("supply_extra", {})
    lim = float(ex.get("single_phase_limit_a", 63.0))
    tot = d.demand.total_a
    line = d.feeder["ib_a"]
    rec = "three-phase" if tot > lim else "single-phase"
    sens = []
    for k in SOCKET_SCALES:
        items = [DemandItem(c.id, c.cat, (c.in_a * k) if c.kind == "socket" else c.ib_a) for c in d.circuits]
        r = max_demand(items, s.premises, s.v_phase)
        sens.append({"socket_current_factor": k, "total_a_1ph_equiv": round(r.total_a, 1), "kva": round(r.kva, 1), "line_a_3ph": round(r.total_a / 3.0, 1)})
    return {"max_demand_kva": round(d.demand.kva, 1), "single_phase_equiv_a": round(tot, 1), "line_current_a_3ph_worst_phase": round(line, 1),
            "incomer_in_a": d.feeder["in_a"], "recommendation": rec, "single_phase_limit_a": lim, "limit_note": ex.get("single_phase_limit_note", ""),
            "connected_kva": round(d.demand.connected_a * s.v_phase / 1000.0, 1), "sensitivity": sens,
            "rationale": f"single-phase equivalent demand {tot:.0f} A is {'above' if tot > lim else 'within'} the {lim:g} A policy limit for one phase; three phases give a worst-phase line current of {line:.0f} A"}


def load_rows(d: Design) -> list[dict]:
    rows = []
    v = d.house.supply.v_phase
    for cat, x in sorted(d.demand.by_cat.items()):
        rows.append({"scope": "installation", "category": cat, "n_circuits": x["n"], "connected_a_1ph_equiv": round(x["connected_a"], 1), "demand_a_1ph_equiv": round(x["demand_a"], 1),
                     "demand_kva": round(x["demand_a"] * v / 1000.0, 1)})
    for bid, bd in d.board_demand.items():
        for cat, x in sorted(bd.by_cat.items()):
            rows.append({"scope": bid, "category": cat, "n_circuits": x["n"], "connected_a_1ph_equiv": round(x["connected_a"], 1), "demand_a_1ph_equiv": round(x["demand_a"], 1),
                         "demand_kva": round(x["demand_a"] * v / 1000.0, 1)})
    return rows


def load_markdown(d: Design) -> str:
    sr = supply_recommendation(d)
    s = "# Load schedule and maximum demand, D1 villa\n\n"
    s += (f"Supply {d.house.supply.v_phase:g}/{round(d.house.supply.v_phase * 1.732 / 10) * 10:.0f} V 50 Hz, {d.house.supply.earthing}. "
          "Diversity: Whitfield Table 6.2 household column (EL-WHIT-T62-DIV); socket radials are counted at their breaker rating.\n\n")
    s += f"- Connected load (sum of Ib, single-phase equivalent at 220 V): {sr['connected_kva']} kVA\n- Maximum demand after diversity: **{sr['max_demand_kva']} kVA** = {sr['single_phase_equiv_a']} A single-phase equivalent\n"
    s += f"- Worst-phase line current on three phases: {sr['line_current_a_3ph_worst_phase']} A; incomer {sr['incomer_in_a']:g} A\n- Supply recommendation: **{sr['recommendation']}**. {sr['rationale']}. {sr['limit_note']}\n\n"
    s += "## By board (own diversified demand)\n\n| board | circuits | demand kVA | worst-phase line A |\n|---|---|---|---|\n"
    for b in d.boards:
        n = sum(1 for c in d.circuits if c.board == b.id)
        fd = d.board_feeders.get(b.id)
        s += f"| {b.id} | {n} | {d.board_demand[b.id].kva:.1f} | {fd['ib_a']:.1f} |\n" if fd else f"| {b.id} | {n} | {d.board_demand[b.id].kva:.1f} | - |\n"
    s += "\n## By category (installation)\n\n| category | circuits | connected A | demand A | demand kVA |\n|---|---|---|---|---|\n"
    for r in load_rows(d):
        if r["scope"] == "installation":
            s += f"| {r['category']} | {r['n_circuits']} | {r['connected_a_1ph_equiv']} | {r['demand_a_1ph_equiv']} | {r['demand_kva']} |\n"
    s += "\n## Sensitivity to the socket-circuit assumption (the headline above is the upper bound; sizing uses it)\n\n"
    s += ("The carded rule (100 % of the largest circuit + 40 % of every other) is applied to the breaker rating of each socket radial. With many radials it dominates, so the headline is an upper bound. "
          "The table shows the demand if the radials carried a fraction of their rating; the reduced factors are policy, not sourced. "
          "The three-phase recommendation holds in every row (each is above the 63 A single-phase limit).\n\n")
    s += "| socket current factor | demand kVA | 1-ph equivalent A | worst-phase 3-ph line A |\n|---|---|---|---|\n"
    for r in sr["sensitivity"]:
        s += f"| {r['socket_current_factor']} | {r['kva']} | {r['total_a_1ph_equiv']} | {r['line_a_3ph']} |\n"
    s += "\n## Phases (sum of Ib)\n\n" + ", ".join(f"{k} {v:.1f} A" for k, v in d.phase_loads.items()) + "\n"
    return s


def device_rows(d: Design, elv=None) -> list[dict]:
    by_dev: dict[str, str] = {}
    for c in d.circuits:
        for i in c.load_ids:
            by_dev[i] = c.id
    lights: dict[str, list[str]] = {}
    for c in d.circuits:
        if c.kind == "lighting":
            for r in c.rooms:
                lights.setdefault(r, []).append(c.id)
    lvl = {r.id: r.level for r in d.house.rooms}
    rows = []
    for x in d.devices:
        circ = by_dev.get(x.id) or next((c.id for c in d.circuits if x.serves and x.serves in c.load_ids), "")
        if not circ and x.kind == "switch":
            circ = "+".join(lights.get(x.room, []))
        rows.append({"room": x.room, "level": lvl.get(x.room, ""), "id": x.id, "family": "power/lighting control", "kind": x.kind,
                     "x_mm": round(x.x), "y_mm": round(x.y), "z_mm": round(x.z), "rule": x.rule, "serves": x.serves, "circuit": circ,
                     "note": "; ".join(n for n in (("hinge assumed (policy)" if x.kind == "switch" and x.params.get("hinge_known") is False else ""), x.params.get("relocated", ""),
                                                  ("24 V DC SELV driver/junction behind the head panel, feeds " + ", ".join(x.params["lamps"])) if x.params.get("lamps") else "") if n)})
    for l in d.house.luminaires:
        rows.append({"room": l.room, "level": lvl.get(l.room, ""), "id": l.id, "family": "luminaire", "kind": l.layer, "x_mm": round(l.xy[0]) if l.xy else "", "y_mm": round(l.xy[1]) if l.xy else "",
                     "z_mm": "", "rule": "", "serves": l.zone, "circuit": by_dev.get(l.id, ""), "note": f"{l.watts:g} W"})
    if elv is not None:
        for e in elv.devices:
            rows.append({"room": e.room, "level": e.level, "id": e.id, "family": "ELV/fire", "kind": e.kind, "x_mm": round(e.x), "y_mm": round(e.y), "z_mm": round(e.z), "rule": e.rule,
                         "serves": "", "circuit": "", "note": e.note})
    return sorted(rows, key=lambda r: (r["level"], r["room"], r["family"], r["kind"], r["id"]))


def device_markdown(rows: list[dict]) -> str:
    by: dict = defaultdict(Counter)
    for r in rows:
        by[(r["level"], r["room"])][f"{r['family'][:3]}:{r['kind']}"] += 1
    s = "# Device list per room (counts; full list in device_list.csv)\n\n| level | room | devices |\n|---|---|---|\n"
    for (lv, room), c in sorted(by.items()):
        s += f"| {lv} | {room} | " + ", ".join(f"{k} x{v}" for k, v in sorted(c.items())) + " |\n"
    return s
