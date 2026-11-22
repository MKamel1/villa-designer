"""Blender (headless) preview of a garden Scene spec. Not importable outside Blender.

    blender -b --factory-startup --python-exit-code 1 -P preview_blender.py -- spec.json OUT_DIR TAG

Writes OUT_DIR/TAG-<view>.jpg for each view and OUT_DIR/TAG.receipt.json (measured placement of every drawn asset).
Materials are procedural and chosen by the part's material name; they are stated finishes for a PREVIEW, not product data.
"""
import json
import math
import sys
import zlib

import os

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fab_blender  # noqa: E402

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
    "grille-steel": ((0.025, 0.025, 0.028), 0.5, 0.6), "pit-steel": ((0.10, 0.10, 0.10), 0.5, 0.8), "lava-rock": ((0.05, 0.045, 0.045), 1.0, 0),
    "burner": ((0.15, 0.15, 0.15), 0.4, 0.9), "bbq-steel": ((0.04, 0.04, 0.04), 0.45, 0.6), "ctx": ((0.80, 0.79, 0.77), 0.95, 0),
    "ground-far": ((0.50, 0.44, 0.34), 1.0, 0), "ground-neutral": ((0.36, 0.36, 0.35), 1.0, 0), "ctx-street": ((0.13, 0.13, 0.135), 0.9, 0), "root-barrier": ((0.08, 0.08, 0.09), 0.6, 0),
    "trunk-bark": ((0.20, 0.15, 0.11), 0.95, 0),
}
SEASON = spec.get("season", "summer")


def climber_material(m, base, bare):
    """Leaf-cutout panel (procedural, a STAND-IN look): a Voronoi blob mask makes leaves, a noise mask makes holes; bare = a sparse twig network (winter)."""
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    vo = nt.nodes.new("ShaderNodeTexVoronoi"); vo.voronoi_dimensions = "3D"; vo.inputs["Scale"].default_value = 26.0
    no = nt.nodes.new("ShaderNodeTexNoise"); no.inputs["Scale"].default_value = 3.2; no.inputs["Detail"].default_value = 4.0
    cr = nt.nodes.new("ShaderNodeValToRGB")
    ncr = nt.nodes.new("ShaderNodeValToRGB")
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    pb = nt.nodes.new("ShaderNodeBsdfPrincipled")
    mix = nt.nodes.new("ShaderNodeMixShader")
    cvar = nt.nodes.new("ShaderNodeTexNoise"); cvar.inputs["Scale"].default_value = 18.0
    cc = nt.nodes.new("ShaderNodeMixRGB")
    wp = nt.nodes.new("ShaderNodeTexNoise"); wp.inputs["Scale"].default_value = 2.5; wp.inputs["Detail"].default_value = 1.0       # domain warp: organic, not a regular cell pattern
    vm = nt.nodes.new("ShaderNodeVectorMath"); vm.operation = "MULTIPLY_ADD"; vm.inputs[1].default_value = (0.35, 0.35, 0.35)
    nt.links.new(tc.outputs["Object"], wp.inputs["Vector"]); nt.links.new(wp.outputs["Color"], vm.inputs[0]); nt.links.new(tc.outputs["Object"], vm.inputs[2])
    nt.links.new(vm.outputs["Vector"], vo.inputs["Vector"]); nt.links.new(tc.outputs["Object"], no.inputs["Vector"]); nt.links.new(tc.outputs["Object"], cvar.inputs["Vector"])
    if bare:
        vo.feature = "DISTANCE_TO_EDGE"; vo.inputs["Scale"].default_value = 7.0
        cr.color_ramp.elements[0].position = 0.0; cr.color_ramp.elements[0].color = (1, 1, 1, 1)
        cr.color_ramp.elements[1].position = 0.035; cr.color_ramp.elements[1].color = (0, 0, 0, 1)
        nt.links.new(vo.outputs["Distance"], cr.inputs["Fac"])
        ncr.color_ramp.elements[0].position = 0.30; ncr.color_ramp.elements[1].position = 0.40
        c1, c2 = (0.07, 0.045, 0.03), (0.16, 0.11, 0.07)
    else:
        vo.feature = "F1"
        cr.color_ramp.elements[0].position = 0.0; cr.color_ramp.elements[0].color = (1, 1, 1, 1)
        cr.color_ramp.elements[1].position = 0.62; cr.color_ramp.elements[1].color = (0, 0, 0, 1)
        nt.links.new(vo.outputs["Distance"], cr.inputs["Fac"])
        ncr.color_ramp.elements[0].position = 0.20; ncr.color_ramp.elements[1].position = 0.34      # holes where the noise is low
        c1, c2 = tuple(0.55 * x for x in base), tuple(min(1.0, 1.25 * x) for x in base)
    nt.links.new(no.outputs["Fac"], ncr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], mul.inputs[0]); nt.links.new(ncr.outputs["Color"], mul.inputs[1])
    cc.inputs[1].default_value = (*c1, 1); cc.inputs[2].default_value = (*c2, 1)
    nt.links.new(cvar.outputs["Fac"], cc.inputs[0]); nt.links.new(cc.outputs["Color"], pb.inputs["Base Color"])
    pb.inputs["Roughness"].default_value = 0.55
    nt.links.new(mul.outputs["Value"], mix.inputs["Fac"]); nt.links.new(tr.outputs["BSDF"], mix.inputs[1]); nt.links.new(pb.outputs["BSDF"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])



