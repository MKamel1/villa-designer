"""Blender (headless) fit-to-object turntable + stats for outdoor furniture / koi candidates.

    blender -b --python-exit-code 1 -P outdoor_preview.py -- --assets list.json --out DIR [--cpu]

list.json: [{"id", "gltf" (abs path), "koi": bool (optional)}]. Writes DIR/<id>_az<0|90|180|270>.png (3/4 view, camera at
2.2 x the longest side, elevation 22 deg; koi also DIR/<id>_koi15.png: scaled to 0.6 m long, seen from 1.5 m, 35 mm
lens, 55 deg down) and DIR/stats.json: triangles, native size (Z-up, as imported, before any lift), textures,
open (boundary) edge share and non-manifold edge share as a watertightness proxy, flat-card flag.
"""
import json, math, sys
import bpy, bmesh
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
cpu = "--cpu" in argv
args = dict(zip([a for a in argv if a != "--cpu"][::2], [a for a in argv if a != "--cpu"][1::2]))
assets = json.load(open(args["--assets"]))
out = args["--out"]
RES = 360


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"; sc.cycles.samples = 32; sc.cycles.use_denoising = False
    sc.render.resolution_x = sc.render.resolution_y = RES
    try:
        if cpu: raise RuntimeError("cpu")
        p = bpy.context.preferences.addons["cycles"].preferences
        p.compute_device_type = "CUDA"; p.get_devices()
        for d in p.devices: d.use = d.type == "CUDA"
        sc.cycles.device = "GPU"
    except Exception as e:
        print("cpu fallback", e)
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.62, 0.72, 0.9, 1)
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sun.data.energy = 4.0
    sun.rotation_euler = (math.radians(50), 0, math.radians(35)); sc.collection.objects.link(sun)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); cam.data.sensor_width = 36
    sc.collection.objects.link(cam); sc.camera = cam
    return sc, cam


def bounds(meshes):
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for o in meshes:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    return lo, hi


def mesh_stats(meshes):
    dg = bpy.context.evaluated_depsgraph_get()
    tris = edges = bnd = nm = 0
    for o in meshes:
        bm = bmesh.new(); bm.from_mesh(o.evaluated_get(dg).to_mesh()); bm.transform(o.matrix_world)
        tris += sum(len(f.verts) - 2 for f in bm.faces)
        for e in bm.edges:
            edges += 1
            n = len(e.link_faces)
            bnd += n == 1; nm += n > 2
        bm.free()
    return tris, edges, bnd, nm


def look(cam, tgt, loc):
    cam.location = loc
    cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()


res = {}
for a in assets:
    sc, cam = reset()
    cam.data.lens = 35
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=a["gltf"])
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == "MESH"]
    bpy.context.view_layer.update()
    lo, hi = bounds(meshes)
    size = [round(hi[i] - lo[i], 3) for i in range(3)]
    tris, edges, bnd, nm = mesh_stats(meshes)
    texs = sorted({n.image.name for m in bpy.data.materials if m.use_nodes for n in m.node_tree.nodes if n.type == "TEX_IMAGE" and n.image})
    res[a["id"]] = dict(size_m=size, triangles=tris, n_mesh_objects=len(meshes), textures=len(texs),
                        boundary_edge_share=round(bnd / max(edges, 1), 3), nonmanifold_edge_share=round(nm / max(edges, 1), 3),
                        flat_card=min(size) < 0.02 * max(size), bbox_min_m=[round(x, 3) for x in lo])
    # stand on z=0, centred; ground plane
    for o in new:
        if o.parent is None:
            o.location += Vector((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z))
    bpy.context.view_layer.update()
    me = bpy.data.meshes.new("g"); g = bpy.data.objects.new("g", me)
    me.from_pydata([(-30, -30, 0), (30, -30, 0), (30, 30, 0), (-30, 30, 0)], [], [(0, 1, 2, 3)])
    gm = bpy.data.materials.new("gm"); gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.35, 0.33, 0.3, 1); me.materials.append(gm)
    sc.collection.objects.link(g)
    L = max(size); d = 2.2 * L; el = math.radians(22)
    for az in (0, 90, 180, 270):
        r = math.radians(az)
        look(cam, (0, 0, size[2] / 2), (d * math.cos(el) * math.sin(r), -d * math.cos(el) * math.cos(r), size[2] / 2 + d * math.sin(el)))
        sc.render.filepath = f"{out}/{a['id']}_az{az}.png"; bpy.ops.render.render(write_still=True)
    if a.get("koi"):
        s = 0.6 / L
        for o in new:
            if o.parent is None:
                o.scale *= s; o.location *= s
        bpy.context.view_layer.update()
        g.location.z = -0.0
        # water-ish dark ground for contrast
        gm.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.05, 0.12, 0.12, 1)
        zc = size[2] * s / 2
        look(cam, (0, 0, zc), (0, -1.5 * math.cos(math.radians(55)), zc + 1.5 * math.sin(math.radians(55))))
        sc.render.filepath = f"{out}/{a['id']}_koi15.png"; bpy.ops.render.render(write_still=True)
json.dump(res, open(f"{out}/stats.json", "w"), indent=1)
