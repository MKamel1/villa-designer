"""Final design (round 2, client DECIDED 2026-11-22): concept B adapted. One layout, ids unique across gardens, every surface declared.

South garden local frame (a, b): a = depth from the house face (x - 22.597), b = width from the WEST LINE with the sister plot (y + 29.916).
  west line  b = 0           fire pit ON the line (centre b 0.0), 2.1 m screen except an opening sized to the seating
  terrace    b 0 .. 7.2      social: dining table (8, extending to 10) close to the pit, BBQ stand, built-in rear bench
  mass       b 7.2 .. 9.3    planted mass with the pomegranate, herb strip on the east fence, SE quiet bench
  quiet room the east yard   (own pond, bench, divider) reached along the house wall behind the mass
North court: quiet room with the second pond (shade foliage). Both ponds kept (client).
Nothing here is invented: figures that are policy are marked POLICY; fire clearances come from the shortlisted manuals (FIRE below).
"""
from __future__ import annotations

import math

from shapely.geometry import Point, box
from shapely.ops import unary_union

from . import site as S, ty_core as C, ty_courts as TC
from .geom import rbox, rects_of
from .species import sun_ok
from .ty_core import A, B, POOL, RM, P, bed, entry, frag, pergola, row, tree

# ---- fire pit: manual-stated clearances of the shortlisted products (see FIRE_PRODUCTS in final_fire.py) --------------------------
PIT = (2.8, 0.0)                    # centre on the west line (b = 0): half on each side
FIRE_SIDE_M = 1.25                  # design clearance to combustibles: the strictest shortlisted figure, PTI "sides 4 ft" = 1.22 m, rounded up
FIRE_OVER_M = 2.0                   # design overhead clearance: MAD ESF 2000 mm to trees/curtains (PTI 1.83 m, Planika n/a, Solus 1.95 m)
OPEN_A = (1.1, 4.5)                 # screen opening along the west line (a range): pit edge to each screen end >= FIRE_SIDE_M; sized to the seating
# Crown densities (shade fraction) are the LDC CROWN assumption (critic/site.py: evergreen 0.8, deciduous leaf-on 0.7, bare 0.15): no held source gives a leaf density.
CROWN = {"evergreen": 0.8, "deciduous_on": 0.7, "deciduous_off": 0.15}
# Pruned crown = a MAINTENANCE SPECIFICATION (tree_pruning below): layout carries the pruned size, the species figures stay in LDL.
TREE_PRUNING = {
    "lagerstroemia_indica": dict(height_m=4.5, spread_m=4.0, underside_m=2.2, regime="multi-stem (3-5 stems; the head is trained to lean toward the table, at most 1.3 m off the trunk), clear trunk to 2.2 m; structural thinning every year in January-February while bare; crown held at 4.0 m by cutting back to the previous year's heads, never flat topping; "
                                 "removing suckers at the base twice a year", source="UF/IFAS EP399 'What is a crape murder?' (hard pruning/pollarding makes vigorous sprouts and, once started, needs annual pruning; blooms fall with the size of branch removed)",
                                 source_status="READ AS SEARCH EXCERPT 2026-11-22 (page itself not fetched); tolerance to a held 3.4 m crown is INFERENCE from 'pollarding keeps a plant at a set height'"),
    "olea_europaea": dict(height_m=4.5, spread_m=3.6, underside_m=2.2, regime="pruned multi-stem umbrella: thin the crown each late winter, hold the spread at 3.6 m", source=None,
                          source_status="GAP: no source on olive tolerance of an umbrella-held crown was found (search 2026-11-22 returned none)"),
}

PAR = dict(table_a0=1.5, table_b0=4.05, tree=(3.15, 8.4), east_b0=7.2, bbq=(2.0, 2.3), crape=(3.45, 6.1), crown_shift=(-0.75, -1.0), crape_spread=4.0, gravel2=(1.4, 3.7, 5.4, 7.6), olive=(4.2, 7.4), olive_spread=3.6)


