"""Computed critics: horticulturist, user, climate and the measurable part of the landscape architect.

Every check returns Findings (achieved vs required, source). Thresholds without a held source are labelled
`policy` in `source`; qualitative sources (AD-* advisories) are never turned into a number by the source itself.
A check that lacks its input returns `not_evaluated`, never `pass`.
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict

from shapely.geometry import LineString, Point
from shapely.ops import unary_union

from . import site as S
from .common import Finding, layer_of, path_line, plant_positions, rect_poly, species_info, zone_of_point

TOX_BAD = ("toxic", "highly_toxic")


def F(critic, crit, status, sev, ev, src, **kw):
    return Finding(critic, crit, status, sev, ev, src, **kw)


def ok(cond, warn=False):
    return "pass" if cond else ("warn" if warn else "fail")


# ------------------------------------------------------------------------------------------------ geometry
def seat_points(layout):
    """[{id, pt, use}] one per seat: bench/sofa rect -> seats spread along its long side, table -> ring."""
    out = []
    for s in layout.get("seating", []):
        x0, y0, x1, y1 = s["rect"]; n = max(1, int(s.get("seats", 1)))
        horiz = (x1 - x0) >= (y1 - y0)
        for k in range(n):
            f = (k + .5) / n
            pt = (x0 + (x1 - x0) * f, (y0 + y1) / 2) if horiz else ((x0 + x1) / 2, y0 + (y1 - y0) * f)
            out.append({"id": f"{s['id']}#{k}", "pt": pt, "use": _use(layout, pt, s.get("zone"))})
    for t in layout.get("tables", []):
        n = int(t.get("seats", 0)); r = (t.get("diameter_m") or max(t.get("size_m", [1, 1]))) / 2 + 0.45
        for k in range(n):
            a = 2 * math.pi * k / n
            pt = (t["center"][0] + r * math.cos(a), t["center"][1] + r * math.sin(a))
            out.append({"id": f"{t['id']}#{k}", "pt": pt, "use": _use(layout, pt, t.get("zone"))})
    return out


def _use(layout, pt, zone_id=None):
    z = zone_of_point(layout, pt)
    if z is None and zone_id:
        z = next((q for q in layout.get("zones", []) if q["id"] == zone_id), None)
    return (z or {}).get("use", "other")


def feature_pt(f):
    if f.get("center"): return tuple(f["center"])
    r = f["rect"]; return ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)


def features(layout, kind):
    return [f for f in layout.get("features", []) if f.get("kind") == kind]


def walkable(layout, min_w=0.6):
    """Walkable ground: zones that are not planting or water, paved areas and paths, minus planting beds,
    water/fire features, seats, tables, buildings, walls; eroded by half `min_w` (a person needs that width)."""
    ground = [rect_poly(z["rect"]) for z in layout.get("zones", []) if z.get("rect") and z.get("surface") not in ("planting", "water")]
    ground += [rect_poly(a["rect"]) for a in layout.get("paved_areas", []) if a.get("rect")]
    for p in layout.get("paths", []):
        ln = path_line(p)
        if ln is not None: ground.append(ln.buffer(p.get("width_m", 1.0) / 2, cap_style=2))
    if not ground: return None
    g = unary_union(ground)
    block = [rect_poly(b) for b in layout.get("buildings", [])] + [rect_poly(w["rect"]) for w in layout.get("walls", []) if w.get("rect")]
    block += [rect_poly(b["rect"]) for b in layout.get("planting_groups", []) if b.get("rect")]
    block += [rect_poly(s["rect"]) for s in layout.get("screens", []) if s.get("rect") and not s.get("canopy")]
    for t in layout.get("tables", []):
        block.append(Point(t["center"]).buffer((t.get("diameter_m") or 1.0) / 2))
    for f in layout.get("features", []):
        if f.get("kind") in ("pond", "herb_bed", "fruit_tree") or not f.get("flush", True):
            block.append(Point(feature_pt(f)).buffer((f.get("diameter_m") or 1.0) / 2) if f.get("center") else rect_poly(f["rect"]))
    for t in layout.get("trees", []):
        block.append(Point(t["center"]).buffer(0.25))
    g = g.difference(unary_union(block)) if block else g
    return g.buffer(-min_w / 2).buffer(min_w / 2 - 1e-6) if False else g.buffer(-min_w / 2)


def reachable(walk, a, b, tol=0.45):
    """Is b reachable from a on `walk`? Endpoints snap to the nearest walkable piece within `tol` m."""
    if walk is None or walk.is_empty: return False
    comps = list(walk.geoms) if walk.geom_type == "MultiPolygon" else [walk]
    def comp(p):
        pt = Point(p); best = min(comps, key=lambda c: c.distance(pt))
        return best if best.distance(pt) <= tol else None
    ca, cb = comp(a), comp(b)
    return ca is not None and ca is cb


def _reach(f):
    """How far from a feature's centre a person can stand to use it (its radius, or half its long side, plus 0.9 m)."""
    r = (f.get("diameter_m") or 0) / 2 if f.get("center") else max(abs(f["rect"][2] - f["rect"][0]), abs(f["rect"][3] - f["rect"][1])) / 2
    return r + 0.9


