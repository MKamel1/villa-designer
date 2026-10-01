"""Render a validated villa-render/1 scene inside Blender.

Units are metres and calibrated lux. The display exposure is
    Blender stops = log2(pi / (2.5 * 2**EV100)).
Here EV100 is the stated exposure value at ISO 100. The denominator is the
ISO 100 incident-light meter's 2.5 lux per exposure-value unit (C = 250); a
Lambertian card of reflectance rho under E lux has luminance rho*E/pi. An
incident meter exposes an 18 % grey card as middle grey (ISO 2720), so at a
matching EV100 the grey card enters AgX at scene-linear 0.18 and a white card
at 1.0. (The first version mapped the WHITE card to 0.18: every image 2.47
stops dark; the villa's first draft set showed it.) The --calibrate run records the actual
Blender white-card reading; no unrun value is claimed here.

IES_POINT_POWER = 162.624 is measured in ADR-0010: the IES node emits its
file's raw candela, without flux normalization. The spec's lumens therefore
scale the file's candela by specified lumens / integrated file lumens.

For an emitting surface, luminous exitance M is emitted lumens per square
metre. A Lambertian face emits into its outward hemisphere; integrating
constant radiance over that hemisphere gives M = pi * radiance. In this
project's calibrated units, Blender Emission strength is therefore M/pi.
The --calibrate sphere probe checks the rendered result independently.

The prior workstation selftest measured the IES probe at 167.25 lux
against 172.75 lux analytic (3.2 percent), with EV100 6.11 at 172 lux.
Those are the user's measured baseline; the new sphere reading is pending.
"""
import argparse
import importlib.util
import json
import math
import os
import sys
import time

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))