def shade_tree(f, tid, slug, at, lean=(0.0, 0.0), spread=None):
    """A trimmed shade tree: the layout carries the PRUNED crown (TREE_PRUNING, a maintenance specification), the species figures stay in LDL. Crown underside is where the critic's crown disc starts."""
    pr = TREE_PRUNING[slug]
    tree(f, tid, slug, at)
    t = f["trees"][-1]
    t.update(mature_spread_m=spread or pr["spread_m"], crown_center=[round(t["center"][0] + lean[0], 3), round(t["center"][1] + lean[1], 3)], crown_lean_m=round(math.hypot(*lean), 2), mature_height_m=pr["height_m"], pruned=True, crown_underside_m=pr["underside_m"], pruning=pr["regime"], pruning_source=pr["source"], pruning_source_status=pr["source_status"],
             species_mature_spread_m=[POOL[slug].s_min, POOL[slug].s_max], species_mature_height_m=POOL[slug].h_max)
    return t


def sid(p, k):
    return f"{p}-{k}"


def paving(f, pfx, zone_rect, cut_rects, material="unit-paving"):
    poly = box(*zone_rect).difference(unary_union([box(*r) for r in cut_rects])) if cut_rects else box(*zone_rect)
    f["paved_areas"] += [{"id": f"{pfx}-paving-{i}", "rect": r, "material": material, "slope_pct": 1.5, "trace": ["U-S-STAND", "LS-SLOPE"]}
                         for i, r in enumerate(rects_of(poly, 0.02))]


