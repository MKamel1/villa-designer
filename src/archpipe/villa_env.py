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
SISTER_FACE = round(2 * AXIS_Y - BAR[1], 2)  # the sister's face across the core (-31160.32)
# The 2.49 m strip between the two villas is the SHARED CORE (old PDF plans, client 2026-09-25): entrance lobby,
# the main stair to the apartments, an air shaft, a lobby, a lift, then the two GF bathrooms staggered (the sister's
# first, ours at the rear, CAD). In the basement both ends of the core are split on the axis between the villas.
# Positions along x: walls crossing the core measured on the PDFs (PDF, +-0.15 m), scaled on the CAD length 18.98 m.
CORE_GF = [  # (id, x0, x1, what)
    ("core-entrance", 3617, 8506, "shared entrance lobby from the street gate (+0.00 FFL of the old plan = GF)"),
    ("core-stair", 8506, 12778, "shared main stair to the apartments (not in the DWG or Revit)"),
    ("core-shaft-landing", 12778, 14134, "stair landing and air shaft"),
    ("core-lobby", 14134, 15928, "shared lobby, doors to both villas"),
    ("core-lift", 15928, 17408, "X-marked box with a 0.80 door: most likely the lift"),
    ("sister-bath", 17408, 19604, "the sister's GF bathroom (staggered with ours)"),
]
CORE_B_OURS_FRONT = (3617, 6940)             # PDF basement: kitchen zone split on the axis
CORE_B_OURS_REAR = (17268, 22597)            # PDF basement: split on the axis under the GF bathrooms
SHAFT = (12838, -30271, 14074, -28671)     # PDF: air shaft on our side of the landing, 1.5 m wide, all floors
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
# Building face to the fence's INNER face, measured on the old GF PDF (client: "the fence offset can be used from the
# pdf"); the PDF's own 4.02 front dimension runs to the fence's outer face (3.74 + 0.25 = 3.99).
OFFSET_N, OFFSET_E, OFFSET_S = 3740, 2990, 5710
FENCE_H, FENCE_T = 4000, 250                  # BRIEF: 4.00 m from basement level; PDF: drawn 0.25 thick
NEIGHBOUR_H = 12000                           # BRIEF 12 m; measured from their basement level (ASSUMED datum)
STREET_WIDTH = 10000                          # ASSUMED
BEAM_W, BEAM_D = 250, 600                     # ASSUMED section; perimeter only (client)
WINDOW_SILL, WINDOW_H = 900, 1500             # ASSUMED, neighbour windows only

ASSUMPTIONS = [   # confirmed by the client 2026-09-25 unless marked OPEN
    "Floor-to-floor 3.00 m for the apartment above as for our ground floor.",
    "Neighbour buildings are 12 m tall from their basement level (-1.80), four 3 m storeys, windows at our current "
    "window positions (sill 0.9, height 1.5) on every storey.",
    "Neighbour plots mirror ours, set back from the shared fence as we are (PDF offsets).",
    "Perimeter beams 250 x 600 mm under the GF, apartment and roof slabs.",
    "The street-side strip (CAD, 1.83 m deep x 5.08 m, in front of the living room, beside the shared entrance) is "
    "part of our GF with no use yet; the old plan asked whether to open it to the villa or to the stair, or close "
    "it. The apartment repeats it. The old PDF draws it about 1.0-1.3 m deep; the CAD governs building geometry.",
    "The shared entrance steps run from the street gate over the sunken front yard to the core's GF entrance.",
    "Street width 10 m (context only). No fence between our yard and the sister's.",
    "The lift position is read from an X-marked box with a door on both floors (OPEN: confirm it is a lift).",
]
QUESTIONS = []   # all answered 2026-09-25 (docs/villa/environment-model.md)


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


def footprint_b():
    """Our basement outline: the bar plus our halves of the core's two ends (split on the axis), counter-clockwise."""
    bx0, by0, bx1, by1 = BAR
    (f0, f1), (r0, r1) = CORE_B_OURS_FRONT, CORE_B_OURS_REAR
    return [(bx0, by1), (bx0, AXIS_Y), (f1, AXIS_Y), (f1, by0), (r0, by0), (r0, AXIS_Y), (bx1, AXIS_Y), (bx1, by1)]


def plot():
    """The whole plot (ours + sister) to the fence's OUTER face: x0, y0, x1, y1."""
    sister_outer = round(2 * AXIS_Y - BAR[3], 2)
    t = FENCE_T
    return (BAR[0] - OFFSET_N - t, sister_outer - OFFSET_E - t, BAR[2] + OFFSET_S + t, BAR[3] + OFFSET_E + t)


def yard():
    """Our sunken yard: the east strip plus our halves (to the axis) of the street and rear strips. The strip
    between the villas is the shared core, not yard."""
    px0, py0, px1, py1 = plot()
    bx0, by0, bx1, by1 = BAR
    return [(px0, py1), (px0, AXIS_Y), (bx0, AXIS_Y), (bx0, by1), (bx1, by1), (bx1, AXIS_Y), (px1, AXIS_Y), (px1, py1)]


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
    slabs = [{"id": "slab-%s" % tags[z], "level": name, "pts": footprint_b() if z == B else fp,
              "note": "our footprint slab (CAD outline%s)" % (" + our halves of the core ends" if z == B else "")}
             for name, z in LEVELS if z in tags]
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
    # the shared core between the villas (not ours), per storey; the apartment storey repeats the GF (assumed)
    for x0, x1, tag in ((CORE_B_OURS_FRONT[1], CORE_B_OURS_REAR[0], "core-B-shared"),):
        elements.append(_box(tag, "GenericModel", (x0, SISTER_FACE, x1, by0), B, GF - 200,
                             "shared basement core: lobby, main stair, shaft, lift (PDF)"))
    for (x0, x1), tag in ((CORE_B_OURS_FRONT, "sister-core-B-front"), (CORE_B_OURS_REAR, "sister-core-B-rear")):
        elements.append(_box(tag, "GenericModel", (x0, SISTER_FACE, x1, AXIS_Y), B, GF - 200,
                             "the sister's half of the basement core end (PDF)"))
    for z0, lv in ((GF, "GF"), (APT, "APT")):
        for ident, x0, x1, what in CORE_GF:
            elements.append(_box("%s-%s" % (ident, lv), "GenericModel", (x0, SISTER_FACE, x1, by0), z0, z0 + 2800,
                                 what + ("" if lv == "GF" else " (apartment storey, assumed as GF)")))
    elements.append(_box("core-shaft", "GenericModel", SHAFT, B,
                         ROOF + 1000, "air shaft beside our party wall, all floors, open to the sky (PDF)"))
    elements.append(_box("entrance-steps", "GenericModel", (px0 + FENCE_T, SISTER_FACE, bx0, by0), STREET, GF,
                         "shared entrance steps from the street gate up to the core's GF entrance (PDF)"))
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
        "plot": list(plot()), "axis_y": AXIS_Y, "footprint": fp, "footprint_b": footprint_b(),
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
