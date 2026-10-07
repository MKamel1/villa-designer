"""D1 garden evidence and fail-closed G1/G2/G3 rebuild candidate.

The south planting zone is the southern end of our east yard. The land below
the rear boundary belongs to the sister plot and is never dressed as ours.
All positions are metres in the same frame as the villa scene.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from math import cos, hypot, pi, radians, sin, tan
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
TOP_SURFACE = 0.0  # Scene GF datum; street +1.20 m in villa_parking.
TROUGH_COLOUR = dict(name="dark bronze, ASSUMED pending client confirmation",
                     base_rgb=[0.12, 0.075, 0.045])
# Dimensions below are authored ASSUMED design intent, not supplier sizes.
TOP_TROUGHS = (
    ("deck-north", (9.20, -21.10, 12.40, -20.76), "Salvia rosmarinus Prostrata Group",
     ((9.80, -20.93), (10.80, -20.93), (11.80, -20.93))),
    ("roof-north", (13.02, -21.16, 15.15, -20.76), "Aloe vera",
     ((13.40, -20.96), (14.10, -20.96), (14.80, -20.96))),
    ("roof-south", (13.02, -23.44, 15.15, -23.04), "Aloe vera",
     ((13.40, -23.24), (14.10, -23.24), (14.80, -23.24))),
)
TOP_TROUGH_HEIGHT = .25
BENCH_KNEE_CLEAR = .60  # ASSUMED free space in front; nursery/furniture review pending.
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


def _pot(cx, cy, z, lower, upper, height, count=16):
    """Closed tapered container, raised rim and soil, each a separate physical solid."""
    def ring(radius, zz):
        return [[cx + radius*cos(2*pi*i/count), cy + radius*sin(2*pi*i/count), zz]
                for i in range(count)]
    bottom, top = ring(lower, z), ring(upper, z+height)
    inner_floor, inner_top = ring(lower-.015, z+.025), ring(upper-.015, z+height)
    body = [bottom[::-1], inner_floor]
    for i in range(count):
        j = (i+1)%count
        body += [[bottom[i], bottom[j], top[j], top[i]],
                 [top[i], top[j], inner_top[j], inner_top[i]],
                 [inner_floor[j], inner_floor[i], inner_top[i], inner_top[j]]]
    outer_low, outer_high = ring(upper+.009, z+height-.026), ring(upper+.009, z+height)
    inner_low, inner_high = ring(upper-.012, z+height-.026), ring(upper-.012, z+height)
    rim = []
    for i in range(count):
        j = (i+1)%count
        rim += [[outer_low[i], outer_low[j], outer_high[j], outer_high[i]],
                [outer_high[i], outer_high[j], inner_high[j], inner_high[i]],
                [inner_high[j], inner_low[j], inner_low[i], inner_high[i]],
                [inner_low[j], outer_low[j], outer_low[i], inner_low[i]]]
    soil_low, soil_high = ring(lower-.019, z+.026), ring(upper-.019, z+height-.005)
    soil = [soil_low[::-1], soil_high] + [[soil_low[i], soil_low[(i+1)%count],
             soil_high[(i+1)%count], soil_high[i]] for i in range(count)]
    return body, rim, soil


def _raised_bed(rect, z, height):
    """Five thin closed boards and a visible soil surface, not a solid planter block."""
    x0, y0, x1, y1 = rect
    t = .025
    body = (_box(x0, y0, z, x1, y1, z+t) +
            _box(x0, y0, z+t, x0+t, y1, z+height) +
            _box(x1-t, y0, z+t, x1, y1, z+height) +
            _box(x0+t, y0, z+t, x1-t, y0+t, z+height) +
            _box(x0+t, y1-t, z+t, x1-t, y1, z+height))
    soil = _box(x0+t, y0+t, z+height-.009, x1-t, y1-t, z+height-.005)
    return body, soil


def _steel_trough(rect, z, height):
    """Closed 3 mm base and side plates, folded rim, and recessed soil.

    All dimensions are ASSUMED fabrication intent awaiting a supplier.
    No pedestal, cap or stone proxy forms part of this assembly.
    """
    x0, y0, x1, y1 = rect
    t = .003
    body = (_box(x0,y0,z,x1,y1,z+t) +
            _box(x0,y0,z+t,x0+t,y1,z+height) +
            _box(x1-t,y0,z+t,x1,y1,z+height) +
            _box(x0+t,y0,z+t,x1-t,y0+t,z+height) +
            _box(x0+t,y1-t,z+t,x1-t,y1,z+height))
    # Inward folds retain the stated outside envelope.
    body += (_box(x0+t,y0+t,z+height-t,x1-t,y0+.012,z+height) +
             _box(x0+t,y1-.012,z+height-t,x1-t,y1-t,z+height))
    soil = _box(x0+t,y0+t,z+t,x1-t,y1-t,z+height-.005)
    return body, soil


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
    "gate-link": (6.877, -22.55, 8.734, -21.636),
}

# Boundary beds actually built, excluding the lawn-only east by client decision.
BEDS = {
    "west": (-.05, -28.50, 3.45, -26.90),
    "north": (17.45, -22.70, 20.05, -20.65),
}

# The agreed tracked record is the only botanical/placement evidence input.
PALETTE = Path(__file__).resolve().parents[3] / "knowledge/garden-palette.json"
MANIFEST = Path(__file__).resolve().parents[3] / "ops/workstation/library-manifest.json"
# Identity bindings are appearances, not additional botanical evidence. Legacy
# bindings stay here so an excluded/unknown model cannot masquerade as furniture.
ASSET_SPECIES = {
    "sf_frangipani": "Plumeria rubra", "sf_bauhinia": "Bauhinia variegata",
    "sf_bottlebrush": "Callistemon citrinus", "sf_ixora": "Ixora coccinea",
    "sf_bougainvillea": "Bougainvillea glabra", "flower_ursinia": "Ursinia anthemoides",
    "sf_lavender_clump": "Lavandula angustifolia 'Hidcote'",
    "sf_hibiscus": "Hibiscus rosa-sinensis", "sf_lemon_tree": "Citrus limon",
    "sf_olive_old": "Olea europaea", "flower_gazania": "Gazania rigens",
    "sf_garden_flower_clump": "Bellis perennis", "flower_heliophila": "Plumbago auriculata",
    "jacaranda_tree": "Jacaranda mimosifolia",
}

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
    record = json.loads(PALETTE.read_text(encoding="utf-8"))
    rows = {row["species"]: row for row in record["species"]}
    if len(rows) != len(record["species"]) or set(rows) & {r["species"] for r in record["excluded"]}:
        raise ValueError("garden palette duplicates or approves an excluded species")
    return rows


def require_species(species, data=None):
    """Fail before placement, including for unnamed/unknown plants."""
    data = _plant_data() if data is None else data
    if species not in data:
        raise ValueError("unknown or excluded garden species: " + str(species))
    return data[species]


def species_violations(items):
    """Check props AND procedural plant meshes; asset identity may not be relabelled."""
    out = []
    for item in items:
        bound = ASSET_SPECIES.get(item.get("asset"))
        is_plant = bound is not None or "species" in item or item.get("part_kind") in ("climber", "climber-branch")
        if not is_plant:
            # Manifest plant roles catch assets absent from the explicit binding table.
            if item.get("asset") not in PLANT_ASSETS:
                continue
        species = item.get("species")
        try:
            require_species(species)
        except ValueError as exc:
            out.append((item["id"], str(exc)))
        if bound is not None and species != bound:
            out.append((item["id"], "species differs from asset identity " + bound))
    return out


def dimension_violations(props, tol=1e-6):
    """Actual uniformly scaled model height and maximum plan span, in metres.

    Mature card ranges apply unless the record explicitly supplies a nursery,
    pruned or multi-plant-pack assumption for this asset. No scene label can
    invent a dimensional exception.
    """
    out = species_violations(props)
    for p in props:
        if not p.get("species"):
            continue
        row = require_species(p["species"])
        if p.get("part_kind") in ("climber", "climber-branch", "plant-clump"):
            points = [point for face in p["faces"] for point in face]
            assumed = row["placement_assumptions"]["procedural-clump" if p.get("part_kind") == "plant-clump" else "procedural-trellis"]
            achieved = {"height": max(q[2] for q in points)-min(q[2] for q in points),
                        "spread": max(max(q[i] for q in points)-min(q[i] for q in points) for i in (0, 1))}
            for field, got in achieved.items():
                lo, hi = assumed[field]["range_m"]
                if not lo-tol <= got <= hi+tol:
                    out.append((p["id"], "procedural " + field + " outside recorded ASSUMED envelope"))
            continue
        if p.get("asset") not in PROP_BOUNDS:
            out.append((p["id"], "plant asset has no measured bounds"))
            continue
        scale = p.get("scale", 1.0)
        if not isinstance(scale, (int, float)):
            out.append((p["id"], "plant scale must be uniform"))
            continue
        mn, mx = PROP_BOUNDS[p["asset"]]
        achieved = {"height": (mx[1]-mn[1])*scale,
                    "spread": max(mx[0]-mn[0], mx[2]-mn[2])*scale}
        assumed = row["placement_assumptions"].get(p["asset"], {})
        for field, got in achieved.items():
            evidence = assumed.get(field, row[field])
            limits = evidence.get("range_m")
            if not limits or evidence["status"] == "UNVERIFIED":
                out.append((p["id"], field + " has no verified range or recorded assumption"))
            elif (limits[0] is not None and got < limits[0]-tol) or (limits[1] is not None and got > limits[1]+tol):
                out.append((p["id"], "%s %.3f m outside %s %s" % (field, got, evidence["status"], limits)))
    return out


PLANT_ASSETS = {r["id"] for r in json.loads(MANIFEST.read_text())["props"]
                if r.get("role") == "plant" or r.get("species")}


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
    if asset in ASSET_SPECIES:
        require_species(ASSET_SPECIES[asset])
    elif asset in PLANT_ASSETS:
        raise ValueError("plant asset has no approved species binding: " + asset)
    mn, mx = PROP_BOUNDS[asset]
    scale = height / (mx[1] - mn[1])
    c, s = cos(radians(yaw)), sin(radians(yaw))
    cx = scale * (mn[0] + mx[0]) / 2
    cy = -scale * (mn[2] + mx[2]) / 2
    origin = [center[0] - cx * c + cy * s, center[1] - cx * s - cy * c, ground]
    return dict(id=pid, asset=asset, position=origin, rotation_deg=[0, 0, yaw],
                scale=scale, zone=zone, label="dressing: " + label)


def _clump_prop(pid, asset, center, ground, label, zone="lower", yaw=0):
    """Place a multi-variant pack at native scale when no height is authored."""
    mn, mx = PROP_BOUNDS[asset]
    return _prop(pid, asset, center, ground, mx[1] - mn[1], label, zone=zone, yaw=yaw)


def _rect(p):
    if "rect" in p:
        return p["rect"]
    if "faces" in p:
        return _mesh_rect(p)
    x0, y0, _, x1, y1, _ = prop_world_box(p["asset"], p["position"],
                                          p["rotation_deg"], p["scale"])
    return x0, y0, x1, y1


def route_violations(items, routes=PATHS, route_ground=None):
    """Physical walking envelopes from ground to 2.0 m, for every prop/mesh.

    Height basis: render_support.blocked_openings uses the same 2.0 m
    passage height. Prop triangles (including node transforms and floor
    seating) are intersected with each envelope; high canopy alone cannot
    obstruct walking. Rect-only legacy objects conservatively occupy the
    envelope unless explicit bottom/top elevations are supplied.
    route_ground optionally maps route names to floor elevations in metres.
    """
    import numpy as np
    from .route_geometry import prop_triangles
    from .render_support import _tri_box_overlap, _triangles
    out = []
    for item in items:
        # Validate every placed asset, including props clear of all routes.
        triangles = prop_triangles(item) if "asset" in item else None
        candidates = [(name, route) for name, route in routes.items()
                      if _rect_overlap_area(_rect(item), route) > 1e-6]
        if not candidates:
            continue
        if "faces" in item and "asset" not in item:
            triangles, _ = _triangles([item])
        for name, route in candidates:
            ground = (route_ground or {}).get(name, TOP_SURFACE if name in ("study", "gate-link") else GROUND)
            if "asset" in item:
                # A lower placement/higher route floor may reach omitted canopy.
                prop_triangles(item, walking_top_m=ground+2.0)
            low = np.array([route[0], route[1], ground])
            high = np.array([route[2], route[3], ground+2.0])
            if triangles is not None:
                nearby = np.all(triangles.min(axis=1) <= high, axis=1) & np.all(triangles.max(axis=1) >= low, axis=1)
                blocked = nearby.any() and _tri_box_overlap(triangles[nearby], (low+high)/2, (high-low)/2).any()
            else:
                blocked = item.get("bottom_m", ground) < high[2] and item.get("top_m", high[2]) > low[2]
            if blocked:
                out.append((item["id"], name))
    return out


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


def planting_layer(plant):
    """Planting strata have their own field; layer is reserved for lighting.

    Frozen historical guard inputs may retain the old field.
    """
    return plant.get("planting_layer", plant.get("layer"))


def spacing_violations(plants):
    """Compare neighbours within a bed and planting layer; trees over understory are intentional."""
    out = []
    for i, a in enumerate(plants):
        for b in plants[i + 1:]:
            if a.get("bed") != b.get("bed") or planting_layer(a) != planting_layer(b):
                continue
            need = 0.8 * max(a["spread_m"], b["spread_m"])
            got = hypot(a["center"][0] - b["center"][0], a["center"][1] - b["center"][1])
            if got + 1e-6 < need:
                out.append((a["id"], b["id"], round(got, 3), round(need, 3)))
    return out


PRIMARY_LAYERS = ("back", "mid", "front", "edge")


def layer_violations(plants, beds=None):
    """Three primary layers on beds that exist, never on a lawn-only court.

    Explicit beds come from the plan's authored bed data. Without a plan,
    derive the ground-bed scope from the plants' declared primary layers.
    """
    if beds is None:
        beds = {p["bed"] for p in plants if planting_layer(p) in PRIMARY_LAYERS}
    out = []
    for bed in beds:
        layers = {planting_layer(p) for p in plants if p.get("bed") == bed and planting_layer(p) in PRIMARY_LAYERS}
        if len(layers) < 3:
            out.append((bed, sorted(layers)))
    return out


def drift_violations(plants, min_count=3, max_count=5, layers=("back", "mid", "front")):
    """Ground-bed strata and top troughs each require 3-5 of one species.

    Pots remain individual accents; troughs never inherit that exemption.
    """
    seen = {}
    for p in plants:
        if planting_layer(p) in layers or p.get("trough") is not None:
            key = (p["bed"], planting_layer(p), p["species"])
            seen[key] = seen.get(key, 0) + 1
    return [(bed, layer, species, n) for (bed, layer, species), n in seen.items() if not min_count <= n <= max_count]


def sunlight_violations(plants):
    """Full-sun-only appearances in the ground courts need measured sun hours.

    More than six direct hours at midsummer is the RHS definition recorded
    in the sole palette. Existing top placements belong to G3, not G2.
    """
    threshold = json.loads(PALETTE.read_text())["design_assumptions"]["full_sun_screen"]["hours"]
    out=[]
    for plant in plants:
        if plant.get("bed") not in BEDS or plant["species"] not in ("Callistemon citrinus","Ursinia anthemoides"):
            continue
        hours = direct_sun_hours(*plant["center"])
        if len(hours) <= threshold:
            out.append((plant["id"],"full sun requires >%d h, achieved %d h (%s)"%(threshold,len(hours),hours)))
    return out


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


def _mesh(mid, group, material, faces, label, *, kind, surface=False, occupied_side=None):
    return dict(id="landscape-" + mid, group=group, material=material,
                faces=faces, label=label, part_kind=kind, surface=surface, occupied_side=occupied_side)


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
                            _box(box[0], box[1], z, box[2], box[3], z + .012),
                            "ASSUMED flush threshold stone; route width 0.914 m, "
                            "Time-Saver 2nd ed. p.340-9, lts-path-width-oneway-900", kind="stepping-stone"))
    for i in range(count):
        t = (i + 0.5) / count
        if vertical:
            cx, cy = (x0 + x1) / 2, y0 + t * length
            box = (x0, cy - 0.24, x1, cy + 0.24)
        else:
            cx, cy = x0 + t * length, (y0 + y1) / 2
            box = (cx - 0.24, y0, cx + 0.24, y1)
        meshes.append(_mesh("stone-%s-%02d" % (name, i), "ground", "stepping-stone",
                            _box(box[0], box[1], z, box[2], box[3], z + .012),
                            "ASSUMED flush stepping stone; clear route width 0.914 m, "
                            "Time-Saver 2nd ed. p.340-9, lts-path-width-oneway-900", kind="stepping-stone"))


# Court dimensions are measured from villa_env, not the rounded brief.
EAST = (E.BAR[2]/1000, E.AXIS_Y/1000, PLOT[2], PLOT[3])
EAST_CENTER = ((EAST[0]+EAST[2])/2, (EAST[1]+EAST[3])/2)


def _mesh_rect(mesh):
    pts = [p for face in mesh["faces"] for p in face]
    return min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)


def _covers_point(face, x, y):
    """Ray crossing in the floor plane, independent of a polygon's centroid."""
    inside = False
    for a, b in zip(face, face[1:]+face[:1]):
        if (a[1] > y) != (b[1] > y) and x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:
            inside = not inside
    return inside


