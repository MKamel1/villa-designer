"""Megascans material wiring shared by fab_preview.py and atlas_panel.py (Blender, headless). Textures are read only from the
archive's own JPGs; single-channel maps (Opacity, Roughness, Gloss, AO, Displacement) hold their data in the RED channel,
so every one goes through red() (the pass-5 ghost-leaf defect; guarded in tests/landscape/plants/test_assets.py)."""
import glob, math, os
import bpy


def maps_of(d):
    """{MapName: path} of the archive's non-billboard JPGs, plus the 'prefix_res' stem."""
    m, stem = {}, None
    for f in sorted(glob.glob(d + "/*.jpg")):
        b = os.path.basename(f)[:-4]
        if "_Billboard_" in b:
            continue
        pre, name = b.rsplit("_", 1)
        m[name] = f; stem = pre
    return m, stem


def tex(nt, path, noncolor, name):
    n = nt.nodes.new("ShaderNodeTexImage"); n.image = bpy.data.images.load(path); n.label = name
    n.image.colorspace_settings.name = "Non-Color" if noncolor else "sRGB"
    return n


def red(nt, t):
    """Megascans single-channel maps (Opacity, Roughness, Gloss, AO, Displacement) keep the data in the RED channel only
    (G and B are ~0 in the JPG: measured). Read as colour -> luminance they come out ~5x too dark (leaves went ghostly)."""
    sp = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(t.outputs["Color"], sp.inputs["Color"])
    return sp.outputs["Red"]


def build_material(mat, maps, meta, uvscale=None):
    mat.use_nodes = True
    nt = mat.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    pb = nt.nodes.new("ShaderNodeBsdfPrincipled")
    coord = None
    def src(t):
        if uvscale:
            if coord[0] is None:
                coord[0] = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
                mp.inputs["Scale"].default_value = (uvscale, uvscale, 1); nt.links.new(coord[0].outputs["UV"], mp.inputs["Vector"]); coord[1] = mp
            nt.links.new(coord[1].outputs["Vector"], t.inputs["Vector"])
    coord = [None, None]
    bc = tex(nt, maps["BaseColor"], False, "BaseColor"); src(bc); nt.links.new(bc.outputs["Color"], pb.inputs["Base Color"])
    if "Roughness" in maps:
        r = tex(nt, maps["Roughness"], True, "Roughness"); src(r); nt.links.new(red(nt, r), pb.inputs["Roughness"])
    elif "Gloss" in maps:
        r = tex(nt, maps["Gloss"], True, "Gloss"); src(r)
        inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0
        nt.links.new(red(nt, r), inv.inputs[1]); nt.links.new(inv.outputs[0], pb.inputs["Roughness"])
    if "Normal" in maps:
        n = tex(nt, maps["Normal"], True, "Normal"); src(n)
        nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(n.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], pb.inputs["Normal"])
    shader = pb.outputs["BSDF"]
    if "Translucency" in maps:                       # backlit leaf: translucent BSDF tinted by the JSON's Translucency Tint
        tr = tex(nt, maps["Translucency"], False, "Translucency"); src(tr)
        tint = next((p["Value"] for p in meta.get("material_params", {}).get("material", []) if p["Name"] == "Translucency Tint"), None)
        col = tr.outputs["Color"]
        if tint:
            mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"; mx.inputs[0].default_value = 1.0
            mx.inputs[7].default_value = tuple(tint[:3]) + (1,)
            nt.links.new(col, mx.inputs[6]); col = mx.outputs[2]
        tb = nt.nodes.new("ShaderNodeBsdfTranslucent"); nt.links.new(col, tb.inputs["Color"])
        ms = nt.nodes.new("ShaderNodeMixShader"); ms.inputs[0].default_value = 0.3
        nt.links.new(shader, ms.inputs[1]); nt.links.new(tb.outputs[0], ms.inputs[2]); shader = ms.outputs[0]
    if "Opacity" in maps:
        o = tex(nt, maps["Opacity"], True, "Opacity"); src(o)
        tp = nt.nodes.new("ShaderNodeBsdfTransparent"); mo = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(red(nt, o), mo.inputs[0]); nt.links.new(tp.outputs[0], mo.inputs[1]); nt.links.new(shader, mo.inputs[2]); shader = mo.outputs[0]
    nt.links.new(shader, out.inputs["Surface"])


def reset_scene(RES, SAMPLES):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = False
    sc.cycles.transparent_max_bounces = 24
    sc.render.resolution_x = sc.render.resolution_y = RES
    sc.render.image_settings.file_format = "PNG"
    try:
        if os.environ.get("ARCHPIPE_CPU"): raise RuntimeError("CPU requested (GPU lock held elsewhere)")
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "CUDA"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type == "CUDA"
        sc.cycles.device = "GPU"
    except Exception as e:
        print("GPU not available:", e)
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.62, 0.72, 0.9, 1); bg.inputs[1].default_value = 1.0
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sun.data.energy = 4.0
    sun.rotation_euler = (math.radians(50), 0, math.radians(35)); sc.collection.objects.link(sun)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); cam.data.lens, cam.data.sensor_width = 35, 36
    sc.collection.objects.link(cam); sc.camera = cam
    g = bpy.data.objects.new("g", bpy.data.meshes.new("g"))
    g.data.from_pydata([(-60, -60, -0.002), (60, -60, -0.002), (60, 60, -0.002), (-60, 60, -0.002)], [], [(0, 1, 2, 3)])
    gm = bpy.data.materials.new("gm"); gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.3, 0.26, 0.2, 1); g.data.materials.append(gm)
    sc.collection.objects.link(g)
    return sc, cam
