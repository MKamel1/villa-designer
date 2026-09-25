"""Worker entry for thermal studies. Runs under the thermal environment:

    <thermal_python> scripts/thermal_job.py --input job.json --epw <file.epw> --energyplus <path> --out <dir>

job.json: {"kind": "climate" | "study" | "validate", "base": {...}, "sweep": {...}}
Prints one JSON document on stdout (EnergyPlus's own output goes to per-case logs).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from archpipe import thermal as t  # noqa: E402


def validate(epw: Path, eplus: Path, out: Path) -> dict:
    checks = []
    stat = t.stat_monthly_means(epw.with_suffix(".stat")) if epw.with_suffix(".stat").is_file() else None
    ours = [v["mean_c"] for v in t.climate_summary(epw)["monthly"].values()]
    if stat:
        d = max(abs(a - b) for a, b in zip(ours, stat))
        checks.append({"check": "monthly mean dry-bulb vs the weather converter's .stat", "max_diff_c": round(d, 2),
                       "passed": d <= 0.15})
    runs = {}
    for az in (0, 90, 180, 270):
        runs[az] = t.run_case({"azimuth_deg": az, "wwr": 0.3}, epw, eplus, out / f"v_az{az}")
        hand = t.hand_vertical_incident(epw, az)
        eb = runs[az]["facade_beam_kwh_m2"]
        diff = (eb - hand["beam"]) / hand["beam"]
        checks.append({"check": f"facade direct (beam) solar az {az}: EnergyPlus vs hand geometry",
                       "energyplus_kwh_m2": eb, "hand_kwh_m2": round(hand["beam"], 1),
                       "diff": round(diff, 4), "passed": abs(diff) <= 0.02,
                       "info_total": {"energyplus_perez": runs[az]["facade_incident_kwh_m2"],
                                      "hand_isotropic": round(hand["total"], 1)}})
    order = sorted(runs, key=lambda a: runs[a]["facade_incident_kwh_m2"])
    checks.append({"check": "north facade receives the least solar radiation", "order": order, "passed": order[0] == 0})
    base = {"azimuth_deg": 180, "wwr": 0.3}
    big = t.run_case(dict(base, wwr=0.6), epw, eplus, out / "v_big")
    shade = t.run_case(dict(base, overhang_m=0.8), epw, eplus, out / "v_shade")
    lowg = t.run_case(dict(base, glass={"shgc": 0.25}), epw, eplus, out / "v_lowg")
    ref = runs[180]["cooling_kwh_m2"]
    checks.append({"check": "larger window raises cooling", "ref": ref, "value": big["cooling_kwh_m2"],
                   "passed": big["cooling_kwh_m2"] > ref})
    checks.append({"check": "overhang lowers cooling", "ref": ref, "value": shade["cooling_kwh_m2"],
                   "passed": shade["cooling_kwh_m2"] < ref})
    checks.append({"check": "lower SHGC lowers cooling", "ref": ref, "value": lowg["cooling_kwh_m2"],
                   "passed": lowg["cooling_kwh_m2"] < ref})
    return {"passed": all(c["passed"] for c in checks), "checks": checks}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--epw", type=Path, required=True)
    ap.add_argument("--energyplus", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    job = json.loads(a.input.read_text())
    a.out.mkdir(parents=True, exist_ok=True)
    kind = job.get("kind")
    if kind == "climate":
        result = {"climate": t.climate_summary(a.epw)}
    elif kind == "study":
        result = {"results": t.window_study(job.get("base", {}), job.get("sweep", {}), a.epw, a.energyplus, a.out)}
    elif kind == "validate":
        result = validate(a.epw, a.energyplus, a.out)
    else:
        raise SystemExit(f"unknown kind {kind!r}")
    result.update({"kind": kind, "epw": a.epw.name, "assumptions_default": t.ASSUMPTIONS})
    print(json.dumps(result))
    return 0 if result.get("passed", True) else 1


if __name__ == "__main__":
    sys.exit(main())
