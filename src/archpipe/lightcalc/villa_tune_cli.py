"""L6b: solve the zone driver table from a Radiance run.

    PYTHONPATH=src python -m archpipe.lightcalc.villa_tune_cli --tag iter1 [--write]

The Radiance results of `--tag` were computed with the drivers currently in knowledge/lighting/zone-drivers.json applied, so
the solve returns a factor relative to them; --write multiplies the table by it (product-bound zones are capped at 1.0 when
the design is applied, generic zones may exceed it).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import villa_report as VR
from .villa import CLUSTERS, Villa
from .villa_tune import residuals, solve

ROOT = Path(__file__).resolve().parents[3]
TABLE = ROOT / "knowledge" / "lighting" / "zone-drivers.json"


def main(tag: str, out_dir: str = "out/L6b", write: bool = False, lo: float = 0.15):
    from ..concept.villa_lighting import SCENES
    v = Villa()
    planes = [p for p in v.planes() if p.scene != "Dinner"]
    res = {}
    for cl in CLUSTERS:
        f = ROOT / out_dir / tag / (cl + ".json")
        if f.exists():
            res[cl] = VR.ClusterRes.load(f)
    tunable = set()
    for cl, r in res.items():
        for z, layer in r.zone_layer.items():
            if layer == "task" or z.endswith(("-ISLAND-PENDANTS", "-TABLE-PENDANT")):
                tunable.add(z)
    init = json.loads(TABLE.read_text(encoding="utf-8")) if TABLE.exists() else {}
    d, rows = solve(res, planes, SCENES, tunable, lo=lo)
    for pid, t, em, ratio in residuals(rows, d):
        print("%-22s target %4d -> %5.0f (%.2fx)" % (pid, t, em, ratio))
    new = {z: round(init.get(z, 1.0) * f, 3) for z, f in d.items()}
    for z in sorted(new):
        print("driver %-44s %.2f (x%.2f this round)" % (z, new[z], d[z]))
    if write:
        merged = dict(init)
        merged.update(new)
        TABLE.write_text(json.dumps(merged, indent=1, sort_keys=True), encoding="utf-8")
        print("wrote", TABLE)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    main(a.tag, write=a.write)
