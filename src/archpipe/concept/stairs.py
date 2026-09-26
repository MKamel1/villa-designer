"""Private stairs of the villa as 3D solids, clash-checked against the structure we must keep.

Round 3 drew the stair as a 2D rectangle and every check passed while the flight ran into a column. Here a stair is
treads + landings + a headroom envelope (2.0 m over each tread and landing, AD K card ukadk-stair-headroom-min),
in Revit project coordinates, mm (x along the bar from the street, y toward plot-east, z with the GF FFL = 0, so the
basement FFL is -3000 and the street -1200). The same solids are built in Revit (revit/build_villa_stairs.py) and
Revit's own intersection filter is the independent second check.

Kept structure (villa_env): the nine columns on three storeys, the perimeter beams (250 x 600, ASSUMED section) and
the GF slab, which a stair may pass only through its declared opening.
"""
from __future__ import annotations

from .. import villa_env as E

B_FFL, GF_FFL = E.B, E.GF                     # -3000, 0
HEAD = 2000                                   # AD K Diagram 1.3 (card ukadk-stair-headroom-min)
TREAD_T = 60                                  # tread block thickness drawn under each tread top (visual + clash)
LANDING_T = 150
LANDING_DEPTH = 950                           # half landing: at least the flight width (0.9 m)
YC = E.BAR[1] + 1300                          # spine edge (hall 0.9 m clear), as in concept.villa


def _box(x0, y0, z0, x1, y1, z1, what):
    return {"box": [min(x0, x1), min(y0, y1), min(z0, z1), max(x0, x1), max(y0, y1), max(z0, z1)], "what": what}


def straight(x_top, x_foot, y0, y1, risers, name):
    """A straight flight rising from the basement foot (x_foot) to the GF (x_top); goings are equal."""
    n_go = risers - 1
    going = (x_foot - x_top) / n_go
    rise = (GF_FFL - B_FFL) / risers
    parts = []
    for i in range(1, n_go + 1):                       # tread i sits i risers above the basement
        xa = x_foot - (i - 1) * going
        xb = x_foot - i * going
        top = B_FFL + i * rise
        parts.append(_box(xa, y0, top - TREAD_T, xb, y1, top, f"{name} tread {i}"))
        parts.append(_box(xa, y0, top, xb, y1, top + HEAD, f"{name} headroom over tread {i}"))
    return {"name": name, "parts": parts, "rise": rise, "going": abs(going), "risers": risers,
            "ends": {"foot": ["v", x_foot, y0, y1], "top": ["v", x_top, y0, y1]}}


def u_stair(x0, x1, y_start, risers1, risers2, width, going, name):
    """A U (dog-leg) stair: flight 1 rises across the bar from the spine edge (y_start) to a half landing at the
    facade side, flight 2 returns to the spine edge. Both ends open onto the spine hall."""
    rise = (GF_FFL - B_FFL) / (risers1 + risers2)
    parts = []
    fa = (x0, x0 + width)                              # flight 1 on the street side of the well
    fb = (x1 - width, x1)                              # flight 2 on the rear side
    for i in range(1, risers1):
        ya, yb = y_start + (i - 1) * going, y_start + i * going
        top = B_FFL + i * rise
        parts.append(_box(fa[0], ya, top - TREAD_T, fa[1], yb, top, f"{name} flight 1 tread {i}"))
        parts.append(_box(fa[0], ya, top, fa[1], yb, top + HEAD, f"{name} headroom f1 tread {i}"))
    y_land0 = y_start + (risers1 - 1) * going
    y_land1 = y_land0 + LANDING_DEPTH
    z_land = B_FFL + risers1 * rise
    parts.append(_box(x0, y_land0, z_land - LANDING_T, x1, y_land1, z_land, f"{name} half landing"))
    parts.append(_box(x0, y_land0, z_land, x1, y_land1, z_land + HEAD, f"{name} headroom over the landing"))
    for j in range(1, risers2):
        ya, yb = y_land0 - (j - 1) * going, y_land0 - j * going
        top = z_land + j * rise
        parts.append(_box(fb[0], ya, top - TREAD_T, fb[1], yb, top, f"{name} flight 2 tread {j}"))
        parts.append(_box(fb[0], ya, top, fb[1], yb, top + HEAD, f"{name} headroom f2 tread {j}"))
    y_top = y_land0 - (risers2 - 1) * going
    return {"name": name, "parts": parts, "rise": rise, "going": going, "risers": risers1 + risers2,
            "landing": [x0, y_land0, x1, y_land1], "top_y": y_top,
            "ends": {"foot": ["h", y_start, fa[0], fa[1]], "top": ["h", y_top, fb[0], fb[1]]}}