def south(p=PAR):
    f = frag()
    ea = p["east_b0"]
    # screen: two segments, the opening at the pit (obstacles keep both so the fire rules see them)
    for k, (a0, a1) in (("n", (0.0, OPEN_A[0])), ("s", (OPEN_A[1], A))):
        r = RM(a0, 0, a1, 0.15)
        f["screens"].append({"id": f"sister-screen-{k}", "rect": r, "kind": "trellis", "height_m": C.SCREEN_H, "opacity": 0.9, "non_combustible_frame": True})
        f["obstacles"].append({"id": f"obs-sister-screen-{k}", "rect": r, "trace": ["U-PRIVACY", "LS-SCREEN"]})
    f["boundary"].append({"id": "sister-line-screen", "side": "neighbour", "kind": "fence", "height_m": C.SCREEN_H, "trace": ["U-PRIVACY", "LS-SCREEN"]})
    # fixed elements ---------------------------------------------------------------------------------------------------
    t0, tb = p["table_a0"], p["table_b0"]
    table = (t0, tb, t0 + 2.4, tb + 0.9)
    cr = p["crape"]
    wall3 = (5.4, 3.2, A, 5.5)                                          # thin strip (0.31 m) where the table extends to 10: 1.2 m clear of its south end
    wall2 = (4.3, 1.45, 5.1, 2.8)                                      # second wall bed, west of the table's reach
    pocket = (cr[0] - 0.3, 6.15, cr[0] + 0.8, 6.9)                       # planting pocket in the gravel east of the trunk, 1.2 m clear of the table
    wall = (5.1, 1.45, A, 3.2)                                       # planted edge along the south wall: 1.2 m clear of the table end (LS-DINE-CLEAR)
    bq = p["bbq"]
    bbq = (bq[0], bq[1], bq[0] + 0.5, bq[1] + 0.5)
    mass = (1.9, ea, 4.7, B - 0.6)
    herb = (1.3, B - 0.6, 2.5, B)
    mass2 = (2.5, B - 0.6, 4.7, B)
    rbench = (A - 0.45, 5.6, A, 6.9)                                  # lounge, 3 seats
    qbench = (A - 0.45, 7.3, A, 8.5)                                  # quiet, 2 seats
    gravel = (4.7, ea, A - 0.45, B)                                   # permeable floor under the pomegranate and the quiet bench
    # permeable gravel floor under the crowns (LS-ROOTZONE keeps paving out of every dripline); a BBQ stand place keeps a paved slab (hard surface, brief)
    g2 = p["gravel2"]
    # (0, 7.9)-(0.3, B): the east yard tree's dripline reaches 0.27 m into the garden mouth
    grav2 = [(A - 0.45, 6.9, A, 7.3), (A - 0.45, 8.5, A, B), (0.0, 7.0, 1.2, B)] + [tuple(r) for r in rects_of(box(*g2).difference(unary_union([box(bq[0] - 0.3, bq[1] - 0.3, bq[0] + 0.8, bq[1] + 0.8), box(*wall), box(*wall2), box(*wall3), box(*pocket), box(*mass), box(*gravel)])), 0.02)] if g2 else []
    scr = [(0.0, 0.15, OPEN_A[0], 1.45), (OPEN_A[1], 0.15, A, 1.45)]            # climber beds at the foot of the screen stubs
    cuts = [wall, wall2, wall3, pocket, mass, herb, mass2, rbench, qbench, gravel] + scr + grav2
    paving(f, "s", RM(0, 0, A, B), [RM(*c) for c in cuts])
    # zones -----------------------------------------------------------------------------------------------------------
    def zone(zid, use, r, surface, h=4.0, **kw):
        f["zones"].append({"id": zid, "use": use, "rect": RM(*r), "surface": surface, "enclosure_height_m": h,
                           "trace": {"dining": ["U-S-DINE", "LS-DINE-AREA"], "lounge": ["U-S-LOUNGE", "U-S-FIRE", "LS-LOUNGE-AREA"], "quiet": ["U-S-QUIET"],
                                     "standing": ["U-S-STAND", "LS-STAND-AREA"], "other": ["U-S-QUIET"]}[use], **kw})
    zone("s-dining", "dining", (0.0, 0.7, 4.7, 6.7), "paving", 2.7)                     # 4.7 x 6.0 = 28.2 m2 for 8 seats (needs 27.7); stops short of the rear bench so the bench reads as lounge
    zone("s-lounge", "lounge", (2.0, 4.65, A, 8.5), "paving", 2.7)                      # 3.71 x 3.85 across
    zone("s-quiet", "quiet", (A - 1.6, 7.2, A, 8.6), "paving", 2.7)
    zone("s-gravel-floor", "other", gravel, "gravel", 2.7, label=False)
    for i, g in enumerate(grav2):
        zone(f"s-gravel-crown-{i}", "other", g, "gravel", 2.7, label=False)
    sz = (0.0, 0.15, 4.4, ea)
    zone("s-standing", "standing", sz, "paving", 2.7, design_people=int((sz[2] - sz[0]) * (sz[3] - sz[1]) / 1.3))
    f["tables"].append({"id": "s-dining-table", "zone": "s-dining", "center": list(P((table[0] + table[2]) / 2, (table[1] + table[3]) / 2)), "size_m": [2.4, 0.9], "seats": 8,
                        "extends_to_seats": 10, "trace": ["U-S-DINE", "LS-DINE-CLEAR"]})
    f["seating"] += [{"id": "s-bench-rear", "zone": "s-lounge", "rect": RM(*rbench), "seats": 2, "built_in": True, "trace": ["U-S-LOUNGE", "LS-FIRE-SEAT"]},
                     {"id": "s-bench-quiet", "zone": "s-quiet", "rect": RM(*qbench), "seats": 2, "built_in": True, "trace": ["U-S-QUIET", "LS-FIRE-SEAT"]}]
    f["seatwalls"].append({"id": "s-seat-wall", "height_mm": 450, "width_mm": 450, "trace": ["LS-SEATWALL"]})
    # fire pit on the west line -------------------------------------------------------------------------------------------
    f["features"].append({"id": "s-firepit", "kind": "firepit", "center": list(P(*PIT)), "diameter_m": C.PIT_D, "flush": True, "fuel": "gas", "shared_boundary": True,
                          "our_share": 0.5, "cover": {"load_rating_kN": 15.0, "lip_mm": 6.0, "bevelled": False, "max_opening_mm": 12.0}, "overhead_clear_m": 99,
                          "manual_side_clearance_mm": round(FIRE_SIDE_M * 1000), "manual_overhead_clearance_mm": round(FIRE_OVER_M * 1000),
                          "trace": ["U-S-FIRE", "D-FLUSH", "LS-FIRE-CLEAR", "LS-FIRE-COVER"]})
    f["features"].append({"id": "s-bbq", "kind": "bbq", "rect": RM(*bbq), "trace": ["U-S-BBQ", "LS-FIRE-CLEAR"]})
    hr = RM(*herb)
    f["features"].append({"id": "s-herb-bed", "kind": "herb_bed", "rect": hr, "midsummer_sun_hours": round(C.bed_sun(hr), 2), "trace": ["U-S-HERB", "LS-HERB-SUN"]})
    # shade trees replace the pergolas (client 2026-11-22): deciduous crape myrtle over the dining, pomegranate understorey at the quiet room
    shade_tree(f, "s-tree-crape", "lagerstroemia_indica", P(*p["crape"]), lean=p["crown_shift"], spread=p["crape_spread"])
    shade_tree(f, "s-tree-olive", "olea_europaea", P(*p["olive"]), spread=p["olive_spread"])
    tree(f, "s-tree-punica", "punica_granatum", P(*p["tree"]))
    # path: living door to the east yard along the house face (rect: LDB builds rects) ------------------------------------------
    f["paths"].append({"id": "s-path-door", "class": "main", "width_m": 1.2, "cross_slope_pct": 1.5, "rect": RM(0.0, 2.4, 1.2, 7.0), "trace": ["U-ACCESS", "LS-PATH-MAIN"]})      # the last 2.3 m to the yard mouth is the gravel floor under the east tree (no path object over a gravel zone)
    # planting: every bed layered (climber / understorey or palm / shrub / perennial / groundcover), one water class per bed (LS-HYDROZONE) -------------------------------
    mr, m2 = RM(*mass), RM(*mass2)
    bed(f, "s-bed-mass", mr, row(mr, "x", 1.4, ["jasminum_sambac", "petrea_volubilis"], 1.2, run=2, cap=C.SPREAD_CAP_CLIMBER)
        + row(mr, "x", 0.95, ["phoenix_roebelenii", "justicia_brandegeeana"], 0.9, run=1, how="min")
        + row(mr, "x", 0.5, ["pennisetum_alopecuroides", "salvia_leucantha"], 0.7, run=3, how="min")
        + row(mr, "x", 0.15, ["aspidistra_elatior", "justicia_brandegeeana"], 0.5, run=4, how="min"), "mass")
    bed(f, "s-bed-mass-corner", m2, row(m2, "x", 0.3, ["jasminum_sambac", "petrea_volubilis"], 0.8, run=2, cap=0.5), "wall-climber")      # climbers on the east fence
    bed(f, "s-bed-herb", hr, row(hr, "x", 0.3, ["origanum_majorana", "rosmarinus_officinalis"], 0.6, run=3, how="min"), "herb", trace=("U-S-HERB", "LS-HYDROZONE"))
    # west screen beds (1.3 m deep from the screen, 1.1-1.2 m along it: the pit side clearance fixes the length): grape (deciduous) on the north stub, sambac jasmine on the south stub
    rn, rs_ = RM(0.0, 0.15, OPEN_A[0], 1.45), RM(OPEN_A[1], 0.15, A, 1.45)
    bed(f, "s-bed-screen-n", rn, [entry("vitis_vinifera", P(0.35, 0.35), 0.5, "shrub"), entry("vitis_vinifera", P(0.9, 0.35), 0.5, "shrub")]
        + row(rn, "x", 0.75, ["salvia_leucantha"], 0.6, run=2, how="min") + row(rn, "x", 1.15, ["aspidistra_elatior"], 0.45, run=3, how="min"), "screen-climber", trace=("U-PRIVACY", "LS-HYDROZONE"))
    bed(f, "s-bed-screen-s", rs_, [entry("jasminum_sambac", P(A - 0.4 - i * 0.55, 0.35), 0.5, "shrub") for i in range(2)]
        + row(rs_, "x", 0.75, ["justicia_brandegeeana"], 0.6, run=2, how="min") + row(rs_, "x", 1.15, ["aspidistra_elatior"], 0.45, run=3, how="min"), "screen-climber", trace=("U-PRIVACY", "LS-HYDROZONE"))
    # south wall edge (two beds, 1.2 m clear of the table): climbers on the wall face, understorey palm and perennial / groundcover drifts in front, under the crape
    wr, wr2 = RM(*wall), RM(*wall2)
    bed(f, "s-bed-wall", wr, row(wr, "y", 0.3, ["petrea_volubilis", "jasminum_sambac"], 0.9, run=2, cap=0.6) + row(wr, "y", 0.15, ["aspidistra_elatior"], 0.45, run=8, how="min"), "wall-climber", trace=("U-S-DINE", "LS-HYDROZONE"))
    bed(f, "s-bed-wall-b", wr2, row(wr2, "x", 1.0, ["justicia_brandegeeana"], 0.7, run=3, how="min") + row(wr2, "x", 0.55, ["rhapis_excelsa"], 1.4, run=1, how="min")
        + row(wr2, "y", 0.2, ["aspidistra_elatior"], 0.45, run=6, how="min") , "wall-climber", trace=("U-S-DINE", "LS-HYDROZONE"))
    w3 = RM(*wall3)
    bed(f, "s-bed-wall-c", w3, [entry("petrea_volubilis", P(5.55, 3.7 + i * 0.9), 0.5, "shrub") for i in range(3)] + [entry("jasminum_sambac", P(5.55, 4.15 + i * 0.9), 0.5, "shrub") for i in range(2)], "wall-climber", trace=("U-S-DINE", "LS-HYDROZONE"))
    pk = RM(*pocket)
    bed(f, "s-bed-pocket", pk, row(pk, "x", 0.55, ["aspidistra_elatior", "farfugium_japonicum"], 0.45, run=3, how="min") , "strip", trace=("D-SHADE-OVER-SUN", "LS-HYDROZONE"))
    f["meta"].update(pit=PIT, opening_a=OPEN_A)
    return f


