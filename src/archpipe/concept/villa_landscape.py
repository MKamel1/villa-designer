"""D1's assumed shaded Mediterranean garden, constrained to the modeled yard.

The south planting zone is the southern end of our east yard. The land below
the rear boundary belongs to the sister plot and is never dressed as ours.
All positions are metres in the same frame as the villa scene.
"""
from __future__ import annotations

from datetime import datetime, timezone
from math import hypot

from .. import solar, villa_env as E
from . import villa_furniture_detail as FD

GROUND = -3.0
PLOT = tuple(v / 1000 for v in E.plot())
YARD = tuple((x / 1000, y / 1000) for x, y in E.yard())


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

TREES = (
    # The tree is a CC0 jacaranda visual stand-in for the requested olive/citrus shade.
    ("north-shade", "jacaranda_tree", 18.30, -21.55, 1.0),
    ("east-shade", "jacaranda_tree", 24.50, -23.95, 0.85),
    ("south-shade", "tree_small_02", 25.45, -28.35, 1.0),
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
    for name, asset, x, y, scale in TREES:
        if not inside_yard(x, y) or facade_distance(x, y) < 1.5:
            raise ValueError(name + " tree violates plot or 1.5 m trunk setback")
        props.append(dict(id="landscape-tree-" + name, asset=asset,
                          position=[x, y, GROUND], rotation_deg=[0, 0, 0], scale=scale,
                          label="dressing: ASSUMED CC0 " + asset + " shade-tree stand-in; olive/citrus model unavailable"))
    planting = (("searsia", "searsia_lucida", 13.25, -21.65, GROUND + 0.38),
                ("grass-n", "grass_medium_01", 13.75, -22.2, GROUND + 0.38),
                ("gazania", "flower_gazania", 13.1, -22.25, GROUND + 0.38),
                ("periwinkle", "periwinkle_plant", 27.45, -24.15, GROUND + 0.38),
                ("grass-e", "grass_medium_02", 27.6, -25.25, GROUND + 0.38),
                ("rooibos", "wild_rooibos_bush", 27.45, -28.0, GROUND + 0.38),
                ("shrub-a", "shrub_01", 27.48, -28.75, GROUND + 0.38),
                ("shrub-b", "shrub_02", 27.5, -24.9, GROUND + 0.38),
                ("shrub-c", "shrub_03", 0.5, -24.3, GROUND + 0.38),
                ("shrub-d", "shrub_04", 0.5, -24.95, GROUND + 0.38),
                ("boulder", "boulder_01", 26.7, -22.5, GROUND),
                ("stones", "namaqualand_stones_01", 25.4, -29.0, GROUND))
    for name, asset, x, y, z in planting:
        props.append(dict(id="landscape-" + name, asset=asset, position=[x, y, z],
                          rotation_deg=[0, 0, 0], scale=1.0,
                          label="dressing: ASSUMED CC0 " + asset + " garden planting"))
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