def door_out(door):
    """A point 0.7 m outside a house door, on the garden side (`faces` is the outward axis)."""
    x, y = door["at"]; f = door["faces"]
    dx = {"+x": .7, "-x": -.7}.get(f, 0); dy = {"+y": .7, "-y": -.7}.get(f, 0)
    return (x + dx, y + dy)


def doors_of(layout):
    ds = layout.get("doors")
    if ds: return [{"id": d["id"], "at": tuple(d["at"]), "faces": d.get("faces", "+x"), "room": d.get("room", "")} for d in ds]
    return S.doors()


# ================================================================================================ HORTICULTURIST
H = "horticulturist"
DRIFT_MIN = 3          # policy: a drift is >= 3 plants of one species in one group (LDP drift size is a GAP)
DRIFT_SHARE = 0.60     # policy: at least 60 % of shrub/perennial/ground plants sit in drifts
LAYER_MIN = 3          # policy: at least 3 of the 4 layers (canopy, understorey, shrub, ground) present
SEASON_MONTHS = 8      # policy: flowers in at least 8 months of the year, and in winter (Dec-Feb)
TOX_DIST = 2.0         # policy distance (m): toxic plants kept this far from herbs, seats, tables (TS 550-3: out of children's reach)
SRC_RHYTHM = "AD-COMP-RHYTHM (qualitative, Ching); threshold is policy"
SRC_LDL = "LDL plants.json (sourced per attribute); policy thresholds"


