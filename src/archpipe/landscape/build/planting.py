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
import random
import zlib
from pathlib import Path

from . import policy as P
from .geom import Obj, box, ellipsoid, cyl, tube

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


FAB = STORE / "fab" / "unzipped"


def is_fab(asset):
    return (asset.get("manifest_key") or "").startswith("fab/")


def fab_variants(asset):
    """LOD0 FBX of every variation of a Fab/Megascans plant archive (sorted); [] when the archive is not unzipped on this machine."""
    d = FAB / Path(asset["manifest_key"]).name
    return sorted(str(f) for f in d.glob("*_LOD0.fbx"))


def gltf_path(asset):
    """The model file of an asset: glTF (Sketchfab, library) or, for a Fab archive, the hero variation's LOD0 FBX (the key stays `gltf` for the export seam)."""
    if is_fab(asset):
        vs = fab_variants(asset)
        hero = [v for v in vs if "_%s_LOD0" % asset.get("hero_variation", "VarA") in v]
        return Path((hero or vs or [str(FAB / Path(asset["manifest_key"]).name / "missing.fbx")])[0])
    if asset.get("manifest_key"):
        return STORE / asset["manifest_key"] / "scene.gltf"
    return LIB / asset["id"] / "model.gltf"


def pick_variant(asset, oid):
    """The model file for individual `oid`: a Fab archive carries several variations, each individual takes one (stable by id); others have one file."""
    vs = fab_variants(asset) if is_fab(asset) else []
    return vs[zlib.crc32(oid.encode()) % len(vs)] if vs else str(gltf_path(asset))


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
    return dict(known=True, layers=s["layers"], habit=(foliage.get("value") or {}).get("habit") if foliage.get("status") != "GAP" else None, height=_val(at.get("height_m")), spread=_val(at.get("spread_m")),
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
    if climbing is not None:
        if basis.startswith("GAP"):          # no sourced height: a climber is taken to cover 80 % of the structure it climbs at maturity (policy)
            h = 0.8 * climbing["max_h"] * frac; row["size_basis"] = "POLICY: 80 % of the structure height at maturity (height not sourced)"
        return _climber_panel(oid, slug, f, climbing, s, h, age, base_z, support, row)
    if r["drawable"]:
        a = _best_asset(r["assets"], h_m, f.get("spread"))
        sc = h / a["size_m"][2]
        if max_spread and max(a["size_m"][:2]) * sc > max_spread:      # restrained to the room it has (pots beside walls)
            sc = max_spread / max(a["size_m"][:2]); h = sc * a["size_m"][2]; row["restrained_to_m"] = round(max_spread, 3); row["shown_height_m"] = round(h, 3)
        w, d = a["size_m"][0] * sc, a["size_m"][1] * sc
        bounds = (x - w / 2, y - d / 2, base_z, x + w / 2, y + d / 2, base_z + h)
        o = Obj(oid, "plant", "%s: graded %s asset %s (%s, %s), scaled to %.2f m at %s" % (slug, a["grade"], a["id"], a["licence"], a["author"], h,
                "maturity" if age is None else "%d years" % age), rests_on=support, footprint_mode=None, asset=dict(
                    asset_id=a["id"], gltf=pick_variant(a, oid), mode="height", scale=sc, at=[x, y, base_z], bounds=bounds, native_size_m=a["size_m"], grade=a["grade"],
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
    z0 = base_z
    part = ellipsoid(mat, x, y, z0 + h / 2, s / 2, s / 2, h / 2)
    o = Obj(oid, "plant", "STAND-IN generic %s mass (%s has no drawable asset: %s) at %.2f x %.2f m" % (form or "plant", slug, r["why"], s, h), [part],
            rests_on=support, footprint_mode=None, standin=True, meta=dict(species=slug, age=age, colour=why))
    row.update(status="standin", reason=r["why"], colour_basis=why)
    return o, row



def climber_panels():
    """Leaf-scan / curtain assets for climbers: assets.json `climber_panels` rows {slug, texture|gltf, tile_m, grade, licence, author} (added by lane LDL), graded A/B only."""
    return [x for x in _assets().get("climber_panels", []) if x.get("grade") in ("A", "B")]


def _climber_panel(oid, slug, f, cl, s, h, age, base_z, support, row):
    """A climber on a screen or wall: a leaf panel on the garden face of the structure (axis, face coordinate, side, span, max height from the layout rect).

    Order of preference: a graded curtain asset of the species (tiled, at most six tiles) > a graded leaf-scan atlas of the species > a procedural leaf-cutout panel
    (STAND-IN, said so). Width follows height at the stated age (policy), clipped to the structure."""
    C = P.CLIMBER
    hh = min(h, cl["max_h"])
    c = cl["at"][0] if cl["axis"] == "x" else cl["at"][1]
    w = min(max(C["min_w"], C["width_per_height"] * hh), cl["span"][1] - cl["span"][0])
    lo = min(max(cl["span"][0], c - w / 2), cl["span"][1] - w)
    hi = lo + w
    sgn, face = cl["sgn"], cl["face"]
    near, far = face + sgn * C["lift"], face + sgn * (C["lift"] + C["panel_t"])
    n0, n1 = min(near, far), max(near, far)
    row.update(climbing=True, shown_height_m=round(hh, 3), panel_width_m=round(w, 3), on=cl.get("on"))
    assets = [a for a in climber_panels() if slug in (a.get("maps_to") or [a.get("slug")])]
    rr = resolve(slug)
    curtains = [x for x in rr["assets"] if x["size_m"][1] < 0.2 * x["size_m"][0] and x["size_m"][2] > 0.5]     # a graded vertical curtain of leaves (e.g. the English ivy)
    if not assets and curtains:
        x = curtains[0]
        assets = [dict(id=x["id"], gltf=str(gltf_path(x)), tile_m=[x["size_m"][0], x["size_m"][2]], grade=x["grade"], licence=x["licence"], author=x["author"], source=x["source"])]
    if assets and assets[0].get("gltf") and Path(assets[0]["gltf"]).exists():
        a = assets[0]
        tw, th = a["tile_m"][0], a["tile_m"][1]
        sc = max(1.0, (w * hh / (6 * tw * th)) ** 0.5)
        nx, nz = max(1, math.ceil(w / (tw * sc))), max(1, math.ceil(hh / (th * sc)))
        tiles = []
        for ix in range(nx):
            for iz in range(nz):
                u = lo + (ix + 0.5) * w / nx
                zb = base_z + iz * hh / nz
                at = [u, (near + far) / 2, zb] if cl["axis"] == "x" else [(near + far) / 2, u, zb]
                tiles.append(dict(at=at, scale_xyz=[w / nx / tw, w / nx / tw, hh / nz / th], yaw_deg=0 if cl["axis"] == "x" else 90))
        bounds = (lo, n0, base_z, hi, n1, base_z + hh) if cl["axis"] == "x" else (n0, lo, base_z, n1, hi, base_z + hh)
        o = Obj(oid, "plant", "%s climber panel: %d tile(s) of graded %s asset %s (%s, %s)" % (slug, len(tiles), a["grade"], a["id"], a["licence"], a["author"]), rests_on=support, footprint_mode=None,
                asset=dict(asset_id=a["id"], gltf=a["gltf"], at=tiles[0]["at"], bounds=bounds, mode="tiles", tiles=tiles, tile_native_m=a["tile_m"], grade=a["grade"], licence=a["licence"], author=a["author"],
                           source=a.get("source", ""), species_fit="species"), meta=dict(species=slug, age=age, climbing=True, habit=f.get("habit")))
        row.update(status="asset", asset=a["id"], grade=a["grade"], species_fit="species")
        return o, row
    col, why = foliage_colour(f.get("foliage_text", ""))
    atlas = next((a for a in assets if a.get("texture") and Path(a["texture"]).exists()), None)
    mat = ("atlas:%s:%.3f,%.3f,%.3f" % (atlas["texture"], *col)) if atlas else "climber:%.3f,%.3f,%.3f:%s" % (*col, "d" if f.get("habit") == "deciduous" else "e")
    z1 = base_z + hh
    part = box(mat, lo, n0, base_z, hi, n1, z1) if cl["axis"] == "x" else box(mat, n0, lo, base_z, n1, hi, z1)
    if atlas:
        o = Obj(oid, "plant", "%s climber panel: leaf-scan atlas %s (%s, %s) on a plane" % (slug, atlas["id"], atlas["licence"], atlas["author"]), [part], rests_on=support, footprint_mode=None,
                meta=dict(species=slug, age=age, climbing=True, habit=f.get("habit"), atlas=atlas["id"]))
        row.update(status="asset", asset=atlas["id"], grade=atlas["grade"], species_fit="species")
        return o, row
    r = resolve(slug)
    o = Obj(oid, "plant", "STAND-IN procedural leaf-cutout panel for the climber %s (no graded climber asset: %s), %.2f m wide x %.2f m high on %s" % (slug, r["why"], w, hh, cl.get("on")), [part],
            rests_on=support, footprint_mode=None, standin=True, meta=dict(species=slug, age=age, climbing=True, colour=why, habit=f.get("habit")))
    row.update(status="standin", reason=r["why"], colour_basis=why)
    return o, row


def canopy_clumps(cx, cy, base_z, h, spread, stem, mat):
    """Pruned umbrella / lollipop crown as a cloud of overlapping oblate clumps on a trunk: STAND-IN geometry. Returns Parts (trunk(s) + clumps)."""
    parts = []
    tr = max(0.05, min(0.14, 0.03 * h))
    parts.append(cyl("trunk-bark", cx, cy, tr, base_z, base_z + stem + 0.1 * h, n=12, r_top=tr * 0.8))
    cz0 = base_z + stem
    ch = h - stem
    R = spread / 2
    # clump layout: one crown ellipsoid plus a ring of six lower clumps: the silhouette is an umbrella, bounded by the pruned spread and height
    parts.append(ellipsoid(mat, cx, cy, cz0 + ch * 0.62, R * 0.70, R * 0.70, ch * 0.38))
    for k in range(6):
        a = 2 * math.pi * k / 6
        rr = R * 0.45
        parts.append(ellipsoid(mat, cx + rr * math.cos(a), cy + rr * math.sin(a), cz0 + ch * 0.42, R * 0.55, R * 0.55, ch * 0.32))
    return parts


def tree_parts(oid, x, y, cx, cy, base_z, h, spread, stem, leaf_mat, deciduous, lean_stems=None):
    """STAND-IN multi-stem shade tree: trunks rise from (x, y), fork at the clear-stem height and carry limbs to a crown of the PRUNED spread and height centred on (cx, cy)
    (the crape's head leans toward the table). -> (parts, winter_parts): parts = stems + limbs + leaf-cutout clumps (leaf-on, or evergreen); winter_parts = stems, limbs and a twig
    network (leaf-off), empty for an evergreen. Deterministic per id. Geometry is a generic form, not the species' habit: said so in the label."""
    rng = random.Random(zlib.crc32(oid.encode()))
    n_st = lean_stems or (4 if deciduous else 3)
    R = spread / 2
    top = base_z + h
    fork = base_z + stem
    bark = "trunk-bark"
    woody, tw = [], []
    tips = []
    for k in range(n_st):
        a = 2 * math.pi * (k + rng.uniform(-0.15, 0.15)) / n_st
        b0 = (x + 0.09 * math.cos(a), y + 0.09 * math.sin(a), base_z)       # starts at the soil surface: no rigid part sinks into the bed layer
        fx, fy = x + 0.65 * (cx - x) + 0.12 * math.cos(a), y + 0.65 * (cy - y) + 0.12 * math.sin(a)
        mid = (x + 0.04 * (cx - x) + 0.10 * math.cos(a), y + 0.04 * (cy - y) + 0.10 * math.sin(a), base_z + 1.15)      # vertical to 1.15 m (above chair backs), then the lean to the fork
        fk = (fx, fy, fork + rng.uniform(-0.1, 0.15))
        r0 = 0.055 if deciduous else 0.075
        woody += [tube(bark, b0, mid, r0, r0 * 0.85, 7), tube(bark, mid, fk, r0 * 0.85, r0 * 0.7, 7)]
        for j in range(3):
            aa = a + (j - 1) * 0.9 + rng.uniform(-0.3, 0.3)
            rr = R * rng.uniform(0.45, 0.8)
            tz = base_z + stem + (h - stem) * rng.uniform(0.55, 0.92) - 0.35
            tip = (cx + rr * math.cos(aa), cy + rr * math.sin(aa), min(tz, top - 0.45))
            mp = ((fk[0] + tip[0]) / 2, (fk[1] + tip[1]) / 2, (fk[2] + tip[2]) / 2 - 0.08)
            woody += [tube(bark, fk, mp, 0.032, 0.024, 6), tube(bark, mp, tip, 0.024, 0.014, 6)]
            tips.append(tip)
    twigs = []
    for tip in tips:
        for _ in range(5):
            ang, up = rng.uniform(0, 2 * math.pi), rng.uniform(0.15, 0.7)
            L = rng.uniform(0.45, 0.8)
            e = (tip[0] + L * math.cos(ang) * (1 - up * 0.5), tip[1] + L * math.sin(ang) * (1 - up * 0.5), tip[2] + L * up)
            e = (cx + max(-R * 0.97, min(R * 0.97, e[0] - cx)), cy + max(-R * 0.97, min(R * 0.97, e[1] - cy)), min(e[2], top - 0.02))
            twigs.append(tube(bark, tip, e, 0.011, 0.005, 4))
            for _ in range(2):
                m = tuple(a + rng.uniform(0.3, 0.7) * (b - a) for a, b in zip(tip, e))
                a2 = rng.uniform(0, 2 * math.pi)
                f = (m[0] + 0.3 * math.cos(a2), m[1] + 0.3 * math.sin(a2), min(m[2] + rng.uniform(0.05, 0.25), top - 0.02))
                twigs.append(tube(bark, m, f, 0.006, 0.003, 4))
    leaves = []
    cr = 0.2 * spread                                          # leaf mass radius
    for tip in tips:
        for _ in range(2):
            px = tip[0] + rng.uniform(-0.1, 0.1); py = tip[1] + rng.uniform(-0.1, 0.1); pz = tip[2] + rng.uniform(0.0, 0.25)
            ch = max(0.3, min(cr * 0.62, (top - pz) * 0.98))
            pz = min(pz, tip[2] + 0.2)
            rx = max(0.25, min(cr, R - math.hypot(px - cx, py - cy)))
            leaves.append(ellipsoid(leaf_mat, px, py, min(pz, top - ch), rx, rx, ch, 12, 8))
    leaves.append(ellipsoid(leaf_mat, cx, cy, top - 0.3 * (h - stem), R * 0.62, R * 0.62, 0.3 * (h - stem), 14, 8))
    parts = woody + twigs[: len(twigs) // 3] + leaves if deciduous else woody + leaves
    return parts, (woody + twigs if deciduous else [])


def pruned_tree(oid, slug, t, age, ground_z):
    """A trimmed evergreen shade tree: size is the PRUNED canopy the layout asks for (pruned_*), not the species' natural mature size. -> (Obj, row)"""
    pr = t.get("pruned") or {}
    f = species_facts(slug)
    h_m = pr.get("height_m") or t.get("pruned_height_m") or t.get("mature_height_m") or 3.5
    s_m = pr.get("spread_m") or t.get("pruned_spread_m") or t.get("mature_spread_m") or 3.0
    stem_m = pr.get("clear_stem_m") or t.get("clear_stem_m") or P.TREE_CLEAR_STEM * h_m
    frac = size_fraction(age, f.get("growth"), "small_tree")
    h, sp, stem = h_m * frac, s_m * frac, stem_m * frac
    x, y = t["center"]
    r = resolve(slug)
    decid = f.get("habit") == "deciduous"
    if r["drawable"] and decid:     # a graded tree asset is one leaf state only (it cannot go bare) and the graded crape is a 2.8 m sparse flowering specimen: a pruned 4 m shade head needs both states
        r = dict(drawable=False, assets=[], why="graded asset %s exists but is one leaf state only (sparse flowering, 2.8 m): a deciduous shade tree is built with both states" % r["assets"][0]["id"])
    row = dict(id=oid, species=slug, age_years=age, mature_height_m=round(h_m, 3), mature_spread_m=round(s_m, 3), shown_height_m=round(h, 3), shown_spread_m=round(sp, 3),
               size_basis="PRUNED canopy from the layout (natural size not used)", size_fraction=round(frac, 3), pruned=True, clear_stem_m=round(stem, 3))
    if r["drawable"]:
        a = _best_asset(r["assets"], h_m, None)
        nz, nxy = a["size_m"][2], max(a["size_m"][:2])
        sz, sxy = h / nz, sp / nxy
        sxy = min(max(sxy, 0.6 * sz), 1.6 * sz)
        w, d = a["size_m"][0] * sxy, a["size_m"][1] * sxy
        bounds = (x - w / 2, y - d / 2, ground_z, x + w / 2, y + d / 2, ground_z + h)
        o = Obj(oid, "plant", "%s pruned shade tree: graded %s asset %s (%s, %s), scaled to the pruned canopy %.1f m wide x %.1f m high" % (slug, a["grade"], a["id"], a["licence"], a["author"], w, h),
                rests_on=("ground",), footprint_mode=None, asset=dict(asset_id=a["id"], gltf=str(gltf_path(a)), mode="xyz", scale_xyz=[sxy, sxy, sz], at=[x, y, ground_z], bounds=bounds, native_size_m=a["size_m"],
                grade=a["grade"], licence=a["licence"], author=a["author"], source=a["source"], species_fit=a["species_fit"]), meta=dict(species=slug, age=age, pruned=True))
        c0 = ground_z + max(stem, 0.3 * h)
        o.meta["envelope"] = (x, y, (ground_z + h + c0) / 2, w / 2, d / 2, (ground_z + h - c0) / 2)
        row.update(status="asset", asset=a["id"], grade=a["grade"], species_fit=a["species_fit"], achieved_spread_m=round(max(w, d), 3))
        return o, row
    col, why = foliage_colour(f.get("foliage_text", ""))
    deciduous = f.get("habit") == "deciduous"
    cc = t.get("crown_center") or t["center"]
    lean = math.hypot(cc[0] - x, cc[1] - y)
    if lean > max(t.get("crown_lean_m") or 0.0, 0.5 * s_m) + 0.05:      # a head more than half a spread off its trunk is a layout error (LDG's mirrored layout leaves crown_center unmirrored)
        row["crown_center_ignored"] = "crown_center is %.2f m from the trunk (declared lean %s m, spread %.1f m): ignored, crown built over the trunk" % (lean, t.get("crown_lean_m"), s_m)
        cc, lean = (x, y), 0.0
    cxy = (x + (cc[0] - x) * frac, y + (cc[1] - y) * frac) if lean else (x, y)
    parts, winter = tree_parts(oid, x, y, cxy[0], cxy[1], ground_z, h, sp, stem, "leafcut:%.3f,%.3f,%.3f:e" % col, deciduous)
    o = Obj(oid, "plant", "STAND-IN pruned %s shade tree for %s (no graded asset: %s): generic multi-stem trunk, limbs and %s, %.1f m wide x %.1f m high, clear stem %.1f m, crown %.2f m off the trunk" % (
        "deciduous" if deciduous else "evergreen", slug, r["why"], "leaf-cutout foliage (leaf-on) / bare limbs and twigs (leaf-off)" if deciduous else "leaf-cutout foliage all year", sp, h, stem, lean * frac), parts,
            rests_on=("ground",), footprint_mode=None, standin=True, winter_parts=winter, meta=dict(species=slug, age=age, pruned=True, colour=why, deciduous=deciduous, crown_center=cxy))
    row.update(status="standin", reason=r["why"], colour_basis=why, leaf_states=["leaf-on", "leaf-off"] if deciduous else ["evergreen"])
    return o, row
