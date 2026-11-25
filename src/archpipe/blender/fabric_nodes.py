"""Blender node finish for soft-goods fabrics (lane SOFT). Needs bpy; soft_goods.py chooses the numbers.

A cushion's weave is metre-scaled in object space (the same rule as the cloth-weave material), so its size in mm
does not change with the mesh: feature_mm is what the eye sees, and critic.furniture_realism measures the same
quantity on the texture.
"""
import bpy


def finish_fabric(mat, spec):
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    fuzz = spec.get("fuzz", 0.0)
    bsdf.inputs["Sheen Weight"].default_value = min(1.0, spec.get("sheen", 0.0) + 0.5 * fuzz)
    bsdf.inputs["Sheen Roughness"].default_value = 0.45
    # a dark cloth's sheen is dark: white sheen on near-black reads as satin or plastic
    base = bsdf.inputs["Base Color"].default_value
    lum = 0.2126 * base[0] + 0.7152 * base[1] + 0.0722 * base[2]
    dark = min(1.0, lum / 0.2)
    bsdf.inputs["Sheen Weight"].default_value *= 0.25 + 0.75 * dark
    if "Sheen Tint" in bsdf.inputs:
        bsdf.inputs["Sheen Tint"].default_value = (0.35 + 0.65 * base[0], 0.35 + 0.65 * base[1], 0.35 + 0.65 * base[2], 1.0)
    feature_m = {"boucle": 0.005, "linen": 0.002, "cotton": 0.0016, "leather": 0.002, "velvet": 0.0008}[spec["fabric_class"]]
    coord = nt.nodes.new("ShaderNodeTexCoord")
    height = nt.nodes.new("ShaderNodeTexVoronoi" if spec["fabric_class"] == "boucle" else "ShaderNodeTexNoise")
    height.inputs["Scale"].default_value = 1.0 / feature_m
    nt.links.new(coord.outputs["Object"], height.inputs["Vector"])
    if spec["fabric_class"] == "boucle":
        height.feature = "F1"                       # round loops
        value, strength, dist = height.outputs["Distance"], 0.9, 0.0012
        inv = nt.nodes.new("ShaderNodeMath")
        inv.operation = "SUBTRACT"
        inv.inputs[0].default_value = 1.0
        nt.links.new(value, inv.inputs[1])
        value = inv.outputs[0]
    elif spec["fabric_class"] == "leather":
        height.inputs["Detail"].default_value = 3.0
        value, strength, dist = height.outputs["Fac"], 0.35, 0.0006
    else:
        height.inputs["Detail"].default_value = 2.0
        value, strength, dist = height.outputs["Fac"], 0.30, 0.0004
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = dist
    nt.links.new(value, bump.inputs["Height"])
    prior = bsdf.inputs["Normal"].links
    if prior:
        nt.links.new(prior[0].from_socket, bump.inputs["Normal"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    # cloth is never one tone: soft mottle (dye, pile direction, handling) at a few centimetres, a few per cent
    colour_in = bsdf.inputs["Base Color"].links
    mottle = nt.nodes.new("ShaderNodeTexNoise")
    mottle.inputs["Scale"].default_value = 1.0 / 0.05
    mottle.inputs["Detail"].default_value = 3.0
    nt.links.new(coord.outputs["Object"], mottle.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs[0].default_value = 0.0
    ramp = nt.nodes.new("ShaderNodeMapRange")
    ramp.inputs["To Min"].default_value = 0.90
    ramp.inputs["To Max"].default_value = 1.10
    nt.links.new(mottle.outputs["Fac"], ramp.inputs["Value"])
    mix.inputs[0].default_value = 1.0
    grey = nt.nodes.new("ShaderNodeCombineColor")
    for ch in ("Red", "Green", "Blue"):
        nt.links.new(ramp.outputs["Result"], grey.inputs[ch])
    nt.links.new(grey.outputs["Color"], mix.inputs[7])
    if colour_in:
        nt.links.new(colour_in[0].from_socket, mix.inputs[6])
    else:
        mix.inputs[6].default_value = base
    nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    mat["fabric_class"] = spec["fabric_class"]
    mat["fabric_feature_mm"] = feature_m * 1000.0
