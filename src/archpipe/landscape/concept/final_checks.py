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


def zone_check(L):
    """The critics take the FIRST zone (most specific use first) that contains a point: every seating item and table must be classified into the zone it declares (lesson LDG-8 repeated in round 2)."""
    bad = []
    for it in L["seating"] + L["tables"]:
        c = it["center"] if "center" in it else [(it["rect"][0] + it["rect"][2]) / 2, (it["rect"][1] + it["rect"][3]) / 2]
        z = next((z for z in L["zones"] if rbox(z["rect"]).contains(Point(*c))), None)
        if z is None or z["id"] != it["zone"]:
            bad.append((it["id"], it["zone"], z and z["id"]))
    return _r("LDG-ZONE-CLASS", "pass" if not bad else "fail", "zones", "every seat and table is classified into its declared zone" if not bad else f"misclassified (item, declared, first containing zone): {bad[:4]}", len(bad), 0, "items")


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
        items["tree:" + t["id"]] = Point(*(t.get("crown_center") or t["center"])).buffer(t["mature_spread_m"] / 2, 32)
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
        over.append((cn["id"], math.hypot(dh, cn["height_m"] - 0.3)))
    for t in L["trees"]:
        dh = max(0.0, c.distance(Point(*(t.get("crown_center") or t["center"]))) - t["mature_spread_m"] / 2)
        over.append((t["id"], math.hypot(dh, t.get("crown_underside_m") or 0.4 * (t.get("mature_height_m") or 3.0))))
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


BBQ_CROWN_M = 0.3      # design margin outside a crown's projection (POLICY)
BBQ_SIDE_M = 0.65      # design clearance: the manual states 24 in (0.61 m) to combustibles, rounded up to 0.65 m; also never under a crown (nor within 0.65 m of its edge)
BBQ_MANUAL = {"product": "Weber Q1200 gas grill (small, portable; the product is NOT chosen: the figure is a stand-in for any small gas grill and is re-checked at product choice)",
              "url": "https://www.manualslib.com/manual/2027886/Weber-Q1200.html?page=2", "status": "SOURCED, read on the ManualsLib page 2 (the Weber PDF is an image without text)",
              "quotes": ["Keep the grill a minimum of 24 inches away from recreational vehicles and combustible materials like wood, paper, cloth and plastic.",
                         "Do not use in a garage, building, breezeway, tent, any other enclosed area or beneath overhead combustible construction."]}


def bbq_manual_check(L):
    """Replaces the LDK 2.0 m floor (a wood-fire bylaw figure, 'the product instructions govern') for the small gas BBQ stand: manual figure 24 in (0.61 m) from combustibles, design 1.0 m, and not beneath overhead construction or
    a tree crown (a crown is treated as combustible overhead at any height, as the pit rule does)."""
    bq = next(f for f in L["features"] if f["kind"] == "bbq")
    r = rbox(bq["rect"])
    items = {f"building-{i}": box(*b) for i, b in enumerate(L["buildings"])}
    for k in ("planting_groups", "obstacles", "screens", "walls"):
        for it in L[k]:
            if it.get("rect"):
                items[f"{k}:{it['id']}"] = rbox(it["rect"])
    crowns_ = {"crown:" + t["id"]: Point(*(t.get("crown_center") or t["center"])).buffer(t["mature_spread_m"] / 2, 32) for t in L["trees"]}
    crowns_.update({"canopy:" + cn["id"]: rbox(cn["rect"]) for cn in L["canopies"]})
    d = {k: r.distance(v) for k, v in items.items()}
    nk, nd = min(d.items(), key=lambda kv: kv[1])
    dc = {k: r.distance(v) for k, v in crowns_.items()}
    ck, cd = min(dc.items(), key=lambda kv: kv[1]) if dc else ("none", 99.0)
    ok = nd + 1e-9 >= BBQ_SIDE_M and cd + 1e-9 >= BBQ_CROWN_M
    return _r("LDG-BBQ-MANUAL", "pass" if ok else "fail", bq["id"], f"BBQ stand: nearest combustible, structure or planting {nd * 1000:.0f} mm ({nk}; manual 610 mm = 24 in, design {BBQ_SIDE_M * 1000:.0f} mm); nearest crown or roof projection {cd * 1000:.0f} mm ({ck}; the manual forbids use beneath overhead combustible construction, design {BBQ_CROWN_M * 1000:.0f} mm outside it)",
              round(min(nd, cd * BBQ_SIDE_M / BBQ_CROWN_M) * 1000), round(BBQ_SIDE_M * 1000), "mm")


