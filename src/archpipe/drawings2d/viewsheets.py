"""A-201/A-202 elevations and A-301/A-302 sections: Line Art + model cut, composed on sheets."""
from __future__ import annotations

import json
from pathlib import Path

from archpipe import model
from archpipe.documents import plans

from . import modelcut, section, standard, viewdraw


def render_view_sheet(slim: dict, els, spec, sheet, out_stem, *, page=1, pages=1, formats=("pdf", "svg", "png"), strokes_fn=section.run_lineart) -> dict:
    paper = standard.PAPERS[sheet["paper"].split()[0]]
    levels = json.loads(Path(model.api.snapshot_path(spec["design"])).read_text(encoding="utf-8"))["levels"]
    views = [v for v in viewdraw.ALL_VIEWS if v.sheet == sheet["no"]]
    sh = plans._Sheet(0, 0, 0, 0, paper=paper, scale=views[0].scale)
    rep = {"sheet": sheet["no"], "scene_sha256": slim["source_sha256"], "scene_id": slim.get("scene_id"), "views": [],
           "frame": "client-north-up", "generator": "lineart"}
    xmin, xmax = plans.LEFT + 10, paper[0] - plans.EDGE - plans.STRIP - 10
    x, ytop, rowh = xmin, paper[1] - plans.EDGE - 24, 0.0
    for v in views:
        sh.scale = v.scale
        u0, z0, u1, z1 = v.window
        w, h = (u1 - u0) * 1000 / v.scale, (z1 - z0) * 1000 / v.scale
        if x + w > xmax and x > xmin:
            x, ytop, rowh = xmin, ytop - rowh - 10, 0.0
        built = section.build_view(slim, v, strokes_fn)
        cut = modelcut.cut_solids(els, levels, v) if v.kind == "section" else {"structure": [], "context": [], "items": []}
        cnt = viewdraw.draw_view(sh, built, cut, els, levels, v, (x, ytop - h - 10), label_rooms=True)
        rep["views"].append({"name": v.name, "kind": v.kind, "dir": list(v.d), "u_axis": list(v.u_axis), "window_m": list(v.window),
                             "left": viewdraw.left_right(v)[0], "right": viewdraw.left_right(v)[1],
                             "cut_segments": len(built["cut_segments"]), "lines": len(built["lines"]), **{k: cnt[k] for k in ("structure_polys", "context_polys")},
                             "cut_items": [i[0] for i in cut["items"]], "scale": v.scale})
        x += w + 14
        rowh = max(rowh, h + 16)
    sh.scale = views[0].scale
    sh.text((plans.LEFT + 10, plans.EDGE + 8), "Poche: cut of the design-model solids (core material not authored). Lines: Blender Line Art of the built scene %s. "
            "Context (not ours): light grey. Level elevations are Revit datum (scene + 1.2 m)." % str(rep["scene_sha256"])[:10],
            size=4.4, ha="left", color="#444444")
    return plans.finish_sheet(sh, spec, sheet, page, pages, out_stem, formats, rep)
