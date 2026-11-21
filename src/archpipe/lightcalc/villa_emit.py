"""L6b: publish the control zones (contracts.LightingZone) and the villa check records.

    PYTHONPATH=src python -m archpipe.lightcalc.villa_emit --tag after

Writes knowledge/lighting/zones-d1.json (for the electrical lane), knowledge/lighting/villa-after-rows.json and merges the
villa CheckResults into out/checks/L6.json (+ knowledge/lighting/checks/L6.json).
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

from ..contracts import CheckResult, LightingZone, write_results
from . import emit, villa_checks as VC, villa_report as VR
from .villa import CLUSTERS, Villa, cluster_of, fixture_placements, zone_id, zone_layer

ROOT = Path(__file__).resolve().parents[3]
EMERGENCY_ROOMS = ("stair-b", "stair-gf", "landing-gf", "hall-b", "corridor", "gallery-end", "family")


def build_zones(v: Villa) -> list[LightingZone]:
    """One LightingZone per control zone: room x function. The contract layers are ambient | task | accent | decorative |
    exterior | emergency: the night layer on the stair and the basement route is `emergency` (battery-backed markers, see
    LA13), the other night glows (toe-kicks, kids' night lights) are `accent` at <= 10 %."""
    by = defaultdict(list)
    for f in v.fixtures:
        by[zone_id(f)].append(f)
    out = []
    for z, fs in sorted(by.items()):
        layer = zone_layer(fs[0])
        if layer == "night":
            layer = "emergency" if fs[0].room in EMERGENCY_ROOMS else "accent"
        watts = sum(p.watts or 0.0 for f in fs for p in fixture_placements(f))
        phase_cut = all(f.record.product for f in fs)
        dimming = "phase_cut" if phase_cut else ("switched" if layer == "emergency" else "dali2")
        out.append(LightingZone(z, fs[0].room, layer, tuple("lum-" + f.id for f in fs), round(watts, 1), dimming))
    return out


def zones_json(v: Villa, zones: list[LightingZone], scenes: dict) -> dict:
    return {"schema": "archpipe-lighting-zones/1", "design": "D1", "contract": "contracts.LightingZone (v0.1)",
            "units": {"watts": "W installed at the commissioned driver output"},
            "assumptions": ["generic fittings (strips, pendants, sconces, markers, desk lamps) at ASSUMED 90 lm/W",
                            "luminaire ids are the L2 model ids (lum-<fixture id>) of concept.villa_lighting.design()",
                            "dimming: LSEVO-only zones phase_cut (product datasheet: trailing/leading edge); other zones "
                            "dali2 (ASSUMED driver choice); emergency markers switched (maintained, battery-backed, ASSUMED)",
                            "night layer on the stair and the basement route is published as `emergency`"],
            "zones": [asdict(z) for z in zones], "scenes": scenes}


def markdown_table(before: list[dict], after: list[dict]) -> str:
    """Per-plane before (full scene, 100 %) -> after (owning scene) table for docs/lanes/L6b-villa-lighting.md."""
    b = {r["plane"]: r for r in before}
    lines = ["| room | plane | card lx | scene | before Em (x target) | before U0 | after Em | after Emin | after U0 | x target | LA1 | LA2 |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(after, key=lambda r: (r["room"], r["plane"])):
        o = b.get(r["plane"])
        if r["gauge"] == "minimum":
            la1 = "pass" if r["em"] >= r["target"] else "FAIL"
            la2 = "n/a"
        else:
            la1 = "pass" if 0.9 * r["target"] <= r["em"] <= 1.1 * r["target"] else "FAIL"
            la2 = "pass" if r["em"] <= 1.5 * r["target"] else "FAIL"
        bef = "%.0f (%.1fx)" % (o["em"], o["ratio"]) if o else "-"
        bu = "%.2f" % o["u0"] if o else "-"
        lines.append("| %s | %s | %d%s | %s | %s | %s | %.0f | %.0f | %.2f | %.2f | %s | %s |" % (
            r["room"], r["plane"], r["target"], " (min)" if r["gauge"] == "minimum" else "", r["scene"], bef, bu, r["em"],
            r["emin"], r["u0"], r["ratio"], la1, la2))
    return chr(10).join(lines) + chr(10)


def main(tag: str = "after", out_dir: str = "out/L6b"):
    from ..concept.villa_lighting import SCENES
    v = Villa()
    planes = v.planes()
    rows = []
    for cl in CLUSTERS:
        f = ROOT / out_dir / tag / (cl + ".json")
        if not f.exists():
            continue
        res = VR.ClusterRes.load(f)
        rows += VR.plane_rows(res, [p for p in planes if cluster_of(p.room) == cl], SCENES.get(cl, {}))
    (ROOT / "knowledge/lighting/villa-after-rows.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    before = json.loads((ROOT / "knowledge/lighting/villa-before-rows.json").read_text(encoding="utf-8"))
    (ROOT / "knowledge/lighting/villa-table.md").write_text(markdown_table(before, rows), encoding="utf-8")
    zones = build_zones(v)
    (ROOT / "knowledge/lighting/zones-d1.json").write_text(json.dumps(zones_json(v, zones, SCENES), indent=1), encoding="utf-8")
    res_list = emit.reference_results() + emit.dining_results() + VR.results_for(rows, "villa")
    res_list += VC.check_la6(v.fixtures) + VC.check_la8(v.fixtures) + VC.check_la9(v)
    res_list += VC.check_la13(v) + VC.check_la10_scenes(SCENES) + [VC.check_la10_night(v)]
    res_list += VC.check_la4(v, VC.sightlines(v)) + VC.check_la12(v)
    res_list += VC.check_v12(json.loads((ROOT / "knowledge/lighting/zone-drivers.json").read_text(encoding="utf-8")))
    res_list.append(CheckResult("LA4", "L6", "not_evaluated", "villa/study-UGR",
                                message="UGR (study, limit 19) needs a vertical-eye Radiance sensor for Lb and the CIE 190 worked "
                                        "example is not demonstrated (docs/lanes/L6-lighting-engine.md); luminance checks above run."))
    p = write_results("L6", res_list, root=ROOT / "out" / "checks")
    q = write_results("L6", res_list, root=ROOT / "knowledge" / "lighting" / "checks")
    print(p, q, len(res_list), "results,", len(zones), "zones")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="after")
    ap.add_argument("--out", default="out/L6b")
    a = ap.parse_args()
    main(a.tag, a.out)
