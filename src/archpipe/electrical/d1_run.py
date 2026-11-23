"""Run the electrical engine on the D1 villa.

    PYTHONPATH=src python -m archpipe.electrical.d1_run [--out DIR] [--docs DIR] [--data DIR]

Writes board schedules, SLDs, cable schedule, load schedule, device list, ELV list and summary.json to DIR
(default out/electrical/d1), out/checks/L7.json, and a copy of the small outputs: markdown to --docs
(docs/lanes/L7b-d1, the only docs path lane L7b owns is *.md) and csv/svg/json to --data (tests/electrical/d1).
"""
from __future__ import annotations

from archpipe.safe_io import copy_file
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

from .. import contracts
from . import checks, circuits, elv, outputs, placement, villa

ROOT = Path(__file__).resolve().parents[3]
COPY = ["board_schedule_MDB.csv", "board_schedule_DB-B.csv", "board_schedule_DB-GF.csv", "board_schedule_MDB.md", "board_schedule_DB-B.md", "board_schedule_DB-GF.md",
        "sld_MDB.svg", "sld_DB-B.svg", "sld_DB-GF.svg", "cable_schedule.csv", "load_schedule.md", "load_schedule.csv", "device_list.csv", "device_list_by_room.md",
        "elv_devices.csv", "summary.json", "L7.json"]


def run(out_dir: Path | None = None, docs_dir: Path | None = None, data_dir: Path | None = None, checks_root: Path | str | None = None) -> dict:
    h = villa.load_villa()
    devs = placement.place_devices(h)
    d = circuits.design(h, devs)
    lay = elv.build_layout(h, devs)
    svgs = {b.id: outputs.sld_board_svg(d, b.id) for b in d.boards}
    res = checks.run_checks(d, svgs=svgs, elv=lay)
    out_dir = Path(out_dir) if out_dir else ROOT / "out" / "electrical" / "d1"
    out_dir.mkdir(parents=True, exist_ok=True)
    for b in d.boards:
        (out_dir / f"board_schedule_{b.id}.csv").write_text(outputs.board_csv(d, b.id), encoding="utf-8")
        (out_dir / f"board_schedule_{b.id}.md").write_text(outputs.board_markdown(d, b.id), encoding="utf-8")
        (out_dir / f"sld_{b.id}.svg").write_text(svgs[b.id], encoding="utf-8")
    outputs.write_csv(out_dir / "cable_schedule.csv", outputs.cable_rows(d))
    outputs.write_csv(out_dir / "load_schedule.csv", outputs.load_rows(d))
    (out_dir / "load_schedule.md").write_text(outputs.load_markdown(d), encoding="utf-8")
    drows = outputs.device_rows(d, lay)
    outputs.write_csv(out_dir / "device_list.csv", drows)
    (out_dir / "device_list_by_room.md").write_text(outputs.device_markdown(drows), encoding="utf-8")
    outputs.write_csv(out_dir / "elv_devices.csv", [{"id": e.id, "kind": e.kind, "room": e.room, "level": e.level, "x_mm": round(e.x), "y_mm": round(e.y), "z_mm": round(e.z), "rule": e.rule, "note": e.note} for e in lay.devices])
    (out_dir / "circuits.json").write_text(json.dumps([c.__dict__ for c in circuits.to_contract(d)], indent=1, default=str), encoding="utf-8")
    cs = Counter((r.criterion, r.status) for r in res)
    summary = {
        "design": "D1", "supply": outputs.supply_recommendation(d),
        "boards": {b.id: {"level": b.level, "room": b.room, "circuits": sum(1 for c in d.circuits if c.board == b.id), "ways": d.board_ways[b.id],
                          "demand_kva": round(d.board_demand[b.id].kva, 1)} for b in d.boards},
        "circuits": {"total": len(d.circuits), **dict(Counter(c.kind for c in d.circuits))},
        "devices": dict(Counter(x.kind for x in d.devices)), "elv": dict(Counter(x.kind for x in lay.devices)),
        "adb": lay.adb, "storey_area_m2": lay.storey_area_m2, "provisional_zones": h.provisional_zones,
        "phase_loads_a": {k: round(v, 1) for k, v in d.phase_loads.items()},
        "checks": {f"{k[0]}:{k[1]}": v for k, v in sorted(cs.items())},
        "flags": h.flags,
        "equipment_assumed": [{"id": e.id, "room": e.room, "kw": e.kw, "reason": e.reason} for e in h.equipment],
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    cp = contracts.write_results("L7", res, checks_root if checks_root is not None else ROOT / "out" / "checks")
    copy_file(cp, out_dir / "L7.json")
    for dest, want in ((docs_dir, lambda f: f.endswith(".md")), (data_dir, lambda f: not f.endswith(".md"))):
        if dest:
            dest = Path(dest)
            dest.mkdir(parents=True, exist_ok=True)
            for f in COPY:
                if want(f) and (out_dir / f).exists():
                    copy_file(out_dir / f, dest / f)
    return {"design": d, "results": res, "layout": lay, "house": h, "summary": summary, "out_dir": out_dir, "checks_path": cp}


if __name__ == "__main__":
    a = sys.argv[1:]
    out = Path(a[a.index("--out") + 1]) if "--out" in a else None
    docs = Path(a[a.index("--docs") + 1]) if "--docs" in a else None
    data = Path(a[a.index("--data") + 1]) if "--data" in a else None
    r = run(out, docs, data)
    print(json.dumps({k: r["summary"][k] for k in ("supply", "boards", "circuits", "checks")}, indent=1))
