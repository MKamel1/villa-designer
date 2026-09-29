"""D1's assumed shaded Mediterranean garden, constrained to the modeled yard.

The south planting zone is the southern end of our east yard. The land below
the rear boundary belongs to the sister plot and is never dressed as ours.
All positions are metres in the same frame as the villa scene.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from math import cos, hypot, radians, sin
from pathlib import Path

from .. import solar, villa_env as E
from . import villa_furniture_detail as FD

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
    rotated = [(scale * (x * c - y * s), scale * (x * s + y * c)) for x, y in corners]
    px, py, pz = position
    xs = [px + rx for rx, _ in rotated]
    ys = [py + ry for _, ry in rotated]
    height = scale * (lz1 - lz0)
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


def extent_violations(props):
    """For every placed prop with known library bounds: (a) its full world box (trunk + canopy) must not enter our
    building's occupied volume -- may overhang paving, must not overhang the villa; (b) its footprint must stay
    inside our plot and our modeled yard, not the sister plot, the street or the neighbours. Returns a list of
    (prop id, reason) pairs; empty means every prop passes."""
    out = []
    for p in props:
        asset = p["asset"]
        if asset not in PROP_BOUNDS:
            continue
        x0, y0, z0, x1, y1, z1 = prop_world_box(asset, p["position"], p.get("rotation_deg", [0, 0, 0]),
                                                 p.get("scale", 1.0))
        if z1 > 0 and z0 < BUILDING_HEIGHT:           # the prop's own z-range overlaps our GF storey's (0..APT)
            for rect in BUILDING_RECTS:
                if _rect_overlap_area((x0, y0, x1, y1), rect) > 1e-6:
                    out.append((p["id"], "world box (%.2f,%.2f)-(%.2f,%.2f) enters the building footprint %s"
                                % (x0, y0, x1, y1, tuple(round(v, 3) for v in rect))))
                    break
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


# Door approaches are rectangles ending exactly on the garden threshold.
# The lounge garden door is the west wing; the other three open north/east.
PATHS = {
    "dining": (16.439, -23.591, 17.339, -21.35),
    "living-north": (20.107, -23.591, 21.007, -21.35),
    "living-east": (22.597, -26.581, 25.10, -25.681),
    "lounge-west": (1.00, -26.606, 3.617, -25.706),
}

# Mature height per tree, metres. Requested species is olive (Olea europaea); no cited figure for its mature
# height is held in knowledge/library.json (checked 2026-09-28), so these are ASSUMED, not sourced: a young/
# semi-mature landscaping specimen (the size actually sold and planted for immediate shade) is commonly
# 3.5-4.5 m; a full jacaranda/tree_small_02 CC0 mesh at its native height (19.3 m / 4.5 m) was never checked
# against either the plot or the building before this fix and produced the defect (canopies inside the parents'
# bedroom and the garden-living ceiling, D1 draft renders v01/v02/v05/v07/v17). Height drives an isotropic
# scale = target_h / native_h (never scaled non-uniformly, which would distort the canopy's own proportions);
# native_h comes from PROP_BOUNDS, the checked-in library-manifest.json bounds_m. Position and yaw (rotation
# about Z only) were then chosen, in that order, to clear archpipe.concept.villa_landscape.extent_violations
# (building footprint + plot/yard) while keeping the tree near its original door/terrace, per the client's shade
# preference (docs/LEARNINGS.md "Shade over sun"): the north strip beside the BAR facade is only 3.24 m deep, so
# a wide-canopy jacaranda cannot fit there at any usable height -- the narrower tree_small_02 stands in for it,
# yawed 90 deg so its own canopy's long axis (the asset is itself asymmetric, not our doing) points across the
# strip's width rather than into the facade or the front plot line.
TREES = (
    ("north-shade", "tree_small_02", 18.30, -21.80, 90, 3.8),
    ("east-shade", "jacaranda_tree", 25.00, -24.50, 90, 4.0),
    ("south-shade", "tree_small_02", 25.45, -28.35, 90, 4.0),
)


def _furniture(mid, parts, center, width, depth, height):
    out = []
    for k, (name, (vertices, triangles)) in enumerate(parts):
        faces = []
        for tri in triangles:
            face = [[center[0] + vertices[j][0] / 1000,
                     center[1] + vertices[j][1] / 1000,
                     GROUND + vertices[j][2] / 1000] for j in tri]
            for x, y, z in face:
                if not (center[0] - width / 2 - 0.001 <= x <= center[0] + width / 2 + 0.001 and
                        center[1] - depth / 2 - 0.001 <= y <= center[1] + depth / 2 + 0.001 and
                        GROUND - 0.001 <= z <= GROUND + height + 0.001):
                    raise ValueError(mid + ": outside checked outdoor furniture envelope")
            faces.append(face)
        mat = "outdoor-fabric" if name in ("seat", "back", "arm") else "teak"
        if name == "leg":
            mat = "teak"
        out.append(dict(id="landscape-" + mid + "-%02d" % k, group="furniture", material=mat,
                        label="ASSUMED outdoor teak and weatherproof-fabric lounge: " + mid,
                        faces=faces, keep_object=True, subdivide=1 if mat == "outdoor-fabric" else 0,
                        bevel_m=0.006))
    return out


def build(spec):
    """Return scene meshes, supported CC0 props, notes and checkable layout."""
    meshes, props = [], []
    doors = [d for d in spec["doors"] if d.get("garden")]
    if len(doors) != len(PATHS):
        raise ValueError("garden-door count changed; redraw all landscape approaches")
    for name, (x0, y0, x1, y1) in PATHS.items():
        if not all(inside_yard(x, y) for x in (x0, x1) for y in (y0, y1)):
            raise ValueError(name + " path leaves our yard")
        meshes.append(dict(id="landscape-path-" + name, group="ground", material="paving",
                           label="ASSUMED honed sandstone walking path to " + name + " garden door",
                           faces=_quad(x0, y0, x1, y1, GROUND + 0.004)))
        if x1 - x0 < y1 - y0:
            joint = _quad(x0, y0, x0 + 0.06, y1, GROUND + 0.007) + \
                    _quad(x1 - 0.06, y0, x1, y1, GROUND + 0.007)
        else:
            joint = _quad(x0, y0, x1, y0 + 0.06, GROUND + 0.007) + \
                    _quad(x0, y1 - 0.06, x1, y1, GROUND + 0.007)
        meshes.append(dict(id="landscape-pebble-joints-" + name, group="ground", material="garden-pebbles",
                           label="ASSUMED pebble-set edge to sandstone path", faces=joint))
    # Gravel and raised sandstone beds avoid all four walking routes.
    beds = (("north", (13.00, -22.65, 14.05, -20.80)),
            ("east", (26.95, -25.85, 28.15, -23.75)),
            ("south", (26.90, -29.25, 28.10, -27.25)),
            ("west", (0.20, -25.35, 0.85, -23.75)))
    for name, (x0, y0, x1, y1) in beds:
        if not all(inside_yard(x, y) for x in (x0, x1) for y in (y0, y1)):
            raise ValueError(name + " bed leaves our yard")
        meshes.append(dict(id="landscape-gravel-" + name, group="ground", material="garden-gravel",
                           label="ASSUMED gravel planting bed, " + name,
                           faces=_quad(x0, y0, x1, y1, GROUND + 0.006)))
        t = 0.08
        sides = (_box(x0, y0, GROUND, x0 + t, y1, GROUND + 0.45) +
                 _box(x1 - t, y0, GROUND, x1, y1, GROUND + 0.45) +
                 _box(x0 + t, y0, GROUND, x1 - t, y0 + t, GROUND + 0.45) +
                 _box(x0 + t, y1 - t, GROUND, x1 - t, y1, GROUND + 0.45))
        meshes.append(dict(id="landscape-planter-" + name, group="furniture", material="garden-sandstone",
                           label="ASSUMED raised sandstone planter, " + name, faces=sides, bevel_m=0.005))
        meshes.append(dict(id="landscape-planter-soil-" + name, group="ground", material="garden-gravel",
                           label="ASSUMED gravel mulch inside " + name + " planter",
                           faces=_quad(x0 + t, y0 + t, x1 - t, y1 - t, GROUND + 0.38)))
    tree_props = []
    for name, asset, x, y, yaw_deg, target_h in TREES:
        if not inside_yard(x, y) or facade_distance(x, y) < 1.5:
            raise ValueError(name + " tree violates plot or 1.5 m trunk setback")
        native_min, native_max = PROP_BOUNDS[asset]
        scale = target_h / (native_max[1] - native_min[1])
        tree_props.append(dict(id="landscape-tree-" + name, asset=asset,
                          position=[x, y, GROUND], rotation_deg=[0, 0, yaw_deg], scale=scale,
                          label="dressing: ASSUMED CC0 %s shade-tree stand-in for olive (Olea europaea); height "
                                "%.1f m ASSUMED (no cited mature-height figure held for the species), scale "
                                "derived from the asset's measured native height" % (asset, target_h)))
    bad = extent_violations(tree_props)
    if bad:
        raise ValueError("landscape tree(s) violate the building/plot extent guard: " + "; ".join(
            "%s: %s" % item for item in bad))
    props += tree_props
    # scale defaults to 1.0; four of these CC0 files are themselves multi-plant clusters (several complete
    # variants as separate glTF root nodes at different offsets -- library-manifest.json bounds_m records the
    # combined box, exactly what Blender's importer builds), so at scale 1.0 they are wider than the single small
    # clump their name/position implied and crossed the plot or yard line once the real bounds were checked
    # (extent_violations below; the fix is a smaller scale, not a moved point -- these dress a bed, not a tree).
    planting = (("searsia", "searsia_lucida", 13.25, -21.65, GROUND + 0.38, 0.7),
                ("grass-n", "grass_medium_01", 13.75, -22.2, GROUND + 0.38, 1.0),
                ("gazania", "flower_gazania", 13.1, -22.25, GROUND + 0.38, 1.0),
                ("periwinkle", "periwinkle_plant", 27.45, -24.15, GROUND + 0.38, 1.0),
                ("grass-e", "grass_medium_02", 27.6, -25.25, GROUND + 0.38, 0.5),
                ("rooibos", "wild_rooibos_bush", 27.45, -28.0, GROUND + 0.38, 0.45),
                ("shrub-a", "shrub_01", 27.48, -28.75, GROUND + 0.38, 1.0),
                ("shrub-b", "shrub_02", 27.5, -24.9, GROUND + 0.38, 0.18),
                ("shrub-c", "shrub_03", 0.5, -24.3, GROUND + 0.38, 1.0),
                ("shrub-d", "shrub_04", 0.5, -24.95, GROUND + 0.38, 1.0),
                ("boulder", "boulder_01", 26.7, -22.5, GROUND, 1.0),
                ("stones", "namaqualand_stones_01", 25.4, -29.0, GROUND, 1.0))
    planting_props = [dict(id="landscape-" + name, asset=asset, position=[x, y, z],
                          rotation_deg=[0, 0, 0], scale=scale,
                          label="dressing: ASSUMED CC0 " + asset + " garden planting")
                      for name, asset, x, y, z, scale in planting]
    bad = extent_violations(planting_props)
    if bad:
        raise ValueError("landscape planting violates the building/plot extent guard: " + "; ".join(
            "%s: %s" % item for item in bad))
    props += planting_props
    meshes += _furniture("sofa", FD._sofa(2100, 850, 800, 3, 125), (24.95, -27.65), 2.1, 0.85, 0.8)
    meshes += _furniture("chair-one", FD._sofa(800, 800, 800, 1, 110), (23.35, -28.65), 0.8, 0.8, 0.8)
    meshes += _furniture("chair-two", FD._sofa(800, 800, 800, 1, 110), (24.45, -28.65), 0.8, 0.8, 0.8)
    meshes += _furniture("table", FD._coffee_table(650, 650, 390), (25.55, -28.75), 0.65, 0.65, 0.39)
    # Solar position is calculated for the illustrative Cairo site, summer
    # solstice 14:00-17:00 local time (UTC+03). A tree canopy close to the
    # east door and another above the north approach give afternoon shade;
    # exact shadow coverage needs the workstation render and a real site.
    positions = [solar.sun_position(datetime(2026, 6, 21, h - 3, tzinfo=timezone.utc),
                                    E.LATITUDE, E.LONGITUDE) for h in (14, 15, 16, 17)]
    solar_note = ", ".join("%02d:00 altitude %.1f°, azimuth %.1f°" % (h, p.altitude, p.azimuth)
                           for h, p in zip((14, 15, 16, 17), positions))
    notes = ["ASSUMED shaded Mediterranean garden on our north strip and east/west wings, including a south zone "
             "within our east wing. Trees are >=1.5 m from the built facades; paths reach each garden door. "
             "The sister plot south of the rear boundary remains untouched.",
             "Summer solstice afternoon at placeholder Cairo site (local UTC+03): " + solar_note +
             ". Tree canopies are placed over north/east garden approaches and the east terrace; exact shade "
             "on each door and hour needs a render with actual asset dimensions and the real site.",
             "ASSUMED drip irrigation to all raised planters and gravel beds; pipework is not rendered. "
             "Olive, citrus and climber CC0 models are unavailable, so jacaranda/tree_small_02 are labelled "
             "visual shade-tree stand-ins; no bougainvillea or jasmine mesh is shown."]
    return meshes, props, notes, dict(paths=PATHS, trees=TREES, beds=beds)
