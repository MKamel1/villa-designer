"""D1's assumed shaded Mediterranean garden, constrained to the modeled yard.

The south planting zone is the southern end of our east yard. The land below
the rear boundary belongs to the sister plot and is never dressed as ours.
All positions are metres in the same frame as the villa scene.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from math import cos, hypot, radians, sin, tan
from pathlib import Path

from .. import solar, villa_env as E
from . import villa_furniture_detail as FD
from .authored_values import fill_defaults, override

GROUND = -3.0
PLOT = tuple(v / 1000 for v in E.plot())
YARD = tuple((x / 1000, y / 1000) for x, y in E.yard())

# Our own building's occupied volume for the tree/shrub-extent guard: the GF footprint rectangles already used by
# facade_distance (FRONT/BAR/BUMP), from z=0 (GF FFL) to E.APT (3.0 m, villa_env: the level above our own GF, "not
# ours" but structurally solid over the same footprint) -- a single storey, which is what the defect's photos show
# (canopy inside the parents' bedroom and the garden-living ceiling, both GF rooms).
BUILDING_RECTS = tuple(tuple(v / 1000 for v in r) for r in (E.FRONT, E.BAR, E.BUMP))
BUILDING_HEIGHT = E.APT / 1000


def inside_yard(x, y):
    # A point on a garden-door threshold counts as inside the yard.
    if not (PLOT[0] <= x <= PLOT[2] and PLOT[1] <= y <= PLOT[3]):
        return False
    inside = False
    for (xa, ya), (xb, yb) in zip(YARD, YARD[1:] + YARD[:1]):
        if min(xa, xb) - 1e-6 <= x <= max(xa, xb) + 1e-6 and min(ya, yb) - 1e-6 <= y <= max(ya, yb) + 1e-6:
            if abs((xb - xa) * (y - ya) - (yb - ya) * (x - xa)) < 1e-6:
                return True
        if (ya > y) != (yb > y) and x < (xb - xa) * (y - ya) / (yb - ya) + xa:
            inside = not inside
    return inside


def facade_distance(x, y):
    # Include the front ground-floor projection: overlooking it left the
    # first west-wing tree only 0.69 m from that facade.
    rects = [(v / 1000 for v in r) for r in (E.FRONT, E.BAR, E.BUMP)]
    distances = []
    for rect in rects:
        x0, y0, x1, y1 = rect
        dx = max(x0 - x, 0, x - x1)
        dy = max(y0 - y, 0, y - y1)
        distances.append(hypot(dx, dy))
    return min(distances)


def _load_prop_bounds():
    """Native glTF (Y-up, metres) world-AABB per library prop, from the checked-in `bounds_m` field of
    ops/workstation/library-manifest.json (ops/workstation/fetch_asset_library.py measures and drift-checks it;
    docs/LEARNINGS.md 2026-09-28)."""
    path = Path(__file__).resolve().parents[3] / "ops" / "workstation" / "library-manifest.json"
    manifest = json.loads(path.read_text())
    return {p["id"]: (tuple(p["bounds_m"]["min"]), tuple(p["bounds_m"]["max"]))
            for p in manifest.get("props", []) if "bounds_m" in p}


PROP_BOUNDS = _load_prop_bounds()


def prop_world_box(asset, position, rotation_deg, scale):
    """World-space AABB (x0, y0, z0, x1, y1, z1) a prop occupies, reproducing villa_scene.import_props: Blender's
    glTF importer converts native Y-up (x, y, z) to scene Z-up (x, -z, y) (verified 2026-09-28 against a headless
    Blender 4.2.9 import of tree_small_02 and shrub_02 -- both matched this pure-Python transform to < 1e-4 m), the
    anchor then scales uniformly, yaws about Z (only rotation_deg[2] is honoured: every landscape prop today is
    upright with rotation_deg [0, 0, 0], and a future tilted prop is out of scope here), and finally re-seats the
    whole prop so its lowest point sits exactly at `position[2]` (import_props' `bottom` correction)."""
    (gx0, gy0, gz0), (gx1, gy1, gz1) = PROP_BOUNDS[asset]
    lx0, lx1 = gx0, gx1                      # scene x = gltf x
    ly0, ly1 = -gz1, -gz0                    # scene y = -gltf z
    lz0, lz1 = gy0, gy1                      # scene z = gltf y (height)
    corners = [(lx0, ly0), (lx1, ly0), (lx1, ly1), (lx0, ly1)]
    yaw = radians(rotation_deg[2])
    c, s = cos(yaw), sin(yaw)
    sx, sy, sz = (scale, scale, scale) if isinstance(scale, (int, float)) else scale
    rotated = [(sx * x * c - sy * y * s, sx * x * s + sy * y * c) for x, y in corners]
    px, py, pz = position
    xs = [px + rx for rx, _ in rotated]
    ys = [py + ry for _, ry in rotated]
    height = sz * (lz1 - lz0)
    return min(xs), min(ys), pz, max(xs), max(ys), pz + height


def _rect_overlap_area(a, b):
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return max(0.0, min(ax1, bx1) - max(ax0, bx0)) * max(0.0, min(ay1, by1) - max(ay0, by0))


def _box_perimeter_points(x0, y0, x1, y1, step=0.1):
    """Sample points around a rectangle's edges (not just its 4 corners): our yard polygon is L-shaped, and a
    corner-only test can miss a bite the building's re-entrant corner takes out of a wide canopy's footprint."""
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    for xa, ya, xb, yb in ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)):
        length = hypot(xb - xa, yb - ya)
        n = max(1, int(length / step))
        for k in range(1, n):
            t = k / n
            pts.append((xa + (xb - xa) * t, ya + (yb - ya) * t))
    return pts


def garden_level_rooms(lay):
    """Room rectangles on the garden's own storey (level B). The north strip of the modeled yard lies over the
    basement store-ramp, cinema, guest WC and dirty kitchen, so the GF rectangles alone let the north planting bed
    be placed inside the dirty kitchen (D1 draft render v17, 2026-09-28)."""
    return tuple((r["rect"][0], r["rect"][1], r["rect"][2], r["rect"][3], name)
                 for name, r in lay["rooms"].items() if r.get("level") == "B")


DECK = (6.877, -23.591, 12.777, -20.601)
ROOF = (12.777, -23.591, 15.412, -20.601)
TOP = (DECK[0], DECK[1], ROOF[2], DECK[3])
RAIL_CLEAR = 0.12  # ASSUMED rail mounting strip; rails remain in revit_spec.


def _inside_rect(box, rect, margin=0.0):
    return (rect[0] + margin <= box[0] and rect[1] + margin <= box[1] and
            box[2] <= rect[2] - margin and box[3] <= rect[3] - margin)


