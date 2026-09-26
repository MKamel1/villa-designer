"""Environment model of the real villa (Sheikh Zayed): plot, sunken yard, fence, neighbours, sister villa, the
apartment above, and the structure to keep. It generates the spec that `revit/build_villa_env.py` builds in a COPY
of omar.rvt.

Coordinates are Revit project internal coordinates in mm, which the client's CAD export shares exactly: the DWG
"01-GROUND_FLOOR_PLAN" (units m) has the same extents as the Revit model's floor. z = 0 is the ground-floor FFL
("Level 1"), which the brief puts at street +1.20. So street = -1200 and basement = -3000.

Model axes against the plot, derived from the CAD rather than assumed:
  - model -x = plot-north (street). The entrance door and the front terrace are on the x-min face, and the Revit
    yard floor stops exactly 2.5 m past the +y face (the brief's plot-east offset).
  - model +y = plot-east, model +x = plot-south (rear), model -y = the sister villa (plot-west).
  - the twin is mirrored about y = AXIS_Y: mirroring our columns reproduces the Revit sister columns (tested).

Every value names its source: CAD (measured from the DWG), REVIT (read from the model), BRIEF (client answer,
docs/villa/brief-2026-09.md) or ASSUMED (listed in ASSUMPTIONS for the client to confirm).
"""
from __future__ import annotations

import json
from pathlib import Path

# --- measured -------------------------------------------------------------------------------------------------
BAR = (3617, -28671, 22597, -23591)          # CAD A-WALL outer faces: x0, y0, x1, y1 (18.98 x 5.08 m)
BUMP = (19604, -31311, 22324, -28671)        # CAD: bathroom projection on the sister side
FRONT = (1787, -28671, 3617, -23591)         # CAD I-WALL: street-side terrace enclosure at GF (use ASSUMED)
AXIS_Y = -29915.66                           # REVIT: mirror axis of the twin (mean of our/sister column faces)
# CAD S-COLS: our nine columns, (x0, y0, x1, y1). The Revit GF columns coincide to < 1 mm.
COLUMNS = [
    (7017, -24101, 7377, -23591), (9227, -24101, 9567, -23591), (11197, -24251, 11537, -23591),
    (14902, -23951, 15412, -23591), (22237, -28671, 22597, -28161), (3617, -24151, 3977, -23641),
    (3617, -28671, 3977, -28161), (18367, -23951, 18877, -23591), (22237, -24101, 22597, -23591),
]
REVIT_GF_COLUMN_IDS = [1585908, 1585915, 1585917, 1585924, 1585933, 1585938, 1590377, 1591282, 1591340]
# CAD A-GLAZ: current windows, used only to place the NEIGHBOURS' windows ("similar positions to ours").
EAST_FACE_WINDOWS_X = [(4647, 6247), (7797, 8797), (12437, 14007), (16307, 17757), (19967, 21417)]
REAR_FACE_WINDOWS_Y = [(-26521, -25071)]
PARTY_FACE_WINDOWS_X = [(14869, 16319)]

# --- levels (z of FFL / structural top, mm) ---------------------------------------------------------------------
STREET = -1200                                # BRIEF: GF at street +1.20
B, GF, APT, ROOF = -3000, 0, 3000, 6000       # BRIEF basement -1.80; REVIT columns 0..3000; APT/ROOF ASSUMED same 3.0 m
LEVELS = [("Street +-0.00", STREET), ("B -1.80", B), ("GF +1.20", GF), ("APT +4.20 (not ours)", APT),
          ("APT roof +7.20", ROOF)]

