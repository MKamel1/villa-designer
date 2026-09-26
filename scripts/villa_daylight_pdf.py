"""Daylight report PDF from scripts/villa_daylight.py fetch (out/villa/daylight/<job>/report.json).

    PYTHONPATH=src python scripts/villa_daylight_pdf.py      # out/villa/daylight/Daylight-villa-options.pdf

Page 1: validation and the per-room average daylight factor of every option against the SLL minimum ADF cards.
Then one page per option: daylight factor maps of both storeys (every sensor point, colour = DF %).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from archpipe import daylight as D
from archpipe.concept import villa as V
from archpipe.safe_io import writable_path

sys.path.insert(0, str(Path(__file__).parent))
from villa_daylight import JOB, LOCAL                                 # noqa: E402

TARGET = {"bedroom": "sll-min-adf-bedroom", "living": "sll-min-adf-living", "dining": "sll-min-adf-living",
          "study": "sll-min-adf-living", "kitchen": "sll-min-adf-kitchen"}
OPTIONS = ["S1", "S5", "P1", "P2", "P3", "P4"]


def target(occ):
    cid = TARGET.get(occ)
    return (V._card(cid)[0], cid) if cid else (None, None)


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    rep = json.loads((LOCAL / "report.json").read_text(encoding="utf-8"))
    res, val = rep["results"], rep["validation"]
    out = writable_path(LOCAL.parent / "Daylight-villa-options.pdf")
    with PdfPages(out) as pdf:
        # ---- page 1: validation + table -------------------------------------------------------------------
        fig = plt.figure(figsize=(16.5, 11.7))
        vt = "; ".join("%s: %s" % (k, "PASS" if c["pass"] else "FAIL") for k, c in val["checks"].items())
        box = val["checks"]["box vs Metric Handbook eq. (4)"]
        import textwrap
        head = ("Validation: %s. Box room: Radiance %.2f %% vs Metric Handbook p. 9-8 eq. (4) %.2f %% (%.0f %% apart, "
                "tolerance %.0f %% fixed before the run)." % (vt, box["radiance"], box["formula"], box["relative"] * 100,
                                                              box["tolerance"] * 100))
        fig.suptitle("Daylight factor, CIE overcast sky (Radiance 6.0.1): %s\n" % rep["status"] +
                     "\n".join(textwrap.wrap(head, 170)), fontsize=10)
        rooms = {}
        for opt in OPTIONS:
            for rid, r in res.get(opt, {}).get("rooms", {}).items():
                rooms.setdefault((r["level"], rid), {})[opt] = r
        occ = {}
        from archpipe.concept import villa_options as VO
        from archpipe.concept import villa_parking as P
        for lay in [VO.s1(), VO.s5()] + P.options():
            for rid, r in lay["rooms"].items():
                occ[rid] = r["occupancy"]
        rows = []
        for (lv, rid) in sorted(rooms, key=lambda k: (k[0] != "B", k[1])):
            t, cid = target(occ.get(rid))
            if t is None:
                continue
            cells = []
            for opt in OPTIONS:
                r = rooms[(lv, rid)].get(opt)
                cells.append("-" if r is None else ("%.2f%s" % (r["adf"], "" if r["adf"] >= t else " *")))
            rows.append([lv, rid, "%.1f" % t] + cells)
        ax = fig.add_axes([0.03, 0.06, 0.94, 0.82])
        ax.axis("off")
        tb = ax.table(cellText=rows, colLabels=["storey", "room", "SLL min ADF %"] + OPTIONS, loc="upper center",
                      cellLoc="center", colWidths=[0.06, 0.2, 0.1] + [0.1] * len(OPTIONS))
        tb.auto_set_font_size(False)
        tb.set_fontsize(7.5)
        tb.scale(1, 1.25)
        for (i, j), cell in tb.get_celld().items():
            if i > 0 and j >= 3 and cell.get_text().get_text().endswith("*"):
                cell.set_facecolor("#f6d0d0")
        ax.text(0.0, -0.02, "Average daylight factor per room (%). * = under the SLL Code for Lighting minimum ADF "
                "(bedroom 1.0, living 1.5, kitchen 2.0; dining and study held to the living figure). Stated: no car on "
                "the deck, internal doors closed, open-plan joins open, clean glass (T 0.70), reflectances floor 0.2 / "
                "wall 0.5 / ceiling 0.7, guard rails solid, the neighbours' yards flat at street level.",
                transform=ax.transAxes, fontsize=7.5, wrap=True, va="top")
        pdf.savefig(fig)
        plt.close(fig)
        # ---- one page per option: DF maps -------------------------------------------------------------------
        for opt in OPTIONS:
            case = LOCAL / "cases" / opt
            if not (case / "out.txt").exists():
                continue
            meta = json.loads((case / "rooms.json").read_text(encoding="utf-8"))
            vals = [float(v) for v in (case / "out.txt").read_text().split()]
            pts = [tuple(map(float, l.split()[:3])) for l in (case / "points.txt").read_text().split("\n") if l.strip()]
            df = [D.df_percent(*vals[3 * i:3 * i + 3]) for i in range(len(pts))]
            fig, axes = plt.subplots(1, 2, figsize=(16.5, 11.7))
            for ax, lv, z in ((axes[0], "B", -3.0), (axes[1], "GF", 0.0)):
                sel = [(p, d) for p, d in zip(pts, df) if abs(p[2] - (z + 0.85)) < 0.01]
                sc = ax.scatter([p[1] for p, _ in sel], [-p[0] for p, _ in sel], c=[min(d, 5.0) for _, d in sel],
                                cmap="viridis", vmin=0, vmax=5, s=14, marker="s")
                for r in meta["rooms"]:
                    if r.get("level") != lv:
                        continue
                    poly = r["polygon"] + [r["polygon"][0]]
                    ax.plot([p[1] for p in poly], [-p[0] for p in poly], c="k", lw=0.6)
                    rr = res[opt]["rooms"][r["id"]]
                    cx = sum(p[0] for p in r["polygon"]) / len(r["polygon"])
                    cy = sum(p[1] for p in r["polygon"]) / len(r["polygon"])
                    ax.text(cy, -cx, "%s\n%.2f %%" % (r["id"], rr["adf"]), ha="center", va="center", fontsize=5.5,
                            bbox=dict(fc="white", ec="none", alpha=0.75, pad=0.2))
                ax.set_aspect("equal")
                ax.set_title({"B": "BASEMENT", "GF": "GROUND FLOOR"}[lv] + " - daylight factor % (street at the top)",
                             fontsize=10)
                ax.axis("off")
            fig.colorbar(sc, ax=axes, fraction=0.02, label="daylight factor % (5 % and above shown as 5)")
            fig.suptitle("Option %s: daylight factor maps (sensors 0.85 m above each floor, 0.5 m grid)" % opt,
                         fontsize=11, weight="bold")
            pdf.savefig(fig)
            plt.close(fig)
    print(out)


if __name__ == "__main__":
    main()
