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


# Room surface reflectances. These are not decoration: in an interior most
# of the light reaching the eye has bounced at least once, so an albedo
# that is too high inflates every subsequent bounce and the whole room
# renders brighter than it will ever be. The values are the ordinary
# design figures for a decorated interior, the same ones
# `archpipe.lighting.Surfaces` uses for its inter-reflection estimate, so
# the render and the calculation describe the same room.
#
#   ceiling  0.80   white matt emulsion
#   walls    0.60   light mid-tone emulsion
#   floor    0.25   mid timber
#
# A material carried in the extract should override these; until Revit
# materials are extracted, these are the stated assumption rather than a
# hidden one.
REFLECTANCE = {"ceiling": 0.80, "wall": 0.60, "floor": 0.25,
               "furniture": 0.35}


def surface(name, reflectance, tint=(1.0, 1.0, 1.0), roughness=0.7):
    """A diffuse material whose PHOTOMETRIC reflectance is exactly as asked.

    Cycles treats base colour as per-channel reflectance, so a tinted
    surface's luminous reflectance is the Rec. 709 luminance of its RGB,
    not the average and not the largest channel. Scaling the tint to hit
    the target luminance means "a 0.60 wall" is 0.60 whether it is warm
    white or pale grey -- otherwise choosing a colour would quietly change
    the lighting result.
    """
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    y = 0.2126 * tint[0] + 0.7152 * tint[1] + 0.0722 * tint[2]
    k = (reflectance / y) if y > 0 else reflectance
    rgb = [min(1.0, c * k) for c in tint]
    if max(c * k for c in tint) > 1.0:
        print("SCENE NOTE material %r: tint %s clipped at reflectance %.2f; "
              "the rendered surface is slightly darker than asked."
              % (name, tint, reflectance))
    return material(name, (rgb[0], rgb[1], rgb[2], 1.0), roughness=roughness)


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


def build_ceilings(data, mat, default_height=2700.0):
    """A slab over each room, at the top of its walls.

    Not cosmetic. A room without a ceiling loses every ray that leaves a
    fitting upward or sideways-and-up, so the inter-reflected component --
    most of the light at the darkest point in a real room -- simply does
    not exist. Measured on the mock bedroom: without a ceiling, adding 16
    bounces raised average illuminance by 9.6 lx; the same room closed adds
    far more, and only the second figure describes a room anyone could
    stand in.

    Its reflectance matters more than any other surface's, because a
    downlight scheme sends most of its first bounce to the floor and the
    ceiling is what returns light to the upper half of the room.
    """
    made = []
    for r in data.get("rooms", []):
        pts = [(m(p[0]), m(p[1])) for p in r.get("boundary", [])]
        if len(pts) < 3:
            continue
        z = level_elevation(data, r.get("level"))
        h = m(r.get("ceiling_height") or _room_wall_height(data, r)
              or default_height)
        obj = mesh_from_polygon(
            "ceiling_%s" % (r.get("name") or r["id"][:8]), pts, z + h, 0.0, mat)
        if obj:
            made.append(obj)
    return made


def _room_wall_height(data, room):
    """Height of the walls on this room's level, if they agree."""
    heights = {w.get("height") for w in data.get("walls", [])
               if w.get("level") == room.get("level") and w.get("height")}
    return heights.pop() if len(heights) == 1 else None


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


# Blender light power that makes an IES-profiled point light render at the
# luminaire's REAL candela values, so rendered illuminance is numerically
# lux. Measured, not taken from a forum post -- see
# `calibrate_photometry.py` and ADR-0010.
#
# Blender's IES node returns the file's RAW candela divided by a constant;
# it does NOT normalise by flux. Proved with three synthetic probes:
# halving the candela halved the output exactly, while moving the same
# candela from a full sphere to a hemisphere -- halving the flux --
# changed nothing at all. Because the constant is universal, so is this
# power, whatever the fitting's distribution.
#
# Verified against `archpipe.lighting` (itself checked against hand
# calculation) at nine radial offsets: agreement to +/-0.02% from 2.9 to
# 51 degrees off nadir. Two exceptions, both understood and both small:
# exactly at nadir it reads 0.9% low, where Blender's IES lookup
# degenerates because azimuth is undefined at the pole; and in a beam's
# far tail the relative error grows while the absolute error stays under
# 0.1 lx.
IES_POINT_POWER = 162.624

# Without a photometric profile there is no honest brightness to use, so
# the scene falls back to treating the fitting as an isotropic source of
# its stated lumens. E = lumens / (4*pi*d^2) then holds exactly, which the
# same calibration confirmed to 0.02%. It is a real luminaire model, just
# a crude one, and `build_lights` says so in the log.
DEFAULT_LUMENS = 800.0


