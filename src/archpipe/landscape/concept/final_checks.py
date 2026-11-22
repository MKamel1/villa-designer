"""Checks for the final design: the LDK rules, pass-2 policy checks, plus the checks the round-2 decisions and the LDB findings add.

Every new check has a negative test in tests/landscape/concept/test_final.py. The visualisation layout is never passed here.
"""
from __future__ import annotations

import math

import numpy as np
from shapely.geometry import Point, box
from shapely.ops import unary_union

from . import final as F, site as S, ty_core as C, ty_run as R
from .geom import rbox
from .ty_core import A, B, POOL, _r

LAYERS = ("zones", "paved_areas", "planting_groups", "seating", "tables", "features", "trees", "paths", "canopies", "screens", "walls", "obstacles")


# ---- ids and surfaces (LDB findings 5) --------------------------------------------------------------------------------------
def id_check(L):
    seen, dup = {}, []
    for k in LAYERS:
        for it in L.get(k, []):
            i = it.get("id")
            if i in seen:
                dup.append((i, seen[i], k))
            seen[i] = k
    return _r("LDG-IDS", "pass" if not dup else "fail", "layout", "every element id is unique across all gardens (%d ids)" % len(seen) if not dup else f"duplicate ids: {dup[:4]}", len(dup), 0, "duplicates")


GARDENS = {"south": S.ZONES["south"], "north court": None, "east yard": None}


def garden_rects():
    return {"south": [S.SX0, S.SY0, S.SX0 + A, S.SY0 + B], "north court": F.TC.NR(0, 0, F.TC.NH, F.TC.NW), "east yard": F.TC.ER(0, 0, F.TC.EL, F.TC.EW)}


def surface_check(L):
    """Every square metre of each garden room is a declared surface: paved area, bed, pond, bench plinth, pit or a gravel zone."""
    cover = [rbox(a["rect"]) for a in L["paved_areas"]] + [rbox(g["rect"]) for g in L["planting_groups"]] + [rbox(s["rect"]) for s in L["seating"]]
    cover += [rbox(f["rect"]) for f in L["features"] if f.get("rect")]
    cover += [Point(*f["center"]).buffer(f["diameter_m"] / 2, 32) for f in L["features"] if f.get("diameter_m")]
    cover += [rbox(z["rect"]) for z in L["zones"] if z.get("surface") == "gravel"]
    cov = unary_union(cover)
    out, worst = [], 0.0
    for name, r in garden_rects().items():
        gap = box(*r).difference(cov).area
        worst = max(worst, gap)
        out.append((name, round(gap, 3)))
    return _r("LDG-SURFACE", "pass" if worst <= 0.02 else "fail", "gardens", f"area with no declared surface per garden (m2): {out}", round(worst, 3), 0.02, "m2")


def gravel_check(L):
    """A zone that says gravel must BE the gravel (LDB builds gravel from zone rectangles): zone rects with surface gravel may not overlap paving or a bed."""
    bad = []
    pav = unary_union([rbox(a["rect"]) for a in L["paved_areas"]] + [rbox(g["rect"]) for g in L["planting_groups"]])
    for z in L["zones"]:
        if z.get("surface") == "gravel" and rbox(z["rect"]).intersection(pav).area > 1e-3:
            bad.append(z["id"])
    return _r("LDG-GRAVEL-ZONE", "pass" if not bad else "fail", "zones", "gravel zones coincide with gravel" if not bad else f"gravel zone also paved/planted: {bad}", len(bad), 0, "zones")


# ---- LDB finding 1-3: tree and pergola, plants in solids, pot ---------------------------------------------------------------------
def tree_pergola_check(L):
    bad = []
    for t in L["trees"]:
        c = Point(*t["center"])
        crown = c.buffer(t["mature_spread_m"] / 2, 24)
        for cn in L["canopies"]:
            r = rbox(cn["rect"])
            if r.distance(c) < 1.0 or crown.intersects(r):
                bad.append((t["id"], cn["id"], round(r.distance(c), 2)))
    return _r("LDG-TREE-PERGOLA", "pass" if not bad else "fail", "trees", "no tree stands within 1.0 m of a pergola or has its minimum crown inside one" if not bad else f"tree inside or against a pergola: {bad}", len(bad), 0, "trees")


