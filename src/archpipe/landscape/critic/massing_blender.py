"""Blender (headless) clay massing render of a garden layout spec. Not importable outside Blender.

    blender -b --python-exit-code 1 -P massing_blender.py -- spec.json out.png

spec.json is written by `archpipe.landscape.critic.massing.massing_png`; all coordinates are metres in the PLOT frame
(x east, y north, z up). Solids: slabs (extruded polygons), boxes, ellipsoids, cylinders. Flat clay colours, one sun, soft sky.
"""
import json
import math
import sys

import bmesh
import bpy
from mathutils import Vector

spec = json.load(open(sys.argv[sys.argv.index("--") + 1]))
out = sys.argv[sys.argv.index("--") + 2]
sc = None
MATS = {}


def mat(name, rgb):
    if name not in MATS:
        m = bpy.data.materials.new(name); m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = 0.95
        if name == "ghost":                                       # see-through boundary fences: drawn at height, not hiding the garden
            b.inputs["Alpha"].default_value = 0.18
        MATS[name] = m
    return MATS[name]


def link(o, m):
    sc.collection.objects.link(o); o.data.materials.append(m); return o


def slab(poly, z0, z1, m):
    """Closed prism: bottom, top and side faces built explicitly (outward normals)."""
    area = sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))
    if area < 0: poly = poly[::-1]
    n = len(poly)
    vs = [(x, y, z0) for x, y in poly] + [(x, y, z1) for x, y in poly]
    fs = [list(range(n - 1, -1, -1)), list(range(n, 2 * n))] + [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    me = bpy.data.meshes.new("s"); me.from_pydata(vs, [], fs)
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="EAR_CLIP")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    link(bpy.data.objects.new("s", me), m)


def box(x0, y0, x1, y1, z0, z1, m):
    slab([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, m)


def ellipsoid(cx, cy, cz, rx, rz, m):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, location=(cx, cy, cz))
    o = bpy.context.active_object; o.scale = (rx, rx, rz)
    for c in list(o.users_collection): c.objects.unlink(o)
    link(o, m)
    bpy.ops.object.shade_smooth() if False else None


def cylinder(cx, cy, z0, z1, r, m):
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=r, depth=z1 - z0, location=(cx, cy, (z0 + z1) / 2))
    o = bpy.context.active_object
    for c in list(o.users_collection): c.objects.unlink(o)
    link(o, m)


bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.samples = 48; sc.cycles.use_denoising = False; sc.view_settings.view_transform = "Standard"
sc.render.resolution_x, sc.render.resolution_y = spec.get("size", [1400, 900])
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "CUDA"; prefs.get_devices()
    for d in prefs.devices: d.use = d.type == "CUDA"
    sc.cycles.device = "GPU"
except Exception as e:
    print("GPU not available:", e)
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.82, 0.86, 0.92, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.35
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sun.data.energy = 1.5; sun.data.angle = math.radians(4)
sun.rotation_euler = (math.radians(48), 0, math.radians(35)); sc.collection.objects.link(sun)

C = {"ground": (0.60, 0.58, 0.53), "house": (0.90, 0.89, 0.87), "paving": (0.78, 0.76, 0.72), "bed": (0.45, 0.38, 0.30),
     "tree": (0.30, 0.46, 0.28), "trunk": (0.30, 0.24, 0.18), "drift": (0.45, 0.62, 0.32), "water": (0.30, 0.58, 0.82),
     "wood": (0.72, 0.58, 0.40), "screen": (0.45, 0.58, 0.42), "wall": (0.80, 0.80, 0.80), "furn": (0.60, 0.45, 0.30), "ghost": (0.55, 0.55, 0.60)}
x0, y0, x1, y1 = spec["bounds"]
m_ = 3.0
box(x0 - m_, y0 - m_, x1 + m_, y1 + m_, -0.05, 0.0, mat("ground", C["ground"]))
for it in spec["solids"]:
    k = it["kind"]; m = mat(it["mat"], C[it["mat"]])
    if k == "slab": slab(it["poly"], it["z0"], it["z1"], m)
    elif k == "box": box(*it["rect"], it["z0"], it["z1"], m)
    elif k == "ellipsoid": ellipsoid(*it["at"], it["rx"], it["rz"], m)
    elif k == "cylinder": cylinder(*it["at"], it["z0"], it["z1"], it["r"], m)

cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
az, el = math.radians(spec["azimuth"]), math.radians(spec["elevation"])
dist = spec["distance"]
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); cam.data.lens, cam.data.sensor_width = 35, 36
cam.location = (cx + dist * math.cos(el) * math.sin(az), cy - dist * math.cos(el) * math.cos(az), dist * math.sin(el))
tgt = bpy.data.objects.new("t", None); tgt.location = (cx, cy, 0.8); sc.collection.objects.link(tgt)
tc = cam.constraints.new("TRACK_TO"); tc.target = tgt; tc.track_axis = "TRACK_NEGATIVE_Z"; tc.up_axis = "UP_Y"
sc.collection.objects.link(cam); sc.camera = cam
sc.render.image_settings.file_format = "PNG"; sc.render.filepath = out
bpy.ops.render.render(write_still=True)
