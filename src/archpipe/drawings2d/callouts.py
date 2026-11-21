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
        sh.text((x, sh.oy + h + 7.5), p["label"], size=8.5, ha="left", weight="bold")
        sh.text((x, sh.oy + h + 2.5), "1:20", size=7, ha="left", color="#444444")
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


def render_yard_wall(els, spec, sheet, out_stem, *, page=1, pages=1, formats=("pdf", "svg", "png")) -> dict:
    """A-143: the NE yard wall (`ctx-yard-wall-ne`) dimensioned in plan and elevation for client confirmation (old row U17-1).
    Dimensions are the model's own numbers (length, thickness, height, base and top level); position is tied to the NE column."""
    from matplotlib.patches import Rectangle
    paper = standard.PAPERS[sheet["paper"].split()[0]]
    scale = plans.parse_scale(sheet["scale"])
    w = next(e for e in els if e.id == "ctx-yard-wall-ne")
    cels = orient.to_client(els)
    cw = next(e for e in cels if e.id == "ctx-yard-wall-ne")
    cx, cy, (lx, ly) = cw.placement[0], cw.placement[1], (cw.size[0], cw.size[1])
    sh = plans._Sheet(0, 0, 0, 0, paper=paper, scale=scale)
    levels = plans._model_levels(spec)
    z0, z1 = w.params["z0_scene_mm"], w.params["z1_scene_mm"]
    rep = {"sheet": sheet["no"], "frame": "client-north-up", "scale": scale, "wall": {"length_mm": max(lx, ly), "thickness_mm": min(lx, ly), "height_mm": z1 - z0,
           "base_revit_mm": z0 + 1200, "top_revit_mm": z1 + 1200}}
    # plan crop: wall plus the NE corner of the villa (basement walls and kept columns), 1.5 m margin
    x0, y0, x1, y1 = cx - lx / 2 - 1200, cy - ly / 2 - 800, cx + lx / 2 + 1200, cy + ly / 2 + 800
    sh.ox, sh.oy, sh.x0, sh.y0 = plans.LEFT + 16, paper[1] - plans.EDGE - 30 - (y1 - y0) / scale, x0, y0
    geo = plans._level_geometry(cels, "B")
    geo["walls"] = [e for e in geo["walls"] if min(e.params["x0_mm"], e.params["x1_mm"]) < x1 and max(e.params["x0_mm"], e.params["x1_mm"]) > x0
                    and min(e.params["y0_mm"], e.params["y1_mm"]) < y1 and max(e.params["y0_mm"], e.params["y1_mm"]) > y0]
    geo["columns"] = [c for c in geo["columns"] if x0 < c.placement[0] < x1 and y0 < c.placement[1] < y1]
    geo["stairs"], geo["bbox"] = [], (x0, y0, x1, y1)
    n0 = (len(sh.ax.patches), len(sh.ax.lines), len(sh.ax.texts))
    plans._draw_walls(sh, geo)
    plans._draw_stairs_columns(sh, geo, existing_distinct=True)
    sh.ax.add_patch(Rectangle(sh.p(cx - lx / 2, cy - ly / 2), lx / scale, ly / scale, fc="#999999", ec="k", lw=standard.lw("cut", scale), zorder=6))
    clip = Rectangle(sh.p(x0, y0), (x1 - x0) / scale, (y1 - y0) / scale, transform=sh.ax.transData, fc="none", ec="none")
    sh.ax.add_patch(clip)
    for art in list(sh.ax.patches[n0[0]:]) + list(sh.ax.lines[n0[1]:]):
        if art is not clip:
            art.set_clip_path(clip)
    sh.ax.add_patch(Rectangle(sh.p(x0, y0), (x1 - x0) / scale, (y1 - y0) / scale, fc="none", ec="k", lw=0.3, zorder=12))
    ex0, ex1 = cx - lx / 2, cx + lx / 2
    rep["dimensions"] = []
    plans._chain(sh, rep, [ex0, ex1], cy + ly / 2 + 700, True, "yardwall", w.id, 7.0)
    plans._chain(sh, rep, [cy - ly / 2, cy + ly / 2], ex1 + 500, False, "yardwall", w.id, 7.0)
    sh.text((sh.ox, sh.oy + (y1 - y0) / scale + 6), "NE yard wall: plan, basement, 1:%g" % scale, size=8.5, ha="left", weight="bold")
    sh.text(sh.p(x0 + 100, y0 + 400), "flush with the villa's east face", size=7, ha="left", bg=True)
    # elevation below / beside: length x height, base and top levels
    px = sh.ox + (x1 - x0) / scale + 22
    py = paper[1] - plans.EDGE - 30 - (z1 - z0) / scale - 14
    sh.ax.add_patch(Rectangle((px, py), max(lx, ly) / scale, (z1 - z0) / scale, fc="#999999", ec="k", lw=standard.lw("cut", scale), zorder=6))
    sh.line((px - 8, py), (px + max(lx, ly) / scale + 8, py), lw=0.4, color="#0b5394", ls=(0, (6, 2)))
    sh.line((px - 8, py + (z1 - z0) / scale), (px + max(lx, ly) / scale + 8, py + (z1 - z0) / scale), lw=0.4, color="#0b5394", ls=(0, (6, 2)))
    sh.text((px, py - 14), "base %+.2f (basement floor)" % ((z0 + 1200) / 1000.0), size=7, ha="left", color="#0b5394")
    sh.text((px, py + (z1 - z0) / scale + 3), "top %+.2f" % ((z1 + 1200) / 1000.0), size=7, ha="left", color="#0b5394")
    yy = py - 6
    sh.line((px, yy), (px + max(lx, ly) / scale, yy), lw=0.2)
    sh.text((px + max(lx, ly) / scale / 2, yy - 3.2), "%d" % max(lx, ly), size=7)
    xx = px - 6
    sh.line((xx, py), (xx, py + (z1 - z0) / scale), lw=0.2)
    sh.text((xx - 3.2, py + (z1 - z0) / scale / 2), "%d" % (z1 - z0), size=7, rot=90)
    sh.text((px, py + (z1 - z0) / scale + 9), "NE yard wall: elevation, 1:%g" % scale, size=8.5, ha="left", weight="bold")
    note = ("Source: model element ctx-yard-wall-ne. %s Position relative to the NE column and the street fence is as modelled; "
            "no survey. For client confirmation: wall length, thickness, height and finish top level." % w.params["note"])
    import textwrap
    for i, ln in enumerate(textwrap.wrap(note, 95)):
        sh.text((plans.LEFT + 12, plans.EDGE + 8 + 4.6 * (len(textwrap.wrap(note, 95)) - 1 - i)), ln, size=7, ha="left", color="#444444")
    return plans.finish_sheet(sh, spec, sheet, page, pages, out_stem, formats, rep)