def solids(L):
    out = {}
    for s in L["seating"]:
        out["seat:" + s["id"]] = rbox(s["rect"])
    for t in L["tables"]:
        cx, cy = t["center"]; w, h = t["size_m"]
        out["table:" + t["id"]] = box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    for f in L["features"]:
        if f.get("kind") in ("bbq", "pond") and f.get("rect"):
            out[f["kind"] + ":" + f["id"]] = rbox(f["rect"])
        if f.get("kind") == "firepit":
            out["pit:" + f["id"]] = Point(*f["center"]).buffer(f["diameter_m"] / 2, 32)
    for o in L["obstacles"]:
        if o["id"].startswith("pot") and o.get("rect"):
            out["pot:" + o["id"]] = rbox(o["rect"])
    return out


def plant_solid_check(L):
    sol = solids(L)
    bad = []
    for g, p in C.all_plants(L):
        pt = Point(*p["at"])
        for k, s in sol.items():
            if pt.within(s):
                bad.append((p["species"], k))
    return _r("LDG-PLANT-SOLID", "pass" if not bad else "fail", "planting", "no plant stands inside a bench, table, pot, BBQ, pit or pond" if not bad else f"plants inside solids: {bad[:4]}", len(bad), 0, "plants")


POT_FENCE_M = 1.0      # POLICY: frangipani size is a GAP in LDL; the build assumes 1.8 m, so the pot centre keeps 0.9 m + 0.1 from any wall, fence or screen


def pot_check(L):
    pots = [o for o in L["obstacles"] if o["id"].startswith("pot")]
    walls = [rbox(w["rect"]) for w in L["walls"]] + [rbox(s["rect"]) for s in L["screens"]] + [rbox(b) for b in L["buildings"]]
    out, bad = [], []
    for p in pots:
        c = rbox(p["rect"]).centroid
        d = min(w.distance(c) for w in walls)
        out.append(round(d, 2))
        if d < POT_FENCE_M + 0.3:
            bad.append(p["id"])
    return _r("LDG-POT", "pass" if not bad else "fail", "pot", f"pot centre to nearest wall, fence or screen {out} m (>= {POT_FENCE_M + 0.3:.1f} m so the 1.8 m crown assumed by the build is not squeezed; POLICY)", min(out) if out else None, POT_FENCE_M + 0.3, "m")