def mat(name):
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = principled(m)
    base = name.split("#")[0]
    if base.startswith("climber:") or base.startswith("leafcut:"):     # leafcut: = foliage clumps of a stand-in tree (always leafed; a deciduous tree's bare state is its own geometry)
        kind, col, hab = base.split(":")
        climber_material(m, tuple(float(x) for x in col.split(",")), kind == "climber" and SEASON == "winter" and hab == "d")
    elif base.startswith("atlas:"):
        _, path, col = base.split(":", 2)
        nt = m.node_tree
        im = nt.nodes.new("ShaderNodeTexImage"); im.image = bpy.data.images.load(path)
        nt.links.new(im.outputs["Color"], principled(m).inputs["Base Color"]); nt.links.new(im.outputs["Alpha"], principled(m).inputs["Alpha"])
    elif base.startswith("standin:"):
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
        # a SURFACE (top face only): mostly transparent, a Fresnel-weighted glossy reflection with a ripple. The depth tint lives in the liner below (pond-liner), so there is no
        # glass block, no refracted caustic noise and no mirror slab; at a steep view the bottom shows through, at a low view the sky and walls reflect, as real water does.
        nt = m.node_tree
        for n in list(nt.nodes):
            nt.nodes.remove(n)
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        tr = nt.nodes.new("ShaderNodeBsdfTransparent"); tr.inputs["Color"].default_value = (0.80, 0.93, 0.90, 1)
        gl = nt.nodes.new("ShaderNodeBsdfGlossy"); gl.inputs["Roughness"].default_value = 0.04
        fr = nt.nodes.new("ShaderNodeFresnel"); fr.inputs["IOR"].default_value = 1.333
        mx = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(fr.outputs["Fac"], mx.inputs["Fac"]); nt.links.new(tr.outputs["BSDF"], mx.inputs[1]); nt.links.new(gl.outputs["BSDF"], mx.inputs[2])
        nt.links.new(mx.outputs["Shader"], out.inputs["Surface"])
        tc = nt.nodes.new("ShaderNodeTexCoord"); w1 = nt.nodes.new("ShaderNodeTexNoise"); w1.inputs["Scale"].default_value = 7.0; w1.inputs["Detail"].default_value = 3.0
        bm = nt.nodes.new("ShaderNodeBump"); bm.inputs["Strength"].default_value = 0.22; bm.inputs["Distance"].default_value = 0.01
        nt.links.new(tc.outputs["Object"], w1.inputs["Vector"]); nt.links.new(w1.outputs["Fac"], bm.inputs["Height"])
        nt.links.new(bm.outputs["Normal"], gl.inputs["Normal"]); nt.links.new(bm.outputs["Normal"], fr.inputs["Normal"])
    elif base == "pond-liner":
        # wet liner: lighter on the shelf and entry slope, darker and greener with depth (the depth tint of the water)
        nt = m.node_tree
        gp = nt.nodes.new("ShaderNodeNewGeometry"); sp = nt.nodes.new("ShaderNodeSeparateXYZ"); mr = nt.nodes.new("ShaderNodeMapRange"); cr = nt.nodes.new("ShaderNodeValToRGB")
        lo, hi = (spec.get("water_range") or [G - 1.05, G - 0.15])
        mr.inputs["From Min"].default_value = lo; mr.inputs["From Max"].default_value = hi
        cr.color_ramp.elements[0].position = 0.0; cr.color_ramp.elements[0].color = (0.015, 0.045, 0.045, 1)
        cr.color_ramp.elements[1].position = 1.0; cr.color_ramp.elements[1].color = (0.20, 0.34, 0.29, 1)
        nt.links.new(gp.outputs["Position"], sp.inputs["Vector"]); nt.links.new(sp.outputs["Z"], mr.inputs["Value"]); nt.links.new(mr.outputs["Result"], cr.inputs["Fac"])
        nt.links.new(cr.outputs["Color"], principled(m).inputs["Base Color"]); principled(m).inputs["Roughness"].default_value = 0.6
        noise_bump(m, 40.0, 0.3, 4)
    elif base == "flame":
        b.inputs["Base Color"].default_value = (1, 0.4, 0.05, 1)
        b.inputs["Emission Color"].default_value = (1.0, 0.35, 0.05, 1); b.inputs["Emission Strength"].default_value = 25.0
    elif base in SPEC:
        c, r, mt = SPEC[base]
        b.inputs["Base Color"].default_value = (*c, 1); b.inputs["Roughness"].default_value = r; b.inputs["Metallic"].default_value = mt
        if base == "trunk-bark":
            noise_bump(m, 60.0, 0.6)
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


