"""D1 lighting and finishes for review: out/villa/render-d1/D1-lighting-finishes.pdf

    PYTHONPATH=src python scripts/villa_lighting_pdf.py

Pages: lighting plans (basement, GF) with every fitting by kind; the function check (task points and rooms,
achieved vs required, card per row); the beauty intent per room; the luminaire schedule (product or GENERIC);
the finishes schedule.
"""
import sys
import textwrap
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                     # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages                # noqa: E402
from matplotlib.patches import Rectangle                            # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from archpipe.concept import villa_furnish as F                      # noqa: E402
from archpipe.concept import villa_lighting as VL                    # noqa: E402
from archpipe.concept import villa_r11 as R                          # noqa: E402
from archpipe.concept import villa_render as VR                      # noqa: E402

OUT = ROOT / "out" / "villa" / "render-d1"
STYLE = {"DL": ("o", "#333333", 16), "DLN": ("o", "#d62728", 22), "ADJ": ("D", "#ff7f0e", 18),
         "WW": ("v", "#9467bd", 20), "PEN-GLOBE": ("o", "#2ca02c", 70), "PEN-SMALL": ("o", "#2ca02c", 40),
         "PEN-LIN": ("s", "#2ca02c", 60), "SCONCE": ("h", "#17becf", 34), "STEP": ("^", "#8c564b", 18),
         "PATH": ("^", "#8c564b", 18)}
STRIP = {"COVE": "#e377c2", "BACK": "#bcbd22", "UC": "#1f77b4", "RAIL": "#1f77b4", "TOE": "#8c564b",
         "NL": "#8c564b"}

BEAUTY = [
    ("Street lounge", "A cove along the street and stair sides makes the ceiling float over the family TV room; soft "
     "ambient downlights dim low for films; a reading spot over the armchair; the walnut fluted TV wall catches the "
     "cove's grazing light."),
    ("Kitchen", "Three opal globes over the island are the room's jewellery, 762 mm above the worktop; task light "
     "comes from flush spots on the cooking side and over the sink run, and a strip under the wall units; the "
     "island's plinth glows at night so it floats."),
    ("Dining", "A linear pendant along the table draws the eye and lights faces and food; two adjustable spots cross "
     "the table from opposite corners (never straight down); the sideboard and the art above it are accented at "
     "~30 deg."),
    ("Garden living", "The walnut library wall is backlit shelf by shelf so it reads as a lantern from the garden; a "
     "cove on the dining and library sides; a reading spot at the window bench; downlights low."),
    ("Cinema", "Only the rear wall is washed, dimmed; a low glow along the floor to the door; nothing on the screen."),
    ("Stair", "A cluster of three globes drops into the stair void from the GF ceiling: the heart of the house, seen "
     "from both floors; warm step markers every third tread at night."),
    ("GF corridor", "Lit by its long wall (grazing wall washers), not by a row of spots; low path markers to the "
     "bathrooms at night (2200 K)."),
    ("Parents' bedroom", "A cove grazes the oak-slatted headboard wall; low opal globes hang either side of the bed; "
     "reading spots on each pillow; everything dims to candle levels."),
    ("Dressing", "Light over every hanging rail (clothes lit from the front-top), soft aisle downlights."),
    ("Bathrooms", "Opal sconces either side of each mirror at eye level for faces, a flush spot over the basin for "
     "the counter, warm toe-kick glow under the vanity at night."),
    ("Kids' rooms", "Soft ambient, a task spot over every desk, a warm 2200 K glow under the bed as night light."),
    ("Study / game room", "Task spots over both desks, ambient dimmable down to gaming levels."),
]