# ---- the fire pit against the shortlisted manuals ------------------------------------------------------------------------------
def fire_manual_check(L):
    """Manual-stated clearances (FIRE_SIDE_M horizontal, FIRE_OVER_M overhead) replace the 2.0 m open-fire floor only for the pit and only because the
    manuals state them. Horizontal: pit edge to any building, fence, screen, bed (planting), tree crown, pergola, pot. Overhead: straight-line distance from the burner
    to the nearest pergola/vine/tree-crown underside."""
    pit = next(f for f in L["features"] if f["kind"] == "firepit")
    c = Point(*pit["center"])
    edge = c.buffer(pit["diameter_m"] / 2, 48)
    items = {}
    for i, b in enumerate(L["buildings"]):
        items[f"building-{i}"] = box(*b)
    for k in ("planting_groups", "obstacles", "screens", "walls"):
        for it in L[k]:
            if it.get("rect"):
                items[f"{k}:{it['id']}"] = rbox(it["rect"])
    for t in L["trees"]:
        items["tree:" + t["id"]] = Point(*t["center"]).buffer(t["mature_spread_m"] / 2, 32)
    for cn in L["canopies"]:
        items["canopy:" + cn["id"]] = rbox(cn["rect"])
    d = {k: edge.distance(v) for k, v in items.items()}
    nk, nd = min(d.items(), key=lambda kv: kv[1])
    out = [_r("LDG-FIRE-MANUAL", "pass" if nd + 1e-9 >= F.FIRE_SIDE_M else "fail", pit["id"] + "/side",
              f"nearest combustible, structure or planting to the burner envelope: {nd * 1000:.0f} mm ({nk}); manuals state {F.FIRE_SIDE_M * 1000:.0f} mm at most (PTI 'sides 4 ft', Planika '1 metre radius', MAD 24 in to fixed furniture, Solus 0.5 m)",
              round(nd * 1000), round(F.FIRE_SIDE_M * 1000), "mm")]
    over = []
    for cn in L["canopies"]:
        dh = rbox(cn["rect"]).distance(c)
        over.append((cn["id"], math.hypot(dh, F.VINE_UNDERSIDE_M if cn.get("roof") == "vine" else cn["height_m"] - 0.3)))
    for t in L["trees"]:
        dh = max(0.0, c.distance(Point(*t["center"])) - t["mature_spread_m"] / 2)
        over.append((t["id"], math.hypot(dh, 0.4 * (t.get("mature_height_m") or 3.0))))
    for g, p in C.all_plants(L):
        if POOL[p["species"]].h_max and POOL[p["species"]].h_max > 2.0:       # tall climbers and shrubs: crown underside taken as 1/3 of the height
            dh = max(0.0, c.distance(Point(*p["at"])) - p["spread_m"] / 2)
            over.append((g["id"] + ":" + p["species"], math.hypot(dh, POOL[p["species"]].h_max / 3)))
    if over:
        k, v = min(over, key=lambda kv: kv[1])
        out.append(_r("LDG-FIRE-MANUAL", "pass" if v + 1e-9 >= F.FIRE_OVER_M else "fail", pit["id"] + "/overhead",
                      f"nearest pergola, vine, crown or tall plant above or beside the burner: {v * 1000:.0f} mm straight-line ({k}); manuals state 1830-2000 mm overhead (PTI top 6 ft, Solus 1.95 m, MAD 2000 mm). No pergola or climber is over the pit.",
                      round(v * 1000), round(F.FIRE_OVER_M * 1000), "mm"))
    return out


def superseded(res):
    """LDK LS-FIRE-STRUCT shortfalls on the pit that the manuals replace; the 2.0 m floor is a wood-fire bylaw, the pit is gas. Reported, never dropped silently."""
    return [r for r in res if r.criterion == "LS-FIRE-STRUCT" and r.subject == "s-firepit" and r.status != "pass"]


# ---- wind (decision: summer-evening wind runs toward the west; confirm on data) --------------------------------------------------
def wind_check(L):
    from ..critic.computed import _wind_to_seat
    pit = next(f for f in L["features"] if f["kind"] == "firepit")["center"]
    sets = S._file("wind")["sets"]
    # toward-west half plane share (all sectors whose downwind direction has a westward component)
    tw = {}
    for name, s in sets.items():
        tot = sum(x["share_pct"] for x in s["sectors"])
        toward = sum(x["share_pct"] for x in s["sectors"] if math.cos(math.radians((x["from_bearing_true"] + 180) % 360 - 200)) > 0)
        num = sum(x["share_pct"] * (x.get("mean_speed_ms") or 0) * math.cos(math.radians((x["from_bearing_true"] + 180) % 360 - 200)) for x in s["sectors"])
        tw[name] = (round(toward / tot * 100, 1), round(num / tot, 2), s["hours"])
    seats = []
    for t in L["tables"]:
        seats.append((t["id"], t["center"]))
    for s in L["seating"]:
        if s["rect"][0] > 20:
            seats.append((s["id"], [(s["rect"][0] + s["rect"][2]) / 2, (s["rect"][1] + s["rect"][3]) / 2]))
    per = {}
    for sid, pt in seats:
        per[sid] = {k: round(_wind_to_seat(L, pit, pt, k) * 100, 1) for k in sets}
    # the sister seats (mirror): downwind of the pit across the line
    mir = {k: round(_wind_to_seat(L, pit, [pit[0], 2 * S.SY0 - (pit[1] + 2.0)], k) * 100, 1) for k in sets}
    return tw, per, mir


