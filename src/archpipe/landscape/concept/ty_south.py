"""South garden typologies (stage LD-G pass 2). Local frame a (depth from the house face), b (width from the west line).

Each function returns a layout fragment (model frame) plus `rooms` (use rects for the privacy/shade checks) and `covers` (pergola rects).
The typology fixes the bones; `p` holds only the furniture parameters that the search fits at the rule distances.
"""
from __future__ import annotations

from shapely.geometry import box

from . import ty_core as C
from .ty_core import A, B, RM, P, bed, entry, frag, pergola, row, tree, west_screen

DOOR_B = (2.585, 4.985)          # living door (LDS), centre 3.785
DOOR_C = 3.785


def _rm(r):
    return RM(*r)


def _hearth(f, pit, bbq, trace_extra=(), overhead=99):
    f["features"].append({"id": "firepit", "kind": "firepit", "center": list(P(*pit)), "diameter_m": C.PIT_D, "flush": True, "fuel": "gas",
                          "cover": {"load_rating_kN": 15.0, "lip_mm": 6.0, "bevelled": False, "max_opening_mm": 12.0}, "overhead_clear_m": overhead,
                          "trace": ["U-S-FIRE", "D-FLUSH", "LS-FIRE-CLEAR", "LS-FIRE-COVER"]})
    f["features"].append({"id": "bbq", "kind": "bbq", "rect": _rm(bbq), "trace": ["U-S-BBQ", "LS-FIRE-CLEAR"]})


def _table(f, tid, rect_local, seats, zone="dining"):
    a0, b0, a1, b1 = rect_local
    cx, cy = P((a0 + a1) / 2, (b0 + b1) / 2)
    f["tables"].append({"id": tid, "zone": zone, "center": [cx, cy], "size_m": [a1 - a0, b1 - b0], "seats": seats, "trace": ["U-S-DINE", "LS-DINE-CLEAR"]})


def _bench(f, sid, rect_local, zone, seats, wall=True):
    f["seating"].append({"id": sid, "zone": zone, "rect": _rm(rect_local), "seats": seats, "trace": ["U-S-LOUNGE" if zone != "quiet" else "U-S-QUIET", "LS-FIRE-SEAT"]})


def _zone(f, zid, use, rect_local, surface, h=4.0, **kw):
    f["zones"].append({"id": zid, "use": use, "rect": _rm(rect_local), "surface": surface, "enclosure_height_m": h,
                       "trace": {"dining": ["U-S-DINE", "LS-DINE-AREA"], "lounge": ["U-S-LOUNGE", "U-S-FIRE", "LS-LOUNGE-AREA"], "quiet": ["U-S-QUIET"],
                                 "standing": ["U-S-STAND", "LS-STAND-AREA"]}[use], **kw})


def _seatwall_ok(f):
    f["seatwalls"].append({"id": "seat-wall", "height_mm": 450, "width_mm": 450, "trace": ["LS-SEATWALL"]})


def _pot(f, at):
    r = RM(at[0] - .3, at[1] - .3, at[0] + .3, at[1] + .3)
    f["obstacles"].append({"id": "pot-0-plumeria", "rect": r, "trace": ["D-FRANGIPANI", "D-TERRACOTTA"]})
    f["meta"]["pot"] = at


