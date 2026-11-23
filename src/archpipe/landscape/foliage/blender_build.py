"""Blender (headless) builder for generated plants: `build_plant(plant)` -> objects; sheet renderer; glb export.

    blender -b --python-exit-code 1 -P blender_build.py -- sheet --out DIR --spec "slug:seed:H:S:state[:lod]" [--spec ...]
    blender -b --python-exit-code 1 -P blender_build.py -- glb   --out DIR --spec ...

Run through ~/archpipe/bin/jobq submit --gpu (docs/lanes/L8-runner.md). Leaf material: the scan's BaseColor x per-leaf
tint (vertex colour), Opacity read from the RED channel (Megascans single-channel maps), Roughness/Gloss, Normal, and a
30 % translucent BSDF tinted by the base colour (two-sided leaf). Cards are bent (droop) and V-folded so no flat plane
shows at 5 m."""
import json
import math
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
from archpipe.landscape.foliage import generate as G          # noqa: E402
from archpipe.landscape.plants.megascans_mat import red, reset_scene, tex   # noqa: E402

BANKS = G.BANKS
_U = "/home/omar/archpipe/shared/assets/user/landscape"
# bark candidates: (diffuse, roughness, normal) per choice; FG_BARK selects (default = the choice recorded in docs/lanes/FG.md)
BARKS = {"platanus": tuple(_U + "/polyhaven-tex/bark_platanus/bark_platanus_%s_2k.jpg" % k for k in ("diff", "rough", "nor_gl")),
         "sakura": tuple(_U + "/polyhaven-tex/sakura_bark/sakura_bark_%s_2k.jpg" % k for k in ("diff", "rough", "nor_gl")),
         "banyan": tuple(_U + "/fab/unzipped/banyan_bark_tfhjaeju_4k/Banyan_Bark_tfhjaeju_4K_%s.jpg" % k for k in ("BaseColor", "Roughness", "Normal"))}
BARK_CHOICE = os.environ.get("FG_BARK", "platanus")
COLS, ROWS = 3, 5
RGBA = "/home/omar/archpipe/shared/assets/generated/foliage/atlas/rgba_%s.png"


# ------------------------------------------------------------------ meshes
def leaf_mesh(plant, bank):
    """One mesh of every leaf card of `bank`: ROWS x COLS grid per leaf following the bent centre line."""
    L = plant.leaves
    idx = [i for i, b in enumerate(L["bank"]) if b == bank]
    if not idx:
        return None
    recs = BANKS[bank]["leaves"]
    V, UV, C, F = [], [], [], []
    for n, i in enumerate(idx):
        r = recs[L["leaf"][i]]
        d, base, length, wid, arch = L["dir"][i], L["base"][i], L["length"][i], L["width"][i], L["arch"][i]
        cl = G.leaf_curve(base, d, length, arch, ROWS)
        tang = np.gradient(cl, axis=0)
        nrm0 = L["normal"][i]
        N = r.get("size_px", 4096)
        bp, ax = np.array(r["base_px"]), np.array(r["axis"])
        nv = np.array([-ax[1], ax[0]])
        for k in range(ROWS):
            t = k / (ROWS - 1)
            tg = G.unit(tang[k])
            side = G.unit(np.cross(tg, nrm0))
            nrm = G.unit(np.cross(side, tg))
            # a leaf is widest in the middle of its blade; the atlas outline carries that, the card spans the full width
            for j, s in enumerate((-1.0, 0.0, 1.0)):
                fold = 0.10 * wid * abs(s)                       # V-trough: edges lift
                V.append(cl[k] + side * s * wid * 0.5 * 1.06 + nrm * fold)
                px = bp + ax * t * r["len_px"] + nv * s * r["wid_px"] * 0.5 * 1.06
                UV.append((px[0] / N, 1 - px[1] / N))
                C.append(L["tint"][i] * (0.82 + 0.18 * t))      # base slightly darker (self-shadow in the clump)
        o = n * ROWS * COLS
        for k in range(ROWS - 1):
            for j in range(COLS - 1):
                a = o + k * COLS + j
                F.append((a, a + 1, a + 1 + COLS, a + COLS))
    me = bpy.data.meshes.new("leaves_" + bank)
    me.from_pydata(np.array(V).tolist(), [], F)
    uvl = me.uv_layers.new(name="UV")
    uv = np.array(UV)
    for li, lp in enumerate(me.loops):
        uvl.data[li].uv = uv[lp.vertex_index]
    ca = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
    col = np.array(C)
    for vi in range(len(me.vertices)):
        ca.data[vi].color = (*col[vi], 1.0)
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    return me