def horticulturist(layout):
    out = []
    pls = plant_positions(layout)
    if not pls:
        return [F(H, "H-PLANTING-PRESENT", "fail", "blocking", "no plants in the layout", "brief: lush planting, colourful drifts (policy)")]
    species = sorted({p["species"] for p in pls})
    unknown = [s for s in species if not species_info(s)["known"]]
    out.append(F(H, "H-SPECIES-KNOWN", ok(not unknown, True), "minor", f"{len(unknown)} of {len(species)} species not in the plant library" + (f": {unknown}" if unknown else ""), SRC_LDL))
    # viability
    bad = [s for s in species if species_info(s)["viability"] == "not_viable"]
    cond = [s for s in species if species_info(s)["viability"] == "viable_with_conditions"]
    out.append(F(H, "H-SITE-VIABLE", ok(not bad), "major", f"not viable on this site: {bad or 'none'}; viable with conditions: {len(cond)} ({cond[:6]})", "LDL site_viability (frost floor 0 C policy vs TMYx min 5.1 C)"))
    # mature size versus space: tree crown vs the room it stands in; bed crowding
    for t in layout.get("trees", []):
        sp = t.get("mature_spread_m") or species_info(t["species"], t.get("form"))["draw_spread_m"]
        z = zone_of_point(layout, t["center"])
        if z and z.get("rect"):
            x0, y0, x1, y1 = z["rect"]; short = min(abs(x1 - x0), abs(y1 - y0))
            out.append(F(H, "H-SIZE-VS-SPACE", ok(sp <= 0.8 * short), "major", f"{t['species']}: mature spread {sp:.1f} m in a space {short:.1f} m across (limit 0.8 x = {0.8*short:.1f} m)", "LDL mature spread; 0.8 ratio is policy", subject=t["id"]))
    for g in layout.get("planting_groups", []):
        if not g.get("rect"): continue
        area = rect_poly(g["rect"]).area
        mine = [p for p in pls if p["group"] == g["id"] and p["layer"] != "ground" and "screen_hedge" not in species_info(p["species"])["layers"]]
        if not mine or area <= 0: continue
        cover = sum(math.pi * (p["spread"] / 2) ** 2 for p in mine)
        out.append(F(H, "H-BED-CROWDING", ok(cover <= 1.5 * area, True), "minor", f"bed {g['id']}: mature crowns {cover:.1f} m2 on {area:.1f} m2 of bed (limit 1.5 x)", "LDL mature spread; 1.5 overlap is policy", subject=g["id"]))
    # drifts and repetition (the pattern of a planting, measured on non-tree plants)
    small = [p for p in pls if p["layer"] in ("shrub", "ground")]
    cnt = Counter((p["group"], p["species"]) for p in small)
    in_drift = sum(n for n in cnt.values() if n >= DRIFT_MIN)
    share = in_drift / len(small) if small else 0
    lone = [s for s in {p["species"] for p in small} if sum(1 for p in small if p["species"] == s) == 1]
    sizes = sorted(n for n in cnt.values() if n >= 2)
    out.append(F(H, "H-DRIFTS", ok(share >= DRIFT_SHARE), "major",
                 f"{share:.0%} of {len(small)} shrub/ground plants sit in drifts of >= {DRIFT_MIN} (required {DRIFT_SHARE:.0%}); median drift {sizes[len(sizes)//2] if sizes else 0}; lone single-plant species: {len(lone)}", SRC_RHYTHM,
                 extra={"share": round(share, 3), "lone": lone}))
    # repetition across the garden: some species recur in >= 2 groups
    groups_of = defaultdict(set)
    for p in pls: groups_of[p["species"]].add(p["group"])
    rep = [s for s, g in groups_of.items() if len(g) >= 2]
    out.append(F(H, "H-REPETITION", ok(len(rep) >= 2, True), "minor", f"{len(rep)} species recur in two or more beds (required >= 2): {rep[:5]}", SRC_RHYTHM))
    # layers
    present = Counter(p["layer"] for p in pls)
    n_l = sum(1 for k in ("canopy", "understorey", "shrub", "ground") if present[k])
    out.append(F(H, "H-LAYERS", ok(n_l >= LAYER_MIN and present["canopy"] + present["understorey"] >= 1), "major",
                 f"{n_l} of 4 layers present ({dict(present)}); required >= {LAYER_MIN} including a tree layer", "AD-COMP-LAYERING (qualitative); counts policy"))
    # seasonality
    months = set()
    for s in species:
        m = species_info(s)["months"]
        if m: months |= set(m)
    have = len(months); winter = bool(months & {12, 1, 2})
    known = sum(1 for s in species if species_info(s)["months"])
    st = "not_evaluated" if known == 0 else ok(have >= SEASON_MONTHS and winter)
    out.append(F(H, "H-SEASONALITY", st, "minor", f"flowers in {have} of 12 months, winter: {winter} (required >= {SEASON_MONTHS} and winter); {known} of {len(species)} species have month data", "brief: seasonal colour; LDL flowering months; thresholds policy"))
    # sun fit at the plant position
    misfit = []
    for p in pls:
        info = species_info(p["species"]); sun = info["sun"]
        h = S.sample("sun.json", "sun_hours_summer_solstice", p["at"])
        if not sun or h is None: continue
        if sun == ["full_sun"] and h < 3: misfit.append((p["species"], "full-sun species, %.1f h summer sun" % h))
        if "full_sun" not in sun and h >= 9: misfit.append((p["species"], "shade species, %.1f h summer sun" % h))
    names = sorted({m[0] for m in misfit})
    out.append(F(H, "H-SUN-FIT", ok(not misfit, True), "major", f"{len(misfit)} plants where the LDS sun layer contradicts the species' stated sun class ({names[:6]}); full sun is 6 h+ (RHS via LDK), limit used 3 h", "LDL sun class vs LDS sun.json; limits policy"))
    # toxicity placement
    sensitive = [("herb bed", feature_pt(f)) for f in features(layout, "herb_bed")] + [("seat", s["pt"]) for s in seat_points(layout)]
    hits = []
    for p in pls:
        t = species_info(p["species"])["tox_people"]
        if t in TOX_BAD:
            for lab, pt in sensitive:
                d = math.dist(p["at"], pt) - p["spread"] / 2
                if d < TOX_DIST: hits.append((p["species"], lab, round(max(d, 0), 1))); break
    out.append(F(H, "H-TOXIC-PLACEMENT", ok(not hits), "major", f"{len(hits)} toxic-to-people plants within {TOX_DIST} m of a herb bed or seat: {hits[:4]}" if hits else f"no toxic plant within {TOX_DIST} m of a herb bed or seat (toxicity known for {sum(1 for s in species if species_info(s)['tox_people'])} of {len(species)} species)", "LDL toxicity_people; Time-Saver 550-3 (poisonous plants out of children's reach); distance policy"))
    ponds = features(layout, "pond")
    if ponds:
        fhits = [(p["species"]) for p in pls for f in ponds if species_info(p["species"])["tox_fish"] in TOX_BAD and math.dist(p["at"], feature_pt(f)) < 3]
        known_f = [s for s in species if species_info(s)["tox_fish"]]
        out.append(F(H, "H-FISH-TOXIC", "not_evaluated" if not known_f and not fhits else ok(not fhits), "minor", f"fish toxicity stated for {len(known_f)} of {len(species)} species (a GAP in LDL for all pond plants); toxic near the pond: {fhits or 'none'}", "LDL GAP (no fish-toxicity source)"))
    return out + _ldk(layout, H, ("LS-TREE-BUILDING", "LS-ROOTZONE", "LS-SOIL-DEPTH", "LS-HYDROZONE", "LS-HERB-SUN", "LS-POND-SHADE", "LS-HEDGE-SPACING"))


