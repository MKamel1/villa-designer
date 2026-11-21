"""Model-generated cover/index sheet (A-001) and schedule sheet (A-601), same title block as the plans."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

from archpipe.contracts import DesignElement

from archpipe.drawings2d import standard

from . import plans, schedules


def _table(sh, x, y, title, rows, cols, caps, row_h=4.6, size=7.0) -> tuple[float, float]:
    """Table at paper (x, y) down. `caps` = old per-column width in paper mm at 3.6 pt, kept as the character cap
    (cap / 1.55 chars); the printed column is as wide as its longest cell at `size` (7 pt = 1.8 mm cap height).
    Returns (y below the table, table width)."""
    ch = size * 0.24                                               # average glyph advance in mm
    cells = [[("%.2f" % r[c]) if isinstance(r[c], float) else str(r[c]) for c in cols] for r in rows]
    nchar = [max([len(c)] + [len(row[i]) for row in cells]) for i, c in enumerate(cols)]
    nchar = [min(n, int(cap / 1.55) + 1) for n, cap in zip(nchar, caps)]
    widths = [n * ch + 3.0 for n in nchar]
    sh.text((x, y), "%s (%d)" % (title, len(rows)), size=9, ha="left", weight="bold")
    y -= 6
    cx = x
    for c, w in zip(cols, widths):
        sh.text((cx, y), c, size=size, ha="left", color="#333333")
        cx += w
    sh.ax.plot([x, x + sum(widths)], [y - 2.0, y - 2.0], color="k", lw=0.3)
    y -= row_h + 0.6
    for row in cells:
        cx = x
        for v, w, n in zip(row, widths, nchar):
            sh.text((cx, y), v[:n], size=size, ha="left")
            cx += w
        y -= row_h
    return y, sum(widths)


def render_schedules(els: list[DesignElement], spec: dict, sheet: dict, out_stem, *, page: int, pages: int,
                     formats=("pdf", "svg", "png")) -> dict:
    paper = standard.PAPERS[sheet.get("paper", "A3 landscape").split()[0]]
    sh = plans._Sheet(0, 0, 0, 0, paper=paper)
    d, w, r = schedules.door_schedule(els), schedules.window_schedule(els), schedules.room_schedule(els)
    top = paper[1] - plans.EDGE - 18
    x0 = plans.LEFT + 4
    yd, wd = _table(sh, x0, top, "Door schedule (hinge side: client compass; ? = handing to confirm)", d,
                    ["tag", "level", "from", "to", "width_mm", "height_mm", "operation", "handing", "hinge_side", "to_confirm"],
                    [8, 7, 32, 32, 11, 11, 13, 10, 12, 12])
    _table(sh, x0, yd - 10, "Window schedule", w,
           ["tag", "level", "room", "width_mm", "height_mm", "sill_mm", "glazed_area_m2"], [9, 9, 34, 12, 12, 10, 16])
    x1 = x0 + wd + 14
    y, _ = _table(sh, x1, top, "Room schedule", r,
                  ["tag", "level", "name", "gross_area_m2", "net_area_m2", "clear_height_mm"], [9, 8, 58, 17, 15, 17])
    tot = schedules.room_area_totals(r)
    y -= 2
    for lv, t in tot.items():
        sh.text((x1, y), "Level %s: %d rooms, gross %.2f m², net %.2f m²" % (lv, t["rooms"], t["gross_area_m2"], t["net_area_m2"]),
                size=7, ha="left", weight="bold")
        y -= 5
    plans._title_block(sh, spec, sheet, page, pages)
    sh.text((plans.LEFT + 4, paper[1] - plans.EDGE - 5), sheet["title_en"], size=9, ha="left", weight="bold")
    sh.text((plans.x_title_ar(paper), paper[1] - plans.EDGE - 5), sheet["title_ar"], size=9, ha="right", weight="bold")
    return _save(sh, out_stem, formats, {"sheet": sheet["no"], "door_rows": len(d), "window_rows": len(w), "room_rows": len(r)})


def render_cover(spec: dict, sheet: dict, out_stem, *, page: int, pages: int, formats=("pdf", "svg", "png")) -> dict:
    sh = plans._Sheet(0, 0, 0, 0)
    x0, y = plans.LEFT + 6, plans.PAPER[1] - plans.EDGE - 16
    sh.text((x0, y), "Sheet index (model = generated from the design model; line art = Blender line art of the built scene)", size=9, ha="left", weight="bold")
    
    y -= 10
    for s in spec["sheets"]:
        gen = {"model": "model", "lineart": "line art"}[s["generator"]]
        sh.text((x0, y), s["no"], size=7, ha="left", weight="bold")
        sh.text((x0 + 18, y), s["title_en"], size=7, ha="left")
        sh.text((x0 + 250, y), s["title_ar"], size=7, ha="right")
        sh.text((x0 + 256, y), s["scale"], size=7, ha="left")
        sh.text((x0 + 270, y), gen, size=7, ha="left")
        y -= 8
    y -= 6
    sh.text((x0, y), "Legend", size=9, ha="left", weight="bold")
    sh.text((plans.x_title_ar(), y), "مفتاح الرموز", size=9, ha="right", weight="bold")
    for i, t in enumerate(["D01: door tag (circle); schedule A-601", "W01: window tag (hexagon); schedule A-601",
                           "R01: room tag with name, Arabic name and net area m²",
                           "Red dash-dot lines: structural grid from column centres (letters east-west, numbers north-south)",
                           "Dimension chains: opening chain per exterior wall, grid and overall chains per side",
                           "Solid black: exterior wall; hatched: interior wall (core material not authored); dark squares: columns; purple cross-hatch: kept existing columns",
                           "Door leaf and arc show the authored hinge; ? (pink) = handing is a judgement call, to confirm; dashed = pocket door",
                           "North is the street side (up); true north only on the site plan"]):
        sh.text((x0, y - 8 - i * 6), t, size=5.5, ha="left")
    plans._title_block(sh, spec, sheet, page, pages)
    return _save(sh, out_stem, formats, {"sheet": sheet["no"]})


def _save(sh, out_stem, formats, rep: dict) -> dict:
    stem = Path(out_stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    rep["files"] = []
    for fmt in formats:
        p = stem.with_suffix("." + fmt)
        sh.fig.savefig(p, dpi=110 if fmt == "png" else None, facecolor="white")
        rep["files"].append(p.name)
    plt.close(sh.fig)
    return rep


def render_table_sheet(els: list[DesignElement], spec: dict, sheet: dict, out_stem, *, page: int, pages: int,
                       formats=("pdf", "svg", "png")) -> dict:
    """A-602 finish, A-603 furniture, A-604 luminaire schedules: one table, rows straight from the model."""
    v = sheet["variant"]
    rows, cols, widths, title = {
        "finish": (schedules.finish_schedule(els), ["tag", "level", "name", "floor", "walls", "ceiling", "ceiling_kind", "ceiling_mm"],
                   [9, 8, 70, 26, 34, 26, 20, 16], "Finish schedule (codes from the model; blank = none authored)"),
        "furniture": (schedules.furniture_schedule(els), ["id", "level", "room", "type", "w_mm", "d_mm", "h_mm", "product"],
                      [56, 8, 52, 30, 12, 12, 12, 30], "Furniture schedule (dressing props excluded)"),
        "luminaire": (schedules.luminaire_schedule(els), ["mark", "manufacturer", "code", "description", "cct_k", "lumens", "watts", "lm_per_w",
                                                          "count_B", "count_GF", "total_watts"],
                      [14, 20, 26, 62, 10, 12, 10, 10, 10, 10, 14], "Luminaire schedule (one row per type)"),
    }[v]
    paper = standard.PAPERS[sheet.get("paper", "A3 landscape").split()[0]]
    sh = plans._Sheet(0, 0, 0, 0, paper=paper)
    top = paper[1] - plans.EDGE - 18
    _table(sh, plans.LEFT + 4, top, title, rows, cols, widths)
    if v == "luminaire":
        sh.text((plans.LEFT + 4, plans.EDGE + 8), "Total: %d luminaires, %.0f W installed (sum of lamp watts; control gear not included)."
                % (sum(r["count_B"] + r["count_GF"] for r in rows), sum(r["total_watts"] for r in rows)), size=5, ha="left")
    plans._title_block(sh, spec, sheet, page, pages)
    sh.text((plans.LEFT + 4, paper[1] - plans.EDGE - 5), sheet["title_en"], size=9, ha="left", weight="bold")
    sh.text((plans.x_title_ar(paper), paper[1] - plans.EDGE - 5), sheet["title_ar"], size=9, ha="right", weight="bold")
    return _save(sh, out_stem, formats, {"sheet": sheet["no"], "rows": len(rows)})
