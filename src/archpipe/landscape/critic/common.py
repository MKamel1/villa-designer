"""Shared helpers for the landscape critics: layout geometry, plant lookup, site layers.

Frame: model metres; client NORTH (street) = model -x, east = +y, south = +x. A layout is `landscape-layout/1`
(docs/lanes/LDK.md) plus the optional LDC keys documented in docs/lanes/LDC.md (`walls`, `screens`, `canopies`,
`uses`, `doors`, path `polyline`, plant `at`/`count`). Unknown keys are ignored by the LDK rules.
"""
from __future__ import annotations

import functools
import json
import math
from dataclasses import dataclass, field, asdict
from pathlib import Path

from shapely.geometry import LineString, Point, box

ROOT = Path(__file__).resolve().parents[4]
KNOW = ROOT / "knowledge/landscape"
FORM_SPREAD = {"large_tree": 5.0, "small_tree": 3.0, "shrub": 1.2, "ground_cover": 0.5}
LAYER_ORDER = ("canopy", "understorey", "shrub", "ground")


@dataclass
class Finding:
    """One critic finding. `status`: pass | fail | warn | not_evaluated. `calibrated` is filled by the
    calibration table (knowledge/landscape/critic/calibration.json), never by the check itself."""
    critic: str
    criterion: str
    status: str
    severity: str           # blocking | major | minor | info
    evidence: str           # achieved vs required, with numbers
    source: str             # rule / source it cites
    kind: str = "computed"  # computed | vlm
    subject: str = ""
    calibrated: bool = False
    extra: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


def rect_poly(r):
    x0, y0, x1, y1 = r
    return box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


@functools.lru_cache(maxsize=1)
def plants_db() -> dict:
    p = json.loads((KNOW / "plants/plants.json").read_text(encoding="utf-8"))
    return {s["slug"]: s for s in p["species"]}


def slug(name: str) -> str:
    return "_".join(name.lower().replace("×", "x").split()[:2])


def _val(rec, attr):
    a = rec["attributes"].get(attr, {})
    return a.get("value") if a.get("status") == "SOURCED" else None


def species_info(name: str, form: str | None = None) -> dict:
    """Facts for a species used by the critics. Absent data stays None (never guessed) except the drawing spread."""
    rec = plants_db().get(slug(name))
    out = {"species": name, "known": rec is not None, "layers": [], "spread_m": None, "height_m": None, "water": None,
           "sun": None, "tox_people": None, "tox_fish": None, "months": None, "viability": None, "pond": False}
    if rec:
        sp, ht = _val(rec, "spread_m"), _val(rec, "height_m")
        out.update(layers=rec["layers"], viability=rec["site_viability"]["verdict"], pond=rec["pond_relevant"])
        if sp: out["spread_m"] = (sp["min"] + sp["max"]) / 2
        if ht: out["height_m"] = (ht["min"] + ht["max"]) / 2
        w = _val(rec, "water"); out["water"] = w and w["hydrozone"]
        s = _val(rec, "sun"); out["sun"] = s and s["classes"]
        t = _val(rec, "toxicity_people"); out["tox_people"] = t and t["class"]
        t = _val(rec, "toxicity_fish"); out["tox_fish"] = t and t["class"]
        f = _val(rec, "flowering"); out["months"] = f and (f["months"] or None)
    out["draw_spread_m"] = out["spread_m"] or FORM_SPREAD.get(form or "", 1.0)
    return out


def layer_of(species: str, form: str | None) -> str:
    """canopy | understorey | shrub | ground (our classification, from the LDL layer tags then the form)."""
    info = species_info(species, form)
    L = set(info["layers"])
    if form in ("large_tree",) or "canopy_tree" in L or "palm" in L and (info["height_m"] or 0) > 4: return "canopy"
    if form == "small_tree" or L & {"small_fruit_tree"}: return "understorey"
    if form == "ground_cover" or L & {"groundcover_lawn", "perennial", "grass"} and not L & {"screen_hedge"}: return "ground"
    return "shrub"


