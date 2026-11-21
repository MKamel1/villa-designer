"""V5 engine (c): Cycles calibrated photometric render of one closed room, read with the production sensor method.

Run inside Blender:  blender -b -P cycles_probe.py -- JOB.json OUT.json
JOB: {"src": repo src dir, "ies_dir", "lights": [villa_scene light specs], "room": {"polygon","floor","ceiling","rho_floor",
"rho_wall","rho_ceiling"}, "points": [[x,y,z]...], "mf": 0.8, "samples": 256, "bounces": 8}
Lights are built by the production constructor (villa_scene.add_light: IES texture node, IES_POINT_POWER calibration, aim),
the sensor by the production method (0.5-reflectance 4 cm plane 1 mm over the point, 20 mm ortho camera, central 16x16 of
32x32, radiance x pi / 0.5). Writes [{point, direct_lux, total_lux}] with the maintenance factor applied.
"""
import json
import math
import os
import sys

import bmesh
import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
JOB = json.load(open(argv[0]))
sys.path.insert(0, JOB["src"])
from archpipe.blender import villa_scene as VS  # noqa: E402


def mat(name, rho):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    d = nt.nodes.new("ShaderNodeBsdfDiffuse")
    d.inputs["Color"].default_value = (rho, rho, rho, 1)
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(d.outputs[0], o.inputs["Surface"])
    return m


def build_room(r):
    me = bpy.data.meshes.new("room")
    bm = bmesh.new()
    poly = r["polygon"]
    f0, f1 = r["floor"], r["ceiling"]
    bot = [bm.verts.new((x, y, f0)) for x, y in poly]
    top = [bm.verts.new((x, y, f1)) for x, y in poly]
    fl = bm.faces.new(bot)
    fl.material_index = 0
    ce = bm.faces.new(top)
    ce.material_index = 2
    n = len(poly)
    for i in range(n):
        w = bm.faces.new((bot[i], bot[(i + 1) % n], top[(i + 1) % n], top[i]))
        w.material_index = 1
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("room", me)
    bpy.context.collection.objects.link(o)
    for nm, rho in (("floor", r["rho_floor"]), ("wall", r["rho_wall"]), ("ceiling", r["rho_ceiling"])):
        me.materials.append(mat(nm, rho))


def lum(p):
    return 0.2126 * p[0] + 0.7152 * p[1] + 0.0722 * p[2]


bpy.ops.wm.read_factory_settings(use_empty=True)
S = bpy.context.scene
S.render.engine = "CYCLES"
dev = "CPU"
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for t in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = t
            prefs.get_devices()
            if any(d.type == t for d in prefs.devices):
                for d in prefs.devices:
                    d.use = d.type == t
                dev = "GPU"
                break
        except Exception:
            continue
except Exception:
    pass
S.cycles.device = dev
build_room(JOB["room"])
for spec in JOB["lights"]:
    VS.add_light(spec, JOB["ies_dir"])
for o in bpy.data.objects:
    if o.type == "LIGHT":
        o.data.energy *= JOB.get("mf", 0.8)
w = bpy.data.worlds.new("black")
w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0
S.world = w
S.cycles.use_denoising = False
S.cycles.sample_clamp_direct = 0.0      # Cycles default clamps indirect samples at 10: biased low at these radiance levels (found by the cube test)
S.cycles.sample_clamp_indirect = 0.0
S.cycles.samples = JOB.get("samples", 256)
S.render.resolution_x = S.render.resolution_y = 32
S.render.resolution_percentage = 100
S.render.image_settings.file_format = "OPEN_EXR"
S.render.image_settings.color_depth = "32"
S.view_settings.view_transform = "Standard"
S.view_settings.look = "None"
bpy.ops.mesh.primitive_plane_add(size=0.04)
sensor = bpy.context.object
sensor.data.materials.append(mat("sensor", 0.5))
cd = bpy.data.cameras.new("cam")
cd.type = "ORTHO"
cd.ortho_scale = 0.02
cd.clip_start = 0.001
cd.clip_end = 0.1
cam = bpy.data.objects.new("cam", cd)
bpy.context.collection.objects.link(cam)
S.camera = cam
wd = os.path.join(os.path.dirname(os.path.abspath(argv[1])), "exr")
os.makedirs(wd, exist_ok=True)
out = []
for i, (x, y, z) in enumerate(JOB["points"]):
    sensor.location = (x, y, z + 0.001)
    cam.location = (x, y, z + 0.025)
    rec = {"point": [x, y, z]}
    for key, b in (("direct_lux", 0), ("total_lux", JOB.get("bounces", 8))):
        S.cycles.max_bounces = b
        S.cycles.diffuse_bounces = b
        S.cycles.glossy_bounces = 0
        S.cycles.transmission_bounces = 0
        S.cycles.transparent_max_bounces = 8
        path = os.path.join(wd, "p%03d-%s.exr" % (i, key))
        S.render.filepath = path
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(path)
        px = img.pixels[:]
        vals = [lum(px[4 * (yy * 32 + xx):4 * (yy * 32 + xx) + 3]) for yy in range(8, 24) for xx in range(8, 24)]
        rec[key] = sum(vals) / len(vals) * math.pi / 0.5
        bpy.data.images.remove(img)
    out.append(rec)
json.dump({"device": dev, "readings": out}, open(argv[1], "w"))
