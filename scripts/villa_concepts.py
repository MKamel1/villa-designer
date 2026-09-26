"""Concepts for the real villa: critique, write the layouts, draw plan PDFs for the client.

    PYTHONPATH=src python scripts/villa_concepts.py        # out/villa/concepts/*.pdf|png + spec/concepts/villa/*.json

Plans are drawn with the street at the top (as the client's old sheets), our villa right of the shared core.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from archpipe import villa_env as E
from archpipe import vocabulary as vocab
from archpipe.concept import villa as V

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out" / "villa" / "concepts"
SPEC = ROOT / "spec" / "concepts" / "villa"


def T(x, y):
    """Model (x along the bar from the street, y toward plot-east) -> sheet (street up, east right)."""
    return y, -x


def draw(lay, res, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon

    def poly(ax, rect, **kw):
        x0, y0, x1, y1 = rect
        ax.add_patch(Polygon([T(x0, y0), T(x1, y0), T(x1, y1), T(x0, y1)], closed=True, **kw))

    fig, axes = plt.subplots(1, 2, figsize=(16.5, 11.7))             # A3 landscape
    ext = lay.get("extension")
    for ax, lv in zip(axes, ("B", "GF")):
        # context: fence lines, yard, shared core
        px0, py0, px1, py1 = [v / 1000 for v in E.plot()]
        t = E.FENCE_T / 1000
        poly(ax, (px0 + t, V.AX, px1 - t, py1 - t), fc="#e9f2e1" if lv == "B" else "white", ec="none")
        for f in ((px0, V.AX, px0 + t, py1), (px0, py1 - t, px1, py1), (px1 - t, V.AX, px1, py1)):
            poly(ax, f, fc="#666666", ec="none")
        core = [(x0 / 1000, x1 / 1000, what.split(":")[0]) for _, x0, x1, what in E.CORE_GF]
        if lv == "GF":
            for x0, x1, what in core:
                poly(ax, (x0, V.m(E.SISTER_FACE), x1, V.YP), fc="#f3e4cf", ec="#9a8060", lw=0.6)
        else:
            poly(ax, (V.FRONT_SHARE[2], V.m(E.SISTER_FACE), V.REAR_SHARE[0], V.YP), fc="#f3e4cf", ec="#9a8060",
                 lw=0.6)
        sx0, _, sx1, _ = [v / 1000 for v in E.SHAFT]
        poly(ax, (sx0, V.m(E.SHAFT[1]), sx1, V.YP), fc="#bcd6ee", ec="#5577aa", lw=0.6, hatch="xx")
        cx, cy = T((V.XS + V.XR) / 2, V.m(E.SISTER_FACE) - 0.6)
        ax.text(*T(12.0, V.m(E.SISTER_FACE) + 0.4), "shared core (not ours): entrance, main stair, shaft, lobby, lift",
                rotation=90, ha="center", va="center", fontsize=6, color="#7a6040")
        # rooms
        for rid, r in lay["rooms"].items():
            if r["level"] != lv:
                continue
            circ = r["occupancy"] in vocab.CIRCULATION
            fc = "#eeeeee" if circ else "#fff8ec" if r.get("suite") else "white"
            poly(ax, r["rect"], fc=fc, ec="k", lw=1.2)
            x0, y0, x1, y1 = r["rect"]
            s = res["sizes"][rid]
            ax.text(*T((x0 + x1) / 2, (y0 + y1) / 2), f"{r['name']}\n{s['net_m2']:.1f} m²\n{s['net_w']:.2f} x {s['net_d']:.2f}",
                    ha="center", va="center", fontsize=5.6, rotation=0 if (y1 - y0) >= 1.6 else 90)
            if r["occupancy"] == "stair":
                ax.plot(*zip(T(x0, y0), T(x1, y1)), c="0.4", lw=0.6)
                ax.plot(*zip(T(x0, y1), T(x1, y0)), c="0.4", lw=0.6)
            # windows on allowed faces
            for e in V.edges(r["rect"]):
                for f in V.window_faces(lv, ext):
                    L_ = V.overlap_len(e, f)
                    if L_ >= 1.0 and (r["occupancy"] in vocab.HABITABLE or r["occupancy"] in vocab.SANITARY):
                        lo, hi = max(e[2], f[2]), min(e[3], f[3])
                        pad = 0.25
                        a, b = (lo + pad, hi - pad) if hi - lo > 1.2 else (lo, hi)
                        pts = [(a, e[1]), (b, e[1])] if e[0] == "h" else [(e[1], a), (e[1], b)]
                        ax.plot(*zip(*[T(*p) for p in pts]), c="tab:blue", lw=3.2, solid_capstyle="butt")
        # doors and entrances
        for a, b in lay["links"]:
            ra, rb = lay["rooms"][a], lay["rooms"][b]
            if ra["level"] != lv or rb["level"] != lv:
                continue
            best = max(((V.overlap_len(e1, e2), e1, e2) for e1 in V.edges(ra["rect"]) for e2 in V.edges(rb["rect"])),
                       key=lambda t_: t_[0])
            L_, e1, e2 = best
            if L_ <= 0:
                continue
            mid = (max(e1[2], e2[2]) + min(e1[3], e2[3])) / 2
            p = (mid, e1[1]) if e1[0] == "h" else (e1[1], mid)
            ax.plot(*T(*p), "o", ms=4, c="tab:orange")
        for rid, l2, seg in lay["entries"]:
            if l2 != lv:
                continue
            s = V.ENTRY_SEGMENTS[lv][seg]
            e = max(V.edges(lay["rooms"][rid]["rect"]), key=lambda e_: V.overlap_len(e_, s))
            lo, hi = max(e[2], s[2]), min(e[3], s[3])
            mid = (lo + hi) / 2
            p = (mid, e[1]) if e[0] == "h" else (e[1], mid)
            ax.plot(*T(*p), "s", ms=7, c="tab:red")
        # columns (CAD), both storeys
        for x0, y0, x1, y1 in E.COLUMNS:
            poly(ax, (x0 / 1000, y0 / 1000, x1 / 1000, y1 / 1000), fc="k", ec="none")
        # true north from the environment model (street facade faces 290 deg)
        th = math.radians(E.STREET_FACADE_AZIMUTH - 180.0)
        vx, vy = T(math.cos(th), math.sin(th))
        ox, oy = T(2.0, V.YE + 1.5)
        ax.annotate("", xy=(ox + 1.6 * vx, oy + 1.6 * vy), xytext=(ox, oy), arrowprops=dict(arrowstyle="-|>", lw=1.6))
        ax.text(ox + 2.1 * vx, oy + 2.1 * vy, "N", ha="center", va="center", fontsize=11, weight="bold")
        ax.text(*T(px0 - 0.6, (V.YP + V.YE) / 2), "STREET", ha="center", va="center", fontsize=9, color="0.4")
        ax.set_aspect("equal")
        X = [T(px0 - 1.5, V.m(E.SISTER_FACE) - 0.8), T(px1, py1)]
        ax.set_xlim(min(p[0] for p in X), max(p[0] for p in X) + 0.2)
        ax.set_ylim(min(p[1] for p in X), max(p[1] for p in X) + 0.2)
        ax.axis("off")
        name = {"B": "BASEMENT  FFL -1.80  (yard level)", "GF": "GROUND FLOOR  FFL +1.20"}[lv]
        ax.set_title(name, fontsize=11, weight="bold")
    fails = ", ".join(res["fails"]) or "none"
    warns = ", ".join(res["warnings"]) or "none"
    fig.suptitle(f"CONCEPT {lay['id']}: {lay['title']}\n{lay['summary']}\n"
                 f"Critic: fails {fails}; warnings {warns}.  Net areas inside assumed walls (ext 0.20, int 0.10).  "
                 "blue = window zone, orange = door, red = entrance, black = existing columns (keep)",
                 fontsize=8.5)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    for ext_ in (".pdf", ".png"):
        fig.savefig(str(path) + ext_, dpi=130)
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for lay in V.concepts():
        res = V.critique(lay)
        V.write(lay, res, SPEC)
        draw(lay, res, OUT / f"concept-{lay['id']}")
        rows.append((lay["id"], res["fails"], res["warnings"]))
        print(lay["id"], "fails", res["fails"], "warnings", res["warnings"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
