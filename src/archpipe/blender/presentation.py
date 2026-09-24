"""Presentation-quality geometry and materials for ACTUAL extracted Revit content.

Runs INSIDE Blender's own bundled Python, alongside `build_scene.py`. It must
not import `archpipe`, `build_scene`, or any third-party package -- only
`bpy` and `mathutils`, so it stays usable regardless of how the caller wires
the two files together.

UNITS: `build_scene.py` extracts are millimetres; Blender is metres. Mesh
vertices handed to `build_items` are WORLD millimetres (already positioned
and rotated by Revit), so the conversion to metres happens exactly once,
here, and the resulting objects keep an identity transform (location 0,
rotation 0, scale 1) -- applying the extract's own placement a second time
would double it.

Two entry points:

* `build_items()` turns `meshes` entries in the extract into real geometry
  with real materials, and reports which items had none so the caller can
  fall back to a proxy (this module never invents a substitute box).
* `enhance_finishes()` adds non-destructive procedural detail (grain, plank
  joints, weave, bump) to materials that `build_scene.finish_surface` and
  `build_items` already created, and returns what it did so the render log
  can state the assumptions rather than bury them in a node tree.

Abbreviations used below: mm = millimetre, m = metre; sRGB = the standard
gamma-encoded RGB the extract's colours are stored in, converted to linear
light once before any shading math; BSDF = bidirectional scattering
distribution function, the light model behind Blender's Principled BSDF
node; IOR = index of refraction, the Principled BSDF's glass parameter.
"""
import math
import os

import bmesh
import bpy
from mathutils import Vector

MM_TO_M = 0.001


def m(mm):
    """Millimetres -> metres. Mirrors build_scene.m; the only conversion here."""
    return float(mm) * MM_TO_M


def _srgb_to_linear(v255):
    s = max(0.0, min(255.0, float(v255))) / 255.0
    return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4


# ---------------------------------------------------------------------------
# build_items: real geometry, real materials, honest gaps
# ---------------------------------------------------------------------------
SMOOTH_ANGLE_DEG = 32.0  # below this, adjacent faces smooth; above, silhouette stays hard


def _validate_mesh(spec):
    """Convert + validate one mesh entry; returns (verts_m, triangles, dropped) or None.

    Rejects malformed input outright rather than substituting a default --
    a bad vertex or an out-of-range index must lose that triangle, not gain
    an invented one.
    """
    verts = spec.get("vertices_mm")
    tris = spec.get("triangles")
    if not isinstance(verts, list) or not isinstance(tris, list):
        return None
    if len(verts) < 3 or len(tris) < 1:
        return None

    verts_m = []
    for v in verts:
        if not (isinstance(v, (list, tuple)) and len(v) == 3):
            return None
        try:
            coords = [float(c) for c in v]
        except (TypeError, ValueError):
            return None
        if any(math.isnan(c) or math.isinf(c) for c in coords):
            return None
        verts_m.append(Vector((m(coords[0]), m(coords[1]), m(coords[2]))))

    def as_index(value):
        # bool is a subclass of int in Python, and a non-integral float
        # (1.7) truncating to 1 is a silent substitution -- reject both
        # rather than accept them as an index.
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return None

    n = len(verts_m)
    valid_tris = []
    dropped = 0
    for t in tris:
        if not (isinstance(t, (list, tuple)) and len(t) == 3):
            dropped += 1
            continue
        a, b, c = as_index(t[0]), as_index(t[1]), as_index(t[2])
        if a is None or b is None or c is None:
            dropped += 1
            continue
        if not (0 <= a < n and 0 <= b < n and 0 <= c < n):
            dropped += 1
            continue
        if a == b or b == c or a == c:
            dropped += 1
            continue
        area2 = (verts_m[b] - verts_m[a]).cross(verts_m[c] - verts_m[a]).length
        if area2 < 1e-10:  # degenerate (near-zero area, in m^2 x2)
            dropped += 1
            continue
        valid_tris.append((a, b, c))

    if not valid_tris:
        return None
    return verts_m, valid_tris, dropped


def _valid_rgb255(rgb255):
    if not isinstance(rgb255, (list, tuple)) or len(rgb255) != 3:
        return None
    try:
        vals = [float(c) for c in rgb255]
    except (TypeError, ValueError):
        return None
    if any(math.isnan(v) or v < 0 or v > 255 for v in vals):
        return None
    return vals


