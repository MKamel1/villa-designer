"""L6b driver: run every cluster's Radiance job (parallel over clusters) and cache per-zone results as JSON.

    PYTHONPATH=src python -m archpipe.lightcalc.villa_run --tag after --out out/L6b [--design before|after] [--reuse]

`--design before` rebuilds the scheme from the committed model snapshot's luminaire records is NOT possible without the
authoring inputs, so `before` is simply the design function at a given git revision: run it from a checkout of that
revision (the before results of this lane were produced at origin/integ/aplus and are frozen in
knowledge/lighting/villa-before.json).
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .roomcalc import RoomCalc
from .villa import CLUSTERS, Villa, run_cluster


def _dump(calc: RoomCalc, path: Path):
    data = {"cluster": calc.name, "mf": calc.mf, "slices": calc._slices, "grid": calc._grid_info,
            "params": {"ab": calc.params.ab, "ab_extra": list(calc.params.ab_extra)},
            "zones": {z: {str(ab): v for ab, v in d.items()} for z, d in calc.results.items()},
            "zone_watts": {}, "zone_layer": {}}
    for p in calc.placements:
        data["zone_watts"][p.zone] = data["zone_watts"].get(p.zone, 0.0) + (p.watts or 0.0)
        data["zone_layer"][p.zone] = p.layer
    path.write_text(json.dumps(data), encoding="utf-8")


def run_all(villa: Villa, tag: str, out: Path, host: str = "ai-workstation", reuse: bool = False, fast: bool = False,
            only: list | None = None):
    planes = villa.planes()
    out = Path(out) / tag
    out.mkdir(parents=True, exist_ok=True)
    calcs = {}
    for name in CLUSTERS:
        if only and name not in only:
            continue
        c = villa.calc(name, planes, fast=fast)
        if not c.planes or not c.placements:
            continue
        c.name = "%s-%s" % (tag, name)
        calcs[name] = c

    def one(item):
        name, c = item
        run_cluster(c, out / name, host=host, reuse=reuse)
        _dump(c, out / (name + ".json"))
        return name

    with ThreadPoolExecutor(max_workers=3) as ex:
        list(ex.map(one, calcs.items()))
    return calcs, planes


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--out", default="out/L6b")
    ap.add_argument("--reuse", action="store_true")
    ap.add_argument("--fast", action="store_true", help="ab 6 only (no ab 12 convergence run)")
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    run_all(Villa(), a.tag, Path(a.out), reuse=a.reuse, fast=a.fast, only=a.only)
