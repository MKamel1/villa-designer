"""One PDF for the client to confirm the kept NE yard wall: dimensioned plan and section drawn from Revit's own
read-back (revit/probe_yard_wall.py), beside the plan, section and 3D view Revit exported.

    PYTHONPATH=src python scripts/yard_wall_pdf.py      # out/villa/yard-wall/NE-yard-wall-check.pdf
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).parent))
from villa_option_pdfs import light                                  # noqa: E402

DIR = Path("out/villa/yard-wall")
STREET = -1200.0                       # model z of street +-0.00 (mm)


def img(prefix):
    return sorted(DIR.glob(prefix + "*.png"))[0]


def dim(ax, p, q, text, off=(0, 0), **kw):
    ax.annotate("", p, q, arrowprops=dict(arrowstyle="<->", lw=0.7, color=kw.get("c", "k")))
    ax.text((p[0] + q[0]) / 2 + off[0], (p[1] + q[1]) / 2 + off[1], text, ha="center", va="center", fontsize=7,
            color=kw.get("c", "k"), bbox=dict(fc="white", ec="none", pad=0.5))


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.backends.backend_pdf import PdfPages
    rb = json.loads((DIR / "yard-wall-readback.json").read_text(encoding="utf-8"))
    E = rb["elements"]
    wx0, wy0, wz0, wx1, wy1, wz1 = E["yard-wall-ne"]
    col = next(c["bbox"] for c in rb["ne_columns"] if c["bbox"][2] < -2000)       # the basement storey column
    fs, fe, rp = E["fence-street"], E["fence-east"], E["ramp"]
    YE, X0, XS = -23591.0, 3617.0, 1787.0                                          # building face, street face, terrace
    T = lambda x, y: (y, -x)                                                     # noqa: E731  street up, east right

    with PdfPages(DIR / "NE-yard-wall-check.pdf") as pdf:
        # ---- page 1: plan -------------------------------------------------------------------------------------
        fig = plt.figure(figsize=(16.5, 11.7))
        ax = fig.add_axes([0.03, 0.06, 0.52, 0.82])

        def rect(x0, y0, x1, y1, **kw):
            a, b = T(x0, y0)
            c, d = T(x1, y1)
            ax.add_patch(Rectangle((min(a, c), min(b, d)), abs(c - a), abs(d - b), **kw))

        rect(X0, -28671, 8000, YE, fc="#f2f2f2", ec="k", lw=1)                     # the villa (basement)
        ax.text(*T(6000, -26200), "VILLA (basement)", ha="center", fontsize=9, color="0.4")
        rect(-123, -28671, X0, wy0, fc="#dcefd6", ec="none")                       # north sunken yard
        ax.text(*T(700, -26200), "north sunken yard (-1.80)", ha="center", fontsize=8, color="darkgreen")
        ax.plot(*zip(T(XS, -28671), T(XS, YE)), ls=":", c="0.4", lw=0.8)
        ax.text(*T(XS + 150, -27400), "GF terrace edge above", fontsize=6.5, color="0.4")
        rect(rp[0], rp[1], 8000, rp[4], fc="none", ec="tab:orange", ls="--", lw=1)  # ramp, above
        ax.text(*T(4500, -22100), "RAMP above (10 %, street 0.00 at the gate)\nstore under it", ha="center",
                fontsize=7.5, color="tab:orange")
        rect(fs[0], -28671, fs[3], fs[4], fc="0.35", ec="k")                        # street fence
        rect(fe[0], fe[1], 8000, fe[4], fc="0.35", ec="k")                          # east fence
        ax.text(*T(-700, -25000), "STREET FENCE", ha="center", fontsize=7)
        ax.text(*T(6000, -20100), "EAST FENCE", ha="center", fontsize=7, rotation=90)
        rect(col[0], col[1], col[3], col[4], fc="k", ec="k")                        # NE column
        ax.annotate("NE column (Revit %d)\n%.0f x %.0f" % (next(c["id"] for c in rb["ne_columns"] if c["bbox"][2] < -2000),
                                                            col[3] - col[0], col[4] - col[1]),
                    T(col[3], col[1]), xytext=T(5600, -25300), fontsize=7, arrowprops=dict(arrowstyle="-", lw=0.5))
        rect(wx0, wy0, wx1, wy1, fc="tab:red", ec="k")                             # the wall
        ax.annotate("EXISTING WALL (kept)\n1.40 m high from the basement floor", T(1500, wy0),
                    xytext=T(1500, -25400), fontsize=8, color="tab:red", weight="bold", ha="center",
                    arrowprops=dict(arrowstyle="->", lw=0.8, color="tab:red"))
        # dimensions
        dim(ax, T(wx0, wy1 + 500), T(wx1, wy1 + 500), "%.0f" % (wx1 - wx0), off=(0, 0))
        dim(ax, T(1000, wy0), T(1000, wy1), "", c="tab:red")
        ax.text(*T(1000, wy1 + 120), "%.0f thick" % (wy1 - wy0), fontsize=7, color="tab:red", ha="left",
                va="bottom", rotation=0)
        dim(ax, T(-123 + 200, wy1), T(-123 + 200, fe[1]), "gate %.0f" % (fe[1] - wy1), off=(0, 0.25))
        dim(ax, T(7000, YE), T(7000, fe[1]), "%.0f" % (fe[1] - YE))
        ax.text(*T(X0 - 150, wy1 + 20), "wall face flush with the column face; %.0f mm\ninside the building's east "
                "face line" % (wy1 - YE if wy1 > YE else YE - wy1), fontsize=6.5, ha="left", va="bottom",
                rotation=0, color="0.25")
        ax.set_xlim(-28900, -19700)
        ax.set_ylim(-8200, 900)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title("PLAN at the basement (street at the top, east to the right) - mm, from the Revit model",
                     fontsize=10, weight="bold")
        ax2 = fig.add_axes([0.57, 0.12, 0.42, 0.70])
        ax2.imshow(np.rot90(light(img("yard-wall-plan")), k=-1))
        ax2.axis("off")
        ax2.set_title("Revit basement plan export (same orientation): the wall is the thin element from the\n"
                      "street fence to the column, beside the store under the ramp", fontsize=8.5)
        fig.suptitle("NE yard wall - please confirm location and height (model out/villa/options-r7/omar-option-P1.rvt,"
                     " read back from Revit)\nASSUMED, not measured: 250 mm thickness, and the wall's east face flush "
                     "with the column's east face.", fontsize=10)
        pdf.savefig(fig)
        plt.close(fig)

        # ---- page 2: section across the wall at 1.8 m from the building -----------------------------------------
        fig = plt.figure(figsize=(16.5, 11.7))
        ax = fig.add_axes([0.03, 0.08, 0.55, 0.78])
        x = 1800.0
        z = lambda v: v - STREET                                                   # noqa: E731  street datum
        ramp_top = 0.10 * (x - rp[0])
        ramp_soff = ramp_top - 350
        ax.add_patch(Rectangle((-26500, z(-3200)), 6500, 200, fc="0.8", ec="k"))   # yard floor
        ax.add_patch(Rectangle((wy0, z(wz0)), wy1 - wy0, wz1 - wz0, fc="tab:red", ec="k"))
        ax.add_patch(Rectangle((fe[1], z(fe[2])), fe[4] - fe[1], fe[5] - fe[2], fc="0.35", ec="k"))
        ax.add_patch(Rectangle((YE, ramp_soff), fe[1] - YE, 350, fc="tab:orange", ec="k", alpha=0.8))
        for lab, lv in (("street +-0.00", 0), ("basement FFL -1.80", -1800), ("GF FFL +1.20", 1200)):
            ax.axhline(lv, c="0.6", lw=0.6, ls="--")
            ax.text(-26550, lv + 40, lab, fontsize=7, color="0.35", ha="right")   # axis is inverted: the free side
        ax.text(-24900, -1100, "north sunken yard\n(patio)", ha="center", fontsize=8, color="darkgreen")
        ax.text(-22100, -1100, "store under the ramp", ha="center", fontsize=8, color="0.3")
        ax.text(-22100, ramp_top + 150, "RAMP (top street +%.2f here)" % (ramp_top / 1000), ha="center",
                fontsize=8, color="tab:orange")
        dim(ax, (wy0 - 250, -1800), (wy0 - 250, z(wz1)), "%.0f" % (wz1 - wz0), off=(-280, 0), c="tab:red")
        dim(ax, (wy1 + 250, z(wz1)), (wy1 + 250, ramp_soff), "%.0f gap" % (ramp_soff - z(wz1)), off=(420, 0))
        ax.annotate("", (fe[1] - 250, -1800), (fe[1] - 250, z(fe[5])), arrowprops=dict(arrowstyle="<->", lw=0.7))
        ax.text(fe[1] - 330, 1700, "east fence\n%.0f from the\nbasement floor" % (fe[5] - fe[2]), fontsize=7,
                ha="left", va="center")
        ax.text(wy0 + 125, z(wz1) + 60, "wall top\nstreet %.2f" % (z(wz1) / 1000), ha="center", va="bottom",
                fontsize=7, color="tab:red")
        ax.set_xlim(-20000, -26600)                  # looking toward the villa from the street: east on the LEFT
        ax.set_ylim(-2300, 2600)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title("SECTION across the wall, 1.8 m in front of the villa, looking from the street toward the villa "
                     "(east on the LEFT)\nlevels on the street datum; at the street gate the gap under the ramp is "
                     "%.0f mm, at the column %.0f mm" % (0.10 * (wx0 - rp[0]) - 350 - z(wz1),
                                                         0.10 * (wx1 - rp[0]) - 350 - z(wz1)), fontsize=9.5,
                     weight="bold")
        ax2 = fig.add_axes([0.60, 0.10, 0.39, 0.74])
        ax2.imshow(light(img("yard-wall-section-across")))
        ax2.axis("off")
        ax2.set_title("Revit section at the same cut, same direction (east on the left). Left to right: east fence,\n"
                      "ramp slab (cut), the store's two walls (hatched), the 1.40 m wall (plain), the villa beyond", fontsize=8.5)
        fig.suptitle("NE yard wall - height and relation to the ramp", fontsize=11, weight="bold")
        pdf.savefig(fig)
        plt.close(fig)

        # ---- page 3: Revit 3D --------------------------------------------------------------------------------
        fig = plt.figure(figsize=(16.5, 11.7))
        ax = fig.add_axes([0.05, 0.04, 0.9, 0.86])
        ax.imshow(light(img("yard-wall-3d"), lines=False, crop=True))
        ax.axis("off")
        fig.suptitle("Revit 3D from above the east yard, cut just above street level; fences and other context "
                     "hidden; the ramp is see-through.\nThe kept wall is the RED strip from the villa's NE column "
                     "(magenta) to the street end. The grey wall just in front of it is the store's own side wall, "
                     "which the option model\nbuilds on the villa's face line 50 mm east of the kept wall: once you "
                     "confirm the wall, the store will use the kept wall instead (plus infill up to the ramp)",
                     fontsize=10)
        pdf.savefig(fig)
        plt.close(fig)
    print(DIR / "NE-yard-wall-check.pdf")


if __name__ == "__main__":
    main()