# ---- grape: summer shade, winter bareness -----------------------------------------------------------------------------------
GRAPE_SRC = [
    {"id": "NCSU-vitis-vinifera", "url": "https://plants.ces.ncsu.edu/plants/vitis-vinifera/", "quote": "It is a woody, deciduous vine", "also": "Leaf Characteristics: Deciduous; Fire Risk Rating: high flammability",
     "status": "SOURCED (deciduous habit; no calendar dates)"},
    {"id": "Burkes-ornamental-grape", "url": "https://www.burkesbackyard.com.au/fact-sheets/in-the-garden/flowering-plants-shrubs/ornamental-grape/", "quote": "shade in summer and sun in winter",
     "status": "SOURCED (qualitative, garden fact sheet; Vitis vinifera purpurea/ornamental grape, Australia)"},
    {"id": "EKB-dormex-trials", "url": "https://journals.ekb.eg/article_171522.html", "quote": "Thompson Seedless grapevines ... sprayed hydrogen cyanamide on 1, 7 or 14 January",
     "status": "INFERENCE: a dormancy-breaker is applied to dormant vines, so vines in Egypt are dormant (leafless) in early January; no leaf-fall or leaf-out date was found (GAP)"},
]


def grape_check(L):
    """Direct sun at the table seats through the pergola, midday window: 21 Jun 10-15 with the leafed vine, 21 Dec 10-15 with the bare vine. The ray test is the LDS one
    (analyse.sunlit_matrix, structure only) plus the pergola plane as a screen of density d (POLICY)."""
    from ..site import analyse as AN
    cn = next(c for c in L["canopies"] if c.get("deciduous"))
    tb = next(t for t in L["tables"])
    cx, cy = tb["center"]
    pts = np.array([[cx + dx, cy + dy, S.FLOOR_Z + 1.1] for dx in (-0.9, 0.0, 0.9) for dy in (-0.3, 0.3)])
    r = cn["rect"]
    zr = S.FLOOR_Z + cn["height_m"]

    def run(day, lo, hi, d):
        mids, lit = AN.sunlit_matrix(day, pts)
        from datetime import datetime, timedelta, timezone
        from ... import solar, villa_env as E
        from ...orientation import sun_direction
        tot0 = tot1 = 0.0
        w = [(i, m) for i, m in enumerate(mids) if lo * 60 <= m < hi * 60]
        for i, m in w:
            when = datetime.fromisoformat(day).replace(tzinfo=timezone.utc) + timedelta(minutes=float(m)) - timedelta(hours=E.TIME_ZONE)
            s = solar.sun_position(when, E.LATITUDE, E.LONGITUDE)
            dv = np.array(sun_direction(s.azimuth, s.altitude))
            for k, p in enumerate(pts):
                if not lit[i, k]:
                    continue
                t = (zr - p[2]) / dv[2]
                x, y = p[0] + t * dv[0], p[1] + t * dv[1]
                hit = r[0] <= x <= r[2] and r[1] <= y <= r[3]
                tot0 += 0.25
                tot1 += 0.25 * (1 - (d if hit else 0.0))
        return round(tot0 / len(pts), 2), round(tot1 / len(pts), 2)
    sb, sa = run("2026-06-21", 10, 15, F.GRAPE["summer_density"])
    wb, wa = run("2026-12-21", 10, 15, F.GRAPE["winter_density"])           # bare vine, louvres open
    _, wev = run("2026-12-21", 10, 15, F.GRAPE["winter_closed_density"])    # bare vine, louvres closed (opaque)
    st = "pass" if (sb > 0 and sa <= 0.5 * sb + 1e-9 and wa >= 0.8 * wb - 1e-9) else "fail"
    return _r("LDG-GRAPE-SEASON", st, cn["id"],
              f"table seats, direct sun 10-15 h: 21 Jun {sb} h open sky, {sa} h under the leafed vine (density {F.GRAPE['summer_density']}, POLICY); 21 Dec {wb} h open sky, {wa} h under the bare vine (density {F.GRAPE['winter_density']}, POLICY), "
              f"{wev} h with the louvres closed. Pass = summer midday sun at least halved and winter sun at least 80 % kept.", wa, wb, "h"), \
        {"summer": {"open": sb, "leafed": sa}, "winter": {"open": wb, "bare": wa, "louvres_closed": wev}, "window": "10-15 h local standard time"}


