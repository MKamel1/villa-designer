"""L6b truth-question probe: Cycles direct illuminance at the D1 dining-table points, with controlled variants.

Run inside Blender (4.5):  blender -b -P truth_probe_blender.py -- CASES.json OUT.json
Reuses the production light constructor (archpipe.blender.villa_scene.add_light) and the production sensor method
(0.5-reflectance 4 cm plane 1 mm above the point, 20 mm ortho camera 25 mm over it, 0 bounces for direct, central 16x16 of
32x32, radiance * pi / 0.5). A case is {"name", "lights": [scene.json light specs], "ies_dir", "table_top_z",
"vase": null | {"position": [x,y,z], "asset_dir"}, "pendant": null | {...}, "points": [[x,y,z], ...], "mf": 0.8}.
Writes {case: [{point, direct_lux}]}. Nothing here edits the pipeline.
"""
import json
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.environ.get("ARCHPIPE_SRC", "src"))
from archpipe.blender import villa_scene as VS  # noqa: E402


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def diffuse_mat(name, rho):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    d = nt.nodes.new("ShaderNodeBsdfDiffuse")
    d.inputs["Color"].default_value = (rho, rho, rho, 1)
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(d.outputs[0], o.inputs["Surface"])
    return m


def box(name, x0, y0, z0, x1, y1, z1, rho=0.2):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.object
    o.name = name
    o.scale = (x1 - x0, y1 - y0, z1 - z0)
    o.location = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    o.data.materials.append(diffuse_mat(name, rho))
    return o


def emissive_strip(name, x0, x1, yc, w, z, exitance_lm_m2):
    """A downward-facing Lambertian strip (production: strength = exitance / pi)."""
    bpy.ops.mesh.primitive_plane_add(size=1)
    o = bpy.context.object
    o.name = name
    o.scale = (x1 - x0, w, 1)
    o.location = ((x0 + x1) / 2, yc, z)
    o.rotation_euler = (math.pi, 0, 0)          # normal down
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Strength"].default_value = exitance_lm_m2 / math.pi
    o_ = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(e.outputs[0], o_.inputs["Surface"])
    o.data.materials.append(m)
    return o


def import_vase(spec):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(spec["asset_dir"], "model.gltf"))
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == "MESH"]
    anchor = bpy.data.objects.new("vase-anchor", None)
    bpy.context.collection.objects.link(anchor)
    for o in new:
        if o.parent is None:
            o.parent = anchor
    anchor.location = (spec["position"][0], spec["position"][1], 0)
    bpy.context.view_layer.update()
    bottom = min((o.matrix_world @ Vector(c)).z for o in meshes for c in o.bound_box)
    anchor.location.z += spec["position"][2] - bottom
    bpy.context.view_layer.update()
    lo = [min((o.matrix_world @ Vector(c))[i] for o in meshes for c in o.bound_box) for i in range(3)]
    hi = [max((o.matrix_world @ Vector(c))[i] for o in meshes for c in o.bound_box) for i in range(3)]
    return lo, hi


def luminance(rgb):
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


def run_case(case, workdir):
    clear()
    s = bpy.context.scene
    s.render.engine = "CYCLES"
    s.cycles.device = "CPU"
    top = case["table_top_z"]
    cx, cy = 16.95, -25.9
    box("table", cx - 0.9, cy - 0.45, top - 0.12, cx + 0.9, cy + 0.45, top)
    info = {}
    for spec in case["lights"]:
        VS.add_light(spec, case["ies_dir"])
    mf = case.get("mf", 0.8)
    for o in bpy.data.objects:
        if o.type == "LIGHT":
            o.data.energy *= mf
    if case.get("vase"):
        info["vase_bbox"] = import_vase(case["vase"])
    if case.get("pendant"):
        p = case["pendant"]
        emissive_strip("pendant", p["x0"], p["x1"], p["y"], p["w"], p["z"], p["exitance"] * mf)
    world = bpy.data.worlds.new("black")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0
    s.world = world
    s.cycles.use_denoising = False
    s.cycles.samples = 256
    s.cycles.max_bounces = 0
    s.render.resolution_x = s.render.resolution_y = 32
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = "OPEN_EXR"
    s.render.image_settings.color_depth = "32"
    s.view_settings.view_transform = "Standard"
    s.view_settings.look = "None"
    sensor_mat = diffuse_mat("sensor", 0.5)
    bpy.ops.mesh.primitive_plane_add(size=0.04)
    sensor = bpy.context.object
    sensor.data.materials.append(sensor_mat)
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = 0.02
    cam_data.clip_start = 0.001
    cam_data.clip_end = 0.1
    cam = bpy.data.objects.new("cam", cam_data)
    bpy.context.collection.objects.link(cam)
    s.camera = cam
    out = []
    for i, (x, y, z) in enumerate(case["points"]):
        sensor.location = (x, y, z + 0.001)
        cam.location = (x, y, z + 0.025)
        path = os.path.join(workdir, "%s-%02d.exr" % (case["name"], i))
        s.render.filepath = path
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(path)
        px = img.pixels[:]
        vals = [luminance(px[4 * (yy * 32 + xx):4 * (yy * 32 + xx) + 3]) for yy in range(8, 24) for xx in range(8, 24)]
        out.append({"point": [x, y, z], "direct_lux": sum(vals) / len(vals) * math.pi / 0.5})
        bpy.data.images.remove(img)
    return {"readings": out, **info}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    cases = json.load(open(argv[0]))
    os.makedirs(os.path.dirname(os.path.abspath(argv[1])), exist_ok=True)
    wd = os.path.join(os.path.dirname(os.path.abspath(argv[1])), "exr")
    os.makedirs(wd, exist_ok=True)
    res = {c["name"]: run_case(c, wd) for c in cases}
    json.dump(res, open(argv[1], "w"), indent=1)


main()
