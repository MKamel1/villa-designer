"""Plan PNGs, one per layer. Drawn with client NORTH (street, model -x) at the top and client EAST (+y) to the right."""
from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from . import grid as G, model as M  # noqa: E402

OUT = Path(__file__).resolve().parents[4] / "knowledge" / "landscape" / "site"
TRUE_N = (math.cos(math.radians(20)), math.sin(math.radians(20)))     # screen (right, up) of TRUE north: +y is 20 deg E of true N


def _load(name):
    return json.loads((OUT / (name + ".json")).read_text())


def _rows(r):
    return G.from_rows(r)


def _base(title, figsize=(9.5, 12.5)):
    import textwrap
    title = "\n".join(textwrap.fill(t, 80) for t in title.split("\n"))
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_xlim(G.ORIGIN_Y, -11.5)   # the strip right of the plot holds the north arrow and the legend
    ax.set_ylim(G.ORIGIN_X + G.NX * G.CELL, G.ORIGIN_X)
    ax.set_aspect("equal")
    ax.set_xlabel("model y (m)  ->  client EAST")
    ax.set_ylabel("model x (m)  ->  client SOUTH (down)")
    ax.set_title(title, fontsize=10)
    # building, fences as context
    ax.add_patch(Rectangle((M.AXIS, M.BAR[0]), M.BAR[3] - M.AXIS, M.BAR[2] - M.BAR[0], fc="#bdbdbd", ec="#555", lw=.8, zorder=1))
    ax.text(-26.5, 13, "VILLA (ours)", ha="center", va="center", fontsize=9, color="#333", zorder=6)
    return fig, ax


def _outlines(ax):
    for name, (x0, y0, x1, y1, _) in M.ZONES.items():
        ax.add_patch(Rectangle((y0, x0), y1 - y0, x1 - x0, fill=False, ec="k", lw=1.2, zorder=5))
        ax.text((y0 + y1) / 2, (x0 + x1) / 2, name, ha="center", va="center", fontsize=7, color="k", zorder=7,
                bbox=dict(fc="white", ec="none", alpha=.55, pad=1))
    ax.axhline(M.AXIS and 0, color="none")
    ax.plot([M.AXIS, M.AXIS], [M.X0I, M.X1I], color="#c00", lw=1.5, ls="--", zorder=6)
    ax.text(M.AXIS + .12, 3.0, "open line to the sister plot (not ours)", rotation=90, ha="left", va="top", fontsize=7, color="#c00", zorder=9)


def _north(ax, xy=(-15.5, 7.0)):
    y, x = xy
    ax.annotate("", xy=(y, x - 2.2), xytext=(y, x), arrowprops=dict(arrowstyle="-|>", color="k", lw=1.6), zorder=9)
    ax.text(y, x - 2.45, "N (client: street)", ha="center", fontsize=8, zorder=9)
    # true north arrow: screen vector (right, up) -> (dy, -dx) in plot axes (y right, x down)
    tx, ty = y + 2.2 * TRUE_N[0], x - 2.2 * TRUE_N[1]
    ax.annotate("", xy=(tx, ty), xytext=(y, x), arrowprops=dict(arrowstyle="-|>", color="#c60", lw=1.4, ls="--"), zorder=9)
    ax.text(tx + .15, ty, "true N (sun only)", fontsize=7, color="#c60", zorder=9)


def _layer(ax, a, cmap, vmin, vmax, label):
    im = ax.imshow(a.T, extent=[G.ORIGIN_Y, G.ORIGIN_Y + G.NY * G.CELL, G.ORIGIN_X + G.NX * G.CELL, G.ORIGIN_X],
                   cmap=cmap, vmin=vmin, vmax=vmax, interpolation="nearest", zorder=3)
    cb = plt.colorbar(im, ax=ax, fraction=.025, pad=.01)
    cb.set_label(label, fontsize=8)
    return im


def _save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / (name + ".png"), dpi=110)
    plt.close(fig)