def tube_mesh(branches, sides_fn, bark_len=0.5):
    V, F, UV = [], [], []
    for b in branches:
        pts, rad = b["pts"], b["radii"]
        n = len(pts)
        if n < 2:
            continue
        k = sides_fn(rad[0])
        tg = np.gradient(pts, axis=0)
        ref = G.perp(G.unit(tg[0]))
        s = 0.0
        o = len(V)
        for i in range(n):
            t = G.unit(tg[i])
            ref = G.unit(ref - t * np.dot(ref, t))               # parallel transport: no twist
            bn = np.cross(t, ref)
            if i:
                s += np.linalg.norm(pts[i] - pts[i - 1])
            for j in range(k):
                a = 2 * math.pi * j / k
                V.append(pts[i] + (ref * math.cos(a) + bn * math.sin(a)) * rad[i])
                UV.append((j / k * min(1.0, 2 * math.pi * rad[0] / bark_len + 0.15), s / bark_len))
        for i in range(n - 1):
            for j in range(k):
                a = o + i * k + j; b2 = o + i * k + (j + 1) % k
                F.append((a, b2, b2 + k, a + k))
    if not V:
        return None
    me = bpy.data.meshes.new("wood")
    me.from_pydata(np.array(V).tolist(), [], F)
    uvl = me.uv_layers.new(name="UV")
    uv = np.array(UV)
    for li, lp in enumerate(me.loops):
        uvl.data[li].uv = uv[lp.vertex_index]
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    return me


# ------------------------------------------------------------------ materials
def leaf_material(bank, glossy=0.4):
    m = bpy.data.materials.new("leaf_" + bank); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); pb = nt.nodes.new("ShaderNodeBsdfPrincipled")
    mp = BANKS[bank]["maps"]
    bc = tex(nt, mp["BaseColor"], False, "BaseColor")
    at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "Col"
    mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs[0].default_value = 1.0
    nt.links.new(bc.outputs["Color"], mul.inputs[6]); nt.links.new(at.outputs["Color"], mul.inputs[7])
    nt.links.new(mul.outputs[2], pb.inputs["Base Color"])
    if "Roughness" in mp and os.path.exists(mp["Roughness"]):
        r = tex(nt, mp["Roughness"], True, "Roughness"); nt.links.new(red(nt, r), pb.inputs["Roughness"])
    else:
        pb.inputs["Roughness"].default_value = glossy
    if "Normal" in mp and os.path.exists(mp["Normal"]):
        n = tex(nt, mp["Normal"], True, "Normal"); nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(n.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], pb.inputs["Normal"])
    shader = pb.outputs["BSDF"]
    tb = nt.nodes.new("ShaderNodeBsdfTranslucent"); nt.links.new(mul.outputs[2], tb.inputs["Color"])
    ms = nt.nodes.new("ShaderNodeMixShader"); ms.inputs[0].default_value = 0.3
    nt.links.new(shader, ms.inputs[1]); nt.links.new(tb.outputs[0], ms.inputs[2]); shader = ms.outputs[0]
    o = tex(nt, mp["Opacity"], True, "Opacity")
    tp = nt.nodes.new("ShaderNodeBsdfTransparent"); mo = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(red(nt, o), mo.inputs[0]); nt.links.new(tp.outputs[0], mo.inputs[1]); nt.links.new(shader, mo.inputs[2])
    nt.links.new(mo.outputs[0], out.inputs["Surface"])
    m.use_backface_culling = False
    return m


