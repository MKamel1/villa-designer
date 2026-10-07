"""Pure-Python validation of the villa-render/1 authored scene contract."""
from __future__ import annotations

import math
import re
from datetime import datetime
from pathlib import PurePosixPath

KINDS = {"principled", "glass", "emissive", "translucent"}
GROUPS = {"shell", "context", "furniture", "fixture", "dressing", "ground"}
LAYERS = {"ambient", "task", "accent", "decorative", "night"}
RAY_VISIBILITY = ("camera", "shadow", "diffuse", "glossy", "transmission")
# archpipe.concept.villa_furnish.BODY: card mitton-path-of-travel-min, paths of travel at least 36 in (914 mm).
# Duplicated as a literal (not imported) so this generic contract module stays free of a concept-package
# dependency; villa_render.py's curtain loop cites the same card and constant name when it computes the field.
DOOR_CLEAR_WIDTH_M = 0.914


def _number(value, positive=False):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and (not positive or value > 0)


def _vector(value, length=3):
    return isinstance(value, (list, tuple)) and len(value) == length and all(_number(v) for v in value)


def _length(v):
    return math.sqrt(sum(x*x for x in v))


def _sub(a, b):
    return [x-y for x, y in zip(a, b)]


def _cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def _relative_path(value):
    return (isinstance(value, str) and bool(value) and
            re.fullmatch(r"[A-Za-z0-9_.\-/]+", value) is not None and
            not PurePosixPath(value).is_absolute() and
            ".." not in PurePosixPath(value).parts and "\\" not in value)


def _timestamp(value):
    if not isinstance(value, str):
        return False
    try:
        return datetime.fromisoformat(value).tzinfo is not None
    except ValueError:
        return False


def emission_strength(exitance_lm_per_m2: float) -> float:
    """Blender emission strength for Lambertian luminous exitance.

    Exitance is flux per emitting area. Lambert's cosine law integrates
    constant radiance over one outward hemisphere to pi times radiance.
    This project's measured light scale reads one Blender watt as one lumen.
    Thus strength is exitance divided by pi in calibrated radiance units.
    """
    return exitance_lm_per_m2 / math.pi


def mesh_batch_key(mesh: dict, material_kind: str):
    """Only merge non-emitting architectural meshes with identical ray flags."""
    if (mesh.get("keep_object") or "face_materials" in mesh or "bevel_m" in mesh or "subdivide" in mesh or
            mesh.get("group") in ("furniture", "fixture", "dressing") or material_kind == "emissive"):
        return None
    visibility = mesh.get("visibility", {})
    return mesh["material"], tuple(visibility.get(name, True) for name in RAY_VISIBILITY)


def emissive_mesh_output_factor(mesh: dict, view: dict) -> float:
    """An unlayered mesh is always on; a layered one follows the view."""
    layer = mesh.get("layer")
    if layer is None:
        return 1.0
    if layer not in view["layers_on"]:
        return 0.0
    return view.get("dimmers", {}).get(layer, 1.0)


def sky_state_for_view(state: str) -> str:
    """Exterior dusk uses the specified evening sky with its own exposure."""
    return "evening" if state == "exterior-dusk" else state


def mesh_bbox_corners(mesh: dict):
    """Bounds of one authored source, independent of Blender mesh merging."""
    points = [point for face in mesh["faces"] for point in face]
    low = [min(point[axis] for point in points) for axis in range(3)]
    high = [max(point[axis] for point in points) for axis in range(3)]
    return [(x, y, z) for x in (low[0], high[0]) for y in (low[1], high[1])
            for z in (low[2], high[2])]