def bbq_checks(L):
    return [bbq_manual_check(L)] if any(f["kind"] == "bbq" for f in L["features"]) else []


def superseded(res):
    """LDK LS-FIRE-STRUCT shortfalls on the pit that the manuals replace; the 2.0 m floor is a wood-fire bylaw, the pit is gas. Reported, never dropped silently."""
    return [r for r in res if r.criterion == "LS-FIRE-STRUCT" and r.subject in ("s-firepit", "s-bbq") and r.status != "pass"]


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


# ---- shade trees: leaf-on and leaf-off states ---------------------------------------------------------------------------------
def habit(slug):
    return POOL[slug].habit if slug in POOL else None


def crowns(L):
    """One record per tree: crown disc at the PRUNED spread, densities from the LDC CROWN assumption (F.CROWN). Evergreen keeps its density all year; deciduous is bare Dec-Feb (client's own months; Cairo months GAP)."""
    out = []
    for t in L["trees"]:
        if t["center"][0] < 20:
            continue
        ev = habit(t["species"]) != "deciduous"
        r = t["mature_spread_m"] / 2
        out.append({"id": t["id"], "species": t["species"], "c": t.get("crown_center") or t["center"], "r": r, "evergreen": ev, "d_on": F.CROWN["evergreen" if ev else "deciduous_on"], "d_off": F.CROWN["evergreen" if ev else "deciduous_off"],
                    "z": S.FLOOR_Z + (t.get("crown_underside_m") or 0.4 * t["mature_height_m"]) + 0.3 * (t["mature_height_m"] - (t.get("crown_underside_m") or 0.4 * t["mature_height_m"]))})
    return out


def crown_cells(L, season, st=0.25):
    """Cover rectangles for the privacy rule: the crown disc as 0.25 m cells whose centre lies inside it. Winter: evergreen crowns only (a bare crown is not cover)."""
    out = []
    for c in crowns(L):
        if season != "summer" and not c["evergreen"]:
            continue
        n = int(c["r"] / st) + 1
        for i in range(-n, n):
            for j in range(-n, n):
                x, y = c["c"][0] + (i + .5) * st, c["c"][1] + (j + .5) * st
                if math.hypot(x - c["c"][0], y - c["c"][1]) <= c["r"]:
                    out.append([x - st / 2, y - st / 2, x + st / 2, y + st / 2])
    return out


def sun_hours_state(L, pts, day, lo, hi, state):
    """Direct sun hours at points (x, y, z) between lo and hi hours on `day`: LDS structure rays reduced by the layout's crowns in `state` ('on' or 'off': leaf state), product of (1 - density) over crowns the ray crosses."""
    from ..site import analyse as AN
    from datetime import datetime, timedelta, timezone
    from ... import solar, villa_env as E
    from ...orientation import sun_direction
    pts = np.asarray(pts, float)
    mids, lit = AN.sunlit_matrix(day, pts)
    cr = crowns(L)
    tot = np.zeros(len(pts))
    for i, m in enumerate(mids):
        if not (lo * 60 <= m < hi * 60):
            continue
        when = datetime.fromisoformat(day).replace(tzinfo=timezone.utc) + timedelta(minutes=float(m)) - timedelta(hours=E.TIME_ZONE)
        sp = solar.sun_position(when, E.LATITUDE, E.LONGITUDE)
        dv = np.array(sun_direction(sp.azimuth, sp.altitude))
        for k, p in enumerate(pts):
            if not lit[i, k] or dv[2] <= 0:
                continue
            tr = 1.0
            for c in cr:
                t = (c["z"] - p[2]) / dv[2]
                if t > 0 and math.hypot(p[0] + t * dv[0] - c["c"][0], p[1] + t * dv[1] - c["c"][1]) <= c["r"]:
                    tr *= 1 - c["d_on" if state == "on" else "d_off"]
            tot[k] += 0.25 * tr
    return tot


