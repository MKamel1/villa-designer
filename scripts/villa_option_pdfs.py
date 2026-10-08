"""One PDF per option, from the Revit models: plans and 3D views exported from Revit, room names with Revit's own
areas, the garden-view analysis and every check.

    PYTHONPATH=src python scripts/villa_option_pdfs.py [r7]         # out/villa/options[-r7]/Option-<id>.pdf
    PYTHONPATH=src python scripts/villa_option_pdfs.py spec [r7]    # the Revit spec for build_villa_option.py

Needs revit/build_villa_option.py to have run (out/villa/options/*.png + readback.json).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np

from archpipe.concept import stair_options as SO
from archpipe.concept import villa as V
from archpipe.concept import revit_spec as RS
from archpipe.concept import villa_options as VO
from archpipe.concept import villa_parking as VP

from archpipe.concept import villa_r11 as VR                          # noqa: E402
from archpipe.execution_context import ContextError, project_context  # noqa: E402

SETS = {"s": (VO.options, Path("out/villa/options")), "r7": (VP.options, Path("out/villa/options-r7")),
        "r11": (VR.designs, Path("out/villa/designs-r12"))}
OPT = SETS["s"][1]
CROP = (0.6, -31.8, 28.0, -20.6)          # the plan views' crop box (build_villa_option.py), metres
CROP_PARKING = (-0.9, -31.8, 28.0, -20.6)  # parking options: the north yard is in the plan


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
        x0, y0, x1, y1 = CROP_PARKING if lay.get("parking2") else CROP
        ax.imshow(rot, extent=[y0, y1, -x1, -x0])
        for rid, r in lay["rooms"].items():
            if r["level"] != lv:
                continue
            a, b, c, d = r["rect"]
            A = areas.get((lv, rid))
            ax.text(*T((a + c) / 2, (b + d) / 2), f"{r['name']}\n{A:.1f} m²" if A else r["name"], ha="center",
                    va="center", fontsize=5.3, rotation=0 if (d - b) >= 1.6 else 90,
                    bbox=dict(fc="white", ec="none", alpha=0.7, pad=0.3))
        ax.text(*T(x0 + 0.3, (V.YP + V.YE) / 2), "STREET", ha="center", fontsize=8, color="0.3")
        ax.text(*T(V.XR + 1.0, (V.YP + V.YE) / 2), "GARDEN (rear yard)", ha="center", fontsize=8, color="0.3")
        pk = lay.get("parking2")
        if pk:                                        # the ramp and deck are above the basement cut / below the GF
            parts = [(pk["ramp"], "RAMP %d %% (%d %% ends) 0.00 to +%.2f"
                      % (pk["gradient"] * 100, pk.get("transition", (0, 0))[1] * 100, pk["deck_top"])),
                     (pk["deck"], "DECK +%.2f = GF (%d car%s)" % (pk["deck_top"], pk["cars"], "s" if pk["cars"] > 1
                                                                   else ""))]
            if pk.get("roof_beyond_deck"):
                parts.append((pk["roof_beyond_deck"], "roof"))
            dd = lay.get("deck_door")
            if dd and lv == "GF":
                ax.plot(*zip(T(dd["x0"], V.YE), T(dd["x1"], V.YE)), c="tab:orange", lw=4, solid_capstyle="butt")
                ax.annotate("1.80 sliding door\nto the deck", T((dd["x0"] + dd["x1"]) / 2, V.YE),
                            xytext=T((dd["x0"] + dd["x1"]) / 2, V.YE - 1.2), fontsize=5.5, color="tab:orange",
                            ha="center", arrowprops=dict(arrowstyle="-", lw=0.5, color="tab:orange"))
            for rect, lab in parts:
                a, b, c, d = rect
                ax.plot(*zip(*[T(a, b), T(c, b), T(c, d), T(a, d), T(a, b)]), ls="--", c="tab:orange", lw=1)
                if lv == "GF":
                    ax.text(*T((a + c) / 2, (b + d) / 2), lab, ha="center", va="center", fontsize=5.2, rotation=90,
                            color="tab:orange", bbox=dict(fc="white", ec="none", alpha=0.8, pad=0.3))
        np_ = lay.get("north_patio")
        if np_ and lv == "B":
            from matplotlib.patches import Polygon as Pg
            a, b, c, d = np_["rect"]
            ax.add_patch(Pg([T(a, b), T(c, b), T(c, d), T(a, d)], closed=True, fc="#dcefd6", ec="tab:green",
                            lw=0.8, alpha=0.6, zorder=0))
            ca, _, cc, _ = np_["covered"]
            ax.plot(*zip(T(ca, b), T(ca, d)), ls=":", c="tab:green", lw=0.8)
            ax.text(*T((a + ca) / 2, (b + d) / 2), "sunken patio (open)", ha="center", va="center", fontsize=5.5,
                    color="darkgreen")
            ax.text(*T((ca + cc) / 2, (b + d) / 2), "loggia under the GF terrace", ha="center", va="center",
                    fontsize=5.5, color="darkgreen")
        if lv == "B":
            wx0, wy0, wx1, wy1 = (v / 1000 for v in V.E.YARD_WALL)
            from matplotlib.patches import Polygon as Pg
            ax.add_patch(Pg([T(wx0, wy0), T(wx1, wy0), T(wx1, wy1), T(wx0, wy1)], closed=True, fc="k", ec="k"))
            ax.annotate("existing wall 1.40 m (kept)", T(wx0 + 0.5, wy1), xytext=T(wx0 + 0.5, wy1 + 1.5),
                        fontsize=5.5, ha="center", arrowprops=dict(arrowstyle="-", lw=0.5))
        ax.set_xlim(y0, y1)
        ax.set_ylim(-x1, -x0)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title({"B": "BASEMENT  FFL -1.80 (yard level)", "GF": "GROUND FLOOR  FFL +1.20"}[lv] +
                     "  (Revit plan view, 1:100 model)", fontsize=10, weight="bold")
    crit = ", ".join(res["fails"]) or "no failures"
    warn = "; ".join(f"{w['room']} {w['achieved_m2']} m² vs M4(2) {w['required_m2']} (preference)"
                     for c in res["checks"] if c["check"] == "min_area" for w in c.get("preference", []))
    others = ["%s (%s)" % (c["check"], "; ".join(str(x) for x in (c.get("borrowed_light") or c.get("warnings") or [])) or
                           "see checks page") + " borrowed light, no own window" for c in res["checks"] if c["status"] == "warning" and c["check"] != "min_area"]
    warn = "; ".join([w for w in [warn] + others if w])
    import textwrap
    summary = "\n".join(textwrap.wrap(lay["summary"], 190))
    fig.suptitle(f"{lay['title']}\n{summary}\nCritic: {crit}. Warnings: {warn or 'none'}. Room areas are "
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
    if find(f"{lay['id']}-street-view"):
        spots[2] = ("garden-view", [0.01, 0.01, 0.40, 0.34], spots[2][2])
        spots.append(("street-view", [0.42, 0.01, 0.57, 0.34], "From the street corner: gate, ramp up to the GF-level "
                                                               "deck, car envelope(s), guard rails; cut at 2.55 m"))
    for key, box, title in spots:
        p = find(f"{lay['id']}-{key}")
        ax = fig.add_axes(box)
        ax.imshow(light(p, lines=False, crop=True))
        ax.axis("off")
        ax.set_title(title, fontsize=9)
    fig.suptitle(f"{lay['title']}: 3D views from the Revit model ({OPT.as_posix()}/omar-option-{lay['id']}.rvt)",
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
                     + (e["card"].split(" (")[0] + "; " + e["note"])[:200]])
    if lay.get("parking2"):
        sp = RS.build(lay)
        doors = [d for d in rb.get("doors", []) if d.get("height")]
        missing = len(rb.get("doors", [])) - len(doors)
        probs = RS.clearance_problems(lay, rb.get("walls", []), doors, sp.get("infills", []))
        ok = not probs and missing == 0 and rb.get("walls")
        rows.append(["PASS" if ok else "FAIL", "BUILT: walls/doors under the ramp fit (Revit read-back)",
                     ("%d problems" % len(probs) + ("; " + "; ".join(probs[:2]) if probs else "") +
                      ("; %d doors without a read height" % missing if missing else ""))[:200]])
    built_doors = [dict(d, level=d["level"]) for d in rb.get("doors", []) if d.get("width")]
    op = RS.opening_problems({"windows": RS.build(lay)["windows"], "doors": built_doors})
    rows.append(["PASS" if not op else "FAIL", "BUILT: no door or window through a kept column",
                 ("%d problems" % len(op) + ("; " + "; ".join(op[:2]) if op else ""))[:200]])
    sp_ = RS.build(lay)
    if sp_.get("dropped"):
        rows.append(["ADVISORY", "openings left out at a column (spec)",
                     "; ".join("%s %s: %s" % (d["room"], d["level"], d["reason"]) for d in sp_["dropped"])[:200]])
    wc = RS.window_credit_problems(lay, rb.get("windows", []), rb.get("doors", []))
    rows.append(["PASS" if not wc and rb.get("windows") is not None else "FAIL",
                 "BUILT: every room credited with a window has one (Revit read-back)",
                 ("%d problems" % len(wc) + ("; " + "; ".join(wc[:2]) if wc else ""))[:200]])
    gp = RS.glazing_problems(lay, rb.get("windows", []), rb.get("doors", []))
    rows.append(["PASS" if not gp and rb.get("windows") is not None else "FAIL",
                 "BUILT: street face and extension end glazed floor to beam (Revit read-back)",
                 ("%d problems" % len(gp) + ("; " + "; ".join(gp[:2]) if gp else ""))[:200]])
    rows.append(["BUILT", "Revit model",f"walls {rb['built'].get('walls')}, doors {rb['built'].get('doors')}, windows "
                 f"{rb['built'].get('windows')}, rooms {len(rb['rooms'])}, build failures {len(rb['failed'])}"])
    t = tx.table(cellText=rows, colLabels=["", "check", "result / basis"], colWidths=[0.07, 0.25, 0.68],
                 loc="upper center", cellLoc="left")
    t.auto_set_font_size(False)
    t.set_fontsize(5.8)
    t.scale(1, 1.18)
    fig.suptitle(f"{lay['title']}: checks (critic, elevations, stair in 3D) and the garden view", fontsize=10,
                 weight="bold")
    pdf.savefig(fig)
    plt.close(fig)


def main(argv=None) -> int:
    global OPT
    args = sys.argv[1:] if argv is None else argv[1:]
    make, OPT = SETS["r11" if "r11" in args else "r7" if "r7" in args else "s"]
    is_spec = "spec" in args
    try:
        project_context(
            ROOT,
            Path(__file__).resolve(),
            "villa-option-pdfs",
            inputs=[] if is_spec else [OPT / "readback.json"],
            output=OPT,
            modules=["numpy", "PIL", "matplotlib"],
        )
    except ContextError as exc:
        print("PREFLIGHT FAILED: " + str(exc), file=sys.stderr)
        return 2
    if is_spec:
        OPT.mkdir(parents=True, exist_ok=True)
        path = OPT / "options-spec.json"
        path.write_text(json.dumps([RS.build(l) for l in make()], indent=1), encoding="utf-8")
        print(path)
        from archpipe.stage_result import enforce_clean_verdict, write_stage_result
        stage_record = OPT / "villa-option-pdfs.stage-result.json"
        write_stage_result(
            "villa-option-pdfs",
            record_path=stage_record,
            inputs=[],
            outputs=[path],
            exit_code=0,
            metadata={"mode": "spec"},
        )
        return enforce_clean_verdict(True, exit_code=1)
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.backends.backend_pdf import PdfPages
    rbs = {o["id"]: o for o in json.loads((OPT / "readback.json").read_text(encoding="utf-8"))["options"]}
    made = []
    for lay in make():
        rb = rbs.get(lay["id"])
        if rb is None:
            print("no Revit read-back for", lay["id"])
            continue
        res = V.critique(lay)
        op = SO.analyse_layout(lay)
        path = OPT / f"Option-{lay['id']}.pdf"
        from archpipe.safe_io import writable_path
        path = writable_path(path)
        with PdfPages(path) as pdf:
            plan_page(pdf, lay, rb, res)
            views_page(pdf, lay)
            checks_page(pdf, lay, res, rb, op)
        made.append(path)
        print(path, "built:", rb["built"], "failed:", len(rb["failed"]))
    failed_items = [
        f"{lay['id']}: {f}"
        for lay in make()
        for f in (rbs.get(lay["id"]) or {}).get("failed", [])
    ]
    bad = len(failed_items) > 0
    from archpipe.stage_result import enforce_clean_verdict, write_stage_result
    stage_record = OPT / "villa-option-pdfs.stage-result.json"
    inputs = [p for p in [OPT / "readback.json", OPT / "options-spec.json", *sorted(OPT.glob("*.png"))] if p.is_file()]
    write_stage_result(
        "villa-option-pdfs",
        record_path=stage_record,
        inputs=inputs,
        outputs=made,
        exit_code=1 if bad else 0,
        metadata={
            "options_made": [p.name for p in made],
            "failed_count": len(failed_items),
            "failed": failed_items,
            "passed": not bad,
        },
    )
    return enforce_clean_verdict({"passed": not bad, "failed": failed_items}, exit_code=1)


if __name__ == "__main__":
    sys.exit(main())