def east_content_violations(meshes, props, objects=()):
    """Physical lower-court contents; no dependence on east/south ID names."""
    out, trees = [], []
    pit_center = tuple(json.loads(PALETTE.read_text())["design_assumptions"]["east_tree_position"]["center_m"])
    for item in list(props)+list(objects):
        if item.get("zone") == "top":
            continue
        rect = item["rect"] if "rect" in item else _rect(item)
        if _rect_overlap_area(rect, EAST) <= 1e-6:
            continue
        if item.get("species") == "Plumeria rubra" and item.get("asset") == "sf_frangipani":
            trees.append(item)
        else:
            out.append((item["id"], "east permits only lawn, paths, tree pit and one Plumeria"))
    for mesh in meshes:
        pts = [p for face in mesh["faces"] for p in face]
        if min(p[2] for p in pts) >= -.01 or _rect_overlap_area(_mesh_rect(mesh), EAST) <= 1e-6:
            continue
        allowed = (mesh["material"] == "artificial-grass" and mesh.get("part_kind") == "finish-layer" or
                   mesh.get("part_kind") == "stepping-stone" or mesh.get("part_kind") == "tree-pit")
        if not allowed:
            out.append((mesh["id"], "east contains a forbidden surface or object"))
    if len(trees) != 1:
        out.append(("east", "exactly one Plumeria required; found %d" % len(trees)))
    else:
        tree = trees[0]
        ax, _, az = require_species("Plumeria rubra")["appearance_measurements"]["sf_frangipani"]["trunk_base_gltf_m"]
        yaw = radians(tree.get("rotation_deg", [0, 0, 0])[2])
        dx, dy = ax*tree["scale"], -az*tree["scale"]
        trunk = (tree["position"][0]+dx*cos(yaw)-dy*sin(yaw),
                 tree["position"][1]+dx*sin(yaw)+dy*cos(yaw))
        if abs(tree["center"][0]-EAST_CENTER[0]) > .5+1e-9:
            out.append((tree["id"], "D4 trunk exceeds 0.5 m from court centre line"))
        if hypot(trunk[0]-tree["center"][0], trunk[1]-tree["center"][1]) > 1e-6:
            out.append((tree["id"], "declared centre differs from measured trunk"))
        if hypot(trunk[0]-pit_center[0], trunk[1]-pit_center[1]) > 1e-6:
            out.append((tree["id"], "measured trunk is not centred in the lawn pit"))
    pits = [m for m in meshes if m.get("part_kind") == "tree-pit"]
    if len(pits) != 1:
        out.append(("east", "exactly one visible tree pit required"))
    else:
        radius = json.loads(PALETTE.read_text())["design_assumptions"]["east_tree_pit"]["diameter_m"]/2
        if any(abs(hypot(p[0]-pit_center[0], p[1]-pit_center[1])-radius) > 1e-6
               for face in pits[0]["faces"] for p in face):
            out.append((pits[0]["id"], "tree pit differs from the recorded ASSUMED diameter/centre"))
        for mesh in meshes:
            if mesh["material"] != "artificial-grass":
                continue
            # A large covering face can have its centroid outside the pit.
            # Test containment as well; the builder emits an annulus.
            for face in mesh["faces"]:
                checks = list(face)+[[sum(p[i] for p in face)/len(face) for i in range(3)]]
                if (min(p[2] for p in face) < -.01 and _covers_point(face, *pit_center) or
                        any(p[2] < -.01 and hypot(p[0]-pit_center[0], p[1]-pit_center[1]) < radius-1e-6 for p in checks)):
                    out.append((mesh["id"], "artificial grass covers the tree pit"))
                    break
    return out


