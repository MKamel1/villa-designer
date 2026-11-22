"""Blender (headless) turntable preview + geometry stats for candidate plant assets.

    blender -b --python-exit-code 1 -P asset_preview.py -- --assets assets.json --out DIR

assets.json: [{"id": "...", "gltf": "/abs/model.gltf"}, ...]. For each asset writes
DIR/<id>_d5_az<deg>.png and DIR/<id>_d15_az<deg>.png (35 mm lens, eye 1.6 m, camera 5 m and 15 m
from the asset centre, azimuths 0/90/180/270) and DIR/stats.json (triangles, bbox, alpha-card share).
Run it through ~/archpipe/bin/jobq (GPU lock). Assets are left at their authored scale.
"""
import json
import math
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
args = dict(zip(argv[::2], argv[1::2]))
assets = json.load(open(args["--assets"]))
out = args["--out"]
RES = 400


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 48
    sc.cycles.use_denoising = False
    sc.render.resolution_x = sc.render.resolution_y = RES
    sc.render.image_settings.file_format = "PNG"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "CUDA"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type == "CUDA"
        sc.cycles.device = "GPU"
    except Exception as e:  # CPU fallback is fine for a preview
        print("GPU not available:", e)
    w = bpy.data.worlds.new("w")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.62, 0.72, 0.9, 1)
    bg.inputs[1].default_value = 1.0
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 4.0
    sun.rotation_euler = (math.radians(50), 0, math.radians(35))
    sc.collection.objects.link(sun)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    cam.data.lens, cam.data.sensor_width = 35, 36
    sc.collection.objects.link(cam)
    sc.camera = cam
    return sc, cam


def stats(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    tris, alpha_tris, lo, hi, area = 0, 0, Vector((1e9,) * 3), Vector((-1e9,) * 3), 0.0
    for o in objs:
        me = o.evaluated_get(dg).to_mesh()
        me.calc_loop_triangles()
        mats = [s.material for s in o.material_slots]
        for t in me.loop_triangles:
            tris += 1
            area += t.area
            m = mats[t.material_index] if t.material_index < len(mats) else None
            if m is not None and m.use_nodes:
                bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
                if bsdf and (bsdf.inputs["Alpha"].is_linked or bsdf.inputs["Alpha"].default_value < 1):
                    alpha_tris += 1
        for v in me.vertices:
            w = o.matrix_world @ v.co
            lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
        o.evaluated_get(dg).to_mesh_clear()
    return {"triangles": tris, "alpha_card_tri_share": round(alpha_tris / max(tris, 1), 3),
            "mean_tri_area_cm2": round(area / max(tris, 1) * 1e4, 3),
            "bbox_min_m": [round(x, 3) for x in lo], "bbox_max_m": [round(x, 3) for x in hi],
            "size_m": [round(hi[i] - lo[i], 3) for i in range(3)]}


result = {}
for a in assets:
    sc, cam = reset()
    ground = bpy.data.objects.new("g", bpy.data.meshes.new("g"))
    me = ground.data
    me.from_pydata([(-60, -60, 0), (60, -60, 0), (60, 60, 0), (-60, 60, 0)], [], [(0, 1, 2, 3)])
    gm = bpy.data.materials.new("gm"); gm.diffuse_color = (0.3, 0.28, 0.25, 1)
    gm.use_nodes = True; gm.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.3, 0.28, 0.25, 1)
    me.materials.append(gm)
    sc.collection.objects.link(ground)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=a["gltf"])
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == "MESH"]
    # glTF imports Y-up -> Z-up; the plant should stand on z=0
    st = stats(meshes)
    lift = -st["bbox_min_m"][2]
    for o in new:
        if o.parent is None:
            o.location.z += lift
    bpy.context.view_layer.update()
    st = stats(meshes)
    result[a["id"]] = st
    cx = (st["bbox_min_m"][0] + st["bbox_max_m"][0]) / 2
    cy = (st["bbox_min_m"][1] + st["bbox_max_m"][1]) / 2
    target_z = max(0.4, min(st["bbox_max_m"][2] / 2, 3.0))
    for d in (5, 15):
        for az in (0, 90, 180, 270):
            r = math.radians(az)
            cam.location = (cx + d * math.sin(r), cy - d * math.cos(r), 1.6)
            dirv = Vector((cx, cy, target_z)) - cam.location
            cam.rotation_euler = dirv.to_track_quat("-Z", "Y").to_euler()
            sc.render.filepath = f"{out}/{a['id']}_d{d}_az{az}.png"
            bpy.ops.render.render(write_still=True)
json.dump(result, open(f"{out}/stats.json", "w"), indent=1)
