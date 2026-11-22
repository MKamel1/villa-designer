"""Shade-tree comparison on data (client 2026-11-22: trees instead of pergolas; NOT evergreen: sun in Dec-Feb is welcome) and the layer table.

Every figure is read from LDL's plants.json (sourced there) or computed here from the layout; the leaf-drop and leaf-out MONTHS for Cairo are a GAP for every species (searches 2026-11-22 found
habit statements only) and are carried as such: the design uses the client's own months (bare Dec-Feb, in leaf Mar-Nov) as a stated ASSUMPTION, never as a sourced fact.
"""
from __future__ import annotations

import json

from ..build import planting as PL
from . import final as F, site as S
from .species import POOL
from .ty_core import A, B

FACTOR = {"high": 1.25, "moderate": 0.75, "low": 0.5}          # NHBC 2024 ch. 4.2 table 3b via LDK LS-TREE-BUILDING
NHBC_WATER = {"low": "low", "medium": "moderate", "high": "high"}

# habit evidence read in the search of 2026-11-22 (excerpts; pages not fetched unless stated)
PHENO = {
    "lagerstroemia_indica": "deciduous (LDL: UF/IFAS ST342 'deciduous', autumn colour yellow/orange/red); Cairo leaf-drop and leaf-out months: GAP (no Egypt source found)",
    "jacaranda_mimosifolia": "deciduous or semi-deciduous (LDL, NCSU: flowers while leafless); UF/IFAS ST317 excerpt: blooms April-August, sometimes before the new leaves; a Zambian guide gives leaf fall July-August (southern hemisphere: NOT used); Cairo months: GAP",
    "delonix_regia": "semi-evergreen (LDL); Cairo months: GAP",
    "punica_granatum": "deciduous (LDL: NCSU, SelecTree); Cairo months: GAP",
    "ficus_carica": "deciduous (LDL); Cairo months: GAP",
    "tipuana_tipu": "semi-evergreen, 'largely deciduous midwinter to spring depending on site' (LDL, Wikipedia excerpt): the only sourced drop window, and it runs into the hot months",
    "olea_europaea": "evergreen (LDL, NCSU)", "ficus_microcarpa": "evergreen (LDL, NCSU)", "citrus_limon": "evergreen (LDL)",
}
NOT_IN_POOL = {
    "melia_azedarach": "no LDL record, no graded asset; no Cairo leaf-month source found (street-tree surveys of Greater Cairo exist but the excerpts read give no phenology); not evaluated",
    "bauhinia_variegata": "no LDL record, no graded asset; no leaf-month source found; not evaluated",
    "morus_alba": "no LDL record, no graded asset; fruit stains paving (not tested); no leaf-month source found; not evaluated",
    "ceratonia_siliqua": "no LDL record (large evergreen, brief names it); not evaluated",
}
PICK = {
    "lagerstroemia_indica": "PICKED over the dining: deciduous, graded B asset, benign roots, high heat, tolerates alkaline soil, non-toxic, summer flowers (Jul-Sep: the summer evenings), pruning regime sourced (UF/IFAS EP399, excerpt). NHBC fits only at the pruned height.",
    "jacaranda_mimosifolia": "REJECTED for these gardens: graded A and deciduous, but 15.2 m mature height needs 7.6 m from the house (low water) and the sourced minimum spread 4.6 m will not fit; no source on holding it at 4.5 m; messy (leaf and flower litter). Fits a larger plot.",
    "delonix_regia": "REJECTED: graded A, but alkaline soil intolerant (LDL), aggressive shallow roots that lift walls, 18 m.",
    "punica_granatum": "KEPT as the understorey fruit tree (graded B, deciduous, benign roots); too small to roof a seat (spread 2.4-3.0 m) and NHBC moderate x 3.7 m = 2.8 m cannot fit the east yard (2.3 m to the house wall).",
    "ficus_carica": "REJECTED: deciduous and fruiting but not drawable, alkaline soil intolerant (LDL) in a site of unknown soil pH, suckers; wet-fruit litter.",
    "tipuana_tipu": "REJECTED: its leaf-drop window (midwinter to spring) is sourced but leaves the hot early spring bare; large (30 m), invasive flag, alkaline intolerant.",
    "olea_europaea": "PICKED where year-round screening matters (quiet bench, east yard bench) and winter sun is already small: evergreen, low water (NHBC 0.5), roots moderate; stand-in asset only (grade C); NO source on umbrella pruning (GAP, stated).",
    "ficus_microcarpa": "REJECTED: densest shade but aggressive roots (LDL): needs 6 m (policy) from a pond or building: no position in the 5.7 m x 9.3 m garden or the courts; invasive flag; ('Nitida' clipping tolerance is well attested in trade sources, not used).",
    "citrus_limon": "REJECTED as a shade tree: light shade, 6.1 m, hydrozone high (needs its own bed), thorny; graded A, fine as a fruit tree elsewhere.",
}


def _attr(slug, key):
    a = PL._plants()[slug]["attributes"][key]
    return a.get("value") if a.get("status") != "GAP" else None


