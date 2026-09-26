"""Stair options sheet: basement plans shaded by whether each point sees the back garden, plus the metrics table.

    PYTHONPATH=src python scripts/villa_stair_options.py     # out/villa/concepts/stair-options.pdf|png + .json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from archpipe.concept import stair_options as O
from archpipe.concept import villa as V

OUT = Path("out/villa/concepts")


def T(x, y):
    return y, -x                     # street at the top, east to the right (as the plan sheets)


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon

    res = [O.analyse(o) for o in O.OPTIONS]
    fig = plt.figure(figsize=(16.5, 11.7))
    for k, r in enumerate(res):
        ax = fig.add_axes([0.02 + k * 0.245, 0.30, 0.23, 0.62])

        def poly(rect, **kw):
            x0, y0, x1, y1 = rect
            ax.add_patch(Polygon([T(x0, y0), T(x1, y0), T(x1, y1), T(x0, y1)], closed=True, **kw))

        poly((V.X0, V.YP, V.XR, V.YE), fc="white", ec="k", lw=1.2)
        xs = [T(*p)[0] for p, v in r["points"]]
        ys = [T(*p)[1] for p, v in r["points"]]
        cs = ["#7cc36a" if v else "#c9c9c9" for p, v in r["points"]]
        ax.scatter(xs, ys, c=cs, s=5, marker="s", linewidths=0)
        ob = r["obstacles"]
        poly(ob["stair"], fc="#9aa7c7", ec="k", lw=0.8)
        ax.text(*T((ob["stair"][0] + ob["stair"][2]) / 2, (ob["stair"][1] + ob["stair"][3]) / 2), "stair",
                ha="center", va="center", fontsize=6)
        poly(ob["flex"], fc="#f2e3c6", ec="k", lw=0.8)
        ax.text(*T((ob["flex"][0] + ob["flex"][2]) / 2, (ob["flex"][1] + ob["flex"][3]) / 2), "flex", ha="center",
                va="center", fontsize=6)
        for s in ob["services"]:
            poly(s, fc="#e8c4c4", ec="k", lw=0.8)
        for c in ob["columns"]:
            poly(c, fc="k", ec="none")
        g = O.GLAZING
        ax.plot(*zip(T(g[0], g[1]), T(g[0], g[2])), c="tab:blue", lw=4)
        ax.text(*T(g[0] + 0.5, (g[1] + g[2]) / 2), "garden (rear glazing)", ha="center", fontsize=6, color="tab:blue")
        e = next(o for o in O.OPTIONS if o["id"] == r["id"])["entrance"]
        for i in range(0, 12, 2):
            gy = g[1] + (i + 0.5) * (g[2] - g[1]) / 12
            blocked = any(O._seg_hits_rect(e, (g[0], gy), b) for b in [ob["stair"], ob["flex"]] + ob["services"]
                          + ob["columns"])
            ax.plot(*zip(T(*e), T(g[0], gy)), c="tab:red" if blocked else "tab:green", lw=0.5, ls="--")
        ax.plot(*T(*e), "s", ms=7, c="tab:red")
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(f"{r['id']}: {r['name']}\nsees garden {r['garden_view_m2']} of {r['open_m2']} m² "
                     f"({int(r['garden_view_share'] * 100)} %); entrance view {int(r['entrance_view_share'] * 100)} %",
                     fontsize=7.5)
    tx = fig.add_axes([0.02, 0.02, 0.96, 0.25])
    tx.axis("off")
    rows = [[r["id"], f"{r['garden_view_m2']} / {r['open_m2']}", f"{int(r['entrance_view_share'] * 100)} %",
             "none" if not r["clashes"] else ", ".join(r["clashes"]), f"{r['rise']} / {r['going']:.0f} / {r['pitch_deg']}°",
             f"{r['gf_facade_m']} m", r["opening"], r["core_doors"]] for r in res]
    t = tx.table(cellText=rows, colLabels=["", "basement m² seeing the garden / open", "entrance sees garden",
                                           "3D clashes (Python + Revit)", "rise / going / pitch",
                                           "GF facade taken", "GF slab", "core doors"],
                 colWidths=[0.03, 0.12, 0.08, 0.1, 0.1, 0.07, 0.25, 0.25], loc="upper center", cellLoc="left")
    t.auto_set_font_size(False)
    t.set_fontsize(7)
    t.scale(1, 1.6)
    fig.suptitle("BASEMENT STAIR OPTIONS: how much of the open basement sees the back garden "
                 "(green = sight line to the rear glazing; red/pink = dirty kitchen and guest WC; grey = blocked)",
                 fontsize=10, weight="bold")
    OUT.mkdir(parents=True, exist_ok=True)
    for ext in (".pdf", ".png"):
        fig.savefig(OUT / ("stair-options" + ext), dpi=130)
    (OUT / "stair-options.json").write_text(json.dumps([{k: v for k, v in r.items() if k not in ("points",)}
                                                        for r in res], indent=1), encoding="utf-8")
    for r in res:
        print(r["id"], r["garden_view_m2"], r["open_m2"], r["entrance_view_share"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
