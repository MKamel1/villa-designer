"""Model-generated cover/index sheet (A-001) and schedule sheet (A-601), same title block as the plans."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

from archpipe.contracts import DesignElement

from . import arabic, plans, schedules


def _table(sh, x, y, title, rows, cols, widths, row_h=3.7, size=4.2) -> float:
    sh.text((x, y), "%s (%d)" % (title, len(rows)), size=7, ha="left", weight="bold")
    y -= 5
    cx = x
    for c, w in zip(cols, widths):
        sh.text((cx, y), c, size=size, ha="left", weight="bold")
        cx += w
    sh.ax.plot([x, x + sum(widths)], [y - 1.5, y - 1.5], color="k", lw=0.3)
    y -= 4.5
    for r in rows:
        cx = x
        for c, w in zip(cols, widths):
            v = r[c]
            v = ("%.2f" % v) if isinstance(v, float) else str(v)
            sh.text((cx, y), v[: int(w / 1.55)], size=size, ha="left")
            cx += w
        y -= row_h
    return y


def render_schedules(els: list[DesignElement], spec: dict, sheet: dict, out_stem, *, page: int, pages: int,
                     formats=("pdf", "svg", "png")) -> dict:
    sh = plans._Sheet(0, 0, 0, 0)
    d, w, r = schedules.door_schedule(els), schedules.window_schedule(els), schedules.room_schedule(els)
    top = plans.PAPER[1] - plans.EDGE - 14
    x0 = plans.LEFT + 4
    _table(sh, x0, top, "Door schedule", [{**q, "swing": q["operation"]} for q in d],
           ["tag", "level", "from", "to", "width_mm", "height_mm", "operation"], [9, 9, 34, 22, 12, 12, 14], size=3.8)
    _table(sh, x0, top - 100, "Window schedule", w,
           ["tag", "level", "room", "width_mm", "height_mm", "sill_mm", "glazed_area_m2"], [9, 9, 34, 12, 12, 10, 16], size=3.8)
    x1 = x0 + 128
    y = _table(sh, x1, top, "Room schedule", r,
               ["tag", "level", "name", "gross_area_m2", "net_area_m2", "clear_height_mm"], [9, 8, 58, 17, 15, 17], row_h=3.4, size=3.6)
    tot = schedules.room_area_totals(r)
    y -= 2
    for lv, t in tot.items():
        sh.text((x1, y), "Level %s: %d rooms, gross %.2f m², net %.2f m²" % (lv, t["rooms"], t["gross_area_m2"], t["net_area_m2"]),
                size=4.4, ha="left", weight="bold")
        y -= 4
    plans._title_block(sh, spec, sheet, page, pages)
    sh.text((plans.LEFT + 4, plans.PAPER[1] - plans.EDGE - 5), sheet["title_en"], size=9, ha="left", weight="bold")
    sh.text((plans.x_title_ar(), plans.PAPER[1] - plans.EDGE - 5), sheet["title_ar"], size=9, ha="right", weight="bold")
    return _save(sh, out_stem, formats, {"sheet": sheet["no"], "door_rows": len(d), "window_rows": len(w), "room_rows": len(r)})


def render_cover(spec: dict, sheet: dict, out_stem, *, page: int, pages: int, formats=("pdf", "svg", "png")) -> dict:
    sh = plans._Sheet(0, 0, 0, 0)
    x0, y = plans.LEFT + 6, plans.PAPER[1] - plans.EDGE - 16
    sh.text((x0, y), "Sheet index", size=11, ha="left", weight="bold")
    sh.text((plans.x_title_ar(), y), "فهرس اللوحات", size=11, ha="right", weight="bold")
    y -= 10
    for s in spec["sheets"]:
        gen = {"model": "model-generated (this set)", "revit": "needs Revit (not produced: Revit unavailable)"}[s["generator"]]
        sh.text((x0, y), s["no"], size=7, ha="left", weight="bold")
        sh.text((x0 + 18, y), s["title_en"], size=7, ha="left")
        sh.text((x0 + 120, y), s["title_ar"], size=7, ha="right")
        sh.text((x0 + 128, y), s["scale"], size=6, ha="left")
        sh.text((x0 + 148, y), gen, size=5.5, ha="left", color="#b00020" if s["generator"] == "revit" else "k")
        y -= 8
    y -= 6
    sh.text((x0, y), "Legend", size=9, ha="left", weight="bold")
    sh.text((plans.x_title_ar(), y), "مفتاح الرموز", size=9, ha="right", weight="bold")
    for i, t in enumerate(["D01: door tag (circle); schedule A-601", "W01: window tag (hexagon); schedule A-601",
                           "R01: room tag with name, Arabic name and net area m²",
                           "Red dash-dot lines A..G / 1..2: structural grid from column centres",
                           "Dimension chains: opening chain per exterior wall, grid and overall chains per side",
                           "Black fill: exterior wall; grey fill: interior wall; dark squares: columns"]):
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
