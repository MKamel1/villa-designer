"""python -m archpipe.lightverify --design D1  ->  out/checks/LV.json and docs/lanes/LV-report.md"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCENE_CANDIDATES = ["/tmp/LV-scene2/scene.json", "/home/omar/archpipe/lanes/RA2/out/ra2/prod/scene.json", "/tmp/LV-scene/scene.json", "/tmp/RV1-scene/scene.json", "/tmp/laneP-render/scene.json"]


def regen_radiance(rad: Path, freeze: bool) -> Path:
    """Run the engine's own Radiance driver on the current design (the heavy part of V5-V7) and return the directory of results."""
    import shutil
    import subprocess
    out = ROOT / "out" / "LV-regen"
    env = dict(os.environ, ARCHPIPE_L6_LOCAL="1", PYTHONPATH=str(ROOT / "src"),
               PATH=os.path.expanduser("~/archpipe/tools/radiance-6.0.1/bin") + os.pathsep + os.environ.get("PATH", ""))
    subprocess.run([sys.executable, "-m", "archpipe.lightcalc.villa_run", "--tag", "lvregen", "--out", str(out)], check=True, env=env, cwd=ROOT)
    res = out / "lvregen"
    if freeze:
        for f in res.glob("*.json"):
            shutil.copyfile(f, rad / f.name)
        return rad
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m archpipe.lightverify")
    ap.add_argument("--design", default="D1")
    ap.add_argument("--scene", default=os.environ.get("LV_SCENE"), help="workstation-built scene.json (see docs/lanes/P-pipeline.md)")
    ap.add_argument("--rad-dir", default=str(ROOT / "knowledge" / "lighting-verify" / "radiance"), help="frozen per-cluster Radiance JSON (villa_run --tag lv3, ab 12 + 24, L6c design; regenerate: see docs/lanes/LV-report.md)")
    ap.add_argument("--no-cycles", action="store_true")
    ap.add_argument("--regen-radiance", action="store_true",
                    help="first re-run the lane's own Radiance study of the current design (villa_run, ab 12 + 24, ~25 min, CPU) and use it instead of --rad-dir")
    ap.add_argument("--freeze", action="store_true", help="with --regen-radiance: copy the regenerated JSON over --rad-dir (the tests' baseline)")
    ap.add_argument("--skip-v8", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "docs" / "lanes" / "LV-report.md"))
    a = ap.parse_args(argv)
    if a.design != "D1":
        raise SystemExit("only design D1 exists")
    from ..contracts import CheckResult, write_results
    from ..lightcalc.villa import Villa
    from . import (report, scene_geom, v1_inputs, v2_placement, v3_sensors, v4_reference, v5_engines, v6_handcalc, v7_convergence,
                   v8_mutation, v10_erco, v12_headroom, dialux_compare, dialux_pack)
    from .common import LayerResult, check
    villa = Villa()
    rad = Path(a.rad_dir)
    if a.regen_radiance:
        rad = regen_radiance(rad, a.freeze)
    layers = {}
    layers["V1"] = v1_inputs.check_inputs(villa)
    layers["V2"] = v2_placement.check_placement(villa)
    scene = a.scene or next((s for s in SCENE_CANDIDATES if Path(s).exists()), None)
    from . import v_la4
    layers["V2"].results += v_la4.results(villa, scene)        # L6d's LA4 lying-looking-up sightlines, recomputed here
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
        if not a.no_cycles:                              # one light per product kind: catches an orientation error a room average hides
            v5_engines.run_orientation(villa, layers["V5"])
        layers["V6"] = v6_handcalc.run(villa, rad)
        layers["V7"] = v7_convergence.run(villa, rad)
    else:
        for k in ("V5", "V6", "V7"):
            L = LayerResult(k)
            L.results.append(check("L" + k, "not_evaluated", "all", (), message="no Radiance results in %s" % rad))
            layers[k] = L
    layers["V10"] = v10_erco.run(villa)
    layers["V11"] = dialux_compare.run(dialux_pack.OUT) if dialux_pack.OUT.exists() else LayerResult("V11")
    layers["V12"] = v12_headroom.run(villa)
    if rad.exists():
        v12_headroom.cards_met(villa, rad, layers["V12"])
    if a.skip_v8:
        L = LayerResult("V8")
        L.results.append(check("LV8", "not_evaluated", "all", (), message="skipped (--skip-v8)"))
        layers["V8"] = L
    else:
        layers["V8"] = v8_mutation.run(villa, rad if rad.exists() else rad, ts)
    results = [r for k in sorted(layers, key=lambda s: int(s[1:])) for r in layers[k].results]
    path = write_results("LV", results)
    sha = None
    if scene and Path(scene).exists():
        import hashlib
        h = hashlib.sha256()
        with open(scene, "rb") as fh:
            for blk in iter(lambda: fh.read(1 << 24), b""):
                h.update(blk)
        sha = h.hexdigest()
    meta = dict(design=a.design, scene=scene, scene_sha256=sha, rad=str(rad),
                scene_note="geometry only: the scene's lights are those of the build, V3 does not use them" if scene else "none")
    Path(a.out).write_text(report.render(villa, layers, meta), encoding="utf-8")
    counts = {}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1
    print("wrote %s and %s: %s" % (path, a.out, counts))
    return 1 if counts.get("fail") else 0          # a failing layer is a closed gate; the report says which (known partials are named there)


if __name__ == "__main__":
    sys.exit(main())