def _make_material(name, rgb255, transparency, reflectance):
    """A Principled BSDF material, cached by name like build_scene.material.

    Glass is recognised by the extract's own signal -- material transparency
    or a glass/glazing name -- never by category, so a door mesh with an
    opaque material stays opaque even though it lives in `openings`.

    Returns None if `rgb255` is missing or malformed -- a made-up grey would
    be a silent substitution the spec forbids.
    """
    valid_rgb = _valid_rgb255(rgb255)
    if valid_rgb is None:
        return None
    rgb255 = valid_rgb

    mat = bpy.data.materials.get(name)
    if mat:
        prior = mat.get("presentation_source_rgb")
        if prior is not None and list(prior) != list(rgb255):
            print("PRESENTATION NOTE: material %r requested with rgb %s but "
                  "already exists with rgb %s; keeping the first."
                  % (name, rgb255, list(prior)))
        return mat
    mat = bpy.data.materials.new(name)
    mat["presentation_source_rgb"] = rgb255
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    is_glass = transparency > 0 or any(
        k in name.lower() for k in ("glass", "glazing"))

    if is_glass:
        # Assumed clear glazing: the extract signals "transparent", not an
        # optical spec. IOR and roughness are stated assumptions.
        bsdf.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)
        trans_input = ("Transmission Weight" if "Transmission Weight" in bsdf.inputs
                       else "Transmission")
        bsdf.inputs[trans_input].default_value = 1.0
        bsdf.inputs["Roughness"].default_value = 0.02
        bsdf.inputs["IOR"].default_value = 1.5
        mat["presentation_assumption"] = (
            "clear glazing assumed: IOR 1.5, roughness 0.02, not measured")
    else:
        rgb_lin = tuple(_srgb_to_linear(v) for v in rgb255)
        y = 0.2126 * rgb_lin[0] + 0.7152 * rgb_lin[1] + 0.0722 * rgb_lin[2]
        k = (reflectance / y) if y > 0 else reflectance
        rgb = tuple(min(1.0, c * k) for c in rgb_lin)
        bsdf.inputs["Base Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
        bsdf.inputs["Roughness"].default_value = 0.6
        mat["presentation_reflectance"] = reflectance
    return mat


def _shade_by_angle(obj, angle_deg):
    """Angle-based edge normals: below the threshold smooth, above it hard.

    A single mechanism does both jobs the spec asks for -- a rounded
    surface's low-angle tessellation smooths, while a wardrobe's ~90 degree
    panel joins stay a hard silhouette -- without per-item classification.

    Uses the mesh-data calls added in Blender 4.1 (`shade_smooth`,
    `set_sharp_from_angle`) rather than the `shade_auto_smooth` operator, so
    it needs no active/selected-object context and works the same in
    background mode.
    """
    mesh = obj.data
    mesh.shade_smooth()
    try:
        mesh.set_sharp_from_angle(angle=math.radians(angle_deg))
    except Exception:
        # If the sharp pass fails after shade_smooth already ran, a fully
        # smooth mesh with no hard edges is the worst case (a wardrobe's
        # panel joins would round off) -- fall back to flat rather than
        # leave that half-applied state.
        mesh.shade_flat()
        raise


def _build_mesh_object(name, verts_m, triangles, mat):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    bverts = [bm.verts.new(v) for v in verts_m]
    bm.verts.ensure_lookup_table()
    made_face = False
    for a, b, c in triangles:
        try:
            bm.faces.new((bverts[a], bverts[b], bverts[c]))
            made_face = True
        except ValueError:
            continue  # duplicate/degenerate face under this winding; skip it
    if not made_face:
        bm.free()
        bpy.data.objects.remove(obj)
        bpy.data.meshes.remove(mesh)
        return None
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()

    if mat:
        obj.data.materials.append(mat)
    try:
        _shade_by_angle(obj, SMOOTH_ANGLE_DEG)
    except Exception as exc:
        print("PRESENTATION NOTE: angle-based shading unavailable (%s); "
              "leaving %s flat-shaded." % (exc, name))
    return obj


def build_items(data, categories=("furniture", "casework", "openings"),
                reflectance=0.35):
    """Real geometry for extract items that carry meshes; the rest reported.

    `data[category]` items with a non-empty, valid `meshes` list become
    real Blender objects, tagged with their source category/id/type so the
    caller can trace an object back to the extract. Items with no meshes,
    come back unchanged in `missing`. Malformed meshes raise; this
    function never substitutes a proxy. That decision
    stays with the caller (e.g. build_scene.build_furniture).
    """
    objects = []
    missing = []
    for category in categories:
        for item in data.get(category, []):
            meshes = item.get("meshes") or []
            built = []
            for i, mesh_spec in enumerate(meshes):
                if mesh_spec.get('geometry_role') == 'light_source_symbol':
                    print('PRESENTATION NOTE excluded native light-source display symbol for '+str(item.get('id')))
                    continue
                item_tag = "%s %s mesh %d" % (
                    category, item.get("id") or "?", i)

                validated = _validate_mesh(mesh_spec)
                if validated is None:
                    raise ValueError('Malformed extracted mesh: '+item_tag)
                verts_m, triangles, dropped = validated
                if dropped:
                    raise ValueError('%s contains %d invalid or degenerate triangles' % (item_tag,dropped))

                mat_spec = mesh_spec.get("material") or {}
                mat_name = mat_spec.get("name")
                rgb255 = mat_spec.get("rgb")
                if not mat_name or rgb255 is None:
                    raise ValueError('Missing material in '+item_tag)
                raw_transparency = mat_spec.get("transparency", 0)
                try:
                    transparency = float(raw_transparency)
                except (TypeError, ValueError):
                    raise ValueError('Invalid transparency in '+item_tag)
                if math.isnan(transparency) or not (0 <= transparency <= 100):
                    raise ValueError('Transparency outside 0..100 in '+item_tag)
                mat = _make_material(mat_name, rgb255, transparency, reflectance)
                if mat is None:
                    raise ValueError('Invalid material colour in '+item_tag)

                obj_name = mesh_spec.get("name") or (
                    "%s_%s_%d" % (category, str(item.get("id") or "")[:8], i))
                obj = _build_mesh_object(obj_name, verts_m, triangles, mat)
                if obj is None:
                    raise ValueError('No render geometry for '+item_tag)
                obj["source_category"] = category
                obj["source_id"] = item.get("id") or ""
                obj["source_type"] = item.get("type_name") or ""
                if dropped:
                    obj["dropped_triangles"] = dropped
                    print("PRESENTATION NOTE: %s dropped %d malformed/"
                          "degenerate triangle(s), kept %d."
                          % (item_tag, dropped, len(triangles)))
                built.append(obj)

            if built:
                objects.extend(built)
            else:
                missing.append(item)
    return objects, missing


# ---------------------------------------------------------------------------
# enhance_finishes: procedural detail on materials that already exist
# ---------------------------------------------------------------------------
def _bsdf(mat):
    return mat.node_tree.nodes.get("Principled BSDF")


def _world_coord(nt):
    """World-space position, independent of any object's own transform.

    Object-space coordinates only equal world metres while every built
    object keeps an identity transform; Geometry's Position output is
    world space by definition, so it stays correct even if that changes.
    """
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    return geo.outputs["Position"]


def _mark_done(mat, key):
    mat["presentation_detail"] = key


def _already_done(mat, key):
    return mat.get("presentation_detail") == key


def _enhance_floor_timber(mat):
    """Board-scale grain + plank joints, not a groove every few millimetres.

    Boards are ~160 mm wide, ~1.0-1.6 m long: exactly what Brick Texture's
    row-height/brick-width controls model, so joints land at plank scale
    instead of at texture-noise scale.
    """
    key = "floor_timber_v1"
    if _already_done(mat, key):
        return
    nt = mat.node_tree
    bsdf = _bsdf(mat)
    coord = _world_coord(nt)

    joints = nt.nodes.new("ShaderNodeTexBrick")
    joints.inputs["Scale"].default_value = 1.0
    joints.inputs["Mortar Size"].default_value = 0.0015
    joints.inputs["Mortar Smooth"].default_value = 0.4
    joints.inputs["Brick Width"].default_value = 1.3   # metres: board length, ~mid 1.0-1.6 m
    joints.inputs["Row Height"].default_value = 0.16   # metres: board width
    nt.links.new(coord, joints.inputs["Vector"])

    # Boards run along X (Brick's width axis); grain lines run along the
    # board's length, so they must vary ACROSS it -- bands along Y.
    grain = nt.nodes.new("ShaderNodeTexWave")
    grain.wave_type = "BANDS"
    grain.bands_direction = "Y"
    grain.inputs["Scale"].default_value = 45.0
    grain.inputs["Distortion"].default_value = 2.5
    nt.links.new(coord, grain.inputs["Vector"])

    # Brick's Fac is 1 in the mortar/seam, 0 on the board face; inverted so
    # the seam reads as a groove, not a ridge.
    bump_joint = nt.nodes.new("ShaderNodeBump")
    bump_joint.invert = True
    bump_joint.inputs["Strength"].default_value = 0.15
    bump_joint.inputs["Distance"].default_value = 0.0015
    nt.links.new(joints.outputs["Fac"], bump_joint.inputs["Height"])

    bump_grain = nt.nodes.new("ShaderNodeBump")
    bump_grain.inputs["Strength"].default_value = 0.06
    bump_grain.inputs["Distance"].default_value = 0.0004
    nt.links.new(grain.outputs["Fac"], bump_grain.inputs["Height"])
    nt.links.new(bump_joint.outputs["Normal"], bump_grain.inputs["Normal"])
    nt.links.new(bump_grain.outputs["Normal"], bsdf.inputs["Normal"])

    # Subtle colour variance around the extracted hue -- presentation
    # detail, not a measured optical property. Mean stays at the base
    # colour; the ramp only nudges it +/-.
    base = bsdf.inputs["Base Color"].default_value[:3]
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = tuple(c * 0.92 for c in base) + (1.0,)
    ramp.color_ramp.elements[1].color = tuple(min(1.0, c * 1.08) for c in base) + (1.0,)
    nt.links.new(grain.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

    _mark_done(mat, key)


def _enhance_furniture_oak(mat):
    """Mild grain for oak furniture -- no plank joints; this is not a floor."""
    key = "furniture_oak_v1"
    if _already_done(mat, key):
        return
    nt = mat.node_tree
    bsdf = _bsdf(mat)
    coord = _world_coord(nt)

    grain = nt.nodes.new("ShaderNodeTexWave")
    grain.wave_type = "BANDS"
    grain.bands_direction = "Z"
    grain.inputs["Scale"].default_value = 30.0
    grain.inputs["Distortion"].default_value = 1.5

    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (1.0, 1.0, 3.0)
    nt.links.new(coord, mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], grain.inputs["Vector"])

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.05
    bump.inputs["Distance"].default_value = 0.0003
    nt.links.new(grain.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    base = bsdf.inputs["Base Color"].default_value[:3]
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = tuple(c * 0.95 for c in base) + (1.0,)
    ramp.color_ramp.elements[1].color = tuple(min(1.0, c * 1.05) for c in base) + (1.0,)
    nt.links.new(grain.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

    _mark_done(mat, key)


def _enhance_fine_bump(mat, key, scale, strength, distance, roughness_jitter):
    """Shared shape for "almost imperceptible" surfaces: paint and plaster.

    Both get a bump only, no colour or joint pattern; `strength`/`distance`
    are the only knobs, tuned per surface so plaster reads flatter than paint.
    """
    if _already_done(mat, key):
        return
    nt = mat.node_tree
    bsdf = _bsdf(mat)
    coord = _world_coord(nt)

    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = 2.0
    noise.inputs["Roughness"].default_value = 0.5
    nt.links.new(coord, noise.inputs["Vector"])

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = distance
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    if roughness_jitter:
        base_r = bsdf.inputs["Roughness"].default_value
        map_range = nt.nodes.new("ShaderNodeMapRange")
        map_range.inputs["To Min"].default_value = max(0.0, base_r - roughness_jitter)
        map_range.inputs["To Max"].default_value = min(1.0, base_r + roughness_jitter)
        nt.links.new(noise.outputs["Fac"], map_range.inputs["Value"])
        nt.links.new(map_range.outputs["Result"], bsdf.inputs["Roughness"])

    _mark_done(mat, key)


def _enhance_fabric(mat):
    """Fine weave for linen/bedding/throw: bump plus roughness variation."""
    key = "fabric_weave_v1"
    if _already_done(mat, key):
        return
    nt = mat.node_tree
    bsdf = _bsdf(mat)
    coord = _world_coord(nt)

    # Two crossed band sets approximate a woven warp/weft rather than a
    # single set of parallel ridges.
    warp = nt.nodes.new("ShaderNodeTexWave")
    warp.wave_type = "BANDS"
    warp.bands_direction = "X"
    warp.inputs["Scale"].default_value = 300.0
    warp.inputs["Distortion"].default_value = 0.2
    weft = nt.nodes.new("ShaderNodeTexWave")
    weft.wave_type = "BANDS"
    weft.bands_direction = "Y"
    weft.inputs["Scale"].default_value = 300.0
    weft.inputs["Distortion"].default_value = 0.2
    combine = nt.nodes.new("ShaderNodeMath")
    combine.operation = "MULTIPLY"
    nt.links.new(coord, warp.inputs["Vector"])
    nt.links.new(coord, weft.inputs["Vector"])
    nt.links.new(warp.outputs["Fac"], combine.inputs[0])
    nt.links.new(weft.outputs["Fac"], combine.inputs[1])

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.12
    bump.inputs["Distance"].default_value = 0.00015
    nt.links.new(combine.outputs["Value"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    base_r = bsdf.inputs["Roughness"].default_value
    map_range = nt.nodes.new("ShaderNodeMapRange")
    map_range.inputs["To Min"].default_value = max(0.0, base_r - 0.08)
    map_range.inputs["To Max"].default_value = min(1.0, base_r + 0.08)
    nt.links.new(combine.outputs["Value"], map_range.inputs["Value"])
    nt.links.new(map_range.outputs["Result"], bsdf.inputs["Roughness"])

    _mark_done(mat, key)


def _enhance_dark_metal(mat):
    """Metallic finish for dark metal fittings -- no procedural pattern.

    Metallic .8 and satin roughness are assumed, not read from the extract:
    the extract carries a colour, not a finish class.
    """
    key = "dark_metal_v1"
    if _already_done(mat, key):
        return
    bsdf = _bsdf(mat)
    bsdf.inputs["Metallic"].default_value = 0.8
    bsdf.inputs["Roughness"].default_value = 0.35
    mat["presentation_assumption"] = (
        "dark metal assumed satin finish: metallic 0.8, roughness 0.35, not measured")
    _mark_done(mat, key)


def _load_pbr_images(library_root, asset_id):
    """Load an ambientCG material's Color/Roughness/NormalGL maps by name.

    Returns None (never a partial dict) if the library or any expected file
    is missing, so the caller's fallback is "keep the procedural material
    as-is", not a half-textured one.
    """
    base = os.path.join(library_root, "materials", asset_id)
    names = {"color": "%s_1K-JPG_Color.jpg" % asset_id,
             "roughness": "%s_1K-JPG_Roughness.jpg" % asset_id}
    images = {}
    for key, fname in names.items():
        path = os.path.join(base, fname)
        if not os.path.isfile(path):
            return None
        img = bpy.data.images.get(fname) or bpy.data.images.load(path)
        img.colorspace_settings.name = "sRGB" if key == "color" else "Non-Color"
        images[key] = img
    return images


def _image_mean_linear_luminance(img, samples=20000):
    """Approximate mean Rec.709 luminance, in LINEAR light, of an image.

    `Image.pixels` returns the file's own encoded values -- for an sRGB-
    tagged JPEG that is still gamma-encoded, not scene-linear -- regardless
    of `colorspace_settings`, which only affects how Cycles reads the image
    at render time. Averaging the raw bytes would read a photo's *encoded*
    brightness as if it were radiance, which is not the quantity the
    calibrated flat materials elsewhere in this file are stated in. Every
    sampled channel goes through the same sRGB->linear curve `_make_material`
    already uses before Rec.709-weighting it.
    """
    px = img.pixels[:]
    n = len(px) // 4
    if n == 0:
        return 0.5
    stride = max(1, n // samples)
    total = 0.0
    count = 0
    for i in range(0, n, stride):
        o = i * 4
        r = _srgb_to_linear(px[o] * 255.0)
        g = _srgb_to_linear(px[o + 1] * 255.0)
        b = _srgb_to_linear(px[o + 2] * 255.0)
        total += 0.2126 * r + 0.7152 * g + 0.0722 * b
        count += 1
    return total / count if count else 0.5


def _apply_photo_texture(mat, library_root, asset_id, target_reflectance, tile_m=1.0,
                         bump_strength=0.0):
    """Swap a material's Base Color/Roughness for a real photographed sample.

    The existing procedural bump (already wired to Normal by an earlier
    `_enhance_*` call) is left untouched -- Base Color and Roughness are
    separate BSDF inputs, so this only replaces what it explicitly links.
    Photographed NormalGL maps are deliberately NOT used: they are tangent-
    space data, correct only against the mesh's own UV layout, and these
    objects carry none (Box-projected world coordinates drive the texture
    instead, exactly like the procedural functions already do) -- wiring a
    tangent-space map onto an unrelated projection produces confidently
    wrong-looking shading, not a visible error. `bump_strength` > 0 instead
    drives a height-based Bump node from the roughness map's own greyscale
    -- a weave/grain map's roughness channel tracks its surface relief
    closely enough to read as real bump, and Bump (unlike Normal Map) works
    from a scalar height field in whatever coordinate space fed it, tangent
    basis or not, so it has none of the Normal Map risk above. This
    replaces whichever procedural bump the caller's earlier `_enhance_*`
    call wired to Normal -- Blender drops the old link when a new one is
    made to the same input, so it is a clean upgrade, not a conflict.

    Mean-normalized to `target_reflectance` using the SAME linear-luminance
    convention `_make_material`'s flat colours already use, so swapping a
    flat calibrated colour for a photograph never changes the material's
    average light return -- the one invariant this project's photometric
    validation (ADR-0009, scripts/verify.py) depends on.
    """
    key = "photo_" + asset_id
    if mat.get("presentation_photo_detail") == key:
        return True
    images = _load_pbr_images(library_root, asset_id)
    if images is None:
        return False
    nt = mat.node_tree
    bsdf = _bsdf(mat)
    coord = _world_coord(nt)

    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (1.0 / tile_m, 1.0 / tile_m, 1.0 / tile_m)
    nt.links.new(coord, mapping.inputs["Vector"])

    color_node = nt.nodes.new("ShaderNodeTexImage")
    color_node.image = images["color"]
    color_node.projection = "BOX"
    color_node.projection_blend = 0.3
    nt.links.new(mapping.outputs["Vector"], color_node.inputs["Vector"])

    rough_node = nt.nodes.new("ShaderNodeTexImage")
    rough_node.image = images["roughness"]
    rough_node.projection = "BOX"
    rough_node.projection_blend = 0.3
    nt.links.new(mapping.outputs["Vector"], rough_node.inputs["Vector"])

    mean = _image_mean_linear_luminance(images["color"])
    factor = (target_reflectance / mean) if mean > 0 else target_reflectance
    scale = nt.nodes.new("ShaderNodeVectorMath")
    scale.operation = "MULTIPLY"
    scale.inputs[1].default_value = (factor, factor, factor)
    nt.links.new(color_node.outputs["Color"], scale.inputs[0])
    nt.links.new(scale.outputs["Vector"], bsdf.inputs["Base Color"])
    nt.links.new(rough_node.outputs["Color"], bsdf.inputs["Roughness"])

    if bump_strength > 0:
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = bump_strength
        bump.inputs["Distance"].default_value = 0.001
        nt.links.new(rough_node.outputs["Color"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    mat["presentation_photo_texture"] = asset_id
    mat["presentation_photo_mean_scale"] = factor
    mat["presentation_photo_detail"] = key
    return True


def enhance_finishes(data, library_root=None):
    """Add procedural detail to materials build_scene/build_items already made.

    Non-destructive: each material is found by name in `bpy.data.materials`
    (nothing is created here that wasn't already there) and each enhancer is
    idempotent, guarded by a `presentation_detail` custom property, so
    calling this twice on the same scene is harmless.

    Returns a compact dict of {material_name: assumption/description} meant
    to be logged next to the render, not consumed programmatically.
    """
    report = {
        "_reflectance_assumptions": (
            "furniture 0.35, floor 0.25, wall 0.60, ceiling 0.80 (fixed, "
            "matching archpipe.lighting.Surfaces); dark metal additionally "
            "metallic 0.8 with roughness treated as finish, not reflectance")
    }

    # Role -> material names comes from the extract itself (the same
    # `finishes` entries build_scene.finish_surface reads), not a hardcoded
    # literal, so differently-named paints/plasters/timbers still get found.
    # Walls are finished per element (finish_surface is called with
    # element=w['id']), so a role can legitimately have more than one name.
    role_to_names = {}
    for item in data.get("finishes", []):
        role = item.get("role")
        paints = item.get("paint") or []
        if role and len(paints) == 1 and paints[0].get("name"):
            role_to_names.setdefault(role, set()).add(paints[0]["name"])

    handled = set()

    for floor_name in role_to_names.get("floor", ()):
        timber = bpy.data.materials.get(floor_name)
        if not timber:
            continue
        _enhance_floor_timber(timber)
        note = ("floor: plank joints ~1.3 m x 0.16 m (Brick Texture), grain bump, "
                "+/-8% colour variance around extracted hue -- presentation "
                "detail, not measured optics")
        if library_root and _apply_photo_texture(timber, library_root, "WoodFloor041",
                                                  0.25, tile_m=1.0):
            note += "; Base Color/Roughness replaced by WoodFloor041 (ambientCG, CC0), mean-matched to 0.25"
        report[timber.name] = note
        handled.add(timber)

    for wall_name in role_to_names.get("walls", ()):
        painted = bpy.data.materials.get(wall_name)
        if not painted:
            continue
        _enhance_fine_bump(painted, "wall_painted_v1", scale=180.0,
                           strength=0.02, distance=0.0002, roughness_jitter=0.03)
        report[painted.name] = (
            "wall: subtle orange-peel bump only, no colour/roughness pattern "
            "beyond a small roughness jitter; assumed emulsion finish")
        handled.add(painted)

    for ceiling_name in role_to_names.get("ceiling", ()):
        plaster = bpy.data.materials.get(ceiling_name)
        if not plaster:
            continue
        _enhance_fine_bump(plaster, "ceiling_plaster_v1", scale=250.0,
                           strength=0.006, distance=0.00015, roughness_jitter=0.0)
        report[plaster.name] = (
            "ceiling: almost imperceptible bump only, flatter than the wall "
            "paint treatment; assumed smooth trowel finish")
        handled.add(plaster)

    for mat in list(bpy.data.materials):
        if mat in handled:
            continue
        name_l = mat.name.lower()
        if mat.get("presentation_assumption") and mat.get("presentation_detail") is None:
            # Glass (or another material stamped by _make_material with an
            # assumption but no procedural detail): surface the assumption
            # in the log without touching the material further.
            report[mat.name] = mat["presentation_assumption"]
            continue
        if not name_l.startswith("archpipe"):
            continue
        reflectance = mat.get("presentation_reflectance", 0.35)
        if "oak" in name_l:
            _enhance_furniture_oak(mat)
            note = "furniture oak: mild grain bump, +/-5% colour variance"
            if library_root and _apply_photo_texture(mat, library_root, "Wood049",
                                                      reflectance, tile_m=0.8):
                note += "; Base Color/Roughness replaced by Wood049 (ambientCG, CC0), mean-matched to %.2f" % reflectance
            report[mat.name] = note
        elif any(k in name_l for k in ("linen", "bedding", "throw")):
            _enhance_fabric(mat)
            note = "fabric: crossed-band weave bump + roughness variation"
            fabric_id = ("Fabric019" if "bedding" in name_l else
                        "Fabric082A" if "throw" in name_l else "Fabric036")
            # A larger tile than the other materials: at 0.3 m the weave
            # repeated too finely to read as fabric from camera distance --
            # the requested fix is legibility of the weave, not fineness.
            if library_root and _apply_photo_texture(mat, library_root, fabric_id,
                                                      reflectance, tile_m=0.7,
                                                      bump_strength=0.35):
                note += "; Base Color/Roughness replaced by %s (ambientCG, CC0), mean-matched to %.2f, roughness-driven bump" % (fabric_id, reflectance)
            report[mat.name] = note
        elif "metal" in name_l:
            _enhance_dark_metal(mat)
            note = mat.get("presentation_assumption", "dark metal: metallic 0.8")
            if library_root and _apply_photo_texture(mat, library_root, "Metal046A",
                                                      reflectance, tile_m=0.4):
                note += "; Base Color/Roughness replaced by Metal046A (ambientCG, CC0), mean-matched to %.2f" % reflectance
            report[mat.name] = note

    return report
