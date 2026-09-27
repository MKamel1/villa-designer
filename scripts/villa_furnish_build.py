"""D1 furnished in Revit (Phase 2).

    PYTHONPATH=src python scripts/villa_furnish_build.py spec    # writes out/villa/furnish-d1/revit/options-spec.json
    (then revit/build_villa_option.py with ARCHPIPE_OPTIONS_SPEC / _OUT pointing there)
    PYTHONPATH=src python scripts/villa_furnish_build.py check   # the post-condition on readback.json; exit 1 on a problem

The post-condition's tolerance (5 mm on every face of every element's box, categories exact, each Mark once, and
every furniture check re-run on the as-built footprints) was fixed in villa_furnish3d.TOL before the first build.
"""
import json
import sys
from pathlib import Path

from archpipe.concept import revit_spec as RS
from archpipe.concept import villa_furnish3d as F3
from archpipe.concept import villa_r11 as R

OUT = Path("out/villa/furnish-d1/revit")


def main():
    lay = R.design("D1")
    if "spec" in sys.argv[1:]:
        OUT.mkdir(parents=True, exist_ok=True)
        sp = RS.build(lay)
        sp["id"] = "D1F"
        sp["furniture"] = F3.spec(lay)
        (OUT / "options-spec.json").write_text(json.dumps([sp], indent=1), encoding="utf-8")
        print(OUT / "options-spec.json", len(sp["furniture"]), "elements")
        return 0
    rb = json.loads((OUT / "readback.json").read_text(encoding="utf-8"))["options"][0]
    spec = json.loads((OUT / "options-spec.json").read_text(encoding="utf-8"))[0]["furniture"]
    probs = F3.postcondition(spec, rb.get("furniture", []), lay)
    fails = [f for f in rb["failed"] if "furniture" in f]
    print("built:", rb["built"], "| furniture failures:", len(fails), "| other build failures:",
          len(rb["failed"]) - len(fails))
    for p in fails + probs:
        print("  FAIL", p)
    print("POST-CONDITION", "PASS" if not probs and not fails else "FAIL")
    return 1 if probs or fails else 0


if __name__ == "__main__":
    sys.exit(main())