def seat_points(L):
    """Seated-eye-level (1.1 m) points: four around the table (chairs), the centre of each south bench."""
    out = {}
    for t in L["tables"]:
        cx, cy = t["center"]
        w, h = t["size_m"]
        out["table"] = [(cx - w / 3, cy - h / 2 - 0.3), (cx + w / 3, cy - h / 2 - 0.3), (cx - w / 3, cy + h / 2 + 0.3), (cx + w / 3, cy + h / 2 + 0.3)]
    for s_ in L["seating"]:
        if s_["rect"][0] > 20:
            out[s_["id"]] = [((s_["rect"][0] + s_["rect"][2]) / 2, (s_["rect"][1] + s_["rect"][3]) / 2)]
    return {k: [(x, y, S.FLOOR_Z + 1.1) for x, y in v] for k, v in out.items()}


WINTER_SEAT_MIN_H = 2.5      # POLICY: at least half of the 5 h window 10-15 h on 21 Dec for the best seated place; no held source gives a winter-sun target (GAP-SHADE-TARGET)


def season_check(L):
    """Summer midday (21 Jun 10-15) and winter midday (21 Dec 10-15) direct sun at every south seat, leaf-on and leaf-off, against open sky (structure only). Evening (17-20 DST) is already sun-free from the structure (LDS layer, 0 h at the seats).
    Checks: summer, leaf-on crowns cut the table's summer midday sun to at most 60 % of open sky; winter, leaf-off keeps at least 80 % of open-sky sun at the table; the best seated place keeps WINTER_SEAT_MIN_H h in winter."""
    pts = seat_points(L)
    tab = {}
    L0 = {**L, "trees": []}
    for k, ps in pts.items():
        sb = sun_hours_state(L0, ps, "2026-06-21", 10, 15, "on")
        sa = sun_hours_state(L, ps, "2026-06-21", 10, 15, "on")
        wb = sun_hours_state(L0, ps, "2026-12-21", 10, 15, "on")
        wa = sun_hours_state(L, ps, "2026-12-21", 10, 15, "off")
        we = sun_hours_state(L, ps, "2026-12-21", 10, 15, "on")           # the same trees if they were evergreen-dense (what a pergola-like roof would do): leaf-on state in winter
        tab[k] = {"summer_open_sky_h": round(float(sb.mean()), 2), "summer_leaf_on_h": round(float(sa.mean()), 2), "winter_open_sky_h": round(float(wb.mean()), 2), "winter_leaf_off_h": round(float(wa.mean()), 2), "winter_if_leaf_on_h": round(float(we.mean()), 2)}
    t = tab.get("table")
    res = []
    if t:
        ok_s = t["summer_open_sky_h"] == 0 or t["summer_leaf_on_h"] <= 0.6 * t["summer_open_sky_h"] + 1e-9
        res.append(_r("LDG-SHADE-SUMMER", "pass" if ok_s else "fail", "table", f"table seats, direct sun 10-15 h on 21 Jun: {t['summer_open_sky_h']} h open sky, {t['summer_leaf_on_h']} h under the leafed crown (density {F.CROWN['deciduous_on']}, LDC assumption); pass = at most 60 % of open-sky sun",
                      t["summer_leaf_on_h"], round(0.6 * t["summer_open_sky_h"], 2), "h"))
        ok_w = t["winter_leaf_off_h"] >= 0.8 * t["winter_open_sky_h"] - 1e-9
        res.append(_r("LDG-SHADE-WINTER", "pass" if ok_w else "fail", "table", f"table seats, direct sun 10-15 h on 21 Dec: {t['winter_open_sky_h']} h open sky, {t['winter_leaf_off_h']} h with the bare crown (density {F.CROWN['deciduous_off']}), {t['winter_if_leaf_on_h']} h if it kept its leaves; pass = at least 80 % of open-sky sun kept",
                      t["winter_leaf_off_h"], round(0.8 * t["winter_open_sky_h"], 2), "h"))
    best = max(tab.items(), key=lambda kv: kv[1]["winter_leaf_off_h"])
    res.append(_r("LDG-WINTER-SEAT", "pass" if best[1]["winter_leaf_off_h"] >= WINTER_SEAT_MIN_H else "fail", best[0], f"best seated place in winter ({best[0]}): {best[1]['winter_leaf_off_h']} h direct sun 10-15 h on 21 Dec with leaf-off crowns (POLICY minimum {WINTER_SEAT_MIN_H} h of the 5 h window)",
                  best[1]["winter_leaf_off_h"], WINTER_SEAT_MIN_H, "h"))
    return res, tab


