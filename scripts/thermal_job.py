"""Worker entry for thermal studies. Runs under the thermal environment:

    <thermal_python> scripts/thermal_job.py --input job.json --epw <file.epw> --energyplus <path> --out <dir>

job.json: {"kind": "climate" | "study" | "cases" | "validate", "base": {...}, "sweep": {...}}
Prints one JSON document on stdout (EnergyPlus's own output goes to per-case logs).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from archpipe.execution_context import ContextError, project_context  # noqa: E402
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


def validate_daylight(radiance: Path, out: Path) -> dict:
    checks = []
    base = {"azimuth_deg": 0, "wwr": 0.3}
    r0 = t.daylight_factor(base, radiance, out / "v0")
    checks.append({"check": "sky normalisation: unobstructed upward probe reads DF 100 %",
                   "value": r0["sky_check_df"], "passed": abs(r0["sky_check_df"] - 100) <= 3})
    diff = (r0["df_avg"] - r0["lynes_adf_unobstructed"]) / r0["lynes_adf_unobstructed"]
    checks.append({"check": "simulated average DF vs simplified Lynes formula (Baker & Steemers p. 65)",
                   "sim": r0["df_avg"], "formula": r0["lynes_adf_unobstructed"], "diff": round(diff, 3),
                   "passed": abs(diff) <= 0.35})
    big = t.daylight_factor(dict(base, wwr=0.6), radiance, out / "v1")
    lowt = t.daylight_factor(dict(base, glass={"vt": 0.3}), radiance, out / "v2")
    over = t.daylight_factor(dict(base, overhang_m=1.2), radiance, out / "v3")
    fin = t.daylight_factor(dict(base, fin_m=0.6), radiance, out / "v4")
    checks.append({"check": "larger window raises DF", "ref": r0["df_avg"], "value": big["df_avg"],
                   "passed": big["df_avg"] > r0["df_avg"]})
    ratio = lowt["df_avg"] / r0["df_avg"]
    checks.append({"check": "halving VT roughly halves DF", "ratio": round(ratio, 2), "passed": 0.4 <= ratio <= 0.6})
    checks.append({"check": "overhang lowers DF", "ref": r0["df_avg"], "value": over["df_avg"],
                   "passed": over["df_avg"] < r0["df_avg"]})
    checks.append({"check": "fins lower DF", "ref": r0["df_avg"], "value": fin["df_avg"],
                   "passed": fin["df_avg"] < r0["df_avg"]})
    return {"passed": all(c["passed"] for c in checks), "checks": checks}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--epw", type=Path, required=True)
    ap.add_argument("--energyplus", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--radiance", type=Path)
    a = ap.parse_args(argv)
    try:
        project_context(
            ROOT,
            Path(__file__).resolve(),
            "thermal-job",
            inputs=[a.input, a.epw],
            output=a.out,
        )
    except ContextError as exc:
        print("PREFLIGHT FAILED: " + str(exc), file=sys.stderr)
        return 2
    job = json.loads(a.input.read_text())
    a.out.mkdir(parents=True, exist_ok=True)
    kind = job.get("kind")
    if kind == "climate":
        result = {"climate": t.climate_summary(a.epw)}
    elif kind == "study":
        result = {"results": t.window_study(job.get("base", {}), job.get("sweep", {}), a.epw, a.energyplus, a.out)}
    elif kind == "cases":          # explicit cases, e.g. one per concept room (scripts/concept.py thermal)
        result = {"results": [dict(t.run_case(c, a.epw, a.energyplus, a.out / f"case{i:03d}"), label=c.get("label"))
                              for i, c in enumerate(job["cases"])]}
    elif kind == "daylight":
        import itertools
        base, sweep = job.get("base", {}), job.get("sweep", {})
        keys = list(sweep)
        result = {"results": [t.daylight_factor(dict(base, **dict(zip(keys, v))), a.radiance, a.out / f"d{i:03d}")
                              for i, v in enumerate(itertools.product(*(sweep[k] for k in keys)))]}
    elif kind == "daylight-validate":
        result = validate_daylight(a.radiance, a.out)
    elif kind == "validate":
        result = validate(a.epw, a.energyplus, a.out)
    else:
        raise SystemExit(f"unknown kind {kind!r}")
    result.update({"kind": kind, "epw": a.epw.name, "assumptions_default": t.ASSUMPTIONS})
    print(json.dumps(result))
    return 0 if result.get("passed", True) else 1


if __name__ == "__main__":
    sys.exit(main())