def canopy_violations(props, *, mature=False):
    """Mature lower-range circle or measured model box against inner wall faces.

    The rear and east fences occupy the inner 0.25 m of the plot. Every
    footprint must stay on the court side of those faces, including above
    the wall; crossing a property boundary is not allowed at canopy height.
    """
    out = []
    fence = E.FENCE_T/1000
    usable = (EAST[0], EAST[1], EAST[2]-fence, EAST[3]-fence)
    for p in props:
        if p.get("species") != "Plumeria rubra":
            continue
        if mature:
            spread = require_species(p["species"])["spread"]["range_m"][0]
            radius = spread/2
            x, y = p["center"]
            box = (x-radius, y-radius, x+radius, y+radius)
        else:
            box = _rect(p)
        if not _inside_rect(box, usable):
            out.append((p["id"], "%s canopy %s crosses court wall/plot limits %s" %
                        ("mature" if mature else "modelled", tuple(round(v,3) for v in box), usable)))
    return out


def _lawn_with_pit(rect, center, radius, z, count=64):
    """An annulus tessellated from the pit ring to a rectangle; turf never caps the pit."""
    cx, cy = center
    # Include corner rays so every rectangle corner is represented exactly.
    from math import atan2
    angles = sorted(set([2*pi*i/count for i in range(count)] +
                        [atan2(y-cy,x-cx) % (2*pi) for x,y in
                         ((rect[0],rect[1]),(rect[2],rect[1]),(rect[2],rect[3]),(rect[0],rect[3]))]))
    inner, outer = [], []
    for angle in angles:
        dx, dy = cos(angle), sin(angle)
        distances = []
        if abs(dx) > 1e-12:
            distances.append(((rect[2] if dx > 0 else rect[0])-cx)/dx)
        if abs(dy) > 1e-12:
            distances.append(((rect[3] if dy > 0 else rect[1])-cy)/dy)
        distance = min(distances)
        inner.append([cx+radius*dx,cy+radius*dy,z])
        outer.append([cx+distance*dx,cy+distance*dy,z])
    return [[inner[i],outer[i],outer[(i+1)%len(inner)],inner[(i+1)%len(inner)]] for i in range(len(inner))], inner


def _paddle_clump(identifier, species, center, ground, data, *, bed, layer):
    """Staged basal paddle-leaf appearance, in the palette's young envelope.

    Dense overlapping leaves arise from several ground-level fans. Outer
    blades arch; inner blades stand up. Every blade has independent height,
    rotation and a measured final length:width ratio between 3 and 4.
    """
    import numpy as np
    row = require_species(species, data)
    assumed = row["placement_assumptions"]["procedural-clump"]
    height, spread = assumed["height"]["range_m"][0], assumed["spread"]["range_m"][0]
    faces, leaf_indices, blade_records = [], [], []
    for index in range(17):
        angle = index*2*pi*(3-5**.5)/2
        radial = np.array([cos(angle),sin(angle),0.])
        side = np.array([-sin(angle),cos(angle),0.])
        outer = index < 6
        root = radial*(.026+.009*(index%3))
        base = root+np.array([0.,0.,.055+.023*(index%4) if outer else .16+.062*(index%5)])
        blade_length = .53+.037*(index%5) if outer else .65+.028*(index%4)
        width = blade_length/((4.4+.13*(index%4)) if outer else (3.9+.12*(index%4)))
        tilt = .29+.015*(index%3) if outer else .06+.012*(index%4)
        rings=[]
        for segment in range(21):
            t=segment/20
            w=.008 if segment in (0,20) else sin(pi*t)**.48
            reach = tilt*blade_length*(t+.18*sin(pi*t))
            z = blade_length*(t-.23*t*t if outer else t-.035*t*t)
            point = base+radial*reach+np.array([0.,0.,z])
            tangent = radial*tilt+np.array([0.,0.,1-.46*t if outer else 1-.07*t])
            normal = np.cross(side,tangent);normal/=np.linalg.norm(normal)
            # Cross-section is a closed diamond: the ridge reads as a midrib,
            # unlike the previous equal-height radial cup.
            rings.append([(point-side*width*w/2).tolist(),(point-normal*.0018).tolist(),
                          (point+side*width*w/2).tolist(),(point+normal*.0035).tolist()])
        blade=[rings[0][::-1],rings[-1]]
        for a,b in zip(rings,rings[1:]):
            blade += [[a[k],a[(k+1)%4],b[(k+1)%4],b[k]] for k in range(4)]
        blade=[[f[0],f[k+1],f[k]] for f in blade for k in range(1,len(f)-1)]
        leaf_indices.extend(range(len(faces),len(faces)+len(blade)));faces+=blade
        blade_records.append(dict(face_indices=list(range(len(faces)-len(blade),len(faces))),outer=outer))
        # Petioles connect to their own basal fan, with overlap into the blade.
        top=base+np.array([0.,0.,.025])
        axis=top-root;axis/=np.linalg.norm(axis)
        u=side;v=np.cross(axis,u)
        a,b=[[(q+.004*(u*cos(k*2*pi/8)+v*sin(k*2*pi/8))).tolist() for k in range(8)] for q in (root,top)]
        stem=[a[::-1],b]+[[a[k],a[(k+1)%8],b[(k+1)%8],b[k]] for k in range(8)]
        faces += [[f[0],f[k],f[k+1]] for f in stem for k in range(1,len(f)-1)]
    points=[q for f in faces for q in f]
    lo=[min(q[k] for q in points) for k in range(3)];hi=[max(q[k] for q in points) for k in range(3)]
    # Normalize to the sole palette envelope, then independently measure
    # each real blade, including the effect of both coordinate factors.
    horizontal_scale=spread/max(hi[k]-lo[k] for k in (0,1))
    vertical_scale=height/(hi[2]-lo[2])
    # The measured blade guard below refuses normalization that destroys
    # the requested paddle proportions.
    faces=[[[center[0]+q[0]*horizontal_scale,center[1]+q[1]*horizontal_scale,
             ground+(q[2]-lo[2])*vertical_scale] for q in f] for f in faces]
    for record in blade_records:
        pts=np.unique(np.array([faces[i] for i in record["face_indices"]]).reshape(-1,3),axis=0)
        _,_,axes=np.linalg.svd(pts-pts.mean(axis=0))
        spans=np.ptp(pts@axes.T,axis=0)
        record["measured_length_width_ratio"]=float(spans[0]/spans[1])
        if not 3 <= record["measured_length_width_ratio"] <= 4:
            raise ValueError("paddle blade length:width outside authored 3:1--4:1 brief")
    mesh=_mesh(identifier,"dressing","strelitzia-foliage",faces,
               "ASSUMED authored young Strelitzia reginae paddle-leaf clump; non-flowering young stage; photographic likeness and nursery supply UNVERIFIED",kind="plant-clump")
    mesh.update(species=species,center=center,spread_m=row["spread"]["range_m"][1],bed=bed,
                planting_layer=layer,root_z_m=ground,leaf_face_indices=leaf_indices,blade_records=blade_records,bevel_m=.0001)
    return mesh