def leaf_material_export(bank):
    """glTF-exportable leaf: one RGBA atlas (BaseColor rgb + Opacity as alpha, baked by library.bake_rgba) x vertex colour.
    glTF has no translucency/red-channel wiring, so the portable glb is plainer than the in-Blender material."""
    m = bpy.data.materials.new("leafx_" + bank); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); pb = nt.nodes.new("ShaderNodeBsdfPrincipled")
    img = tex(nt, RGBA % bank, False, "RGBA")
    at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "Col"
    mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs[0].default_value = 1.0
    nt.links.new(img.outputs["Color"], mul.inputs[6]); nt.links.new(at.outputs["Color"], mul.inputs[7])
    nt.links.new(mul.outputs[2], pb.inputs["Base Color"]); nt.links.new(img.outputs["Alpha"], pb.inputs["Alpha"])
    pb.inputs["Roughness"].default_value = 0.45
    nt.links.new(pb.outputs["BSDF"], out.inputs["Surface"])
    m.blend_method = "BLEND" if hasattr(m, "blend_method") else None
    m.use_backface_culling = False
    return m


def wood_material(kind):
    m = bpy.data.materials.new("wood_" + kind); m.use_nodes = True
    nt = m.node_tree; pb = nt.nodes["Principled BSDF"]
    if kind == "bark" and os.path.exists(BARKS[BARK_CHOICE][0]):
        d = tex(nt, BARKS[BARK_CHOICE][0], False, "diff"); r = tex(nt, BARKS[BARK_CHOICE][1], True, "rough"); n = tex(nt, BARKS[BARK_CHOICE][2], True, "nor")
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(d.outputs["Color"], pb.inputs["Base Color"]); nt.links.new(red(nt, r), pb.inputs["Roughness"])
        nt.links.new(n.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], pb.inputs["Normal"])
    else:
        pb.inputs["Base Color"].default_value = (0.16, 0.12, 0.07, 1) if kind == "twig" else (0.08, 0.2, 0.06, 1)
        pb.inputs["Roughness"].default_value = 0.75
    return m


def build_plant(plant, name=None, export=False):
    """-> list of bpy objects (wood + one leaf mesh per atlas), plant base at the origin."""
    objs = []
    form = G.SPECS[plant.species]["form"]
    sides = (lambda r: 8 if r > 0.03 else 6 if r > 0.008 else 4) if form == "tree" else (lambda r: 5 if r > 0.006 else 3)
    wood = [b for b in plant.branches if b["kind"] == "stem"]
    pet = [b for b in plant.branches if b["kind"] == "petiole"]
    for kind, bs, mat in (("wood", wood, wood_material("bark" if form == "tree" else "twig")), ("petiole", pet, wood_material("petiole"))):
        me = tube_mesh(bs, sides)
        if me:
            me.materials.append(mat)
            o = bpy.data.objects.new((name or plant.species) + "_" + kind, me); bpy.context.scene.collection.objects.link(o); objs.append(o)
    for bank in sorted(set(plant.leaves.get("bank", []))):
        me = leaf_mesh(plant, bank)
        me.materials.append(leaf_material_export(bank) if export else leaf_material(bank))
        o = bpy.data.objects.new((name or plant.species) + "_leaves_" + bank, me); bpy.context.scene.collection.objects.link(o); objs.append(o)
    for o in objs:
        o["generated_foliage"] = json.dumps(plant.label)
    return objs