def _pot(f, at):
    r = [round(at[0] - .3, 3), round(at[1] - .3, 3), round(at[0] + .3, 3), round(at[1] + .3, 3)]       # model metres
    f["obstacles"].append({"id": "pot-0-plumeria", "rect": r, "trace": ["D-FRANGIPANI", "D-TERRACOTTA"]})


# =====================================================================================================================
# courts (own kits: pond section fitted to the real width; every surface declared; rect paths; unique ids)
POND_SECTION = {"entry_slope_run_per_rise": 4, "entry_drop_mm": 150, "entry_run_m": 0.6, "shelf_m": 0.3, "shelf_below_water_mm": 150, "trench_m": 0.5, "trench_below_water_mm": 900,
                "freeboard_mm": 150, "far_side": "vertical wall with marginal planting deterrent and the rigid grille",
                "note": "1:4 applies to the entry margin (waterline to the safety shelf), not to the 900 mm koi trench: a 1:4 slope to 900 mm needs 3.6 m of run per side (LDK GAP-POND-EDGE-SAFETY)"}


def pond_feat(fid, rect, entry_side):
    x0, y0, x1, y1 = rect
    w, ln = sorted((x1 - x0, y1 - y0))
    area = w * ln
    koi = max(1, int(28.7 * area / 27.6))                         # OSU: 12 in per 0.42 m2 unaerated = 28.7 in/m2; adult 70 cm = 27.6 in
    sec = POND_SECTION
    need_w = sec["entry_run_m"] + sec["shelf_m"] + sec["trench_m"]
    return {"id": fid, "kind": "pond", "rect": rect, "flush": True, "edge": "soft", "freeboard_mm": sec["freeboard_mm"], "depth_mm": sec["trench_below_water_mm"] + sec["freeboard_mm"],
            "volume_m3": round(0.7 * (sec["trench_below_water_mm"] / 1000) * area, 2), "koi_count": koi, "koi_adult_length_cm": 70, "aerated": False, "child_protection": "rigid_grille",
            "edge_slope_run_per_rise": sec["entry_slope_run_per_rise"], "margin_slope_back_mm": 600, "area_m2": round(area, 2), "width_m": round(w, 2), "section": dict(sec, entry_side=entry_side, section_width_m=round(need_w, 2)),
            "trace": ["U-POND", "D-FLUSH", "LS-POND-GUARD", "LS-POND-DEPTH", "LS-POND-STOCK", "LS-POND-FLUSH-MARGIN", "LS-POND-EDGE-SLOPE"]}