def _botanical_clump(identifier, species, center, ground, data, *, bed, layer):
    """Authored leaves on connected petioles, not an imported species stand-in.

    Aspidistra has basal lanceolate blades; Strelitzia has longer upright
    petioles and broad paddle blades. Young size is authored only in the
    palette. Photographic likeness and nursery supply need lead review.
    """
    if species == "Strelitzia reginae":
        return _paddle_clump(identifier,species,center,ground,data,bed=bed,layer=layer)
    row = require_species(species, data)
    assumed = row["placement_assumptions"]["procedural-clump"]
    height, spread = assumed["height"]["range_m"][0], assumed["spread"]["range_m"][0]
    faces = []
    leaf_indices = []
    for index in range(10):
        angle = index*2*pi/10
        c, sn = cos(angle), sin(angle)
        blade_base = .28 if species == "Aspidistra elatior" else .60
        rings = []
        # Horizontal sections describe a swept, tapered blade with a
        # midrib bend. The four points close real thickness, in order.
        for t, width in ((0,.003),(.2,.08),(.55,.10),(.85,.06),(1,.002)):
            z = blade_base + t*(1-blade_base)
            reach = .03 + .14*t + .035*sin(pi*t)
            rings.append([[c*reach-sn*width,sn*reach+c*width,z],
                          [c*(reach-.003),sn*(reach-.003),z],
                          [c*reach+sn*width,sn*reach-c*width,z],
                          [c*(reach+.003),sn*(reach+.003),z]])
        start=len(faces)
        faces += [rings[0][::-1],rings[-1]]
        for a,b in zip(rings,rings[1:]):
            faces += [[a[k],a[(k+1)%4],b[(k+1)%4],b[k]] for k in range(4)]
        leaf_indices.extend(range(start,len(faces)))
        stem_rings = [[[c*.03 + .003*cos(k*2*pi/8),sn*.03 + .003*sin(k*2*pi/8),zz]
                       for k in range(8)] for zz in (0,blade_base+.02)]
        a,b = stem_rings
        faces += [a[::-1],b] + [[a[k],a[(k+1)%8],b[(k+1)%8],b[k]] for k in range(8)]
    # Normalize the authored appearance to its recorded young size; this
    # does not edit an external mesh or introduce another species authority.
    points = [q for f in faces for q in f]
    lo = [min(q[i] for q in points) for i in range(3)]
    hi = [max(q[i] for q in points) for i in range(3)]
    plan_scale = spread/max(hi[i]-lo[i] for i in (0,1))
    faces = [[[center[0] + (q[0]-(hi[0]+lo[0])/2)*plan_scale,
               center[1] + (q[1]-(hi[1]+lo[1])/2)*plan_scale,
               ground + (q[2]-lo[2])*height/(hi[2]-lo[2])] for q in f] for f in faces]
    # Swept blade rings are not coplanar quads. Triangulate their actual
    # closed surfaces before exporting; no render-side geometry repair.
    source_faces=faces
    leaf_indices=[j for j,(i,_) in enumerate((i,k) for i,f in enumerate(source_faces) for k in range(1,len(f)-1)) if i in leaf_indices]
    faces = [[face[0],face[k],face[k+1]] for face in faces for k in range(1,len(face)-1)]
    mesh = _mesh(identifier,"dressing","garden-foliage",faces,
                 "ASSUMED authored young " + species + " botanical appearance; photographic likeness UNVERIFIED; care: " + row["source_url"]["value"],kind="plant-clump")
    mesh.update(species=species,center=center,spread_m=row["spread"]["range_m"][1],bed=bed,planting_layer=layer,root_z_m=ground,leaf_face_indices=leaf_indices)
    return mesh


def _top_clump(identifier, species, center, soil_z, data, bed):
    """Species-specific solid leaves/shoots; palette owns all size claims.

    Rosemary has branched horizontal stems with paired needle leaves and
    descending inward trails. Aloe has thick tapered radial rosette blades.
    These are ASSUMED authored botanical appearances, not product assets.
    """
    import numpy as np
    row = require_species(species,data)
    assumption = row["placement_assumptions"]["procedural-clump"]
    height = assumption["height"]["range_m"][0]
    spread = assumption["spread"]["range_m"][0]
    faces = []
    leaf_source_indices = []

    def tube(a,b,r):
        # Metre-native closed tube: every leaf physically meets its stem.
        a,b = np.array(a),np.array(b)
        axis = b-a; axis /= np.linalg.norm(axis)
        helper = np.array([0.,0.,1.]) if abs(axis[2]) < .9 else np.array([1.,0.,0.])
        u = np.cross(axis,helper); u /= np.linalg.norm(u)
        v = np.cross(axis,u)
        rings = [[(p+r*(u*cos(k*2*pi/6)+v*sin(k*2*pi/6))).tolist() for k in range(6)] for p in (a,b)]
        low,high = rings
        return [low[::-1],high]+[[low[k],low[(k+1)%6],high[(k+1)%6],high[k]] for k in range(6)]

    if species == "Aloe vera":
        for index in range(15):
            angle = index*2*pi/15
            c,s = cos(angle),sin(angle)
            length = .95 if index%3==0 else .65+.10*(index%3)
            rings=[]
            for t,width in ((0,.018),(.18,.055),(.50,.040),(.80,.019),(1,.001)):
                reach = .015+.165*t
                z = length*(t**.72)
                rings.append([[c*reach-s*width,s*reach+c*width,z],
                              [c*(reach-(.0008+.014*(1-t))),s*(reach-(.0008+.014*(1-t))),z],
                              [c*reach+s*width,s*reach-c*width,z],
                              [c*(reach+(.0008+.014*(1-t))),s*(reach+(.0008+.014*(1-t))),z]])
            faces += [rings[0][::-1],rings[-1]]
            for a,b in zip(rings,rings[1:]):
                faces += [[a[k],a[(k+1)%4],b[(k+1)%4],b[k]] for k in range(4)]
        leaf_source_indices=list(range(len(faces)))
        material="top-aloe-foliage"
    else:
        # A basal woody crown and alternating needle-covered branchlets.
        faces += tube((0,0,0),(0,0,.15),.006)
        for index in range(14):
            sign = -1 if index%2 else 1
            tip=(sign*(.34+.012*index), .06*cos(index*1.7), .10+.007*(index%5))
            origin=(0,0,.09)
            faces += tube(origin,tip,.003)
            for j in range(1,18):
                t=j/18
                point=tuple(origin[k]+t*(tip[k]-origin[k]) for k in range(3))
                for side in (-1,1):
                    leaf=(point[0]+sign*.024,point[1]+side*.022,point[2]+.018)
                    leaf_faces=tube(point,leaf,.0015)
                    leaf_source_indices.extend(range(len(faces),len(faces)+len(leaf_faces)))
                    faces += leaf_faces
        for index in range(7):
            x=(index-3)*.12
            points=[(0,0,.08),(x,-.08,.10),(x,-.17,.04),(x,-.24,-.10)]
            for a,b in zip(points,points[1:]):
                faces += tube(a,b,.003)
                for j in range(1,7):
                    point=tuple(a[k]+j/7*(b[k]-a[k]) for k in range(3))
                    for side in (-1,1):
                        leaf_faces=tube(point,(point[0]+side*.022,point[1]-.008,point[2]+.01),.0015)
                        leaf_source_indices.extend(range(len(faces),len(faces)+len(leaf_faces)))
                        faces += leaf_faces
        material="top-rosemary-foliage"
    pts=[q for f in faces for q in f]
    lo=[min(q[i] for q in pts) for i in range(3)]
    hi=[max(q[i] for q in pts) for i in range(3)]
    plan_scale=spread/max(hi[i]-lo[i] for i in (0,1))
    # Rosemary trails inward (negative scene Y); only its longitudinal
    # span carries the card's spread. Young narrow depth is ASSUMED.
    y_scale = .32/(hi[1]-lo[1]) if species != "Aloe vera" else plan_scale
    root_z = soil_z
    # Rosemary height includes its descending shoots; root remains at soil.
    bottom = -height/3 if species != "Aloe vera" else 0
    faces=[[[center[0]+q[0]*plan_scale,
             center[1]+q[1]*y_scale,
             soil_z+bottom+(q[2]-lo[2])*height/(hi[2]-lo[2])] for q in f] for f in faces]
    # Include a real basal stem from soil into the crown after normalisation.
    faces += tube((center[0],center[1],root_z),(center[0],center[1],soil_z+height*.20),.005)
    leaf_set=set(leaf_source_indices)
    leaf_indices=[j for j,(i,_) in enumerate((i,k) for i,f in enumerate(faces) for k in range(1,len(f)-1)) if i in leaf_set]
    faces=[[face[0],face[k],face[k+1]] for face in faces for k in range(1,len(face)-1)]
    mesh=_mesh(identifier,"dressing",material,faces,
               "ASSUMED authored young "+species+" appearance; photographic likeness and nursery supply UNVERIFIED; care: "+row["source_url"]["value"],kind="plant-clump")
    spacing=row["placement_assumptions"].get("spacing_spread",{}).get("value",row["spread"]["range_m"][0] if row["spread"]["range_m"] else spread)
    mesh.update(species=species,zone="top",center=center,spread_m=spacing,bed=bed,
                trough=bed,planting_layer="trough",root_z_m=root_z,leaf_face_indices=leaf_indices,sun_hours=direct_sun_hours(*center))
    return mesh


