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
        us = [q[0] for l in built["lines"] for q in l["uz"]]
        rep["views"].append({"name": v.name, "stroke_u_range_m": [min(us), max(us)] if us else None, "kind": v.kind, "dir": list(v.d), "u_axis": list(v.u_axis), "window_m": list(v.window),
                             "left": viewdraw.left_right(v)[0], "right": viewdraw.left_right(v)[1],
                             "cut_segments": len(built["cut_segments"]), "lines": len(built["lines"]), **{k: cnt[k] for k in ("structure_polys", "context_polys")},
                             "cut_items": [i[0] for i in cut["items"]], "scale": v.scale, "stair_detail": cnt.get("stair_detail")})
        x += w + 14
        rowh = max(rowh, h + 16)
    sh.scale = views[0].scale
    if views[0].name.startswith("Section 1"):
        import textwrap
        st = next(e for e in els if e.kind == "stair")
        q, inf = st.params, st.params["riser_infill"]
        xr, y = x + 4, paper[1] - plans.EDGE - 40
        lines = ["Stair detail (from the design model)", "",
                 "%d risers x %.1f mm, %d treads x %.0f mm going, width %.0f mm." % (q["risers"], q["riser_mm"], q["treads"], q["tread_mm"], q["width_mm"]),
                 "", "Red: riser infill, %d horizontal flat bars %d x %d mm; openings above and below each bar %.1f mm (100 mm sphere test)."
                 % (inf["count"], inf["bar_h_mm"], inf["bar_t_mm"], inf["openings_above_and_below_bar_mm"]),
                 "", "Blue: guards beyond the plane, frameless laminated glass: stair open side 900 mm, GF stair-void edge 1100 mm.",
                 "", "Tan: understair cupboard, %d treads enclosed; end wall and toe panel cut, side wall and door beyond." % q["under_flight"]["treads_enclosed"]]
        for i, t in enumerate(lines):
            for ln in (textwrap.wrap(t, 44) or [""]):
                sh.text((xr, y), ln, size=9 if i == 0 else 7, ha="left", weight="bold" if i == 0 else "normal")
                y -= 4.6
    note = ("Poche: cut of the design-model solids (core material not authored). Lines: Blender Line Art of the built scene %s. "
            "Context (not ours): light grey. Level elevations are Revit datum (scene + 1.2 m)." % str(rep["scene_sha256"])[:10])
    import textwrap as _tw
    for i, ln in enumerate(_tw.wrap(note, 150)[::-1]):
        sh.text((plans.LEFT + 10, plans.EDGE + 8 + 4.6 * i), ln, size=7, ha="left", color="#444444")
    return plans.finish_sheet(sh, spec, sheet, page, pages, out_stem, formats, rep)
