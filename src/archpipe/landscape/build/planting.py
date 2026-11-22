"""Species data (LDL), drawability (LDL asset table), size at a stated age, and the plant objects.

Rule (garden brief 2026-11-22): a species is DRAWN only from a graded A/B asset of that species or its genus. Otherwise it is an
honest generic mass at the species' size and foliage colour, labelled STAND-IN in the schedule. A look-alike of another species is
never used (`resolve` refuses an asset that the table flags as a stand-in for a different species).
"""
from __future__ import annotations

import functools
import json
import math
import os
from pathlib import Path

from . import policy as P
from .geom import Obj, ellipsoid, cyl

ROOT = Path(__file__).resolve().parents[4]
PLANTS = ROOT / "knowledge/landscape/plants"
STORE = Path(os.path.expanduser("~/archpipe/shared/assets/user/landscape"))
LIB = Path(os.path.expanduser("~/archpipe/assets/library/props"))


@functools.lru_cache(maxsize=None)
def _plants():
    return {s["slug"]: s for s in json.loads((PLANTS / "plants.json").read_text())["species"]}


@functools.lru_cache(maxsize=None)
def _assets():
    return json.loads((PLANTS / "assets.json").read_text())


def gltf_path(asset):
    if asset.get("manifest_key"):
        return STORE / asset["manifest_key"] / "scene.gltf"
    return LIB / asset["id"] / "model.gltf"


def resolve(slug, assets=None, table=None):
    """-> {'drawable': bool, 'assets': [asset...], 'why': str}. `assets`/`table` can be injected (tests)."""
    a = assets or _assets()
    row = next((s for s in (table or a["species"]) if s["slug"] == slug), None)
    if row is None:
        return dict(drawable=False, assets=[], why="species not in the LDL asset table")
    if row.get("drawable") != "drawable":
        return dict(drawable=False, assets=[], why=row.get("drawable") or "no asset")
    if "stand-in" in (row.get("note") or "").lower():     # the table itself says the asset is another species
        return dict(drawable=False, assets=[], why="only a look-alike asset exists (" + row["note"][:80] + ")")
    ok = [x for x in a["assets"] if x.get("grade") in ("A", "B") and slug in (x.get("maps_to") or []) and x.get("species_fit") in ("species", "genus")]
    ok = [x for x in ok if gltf_path(x).exists()]
    if not ok:
        return dict(drawable=False, assets=[], why="graded asset file missing on this machine")
    return dict(drawable=True, assets=ok, why="graded " + "/".join(sorted({x["grade"] for x in ok})))


def _val(attr):
    """(min, max) of a sourced numeric attribute, or None for a GAP."""
    if not attr or attr.get("status") == "GAP" or not isinstance(attr.get("value"), dict):
        return None
    v = attr["value"]
    return (v["min"], v["max"]) if "min" in v else None


def species_facts(slug):
    s = _plants().get(slug)
    if s is None:
        return dict(known=False)
    at = s["attributes"]
    gr = at.get("growth_rate", {})
    foliage = at.get("foliage", {})
    return dict(known=True, layers=s["layers"], height=_val(at.get("height_m")), spread=_val(at.get("spread_m")),
                growth=(gr.get("value") or {}).get("class") if gr.get("status") != "GAP" else None,
                foliage_text=((foliage.get("value") or {}).get("character") or "") if foliage.get("status") != "GAP" else "",
                flowers=((at.get("flowering", {}).get("value") or {}).get("colours")) if at.get("flowering", {}).get("status") != "GAP" else None)


def size_fraction(age, growth, form):
    """Policy (ASSUMED, no growth curve is held): fraction of mature size at `age` years; None age = mature."""
    if age is None:
        return 1.0
    t = P.YEARS_SMALL_FORMS if form in P.SMALL_FORMS else P.YEARS_TO_MATURE.get(growth, 8.0)
    return min(1.0, P.FRAC_FLOOR + (1 - P.FRAC_FLOOR) * age / t)


def foliage_colour(text):
    t = text.lower()
    if "gray" in t or "grey" in t or "silver" in t:
        return (0.46, 0.52, 0.42), 'foliage text "%s"' % text[:40]
    if "dark green" in t:
        return (0.12, 0.30, 0.12), 'foliage text "%s"' % text[:40]
    return P.FOLIAGE_DEFAULT, "default green: foliage colour not stated (GAP)"


def mature_size(slug, layout_plant):
    """(height, spread, basis) at maturity. Spread from the layout (it checked it against the space); height from the source (mid-range)."""
    f = species_facts(slug)
    spread = layout_plant.get("mature_spread_m") or layout_plant.get("spread_m")
    height = layout_plant.get("mature_height_m")
    basis = "layout"
    if height is None and f.get("height"):
        height, basis = sum(f["height"]) / 2, "source mid-range"
    if height is None:
        height, basis = (spread or 0.5), "GAP: height not sourced, taken equal to spread"
    if spread is None and f.get("spread"):
        spread = sum(f["spread"]) / 2
    return height, spread, basis


