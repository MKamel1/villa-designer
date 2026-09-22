"""Extract JSON -> Blender scene -> Cycles render.

This is the bridge that lets Revit on Windows drive a GPU on Linux
without either knowing about the other. Revit's job ends at producing the
extract; this consumes it. Nothing binary crosses the gap -- the extract
is text, already git-synced (ADR-0002, ADR-0003).

Runs INSIDE Blender's own bundled Python, so it must not import anything
from `archpipe`: that package lives in a different interpreter. It is
deliberately standalone.

    blender -b -P build_scene.py -- --extract model.json --out render.png

Geometry is built procedurally rather than imported from FBX/glTF. That
keeps one source of truth and avoids a manual export step, at the cost of
representing families as proxies until real content exists.

UNITS: the extract is millimetres; Blender is metres. That conversion
happens in exactly one place, `m()`. This is the same class of bug as
Revit's decimal feet -- it does not raise, it silently produces a model
1000x wrong.
"""
import json
import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector

MM_TO_M = 0.001          # the single units boundary


def m(mm):
    """Millimetres -> metres. The only place this conversion happens."""
    return float(mm) * MM_TO_M


# ---------------------------------------------------------------------------
# scene setup
# ---------------------------------------------------------------------------
def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.lights,
                  bpy.data.cameras):
        for item in list(block):
            if item.users == 0:
                block.remove(item)


def material(name, rgba, roughness=0.6, emission=None):
    """A simple principled material, reused by name."""
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = rgba
        bsdf.inputs["Roughness"].default_value = roughness
        if emission is not None and "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = rgba
            bsdf.inputs["Emission Strength"].default_value = emission
    return mat