# =====================================================================================================================
def south_A(p):
    """A. TREE COURT. Organising idea: a courtyard room around one focal tree (centralised organisation, Ching).

    A pomegranate stands in a permeable gravel floor that is the dining court; a long built-in bench runs along the rear wall under a pergola
    (quiet seats under the tree, lounge seats facing the hearth); the paved hearth court is east of it; a 1.2 m layered border wraps the screened
    west line; the herb strip takes the 6 h sun on the east fence.
    """
    f = frag()
    west_screen(f)
    ta, tb = p["tree"]
    # bones --------------------------------------------------------------------------------------------------------
    wb = (0.0, 0.15, A, 0.15 + p.get("wdepth", 1.2))                # west border, full length
    herb = p.get('herb', (4.1, B - 0.6, 5.4, B))
    gravel = (1.25, wb[3], A, p["gravel_b1"])                      # dining court floor (permeable), tree dripline inside it
    rear_bench = (A - 0.45, p["bench_b0"], A, p["bench_b1"])
    t0 = p["table_a0"]
    table = (t0, p["table_b0"], t0 + 2.4, p["table_b0"] + 0.9)
    pit, bbq = p["pit"], p["bbq"]
    bbq_r = (bbq[0], bbq[1], bbq[0] + 0.5, bbq[1] + 0.5)
    se = (A - 1.2, 7.0, A, B - 0.6)                                  # south-east mass, 1.2 m deep: 2.0 m from the fire items by construction
    cuts = [wb, herb, gravel, rear_bench, se]
    f["paved_areas"] += C.paving_from(RM(0, 0, A, B), [_rm(c) for c in cuts])
    f["paved_areas"] += []
    # zones (rooms) --------------------------------------------------------------------------------------------------
    dz = (0.0, wb[3], 4.55, B - 0.6)                                  # dining court + hearth: the shared central room (>= 3.46 m2 per dining seat, LS-DINE-AREA)
    _zone(f, "dining", "dining", dz, "gravel", 2.7)
    _zone(f, "lounge", "lounge", (2.0, p["bench_b0"] - 1.3, A, B - 0.6), "paving", 2.7)
    qb = (rear_bench[0] - 0.8, p["bench_b0"], A, p["bench_b0"] + 1.2)
    _zone(f, "quiet", "quiet", (4.3, wb[3], A, wb[3] + 2.4), "gravel", 2.7)
    sz = (0.0, wb[3], 3.0, B - 0.6)
    n_stand = int(((sz[2] - sz[0]) * (sz[3] - sz[1])) / 1.3)
    _zone(f, "standing", "standing", sz, "paving", 2.7, design_people=n_stand)
    _table(f, "dining-table", table, 8)
    _bench(f, "bench-quiet", (A - 0.45, p["bench_b0"], A, p["bench_b0"] + 1.2), "quiet", 2)
    ln = p["bench_b1"] - (p["bench_b0"] + 1.2)
    _bench(f, "bench-rear", (A - 0.45, p["bench_b0"] + 1.2, A, p["bench_b1"]), "lounge", int(ln / C.BENCH_PER_PERSON))
    _seatwall_ok(f)
    _hearth(f, pit, bbq_r, overhead=99)
    f["features"].append({"id": "herb-bed", "kind": "herb_bed", "rect": _rm(herb), "midsummer_sun_hours": round(C.bed_sun(_rm(herb)), 2), "trace": ["U-S-HERB", "LS-HERB-SUN"]})
    # canopy -----------------------------------------------------------------------------------------------------------
    pergola(f, "pergola-dining", _rm((0.15, wb[3], 3.95, p["table_b0"] + 1.9)), 2.7, 0.6)
    pergola(f, "pergola-bench", _rm((A - 1.5, p["bench_b0"] - 0.2, A, p["bench_b1"] + 0.2)), 2.7, 0.6)
    tree(f, "tree-0-punica", "punica_granatum", P(ta, tb))
    _pot(f, p["pot"])
    # path: living door to the hearth court (main, 1.2 m) ---------------------------------------------------------------
    f["paths"].append({"id": "path-door", "class": "main", "width_m": 1.2, "cross_slope_pct": 1.5, "rect": _rm((0.0, DOOR_C - 0.6, 1.2, DOOR_C + 0.6)), "trace": ["U-ACCESS", "LS-PATH-MAIN"]})
    # planting ---------------------------------------------------------------------------------------------------------
    wr = _rm(wb)
    bed(f, "bed-west", wr, row(wr, "x", 0.9, ["salvia_leucantha", "justicia_brandegeeana"], 0.7, run=4, how="min")
        + row(wr, "x", 0.5, ["pennisetum_alopecuroides", "salvia_leucantha"], 0.8, run=3, how="min")
        + row(wr, "x", 0.2, ["jasminum_sambac", "petrea_volubilis"], 1.2, run=2, cap=C.SPREAD_CAP_CLIMBER), "border")
    hr = _rm(herb)
    sr = _rm(se)
    bed(f, "bed-se", sr, row(sr, "y", 0.3, ["jasminum_sambac", "petrea_volubilis"], 1.2, run=1, cap=C.SPREAD_CAP_CLIMBER)
        + row(sr, "y", 0.75, ["justicia_brandegeeana", "salvia_leucantha", "pennisetum_alopecuroides"], 0.6, run=3, how="min"), "border")
    bed(f, "bed-herb", hr, row(hr, "x", 0.3, ["origanum_majorana", "rosmarinus_officinalis"], 0.6, run=3, how="min"), "herb", trace=("U-S-HERB", "LS-HYDROZONE"))
    return f, {"dining": (_rm(dz), 0.30), "lounge": (_rm((2.0, p["bench_b0"] - 1.3, A, B - 0.6)), 0.30), "quiet": (_rm((4.3, wb[3], A, wb[3] + 2.4)), 0.25)}, \
        [c["rect"] for c in f["canopies"]]


