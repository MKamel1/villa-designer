"""Prove the render is photometrically faithful, across the beam.

Run inside Blender:

    blender -b -P validate_render_photometry.py -- --ies f.ies --height 2.0

WHAT THIS ANSWERS

`calibrate_photometry.py` established two facts by measurement:

  * a bare Blender point light of power P gives E = P / (4*pi*d^2), to
    within 0.02% -- so Blender's "Watts" behave as an isotropic photometric
    flux when we choose to read them that way;
  * the IES node does NOT normalise. It returns the file's RAW candela
    divided by a constant. Proved by three synthetic probes: halving the
    candela halved the output exactly, while moving the same candela from
    a full sphere to a hemisphere -- halving the flux -- changed nothing.

That second fact is the important one and it is a trap. If Blender had
normalised by flux, a wide fitting and a narrow one of equal lumens would
render at the same brightness. It does not, so the correct power depends
only on the constant, which makes it universal:

    E_rendered = P * I(theta) / (C * 4*pi * d^2)
    E_true     = I(theta) / d^2          (inverse-square, from the file)

    => P = 4*pi*C   for every IES fitting, whatever its distribution.

Nadir agreement alone does not prove the render faithful, though. The whole
value of an IES profile is the SHAPE of the beam, so this script measures
illuminance at a series of radial offsets and compares each against
`archpipe.lighting`, which was itself validated against hand calculation.
Two independent implementations -- a path tracer and a closed-form
inverse-square sum -- agreeing across the beam is the evidence worth having.

METHOD

A Lambertian plane of known albedo; for a horizontal surface

    E = I(theta) * cos(theta) / d^2      and      L = E * rho / pi

so a linear (Standard view transform, OpenEXR) render gives E back as
L * pi / rho. Bounces are disabled so the measurement is the direct
component only -- exactly what the analytical engine computes. Comparing a
full global-illumination render against a direct-only formula would
disagree for a real reason and teach nothing.
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


ALBEDO = 0.5
PATCH = 0.04          # metres across, the measuring window


def argv_after_dashes():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(args, name, default=None, cast=str):
    return cast(args[args.index(name) + 1]) if name in args else default


def clear():
    for block in (bpy.data.objects, bpy.data.meshes, bpy.data.lights,
                  bpy.data.materials, bpy.data.cameras, bpy.data.images):
        for item in list(block):
            block.remove(item, do_unlink=True)


def build(power, height, ies_path):
    clear()
    bpy.ops.mesh.primitive_plane_add(size=40.0, location=(0, 0, 0))
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
    bpy.context.active_object.data.materials.append(mat)

    ld = bpy.data.lights.new("fixture", type="POINT")
    ld.energy = power
    ld.shadow_soft_size = 0.0
    ld.use_nodes = True
    nt = ld.node_tree
    ies = nt.nodes.new("ShaderNodeTexIES")
    ies.mode = "EXTERNAL"
    ies.filepath = ies_path
    ies.inputs["Strength"].default_value = 1.0
    nt.links.new(ies.outputs["Fac"], nt.nodes["Emission"].inputs["Strength"])
    obj = bpy.data.objects.new("fixture", ld)
    obj.location = (0, 0, height)
    bpy.context.collection.objects.link(obj)

    cd = bpy.data.cameras.new("cam")
    cd.type = "ORTHO"
    cd.ortho_scale = PATCH
    cam = bpy.data.objects.new("cam", cd)
    cam.rotation_euler = (0, 0, 0)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    return cam


def configure(samples=512, res=24):
    s = bpy.context.scene
    s.render.engine = "CYCLES"
    s.cycles.samples = samples
    s.cycles.use_denoising = False
    s.render.resolution_x = res
    s.render.resolution_y = res
    s.render.image_settings.file_format = "OPEN_EXR"
    s.render.image_settings.color_depth = "32"
    s.view_settings.view_transform = "Standard"
    s.view_settings.look = "None"
    s.view_settings.exposure = 0.0
    s.view_settings.gamma = 1.0
    w = bpy.data.worlds.new("black")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.0
    s.world = w
    # Direct component only, to match the analytical engine exactly.
    s.cycles.max_bounces = 0
    s.cycles.diffuse_bounces = 0


def read(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(path)
    px = list(img.pixels)
    n = len(px) // 4
    v = sum(luminance(px[i * 4], px[i * 4 + 1], px[i * 4 + 2])
            for i in range(n)) / n
    bpy.data.images.remove(img)
    return v * math.pi / ALBEDO          # radiance -> illuminance


def main():
    args = argv_after_dashes()
    ies_path = arg(args, "--ies")
    height = arg(args, "--height", 2.0, float)
    power = arg(args, "--power", 4.0 * math.pi * 13.0577, float)
    out_dir = arg(args, "--out", "/tmp")
    offsets = [float(v) for v in
               arg(args, "--offsets", "0,0.25,0.5,0.75,1.0,1.5,2.0").split(",")]

    configure()
    cam = build(power, height, ies_path)

    rows = []
    for r in offsets:
        cam.location = (r, 0.0, height * 0.5)
        e = read(os.path.join(out_dir, "val_%0.2f.exr" % r))
        rows.append({"offset_m": r, "E_rendered": e})
        print("VAL offset=%.3f E_rendered=%.4f" % (r, e))

    print("VAL JSON " + json.dumps(
        {"ies": os.path.basename(ies_path), "height": height,
         "power": power, "rows": rows}))
    print("VAL DONE")


if __name__ == "__main__":
    main()