def build_lights(data):
    """Fixtures from the extract; a fallback only if there are none.

    The fallback is flagged in the log rather than silent, because a
    render lit by an invented lamp says nothing about the real scheme.

    A fixture carrying an `ies` path gets its real measured distribution.
    That is the whole point of the exercise: the shape of the beam, the
    scallop on the wall and the pool on the floor are properties of the
    fitting, and a bare point light has none of them.
    """
    made = []
    with_ies = 0
    for fx in data.get("lighting", []):
        at = fx.get("at")
        if not at:
            continue
        light = bpy.data.lights.new(name="lamp_%s" % fx["id"][:8], type="POINT")

        # A real fitting has a luminous opening, and its size is what makes
        # shadow edges soft. 0 would give razor shadows no room has.
        light.shadow_soft_size = max(
            0.0, float(fx.get("luminous_size_mm") or 60.0) * 0.5 * MM_TO_M)

        ies_path = fx.get("ies")
        if ies_path and os.path.isfile(ies_path):
            light.energy = IES_POINT_POWER * float(fx.get("output") or 1.0)
            light.use_nodes = True
            nt = light.node_tree
            node = nt.nodes.new("ShaderNodeTexIES")
            node.mode = "EXTERNAL"
            node.filepath = ies_path
            node.inputs["Strength"].default_value = 1.0
            nt.links.new(node.outputs["Fac"],
                         nt.nodes["Emission"].inputs["Strength"])
            with_ies += 1
        else:
            lumens = float(fx.get("lumens") or DEFAULT_LUMENS)
            light.energy = lumens * float(fx.get("output") or 1.0)

        kelvin = fx.get("kelvin")
        if kelvin:
            light.color = kelvin_to_rgb(float(kelvin))

        obj = bpy.data.objects.new(light.name, light)
        obj.location = (m(at[0]), m(at[1]), m(fx.get("mounting_height") or 2400))
        bpy.context.collection.objects.link(obj)
        made.append(obj)

    if made:
        print("SCENE LIGHTING %d fixtures, %d with measured IES photometry"
              % (len(made), with_ies))
        if with_ies < len(made):
            print("SCENE NOTE %d fixture(s) have no IES profile and are "
                  "rendered as isotropic sources of their stated lumens. "
                  "Brightness is right; beam shape is not."
                  % (len(made) - with_ies))
    return made


def kelvin_to_rgb(kelvin):
    """Approximate blackbody colour, normalised so luminance is unchanged.

    Colour temperature must not become a brightness control. Tinting a
    light without renormalising would make a 2700 K lamp render dimmer
    than a 4000 K one of identical output, which is a lighting error
    dressed up as a colour choice.

    Planckian approximation after Tanner Helland's widely-used fit;
    adequate for 1000-40000 K and well inside the tolerance of anything
    we assert about a scheme.
    """
    t = max(1000.0, min(40000.0, float(kelvin))) / 100.0
    if t <= 66:
        r = 255.0
        g = 99.4708025861 * math.log(t) - 161.1195681661
        b = 0.0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307
    else:
        r = 329.698727446 * ((t - 60) ** -0.1332047592)
        g = 288.1221695283 * ((t - 60) ** -0.0755148492)
        b = 255.0
    rgb = [max(0.0, min(255.0, v)) / 255.0 for v in (r, g, b)]
    # Rec. 709 luminance, so the tint changes hue and not output.
    y = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
    return tuple(v / y for v in rgb) if y > 0 else (1.0, 1.0, 1.0)


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


def add_interior_camera(data, lens_mm=20.0, eye_mm=1600.0, inset=0.35):
    """Stand inside the room and look across it.

    The exterior three-quarter view in `add_camera` frames a model; it
    cannot show an interior once the room has a ceiling, because the
    camera is outside the box. A lighting scheme is judged from inside it,
    at eye height, which is also where the client will stand.

    A wide lens is deliberate: a real room at 28 mm shows a sliver. 20 mm
    is about what an interior photograph uses.
    """
    x0, y0, x1, y1 = bounds(data)
    z1 = model_height(data)
    # Stand back in one corner, inset so as not to clip through the wall.
    cam_data = bpy.data.cameras.new("cam_interior")
    cam_data.lens = lens_mm
    cam_data.clip_start = 0.05
    cam = bpy.data.objects.new("cam_interior", cam_data)
    bpy.context.collection.objects.link(cam)

    eye = m(eye_mm)
    cam.location = (x0 + (x1 - x0) * inset * 0.5,
                    y0 + (y1 - y0) * inset * 0.5,
                    min(eye, z1 * 0.85))
    target = Vector(((x0 + x1) / 2 + (x1 - x0) * 0.2,
                     (y0 + y1) / 2 + (y1 - y0) * 0.25,
                     min(m(1200.0), z1 * 0.5)))
    direction = target - Vector(cam.location)
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    return cam


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


# Mid-grey. A photographic reference card is 18% reflectance, and mapping
# it to 0.18 in the display image is what "correctly exposed" means.
MID_GREY = 0.18