PAL = {
    "north_shade": [(["fatsia_japonica", "rhapis_excelsa"], 0.9, 1, "min", None), (["aspidistra_elatior", "farfugium_japonicum"], 0.45, 3, "min", None)],
    "north_edge": [(["acorus_gramineus"], 0.35, 6, "min", None)],
    "yard_mass": [(["fatsia_japonica", "phoenix_roebelenii"], 0.9, 1, "min", None), (["farfugium_japonicum", "aspidistra_elatior"], 0.45, 3, "min", None)],
    "pond_edge": [(["acorus_gramineus"], 0.3, 6, "min", None)],
}
TC.PAL.update(PAL)


def court(kit, zid, pfx):
    f = frag()
    zone = kit["zone"]
    cuts = [b["rect"] for b in kit["beds"]] + [kit[k] for k in ("pond", "bench") if kit.get(k)]
    grav = []
    if kit.get("gravel"):                                   # permeable floor under a tree's dripline (LS-ROOTZONE)
        grav = [tuple(r) for r in rects_of(box(*kit["gravel"]).difference(unary_union([box(*c) for c in cuts])), 0.02)]
        for i, g in enumerate(grav):
            f["zones"].append({"id": f"{pfx}-gravel-{i}", "use": "other", "rect": list(g), "surface": "gravel", "enclosure_height_m": 4.0, "label": False, "trace": ["U-N-QUIET"]})
    paving(f, pfx, zone, cuts + grav, kit.get("material", "unit-paving"))
    for b in kit["beds"]:
        bed(f, f"{pfx}-{b['id']}", b["rect"], TC.layered(b["rect"], b["pal"], b.get("back", "lo")), b["role"],
            trace=("U-POND" if b["pal"].startswith(("pond", "north_edge")) else "U-PRIVACY", "LS-HYDROZONE"))
    for cl in kit.get("climbers", []):                       # climbers on the court or yard fence face (jasmine; the beds here are all medium water)
        bid = f"{pfx}-{cl['bed']}"
        g = next(g for g in f["planting_groups"] if g["id"] == bid)
        g["plants"] += [dict(entry("jasminum_sambac", at, 0.5, "shrub"), role="climber") for at in cl["at"]]
    if kit.get("pond"):
        f["features"].append(pond_feat(f"{pfx}-pond", kit["pond"], kit["entry_side"]))
    if kit.get("bench"):
        f["zones"].append({"id": f"{pfx}-quiet", "use": "quiet", "rect": kit["quiet"], "surface": "paving", "enclosure_height_m": 4.0, "trace": ["U-N-QUIET"]})
        f["seating"].append({"id": f"{pfx}-bench", "zone": f"{pfx}-quiet", "rect": kit["bench"], "seats": 2, "built_in": True, "trace": ["U-N-QUIET"]})
    if kit.get("pergola"):
        pergola(f, f"{pfx}-pergola", kit["pergola"], 2.6, 0.6)
    for k, r in enumerate(kit["paths"]):
        f["paths"].append({"id": f"{pfx}-path-{k}", "class": kit.get("path_class", "main"), "width_m": 1.2, "cross_slope_pct": 1.5, "rect": r, "trace": ["U-ACCESS", "LS-PATH-MAIN"]})
    f["meta"][f"focal-{pfx}"] = kit.get("focal", "")
    return f