def mesh_from_polygon(name, points_m, z_m, height_m, mat=None):
    """Build a prism: a flat polygon at z, extruded up by `height_m`."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    verts = [bm.verts.new((p[0], p[1], z_m)) for p in points_m]
    bm.verts.ensure_lookup_table()
    try:
        face = bm.faces.new(verts)
    except ValueError:
        bm.free()
        bpy.data.objects.remove(obj)
        return None                      # degenerate / duplicate points
    if height_m:
        res = bmesh.ops.extrude_face_region(bm, geom=[face])
        moved = [v for v in res["geom"] if isinstance(v, bmesh.types.BMVert)]
        bmesh.ops.translate(bm, vec=Vector((0, 0, height_m)), verts=moved)
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()

    if mat:
        obj.data.materials.append(mat)
    return obj


# ---------------------------------------------------------------------------
# model -> geometry
# ---------------------------------------------------------------------------
def wall_footprint(wall):
    """The four corners of a wall's plan footprint, in metres.

    Mirrors the centreline-plus-thickness convention used by the DXF
    renderer, so the two representations agree.
    """
    x1, y1 = m(wall["start"][0]), m(wall["start"][1])
    x2, y2 = m(wall["end"][0]), m(wall["end"][1])
    t = m(wall.get("thickness") or 100.0)
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length < 1e-9:
        return None
    nx, ny = -dy / length, dx / length          # left-hand normal
    h = t / 2.0
    return [
        (x1 + nx * h, y1 + ny * h),
        (x2 + nx * h, y2 + ny * h),
        (x2 - nx * h, y2 - ny * h),
        (x1 - nx * h, y1 - ny * h),
    ]


def level_elevation(data, level_id):
    for lv in data.get("levels", []):
        if lv["id"] == level_id:
            return m(lv.get("elevation") or 0.0)
    return 0.0


def build_walls(data, mat):
    made = []
    default_h = 2700.0
    for w in data.get("walls", []):
        corners = wall_footprint(w)
        if not corners:
            continue
        z = level_elevation(data, w.get("level"))
        h = m(w.get("height") or default_h)
        obj = mesh_from_polygon("wall_%s" % w["id"][:8], corners, z, h, mat)
        if obj:
            made.append((obj, w))
    return made


def build_floors(data, mat):
    made = []
    for r in data.get("rooms", []):
        pts = [(m(p[0]), m(p[1])) for p in r.get("boundary", [])]
        if len(pts) < 3:
            continue
        z = level_elevation(data, r.get("level"))
        obj = mesh_from_polygon("floor_%s" % (r.get("name") or r["id"][:8]),
                                pts, z, 0.0, mat)
        if obj:
            made.append(obj)
    return made


def cut_openings(data, walls_made):
    """Subtract each opening from its host wall with a boolean modifier.

    An opening is a real hole, not a rectangle painted on the surface --
    otherwise daylight would not pass through it and every lighting study
    built on this scene would be wrong.
    """
    by_id = {w["id"]: (obj, w) for obj, w in walls_made}
    cut = 0
    for o in data.get("openings", []):
        host = by_id.get(o.get("host"))
        if not host or o.get("at") is None:
            continue
        obj, w = host
        width = m(o.get("width") or 0)
        height = m(o.get("height") or 0)
        if width <= 0 or height <= 0:
            continue

        x1, y1 = m(w["start"][0]), m(w["start"][1])
        x2, y2 = m(w["end"][0]), m(w["end"][1])
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        if length < 1e-9:
            continue
        ux, uy = dx / length, dy / length
        at = m(o["at"])
        sill = m(o.get("sill") or 0)
        z = level_elevation(data, w.get("level"))
        t = m(w.get("thickness") or 100.0)

        cx, cy = x1 + ux * at, y1 + uy * at
        cz = z + sill + height / 2.0

        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, cz))
        cutter = bpy.context.active_object
        cutter.name = "cut_%s" % o["id"][:8]
        # Slightly over-deep so the boolean breaks cleanly through both faces.
        cutter.scale = (width, t * 2.0, height)
        cutter.rotation_euler[2] = math.atan2(uy, ux)

        mod = obj.modifiers.new(name="cut_%s" % o["id"][:8], type="BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.object = cutter
        cutter.hide_render = True
        cutter.hide_viewport = True
        cut += 1
    return cut


def build_furniture(data, mat):
    """Proxy boxes until a real family library exists.

    Deliberately crude and deliberately obvious: a box should never be
    mistaken for a design proposal.
    """
    made = []
    for f in data.get("furniture", []) + data.get("casework", []):
        at = f.get("at")
        if not at:
            continue
        size = f.get("size") or [600, 600]
        h = m(f.get("height") or 750)
        bpy.ops.mesh.primitive_cube_add(size=1.0,
                                        location=(m(at[0]), m(at[1]), h / 2))
        obj = bpy.context.active_object
        obj.name = "furn_%s" % (f.get("type_name") or f["id"][:8])
        obj.scale = (m(size[0]), m(size[1]), h)
        obj.rotation_euler[2] = math.radians(f.get("rotation") or 0.0)
        if mat:
            obj.data.materials.append(mat)
        made.append(obj)
    return made


def build_lights(data):
    """Fixtures from the extract; a fallback only if there are none.

    The fallback is flagged in the log rather than silent, because a
    render lit by an invented lamp says nothing about the real scheme.
    """
    made = []
    for fx in data.get("lighting", []):
        at = fx.get("at")
        if not at:
            continue
        light = bpy.data.lights.new(name="lamp_%s" % fx["id"][:8], type="POINT")
        light.energy = float(fx.get("watts") or 60) * 10.0
        obj = bpy.data.objects.new(light.name, light)
        obj.location = (m(at[0]), m(at[1]), m(fx.get("mounting_height") or 2400))
        bpy.context.collection.objects.link(obj)
        made.append(obj)
    return made


# ---------------------------------------------------------------------------
def bounds(data):
    xs, ys = [], []
    for w in data.get("walls", []):
        for p in (w["start"], w["end"]):
            xs.append(m(p[0])); ys.append(m(p[1]))
    for r in data.get("rooms", []):
        for p in r.get("boundary", []):
            xs.append(m(p[0])); ys.append(m(p[1]))
    if not xs:
        return (0, 0, 10, 10)
    return (min(xs), min(ys), max(xs), max(ys))


def model_height(data, default_mm=2700.0):
    hs = [m(w["height"]) for w in data.get("walls", []) if w.get("height")]
    return max(hs) if hs else m(default_mm)


def add_camera(data, lens_mm=28.0, margin=1.25):
    """Frame the whole model, rather than guessing a distance.

    The first version placed the camera at a fixed fraction of the plan
    span and ended up pressed against a wall face. Fitting to the
    bounding box means the framing is right whatever the model's size --
    a 4 m bedroom and a 20 m villa both land in shot.
    """
    x0, y0, x1, y1 = bounds(data)
    z1 = model_height(data)
    cx, cy, cz = (x0 + x1) / 2, (y0 + y1) / 2, z1 / 2

    cam_data = bpy.data.cameras.new("cam")
    cam_data.lens = lens_mm
    cam = bpy.data.objects.new("cam", cam_data)
    bpy.context.collection.objects.link(cam)

    # Distance that fits the bounding sphere in the horizontal field of
    # view. sensor_width defaults to 36 mm.
    radius = max(math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2 + z1 ** 2) / 2, 1.0)
    fov = 2.0 * math.atan(cam_data.sensor_width / (2.0 * lens_mm))
    dist = (radius / math.tan(fov / 2.0)) * margin

    # Three-quarter view from above: the standard architectural setup.
    az, elev = math.radians(225.0), math.radians(28.0)
    cam.location = (
        cx + dist * math.cos(elev) * math.cos(az),
        cy + dist * math.cos(elev) * math.sin(az),
        cz + dist * math.sin(elev),
    )
    direction = Vector((cx, cy, cz)) - Vector(cam.location)
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    return cam


def add_world(strength=1.0):
    """A sky background, so surfaces facing away from the sun are not black.

    Without ambient light a render reads as a lighting failure when it is
    only a missing world.
    """
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.55, 0.65, 0.80, 1.0)
        bg.inputs["Strength"].default_value = strength
    return world


def configure_render(samples, resolution, use_gpu=True):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.render.resolution_x, scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"

    if not use_gpu:
        scene.cycles.device = "CPU"
        return "CPU"

    prefs = bpy.context.preferences.addons["cycles"].preferences
    chosen = None
    for backend in ("OPTIX", "CUDA"):          # OptiX first: RT cores
        try:
            prefs.compute_device_type = backend
        except TypeError:
            continue
        prefs.get_devices()
        gpus = [d for d in prefs.devices if d.type == backend]
        if gpus:
            for d in prefs.devices:
                d.use = (d.type == backend)
            chosen = "%s (%s)" % (backend, ", ".join(g.name for g in gpus))
            break
    scene.cycles.device = "GPU" if chosen else "CPU"
    return chosen or "CPU (no GPU backend found)"


def parse_args(argv):
    args = argv[argv.index("--") + 1:] if "--" in argv else []
    out = {"extract": None, "out": "render.png", "samples": 64,
           "res": (960, 540), "gpu": True}
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--extract":
            i += 1; out["extract"] = args[i]
        elif a == "--out":
            i += 1; out["out"] = args[i]
        elif a == "--samples":
            i += 1; out["samples"] = int(args[i])
        elif a == "--res":
            i += 1; w, h = args[i].split("x"); out["res"] = (int(w), int(h))
        elif a == "--cpu":
            out["gpu"] = False
        i += 1
    return out


def main():
    opt = parse_args(sys.argv)
    if not opt["extract"] or not os.path.isfile(opt["extract"]):
        print("SCENE ERROR: --extract <model.json> is required")
        sys.exit(2)

    with open(opt["extract"]) as fh:
        data = json.load(fh)

    units = data.get("units")
    if units != "mm":
        print("SCENE ERROR: extract units are %r, expected 'mm'" % units)
        sys.exit(2)

    clear_scene()

    wall_mat = material("wall", (0.86, 0.85, 0.82, 1.0), roughness=0.75)
    floor_mat = material("floor", (0.45, 0.32, 0.20, 1.0), roughness=0.45)
    furn_mat = material("furniture_proxy", (0.55, 0.57, 0.60, 1.0))

    walls = build_walls(data, wall_mat)
    floors = build_floors(data, floor_mat)
    holes = cut_openings(data, walls)
    furn = build_furniture(data, furn_mat)
    lights = build_lights(data)

    if not lights:
        # No fixtures in the extract. Add sun so the geometry is visible,
        # and say so -- an invented lamp must never be read as the scheme.
        sun_data = bpy.data.lights.new("fallback_sun", type="SUN")
        sun_data.energy = 3.0
        sun = bpy.data.objects.new("fallback_sun", sun_data)
        sun.rotation_euler = (math.radians(50), 0, math.radians(35))
        bpy.context.collection.objects.link(sun)
        print("SCENE NOTE: no light fixtures in the extract -- added a "
              "fallback sun. This render shows GEOMETRY, not a lighting "
              "scheme.")

    add_world()
    add_camera(data)
    device = configure_render(opt["samples"], opt["res"], opt["gpu"])

    print("SCENE walls=%d floors=%d openings_cut=%d furniture=%d lights=%d"
          % (len(walls), len(floors), holes, len(furn), len(lights)))
    print("SCENE device=%s samples=%d res=%dx%d"
          % (device, opt["samples"], opt["res"][0], opt["res"][1]))

    bpy.context.scene.render.filepath = os.path.abspath(opt["out"])
    bpy.ops.render.render(write_still=True)
    print("SCENE wrote %s" % os.path.abspath(opt["out"]))


if __name__ == "__main__":
    main()
