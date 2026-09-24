"""Presentation-only realism: daylight, glass, finishes, camera, bedding, dressing.

Runs INSIDE Blender beside build_scene.py and presentation.py, imported the
same way (by file path), and like them imports only bpy/bmesh/mathutils.

Nothing here is used by --measure. The photometric path (ADR-0009/0010)
never sees architectural glass, the physical sky, the camera meter or any
dressing, so a presentation choice can never move a validated lux figure.
The recipe and its sources are in ADR-0013.
"""
import math
import os
import tempfile

import bmesh
import bpy
from mathutils import Vector

# MEASURED (calibrate_sky.py, Blender 4.5.14): Nishita at strength 1 gives
# 30.5 / 76.7 / 120.0 "lux" on an open horizontal plane at sun elevation
# 15 / 35 / 60 deg, in this project's calibrated units (1 W reads as 1 lm).
# Real clear-sky global horizontal illuminance at those elevations is about
# 25k / 60k / 100k lx: a constant x~800 (+/-5%). Nishita's SHAPE with sun
# height is right; only its scale is not in lux, so it is scaled by this.
NISHITA_LUX_SCALE = 800.0

# MEASURED: sun_rotation 0 puts the sun at +Y, 90 at +X, i.e. the Nishita
# rotation IS the compass azimuth (clockwise from north) when the model's
# +Y is true north (the extract's north_angle is 0).


def _lin(v):
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


# ---------------------------------------------------------------------------
# Glass
# ---------------------------------------------------------------------------
def architectural_glass():
    """Let sun and sky through thin window panes.

    Cycles treats a Principled glass slab as an occluder for shadow rays,
    so direct sun and sky through a window only arrive as refractive
    caustics -- almost never sampled. The standard archviz fix routes
    shadow and diffuse rays through a Transparent BSDF while camera and
    glossy rays still see the glass: a real 4-6 mm pane casts essentially
    no shadow, and the camera still sees its reflection and refraction.
    """
    done = []
    for mat in bpy.data.materials:
        if not str(mat.get("presentation_assumption", "")).startswith("clear glazing"):
            continue
        if mat.get("photoreal_glass"):
            continue
        nt = mat.node_tree
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        bsdf = nt.nodes.get("Principled BSDF")
        path = nt.nodes.new("ShaderNodeLightPath")
        add = nt.nodes.new("ShaderNodeMath")
        add.operation = "ADD"
        add.use_clamp = True
        nt.links.new(path.outputs["Is Shadow Ray"], add.inputs[0])
        nt.links.new(path.outputs["Is Diffuse Ray"], add.inputs[1])
        clear = nt.nodes.new("ShaderNodeBsdfTransparent")
        mix = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(add.outputs["Value"], mix.inputs["Fac"])
        nt.links.new(bsdf.outputs["BSDF"], mix.inputs[1])
        nt.links.new(clear.outputs["BSDF"], mix.inputs[2])
        nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
        mat["photoreal_glass"] = True
        done.append(mat.name)
    return done