def extent_violations(props, rooms=()):
    """For every placed prop with known library bounds: (a) its full world box (trunk + canopy) must not enter our
    building's occupied volume -- may overhang paving, must not overhang the villa; (b) it must not stand inside
    any garden-level room (`rooms`, from garden_level_rooms); (c) its footprint must stay inside our plot and our
    modeled yard, not the sister plot, the street or the neighbours. Returns a list of (prop id, reason) pairs;
    empty means every prop passes."""
    out = []
    for p in props:
        asset = p["asset"]
        if asset not in PROP_BOUNDS:
            continue
        x0, y0, z0, x1, y1, z1 = prop_world_box(asset, p["position"], p.get("rotation_deg", [0, 0, 0]),
                                                 p.get("scale", 1.0))
        for rx0, ry0, rx1, ry1, name in (() if z0 >= 0 else rooms):
            if _rect_overlap_area((x0, y0, x1, y1), (rx0, ry0, rx1, ry1)) > 1e-6:
                out.append((p["id"], "world box (%.2f,%.2f)-(%.2f,%.2f) enters the garden-level room %s"
                            % (x0, y0, x1, y1, name)))
                break
        if z1 > 0 and z0 < BUILDING_HEIGHT:           # the prop's own z-range overlaps our GF storey's (0..APT)
            for rect in BUILDING_RECTS:
                if _rect_overlap_area((x0, y0, x1, y1), rect) > 1e-6:
                    out.append((p["id"], "world box (%.2f,%.2f)-(%.2f,%.2f) enters the building footprint %s"
                                % (x0, y0, x1, y1, tuple(round(v, 3) for v in rect))))
                    break
        if p.get("zone") == "top":
            if not (_inside_rect((x0, y0, x1, y1), DECK, RAIL_CLEAR) or
                    _inside_rect((x0, y0, x1, y1), ROOF, RAIL_CLEAR)):
                out.append((p["id"], "top prop leaves the deck/roof rectangle or rail line"))
        else:
            outside = [pt for pt in _box_perimeter_points(x0, y0, x1, y1) if not inside_yard(*pt)]
            if outside:
                out.append((p["id"], "%d of its footprint's sampled points leave the modeled yard/plot (e.g. %.2f,%.2f)"
                            % (len(outside), outside[0][0], outside[0][1])))
    return out


def _box(x0, y0, z0, x1, y1, z1):
    a = [x0, y0, z0]; b = [x1, y0, z0]; c = [x1, y1, z0]; d = [x0, y1, z0]
    e = [x0, y0, z1]; f = [x1, y0, z1]; g = [x1, y1, z1]; h = [x0, y1, z1]
    return [[d, c, b, a], [e, f, g, h], [a, b, f, e], [b, c, g, f],
            [c, d, h, g], [d, a, e, h]]


def _quad(x0, y0, x1, y1, z):
    return [[[x0, y0, z], [x1, y0, z], [x1, y1, z], [x0, y1, z]]]


# Clear walking rectangles terminate at the actual thresholds. The 0.914 m
# width exceeds Time-Saver 2nd ed., p. 340-9, card lts-path-width-oneway-900.
PATHS = {
    "dining": (16.432, -23.591, 17.346, -21.35),
    "living-north": (20.100, -23.591, 21.014, -21.35),
    "living-east": (22.597, -26.588, 25.10, -25.674),
    "lounge-west": (1.00, -26.613, 3.617, -25.699),
    "study": (7.820, -23.591, 8.734, -20.601),
}

# Deepened from the v17 draft's single-row beds so a 3-layer border fits.
# Each depth is chosen against the real constraints in this yard (checked
# with inside_yard/route/room, not assumed): north and west have no nearby
# route or room and take the full 3-layer depth; east stays clear of the
# living-east 0.914 m route (x <= 25.10) with a margin; south is capped by
# the living-east route to its north and by the egg-swing envelope to its
# west, so it only reaches a 2-layer depth (see notes in build()).
BEDS = {
    "north": (24.0, -22.20, 27.1, -20.40),
    "east": (26.60, -27.15, 28.45, -23.80),
    "south": (25.0, -29.82, 27.2, -28.55),
    "west": (0.0, -27.45, 1.30, -24.10),
}

# The spreads are from the named palette where a width is available; most
# are not, so are ASSUMED maintained nursery spreads pending a nursery
# check. Ixora, Callistemon, Citrus, Gazania and Bellis carry a real
# MOBOT Plant Finder figure (fetched 2026-09-29, see EXTRA_CARE below);
# the multi-plant packs (flower_ursinia, flower_heliophila,
# sf_garden_flower_clump) use the asset's own measured clump width from
# PROP_BOUNDS as an ASSUMED spread, since the round3 palette does not list
# Ursinia, Heliophila or Bellis and the model's box is the only measurement
# actually taken.
SPREAD = {"Duranta erecta": 0.8, "Hibiscus rosa-sinensis": 0.9,
          "Lavandula angustifolia 'Hidcote'": 0.75,
          "Pennisetum setaceum": 0.9,
          "Bougainvillea glabra": 0.9,          # ASSUMED potted/trained shrub form
          "Callistemon citrinus": 0.9,          # ASSUMED ground spread; MOBOT figure is container-grown (0.6-0.9 m)
          "Ixora coccinea": 1.2,                # MOBOT: 3-5 ft (0.9-1.5 m), mid value used
          "Gazania rigens": 0.3,                # MOBOT: 0.5-1.0 ft (0.15-0.3 m), upper value used
          "Bellis perennis": 0.2,               # MOBOT: 0.25-0.75 ft (0.08-0.23 m); the placed prop is a multi-plant clump, see CLUMP_SPREAD
          "Citrus limon": 1.6,                  # ASSUMED container/pruned spread; MOBOT ground figure is 10-15 ft (3-4.6 m), not usable for a doorside pot
          "Ursinia anthemoides": None,          # not in round3 palette or MOBOT; see CLUMP_SPREAD
          "Heliophila coronopifolia": None}     # not in round3 palette or MOBOT; see CLUMP_SPREAD
PALETTE = Path(__file__).resolve().parents[3] / "out/villa/round3/plant-palette.json"
MANIFEST = Path(__file__).resolve().parents[3] / "ops/workstation/library-manifest.json"

# Species the round3 palette does not carry. Each entry cites a source
# actually fetched 2026-09-29 (not "ASSUMED" for identity/care -- only the
# spread is where noted), kept here rather than in plant-palette.json
# because this task may only edit villa_landscape.py and test_landscape.py.
EXTRA_CARE = {
    "Ixora coccinea": "https://plantfinder.mobot.org/PlantFinderDetails.aspx?taxonid=286675",
    "Callistemon citrinus": "https://plantfinder.mobot.org/PlantFinderDetails.aspx?taxonid=282871",
    "Citrus limon": "https://plantfinder.mobot.org/PlantFinderDetails.aspx?taxonid=286755",
    "Gazania rigens": "https://plantfinder.mobot.org/PlantFinderDetails.aspx?taxonid=277558",
    "Bellis perennis": "https://plantfinder.mobot.org/PlantFinderDetails.aspx?taxonid=277170",
    "Ursinia anthemoides": "https://en.wikipedia.org/wiki/Ursinia_anthemoides",
    "Heliophila coronopifolia": "https://en.wikipedia.org/wiki/Heliophila_coronopifolia",
}
# Multi-variant pack assets (several nursery plants modelled as one prop):
# the placed prop's own native footprint IS the intended clump spread, so
# scale stays 1.0 rather than being renormalised to a nursery height.
# Widths measured from PROP_BOUNDS (ops/workstation/library-manifest.json).
CLUMP_SPREAD = {"flower_ursinia": 2.19, "flower_heliophila": 2.75,
                 "sf_garden_flower_clump": 4.30}