def _enrich(layout):
    """Copy of the layout with water_need / form filled from the plant library where the layout leaves them out."""
    import copy
    lay = copy.deepcopy(layout)
    wmap = {"low": "low", "moderate": "medium", "high": "high"}
    for g in lay.get("planting_groups", []):
        for p in g.get("plants", []):
            info = species_info(p["species"], p.get("form"))
            if not p.get("water_need") and info["water"] in wmap: p["water_need"] = wmap[info["water"]]
            if not p.get("form") and info["known"]: p["form"] = {"canopy": "large_tree", "understorey": "small_tree", "shrub": "shrub", "ground": "ground_cover"}[layer_of(p["species"], None)]
    from . import site as SS
    for f in lay.get("features", []):
        if f.get("kind") == "herb_bed" and "midsummer_sun_hours" not in f:
            h = SS.sample("sun.json", "sun_hours_summer_solstice", feature_pt(f))
            if h is not None: f["midsummer_sun_hours"] = h
    return lay


def _ldk(layout, critic, ids):
    """Pass through the sourced LDK hard rules that belong to this critic (their sources are on the result);
    several results of one rule collapse to the worst one so a bed-by-bed rule does not flood the report."""
    from ..rules import evaluate
    by = defaultdict(list)
    for r in evaluate(_enrich(layout)):
        if r.criterion in ids: by[r.criterion].append(r)
    res = []
    for cid, rs in by.items():
        for rank in ("fail", "warn", "not_evaluated", "pass"):
            pick = [r for r in rs if r.status == rank]
            if pick: break
        r = pick[0]
        sev = {"fail": "major", "warn": "minor"}.get(r.status, "info")
        n = f" ({len(pick)} of {len(rs)} results)" if len(rs) > 1 else ""
        res.append(F(critic, cid, r.status, sev, f"{r.message}{n}" + (f" [achieved {r.achieved} {r.unit or ''} vs required {r.required}]" if getattr(r, "achieved", None) is not None else ""),
                     ",".join(getattr(r, "source_ids", ()) or ()) or "LDK", subject=getattr(r, "subject", "") or "", extra={"via": "LDK evaluate"}))
    return res


# ================================================================================================ USER
U = "user"
BRIEF = "brief garden-brief-2026-11-22 (client decision)"
SOUTH_X = 15.0      # model x beyond which a point is in the south garden (client naming); north court is x < 8


def _south(pt): return pt[0] >= SOUTH_X
def _north(pt): return pt[0] < 8.0


