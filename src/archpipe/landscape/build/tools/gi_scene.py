"""Build the production D1 scene with the decided garden for lane GI.

    python -m archpipe.landscape.build.tools.gi_scene OUT_DIR [--dev] [--measure]
`--dev` bypasses the furniture-stage2 and parents-bed receipts (a DIAGNOSTIC build for look development only: the receipts are bound to the pre-garden fixed inputs and are
regenerated, baseline-relative, in the lane's last step). Without `--dev` the production build runs with every receipt active and no bypass. The view list is the render set
(knowledge/render-set/views.json) plus the lane's key views. `--measure` writes the scene for the Blender exposure-group measurement (no frozen record needed).
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[5]


def views():
    from archpipe.concept import villa_r11 as R, villa_render as VR
    from archpipe.critic import render_set as RS
    from archpipe.landscape.build import production as PRD
    lay = R.design("D1")
    base = VR.VIEWS(lay)
    return RS.resolve(RS.load(), lay, base) + [v for v in base if v["id"] in PRD.KEY_VIEWS]      # the key views are part of VIEWS(lay) (villa_render appends them)


def main(out, dev=False, measure=False, record=None):
    from archpipe.critic import render_set as RS
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    vs = views()
    if dev:
        with patch("archpipe.concept.furniture_stage2.apply", side_effect=lambda s, *a: s), patch("archpipe.concept.parents_bed.apply", side_effect=lambda s, *a: s):
            RS.write_scene(out / "scene.json", vs, record, measure=measure)
    else:
        RS.write_scene(out / "scene.json", vs, record, measure=measure)
    from archpipe.landscape.build import production as PRD
    import json as _j
    bad = PRD.uncleared(_j.loads((out / "scene.json").read_text(encoding="utf-8"))["views"])
    if bad:
        raise SystemExit("cameras inside a garden solid, not cleared: %s" % bad)
    print("wrote", out / "scene.json")


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], "--dev" in a, "--measure" in a, next((x.split("=", 1)[1] for x in a if x.startswith("--record=")), None))