def compare(L):
    """One row per candidate: LDL figures, NHBC distance needed at the species height and at the pruned height against the distance available at the picked spot, grade, leaf-state evidence, decision."""
    rows = []
    picked = {t["species"]: t for t in L["trees"]}
    for slug in PHENO:
        sp = POOL[slug] if slug in POOL else None
        if sp is None:
            continue
        res = PL.resolve(slug)
        grade = None
        for a in PL._assets()["assets"]:
            if slug in (a.get("maps_to") or []):
                grade = max([grade or "D", a["grade"]], key=lambda g: -ord(g)) if grade else a["grade"]
        roots = (_attr(slug, "root_behaviour") or {}).get("class")
        alk = (_attr(slug, "alkaline_soil") or {}).get("class")
        fol = (_attr(slug, "foliage") or {}).get("habit")
        water = NHBC_WATER.get(sp.water, "high")
        t = picked.get(slug)
        rows.append({"slug": slug, "name": sp.name, "habit": fol, "leaf_evidence": PHENO[slug], "height_m": sp.h_max, "spread_m": [sp.s_min, sp.s_max], "roots": roots, "alkaline": alk, "heat_verdict": sp.verdict, "toxic": sp.toxic,
                     "nhbc_water": water, "nhbc_need_species_height_m": round(FACTOR[water] * sp.h_max, 2) if sp.h_max else None, "graded_best": grade, "drawable": res["drawable"],
                     "pruned": ({"height_m": t["mature_height_m"], "spread_m": t["mature_spread_m"], "nhbc_need_m": round(FACTOR[water] * t["mature_height_m"], 2), "source_status": t["pruning_source_status"]} if t else None),
                     "decision": PICK[slug]})
    rows += [{"slug": k, "name": k.replace("_", " "), "decision": v, "in_pool": False} for k, v in NOT_IN_POOL.items()]
    return rows


# ---- layers -----------------------------------------------------------------------------------------------------------------------
LAYERS = ("canopy", "understorey", "shrub", "perennial", "groundcover", "climber")
CLIMBERS = {"vitis_vinifera", "petrea_volubilis", "bougainvillea_glabra", "jasminum_grandiflorum", "podranea_ricasoliana"}


def layer_of(slug, role=""):
    sp = POOL[slug]
    if slug in CLIMBERS or (role.endswith("climber") and slug == "jasminum_sambac"):
        return "climber"
    if "palm" in sp.layers or sp.form == "small_tree":
        return "understorey"
    h = sp.h_max or 1.0
    if "groundcover_lawn" in sp.layers or sp.form == "ground_cover" or h <= 0.6:
        return "groundcover"
    if h <= 1.3 or "perennial" in sp.layers or "grass" in sp.layers or "herb" in sp.layers:
        return "perennial"
    return "shrub"


def room_of(x, y):
    return "south garden" if x > 22.597 else "east yard" if x > 15.412 else "north court"


def layer_table(L):
    """Plants (not species) per layer per garden room; trees are canopy (crape, olive) or understorey (pomegranate: below 4 m). The frangipani pot is a container understorey tree."""
    tab = {r: {k: {"plants": 0, "species": set()} for k in LAYERS} for r in ("south garden", "east yard", "north court")}
    for g in L["planting_groups"]:
        for p in g["plants"]:
            r = room_of(*p["at"])
            ly = layer_of(p["species"], g.get("role", ""))
            tab[r][ly]["plants"] += 1
            tab[r][ly]["species"].add(p["species"])
    for t in L["trees"]:
        r = room_of(*t["center"])
        ly = "canopy" if (t.get("pruned") and t["mature_spread_m"] >= 2.6) else "understorey"
        tab[r][ly]["plants"] += 1
        tab[r][ly]["species"].add(t["species"])
    pot = next((o for o in L["obstacles"] if o["id"].startswith("pot")), None)
    if pot:
        tab[room_of((pot["rect"][0] + pot["rect"][2]) / 2, (pot["rect"][1] + pot["rect"][3]) / 2)]["understorey"]["plants"] += 1
        tab["south garden"]["understorey"]["species"].add("plumeria_rubra")
    out = {}
    for r, d in tab.items():
        out[r] = {k: {"plants": v["plants"], "species": sorted(v["species"])} for k, v in d.items()}
        out[r]["missing"] = [k for k in LAYERS if d[k]["plants"] == 0]
    return out


def climber_faces(L, reach=0.9):
    """Every screen and blank wall face of the gardens and whether a climber stands within `reach` of it. Faces: the two screen stubs (garden side), the south (rear) wall, the east fence, and the court/yard fences; the house facade is NOT clad (client brief: facade clear of planting for the fire items)."""
    from shapely.geometry import Point, box
    faces = {"screen N stub": box(S.SX0, S.SY0 + 0.15, S.SX0 + F.OPEN_A[0], S.SY0 + 0.2), "screen S stub": box(S.SX0 + F.OPEN_A[1], S.SY0 + 0.15, S.SX0 + A, S.SY0 + 0.2),
             "south garden rear wall": box(S.SX0 + A - 0.02, S.SY0 + 1.45, S.SX0 + A, S.SY0 + B), "south garden east fence": box(S.SX0 + 1.3, S.SY0 + B - 0.02, S.SX0 + A, S.SY0 + B),
             "east yard fence": box(F.TC.EX0 + 0.2, F.TC.EY0 + F.TC.EW - 0.02, F.TC.EX0 + F.TC.EL, F.TC.EY0 + F.TC.EW), "north court street fence": box(F.TC.NX1 - F.TC.NH, F.TC.NY0 + 0.3, F.TC.NX1 - F.TC.NH + 0.02, F.TC.NY0 + F.TC.NW)}
    out = {}
    for k, face in faces.items():
        near = sorted({p["species"] for g in L["planting_groups"] for p in g["plants"] if layer_of(p["species"], g.get("role", "")) == "climber" and Point(*p["at"]).distance(face) <= reach})
        out[k] = near
    return out