def sibling(name):
    spec = importlib.util.spec_from_file_location("villa_" + name, os.path.join(HERE, name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


photoreal = sibling("photoreal")
build_scene = sibling("build_scene")
grain = sibling("grain")
contract_spec = importlib.util.spec_from_file_location(
    "villa_render_contract", os.path.join(HERE, "..", "villa_render_contract.py"))
contract = importlib.util.module_from_spec(contract_spec)
contract_spec.loader.exec_module(contract)
IES_POINT_POWER = build_scene.IES_POINT_POWER
IES_AZIMUTH_OFFSET_DEG = build_scene.IES_AZIMUTH_OFFSET_DEG


def luminance(rgb):
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


def configure_glass(materials, material_specs):
    """Respect whether a ray crosses one sheet or both sides of a slab.

    The shared bedroom adapter assumes a closed slab. The villa daylight
    shell represents each window as one sheet; applying the slab's square
    root there overstated a specified 70 percent as 83.7 percent.
    """
    photoreal.architectural_glass()
    for name, spec in material_specs.items():
        if spec["kind"] != "glass":
            continue
        mat = materials[name]
        interfaces = spec.get("interfaces", 2)
        per_face = spec["transmittance"] ** (1 / interfaces)
        for node in mat.node_tree.nodes:
            if node.type == "BSDF_TRANSPARENT":
                node.inputs["Color"].default_value = (per_face, per_face, per_face, 1)
        mat["glass_interfaces"] = interfaces


def world_to_camera_view(scene, camera, point):
    """Project a world point using Blender's camera frame and lens shifts.

    Same normalized coordinates as bpy_extras.object_utils, implemented here
    to keep this Blender script's imports to bpy, bmesh, mathutils and stdlib.
    """
    local = camera.matrix_world.inverted() @ point
    frame = camera.data.view_frame(scene=scene)
    z = frame[0].z
    left, right = min(v.x for v in frame), max(v.x for v in frame)
    bottom, top = min(v.y for v in frame), max(v.y for v in frame)
    if local.z >= -1e-9:
        return Vector((0, 0, -1))
    x = local.x * z / local.z
    y = local.y * z / local.z
    return Vector(((x-left)/(right-left), (y-bottom)/(top-bottom), -local.z))


def image_mean(img):
    pixels = img.pixels[:]
    step = max(1, len(pixels) // (4 * 20000))
    total = count = 0
    for i in range(0, len(pixels) // 4, step):
        # Blender's image pixel buffer for an sRGB JPEG contains encoded samples.
        def linear(v):
            return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
        total += luminance([linear(pixels[4*i+j]) for j in range(3)])
        count += 1
    return total / max(count, 1)


def image_mean_rgb(img):
    """Mean LINEAR colour of an sRGB texture, per channel."""
    pixels = img.pixels[:]
    step = max(1, len(pixels) // (4 * 20000))
    tot = [0.0, 0.0, 0.0]
    count = 0

    def linear(v):
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    for i in range(0, len(pixels) // 4, step):
        for j in range(3):
            tot[j] += linear(pixels[4*i+j])
        count += 1
    return [t / max(count, 1) for t in tot]


def triplanar_normal(nt, coordinates, image):
    """Interpret NormalGL as tangent vectors on three object-space planes."""
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    to_object = nt.nodes.new("ShaderNodeVectorTransform")
    to_object.vector_type = "NORMAL"
    to_object.convert_from, to_object.convert_to = "WORLD", "OBJECT"
    nt.links.new(geo.outputs["Normal"], to_object.inputs["Vector"])
    xyz = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(coordinates, xyz.inputs[0])
    normal_xyz = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(to_object.outputs["Vector"], normal_xyz.inputs[0])
    def math_node(op, a, b=None):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = op
        nt.links.new(a, n.inputs[0])
        if isinstance(b, (int, float)):
            n.inputs[1].default_value = b
        elif b is not None:
            nt.links.new(b, n.inputs[1])
        return n.outputs[0]
    weighted = []
    weights = []
    projections = (("X", ("Y", "Z"), ("B", "R", "G")),
                   ("Y", ("Z", "X"), ("G", "B", "R")),
                   ("Z", ("X", "Y"), ("R", "G", "B")))
    for axis, uv, arrangement in projections:
        coord = nt.nodes.new("ShaderNodeCombineXYZ")
        nt.links.new(xyz.outputs[uv[0]], coord.inputs["X"])
        nt.links.new(xyz.outputs[uv[1]], coord.inputs["Y"])
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = image
        nt.links.new(coord.outputs[0], tex.inputs["Vector"])
        minus = nt.nodes.new("ShaderNodeVectorMath")
        minus.operation = "SUBTRACT"
        minus.inputs[1].default_value = (0.5, 0.5, 0.5)
        nt.links.new(tex.outputs["Color"], minus.inputs[0])
        twice = nt.nodes.new("ShaderNodeVectorMath")
        twice.operation = "SCALE"
        twice.inputs["Scale"].default_value = 2
        nt.links.new(minus.outputs[0], twice.inputs[0])
        split = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(twice.outputs[0], split.inputs[0])
        mapped = {"R": split.outputs["X"], "G": split.outputs["Y"], "B": split.outputs["Z"]}
        sign = math_node("SIGN", normal_xyz.outputs[axis])
        components = [mapped[c] for c in arrangement]
        normal_axis_index = "XYZ".index(axis)
        components[normal_axis_index] = math_node("MULTIPLY", components[normal_axis_index], sign)
        combined = nt.nodes.new("ShaderNodeCombineXYZ")
        for socket, value in zip(("X", "Y", "Z"), components):
            nt.links.new(value, combined.inputs[socket])
        weight = math_node("POWER", math_node("ABSOLUTE", normal_xyz.outputs[axis]), 4)
        scaled = nt.nodes.new("ShaderNodeVectorMath")
        scaled.operation = "SCALE"
        nt.links.new(combined.outputs[0], scaled.inputs[0])
        nt.links.new(weight, scaled.inputs["Scale"])
        weighted.append(scaled.outputs[0])
        weights.append(weight)
    result = weighted[0]
    for other in weighted[1:]:
        add = nt.nodes.new("ShaderNodeVectorMath")
        add.operation = "ADD"
        nt.links.new(result, add.inputs[0])
        nt.links.new(other, add.inputs[1])
        result = add.outputs[0]
    normalized = nt.nodes.new("ShaderNodeVectorMath")
    normalized.operation = "NORMALIZE"
    nt.links.new(result, normalized.inputs[0])
    to_world = nt.nodes.new("ShaderNodeVectorTransform")
    to_world.vector_type = "NORMAL"
    to_world.convert_from, to_world.convert_to = "OBJECT", "WORLD"
    nt.links.new(normalized.outputs[0], to_world.inputs["Vector"])
    return to_world.outputs["Vector"]


def add_material(name, spec, library_root, warnings):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    out = nt.nodes.get("Material Output")
    base = tuple(spec["base_rgb"]) + (1.0,)
    bsdf.inputs["Base Color"].default_value = base
    bsdf.inputs["Roughness"].default_value = spec.get("roughness", 0.6)
    bsdf.inputs["Metallic"].default_value = spec.get("metallic", 0.0)
    if name in ("boucle", "linen", "sage-fabric", "charcoal-fabric", "taupe-fabric", "bedding-white", "throw-taupe",
                "outdoor-fabric", "curtain-sheer", "curtain-heavy", "curtain-heavy-dimout"):
        bsdf.inputs["Sheen Weight"].default_value = 0.18
        bsdf.inputs["Sheen Roughness"].default_value = 0.7
    kind = spec["kind"]
    if kind == "glass":
        bsdf.inputs["Transmission Weight"].default_value = 1.0
        # WP4-B4: honour a fitting's own measured index of refraction (e.g. the ensuite bath screen's 1.52,
        # revit_spec bath_fittings) instead of always assuming 1.5.
        ior = spec.get("ior")
        bsdf.inputs["IOR"].default_value = ior if ior is not None else 1.5
        if ior is None:
            warnings.append(name + ": glass IOR 1.5 assumed; the contract has no IOR field")
        mat["presentation_assumption"] = "clear glazing from villa contract"
        mat["presentation_transmittance"] = spec["transmittance"]
    elif kind == "translucent":
        trans = nt.nodes.new("ShaderNodeBsdfTranslucent")
        trans.inputs["Color"].default_value = base
        mix = nt.nodes.new("ShaderNodeMixShader")
        mix.inputs[0].default_value = spec.get("transmittance", 0.5)
        nt.links.new(bsdf.outputs["BSDF"], mix.inputs[1])
        nt.links.new(trans.outputs["BSDF"], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs["Surface"])
    elif kind == "emissive":
        mat["emission_lm_per_m2"] = spec["emission_lm_per_m2"]
        emit = nt.nodes.new("ShaderNodeEmission")
        emit.name = "Villa Emission"
        emit.inputs["Color"].default_value = build_scene.kelvin_to_rgb(spec["cct_k"]) + (1.0,)
        emit.inputs["Strength"].default_value = contract.emission_strength(spec["emission_lm_per_m2"])
        # Keep the authored base surface when the light output is zero.
        # Adding the emission closure leaves that surface visible while lit.
        surface = nt.nodes.new("ShaderNodeAddShader")
        nt.links.new(bsdf.outputs["BSDF"], surface.inputs[0])
        nt.links.new(emit.outputs[0], surface.inputs[1])
        # Emit from outward faces only. Closed shells use their full outer
        # area; a zero-thickness plane emits from the CCW side only.
        geometry = nt.nodes.new("ShaderNodeNewGeometry")
        transparent = nt.nodes.new("ShaderNodeBsdfTransparent")
        mix = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(geometry.outputs["Backfacing"], mix.inputs[0])
        nt.links.new(surface.outputs[0], mix.inputs[1])
        nt.links.new(transparent.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs["Surface"])
        if hasattr(mat, "cycles") and hasattr(mat.cycles, "sample_as_light"):
            mat.cycles.sample_as_light = True
    asset = spec.get("asset")
    # Curtains (client 2026-09-28) are "translucent" (the sheer/heavy Mix Shader above), not "principled"; extended
    # here so they get the same per-channel mean-matched photo texture as every other finish (ADR-0013 part 7)
    # instead of a flat colour.
    if asset and kind in ("principled", "translucent"):
        folder = os.path.join(library_root, "materials", asset)
        def find(suffix):
            if not os.path.isdir(folder):
                return None
            names = sorted(n for n in os.listdir(folder) if suffix.lower() in n.lower() and n.lower().endswith((".jpg", ".jpeg", ".png", ".exr")))
            return os.path.join(folder, names[0]) if names else None
        color_path = find("_Color")
        if not color_path:
            warnings.append("missing albedo asset: " + asset)
        else:
            coord = nt.nodes.new("ShaderNodeTexCoord")
            mapping = nt.nodes.new("ShaderNodeMapping")
            tile = spec.get("tile_m", 1.0)
            mapping.inputs["Scale"].default_value = (1/tile, 1/tile, 1/tile)
            axis = spec.get("grain_axis", "x")
            # docs/LEARNINGS.md 2026-09-28 (stair-tread / vanity wood smear): this rotation table is shared with
            # the bpy-free archpipe.blender.grain module so the same numbers are proven by a unit test.
            mapping.inputs["Rotation"].default_value = tuple(math.radians(v) for v in grain.GRAIN_ROTATION_DEG[axis])
            nt.links.new(coord.outputs["Generated"], mapping.inputs["Vector"])
            # Generated coordinates are normalized by object bounds; Object
            # coordinates retain the authored metre scale across all meshes.
            nt.links.new(coord.outputs["Object"], mapping.inputs["Vector"])
            def texture(path, colorspace):
                node = nt.nodes.new("ShaderNodeTexImage")
                node.image = bpy.data.images.load(path, check_existing=True)
                node.image.colorspace_settings.name = colorspace
                node.projection = "BOX"
                node.projection_blend = 0.25
                nt.links.new(mapping.outputs["Vector"], node.inputs["Vector"])
                return node
            color = texture(color_path, "sRGB")
            # ADR-0013 part 7: the photo keeps its PATTERN, the finish keeps its stated COLOUR. Each channel's mean
            # is matched to the stated base colour at the stated reflectance. Matching luminance only let the photo's
            # own chroma through (Marble014 G/R 0.87, B/R 0.69 against a stated cream 0.95 / 0.86): the stone floors
            # and every bounce off them read pink.
            mean_rgb = image_mean_rgb(color.image)
            mean = luminance(mean_rgb)
            refl = spec.get("reflectance", luminance(base))
            target = [c * refl / max(luminance(base), 1e-9) for c in base[:3]]
            factor = [t / max(m, 1e-9) for t, m in zip(target, mean_rgb)]
            scale = nt.nodes.new("ShaderNodeVectorMath")
            scale.operation = "MULTIPLY_ADD"
            contrast = spec.get("contrast", 1.0)
            # Draw the photographed variation toward its own mean. Per-channel
            # target means remain unchanged, so the stated hue and reflectance
            # survive while veneer stops reading as printed stripes.
            scale.inputs[1].default_value = [f * contrast for f in factor]
            scale.inputs[2].default_value = [t * (1 - contrast) for t in target]
            nt.links.new(color.outputs["Color"], scale.inputs[0])
            # A reflectance cannot exceed one. Mean normalization of a dark
            # photographic texture otherwise produces energy-gaining texels.
            bounded = nt.nodes.new("ShaderNodeVectorMath")
            bounded.operation = "MINIMUM"
            bounded.inputs[1].default_value = (1, 1, 1)
            nt.links.new(scale.outputs["Vector"], bounded.inputs[0])
            nt.links.new(bounded.outputs["Vector"], bsdf.inputs["Base Color"])
            if kind == "translucent":
                # the transmitted (Translucent BSDF) colour keeps the same weave, not just the reflected one
                nt.links.new(bounded.outputs["Vector"], trans.inputs["Color"])
            mat["texture_mean_linear"] = mean
            mat["texture_mean_rgb_linear"] = mean_rgb
            mat["texture_scale"] = factor
            mat["reflectance_bounded"] = True
            rough = find("_Roughness")
            if rough:
                rough_color = texture(rough, "Non-Color").outputs["Color"]
                # Preserve the specified roughness while retaining photographed
                # small-scale variation. The map is also a projection-safe
                # scalar height cue; a tangent normal map has no valid UV basis
                # on these world-coordinate, box-projected meshes.
                rough_range = nt.nodes.new("ShaderNodeMapRange")
                rough_range.inputs["To Min"].default_value = max(0.0, spec.get("roughness", 0.6) - 0.12)
                rough_range.inputs["To Max"].default_value = min(1.0, spec.get("roughness", 0.6) + 0.12)
                nt.links.new(rough_color, rough_range.inputs["Value"])
                nt.links.new(rough_range.outputs["Result"], bsdf.inputs["Roughness"])
                fabrics = ("boucle", "linen", "sage-fabric", "charcoal-fabric", "taupe-fabric", "bedding-white",
                           "throw-taupe", "outdoor-fabric", "curtain-sheer", "curtain-heavy", "curtain-heavy-dimout")
                if name in fabrics:
                    # woven cloth: a subtle bump from the weave, not a hard photographed relief
                    bump = nt.nodes.new("ShaderNodeBump")
                    bump.inputs["Strength"].default_value = 0.15
                    bump.inputs["Distance"].default_value = 0.0002
                    nt.links.new(rough_color, bump.inputs["Height"])
                    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
            normal = find("_NormalGL")
            if normal and name not in ("boucle", "linen", "sage-fabric", "charcoal-fabric", "taupe-fabric",
                                       "bedding-white", "throw-taupe", "outdoor-fabric", "walnut", "oak",
                                       "door-oak", "teak", "oak-floor", "curtain-sheer", "curtain-heavy",
                                       "curtain-heavy-dimout"):
                # stone and paving keep their photographed relief through the object-space triplanar normal. Wood
                # does not: a finished veneer is nearly flat, and on a close wardrobe end the normal map read as
                # large watery ripples (draft 14 dressing view)
                normal_image = bpy.data.images.load(normal, check_existing=True)
                normal_image.colorspace_settings.name = "Non-Color"
                nt.links.new(triplanar_normal(nt, mapping.outputs["Vector"], normal_image), bsdf.inputs["Normal"])
    return mat


def apply_visibility(obj, visibility):
    for key in contract.RAY_VISIBILITY:
        setattr(obj, "visible_" + key, visibility.get(key, True))


def add_mesh_batch(specs, name, material, warnings):
    """Build one Blender object from one or more authored mesh records."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    for spec in specs:
        index = {}
        source_faces = []
        for polygon in spec["faces"]:
            # A keyhole polygon (a wall with its openings, daylight.with_holes) revisits vertices along its bridge:
            # a repeat inside one face gets its own vertex; a face that already exists (coincident faces) is built
            # from fresh vertices. Both made faces.new raise on the villa shell.
            vertices, seen = [], set()
            for point in polygon:
                key = tuple(point)
                if key not in index:
                    index[key] = bm.verts.new(key)
                v = index[key]
                if v in seen:
                    v = bm.verts.new(key)
                seen.add(v)
                vertices.append(v)
            try:
                source_faces.append(bm.faces.new(vertices))
            except ValueError:
                source_faces.append(bm.faces.new([bm.verts.new(tuple(p)) for p in polygon]))
        source_edges = {edge for face in source_faces for edge in face.edges}
        if all(len(edge.link_faces) == 2 for edge in source_edges):
            volume = 0.0
            for face in source_faces:
                a = face.verts[0].co
                for i in range(1, len(face.verts)-1):
                    volume += a.dot(face.verts[i].co.cross(face.verts[i+1].co)) / 6
            if volume < -1e-9:
                bmesh.ops.reverse_faces(bm, faces=source_faces)
                warnings.append(spec["id"] + ": reversed " + str(len(source_faces)) + " faces (negative signed volume)")
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(material)
    apply_visibility(obj, specs[0].get("visibility", {}))
    if material.get("emission_lm_per_m2") is not None and hasattr(obj, "cycles") and hasattr(obj.cycles, "use_multiple_importance_sampling"):
        obj.cycles.use_multiple_importance_sampling = True
    return obj


def add_mesh_detail(obj, spec):
    """Apply authored edge rounding and smoothing only to a separate object."""
    bevel_width = spec.get("bevel_m", 0)
    subdivision_levels = spec.get("subdivide", 0)
    if bevel_width <= 0 and subdivision_levels <= 0:
        return
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    for face in bm.faces:
        face.smooth = True
    angle = math.radians(30)
    for edge in bm.edges:
        if edge.is_manifold:
            edge.smooth = edge.calc_face_angle(0.0) <= angle
    bm.to_mesh(obj.data)
    bm.free()
    if bevel_width > 0:
        bevel = obj.modifiers.new("Villa Bevel", "BEVEL")
        bevel.width = bevel_width
        bevel.segments = 2
        bevel.limit_method = "ANGLE"
        bevel.angle_limit = angle
        bevel.harden_normals = True
    if subdivision_levels > 0:
        subdivision = obj.modifiers.new("Villa Subdivision", "SUBSURF")
        subdivision.levels = subdivision_levels
        subdivision.render_levels = subdivision_levels


def build_meshes(mesh_specs, materials, material_specs, warnings):
    batches = {}
    for spec in mesh_specs:
        key = contract.mesh_batch_key(spec, material_specs[spec["material"]]["kind"])
        if key is None:
            key = ("one", spec["id"])
        batches.setdefault(key, []).append(spec)
    objects = {}
    for index, specs in enumerate(batches.values()):
        name = specs[0]["id"] if len(specs) == 1 else "villa-merged-%04d" % index
        obj = add_mesh_batch(specs, name, materials[specs[0]["material"]], warnings)
        if len(specs) == 1:
            add_mesh_detail(obj, specs[0])
        for spec in specs:
            objects[spec["id"]] = obj
    return objects


def build_climbers(mesh_specs, objects, materials, warnings):
    """Replace each box mass with dense individual leaf and bract polygons."""
    placing = sibling("climber_placement")
    for spec in mesh_specs:
        if spec["material"] != "bougainvillea-bract" or "climber-" not in spec["id"]:
            continue
        obj = objects[spec["id"]]
        obj.hide_render = True
        points = [v for face in spec["faces"] for v in face]
        box = (min(v[0] for v in points), min(v[1] for v in points), min(v[2] for v in points),
               max(v[0] for v in points), max(v[1] for v in points), max(v[2] for v in points))
        # Client round-3 (v01/v02/v24): climbers were "almost invisible" at the previous fixed density=120.
        # density_for_coverage() targets >= 80% coverage of the largest vertical face (see climber_placement's
        # module docstring for the Poisson-coverage derivation); it is computed here, not hardcoded, so it tracks
        # SIZE if that ever changes.
        density = placing.density_for_coverage(target=0.80)
        positions = placing.placements(box, density=density, seed=sum(map(ord, spec["id"])))
        for kind, matname in (("leaf", "bougainvillea-leaf"), ("bract", "bougainvillea-bract")):
            verts, faces = [], []
            for x, y, z, label in positions:
                if label != kind:
                    continue
                half = placing.SIZE[kind]
                dx = min(half, x-box[0], box[3]-x)
                dy = min(half, y-box[1], box[4]-y)
                dz = min(half*1.5, z-box[2], box[5]-z)
                if min(dx, dy, dz) <= 0:
                    continue
                base = len(verts)
                verts.extend(((x-dx, y, z), (x, y-dy, z+dz),
                              (x+dx, y, z), (x, y+dy, z-dz)))
                faces.append((base, base+1, base+2, base+3))
            mesh = bpy.data.meshes.new(spec["id"] + "-" + kind)
            mesh.from_pydata(verts, [], faces)
            mesh.update()
            leaf_obj = bpy.data.objects.new(mesh.name, mesh)
            bpy.context.collection.objects.link(leaf_obj)
            mesh.materials.append(materials[matname])
        warnings.append(spec["id"] + ": replaced box with %d scattered leaf/bract instances" % len(positions))


def layered_emissive_materials(mesh_specs, objects, material_specs):
    """Give each switched emitter its own emission node; shared finishes stay shared."""
    result = {}
    for spec in mesh_specs:
        if "layer" not in spec or material_specs[spec["material"]]["kind"] != "emissive":
            continue
        obj = objects[spec["id"]]
        original = obj.data.materials[0]
        material = original.copy()
        material.name = "villa-emissive-" + spec["id"]
        obj.data.materials[0] = material
        result[spec["id"]] = material.node_tree.nodes["Villa Emission"]
    return result


def set_emissive_view(emissive_sources, mesh_by_id, switched_emitters, view):
    """Set only emission strength; object visibility and base shader persist."""
    current = []
    for source in emissive_sources:
        factor = contract.emissive_mesh_output_factor(mesh_by_id[source["id"]], view)
        if source["id"] in switched_emitters:
            switched_emitters[source["id"]].inputs["Strength"].default_value = contract.emission_strength(
                source["exitance_lm_per_m2"]) * factor
        current.append({**source, "output_factor": factor,
                        "emitted_lumens": source["emitted_lumens"] * factor})
    return current


def ies_flux(path):
    """Integrate Type C candela with LM-63 horizontal symmetry."""
    lines = open(path, encoding="utf-8-sig", errors="replace").read().splitlines()
    tilt = next(i for i, line in enumerate(lines) if line.upper().startswith("TILT="))
    if lines[tilt].strip().upper() != "TILT=NONE":
        raise ValueError("external/embedded IES tilt is unsupported: " + path)
    data = [float(v) for v in " ".join(lines[tilt+1:]).replace(",", " ").split()]
    lamps, lamp_lm, multiplier, nv, nh, photo_type = data[:6]
    nv, nh = int(nv), int(nh)
    if int(photo_type) != 1:
        raise ValueError("only IES Type C supported: " + path)
    start = 13
    vertical = data[start:start+nv]
    horizontal = data[start+nv:start+nv+nh]
    vals = data[start+nv+nh:start+nv+nh+nv*nh]
    if len(vals) != nv*nh or nv < 2 or nh < 1:
        raise ValueError("incomplete IES candela table: " + path)
    def candela(theta_index, azimuth):
        if nh == 1:
            return vals[theta_index]
        maximum = horizontal[-1]
        azimuth %= 360
        if maximum <= 90:
            azimuth %= 180
            if azimuth > 90:
                azimuth = 180-azimuth
        elif maximum <= 180 and azimuth > 180:
            azimuth = 360-azimuth
        azimuth = min(azimuth, maximum)
        for j in range(nh-1):
            if horizontal[j] <= azimuth <= horizontal[j+1]:
                f = (azimuth-horizontal[j]) / max(horizontal[j+1]-horizontal[j], 1e-9)
                return vals[j*nv+theta_index]*(1-f) + vals[(j+1)*nv+theta_index]*f
        return vals[(nh-1)*nv+theta_index]
    flux = 0.0
    for j in range(72):
        da = 2*math.pi/72
        az = (j+0.5)*360/72
        for i in range(nv-1):
            domega = da * (math.cos(math.radians(vertical[i]))-math.cos(math.radians(vertical[i+1])))
            flux += max(0, domega) * (candela(i, az)+candela(i+1, az)) / 2
    return flux * multiplier * data[10]


def ies_nadir(path):
    lines = open(path, encoding="utf-8-sig", errors="replace").read().splitlines()
    tilt = next(i for i, line in enumerate(lines) if line.upper().startswith("TILT="))
    data = [float(v) for v in " ".join(lines[tilt+1:]).replace(",", " ").split()]
    nv, nh = int(data[3]), int(data[4])
    if data[13] != 0 or len(data) < 13+nv+nh+1:
        raise ValueError("IES nadir sample missing: " + path)
    return data[13+nv+nh] * data[2] * data[10]


def add_light(spec, ies_dir):
    kind = spec["type"]
    lamp = bpy.data.lights.new(spec["id"], "POINT" if kind == "ies" else "AREA")
    lamp.color = build_scene.kelvin_to_rgb(spec["cct_k"])
    if kind == "ies":
        path = os.path.abspath(os.path.join(ies_dir, spec["ies"]))
        if not path.startswith(os.path.abspath(ies_dir) + os.sep) or not os.path.isfile(path):
            raise FileNotFoundError(path)
        flux = ies_flux(path)
        lamp.energy = IES_POINT_POWER * spec["lumens"] / flux
        lamp.shadow_soft_size = 0.001
        lamp.use_nodes = True
        nodes = lamp.node_tree.nodes
        tex = nodes.new("ShaderNodeTexIES")
        tex.mode = "EXTERNAL"
        tex.filepath = path
        lamp.node_tree.links.new(tex.outputs["Fac"], nodes["Emission"].inputs["Strength"])
    else:
        lamp.shape = "RECTANGLE"
        lamp.size, lamp.size_y = spec["size"]
        lamp.energy = spec["lumens"]
        lamp.spread = math.radians(spec["spread_deg"])
    obj = bpy.data.objects.new(spec["id"], lamp)
    bpy.context.collection.objects.link(obj)
    obj.location = spec["position"]
    aim = Vector(spec["aim"]).normalized()
    if kind == "ies":
        obj.rotation_euler = aim.to_track_quat("-Z", "Y").to_euler()
        obj.rotation_euler.rotate_axis("Z", math.radians(spec["spin_deg"] + IES_AZIMUTH_OFFSET_DEG))
    else:
        length = Vector(spec["length_dir"])
        length = (length - length.dot(aim)*aim).normalized()
        width = aim.cross(length).normalized()
        # Local X is width, local Y is length, local -Z is emission.
        obj.rotation_euler = Matrix(((width.x, length.x, -aim.x), (width.y, length.y, -aim.y), (width.z, length.z, -aim.z))).to_euler()
    return obj


def configure_camera(view):
    c = view["camera"]
    camera = bpy.data.cameras.new("villa-camera")
    obj = bpy.data.objects.new("villa-camera", camera)
    bpy.context.collection.objects.link(obj)
    obj.location = c["position"]
    direction = Vector(c["target"]) - Vector(c["position"])
    horizontal = Vector((direction.x, direction.y, 0))
    pitch = math.degrees(math.atan2(direction.z, horizontal.length))
    obj.rotation_euler = horizontal.to_track_quat("-Z", "Y").to_euler()
    camera.lens = c["lens_mm"]
    camera.sensor_width = c["sensor_mm"]
    camera.sensor_fit = "HORIZONTAL"
    camera.shift_x = c.get("shift_x", 0)
    camera.shift_y = c.get("shift_y", 0) + direction.z / max(horizontal.length, 1e-9) * camera.lens / camera.sensor_width
    bpy.context.scene.camera = obj
    return obj, pitch


def subjects(view, mesh_specs, objects):
    result = []
    scene = bpy.context.scene
    for subject in view["subjects"]:
        matches = [m for m in mesh_specs if m["id"] == subject or m["id"].startswith(subject) or m.get("room") == subject or m.get("label") == subject]
        coords = [world_to_camera_view(scene, scene.camera, objects[m["id"]].matrix_world @ Vector(corner))
                  for m in matches for corner in contract.mesh_bbox_corners(m)]
        rect = [min((p.x for p in coords), default=0), min((p.y for p in coords), default=0),
                max((p.x for p in coords), default=0), max((p.y for p in coords), default=0)]
        overlap = max(0, min(1, rect[2])-max(0, rect[0])) * max(0, min(1, rect[3])-max(0, rect[1]))
        area = max(1e-9, (rect[2]-rect[0])*(rect[3]-rect[1]))
        visible = bool(coords) and any(p.z >= 0 for p in coords) and overlap > 0
        result.append({"id": subject, "in_frame": visible, "coverage": overlap/area,
                       "screen": rect,
                       "matched_objects": [m["id"] for m in matches]})
    return result


def drape_cloth(cloth_specs, materials):
    """Bedding as cloth (render review: box duvets read as rigid slabs). Each spec is a sheet dropped onto the
    authored bed parts and settled with the bedroom's tested settings (photoreal._grid / _simulate: cotton that
    barely stretches, pinned under the pillows), then given loft and thickness like photoreal.cloth_bedding. The
    bed frame, mattress and footprint are untouched: only the soft goods are simulated."""
    import random
    report = []
    for spec in cloth_specs:
        colliders = [o for o in bpy.data.objects if o.type == "MESH" and
                     any(o.name.startswith(pfx) for pfx in spec["colliders"])]
        sheet = photoreal._grid("cloth-" + spec["id"], spec["size"][0], spec["size"][1],
                                max(8, int(spec["size"][0] / 0.03)), max(8, int(spec["size"][1] / 0.03)),
                                tuple(spec["center"]), spec["z_start"])
        rnd = random.Random(7)
        for v in sheet.data.vertices:
            v.co.z += rnd.uniform(0.0, 0.015)
        pin = spec.get("pin")
        photoreal._simulate(sheet, colliders, spec.get("frames", 50), mass=spec.get("mass", 0.4),
                            bending=spec.get("bending", 0.6), pin_band=tuple(pin) if pin else None)
        if spec.get("loft", 0) > 0:
            tex = bpy.data.textures.new("loft-" + spec["id"], type="CLOUDS")
            tex.noise_scale = 0.55
            disp = sheet.modifiers.new("loft", "DISPLACE")
            disp.texture = tex
            disp.strength = spec["loft"]
            disp.mid_level = 0.3
        solid = sheet.modifiers.new("thickness", "SOLIDIFY")
        solid.thickness = spec.get("thickness", 0.04)
        solid.offset = 1.0
        sub = sheet.modifiers.new("smooth", "SUBSURF")
        sub.levels = sub.render_levels = 1
        sheet.data.materials.append(materials[spec["material"]])
        for poly in sheet.data.polygons:
            poly.use_smooth = True
        pts = [sheet.matrix_world @ v.co for v in sheet.data.vertices]
        report.append({"id": spec["id"], "colliders": len(colliders),
                       "bounds": [round(min(q.x for q in pts), 3), round(min(q.y for q in pts), 3),
                                  round(min(q.z for q in pts), 3), round(max(q.x for q in pts), 3),
                                  round(max(q.y for q in pts), 3), round(max(q.z for q in pts), 3)]})
    return report


def build_curtains(curtain_specs, materials):
    """Sheer + a heavy layer per opening (client 2026-09-28), ported from the bedroom's tested curtain
    (`photoreal.dress_room`, ~919-964: irregular per-pleat depth/phase gathered at the heading and relaxing toward
    the hem -- a pure sine extrusion read as corrugated sheet) and made axis-general (the bedroom's single fixed
    wall) and stateful (an always-open sheer, an open-stacked heavy pair and a separate closed-heavy panel, so
    per-view visibility is a hide, not a rebuild). Colliders are the room's own floor mesh (`villa_render.mesh`
    names it "floor-<room>"); the top is pinned to the track height, so each panel hangs from the track by
    construction and settles onto the floor rather than through it -- the generic float guard never sees these (they
    are not `scene["meshes"]`, exactly like the cloth duvets), so this pin/collide is what keeps them off the
    floor and clear of the ceiling. Returns (objects, report) -- report is the post-simulation world bounds per
    panel (like `drape_cloth`'s bedding report), so a render's own JSON can be read to confirm where a panel
    actually ended up, not just where it was authored to be."""
    import random
    objects = {}
    report = []
    floors = [o for o in bpy.data.objects if o.name.startswith("floor-")]
    for spec in curtain_specs:
        rnd = random.Random(abs(hash(spec["id"])) % (2 ** 31))
        axis = spec["axis"]                                  # "h": opening runs along x, normal along y; "v": along y, normal along x
        cx, cy = spec["center"]                               # the WINDOW LINE -- width-axis anchor only, never the hang depth
        sign = spec["normal_sign"]
        wall_face = spec["wall_face"]                         # clear_rect's room-side boundary (past the wall's full thickness)
        floor_z, track_z = spec["floor_z"], spec["track_z"]
        height = track_z - floor_z - 0.012                   # 12 mm floor clearance (the asked 10-15 mm)
        width, stack = spec["width"], spec["open_stack_m"]
        pier_reach, closed_overlap = spec["open_pier_reach_m"], spec.get("closed_overlap_m", 0.05)
        room_floor = [o for o in floors if o.name == "floor-" + spec["room"]]
        colliders = room_floor or floors

        def panel(name, u0, u1, offset, material_name):
            sx = u1 - u0
            uc = (u0 + u1) / 2.0
            n_u = max(8, int(sx / 0.05))
            grid = photoreal._grid(name, sx, height, n_u, 60, (0.0, 0.0), 0.0)
            pleats = 7
            depth = [0.035 * rnd.uniform(0.6, 1.4) for _ in range(pleats + 1)]
            phase = [rnd.uniform(-0.35, 0.35) for _ in range(pleats + 1)]
            for v_ in grid.data.vertices:
                u = (v_.co.x + sx / 2.0) / sx
                t = (v_.co.y + height / 2.0) / height        # 0 = hem, 1 = the gathered heading at the track
                k = min(pleats, int(u * pleats))
                relax = 0.55 + 0.45 * t
                wave = depth[k] * relax * math.sin((u * pleats + phase[k]) * 2.0 * math.pi)
                # `offset` is an ABSOLUTE world coordinate along the perpendicular (hang-depth) axis -- built from
                # `wall_face` below, never from cy/cx here. u0/u1 (and so uc) ARE opening-relative along the WIDTH
                # axis, so that one still needs cx/cy added. (Earlier bug, fixed: leaving cx/cy out of the width
                # axis placed every curtain in the whole villa near world origin -- invisible in both rendered
                # views, found only by reading the render's own JSON. Separately, the lead's review caught the
                # depth axis hanging inside the wall/reveal because it was offset from the window line, not from
                # `wall_face`.)
                local_u, local_off, local_z = v_.co.x, offset + sign * wave, floor_z + 0.006 + t * height
                v_.co = Vector((cx + uc + local_u, local_off, local_z)) if axis == "h" else \
                    Vector((local_off, cy + uc + local_u, local_z))
            photoreal._simulate(grid, colliders, 60, mass=0.30, bending=0.35,
                                pin_band=("z", floor_z + 0.006 + height, 0.02))
            solid = grid.modifiers.new("thickness", "SOLIDIFY")
            solid.thickness = 0.004
            grid.modifiers.new("smooth", "SUBSURF").levels = 1
            grid.data.materials.append(materials[material_name])
            for p_ in grid.data.polygons:
                p_.use_smooth = True
            return grid

        # Lead review (draft render 1): hang from the ROOM side of the wall's inner face, not a few cm off the
        # window line (which is still inside the wall thickness, behind detail-window-frames and the reveal --
        # the closed curtain read as hanging inside the window, split by the mullion). Sheer 0.10 m and heavy
        # 0.15 m past `wall_face`, both within the client's stated 0.10-0.15 m band.
        sheer_off, heavy_off = wall_face + sign * 0.10, wall_face + sign * 0.15
        half = width / 2.0
        # Each stack is anchored to the OUTER end of its track extension (half + pier_reach) and extends inward by
        # `stack` (villa_render's STACK_RATIO x width, clamped for a door so F.BODY stays clear -- see
        # villa_render.py's curtain loop), so when stack > pier_reach its innermost edge crosses half: exactly the
        # "rest overlaps the glazing edge" the lead asked for, on the SAME rail (a real short-pier stacking
        # curtain). The old flat 0.14 m cap treated any overlap as a defect; it wasn't -- only a passable clear
        # width through a DOOR is (villa_render's `open_clear_width_m`, checked in
        # test_curtain_clear_width_through_doors, not by the generic render_support.blocked_openings, which has
        # no notion of "clear width" and would flag this overlap by design).
        panels = [
            panel(spec["id"] + "-sheer-l", -half - pier_reach, -half - pier_reach + stack, sheer_off, spec["sheer_material"]),
            panel(spec["id"] + "-sheer-r", half + pier_reach - stack, half + pier_reach, sheer_off, spec["sheer_material"]),
            panel(spec["id"] + "-heavy-open-l", -half - pier_reach, -half - pier_reach + stack, heavy_off, spec["heavy_material"]),
            panel(spec["id"] + "-heavy-open-r", half + pier_reach - stack, half + pier_reach, heavy_off, spec["heavy_material"]),
            panel(spec["id"] + "-heavy-closed", -half - closed_overlap, half + closed_overlap, heavy_off, spec["heavy_material"]),
        ]
        for obj in panels:
            objects[obj.name] = obj
            pts = [obj.matrix_world @ vv.co for vv in obj.data.vertices]
            bx = (round(min(p.x for p in pts), 3), round(min(p.y for p in pts), 3), round(min(p.z for p in pts), 3),
                 round(max(p.x for p in pts), 3), round(max(p.y for p in pts), 3), round(max(p.z for p in pts), 3))
            # Post-condition (the missing-cx/cy bug above was invisible to every existing test, since a
            # dropped-translation bug still produces a perfectly valid, contract-shaped mesh): the panel must
            # actually be near its own opening, not near world origin or another room.
            if abs((bx[0] + bx[3]) / 2 - cx) > 2.0 or abs((bx[1] + bx[4]) / 2 - cy) > 2.0:
                raise ValueError("%s centred at (%.2f, %.2f), far from its opening at (%.2f, %.2f)" %
                                 (obj.name, (bx[0] + bx[3]) / 2, (bx[1] + bx[4]) / 2, cx, cy))
            report.append({"id": obj.name, "bounds": list(bx)})
    return objects, report


def import_props(prop_specs, library_root):
    """Transform each complete asset around one shared origin, then seat it."""
    imported = []
    for spec in prop_specs:
        from archpipe.asset_intake import require_registered_asset
        from pathlib import Path
        require_registered_asset(spec["asset"], Path(__file__).resolve().parents[3] / "ops/workstation/library-manifest.json",
                                 Path(library_root) / "props" / spec["asset"] / "model.gltf")
        before = set(bpy.data.objects)
        path = os.path.join(library_root, "props", spec["asset"], "model.gltf")
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
        bpy.ops.import_scene.gltf(filepath=path)
        new = [obj for obj in bpy.data.objects if obj not in before]
        meshes = [obj for obj in new if obj.type == "MESH"]
        if not meshes:
            raise FileNotFoundError(os.path.join(library_root, "props", spec["asset"], "model.gltf"))
        roots = [obj for obj in new if obj.parent is None]
        # Multi-part pots have translated roots. Scaling those independently
        # leaves component offsets unscaled and separates the leaves/soil/pot.
        anchor = bpy.data.objects.new("prop-anchor-" + spec["id"], None)
        bpy.context.collection.objects.link(anchor)
        for root in roots:
            root.parent = anchor
        anchor.rotation_mode = "XYZ"
        anchor.rotation_euler = tuple(math.radians(v) for v in spec["rotation_deg"])
        scale = spec["scale"]
        anchor.scale = (scale,) * 3 if isinstance(scale, (int, float)) else tuple(scale)
        anchor.location = (spec["position"][0], spec["position"][1], 0)
        bpy.context.view_layer.update()
        bottom = min((obj.matrix_world @ Vector(corner)).z for obj in meshes for corner in obj.bound_box)
        anchor.location.z += spec["position"][2] - bottom
        bpy.context.view_layer.update()
        for index, obj in enumerate(new):
            obj.name = "prop-%s-%03d" % (spec["id"], index)
        imported.append({"id": spec["id"], "asset": spec["asset"], "label": spec["label"],
                         "objects": meshes})
    return imported


def import_models(model_specs, library_root):
    """Import complete glTF products at one uniform scale, centred and seated on the floor."""
    imported = []
    for spec in model_specs:
        from archpipe.asset_intake import require_registered_asset
        from pathlib import Path
        require_registered_asset(spec["asset"], Path(__file__).resolve().parents[3] / "ops/workstation/library-manifest.json",
                                 Path(library_root) / "props" / spec["asset"] / "model.gltf")
        from archpipe.furniture_orientation import check_model_orientation
        check_model_orientation(spec)
        before = set(bpy.data.objects)
        path = os.path.join(library_root, "props", spec["asset"], "model.gltf")
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
        bpy.ops.import_scene.gltf(filepath=path)
        new = [obj for obj in bpy.data.objects if obj not in before]
        meshes = [obj for obj in new if obj.type == "MESH"]
        if not meshes:
            raise ValueError("model has no meshes: " + spec["asset"])
        anchor = bpy.data.objects.new("model-anchor-" + spec["id"], None)
        bpy.context.collection.objects.link(anchor)
        for root in (obj for obj in new if obj.parent is None):
            root.parent = anchor
        anchor.rotation_mode = "XYZ"
        anchor.rotation_euler = tuple(math.radians(v) for v in spec["rotation_deg"])
        anchor.scale = (spec["scale"],) * 3
        bpy.context.view_layer.update()
        def corners():
            return [obj.matrix_world @ Vector(c) for obj in meshes for c in obj.bound_box]
        xyz = corners()
        anchor.location = (spec["position"][0] - (min(v.x for v in xyz) + max(v.x for v in xyz))/2,
                           spec["position"][1] - (min(v.y for v in xyz) + max(v.y for v in xyz))/2,
                           spec["position"][2] - min(v.z for v in xyz))
        bpy.context.view_layer.update()
        total_faces = sum(len(obj.data.polygons) for obj in meshes)
        asset_ratio = min(1.0, 500000 / max(total_faces, 1))
        for obj in meshes:
            faces = len(obj.data.polygons)
            ratio = min(spec.get("decimate_ratio", 1.0), asset_ratio)
            if ratio < 1.0 and faces > 10:
                mod = obj.modifiers.new("bounded product decimation", "DECIMATE")
                mod.ratio = ratio
            obj.name = "model-%s-%s" % (spec["id"], obj.name)
        xyz = corners()
        box = (min(v.x for v in xyz), min(v.y for v in xyz), min(v.z for v in xyz),
               max(v.x for v in xyz), max(v.y for v in xyz), max(v.z for v in xyz))
        if "footprint_w" in spec:
            if box[3]-box[0] > spec["footprint_w"] + 0.020 or box[4]-box[1] > spec["footprint_d"] + 0.020:
                raise ValueError("model exceeds product footprint: " + spec["id"])
            if abs((box[5]-box[2]) / spec["reference_h"] - 1) > 0.05:
                raise ValueError("model height exceeds five percent tolerance: " + spec["id"])
        imported.append({"id": spec["id"], "asset": spec["asset"], "bounds": box, "objects": meshes})
    return imported


def visible_props(imported):
    scene = bpy.context.scene
    records = []
    for prop in imported:
        coords = [world_to_camera_view(scene, scene.camera, obj.matrix_world @ Vector(corner))
                  for obj in prop["objects"] for corner in obj.bound_box]
        x0 = min((p.x for p in coords), default=0)
        y0 = min((p.y for p in coords), default=0)
        x1 = max((p.x for p in coords), default=0)
        y1 = max((p.y for p in coords), default=0)
        overlap = max(0, min(1, x1)-max(0, x0)) * max(0, min(1, y1)-max(0, y0))
        records.append({"id": prop["id"], "asset": prop["asset"], "label": prop["label"],
                        "objects": [obj.name for obj in prop["objects"]],
                        "in_frame": overlap > 0 and any(p.z >= 0 for p in coords),
                        "screen": [x0, y0, x1, y1]})
    return records


def configure_cycles(cpu):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    if not cpu:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for backend in ("OPTIX", "CUDA"):
            try:
                prefs.get_devices()
                prefs.compute_device_type = backend
                devices = prefs.get_devices_for_type(backend)
                if devices:
                    for device in devices:
                        device.use = device.type != "CPU"
                    scene.cycles.device = "GPU"
                    break
            except Exception:
                pass
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = "OPENIMAGEDENOISE"
    scene.cycles.use_light_tree = True
    scene.render.use_persistent_data = True
    # This scene uses calibrated lumen units. Clamping at Blender's default
    # 10 discards the bounced energy that lights deep interiors (the same
    # measured trap already handled by build_scene.configure_render).
    scene.cycles.sample_clamp_indirect = 0
    scene.cycles.sample_clamp_direct = 0
    scene.cycles.diffuse_bounces = 16
    scene.cycles.glossy_bounces = 8
    scene.cycles.transmission_bounces = 16
    scene.cycles.transparent_max_bounces = 16
    scene.cycles.max_bounces = 16


def calibrate(scene_data, args):
    """Measure IES lux, EV100 response and an 800-lumen emitting sphere."""
    bpy.context.scene.render.use_persistent_data = False
    ies = next((l for l in scene_data["lights"] if l["type"] == "ies"), None)
    if ies is None:
        raise ValueError("--calibrate requires an IES light for the baseline probe")
    path = os.path.join(args.ies_dir, ies["ies"])
    height = ies["position"][2]
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.mesh.primitive_plane_add(size=0.4)
    card = bpy.context.object
    mat = bpy.data.materials.new("calibration Lambert card")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    diffuse = nodes.new("ShaderNodeBsdfDiffuse")
    diffuse.inputs["Color"].default_value = (0.5, 0.5, 0.5, 1)
    out = nodes.new("ShaderNodeOutputMaterial")
    mat.node_tree.links.new(diffuse.outputs["BSDF"], out.inputs["Surface"])
    card.data.materials.append(mat)
    lamp = add_light(ies, args.ies_dir)
    lamp.location = (0, 0, height)
    lamp.rotation_euler = Vector((0, 0, -1)).to_track_quat("-Z", "Y").to_euler()
    lamp.rotation_euler.rotate_axis("Z", math.radians(IES_AZIMUTH_OFFSET_DEG))
    cam_data = bpy.data.cameras.new("calibration camera")
    cam = bpy.data.objects.new("calibration camera", cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = (0, 0, 1)
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = 0.3
    s = bpy.context.scene
    s.camera = cam
    world = bpy.data.worlds.new("calibration black")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0
    s.world = world
    s.cycles.max_bounces = 0
    s.cycles.use_denoising = False
    s.cycles.samples = 512
    s.render.resolution_x = s.render.resolution_y = 64
    s.render.image_settings.file_format = "OPEN_EXR"
    s.render.image_settings.color_depth = "32"
    s.view_settings.view_transform = "Standard"
    s.view_settings.exposure = 0
    exr = os.path.join(args.out, "calibration.exr")
    s.render.filepath = exr
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(exr)
    pixel = [img.pixels[4*(32*64+32)+i] for i in range(3)]
    bpy.data.images.remove(img)
    measured = luminance(pixel) * math.pi / 0.5
    analytic = ies_nadir(path) * ies["lumens"] / ies_flux(path) / (height*height)
    diffuse.inputs["Color"].default_value = (1, 1, 1, 1)
    ev = math.log2(analytic / 2.5)
    s.view_settings.view_transform = "AgX"
    s.view_settings.look = "AgX - Medium High Contrast"
    s.view_settings.exposure = math.log2(math.pi / (2.5*2**ev))
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_depth = "8"
    png = os.path.join(args.out, "calibration.png")
    s.render.filepath = png
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(png)
    display = [img.pixels[4*(32*64+32)+i] for i in range(3)]
    bpy.data.images.remove(img)
    lamp_data = lamp.data
    bpy.data.objects.remove(lamp, do_unlink=True)
    bpy.data.lights.remove(lamp_data)
    diffuse.inputs["Color"].default_value = (0.5, 0.5, 0.5, 1)
    radius = 0.15
    total_lumens = 800.0
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=radius, location=(0, 0, height))
    sphere = bpy.context.object
    area = sum(face.area for face in sphere.data.polygons)
    exitance = total_lumens / area
    sphere.data.materials.append(add_material("calibration emissive sphere", {
        "kind": "emissive", "base_rgb": [1, 1, 1], "cct_k": ies["cct_k"],
        "emission_lm_per_m2": exitance}, "", []))
    if hasattr(sphere, "cycles") and hasattr(sphere.cycles, "use_multiple_importance_sampling"):
        sphere.cycles.use_multiple_importance_sampling = True
    s.view_settings.view_transform = "Standard"
    s.view_settings.exposure = 0
    s.cycles.sample_clamp_indirect = 0
    s.render.image_settings.file_format = "OPEN_EXR"
    s.render.image_settings.color_depth = "32"
    sphere_exr = os.path.join(args.out, "calibration-emissive.exr")
    s.render.filepath = sphere_exr
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(sphere_exr)
    sphere_pixel = [img.pixels[4*(32*64+32)+i] for i in range(3)]
    bpy.data.images.remove(img)
    sphere_measured = luminance(sphere_pixel) * math.pi / 0.5
    distance = height  # The probe is directly below the sphere centre.
    sphere_analytic = (total_lumens / (4 * math.pi)) * height / distance**3
    # ---- glass probe: direct sun through one single-sheet pane (interfaces 1) and through a closed slab
    # (interfaces 2) must transmit exactly the stated Tv. The camera sits BETWEEN the card and the glass, so its own
    # rays never cross the glass; only the light's shadow rays do.
    sphere_data = sphere.data
    bpy.data.objects.remove(sphere, do_unlink=True)
    bpy.data.meshes.remove(sphere_data)
    sun_data = bpy.data.lights.new("glass probe sun", "SUN")
    sun_data.energy = 10.0
    sun_data.angle = 0.0
    sun = bpy.data.objects.new("glass probe sun", sun_data)
    bpy.context.collection.objects.link(sun)
    sun.rotation_euler = (0, 0, 0)                       # pointing straight down
    cam.location = (0, 0, 0.3)
    s.cycles.max_bounces = 0

    def read_card(tag):
        path_ = os.path.join(args.out, "calibration-glass-%s.exr" % tag)
        s.render.filepath = path_
        bpy.ops.render.render(write_still=True)
        im = bpy.data.images.load(path_)
        px = [im.pixels[4*(32*64+32)+i] for i in range(3)]
        bpy.data.images.remove(im)
        return luminance(px)

    open_sky = read_card("open")
    glass_report = {}
    for tag, interfaces, tv, solid in (("sheet", 1, 0.70, False), ("slab", 2, 0.85, True)):
        spec = {"kind": "glass", "base_rgb": [1, 1, 1], "transmittance": tv, "interfaces": interfaces,
                "roughness": 0.0}
        gmat = add_material("probe glass " + tag, spec, "", [])
        if solid:
            bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0.6))
            pane = bpy.context.object
            pane.scale = (1.0, 1.0, 0.003)
        else:
            bpy.ops.mesh.primitive_plane_add(size=2.0, location=(0, 0, 0.6))
            pane = bpy.context.object
        pane.data.materials.append(gmat)
        configure_glass({"probe glass " + tag: gmat}, {"probe glass " + tag: spec})
        through = read_card(tag)
        glass_report[tag] = {"interfaces": interfaces, "stated_tv": tv, "measured_tv": through / open_sky,
                             "within_0_03": abs(through / open_sky - tv) <= 0.03}
        pane_data = pane.data
        bpy.data.objects.remove(pane, do_unlink=True)
        bpy.data.meshes.remove(pane_data)
    report = {"analytic_direct_lux": analytic, "blender_direct_lux": measured,
              "glass_probe": glass_report,
              "relative_error": abs(measured-analytic)/analytic, "ev100": ev,
              "exposure_stops": s.view_settings.exposure,
              "white_card_display_luminance": luminance(display),
              "white_card_scene_linear_target": 1.0,
              "emissive_sphere": {"diameter_m": 2*radius, "mesh_area_m2": area,
                                   "total_lumens": total_lumens, "exitance_lm_per_m2": exitance,
                                   "emission_strength": contract.emission_strength(exitance),
                                   "analytic_point_lux": sphere_analytic,
                                   "blender_direct_lux": sphere_measured,
                                   "relative_error": abs(sphere_measured-sphere_analytic)/sphere_analytic,
                                   "within_10_percent": abs(sphere_measured-sphere_analytic)/sphere_analytic <= 0.10,
                                   "light_tree": s.cycles.use_light_tree}}
    with open(os.path.join(args.out, "calibration.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print("VILLA RENDER calibration " + json.dumps(report), flush=True)


def measure_lighting(scene_data, args, lights, full_power, emissive_sources, mesh_by_id, switched_emitters):
    """Read maintained horizontal illuminance from the furnished scene.

    Each tiny diffuse sensor has reflectance 0.5. Its linear radiance times
    pi divided by 0.5 gives illuminance in the independently calibrated lux
    units. No display exposure, white balance, denoising or ambient sky is
    applied. Direct and reflected-light results are separate. These are
    predictions for the authored fixtures and materials, not installed tests.
    """
    points = scene_data.get("measurement_points", [])
    if not points:
        raise ValueError("No measurement_points authored")
    s = bpy.context.scene
    maintenance = scene_data["measurement_maintenance_factor"]
    layers = ["ambient", "task", "accent", "decorative"]
    view = {"layers_on": layers, "dimmers": {layer: maintenance for layer in layers}}
    set_emissive_view(emissive_sources, mesh_by_id, switched_emitters, view)
    for spec in scene_data["lights"]:
        obj = lights[spec["id"]]
        obj.data.energy = full_power[spec["id"]] * maintenance if spec["layer"] in layers else 0
        obj.hide_render = obj.data.energy <= 0
    world = bpy.data.worlds.new("villa measurement black sky")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0
    s.world = world
    s.cycles.use_denoising = False
    s.cycles.samples = args.samples or 256
    s.render.resolution_x = s.render.resolution_y = 32
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = "OPEN_EXR"
    s.render.image_settings.color_depth = "32"
    s.view_settings.view_transform = "Standard"
    s.view_settings.look = "None"
    s.view_settings.exposure = 0
    if hasattr(s.view_settings, "use_white_balance"):
        s.view_settings.use_white_balance = False
    material = bpy.data.materials.new("villa diffuse sensor 0.5")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    diffuse = nodes.new("ShaderNodeBsdfDiffuse")
    diffuse.inputs["Color"].default_value = (0.5, 0.5, 0.5, 1)
    output = nodes.new("ShaderNodeOutputMaterial")
    material.node_tree.links.new(diffuse.outputs[0], output.inputs["Surface"])
    bpy.ops.mesh.primitive_plane_add(size=0.04)
    sensor = bpy.context.object
    sensor.name = "villa measurement sensor"
    sensor.data.materials.append(material)
    camera_data = bpy.data.cameras.new("villa measurement camera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 0.02
    # the camera is 25 mm over the sensor: Blender's default near clip (100 mm) hid the sensor, so the camera saw
    # the inside of the worktop / desk 100 mm below (0 lx at every task point on a surface; found 2026-09-27)
    camera_data.clip_start = 0.001
    camera_data.clip_end = 0.1
    camera = bpy.data.objects.new("villa measurement camera", camera_data)
    bpy.context.collection.objects.link(camera)
    s.camera = camera
    records = []
    for index, point in enumerate(points):
        x, y, z = point["position"]
        sensor.location = (x, y, z + 0.001)
        camera.location = (x, y, z + 0.025)
        record = dict(point)
        for mode, bounces in (("direct", 0), ("total", 16)):
            s.cycles.max_bounces = bounces
            path = os.path.join(args.out, "probe-%02d-%s.exr" % (index, mode))
            s.render.filepath = path
            bpy.ops.render.render(write_still=True)
            image = bpy.data.images.load(path)
            pixels = image.pixels[:]
            radiances = [luminance(pixels[4*(y*32+x):4*(y*32+x)+3])
                         for y in range(8, 24) for x in range(8, 24)]
            record[mode + "_lux"] = sum(radiances) / len(radiances) * math.pi / 0.5
            bpy.data.images.remove(image)
        record["meets_target"] = record["total_lux"] >= point["required_lux"]
        records.append(record)
    result = {"maintenance_factor": maintenance, "sky": "off", "dimming": "all functional layers at full output",
              "method": "0.5-reflectance sensor; linear radiance times pi / 0.5; 1 mm above task plane",
              "occlusion": "actual scene geometry", "samples": s.cycles.samples,
              "assumptions": scene_data["notes"], "points": records,
              "all_targets_met": all(r["meets_target"] for r in records)}
    with open(os.path.join(args.out, "lighting-measurements.json"), "w", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)


def render(scene_data, args):
    os.makedirs(args.out, exist_ok=True)
    if args.views == "none" and not (args.calibrate or args.measure_lighting):
        raise ValueError("--views none requires --calibrate or --measure-lighting")
    if args.views == "none" and args.calibrate:
        configure_cycles(args.cpu)
        calibrate(scene_data, args)
        return
    warnings = []
    library_root = os.path.expandvars(os.path.expanduser(args.library_root or scene_data["library_root"]))
    materials = {name: add_material(name, spec, library_root, warnings) for name, spec in scene_data["materials"].items()}
    configure_glass(materials, scene_data["materials"])
    objects = build_meshes(scene_data["meshes"], materials, scene_data["materials"], warnings)
    build_climbers(scene_data["meshes"], objects, materials, warnings)
    switched_emitters = layered_emissive_materials(scene_data["meshes"], objects, scene_data["materials"])
    emissive_sources = []
    for spec in scene_data["meshes"]:
        mat_spec = scene_data["materials"][spec["material"]]
        if mat_spec["kind"] == "emissive":
            area = sum(face.area for face in objects[spec["id"]].data.polygons)
            emissive_sources.append({"id": spec["id"], "layer": spec.get("layer"), "area_m2": area,
                                     "exitance_lm_per_m2": mat_spec["emission_lm_per_m2"],
                                     "emitted_lumens": area * mat_spec["emission_lm_per_m2"]})
    cloth_report = drape_cloth(scene_data.get("cloth", []), materials)
    # Curtains (client 2026-09-28) are cloth-simulated like the duvets above, not static meshes; their objects are
    # merged into `objects` so the per-view hide mechanism below (villa_render's authored hide_meshes, the same
    # doorway-open-door path) can toggle the heavy layer's open/closed pair per view.
    curtain_objects, curtain_report = build_curtains(scene_data.get("curtains", []), materials)
    objects.update(curtain_objects)
    imported_props = import_props(scene_data.get("props", []), library_root)
    imported_models = import_models(scene_data.get("models", []), library_root)
    lights = {l["id"]: add_light(l, args.ies_dir) for l in scene_data["lights"]}
    full_power = {ident: obj.data.energy for ident, obj in lights.items()}
    mesh_by_id = {mesh["id"]: mesh for mesh in scene_data["meshes"]}
    configure_cycles(args.cpu)
    if args.measure_lighting:
        measure_lighting(scene_data, args, lights, full_power, emissive_sources, mesh_by_id, switched_emitters)
        return
    selected = {v["id"] for v in scene_data["views"]} if args.views == "all" else set(args.views.split(","))

    hideable = {m for v in scene_data["views"] for m in v.get("hide_meshes", [])}

    def setup_view(view):
        for mid in hideable:                     # a door opened for a doorway camera, in that view only
            objects[mid].hide_render = mid in view.get("hide_meshes", [])
        for spec in scene_data["lights"]:
            obj = lights[spec["id"]]
            factor = (view.get("dimmers", {}).get(spec["layer"], 1.0) * spec.get("dimmer", 1.0)) if spec["layer"] in view["layers_on"] else 0
            obj.data.energy = full_power[spec["id"]] * factor
            obj.hide_render = factor <= 0
        emissive = set_emissive_view(emissive_sources, mesh_by_id, switched_emitters, view)
        if view["state"] == "day":
            sun = view["sun"]
            photoreal.daylight_world(sun["altitude_deg"], sun["azimuth_true_deg"] - scene_data["north"]["model_y_bearing_deg"])
        else:
            sky_state = contract.sky_state_for_view(view["state"])
            sky = scene_data["sky"][sky_state]
            hdri = os.path.join(library_root, "hdri", sky["hdri"])
            if not os.path.isfile(hdri):
                raise FileNotFoundError(hdri)
            photoreal.hdri_world(hdri, sky["horizontal_lux"])
        return emissive

    # ADR-0013 part 6, the bedroom standard: meter every view with photoreal.camera_meter (fast pre-render,
    # log-average luminance, top 3 % excluded, highlight priority, -0.4 stop bias), then LOCK one exposure per
    # state (the median of its views) so rooms still compare honestly (ADR-0013 amendment).
    locked, metered = {}, {}
    if scene_data.get("exposure_mode") == "set-metered":
        by_state = {}
        for view in scene_data["views"]:
            if view["id"] not in selected:
                continue
            setup_view(view)
            cam_, _ = configure_camera(view)
            s0 = bpy.context.scene
            s0.render.resolution_x, s0.render.resolution_y = args.res or view["resolution"]
            s0.view_settings.view_transform = "AgX"
            s0.view_settings.look = "AgX - Medium High Contrast"
            ev, logavg = photoreal.camera_meter(bias_stops=-0.4, look="AgX - Medium High Contrast")
            metered[view["id"]] = {"exposure_stops": ev, "log_average": logavg}
            by_state.setdefault(view["exposure"], []).append(ev)
            cdata = cam_.data
            bpy.data.objects.remove(cam_, do_unlink=True)
            bpy.data.cameras.remove(cdata)
        for key, evs in by_state.items():
            evs = sorted(evs)
            locked[key] = evs[len(evs) // 2]
    for view in scene_data["views"]:
        if view["id"] not in selected:
            continue
        current_warnings = list(warnings)
        current_emissive = setup_view(view)
        camera, pitch = configure_camera(view)
        s = bpy.context.scene
        s.render.resolution_x, s.render.resolution_y = args.res or view["resolution"]
        s.render.resolution_percentage = 100
        s.cycles.samples = args.samples or view["samples"]
        s.cycles.max_bounces = view.get("max_bounces", 16)
        preset = scene_data["exposure"][view["exposure"]]
        s.view_settings.view_transform = "AgX"
        s.view_settings.look = "AgX - Medium High Contrast"
        if view["exposure"] in locked:
            s.view_settings.exposure = locked[view["exposure"]]
        else:
            s.view_settings.exposure = math.log2(math.pi / (2.5 * 2**preset["ev100"]))
        locked_ev100 = math.log2(math.pi / (2.5 * 2 ** s.view_settings.exposure))
        wb = photoreal.white_balance(preset["white_balance_k"])
        if not wb:
            current_warnings.append("Blender does not support stated white balance")
        bpy.context.view_layer.update()
        subject_result = subjects(view, scene_data["meshes"], objects)
        prop_result = visible_props(imported_props)
        path = os.path.join(args.out, view["id"] + ".png")
        s.render.filepath = path
        s.render.image_settings.file_format = "PNG"
        started = time.monotonic()
        bpy.ops.render.render(write_still=True)
        elapsed = time.monotonic() - started
        image = bpy.data.images.load(path)
        pixels = image.pixels[:]
        n = len(pixels)//4
        clipped = sum(1 for i in range(n) if max(pixels[4*i:4*i+3]) >= 0.995)/max(n, 1)
        mean = sum(luminance(pixels[4*i:4*i+3]) for i in range(n))/max(n, 1)
        bpy.data.images.remove(image)
        # ONE render, developed twice: the fixed-EV image above (compares rooms honestly) and a metered one (what
        # an eye adapted to the room would see). The linear EXR is kept, so both are exposures of the same light.
        result = bpy.data.images["Render Result"]
        exr = os.path.join(args.out, view["id"] + ".exr")
        s.render.image_settings.file_format = "OPEN_EXR"
        s.render.image_settings.color_depth = "32"
        result.save_render(exr, scene=s)
        lin = bpy.data.images.load(exr)
        lp = lin.pixels[:]
        lums = sorted(luminance(lp[4*i:4*i+3]) for i in range(0, len(lp)//4, 7))
        bpy.data.images.remove(lin)
        keep = lums[:max(1, int(len(lums) * 0.99))]                   # the brightest 1 % (sky, lamps) excluded
        log_avg = math.exp(sum(math.log(max(v, 1e-6)) for v in keep) / len(keep))
        s.render.image_settings.file_format = "PNG"
        s.render.image_settings.color_depth = "8"
        # QA provenance: screen windows are projected from the actual glass
        # faces; cloth bounds are read after simulation, not from the cut.
        windows = []
        if view["state"] == "day":
            origin = camera.matrix_world.translation
            depsgraph = bpy.context.view_layer.depsgraph
            for spec in scene_data["meshes"]:
                if spec["material"] != "glass-clear" or spec["id"] in view.get("hide_meshes", []):
                    continue
                for k, face in enumerate(spec["faces"]):
                    points = [world_to_camera_view(s, camera, Vector(p)) for p in face]
                    if not points or any(p.z <= 0 for p in points):
                        continue
                    # Projected does not mean visible: a pane in the next
                    # room must not make the image checker sample a wall.
                    centre = sum((Vector(p) for p in face), Vector()) / len(face)
                    samples = [centre] + [centre * 0.5 + Vector(p) * 0.5 for p in face]
                    visible = False
                    for target in samples:
                        ray = target - origin
                        hit, location, _normal, _index, obj, _matrix = s.ray_cast(
                            depsgraph, origin, ray.normalized(), distance=ray.length + 0.02)
                        if hit and obj.name == objects[spec["id"]].name and (location - target).length < 0.03:
                            visible = True
                            break
                    if not visible:
                        continue
                    rect = [max(0, min(p.x for p in points)), max(0, min(p.y for p in points)),
                            min(1, max(p.x for p in points)), min(1, max(p.y for p in points))]
                    if rect[2] - rect[0] >= 0.03 and rect[3] - rect[1] >= 0.03:
                        windows.append({"id": spec["id"] + "-" + str(k), "screen": rect})
        qa_materials = [{"name": name, "note": mat.get("note", ""), "override": "base_rgb" in mat,
                         "luminance": luminance(mat.get("base_rgb", [0, 0, 0])),
                         "glass": mat["kind"] == "glass", "photo": bool(mat.get("asset")),
                         "saturation": max(mat.get("base_rgb", [0, 0, 0])) - min(mat.get("base_rgb", [0, 0, 0]))}
                        for name, mat in scene_data["materials"].items()]
        textile_names = {"boucle", "linen", "sage-fabric", "taupe-fabric", "charcoal-fabric",
                         "bedding-white", "throw-taupe", "rug", "outdoor-fabric", "leather-brown"}
        qa_textiles = [{"name": name, "reflectance": scene_data["materials"][name].get("reflectance")}
                       for name in sorted(textile_names & scene_data["materials"].keys())]
        cloth_specs = {c["id"]: c for c in scene_data.get("cloth", [])}
        qa_bedding = []
        for record in cloth_report:
            spec = cloth_specs[record["id"]]
            if not record["id"].startswith("duvet-"):
                continue
            axis = 0 if spec["length_axis"] == "x" else 1
            bounds = record["bounds"]
            qa_bedding.append({"id": record["id"], "mattress_y": spec["mattress_span"],
                               "duvet_y": [bounds[axis], bounds[axis + 3]],
                               "duvet_z_min": bounds[2]})
        report = {"view": view["id"], "state": view["state"], "samples": s.cycles.samples,
                  "resolution": [s.render.resolution_x, s.render.resolution_y], "render_seconds": elapsed,
                  "lights_on_count": sum(not obj.hide_render for obj in lights.values()), "subjects": subject_result,
                  "imported_props": prop_result,
                  "imported_models": [{"id": m["id"], "asset": m["asset"], "bounds": m["bounds"]}
                                      for m in imported_models], "cloth": cloth_report,
                  "curtains": [dict(r, hidden=objects[r["id"]].hide_render) for r in curtain_report],
                  "mesh_object_count": len(set(objects.values())),
                  "emissive_sources": current_emissive,
                  "max_bounces": s.cycles.max_bounces, "clamp_indirect": s.cycles.sample_clamp_indirect,
                  "clipped_pixel_fraction": clipped, "mean_luminance": mean, "ev100": preset["ev100"],
                  "locked_ev100": locked_ev100, "view_meter": metered.get(view["id"]),
                  "exposure_locked_per_state": bool(locked), "log_average_linear": log_avg,
                  "exposure_stops": s.view_settings.exposure, "white_balance_applied": wb,
                  "camera_pitch_deg": pitch, "warnings": current_warnings}
        architectural_glass = sum(name == "glass-clear" and spec["kind"] == "glass" and
                                  any(node.type == "BSDF_TRANSPARENT" for node in materials[name].node_tree.nodes)
                                  for name, spec in scene_data["materials"].items())
        report["qa_scene"] = {"windows": windows,
                              "glass": {"architectural": architectural_glass},
                              "materials": qa_materials, "textiles": qa_textiles,
                              "soft_goods": [{"name": c["id"], "simulated": c["colliders"] > 0}
                                             for c in cloth_report], "bedding": qa_bedding}
        with open(os.path.join(args.out, view["id"] + ".json"), "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print("VILLA RENDER wrote " + path, flush=True)
        camera_data = camera.data
        bpy.data.objects.remove(camera, do_unlink=True)
        bpy.data.cameras.remove(camera_data)
        for unused in list(bpy.data.images):
            if unused.users == 0 and unused.source == "FILE" and unused.filepath:
                bpy.data.images.remove(unused)
    if args.calibrate:
        calibrate(scene_data, args)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", required=True)
    ap.add_argument("--views", default="all")
    ap.add_argument("--out", required=True)
    ap.add_argument("--ies-dir", required=True)
    ap.add_argument("--library-root")
    ap.add_argument("--samples", type=int)
    ap.add_argument("--res", type=lambda s: [int(v) for v in s.lower().split("x")])
    ap.add_argument("--cpu", action="store_true")
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--measure-lighting", action="store_true")
    args = ap.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    with open(args.scene, encoding="utf-8") as f:
        render(json.load(f), args)


if __name__ == "__main__":
    main()