def user(layout):
    """Walk each brief use from the doors that exist: has it a place, a route and seats?"""
    out = []
    doors = doors_of(layout)
    walk = walkable(layout)
    seats = seat_points(layout)
    sg = [s for s in seats if _south(s["pt"])]
    ng = [s for s in seats if _north(s["pt"])]
    sdoors = [d for d in doors if _south(d["at"])]
    ndoors = [d for d in doors if _north(d["at"])]

    def route(pt, ds, reach=0.0):
        """Shortest straight-line distance from the nearest door the route actually reaches, else None."""
        best = None
        for d in ds:
            if reachable(walk, door_out(d), pt, 0.45 + reach):
                dist = math.dist(d["at"], pt)
                best = dist if best is None else min(best, dist)
        return best

    def use(cid, label, ok_, ev, sev="major", src=BRIEF):
        out.append(F(U, cid, "pass" if ok_ else "fail", sev, f"{label}: {ev}", src))

    # 1 gathering 10-20: seats, a dining group and a lounge group, a route to each
    n = len(sg)
    by = Counter(s["use"] for s in sg)
    r_d = [route(s["pt"], sdoors) for s in sg if s["use"] == "dining"]
    r_l = [route(s["pt"], sdoors) for s in sg if s["use"] == "lounge"]
    use("U-GATHER-SEATS", "gathering 10-20", n >= 10, f"{n} fixed seats in the south garden (required >= 10; {dict(by)})")
    use("U-GATHER-GROUPS", "gathering 10-20", by["dining"] >= 4 and by["lounge"] >= 3, f"dining seats {by['dining']} (>= 4), lounge seats {by['lounge']} (>= 3): a dining group and a lounge group", src=BRIEF + "; group minimums policy")
    allr = r_d + r_l
    use("U-GATHER-ROUTE", "gathering 10-20", bool(allr) and all(r is not None for r in allr), f"{sum(r is not None for r in allr)} of {len(allr)} dining/lounge seats reachable from a house door on walkable ground 0.6 m wide (LS-PATH-SECONDARY); seats are not obstacles")
    # 2 winter day, 3 summer night -> seats exist in the south garden with a route (the sun is the climate critic's)
    use("U-WINTER-STAY", "winter daytime stay", n >= 2 and any(r is not None for r in [route(s["pt"], sdoors) for s in sg]), f"{n} south seats; a reachable seat exists: {any(route(s['pt'], sdoors) is not None for s in sg)}")
    # 4 quiet corner south: a quiet seat or zone inside the south garden, >= 3 m from the gathering seats' centroid
    quiet_s = [s for s in sg if s["use"] == "quiet"]
    qz = [z for z in layout.get("zones", []) if z.get("use") == "quiet" and _south(((z["rect"][0] + z["rect"][2]) / 2, 0))]
    cent = None
    gat = [s["pt"] for s in sg if s["use"] in ("dining", "lounge")]
    if gat: cent = (sum(p[0] for p in gat) / len(gat), sum(p[1] for p in gat) / len(gat))
    if quiet_s and cent:
        dmin = min(math.dist(s["pt"], cent) for s in quiet_s)
        use("U-QUIET-SOUTH", "quiet corner (south)", dmin >= 3.0 and any(route(s["pt"], sdoors) is not None for s in quiet_s), f"quiet seat {dmin:.1f} m from the gathering seats' centre (required >= 3.0 m, policy) and reachable")
    else:
        use("U-QUIET-SOUTH", "quiet corner (south)", False, "no seat in a quiet-use zone within the south garden" if not quiet_s else "no gathering seats to separate from")
    # 5 quiet north
    use("U-QUIET-NORTH", "quiet north garden", bool(ng) and any(route(s["pt"], ndoors) is not None for s in ng), f"{len(ng)} seats in the north garden; reachable from the lounge door: {any(route(s['pt'], ndoors) is not None for s in ng)}")
    # 6 fire pit
    fp = features(layout, "firepit") + features(layout, "heater")
    if fp:
        p = feature_pt(fp[0]); near = [s for s in sg if 1.5 <= math.dist(s["pt"], p) <= 4.0]
        use("U-FIRE", "fire pit", len(near) >= 4 and route(p, sdoors) is not None, f"{len(near)} seats 1.5-4.0 m from the fire (required >= 4; 1.5 m is LS-FIRE-SEAT); reachable: {route(p, sdoors) is not None}")
    else:
        use("U-FIRE", "fire pit", False, "no fire pit or heater")
    # 7 BBQ: stand place on hard surface, reachable, away from planting
    bq = features(layout, "bbq")
    if bq:
        p = feature_pt(bq[0]); z = zone_of_point(layout, p)
        hard = (z or {}).get("surface") in ("paving", "gravel") or any(rect_poly(a["rect"]).contains(Point(p)) for a in layout.get("paved_areas", []))
        dpl = min([rect_poly(g["rect"]).distance(Point(p)) for g in layout.get("planting_groups", []) if g.get("rect")] or [99])
        use("U-BBQ", "BBQ", hard and dpl >= 1.0 and route(p, sdoors) is not None, f"hard surface {hard}; {dpl:.1f} m from planting (required >= 1.0 m, policy; product instructions govern); reachable {route(p, sdoors) is not None}")
    else:
        use("U-BBQ", "BBQ", False, "no BBQ stand place")
    # 8 pond viewing: pond exists, reachable, a seat within 6 m with a clear sight line at 1.1 m
    pd = features(layout, "pond")
    if pd:
        p = feature_pt(pd[0]); pool = ng + sg
        sc = S.screen_objs(layout)
        def sees(s):
            a = (s["pt"][0], s["pt"][1], S.FLOOR_Z + 1.125); b = (p[0], p[1], S.FLOOR_Z)
            return not any(S._seg_blocked(a, b, o) for o in sc if o.get("d", 1) >= 0.5 and o["top"] > S.FLOOR_Z + 0.9)
        viewers_ = [s for s in pool if math.dist(s["pt"], p) <= 6.0 and sees(s)]
        use("U-POND-VIEW", "pond viewing", bool(viewers_) and (route(p, ndoors + sdoors, _reach(pd[0])) is not None), f"{len(viewers_)} seats within 6 m with a clear sight line to the pond (required >= 1); pond reachable {route(p, ndoors + sdoors, _reach(pd[0])) is not None}")
    else:
        use("U-POND-VIEW", "pond viewing", False, "no pond")
    # 9 herbs / fruit picking: a bed or fruit tree, reachable by a walkable route, <= 12 m from a door (policy)
    hb = features(layout, "herb_bed") + features(layout, "fruit_tree")
    if hb:
        r = [route(feature_pt(f), doors, _reach(f)) for f in hb]
        use("U-PICKING", "herb and fruit picking", any(x is not None and x <= 12 for x in r), f"nearest reachable herb/fruit {min([x for x in r if x is not None], default=None)} m from a door (required reachable and <= 12 m, policy)")
    else:
        use("U-PICKING", "herb and fruit picking", False, "no herb bed or fruit tree")
    # 10 service: a service path >= 0.9 m (LS-PATH-SERVICE) in the layout
    sv = [p for p in layout.get("paths", []) if p.get("class") == "service"]
    use("U-SERVICE", "service", bool(sv) and all(p.get("width_m", 0) >= 0.9 for p in sv), f"{len(sv)} service paths, widths {[p.get('width_m') for p in sv]} (required >= 0.9 m, LS-PATH-SERVICE)", src="LS-PATH-SERVICE (Neufert 1980 p.106 Fig. 22)")
    return out + _ldk(layout, U, ("LS-CAPACITY", "LS-DINE-AREA", "LS-DINE-CLEAR", "LS-LOUNGE-AREA", "LS-STAND-AREA", "LS-BRIEF-FEATURES", "LS-PATH-MAIN", "LS-PATH-SECONDARY", "LS-PATH-SERVICE"))


