"""Board schedule (CSV/markdown) and single-line diagram (SVG) generated from one Design (EA12)."""
from __future__ import annotations

import csv
import io
from xml.sax.saxutils import escape

from .circuits import Design


def schedule_rows(d: Design) -> list[dict]:
    rows = []
    for way, c in enumerate(sorted(d.circuits, key=lambda c: (c.phase, c.id)), start=1):
        rcd = f"RCBO {c.in_a:g} A {c.curve} {c.rcd_ma:g} mA Type {c.rcd_type}" if c.rcd_ma else f"MCB {c.in_a:g} A {c.curve}"
        sz = c.size
        rows.append({
            "way": way, "circuit": c.id, "phase": c.phase, "description": c.name, "device": rcd,
            "ib_a": round(c.ib_a, 2), "in_a": c.in_a, "connected_w": round(c.watts) if c.watts else "",
            "cable": f"2C+E {c.csa_mm2:g} mm2 PVC" if c.csa_mm2 else "NOT SIZED",
            "method": (c.spec.col if c.spec and c.spec.kind.startswith("whit") else (c.spec.method if c.spec else "")),
            "length_m": c.length_m, "iz_a": round(sz.iz_a, 1) if sz and sz.iz_a else "",
            "derating": round(sz.factor, 3) if sz else "", "vd_total_pct": round(c.vd_total_pct, 2),
            "vd_limit_pct": c.vd_limit_pct, "disconnect_s": c.disconnect_s if c.disconnect_s is not None else "",
            "protection": c.protection_note,
        })
    return rows


def schedule_csv(d: Design) -> str:
    rows = schedule_rows(d)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def schedule_markdown(d: Design) -> str:
    rows = schedule_rows(d)
    cols = ["way", "circuit", "phase", "description", "device", "ib_a", "cable", "length_m", "iz_a", "vd_total_pct"]
    s = f"# Board schedule {d.board} ({d.house.supply.earthing}, {d.house.supply.v_phase:g} V, {d.house.supply.phases}-phase)\n\n"
    s += "| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n"
    for r in rows:
        s += "| " + " | ".join(str(r[c]) for c in cols) + " |\n"
    spare = d.ways - len(d.circuits)
    s += f"\nWays {d.ways}, used {len(d.circuits)}, spare {spare} ({100 * spare / d.ways:.0f} %).\n"
    s += f"Max demand {d.demand.total_a:.1f} A single-phase equivalent, {d.demand.kva:.1f} kVA; incomer {d.feeder['in_a']:g} A, "
    s += f"{d.feeder['size'].csa_mm2} mm2 (Ib {d.feeder['ib_a']:.1f} A, vd {d.feeder['vd_pct']:.2f} %).\n"
    s += "\nPhase loads (sum of Ib): " + ", ".join(f"{k} {v:.1f} A" for k, v in d.phase_loads.items()) + "\n"
    return s