# --- site -----------------------------------------------------------------------------------------------------
LATITUDE, LONGITUDE, TIME_ZONE = 30.040260, 30.961099, 2.0   # BRIEF maps link, resolved 2026-09-25
STREET_FACADE_AZIMUTH = 290.0                 # BRIEF: the street (model -x) facade faces true azimuth ~290
OFFSET_N, OFFSET_E, OFFSET_S = 2500, 2500, 5000               # BRIEF yard offsets to the fence
FENCE_H, FENCE_T = 4000, 200                  # BRIEF: concrete fence 4.00 m from basement level; thickness ASSUMED
NEIGHBOUR_H = 12000                           # BRIEF 12 m; measured from their basement level (ASSUMED datum)
STREET_WIDTH = 10000                          # ASSUMED
BEAM_W, BEAM_D = 250, 600                     # ASSUMED section; perimeter only (client)
WINDOW_SILL, WINDOW_H = 900, 1500             # ASSUMED, neighbour windows only

ASSUMPTIONS = [
    "Floor-to-floor 3.00 m for the apartment above as for our ground floor (Revit columns 0-3000); the existing "
    "Revit slab at 2900-3100 is 100 mm higher, within the close-value band.",
    "The 2.5 m street-side offset is measured from the building face (x = 3617), giving the plot edge at x = 1117. "
    "The old Revit yard floor stopped at x = 878 (2.74 m): a 10 % difference, so confirm.",
    "The street-side enclosure (x 1787-3617, CAD I-WALL) is a ground-floor terrace or entrance landing over the "
    "sunken yard; the apartment above repeats it.",
    "Neighbour buildings are 12 m tall measured from their basement level (-1.80), i.e. four 3 m storeys, with "
    "windows at our current window positions, sill 0.9 m, height 1.5 m on every storey.",
    "Neighbour plots mirror ours: east neighbour 2.5 m from the shared fence, rear neighbour 5.0 m from it.",
    "Perimeter beams 250 x 600 mm (top at slab top, outer face flush) under the GF, apartment floor and roof slabs, "
    "following the full outline including the bathroom projection.",
    "The sister villa mirrors our bar and terrace; the bathroom projection is ours only (its mirror falls on it).",
    "Street width 10 m (not needed for the design, drawn for context).",
    "No fence between our yard and the sister's yard (none was mentioned).",
]
QUESTIONS = [
    "The party-side facade (y = -28671) has only corner columns: an 18.98 m span. Are there columns or bearing "
    "walls along it that the model is missing?",
    "Is the bathroom projection (2.72 x 2.64 m) ours, and does it reach the sister's facade (0.15 m past it)?",
    "How is the apartment above reached (stair, lift, entrance), and does that route cross our plot?",
    "How does one get from the street (+-0.00) down to the yard (-1.80) and up to the ground floor (+1.20)?",
    "Is the 2.49 m gap between our building and the sister's ours up to the mirror line, and is there a divider?",
    "Revit has a column at x 22.4, y -31.4 (sister side, at the projection's corner) that the CAD does not show.",
]


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def mirror_y(pts, axis=AXIS_Y):
    return [(x, round(2 * axis - y, 2)) for x, y in reversed(pts)]


def mirror_box(b, axis=AXIS_Y):
    x0, y0, x1, y1 = b
    return (x0, round(2 * axis - y1, 2), x1, round(2 * axis - y0, 2))


def footprint():
    """Our building outline (bar + bathroom projection), counter-clockwise."""
    bx0, by0, bx1, by1 = BAR
    px0, py0, px1, _ = BUMP
    return [(bx0, by1), (bx0, by0), (px0, by0), (px0, py0), (px1, py0), (px1, by0), (bx1, by0), (bx1, by1)]


def plot():
    """The whole plot (ours + sister): x0, y0, x1, y1."""
    sister_face = round(2 * AXIS_Y - BAR[3], 2)
    return (BAR[0] - OFFSET_N, sister_face - OFFSET_E, BAR[2] + OFFSET_S, BAR[3] + OFFSET_E)