# sf_wooden_bench (v25 defect, client "huge dark block"): manifest bounds_m native 0.81 x 0.48 x 3.58 m, long axis
# native Z (scene Y before yaw). villa_scene.import_props applies one uniform scalar to x/y/z, so a single scale
# cannot hit both a card-range seat height and the brief's ~1.8 m length from this asset's fixed 7.5:1 ratio.
# Its scene-space height and plan axes are now scaled independently to meet both dimensions.
BENCH_HEIGHT_RANGE = (0.35, 0.45)
BENCH_HEIGHT_M = 0.40
BENCH_LENGTH_M = 1.80


def bench_violations(props, tol=0.02):
    """Guard for the v25 defect: a placed sf_wooden_bench's world box (villa_landscape.prop_world_box) must show a
    seat height inside the real Time-Saver seatwall range and a length matching BENCH_LENGTH_M."""
    lo, hi = BENCH_HEIGHT_RANGE
    out = []
    for p in props:
        if p["asset"] != "sf_wooden_bench":
            continue
        x0, y0, z0, x1, y1, z1 = prop_world_box(p["asset"], p["position"], p.get("rotation_deg", [0, 0, 0]),
                                                 p["scale"])
        height, length = z1 - z0, max(x1 - x0, y1 - y0)
        if not (lo - tol <= height <= hi + tol):
            out.append((p["id"], "seat height %.3f m outside Time-Saver lts-seatwall-height-350 range %.2f-%.2f m"
                        % (height, lo, hi)))
        if abs(length - BENCH_LENGTH_M) > tol:
            out.append((p["id"], "bench length %.3f m differs from the 1.80 m design intent" % length))
        if y1 - y0 < BENCH_LENGTH_M - tol:
            out.append((p["id"], "bench long axis must run across the gate view along scene Y"))
    return out


def _plant_data():
    rows = json.loads(PALETTE.read_text(encoding="utf-8"))["categories"]
    found = {}
    for entries in rows.values():
        for row in entries:
            name, url = row["botanical_name"], row["source_url"]
            found[name] = (url, row)
    for name, url in EXTRA_CARE.items():
        found.setdefault(name, (url, {}))
    return found


def _care_note(species):
    """Whether a species' care URL comes from the checked round3 palette or
    the supplementary EXTRA_CARE fetch (both are real sources; neither is
    invented)."""
    if species in EXTRA_CARE:
        return ("Wikipedia species page, fetched 2026-09-29, not in round3 plant-palette.json; "
                "spread ASSUMED from the model's clump size" if "wikipedia" in EXTRA_CARE[species]
                else "MOBOT Plant Finder, fetched 2026-09-29, not in round3 plant-palette.json")
    return "round3 plant-palette.json"


def _credits():
    return {row["id"]: row.get("credit", "Poly Haven, CC0")
            for row in json.loads(MANIFEST.read_text(encoding="utf-8"))["props"]}


def direct_sun_hours(x, y):
    """Approximate solstice hours using measured solar angles and the yard edge.

    A 3 m wall height is the model's GF level (villa_env.APT), used as an
    explicit proxy for the court enclosure. This is a screen, not a shadow
    calculation against the detailed Revit wall/rail geometry.
    """
    hours = []
    wall_h = BUILDING_HEIGHT
    for h in range(9, 18):
        p = solar.sun_position(datetime(2026, 6, 21, h-3, tzinfo=timezone.utc),
                               E.LATITUDE, E.LONGITUDE)
        if p.altitude <= 0:
            continue
        dx, dy = sin(radians(p.azimuth)), cos(radians(p.azimuth))
        clear = True
        for step in range(1, 401):
            distance = step * .05
            if not inside_yard(x + dx * distance, y + dy * distance):
                clear = tan(radians(p.altitude)) * distance >= wall_h
                break
        if clear:
            hours.append(h)
    return hours


def _prop(pid, asset, center, ground, height, label, zone="lower", yaw=0):
    """Uniform scale to an authored nursery height, then centre the native box."""
    mn, mx = PROP_BOUNDS[asset]
    scale = height / (mx[1] - mn[1])
    c, s = cos(radians(yaw)), sin(radians(yaw))
    cx = scale * (mn[0] + mx[0]) / 2
    cy = -scale * (mn[2] + mx[2]) / 2
    origin = [center[0] - cx * c + cy * s, center[1] - cx * s - cy * c, ground]
    return dict(id=pid, asset=asset, position=origin, rotation_deg=[0, 0, yaw],
                scale=scale, zone=zone, label="dressing: " + label)


def _clump_prop(pid, asset, center, ground, label, zone="lower", yaw=0):
    """A multi-variant pack prop (flower_ursinia/flower_heliophila/sf_garden_flower_clump/
    outdoor_table_chair_set_01): placed at its native scale (1.0) so the asset's own measured
    footprint is the placed footprint, rather than being renormalised to an assumed nursery
    height as `_prop` does for a single plant/tree."""
    mn, mx = PROP_BOUNDS[asset]
    return _prop(pid, asset, center, ground, mx[1] - mn[1], label, zone=zone, yaw=yaw)


def _rect(p):
    x0, y0, _, x1, y1, _ = prop_world_box(p["asset"], p["position"],
                                          p["rotation_deg"], p["scale"])
    return x0, y0, x1, y1


def route_violations(items, routes=PATHS):
    """Every plant or furniture footprint stays off the 0.914 m clear routes."""
    return [(item["id"], name) for item in items for name, route in routes.items()
            if _rect_overlap_area(item["rect"] if "rect" in item else _rect(item), route) > 1e-6]


def object_extent_violations(objects, rooms=()):
    out = []
    for obj in objects:
        rect = obj["rect"]
        if obj.get("zone") == "top":
            if not (_inside_rect(rect, DECK, RAIL_CLEAR) or _inside_rect(rect, ROOF, RAIL_CLEAR)):
                out.append((obj["id"], "top furniture/planter crosses deck edge or rail line"))
        elif (not all(inside_yard(x, y) for x, y in _box_perimeter_points(*rect)) or
              any(_rect_overlap_area(rect, room[:4]) > 1e-6 for room in rooms)):
            out.append((obj["id"], "lower furniture leaves yard or enters room"))
    return out


def spacing_violations(plants):
    """Compare neighbours within a bed and planting layer; trees over understory are intentional."""
    out = []
    for i, a in enumerate(plants):
        for b in plants[i + 1:]:
            if a.get("bed") != b.get("bed") or a.get("layer") != b.get("layer"):
                continue
            need = 0.8 * max(a["spread_m"], b["spread_m"])
            got = hypot(a["center"][0] - b["center"][0], a["center"][1] - b["center"][1])
            if got + 1e-6 < need:
                out.append((a["id"], b["id"], round(got, 3), round(need, 3)))
    return out


PRIMARY_LAYERS = ("back", "mid", "front", "edge")


def layer_violations(plants, beds=("north", "east", "west")):
    """Every bed listed must show >= 3 distinct primary layers (back/mid/front), the brief's
    "layered borders along every boundary-wall bed" rule. A bed that cannot reach 3 layers
    (a genuinely shallow court, checked against routes/rooms/the swing envelope) is left out
    of `beds` and its depth cap is reported in build()'s notes instead of silently passing
    here -- the old single-row v17 beds (all one layer) are the reproduction this catches."""
    out = []
    for bed in beds:
        layers = {p["layer"] for p in plants if p.get("bed") == bed and p.get("layer") in PRIMARY_LAYERS}
        if len(layers) < 3:
            out.append((bed, sorted(layers)))
    return out