def _best_asset(assets, height, spread_range):
    """Asset whose height-scaled footprint best fits the sourced spread range."""
    def err(x):
        s = height / x["size_m"][2]
        w = max(x["size_m"][0], x["size_m"][1]) * s
        lo, hi = spread_range or (w, w)
        return 0 if lo <= w <= hi else min(abs(w - lo), abs(w - hi))
    return min(assets, key=err)


def is_climber(slug):
    f = species_facts(slug)
    return "climber" in f.get("layers", []) or "climbing" in f.get("foliage_text", "").lower()


def plant_objects(oid, slug, plant, at, age, ground_z, base_z=None, support=("ground",), climbing=None, size_override=None, form=None, max_spread=None):
    """One planted individual -> (Obj, schedule row). `climbing` = (front-face y, side +1/-1, max height) for a climber on a trellis."""
    base_z = ground_z if base_z is None else base_z
    f = species_facts(slug)
    form = form or plant.get("form")
    h_m, s_m, basis = mature_size(slug, plant)
    if size_override:
        h_m, s_m, basis = size_override
    frac = size_fraction(age, f.get("growth"), form)
    h, s = h_m * frac, s_m * frac
    r = resolve(slug)
    x, y = at
    row = dict(id=oid, species=slug, age_years=age, mature_height_m=round(h_m, 3), mature_spread_m=round(s_m, 3), shown_height_m=round(h, 3),
               shown_spread_m=round(s, 3), size_basis=basis, size_fraction=round(frac, 3))
    if r["drawable"] and climbing is None:
        a = _best_asset(r["assets"], h_m, f.get("spread"))
        sc = h / a["size_m"][2]
        if max_spread and max(a["size_m"][:2]) * sc > max_spread:      # restrained to the room it has (pots beside walls)
            sc = max_spread / max(a["size_m"][:2]); h = sc * a["size_m"][2]; row["restrained_to_m"] = round(max_spread, 3); row["shown_height_m"] = round(h, 3)
        w, d = a["size_m"][0] * sc, a["size_m"][1] * sc
        bounds = (x - w / 2, y - d / 2, base_z, x + w / 2, y + d / 2, base_z + h)
        o = Obj(oid, "plant", "%s: graded %s asset %s (%s, %s), scaled to %.2f m at %s" % (slug, a["grade"], a["id"], a["licence"], a["author"], h,
                "maturity" if age is None else "%d years" % age), rests_on=support, footprint_mode=None, asset=dict(
                    asset_id=a["id"], gltf=str(gltf_path(a)), scale=sc, at=[x, y, base_z], bounds=bounds, native_size_m=a["size_m"], grade=a["grade"],
                    licence=a["licence"], author=a["author"], source=a["source"], species_fit=a["species_fit"]),
            meta=dict(species=slug, age=age))
        # crown envelope for clip tests: ellipsoid over the upper 70 % (clear stem below), a coarse model of the real mesh
        top, c0 = base_z + h, base_z + 0.3 * h
        o.meta["envelope"] = ((bounds[0] + bounds[3]) / 2, y, (top + c0) / 2, w / 2, d / 2, (top - c0) / 2)
        row.update(status="asset", asset=a["id"], grade=a["grade"], species_fit=a["species_fit"], achieved_spread_m=round(max(w, d), 3),
                   sourced_spread_range_m=f.get("spread"))
        return o, row
    col, why = foliage_colour(f.get("foliage_text", ""))
    mat = "standin:%.3f,%.3f,%.3f" % col
    if climbing is not None:
        face_y, sgn, max_h = climbing
        hh = min(h, max_h)
        rx, rz = s / 2, hh / 2
        part = ellipsoid(mat, x, face_y + sgn * 0.12, base_z + rz, rx, 0.12, rz)   # flattened against the trellis face
        # a climber's mass is a flat veil, so its spread is the width along the screen
        o = Obj(oid, "plant", "STAND-IN generic climber mass (%s has no drawable asset; %s) on the screen" % (slug, r["why"]), [part],
                rests_on=support, footprint_mode=None, standin=True, meta=dict(species=slug, age=age, climbing=True, colour=why))
        row.update(status="standin", reason=r["why"], colour_basis=why, climbing=True, shown_height_m=round(hh, 3))
        return o, row
    z0 = base_z
    part = ellipsoid(mat, x, y, z0 + h / 2, s / 2, s / 2, h / 2)
    o = Obj(oid, "plant", "STAND-IN generic %s mass (%s has no drawable asset: %s) at %.2f x %.2f m" % (form or "plant", slug, r["why"], s, h), [part],
            rests_on=support, footprint_mode=None, standin=True, meta=dict(species=slug, age=age, colour=why))
    row.update(status="standin", reason=r["why"], colour_basis=why)
    return o, row

