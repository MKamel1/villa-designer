"""Measure illuminance from the render itself, as a lux grid.

    blender -b -P measure_lux.py -- --extract model.json --out lux.json \
        [--plane 850] [--bounces 0|16] [--res 128] [--samples 512]

WHY THIS MATTERS

`archpipe.lighting` computes the DIRECT component only, which is why
ADR-0009 refuses to give a uniformity verdict: EN 12464-1's U0 is defined
on total illuminance, and in a real room most of the light at the darkest
point has bounced. The analytical engine cannot see that light.

Cycles can. It is an unbiased path tracer, so with the photometric
calibration established in ADR-0010 it produces total illuminance --
direct plus every bounce -- as a measurement rather than an estimate.

So this script serves two purposes, and the flag that switches between
them is `--bounces`:

    --bounces 0    direct component only. Must agree with
                   `archpipe.lighting`; that agreement is what proves the
                   render is faithful, because the two are completely
                   independent implementations.

    --bounces 16   total illuminance, inter-reflection included. This is
                   the quantity a real U0 needs.

THE MEASURING PLANE

Illuminance is wanted on the working plane, which is imaginary. Inserting
a real surface there would block light from reaching the floor and change
the very inter-reflection we are trying to measure.

Blender's per-object ray visibility solves it exactly: the probe is
invisible to diffuse, glossy, transmission and shadow rays, so no other
surface can see it and the scene behaves as though it were not there,
while the camera still sees it. A passive instrument.

Its albedo is then inverted out of the reading:

    L = E * rho / pi    =>    E = L * pi / rho
"""
import importlib.util
import json
import math
import os
import sys

import bpy

# Rec. 709 luminance coefficients. Illuminance is a PHOTOMETRIC quantity:
# it weights the spectrum by the eye's response, and in an RGB renderer
# that weighting is the luminance, not the arithmetic mean of the
# channels.
#
# Measured cost of getting this wrong: with the mean, a 2700 K lamp reads
# 5.6% low and a 3000 K lamp 4.3% low, while a neutral white lamp reads
# correctly -- so the error hides completely during calibration with white
# light and only appears once colour temperature is set. It showed up here
# as a flat 0.951 ratio against the analytical engine across a whole room.
LUM_R, LUM_G, LUM_B = 0.2126, 0.7152, 0.0722


def luminance(r, g, b):
    return LUM_R * r + LUM_G * g + LUM_B * b


HERE = os.path.dirname(os.path.abspath(__file__))
PROBE_ALBEDO = 0.5


