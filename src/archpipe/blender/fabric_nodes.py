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
    feature_m = {"boucle": 0.005, "linen": 0.0012, "cotton": 0.0012, "leather": 0.002, "velvet": 0.0008}[spec["fabric_class"]]
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
    mat["fabric_class"] = spec["fabric_class"]
    mat["fabric_feature_mm"] = feature_m * 1000.0
