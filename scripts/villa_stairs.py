"""Stair options for the villa: write the 3D spec, compare Revit's clash read-back with the Python check.

    PYTHONPATH=src python scripts/villa_stairs.py spec      # out/villa/stairs-spec.json
    (run revit/build_villa_stairs.py on a copy of out/villa/omar-env.rvt)
    PYTHONPATH=src python scripts/villa_stairs.py compare   # both checks side by side; exit 1 if they disagree
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from archpipe.concept import stairs as S
from archpipe.execution_context import ContextError, project_context

OUT = Path("out/villa")


def spec():
    from archpipe.concept import stair_options as SO
    data = {"options": [{"name": st["name"], "parts": st["parts"]} for st in S.options() + [SO.u_front_bay()]]}
    p = OUT / "stairs-spec.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def compare():
    rb = json.loads((OUT / "stairs-readback.json").read_text(encoding="utf-8"))
    bad = 0
    from archpipe.concept import stair_options as SO
    for st in S.options() + [SO.u_front_bay()]:
        py = S.clashes(st)
        py_cols = sorted({h["structure"].split()[-1] for h in py["hits"] if h["kind"] == "column"})
        py_beams = sorted({h["structure"].split()[1] for h in py["hits"] if h["kind"] == "beam"})
        rv = next(o for o in rb["options"] if o["name"] == st["name"])
        rv_cols = sorted({str(r["id"]) for r in rv["intersections"] if r["kind"] == "column"})
        rv_beams = sorted({r["name"].replace("ENV ", "") for r in rv["intersections"] if r["kind"] == "framing"})
        rv_floors = sorted({r["name"] for r in rv["intersections"] if r["kind"] == "floor"})
        print(f"== {st['name']}")
        print(f"   python columns {py_cols}  beams {py_beams}")
        print(f"   revit  columns {rv_cols}  beams {rv_beams}  floors {rv_floors}")
        gf_ids = {c for c in py_cols}
        # Revit sees each storey's column as its own element; the GF ones carry the original ids
        if bool(py_cols) != bool(rv_cols) or bool(py_beams) != bool(rv_beams):
            print("   DISAGREE")
            bad += 1
    return bad


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv
    cmd = argv[1] if len(argv) > 1 else "spec"
    try:
        project_context(
            ROOT,
            Path(__file__).resolve(),
            "villa-stairs",
            inputs=[OUT / "stairs-readback.json"] if cmd != "spec" else [],
            output=OUT,
        )
    except ContextError as exc:
        print("PREFLIGHT FAILED: " + str(exc), file=sys.stderr)
        return 2
    if cmd == "spec":
        res_path = spec()
        print(res_path)
        from archpipe.stage_result import enforce_clean_verdict, write_stage_result
        stage_record = OUT / "villa-stairs-spec.stage-result.json"
        write_stage_result(
            "villa-stairs-spec",
            record_path=stage_record,
            inputs=[],
            outputs=[OUT / "stairs-spec.json"],
            exit_code=0,
            metadata={"passed": True},
        )
        return enforce_clean_verdict({"passed": True}, exit_code=1)
    else:
        bad = compare()
        from archpipe.stage_result import enforce_clean_verdict, write_stage_result
        stage_record = OUT / "villa-stairs.stage-result.json"
        inputs = [p for p in [OUT / "stairs-readback.json"] if p.is_file()]
        write_stage_result(
            "villa-stairs",
            record_path=stage_record,
            inputs=inputs,
            outputs=[],
            exit_code=1 if bad else 0,
            metadata={"disagreements": bad, "passed": bad == 0},
        )
        return enforce_clean_verdict(
            {"passed": bad == 0, "failures": [f"Clash check disagreements: {bad}"] if bad else []},
            exit_code=1,
        )


if __name__ == "__main__":
    sys.exit(main())