# ------------------------------------------------------------------ sheets
def look_at(cam, tgt):
    from mathutils import Vector
    d = Vector(tgt) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def render_sheet(plant, out_prefix, climber, res=480):
    """LDL rubric views: 35 mm, eye 1.6 m, camera 5 m and 15 m from the plant, four azimuths; each frame is cropped
    (render border) to 1.5x the plant so a 0.3 m plant is not 12 px wide, plus two close views at 1.6 m."""
    sc, cam = reset_scene(2000, 40)
    if climber:        # a plain plastered wall behind the plant so only the plant's own coverage is judged
        wall = bpy.data.objects.new("wall", bpy.data.meshes.new("wall"))
        wall.data.from_pydata([(-3, -0.06, 0), (3, -0.06, 0), (3, -0.06, 3.2), (-3, -0.06, 3.2)], [], [(0, 1, 2, 3)])
        wm = bpy.data.materials.new("wm"); wm.use_nodes = True; wm.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.62, 0.58, 0.5, 1)
        wall.data.materials.append(wm); sc.collection.objects.link(wall)
    build_plant(plant)
    lo, hi = plant.bbox()
    M = max(hi - lo)
    tgt = (0, 0, (hi[2]) * 0.5)
    shots = []
    sc.render.use_border = True; sc.render.use_crop_to_border = True
    views = [(5.0, az) for az in ((-50, -20, 20, 50) if climber else (0, 90, 180, 270))]
    views += [(15.0, az) for az in ((-50, -20, 20, 50) if climber else (0, 90, 180, 270))]
    views += [(1.6 if M < 1.5 else 3.0, az) for az in ((-30, 30) if climber else (45, 225))]
    for dist, az in views:
        a = math.radians(az)
        cam.location = (dist * math.sin(a), dist * math.cos(a), 1.6) if climber else (dist * math.cos(a), dist * math.sin(a), 1.6)
        look_at(cam, tgt)
        f = min(1.0, 1.5 * M / (1.03 * min(dist, 5.0 if dist > 5 else dist)))   # the 15 m view keeps the 5 m window: the plant is 1/3 the size, as at 15 m
        sc.render.border_min_x = sc.render.border_min_y = 0.5 - f / 2
        sc.render.border_max_x = sc.render.border_max_y = 0.5 + f / 2
        sc.render.resolution_percentage = max(5, int(res / (f * 2000) * 100))
        p = "%s_d%s_az%d.png" % (out_prefix, str(dist).replace(".", "p"), az)
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        shots.append(p)
    return shots


def parse_spec(s):
    p = s.split(":")
    return dict(slug=p[0], seed=int(p[1]), height_m=float(p[2]) if p[2] != "-" else None, spread_m=float(p[3]) if p[3] != "-" else None,
                state=p[4] if len(p) > 4 else "leaf-on", lod=int(p[5]) if len(p) > 5 else 0)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:]
    mode = argv[0]
    out = argv[argv.index("--out") + 1]
    specs = [parse_spec(argv[i + 1]) for i, a in enumerate(argv) if a == "--spec"]
    os.makedirs(out, exist_ok=True)
    res = []
    for sp in specs:
        plant = G.generate(sp["slug"], sp["seed"], sp["height_m"], sp["spread_m"], sp["state"], sp["lod"])
        tag = "%s_s%d_%s" % (sp["slug"], sp["seed"], sp["state"])
        if mode == "glb":
            sc, _ = reset_scene(64, 1)
            for o in list(bpy.data.objects):
                bpy.data.objects.remove(o)
            build_plant(plant, tag, export=True)
            path = os.path.join(out, tag + ".glb")
            bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", export_attributes=True, use_selection=False)
            res.append(dict(tag=tag, glb=path, label=plant.label))
        if mode == "sheet":
            shots = render_sheet(plant, os.path.join(out, tag), G.SPECS[sp["slug"]]["form"] == "climber")
            res.append(dict(tag=tag, shots=shots, label=plant.label, leaves=int(len(plant.leaves["length"])),
                            tris=int(len(plant.leaves["length"]) * (ROWS - 1) * (COLS - 1) * 2)))
    json.dump(res, open(os.path.join(out, "sheet_index.json"), "w"))
