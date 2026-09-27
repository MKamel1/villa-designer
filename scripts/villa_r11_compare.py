"""Round 11: the four designs side by side (basement plans, what changed, areas, measured daylight).

    PYTHONPATH=src python scripts/villa_r11_compare.py      # out/villa/designs-r12/Compare-D1-D3.pdf

Daylight from out/villa/daylight/summary-r12.json (villa_daylight_summary.py r11), areas from the critic's net sizes.
"""
from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

from archpipe.concept import villa as V
from archpipe.concept import villa_r11 as R

OUT = Path("out/villa/designs-r12")
SUM = Path("out/villa/daylight/summary-r12.json")
COLOURS = {"living": "#f6d8a8", "dining": "#f3c37d", "kitchen": "#e9a86b", "media": "#8c8fb3", "wc": "#b9d7ea",
           "utility": "#c9dcc4", "store": "#dddddd", "stair": "#bbbbbb", "hall": "#f2f2f2", "entrance": "#f2f2f2",
           "study": "#f6e3c4", "bedroom": "#d9c7e8", "bathroom": "#b9d7ea", "ensuite": "#b9d7ea",
           "corridor": "#f2f2f2", "landing": "#f2f2f2", "dressing": "#e6dcef"}


def plan(ax, lay, level):
    from matplotlib.patches import Rectangle
    for rid, r in lay["rooms"].items():
        if r["level"] != level:
            continue
        x0, y0, x1, y1 = r["rect"]
        fc = "white" if r.get("void") else COLOURS.get(r["occupancy"], "#eeeeee")
        ax.add_patch(Rectangle((y0, -x1), y1 - y0, x1 - x0, fc=fc, ec="0.3", lw=0.5, hatch="//" if r.get("void") else None))
        if (x1 - x0) > 0.9 and (y1 - y0) > 0.9:
            ax.text((y0 + y1) / 2, -(x0 + x1) / 2, "\n".join(textwrap.wrap(r["name"].split(" (")[0], 12)),
                    ha="center", va="center", fontsize=4.2)
    ax.set_xlim(V.YP - 1.4, V.FENCE_E + 0.2)
    ax.set_ylim(-(V.XR + 0.3), -(V.FENCE_N - 0.2))
    ax.set_aspect("equal")
    ax.axis("off")


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    lays = R.designs()
    day = json.loads(SUM.read_text(encoding="utf-8"))["options"] if SUM.exists() else {}
    OUT.mkdir(parents=True, exist_ok=True)
    from archpipe.safe_io import writable_path
    path = writable_path(OUT / "Compare-D1-D3.pdf")
    with PdfPages(path) as pdf:
        fig, axes = plt.subplots(1, 3, figsize=(16.5, 11.7))
        for ax, lay in zip(axes, lays):
            plan(ax, lay, "B")
            ax.set_title(textwrap.fill(lay["title"].replace("Design ", ""), 38), fontsize=8, weight="bold")
            rs = day.get(lay["id"], {}).get("rooms", {})
            lines = []
            for rid in ("lounge", "family", "kitchen", "dining", "sitting", "living"):
                r = rs.get(rid)
                if r and r.get("df") is not None:
                    lines.append("%-8s DF %.2f %%  sDA %s %%" % (rid, r["df"], r.get("sda300")))
            ax.text(0.5, -0.02, "\n".join(lines) or "(daylight pending)", transform=ax.transAxes, ha="center",
                    va="top", fontsize=6.3, family="monospace")
        fig.suptitle("Round 11: the four designs, BASEMENT (street at the top, garden at the bottom, east yard to the "
                     "right)\nDaylight: CIE overcast daylight factor at 0.85 m and sDA300 (share of floor with 300 lx for "
                     "half the year); white finishes and floor-to-beam glazing in all four", fontsize=10)
        pdf.savefig(fig)
        plt.close(fig)
        fig, axes = plt.subplots(1, 3, figsize=(16.5, 11.7))
        for ax, lay in zip(axes, lays):
            plan(ax, lay, "GF")
            ax.set_title(lay["id"] + (" - GF with the void over the lounge" if lay["id"] == "D4" else " - GF (settled)"),
                         fontsize=9, weight="bold")
        fig.suptitle("Round 11: GROUND FLOOR (the settled plan; D4 cuts a void over the basement lounge)", fontsize=10)
        pdf.savefig(fig)
        plt.close(fig)
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