def sld_svg(d: Design) -> str:
    cs = sorted(d.circuits, key=lambda c: (c.phase, c.id))
    n = len(cs)
    colw, x0, top = 92, 40, 40
    W = max(760, x0 * 2 + n * colw)
    H = 560
    bus_y = 250
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Arial,sans-serif" font-size="9">',
           f'<rect width="{W}" height="{H}" fill="#fff"/>',
           f'<text x="{x0}" y="22" font-size="13" font-weight="bold">{escape(d.house.name)} - {escape(d.board)} single-line diagram</text>']
    cx = W // 2
    s = d.house.supply
    f = d.feeder
    steps = [f"Supply {round(s.v_phase * 1.732 / 10) * 10:.0f}/{s.v_phase:g} V 50 Hz, {s.phases}-phase, {s.earthing}",
             "Utility meter",
             f"Main switch/breaker {f['in_a']:g} A 4P",
             "Type S RCD 300 mA (TT origin)",
             "SPD Type 2"]
    y = top
    for i, t in enumerate(steps):
        out.append(f'<rect x="{cx - 120}" y="{y}" width="240" height="24" fill="#f3f3f3" stroke="#222"/>')
        out.append(f'<text x="{cx}" y="{y + 15}" text-anchor="middle">{escape(t)}</text>')
        if i < len(steps) - 1:
            out.append(f'<line x1="{cx}" y1="{y + 24}" x2="{cx}" y2="{y + 34}" stroke="#222"/>')
        y += 34
    out.append(f'<line x1="{cx}" y1="{y - 10}" x2="{cx}" y2="{bus_y}" stroke="#222"/>')
    out.append(f'<text x="{cx + 6}" y="{y + 12}">incomer cable {f["size"].csa_mm2} mm2 Cu PVC, {f["length_m"]:g} m</text>')
    out.append(f'<line x1="{x0}" y1="{bus_y}" x2="{W - x0}" y2="{bus_y}" stroke="#222" stroke-width="3"/>')
    out.append(f'<text x="{x0}" y="{bus_y - 6}">Busbar {escape(d.board)}, {d.ways} ways ({d.ways - n} spare)</text>')
    colour = {"L1": "#8b4513", "L2": "#111", "L3": "#777"}
    for i, c in enumerate(cs):
        x = x0 + i * colw + colw // 2
        col = colour.get(c.phase, "#000")
        out.append(f'<g id="{escape(c.id)}">')
        out.append(f'<line x1="{x}" y1="{bus_y}" x2="{x}" y2="{bus_y + 20}" stroke="{col}" stroke-width="2"/>')
        out.append(f'<rect x="{x - 36}" y="{bus_y + 20}" width="72" height="44" fill="#eef" stroke="#222"/>')
        out.append(f'<text x="{x}" y="{bus_y + 33}" text-anchor="middle" font-weight="bold">{escape(c.id.split("/")[1])} ({c.phase})</text>')
        dev = f"RCBO {c.in_a:g}A {c.curve}" if c.rcd_ma else f"MCB {c.in_a:g}A {c.curve}"
        out.append(f'<text x="{x}" y="{bus_y + 45}" text-anchor="middle">{escape(dev)}</text>')
        rcdtxt = f"{c.rcd_ma:g} mA Type {c.rcd_type}" if c.rcd_ma else ""
        out.append(f'<text x="{x}" y="{bus_y + 57}" text-anchor="middle">{rcdtxt}</text>')
        out.append(f'<line x1="{x}" y1="{bus_y + 64}" x2="{x}" y2="{bus_y + 120}" stroke="{col}" stroke-width="2"/>')
        out.append(f'<text x="{x}" y="{bus_y + 134}" text-anchor="middle">{c.csa_mm2:g} mm2</text>')
        out.append(f'<text x="{x}" y="{bus_y + 146}" text-anchor="middle">{c.length_m:g} m</text>')
        out.append(f'<text x="{x}" y="{bus_y + 158}" text-anchor="middle">Ib {c.ib_a:.1f} A</text>')
        out.append(f'<text x="{x}" y="{bus_y + 170}" text-anchor="middle">dV {c.vd_total_pct:.2f} %</text>')
        nm = c.name if len(c.name) <= 16 else c.name[:15] + "."
        out.append(f'<rect x="{x - 40}" y="{bus_y + 182}" width="80" height="40" fill="#fff" stroke="#222"/>')
        out.append(f'<text x="{x}" y="{bus_y + 196}" text-anchor="middle">{escape(nm)}</text>')
        out.append(f'<text x="{x}" y="{bus_y + 210}" text-anchor="middle">{escape(",".join(c.rooms))}</text>')
        out.append("</g>")
    out.append(f'<text x="{x0}" y="{H - 14}">Max demand {d.demand.kva:.1f} kVA ({d.demand.total_a:.1f} A single-phase equiv.), '
               f'phases: {", ".join(f"{k} {v:.0f} A" for k, v in d.phase_loads.items())}. Generated from the same Design as the board schedule.</text>')
    out.append("</svg>")
    return "\n".join(out)