def plan(ax, lay, level, fx):
    for rid, r in lay["rooms"].items():
        if r["level"] == level:
            x0, y0, x1, y1 = r["rect"]
            ax.add_patch(Rectangle((y0, -x1), y1 - y0, x1 - x0, fc="#f6f2ea", ec="0.55", lw=0.5))
            if not r.get("part_of"):
                ax.text((y0 + y1) / 2, -(x0 + x1) / 2, r["name"].split(" (")[0], fontsize=4, color="0.45",
                        ha="center", va="center")
    for it in F.layout(lay):
        if it["level"] == level:
            q = F.footprint(it)
            ax.add_patch(Rectangle((q[1], -q[2]), q[3] - q[1], q[2] - q[0], fc="#e3ddd0", ec="0.7", lw=0.3))
    for f in fx:
        if f.level != level:
            continue
        if f.kind in STRIP:
            a = (f.x - f.along[0] * f.length / 2, f.y - f.along[1] * f.length / 2)
            b = (f.x + f.along[0] * f.length / 2, f.y + f.along[1] * f.length / 2)
            ax.plot([a[1], b[1]], [-a[0], -b[0]], color=STRIP[f.kind], lw=1.6, solid_capstyle="butt")
        else:
            m, c, s = STYLE[f.kind]
            ax.scatter([f.y], [-f.x], marker=m, s=s, c=c, edgecolors="k", linewidths=0.3, zorder=5)
    ax.set_aspect("equal")
    ax.axis("off")