def _import(gltf):
    if gltf.lower().endswith(".fbx"):                 # Fab / Megascans plant: FBX + the archive's own maps (red-channel opacity)
        new = fab_blender.import_fbx(gltf)
    else:
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=gltf)
        new = [o for o in bpy.data.objects if o not in before]
    roots = [o for o in new if o.parent is None]
    e = bpy.data.objects.new("ld-asset-root", None); bpy.context.scene.collection.objects.link(e)
    for o in roots:                                   # one wrapper empty: a non-uniform scale and the yaw act in WORLD axes, whatever rotation the glTF roots carry
        o.parent = e; o.matrix_parent_inverse = e.matrix_world.inverted()
    bpy.context.view_layer.update()
    return new + [e], e


def _place_one(gltf, mode, at, target_h=None, scale_xyz=None, box_m=None, length=None, yaw=0.0):
    """Import, scale (mode height | xyz | box | fish), yaw, put the foot (fish: the bbox centre) on `at`. Returns (objects, measured dict)."""
    new, e = _import(gltf)
    lo, hi = world_bbox(new)
    nat = hi - lo
    if mode == "height":
        u = target_h / nat.z; sv = (u, u, u)
    elif mode == "xyz":
        sv = tuple(scale_xyz)
    elif mode == "box":
        sv = (box_m[0] / nat.x, box_m[1] / nat.y, box_m[2] / nat.z)
    elif mode == "fish":
        u = length / max(nat.x, nat.y, nat.z); sv = (u, u, u)
    else:
        raise ValueError(mode)
    e.scale = sv; e.rotation_euler = (0, 0, math.radians(yaw))
    bpy.context.view_layer.update()
    lo, hi = world_bbox(new)
    if mode == "fish":
        c = (lo + hi) / 2
        d = Vector((at[0] - c.x, at[1] - c.y, at[2] - c.z))
    else:
        pts = []                                       # base centroid: mean of the lowest 5 % of vertices (trunk, stem or leg position)
        for o in new:
            if o.type == "MESH":
                for v in o.data.vertices:
                    w = o.matrix_world @ v.co
                    if w.z < lo.z + 0.05 * (hi.z - lo.z):
                        pts.append(w)
        d = Vector((at[0] - sum(p.x for p in pts) / len(pts), at[1] - sum(p.y for p in pts) / len(pts), at[2] - lo.z))
    e.location = d
    bpy.context.view_layer.update()
    lo, hi = world_bbox(new)
    return new, dict(native_m=[round(x, 4) for x in nat], scale=[round(x, 4) for x in sv], measured_min=[round(x, 4) for x in lo], measured_max=[round(x, 4) for x in hi],
                     base_z_error_m=round(lo.z - at[2], 4), centre_z_error_m=round((lo.z + hi.z) / 2 - at[2], 4), height_m=round(hi.z - lo.z, 4), spread_m=round(max(hi.x - lo.x, hi.y - lo.y), 4))


def place_asset(a, name):
    mode = a.get("mode", "height")
    if mode == "tiles":
        allobjs, recs = [], []
        for t in a["tiles"]:
            o, r = _place_one(a["gltf"], "xyz", t["at"], scale_xyz=t["scale_xyz"], yaw=t.get("yaw_deg", 0.0))
            allobjs += o; recs.append(r)
        lo = [min(r["measured_min"][i] for r in recs) for i in range(3)]; hi = [max(r["measured_max"][i] for r in recs) for i in range(3)]
        return allobjs, dict(asset=a["asset_id"], tiles=len(recs), measured_min=lo, measured_max=hi, base_z_error_m=round(min(r["base_z_error_m"] for r in recs), 4),
                             target_height_m=a["bounds"][5] - a["bounds"][2], height_m=round(hi[2] - lo[2], 4), spread_m=round(max(hi[0] - lo[0], hi[1] - lo[1]), 4))
    th = a["bounds"][5] - a["bounds"][2]
    o, r = _place_one(a["gltf"], mode, a["at"], target_h=th, scale_xyz=a.get("scale_xyz"), box_m=a.get("box_m"), length=a.get("length_m"), yaw=a.get("yaw_deg", 0.0))
    r.update(asset=a["asset_id"], target_height_m=th, mode=mode)
    return o, r


bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.samples = spec.get("samples", 96); sc.cycles.use_denoising = True
sc.cycles.max_bounces = 8; sc.cycles.transparent_max_bounces = 32; sc.cycles.transmission_bounces = 8; sc.cycles.caustics_reflective = False; sc.cycles.caustics_refractive = False; sc.cycles.sample_clamp_indirect = 8.0
sc.render.resolution_x, sc.render.resolution_y = spec["size"]
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "None"; sc.view_settings.exposure = spec.get("exposure", -2.0)
sc.render.image_settings.file_format = "JPEG"; sc.render.image_settings.quality = 90
try:
    if spec.get("device") == "CPU":
        raise RuntimeError("cpu requested")
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
sky.sun_elevation = math.radians(52); sky.sun_rotation = math.radians(210); sky.sun_size = math.radians(0.6); sky.air_density = 1.0; sky.dust_density = 1.5; sky.sun_intensity = spec.get("sun_intensity", 0.4)
nt.links.new(sky.outputs["Color"], nt.nodes["Background"].inputs["Color"]); nt.nodes["Background"].inputs["Strength"].default_value = 1.0

receipt = dict(tag=TAG, spec_sha=spec.get("spec_sha"), assets=[], views=[], objects=0, note="preview scene: Nishita sky at a fixed 52 deg elevation, AgX, not exposure-locked; placeholder site (docs: garden is NOT a production render)")
for o in spec["objects"]:
    name = o["id"] if not o["state"] else "%s@%s" % (o["id"], o["state"])
    ob = None
    if o.get("parts"):
        ob = mesh_object(name, o["winter_parts"] if (o.get("winter_parts") and SEASON == "winter") else o["parts"], smooth=o["kind"] in ("plant", "flame"))
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
    ob = mesh_object(c["id"], [dict(material=c.get("material", "ctx"), verts=[[x0, y0, c["z0"]], [x1, y0, c["z0"]], [x1, y1, c["z0"]], [x0, y1, c["z0"]], [x0, y0, c["z1"]], [x1, y0, c["z1"]], [x1, y1, c["z1"]], [x0, y1, c["z1"]]],
                      faces=[[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]])])
    ob["ld_id"] = c["id"]; ob["ld_context"] = True
# far ground, a little below the surfaces so nothing z-fights; cells over a pond opening are left out (a plane under the rim would bury the pond)
gv, gf = [], []
for x0_, y0_, x1_, y1_ in spec["ground_quads"]:
    k = len(gv)
    gv += [[x0_, y0_, G - 0.06], [x1_, y0_, G - 0.06], [x1_, y1_, G - 0.06], [x0_, y1_, G - 0.06]]
    gf.append([k, k + 1, k + 2, k + 3])
mesh_object("ctx-ground", [dict(material="ground-far", verts=gv, faces=gf)])
nv_, nf_ = [], []
for x0_, y0_, x1_, y1_ in spec.get("neutral_quads", []):
    k = len(nv_)
    nv_ += [[x0_, y0_, G - 0.06], [x1_, y0_, G - 0.06], [x1_, y1_, G - 0.06], [x0_, y1_, G - 0.06]]
    nf_.append([k, k + 1, k + 2, k + 3])
if nf_:
    mesh_object("ctx-ground-neutral", [dict(material="ground-neutral", verts=nv_, faces=nf_)])

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.sensor_width = 36; cam.data.clip_start = 0.05; cam.data.clip_end = 300
for v in spec["views"]:
    for o in spec["objects"]:
        for n in o.get("_blender", []):
            bpy.data.objects[n].hide_render = bool(o["state"]) and o["state"] != v["state"]
    for ob in bpy.data.objects:                       # the house box is hidden from the camera (not from light) in bird's-eye views so the garden is legible
        if ob.get("ld_context") and ob.name.startswith("ctx-building"):
            ob.visible_camera = ob.visible_shadow = not v.get("hide_house", False)
    sc.view_settings.exposure = spec.get("exposure_by_group", {}).get(v.get("group"), spec.get("exposure", -2.0))
    cam.data.lens = v["lens"]
    cam.location = Vector(v["eye"])
    cam.rotation_euler = (Vector(v["target"]) - cam.location).to_track_quat("-Z", "Y").to_euler()
    path = "%s/%s-%s.jpg" % (OUT, TAG, v["name"])
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    receipt["views"].append(dict(name=v["name"], file=path, state=v["state"], eye=v["eye"], target=v["target"], lens=v["lens"], group=v.get("group"), exposure=sc.view_settings.exposure))
json.dump(receipt, open("%s/%s.receipt.json" % (OUT, TAG), "w"), indent=1)