def inventory_png():
    inv = _load("inventory")
    cls = np.array(inv["cell_class"])
    cols = ["#ffffff", "#c8e6c9", "#a5d6a7", "#ffe0b2", "#ffcc80", "#ffb74d", "#9e9e9e", "#6d4c41", "#212121", "#bdbdbd", "#e91e63"]
    fig, ax = _base("LDS inventory: surface class per 0.25 m cell, zones, openings onto each zone (client north up)")
    ax.imshow(cls.T, extent=[G.ORIGIN_Y, G.ORIGIN_Y + G.NY * G.CELL, G.ORIGIN_X + G.NX * G.CELL, G.ORIGIN_X],
              cmap=ListedColormap(cols), vmin=0, vmax=10, interpolation="nearest", zorder=2)
    _outlines(ax)
    for zn, z in inv["zones"].items():
        for o in z["openings"]:
            x, y = o["centre_m"]
            ax.plot([y], [x], marker="s", ms=4, color="#d81b60", zorder=8)
    for s in inv["services"]:
        ax.plot([s["at_m"][1]], [s["at_m"][0]], marker="^", ms=6, color="#1565c0", zorder=8)
    from matplotlib.lines import Line2D
    h = [plt.Rectangle((0, 0), 1, 1, fc=cols[k]) for k in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)]
    l = [inv["classes"][str(k)] for k in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)]
    h += [Line2D([], [], marker="s", ls="", color="#d81b60"), Line2D([], [], marker="^", ls="", color="#1565c0")]
    l += ["exterior opening", "extract-fan discharge (only service in the model)"]
    ax.legend(h, l, loc="lower right", fontsize=7, ncol=1, framealpha=.95)
    _north(ax)
    _save(fig, "plan-inventory")


def sun_pngs():
    sun = _load("sun")
    specs = [("sun_hours_summer_solstice", "Direct sun, 21 JUNE (summer solstice), hours per cell", 12),
             ("sun_hours_equinox", "Direct sun, 20 MARCH (equinox), hours per cell", 12),
             ("sun_hours_winter_solstice", "Direct sun, 21 DECEMBER (winter solstice), hours per cell", 12),
             ("summer_evening_17_20_standard_time", "SUMMER EVENING 17:00-20:00 STANDARD time: hours of sun out of 3 (shade = 3 - value)", 3),
             ("summer_evening_17_20_dst_clock", "SUMMER EVENING 17:00-20:00 on a DST (UTC+3) clock = 16-19 std: hours of sun out of 3", 3),
             ("winter_day_10_15", "WINTER DAY 10:00-15:00 (21 Dec): hours of sun out of 5", 5)]
    cmap = plt.get_cmap("YlOrRd").copy()
    cmap.set_under("#37474f")
    for key, title, vmax in specs:
        a = _rows(sun["layers"][key])
        fig, ax = _base(title + "\nlat %.4f lon %.4f (villa_env, plot-level not surveyed); enclosure only, no planting" % (sun["location"]["latitude"], sun["location"]["longitude"]))
        _layer(ax, np.where(a == 0, -0.01, a), cmap, 0, vmax, "hours of direct sun (dark = 0 h)")
        _outlines(ax); _north(ax)
        _save(fig, "plan-" + key.replace("_", "-"))