def north_kit():
    NR, NH, NW, NX1, NY0 = TC.NR, TC.NH, TC.NW, TC.NX1, TC.NY0
    pond = NR(1.4, 3.1, 3.4, 4.5)                       # 2.0 x 1.4: entry side faces the path (low v), far side against the planted strip and the yard wall
    return dict(zone=NR(0, 0, NH, NW), pond=pond, entry_side="low v (toward the path and screen planting)",
                beds=[dict(id="screen", rect=NR(1.5, 1.9, NH, 3.1), role="mass", pal="north_shade", back="lo"),
                      dict(id="edge-far", rect=NR(1.4, 4.5, 3.4, NW), role="strip", pal="north_edge", back="hi"),
                      dict(id="edge-back", rect=NR(3.4, 3.1, NH, NW), role="strip", pal="north_edge", back="hi")],
                bench=NR(1.6, 0.0, 3.0, 0.45), quiet=NR(1.2, 0.0, 3.2, 1.9), pergola=None,
                climbers=[dict(bed="screen", at=[(NX1 - (NH - 0.25), NY0 + v) for v in (2.1, 2.6, 3.0)])],
                paths=[NR(0, 1.9, 1.4, 3.1)], focal="the pond past the planted screen, from the lounge door")


def east_kit():
    ER, EL, EW, EX0, EY0 = TC.ER, TC.EL, TC.EW, TC.EX0, TC.EY0
    pond = ER(1.5, 1.35, 4.7, 2.75)                     # 3.2 x 1.4
    return dict(zone=ER(0, 0, EL, EW), pond=pond, entry_side="low v (toward the service path along the house wall)",
                beds=[dict(id="divider", rect=ER(5.95, 1.5, EL, EW), role="mass", pal="yard_mass", back="hi"),
                      dict(id="far", rect=ER(0, 1.5, 1.2, EW), role="mass", pal="yard_mass", back="hi"),
                      dict(id="edge", rect=ER(1.5, 2.75, 4.2, EW), role="strip", pal="pond_edge", back="hi")],
                bench=ER(5.0, 1.35, 5.45, 2.75), quiet=ER(4.8, 1.3, 5.6, EW), pergola=None,
                climbers=[dict(bed="far", at=[(EX0 + u, EY0 + EW - 0.2) for u in (0.4, 0.9)]), dict(bed="divider", at=[(EX0 + 6.9, EY0 + EW - 0.2)])],
                paths=[ER(0.2, 0, 4.3, 1.2)], path_class="service", gravel=ER(4.3, 0.5, EL, EW), focal="the pond is the focal point of the quiet room, bench at its end")


