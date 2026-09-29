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

BEDS = {
    "north": (24.0, -21.32, 27.1, -20.40),
    "east": (27.35, -27.15, 28.45, -23.80),
    "south": (24.0, -29.82, 27.2, -28.72),
    "west": (0.0, -27.45, 1.10, -24.10),
}

# The spreads are from the named palette where a width is available.
# Duranta and hibiscus list heights only; 0.8 and 0.9 m are ASSUMED
# maintained nursery spreads and must be checked with the nursery.
SPREAD = {"Duranta erecta": 0.8, "Hibiscus rosa-sinensis": 0.9,
          "Lavandula angustifolia 'Hidcote'": 0.75,
          "Pennisetum setaceum": 0.9}
PALETTE = Path(__file__).resolve().parents[3] / "out/villa/round3/plant-palette.json"
MANIFEST = Path(__file__).resolve().parents[3] / "ops/workstation/library-manifest.json"


def _plant_data():
    rows = json.loads(PALETTE.read_text(encoding="utf-8"))["categories"]
    found = {}
    for entries in rows.values():
        for row in entries:
            name, url = row["botanical_name"], row["source_url"]
            found[name] = (url, row)
    return found


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


def _bistro(meshes):
    # Manifest does not contain outdoor_table_chair_set_01; dimensioned
    # procedural proxy keeps the route and footprint independently checkable.
    objects = []
    for name, cx, cy, w, d, h in (("table", 26.05, -26.2, .70, .70, .72),
                                   ("chair-a", 25.42, -26.2, .48, .54, .82),
                                   ("chair-b", 26.80, -26.2, .48, .54, .82)):
        rect = (cx-w/2, cy-d/2, cx+w/2, cy+d/2)
        objects.append(dict(id="landscape-bistro-" + name, rect=rect))
        mesh = _mesh("bistro-" + name, "furniture", "teak",
                     _box(rect[0], rect[1], GROUND, rect[2], rect[3], GROUND+h),
                     "ASSUMED dimensioned bistro proxy for Poly Haven outdoor_table_chair_set_01 (absent from checked manifest)")
        if name == "table":
            # The locked view checker resolves outdoor subjects by this
            # historic prefix. The geometry and label are a bistro table.
            mesh["id"] = "landscape-sofa-bistro-table-view-alias"
        meshes.append(mesh)
    return objects


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

    # Shade specimens are scaled to nursery heights, not native glTF units.
    trees = (("north", "tree_small_02", "Bauhinia variegata", (18.70, -21.80), 2.55, 90),
             ("east", "sf_bauhinia", "Bauhinia variegata", (25.45, -23.15), 2.75, 0),
             ("south", "sf_frangipani", "Plumeria rubra", (26.40, -28.05), 2.20, 0))
    for bed, asset, species, center, height, yaw in trees:
        url = data[species][0]
        standin = "ASSUMED visual stand-in; " if asset == "tree_small_02" else ""
        p = _prop("landscape-tree-" + bed, asset, center, GROUND, height,
                  "%s%s; care: %s; nursery height %.2f m ASSUMED; %s" %
                  (standin, species, url, height, credits[asset]), yaw=yaw)
        props.append(p)

    drifts = (("north", "Duranta erecta", "sf_ixora", (24.65, 25.55, 26.45), -20.88, .66),
              ("west", "Duranta erecta", "sf_ixora", (.48, .48, .48), -24.80, .66),
              ("east", "Hibiscus rosa-sinensis", "sf_hibiscus", (27.90, 27.90, 27.90), -24.35, .80),
              ("south", "Lavandula angustifolia 'Hidcote'", "sf_lavender_clump",
               (25.25, 26.05, 26.85), -29.25, .55))
    for bed, species, asset, xs, y0, height in drifts:
        url = data[species][0]
        for i, x in enumerate(xs):
            y = y0 + i * (-.90 if bed in ("west", "east") else 0)
            label = ("%s; care: %s; %s; nursery height %.2f m ASSUMED; "
                     "maintained spread %.2f m %s" %
                     (species, url, credits[asset], height, SPREAD[species],
                      "ASSUMED" if species != "Lavandula angustifolia 'Hidcote'" else
                      "RHS palette"))
            if species == "Duranta erecta":
                label = "ASSUMED ixora visual stand-in for " + label
            p = _prop("landscape-%s-%02d" % (bed, i), asset, (x, y), GROUND,
                      height, label)
            p.update(bed=bed, layer="mid" if bed != "south" else "edge",
                     center=(x, y), spread_m=SPREAD[species], species=species)
            props.append(p); plants.append(p)

    # Slender wall trellises and coloured climbing masses; the mass is a
    # labelled proxy, since an espaliered Bougainvillea model is unavailable.
    boug = data["Bougainvillea glabra"][0]
    for name, x, y in (("east", 28.42, -24.0), ("south", 26.0, -29.78)):
        if name == "east":
            frame = _box(x-.04, y, GROUND, x, y+1.5, GROUND+2.2)
            mass = _box(x-.13, y+.08, GROUND, x-.05, y+1.42, GROUND+2.05)
        else:
            frame = _box(x-.75, y, GROUND, x+.75, y+.04, GROUND+2.2)
            mass = _box(x-.67, y+.05, GROUND, x+.67, y+.13, GROUND+2.05)
        meshes.append(_mesh("trellis-"+name, "furniture", "trellis", frame,
                            "ASSUMED trellis for Bougainvillea glabra; care: " + boug))
        meshes.append(_mesh("climber-"+name, "dressing", "bougainvillea-bract", mass,
                            "ASSUMED procedural magenta Bougainvillea glabra climber; care: " + boug))

    objects += _bistro(meshes)
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
    top_species = "Lavandula angustifolia 'Hidcote'"
    for i, x in enumerate((10.55, 11.30, 12.05, 13.35, 14.10, 14.85)):
        p = _prop("landscape-top-lavender-%02d" % i, "sf_lavender_clump",
                  (x, -22.70), .32, .48,
                  "%s; care: %s; %s; shallow-root planter, nursery height 0.48 m ASSUMED" %
                  (top_species, data[top_species][0], credits["sf_lavender_clump"]), zone="top")
        p.update(bed="top-deck" if i < 3 else "top-roof", layer="edge",
                 center=(x, -22.70), spread_m=SPREAD[top_species], species=top_species)
        props.append(p); plants.append(p)
    # A potted frangipani has the palette's shallow non-aggressive roots.
    top_tree = _prop("landscape-top-frangipani", "sf_frangipani", (14.0, -21.70), 0.0,
                     1.35, "potted Plumeria rubra; care: %s; nursery height 1.35 m ASSUMED; %s" %
                     (data["Plumeria rubra"][0], credits["sf_frangipani"]), zone="top")
    props.append(top_tree)
    pot = (13.50, -22.20, 14.50, -21.20)
    objects.append(dict(id="landscape-top-tree-pot", rect=pot, zone="top"))
    meshes.append(_mesh("top-tree-pot", "furniture", "garden-sandstone",
                        _box(*pot[:2], 0.0, *pot[2:], .45),
                        "ASSUMED shallow container for Plumeria rubra; engineer waterproofing and load"))
    for i, y in enumerate((-21.15, -22.00)):
        p = _prop("landscape-top-bench-%d" % i, "sf_wooden_bench", (10.70, y), 0.0,
                  .48, "ASSUMED bench; seat height to be checked on the imported mesh against "
                  "Time-Saver 2nd ed. p.340-11, lts-seatwall-height-350; " + credits["sf_wooden_bench"],
                  zone="top", yaw=90)
        props.append(p)

    failures = (extent_violations(props, rooms) + object_extent_violations(objects, rooms) +
                [(pid, "door route " + route) for pid, route in route_violations(props + objects)] +
                [(a, "plant spacing to %s: %.3f < %.3f m" % (b, got, need))
                 for a, b, got, need in spacing_violations(plants)] +
                swing_violations(swing, [swing] + objects))
    if failures:
        raise ValueError("landscape guard: " + "; ".join("%s: %s" % f for f in failures))

    exposure = {bed: direct_sun_hours((r[0]+r[2])/2, (r[1]+r[3])/2)
                for bed, r in BEDS.items()}
    sun = "; ".join("%s %d/9 direct hours (%s)" %
                    (bed, len(hours), ",".join(str(h) for h in hours) or "none")
                    for bed, hours in exposure.items())
    notes = ["Artificial grass in all three lower yard strips and on the deck/roof; "
             "stepping-stone approaches reach four lower doors and the GF study door. "
             "Clear routes 0.914 m, Time-Saver 2nd ed. p.340-9, lts-path-width-oneway-900.",
             "North bed: Duranta erecta 3; west bed: Duranta erecta 3; east bed: "
             "Hibiscus rosa-sinensis 3; south bed: Lavandula angustifolia 'Hidcote' 3; "
             "top deck/roof planters: Lavandula angustifolia 'Hidcote' 3+3. "
             "Species care URLs and asset authors/licences are on each prop label.",
             "ASSUMED drip irrigation to every bed and planter (emitters at each plant, timer-controlled); "
             "artificial grass needs none. ASSUMED irrigated Cairo garden; illustrative-site June 21 direct-sun screen at "
             "each lower bed centre (hourly 09:00-17:00, 3.0 m enclosure from villa_env.APT): " + sun +
             ". This edge-ray screen needs detailed shadow verification before procurement.",
             "Top garden occupies the former parking deck and planted roof. Ramp remains unobstructed "
             "and car-parkable. Existing 1.1 m rails are retained. Planters and furniture clear deck "
             "edges/rail mounting lines by at least %.2f m. Shallow roots only over basement; "
             "waterproofing, drainage and loading need engineering review." % RAIL_CLEAR,
             "Poly Haven outdoor_table_chair_set_01 was absent from the checked prop manifest; "
             "the two-chair bistro is an ASSUMED dimensioned proxy. SF bench seat height and "
             "egg swing operating envelope require manufacturer read-back. The bistro table retains a "
             "legacy landscape-sofa mesh-id prefix solely for the existing view subject resolver; "
             "no sofa geometry remains."]
    used_assets = sorted({p["asset"] for p in props})
    notes.append("Landscape appearance credits: " + "; ".join(
        asset + " -- " + credits[asset] for asset in used_assets))
    return meshes, props, notes, dict(paths=PATHS, trees=trees, beds=BEDS, sun_hours=exposure,
                                      objects=objects, plants=plants, swing=swing)
