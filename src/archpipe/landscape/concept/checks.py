"""LDG's own checks, on top of the LDK `evaluate`: the A2 items LDK does not hold (privacy, shade, spread vs space,
toxicity near seats, hydrozone with trees, geometry sanity). Thresholds are POLICY cards (ours, stated; no published
figure) in POLICY below; every pass/fail cites one.
"""
from __future__ import annotations

import math

from shapely.geometry import Point, box

from ...contracts import CheckResult
from . import site as S
from .geom import circle, rbox
from .planting import layer_of, spread_mid

LANE = "LDG"
POLICY = {
    "LDG-POL-PRIVACY": ("Remaining overlooking in a seated room at most 30 % of the existing overlooking (25 % for the quiet corner)",
                        "brief: privacy is critical; no published figure (LDK GAP-OVERLOOK-ABOVE); ours"),
    "LDG-POL-SHADE": ("Dining room: at least 50 % of its cells under cover (pergola or evergreen canopy); evening cells sun-free at least 90 %",
                      "brief: shade over sun, summer nights; the percentage is the client's (LDK GAP-SHADE-TARGET); ours"),
    "LDG-POL-SPREAD": ("A plant's mature-spread circle may overhang its bed by 0.15 m and must not reach a seat, the door path or the fire-pit clearance",
                       "mature spread against space (LANDSCAPE-METHOD A2); ours"),
    "LDG-POL-TOXIC": ("No toxic species (LDL toxicity_people toxic or highly_toxic) within 2 m of a seat or a herb bed",
                      "Time-Saver Standards 550-3 (poisonous plants out of reach); the 2 m is ours"),
    "LDG-POL-HYDRO": ("One water-need class per planting bed, trees in the bed included", "Time-Saver 750-11 via LS-HYDROZONE; trees added by us"),
    "LDG-POL-GEOM": ("No two elements overlap and all lie inside the zone", "geometry sanity; ours"),
    "LDG-POL-TREEBLDG": ("NHBC trunk-to-building distance (LS-TREE-BUILDING) is hard here: A2 lists tree-to-foundation distance", "A2; NHBC 2024 4.2 via LDK"),
}


def _r(rule, status, subject, msg, ach=None, req=None, unit="", ids=()):
    return CheckResult(criterion=rule, lane=LANE, status=status, subject=subject, achieved=ach, required=req, unit=unit, message=msg,
                       source_ids=(rule.replace("LDG-", "LDG-POL-", 1) if rule.startswith("LDG-") and not rule.startswith("LDG-POL") else rule,),
                       element_ids=tuple(ids))


def _pol(name):
    return {"PRIV": "LDG-POL-PRIVACY", "SHADE": "LDG-POL-SHADE", "SPREAD": "LDG-POL-SPREAD", "TOXIC": "LDG-POL-TOXIC",
            "HYDRO": "LDG-POL-HYDRO", "GEOM": "LDG-POL-GEOM", "TREEBLDG": "LDG-POL-TREEBLDG"}[name]


def mk(rule_key, status, subject, msg, ach=None, req=None, unit="", ids=()):
    return CheckResult(criterion=f"LDG-{rule_key}", lane=LANE, status=status, subject=subject, achieved=ach, required=req, unit=unit,
                       message=msg, source_ids=(_pol(rule_key if rule_key in ("PRIV", "SHADE", "SPREAD", "TOXIC", "HYDRO", "GEOM", "TREEBLDG") else "GEOM"),),
                       element_ids=tuple(ids))


def canopy_rects(trees, pool):
    """Evergreen canopy approximated by the inscribed square of the (min-spread) dripline circle, in MODEL frame."""
    out = []
    for t in trees:
        sp = pool[t["species"]]
        if sp.habit == "evergreen" and (sp.s_min or sp.s_max):
            r = (sp.s_min or sp.s_max) / 2 / math.sqrt(2)
            x, y = S.SX0 + t["center"][0], S.SY0 + t["center"][1]
            out.append([x - r, y - r, x + r, y + r])
    return out