def main():
    lay = R.design("D1")
    VL.bind_products()
    fx = VL.design(lay)
    res = VL.check(lay, fx)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "D1-lighting-finishes.pdf"
    with PdfPages(path) as pdf:
        for level, title in (("B", "BASEMENT (FFL -1.80)"), ("GF", "GROUND FLOOR (FFL +1.20)")):
            fig = plt.figure(figsize=(16.5, 11.7))
            ax = fig.add_axes([0.02, 0.1, 0.72, 0.84])
            plan(ax, lay, level, fx)
            lg = fig.add_axes([0.76, 0.1, 0.22, 0.84])
            lg.axis("off")
            yy = 0.97
            counts = Counter(f.kind for f in fx if f.level == level)
            for k in list(STYLE) + list(STRIP):
                if not counts.get(k):
                    continue
                prod = VL.PRODUCTS.get(k)
                name = (prod["code"] + (" (substitute)" if prod["substitute"] else "")) if prod else "GENERIC"
                if k in STRIP:
                    lg.plot([0.0, 0.06], [yy, yy], color=STRIP[k], lw=2)
                else:
                    m, c, s = STYLE[k]
                    lg.scatter([0.03], [yy], marker=m, s=s, c=c, edgecolors="k", linewidths=0.3)
                lg.text(0.09, yy, "%s x%d  %s\n%s" % (k, counts[k], VL.KINDS[k]["what"], name), fontsize=6.3,
                        va="center")
                yy -= 0.055
            lg.set_xlim(0, 1)
            lg.set_ylim(0, 1)
            fig.suptitle("D1 lighting: %s  (street at the top; flush trimless downlights for ambient, per the "
                         "client; pendants and spots for task and centrepieces)" % title, fontsize=10)
            pdf.savefig(fig)
            plt.close(fig)
        # function
        fig = plt.figure(figsize=(16.5, 11.7))
        ax = fig.add_axes([0.02, 0.03, 0.96, 0.9])
        ax.axis("off")
        rows = [[t["status"].upper(), t["room"], t["what"], "%d" % t["achieved_lx"], "%d" % t["required_lx"],
                 t["card"]] for t in res["tasks"]]
        rows += [[r["status"].upper(), r["room"], "room floor average", "%d" % r["avg_floor_lx_direct"],
                  "%d" % r["required_lx"], r["card"]] for r in res["rooms"]]
        t = ax.table(cellText=rows, colLabels=["", "room", "task / plane", "achieved lx", "required lx", "card"],
                     colWidths=[0.06, 0.13, 0.2, 0.09, 0.09, 0.3], loc="upper center", cellLoc="left")
        t.auto_set_font_size(False)
        t.set_fontsize(6.2)
        t.scale(1, 1.05)
        fig.suptitle("FUNCTION: every task and room against IES Lighting Handbook 10th ed. Table 33.2 (maintained, "
                     "observers 25-65). " + res["note"] + ". Full output; scenes dim to ~1.3x the target.",
                     fontsize=9)
        pdf.savefig(fig)
        plt.close(fig)
        # beauty
        fig = plt.figure(figsize=(16.5, 11.7))
        ax = fig.add_axes([0.02, 0.03, 0.96, 0.9])
        ax.axis("off")
        t = ax.table(cellText=[[a, textwrap.fill(b, 150)] for a, b in BEAUTY], colLabels=["room", "what makes it "
                     "beautiful (layers: ambient / task / accent / decorative / night)"], colWidths=[0.14, 0.86],
                     loc="upper center", cellLoc="left")
        t.auto_set_font_size(False)
        t.set_fontsize(7.5)
        t.scale(1, 2.6)
        fig.suptitle("BEAUTY: the lighting intent per room (Lighting Design Basics pp. 58-63 layers; cove, accent "
                     "30 deg and pendant 762 mm are carded)", fontsize=10)
        pdf.savefig(fig)
        plt.close(fig)
        # schedules
        fig = plt.figure(figsize=(16.5, 11.7))
        ax = fig.add_axes([0.02, 0.5, 0.96, 0.44])
        ax.axis("off")
        counts = Counter(f.kind for f in fx)
        lens = defaultdict(float)
        for f in fx:
            lens[f.kind] += f.length
        rows = []
        for k, spec in VL.KINDS.items():
            if not counts.get(k):
                continue
            p = VL.PRODUCTS.get(k)
            qty = ("%.1f m" % lens[k]) if spec["mount"] == "strip" else "%d" % counts[k]
            rows.append([k, textwrap.fill(spec["what"], 45), qty,
                         textwrap.fill(p["what"] if p else "GENERIC stand-in: %s lm, %s K (product to choose)"
                                       % (spec.get("lm") or "%s/m" % spec.get("lm_per_m"), spec["cct"]), 80),
                         ("%.0f lm %s W" % (p["lm"], p["watts"])) if p else "-"])
        t = ax.table(cellText=rows, colLabels=["kind", "requirement", "qty", "product", "per fitting"],
                     colWidths=[0.07, 0.25, 0.06, 0.48, 0.1], loc="upper center", cellLoc="left")
        t.auto_set_font_size(False)
        t.set_fontsize(6.3)
        t.scale(1, 1.7)
        ax2 = fig.add_axes([0.02, 0.02, 0.96, 0.45])
        ax2.axis("off")
        used = {}
        for rid, (fl, wl, cl) in VR.FINISH.items():
            for part, m in (("floor", fl), ("walls", wl), ("ceiling", cl)):
                used.setdefault((part, m), []).append(rid)
        rows = [[part, m, textwrap.fill(VR.M[m]["note"], 70), "%.2f" % VR.M[m].get("reflectance", 0),
                 textwrap.fill(", ".join(sorted(rs)), 70)] for (part, m), rs in sorted(used.items())]
        t = ax2.table(cellText=rows, colLabels=["surface", "finish", "what", "reflectance", "rooms"],
                      colWidths=[0.06, 0.1, 0.36, 0.06, 0.42], loc="upper center", cellLoc="left")
        t.auto_set_font_size(False)
        t.set_fontsize(6.0)
        t.scale(1, 1.6)
        fig.suptitle("SCHEDULES: luminaires (verified iGuzzini Laser Evo where bound; GENERIC stand-ins named) and "
                     "finishes (ASSUMED from the taste profile: no finishes answers yet)", fontsize=10)
        pdf.savefig(fig)
        plt.close(fig)
    print(path)


if __name__ == "__main__":
    main()