# =====================================================================================================================
def south_B(p):
    """B. TWO ROOMS DIVIDED BY A PLANTED SCREEN: a sociable terrace room (this garden) and a quiet garden room (the east yard, see ty_courts).

    Wind decides the south garden: the fire pit sits at the west end (the prevailing wind carries toward the sister plot), a built-in bench
    runs along the screened west line behind it, the BBQ then the dining table follow east in a cooking line, and a deep layered border
    (2.0+ m) closes the east side and carries the pomegranate and the herbs. A rear bench under a pergola completes the room.
    """
    f = frag()
    west_screen(f)
    pit, bbq = p["pit"], p["bbq"]
    bbq_r = (bbq[0], bbq[1], bbq[0] + 0.5, bbq[1] + 0.5)
    t0, tb = p["table_a0"], p["table_b0"]
    table = (t0, tb, t0 + 2.4, tb + 0.9)
    eb0 = p["east_b0"]
    east = (0.5, eb0, A, B)                                          # deep east mass (cut), planted as two beds
    herb = (0.5, B - 0.6, 3.2, B)
    east_mass = (3.2, eb0, A, B)
    east_north = (0.5, eb0, 3.2, B - 0.6)
    gravel = (p["gravel"][0], p["gravel"][1], p["gravel"][2], eb0)  # tree floor between the table and the mass (permeable)
    wbench = (p["wbench"][0], 0.15, p["wbench"][1], 0.6)
    rbench = (A - 0.45, p["rbench"][0], A, p["rbench"][1])
    cuts = [east, gravel, wbench, rbench]
    f["paved_areas"] += C.paving_from(RM(0, 0, A, B), [_rm(c) for c in cuts])
    dz = (0.0, 0.7, 5.2, tb + 0.9 + 1.2)
    _zone(f, "dining", "dining", dz, "paving", 2.7)
    _zone(f, "lounge", "lounge", (0.0, 0.15, A, p["rbench"][1]), "paving", 2.7)
    _zone(f, "quiet", "quiet", (A - 1.6, p["rbench"][0], A, p["rbench"][0] + 1.3), "paving", 2.7)
    sz = (0.0, 0.15, 4.4, eb0)
    _zone(f, "standing", "standing", sz, "paving", 2.7, design_people=int((sz[2] - sz[0]) * (sz[3] - sz[1]) / 1.3))
    _table(f, "dining-table", table, 8)
    _bench(f, "bench-west", wbench, "lounge", int((wbench[2] - wbench[0]) / C.BENCH_PER_PERSON))
    _bench(f, "bench-quiet", (A - 0.45, p["rbench"][0], A, p["rbench"][0] + 1.2), "quiet", 2)
    _bench(f, "bench-rear", (A - 0.45, p["rbench"][0] + 1.2, A, p["rbench"][1]), "lounge", int((p["rbench"][1] - p["rbench"][0] - 1.2) / C.BENCH_PER_PERSON))
    _seatwall_ok(f)
    _hearth(f, pit, bbq_r, overhead=99)
    hr = _rm(herb)
    f["features"].append({"id": "herb-bed", "kind": "herb_bed", "rect": hr, "midsummer_sun_hours": round(C.bed_sun(hr), 2), "trace": ["U-S-HERB", "LS-HERB-SUN"]})
    pergola(f, "pergola-table", _rm((0.15, tb - 0.4, 4.2, tb + 1.3)), 2.7, 0.6)
    pergola(f, "pergola-rear", _rm((A - 1.5, p["rbench"][0] - 0.2, A, p["rbench"][1] + 0.2)), 2.7, 0.6)
    pergola(f, "pergola-west", _rm((wbench[0] - 0.3, 0.15, wbench[2] + 0.3, 1.45)), 2.7, 0.6)
    ta, tbb = p["tree"]
    tree(f, "tree-0-punica", "punica_granatum", P(ta, tbb))
    _pot(f, p["pot"])
    f["paths"].append({"id": "path-door", "class": "main", "width_m": 1.2, "cross_slope_pct": 1.5, "rect": _rm((0.0, DOOR_C - 0.6, 1.2, DOOR_C + 0.6)), "trace": ["U-ACCESS", "LS-PATH-MAIN"]})
    en = _rm(east_north)
    bed(f, "bed-east-north", en, row(en, "x", 0.3, ["justicia_brandegeeana", "salvia_leucantha"], 0.6, run=3, how="min"), "strip")
    em = _rm(east_mass)
    bed(f, "bed-east", em, row(em, "x", 1.9, ["jasminum_sambac", "petrea_volubilis"], 1.2, run=2, cap=C.SPREAD_CAP_CLIMBER)
        + row(em, "x", 1.35, ["justicia_brandegeeana", "salvia_leucantha"], 0.7, run=4, how="min")
        + row(em, "x", 0.8, ["pennisetum_alopecuroides", "salvia_leucantha"], 0.7, run=3, how="min")
        + row(em, "x", 0.3, ["aspidistra_elatior"], 0.45, run=6, how="min"), "mass")
    bed(f, "bed-herb", hr, row(hr, "x", 0.3, ["origanum_majorana", "rosmarinus_officinalis"], 0.6, run=3, how="min"), "herb", trace=("U-S-HERB", "LS-HYDROZONE"))
    return f, {"dining": (_rm(dz), 0.30), "lounge": (_rm((0.0, 0.15, A, p["rbench"][1])), 0.30), "quiet": (_rm((A - 1.6, p["rbench"][0], A, p["rbench"][0] + 1.3)), 0.25)}, [c["rect"] for c in f["canopies"]]