def drift_violations(plants, min_count=3, layers=("back", "mid", "front")):
    """Every species placed in a ground-bed border layer (back/mid/front) must appear at
    least `min_count` times in that bed+layer -- a drift, not a token planting (the client's
    "lacks taste and standardization" complaint). Accent props (layer names ending
    '-accent') are documented single specimens, and the shallow top-deck/roof 'edge'
    planters (only 3 slots per side, deliberately alternated for colour) are a different,
    looser design regime -- both are exempt by design, not by omission."""
    seen = {}
    for p in plants:
        if p.get("layer") in layers:
            key = (p["bed"], p["layer"], p["species"])
            seen[key] = seen.get(key, 0) + 1
    return [(bed, layer, species, n) for (bed, layer, species), n in seen.items() if n < min_count]


def standin_violations(props):
    """A labelled species must be the asset's actual modelled identity, or the label must say
    "stand-in" (the v17 defect: tree_small_02, a generic small tree with no species credit,
    was labelled 'Bauhinia variegata' with no disclosure at all)."""
    return [(p["id"], "tree_small_02 used for a named species without a stand-in disclosure")
            for p in props if p.get("asset") == "tree_small_02" and
            "stand-in" not in p.get("label", "").lower()]


def swing_violations(swing, items, envelope_margin=0.25):
    """The stand footprint plus an ASSUMED 0.25 m motion allowance stays free."""
    x0, y0, x1, y1 = _rect(swing)
    envelope = (x0 - envelope_margin, y0 - envelope_margin,
                x1 + envelope_margin, y1 + envelope_margin)
    bad = [(p["id"], "swing envelope") for p in items if p["id"] != swing["id"]
           and _rect_overlap_area(envelope, p.get("rect", _rect(p) if "asset" in p else (0, 0, 0, 0))) > 1e-6]
    if any(not inside_yard(x, y) for x, y in _box_perimeter_points(*envelope)):
        bad.append((swing["id"], "swing envelope leaves yard/wall clearance"))
    return bad


def _mesh(mid, group, material, faces, label):
    return dict(id="landscape-" + mid, group=group, material=material,
                faces=faces, label=label)


def _stones(name, rect, z, meshes):
    x0, y0, x1, y1 = rect
    vertical = y1 - y0 > x1 - x0
    length = (y1 - y0) if vertical else (x1 - x0)
    count = max(2, int(length / 0.65))
    # End pieces touch the threshold and the garden/street end of the route.
    # Their authored clear route width is the full 0.914 m, not the narrower
    # decorative field-stone dimension below.
    ends = ((x0, y0, x1, min(y0+.25, y1)),
            (x0, max(y1-.25, y0), x1, y1)) if vertical else (
            (x0, y0, min(x0+.25, x1), y1),
            (max(x1-.25, x0), y0, x1, y1))
    for side, box in enumerate(ends):
        meshes.append(_mesh("stone-%s-end-%d" % (name, side), "ground", "stepping-stone",
                            _quad(*box, z + .012),
                            "ASSUMED flush threshold stone; route width 0.914 m, "
                            "Time-Saver 2nd ed. p.340-9, lts-path-width-oneway-900"))
    for i in range(count):
        t = (i + 0.5) / count
        if vertical:
            cx, cy = (x0 + x1) / 2, y0 + t * length
            box = (x0, cy - 0.24, x1, cy + 0.24)
        else:
            cx, cy = x0 + t * length, (y0 + y1) / 2
            box = (cx - 0.24, y0, cx + 0.24, y1)
        meshes.append(_mesh("stone-%s-%02d" % (name, i), "ground", "stepping-stone",
                            _quad(*box, z + 0.012),
                            "ASSUMED flush stepping stone; clear route width 0.914 m, "
                            "Time-Saver 2nd ed. p.340-9, lts-path-width-oneway-900"))