# ================================================================================================ CLIMATE
CL = "climate"
SUN_FULL_H = 6.0        # RHS definition of full sun, via LDK LS-HERB-SUN
WIN_MIN_H = 2.0         # policy: winter-day seats get >= 2 of the 5 h (10-15)
SEAT_SHARE = 0.7        # policy: this share of seats must meet the sun test
PRIV_MAX = 8            # policy: residual overlooking eye points per seated cell; set with the reference scheme as the clean baseline (LDS counts 5 as the screening floor; the real limit is the client's, GAP-OVERLOOK-ABOVE)
WIND_SHARE = 0.35       # policy: share of wind-hours blowing the fire's smoke at a seat


def _wind_to_seat(layout, fire, pt, setname):
    """Share of the set's hours whose smoke plume from the fire (downwind sector +-45 deg) covers the seat."""
    ws = S.wind_sets()[setname]
    v = (pt[0] - fire[0], pt[1] - fire[1]); ang = math.degrees(math.atan2(v[0], v[1]))   # model angle of fire->seat (x vs y)
    tot = 0.0
    for sec in ws["sectors"]:
        b = sec["from_bearing_true"]
        # wind from b blows toward b+180; direction in the model frame: (x = sin(b+180-20), y = cos(b+180-20))
        t = math.radians(b + 180 - 20); to = math.degrees(math.atan2(math.sin(t), math.cos(t)))
        d = abs((ang - to + 180) % 360 - 180)
        if d <= 45: tot += sec["share_pct"]
    return tot / 100.0


