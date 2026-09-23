"""Measure what Blender's light units mean in lux, instead of guessing.

Run inside Blender:

    blender -b -P calibrate_photometry.py -- --ies /path/to/file.ies

WHY THIS EXISTS

`build_scene.py` used to set `light.energy = watts * 10.0`. That magic 10
is the reason a render could not be trusted as a representation of
lighting: the number had no physical meaning, so the image was a picture
of *a* lighting scheme, not *the* lighting scheme.

To render faithfully we need two facts, and neither is safe to take from a
forum post, because Blender's conventions have changed between releases:

  1. Given a light of power P (Blender's "Watts"), what illuminance does a
     surface at distance d actually receive?
  2. When an IES profile is attached, is the light's total output preserved
     or renormalised? If Blender rescales to the profile's peak, then two
     fittings with the same lumens but different beam angles would render
     at different brightness -- silently.

Both are measured here against a case with a closed-form answer.

THE METHOD

A Lambertian plane of known albedo under a point light has a radiance
that can be written down:

    E = I / d^2            illuminance from a point source, normal incidence
    L = E * rho / pi       radiance leaving a Lambertian surface

So rendering that plane and reading the linear pixel value gives E back:

    E = L * pi / rho

Render to OpenEXR with the view transform set to Standard, so the number
in the file is scene-linear radiance and not a tone-mapped display value.
Tone mapping is the single easiest way to get a confident wrong answer
here -- Filmic or AgX would roll off the highlights and every measurement
would read low.

The camera is orthographic and tiny, pointed straight down at the spot
directly beneath the light, so every sampled pixel is the same measurement
and averaging them just reduces noise.
"""
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


ALBEDO = 0.5          # the measuring surface; mid grey, well away from 0 or 1
HEIGHT = 2.0          # metres, light above the plane
LUMENS = 1000.0       # the flux we ask for


def argv_after_dashes():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def clear():
    for block in (bpy.data.objects, bpy.data.meshes, bpy.data.lights,
                  bpy.data.materials, bpy.data.cameras, bpy.data.images):
        for item in list(block):
            block.remove(item, do_unlink=True)


def build(power, ies_path=None, ies_strength=1.0):
    """A grey plane, a point light above it, an orthographic camera."""
    clear()

    bpy.ops.mesh.primitive_plane_add(size=20.0, location=(0, 0, 0))
    plane = bpy.context.active_object
    mat = bpy.data.materials.new("measure")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    # A PURE LAMBERTIAN surface, not the Principled BSDF.
    #
    # Measured: with Principled at roughness 1.0 the readings came back
    # exactly right at normal incidence and a flat 0.92% high at every
    # oblique angle from 7 to 45 degrees. That is Blender 4.x's diffuse
    # retro-reflection (Oren-Nayar-like) term, and `L = E*rho/pi` assumes
    # a Lambertian reflector. Diffuse BSDF at roughness 0 is Lambertian in
    # Cycles, so the formula and the shader now describe the same surface.
    diff = nt.nodes.new("ShaderNodeBsdfDiffuse")
    diff.inputs["Color"].default_value = (ALBEDO, ALBEDO, ALBEDO, 1.0)
    diff.inputs["Roughness"].default_value = 0.0
    nt.links.new(diff.outputs["BSDF"],
                 nt.nodes["Material Output"].inputs["Surface"])
    plane.data.materials.append(mat)

    light_data = bpy.data.lights.new("probe", type="POINT")
    light_data.energy = power
    # A true point source, to match the closed-form expression. A real
    # fitting has size and softer shadows; that is a separate choice made
    # in build_scene.py, not something to blur the calibration with.
    light_data.shadow_soft_size = 0.0
    light_data.use_nodes = True

    if ies_path:
        nt = light_data.node_tree
        out = nt.nodes["Light Output"]
        emission = nt.nodes["Emission"]
        ies = nt.nodes.new("ShaderNodeTexIES")
        ies.mode = "EXTERNAL"
        ies.filepath = ies_path
        ies.inputs["Strength"].default_value = ies_strength
        nt.links.new(ies.outputs["Fac"], emission.inputs["Strength"])
        nt.links.new(emission.outputs["Emission"], out.inputs["Surface"])

    light = bpy.data.objects.new("probe", light_data)
    light.location = (0, 0, HEIGHT)
    bpy.context.collection.objects.link(light)

    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = 0.05          # 50 mm across: a spot measurement
    cam = bpy.data.objects.new("cam", cam_data)
    cam.location = (0, 0, 1.0)
    cam.rotation_euler = (0, 0, 0)       # looking straight down -Z
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    return plane, light