def _top_garden(spec, data, credits, meshes, props, objects, plants):
    """Construct deck-seated troughs, physical pads and clear seating spaces."""
    surface = spec["parking2"]["deck"]["z_top"]
    if abs(surface-TOP_SURFACE)>1e-9:
        raise ValueError("top garden datum changed; coordinate deck, roof and routes")
    troughs,benches = [],[]
    for name,rect,species,centers in TOP_TROUGHS:
        body,soil = _steel_trough(rect,surface,TOP_TROUGH_HEIGHT)
        identifier="landscape-top-trough-"+name
        for suffix,faces,material,kind in (("body",body,"top-trough-coating","steel-trough"),
                                          ("soil",soil,"garden-soil","planter-soil")):
            item=_mesh("top-trough-"+name+"-"+suffix,"furniture",material,faces,
                       "ASSUMED slim powder-coated steel trough; "+TROUGH_COLOUR["name"]+"; supplier weathering/loaded weight UNVERIFIED",kind=kind)
            item.update(zone="top",trough=identifier)
            meshes.append(item)
        obj=dict(id=identifier,rect=rect,zone="top",bottom_m=surface,top_m=surface+TOP_TROUGH_HEIGHT,
                 species=species,soil_z_m=surface+TOP_TROUGH_HEIGHT-.005,centers=centers)
        # Container recipe species is schedule metadata, not a second plant.
        objects.append({k:v for k,v in obj.items() if k != "species"});troughs.append(obj)
        for i,center in enumerate(centers):
            clump=_top_clump("top-%s-%02d"%(name,i),species,center,obj["soil_z_m"],data,identifier)
            meshes.append(clump); plants.append(clump)
    native=PROP_BOUNDS["sf_wooden_bench"]
    plan_scale=BENCH_LENGTH_M/(native[1][2]-native[0][2])
    height_scale=BENCH_HEIGHT_M/(native[1][1]-native[0][1])
    for i,(center,facing) in enumerate((((10.60,-22.10),(1,0)),((14.00,-22.10),(-1,0)))):
        bench=_prop("landscape-top-bench-%d"%i,"sf_wooden_bench",center,surface+.012,BENCH_HEIGHT_M,
                    "ASSUMED backless bench on paving slab, facing the central garden; 0.40 m seat height, Time-Saver 2nd ed. p.340-11; "+credits["sf_wooden_bench"],zone="top")
        override(bench,"scale",[plan_scale,plan_scale,height_scale],"recorded bench axiswise exception: 1.8 m length and 0.4 m seat height")
        override(bench,"position",[center[0]-plan_scale*(native[0][0]+native[1][0])/2,
                                   center[1]+plan_scale*(native[0][2]+native[1][2])/2,surface+.012],
                 "centre actual final-scale bench on its slab")
        bench["facing"]=facing
        rect=_rect(bench);pad=(rect[0]-.02,rect[1]-.02,rect[2]+.02,rect[3]+.02)
        knee=(rect[2],rect[1],rect[2]+BENCH_KNEE_CLEAR,rect[3]) if facing[0]>0 else (rect[0]-BENCH_KNEE_CLEAR,rect[1],rect[0],rect[3])
        slab=_mesh("top-bench-slab-%d"%i,"ground","stepping-stone",_box(pad[0],pad[1],surface,pad[2],pad[3],surface+.012),
                   "ASSUMED flush bench paving slab, no plinth",kind="bench-slab")
        slab["zone"]="top";meshes.append(slab);props.append(bench)
        benches.append(dict(id=bench["id"],slab_id=slab["id"],knee_rect=knee,required_knee_m=BENCH_KNEE_CLEAR,facing=facing))
    # Turf is the central field; paving and pads have their own exposed faces.
    from shapely.geometry import box
    from shapely.ops import triangulate
    meshes[:] = [m for m in meshes if m["id"] not in ("landscape-grass-top-deck","landscape-grass-top-roof")]
    cutouts = [box(*PATHS["study"]),box(*PATHS["gate-link"])]
    cutouts += [box(*_mesh_rect(m)) for m in meshes if m.get("part_kind")=="bench-slab"]
    for name,rect in (("deck",DECK),("roof",ROOF)):
        field=box(rect[0]+RAIL_CLEAR,-23.04,rect[2]-RAIL_CLEAR,-21.20)
        for cutout in cutouts:
            field=field.difference(cutout)
        faces=[[[x,y,surface+.003] for x,y in list(t.exterior.coords)[:-1]]
               for t in triangulate(field) if field.covers(t)]
        meshes.append(_mesh("grass-top-"+name,"ground","artificial-grass",faces,
                            "ASSUMED central artificial turf, clear paving and bench pads",kind="finish-layer",surface=True,occupied_side=(0,0,1)))
    return troughs,benches


def top_garden_violations(meshes, props, plan, *, spec_surface=TOP_SURFACE,
                          deck=DECK, roof=ROOF, rail_clear=RAIL_CLEAR):
    """Built top envelopes, surface contact, soil seating and routes fail closed.

    Optional outline/datum inputs prove this geometry rule away from D1.
    Ground finishes may reach the rails; containers and planting may not.
    """
    out=[]
    items=[m for m in meshes if m.get("zone")=="top" or m["id"].startswith("landscape-top-")]+[p for p in props if p.get("zone")=="top"]
    for item in items:
        kind=item.get("part_kind")
        if kind in ("finish-layer","stepping-stone"):
            continue
        if not (_inside_rect(_rect(item),deck,rail_clear) or _inside_rect(_rect(item),roof,rail_clear)):
            out.append((item["id"],"built top envelope crosses outline or rail strip"))
        if "faces" in item:
            bottom=min(q[2] for f in item["faces"] for q in f)
            if kind in ("steel-trough","planter","bench-slab") and abs(bottom-spec_surface)>1e-6:
                out.append((item["id"],"container/slab does not sit on deck surface"))
            if kind == "steel-trough":
                import numpy as np
                downward=[]
                for face in item["faces"]:
                    a,b,c=np.array(face[:3])
                    normal=np.cross(b-a,c-a)
                    if normal[2]<0 and abs(normal[2])>np.linalg.norm(normal)*.5:
                        downward.append(face)
                base=min(downward,key=lambda f:sum(q[2] for q in f)/len(f)) if downward else []
                if not base or any(abs(q[2]-spec_surface)>1e-6 for q in base):
                    out.append((item["id"],"trough base is not fully seated on deck surface"))
        if item.get("species"):
            row=require_species(item["species"])
            ixora=item["species"]=="Ixora coccinea"
            threshold=json.loads(PALETTE.read_text())["design_assumptions"]["full_sun_screen"]["hours"]
            quote=str(row["light"]["value"]).lower()
            if ixora:
                if (not item.get("bed","").startswith("top-pot-") or row["light"]["status"]!="VERIFIED" or
                    "full sun for best flowering" not in quote or len(direct_sun_hours(*item["center"]))<=threshold):
                    out.append((item["id"],"top Ixora requires existing pot, checked flowering quote and full-sun hours"))
            elif "top" not in row["zones"]["value"]:
                out.append((item["id"],"species lacks verified top-zone placement"))
            if item.get("trough"):
                trough=next((t for t in plan.get("top_troughs",[]) if t["id"]==item["trough"]),None)
                if (trough is None or not _inside_rect((*item["center"],*item["center"]),trough["rect"]) or
                    abs(item["root_z_m"]-trough["soil_z_m"])>1e-6):
                    out.append((item["id"],"plant root is not seated in its trough soil"))
    routes,ground=walking_routes(meshes)
    out += [(pid,"top walking route "+name) for pid,name in route_violations(items,routes,ground)]
    if plan.get("gate_route"):
        out += gate_route_violations(items,plan["gate_route"])
    by_id={i["id"]:i for i in items}
    for seating in plan.get("top_benches",[]):
        bench=by_id.get(seating["id"]);slab=by_id.get(seating["slab_id"])
        if bench is None or slab is None:
            out.append((seating["id"],"bench lacks physical slab"));continue
        top=max(q[2] for f in slab["faces"] for q in f)
        if not _inside_rect(_rect(bench),_rect(slab)) or abs(bench["position"][2]-top)>1e-6:
            out.append((bench["id"],"bench is not seated on its slab"))
        if tuple(bench.get("facing",()))!=tuple(seating["facing"]) or abs(bench["facing"][0])!=1:
            out.append((bench["id"],"bench facing differs from clear knee side"))
        others=[i for i in items if i["id"] not in (bench["id"],slab["id"]) and i.get("part_kind") not in ("finish-layer","stepping-stone","bench-slab")]
        out += [(bench["id"],"knee space blocked by "+pid) for pid,_ in route_violations(others,{"knee":seating["knee_rect"]},{"knee":spec_surface})]
    return out


def gate_route_violations(items, route):
    """D2 walking contact over an unchanged piecewise-linear driveway.

    route contains its y limits and measured pairs of x and surface z.
    Subtract each segment's sloping floor from actual triangles, so the
    tested vertical walking volume is exactly floor to floor plus 2 m.
    The ramp is shared access, not a newly paved pedestrian ramp.
    """
    import numpy as np
    from .route_geometry import prop_triangles
    from .render_support import _triangles, _tri_box_overlap
    out=[]
    for item in items:
        for (xa,za),(xb,zb) in zip(route["profile"],route["profile"][1:]):
            rect=(xa,route["y0"],xb,route["y1"])
            if _rect_overlap_area(_rect(item),rect)<=1e-6:
                continue
            triangles=prop_triangles(item,walking_top_m=max(za,zb)+2) if "asset" in item else _triangles([item])[0]
            local=triangles.copy()
            local[:,:,2]-=za+(local[:,:,0]-xa)*(zb-za)/(xb-xa)
            lo=np.array([xa,rect[1],0.]);hi=np.array([xb,rect[3],2.])
            nearby=np.all(local.min(axis=1)<=hi,axis=1)&np.all(local.max(axis=1)>=lo,axis=1)
            if nearby.any() and _tri_box_overlap(local[nearby],(lo+hi)/2,(hi-lo)/2).any():
                out.append((item["id"],"street-gate ramp walking envelope"));break
    return out