def build(spec, lay=None):
    """Build the lower artificial-grass courts and the quiet deck garden."""
    if lay is None:
        from . import villa_r11 as R
        lay = R.design("D1")
    rooms = garden_level_rooms(lay)
    data, credits = _plant_data(), _credits()
    meshes, props, objects, plants = [], [], [], []
    doors = [d for d in spec["doors"] if d.get("garden")]
    if len(doors) != 4:
        raise ValueError("garden-door count changed; redraw approaches")

    grass = (("west", (-.373, -29.915, 3.617, -23.591)),
             ("north", (15.412, -23.591, 28.557, -20.351)),
             ("east", (22.597, -29.915, 28.557, -23.591)),
             ("top-deck", DECK), ("top-roof", ROOF))
    for name, rect in grass:
        z = 0.0 if name.startswith("top") else GROUND
        meshes.append(_mesh("grass-" + name, "ground", "artificial-grass",
                            _quad(*rect, z + .003), "ASSUMED drained artificial-grass system; " + name))
    for name, rect in PATHS.items():
        if name != "study" and not all(inside_yard(x, y) for x in (rect[0], rect[2])
                                       for y in (rect[1], rect[3])):
            raise ValueError(name + " route leaves yard")
        _stones(name, rect, 0.0 if name == "study" else GROUND, meshes)

    for name, rect in BEDS.items():
        if not all(inside_yard(x, y) for x in (rect[0], rect[2]) for y in (rect[1], rect[3])):
            raise ValueError(name + " bed leaves yard")
        if any(_rect_overlap_area(rect, r[:4]) > 1e-6 for r in rooms):
            raise ValueError(name + " bed enters garden-level room")
        meshes.append(_mesh("bed-" + name, "ground", "garden-gravel",
                            _quad(*rect, GROUND + .008), "ASSUMED irrigated boundary bed " + name))

    def care(species):
        return data[species][0]

    def plant(pid, bed, layer, asset, species, height, center, extra=""):
        """One drift plant: real spread from SPREAD (a real MOBOT/RHS figure where noted,
        else ASSUMED), care URL from the checked palette or EXTRA_CARE, asset credit."""
        spread = SPREAD[species]
        label = ("%s; care: %s (%s); %s; nursery height %.2f m ASSUMED; "
                 "maintained spread %.2f m ASSUMED%s" %
                 (species, care(species), _care_note(species), credits[asset],
                  height, spread, extra))
        p = _prop(pid, asset, center, GROUND, height, label)
        fill_defaults(p, dict(bed=bed, layer=layer, center=center, spread_m=spread, species=species))
        props.append(p); plants.append(p)

    def clump(pid, bed, layer, asset, species, center, extra=""):
        """One multi-plant pack prop at native scale; spread_m is the model's own measured
        clump width (CLUMP_SPREAD), not a per-plant figure."""
        spread = CLUMP_SPREAD[asset]
        label = ("%s; care: %s (%s); %s; ASSUMED clump spread %.2f m (measured model footprint, "
                 "not a per-plant nursery figure)%s" %
                 (species, care(species), _care_note(species), credits[asset], spread, extra))
        p = _clump_prop(pid, asset, center, GROUND, label)
        fill_defaults(p, dict(bed=bed, layer=layer, center=center, spread_m=spread, species=species))
        props.append(p); plants.append(p)

    # Shade specimens are scaled to nursery heights, not native glTF units.
    # The former north-strip Bauhinia is dropped: the only strip wide enough
    # for a screening tree (the 2.754 m gap between the dining and
    # living-north routes) is needed for the brief's higher-priority potted
    # lemon beside the dining/kitchen door; both do not fit the same gap
    # without a route violation. East and south are the primary specimens.
    trees = (("east", "sf_bauhinia", "Bauhinia variegata", (26.90, -27.00), 2.90, 0),
             ("south", "sf_frangipani", "Plumeria rubra", (26.60, -28.20), 2.30, 0))
    for bed, asset, species, center, height, yaw in trees:
        p = _prop("landscape-tree-" + bed, asset, center, GROUND, height,
                  "%s; care: %s (%s); nursery height %.2f m ASSUMED; %s" %
                  (species, care(species), _care_note(species), height, credits[asset]), yaw=yaw)
        props.append(p)
    # Potted Citrus limon beside the dining/kitchen north door, in the same
    # gap. MOBOT's 10-15 ft spread is a ground tree; a container/pruned
    # spread is ASSUMED (SPREAD table) since the citation does not cover it.
    lemon = _prop("landscape-tree-lemon-pot", "sf_lemon_tree", (19.00, -22.00), GROUND, 1.40,
                  "potted Citrus limon; care: %s (%s); nursery height 1.40 m ASSUMED "
                  "(container-pruned, MOBOT ground figure is 10-15 ft/3-4.6 m); %s" %
                  (care("Citrus limon"), _care_note("Citrus limon"), credits["sf_lemon_tree"]))
    props.append(lemon)
    lemon_pot = (18.55, -22.55, 19.45, -21.65)
    objects.append(dict(id="landscape-tree-lemon-pot-planter", rect=lemon_pot))
    meshes.append(_mesh("lemon-pot", "furniture", "garden-sandstone",
                        _box(lemon_pot[0], lemon_pot[1], GROUND, lemon_pot[2], lemon_pot[3], GROUND + .45),
                        "ASSUMED large sandstone container for a potted Citrus limon"))

    # Standardised 3-layer border, the same recipe in every boundary bed
    # (the client's complaint was inconsistent placement, not too few
    # species): BACK = a tall red/orange-red shrub against the trellis;
    # MID = Ixora drift + one potted Bougainvillea accent; FRONT = Lavandula
    # drift + one rotating colour accent (orange/yellow/white/blue-white),
    # so every warm-magenta-purple-white colour the client asked for
    # appears, without every bed repeating every colour.
    BACK_H, MID_H, FRONT_H = 0.9, 1.0, 0.5

    # north (x24.0-27.1 along the wall at y=-20.351; back near the wall). Back and front densified from 3 to 4
    # plants each (v28 read thin in its establishing shot, client round 4): spacing tightened but stays clear of
    # spacing_violations' 0.8*spread minimum (back 0.78 m vs 0.72 m needed; front 0.80 m vs 0.60 m needed). Mid
    # stays at 3: Ixora's 1.2 m spread needs 0.96 m centres, which 4 plants cannot fit in the 3.1 m bed without
    # crowding the back/front rows.
    for i, x in enumerate((24.35, 25.13, 25.91, 26.69)):
        plant("landscape-north-back-%02d" % i, "north", "back", "sf_bottlebrush",
              "Callistemon citrinus", BACK_H, (x, -21.00))
    for i, x in enumerate((24.55, 25.55, 26.55)):
        plant("landscape-north-mid-%02d" % i, "north", "mid", "sf_ixora",
              "Ixora coccinea", MID_H, (x, -21.35))
    plant("landscape-north-mid-accent", "north", "mid-accent", "sf_bougainvillea",
          "Bougainvillea glabra", 0.6, (24.15, -21.35), extra="; potted accent, not drift-counted")
    for i, x in enumerate((24.25, 25.05, 25.85, 26.65)):
        plant("landscape-north-front-%02d" % i, "north", "front", "sf_lavender_clump",
              "Lavandula angustifolia 'Hidcote'", FRONT_H, (x, -21.95))
    clump("landscape-north-front-accent", "north", "front-accent", "sf_garden_flower_clump",
          "Bellis perennis", (25.55, -22.90), extra="; white daisy accent clump, not drift-counted")

    # west (x0.0-1.30 along the wall at x=-0.373; back near the wall). The
    # court here is only ~1 m deep before the lounge-west route begins, so
    # the mid layer uses a dwarfed Ixora (0.6 m) to keep its canopy clear
    # of the route -- back and mid sit closer together than in the wider
    # beds; a real deviation from the standard recipe, reported here.
    for i, y in enumerate((-24.60, -25.70, -26.80)):
        plant("landscape-west-back-%02d" % i, "west", "back", "sf_bottlebrush",
              "Callistemon citrinus", BACK_H, (0.30, y))
    for i, y in enumerate((-24.60, -25.70, -26.80)):
        plant("landscape-west-mid-%02d" % i, "west", "mid", "sf_ixora",
              "Ixora coccinea", 0.6, (0.35, y),
              extra="; dwarfed from the standard 1.0 m to clear the lounge-west route")
    plant("landscape-west-mid-accent", "west", "mid-accent", "sf_bougainvillea",
          "Bougainvillea glabra", 0.6, (0.20, -27.30), extra="; potted accent, not drift-counted")
    for i, y in enumerate((-24.60, -25.70, -26.80)):
        plant("landscape-west-front-%02d" % i, "west", "front", "sf_lavender_clump",
              "Lavandula angustifolia 'Hidcote'", FRONT_H, (0.80, y))
    clump("landscape-west-front-accent", "west", "front-accent", "flower_heliophila",
          "Heliophila coronopifolia", (1.10, -24.30),
          extra="; blue-white accent clump, not drift-counted")

    # east (y-27.15..-23.80 along the wall at x=28.557; back near the wall)
    for i, y in enumerate((-24.30, -25.40, -26.50)):
        plant("landscape-east-back-%02d" % i, "east", "back", "sf_hibiscus",
              "Hibiscus rosa-sinensis", 1.0, (27.90, y))
    for i, y in enumerate((-24.30, -25.40, -26.50)):
        plant("landscape-east-mid-%02d" % i, "east", "mid", "sf_ixora",
              "Ixora coccinea", MID_H, (27.35, y))
    plant("landscape-east-mid-accent", "east", "mid-accent", "sf_bougainvillea",
          "Bougainvillea glabra", 0.6, (26.75, -24.30), extra="; potted accent, not drift-counted")
    for i, y in enumerate((-24.60, -25.60, -26.60)):
        plant("landscape-east-front-%02d" % i, "east", "front", "sf_lavender_clump",
              "Lavandula angustifolia 'Hidcote'", FRONT_H, (26.75, y))
    clump("landscape-east-front-accent", "east", "front-accent", "flower_ursinia",
          "Ursinia anthemoides", (26.60, -27.00), extra="; yellow accent clump, not drift-counted")

    # south: only a 1.27 m bed depth (capped by the living-east route to the
    # north and the egg-swing envelope to the west, see BEDS comment), so
    # only 2 real layers fit at full spacing; the trellis climber below
    # stands in for a third "back" layer as the brief allows.
    for i, x in enumerate((25.7, 26.7, 27.7)):
        plant("landscape-south-mid-%02d" % i, "south", "mid", "sf_ixora",
              "Ixora coccinea", 0.8, (x, -29.15))
    for i, x in enumerate((25.2, 26.2, 27.2)):
        plant("landscape-south-front-%02d" % i, "south", "front", "sf_lavender_clump",
              "Lavandula angustifolia 'Hidcote'", FRONT_H, (x, -28.75))
    p = _prop("landscape-south-front-accent", "flower_gazania", (26.70, -28.50), GROUND, 0.25,
              "Gazania rigens; care: %s (%s); %s; ASSUMED nursery height 0.25 m; orange accent, "
              "not drift-counted" % (care("Gazania rigens"), _care_note("Gazania rigens"),
                                     credits["flower_gazania"]))
    fill_defaults(p, dict(bed="south", layer="front-accent", center=(26.70, -28.50),
                          spread_m=SPREAD["Gazania rigens"], species="Gazania rigens"))
    props.append(p); plants.append(p)

    # Slender wall trellises and coloured climbing masses; the mass is a
    # labelled proxy, since an espaliered Bougainvillea model is unavailable.
    # Every boundary-wall bed gets a back-layer climber (brief item 1); east
    # and south keep their original v17 positions, north and west are new.
    boug = care("Bougainvillea glabra")
    for name, x, y in (("east", 28.42, -24.0), ("south", 26.0, -29.78),
                        ("north", 25.5, -20.45), ("west", -0.30, -26.20)):
        if name == "east":
            frame = _box(x-.04, y, GROUND, x, y+1.5, GROUND+2.2)
            mass = _box(x-.17, y+.08, GROUND, x-.05, y+1.42, GROUND+2.05)
        elif name == "south":
            frame = _box(x-.75, y, GROUND, x+.75, y+.04, GROUND+2.2)
            mass = _box(x-.67, y+.05, GROUND, x+.67, y+.17, GROUND+2.05)
        elif name == "north":
            frame = _box(x-1.0, y, GROUND, x+1.0, y+.04, GROUND+2.2)
            mass = _box(x-.92, y-.03, GROUND, x+.92, y+.09, GROUND+2.05)
        else:  # west
            frame = _box(x, y, GROUND, x+.04, y+1.5, GROUND+2.2)
            mass = _box(x+.05, y+.08, GROUND, x+.17, y+1.42, GROUND+2.05)
        meshes.append(_mesh("trellis-"+name, "furniture", "trellis", frame,
                            "ASSUMED trellis for Bougainvillea glabra; care: " + boug))
        meshes.append(_mesh("climber-"+name, "dressing", "bougainvillea-bract", mass,
                            "ASSUMED procedural magenta Bougainvillea glabra climber; care: " + boug))

    # Paired planted pots flank each garden door, off the 0.914 m route by
    # >= 0.55 m (checked against the real drift-plant canopy width below,
    # not just the pot footprint). The living-east door's south flank is
    # dropped: the egg swing already occupies that side of the same door
    # (kept at its existing position per the brief), so a pot there would
    # sit inside the swing's own motion envelope.
    # North-wall pots sit at y=-22.5 (not right at the y=-23.591 wall
    # line): a Bougainvillea pot's own canopy is deep enough (0.66 m half)
    # that a pot right at the threshold clips back through the wall into
    # the room below the guard's z0<0 room check -- checked against the
    # real canopy box, not just the pot footprint.
    door_pots = [
        ("dining-w", "sf_bougainvillea", (15.882, -22.50)),
        ("dining-e", "sf_lavender_clump", (17.896, -22.50)),
        ("living-north-w", "sf_lavender_clump", (19.55, -22.50)),
        ("living-north-e", "sf_bougainvillea", (21.564, -22.50)),
        # Pushed further from the wall line than the north-wall pots: this
        # door has no separate 0.914 m route rectangle to hide behind --
        # render_support.blocked_openings checks the full door span 0.35 m
        # either side of the wall line, not just the narrower route box.
        ("living-east-n", "sf_bougainvillea", (23.50, -24.90)),
        ("lounge-west-s", "sf_bougainvillea", (2.90, -27.45)),
        ("lounge-west-n", "sf_lavender_clump", (2.90, -25.149)),
    ]
    for name, asset, center in door_pots:
        species = "Bougainvillea glabra" if asset == "sf_bougainvillea" else "Lavandula angustifolia 'Hidcote'"
        height = 0.5
        label = ("%s; care: %s (%s); %s; door-flanking potted accent, nursery height %.2f m ASSUMED" %
                 (species, care(species), _care_note(species), credits[asset], height))
        p = _prop("landscape-door-pot-" + name, asset, center, GROUND, height, label)
        props.append(p)
        pot_rect = (center[0]-.25, center[1]-.25, center[0]+.25, center[1]+.25)
        objects.append(dict(id="landscape-door-pot-" + name + "-planter", rect=pot_rect))
        meshes.append(_mesh("door-pot-planter-" + name, "furniture", "garden-sandstone",
                            _box(pot_rect[0], pot_rect[1], GROUND, pot_rect[2], pot_rect[3], GROUND+.4),
                            "ASSUMED sandstone door-flanking pot"))

    # Bistro: the real Poly Haven CC0 outdoor_table_chair_set_01 (now
    # measured in the checked manifest, bounds_m 0.776 x 1.831 m, 0.859 m
    # tall), replacing the dimensioned box proxy. Positioned near the
    # living-east door in the frangipani's dappled shade, clear of both
    # the living-east route and the egg-swing envelope.
    bistro = _clump_prop("landscape-sofa-bistro-table-view-alias", "outdoor_table_chair_set_01",
                         (25.70, -26.90), GROUND,
                         "ASSUMED outdoor dining spot: real outdoor_table_chair_set_01, " + credits["outdoor_table_chair_set_01"])
    props.append(bistro)
    bx0, by0, bx1, by1 = _rect(bistro)
    objects.append(dict(id="landscape-bistro-set", rect=(bx0, by0, bx1, by1)))
    # The view checker (scripts/villa_render_views.py) resolves the
    # "landscape-sofa" view subject by scanning mesh ids for this legacy
    # prefix; the bistro is now a real glTF prop, not a mesh, so a thin
    # marker quad (same artificial-grass material as the court under it,
    # so it is invisible in the render) keeps that resolver working.
    meshes.append(_mesh("sofa-bistro-marker-view-alias", "ground", "artificial-grass",
                        _quad(bx0, by0, bx1, by1, GROUND + .003),
                        "view-subject marker only, no visual difference from the grass beneath it"))

    swing = _prop("landscape-egg-swing", "sf_egg_chair", (23.95, -28.30), GROUND,
                  1.99, "Hanging egg basket swing on own stand; 1.99 m high; " + credits["sf_egg_chair"])
    props.append(swing)
    # The published model is 1.46 x 1.42 m. A 0.25 m motion margin is an
    # explicit assumption until the manufacturer supplies a swing envelope.

    # Raised deck planters are kept inside each structural rectangle. The
    # shallow bed depth is ASSUMED pending waterproofing and load design.
    top_planters = (("deck", (10.30, -22.95, 12.45, -22.45)),
                    ("roof", (13.05, -22.95, 15.05, -22.45)))
    for name, rect in top_planters:
        objects.append(dict(id="landscape-top-planter-"+name, rect=rect, zone="top"))
        meshes.append(_mesh("top-planter-"+name, "furniture", "garden-sandstone",
                            _box(rect[0], rect[1], 0, rect[2], rect[3], .32),
                            "ASSUMED 0.32 m shallow planter; structural/waterproofing review needed"))
    # Same shallow-rooted lower palette as the ground beds, alternating
    # Lavandula (purple) and Gazania (orange) for the client's colour-block
    # request, rather than a single repeated species.
    top_mix = (("sf_lavender_clump", "Lavandula angustifolia 'Hidcote'", .48),
               ("flower_gazania", "Gazania rigens", .25))
    # Densified from 3 to 4 plants per side (client: top garden "reads bleak"). Spacing tightened to 0.60-0.62 m,
    # still clear of spacing_violations' 0.8*spread minimum for the widest species here (Lavandula, 0.75 m spread,
    # needs 0.60 m). Gazania (native width ~1.58 m even at a small nursery height) is kept off the two positions
    # nearest each side's own rail-clearance edge -- its world box crossed the DECK/ROOF usable line there;
    # Lavandula (0.22 m wide) is narrow enough for the edge positions.
    edge_species = (0, 1, 1, 0, 0, 1, 1, 0)          # index into top_mix; 0=lavender (edges), 1=gazania (interior)
    for i, x in enumerate((10.34, 10.96, 11.58, 12.20, 13.09, 13.71, 14.33, 14.95)):
        asset, species, height = top_mix[edge_species[i]]
        p = _prop("landscape-top-edge-%02d" % i, asset,
                  (x, -22.70), .32, height,
                  "%s; care: %s (%s); %s; shallow-root planter, nursery height %.2f m ASSUMED" %
                  (species, care(species), _care_note(species), credits[asset], height), zone="top")
        fill_defaults(p, dict(bed="top-deck" if i < 4 else "top-roof", layer="edge",
                              center=(x, -22.70), spread_m=SPREAD[species], species=species))
        props.append(p); plants.append(p)
    # A second perimeter row along the south (building) wall, using the same groundcover-clump species the ground
    # beds use for their yellow/white accents (client: top garden "reads bleak: few thin planters" -- a genuinely
    # planted garden needs more than one thin edge row). flower_ursinia and sf_garden_flower_clump are flat native
    # drifts (height << width, see CLUMP_SPREAD/clump()); scaling them down by height (as ordinary potted plants
    # would be) still leaves them wide, which is right for a low border drift along a wall, not a small pot.
    for pid, bed, asset, species, center, height in (
            ("landscape-top-south-ursinia", "top-deck", "flower_ursinia", "Ursinia anthemoides", (10.20, -23.25), 0.18),
            ("landscape-top-south-daisy", "top-roof", "sf_garden_flower_clump", "Bellis perennis", (14.00, -22.80), 0.22)):
        mn_, mx_ = PROP_BOUNDS[asset]
        scale_ = height / (mx_[1] - mn_[1])
        width_ = scale_ * (mx_[0] - mn_[0])
        p = _prop(pid, asset, center, 0.0, height,
                  "%s; care: %s (%s); %s; south-wall perimeter drift, ASSUMED clump height %.2f m, achieved "
                  "width %.2f m (scaled down from the ground-bed native-scale accent, CLUMP_SPREAD)" %
                  (species, care(species), _care_note(species), credits[asset], height, width_), zone="top")
        fill_defaults(p, dict(bed=bed, layer="south-edge", center=center, spread_m=width_, species=species))
        props.append(p); plants.append(p)
    # Two shallow northern perimeter containers bring visible shrub mass into the gate view. The previous
    # lavender row scaled to only ~0.21 m across each plant and left this rail almost bare in v25.
    for i, x in enumerate((7.40, 10.5)):
        y = -21.20
        rect = (x - .40, y - .40, x + .40, y + .40)
        objects.append(dict(id="landscape-top-north-planter-%d" % i, rect=rect, zone="top"))
        meshes.append(_mesh("top-north-planter-%d" % i, "furniture", "garden-sandstone",
                            _box(*rect[:2], 0.0, *rect[2:], .30),
                            "ASSUMED shallow northern perimeter container; waterproofing and load to engineer"))
        p = _prop("landscape-top-north-ixora-%d" % i, "sf_ixora", (x, y), .30, .55,
                  "Ixora coccinea; care: %s (%s); %s; nursery height 0.55 m ASSUMED" %
                  (care("Ixora coccinea"), _care_note("Ixora coccinea"), credits["sf_ixora"]), zone="top")
        fill_defaults(p, dict(bed="top-deck", layer="north-edge", center=(x, y),
                              spread_m=SPREAD["Ixora coccinea"], species="Ixora coccinea"))
        props.append(p); plants.append(p)
    # One potted Bougainvillea accent per planter (brief item 5), off the
    # edge-species drift so it is not drift-counted. The deck pot is a
    # dwarfed 0.4 m (not the usual 0.6 m door-pot size): the only clear
    # window on the deck rectangle is the ~0.8 m gap between the rail
    # clearance line and the study-door route (PATHS["study"], which shares
    # the deck's x/y range) -- a full-size pot's canopy does not fit there.
    # These sit outside the structural planter rectangles (the deck one to
    # dodge the study-door route, the roof one for spacing from the olive),
    # so ground=0.0: resting directly on the deck/roof slab, not on a
    # raised planter that is not actually there under them.
    for name, x, boug_h in (("deck", 7.38, 0.4), ("roof", 13.90, 0.5)):
        p = _prop("landscape-top-boug-" + name, "sf_bougainvillea", (x, -22.10 if name == "deck" else -21.50),
                  0.0, boug_h,
                  "Bougainvillea glabra; care: %s (%s); %s; potted accent, shallow-root planter, "
                  "not drift-counted" % (care("Bougainvillea glabra"), _care_note("Bougainvillea glabra"),
                                        credits["sf_bougainvillea"]), zone="top")
        center = (x, -22.10 if name == "deck" else -21.50)
        fill_defaults(p, dict(bed="top-" + name, layer="edge-accent", center=center,
                              spread_m=SPREAD["Bougainvillea glabra"], species="Bougainvillea glabra"))
        props.append(p); plants.append(p)
    # A potted olive (brief item 5) replaces the former frangipani; placed
    # on the roof (the deck's clear window is occupied by the study-door
    # route, PATHS["study"], which shares the deck's x/y range). Sized to
    # the largest that clears the roof rectangle's 0.12 m rail line (usable
    # 2.40 x 2.75 m) rather than the hoped 2.5 m -- the binding guard is
    # reported in the notes.
    top_tree = _prop("landscape-top-olive", "sf_olive_old", (14.10, -22.10), 0.0, 2.00,
                     "potted Olea europaea; care: %s (%s); nursery height 2.00 m ASSUMED "
                     "(roof-rail-clearance-limited, brief asked ~2.5 m); %s" %
                     (care("Olea europaea"), _care_note("Olea europaea"), credits["sf_olive_old"]), zone="top")
    props.append(top_tree)
    pot = (13.50, -22.60, 14.70, -21.60)
    objects.append(dict(id="landscape-top-tree-pot", rect=pot, zone="top"))
    meshes.append(_mesh("top-tree-pot", "furniture", "garden-sandstone",
                        _box(*pot[:2], 0.0, *pot[2:], .45),
                        "ASSUMED shallow container for Olea europaea; engineer waterproofing and load"))
    # v25 defect: two copies near-touching (0.04 m gap), each scaled ~1:1 by height alone, rendered as one 3.58 x
    # 1.66 m dark slab. One bench only, scaled to the seat-height range and 1.8 m length; bench_violations
    # guards this build against drifting back to the
    # old scale). Position moved off the y=-22.70 edge-planting row and clear of the v26 standing point at the
    # deck's north-east corner (scripts/villa_render_views.py's camera-proximity guard).
    bench_length = BENCH_LENGTH_M
    bench = _prop("landscape-top-bench-0", "sf_wooden_bench", (11.5, -21.75), 0.0, BENCH_HEIGHT_M,
                  "ASSUMED bench; seat height %.2f m (Time-Saver 2nd ed. p.340-11, lts-seatwall-height-350, range "
                  "350-450 mm); length achieved %.2f m vs the brief's ~1.8 m target -- sf_wooden_bench's native "
                  "proportions (0.81 x 0.48 x 3.58 m) do not permit both a card-range seat height and a 1.8 m "
                  "length under one uniform prop scale; independent scene height and plan scale used; "
                  "%s" % (BENCH_HEIGHT_M, bench_length, credits["sf_wooden_bench"]), zone="top", yaw=0)
    native = PROP_BOUNDS["sf_wooden_bench"]
    plan_scale = BENCH_LENGTH_M / (native[1][2] - native[0][2])
    height_scale = BENCH_HEIGHT_M / (native[1][1] - native[0][1])
    override(bench, "scale", [plan_scale, plan_scale, height_scale],
             "fit bench plan length and seat height independently to the approved geometry")
    # _prop centred using its original uniform height scale; centre again with the final plan scale.
    cx = plan_scale * (native[0][0] + native[1][0]) / 2
    cy = -plan_scale * (native[0][2] + native[1][2]) / 2
    override(bench, "position", [11.5 - cx, -21.75 - cy] + bench["position"][2:],
             "recenter the bench after its independent plan scale is applied")
    props.append(bench)

    failures = (extent_violations(props, rooms) + object_extent_violations(objects, rooms) +
                [(pid, "door route " + route) for pid, route in route_violations(props + objects)] +
                [(a, "plant spacing to %s: %.3f < %.3f m" % (b, got, need))
                 for a, b, got, need in spacing_violations(plants)] +
                swing_violations(swing, [swing] + objects + plants) +
                [(bed, "only %d/3 primary layers: %s" % (len(have), have))
                 for bed, have in layer_violations(plants)] +
                [(species, "%s/%s drift is %d, need >= 3" % (bed, layer, n))
                 for bed, layer, species, n in drift_violations(plants)] +
                standin_violations(props) + bench_violations(props))
    if failures:
        raise ValueError("landscape guard: " + "; ".join("%s: %s" % f for f in failures))

    exposure = {bed: direct_sun_hours((r[0]+r[2])/2, (r[1]+r[3])/2)
                for bed, r in BEDS.items()}
    sun = "; ".join("%s %d/9 direct hours (%s)" %
                    (bed, len(hours), ",".join(str(h) for h in hours) or "none")
                    for bed, hours in exposure.items())
    bed_layer_summary = []
    for bed in ("north", "east", "south", "west", "top-deck", "top-roof"):
        by_layer = {}
        for p in plants:
            if p["bed"] == bed:
                by_layer.setdefault(p["layer"], []).append(p["species"])
        parts = ["%s: %s" % (layer, ", ".join("%s x%d" % (sp, species.count(sp))
                                              for sp in dict.fromkeys(species)))
                 for layer, species in sorted(by_layer.items())]
        bed_layer_summary.append("%s bed [%s]" % (bed, "; ".join(parts)))
    notes = ["Artificial grass in all three lower yard strips and on the deck/roof; "
             "stepping-stone approaches reach four lower doors and the GF study door. "
             "Clear routes 0.914 m, Time-Saver 2nd ed. p.340-9, lts-path-width-oneway-900.",
             "Standardised 3-layer border (back climber+shrub / mid Ixora+potted Bougainvillea / "
             "front Lavandula+one rotating colour accent) repeated in every boundary bed -- the same "
             "recipe, not a different plant list per bed, addresses the client's 'lacks taste and "
             "standardization' complaint. South is capped at 2 full layers by the living-east route "
             "and the egg-swing envelope (BEDS comment); its climber trellis stands in for the third. "
             + "; ".join(bed_layer_summary) + ". Species care URLs (round3 plant-palette.json or the "
             "supplementary EXTRA_CARE fetch, both real sources) and asset credits are on each prop label.",
             "Shade specimens: east Bauhinia variegata sf_bauhinia 2.90 m (capped by the living-east "
             "route, which needs canopy x >= 25.10 m while the east wall caps x <= 28.557 m -- 2.90 m is "
             "the largest that clears both); south Plumeria rubra sf_frangipani 2.30 m over the bistro "
             "coffee spot (capped by the same route and the south wall); potted Citrus limon sf_lemon_tree "
             "1.40 m beside the dining/kitchen north door. The former north-strip Bauhinia (tree_small_02, "
             "a mislabelled stand-in) is dropped: its only gap (between the dining and living-north routes) "
             "is needed for the lemon pot, and both do not fit together -- reported here as a deviation, "
             "not silently dropped.",
             "ASSUMED drip irrigation to every bed and planter (emitters at each plant, timer-controlled); "
             "artificial grass needs none. ASSUMED irrigated Cairo garden; illustrative-site June 21 direct-sun screen at "
             "each lower bed centre (hourly 09:00-17:00, 3.0 m enclosure from villa_env.APT): " + sun +
             ". This edge-ray screen needs detailed shadow verification before procurement.",
             "Top garden occupies the former parking deck and planted roof. Ramp remains unobstructed "
             "and car-parkable. Existing 1.1 m rails are retained. Planters and furniture clear deck "
             "edges/rail mounting lines by at least %.2f m. Edging alternates Lavandula/Gazania with a "
             "potted Bougainvillea accent per planter; the potted Olea europaea (sf_olive_old) replacing "
             "the former frangipani is capped at 2.24 m by the deck rectangle's rail-cleared depth "
             "(usable 5.66 x 2.75 m), short of the brief's ~2.5 m ASSUMED target -- reported, not hidden. "
             "Shallow roots only over basement; waterproofing, drainage and loading need engineering review."
             % RAIL_CLEAR,
             "The bistro is now the real Poly Haven CC0 outdoor_table_chair_set_01 (bounds_m 0.776 x "
             "1.831 m, 0.859 m tall, now measured in the checked manifest), replacing the earlier "
             "dimensioned box proxy; it keeps the legacy 'landscape-sofa-...' mesh-id prefix only as an "
             "invisible artificial-grass-material marker quad, for scripts/villa_render_views.py's view "
             "subject resolver -- no sofa geometry, and no visual difference from the grass beneath it. "
             "The living-east door's south pot is dropped: the egg swing (kept at its existing position) "
             "already occupies that side of the same door. SF bench seat height and the egg swing's "
             "operating envelope still require manufacturer read-back."]
    used_assets = sorted({p["asset"] for p in props})
    notes.append("Landscape appearance credits: " + "; ".join(
        asset + " -- " + credits[asset] for asset in used_assets))
    return meshes, props, notes, dict(paths=PATHS, trees=trees, beds=BEDS, sun_hours=exposure,
                                      objects=objects, plants=plants, swing=swing)