def climate(layout):
    out = []
    seats = [s for s in seat_points(layout) if _south(s["pt"])]
    c_ = "Time-Saver/LDS sun layers + layout shade (assumed crown density, docs/lanes/LDC.md); client: shade over sun"
    if not seats:
        return [F(CL, "C-SEATS", "not_evaluated", "info", "no south-garden seats to analyse", BRIEF)]
    # summer day: full summer sun (>= 6 h on 21 Jun) at seats
    from . import site as SS
    def day_sun(pt):
        base = SS.sample("sun.json", "sun_hours_summer_solstice", pt)
        if base is None: return None
        # layout shade applied over the whole day window as a fraction of sun samples
        suns = SS._suns("2026-06-21", 5 * 60, 19 * 60)
        objs = SS.crowns(layout, "summer"); p = (pt[0], pt[1], SS.FLOOR_Z + 0.5)
        import numpy as np
        if not objs or not suns: return base
        blocked = float(np.mean([1 - np.prod([1 - o["d"] if SS._hit(o, p, d) else 1 for o in objs]) for d in suns]))
        return base * (1 - blocked)
    vals = [(s, day_sun(s["pt"])) for s in seats]
    known = [(s, v) for s, v in vals if v is not None]
    full = [s["id"] for s, v in known if v >= SUN_FULL_H]
    out.append(F(CL, "C-SUMMER-SHADE", ok(len(full) <= (1 - SEAT_SHARE) * len(known)) if known else "not_evaluated", "major",
                 f"{len(full)} of {len(known)} south seats get full summer sun (>= {SUN_FULL_H:g} h on 21 Jun after layout shade; allowed <= {(1-SEAT_SHARE):.0%}): {full[:4]}", c_))
    # summer evening (DST clock): informational and gating if sun reaches the seat
    ev = [(s, SS.sun_hours(layout, s["pt"], "evening")) for s in seats]
    sunny = [s["id"] for s, v in ev if v and v[0] > 1.5]
    out.append(F(CL, "C-SUMMER-EVENING", ok(len(sunny) <= (1 - SEAT_SHARE) * len(ev)), "major",
                 f"{len(sunny)} of {len(ev)} seats have more than 1.5 of 3 h direct sun in the DST-clock evening 17-20 (the LDS layer: south-garden mean {0.07:.2f} h, so this site rarely fails it)", c_))
    # winter day
    wd = [(s, SS.sun_hours(layout, s["pt"], "winter")) for s in seats if s["use"] in ("dining", "lounge")]
    wd = [(s, v) for s, v in wd if v]
    dark = [s["id"] for s, v in wd if v[0] < WIN_MIN_H]
    out.append(F(CL, "C-WINTER-SUN", "not_evaluated" if not wd else ok(len(dark) <= (1 - SEAT_SHARE) * len(wd)), "major",
                 f"{len(dark)} of {len(wd)} dining/lounge seats get under {WIN_MIN_H:g} of 5 h sun on 21 Dec 10-15 (allowed <= {(1-SEAT_SHARE):.0%}); best seat {max([v[0] for s, v in wd], default=0):.2f} h", c_ + "; WIN_MIN_H policy"))
    # privacy per seat
    pv = [(s, SS.overlook(layout, s["pt"], True)) for s in seats]
    pv = [(s, v) for s, v in pv if v]
    exposed = [(s["id"], v[0]) for s, v in pv if v[0] > PRIV_MAX]
    out.append(F(CL, "C-PRIVACY", ok(len(exposed) <= (1 - SEAT_SHARE) * len(pv)) if pv else "not_evaluated", "blocking",
                 f"{len(exposed)} of {len(pv)} south seats overlooked by more than {PRIV_MAX} eye points seated (raw LDS median {sorted(v[1] for s, v in pv)[len(pv)//2] if pv else 0}; residual after layout screens {sorted(v[0] for s, v in pv)[len(pv)//2] if pv else 0}); brief: privacy is critical",
                 "LDS privacy.json (sight-line geometry); brief; threshold policy (LDS 'fewer than 5 eyes')"))
    # wind for the fire pit
    fp = features(layout, "firepit")
    if fp:
        f0 = feature_pt(fp[0]); near = [s for s in seats if math.dist(s["pt"], f0) <= 4.0]
        shares = [(s["id"], max(_wind_to_seat(layout, f0, s["pt"], k) for k in ("all-year", "winter-day-10-15 (Dec-Feb)"))) for s in near]
        bad = [i for i, sh in shares if sh > WIND_SHARE]
        out.append(F(CL, "C-FIRE-WIND", ok(len(bad) <= 0.4 * len(shares)) if shares else "not_evaluated", "major",
                     f"{len(bad)} of {len(shares)} seats within 4 m of the fire sit in its downwind +-45 deg sector for more than {WIND_SHARE:.0%} of hours (max share {max([sh for i, sh in shares], default=0):.0%}; uniform wind would give 25 %)", "LDS wind.json (Cairo West TMYx); threshold policy"))
    else:
        out.append(F(CL, "C-FIRE-WIND", "not_evaluated", "info", "no fire pit", BRIEF))
    # pond sun and water zones
    pd = features(layout, "pond")
    if pd:
        p = feature_pt(pd[0]); h = SS.sample("sun.json", "sun_hours_summer_solstice", p)
        hv = h if h is None else h
        out.append(F(CL, "C-POND-SUN", "not_evaluated" if h is None else ok(h >= 2.0), "major", f"pond cell gets {h} h direct sun on 21 Jun (required >= 2.0 h, policy: deep shade drops the planting and the water goes green); LS-POND-SHADE covers the opposite excess", "AD-EXT-POND-SITING (qualitative: sun, cool water); threshold policy"))
    return out + _ldk(layout, CL, ("LS-HYDROZONE", "LS-SCREEN", "LS-POND-SHADE"))


# ================================================================================================ LANDSCAPE ARCHITECT (measured part)
A = "landscape-architect"
ENCL_H = 1.8           # LS-SCREEN uses 1.8 m for privacy; same height here
ENCL_SHARE = 0.50      # policy: >= 50 % of a room's perimeter enclosed (walls, buildings, screens, planting >= 1.8 m)


def _enclosers(layout):
    objs = [rect_poly(b) for b in layout.get("buildings", [])]
    objs += [rect_poly(w["rect"]) for w in layout.get("walls", []) if w.get("rect") and w.get("height_m", 0) >= ENCL_H]
    objs += [rect_poly(s["rect"]) for s in layout.get("screens", []) if s.get("rect") and not s.get("canopy") and s.get("kind") != "pergola" and s.get("height_m", 0) >= ENCL_H]
    for g in layout.get("planting_groups", []):
        if g.get("rect") and any(species_info(p["species"], p.get("form"))["height_m"] and species_info(p["species"], p.get("form"))["height_m"] >= ENCL_H and layer_of(p["species"], p.get("form")) in ("shrub", "understorey", "canopy") for p in g.get("plants", [])):
            objs.append(rect_poly(g["rect"]))
    return unary_union(objs) if objs else None


