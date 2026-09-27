"""D1 furnished: plans of both storeys with every piece and its clearance zones, the item schedule, the check report
and the decisions the layout needs from the client (Gate A).

    PYTHONPATH=src python scripts/villa_furnish_pdf.py      # out/villa/furnish-d1/D1-furnished.pdf
"""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

from archpipe import catalogue as cat
from archpipe.concept import revit_spec as RS
from archpipe.concept import villa as V
from archpipe.concept import villa_furnish as F
from archpipe.concept import villa_r11 as R

OUT = Path("out/villa/furnish-d1")
FILL = {"living": "#f4ead8", "dining": "#f2e3c6", "kitchen": "#efdcc6", "media": "#dcdcea", "wc": "#e0ecf3",
        "bathroom": "#e0ecf3", "ensuite": "#e0ecf3", "utility": "#e3ece0", "store": "#ececec", "stair": "#e4e4e4",
        "bedroom": "#ebe3f1", "study": "#f4ead8", "dressing": "#ebe3f1"}
DECISIONS = [
    ("Cinema seats", "Two recliners and a 1.19 m aisle. Three recliners fill the 2.99 m room and close the only way "
                     "to the store under the ramp. For three, the store needs its own door from the north patio "
                     "(through the kept 1.40 m yard wall)."),
    ("Family bathroom basin", "One basin. A double basin does not fit beside the WC and the walk-in shower with "
                              "their AD M access zones in 2.15 x 2.53 m."),
    ("Shared kids room (A)", "Two single beds, one desk and one 1.2 m wardrobe. A second desk and wardrobe do not "
                             "fit with a 750 mm zone beside each bed; a bunk bed would free the floor for both."),
    ("Parents' dressing", "The dressing room is 1.30 m deep: a 600 mm hanging wardrobe needs 914 mm in front of it "
                          "(1.51 m in all). Drawn with 350 mm open shelving. Hanging needs a choice: take 0.21 m from the "
                          "ensuite behind it (2.64 -> 2.43 m deep), or keep shelving only. The bedroom side cannot give it: "
                          "the king bed's 750 mm zone leaves 0.11 m."),
    ("Parents' door", "A pocket sliding door: a swinging door would hit the bedside table and the bed's 750 mm zone."),
    ("Garden living", "Tightest path in the basement: 0.92 m, beside the armchair near the east garden door "
                      "(914 mm needed)."),
    ("Changed from the questionnaire's first suggestions", "Updated on the questionnaire so you choose between options "
     "that fit: cinema 4 recliners -> 2; family bathroom double basin -> one; a desk per child -> one per bedroom (the "
     "study has the shared desk); lounge 6 seats -> 5; no bench at the parents' bed foot (it sits in the AD M foot "
     "zone); no pantry column in the tall wall (the front pantry holds 3.3 m of shelving); island hob 80 -> 90 cm."),
    ("Not furnished yet", "Garden terrace, BBQ, north patio and the deck (outdoor pieces follow your questionnaire "
                          "answers). Dimensions: piece sizes are in the schedule; the checks page lists the measured "
                          "clearances."),
]


