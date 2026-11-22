"""Blender-only helpers: wire a Fab/Megascans plant archive's own JPG maps onto an imported FBX (LDL pass 5 wiring, `plants/fab_preview.py`).

Megascans single-channel maps (Opacity, Roughness, Gloss) keep their data in the RED channel only: they are read through `red()`, never as colour
(read as colour the leaves come out ~5x too transparent: LDL's measured defect). The FBX's own texture paths (a Windows .exr atlas) are discarded.
Not wired: AO, Cavity, Bump, Specular (Cycles computes occlusion; Normal supersedes Bump).
"""
import glob
import json
import os

import bpy


def maps_of(d):
    m = {}
    for f in sorted(glob.glob(d + "/*.jpg")):
        b = os.path.basename(f)[:-4]
        if "_Billboard_" in b:
            continue
        m[b.rsplit("_", 1)[1]] = f
    return m


def _tex(nt, path, noncolor):
    n = nt.nodes.new("ShaderNodeTexImage")
    n.image = bpy.data.images.load(path, check_existing=True)
    n.image.colorspace_settings.name = "Non-Color" if noncolor else "sRGB"
    return n


def _red(nt, t):
    sp = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(t.outputs["Color"], sp.inputs["Color"])
    return sp.outputs["Red"]


def build_material(name, d):
    maps = maps_of(d)
    js = glob.glob(d + "/*.json")
    meta = json.load(open(js[0])) if js else {}
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    pb = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bc = _tex(nt, maps["BaseColor"], False)
    nt.links.new(bc.outputs["Color"], pb.inputs["Base Color"])
    if "Roughness" in maps:
        nt.links.new(_red(nt, _tex(nt, maps["Roughness"], True)), pb.inputs["Roughness"])
    elif "Gloss" in maps:
        inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0
        nt.links.new(_red(nt, _tex(nt, maps["Gloss"], True)), inv.inputs[1]); nt.links.new(inv.outputs[0], pb.inputs["Roughness"])
    if "Normal" in maps:
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(_tex(nt, maps["Normal"], True).outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], pb.inputs["Normal"])
    shader = pb.outputs["BSDF"]
    if "Translucency" in maps:                       # backlit leaf: translucent BSDF tinted by the JSON's Translucency Tint, 30 %
        col = _tex(nt, maps["Translucency"], False).outputs["Color"]
        tint = next((p["Value"] for p in meta.get("material_params", {}).get("material", []) if p["Name"] == "Translucency Tint"), None)
        if tint:
            mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"; mx.inputs[0].default_value = 1.0
            mx.inputs[7].default_value = tuple(tint[:3]) + (1,)
            nt.links.new(col, mx.inputs[6]); col = mx.outputs[2]
        tb = nt.nodes.new("ShaderNodeBsdfTranslucent"); nt.links.new(col, tb.inputs["Color"])
        ms = nt.nodes.new("ShaderNodeMixShader"); ms.inputs[0].default_value = 0.3
        nt.links.new(shader, ms.inputs[1]); nt.links.new(tb.outputs[0], ms.inputs[2]); shader = ms.outputs[0]
    if "Opacity" in maps:                            # cut-out leaves: the red channel is the opacity
        tp = nt.nodes.new("ShaderNodeBsdfTransparent"); mo = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(_red(nt, _tex(nt, maps["Opacity"], True)), mo.inputs[0]); nt.links.new(tp.outputs[0], mo.inputs[1]); nt.links.new(shader, mo.inputs[2]); shader = mo.outputs[0]
    nt.links.new(shader, out.inputs["Surface"])
    return mat


def build_game_materials(d):
    """A game-asset archive with PNG maps and no Megascans JPGs (the Fab olive, LDL pass 6): slot 0 = foliage (colour + ALPHA cut-out, normal, AORM green = roughness),
    slot 1 = trunk (colour, normal). Same wiring as LDL's `olive_preview.py`."""
    def img(n, nc):
        i = bpy.data.images.load(os.path.join(d, n), check_existing=True)
        i.colorspace_settings.name = "Non-Color" if nc else "sRGB"
        return i

    def mat(name, color, normal, alpha, rough_from=None):
        m = bpy.data.materials.new(name); m.use_nodes = True
        nt = m.node_tree; nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial"); pb = nt.nodes.new("ShaderNodeBsdfPrincipled")
        c = nt.nodes.new("ShaderNodeTexImage"); c.image = img(color, False); nt.links.new(c.outputs["Color"], pb.inputs["Base Color"])
        n = nt.nodes.new("ShaderNodeTexImage"); n.image = img(normal, True); nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(n.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], pb.inputs["Normal"])
        if rough_from:
            r = nt.nodes.new("ShaderNodeTexImage"); r.image = img(rough_from, True); sp = nt.nodes.new("ShaderNodeSeparateColor")
            nt.links.new(r.outputs["Color"], sp.inputs["Color"]); nt.links.new(sp.outputs["Green"], pb.inputs["Roughness"])
        sh = pb.outputs["BSDF"]
        if alpha:
            tp = nt.nodes.new("ShaderNodeBsdfTransparent"); mx = nt.nodes.new("ShaderNodeMixShader")
            nt.links.new(c.outputs["Alpha"], mx.inputs[0]); nt.links.new(tp.outputs[0], mx.inputs[1]); nt.links.new(sh, mx.inputs[2]); sh = mx.outputs[0]
        nt.links.new(sh, out.inputs["Surface"])
        return m
    return [mat("fab:olive-foliage", "T_ItalianTress_Olive_D.PNG", "T_ItalianTress_Olive_N.PNG", True, "T_ItalianTress_Olive_AORM.PNG"),
            mat("fab:olive-trunk", "T_ItalianTress_Olivio_Tronco_D.PNG", "T_ItalianTress_Olivio_N.PNG", False)]


_MATS, _SRC = {}, {}


def import_fbx(path):
    """-> list of new mesh objects. The first import of a file is a real import (materials rebuilt from the archive's maps); later ones share its mesh data."""
    d = os.path.dirname(path)
    if d not in _MATS:
        _MATS[d] = build_material("fab:" + os.path.basename(d), d) if maps_of(d) else build_game_materials(d)
    if path in _SRC:
        src, mw = _SRC[path]
        ob = bpy.data.objects.new("ld-fab-instance", src.data)
        bpy.context.scene.collection.objects.link(ob)
        ob.matrix_world = mw
        return [ob]
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    ms = [o for o in new if o.type == "MESH"]
    ms = [o for o in ms if not o.name.startswith("UCX_")]            # collision hulls
    assert len(ms) == 1, (path, len(ms))
    o = ms[0]
    mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
    for e in new:
        if e is not o:
            bpy.data.objects.remove(e)
    mats = _MATS[d] if isinstance(_MATS[d], list) else [_MATS[d]] * len(o.material_slots)
    for s, m in zip(o.material_slots, mats):
        s.material = m
    _SRC[path] = (o, mw)
    return [o]
