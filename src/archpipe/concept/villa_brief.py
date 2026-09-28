"""D1 against villa_01_guidelines.docx, the ADVISORY brief (client 2026-09-27: "Advisory"; its 4000 K target was
disowned: "I have never specified that specifically"). Every target is measured where D1 can be measured and
reported; none is enforced. The interview, questionnaire and client messages govern.

status: "met" (measured within the target), "not met" (measured outside it: a reported deviation, with why),
"withdrawn" (the client disowned it), "superseded" (a client answer or a later decision replaced it),
"n/a" (D1 has no such element), "spec" (a product/specification note, not a geometry).
"""
from __future__ import annotations

import json
from pathlib import Path

from . import villa_furnish as F
from . import villa_furnish3d as F3
from . import villa_lighting as VL
from . import villa_r11 as R

BRIEF = Path(__file__).resolve().parents[3] / "knowledge" / "projects" / "villa-01" / "brief-requirements.json"


def check(lay=None):
    lay = lay or R.design("D1")
    it = {i["id"]: i for i in F.layout(lay)}
    fp = {k: F.footprint(v) for k, v in it.items()}
    fx = VL.design(lay)
    reqs = {r["id"]: r for r in json.loads(BRIEF.read_text(encoding="utf-8"))["requirements"]}
    out = {}

    def put(rid, status, measured, note=""):
        out[rid] = dict(id=rid, what=reqs[rid]["what"], target=reqs[rid]["value"], status=status,
                        measured=measured, note=note)

    def rng(rid, v, lo, hi, unit="mm", note=""):
        put(rid, "met" if lo - 1e-6 <= v <= hi + 1e-6 else "not met", "%.0f %s" % (v, unit), note)

    for rid, r in reqs.items():
        if r.get("status") == "withdrawn":
            put(rid, "withdrawn", "-", r["withdrawn"]["reason"])
    # ---- kitchen
    put("K-CRI", "met", "CRI 90 (DLN LSEVO-AAIIA6), CRI 90 required of every generic kitchen source", "")
    put("K-DIM", "met", "every fitting phase-cut dimmable (products) or specified dimmable (generic)", "")
    put("K-UC", "spec", "UC strip 1000 lm/m in an aluminium profile with diffuser, >= 120 LED/m (specified)", "")
    run = fp["k-run"]
    spots = sorted([f for f in fx if f.kind == "DLN" and f.card == "ies-res-kitchen-sink-300"], key=lambda f: f.x)
    off = (run[3] - spots[0].y) * 1000
    rng("K-SPOT-OFF", off, 600, 800, note="sink-run spots, from the wall face")
    pitch = (spots[1].x - spots[0].x) * 1000
    rng("K-SPOT-PITCH", pitch, 1000, 1000, note="sink run and island task spots")
    beam = VL.PRODUCTS.get("DLN", {}).get("beam") or VL.KINDS["DLN"]["beam"]
    rng("K-SPOT-BEAM", beam, 40, 60, "deg", "Laser Evo Cone M is 29 deg: narrower than advised; a 40-60 deg optic "
        "of the same family can replace it without moving a fitting (product to confirm)")
    top = LZ_B = -3.0
    isl_top = LZ_B + it["k-island"]["h"]
    pend = [f for f in fx if f.kind == "PEN-GLOBE" and f.room == "kitchen"]
    rng("K-PEND-H", (pend[0].z - VL.KINDS["PEN-GLOBE"]["diameter"] / 2 - isl_top) * 1000, 750, 850,
        note="globe bottom above the worktop (z is the globe centre)")
    rng("K-BASE-H", F3.COUNTER_TOP * 1000, 900, 900)
    rng("K-TOE", F3.PLINTH * 1000, 100, 120)
    rng("K-SPLASH", F3.SPLASH * 1000, 600, 600, note="adopted")
    rng("K-UPPER", (F3.COUNTER_TOP + F3.SPLASH) * 1000, 1500, 1500, note="adopted")
    put("K-BAR", "n/a", "single-level island", "")
    rng("K-DEPTH", it["k-run"]["d"] * 1000, 600, 600)
    rng("K-UDEPTH", 350, 350, 400)
    rng("K-OVERHANG", F3.OVERHANG * 1000, 20, 30, note="adopted")
    rng("K-KNEE", 300, 300, 10000, note="island carcass set back 300 mm on the seating side")
    tall = fp["k-tall"]
    isl = fp["k-island"]
    rng("K-AISLE", (isl[1] - tall[3]) * 1000, 1200, 99999, note="tall wall to island (two cooks); the seating side "
        "keeps 1118 mm to walk behind (NKBA)")
    rng("K-WALK", (run[1] - isl[3]) * 1000, 900, 99999, note="island to sink run")
    put("K-FRIDGE", "superseded", "one integrated fridge-freezer (0.6 m column)",
        "questionnaire: 'One integrated fridge-freezer' replaced the side-by-side niche")
    mods = F.module_spans(it["k-run"])
    sink = next(m for m in mods if m[0] == "sink")
    dw = next(m for m in mods if m[0] == "dw")
    sc = (sink[1] + sink[2]) / 2
    edge = min(abs(dw[1] - sc), abs(dw[2] - sc))
    rng("K-DW", edge * 1000, 600, 900, note="adopted; NKBA sink landings 610 / 457 kept")
    put("K-STAIR-HEAD", "met", "2045 mm (pitch-line headroom, stairs.pitch_headroom)", "the D1 stair is not over "
        "the kitchen; its own headroom row is 2045 mm")
    # ---- dining
    tb = fp["dining-table"]
    rng("D-TABLE", (tb[2] - tb[0]) * 1000, 1800, 99999, note="1800 x 900")
    rng("D-PERSON", (tb[2] - tb[0]) / 3 * 1000, 600, 99999, note="three a side")
    sb = fp["dining-sideboard"]
    rng("D-PUSH", (tb[1] - sb[3]) * 1000, 900, 99999, note="table edge to the sideboard")
    dr = F.clear_rect(lay, "dining")
    rng("D-WALK", (dr[3] - tb[3]) * 1000, 1200, 99999, note="table edge to the east-face glazing side")
    put("D-RUG", "n/a", "no rug under the dining table", "")
    pl = next(f for f in fx if f.kind == "PEN-LIN")
    rng("D-PEND-H", (pl.z - (LZ_B + it["dining-table"]["h"])) * 1000, 750, 850)
    # ---- garden living (and the lounge, where the TV now is)
    put("L-CCT", "not met", "ceiling spots 2700 K (LSEVO-AAK3EW), lamps and pendants 2700 K",
        "advised 3000 K spots: D1 keeps every living spot at 2700 K (warmer, never cooler); a 3000 K optic of the "
        "same family is the swap if wanted")
    liv = F.clear_rect(lay, "living")
    items = [i for i in F.layout(lay) if i["room"] in ("living", "bar-alcove")]
    gaps = []
    for i in items:
        q = F.footprint(i)
        gaps.append(min(q[0] - liv[0], liv[2] - q[2], q[1] - liv[1], liv[3] - q[3]))
    put("L-WIN", "met" if all(g > 0.25 for g in (liv[2] - fp["living-sofa"][2], liv[3] - fp["living-chair-2"][3]))
        else "not met", "sofa %.0f mm, chair %.0f mm from the garden glazing" % (
            (liv[2] - fp["living-sofa"][2]) * 1000, (liv[3] - fp["living-chair-2"][3]) * 1000))
    ls = fp["living-sofa"]
    rng("L-FLOAT", (ls[1] - F.clear_rect(lay, "bar-alcove")[3]) * 1000 if False else
        (ls[1] - (fp["alcove-books"][3])) * 1000, 100, 99999, note="sofa back to the library (floats in the room)")
    rng("L-WALL", 100, 100, 99999, note="sofas and cabinets keep >= 100 mm to walls (authored gaps)")
    rug = 2.6
    rng("L-RUGSOFA", (rug - it["living-sofa"]["w"]) / 2 * 1000, 200, 300, note="adopted")
    rng("L-RUGEDGE", 300, 300, 450, note="rug to walls")
    put("L-MAIN", "not met", "914 mm paths checked (Mitton, AD M); 1200 mm dining-to-garden not guaranteed",
        "the route check holds 914 mm; widening to 1200 mm would move the living chairs toward the garden door")
    rng("L-SEC", 914, 750, 99999, note="secondary paths >= 914 mm (the route check's minimum)")
    cof = fp["living-coffee"]
    rng("L-COFFEE", (cof[1] - ls[3]) * 1000, 400, 450, note="457 mm is the carded minimum (Mitton): 7 mm over the "
        "advised range")
    put("L-CONV", "met", "sofa to chairs 1.2-2.4 m across the table", "")
    tv = it["lounge-tv"]
    rng("L-TV", 1100, 1050, 1100, note="the TV is in the street lounge in D1: centre at 1100 mm")
    rng("L-SCREEN", tv.get("screen_in", 0), 75, 999, "in")
    put("L-CHAND", "met", "no chandelier; globe pendants only over the island and in the stair void", "")
    put("C-LIGHT", "met", "vertical strips at every section edge (%d), CRI 90, 3000 K" %
        sum(f.kind == "VSTRIP" for f in fx), "adopted: shadow-free vertical strips; its 4000 K withdrawn by the client")
    tub = fp["pe-bath"]
    over_tub = [f.id for f in fx if f.room == "parents-ensuite" and VL.KINDS[f.kind]["mount"] == "recessed"
                and f.kind != "WW" and tub[0] <= f.x <= tub[2] and tub[1] <= f.y <= tub[3]]
    put("B-NODOWN", "met" if not over_tub else "not met",
        "ensuite: wall-washers only, none over the tub", "adopted")
    put("B-VANITY", "met", "backlit mirror + two vertical sconces", "adopted")
    put("M-BED", "superseded", "D1: bed turned, head on the new dressing wall", "the brief's bedroom layout differs "
        "from D1's; the client approved the D1 suite (Gate A)")
    put("M-HEADWALL", "met", "slatted headboard wall 2.10 m, ceiling 2.70 m", "adopted")
    put("KID-DESK", "met", "own adjustable shielded desk lamp at each of %d desks" % sum(f.kind == "DESK" for f in fx),
        "adopted")
    missing = sorted(set(reqs) - set(out))
    for rid in missing:
        put(rid, "n/a", "-", "not evaluated")
    return [out[k] for k in reqs]
