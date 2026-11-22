"""Blender (headless) preview of a garden Scene spec. Not importable outside Blender.

    blender -b --factory-startup --python-exit-code 1 -P preview_blender.py -- spec.json OUT_DIR TAG

Writes OUT_DIR/TAG-<view>.jpg for each view and OUT_DIR/TAG.receipt.json (measured placement of every drawn asset).
Materials are procedural and chosen by the part's material name; they are stated finishes for a PREVIEW, not product data.
"""
import json
import math
import sys
import zlib

import bmesh
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
spec = json.load(open(argv[0]))
OUT, TAG = argv[1], argv[2]
G = spec["ground_z"]
MATS = {}


def principled(m):
    return m.node_tree.nodes["Principled BSDF"]


def noise_bump(m, scale, strength, detail=8.0):
    nt = m.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord"); n = nt.nodes.new("ShaderNodeTexNoise"); b = nt.nodes.new("ShaderNodeBump")
    n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = detail
    b.inputs["Strength"].default_value = strength
    nt.links.new(tc.outputs["Object"], n.inputs["Vector"]); nt.links.new(n.outputs["Fac"], b.inputs["Height"])
    nt.links.new(b.outputs["Normal"], principled(m).inputs["Normal"])
    return n


def colour_noise(m, scale, c1, c2):
    nt = m.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord"); n = nt.nodes.new("ShaderNodeTexNoise"); r = nt.nodes.new("ShaderNodeMixRGB")
    n.inputs["Scale"].default_value = scale
    r.inputs[1].default_value = (*c1, 1); r.inputs[2].default_value = (*c2, 1)
    nt.links.new(tc.outputs["Object"], n.inputs["Vector"]); nt.links.new(n.outputs["Fac"], r.inputs[0])
    nt.links.new(r.outputs["Color"], principled(m).inputs["Base Color"])


SPEC = {  # name: (base colour, roughness, metallic)
    "paving-joint": ((0.22, 0.21, 0.19), 0.95, 0), "path-unit": ((0.50, 0.46, 0.40), 0.75, 0), "bed-soil": ((0.16, 0.11, 0.07), 1.0, 0),
    "wall-render": ((0.82, 0.80, 0.75), 0.9, 0), "trellis-timber": ((0.40, 0.28, 0.17), 0.7, 0), "pergola-alu": ((0.09, 0.075, 0.065), 0.35, 0.8),
    "table-timber": ((0.40, 0.26, 0.14), 0.6, 0), "chair-timber": ((0.45, 0.30, 0.17), 0.6, 0), "seat-timber": ((0.40, 0.26, 0.14), 0.6, 0),
    "terracotta": ((0.60, 0.28, 0.16), 0.8, 0), "pond-concrete": ((0.05, 0.06, 0.055), 0.9, 0), "pond-edge": ((0.06, 0.06, 0.065), 0.5, 0),
    "grille-steel": ((0.18, 0.18, 0.19), 0.4, 0.9), "pit-steel": ((0.10, 0.10, 0.10), 0.5, 0.8), "lava-rock": ((0.05, 0.045, 0.045), 1.0, 0),
    "burner": ((0.15, 0.15, 0.15), 0.4, 0.9), "bbq-steel": ((0.04, 0.04, 0.04), 0.45, 0.6), "ctx": ((0.80, 0.79, 0.77), 0.95, 0),
    "ground-far": ((0.50, 0.44, 0.34), 1.0, 0),
}