# ---- the options ------------------------------------------------------------------------------------------------
def r3_party_flight():
    """Round 3 as drawn (the defect): 16 x 187.5 / 240, y -28471..-27471, top at x 3817 on the street terrace."""
    return straight(3817, 7417, E.BAR[1] + 200, E.BAR[1] + 1200, 16, "r3 party-wall flight")


def u_in_old_bay():
    """In the old stair bay (DWG A-DETL opening x 7377-9387; old PDF U-stair, goings 280), between the column faces
    x 7377 and 9227, the half landing short of the facade columns' inner face (y -24101)."""
    return u_stair(7377, 9227, YC, 9, 8, 900, 280, "U-stair in the old bay")


def party_flight_fixed():
    """Party-wall flight corrected: off the (assumed) party-wall beam, top landing inside the bar clear of column
    1590377 (x 3617-3977), 17 x 176.5 / 280."""
    y0 = E.BAR[1] + 250                               # clear of a 250-wide beam along the party wall
    return straight(3977 + 900, 3977 + 900 + 16 * 280, y0, y0 + 950, 17, "party-wall flight, corrected")


def options():
    return [r3_party_flight(), u_in_old_bay(), party_flight_fixed()]


# ---- structure ----------------------------------------------------------------------------------------------------
REVIT_IDS = dict(zip([tuple(c) for c in E.COLUMNS], E.REVIT_GF_COLUMN_IDS))


def structure():
    out = []
    for c in E.COLUMNS:
        rid = REVIT_IDS[tuple(c)]
        for z0, z1, tag in ((B_FFL, GF_FFL, "basement copy of"), (GF_FFL, E.APT, "GF")):
            out.append({"box": [c[0], c[1], z0, c[2], c[3], z1], "what": f"column {tag} {rid}", "kind": "column"})
    spec = E.spec()
    for e in spec["elements"]:
        if e["category"] == "StructuralFraming" and e["z1"] == GF_FFL:
            xs, ys = [p[0] for p in e["pts"]], [p[1] for p in e["pts"]]
            out.append({"box": [min(xs), min(ys), e["z0"], max(xs), max(ys), e["z1"]],
                        "what": f"beam {e['id']} (assumed 250x600)", "kind": "beam"})
    return out


def _overlap(a, b, tol=1.0):
    d = [min(a[i + 3], b[i + 3]) - max(a[i], b[i]) for i in range(3)]
    return all(v > tol for v in d), d


def clashes(stair, opening=None):
    """Treads, landings and headroom against columns and beams; plus where the GF slab (z -200..0) must be open.
    `opening` = [x0, y0, x1, y1] of the declared GF slab opening; anything needing more is reported."""
    hits = []
    for part in stair["parts"]:
        for s in structure():
            ok, d = _overlap(part["box"], s["box"])
            if ok:
                hits.append({"stair_part": part["what"], "structure": s["what"], "kind": s["kind"],
                             "overlap_mm": [round(v) for v in d]})
    slab = [p["box"] for p in stair["parts"] if p["box"][5] > GF_FFL - 200 + 1 and p["box"][2] < GF_FFL - 1]
    need = None
    if slab:
        need = [min(b[0] for b in slab), min(b[1] for b in slab), max(b[3] for b in slab), max(b[4] for b in slab)]
    outside = []
    if need and opening:
        for p in stair["parts"]:
            b = p["box"]
            if b[5] > GF_FFL - 200 + 1 and b[2] < GF_FFL - 1 and not (
                    b[0] >= opening[0] - 1 and b[1] >= opening[1] - 1 and b[3] <= opening[2] + 1 and b[4] <= opening[3] + 1):
                outside.append(p["what"])
    return {"stair": stair["name"], "hits": hits, "slab_opening_needed": need, "outside_declared_opening": outside}