def review_candidate(spec, lay=None):
    """Measured G1/G2 proposal for lead diagnosis, never a scene-export path.

    build() refuses unresolved geometry. No photographic approval is inferred.
    """
    if lay is None:
        from . import villa_r11 as R
        lay = R.design("D1")
    data, credits = _plant_data(), _credits()
    record = json.loads(PALETTE.read_text())
    meshes, props, objects, plants = [], [], [], []
    if len([d for d in spec["doors"] if d.get("garden")]) != 4:
        raise ValueError("garden-door count changed; redraw approaches")
    radius = record["design_assumptions"]["east_tree_pit"]["diameter_m"]/2
    tree_center = tuple(record["design_assumptions"]["east_tree_position"]["center_m"])
    lawn, ring = _lawn_with_pit(EAST, tree_center, radius, GROUND+.003)
    meshes.append(_mesh("grass-east", "ground", "artificial-grass", lawn,
                        "ASSUMED artificial turf with an open tree pit", kind="finish-layer", surface=True, occupied_side=(0,0,1)))
    meshes.append(_mesh("tree-pit-east", "ground", "garden-gravel", [ring],
                        "ASSUMED 1.2 m diameter gravel tree pit; roots/drainage UNVERIFIED", kind="tree-pit", surface=True, occupied_side=(0,0,1)))
    for name, rect in (("north", (15.412,-23.591,EAST[0],-20.351)),
                       ("top-deck",DECK),("top-roof",ROOF)):
        z = 0.0 if name.startswith("top") else GROUND
        meshes.append(_mesh("grass-"+name,"ground","artificial-grass",_quad(*rect,z+.003),
                            "ASSUMED drained artificial grass; "+name,kind="finish-layer",surface=True,occupied_side=(0,0,1)))
    for name, rect in PATHS.items():
        _stones(name,rect,0.0 if name=="study" else GROUND,meshes)
    beds = dict(BEDS)
    beds["west"] = tuple(record["design_assumptions"]["north_garden_g4"]["beds"]["west"])
    for name,rect in beds.items():
        if any(not inside_yard(x,y) for x,y in _box_perimeter_points(*rect)):
            raise ValueError(name+" bed leaves yard")
        if any(_rect_overlap_area(rect,r[:4]) > 1e-6 for r in garden_level_rooms(lay)):
            raise ValueError(name+" bed enters garden-level room")
        if name == "west":
            continue  # G4 soil and slim edging are constructed together below.
        meshes.append(_mesh("bed-"+name,"ground","garden-gravel",_quad(*rect,GROUND+.008),
                            "ASSUMED boundary bed, three primary layers; G2 young planting",kind="finish-layer",surface=True,occupied_side=(0,0,1)))

    def plant(pid, asset, center, *, zone="lower", bed=None, layer="accent", ground=GROUND):
        species = ASSET_SPECIES[asset]
        row = require_species(species,data)
        assumptions = row["placement_assumptions"].get(asset,{})
        height = assumptions.get("height",row["height"])["range_m"][0]
        # Legacy heights within an explicit assumption are keyed by context.
        context = assumptions.get("contexts",{}).get(pid, {})
        height = context.get("height_m",height)
        spacing = row["placement_assumptions"].get("spacing_spread",{})
        spread = spacing.get("value",row["spread"]["range_m"][0] if row["spread"]["range_m"] else None)
        if spread is None:
            spread = assumptions["spread"]["range_m"][1]
        p = _prop(pid,asset,center,ground,height,
                  "%s; care: %s (knowledge/garden-palette.json); %s; dimensions per tracked evidence/ASSUMED nursery intent" %
                  (species,row["source_url"]["value"],credits[asset]),zone=zone)
        fill_defaults(p,dict(species=species,center=center,spread_m=spread,bed=bed,planting_layer=layer,
                             asset_measurement=dict(native_gltf_y_up_bounds_m=dict(min=PROP_BOUNDS[asset][0],max=PROP_BOUNDS[asset][1]),
                                                    uniform_scale=p["scale"],height_m=height)))
        props.append(p); plants.append(p)
        return p

    tree = plant("landscape-tree-east","sf_frangipani",tree_center,bed="east",layer="tree")
    # Plant the measured trunk, not the asymmetrical canopy box centre, in
    # the lawn opening. Scaling about the canopy centre would miss the pit.
    measurement = data["Plumeria rubra"]["appearance_measurements"]["sf_frangipani"]
    measured_bounds = measurement["native_gltf_y_up_bounds_m"]
    exact_scale = data["Plumeria rubra"]["appearance_measurements"]["sf_frangipani"]["scale"]
    override(tree, "scale", exact_scale, "lead decision 2026-10-06: uniform scale holds measured maximum canopy span to verified lower spread 4.6 m")
    tree["asset_measurement"]["uniform_scale"] = exact_scale
    tree["asset_measurement"]["native_gltf_y_up_bounds_m"] = measured_bounds
    ax, _, az = measurement["trunk_base_gltf_m"]
    override(tree, "position", [tree_center[0]-tree["scale"]*ax,
                                tree_center[1]+tree["scale"]*az, GROUND],
             "D4: seat the measured trunk in its moving pit, in the lawn, offset from centre for a clear door route")
    tree["asset_measurement"]["trunk_base_gltf_m"] = measurement["trunk_base_gltf_m"]
    tree["label"] += "; ASSUMED rendered stage: young pruned tree; stand-in model proportions wider than the species; canopy span held to the verified 4.6 m spread; lead decision 2026-10-06"
    trees = (("east","sf_frangipani","Plumeria rubra",tree_center,tree["asset_measurement"]["height_m"],0),)
    # Uniform species drifts, three height strata per actual boundary bed.
    # Ixora's spacing spread is explicitly ASSUMED in the palette, not a
    # sourced mature spread. Strelitzia and Aspidistra use the card spreads.
    from . import garden_shade as SHADE
    from shapely.geometry import box as polygon_box, Polygon
    from shapely.ops import triangulate
    shade = record["design_assumptions"]["north_garden_g4"]
    ground_beds = {"west": beds["west"], "west-accent": tuple(shade["accent_bed"])}
    gravel = polygon_box(*NORTH_COURT).intersection(Polygon(YARD))
    for rect in ground_beds.values():gravel = gravel.difference(polygon_box(*rect))
    gravel_faces = [[[x,y,GROUND+.003] for x,y in list(t.exterior.coords)[:-1]]
                    for t in triangulate(gravel) if gravel.covers(t)]
    meshes.append(_mesh("gravel-west","ground","garden-gravel",gravel_faces,
                        "ASSUMED mineral gravel paths/mulch; covered GF balcony portion has gravel only",kind="finish-layer",surface=True,occupied_side=(0,0,1)))
    for name, (x0,y0,x1,y1) in ground_beds.items():
        meshes.append(_mesh("bed-west" if name=="west" else "accent-bed-west","ground","garden-soil",_quad(x0,y0,x1,y1,GROUND),
                            "North garden: in-ground soil at court datum; root/drainage engineering UNVERIFIED",kind="soil-bed",surface=True,occupied_side=(0,0,1)))
        edge = (_box(x0,y0,GROUND,x1,y0+.015,GROUND+.018)+
                _box(x0,y1-.015,GROUND,x1,y1,GROUND+.018)+
                _box(x0,y0+.015,GROUND,x0+.015,y1-.015,GROUND+.018)+
                _box(x1-.015,y0+.015,GROUND,x1,y1-.015,GROUND+.018))
        meshes.append(_mesh("edging-"+name,"ground","trellis",edge,
                            "ASSUMED 15 mm slim timber edging, 18 mm above court; no raised container",kind="bed-edge"))
    for drift in shade["drifts"]:
        for i, center in enumerate(drift["centers_m"]):
            species = drift["species"]
            constructor = _botanical_clump if species == "Aspidistra elatior" else SHADE.clump
            clump = constructor("west-%s-%02d"%(drift["layer"],i),species,center,GROUND,data,bed="west",layer=drift["layer"])
            meshes.append(clump);plants.append(clump)
    clump = SHADE.clump("west-rhapis-accent","Rhapis excelsa",shade["accent_center_m"],GROUND,data,bed="west-accent",layer="accent")
    clump["label"] += "; ASSUMED root barrier; keep centre >=1.0 m from walls and paths"
    meshes.append(clump);plants.append(clump)
    meshes.append(SHADE.stone("west-feature-stone",shade["feature_stone_center_m"],GROUND))
    for i, center in enumerate(((17.90,-21.75),(18.90,-21.75),(19.60,-22.45))):
        # Young Ixora at 0.55 m is the recorded default, not the obsolete
        # north nursery context at 1.0 m, whose canopy would close the path.
        plant("landscape-north-mid-drift-%02d"%i,"sf_ixora",center,bed="north",layer="mid")
    for i, x in enumerate((17.90,18.75,19.60)):
        for species, layer, y in (("Strelitzia reginae","back",-20.95),
                                  ("Aspidistra elatior","front",-22.43)):
            clump = _botanical_clump("north-%s-%02d"%(layer,i),species,(x,y),GROUND,data,bed="north",layer=layer)
            meshes.append(clump); plants.append(clump)

    for name, x, y in (("west", *shade["trellis_start_m"]), ("north",18.75,-20.641)):
        if name == "east":
            frame = _box(x-.04, y, GROUND, x, y+1.5, GROUND+2.2)
        elif name == "south":
            frame = _box(x-.75, y, GROUND, x+.75, y+.04, GROUND+2.2)
        elif name == "north":
            frame = _box(x-.75, y, GROUND, x+.75, y+.04, GROUND+2.2)
        else:  # west
            frame = _box(x, y, GROUND, x+.04, y+1.5, GROUND+2.2)
        climber_species = "Bougainvillea glabra" if name == "north" else "Cissus alata"
        climber_source = require_species(climber_species,data)["source_url"]["value"]
        pts = [p for face in frame for p in face]
        fx0, fy0, fx1, fy1 = min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)
        along_x = fx1-fx0 > fy1-fy0
        open_frame = []
        for fraction in (0, .25, .5, .75, 1):
            if along_x:
                xx = fx0 + (fx1-fx0)*fraction
                open_frame += _box(xx-.012, fy0, GROUND, xx+.012, fy1, GROUND+2.2)
            else:
                yy = fy0 + (fy1-fy0)*fraction
                open_frame += _box(fx0, yy-.012, GROUND, fx1, yy+.012, GROUND+2.2)
        for zz in (GROUND+.18, GROUND+1.05, GROUND+2.17):
            open_frame += _box(fx0, fy0, zz, fx1, fy1, zz+.025)
        meshes.append(_mesh("trellis-"+name, "furniture", "trellis", open_frame,
                            "ASSUMED open timber trellis members for " + climber_species + "; care: " + climber_source, kind="trellis"))
        # Woody stems fork across the open members; procedural leaves and bracts are placed separately.
        branches = []
        def branch_box(x0, y0, z0, x1, y1, z1):
            # The wall face supports the frame. Keep every stem on that frame's yard side.
            return _box(max(fx0, x0), max(fy0, y0), z0,
                        min(fx1, x1), min(fy1, y1), z1)
        for fraction in (.2, .5, .8):
            if along_x:
                xx = fx0 + (fx1-fx0)*fraction
                branches += branch_box(xx-.009, fy0-.008, GROUND+.08, xx+.009, fy0+.01, GROUND+1.92)
                branches += branch_box(xx-.11, fy0-.008, GROUND+1.17, xx+.11, fy0+.01, GROUND+1.19)
                branches += branch_box(xx-.009, fy0-.09, GROUND+1.50, xx+.009, fy1+.09, GROUND+1.52)
            else:
                yy = fy0 + (fy1-fy0)*fraction
                branches += branch_box(fx0-.008, yy-.009, GROUND+.08, fx0+.01, yy+.009, GROUND+1.92)
                branches += branch_box(fx0-.008, yy-.11, GROUND+1.17, fx0+.01, yy+.11, GROUND+1.19)
                branches += branch_box(fx0-.09, yy-.009, GROUND+1.50, fx1+.09, yy+.009, GROUND+1.52)
        meshes.append(_mesh("climber-branches-"+name, "dressing", "trellis", branches,
                            "ASSUMED young branched " + climber_species + " woody growth", kind="climber-branch"))
        # The renderer hides this source mesh after deriving the leaf envelope from its bounds.
        # Use the actual closed branch form as its source so the part boundary never admits a mass box.
        meshes.append(_mesh("climber-"+name, "dressing", "bougainvillea-bract" if name=="north" else "grape-ivy-leaf", branches,
                            "ASSUMED thin young " + climber_species + "; target frame coverage 35%; care: " + climber_source, kind="climber"))


    for mesh in meshes:
        if mesh.get("part_kind") in ("climber", "climber-branch"):
            mesh["species"] = "Bougainvillea glabra" if mesh["id"].endswith("north") else "Cissus alata"
            mesh["root_z_m"] = GROUND
            if mesh.get("part_kind") == "climber" and mesh["species"] == "Cissus alata":
                mesh["stem_mesh"] = "landscape-climber-branches-west"

    for name, center in (
            ("dining-w",(15.882,-22.97)), ("dining-e",(17.896,-22.97)),
            ("living-north-w",(19.55,-22.97)), ("living-north-e",(21.564,-22.97)),
):
        species = "Ixora coccinea" if not name.startswith("lounge") else "Aspidistra elatior"
        potdata = record["design_assumptions"]["door_pot"]
        if species == "Ixora coccinea":
            pp = plant("landscape-door-pot-"+name,"sf_ixora",center,bed="door-pot-"+name,ground=GROUND+potdata["height_m"]-.005)
        else:
            pp = _botanical_clump("door-pot-"+name,species,center,GROUND+potdata["height_m"]-.005,data,bed="door-pot-"+name,layer="accent")
            meshes.append(pp); plants.append(pp)
        rect = (center[0]-.259,center[1]-.259,center[0]+.259,center[1]+.259)
        objects.append(dict(id="landscape-door-pot-"+name+"-planter",rect=rect,bottom_m=GROUND,top_m=GROUND+.4))
        body,rim,soil = _pot(*center,GROUND,potdata["lower_radius_m"],potdata["upper_radius_m"],potdata["height_m"])
        for suffix,mat,faces,kind in (("body","terracotta-red-glaze",body,"planter"),
                                      ("rim","terracotta-red-glaze",rim,"planter-rim"),
                                      ("soil","garden-soil",soil,"planter-soil")):
            meshes.append(_mesh("door-pot-planter-"+name+"-"+suffix,"furniture",mat,faces,
                                "ASSUMED glazed ceramic tapered pot; terracotta-red client decision 2026-10-05; planted " + species + "; directly on turf",kind=kind))
    # G4: bistro/pots removed per client. The old swing is architecturally
    # covered; the shade layout has no accepted open motion envelope.
    swing = None
    # Two existing pot positions redesigned as planted glazed pots, with no plinth.
    # Ixora is the brief's explicit top-zone exception, conditional on sun evidence.
    for i, center in enumerate(((7.40,-21.20),(9.30,-22.95))):
        potdata = record["design_assumptions"]["door_pot"]
        body,rim,soil = _pot(*center,TOP_SURFACE,potdata["lower_radius_m"],potdata["upper_radius_m"],potdata["height_m"])
        for suffix,mat,faces,kind in (("body","terracotta-red-glaze",body,"planter"),
                                      ("rim","terracotta-red-glaze",rim,"planter-rim"),
                                      ("soil","garden-soil",soil,"planter-soil")):
            item = _mesh("top-pot-%d-%s"%(i,suffix),"furniture",mat,faces,
                         "ASSUMED planted glazed ceramic pot; replaces stone-look bowl; no plinth",kind=kind)
            item["zone"]="top"
            meshes.append(item)
        ixora = require_species("Ixora coccinea",data)
        full_sun = record["design_assumptions"]["full_sun_screen"]["hours"]
        if (ixora["light"]["status"] == "VERIFIED" and
            "full sun for best flowering" in str(ixora["light"]["value"]).lower() and
            len(direct_sun_hours(*center)) > full_sun):
            pp=plant("landscape-top-north-ixora-%d"%i,"sf_ixora",center,zone="top",bed="top-pot-%d"%i,
                     layer="accent",ground=TOP_SURFACE+potdata["height_m"]-.005)
        else:
            pp=_top_clump("top-pot-aloe-%d"%i,"Aloe vera",center,TOP_SURFACE+potdata["height_m"]-.005,
                          data,"top-pot-%d"%i)
            pp.pop("trough");pp["planting_layer"]="accent"
            meshes.append(pp);plants.append(pp)
        pp["sun_hours"] = direct_sun_hours(*center)
        objects.append(dict(id="landscape-top-pot-%d"%i,rect=(center[0]-.259,center[1]-.259,center[0]+.259,center[1]+.259),zone="top"))
    troughs, benches = _top_garden(spec, data, credits, meshes, props, objects, plants)


    exposure = {name:direct_sun_hours((r[0]+r[2])/2,(r[1]+r[3])/2) for name,r in beds.items()}
    notes = ["North garden G4: lush shade foliage in ground-level soil beds; gravel under the GF balcony. Bistro and lounge pots removed per client 2026-10-06. Covered swing omitted; client to confirm removal. Cissus alata replaces star jasmine on the open timber trellis; light applicability PARTIAL, Cairo winter suitability UNVERIFIED.",
             "G1/G2 review candidate: artificial turf, stepping stones, one Plumeria in the lawn, offset from centre for a clear door route and ASSUMED 1.2 m gravel tree pit.",
             "Only knowledge/garden-palette.json supplies botanical dimensions, sources and placement assumptions. Egypt performance and root behaviour over the basement slab are UNVERIFIED.",
             "Retained east-yard boundary bed and terracotta-red glazed door pots; north garden G4 shade beds and grape ivy on open timber. G3 low steel troughs with rosemary/aloe drifts, two benches on slabs and a gate-link path; no shade tree placed.",
             "ASSUMED drip irrigation to retained beds/containers; tree-pit watering/drainage needs local nursery and engineering review.",
             "Trough colour: " + TROUGH_COLOUR["name"] + "; authored appearance ASSUMED, not a manufacturer finish. Powder-coat weathering in Egyptian sun and loaded deck weight UNVERIFIED; supplier data sheet and engineer decide before ordering.",
             "Top container roots/deep rooting and waterproofing over the basement slab UNVERIFIED: local nursery and waterproofing/structural consultant must confirm; no deep-rooted tree specified.",
             "Round-3 potted small shade tree not placed: no verified top-zone shade-tree species fits the palette; open client/nursery item.",
             "Ursinia omitted: palette light UNVERIFIED and zone gf-beds does not establish this top container placement.",
             "Illustrative 09:00-17:00 direct hours screen: "+str(exposure)]
    ramp=spec["parking2"]["ramp"]
    gate_route=dict(profile=ramp["profile"],y0=PATHS["gate-link"][1],y1=PATHS["gate-link"][3])
    boundary_obstacles = [dict(id=item["id"], rect=(min(p[0] for p in item["pts"])/1000,
                                                   min(p[1] for p in item["pts"])/1000,
                                                   max(p[0] for p in item["pts"])/1000,
                                                   max(p[1] for p in item["pts"])/1000))
                          for item in E.spec()["elements"]
                          if item["id"].startswith("fence-") or item["id"] == "yard-wall-ne"]
    plan = dict(paths=PATHS,gate_route=gate_route,top_troughs=troughs,top_benches=benches,trees=trees,beds=beds,sun_hours=exposure,objects=objects,plants=plants,swing=swing,accent_beds={"west-accent":shade["accent_bed"]},
                boundary_obstacles=boundary_obstacles,
                east_rect=EAST,east_center=EAST_CENTER,tree_pit=dict(center=tree_center,diameter_m=radius*2,status="ASSUMED"))
    from .garden_render_review import normal
    for item in meshes:
        if item["material"] == "stepping-stone":
            item["face_materials"] = ["stone-substrate" if normal(face)[2]<-.7 else item["material"] for face in item["faces"]]
    plan["conflicts"] = candidate_violations(meshes,props,plan,lay)
    notes += ["UNRESOLVED garden guard: %s: %s" % f for f in plan["conflicts"]]
    return meshes,props,notes,plan