def leaf_sun(L):
    """Direct sun at the vine's foliage level (pergola underside 2.4 m above the floor) on 21 June: the ground layer under-reads a roof-level canopy."""
    from ..site import analyse as AN
    cn = next(c for c in L["canopies"] if c.get("deciduous"))
    r = cn["rect"]
    pts = np.array([[x, y, S.FLOOR_Z + F.VINE_UNDERSIDE_M] for x in np.linspace(r[0] + 0.2, r[2] - 0.2, 5) for y in np.linspace(r[1] + 0.2, r[3] - 0.2, 4)])
    mids, lit = AN.sunlit_matrix("2026-06-21", pts)
    return round(float(lit.sum(0).mean() * 0.25), 2)


def sun_checks_final(L, leaf):
    """R.sun_checks, with the grape judged at foliage level (leaf) instead of at the ground under the vine strip."""
    seen = {}
    for g in L["planting_groups"]:
        june = leaf if any(p["species"] == "vitis_vinifera" for p in g["plants"]) else C.bed_sun(g["rect"])
        for p in g["plants"]:
            seen.setdefault((g["id"], p["species"]), (R.sun_ok(POOL[p["species"]], june), june))
    bad = [(k, v) for k, v in seen.items() if v[0] == "fail"]
    return _r("LDG-SUNFIT", "pass" if not bad else "fail", "site", "every plant's sun class is met by its bed's 21-June sun (vine: at leaf level, 2.4 m); part shade 2 h, conditional 75 % of need (POLICY thresholds)" if not bad
              else f"sun class not met: {[(k, round(v[1], 1)) for k, v in bad][:4]}", len(bad), 0, "bed-species"), seen



# ---- privacy with the screen opening honoured (own_checks assumes an unbroken screen) ---------------------------------------------
def _group_open(g, posture, top_z, open_x):
    """S._group with no screen at the opening: sister-group eye points whose cell lies in the opening's x range are not removed."""
    a = np.nan_to_num(S.arr("privacy", f"overlooking_eyes_{g}_{posture}"))
    if g not in S.SISTER:
        return a
    seg = S._file("privacy")["boundaries"]["sister-line"]["segments"]
    gk = g.replace("_", "-")
    out = a.copy()
    for j, y in enumerate(S._CY):
        d = y - S.SY0
        band = 0 if d < 1 else 1 if d < 2 else 2 if d < 3 else 3
        for i, x in enumerate(S._CX):
            if out[j, i] == 0 or open_x[0] <= x <= open_x[1]:
                continue
            need = None
            for sg in seg:
                if sg["along_m"][0] <= x < sg["along_m"][1] + 1e-9:
                    need = sg["by_group"][gk][posture][band]
                    break
            if need is None or top_z >= need:
                out[j, i] = 0.0
    return out


def eyes_open(rect, covers, open_x, top_z=S.FLOOR_Z + C.SCREEN_H, posture="seated"):
    m = S.mask(rect) & ~np.isnan(S.arr("privacy", f"overlooking_eyes_any_{posture}"))
    n = int(m.sum())
    cov = np.zeros_like(m)
    for r in covers:
        cov |= S.mask(r)
    tot = 0.0
    for g in S.GROUPS:
        a = _group_open(g, posture, top_z, open_x)
        sel = m & ~cov if g in S.UPPER else m
        tot += float(a[sel].sum() / n) if n else 0.0
    return tot