def tree_sun_check(L):
    """A tree's sun need is measured at its crown (the ground under a crown is not where its leaves are): direct sun on 21 Jun 10-17 h at the crown centre, LDS structure only, vs species sun class (policy thresholds as for beds)."""
    out, rows = [], {}
    for c in crowns(L):
        h = sun_hours_state({**L, "trees": []}, [(c["c"][0], c["c"][1], c["z"])], "2026-06-21", 8, 18, "on")[0]
        res = R.sun_ok(POOL[c["species"]], float(h))
        rows[c["id"]] = {"crown_sun_h_21jun_8_18": round(float(h), 2), "fit": res}
        out.append(_r("LDG-TREE-SUN", "pass" if res != "fail" else "fail", c["id"], f"{c['id']} ({c['species']}): {h:.1f} h direct sun at crown height on 21 Jun 8-18 h (LDS structure only); species sun class {POOL[c['species']].sun_classes}: {res}", round(float(h), 2), None, "h"))
    return out, rows


def sun_checks_final(L, leaf=None):
    """R.sun_checks with bed sun cut by the leafed crown over the bed (fraction of bed area under a crown x density 0.7)."""
    from shapely.geometry import Point as Pt
    cr = crowns(L)
    seen = {}
    for g in L["planting_groups"]:
        june = C.bed_sun(g["rect"])
        bx = rbox(g["rect"])
        if cr and bx.area > 0:
            f_ = max((bx.intersection(Pt(*c["c"]).buffer(c["r"], 24)).area / bx.area * c["d_on"] for c in cr), default=0.0)
            june *= 1 - f_
        for p in g["plants"]:
            seen.setdefault((g["id"], p["species"]), (R.sun_ok(POOL[p["species"]], june), june))
    bad = [(k, v) for k, v in seen.items() if v[0] == "fail"]
    return _r("LDG-SUNFIT", "pass" if not bad else "fail", "site", "every plant's sun class is met by its bed's 21-June sun, reduced by the leafed crown over the bed (part shade 2 h, conditional 75 % of need; POLICY thresholds)" if not bad
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


def privacy_checks(L, rooms):
    """Per seated room: remaining share of today's overlooking after cover and the screen. HARD in summer (crowns leafed). In WINTER only evergreen crowns count as cover: a bare crown is not cover, so a deciduous
    pick costs winter overhead privacy: reported as a WARN with the figure where it exceeds the limit (the client accepted winter sun; the cost is stated, never hidden). The opening the client asked for at
    the pit lets the sister plot see in: reported as a warning too (waiver), never hidden."""
    ox = (S.SX0 + F.OPEN_A[0], S.SX0 + F.OPEN_A[1])
    top = S.FLOOR_Z + C.SCREEN_H
    cs, cw = crown_cells(L, "summer"), crown_cells(L, "winter")
    res, tab = [], {}
    for name, (rect, lim) in rooms.items():
        base = S.eyes_total(rect, "seated")
        row = {}
        for lab, cv in (("summer", cs), ("winter", cw)):
            row[lab] = round(S.eyes_total(rect, "seated", cover_rects=cv, screen_top_z=top) / base, 3) if base else 0.0
            row[lab + "_with_opening"] = round(eyes_open(rect, cv, ox) / base, 3) if base else 0.0
        row["no_cover"] = round(S.eyes_total(rect, "seated", cover_rects=[], screen_top_z=top) / base, 3) if base else 0.0
        tab[name] = {"limit": lim, "today_eye_points": round(base, 1), **row}
        res.append(_r("LDG-PRIV", "pass" if row["summer"] <= lim + 1e-9 else "fail", f"{name}/summer",
                      f"{name}, summer (crowns leafed): {row['summer']:.0%} of today's overlooking remains with the screen unbroken (limit {lim:.0%}; {row['no_cover']:.0%} with no tree)", row["summer"], lim, "share"))
        if row["winter"] > lim + 1e-9:
            res.append(_r("LDG-PRIV-WINTER", "warn", f"{name}/winter", f"{name}, winter (deciduous crowns bare): {row['winter']:.0%} of today's overlooking remains (limit {lim:.0%}); accepted with the winter sun (client 2026-11-22), shown not hidden", row["winter"], lim, "share"))
        w = row["summer_with_opening"]
        if w > lim + 1e-9 and w > row["summer"] + 1e-9:
            res.append(_r("LDG-PRIV-OPENING", "warn", f"{name}/summer",
                          f"WAIVED by the client's decision (screen opening at the shared fire pit): {name} summer would be overlooked at {w:.0%} of today's through the opening (limit {lim:.0%}); a closable screen leaf would restore {row['summer']:.0%}", w, lim, "share"))
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


def pond_sun(L):
    """Mean 21-June direct sun over each pond's rectangle (LDS layer): water lilies (Nymphaea, full sun 6 h) are specified only where the sun need is met."""
    out = {}
    for f in L["features"]:
        if f.get("kind") == "pond":
            h = S.mean("sun", "sun_hours_summer_solstice", f["rect"])
            out[f["id"]] = {"sun_21jun_h": None if h is None else round(h, 2), "water_lilies": "no: full-sun species needs 6 h" if (h or 0) < 6 else "possible"}
    return out


# ---- everything ---------------------------------------------------------------------------------------------------------
HARD_WARN = R.HARD_WARN       # LDG-PRIV-WINTER and LDG-PRIV-OPENING are warnings by the client's decision, not in this list


def tree_site_checks(L):
    """Pruning regime declared for every tree held below its species size; root distance to the ponds and buildings for species with aggressive roots (POLICY; NHBC does not accept a barrier instead of distance: AD-EXT-TREE-BARRIER)."""
    res = []
    ponds = [rbox(f["rect"]) for f in L["features"] if f.get("kind") == "pond"]
    bs = [box(*b) for b in L["buildings"]]
    for t in L["trees"]:
        if t.get("pruned"):
            ok = bool(t.get("pruning"))
            res.append(_r("LDG-PRUNE", "pass" if ok else "fail", t["id"], f"{t['id']}: pruned crown {t['mature_spread_m']} m wide, {t['mature_height_m']} m high (species {t['species_mature_spread_m']} m, {t['species_mature_height_m']} m): regime declared = {ok}; source status: {t.get('pruning_source_status')}",
                          t["mature_spread_m"], None, "m"))
        sp = POOL[t["species"]]
        root = None
        try:
            from ..build import planting as PL
            root = PL._plants()[t["species"]]["attributes"]["root_behaviour"]["value"]["class"]
        except Exception:
            pass
        if root in ("aggressive", "moderate"):
            c = Point(*t["center"])
            dp = min((p.distance(c) for p in ponds), default=99.0)
            db = min(b.distance(c) for b in bs)
            need = 6.0 if root == "aggressive" else 1.5           # POLICY: no held figure; aggressive roots 6 m from a pond or building; moderate roots 1.5 m from a pond liner (the building distance is the NHBC rule LS-TREE-BUILDING)
            db = db if root == "aggressive" else 99.0
            ok = (dp >= need and db >= need) or bool(t.get("root_barrier"))
            res.append(_r("LDG-ROOTS", "pass" if ok else "fail", t["id"], f"{t['id']} ({root} roots): {dp:.1f} m to the nearest pond, {db:.1f} m to a building; POLICY {need:g} m, or a declared root barrier (a barrier never replaces the NHBC distance)", round(min(dp, db), 2), need, "m"))
    return res


def evaluate_all(L, rooms, covers):
    res = list(C.ldk(L))
    cs = crown_cells(L, "summer") + [c["rect"] for c in L["canopies"]]
    own = [r for r in C.own_checks(L, rooms, cs, S.FLOOR_Z + C.SCREEN_H, None) if r.criterion != "LDG-PRIV"]
    prv, ptab = privacy_checks(L, rooms)
    own += prv
    sunr, seen = sun_checks_final(L)
    ts, trows = tree_sun_check(L)
    sea, stab = season_check(L)
    extra = [id_check(L), zone_check(L), surface_check(L), gravel_check(L), tree_pergola_check(L), plant_solid_check(L), pot_check(L)] + fire_manual_check(L) + bbq_checks(L) + pond_section_check(L) + tree_site_checks(L) + ts + sea
    gdata = {"privacy_table": ptab, "season_table": stab, "tree_sun": trows}
    return res + own + [sunr] + R.tree_checks(L) + extra, seen, gdata


def hard_fails(res):
    sup = {id(r) for r in superseded(res)}
    return [r for r in res if id(r) not in sup and (r.status == "fail" or (r.status == "warn" and r.criterion in HARD_WARN))]