def south_checks(c, plan, pool) -> list[CheckResult]:
    from .layout import M
    from .south import A, B, PIT_D
    res = []
    variant = c["variant"]
    excl = S.SISTER if variant == "open" else ()
    scr = (S.FLOOR_Z + c["screen_top_h"]) if c["screen_top_h"] else None
    cover = [M(r) for r in c["cover"]] + canopy_rects(plan["trees"] if plan else c["trees"], pool)
    rooms = {"dining": (c["dining"], 0.30), "lounge": (c["lounge"], 0.30), "quiet": (c["quiet"]["rect"], 0.25)}
    for name, (rect, lim) in rooms.items():
        base = S.eyes_total(M(rect), "seated", exclude=excl)
        rem = S.eyes_total(M(rect), "seated", cover_rects=cover, screen_top_z=scr, exclude=excl)
        share = rem / base if base else 0.0
        mk_status = "pass" if share <= lim + 1e-9 else "fail"
        res.append(mk("PRIV", mk_status, name, f"{name}: {rem:.1f} eye points still see a seated person against {base:.1f} today "
                      f"({share:.0%} remaining, {lim:.0%} allowed)" + ("; sister plot groups left out (client's open option)" if excl else ""),
                      round(share, 3), lim, "share"))
    # shade: evening (DST clock) sun-free share, and dining cover share
    ev = {}
    for name, (rect, _) in rooms.items():
        v = S.values("sun", "summer_evening_17_20_dst_clock", M(rect))
        ev[name] = sum(1 for x in v if x <= 0.25) / len(v) if v else 0.0
    for name, share in ev.items():
        res.append(mk("SHADE", "pass" if share >= 0.9 else "fail", f"{name}/evening", f"{name}: {share:.0%} of cells sun-free 17-20 h (DST clock), 90 % required",
                      round(share, 3), 0.9, "share"))
    d = rbox(c["dining"])
    covered = d.intersection(__import__("shapely.ops", fromlist=["unary_union"]).unary_union([rbox(r) for r in [x for x in c["cover"]]])).area / d.area if c["cover"] else 0.0
    res.append(mk("SHADE", "pass" if covered >= 0.5 else "fail", "dining/cover", f"dining: {covered:.0%} of the room under cover, 50 % required",
                  round(covered, 3), 0.5, "share"))
    # geometry sanity
    items = {"table": rbox([c["table"]["center"][0] - c["table"]["size"][0] / 2, c["table"]["center"][1] - c["table"]["size"][1] / 2,
                            c["table"]["center"][0] + c["table"]["size"][0] / 2, c["table"]["center"][1] + c["table"]["size"][1] / 2]),
             "pit": circle(c["pit"]["center"], PIT_D), "bbq": rbox(c["bbq"]), "quiet-bench": rbox(c["quiet"]["bench"])}
    for i, s in enumerate(c["seats"]):
        items[f"seat-{i}"] = rbox(s["rect"])
    for b in c["beds"]:
        items[b["id"]] = rbox(b["rect"])
    names = list(items)
    bad = [(a, b) for i, a in enumerate(names) for b in names[i + 1:] if items[a].intersection(items[b]).area > 5e-3]
    inside = all(box(-1e-6, -1e-6, A + 1e-6, B + 1e-6).contains(g) for g in items.values())
    res.append(mk("GEOM", "pass" if not bad and inside else "fail", "south", "elements do not overlap and lie inside the garden" if not bad and inside
                  else f"overlaps {bad[:3]}, inside={inside}", len(bad), 0, "overlaps"))
    # tree canopy (sourced minimum spread: a trained tree) stays inside the garden (0.3 m over the east/rear fences, none over the house and the open sister line) and off the fire pit
    allow = box(0, 0, A + 0.3, B + 0.3)
    for t in (plan["trees"] if plan else c["trees"]):
        sp = pool[t["species"]]
        sm = sp.s_min or sp.s_max
        if not sm:
            continue
        circ = Point(*t["center"]).buffer(sm / 2, 24)
        out_of = circ.difference(allow).area
        near_pit = circ.distance(circle(c["pit"]["center"], PIT_D)) < 0.9
        ok = out_of < 1e-6 and not near_pit
        res.append(mk("SPREAD", "pass" if ok else "fail", f"tree-{t['species']}",
                      f"{sp.name}: canopy radius {sm/2:.2f} m (sourced minimum spread {sm} m); {out_of:.1f} m2 outside the garden"
                      + ("; canopy within 0.9 m of the fire pit" if near_pit else ""), round(out_of, 2), 0, "m2"))
    if plan:
        res += planting_checks("south", c, plan, pool)
    return res


def planting_checks(zone, c, plan, pool, reserved=None, seats=(), herb_rects=()) -> list[CheckResult]:
    """Spread vs space, toxicity near seats, hydrozone with trees (local frame for south; model frame elsewhere)."""
    res = []
    reserved = reserved if reserved is not None else []
    enc = 0
    tox = []
    for bid, p in plan["beds"].items():
        for inst in p["instances"]:
            sp = pool[inst["species"]]
            if inst["layer"] in ("climber", "aquatic"):
                continue
            r = max(0.0, spread_mid(sp) / 2 - 0.15)
            for xy in inst["positions"]:
                circ = Point(*xy).buffer(r, 8)
                if any(circ.intersects(g) for g in reserved):
                    enc += 1
        for inst in p["instances"]:
            sp = pool[inst["species"]]
            if sp.is_toxic:
                for xy in inst["positions"]:
                    if any(Point(*xy).distance(g) < 2.0 for g in list(seats) + list(herb_rects)):
                        tox.append(inst["species"])
    res.append(mk("SPREAD", "pass" if enc == 0 else "fail", zone, f"{enc} plant(s) whose mature spread (less the 0.15 m overhang) reaches a seat, the door path or the fire clearance",
                  enc, 0, "plants"))
    res.append(mk("TOXIC", "pass" if not tox else "fail", zone, "no toxic species within 2 m of a seat or herb bed" if not tox else f"toxic within 2 m: {sorted(set(tox))}",
                  len(tox), 0, "plants"))
    for bid, p in plan["beds"].items():
        if p["hydrozone"] == "unknown":
            res.append(mk("HYDRO", "not_evaluated", bid, f"{bid}: a species' water need is a GAP in LDL; not evaluated", None, 1, "classes"))
            continue
        cls = {p["hydrozone"]} if p["hydrozone"] else set()
        for t in plan.get("trees", []):
            if t.get("bed") == bid and pool[t["species"]].water:
                cls.add(pool[t["species"]].water)
        res.append(mk("HYDRO", "pass" if len(cls) <= 1 else "fail", bid, f"{bid}: water classes {sorted(cls)} (1 allowed)", len(cls), 1, "classes"))
    return res


HARD_WARN = {"LS-TREE-BUILDING"}      # warning-grade in LDK, hard here (A2 lists tree-to-foundation distance)


def hard_fails(results) -> list[CheckResult]:
    out = []
    for r in results:
        if r.status == "fail" or (r.status == "warn" and r.criterion in HARD_WARN):
            out.append(r)
    return out
