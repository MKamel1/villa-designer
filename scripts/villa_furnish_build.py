"""D1 furnished in Revit (Phase 2).

    PYTHONPATH=src python scripts/villa_furnish_build.py spec    # writes out/villa/furnish-d1/revit/options-spec.json
    (then revit/build_villa_option.py with ARCHPIPE_OPTIONS_SPEC / _OUT pointing there)
    PYTHONPATH=src python scripts/villa_furnish_build.py check   # the post-condition on readback.json; exit 1 on a problem

The post-condition uses 5 mm on every face of every element's box, exact categories, each Mark once, and
re-runs furniture checks on the as-built footprints. D1 round-2 details, the wall hatch, study windows and suite
door are also checked. Round-3 nook fixtures, dressing modules and soffit storage bodies have separate measured
world boxes and tags in the same Revit build; villa_furnish3d.TOL was fixed before the first furnishing build.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from archpipe.concept import revit_spec as RS
from archpipe.concept import villa_furnish3d as F3
from archpipe.concept import villa_r11 as R
from archpipe.execution_context import ContextError, project_context

OUT = Path("out/villa/furnish-d1/revit")


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv[1:]
    is_spec = "spec" in args
    try:
        project_context(
            ROOT,
            Path(__file__).resolve(),
            "villa-furnish-build",
            inputs=[] if is_spec else [OUT / "readback.json", OUT / "options-spec.json"],
            output=OUT,
            modules=["shapely"],
        )
    except ContextError as exc:
        print("PREFLIGHT FAILED: " + str(exc), file=sys.stderr)
        return 2
    lay = R.design("D1")
    if is_spec:
        OUT.mkdir(parents=True, exist_ok=True)
        sp = RS.build(lay)
        sp["id"] = "D1F"
        sp["furniture"] = F3.spec(lay)
        sp["round2_elements"] = F3.round2_elements(sp)
        sp["round3_elements"] = F3.round3_elements(sp, lay)
        (OUT / "options-spec.json").write_text(json.dumps([sp], indent=1), encoding="utf-8")
        print(OUT / "options-spec.json", len(sp["furniture"]), "elements")
        from archpipe.stage_result import enforce_clean_verdict, write_stage_result
        stage_record = OUT / "villa-furnish-build-spec.stage-result.json"
        inputs = [p for p in [ROOT / "spec/villa-site.yaml"] if p.is_file()]
        write_stage_result(
            "villa-furnish-build-spec",
            record_path=stage_record,
            inputs=inputs,
            outputs=[OUT / "options-spec.json"],
            exit_code=0,
            metadata={"elements": len(sp["furniture"]), "passed": True},
        )
        return enforce_clean_verdict({"passed": True, "elements": len(sp["furniture"])}, exit_code=1)
    rb = json.loads((OUT / "readback.json").read_text(encoding="utf-8"))["options"][0]
    spec = json.loads((OUT / "options-spec.json").read_text(encoding="utf-8"))[0]
    probs = F3.postcondition(spec["furniture"], rb.get("furniture", []), lay)
    probs += F3.round2_postcondition(spec, rb, lay)
    probs += F3.round3_postcondition(spec, rb, lay)
    fails = rb["failed"]
    print("built:", rb["built"], "| build failures:", len(fails))
    for p in fails + probs:
        print("  FAIL", p)
    print("POST-CONDITION", "PASS" if not probs and not fails else "FAIL")
    bad = bool(probs or fails)
    from archpipe.stage_result import enforce_clean_verdict, write_stage_result
    stage_record = OUT / "villa-furnish-build.stage-result.json"
    inputs = [p for p in [OUT / "readback.json", OUT / "options-spec.json"] if p.is_file()]
    write_stage_result(
        "villa-furnish-build",
        record_path=stage_record,
        inputs=inputs,
        outputs=[],
        exit_code=1 if bad else 0,
        metadata={
            "built": rb.get("built"),
            "build_failures": len(fails),
            "problems": probs,
            "fails": fails,
            "passed": not bad,
        },
    )
    return enforce_clean_verdict(
        {"passed": not bad, "problems": probs, "fails": fails, "failures": probs + fails},
        exit_code=1,
    )


if __name__ == "__main__":
    sys.exit(main())