def validate_scene(scene: dict) -> list[str]:
    """Return actionable errors; an empty list means the input is renderable."""
    errors = []
    def need(condition, path, message):
        if not condition:
            errors.append(f"{path}: {message}")

    if not isinstance(scene, dict):
        return ["scene: expected object"]
    need(scene.get("schema") == "villa-render/1", "schema", "expected villa-render/1")
    need(isinstance(scene.get("id"), str) and bool(scene.get("id")), "id", "nonempty string required")
    north = scene.get("north")
    need(isinstance(north, dict) and _number(north.get("model_y_bearing_deg")), "north.model_y_bearing_deg", "finite number required")
    need(isinstance(scene.get("library_root"), str) and bool(scene.get("library_root")), "library_root", "path required")
    materials = scene.get("materials")
    if not isinstance(materials, dict):
        errors.append("materials: object required")
        materials = {}
    for name, mat in materials.items():
        p = f"materials.{name}"
        need(isinstance(name, str) and bool(name), p, "nonempty name required")
        if not isinstance(mat, dict):
            errors.append(f"{p}: object required"); continue
        need(mat.get("kind") in KINDS, p+".kind", "unknown material kind")
        need(_vector(mat.get("base_rgb")), p+".base_rgb", "three finite numbers required")
        if mat.get("kind") in ("glass", "translucent"):
            need("transmittance" in mat, p+".transmittance", "explicit transmittance required")
        if "interfaces" in mat:
            need(type(mat["interfaces"]) is int and mat["interfaces"] in (1, 2),
                 p+".interfaces", "one sheet or two slab interfaces required")
        # WP4-B4: index of refraction, carried from a fitting's own measured optics (e.g. revit_spec bath_fittings'
        # pe-bath-screen: 1.52) instead of villa_scene's hardcoded 1.5 assumption. Real glasses run roughly 1.45
        # (fused silica) to 1.9 (dense flint); this range never invents a value, only bounds what is plausibly glass.
        if "ior" in mat:
            need(_number(mat["ior"]) and 1.0 < mat["ior"] < 3.0, p+".ior", "plausible glass index of refraction (1-3) required")
        if mat.get("kind") == "emissive":
            need("emission_lm_per_m2" in mat and "cct_k" in mat, p, "explicit emission and colour temperature required")
        if "asset" in mat:
            need("reflectance" in mat and "tile_m" in mat, p, "textured material needs reflectance and tile_m")
        for field in ("roughness", "metallic", "reflectance", "transmittance"):
            if field in mat:
                need(_number(mat[field]) and 0 <= mat[field] <= 1, p+"."+field, "fraction from 0 to 1 required")
        for field in ("tile_m", "cct_k"):
            if field in mat:
                need(_number(mat[field], positive=True), p+"."+field, "positive number required")
        if "emission_lm_per_m2" in mat:
            need(_number(mat["emission_lm_per_m2"]) and mat["emission_lm_per_m2"] >= 0, p+".emission_lm_per_m2", "nonnegative number required")
        if "grain_axis" in mat:
            need(mat["grain_axis"] in ("x", "y", "z"), p+".grain_axis", "expected x, y or z")
        if "asset" in mat:
            need(_relative_path(mat["asset"]), p+".asset", "safe relative asset name required")
    meshes = scene.get("meshes")
    if not isinstance(meshes, list):
        errors.append("meshes: array required"); meshes = []
    mesh_ids = set()
    for i, mesh in enumerate(meshes):
        p = f"meshes[{i}]"
        if not isinstance(mesh, dict):
            errors.append(f"{p}: object required"); continue
        ident = mesh.get("id")
        need(isinstance(ident, str) and bool(ident) and ident not in mesh_ids, p+".id", "unique nonempty string required")
        mesh_ids.add(ident)
        # Guard: Bookkeeping and diagnostic meshes must never enter render meshes.
        # Defect: ~600 bookkeeping meshes with "host-face-", "support-", etc. made walls render solid black.
        is_bookkeeping_id = isinstance(ident, str) and (
            ident.startswith("host-face-")
            or ident.startswith("support-")
        )
        is_diagnostic = bool(mesh.get("diagnostic"))
        if is_bookkeeping_id or is_diagnostic:
            errors.append(f"{p}: render mesh {ident!r} must not be a diagnostic or host/support bookkeeping mesh")
        need(mesh.get("group") in GROUPS, p+".group", "unknown group")
        need(mesh.get("material") in materials, p+".material", "unknown material")
        if "face_materials" in mesh:
            assigned=mesh["face_materials"]
            need(isinstance(assigned,list) and len(assigned)==len(mesh.get("faces",[])) and all(m in materials for m in assigned),
                 p+".face_materials", "one registered finish per authored face required")
        need(mesh.get("room") is None or isinstance(mesh.get("room"), str), p+".room", "string or null required")
        need(isinstance(mesh.get("label"), str), p+".label", "string required")
        if "layer" in mesh:
            need(mesh["layer"] in LAYERS, p+".layer", "unknown lighting layer")
        if "keep_object" in mesh:
            need(isinstance(mesh["keep_object"], bool), p+".keep_object", "boolean required")
        if "bevel_m" in mesh:
            need(_number(mesh["bevel_m"]) and 0 <= mesh["bevel_m"] <= 0.05,
                 p+".bevel_m", "number from 0 to 0.05 m required")
        if "subdivide" in mesh:
            need(isinstance(mesh["subdivide"], int) and not isinstance(mesh["subdivide"], bool) and
                 0 <= mesh["subdivide"] <= 2, p+".subdivide", "integer from 0 to 2 required")
        if "visibility" in mesh:
            visibility = mesh["visibility"]
            need(isinstance(visibility, dict) and all(k in RAY_VISIBILITY and isinstance(v, bool)
                 for k, v in visibility.items()), p+".visibility", "only camera, shadow, diffuse, glossy and transmission booleans allowed")
        faces = mesh.get("faces")
        if not isinstance(faces, list) or not faces:
            errors.append(p+".faces: nonempty array required"); continue
        for j, face in enumerate(faces):
            fp = f"{p}.faces[{j}]"
            if not isinstance(face, list) or len(face) < 3 or not all(_vector(v) for v in face):
                errors.append(fp+": at least three three-dimensional vertices required"); continue
            origin = face[0]
            normal = None
            for k in range(1, len(face)-1):
                candidate = _cross(_sub(face[k], origin), _sub(face[k+1], origin))
                if _length(candidate) > 1e-10:
                    normal = [x/_length(candidate) for x in candidate]; break
            if normal is None:
                errors.append(fp+": degenerate polygon"); continue
            if any(abs(sum(normal[d]*(v[d]-origin[d]) for d in range(3))) > 0.001 for v in face):
                errors.append(fp+": nonplanar by more than 1 mm")
            area = [0.0, 0.0, 0.0]
            for a, b in zip(face, face[1:]+face[:1]):
                c = _cross(a, b)
                area = [area[d]+c[d] for d in range(3)]
            if _length(area) < 1e-8 or any(_length(_sub(a, b)) < 1e-6 for a, b in zip(face, face[1:]+face[:1])):
                errors.append(fp+": degenerate polygon")
    lights = scene.get("lights")
    if not isinstance(lights, list):
        errors.append("lights: array required"); lights = []
    light_ids = set()
    for i, light in enumerate(lights):
        p = f"lights[{i}]"
        if not isinstance(light, dict):
            errors.append(p+": object required"); continue
        ident = light.get("id")
        need(isinstance(ident, str) and bool(ident) and ident not in light_ids and ident not in mesh_ids,
             p+".id", "unique nonempty string required across meshes and lights")
        light_ids.add(ident)
        need(light.get("type") in ("ies", "area", "line"), p+".type", "unknown light type")
        need(light.get("layer") in LAYERS, p+".layer", "unknown layer")
        need(isinstance(light.get("room"), str), p+".room", "room string required")
        need(_vector(light.get("position")), p+".position", "three finite numbers required")
        need(_vector(light.get("aim")) and _length(light["aim"]) > 0, p+".aim", "nonzero vector required")
        need(_number(light.get("lumens")) and light["lumens"] >= 0, p+".lumens", "nonnegative number required")
        need(_number(light.get("cct_k"), positive=True), p+".cct_k", "positive number required")
        need(_number(light.get("cri")) and 0 <= light["cri"] <= 100, p+".cri", "colour rendering index from 0 to 100 required")
        product = light.get("product")
        need(isinstance(product, dict) and isinstance(product.get("manufacturer"), str) and
             isinstance(product.get("code"), str) and isinstance(product.get("generic"), bool),
             p+".product", "manufacturer, code and generic flag required")
        if "dimmer" in light:
            need(_number(light["dimmer"]) and 0 <= light["dimmer"] <= 1, p+".dimmer", "fraction from 0 to 1 required")
        if light.get("type") == "ies":
            need(_relative_path(light.get("ies")), p+".ies", "safe relative IES path required")
            need(_number(light.get("spin_deg")), p+".spin_deg", "finite number required")
        if light.get("type") in ("area", "line"):
            need(_vector(light.get("size"), 2) and all(x > 0 for x in light["size"]), p+".size", "positive width and length required")
            need(_vector(light.get("length_dir")) and _length(light["length_dir"]) > 0, p+".length_dir", "nonzero vector required")
            need(_number(light.get("spread_deg")) and 0 < light["spread_deg"] <= 180, p+".spread_deg", "angle from 0 to 180 required")
    props = scene.get("props", [])
    if not isinstance(props, list):
        errors.append("props: array required"); props = []
    prop_ids = set()
    for i, prop in enumerate(props):
        p = f"props[{i}]"
        if not isinstance(prop, dict):
            errors.append(p+": object required"); continue
        ident = prop.get("id")
        need(isinstance(ident, str) and bool(ident) and ident not in prop_ids and
             ident not in mesh_ids and ident not in light_ids, p+".id", "unique nonempty id required")
        prop_ids.add(ident)
        need(_relative_path(prop.get("asset")), p+".asset", "safe relative asset name required")
        need(_vector(prop.get("position")), p+".position", "three finite numbers required")
        need(_vector(prop.get("rotation_deg")), p+".rotation_deg", "three finite angles required")
        scale = prop.get("scale")
        need(_number(scale, positive=True) or
             (isinstance(scale, list) and len(scale) == 3 and
              all(_number(axis, positive=True) for axis in scale)),
             p+".scale", "positive scale or three positive axis scales required")
        need(isinstance(prop.get("label"), str) and prop["label"].startswith("dressing: "),
             p+".label", "label must begin 'dressing: '")
    # WP4-A: real furniture models replacing a procedural stand-in where the fit rule allows it (uniform scale,
    # never distorted). Kept separate from `props` because a model REPLACES design furniture (its label is not a
    # "dressing: " item) and carries a `replaces` mesh-id prefix so the renderer hides the procedural geometry it
    # stands in for while still leaving that geometry in the scene (dressing cloth colliders match it by name).
    for i, model in enumerate(scene.get("models", [])):
        p = f"models[{i}]"
        if not isinstance(model, dict):
            errors.append(f"{p}: object required"); continue
        need(isinstance(model.get("id"), str) and bool(model.get("id")) and
             model["id"] not in mesh_ids and model["id"] not in light_ids and model["id"] not in prop_ids,
             p+".id", "unique nonempty id required")
        need(_relative_path(model.get("asset")), p+".asset", "safe relative asset name required")
        need(_vector(model.get("position")), p+".position", "three finite numbers required")
        need(_vector(model.get("rotation_deg")), p+".rotation_deg", "three finite angles required")
        need(model.get("front_axis") in ("+X", "-X", "+Z", "-Z", "none"),
             p+".front_axis", "declared native front axis required")
        need(_number(model.get("layout_rotation_deg")), p+".layout_rotation_deg",
             "finite layout yaw required")
        if model.get("front_axis") in ("+X", "-X", "+Z", "-Z", "none") and _vector(model.get("rotation_deg")) and _number(model.get("layout_rotation_deg")):
            from archpipe.furniture_orientation import check_model_orientation
            try:
                check_model_orientation(model)
            except ValueError as exc:
                errors.append(p + ": " + str(exc))
        need(_number(model.get("scale"), positive=True), p+".scale", "positive uniform scale required")
        need(isinstance(model.get("replaces"), str) and bool(model.get("replaces")),
             p+".replaces", "nonempty mesh-id prefix required (the procedural geometry this model hides)")
        if "decimate_ratio" in model:
            need(_number(model["decimate_ratio"]) and 0 < model["decimate_ratio"] <= 1,
                 p+".decimate_ratio", "fraction from 0 (exclusive) to 1 required")
    exposure = scene.get("exposure")
    if not isinstance(exposure, dict):
        errors.append("exposure: object required"); exposure = {}
    for key, preset in exposure.items():
        need(isinstance(key, str) and bool(key) and isinstance(preset, dict) and
             _number(preset.get("ev100")) and _number(preset.get("white_balance_k"), positive=True),
             "exposure."+str(key), "ev100 and positive white_balance_k required")
    sky = scene.get("sky")
    if not isinstance(sky, dict):
        errors.append("sky: object required"); sky = {}
    if "day" in sky:
        need(sky["day"] == "nishita", "sky.day", "nishita required")
    for state in ("evening", "night"):
        if state in sky:
            setting = sky[state]
            need(isinstance(setting, dict) and _relative_path(setting.get("hdri")) and
                 _number(setting.get("horizontal_lux"), positive=True), "sky."+state,
                 "HDRI and positive horizontal_lux required")
    views = scene.get("views")
    if not isinstance(views, list) or not views:
        errors.append("views: nonempty array required"); views = []
    view_ids = set()
    for i, view in enumerate(views):
        p = f"views[{i}]"
        if not isinstance(view, dict):
            errors.append(p+": object required"); continue
        ident = view.get("id")
        need(isinstance(ident, str) and bool(ident) and ident not in view_ids and "/" not in ident and "\\" not in ident, p+".id", "unique safe id required")
        view_ids.add(ident)
        need(view.get("state") in ("day", "evening", "night", "exterior-dusk"), p+".state",
             "day, evening, night or exterior-dusk required")
        sky_state = sky_state_for_view(view.get("state"))
        need(sky_state in sky, p+".state", "matching sky setting required")
        need(isinstance(view.get("title"), str) and bool(view["title"]), p+".title", "nonempty title required")
        need(_timestamp(view.get("when")), p+".when", "timezone-aware ISO timestamp required")
        need(view.get("exposure") in exposure, p+".exposure", "unknown exposure preset")
        camera = view.get("camera")
        if not isinstance(camera, dict):
            errors.append(p+".camera: object required")
        else:
            need(_vector(camera.get("position")), p+".camera.position", "three finite numbers required")
            need(_vector(camera.get("target")), p+".camera.target", "three finite numbers required")
            if _vector(camera.get("position")) and _vector(camera.get("target")):
                need(_length(_sub(camera["position"], camera["target"])) > 1e-6, p+".camera", "position and target differ")
            for field in ("lens_mm", "sensor_mm"):
                need(_number(camera.get(field), positive=True), p+".camera."+field, "positive number required")
            for field in ("shift_x", "shift_y"):
                if field in camera:
                    need(_number(camera[field]), p+".camera."+field, "finite number required")
        res = view.get("resolution")
        need(isinstance(res, list) and len(res) == 2 and all(isinstance(n, int) and not isinstance(n, bool) and n > 0 for n in res), p+".resolution", "two positive integers required")
        need(isinstance(view.get("samples"), int) and view["samples"] > 0, p+".samples", "positive integer required")
        if "max_bounces" in view:
            need(isinstance(view["max_bounces"], int) and not isinstance(view["max_bounces"], bool) and
                 0 <= view["max_bounces"] <= 64, p+".max_bounces", "integer from 0 to 64 required")
        layers = view.get("layers_on")
        need(isinstance(layers, list) and all(layer in LAYERS for layer in layers), p+".layers_on", "array of known layers required")
        dimmers = view.get("dimmers", {})
        need(isinstance(dimmers, dict) and all(k in LAYERS and _number(v) and 0 <= v <= 1 for k, v in dimmers.items()), p+".dimmers", "layer fractions required")
        need(isinstance(view.get("subjects"), list) and all(isinstance(s, str) for s in view["subjects"]), p+".subjects", "array of strings required")
        if view.get("state") == "day":
            sun = view.get("sun")
            need(isinstance(sun, dict) and _number(sun.get("altitude_deg")) and _number(sun.get("azimuth_true_deg")), p+".sun", "altitude and true azimuth required")
    need(isinstance(scene.get("notes"), list) and all(isinstance(n, str) for n in scene.get("notes", [])), "notes", "array of strings required")
    for i, c in enumerate(scene.get("cloth", [])):
        p = "cloth[%d]" % i
        need(isinstance(c, dict), p, "object required")
        if not isinstance(c, dict):
            continue
        need(isinstance(c.get("id"), str), p+".id", "string required")
        need(c.get("material") in scene.get("materials", {}), p+".material", "must name a material")
        need(isinstance(c.get("colliders"), list) and all(isinstance(x, str) for x in c.get("colliders", [])),
             p+".colliders", "list of mesh-id prefixes required")
        need(isinstance(c.get("size"), list) and len(c["size"]) == 2 and all(_number(v) and 0.1 <= v <= 4
                                                                             for v in c["size"]),
             p+".size", "[w, l] in 0.1-4 m required")
        need(isinstance(c.get("center"), list) and len(c["center"]) == 2 and all(_number(v) for v in c["center"]),
             p+".center", "[x, y] required")
        need(_number(c.get("z_start")), p+".z_start", "number required")
    # Curtains (client 2026-09-28): sheer + a heavy layer on a ceiling track, built and cloth-simulated in
    # villa_scene.build_curtains like the cloth bedding above. The contract fixes the geometric guarantee that
    # keeps the open state clear of a door passage (open_stack_m capped) rather than trusting a formula repeated in
    # two places.
    for i, c in enumerate(scene.get("curtains", [])):
        p = "curtains[%d]" % i
        need(isinstance(c, dict), p, "object required")
        if not isinstance(c, dict):
            continue
        need(isinstance(c.get("id"), str) and bool(c.get("id")), p+".id", "nonempty string required")
        need(isinstance(c.get("room"), str) and bool(c.get("room")), p+".room", "nonempty room string required")
        need(c.get("axis") in ("h", "v"), p+".axis", "expected h (opening runs along x) or v (along y)")
        need(_vector(c.get("center"), 2), p+".center", "[x, y] required")
        need(_number(c.get("width"), positive=True), p+".width", "positive number required")
        need(_number(c.get("floor_z")), p+".floor_z", "number required")
        need(_number(c.get("track_z")) and c.get("track_z", 0) > c.get("floor_z", -1e9),
             p+".track_z", "the track must be above the floor")
        need(c.get("normal_sign") in (-1, 1), p+".normal_sign", "-1 or 1 required")
        # The room-side boundary of the room's own clear_rect (past the wall's full thickness), NOT a small offset
        # from the window line -- that hung the first draft's curtain inside the wall/reveal, behind the frame.
        need(_number(c.get("wall_face")), p+".wall_face", "the wall's room-side face (a clear_rect boundary) required")
        need(c.get("sheer_material") in scene.get("materials", {}), p+".sheer_material", "must name a material")
        need(c.get("heavy_material") in scene.get("materials", {}), p+".heavy_material", "must name a material")
        # Lead review (draft render 2): a flat 0.14 m stack cap held no real fabric (a 2.4-2.76 m door's pair of
        # panels carries ~5 m of fullness). The stack (villa_render's STACK_RATIO x width, ASSUMED, not a cited
        # standard) may now overlap the glazing edge; what it must never do is close a DOOR below a walkable
        # clear width -- render_support.blocked_openings has no notion of "clear width" and would flag any such
        # overlap by design, so that check is NOT used for curtains (see test_curtain_clear_width_through_doors).
        need(c.get("opening_kind") in ("window", "garden-door"), p+".opening_kind", "expected window or garden-door")
        need(_number(c.get("open_pier_reach_m"), positive=True), p+".open_pier_reach_m",
             "positive number required (the wall pier's own extent beyond the opening)")
        need(_number(c.get("open_stack_m"), positive=True) and
             c.get("open_stack_m", -1) >= c.get("open_pier_reach_m", 1e9),
             p+".open_stack_m", "must be at least the pier reach (it starts there and may extend further)")
        if c.get("opening_kind") == "garden-door":
            # DOOR_CLEAR_WIDTH_M == archpipe.concept.villa_furnish.BODY: card mitton-path-of-travel-min, paths of
            # travel at least 36 in (914 mm). A window is never walked through, so it carries no clear-width field.
            need(_number(c.get("open_clear_width_m"), positive=True) and
             c.get("open_clear_width_m", -1) >= DOOR_CLEAR_WIDTH_M - 1e-9,
             p+".open_clear_width_m", "a door's open curtains must leave >= %.3f m clear (F.BODY)" % DOOR_CLEAR_WIDTH_M)
    if not errors:
        from .concept.garden_render_review import downward_ground_findings, plant_form_findings, opening_frame_findings, garden_camera_findings
        errors.extend(downward_ground_findings(scene))
        errors.extend(plant_form_findings(meshes))
        from .concept.garden_render_review import soil_visibility_findings
        errors.extend(soil_visibility_findings(scene))
        from .concept.villa_landscape import north_garden_scene_violations
        errors.extend("%s: %s" % f for f in north_garden_scene_violations(scene))
        for view in scene.get("views", []):
            errors.extend(f"{f['view']}: {f['mesh']} {f['reason']}" for f in opening_frame_findings(view,scene))
            errors.extend(garden_camera_findings(view, scene))
    return errors