def configure(samples=256, res=32):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False   # denoising biases a measurement
    scene.render.resolution_x = res
    scene.render.resolution_y = res
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.image_settings.color_depth = "32"
    scene.render.film_transparent = False
    # THE CRITICAL SETTING. Any view transform other than Standard applies
    # a tone curve, and every reading would come back wrong -- low, and
    # plausibly so.
    try:
        scene.view_settings.view_transform = "Standard"
        scene.view_settings.look = "None"
        scene.view_settings.exposure = 0.0
        scene.view_settings.gamma = 1.0
    except Exception as e:
        print("CAL WARNING could not force Standard view transform: %s" % e)
    # No ambient light: we are measuring one source, not a room.
    world = bpy.data.worlds.new("black")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0, 0, 0, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.0
    scene.world = world
    # One bounce of direct light only. Inter-reflection from the plane back
    # onto itself would add to the reading and is not in the formula.
    scene.cycles.max_bounces = 0
    scene.cycles.diffuse_bounces = 0


def render_and_read(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(path)
    px = list(img.pixels)
    n = len(px) // 4
    # Average the channels and all pixels: the light is white and the
    # camera is looking at a uniform patch, so this is noise reduction.
    total = sum(luminance(px[i * 4], px[i * 4 + 1], px[i * 4 + 2])
                for i in range(n))
    bpy.data.images.remove(img)
    return total / n


def illuminance_from_radiance(radiance):
    """Invert L = E*rho/pi."""
    return radiance * math.pi / ALBEDO


def main():
    global HEIGHT
    args = argv_after_dashes()
    ies_path = None
    if "--ies" in args:
        ies_path = args[args.index("--ies") + 1]
    out_dir = args[args.index("--out")+1] if "--out" in args else "/tmp"

    configure()
    results = {}

    # ---------------------------------------------------------------- test 1
    # Does Blender's point light follow E = P / (4*pi*d^2)?
    # If it does, then setting power numerically equal to LUMENS makes the
    # rendered radiance numerically consistent with lux, and no magic
    # constant is needed anywhere.
    build(LUMENS)
    rad = render_and_read(os.path.join(out_dir, "cal_bare.exr"))
    measured = illuminance_from_radiance(rad)
    predicted = LUMENS / (4.0 * math.pi * HEIGHT ** 2)
    results["bare"] = {
        "power_set": LUMENS, "radiance": rad, "measured_E": measured,
        "predicted_E_isotropic": predicted,
        "ratio_measured_over_predicted": measured / predicted if predicted else None,
    }
    print("CAL bare power=%.1f radiance=%.6f E_measured=%.4f "
          "E_predicted=%.4f ratio=%.6f"
          % (LUMENS, rad, measured, predicted, measured / predicted))

    # Linearity: double the power, expect exactly double the reading. If
    # this is not 2.0 something is clamping or tone mapping.
    build(LUMENS * 2)
    rad2 = render_and_read(os.path.join(out_dir, "cal_bare2.exr"))
    results["linearity"] = {"radiance_2x": rad2,
                            "ratio": rad2 / rad if rad else None}
    print("CAL linearity radiance_2x=%.6f ratio=%.6f" % (rad2, rad2 / rad))

    # Inverse square: double the distance, expect a quarter.
    h0 = HEIGHT
    HEIGHT = h0 * 2
    build(LUMENS)
    rad_far = render_and_read(os.path.join(out_dir, "cal_far.exr"))
    HEIGHT = h0
    results["inverse_square"] = {
        "radiance_2d": rad_far,
        "ratio_expected_0.25": rad_far / rad if rad else None}
    print("CAL inverse_square radiance_2d=%.6f ratio=%.6f (expect 0.25)"
          % (rad_far, rad_far / rad))

    # ---------------------------------------------------------------- test 2
    # With an IES profile attached, is total flux preserved or is the
    # light renormalised to the profile's peak? This decides whether two
    # fittings of equal lumens but different beam angles render at the
    # same brightness, which is the difference between a faithful scene
    # and a decorative one.
    if ies_path and os.path.isfile(ies_path):
        build(LUMENS, ies_path=ies_path)
        rad_ies = render_and_read(os.path.join(out_dir, "cal_ies.exr"))
        e_ies = illuminance_from_radiance(rad_ies)
        results["ies"] = {
            "file": ies_path, "radiance": rad_ies, "measured_E_nadir": e_ies,
            "ratio_to_bare": rad_ies / rad if rad else None}
        print("CAL ies file=%s radiance=%.6f E_nadir=%.4f ratio_to_bare=%.6f"
              % (os.path.basename(ies_path), rad_ies, e_ies,
                 rad_ies / rad if rad else float("nan")))
    else:
        print("CAL ies SKIPPED (no --ies path given or file missing)")

    print("CAL JSON " + json.dumps(results))
    print("CAL DONE")


if __name__ == "__main__":
    main()