def mat(name):
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = principled(m)
    base = name.split("#")[0]
    if base.startswith("standin:"):
        c = tuple(float(x) for x in base[8:].split(","))
        b.inputs["Base Color"].default_value = (*c, 1); b.inputs["Roughness"].default_value = 0.7
        noise_bump(m, 90.0, 0.6, 10)
    elif base == "paving-unit":
        tones = [(0.60, 0.58, 0.54), (0.55, 0.53, 0.49), (0.64, 0.61, 0.56)]
        c = tones[int(name.split("#")[1])] if "#" in name else tones[0]
        b.inputs["Base Color"].default_value = (*c, 1); b.inputs["Roughness"].default_value = 0.72
        noise_bump(m, 60.0, 0.05)
    elif base == "cover-top":
        b.inputs["Base Color"].default_value = (0.55, 0.53, 0.49, 1); b.inputs["Roughness"].default_value = 0.72
    elif base == "gravel":
        n = noise_bump(m, 400.0, 0.9, 4); colour_noise(m, 220.0, (0.42, 0.38, 0.31), (0.66, 0.61, 0.52)); b.inputs["Roughness"].default_value = 0.95
    elif base == "ground":
        colour_noise(m, 12.0, (0.40, 0.34, 0.26), (0.52, 0.45, 0.35)); b.inputs["Roughness"].default_value = 1.0; noise_bump(m, 120.0, 0.5)
    elif base == "water":
        b.inputs["Base Color"].default_value = (0.04, 0.10, 0.08, 1); b.inputs["Roughness"].default_value = 0.03
        for k, v in (("Transmission Weight", 0.92), ("IOR", 1.333)):
            b.inputs[k].default_value = v
    elif base == "flame":
        b.inputs["Base Color"].default_value = (1, 0.4, 0.05, 1)
        b.inputs["Emission Color"].default_value = (1.0, 0.35, 0.05, 1); b.inputs["Emission Strength"].default_value = 25.0
    elif base in SPEC:
        c, r, mt = SPEC[base]
        b.inputs["Base Color"].default_value = (*c, 1); b.inputs["Roughness"].default_value = r; b.inputs["Metallic"].default_value = mt
        if base in ("wall-render",):
            noise_bump(m, 200.0, 0.15)
        if base in ("trellis-timber", "table-timber", "chair-timber", "seat-timber"):
            n = noise_bump(m, 25.0, 0.1)
    else:
        raise KeyError("no material for part %r" % name)
    MATS[name] = m
    return m


def mesh_object(name, parts, smooth=False):
    verts, faces, midx, slots = [], [], [], []
    for p in parts:
        if p["material"] not in slots:
            slots.append(p["material"])
        o = len(verts)
        verts += [tuple(v) for v in p["verts"]]
        for f in p["faces"]:
            faces.append([o + i for i in f]); midx.append(slots.index(p["material"]))
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces)
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me); bm.free()
    for s in slots:
        me.materials.append(mat(s))
    for pl, mi in zip(me.polygons, midx):
        pl.material_index = mi; pl.use_smooth = smooth
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def world_bbox(objs):
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for o in objs:
        if o.type != "MESH":
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    return lo, hi


