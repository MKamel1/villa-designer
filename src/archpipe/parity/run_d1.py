"""`python -m archpipe.parity.run_d1 --scene scene.json --ifc D1-ARCH.ifc [--prove]`

Builds nothing. Reads the scene and IFC at the paths given (a missing input exits 2), runs K01-K18 on them, writes
out/checks/RV1.json (CheckResult records) and out/parity/d1-report.json, and exits 1 when any check fails.
`--prove` also runs the frozen historic reproductions and the seeded mutation set and puts the recall tables in the report.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .. import contracts
from . import checks as C
from . import frozen as F
from . import ifc_kernel as K
from . import sources
from .intended import load_model
from .world import load_scene_json


def run(scene, ifc, model_path=None, prove=False):
    world, raw = load_scene_json(scene)
    model = load_model(model_path)
    env = F._j("env-readback.json")
    d1f = F._j("d1f-readback.json")["options"][0]
    areas = {r["id"]: r["area_m2"] for r in d1f["rooms"] if r["area_m2"] > 0}
    hosts = raw.get("mounting_hosts", {})
    host_ids = {k: "lum-" + k for k in hosts if k.startswith("SWING")}
    t0 = time.time()
    fs = []
    fs += C.k01_stair_structure(world) + C.k02_wall_slab(world) + C.k03_opening_column(world)
    fs += C.k04_door_soffit(world, model) + C.k05_openings(world, model) + C.k06_glazing_to_beam(world, model)
    fs += C.k07_fixture_ceiling(world, model)
    fs += C.k09_identity(world, model) + C.k10_placement(world, model)
    fs += C.k11_net_area(world, areas) + C.k12_environment(world, env, model) + C.k13_detail_solids(world)
    fs += C.k14_guards(world, model) + C.k15_mounting(world, hosts, host_ids) + C.k16_headroom(world)
    fs += C.k18_datum(world, env["levels"], model)
    iw = K.load_ifc_world(ifc)
    ifs = K.ifc_clashes(iw)
    fs += ifs
    scene_clash = C.k01_stair_structure(world) + C.k02_wall_slab(world) + C.k03_opening_column(world)
    agree = K.agreement(scene_clash, ifs)
    report = dict(scene=dict(path=str(scene), sha256=world.sha256), ifc=dict(path=str(ifc), sha256=iw.sha256, kernel_failures=iw.kernel_failures),
                  model=str(model_path or "src/archpipe/model/data/d1-elements.json"), seconds=round(time.time() - t0, 1),
                  counts={c: {s: sum(1 for f in fs if f.check == c and f.status == s) for s in ("pass", "fail", "not_evaluated")}
                          for c in sorted({f.check for f in fs})},
                  scene_vs_ifc=agree, unowned_meshes=world.unowned,
                  findings=[dict(check=f.check, subject=f.subject, status=f.status, achieved=f.achieved, required=f.required, unit=f.unit,
                                 message=f.message, element_ids=list(f.element_ids), source=f.source) for f in fs if f.status != "pass"])
    if prove:
        from . import mutate as M
        report["historic_and_synthetic"] = F.run_all()
        report["mutations"] = M.run_mutations(world, model, hosts, env, areas, env["levels"], host_ids)
    return fs, report


def to_results(fs):
    out = []
    for f in fs:
        src = f.source if f.source in sources.CARDS else "RV1-TOL-SCENE"
        out.append(contracts.CheckResult(criterion=f"RV1-{f.check}", lane="RV1", status=f.status, subject=f.subject,
                                         achieved=f.achieved, required=f.required, unit=f.unit, message=f.message,
                                         source_ids=(src,) if f.status in ("pass", "fail") else (), element_ids=tuple(f.element_ids)))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--scene", required=True)
    ap.add_argument("--ifc", required=True)
    ap.add_argument("--model", default=None)
    ap.add_argument("--out", default="out")
    ap.add_argument("--prove", action="store_true", help="also run the frozen reproductions and the mutation set")
    a = ap.parse_args(argv)
    for label, p in (("scene", a.scene), ("ifc", a.ifc)) + ((("model", a.model),) if a.model else ()):
        if not Path(p).is_file():
            print(f"run_d1: missing {label} input: {p}", file=sys.stderr)
            return 2
    try:
        fs, report = run(a.scene, a.ifc, a.model, a.prove)
    except FileNotFoundError as e:
        print(f"run_d1: missing input: {e}", file=sys.stderr)
        return 2
    out = Path(a.out)
    contracts.write_results("RV1", to_results(fs), out / "checks")
    (out / "parity").mkdir(parents=True, exist_ok=True)
    (out / "parity" / "d1-report.json").write_text(json.dumps(report, indent=1, default=str))
    nf = sum(1 for f in fs if f.status == "fail")
    print(f"scene {report['scene']['sha256'][:12]}  ifc {report['ifc']['sha256'][:12]}  "
          f"{sum(1 for f in fs if f.status == 'pass')} pass, {nf} fail, {sum(1 for f in fs if f.status == 'not_evaluated')} not evaluated")
    for f in fs:
        if f.status == "fail" and f.check in ("K01", "K02", "K03", "K04", "K06", "K07", "K14", "K15", "K16", "K17-K01", "K17-K02", "K17-K03", "K18", "K12", "K05"):
            print(f"  FAIL {f.check} {f.subject}: {f.message[:160]}")
    return 1 if nf else 0


if __name__ == "__main__":
    sys.exit(main())
