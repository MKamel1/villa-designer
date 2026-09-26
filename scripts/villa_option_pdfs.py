"""One PDF per option, from the Revit models: plans and 3D views exported from Revit, room names with Revit's own
areas, the garden-view analysis and every check.

    PYTHONPATH=src python scripts/villa_option_pdfs.py      # out/villa/options/Option-<id>.pdf

Needs revit/build_villa_option.py to have run (out/villa/options/*.png + readback.json).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from archpipe.concept import stair_options as SO
from archpipe.concept import villa as V
from archpipe.concept import villa_options as VO

OPT = Path("out/villa/options")
CROP = (0.6, -31.8, 28.0, -20.6)          # the plan views' crop box (build_villa_option.py), metres


def light(path, lines=True, crop=False):
    """Revit exports on its dark canvas: turn the background white; in PLAN views also turn the white linework dark
    (3D views keep their shading: their white is wall surface, not linework). crop: trim to the drawn content."""
    from PIL import Image
    im = np.asarray(Image.open(path).convert("RGB")).astype(int)
    bg = im[2, 2]
    d = np.abs(im - bg).sum(axis=2)
    out = im.copy()
    out[d < 40] = 255
    if lines:
        bright = (im.min(axis=2) > 170) & (d >= 40)
        out[bright] = 40
    if crop:
        mask = d >= 40
        rows, cols = np.where(mask.any(axis=1))[0], np.where(mask.any(axis=0))[0]
        if rows.size and cols.size:
            pad = 20
            out = out[max(0, rows[0] - pad):rows[-1] + pad, max(0, cols[0] - pad):cols[-1] + pad]
    return out.astype(np.uint8)


def find(prefix):
    hits = sorted(OPT.glob(prefix + "*.png"))
    return hits[0] if hits else None


def T(x, y):
    return y, -x


def plan_page(pdf, lay, rb, res):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(16.5, 11.7))
    areas = {(r["level"], r["id"]): r["area_m2"] for r in rb["rooms"]}
    for ax, lv, key in ((axes[0], "B", "plan-B"), (axes[1], "GF", "plan-GF")):
        img = light(find(f"{lay['id']}-{key}"))
        rot = np.rot90(img, k=-1)                     # street to the top, east to the right
        x0, y0, x1, y1 = CROP
        ax.imshow(rot, extent=[y0, y1, -x1, -x0])
        for rid, r in lay["rooms"].items():
            if r["level"] != lv:
                continue
            a, b, c, d = r["rect"]
            A = areas.get((lv, rid))
            ax.text(*T((a + c) / 2, (b + d) / 2), f"{r['name']}\n{A:.1f} m²" if A else r["name"], ha="center",
                    va="center", fontsize=5.3, rotation=0 if (d - b) >= 1.6 else 90,
                    bbox=dict(fc="white", ec="none", alpha=0.7, pad=0.3))
        ax.text(*T(V.X0 - 1.2, (V.YP + V.YE) / 2), "STREET", ha="center", fontsize=8, color="0.3")
        ax.text(*T(V.XR + 1.0, (V.YP + V.YE) / 2), "GARDEN (rear yard)", ha="center", fontsize=8, color="0.3")
        ax.set_xlim(y0, y1)
        ax.set_ylim(-x1, -x0)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title({"B": "BASEMENT  FFL -1.80 (yard level)", "GF": "GROUND FLOOR  FFL +1.20"}[lv] +
                     "  (Revit plan view, 1:100 model)", fontsize=10, weight="bold")
    crit = ", ".join(res["fails"]) or "no failures"
    warn = "; ".join(f"{w['room']} {w['achieved_m2']} m² vs M4(2) {w['required_m2']} (preference)"
                     for c in res["checks"] if c["check"] == "min_area" for w in c.get("preference", []))
    fig.suptitle(f"{lay['title']}\n{lay['summary']}\nCritic: {crit}. Warnings: {warn or 'none'}. Room areas are "
                 "Revit's own (room boundaries from the built walls).", fontsize=8.5)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    pdf.savefig(fig)
    plt.close(fig)


def views_page(pdf, lay):
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(16.5, 11.7))
    spots = [("basement-cutaway", [0.01, 0.36, 0.60, 0.58], "Basement, cut under the GF slab (from the garden side)"),
             ("GF-cutaway", [0.52, 0.36, 0.47, 0.58], "Ground floor, cut at 2.55 m"),
             ("garden-view", [0.2, 0.01, 0.6, 0.34], "The villa in its surroundings (neighbours, fence, apartment "
                                                      "above)")]
    for key, box, title in spots:
        p = find(f"{lay['id']}-{key}")
        ax = fig.add_axes(box)
        ax.imshow(light(p, lines=False, crop=True))
        ax.axis("off")
        ax.set_title(title, fontsize=9)
    fig.suptitle(f"{lay['title']}: 3D views from the Revit model (out/villa/options/omar-option-{lay['id']}.rvt)",
                 fontsize=10, weight="bold")
    pdf.savefig(fig)
    plt.close(fig)


def checks_page(pdf, lay, res, rb, op):
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon
    fig = plt.figure(figsize=(16.5, 11.7))
    ax = fig.add_axes([0.02, 0.08, 0.26, 0.82])

    def poly(rect, **kw):
        a, b, c, d = rect
        ax.add_patch(Polygon([T(a, b), T(c, b), T(c, d), T(a, d)], closed=True, **kw))

    poly((V.X0, V.YP, V.XR, V.YE), fc="white", ec="k", lw=1)
    xs = [T(*p)[0] for p, v in op["points"]]
    ys = [T(*p)[1] for p, v in op["points"]]
    ax.scatter(xs, ys, c=["#7cc36a" if v else "#c9c9c9" for p, v in op["points"]], s=4, marker="s", linewidths=0)
    poly(op["obstacles"]["stair"], fc="#9aa7c7", ec="k", lw=0.6)
    for r in op["obstacles"]["services"]:
        poly(r, fc="#e8c4c4", ec="k", lw=0.5)
    for c in op["obstacles"]["columns"]:
        poly(c, fc="k", ec="none")
    g = SO.GLAZING
    ax.plot(*zip(T(g[0], g[1]), T(g[0], g[2])), c="tab:blue", lw=4)
    if op["entrance"]:
        ax.plot(*T(*op["entrance"]), "s", c="tab:red", ms=7)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(f"Basement view to the garden\n{op['garden_view_m2']} of {op['open_m2']} m² "
                 f"({int(op['garden_view_share'] * 100)} %) sees the rear glazing;\nfrom the entrance (red): "
                 f"{int(op['entrance_view_share'] * 100)} % of it", fontsize=8.5)
    tx = fig.add_axes([0.30, 0.05, 0.69, 0.87])
    tx.axis("off")
    rows = []
    for c in res["checks"]:
        if c["status"] in ("pass", "fail", "warning"):
            rows.append([c["status"].upper(), c["check"], c["basis"][:110]])
    for e in V.elevation_checks(lay):
        rows.append([e["status"].upper(), e["item"][:60], f"{e['achieved']} {e['unit']} (need {e['required']}); "
                     + (e["card"].split(" (")[0] + "; " + e["note"])[:80]])
    rows.append(["BUILT", "Revit model", f"walls {rb['built'].get('walls')}, doors {rb['built'].get('doors')}, windows "
                 f"{rb['built'].get('windows')}, rooms {len(rb['rooms'])}, build failures {len(rb['failed'])}"])
    t = tx.table(cellText=rows, colLabels=["", "check", "result / basis"], colWidths=[0.07, 0.25, 0.68],
                 loc="upper center", cellLoc="left")
    t.auto_set_font_size(False)
    t.set_fontsize(6.2)
    t.scale(1, 1.18)
    fig.suptitle(f"{lay['title']}: checks (critic, elevations, stair in 3D) and the garden view", fontsize=10,
                 weight="bold")
    pdf.savefig(fig)
    plt.close(fig)


def main():
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.backends.backend_pdf import PdfPages
    rbs = {o["id"]: o for o in json.loads((OPT / "readback.json").read_text(encoding="utf-8"))["options"]}
    made = []
    for lay in VO.options():
        rb = rbs.get(lay["id"])
        if rb is None:
            print("no Revit read-back for", lay["id"])
            continue
        res = V.critique(lay)
        op = SO.analyse_layout(lay)
        path = OPT / f"Option-{lay['id']}.pdf"
        with PdfPages(path) as pdf:
            plan_page(pdf, lay, rb, res)
            views_page(pdf, lay)
            checks_page(pdf, lay, res, rb, op)
        made.append(path)
        print(path, "built:", rb["built"], "failed:", len(rb["failed"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
