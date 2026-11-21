"""python -m archpipe.lightverify --design D1  ->  out/checks/LV.json and docs/lanes/LV-report.md"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCENE_CANDIDATES = ["/tmp/LV-scene/scene.json", "/tmp/RV1-scene/scene.json", "/tmp/laneP-render/scene.json"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m archpipe.lightverify")
    ap.add_argument("--design", default="D1")
    ap.add_argument("--scene", default=os.environ.get("LV_SCENE"), help="workstation-built scene.json (see docs/lanes/P-pipeline.md)")
    ap.add_argument("--rad-dir", default=str(ROOT / "knowledge" / "lighting-verify" / "radiance"), help="frozen per-cluster Radiance JSON (villa_run --tag lv, ab 6 + 12, merged L6b design)")
    ap.add_argument("--no-cycles", action="store_true")
    ap.add_argument("--skip-v8", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "docs" / "lanes" / "LV-report.md"))
    a = ap.parse_args(argv)
    if a.design != "D1":
        raise SystemExit("only design D1 exists")
    from ..contracts import CheckResult, write_results
    from ..lightcalc.villa import Villa
    from . import (report, scene_geom, v1_inputs, v2_placement, v3_sensors, v4_reference, v5_engines, v6_handcalc, v7_convergence,
                   v8_mutation, v10_manufacturer, v12_headroom, dialux_compare, dialux_pack)
    from .common import LayerResult, check
    villa = Villa()
    rad = Path(a.rad_dir)
    layers = {}
    layers["V1"] = v1_inputs.check_inputs(villa)
    layers["V2"] = v2_placement.check_placement(villa)
    scene = a.scene or next((s for s in SCENE_CANDIDATES if Path(s).exists()), None)
    ts = None
    if scene:
        ts = scene_geom.load_scene(scene)
        layers["V3"] = v3_sensors.check_sensors(villa, ts)
    else:
        L = LayerResult("V3")
        L.results.append(check("LV3", "not_evaluated", "all", (), message="no workstation-built scene.json found (use --scene)"))
        layers["V3"] = L
    v4 = v4_reference.load()
    if v4 is None:
        v4 = LayerResult("V4")
        v4.results.append(check("LV4", "not_evaluated", "all", (), message="run: python -m archpipe.lightverify.v4_reference"))
    layers["V4"] = v4
    if rad.exists() and any(rad.glob("*.json")):
        layers["V5"] = v5_engines.run(villa, rad, with_cycles=not a.no_cycles)
        layers["V6"] = v6_handcalc.run(villa, rad)
        layers["V7"] = v7_convergence.run(villa, rad)
    else:
        for k in ("V5", "V6", "V7"):
            L = LayerResult(k)
            L.results.append(check("L" + k, "not_evaluated", "all", (), message="no Radiance results in %s" % rad))
            layers[k] = L
    layers["V10"] = v10_manufacturer.run()
    layers["V11"] = dialux_compare.run(dialux_pack.OUT) if dialux_pack.OUT.exists() else LayerResult("V11")
    layers["V12"] = v12_headroom.run(villa)
    if a.skip_v8:
        L = LayerResult("V8")
        L.results.append(check("LV8", "not_evaluated", "all", (), message="skipped (--skip-v8)"))
        layers["V8"] = L
    else:
        layers["V8"] = v8_mutation.run(villa, rad if rad.exists() else rad, ts)
    results = [r for k in sorted(layers, key=lambda s: int(s[1:])) for r in layers[k].results]
    path = write_results("LV", results)
    Path(a.out).write_text(report.render(villa, layers), encoding="utf-8")
    counts = {}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1
    print("wrote %s and %s: %s" % (path, a.out, counts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
