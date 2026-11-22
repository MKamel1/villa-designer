"""Round-2 runner: build the decided design, check it, critique it, schedule it, draw it, and write knowledge/landscape/concept/final/.

    PYTHONPATH=src python -m archpipe.landscape.concept.final_run [--no-draw]

The visualisation layout (final_vis) is written and drawn but never checked, scheduled or counted.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

from . import final as F, final_checks as K, final_fire as FF, final_vis as V, site as S, ty_core as C, ty_run as R
from .ty_core import POOL

OUT = S.ROOT / "knowledge" / "landscape" / "concept" / "final"
PREC = R.PREC


def critique_seasonal(L):
    """LDC critics read one shade_fraction per canopy. The grape pergola is run twice: leafed vine on closed louvres (summer values, all findings) and bare vine with the
    louvres open (winter value 0.15); the winter run replaces C-WINTER-SUN only, so the deciduous vine is not judged as a year-round roof."""
    from ..critic import critique, verdict
    fs = critique(L)
    W = copy.deepcopy(L)
    for c in W["canopies"]:
        if c.get("deciduous"):
            c["shade_fraction"] = c["shade_fraction_winter_open"]
    fw = [f for f in critique(W) if f.criterion == "C-WINTER-SUN"]
    fs = [f for f in fs if f.criterion != "C-WINTER-SUN"] + fw
    by = {}
    for f in fs:
        d = by.setdefault(f.critic, {"pass": 0, "fail": 0, "warn": 0, "not_evaluated": 0})
        d[f.status] += 1
    return fs, by, verdict(fs)


def schedule(L, seen, scene):
    from ..build import planting as PL
    rows = R.schedule(L, seen)
    sch = {(r["id"] if False else r.get("species")): r for r in scene.schedule}
    st = {}
    for r in scene.schedule:
        sp = r.get("species")
        d = st.setdefault(sp, {"asset": 0, "standin": 0, "omitted": 0, "asset_ids": set()})
        d[r["status"]] = d.get(r["status"], 0) + 1
        if r.get("asset"):
            d["asset_ids"].add(f"{r['asset']} (grade {r.get('grade')})")
    for r in rows:
        res = PL.resolve(r["slug"])
        if r["bed"] == "pot":
            r["status"] = "STAND-IN (frangipani asset exists as a genus fit; pot size is a LDL GAP)" if res["drawable"] else "STAND-IN: " + res["why"]
        elif res["drawable"]:
            r["status"] = "DRAWABLE: " + res["why"] + " asset " + "; ".join(sorted({a.get("id", a.get("name", "?")) for a in res["assets"]}))
        else:
            r["status"] = "STAND-IN (generic mass, labelled): " + res["why"]
        r["drawable"] = bool(res["drawable"])
    return rows


def programme(L, res, metrics, ext):
    def g(crit, subj=None):
        return [r for r in res if r.criterion == crit and (subj is None or r.subject == subj)]
    rows = []

    def add(label, achieved, required, status, source):
        rows.append({"item": label, "achieved": achieved, "required": required, "status": status, "source": source})
    cap = g("LS-CAPACITY")
    n_seats = sum(t["seats"] for t in L["tables"]) + sum(s["seats"] for s in L["seating"])
    add("seats, whole design (table + built-in benches)", n_seats, ">= 10 (brief 10-20 people)", cap[0].status if cap else "n/a", "client brief; LS-CAPACITY")
    add("people at an event: seated + standing in the free floor of the south garden", f"{metrics['seats']['dining']} + {metrics['seats']['built_in_and_lounge']} seated south, {metrics['standing_at_1.3m2']} standing at 1.3 m2", "10-20", "pass", "client brief; LS-STAND-AREA (Neufert p.211)")
    add("dining table, 8 seats", "8", "8 (brief: dining 8 extending to 10)", "pass", "client decision 2026-11-22")
    add("dining table extended to 10 (3.0 m), clear to nearest obstruction", f"{ext[10]['clear_mm']} mm", f"{ext[10]['required_mm']} mm", ext[10]["status"], "LS-DINE-CLEAR (Time-Saver Fig. 210-3)")
    add("dining table extended to 12 (3.6 m), clear", f"{ext[12]['clear_mm']} mm", f"{ext[12]['required_mm']} mm", ext[12]["status"] + " (not offered)", "LS-DINE-CLEAR")
    for crit, label in (("LS-DINE-AREA", "dining zone area per seat"), ("LS-DINE-CLEAR", "table to obstruction"), ("LS-LOUNGE-AREA", "lounge area per seat"), ("LS-LOUNGE-CLUSTER", "lounge across"),
                        ("LS-STAND-AREA", "standing area per person"), ("LS-FIRE-CLEAR", "fire pit clear ground"), ("LS-FIRE-SEAT", "fire pit to nearest seat or table"), ("LS-FIRE-COVER", "flush cover load rating (declared, to be certified)"),
                        ("LS-FIRE-OVERHEAD", "clear above the fire"), ("LS-HERB-SUN", "herb bed midsummer sun"), ("LS-TREE-BUILDING", "tree trunk to building"), ("LS-ROOTZONE", "paving in the tree dripline"),
                        ("LS-SCREEN", "neighbour screening height"), ("LS-PATH-MAIN", "main path width"), ("LS-PATH-SERVICE", "service path width"), ("LS-SEATWALL", "seat wall"),
                        ("LS-POND-DEPTH", "pond deepest section"), ("LS-POND-STOCK", "koi stocking"), ("LS-POND-GUARD", "pond child guard"), ("LS-POND-FLUSH-MARGIN", "pond flush margin"), ("LS-POND-EDGE-SLOPE", "pond edge slope"),
                        ("LS-POND-FREEBOARD", "pond freeboard"), ("LS-HYDROZONE", "one water class per bed")):
        for r in g(crit):
            add(f"{label} [{r.subject}]", f"{r.achieved} {r.unit}", f"{r.required} {r.unit}", r.status, crit)
    for r in res:
        if r.criterion.startswith("LDG-") and r.criterion not in ("LDG-GEOM", "LDG-TOXIC"):
            add(f"{r.criterion} [{r.subject}]", f"{r.achieved} {r.unit}", f"{r.required} {r.unit}", r.status, "POLICY / decision (ours)")
    return rows


def main(draw=True):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "plans").mkdir(exist_ok=True)
    L = F.build()
    V.assert_excluded(L)
    Vis = V.mirror(L)
    assert V.tagged_everywhere(Vis)
    rooms = R.seat_rooms(L)
    covers = [c["rect"] for c in L["canopies"]]
    res, seen, gdata = K.evaluate_all(L, rooms, covers)
    hard = K.hard_fails(res)
    sup = K.superseded(res)
    metrics = R.metrics(L)
    ext = R.extension_checks(L)
    tw, per, mir = K.wind_check(L)
    fs, by, ver = critique_seasonal(L)
    from ..build import build as BB, checks as BC
    scene = BB.build_scene(L, age=3)
    bchk = {st: BC.summary(BC.run_all(scene, st)) for st in ("closed", "open")}
    sched = schedule(L, seen, scene)
    prog = programme(L, res, metrics, ext)
    rec = {"design": "B adapted (client decided 2026-11-22)", "hard_fails": [r.criterion + ":" + r.subject for r in hard], "tally": C.tally(res),
           "superseded_by_manual": [{"criterion": r.criterion, "subject": r.subject, "ldk_message": r.message, "replaced_by": "LDG-FIRE-MANUAL (side and overhead), manual clearances in final_fire.PRODUCTS"} for r in sup],
           "metrics": metrics, "precedent": {"hard_share": {"achieved": metrics["hard_share"], "range": PREC["hard"], "inside": PREC["hard"][0] <= metrics["hard_share"] <= PREC["hard"][1]},
                                            "trees_per_100m2_south": {"achieved": metrics["trees_per_100m2_south"], "range": PREC["trees"], "inside": PREC["trees"][0] <= metrics["trees_per_100m2_south"] <= PREC["trees"][1]}},
           "table_extension": ext, "grape": gdata, "grape_sources": K.GRAPE_SRC,
           "wind": {"toward_west": {k: {"share_of_hours_pct": v[0], "mean_westward_component_ms": v[1], "hours": v[2]} for k, v in tw.items()}, "seat_in_downwind_sector_pct": per, "sister_seat_in_downwind_sector_pct": mir,
                    "note": "downwind sector = fire->seat bearing within +-45 deg of the direction the wind blows toward; station-level (Cairo West AP TMYx), no lee modelling (LDS gap W1)"},
           "fire": {"design_side_clearance_mm": round(F.FIRE_SIDE_M * 1000), "design_overhead_clearance_mm": round(F.FIRE_OVER_M * 1000), "opening_a": F.OPEN_A, "products": FF.PRODUCTS, "rejected": FF.REJECTED, "quotes_verified": FF.quotes_ok()},
           "privacy": gdata.get("privacy_table"), "pond_sun": K.pond_sun(L), "critic_counts": by, "critic_verdict": ver, "critic_findings": [f.to_dict() for f in fs if f.status in ("fail", "warn")],
           "build_checks": bchk, "build_warnings": scene.warnings, "checks": R.compact(res), "schedule": sched, "programme": prog,
           "layout_counts": {k: len(L[k]) for k in C.KEYS}, "visualisation": {"file": "layout-visualisation.json", "excluded_from": "checks, schedules, quantities, critics, programme table"}}
    json.dump(L, open(OUT / "layout-final.json", "w"), indent=1)
    json.dump(Vis, open(OUT / "layout-visualisation.json", "w"), indent=1)
    json.dump(rec, open(OUT / "final.json", "w"), indent=1, default=str)
    print("hard fails", rec["hard_fails"], "tally", rec["tally"], "critics", by)
    if draw:
        draw_all(L, Vis)
    return rec


def stamp(path, text, tint=None):
    """Add a red label band above and below the image (extra canvas, nothing covered). tint = (x0, x1, y0, y1) pixel box to wash with translucent red (the visualisation-only half)."""
    from PIL import Image, ImageDraw, ImageFont
    im = Image.open(path).convert("RGB")
    if tint:
        ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(ov).rectangle([tint[0], tint[2], tint[1], tint[3]], fill=(200, 30, 30, 55))
        im = Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", max(18, im.width // 55))
    except OSError:
        f = ImageFont.load_default()
    h = f.size + 14
    out = Image.new("RGB", (im.width, im.height + 2 * h), (150, 20, 20))
    out.paste(im, (0, h))
    d = ImageDraw.Draw(out)
    w = d.textlength(text, font=f)
    for y in (6, im.height + h + 6):
        d.text(((im.width - w) / 2, y), text, fill="white", font=f)
    out.save(path)


def vis_tint(view, px0=320, pw=960, py0=69):
    """Pixel box of the sister half (y < west line) in a plan_png of `view` = [x0, y0, x1, y1]: the plot frame is 960 px wide from x 320, top at y 69."""
    s = pw / (view[3] - view[1])
    return (px0, px0 + (V.LINE_Y - view[1]) * s, py0, py0 + (view[2] - view[0]) * s)


def draw_all(L, Vis, force=False):
    from ..critic import plan_png, massing_png
    P = OUT / "plans"
    todo = lambda n: force or not (P / n).exists()          # noqa: E731
    if todo("final-south.png"):
        plan_png(L, str(P / "final-south.png"), title="Final design (concept B adapted): south garden and east yard; shared fire pit on the west line", view=[14.6, -31.6, 29.3, -19.8])
    if todo("final-north.png"):
        plan_png(L, str(P / "final-north.png"), title="Final design: north court (quiet room, pond)", view=[-0.9, -29.6, 4.6, -22.8])
    M = V.merge_for_view(L, Vis)
    vv = [14.6, -40.2, 29.3, -19.8]
    plan_png(M, str(P / "final-visualisation-plan.png"), title="VISUALISATION ONLY: south garden mirrored onto the sister plot (not our land, not our design); not checked, scheduled or counted", view=vv)
    stamp(str(P / "final-visualisation-plan.png"), V.LABEL.upper(), tint=vis_tint(vv))
    for name, lay, view, kw in (("final-massing-south.png", L, [14.0, -32.0, 30.0, -19.5], {}), ("final-massing-north.png", L, [-1.5, -30.5, 6.5, -22.5], dict(azimuth=205, elevation=50)),
                                ("final-massing-east.png", L, [13.0, -26.0, 24.0, -19.5], dict(azimuth=300, elevation=45)), ("final-visualisation-massing.png", M, [14.0, -41.0, 30.0, -19.5], {})):
        if todo(name):
            massing_png(lay, str(P / name), view=view, **kw)
            if "visualisation" in name:
                stamp(str(P / name), V.LABEL.upper())


if __name__ == "__main__":
    main(draw="--no-draw" not in sys.argv)
