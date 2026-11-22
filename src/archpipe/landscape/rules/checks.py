"""Evaluate the quantitative landscape rules on a garden layout (schema: docs/lanes/LDK.md).

`evaluate(layout)` returns `contracts.CheckResult` records, one per rule per subject:
pass / fail / warn / not_evaluated. A rule whose input is missing reports `not_evaluated`,
never `pass`. Units: layout in metres (model frame), results in the unit named on the record.
"""
from __future__ import annotations

from collections.abc import Iterable

from shapely.geometry import Point, box
from shapely.ops import unary_union

from ...contracts import CheckResult
from ...rules import Measured
from .loader import RuleSet, load

LANE = "LDK"
_FIRE = ("firepit", "bbq")


def shape(item: dict):
    """Footprint of a layout item: `rect` [x0,y0,x1,y1] or `center` + `diameter_m`."""
    if "rect" in item:
        x0, y0, x1, y1 = item["rect"]
        return box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
    if "center" in item and "diameter_m" in item:
        return Point(*item["center"]).buffer(item["diameter_m"] / 2, 32)
    if "center" in item and "size_m" in item:
        (cx, cy), (w, d) = item["center"], item["size_m"]
        return box(cx - w / 2, cy - d / 2, cx + w / 2, cy + d / 2)
    return None


def validate_layout(layout: dict) -> None:
    if layout.get("schema") != "landscape-layout/1":
        raise ValueError("layout.schema must be 'landscape-layout/1'")
    for key in ("zones", "paths", "paved_areas", "steps", "tables", "seating", "planting_groups",
                "trees", "features", "boundary", "buildings", "obstacles"):
        if not isinstance(layout.get(key, []), list):
            raise ValueError(f"layout.{key} must be a list")
    for key in ("zones", "paths", "paved_areas", "steps", "tables", "seating", "planting_groups",
                "trees", "features", "boundary"):
        for it in layout.get(key, []):
            if "id" not in it:
                raise ValueError(f"layout.{key}: every item needs an id")


class _Ctx:
    def __init__(self, layout: dict, rs: RuleSet):
        self.L, self.rs, self.out = layout, rs, []

    def add(self, rule: str, status: str, subject: str, message: str, *, achieved=None, required=None,
            unit="", elements=()):
        sev = self.rs.severity[rule]
        if status == "fail" and sev == "warning":
            status = "warn"       # a warning-grade rule that is not met reports `warn`
        self.out.append(CheckResult(criterion=rule, lane=LANE, status=status, subject=subject,
                                    achieved=achieved, required=required, unit=unit, message=message,
                                    source_ids=self.rs.source_ids[rule], element_ids=tuple(elements)))

    def minimum(self, rule, subject, achieved, required, unit, what, elements=()):
        """achieved >= required, reported as achieved-versus-required."""
        m = Measured(achieved, required, unit)
        ok = achieved + 1e-9 >= required
        self.add(rule, "pass" if ok else "fail", subject, f"{what}: {m}", achieved=achieved,
                 required=required, unit=unit, elements=elements)

    def within(self, rule, subject, achieved, lo, hi, unit, what, elements=()):
        ok = lo - 1e-9 <= achieved <= hi + 1e-9
        req = lo if achieved < lo else hi
        self.add(rule, "pass" if ok else "fail", subject,
                 f"{what}: {achieved:g} {unit} achieved, {lo:g}-{hi:g} {unit} required", achieved=achieved,
                 required=req, unit=unit, elements=elements)

    def skip(self, rule, subject, why):
        self.add(rule, "not_evaluated", subject, f"not evaluated: {why}")


def _obstacles(L: dict, exclude: str = "") -> list:
    """Things a clear zone must keep free: buildings, planting beds, walls, seating, other features."""
    items = [shape({"rect": r}) for r in L.get("buildings", [])]
    for key in ("planting_groups", "obstacles", "seating", "tables", "features"):
        for it in L.get(key, []):
            if it.get("id") != exclude and shape(it) is not None:
                items.append(shape(it))
    return items


def _seats(L: dict) -> dict[str, int]:
    zones = {z["id"]: z for z in L.get("zones", [])}
    out: dict[str, int] = {}
    for key in ("tables", "seating"):
        for it in L.get(key, []):
            z = it.get("zone")
            if z in zones and zones[z].get("use") in ("dining", "lounge"):
                out[z] = out.get(z, 0) + int(it.get("seats", 0))
    return out