def load_build_scene():
    """Import build_scene.py from beside this file.

    Blender does not put the script's directory on sys.path, so a plain
    import would fail depending on where blender was launched from.
    """
    path = os.path.join(HERE, "build_scene.py")
    spec = importlib.util.spec_from_file_location("archpipe_build_scene", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def arg(args, name, default=None, cast=str):
    return cast(args[args.index(name) + 1]) if name in args else default


def add_probe(x0, y0, x1, y1, z):
    """A horizontal plane the camera can see and nothing else can."""
    bpy.ops.mesh.primitive_plane_add(size=1.0,
                                     location=((x0 + x1) / 2, (y0 + y1) / 2, z))
    probe = bpy.context.active_object
    probe.name = "lux_probe"
    probe.scale = (max(x1 - x0, 1e-3), max(y1 - y0, 1e-3), 1.0)

    mat = bpy.data.materials.new("lux_probe_mat")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    # Lambertian, to match E = L*pi/rho exactly. Measured on this project:
    # the Principled BSDF at roughness 1 reads a flat 0.9% high at oblique
    # angles because of its diffuse retro-reflection term.
    d = nt.nodes.new("ShaderNodeBsdfDiffuse")
    d.inputs["Color"].default_value = (PROBE_ALBEDO, PROBE_ALBEDO,
                                       PROBE_ALBEDO, 1.0)
    d.inputs["Roughness"].default_value = 0.0
    nt.links.new(d.outputs["BSDF"], nt.nodes["Material Output"].inputs["Surface"])
    probe.data.materials.append(mat)

    # Invisible to everything except the camera, so it does not perturb the
    # light transport it is measuring.
    for attr in ("visible_diffuse", "visible_glossy", "visible_transmission",
                 "visible_volume_scatter", "visible_shadow"):
        if hasattr(probe, attr):
            setattr(probe, attr, False)
    return probe


def add_ortho_camera(x0, y0, x1, y1, z):
    cd = bpy.data.cameras.new("lux_cam")
    cd.type = "ORTHO"
    cd.ortho_scale = max(x1 - x0, y1 - y0)
    cam = bpy.data.objects.new("lux_cam", cd)
    cam.location = ((x0 + x1) / 2, (y0 + y1) / 2, z + 0.5)
    cam.rotation_euler = (0.0, 0.0, 0.0)      # straight down -Z
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    return cam


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    extract = arg(argv, "--extract")
    out_path = arg(argv, "--out", "lux.json")
    plane_mm = arg(argv, "--plane", 850.0, float)
    bounces = arg(argv, "--bounces", 16, int)
    res = arg(argv, "--res", 128, int)
    samples = arg(argv, "--samples", 512, int)
    exr_path = arg(argv, "--exr", "/tmp/lux_probe.exr")

    if not extract or not os.path.isfile(extract):
        print("LUX ERROR --extract <model.json> is required")
        sys.exit(2)

    bs = load_build_scene()
    with open(extract) as fh:
        data = json.load(fh)

    bs.clear_scene()
    wall_mat = bs.surface("wall", bs.REFLECTANCE["wall"],
                          tint=(1.00, 0.99, 0.95), roughness=0.75)
    floor_mat = bs.surface("floor", bs.REFLECTANCE["floor"],
                           tint=(1.00, 0.72, 0.45), roughness=0.45)
    ceiling_mat = bs.surface("ceiling", bs.REFLECTANCE["ceiling"],
                             tint=(1.0, 1.0, 1.0), roughness=0.85)
    walls = bs.build_walls(data, wall_mat)
    bs.build_floors(data, floor_mat)
    # The ceiling is what returns a downlight scheme's light to the upper
    # half of the room. Without it the inter-reflected component is not
    # merely inaccurate, it is largely absent. The measuring camera sits
    # below it and is unaffected.
    bs.build_ceilings(data, ceiling_mat)
    bs.cut_openings(data, walls)
    lights = bs.build_lights(data)
    if not lights:
        print("LUX ERROR the extract carries no light fixtures, so there is "
              "nothing to measure")
        sys.exit(3)

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False          # a denoiser biases a reading
    scene.cycles.sample_clamp_direct = 0.0
    scene.cycles.sample_clamp_indirect = 0.0    # clamping discards energy
    scene.cycles.max_bounces = bounces
    scene.cycles.diffuse_bounces = bounces
    scene.cycles.glossy_bounces = bounces
    scene.cycles.transmission_bounces = bounces
    scene.render.resolution_x = scene.render.resolution_y = res
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.image_settings.color_depth = "32"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0

    # No sky unless the extract asked for one: a world background is real
    # light and would be counted, correctly, as part of the answer.
    world = bpy.data.worlds.new("lux_world")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.0
    scene.world = world

    x0, y0, x1, y1 = bs.bounds(data)
    z = bs.m(plane_mm)
    add_probe(x0, y0, x1, y1, z)
    add_ortho_camera(x0, y0, x1, y1, z)

    scene.render.filepath = exr_path
    bpy.ops.render.render(write_still=True)

    img = bpy.data.images.load(exr_path)
    w, h = img.size
    px = list(img.pixels)
    span = max(x1 - x0, y1 - y0)

    rows = []
    for j in range(h):
        for i in range(w):
            k = (j * w + i) * 4
            lum = luminance(px[k], px[k + 1], px[k + 2])
            lux = lum * math.pi / PROBE_ALBEDO
            # Pixel centre -> world. The ortho camera is square and centred,
            # and image row 0 is the BOTTOM in Blender, which matches +Y.
            cx = (x0 + x1) / 2 + ((i + 0.5) / w - 0.5) * span
            cy = (y0 + y1) / 2 + ((j + 0.5) / h - 0.5) * span
            rows.append([round(cx * 1000.0, 1), round(cy * 1000.0, 1),
                         round(lux, 3)])
    bpy.data.images.remove(img)

    result = {
        "source": os.path.basename(extract),
        "working_plane_mm": plane_mm,
        "bounces": bounces,
        "samples": samples,
        "resolution": res,
        "probe_albedo": PROBE_ALBEDO,
        "bounds_mm": [x0 * 1000.0, y0 * 1000.0, x1 * 1000.0, y1 * 1000.0],
        "span_mm": span * 1000.0,
        "fixtures": len(lights),
        "furniture_included": False,
        "units": "mm, lux",
        "note": ("Total illuminance including inter-reflection."
                 if bounces else
                 "Direct component only -- comparable with archpipe.lighting."),
        "points": rows,
    }
    with open(out_path, "w") as fh:
        json.dump(result, fh)

    vals = [r[2] for r in rows]
    print("LUX wrote %s  %d points  Eavg=%.1f Emin=%.1f Emax=%.1f bounces=%d"
          % (out_path, len(rows), sum(vals) / len(vals), min(vals),
             max(vals), bounces))
    print("LUX DONE")


if __name__ == "__main__":
    main()