def yard():
    """Our sunken yard: the east strip plus our halves of the street and rear strips, and our half of the gap
    to the sister, as one simple polygon wrapped around the building."""
    px0, py0, px1, py1 = plot()
    bx0, by0, bx1, by1 = BAR
    qx0, _, qx1, _ = BUMP
    return [(px0, py1), (px0, AXIS_Y), (qx0, AXIS_Y), (qx0, by0), (bx0, by0), (bx0, by1), (bx1, by1), (bx1, by0),
            (qx1, by0), (qx1, AXIS_Y), (px1, AXIS_Y), (px1, py1)]


def polygon_area(pts):
    return abs(sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
                   for i in range(len(pts)))) / 2e6


def _box(ident, category, b, z0, z1, note):
    return {"id": ident, "kind": "box", "category": category, "pts": rect(*b), "z0": z0, "z1": z1, "note": note}


def _prism(ident, category, pts, z0, z1, note):
    return {"id": ident, "kind": "box", "category": category, "pts": pts, "z0": z0, "z1": z1, "note": note}


def perimeter_beams(level_z):
    """Beams 250 wide inside each outer edge of the footprint, top at the slab top."""
    pts = footprint()
    out = []
    n = len(pts)
    for i in range(n):
        (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
        # inward normal of a counter-clockwise polygon is to the left of the edge direction
        dx, dy = (x1 - x0), (y1 - y0)
        length = (dx * dx + dy * dy) ** 0.5
        nx, ny = -dy / length * BEAM_W, dx / length * BEAM_W
        quad = [(x0, y0), (x1, y1), (x1 + nx, y1 + ny), (x0 + nx, y0 + ny)]
        out.append(_prism("beam-%d-e%d" % (level_z, i), "StructuralFraming", [(round(x), round(y)) for x, y in quad],
                          level_z - BEAM_D, level_z, "perimeter beam %dx%d ASSUMED section" % (BEAM_W, BEAM_D)))
    return out


def windows_on_face(prefix, axis, face, outward, spans, storeys):
    out = []
    for z in storeys:
        for i, (a, b) in enumerate(spans):
            if axis == "y":      # a face at y = face, spans along x
                box = (a, min(face, face + outward * 60), b, max(face, face + outward * 60))
            else:                # a face at x = face, spans along y
                box = (min(face, face + outward * 60), a, max(face, face + outward * 60), b)
            out.append(_box("%s-w%d-z%d" % (prefix, i, z), "Windows", box, z + WINDOW_SILL,
                            z + WINDOW_SILL + WINDOW_H, "neighbour window, position ASSUMED like ours"))
    return out


def spec():
    px0, py0, px1, py1 = plot()
    bx0, by0, bx1, by1 = BAR
    twin_w = by1 - round(2 * AXIS_Y - by1, 2)            # 12.65 m, the twin's full width
    fp = footprint()
    elements = []
    # our slabs (real Floors): basement floor, GF, apartment floor, apartment roof
    tags = {B: "B", GF: "GF", APT: "APT", ROOF: "ROOF"}
    slabs = [{"id": "slab-%s" % tags[z], "level": name, "pts": fp,
              "note": "our footprint slab (CAD outline)"} for name, z in LEVELS if z in tags]
    slabs.append({"id": "slab-GF-front", "level": "GF +1.20", "pts": rect(*FRONT),
                  "note": "street-side terrace/landing, ASSUMED use"})
    slabs.append({"id": "yard-ours", "level": "B -1.80", "pts": yard(), "note": "our sunken yard at -1.80 (BRIEF)"})
    slabs.append({"id": "yard-sister", "level": "B -1.80", "pts": mirror_y(yard()),
                  "note": "sister's yard, mirrored (context)"})
    # fence: the whole plot perimeter, inside the plot line
    t = FENCE_T
    for ident, b in (("fence-street", (px0, py0, px0 + t, py1)), ("fence-east", (px0, py1 - t, px1, py1)),
                     ("fence-rear", (px1 - t, py0, px1, py1)), ("fence-west", (px0, py0, px1, py0 + t))):
        elements.append(_box(ident, "GenericModel", b, B, B + FENCE_H, "concrete fence 4.00 m from basement (BRIEF)"))
    # the apartment above ours and the sister (with its own apartment)
    elements.append(_prism("apartment-above", "GenericModel", fp, APT, ROOF - 200, "identical apartment above our GF (BRIEF)"))
    elements.append(_prism("apartment-above-front", "GenericModel", rect(*FRONT), APT, APT + 1100,
                           "its street-side terrace parapet zone, ASSUMED"))
    sister = mirror_box(BAR)
    elements.append(_box("sister", "GenericModel", sister, B, ROOF, "sister villa + its apartment, mirrored (BRIEF)"))
    elements.append(_box("sister-front", "GenericModel", mirror_box(FRONT), GF - 200, GF, "sister's terrace, mirrored"))
    elements += windows_on_face("sister", "y", sister[3], +1, PARTY_FACE_WINDOWS_X, (B, GF, APT))
    # neighbours, 12 m from their basement level
    nz1 = B + NEIGHBOUR_H
    east = (bx0, py1 + OFFSET_E, bx1, py1 + OFFSET_E + twin_w)
    rear = (px1 + OFFSET_S, round(2 * AXIS_Y - by1, 2), px1 + OFFSET_S + (bx1 - bx0), by1)
    rear_east = (rear[0], east[1], rear[2], east[3])
    storeys = list(range(B, nz1 - 1, 3000))
    elements.append(_box("neighbour-east", "GenericModel", east, B, nz1, "neighbour, 12 m (BRIEF), plot mirrored ASSUMED"))
    elements.append(_box("neighbour-rear", "GenericModel", rear, B, nz1, "neighbour, 12 m (BRIEF), plot mirrored ASSUMED"))
    elements.append(_box("neighbour-rear-east", "GenericModel", rear_east, B, nz1, "neighbour, 12 m, ASSUMED"))
    elements += windows_on_face("neighbour-east", "y", east[1], -1, EAST_FACE_WINDOWS_X, storeys)
    rear_spans = REAR_FACE_WINDOWS_Y + [tuple(sorted(round(2 * AXIS_Y - v, 2) for v in s)) for s in REAR_FACE_WINDOWS_Y]
    elements += windows_on_face("neighbour-rear", "x", rear[0], -1, rear_spans, storeys)
    elements.append(_box("street", "GenericModel", (px0 - STREET_WIDTH, py0, px0, py1), STREET - 200, STREET,
                         "street at +-0.00, width ASSUMED"))
    for z in (GF, APT, ROOF):
        elements += perimeter_beams(z)
    return {
        "units": "mm", "origin": "Revit project internal = CAD", "levels": [{"name": n, "z": z} for n, z in LEVELS],
        "site": {"latitude": LATITUDE, "longitude": LONGITUDE, "time_zone": TIME_ZONE,
                 "street_facade_azimuth": STREET_FACADE_AZIMUTH, "street_facade_direction": [-1, 0]},
        "plot": list(plot()), "axis_y": AXIS_Y, "footprint": fp,
        "columns": {"revit_ids": REVIT_GF_COLUMN_IDS, "cad": COLUMNS,
                    "copies": [{"base": "B -1.80", "top": "GF +1.20", "dz": B - GF},
                               {"base": "APT +4.20 (not ours)", "top": "APT roof +7.20", "dz": APT - GF}],
                    "gf": {"base": "GF +1.20", "top": "APT +4.20 (not ours)"}},
        "delete_revit_ids": [1586207, 1586214, 1586627],   # whole-plot floors at GF and +2.9..3.1: they cover the yard
        "slabs": slabs, "elements": elements, "assumptions": ASSUMPTIONS, "questions": QUESTIONS,
    }


def write(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(spec(), indent=1), encoding="utf-8")
    return path
