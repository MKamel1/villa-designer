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
        # alternative B: the street-level parking deck (GF sheet) and its outline over the room below (basement sheet)
        pk = lay.get("parking")
        if pk:
            if lv == "GF":
                poly(ax, pk["deck"], fc="#dddddd", ec="0.3", lw=1, hatch="..")
                x0, y0, x1, y1 = pk["deck"]
                cy0, cy1 = (y0 + y1) / 2 - 0.9, (y0 + y1) / 2 + 0.9
                for cx0 in (x0 + 0.15, x0 + 0.15 + 4.75):
                    poly(ax, (cx0, cy0, cx0 + 4.6, cy1), fc="white", ec="0.2", lw=0.8)
                    ax.text(*T(cx0 + 2.3, (y0 + y1) / 2), "car", ha="center", va="center", fontsize=6)
                gx = x0 - E.FENCE_T / 2000
                ax.plot(*zip(T(gx, y0 + 0.3), T(gx, y1 - 0.3)), c="tab:red", lw=4)
                ax.text(*T(x0 - 0.9, (y0 + y1) / 2), "new car gate", ha="center", va="center", fontsize=6,
                        color="tab:red")
                ax.text(*T(x0 + 5.0, y1 - 0.25), "parking deck +/-0.00 (street level)", ha="center", va="center",
                        fontsize=6)
                sx0, sy0, sx1, sy1 = pk["deck_stair"]
                poly(ax, pk["deck_stair"], fc="white", ec="0.2", lw=0.8)
                for i in range(1, 10):
                    xx = sx0 + i * (sx1 - sx0) / 10
                    ax.plot(*zip(T(xx, sy0), T(xx, sy1)), c="0.4", lw=0.5)
                ax.text(*T((sx0 + sx1) / 2, sy0 - 0.3), "down to yard", ha="center", va="center", fontsize=5.5)
            else:
                poly(ax, pk["deck"], fill=False, ec="0.4", lw=0.8, ls="--")
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


def room_at(lay, level, x, y):
    for rid, r in lay["rooms"].items():
        x0, y0, x1, y1 = r["rect"]
        if r["level"] == level and x0 <= x <= x1 and y0 <= y <= y1:
            return r
    return None