def plan(ax, lay, items, sp, level):
    from matplotlib.patches import Polygon, Rectangle
    T = lambda x, y: (y, -x)                                              # noqa: E731  street up, east right
    rect = lambda r, **kw: Polygon([T(r[0], r[1]), T(r[2], r[1]), T(r[2], r[3]), T(r[0], r[3])], closed=True, **kw)  # noqa
    for rid, r in lay["rooms"].items():
        if r["level"] != level:
            continue
        ax.add_patch(rect(r["rect"], fc=FILL.get(r["occupancy"], "#f0f0f0"), ec="0.35", lw=0.6,
                          hatch="//" if r.get("void") else None))
        if not r.get("part_of"):
            x0, y0, x1, y1 = r["rect"]
            ax.text(*T(x0 + 0.12, (y0 + y1) / 2), r["name"].split(" (")[0], fontsize=4.2, color="0.35", ha="center",
                    va="top", rotation=0)
    for c in F._columns():
        ax.add_patch(rect(c, fc="#7a1f5c", ec="none"))
    for d in sp["doors"]:
        if d["level"] != level:
            continue
        ax_ = (d.get("span") or ["h"])[0]
        w = d["width"]
        a = (d["x"] - w / 2, d["y"]) if ax_ == "h" else (d["x"], d["y"] - w / 2)
        b = (d["x"] + w / 2, d["y"]) if ax_ == "h" else (d["x"], d["y"] + w / 2)
        ax.plot(*zip(T(*a), T(*b)), color="#1f6fb2" if d.get("garden") else "#c96b00", lw=2.2, solid_capstyle="butt")
    for w in sp["windows"]:
        if w["level"] != level:
            continue
        ax_ = (w.get("span") or ["h"])[0]
        a = (w["x"] - w["width"] / 2, w["y"]) if ax_ == "h" else (w["x"], w["y"] - w["width"] / 2)
        b = (w["x"] + w["width"] / 2, w["y"]) if ax_ == "h" else (w["x"], w["y"] + w["width"] / 2)
        ax.plot(*zip(T(*a), T(*b)), color="#1f6fb2", lw=1.2)
    for it in items:
        if it["level"] != level:
            continue
        t = cat.get(it["type"])
        for s in F.SIDES:
            if t.clearance[s] > 0:
                ax.add_patch(rect(F.side_zone(it, s, t.clearance[s] / 1000), fc="#3a8f5a", ec="none", alpha=0.12))
        fp = F.footprint(it)
        ax.add_patch(rect(fp, fc="white", ec="0.1", lw=0.7))
        for kind, a, b in F.module_spans(it):
            if kind != "counter":
                sub = (a, fp[1], b, fp[3]) if it["rot"] in (0, 180) else (fp[0], a, fp[2], b)
                ax.add_patch(rect(sub, fc="#d9d2c5", ec="0.3", lw=0.4))
        cx, cy = it["cx"], it["cy"]
        lab = it["id"].split("-", 1)[-1].replace("-", " ")
        ax.text(*T(cx, cy), lab, fontsize=3.8, ha="center", va="center")
        if it.get("chairs"):
            for k in range(it["chairs"] // 2):
                for sgn in (-1, 1):
                    x = fp[0] + (k + 0.5) * (fp[2] - fp[0]) / (it["chairs"] // 2)
                    y = (fp[3] + 0.05 if sgn > 0 else fp[1] - 0.5)
                    ax.add_patch(rect((x - 0.22, y, x + 0.22, y + 0.45), fc="#f6f6f6", ec="0.4", lw=0.4))
        if it.get("stools"):
            for k in range(it["stools"]):
                x = fp[0] + (k + 0.5) * (fp[2] - fp[0]) / it["stools"]
                ax.add_patch(rect((x - 0.2, fp[1] - 0.05, x + 0.2, fp[1] + 0.35), fc="#f6f6f6", ec="0.4", lw=0.4))
    xs = [v for r in lay["rooms"].values() if r["level"] == level for v in (r["rect"][0], r["rect"][2])]
    ys = [v for r in lay["rooms"].values() if r["level"] == level for v in (r["rect"][1], r["rect"][3])]
    ax.set_xlim(min(ys) - 0.4, max(ys) + 0.4)
    ax.set_ylim(-max(xs) - 0.4, -min(xs) + 0.4)
    ax.set_aspect("equal")
    ax.axis("off")


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    lay = R.design("D1")
    items = F.layout(lay)
    sp = RS.build(lay)
    res = F.check(items, lay)
    OUT.mkdir(parents=True, exist_ok=True)
    from archpipe.safe_io import writable_path
    path = writable_path(OUT / "D1-furnished.pdf")
    with PdfPages(path) as pdf:
        for level, title in (("B", "BASEMENT (FFL -1.80)"), ("GF", "GROUND FLOOR (FFL +1.20)")):
            fig, ax = plt.subplots(figsize=(11.7, 16.5))
            plan(ax, lay, items, sp, level)
            ax.set_title("D1 furnished: %s\nstreet at the top, garden at the bottom, east yard to the right; "
                         "green = clearance zones (cards), orange = doors, blue = glazing, purple = kept columns"
                         % title, fontsize=10)
            fig.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)
        # schedule
        rows = [[it["id"], it["room"], cat.get(it["type"]).label, "%.2f x %.2f" % (it["w"], it["d"]),
                 "%.2f" % it["h"], textwrap.shorten(it["why"], 95)] for it in items]
        for chunk in (rows[:34], rows[34:]):
            if not chunk:
                continue
            fig = plt.figure(figsize=(16.5, 11.7))
            ax = fig.add_axes([0.02, 0.02, 0.96, 0.9]); ax.axis("off")
            t = ax.table(cellText=chunk, colLabels=["item", "room", "type", "size m (w x d)", "height", "why"],
                         colWidths=[0.1, 0.09, 0.15, 0.08, 0.05, 0.53], loc="upper center", cellLoc="left")
            t.auto_set_font_size(False); t.set_fontsize(6.5); t.scale(1, 1.25)
            fig.suptitle("D1 furniture schedule (sizes are assumed product envelopes until products are chosen)",
                         fontsize=11)
            pdf.savefig(fig); plt.close(fig)
        # checks + decisions
        fig = plt.figure(figsize=(16.5, 11.7))
        ax = fig.add_axes([0.02, 0.45, 0.96, 0.48]); ax.axis("off")
        NAMES = {"inside_room": "every piece inside its room", "columns": "no piece on a kept column",
                 "overlap": "no two pieces overlap", "clearances": "clearance zones clear (AD M beds, TSS storage "
                 "and dining, Mitton sofa/desk, NKBA aisles and seating)", "doors": "door swings clear",
                 "windows": "no tall piece in front of glazing", "kitchen": "NKBA landing areas, dishwasher to sink",
                 "viewing": "TV / cinema viewing distance 1.0-1.5 x screen (Mitton); eye 0.45 m behind the seat "
                            "front is ASSUMED",
                 "routes": "914 mm path from every door, stair end and the parents' window to every piece's working "
                           "side (Mitton; AD M Diagram 2.4)",
                 "extended_table": "all the above re-run with the dining table extended to 2.8 m (for 10)"}
        crow = []
        for k, v in res.items():
            m = "; ".join("%s: %s" % kv for kv in list(v["measured"].items())[:4])
            crow.append([v["status"].upper(), textwrap.fill(NAMES[k], 58),
                         textwrap.fill(textwrap.shorten(("; ".join(v["problems"]) or m) or "-", 240), 120)])
        t = ax.table(cellText=crow, colLabels=["", "check", "result"], colWidths=[0.05, 0.3, 0.65], loc="upper center",
                     cellLoc="left")
        t.auto_set_font_size(False); t.set_fontsize(7); t.scale(1, 2.3)
        ax2 = fig.add_axes([0.02, 0.02, 0.96, 0.4]); ax2.axis("off")
        t2 = ax2.table(cellText=[[a, textwrap.fill(b, 140)] for a, b in DECISIONS], colLabels=["decision / note", ""],
                       colWidths=[0.16, 0.84], loc="upper center", cellLoc="left")
        t2.auto_set_font_size(False); t2.set_fontsize(7.5); t2.scale(1, 2.6)
        fig.suptitle("D1 furnished: checks and what the layout needs from you. Cards read on the held originals; "
                     "DIAGNOSTIC (no held card): the 914 mm in front of the washer/dryer and folding counter, 600 mm "
                     "at the stores, the recliner envelope", fontsize=10)
        pdf.savefig(fig); plt.close(fig)
    print(path, {k: v["status"] for k, v in res.items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