# =====================================================================================================================
def south_C(p):
    """C. TERRACE WRAPPED BY DEEP LAYERED BORDERS, WITH A MAIN AXIS from the living door to a focal point.

    The axis leaves the living door, crosses the flush concealed fire pit (its lid flush with the paving: the first focal point) and ends at a lit
    sculpture place in the rear wall. The cooking line (BBQ) is west of the pit, the dining table east; a deep layered east border carries the
    pomegranate; a rear-west mass and the herb strip close the corners; the west line is the screen with a built-in bench and a gate pergola
    marks the threshold at the door.
    """
    f = frag()
    west_screen(f)
    ax = p["axis_b"]
    pit, bbq = p["pit"], p["bbq"]
    bbq_r = (bbq[0], bbq[1], bbq[0] + 0.5, bbq[1] + 0.5)
    eb0 = p["east_b0"]
    east = (3.4, eb0, A, B)
    corner = (0.7, eb0, 3.4, B - 0.6)
    herb = (0.7, B - 0.6, 3.4, B)
    rw = (A - 1.2, 0.15, A, p["rw_b1"])                           # rear-west mass
    t0, tb = p["table_a0"], p["table_b0"]
    table = (t0, tb, t0 + 2.4, tb + 0.9)
    wbench = (p["wbench"][0], 0.15, p["wbench"][1], 0.6)
    qbench = (A - 0.45, p["qbench_b0"], A, p["qbench_b0"] + 1.2)
    niche = (A - 0.7, ax - 0.35, A - 0.2, ax + 0.35)
    gravel = (p["gravel"][0], p["gravel"][1], p["gravel"][2], eb0)
    cuts = [east, corner, herb, rw, gravel, wbench, qbench]
    f["paved_areas"] += C.paving_from(RM(0, 0, A, B), [_rm(c) for c in cuts])
    dz = (0.0, 0.7, 5.2, eb0)
    _zone(f, "dining", "dining", dz, "paving", 2.7)
    _zone(f, "lounge", "lounge", (0.0, 0.15, A, eb0), "paving", 2.7)
    _zone(f, "quiet", "quiet", (4.5, p["qbench_b0"] - 0.2, A, p["qbench_b0"] + 1.6), "gravel", 2.7)
    sz = (0.0, 0.15, 4.4, eb0)
    _zone(f, "standing", "standing", sz, "paving", 2.7, design_people=int((sz[2] - sz[0]) * (sz[3] - sz[1]) / 1.3))
    _table(f, "dining-table", table, 8)
    _bench(f, "bench-west", wbench, "lounge", max(1, int((wbench[2] - wbench[0]) / C.BENCH_PER_PERSON)))
    _bench(f, "bench-quiet", qbench, "quiet", 2)
    _seatwall_ok(f)
    _hearth(f, pit, bbq_r, overhead=99)
    hr = _rm(herb)
    f["features"].append({"id": "herb-bed", "kind": "herb_bed", "rect": hr, "midsummer_sun_hours": round(C.bed_sun(hr), 2), "trace": ["U-S-HERB", "LS-HERB-SUN"]})
    f["features"].append({"id": "sculpture-place", "kind": "sculpture", "rect": _rm(niche), "trace": ["U-S-QUIET"]})
    f["meta"]["focal"] = "axis from the living door over the fire pit to a lit sculpture place in the rear wall"
    pergola(f, "pergola-gate", _rm((0.0, DOOR_B[0] - 0.2, 1.2, DOOR_B[1] + 0.2)), 2.7, 0.5)
    pergola(f, "pergola-table", _rm((0.15, tb - 0.4, t0 + 3.0, tb + 1.3)), 2.7, 0.6)
    pergola(f, "pergola-rear", _rm((A - 1.5, p["qbench_b0"] - 0.2, A, p["qbench_b0"] + 1.6)), 2.7, 0.6)
    pergola(f, "pergola-west", _rm((wbench[0] - 0.3, 0.15, wbench[2] + 0.3, 1.45)), 2.7, 0.6)
    ta, tbb = p["tree"]
    tree(f, "tree-0-punica", "punica_granatum", P(ta, tbb))
    _pot(f, p["pot"])
    pl = lambda a0, a1: [list(P(a0, ax)), list(P(a1, ax))]            # noqa: E731
    f["paths"].append({"id": "axis-1", "class": "main", "width_m": 1.2, "cross_slope_pct": 1.5, "polyline": pl(0.0, pit[0] - C.PIT_D / 2 - 0.05), "trace": ["U-ACCESS", "LS-PATH-MAIN"]})
    f["paths"].append({"id": "axis-2", "class": "main", "width_m": 1.2, "cross_slope_pct": 1.5, "polyline": pl(pit[0] + C.PIT_D / 2 + 0.05, niche[0] - 0.05), "trace": ["U-ACCESS", "LS-PATH-MAIN"]})
    er, rr = _rm(east), _rm(rw)
    bed(f, "bed-east", er, row(er, "x", 1.35, ["jasminum_sambac", "petrea_volubilis"], 1.2, run=2, cap=C.SPREAD_CAP_CLIMBER)
        + row(er, "x", 0.9, ["justicia_brandegeeana", "salvia_leucantha"], 0.7, run=4, how="min")
        + row(er, "x", 0.4, ["pennisetum_alopecuroides", "aspidistra_elatior"], 0.6, run=4, how="min"), "mass")
    bed(f, "bed-rear-west", rr, row(rr, "y", 0.95, ["jasminum_sambac", "petrea_volubilis"], 1.2, run=1, cap=C.SPREAD_CAP_CLIMBER)
        + row(rr, "y", 0.5, ["salvia_leucantha", "justicia_brandegeeana"], 0.6, run=3, how="min")
        + row(rr, "y", 0.15, ["aspidistra_elatior"], 0.45, run=5, how="min"), "mass")
    cr = _rm(corner)
    bed(f, "bed-east-north", cr, row(cr, "x", 0.3, ["justicia_brandegeeana", "salvia_leucantha"], 0.6, run=3, how="min"), "strip")
    bed(f, "bed-herb", hr, row(hr, "x", 0.3, ["origanum_majorana", "rosmarinus_officinalis"], 0.6, run=3, how="min"), "herb", trace=("U-S-HERB", "LS-HYDROZONE"))
    return f, {"dining": (_rm(dz), 0.30), "lounge": (_rm((0.0, 0.15, A, eb0)), 0.30), "quiet": (_rm((4.5, p["qbench_b0"] - 0.2, A, p["qbench_b0"] + 1.6)), 0.25)}, [c["rect"] for c in f["canopies"]]