def walking_routes(meshes):
    """Route rectangles and actual ground heights, including every built stone."""
    routes = dict(PATHS)
    ground = {name: (TOP_SURFACE if name in ("study", "gate-link") else GROUND) for name in routes}
    for stone in meshes:
        if stone.get("part_kind") == "stepping-stone":
            routes[stone["id"]] = _mesh_rect(stone)
            ground[stone["id"]] = min(p[2] for face in stone["faces"] for p in face)
    return routes, ground


# Client street-based NORTH is the legacy west court. True north is solar only.
NORTH_COURT = (-.373, -29.916, 3.617, -23.591)
NORTH_BALCONY_EDGE = -28.671
SHADE_ZONE = 'north garden (deep shade)'


def north_garden_violations(meshes, props, objects=(), *, court=NORTH_COURT,
                            ground=GROUND, balcony_edge=NORTH_BALCONY_EDGE, cover=None):
    """Spatial content policy, independent of item identifiers and solar axes.

    court is the client-named court rectangle in metres; ground is its soil
    elevation, balcony_edge its covered end in model y. Optional cover is
    the actual overhead architectural union in the plot plane.
    """
    from shapely.geometry import box
    out=[]
    allowed_species={name for name,row in _plant_data().items() if SHADE_ZONE in row['zones']['value']}
    def occupies(item):
        if item.get('zone')=='top':return False
        if 'faces' in item:
            if min(q[2] for f in item['faces'] for q in f)>ground+2.5:return False
        elif item.get('position',[0,0,ground])[2]>ground+2.5:return False
        return _rect_overlap_area(_rect(item),court)>1e-6
    for item in list(props)+list(objects):
        if not occupies(item):continue
        if item.get('asset')=='sf_egg_chair' and 'client to confirm' in item.get('label','').lower():
            r=_rect(item);envelope=(r[0]-.25,r[1]-.25,r[2]+.25,r[3]+.25)
            if envelope[1]<balcony_edge or cover is not None and box(*envelope).intersection(cover).area>1e-6:
                out.append((item['id'],'north garden swing must be wholly open to sky'))
        else:out.append((item['id'],'north garden forbids containers, table and seating except a flagged open-sky swing'))
    allowed={'finish-layer','stepping-stone','soil-bed','bed-edge','feature-stone','trellis','climber','climber-branch','plant-clump'}
    for item in meshes:
        if not occupies(item):continue
        kind=item.get('part_kind');points=[q for f in item['faces'] for q in f]
        if kind not in allowed:
            out.append((item['id'],'north garden forbids raised container or non-landscape content'))
        if kind=='soil-bed' and abs(max(q[2] for q in points)-ground)>1e-6:
            out.append((item['id'],'north garden soil surface must be at court ground level'))
        if kind=='bed-edge' and (min(q[2] for q in points)<ground-1e-6 or max(q[2] for q in points)>ground+.02+1e-6):
            out.append((item['id'],'north garden edging must be slim at ground level'))
        if item.get('material')=='artificial-grass':
            out.append((item['id'],'north garden requires gravel mulch and paths'))
        if 'species' in item:
            if item['species'] not in allowed_species:
                out.append((item['id'],'north garden requires its recorded shade palette'))
            if kind=='plant-clump':
                if abs(item.get('root_z_m',float('inf'))-ground)>1e-6:
                    out.append((item['id'],'north garden roots must meet ground-level soil'))
                if min(q[1] for q in points)<balcony_edge and item['species']!='Aspidistra elatior':
                    out.append((item['id'],'only Aspidistra allowed under the GF balcony'))
            if item['species']=='Rhapis excelsa':
                x,y=item['center'];distances=[x-(court[0]+E.FENCE_T/1000),court[2]-x,y-court[1],court[3]-y]
                distances += [hypot(max(r[0]-x,0,x-r[2]),max(r[1]-y,0,y-r[3])) for r in PATHS.values() if _rect_overlap_area(r,court)>1e-6]
                if min(distances)<1.-1e-6:out.append((item['id'],'Rhapis centre needs >=1.0 m from walls/paths; ASSUMED root barrier'))
    return out