def draw_section(lay, checks, path, x_cut=5.5):
    """Cross-section across the bar and the east strip at x_cut, street datum, plus the elevation-check table."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig = plt.figure(figsize=(16.5, 11.7))
    ax = fig.add_axes([0.05, 0.42, 0.9, 0.5])
    B, GF = V.LEVELS["B"], V.LEVELS["GF"]
    APT, ROOF = GF + V.STOREY, GF + 2 * V.STOREY
    sis = V.m(E.SISTER_FACE)
    fence_out = V.FENCE_E + E.FENCE_T / 1000
    neigh = fence_out + E.OFFSET_E / 1000

    def box(y0, z0, y1, z1, **kw):
        ax.add_patch(Rectangle((y0, z0), y1 - y0, z1 - z0, **kw))

    box(sis - 0.3, B - 0.4, V.YP, ROOF, fc="#f3e4cf", ec="#9a8060", lw=0.6)
    ax.text((sis + V.YP) / 2, (B + APT) / 2, "shared core\n(not ours)", ha="center", va="center", fontsize=7, rotation=90)
    for z, name in ((B, "basement"), (GF, "GF"), (APT, "apartment (not ours)"), (ROOF, "roof")):
        box(V.YP, z - V.SLAB - (0.2 if z == B else 0), V.YE, z, fc="0.55", ec="none")
    for z in (GF, APT, ROOF):
        for y0 in (V.YP, V.YE - 0.25):
            box(y0, z - V.BEAM, y0 + 0.25, z, fc="0.35", ec="none")
    for zf, lv in ((B, "B"), (GF, "GF")):
        r = room_at(lay, lv, x_cut, (V.YP + V.YE) / 2 + 0.8)
        ax.text((V.YP + V.YE) / 2, zf + 1.3, (r["name"] if r else "") + f"\nFFL {zf:+.2f}", ha="center", fontsize=8)
        ax.annotate("", xy=((V.YP + V.YE) / 2 + 1.3, zf + V.STOREY - V.SLAB), xytext=((V.YP + V.YE) / 2 + 1.3, zf + V.FLOOR_BUILDUP),
                    arrowprops=dict(arrowstyle="<->", lw=0.7))
        ax.text((V.YP + V.YE) / 2 + 1.4, zf + 1.35, f"{V.STOREY - V.SLAB - V.FLOOR_BUILDUP:.2f} clear\n"
                f"{V.STOREY - V.BEAM - V.FLOOR_BUILDUP:.2f} under beam", fontsize=6.5)
    ax.text((V.YP + V.YE) / 2, APT + 1.3, "apartment above (not ours)", ha="center", fontsize=8, color="0.3")
    if lay.get("stair") == "spine" and V.X0 + V.EXT_WALL <= x_cut <= V.SPINE_X1:
        g = V.stair_geometry("spine")
        h = (x_cut - V.X0 - V.EXT_WALL) * g["rise"] / g["going"]
        box(V.YP + 0.25, B, V.YS1, B + h, fc="#c8c8c8", ec="0.2", lw=0.6)
        ax.text((V.YP + V.YS1) / 2 + 0.1, B + h + 0.15, "stair\nflight", fontsize=6, ha="center")
    # east strip
    pk = lay.get("parking")
    if pk:
        box(V.YE, -V.DECK_BUILDUP - V.DECK_SLAB, V.FENCE_E, 0.0, fc="0.55", ec="none")
        box(V.YE + 0.25, V.EXTRA_FFL - 0.25, V.FENCE_E, V.EXTRA_FFL, fc="0.7", ec="none")
        box(V.YE + 0.55, 0.0, V.YE + 0.55 + 1.85, 1.45, fc="white", ec="0.2", lw=0.8)
        ax.text(V.YE + 1.47, 0.7, "car", ha="center", fontsize=7)
        ax.text((V.YE + V.FENCE_E) / 2, V.EXTRA_FFL + 1.0, f"extra room\nFFL {V.EXTRA_FFL:+.2f}\n2.40 clear",
                ha="center", fontsize=7)
        ax.text((V.YE + V.FENCE_E) / 2, 0.15 + 1.5, "parking deck +/-0.00", ha="center", fontsize=7)
    else:
        box(V.YE, B - 0.25, V.FENCE_E, B, fc="#b7d3a0", ec="none")
        ax.text((V.YE + V.FENCE_E) / 2, B + 0.2, "yard -1.80", ha="center", fontsize=7)
    box(V.FENCE_E, B - 0.6, fence_out, B + E.FENCE_H / 1000, fc="0.4", ec="none")
    ax.text(fence_out + 0.1, B + E.FENCE_H / 1000, f"fence top {B + E.FENCE_H / 1000:+.2f}", fontsize=7, va="bottom")
    box(neigh, B, neigh + 3.0, B + E.NEIGHBOUR_H / 1000, fc="#c9c9d9", ec="#555577", lw=0.8)
    ax.text(neigh + 1.5, B + 6, "neighbour\n12 m", ha="center", fontsize=7)
    for z, lab in ((0.0, "street +/-0.00"), (B, "-1.80"), (GF, "+1.20"), (APT, "+4.20"), (ROOF, "+7.20")):
        ax.axhline(z, color="0.6", lw=0.5, ls=":")
        ax.text(sis - 0.5, z, lab, fontsize=7, ha="right", va="center")
    ax.set_xlim(sis - 2.5, neigh + 3.5)
    ax.set_ylim(min(B, V.EXTRA_FFL if pk else B) - 1.0, ROOF + 1.0)
    ax.set_aspect("equal")
    ax.set_xlabel("section across the bar at x = %.1f m from the street wall (looking toward the rear); metres" %
                  (x_cut - V.X0))
    ax.set_title(f"CONCEPT {lay['id']}: section and elevation checks (datum: street +/-0.00)", fontsize=11,
                 weight="bold")
    tx = fig.add_axes([0.05, 0.02, 0.9, 0.36])
    tx.axis("off")
    rows = [[c["status"].upper(), c["item"], f"{c['achieved']} {c['unit']}", f"{c['required']}",
             (c["card"].split(" (")[0] + ("; " + c["note"] if c["note"] else ""))[:95]] for c in checks]
    t = tx.table(cellText=rows, colLabels=["", "check", "achieved", "required", "source / note"], loc="upper center",
                 colWidths=[0.05, 0.35, 0.08, 0.08, 0.44], cellLoc="left")
    t.auto_set_font_size(False)
    t.set_fontsize(6.5)
    t.scale(1, 1.25)
    for ext_ in (".pdf", ".png"):
        fig.savefig(str(path) + ext_, dpi=130)
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for lay in V.concepts():
        res = V.critique(lay)
        res["elevation_checks"] = V.elevation_checks(lay)
        V.write(lay, res, SPEC)
        draw(lay, res, OUT / f"concept-{lay['id']}")
        draw_section(lay, res["elevation_checks"], OUT / f"section-{lay['id']}")
        rows.append((lay["id"], res["fails"], res["warnings"]))
        print(lay["id"], "fails", res["fails"], "warnings", res["warnings"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