P_EAST = dict(u=6.25, v=2.3, lean=(-0.7, -0.4), spread=2.6)       # east yard tree: trunk in the divider bed; lean toward the bench


def build(pot_at=None, p_e=None):
    p_e = p_e or P_EAST
    fs = south()
    fn = court(north_kit(), "n", "n")
    fe = court(east_kit(), "e", "e")
    ex, ey = TC.EX0 + p_e["u"], TC.EY0 + p_e["v"]
    shade_tree(fe, "e-tree-olive", "olea_europaea", (ex, ey), lean=p_e["lean"], spread=p_e["spread"])
    pot = pot_at or POT
    fp = frag()
    _pot(fp, pot)
    fw = C.site_frag()
    for w in fw["walls"]:
        w["id"] = "wall-" + w["id"]                      # walls are built as ld-wall-*; the fire/overlap rules read the obstacles (ids fence-*)
    L = C.assemble(fw, fs, fn, fe, fp)
    from . import ty_run as R
    free = R.free_floor(L)                       # the standing zone declares the people the FREE floor holds (not the zone rectangle, which includes furniture)
    for z in L["zones"]:
        if z.get("use") == "standing":
            z["design_people"] = min(int(free / 1.3), int((z["rect"][2] - z["rect"][0]) * (z["rect"][3] - z["rect"][1]) / 1.3))
    L["meta"]["pot"] = list(pot)
    L["meta"]["layout_id"] = "LDG-final-B"
    return L


POT = (24.1, -21.97)       # model metres: a 1.5, b 7.95; found by search over the south garden (LDG-POT, fire clearances, no plant inside)