def place_asset(a, name):
    """Import the glTF, scale to the target height, put the base centroid on (x, y) and the foot on base_z. Returns measured receipt."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=a["gltf"])
    new = [o for o in bpy.data.objects if o not in before]
    roots = [o for o in new if o.parent is None]
    bpy.context.view_layer.update()
    lo, hi = world_bbox(new)
    target_h = a["bounds"][5] - a["bounds"][2]
    s = target_h / (hi.z - lo.z)
    # restrained assets (pots beside walls): the layout bounds carry the allowed footprint
    for o in roots:
        o.scale = o.scale * s
    bpy.context.view_layer.update()
    lo, hi = world_bbox(new)
    # base centroid: mean of the lowest 5 % of vertices (trunk or stem position)
    pts = []
    for o in new:
        if o.type == "MESH":
            for v in o.data.vertices:
                w = o.matrix_world @ v.co
                if w.z < lo.z + 0.05 * (hi.z - lo.z):
                    pts.append(w)
    cx = sum(p.x for p in pts) / len(pts); cy = sum(p.y for p in pts) / len(pts)
    d = Vector((a["at"][0] - cx, a["at"][1] - cy, a["at"][2] - lo.z))
    for o in roots:
        o.location = o.location + d
        o["ld_id"] = name
    bpy.context.view_layer.update()
    lo, hi = world_bbox(new)
    return new, dict(asset=a["asset_id"], target_height_m=target_h, measured_min=[round(x, 4) for x in lo], measured_max=[round(x, 4) for x in hi],
                     base_z_error_m=round(lo.z - a["at"][2], 4), height_m=round(hi.z - lo.z, 4), spread_m=round(max(hi.x - lo.x, hi.y - lo.y), 4))


bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.samples = spec.get("samples", 96); sc.cycles.use_denoising = True
sc.cycles.max_bounces = 8; sc.cycles.transmission_bounces = 8
sc.render.resolution_x, sc.render.resolution_y = spec["size"]
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "None"; sc.view_settings.exposure = spec.get("exposure", -0.5)
sc.render.image_settings.file_format = "JPEG"; sc.render.image_settings.quality = 90
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "CUDA"; prefs.get_devices()
    for d in prefs.devices:
        d.use = d.type == "CUDA"
    sc.cycles.device = "GPU"
except Exception as e:
    print("GPU not available:", e)

w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
nt = w.node_tree
sky = nt.nodes.new("ShaderNodeTexSky"); sky.sky_type = "NISHITA"
sky.sun_elevation = math.radians(52); sky.sun_rotation = math.radians(210); sky.sun_size = math.radians(0.6); sky.air_density = 1.0; sky.dust_density = 1.5; sky.sun_intensity = spec.get("sun_intensity", 0.45)
nt.links.new(sky.outputs["Color"], nt.nodes["Background"].inputs["Color"]); nt.nodes["Background"].inputs["Strength"].default_value = 1.0

receipt = dict(tag=TAG, assets=[], views=[], objects=0, note="preview scene: Nishita sky at a fixed 52 deg elevation, AgX, not exposure-locked; placeholder site (docs: garden is NOT a production render)")
for o in spec["objects"]:
    name = o["id"] if not o["state"] else "%s@%s" % (o["id"], o["state"])
    ob = None
    if o.get("parts"):
        ob = mesh_object(name, o["parts"], smooth=o["kind"] in ("plant", "flame"))
        objs = [ob]
    elif o.get("asset"):
        objs, rec = place_asset(o["asset"], o["id"])
        rec["id"] = o["id"]; receipt["assets"].append(rec)
    else:
        continue
    for x in objs:
        x["ld_id"] = o["id"]; x["ld_kind"] = o["kind"]; x["ld_state"] = o["state"] or ""
    o["_blender"] = [x.name for x in objs]
    receipt["objects"] += 1
for c in spec["context"]:
    x0, y0, x1, y1 = c["rect"]
    ob = mesh_object(c["id"], [dict(material="ctx", verts=[[x0, y0, c["z0"]], [x1, y0, c["z0"]], [x1, y1, c["z0"]], [x0, y1, c["z0"]], [x0, y0, c["z1"]], [x1, y0, c["z1"]], [x1, y1, c["z1"]], [x0, y1, c["z1"]]],
                      faces=[[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]])])
    ob["ld_id"] = c["id"]; ob["ld_context"] = True
# far ground, a little below the surfaces so nothing z-fights
mesh_object("ctx-ground", [dict(material="ground-far", verts=[[-60, -80, G - 0.06], [80, -80, G - 0.06], [80, 40, G - 0.06], [-60, 40, G - 0.06]], faces=[[0, 1, 2, 3]])])

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.sensor_width = 36; cam.data.clip_start = 0.05; cam.data.clip_end = 300
for v in spec["views"]:
    for o in spec["objects"]:
        for n in o.get("_blender", []):
            bpy.data.objects[n].hide_render = bool(o["state"]) and o["state"] != v["state"]
    for ob in bpy.data.objects:                       # the house box is hidden from the camera (not from light) in bird's-eye views so the garden is legible
        if ob.get("ld_context") and ob.name.startswith("ctx-building"):
            ob.visible_camera = ob.visible_shadow = not v.get("hide_house", False)
    cam.data.lens = v["lens"]
    cam.location = Vector(v["eye"])
    cam.rotation_euler = (Vector(v["target"]) - cam.location).to_track_quat("-Z", "Y").to_euler()
    path = "%s/%s-%s.jpg" % (OUT, TAG, v["name"])
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    receipt["views"].append(dict(name=v["name"], file=path, state=v["state"], eye=v["eye"], target=v["target"], lens=v["lens"]))
json.dump(receipt, open("%s/%s.receipt.json" % (OUT, TAG), "w"), indent=1)