def zone_of_point(layout, pt):
    p = Point(pt)
    for z in layout.get("zones", []):
        if z.get("rect") and rect_poly(z["rect"]).contains(p): return z
    return None


def plant_positions(layout) -> list[dict]:
    """Every plant with a position: trees at their centre; group members at `at` or packed deterministically in
    the group rect (one strip per species, in order of first appearance, weighted by count x spread^2).
    Returns [{species, form, at, spread, group, layer}]."""
    out = []
    for t in layout.get("trees", []):
        out.append({"species": t["species"], "form": t.get("form", "large_tree"), "at": tuple(t["center"]),
                    "spread": t.get("mature_spread_m") or species_info(t["species"], t.get("form"))["draw_spread_m"],
                    "group": t["id"], "layer": layer_of(t["species"], t.get("form", "large_tree"))})
    for g in layout.get("planting_groups", []):
        members = []
        for p in g.get("plants", []):
            members += [p] * int(p.get("count", 1))
        if not members or not g.get("rect"): continue
        x0, y0, x1, y1 = g["rect"]
        order = list(dict.fromkeys(m["species"] for m in members))
        fixed = [m for m in members if m.get("at")]
        auto = [m for m in members if not m.get("at")]
        for m in fixed:
            out.append({"species": m["species"], "form": m.get("form"), "at": tuple(m["at"]),
                        "spread": m.get("spread_m") or species_info(m["species"], m.get("form"))["draw_spread_m"], "group": g["id"],
                        "layer": layer_of(m["species"], m.get("form"))})
        if not auto: continue
        w = {s: sum(species_info(s, m.get("form"))["draw_spread_m"] ** 2 for m in auto if m["species"] == s) for s in order if any(m["species"] == s for m in auto)}
        tot = sum(w.values()) or 1.0
        long_x = (x1 - x0) >= (y1 - y0)
        cur = x0 if long_x else y0
        span = (x1 - x0) if long_x else (y1 - y0)
        for s, ws in w.items():
            ms = [m for m in auto if m["species"] == s]
            seg = span * ws / tot
            a0, a1 = (cur, cur + seg) if long_x else (cur, cur + seg)
            cur += seg
            n = len(ms); cross = (y1 - y0) if long_x else (x1 - x0)
            cols = max(1, round(math.sqrt(n * seg / max(cross, 1e-6))))
            rows = math.ceil(n / cols)
            for k, m in enumerate(ms):
                r, c = divmod(k, cols)
                u = a0 + seg * (c + .5) / cols
                v = ((y0 if long_x else x0) + cross * (r + .5) / rows)
                pos = (u, v) if long_x else (v, u)
                out.append({"species": s, "form": m.get("form"), "at": pos,
                            "spread": m.get("spread_m") or species_info(s, m.get("form"))["draw_spread_m"], "group": g["id"],
                            "layer": layer_of(s, m.get("form"))})
    return out


def extent(layout, pad=1.0):
    xs, ys = [], []
    for key in ("zones", "paved_areas", "planting_groups", "seating", "features", "walls", "screens", "canopies"):
        for it in layout.get(key, []):
            r = it.get("rect")
            if r: xs += [r[0], r[2]]; ys += [r[1], r[3]]
            elif it.get("center"): xs.append(it["center"][0]); ys.append(it["center"][1])
            for p in it.get("polyline", []): xs.append(p[0]); ys.append(p[1])
    if not xs: return (0, 0, 10, 10)
    return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)


def path_line(p):
    """Centre line of a path: its polyline, or the long axis of its rect."""
    if p.get("polyline"): return LineString(p["polyline"])
    if p.get("rect"):
        x0, y0, x1, y1 = p["rect"]
        if (x1 - x0) >= (y1 - y0): return LineString([(x0, (y0 + y1) / 2), (x1, (y0 + y1) / 2)])
        return LineString([((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1)])
    return None