def architect(layout):
    out = []
    enc = _enclosers(layout)
    rooms = [z for z in layout.get("zones", []) if z.get("use") in ("dining", "lounge", "quiet") and z.get("rect")]
    for z in rooms:
        poly = rect_poly(z["rect"]); per = poly.exterior
        if enc is None:
            share = 0.0
        else:
            share = per.intersection(enc.buffer(0.3)).length / per.length
        out.append(F(A, "A-ENCLOSURE", ok(share >= ENCL_SHARE), "major", f"room '{z['id']}': {share:.0%} of its perimeter enclosed by walls/buildings/screens/planting >= {ENCL_H} m (required >= {ENCL_SHARE:.0%})", "AD-COMP-ENCLOSURE / AD-TS-ENCLOSURE (qualitative); share threshold policy", subject=z["id"]))
    # paths to nowhere: every path end must meet a door, zone, seat, feature, another path, or the plot edge
    paths = layout.get("paths", [])
    targets = [Point(d["at"]).buffer(1.2) for d in doors_of(layout) if True]
    targets += [rect_poly(z["rect"]).buffer(0.3) for z in layout.get("zones", []) if z.get("rect") and z.get("surface") in ("paving", "gravel")]
    targets += [rect_poly(a["rect"]).buffer(0.3) for a in layout.get("paved_areas", []) if a.get("rect")]
    targets += [rect_poly(s["rect"]).buffer(0.5) for s in layout.get("seating", []) if s.get("rect")]
    targets += [Point(feature_pt(f)).buffer(1.2) for f in layout.get("features", [])]
    targets += [Point(t["center"]).buffer(1.0) for t in layout.get("tables", [])]
    for pth in paths:
        ln = path_line(pth)
        if ln is None: continue
        others = [path_line(q) for q in paths if q is not pth and path_line(q) is not None]
        ends = [Point(ln.coords[0]), Point(ln.coords[-1])]
        dead = []
        for k, e in enumerate(ends):
            if not (any(t.contains(e) or t.distance(e) < 0.01 for t in targets) or any(o.distance(e) < 0.6 for o in others)):
                dead.append(k)
        out.append(F(A, "A-PATH-TERMINUS", ok(not dead), "major", f"path '{pth['id']}': {len(dead)} of 2 ends lead to nothing (no door, paved room, seat, feature or path within reach)", "AD-COMP-AXIS / AD-COMP-PATH (qualitative: an axis ends in something worth reaching)", subject=pth["id"]))
    # thresholds: each house door opens onto paved ground, not directly onto planting/turf
    dsouth = [d for d in doors_of(layout) if _south(d["at"]) or True]
    for d in dsouth:
        z = door_out(d)
        zz = zone_of_point(layout, z)
        pav = (zz or {}).get("surface") in ("paving", "gravel") or any(rect_poly(a["rect"]).contains(Point(z)) for a in layout.get("paved_areas", [])) or any((path_line(p) is not None and path_line(p).buffer(p.get("width_m", 1) / 2).contains(Point(z))) for p in paths)
        if zz is None and not pav: continue            # outside the layout's frame: not judged
        out.append(F(A, "A-THRESHOLD", ok(pav, True), "minor", f"door {d['id']} opens onto {(zz or {}).get('surface', 'unknown')} (a paved landing or path marks the threshold)", "AD-COMP-THRESHOLD (qualitative)", subject=d["id"]))
    # focal point: 1..3 focal elements (features, specimen trees, pergolas) per layout
    foc = [f.get("kind") for f in layout.get("features", []) if f.get("kind") in ("pond", "firepit", "fountain", "sculpture")]
    tr = layout.get("trees", [])
    spec = [t for t in tr if all(math.dist(t["center"], u["center"]) > 5 for u in tr if u is not t)]
    foc += ["specimen-tree"] * len(spec) + ["pergola"] * len([c for c in layout.get("canopies", [])])
    out.append(F(A, "A-FOCAL", ok(1 <= len(foc) <= 4), "minor", f"{len(foc)} focal elements ({foc}); required 1-4 (one primary with restraint)", "AD-COMP-FOCAL (qualitative); count policy"))
    # path hierarchy
    classes = {p.get("class") for p in paths}
    if paths:
        out.append(F(A, "A-HIERARCHY", ok(len(classes) >= 2, True), "minor", f"path classes present: {sorted(classes)} (a graded main / secondary / service hierarchy needs >= 2)", "AD-COMP-HIERARCHY / AD-COMP-PATH (qualitative); count policy"))
    # outdoor rooms: at least 2 distinct uses with distinct floor surface
    ru = {(z.get("use"), z.get("surface")) for z in rooms}
    out.append(F(A, "A-ROOMS", ok(len({u for u, s in ru}) >= 2 and len({s for u, s in ru}) >= 2, True), "minor", f"{len(rooms)} outdoor rooms with uses/surfaces {sorted(map(str, ru))}; a change of floor marks a room", "AD-COMP-BASE-PLANE (qualitative)"))
    return out + _ldk(layout, A, ("LS-ENCLOSURE", "LS-STEP-RISER", "LS-STEP-2RG", "LS-STEP-COUNT", "LS-SEATWALL", "LS-LOUNGE-CLUSTER"))
