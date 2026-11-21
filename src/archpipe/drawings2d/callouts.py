"""Enlarged plan callouts at 1:20 (plan row C10): stair B + GF, and the wet rooms. Panels share one sheet; each panel is
a clipped crop of the same plan drawing code the GA plans use (so a fix there fixes both)."""
from __future__ import annotations

from matplotlib.patches import Rectangle

from archpipe.contracts import DesignElement
from archpipe.documents import plans, schedules

from . import layers as L
from . import orient, standard


def room_crop(cels: list[DesignElement], room_ids: list[str], margin: float = 600.0):
    pts = [q for e in cels if e.kind == "room" and e.room in room_ids for q in e.params["polygon_mm"]]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (min(xs) - margin, min(ys) - margin, max(xs) + margin, max(ys) + margin)


STAIR_ROOMS = ["stair-b", "hall-b", "stair-gf", "landing-gf"]
WET = [("Family bathroom", "GF", ["family-bath"]), ("Parents' ensuite", "GF", ["parents-ensuite"]),
       ("Guest WC", "B", ["guest-wc"])]


def panels_for(variant: str, cels: list[DesignElement]) -> list[dict]:
    if variant == "stair":
        return [{"label": "Stair, basement -1.80 (UP)", "level": "B", "crop": room_crop(cels, ["stair-b"], 900)},
                {"label": "Stair, ground floor +1.20 (DN)", "level": "GF", "crop": room_crop(cels, ["stair-gf", "landing-gf"], 900)}]
    return [{"label": "%s (%s)" % (n, lv), "level": lv, "crop": room_crop(cels, ids, 300)} for n, lv, ids in WET]


def render_callouts(els, spec, sheet, out_stem, *, page=1, pages=1, formats=("pdf", "svg", "png")) -> dict:
    paper = standard.PAPERS[sheet["paper"].split()[0]]
    scale = plans.parse_scale(sheet["scale"])
    cels = orient.to_client(els)
    levels = plans._model_levels(spec)
    tagmap = schedules.tag_numbers(els)
    sh = plans._Sheet(0, 0, 0, 0, paper=paper, scale=scale)
    rep = {"sheet": sheet["no"], "frame": "client-north-up", "scale": scale, "panels": [], "room_tags": [], "door_tags": [],
           "window_tags": [], "dimensions": []}
    pl = panels_for(sheet["variant"], cels)
    gap = 12.0
    widths = [(p["crop"][2] - p["crop"][0]) / scale for p in pl]
    xmin, xmax = plans.LEFT + 10, paper[0] - plans.EDGE - plans.STRIP - 10
    x, ytop, rowh = xmin, paper[1] - plans.EDGE - 22, 0.0
    for p, w in zip(pl, widths):
        x0, y0, x1, y1 = p["crop"]
        h = (y1 - y0) / scale
        if x + w > xmax and x > xmin:                       # wrap to the next row
            x, ytop, rowh = xmin, ytop - rowh - 12, 0.0
        rowh = max(rowh, h + 8)
        sh.ox, sh.oy, sh.x0, sh.y0 = x, ytop - h - 6, x0, y0
        geo = plans._level_geometry(cels, p["level"])
        # keep only what is inside the crop window so tags and dimensions are for this panel
        inside = lambda px, py: x0 <= px <= x1 and y0 <= py <= y1                       # noqa: E731
        geo["rooms"] = [r for r in geo["rooms"] if inside(*r.placement[:2])]
        geo["doors"] = [d for d in geo["doors"] if inside(*d.placement[:2])]
        geo["windows"] = [d for d in geo["windows"] if inside(*d.placement[:2])]
        geo["bbox"] = (x0, y0, x1, y1)
        n_before = (len(sh.ax.patches), len(sh.ax.lines), len(sh.ax.texts))
        plans._draw_walls(sh, geo)
        plans._draw_stairs_columns(sh, geo, existing_distinct=True)
        plans._draw_openings(sh, geo, rep, flag_judgement=True)
        L.furniture(sh, cels, p["level"], window=p["crop"])
        plans._tags(sh, geo, tagmap, rep)
        # key clear dimensions of each room in the panel (net polygon bbox), drawn inside the panel margin
        for r in geo["rooms"]:
            pts = r.params.get("net_polygon_mm") or r.params["polygon_mm"]
            rx0, ry0 = min(q[0] for q in pts), min(q[1] for q in pts)
            rx1, ry1 = max(q[0] for q in pts), max(q[1] for q in pts)
            plans._chain(sh, rep, [rx0, rx1], y0 + 150, True, "clear", r.id, 4.2)
            plans._chain(sh, rep, [ry0, ry1], x0 + 150, False, "clear", r.id, 4.2)
        clip = Rectangle(sh.p(x0, y0), w, h, transform=sh.ax.transData, fc="none", ec="none")
        sh.ax.add_patch(clip)
        for art in list(sh.ax.patches[n_before[0]:]) + list(sh.ax.lines[n_before[1]:]) + list(sh.ax.texts[n_before[2]:]):
            if art is not clip:
                art.set_clip_path(clip)
                if hasattr(art, "set_clip_on"):
                    art.set_clip_on(True)
        sh.ax.add_patch(Rectangle(sh.p(x0, y0), w, h, fc="none", ec="k", lw=standard.lw("cut", 20) / 2, zorder=12))
        sh.text((x, sh.oy + h + 4), p["label"], size=7, ha="left", weight="bold")
        sh.text((x, sh.oy + h + 0.2), "1:20", size=4.5, ha="left", color="#444444")
        rep["panels"].append({"label": p["label"], "level": p["level"], "crop_mm": [round(v) for v in p["crop"]]})
        x += w + gap
    if sheet["variant"] == "stair":
        st = next(e for e in els if e.kind == "stair")
        q = st.params
        sh.text((plans.LEFT + 12, plans.EDGE + 14),
                "Stair: %d risers x %.1f mm rise, %d treads x %.0f mm going, width %.0f mm. Flight rises toward the rear (south)."
                % (q["risers"], q["riser_mm"] if "riser_mm" in q else q["rise_mm"], q["treads"], q["tread_mm"], q["width_mm"]),
                size=5, ha="left")
        rep["stair"] = {k: q[k] for k in ("risers", "treads", "tread_mm", "width_mm")}
    sh.text((plans.LEFT + 12, plans.EDGE + 8), "? = door handing not decided by the client (to confirm).  Purple cross-hatch = kept existing column.",
            size=4.6, ha="left", color="#c2185b")
    return plans.finish_sheet(sh, spec, sheet, page, pages, out_stem, formats, rep)