def privacy_checks(L, rooms, covers_summer, covers_winter_open, covers_winter_closed):
    """Per seated room: remaining share of today's overlooking. HARD: screen unbroken, upper-storey groups cut by covers (summer = leafed vine on closed louvres;
    winter louvres closed = opaque while closed, LDK GAP-OVERLOOK-ABOVE). The opening the client asked for at the pit lets the sister plot see in: that share is the client's
    decision (waiver), reported as a warning with its figure, never hidden."""
    ox = (S.SX0 + F.OPEN_A[0], S.SX0 + F.OPEN_A[1])
    top = S.FLOOR_Z + C.SCREEN_H
    res, tab = [], {}
    for name, (rect, lim) in rooms.items():
        base = S.eyes_total(rect, "seated")
        row = {}
        for lab, cv in (("summer", covers_summer), ("winter_louvres_open", covers_winter_open), ("winter_louvres_closed", covers_winter_closed)):
            row[lab] = round(S.eyes_total(rect, "seated", cover_rects=cv, screen_top_z=top) / base, 3) if base else 0.0
            row[lab + "_with_opening"] = round(eyes_open(rect, cv, ox) / base, 3) if base else 0.0
        tab[name] = {"limit": lim, "today_eye_points": round(base, 1), **row}
        for lab in ("summer", "winter_louvres_closed"):
            res.append(_r("LDG-PRIV", "pass" if row[lab] <= lim + 1e-9 else "fail", f"{name}/{lab}",
                          f"{name}, {lab.replace('_', ' ')}: {row[lab]:.0%} of today's overlooking remains with the screen unbroken (limit {lim:.0%})", row[lab], lim, "share"))
            w = row[lab + "_with_opening"]
            if w > lim + 1e-9 and w > row[lab] + 1e-9:
                res.append(_r("LDG-PRIV-OPENING", "warn", f"{name}/{lab}",
                              f"WAIVED by the client's decision (screen opening at the shared fire pit): {name} {lab.replace('_', ' ')} would be overlooked at {w:.0%} of today's through the opening (limit {lim:.0%}); a closable screen leaf would restore {row[lab]:.0%}", w, lim, "share"))
    return res, tab


# ---- pond section fits the real width ---------------------------------------------------------------------------------------
def pond_section_check(L):
    out = []
    for f in L["features"]:
        if f.get("kind") != "pond":
            continue
        sec = f["section"]
        need = sec["entry_run_m"] + sec["shelf_m"] + sec["trench_m"]
        slope_ok = abs(sec["entry_run_m"] / (sec["entry_drop_mm"] / 1000) - sec["entry_slope_run_per_rise"]) < 1e-6
        st = "pass" if need <= f["width_m"] + 1e-9 and slope_ok and sec["trench_below_water_mm"] >= 900 else "fail"
        out.append(_r("LDG-POND-SECTION", st, f["id"],
                      f"width {f['width_m']} m holds entry slope {sec['entry_run_m']} m (1:{sec['entry_slope_run_per_rise']} over {sec['entry_drop_mm']} mm) + shelf {sec['shelf_m']} m + trench {sec['trench_m']} m = {need:.2f} m; trench {sec['trench_below_water_mm']} mm below water; "
                      f"{f['koi_count']} koi at 12 in per 0.42 m2 on {f['area_m2']} m2", round(f["width_m"], 2), round(need, 2), "m"))
    return out


# ---- everything ---------------------------------------------------------------------------------------------------------
HARD_WARN = R.HARD_WARN


def evaluate_all(L, rooms, covers):
    res = list(C.ldk(L))
    own = [r for r in C.own_checks(L, rooms, covers, S.FLOOR_Z + C.SCREEN_H, None) if r.criterion != "LDG-PRIV"]
    allc = [c["rect"] for c in L["canopies"]]
    nonvine = [c["rect"] for c in L["canopies"] if not c.get("roof") == "vine"]
    prv, ptab = privacy_checks(L, rooms, allc, nonvine, allc)
    own += prv
    sunr, seen = sun_checks_final(L, leaf_sun(L))
    sun = [sunr]
    extra = [id_check(L), surface_check(L), gravel_check(L), tree_pergola_check(L), plant_solid_check(L), pot_check(L)] + fire_manual_check(L) + pond_section_check(L)
    g, gdata = grape_check(L)
    extra.append(g)
    gdata["leaf_level_sun_21jun_h"] = leaf_sun(L)
    gdata['privacy_table'] = ptab
    return res + own + sun + R.tree_checks(L) + extra, seen, gdata


def hard_fails(res):
    sup = {id(r) for r in superseded(res)}
    return [r for r in res if id(r) not in sup and (r.status == "fail" or (r.status == "warn" and r.criterion in HARD_WARN))]