def candidate_violations(meshes, props, plan, lay):
    """Existing checks plus identity, dimensions, east contents and real wall limits."""
    rooms = garden_level_rooms(lay)
    plants,objects = plan["plants"],plan["objects"]
    routes, ground = walking_routes(meshes)
    from .garden_render_review import plant_form_findings
    swings = [p for p in props if p["asset"] == "sf_egg_chair"]
    from .render_support import blocked_openings
    return ([(mid,"door passage "+why) for mid,why in blocked_openings(dict(meshes=meshes),lay)]+north_garden_violations(meshes,props,objects)+extent_violations(props,rooms)+object_extent_violations(objects,rooms)+
            [f for swing in swings for f in swing_violations(swing,props+objects+plants+plan.get("boundary_obstacles", [])+[dict(id="bed-"+name,rect=rect) for name,rect in plan["beds"].items()])]+
            [(pid,"door route "+route) for pid,route in route_violations(props+objects+[p for p in plants if "faces" in p], routes, ground)]+
            [(a,"plant spacing to %s: %.3f < %.3f m"%(b,got,need)) for a,b,got,need in spacing_violations(plants)]+
            [(bed,"only %d/3 primary layers: %s"%(len(have),have)) for bed,have in layer_violations(plants,plan["beds"])]+
            [(species,"%s/%s drift is %d, need 3-5"%(bed,layer,n)) for bed,layer,species,n in drift_violations(plants)]+
            sunlight_violations(plants)+standin_violations(props)+bench_violations(props)+species_violations(meshes+props)+
            dimension_violations(meshes+props)+[("plant-form",f) for f in plant_form_findings(meshes)]+east_content_violations(meshes,props,objects)+
            canopy_violations(props)+canopy_violations(props,mature=True)+
            top_garden_violations(meshes,props,plan,spec_surface=TOP_SURFACE))


def build(spec, lay=None):
    """Scene export fails closed on all unresolved candidate conflicts."""
    meshes,props,notes,plan = review_candidate(spec,lay)
    if plan["conflicts"]:
        raise ValueError("landscape guard: "+"; ".join("%s: %s"%f for f in plan["conflicts"]))
    return meshes,props,notes,plan


def north_garden_scene_violations(scene):
    """Apply the court policy to authoritative physical contents and cover."""
    from .garden_render_review import overhead_cover
    return north_garden_violations(
        [m for m in scene['meshes'] if m.get('group') in ('ground','furniture','dressing')],
        scene.get('props',[]),cover=overhead_cover(scene,GROUND))


def reveal_ground_soil(shell_meshes, soil_meshes):
    """Cut competing floor finish faces at authored soil boundaries.

    This constructs render finishes from the measured shell; it never edits
    an extract. Soil elevation is fixed. Side/underside geometry and all
    architectural datums stay intact; the soil face supplies the removed cap.
    """
    from shapely.geometry import Polygon
    from shapely.ops import triangulate
    from .garden_render_review import normal
    beds=[(Polygon([q[:2] for q in m['faces'][0]]),m['faces'][0][0][2]) for m in soil_meshes if m.get('part_kind')=='soil-bed']
    for m in shell_meshes:
        if m.get('group') not in ('shell','ground','context'):continue
        slots=m.get('face_materials',[m['material']]*len(m['faces']))
        faces=[];materials=[];changed=False
        for face,material in zip(m['faces'],slots):
            if normal(face)[2]<.999 or max(q[2] for q in face)-min(q[2] for q in face)>1e-6:
                faces.append(face);materials.append(material);continue
            z=face[0][2];polygon=Polygon([q[:2] for q in face]);remaining=polygon
            for bed,soil_z in beds:
                if abs(z-soil_z)<1e-6:remaining=remaining.difference(bed)
            if abs(remaining.area-polygon.area)<1e-9:
                faces.append(face);materials.append(material);continue
            changed=True
            for triangle in triangulate(remaining):
                if remaining.covers(triangle):
                    faces.append([[x,y,z] for x,y in list(triangle.exterior.coords)[:-1]]);materials.append(material)
        if changed:
            m['faces']=faces;m['face_materials']=materials
            m['label']=m.get('label','')+'; ground finish cut back at authored soil-bed boundaries'