# ---------------------------------------------------------------------------
# Sky, sun, view out
# ---------------------------------------------------------------------------
def _image_mean_luminance(img, samples=40000):
    px = img.pixels[:]
    n = len(px) // 4
    stride = max(1, n // samples)
    tot = cnt = 0
    for i in range(0, n, stride):
        o = i * 4
        tot += 0.2126 * px[o] + 0.7152 * px[o + 1] + 0.0722 * px[o + 2]
        cnt += 1
    return tot / cnt if cnt else 1.0


def daylight_world(sun_alt_deg, sun_az_deg, view_hdri=None, view_rotation_deg=0.0,
                   sky_scale=NISHITA_LUX_SCALE):
    """Physical Nishita sun + sky for LIGHT; a photographed view for the EYE.

    Camera rays see `view_hdri` (a real place with a horizon), everything
    else sees the Nishita sky. Without the split, the only thing visible
    through a window is a gradient with no ground, which reads as a void.
    The view is scaled so its mean luminance matches the diffuse sky's,
    so the garden is neither a black hole nor a white card through glass.
    """
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")

    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "NISHITA"
    sky.sun_disc = True
    sky.sun_size = math.radians(0.545)
    sky.sun_elevation = math.radians(sun_alt_deg)
    sky.sun_rotation = math.radians(sun_az_deg)
    light_bg = nt.nodes.new("ShaderNodeBackground")
    light_bg.inputs["Strength"].default_value = sky_scale
    nt.links.new(sky.outputs["Color"], light_bg.inputs["Color"])

    if not (view_hdri and os.path.isfile(view_hdri)):
        nt.links.new(light_bg.outputs["Background"], out.inputs["Surface"])
        return {"sky": "nishita", "view": None}

    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Rotation"].default_value = (0.0, 0.0, math.radians(view_rotation_deg))
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(view_hdri)
    nt.links.new(coord.outputs["Generated"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], env.inputs["Vector"])
    # Diffuse-sky luminance for a clear sky is roughly a quarter of the
    # global horizontal illuminance, spread over the hemisphere: E/(4*pi).
    diffuse_lum = 0.25 * max(1.0, 76.7 * math.sin(math.radians(max(5.0, sun_alt_deg)))
                             / math.sin(math.radians(35.0))) * sky_scale / math.pi
    mean = _image_mean_luminance(env.image)
    view_bg = nt.nodes.new("ShaderNodeBackground")
    view_bg.inputs["Strength"].default_value = diffuse_lum / max(mean, 1e-6)
    nt.links.new(env.outputs["Color"], view_bg.inputs["Color"])

    # "Seen by the eye" is not just Is Camera Ray: a camera ray that passes
    # through window glass comes out as a TRANSMISSION ray, so it would see
    # the lighting sky (no ground) instead of the view. Measured in the
    # first draft: the window showed a gradient over a white plain. Eye rays
    # = camera rays, plus transmission rays that have not yet bounced off
    # any diffuse or glossy surface.
    path = nt.nodes.new("ShaderNodeLightPath")

    def math_node(op, a, b=None, clamp=False, value=None):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = op
        n.use_clamp = clamp
        nt.links.new(a, n.inputs[0])
        if b is not None:
            nt.links.new(b, n.inputs[1])
        elif value is not None:
            n.inputs[1].default_value = value
        return n.outputs["Value"]

    no_diffuse = math_node("LESS_THAN", path.outputs["Diffuse Depth"], value=0.5)
    no_glossy = math_node("LESS_THAN", path.outputs["Glossy Depth"], value=0.5)
    straight = math_node("MULTIPLY", path.outputs["Is Transmission Ray"],
                         math_node("MULTIPLY", no_diffuse, no_glossy))
    eye = math_node("ADD", path.outputs["Is Camera Ray"], straight, clamp=True)
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(eye, mix.inputs["Fac"])
    nt.links.new(light_bg.outputs["Background"], mix.inputs[1])
    nt.links.new(view_bg.outputs["Background"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return {"sky": "nishita", "view": os.path.basename(view_hdri),
            "view_strength": view_bg.inputs["Strength"].default_value}


def exterior_ground(data, albedo=0.25):
    """A paved ground outside the walls: invisible to the camera, but it is
    what bounces sunlight up onto the ceiling near a real window."""
    mesh = bpy.data.meshes.new("exterior_ground")
    obj = bpy.data.objects.new("exterior_ground", mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    s = 60.0
    for x, y in ((-s, -s), (s, -s), (s, s), (-s, s)):
        bm.verts.new((x, y, -0.02))
    bm.faces.new(bm.verts)
    bm.to_mesh(mesh)
    bm.free()
    mat = bpy.data.materials.new("exterior_paving")
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (albedo, albedo * 0.95, albedo * 0.88, 1.0)
    b.inputs["Roughness"].default_value = 0.9
    mesh.materials.append(mat)
    # Hidden from every ray that stands in for the eye (direct, through
    # glass, reflected), so the photographed view's own ground shows; it
    # still bounces sunlight into the room via diffuse rays.
    obj.visible_camera = False
    obj.visible_transmission = False
    obj.visible_glossy = False
    return obj


def window_portals(data):
    """An area-light portal filling each window opening, to guide sky samples."""
    made = []
    walls = {w["id"]: w for w in data.get("walls", [])}
    for op in data.get("openings", []):
        if op.get("kind") != "window" or op.get("host") not in walls:
            continue
        w = walls[op["host"]]
        sx, sy = w["start"]; ex, ey = w["end"]
        length = math.hypot(ex - sx, ey - sy) or 1.0
        ux, uy = (ex - sx) / length, (ey - sy) / length
        cx, cy = sx + ux * op["at"], sy + uy * op["at"]
        cz = op.get("sill", 900.0) + op["height"] / 2.0
        light = bpy.data.lights.new("portal_" + str(op.get("id", ""))[-6:], type="AREA")
        light.shape = "RECTANGLE"
        light.size = op["width"] / 1000.0
        light.size_y = op["height"] / 1000.0
        light.cycles.is_portal = True
        obj = bpy.data.objects.new(light.name, light)
        obj.location = (cx / 1000.0, cy / 1000.0, cz / 1000.0)
        # Area lights emit along local -Z. Face the room: the wall normal
        # that points toward the room centre.
        nx, ny = -uy, ux
        room = data.get("rooms", [{}])[0].get("boundary") or [[0, 0]]
        rcx = sum(p[0] for p in room) / len(room); rcy = sum(p[1] for p in room) / len(room)
        if (rcx - cx) * nx + (rcy - cy) * ny < 0:
            nx, ny = -nx, -ny
        direction = Vector((nx, ny, 0.0))
        obj.rotation_euler = (-direction).to_track_quat("Z", "Y").to_euler()
        bpy.context.collection.objects.link(obj)
        made.append(obj.name)
    return made


# ---------------------------------------------------------------------------
# Finishes
# ---------------------------------------------------------------------------
# Revit shading colours are not finishes: they are what Revit draws in a
# shaded view. Rescaled to the furniture reflectance they gave a pure red
# lamp shade and an orange door frame. These are stated presentation
# finishes, not measurements; each is logged next to the render.
FINISHES = {
    "Sash": dict(color=(0.93, 0.93, 0.91), rough=0.35, note="white powder-coated aluminium"),
    "Door - Frame": dict(color=(0.90, 0.90, 0.88), rough=0.45, note="white satin paint"),
    "Door - Panel": dict(color=(0.90, 0.90, 0.88), rough=0.45, note="white satin paint"),
    "Shade Finish Dark Bronze": dict(color=(0.42, 0.30, 0.20), metal=1.0, rough=0.38,
                                     note="dark bronze metal"),
    "Shade Interior White": dict(color=(0.85, 0.85, 0.83), rough=0.5, note="white enamel"),
    "Lens -White": dict(color=(0.92, 0.92, 0.92), rough=0.3, note="opal diffuser"),
    "Chrome": dict(color=(0.90, 0.90, 0.90), metal=1.0, rough=0.06, note="polished chrome"),
    "Stainless Steel": dict(color=(0.75, 0.74, 0.72), metal=1.0, rough=0.22, note="brushed steel"),
    "Aluminum": dict(color=(0.88, 0.88, 0.88), metal=1.0, rough=0.3, note="satin aluminium"),
    "Metal Black": dict(color=(0.04, 0.04, 0.04), metal=0.8, rough=0.4, note="black satin metal"),
    "Matte Black": dict(color=(0.03, 0.03, 0.03), rough=0.7, note="matte black"),
    "Cord Black": dict(color=(0.02, 0.02, 0.02), rough=0.6, note="black cord"),
    "Wood": dict(color=(0.30, 0.19, 0.10), rough=0.45, note="stained beech (chair)"),
}


def apply_finish_overrides():
    report = {}
    for mat in bpy.data.materials:
        base = mat.name.split(".")[0]
        spec = FINISHES.get(base)
        if not spec or not mat.use_nodes:
            continue
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if not bsdf:
            continue
        for name in ("Base Color", "Roughness", "Metallic"):
            for link in list(bsdf.inputs[name].links):
                mat.node_tree.links.remove(link)
        bsdf.inputs["Base Color"].default_value = tuple(spec["color"]) + (1.0,)
        bsdf.inputs["Roughness"].default_value = spec["rough"]
        bsdf.inputs["Metallic"].default_value = spec.get("metal", 0.0)
        mat["presentation_assumption"] = "finish override: " + spec["note"]
        report[mat.name] = spec["note"]
    return report


# ---------------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------------
# Eye and target in model metres. Room: 0..4.2 x 0..3.6, window on the
# south wall (x 1.35-2.85), door on the east wall (y 0.35-1.25), bed x
# 1.45-3.05 y 1.6-3.6 with the headboard on the north wall.
VIEWS = {
    "door":     ((4.00, 0.80, 1.35), (1.20, 2.60, 1.00), 24.0),
    "bedfoot":  ((3.95, 0.30, 1.35), (2.10, 3.30, 0.95), 24.0),
    "window":   ((3.95, 3.35, 1.35), (1.80, 0.00, 1.30), 24.0),
    "desk":     ((3.30, 1.25, 1.35), (0.80, 0.40, 0.95), 24.0),
    "wardrobe": ((3.40, 1.30, 1.35), (0.30, 2.30, 1.10), 24.0),
    "detail":   ((3.95, 2.40, 1.05), (3.20, 3.45, 0.70), 50.0),
}


def photographic_camera(name):
    """A level camera with lens shift: vertical lines stay vertical.

    Architectural photographers keep the camera body level and shift the
    lens instead of tilting; a tilted camera makes every wall lean in.
    Blender's shift_y is a fraction of the sensor width (sensor_fit AUTO,
    landscape frame), so a point `theta` above the horizon lands on the
    frame centre when shift_y = f * tan(theta) / sensor_width.
    """
    eye, target, lens = VIEWS[name]
    cam_data = bpy.data.cameras.new("camera_" + name)
    cam_data.lens = lens
    cam_data.sensor_width = 36.0
    cam_data.sensor_fit = "HORIZONTAL"
    cam_data.clip_start = 0.05
    dx, dy, dz = (target[0] - eye[0], target[1] - eye[1], target[2] - eye[2])
    yaw = math.atan2(dy, dx) - math.pi / 2.0
    theta = math.atan2(dz, math.hypot(dx, dy))
    cam_data.shift_y = lens * math.tan(theta) / cam_data.sensor_width
    cam = bpy.data.objects.new("camera_" + name, cam_data)
    cam.location = eye
    cam.rotation_euler = (math.radians(90.0), 0.0, yaw)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    return cam


# ---------------------------------------------------------------------------
# Exposure and white balance
# ---------------------------------------------------------------------------
def camera_meter(key=0.18, bias_stops=0.0):
    """Expose like a camera's meter: a fast pre-render, log-average luminance.

    Returns the exposure in stops that maps the scene's log-average
    luminance to `key` (mid grey). Windows and lamps are clipped out of the
    average (top 3%) the way a centre-weighted meter is fooled less than
    an average one; `bias_stops` is the photographer's compensation.
    """
    s = bpy.context.scene
    saved = (s.cycles.samples, s.render.resolution_percentage, s.cycles.use_denoising,
             s.render.image_settings.file_format, s.render.image_settings.color_depth,
             s.view_settings.view_transform, s.view_settings.exposure, s.render.filepath)
    s.cycles.samples = 24
    s.render.resolution_percentage = 15
    s.cycles.use_denoising = True
    s.render.image_settings.file_format = "OPEN_EXR"
    s.render.image_settings.color_depth = "32"
    s.view_settings.view_transform = "Standard"
    s.view_settings.exposure = 0.0
    path = os.path.join(tempfile.mkdtemp(), "meter.exr")
    s.render.filepath = path
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(path)
    px = img.pixels[:]
    bpy.data.images.remove(img)
    lums = sorted(0.2126 * px[i] + 0.7152 * px[i + 1] + 0.0722 * px[i + 2]
                  for i in range(0, len(px), 4))
    lums = [v for v in lums[: int(len(lums) * 0.97)] if v > 0]
    logavg = math.exp(sum(math.log(v) for v in lums) / len(lums)) if lums else 1.0
    (s.cycles.samples, s.render.resolution_percentage, s.cycles.use_denoising,
     s.render.image_settings.file_format, s.render.image_settings.color_depth,
     s.view_settings.view_transform, s.view_settings.exposure, s.render.filepath) = saved
    return math.log2(key / logavg) + bias_stops, logavg


def white_balance(kelvin):
    vs = bpy.context.scene.view_settings
    if not hasattr(vs, "white_balance_temperature"):
        return False                          # Blender < 4.3
    vs.use_white_balance = True
    vs.white_balance_temperature = float(kelvin)
    vs.white_balance_tint = 10.0              # Blender's neutral at D65
    return True


def presentation_render_settings():
    s = bpy.context.scene
    c = s.cycles
    c.transmission_bounces = 32
    c.glossy_bounces = 32
    c.transparent_max_bounces = 32
    c.caustics_reflective = True
    c.caustics_refractive = True
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.005
    if hasattr(c, "use_light_tree"):
        c.use_light_tree = True
    try:
        s.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass


# ---------------------------------------------------------------------------
# Bedding: cloth-simulated duvet and throw over the Revit bed
# ---------------------------------------------------------------------------
def _islands(obj):
    """Split a mesh object into loose parts; returns [(bbox_min, bbox_max, obj)]."""
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="LOOSE")
    bpy.ops.object.mode_set(mode="OBJECT")
    parts = [o for o in bpy.context.selected_objects]
    out = []
    for o in parts:
        vs = [o.matrix_world @ v.co for v in o.data.vertices]
        lo = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
        hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
        out.append((lo, hi, o))
    return out


def _grid(name, sx, sy, nx, ny, center, z):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=nx, y_segments=ny, size=0.5)
    for v in bm.verts:
        v.co.x = center[0] + v.co.x * sx
        v.co.y = center[1] + v.co.y * sy
        v.co.z = z
    bm.to_mesh(mesh)
    bm.free()
    return obj


def _simulate(obj, colliders, frames, mass, bending, pin_band=None):
    for c in colliders:
        if not any(m.type == "COLLISION" for m in c.modifiers):
            c.modifiers.new("collision", "COLLISION")
            c.collision.thickness_outer = 0.004
            c.collision.cloth_friction = 8.0
    cloth = obj.modifiers.new("cloth", "CLOTH")
    st = cloth.settings
    st.quality = 8
    st.mass = mass
    st.tension_stiffness = st.compression_stiffness = 12.0
    st.shear_stiffness = 6.0
    st.bending_stiffness = bending
    st.air_damping = 1.5
    cs = cloth.collision_settings
    cs.collision_quality = 4
    cs.distance_min = 0.004
    cs.use_self_collision = True
    cs.self_distance_min = 0.004
    cloth.point_cache.frame_start = 1
    cloth.point_cache.frame_end = frames
    scene = bpy.context.scene
    for f in range(1, frames + 1):
        scene.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    baked = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    obj.modifiers.remove(cloth)
    old = obj.data
    obj.data = baked
    bpy.data.meshes.remove(old)
    scene.frame_set(1)


def cloth_bedding(data):
    """Replace the extract's sculpted duvet and throw with draped cloth.

    The Revit bed (frame, headboard, mattress, footprint, position) stays
    exactly as extracted: ADR-0001. Only the soft furnishing -- which Revit
    does not model at all -- is re-made, by letting a sheet fall onto the
    real mattress and settle, which is the only way folds come out right.
    """
    bed = next((f for f in data.get("furniture", [])
                if "bed_double" in str(f.get("type_name", ""))), None)
    if not bed:
        return {"bedding": "no bed in extract"}
    bid = bed["id"]
    objs = [o for o in bpy.data.objects if o.get("source_id") == bid]
    bedding = next((o for o in objs if "bedding" in o.name), None)
    throw = next((o for o in objs if "throw" in o.name), None)
    if not bedding:
        return {"bedding": "no bedding mesh"}
    parts = _islands(bedding)
    mattress = max(parts, key=lambda p: (p[1].x - p[0].x) * (p[1].y - p[0].y) *
                   (1.0 if p[1].z - p[0].z > 0.08 else 0.0))
    m_lo, m_hi, m_obj = mattress
    removed = 0
    keep = []
    for lo, hi, o in parts:
        footprint = (hi.x - lo.x) * (hi.y - lo.y)
        is_duvet = o is not m_obj and footprint > 1.0 and hi.z > m_hi.z
        if is_duvet:
            bpy.data.objects.remove(o, do_unlink=True)
            removed += 1
        else:
            keep.append(o)
    if throw:
        bpy.data.objects.remove(throw, do_unlink=True)

    frame = [o for o in bpy.data.objects
             if o.get("source_id") == bid and o not in keep
             and ("oak" in o.name or "linen" in o.name)]
    colliders = keep + frame
    mat_bedding = next((m for m in bpy.data.materials if m.name.startswith("archpipe ivory bedding")), None)
    mat_throw = next((m for m in bpy.data.materials if m.name.startswith("archpipe muted taupe throw")), None)

    width = m_hi.x - m_lo.x
    length = m_hi.y - m_lo.y
    head_y = m_hi.y if bed.get("rotation", 0) in (180, 180.0) else m_lo.y
    foot_sign = -1.0 if head_y == m_hi.y else 1.0
    # Duvet: mattress width plus a 0.30 m drop each side; from 0.45 m below
    # the pillows to 0.30 m over the foot.
    dw = width + 0.60
    dl = length - 0.45 + 0.30
    cy = head_y + foot_sign * (0.45 + dl / 2.0)
    duvet = _grid("duvet_cloth", dw, dl, 70, 80, ((m_lo.x + m_hi.x) / 2.0, cy), m_hi.z + 0.06)
    # Seed small irregularities so the sheet folds instead of settling as
    # a perfectly smooth, CG-looking slab.
    import random
    rnd = random.Random(7)
    for v in duvet.data.vertices:
        v.co.z += rnd.uniform(0.0, 0.02)
    _simulate(duvet, colliders, 50, mass=0.4, bending=0.6)
    solid = duvet.modifiers.new("thickness", "SOLIDIFY")
    solid.thickness = 0.035
    solid.offset = 1.0
    sub = duvet.modifiers.new("smooth", "SUBSURF")
    sub.levels = sub.render_levels = 1
    if mat_bedding:
        duvet.data.materials.append(mat_bedding)
    for p in duvet.data.polygons:
        p.use_smooth = True

    # Throw: folded runner across the foot of the bed, over the duvet.
    tl = 0.55
    ty = head_y + foot_sign * (length - 0.40)
    thr = _grid("throw_cloth", width + 0.50, tl, 60, 24, ((m_lo.x + m_hi.x) / 2.0, ty),
                m_hi.z + 0.20)
    _simulate(thr, colliders + [duvet], 40, mass=0.8, bending=4.0)
    s2 = thr.modifiers.new("thickness", "SOLIDIFY")
    s2.thickness = 0.012
    s2.offset = 1.0
    thr.modifiers.new("smooth", "SUBSURF").levels = 1
    if mat_throw:
        thr.data.materials.append(mat_throw)
    for p in thr.data.polygons:
        p.use_smooth = True
    for o in keep:
        if o is not m_obj:
            sd = o.modifiers.new("smooth", "SUBSURF")
            sd.levels = sd.render_levels = 2
    return {"bedding": "cloth", "duvet_removed_islands": removed,
            "mattress_top_m": round(m_hi.z, 3)}


# ---------------------------------------------------------------------------
# Dressing
# ---------------------------------------------------------------------------
def import_prop(library_root, prop_id, location, rotation_deg=0.0):
    path = os.path.join(library_root, "props", prop_id, "model.gltf")
    if not os.path.isfile(path):
        return None
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    roots = [o for o in new if o.parent is None]
    meshes = [o for o in new if o.type == "MESH"]
    if not meshes:
        return None
    zmin = min((o.matrix_world @ Vector(c)).z for o in meshes for c in o.bound_box)
    for r in roots:
        r.location.x += location[0]
        r.location.y += location[1]
        r.location.z += location[2] - zmin
        r.rotation_euler.z += math.radians(rotation_deg)
    return prop_id


def _top_of(data, mark):
    item = next((f for f in data.get("furniture", []) if f.get("mark") == mark), None)
    if not item:
        return None
    return (item["at"][0] / 1000.0, item["at"][1] / 1000.0, item["size_mm"][2] / 1000.0)


def dress_room(data, library_root, presentation):
    placed = []
    bl = _top_of(data, "FN-BST-L")
    br = _top_of(data, "FN-BST-R")
    dk = _top_of(data, "FN-DSK")
    if br:
        placed.append(import_prop(library_root, "alarm_clock_01", (br[0] + 0.08, br[1] - 0.05, br[2]), 200))
    if bl:
        placed.append(import_prop(library_root, "book_encyclopedia_set_01", (bl[0], bl[1] + 0.02, bl[2]), 90))
        placed.append(import_prop(library_root, "potted_plant_04", (bl[0] - 0.12, bl[1] - 0.05, bl[2])))
    if dk:
        placed.append(import_prop(library_root, "brass_vase_03", (dk[0] - 0.45, dk[1] + 0.05, dk[2])))
    placed.append(import_prop(library_root, "potted_plant_01", (3.90, 3.30, 0.0)))
    before = set(bpy.data.materials)
    placed.append(import_prop(library_root, "throw_pillows_01", (2.25, 3.00, 0.56), 180))
    # Keep the scanned cushion shapes, re-cover them in a muted sage linen:
    # the scan's zig-zag print reads dated next to a contemporary scheme.
    for mat in [m for m in bpy.data.materials if m not in before]:
        presentation._apply_photo_texture(mat, library_root, "Fabric036", 0.28, tile_m=0.4,
                                          tint=(0.80, 0.90, 0.78))

    # Skirting: 80 mm white paint along the inner wall faces, gap at the door.
    skirt = bpy.data.materials.new("skirting_paint")
    skirt.use_nodes = True
    sb = skirt.node_tree.nodes["Principled BSDF"]
    sb.inputs["Base Color"].default_value = (0.88, 0.88, 0.86, 1.0)
    sb.inputs["Roughness"].default_value = 0.4
    runs = [((0.0, 0.0), (4.2, 0.0), (0, 1)), ((0.0, 3.6), (4.2, 3.6), (0, -1)),
            ((0.0, 0.0), (0.0, 3.6), (1, 0)), ((4.2, 1.25), (4.2, 3.6), (-1, 0)),
            ((4.2, 0.0), (4.2, 0.35), (-1, 0))]
    for (ax, ay), (bx, by), (nx, ny) in runs:
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        o = bpy.context.active_object
        o.name = "skirting"
        length = math.hypot(bx - ax, by - ay)
        o.scale = ((length, 0.015, 0.08) if ay == by else (0.015, length, 0.08))
        o.location = ((ax + bx) / 2 + nx * 0.0075, (ay + by) / 2 + ny * 0.0075, 0.04)
        o.data.materials.append(skirt)

    # Rug under the bed, running past its foot.
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    rug = bpy.context.active_object
    rug.name = "rug"
    rug.scale = (2.3, 2.1, 0.012)
    rug.location = (2.25, 2.15, 0.006)
    rmat = bpy.data.materials.new("archpipe rug")
    rmat.use_nodes = True
    rug.data.materials.append(rmat)
    presentation._apply_photo_texture(rmat, library_root, "Carpet001", 0.30, tile_m=1.0,
                                      bump_strength=0.3)
    bev = rug.modifiers.new("bevel", "BEVEL")
    bev.width = 0.004
    bev.segments = 2

    # Curtains: pleated linen panels drawn to either side of the window.
    cmat = next((m for m in bpy.data.materials if m.name.startswith("archpipe warm linen")), None)
    for x0, x1 in ((0.85, 1.30), (2.90, 3.35)):
        c = _grid("curtain", x1 - x0, 2.55, 40, 60, ((x0 + x1) / 2.0, 0.0), 0.0)
        for v in c.data.vertices:
            # Grid y (-1.275..1.275) becomes height; x gets sinusoidal pleats.
            u = (v.co.x - x0) / (x1 - x0)
            v.co = Vector((v.co.x, 0.10 + 0.035 * math.sin(u * math.pi * 9.0),
                           0.05 + (v.co.y + 1.275)))
        solid = c.modifiers.new("thickness", "SOLIDIFY")
        solid.thickness = 0.004
        c.modifiers.new("smooth", "SUBSURF").levels = 1
        if cmat:
            c.data.materials.append(cmat)
        for p in c.data.polygons:
            p.use_smooth = True
    return [p for p in placed if p]
