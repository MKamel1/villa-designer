"""Round-3 final review renders (layout-final, LDL graded Fab plants): summer, winter, mature, and the labelled visualisation bird's-eye, as parallel jobq GPU jobs.

    python -m archpipe.landscape.build.final_previews OUT_DIR
Exposure is fixed per view group (`preview.EXPOSURE`) and is the same in summer and winter, so the two seasons compare like for like.
"""
from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import build, preview, visualisation

ROOT = Path(__file__).resolve().parents[4]
FIN = ROOT / "knowledge/landscape/concept/final"
WINTER_VIEWS = ("dining-crown-winter", "eye-dining-firepit", "bird-south-east", "grape-winter")


def jobs(out):
    L = build.load_layout(FIN / "layout-final.json")
    V = build.load_layout(FIN / "layout-visualisation.json")
    out = Path(out)
    s3, sm = build.build_scene(L, age=3), build.build_scene(L, age=None)
    w3, wm = build.build_scene(L, age=3, season="winter"), build.build_scene(L, age=None, season="winter")
    vis = visualisation.build_visualisation(L, V, age=3)

    def only(sc, names):
        return [v for v in preview.default_views(sc, "x") if v["name"] in names]
    yield "age3", s3, out / "previews", None
    yield "mature", sm, out / "previews", None
    yield "age3-winter", w3, out / "previews", only(w3, WINTER_VIEWS)
    yield "mature-winter", wm, out / "previews", only(wm, WINTER_VIEWS[:1])
    yield "age3-vis", vis, out / "visualisation", None


def main(out):
    def run(j):
        tag, sc, d, views = j
        rec = preview.render(sc, d, tag, views=views)
        return tag, [(v["name"], v["file"]) for v in rec["views"]], rec
    with ThreadPoolExecutor(3) as ex:
        for tag, vs, rec in ex.map(run, jobs(out)):
            print(tag, len(vs), "views; assets placed:", len(rec["assets"]))
            for n, f in vs:
                print("  ", n, f)


if __name__ == "__main__":
    main(sys.argv[1])
