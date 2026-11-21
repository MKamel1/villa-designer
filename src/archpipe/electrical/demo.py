"""Run the engine on the test house: board schedule, SLD SVG, out/checks/L7.json.

    PYTHONPATH=src python -m archpipe.electrical.demo [house.json] [--out DIR]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .. import contracts
from . import checks, circuits, placement, schedule
from .model import load_house

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_HOUSE = ROOT / "tests" / "electrical" / "fixtures" / "test_house.json"


def run(house_path: Path = DEFAULT_HOUSE, out_dir: Path | None = None, checks_root: Path | str | None = None) -> dict:
    h = load_house(house_path)
    devs = placement.place_devices(h)
    d = circuits.design(h, devs)
    svg = schedule.sld_svg(d)
    res = checks.run_checks(d, svg)
    out_dir = Path(out_dir) if out_dir else ROOT / "out" / "electrical"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "board_schedule.csv").write_text(schedule.schedule_csv(d), encoding="utf-8")
    (out_dir / "board_schedule.md").write_text(schedule.schedule_markdown(d), encoding="utf-8")
    (out_dir / "sld.svg").write_text(svg, encoding="utf-8")
    (out_dir / "circuits.json").write_text(json.dumps([c.__dict__ for c in circuits.to_contract(d)], indent=1, default=str), encoding="utf-8")
    (out_dir / "devices.csv").write_text("id,kind,room,x_mm,y_mm,z_mm,rule,serves\n" + "\n".join(
        f"{x.id},{x.kind},{x.room},{x.x:.0f},{x.y:.0f},{x.z:.0f},{x.rule},{x.serves}" for x in d.devices) + "\n", encoding="utf-8")
    path = contracts.write_results("L7", res, checks_root if checks_root is not None else ROOT / "out" / "checks")
    return {"design": d, "results": res, "checks_path": path, "out_dir": out_dir}


def summary(res) -> dict:
    from collections import Counter
    c = Counter((r.criterion, r.status) for r in res)
    return {f"{k[0]}:{k[1]}": v for k, v in sorted(c.items())}


if __name__ == "__main__":
    args = sys.argv[1:]
    out = Path(args[args.index("--out") + 1]) if "--out" in args else None
    house = Path(args[0]) if args and not args[0].startswith("--") else DEFAULT_HOUSE
    r = run(house, out)
    print(json.dumps(summary(r["results"]), indent=1))
    print("checks:", r["checks_path"])