def photometric_exposure(target_lux):
    """Exposure, in stops, that makes `target_lux` look correctly exposed.

    Once lights carry real photometry, scene values are LUX -- a lit room
    sits around 100-300, where Blender's display pipeline expects roughly
    0-1. Rendered with default exposure the image is pure white, which is
    what a camera at the wrong aperture would also produce. Nothing is
    wrong with the light transport; the camera is simply not set.

    A mid-grey card under `target_lux` has radiance E*rho/pi, and we want
    that to land on MID_GREY after a gain of 2**exposure:

        2**exposure = MID_GREY * pi / (target_lux * MID_GREY) = pi / target_lux

    so exposure = log2(pi / target_lux), about -6 stops at 200 lx.

    This changes only how the image is DISPLAYED. The measurement path
    (`--measure`) forces exposure 0 and the Standard transform, so nothing
    here can affect a lux figure.
    """
    return math.log2(math.pi / max(1.0, float(target_lux)))


def configure_render(samples, resolution, use_gpu=True, measure=False,
                     exposure=None, target_lux=200.0):
    """Cycles settings chosen for physical fidelity, not for a pretty frame.

    Three defaults actively bias light transport and all three are changed
    here. Each would make the render disagree with the calculation while
    still looking entirely plausible:

    * **Indirect clamping.** Cycles clamps indirect samples at 10.0 by
      default. It suppresses fireflies by throwing away energy, which is
      precisely the bounced light an interior depends on. Set to 0 (off);
      noise is dealt with by sampling, which costs time rather than
      accuracy.
    * **Bounce limits.** A room is lit by light that has bounced several
      times. The defaults are tuned for an average scene, so diffuse
      bounces are raised explicitly.
    * **View transform.** `measure=True` forces Standard and linear EXR, so
      the file holds scene-linear radiance rather than a tone-mapped
      display value. AgX or Filmic would roll the highlights off and every
      reading would come back low, plausibly.

    The viewing render keeps a filmic transform on purpose: it is the
    display response, the equivalent of a camera's, and it does not touch
    the light transport that produced the image.
    """
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.render.resolution_x, scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100

    # Energy-conserving transport.
    scene.cycles.sample_clamp_indirect = 0.0
    scene.cycles.sample_clamp_direct = 0.0
    scene.cycles.max_bounces = 32
    scene.cycles.diffuse_bounces = 16
    scene.cycles.glossy_bounces = 8
    scene.cycles.transmission_bounces = 16
    scene.cycles.transparent_max_bounces = 16

    if measure:
        scene.render.image_settings.file_format = "OPEN_EXR"
        scene.render.image_settings.color_depth = "32"
        scene.cycles.use_denoising = False   # a denoiser biases a reading
        scene.view_settings.view_transform = "Standard"
        scene.view_settings.look = "None"
        scene.view_settings.exposure = 0.0
        scene.view_settings.gamma = 1.0
    else:
        scene.render.image_settings.file_format = "PNG"
        scene.cycles.use_denoising = True
        for transform in ("AgX", "Filmic", "Standard"):
            try:
                scene.view_settings.view_transform = transform
                break
            except TypeError:
                continue
        scene.view_settings.exposure = (
            photometric_exposure(target_lux) if exposure is None
            else exposure)
        print("SCENE EXPOSURE %.2f stops (target %.0f lx)"
              % (scene.view_settings.exposure, target_lux))

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
           "res": (960, 540), "gpu": True, "measure": False,
           "exposure": None, "interior": False,
           "target_lux": 200.0}
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
        elif a == "--interior":
            # Stand inside the room. Required once a ceiling exists.
            out["interior"] = True
        elif a == "--measure":
            # Linear EXR, no tone curve, no denoiser: the image becomes a
            # measurement instead of a picture.
            out["measure"] = True
        elif a == "--exposure":
            i += 1; out["exposure"] = float(args[i])
        elif a == "--target-lux":
            i += 1; out["target_lux"] = float(args[i])
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

    # Reflectances stated, not guessed -- see REFLECTANCE above.
    wall_mat = surface("wall", REFLECTANCE["wall"],
                       tint=(1.00, 0.99, 0.95), roughness=0.75)
    floor_mat = surface("floor", REFLECTANCE["floor"],
                        tint=(1.00, 0.72, 0.45), roughness=0.45)
    furn_mat = surface("furniture_proxy", REFLECTANCE["furniture"],
                       tint=(0.92, 0.95, 1.00))
    ceiling_mat = surface("ceiling", REFLECTANCE["ceiling"],
                          tint=(1.0, 1.0, 1.0), roughness=0.85)

    walls = build_walls(data, wall_mat)
    floors = build_floors(data, floor_mat)
    ceilings = build_ceilings(data, ceiling_mat)
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
    (add_interior_camera(data) if opt["interior"] else add_camera(data))
    device = configure_render(opt["samples"], opt["res"], opt["gpu"],
                              measure=opt["measure"],
                              exposure=opt["exposure"],
                              target_lux=opt["target_lux"])

    print("SCENE walls=%d floors=%d openings_cut=%d furniture=%d lights=%d"
          % (len(walls), len(floors), holes, len(furn), len(lights)))
    print("SCENE device=%s samples=%d res=%dx%d"
          % (device, opt["samples"], opt["res"][0], opt["res"][1]))

    bpy.context.scene.render.filepath = os.path.abspath(opt["out"])
    bpy.ops.render.render(write_still=True)
    print("SCENE wrote %s" % os.path.abspath(opt["out"]))


if __name__ == "__main__":
    main()