def evaluate(layout: dict, rs: RuleSet | None = None) -> list[CheckResult]:
    rs = rs or load()
    validate_layout(layout)
    c = _Ctx(layout, rs)
    P = rs.params
    L = layout

    # --- brief features (traceability) ---------------------------------------------------------
    have = {f.get("kind") for f in L.get("features", [])}
    alts = P["LS-BRIEF-FEATURES"]["alternatives"]
    for kind in P["LS-BRIEF-FEATURES"]["required_kinds"]:
        ok = bool(have & set(alts.get(kind, [kind])))
        c.add("LS-BRIEF-FEATURES", "pass" if ok else "fail", kind,
              f"brief feature {kind}: {'present' if ok else 'absent from the layout'}", achieved=int(ok), required=1,
              unit="count")

    # --- paths -------------------------------------------------------------------------------
    for p in L.get("paths", []):
        w = p["width_m"] * 1000
        if p.get("class") == "service":
            sp = P["LS-PATH-SERVICE"]
            if w + 1e-9 < sp["min_mm"]:
                c.add("LS-PATH-SERVICE", "fail", p["id"], f"service path clear width: {w:g} mm achieved, {sp['min_mm']} mm required",
                      achieved=w, required=sp["min_mm"], unit="mm", elements=[p["id"]])
            elif w < sp["recommended_mm"]:
                c.add("LS-PATH-SERVICE", "warn", p["id"], f"service path meets the {sp['min_mm']} mm wheelbarrow width but not the "
                      f"{sp['recommended_mm']} mm access-path width: {w:g} mm achieved", achieved=w,
                      required=sp["recommended_mm"], unit="mm", elements=[p["id"]])
            else:
                c.add("LS-PATH-SERVICE", "pass", p["id"], f"service path clear width: {w:g} mm achieved, {sp['recommended_mm']} mm recommended",
                      achieved=w, required=sp["recommended_mm"], unit="mm", elements=[p["id"]])
            continue
        rule = {"main": "LS-PATH-MAIN", "secondary": "LS-PATH-SECONDARY"}.get(p.get("class"))
        if rule is None:
            c.skip("LS-PATH-SECONDARY", p["id"], f"path class {p.get('class')!r} is not main, secondary or service")
            continue
        c.minimum(rule, p["id"], w, P[rule]["min_width_mm"], "mm", f"{p.get('class')} path clear width", [p["id"]])

    # --- steps ------------------------------------------------------------------------------
    for s in L.get("steps", []):
        r, g, n = s["riser_mm"], s["going_mm"], s["count"]
        P_r = P["LS-STEP-RISER"]
        ok = P_r["min_mm"] <= r <= P_r["max_mm"]
        if ok:
            c.add("LS-STEP-RISER", "pass", s["id"], f"riser {r:g} mm within {P_r['min_mm']}-{P_r['max_mm']} mm",
                  achieved=r, required=P_r["max_mm"], unit="mm", elements=[s["id"]])
        elif P_r["max_mm"] < r <= P_r["utilitarian_max_mm"]:
            c.add("LS-STEP-RISER", "warn", s["id"], f"riser {r:g} mm exceeds {P_r['max_mm']} mm; "
                  f"only acceptable for a utilitarian step (max {P_r['utilitarian_max_mm']})", achieved=r,
                  required=P_r["max_mm"], unit="mm", elements=[s["id"]])
        else:
            c.within("LS-STEP-RISER", s["id"], r, P_r["min_mm"], P_r["max_mm"], "mm", "riser", [s["id"]])
        rg = 2 * r + g
        c.within("LS-STEP-2RG", s["id"], rg, P["LS-STEP-2RG"]["min_mm"], P["LS-STEP-2RG"]["max_mm"], "mm",
                 f"2R+G (riser {r:g}, going {g:g})", [s["id"]])
        c.minimum("LS-STEP-COUNT", s["id"], n, P["LS-STEP-COUNT"]["min_steps"], "steps", "steps in the run", [s["id"]])
        if "width_mm" in s:
            c.minimum("LS-STEP-WIDTH", s["id"], s["width_mm"], P["LS-STEP-WIDTH"]["min_mm"], "mm", "stair width", [s["id"]])
        rise = n * r
        mx = P["LS-STEP-LANDING"]["max_rise_mm"]
        c.add("LS-STEP-LANDING", "pass" if rise <= mx else "fail", s["id"],
              f"rise without a landing: {rise:g} mm achieved, {mx} mm maximum", achieved=rise, required=mx,
              unit="mm", elements=[s["id"]])

    for w in L.get("seatwalls", []):
        h, wd = P["LS-SEATWALL"]["height_mm"], P["LS-SEATWALL"]["width_mm"]
        c.within("LS-SEATWALL", w["id"] + "/height", w["height_mm"], h[0], h[1], "mm", "seat wall height", [w["id"]])
        c.within("LS-SEATWALL", w["id"] + "/width", w["width_mm"], wd[0], wd[1], "mm", "seat wall width", [w["id"]])

    # --- dining and capacity ----------------------------------------------------------------
    seats = _seats(L)
    for z in L.get("zones", []):
        if z.get("use") != "dining":
            continue
        n = sum(int(t.get("seats", 0)) for t in L.get("tables", []) if t.get("zone") == z["id"])
        area = shape(z).area
        if n == 0:
            c.skip("LS-DINE-AREA", z["id"], "dining zone with no seated tables")
            continue
        c.minimum("LS-DINE-AREA", z["id"], round(area / n, 2), P["LS-DINE-AREA"]["min_m2_per_seat"], "m2",
                  f"dining zone area per seat ({area:.1f} m2 / {n} seats)", [z["id"]])
    for t in L.get("tables", []):
        others = _obstacles(L, exclude=t["id"])
        if not others:
            c.skip("LS-DINE-CLEAR", t["id"], "no obstacles in the layout to measure against")
            continue
        d = min(shape(t).distance(o) for o in others) * 1000
        c.minimum("LS-DINE-CLEAR", t["id"], round(d), P["LS-DINE-CLEAR"]["min_mm"], "mm",
                  "clear distance from table edge to nearest obstruction", [t["id"]])
    total = sum(seats.values())
    cap = P["LS-CAPACITY"]
    c.minimum("LS-CAPACITY", "south garden", total, cap["min_seats"], "seats",
              f"seats in dining and lounge zones (brief {cap['min_seats']}-{cap['max_seats']} people)")

    for z in L.get("zones", []):
        if z.get("use") == "lounge":
            n = sum(int(t.get("seats", 0)) for t in L.get("seating", []) if t.get("zone") == z["id"])
            if n:
                c.minimum("LS-LOUNGE-AREA", z["id"], round(shape(z).area / n, 2), P["LS-LOUNGE-AREA"]["min_m2_per_seat"], "m2",
                          f"lounge area per seat ({shape(z).area:.1f} m2 / {n} seats)", [z["id"]])
            else:
                c.skip("LS-LOUNGE-AREA", z["id"], "lounge zone with no seats")
            x0, y0, x1, y1 = shape(z).bounds
            c.minimum("LS-LOUNGE-CLUSTER", z["id"], round(min(x1 - x0, y1 - y0) * 1000), P["LS-LOUNGE-CLUSTER"]["min_diameter_mm"], "mm",
                      "shorter side of the lounge zone (a conversation cluster is about 3.66 m across)", [z["id"]])
    standing = [z for z in L.get("zones", []) if z.get("use") == "standing"]
    if not standing:
        c.skip("LS-STAND-AREA", "south garden", "no standing zone in the layout (brief: standing room for 10-20 people)")
    for z in standing:
        n = z.get("design_people")
        if not n:
            c.skip("LS-STAND-AREA", z["id"], "design_people not stated")
        else:
            c.minimum("LS-STAND-AREA", z["id"], round(shape(z).area / n, 2), P["LS-STAND-AREA"]["min_m2_per_person"], "m2",
                      f"standing area per person ({shape(z).area:.1f} m2 / {n} people)", [z["id"]])

    # --- fire pit / BBQ ---------------------------------------------------------------------
    for f in L.get("features", []):
        if f.get("kind") not in _FIRE:
            continue
        fp = shape(f)
        if fp is None:
            c.skip("LS-FIRE-CLEAR", f["id"], "feature has no footprint")
            continue
        others = _obstacles(L, exclude=f["id"])
        d = round(min((fp.distance(o) for o in others), default=1e9) * 1000)
        p = P["LS-FIRE-CLEAR"]
        shown = min(d, 99999)
        if d + 1e-9 < p["min_mm"]:
            c.add("LS-FIRE-CLEAR", "fail", f["id"], f"clear ground: {shown} mm achieved, {p['min_mm']} mm required",
                  achieved=shown, required=p["min_mm"], unit="mm", elements=[f["id"]])
        elif d < p["recommended_mm"]:
            c.add("LS-FIRE-CLEAR", "warn", f["id"], f"clear ground meets the {p['min_mm']} mm minimum but not the "
                  f"{p['recommended_mm']} mm recommended: {shown} mm achieved", achieved=shown,
                  required=p["recommended_mm"], unit="mm", elements=[f["id"]])
        else:
            c.add("LS-FIRE-CLEAR", "pass", f["id"], f"clear ground: {shown} mm achieved, {p['recommended_mm']} mm recommended",
                  achieved=shown, required=p["recommended_mm"], unit="mm", elements=[f["id"]])
        if f["kind"] == "firepit":
            ss = [shape(s) for s in L.get("seating", []) + L.get("tables", []) if shape(s) is not None]
            if ss:
                ds = round(min(fp.distance(s) for s in ss) * 1000)
                c.minimum("LS-FIRE-SEAT", f["id"], ds, P["LS-FIRE-SEAT"]["min_mm"], "mm",
                          "fire pit to nearest seat or table", [f["id"]])
            cover = f.get("cover")
            if cover and cover.get("load_rating_kN") is not None:
                need = P["LS-FIRE-COVER"]["min_kN"]
                got = cover["load_rating_kN"]
                c.add("LS-FIRE-COVER", "pass" if got >= need else "fail", f["id"],
                      f"flush cover declared load rating: {got:g} kN achieved, {need:g} kN required (BS EN 124 class A15, the "
                      "nearest published pedestrian-load class; the supplier must certify the rating for a heated cover)",
                      achieved=got, required=need, unit="kN", elements=[f["id"]])
            elif f.get("flush"):
                c.skip("LS-FIRE-COVER", f["id"], "flush fire pit with no declared cover load rating")
            if f.get("flush"):
                ov = f.get("overhead_clear_m")
                if ov is None:
                    c.skip("LS-FIRE-OVERHEAD", f["id"], "overhead_clear_m not stated (clear height above the burner; 99 for open sky)")
                else:
                    c.minimum("LS-FIRE-OVERHEAD", f["id"], round(ov * 1000), P["LS-FIRE-OVERHEAD"]["min_mm"], "mm",
                              "clear height above the fire to any combustible structure, tree or planting", [f["id"]])
        pc = f.get("product_clearance_mm")
        if pc is None:
            c.skip("LS-FIRE-PRODUCT", f["id"], "no product clearance entered (brief: product instructions govern)")
        else:
            ok = d >= pc
            c.add("LS-FIRE-PRODUCT", "pass" if ok else "fail", f["id"],
                  f"clearance to facade/planting/obstruction: {shown} mm achieved, {pc} mm required (product instructions)",
                  achieved=shown, required=pc, unit="mm", elements=[f["id"]])

    for f in L.get("features", []):
        if f.get("kind") not in _FIRE or shape(f) is None:
            continue
        fp = shape(f)
        comb = [shape({"rect": r}) for r in L.get("buildings", [])]
        for key in ("planting_groups", "obstacles"):
            comb += [shape(it) for it in L.get(key, []) if shape(it) is not None]
        comb += [Point(*t["center"]).buffer(t.get("mature_spread_m", 0) / 2, 32) for t in L.get("trees", []) if "center" in t]
        if not comb:
            c.skip("LS-FIRE-STRUCT", f["id"], "no structures or planting in the layout to measure against")
            continue
        d = round(min(fp.distance(o) for o in comb) * 1000)
        p = P["LS-FIRE-STRUCT"]
        need = p["min_mm"]
        why = "house, fence, structure or planting (Calgary Fire Department)"
        if f.get("fuel") == "wood":
            need, why = p["wood_mm"], "structure or combustible material for a wood fire (International Fire Code 307.4)"
        c.add("LS-FIRE-STRUCT", "pass" if d >= need else "fail", f["id"],
              f"distance to {why}: {d} mm achieved, {need} mm required (the product instructions govern; this is the published floor)",
              achieved=d, required=need, unit="mm", elements=[f["id"]])

    # --- pond -------------------------------------------------------------------------------
    for f in L.get("features", []):
        if f.get("kind") != "pond":
            continue
        edge, fb = f.get("edge"), f.get("freeboard_mm")
        need = {"hard": P["LS-POND-FREEBOARD"]["hard_edge_mm"], "soft": P["LS-POND-FREEBOARD"]["soft_edge_mm"]}.get(edge)
        if need is None or fb is None:
            c.skip("LS-POND-FREEBOARD", f["id"], "edge type (hard|soft) or freeboard_mm missing")
        else:
            c.minimum("LS-POND-FREEBOARD", f["id"], fb, need, "mm", f"{edge}-edge freeboard", [f["id"]])
        if f.get("flush"):
            m = f.get("margin_slope_back_mm")
            if m is None:
                c.skip("LS-POND-FLUSH-MARGIN", f["id"], "margin_slope_back_mm not stated for a flush pond")
            else:
                c.minimum("LS-POND-FLUSH-MARGIN", f["id"], m, P["LS-POND-FLUSH-MARGIN"]["min_mm"], "mm",
                          "paving sloped back toward the pond from the clearance", [f["id"]])

    for f in L.get("features", []):
        if f.get("kind") != "pond":
            continue
        if f.get("depth_mm") is None:
            c.skip("LS-POND-DEPTH", f["id"], "depth_mm (deepest section) not stated")
        else:
            c.minimum("LS-POND-DEPTH", f["id"], f["depth_mm"], P["LS-POND-DEPTH"]["min_mm"], "mm", "deepest section of the pond", [f["id"]])
        area = shape(f).area if shape(f) is not None else None
        if f.get("koi_count") is None or f.get("koi_adult_length_cm") is None or not area:
            c.skip("LS-POND-STOCK", f["id"], "koi_count, koi_adult_length_cm or the pond footprint is missing")
        else:
            inches = f["koi_count"] * f["koi_adult_length_cm"] / 2.54
            lim = P["LS-POND-STOCK"]["inches_per_m2_aerated" if f.get("aerated") else "inches_per_m2_unaerated"]
            got = round(inches / area, 1)
            c.add("LS-POND-STOCK", "pass" if got <= lim else "fail", f["id"],
                  f"fish length per m2 of surface: {got} in/m2 achieved, {lim} in/m2 allowed "
                  f"({'aerated' if f.get('aerated') else 'unaerated'}; the source figure is for 12-inch fish)",
                  achieved=got, required=lim, unit="in/m2", elements=[f["id"]])
        sh = f.get("surface_shade_pct")
        if sh is None:
            c.skip("LS-POND-SHADE", f["id"], "surface_shade_pct not stated")
        else:
            c.within("LS-POND-SHADE", f["id"], sh, P["LS-POND-SHADE"]["min_pct"], P["LS-POND-SHADE"]["max_pct"], "%",
                     "water surface shaded by plants", [f["id"]])

    # --- flush features: child protection, shore slope, lip, openings, edge lighting --------------
    for f in L.get("features", []):
        if f.get("kind") not in ("pond", "firepit") or not f.get("flush"):
            continue
        sid = f["id"]
        if f["kind"] == "pond":
            prot = f.get("child_protection")
            G = P["LS-POND-GUARD"]
            if prot is None:
                c.add("LS-POND-GUARD", "fail", sid, "flush pond with no child protection declared (RoSPA: rigid grille or a 1.1 m fence; "
                      "the client may waive it with a reason)", achieved=0, required=1, unit="count", elements=[sid])
            elif prot == "fence" and (f.get("fence_height_mm") or 0) < G["min_fence_mm"]:
                c.add("LS-POND-GUARD", "fail", sid, f"fence height: {f.get('fence_height_mm') or 0} mm achieved, {G['min_fence_mm']} mm required",
                      achieved=f.get("fence_height_mm") or 0, required=G["min_fence_mm"], unit="mm", elements=[sid])
            elif prot in G["accepted"]:
                c.add("LS-POND-GUARD", "pass", sid, f"child protection declared: {prot} (no published load figure: GAP-POND-GRILLE-LOAD)",
                      achieved=1, required=1, unit="count", elements=[sid])
            else:
                c.add("LS-POND-GUARD", "fail", sid, f"child protection {prot!r} is not one of {G['accepted']}", achieved=0, required=1,
                      unit="count", elements=[sid])
            run = f.get("edge_slope_run_per_rise")
            if run is None:
                c.skip("LS-POND-EDGE-SLOPE", sid, "edge_slope_run_per_rise not stated")
            else:
                c.minimum("LS-POND-EDGE-SLOPE", sid, run, P["LS-POND-EDGE-SLOPE"]["min_run_per_rise"], "run:rise",
                          "shore slope as run per unit rise (4 = 1:4)", [sid])
        cov = f.get("cover") or ({"lip_mm": f["lip_mm"]} if "lip_mm" in f else None)
        if cov:
            if cov.get("lip_mm") is not None:
                v, b = cov["lip_mm"], P["LS-FLUSH-LIP"]
                if v <= b["max_vertical_mm"]:
                    c.add("LS-FLUSH-LIP", "pass", sid, f"vertical lip: {v:g} mm achieved, {b['max_vertical_mm']} mm allowed", achieved=v,
                          required=b["max_vertical_mm"], unit="mm", elements=[sid])
                elif v <= b["max_bevel_mm"] and cov.get("bevelled"):
                    c.add("LS-FLUSH-LIP", "pass", sid, f"lip {v:g} mm is bevelled (allowed up to {b['max_bevel_mm']} mm)", achieved=v,
                          required=b["max_bevel_mm"], unit="mm", elements=[sid])
                else:
                    c.add("LS-FLUSH-LIP", "fail", sid, f"lip {v:g} mm: {b['max_vertical_mm']} mm vertical or {b['max_bevel_mm']} mm if bevelled",
                          achieved=v, required=b["max_vertical_mm"] if v <= b["max_vertical_mm"] or not cov.get("bevelled") else b["max_bevel_mm"],
                          unit="mm", elements=[sid])
            else:
                c.skip("LS-FLUSH-LIP", sid, "cover.lip_mm not stated")
            if cov.get("max_opening_mm") is not None:
                ok = cov["max_opening_mm"] <= P["LS-FLUSH-OPENING"]["max_mm"]
                c.add("LS-FLUSH-OPENING", "pass" if ok else "fail", sid, f"largest opening in the cover: {cov['max_opening_mm']:g} mm achieved, "
                      f"{P['LS-FLUSH-OPENING']['max_mm']} mm allowed", achieved=cov["max_opening_mm"],
                      required=P["LS-FLUSH-OPENING"]["max_mm"], unit="mm", elements=[sid])
            else:
                c.skip("LS-FLUSH-OPENING", sid, "cover.max_opening_mm not stated")
        lx = f.get("edge_lux")
        if lx is None:
            c.skip("LS-POND-EDGE-LIGHT", sid, "edge_lux not stated (the lighting lane supplies the night level at the edge)")
        else:
            c.minimum("LS-POND-EDGE-LIGHT", sid, lx, P["LS-POND-EDGE-LIGHT"]["min_lx"], "lx",
                      f"horizontal illuminance at the edge (IES recommends {P['LS-POND-EDGE-LIGHT']['recommended_lx']} lx over age 65)", [sid])

    # --- soil depth over structure ----------------------------------------------------------
    mins = P["LS-SOIL-DEPTH"]["min_mm"]
    for g in L.get("planting_groups", []) + L.get("trees", []):
        if not g.get("over_structure"):
            continue
        forms = {g["form"]} if "form" in g else {p.get("form") for p in g.get("plants", [])}
        depth = g.get("soil_depth_mm")
        if not any(forms):
            c.skip("LS-SOIL-DEPTH", g["id"], "plant form (ground_cover|shrub|small_tree|large_tree) not known")
        for form in sorted(f for f in forms if f):
            if form not in mins:
                c.skip("LS-SOIL-DEPTH", g["id"], f"unknown plant form {form!r}")
            elif depth is None:
                c.skip("LS-SOIL-DEPTH", f"{g['id']}/{form}", "soil_depth_mm not stated for planting over structure")
            else:
                c.minimum("LS-SOIL-DEPTH", f"{g['id']}/{form}", depth, mins[form], "mm", f"soil depth for {form}", [g["id"]])

    # --- slopes -----------------------------------------------------------------------------
    S = P["LS-SLOPE"]
    for a in L.get("paved_areas", []):
        if a.get("slope_pct") is None:
            c.skip("LS-SLOPE", a["id"], "paving fall not stated")
            continue
        key = "terrace_concrete_pct" if a.get("material") == "concrete" else "terrace_unit_pct"
        c.within("LS-SLOPE", a["id"], a["slope_pct"], *S[key], "%", f"fall of {a.get('material')} terrace", [a["id"]])
    for p in L.get("paths", []):
        cs, ls = p.get("cross_slope_pct"), p.get("long_slope_pct")
        if cs is not None:
            hi = S["main_path_cross_max_pct"] if p.get("class") == "main" else S["path_cross_pct"][1]
            c.within("LS-SLOPE", p["id"] + "/cross", cs, S["path_cross_pct"][0], hi, "%", "path cross fall", [p["id"]])
        if ls is not None:
            c.within("LS-SLOPE", p["id"] + "/long", ls, 0.0, S["path_long_pct"][1], "%", "path longitudinal slope", [p["id"]])
    for s in L.get("steps", []):
        if s.get("tread_pitch_pct") is not None:
            c.within("LS-SLOPE", s["id"] + "/tread", s["tread_pitch_pct"], 1.0, 3.0, "%", "tread pitch (source: 2 %)", [s["id"]])
    for z in L.get("zones", []):
        if z.get("surface") == "lawn" and z.get("slope_pct") is not None:
            c.within("LS-SLOPE", z["id"], z["slope_pct"], *S["lawn_recreation_pct"], "%", "recreation lawn fall", [z["id"]])

    # --- hydrozoning ------------------------------------------------------------------------
    for g in L.get("planting_groups", []):
        needs = {p.get("water_need") for p in g.get("plants", [])}
        if None in needs or not needs:
            c.skip("LS-HYDROZONE", g["id"], "a plant has no water_need")
            continue
        n = len(needs)
        mx = P["LS-HYDROZONE"]["max_classes"]
        c.add("LS-HYDROZONE", "pass" if n <= mx else "fail", g["id"],
              f"water-need classes in the group: {n} achieved, {mx} allowed ({', '.join(sorted(needs))})",
              achieved=n, required=mx, unit="classes", elements=[g["id"]])

    # --- enclosure --------------------------------------------------------------------------
    for z in L.get("zones", []):
        if z.get("use") not in ("dining", "lounge", "quiet"):
            continue
        h = z.get("enclosure_height_m")
        if h is None:
            c.skip("LS-ENCLOSURE", z["id"], "enclosure_height_m not stated")
            continue
        x0, y0, x1, y1 = shape(z).bounds
        width = min(x1 - x0, y1 - y0)
        c.minimum("LS-ENCLOSURE", z["id"], round(h / width, 3), P["LS-ENCLOSURE"]["min_ratio"], "ratio",
                  f"enclosure height {h:g} m / room width {width:.2f} m", [z["id"]])

    # --- screening --------------------------------------------------------------------------
    for b in L.get("boundary", []):
        if b.get("side") != "neighbour":
            continue
        need = P["LS-SCREEN"]["min_m"]
        h = b["height_m"]
        if h + 1e-9 < need:
            c.add("LS-SCREEN", "fail", b["id"], f"boundary height: {h:.2f} m achieved, {need:.2f} m required",
                  achieved=h, required=need, unit="m", elements=[b["id"]])
        elif b.get("kind") == "hedge":
            c.add("LS-SCREEN", "warn", b["id"], f"hedge at {h:.2f} m meets the height but the source speaks of an "
                  "impermeable wall or fence; hedge density is a GAP (GAP-SCREEN-PLANT)", achieved=h, required=need,
                  unit="m", elements=[b["id"]])
        else:
            c.add("LS-SCREEN", "pass", b["id"], f"boundary height: {h:.2f} m achieved, {need:.2f} m required",
                  achieved=h, required=need, unit="m", elements=[b["id"]])

    # --- root zone --------------------------------------------------------------------------
    hard = [shape(a) for a in L.get("paved_areas", [])] + [shape({"rect": r}) for r in L.get("buildings", [])]
    hard = [h for h in hard if h is not None]
    turf = [z for z in L.get("zones", []) if z.get("surface") == "artificial-turf"]
    for t in L.get("trees", []):
        spread = t.get("mature_spread_m")
        if spread is None:
            c.skip("LS-ROOTZONE", t["id"], "mature_spread_m not stated")
            continue
        zone = Point(*t["center"]).buffer(spread / 2, 32)
        covered = unary_union(hard).intersection(zone).area if hard else 0.0
        if covered > 1e-6:
            c.add("LS-ROOTZONE", "fail", t["id"], f"paving/building covers {covered:.1f} m2 of the {zone.area:.1f} m2 "
                  f"dripline zone (mature spread {spread:g} m)", achieved=round(covered, 2), required=0.0, unit="m2",
                  elements=[t["id"]])
        else:
            c.add("LS-ROOTZONE", "pass", t["id"], f"no paving or building inside the mature dripline zone "
                  f"({zone.area:.1f} m2, spread {spread:g} m)", achieved=0.0, required=0.0, unit="m2", elements=[t["id"]])
        for z in turf:
            if shape(z).intersects(zone):
                c.skip("LS-ROOTZONE", f"{t['id']}/{z['id']}", "artificial turf over the root zone: its air/water "
                       "permeability is UNVERIFIED")
    # --- tree distance to buildings (NHBC zone of influence) --------------------------------
    T = P["LS-TREE-BUILDING"]
    bs = [shape({"rect": r}) for r in L.get("buildings", [])]
    for t in L.get("trees", []):
        h = t.get("mature_height_m")
        if h is None or "center" not in t or not bs:
            c.skip("LS-TREE-BUILDING", t["id"], "mature_height_m, the tree position or a building is missing")
            continue
        demand = t.get("water_demand") or T["default_water_demand"]
        need = round(T["factor"][demand] * h, 2)
        d = round(min(Point(*t["center"]).distance(b) for b in bs), 2)
        assumed = "" if t.get("water_demand") else " (water demand unknown: NHBC says assume high)"
        c.add("LS-TREE-BUILDING", "pass" if d >= need else "fail", t["id"],
              f"trunk to building: {d:g} m achieved, {need:g} m required ({T['factor'][demand]} x {h:g} m mature height, "
              f"{demand} water demand{assumed}); UK clay guidance, the site soil test governs", achieved=d, required=need,
              unit="m", elements=[t["id"]])

    # --- hedge spacing, herb and fruit sun -------------------------------------------------
    for b in L.get("boundary", []):
        if b.get("kind") == "hedge":
            if b.get("row_spacing_mm") is None:
                c.skip("LS-HEDGE-SPACING", b["id"], "row_spacing_mm not stated")
            else:
                c.within("LS-HEDGE-SPACING", b["id"], b["row_spacing_mm"], P["LS-HEDGE-SPACING"]["min_mm"],
                         P["LS-HEDGE-SPACING"]["max_mm"], "mm", "in-row hedge plant spacing", [b["id"]])
    for f in L.get("features", []):
        if f.get("kind") in ("herb_bed", "fruit_tree"):
            hrs = f.get("midsummer_sun_hours")
            if hrs is None:
                c.skip("LS-HERB-SUN", f["id"], "midsummer_sun_hours not stated (the LDS sun study supplies it)")
            else:
                c.minimum("LS-HERB-SUN", f["id"], hrs, P["LS-HERB-SUN"]["min_hours"], "h", "direct midsummer sun on the bed", [f["id"]])
    return c.out


def summarize(results: Iterable[CheckResult]) -> dict:
    out: dict = {}
    for r in results:
        out.setdefault(r.criterion, {"pass": 0, "fail": 0, "warn": 0, "not_evaluated": 0})[r.status] += 1
    return out