def privacy_pngs():
    pv = _load("privacy")
    a = _rows(pv["layers"]["overlooking_eyes_any_standing"])
    fig, ax = _base("PRIVACY: number of neighbour / apartment / sister eye points that see a standing person (1.525 m) in each cell")
    _layer(ax, np.where(a == 0, -0.01, a), plt.get_cmap("YlOrRd").copy().with_extremes(under="#e3f2fd"), 0, float(np.nanmax(a)), "eye points with a clear sightline (white-blue = unseen)")
    for v in pv["viewers"]:
        ex, ey, ez = v["eye_m"]
        if G.ORIGIN_Y - 2 < ey < G.ORIGIN_Y + G.NY * G.CELL + 2 and -3 < ex < 30:
            ax.plot([ey], [ex], marker=".", ms=3, color="#1a237e", zorder=8)
    _outlines(ax); _north(ax)
    ax.text(-29.9, 29.4, "dots = viewer eye points inside the frame (neighbours beyond the fences: see privacy.json)", fontsize=7)
    _save(fig, "plan-privacy-overlooked")
    groups = [g for g in pv["groups"] if g != "street"]
    fig, axs = plt.subplots(2, 3, figsize=(15, 9))
    for g, ax in zip(groups, axs.ravel()):
        a = _rows(pv["layers"]["overlooking_eyes_%s_standing" % g.replace("-", "_")])
        ax.imshow(np.where(a == 0, -0.01, a).T, extent=[G.ORIGIN_Y, G.ORIGIN_Y + G.NY * G.CELL, G.ORIGIN_X + G.NX * G.CELL, G.ORIGIN_X],
                  cmap=plt.get_cmap("YlOrRd").copy().with_extremes(under="#e3f2fd"), vmin=0, vmax=max(1, float(np.nanmax(a))), interpolation="nearest")
        for name, (x0, y0, x1, y1, _) in M.ZONES.items():
            ax.add_patch(Rectangle((y0, x0), y1 - y0, x1 - x0, fill=False, ec="k", lw=.8))
        ax.set_title("%s (max %d eyes)" % (g, np.nanmax(a)), fontsize=9)
        ax.set_aspect("equal")
    fig.suptitle("Privacy by viewer group (client north up, east right; white-blue = unseen from that group)")
    _save(fig, "plan-privacy-by-group")


def views_png():
    vw = _load("views")
    a = _rows(vw["layers"]["rooms_seeing_cell"])
    fig, ax = _base("VIEWS OUT: number of garden-facing rooms that see each cell (seated eye 1.125 m); squares = focal-point candidates")
    _layer(ax, np.where(a == 0, -0.01, a), plt.get_cmap("YlGn").copy().with_extremes(under="#eeeeee"), 0, float(np.nanmax(a)), "rooms that see the cell")
    _outlines(ax); _north(ax)
    for zn, picks in vw["focal_point_candidates"].items():
        for k, p in enumerate(picks):
            cx, cy = p["centre_m"]
            ax.add_patch(Rectangle((cy - p["patch_m"] / 2, cx - p["patch_m"] / 2), p["patch_m"], p["patch_m"], fill=False, ec="#d81b60", lw=1.6, zorder=8))
            ax.text(cy, cx, str(k + 1), color="#d81b60", fontsize=7, ha="center", va="center", zorder=9)
    _save(fig, "plan-views-out")


def wind_png():
    wd = _load("wind")
    fig, axs = plt.subplots(1, 3, figsize=(15, 5.6), subplot_kw=dict(projection="polar"))
    for ax, (name, s) in zip(axs, wd["sets"].items()):
        th = np.radians([x["from_bearing_true"] for x in s["sectors"]])
        ax.set_theta_zero_location("N"); ax.set_theta_direction(-1)
        ax.bar(th, [x["share_pct"] for x in s["sectors"]], width=math.radians(20), color="#4c72b0", ec="k")
        for lab, b in (("client N\n(street)", 290), ("client E", 20), ("client S", 110), ("client W\n(sister)", 200)):
            ax.annotate(lab, xy=(math.radians(b), ax.get_rmax() * 1.0), ha="center", fontsize=7, color="#c60")
        ax.set_title("%s\n%d h, calm %.0f%%, mean %.1f m/s\nbars: %% of hours wind blows FROM (true bearing)" % (name, s["hours"], s["calm_pct"], s["mean_speed_ms"]), fontsize=8)
    fig.suptitle("Wind rose, Cairo West AP TMYx (station-level, not on-site); orange = bearings the client's sides face (true)")
    _save(fig, "plan-wind-rose")


def all_plots():
    inventory_png(); sun_pngs(); privacy_pngs(); views_png(); wind_png()
