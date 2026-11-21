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


def main(tag: str, out_dir: str = "out/L6b", write: bool = False, lo: float = 0.15, size_generics: bool = False):
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
    d, rows = solve(res, planes, SCENES, tunable, lo=lo, applied=init)
    for pid, t, em, ratio in residuals(rows, d):
        print("%-22s target %4d -> %5.0f (%.2fx)" % (pid, t, em, ratio))
    new = {z: round(f, 3) for z, f in d.items()}
    for z in sorted(new):
        print("driver %-44s %.2f (was %.2f)" % (z, new[z], init.get(z, 1.0)))
    # Dinner: the table pendant's scene level that puts the table top on its 100 lx card, other Dinner zones as stated
    # (Em is linear in the level; the Radiance results already contain the drivers applied to the design)
    from .villa_report import scene_levels
    for p in v.planes():
        if p.scene != "Dinner":
            continue
        cl = "B-open"
        r = res[cl]
        lev = scene_levels(r, SCENES[cl], "Dinner")
        zp = [z for z in lev if z.endswith("-TABLE-PENDANT")][0]
        lev0 = dict(lev, **{zp: 0.0})
        fixed = r.stats(p.id, lev0).em
        per = r.stats(p.id, {zp: 1.0}).em
        L = (p.target - fixed) / per
        print("Dinner: %s level %.3f solves %s to %d lx (others contribute %.0f lx; pendant at 1.0 gives %.0f lx)" %
              (zp, L, p.id, p.target, fixed, per))
    if size_generics:
        # L6c: a zone made only of generic fittings is re-sized (rated lumens x d/0.70) and driven at 0.70 (V12 <= 0.80)
        from ..concept import villa_lighting as VL
        kinds = {}
        for f in v.fixtures:
            kinds.setdefault(VL.zone_id(f), set()).add(f.kind)
        sz_path = ROOT / "knowledge" / "lighting" / "zone-sizing.json"
        sizing = json.loads(sz_path.read_text(encoding="utf-8")) if sz_path.exists() else {}
        for z in sorted(new):
            if kinds.get(z) and not any(k in VL.PRODUCTS for k in kinds[z]):
                sizing[z] = round(sizing.get(z, 1.0) * new[z] / 0.70, 3)
                print("size   %-44s rated x%.3f (driver %.2f -> 0.70)" % (z, sizing[z], new[z]))
                new[z] = 0.70
        if write:
            sz_path.write_text(json.dumps(sizing, indent=1, sort_keys=True), encoding="utf-8")
    if write:
        merged = dict(init)
        merged.update(new)
        TABLE.write_text(json.dumps(merged, indent=1, sort_keys=True), encoding="utf-8")
        print("wrote", TABLE)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--out", default="out/L6c")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--size-generics", action="store_true")
    ap.add_argument("--lo", type=float, default=0.15, help="lowest driver the solve may choose (default 0.15)")
    a = ap.parse_args()
    main(a.tag, out_dir=a.out, write=a.write, lo=a.lo, size_generics=a.size_generics)
