"""Blender (headless): render a scatter DRIFT of a small plant asset (gazania, lawn grass, groundcover) at 5 m and 15 m.

    blender -b -P drift_preview.py -- --assets drift.json --out DIR [--cpu]
drift.json: [{"id": "...", "gltf": "/abs/model.gltf", "n": 60, "size_m": 3.0, "scale": 1.0}]
Tests whether a scatter asset reads as a planting when instanced, instead of assuming it (docs/lanes/LDL.md).
"""
import json, math, random, sys
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
args = dict(zip([a for a in argv if a != "--cpu"][::2], [a for a in argv if a != "--cpu"][1::2]))
out = args["--out"]


def scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"; sc.cycles.samples = 32; sc.cycles.use_denoising = False
    sc.render.resolution_x = sc.render.resolution_y = 400
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.62, 0.72, 0.9, 1)
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sun.data.energy = 4
    sun.rotation_euler = (math.radians(50), 0, math.radians(35)); sc.collection.objects.link(sun)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); cam.data.lens = 35
    sc.collection.objects.link(cam); sc.camera = cam
    g = bpy.data.objects.new("g", bpy.data.meshes.new("g"))
    g.data.from_pydata([(-60, -60, 0), (60, -60, 0), (60, 60, 0), (-60, 60, 0)], [], [(0, 1, 2, 3)])
    m = bpy.data.materials.new("gm"); m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.3, 0.26, 0.2, 1); g.data.materials.append(m)
    sc.collection.objects.link(g)
    return sc, cam


for a in json.load(open(args["--assets"])):
    sc, cam = scene()
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=a["gltf"])
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == "MESH"]
    # one variant per mesh object: unparent keeping transform, move to origin, then instance with linked data
    variants = []
    for o in meshes:
        mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        c = sum(bb, Vector()) / 8
        o.location -= Vector((c.x, c.y, min(v.z for v in bb)))
        variants.append(o); o.hide_render = True
    rnd = random.Random(7)
    for i in range(a["n"]):
        src = rnd.choice(variants)
        inst = bpy.data.objects.new(f"i{i}", src.data)
        inst.location = (rnd.uniform(-a["size_m"] / 2, a["size_m"] / 2), rnd.uniform(-a["size_m"] / 2, a["size_m"] / 2), src.location.z)
        inst.rotation_euler = (src.rotation_euler.x, src.rotation_euler.y, rnd.uniform(0, 6.283))
        s = a.get("scale", 1.0) * rnd.uniform(0.8, 1.2); inst.scale = (s * src.scale.x, s * src.scale.y, s * src.scale.z)
        sc.collection.objects.link(inst)
    for d in (5, 15):
        for az in (0, 90):
            r = math.radians(az)
            cam.location = (d * math.sin(r), -d * math.cos(r), 1.6)
            cam.rotation_euler = (Vector((0, 0, 0.2)) - cam.location).to_track_quat("-Z", "Y").to_euler()
            sc.render.filepath = f"{out}/{a['id']}_drift_d{d}_az{az}.png"
            bpy.ops.render.render(write_still=True)
