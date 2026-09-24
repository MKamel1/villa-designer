"""Measure Blender's Nishita sky: which way is the sun, and how many lux.

Run inside Blender:

    blender -b -P calibrate_sky.py -- --elevation 35 --rotation 0

Two facts the presentation renders depend on, measured rather than
assumed (the same discipline as calibrate_photometry.py):

1. DIRECTION. `sun_rotation` is an angle about the zenith, but the manual
   does not say where 0 points. A white sphere viewed straight down from
   above is brightest where its normal faces the sun, so the luminance-
   weighted centroid of its top view gives the sun's azimuth in world XY.

2. ILLUMINANCE. A horizontal Lambertian plane of known albedo has
   E = L * pi / rho. With the project's calibrated convention (one Blender
   watt reads as one lumen; calibrate_photometry.py) this is lux, directly
   comparable with the IES fixtures.

Prints `SKY JSON {...}`.
"""
import json
import math
import os
import sys
import tempfile

import bpy

ALBEDO = 0.5


def arg(name, default, cast=float):
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return cast(args[args.index(name) + 1]) if name in args else default


def luminance(r, g, b):
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def lambert(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    d = nt.nodes.new("ShaderNodeBsdfDiffuse")
    d.inputs["Color"].default_value = (ALBEDO, ALBEDO, ALBEDO, 1.0)
    d.inputs["Roughness"].default_value = 0.0
    nt.links.new(d.outputs["BSDF"], nt.nodes["Material Output"].inputs["Surface"])
    return mat


def render_pixels(res):
    s = bpy.context.scene
    s.render.resolution_x = s.render.resolution_y = res
    path = os.path.join(tempfile.mkdtemp(), "probe.exr")
    s.render.filepath = path
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(path)
    px = list(img.pixels)
    bpy.data.images.remove(img)
    return [luminance(px[i], px[i + 1], px[i + 2]) for i in range(0, len(px), 4)]


def main():
    elevation = arg("--elevation", 35.0)
    rotation = arg("--rotation", 0.0)
    for block in (bpy.data.objects, bpy.data.meshes, bpy.data.materials,
                  bpy.data.cameras, bpy.data.lights):
        for item in list(block):
            block.remove(item, do_unlink=True)

    s = bpy.context.scene
    s.render.engine = "CYCLES"
    s.cycles.samples = 256
    s.cycles.use_denoising = False
    s.render.image_settings.file_format = "OPEN_EXR"
    s.render.image_settings.color_depth = "32"
    s.view_settings.view_transform = "Standard"
    s.view_settings.look = "None"
    s.view_settings.exposure = 0.0
    s.cycles.max_bounces = 0          # direct sun + sky only, no ground bounce

    world = bpy.data.worlds.new("sky")
    world.use_nodes = True
    sky = world.node_tree.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "NISHITA"
    sky.sun_disc = True
    sky.sun_elevation = math.radians(elevation)
    sky.sun_rotation = math.radians(rotation)
    world.node_tree.links.new(sky.outputs["Color"],
                              world.node_tree.nodes["Background"].inputs["Color"])
    s.world = world

    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam = bpy.data.objects.new("cam", cam_data)
    bpy.context.collection.objects.link(cam)
    s.camera = cam

    # 1. Illuminance on an open horizontal plane.
    bpy.ops.mesh.primitive_plane_add(size=4.0, location=(0, 0, 0))
    plane = bpy.context.active_object
    plane.data.materials.append(lambert("plane"))
    cam_data.ortho_scale = 0.5
    cam.location = (0, 0, 1.0)
    cam.rotation_euler = (0, 0, 0)
    vals = render_pixels(16)
    lux = sum(vals) / len(vals) * math.pi / ALBEDO

    # 2. Sun azimuth from a sphere seen from directly above.
    plane.hide_render = True
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=(0, 0, 0),
                                         segments=64, ring_count=32)
    sphere = bpy.context.active_object
    sphere.data.materials.append(lambert("sphere"))
    bpy.ops.object.shade_smooth()
    cam_data.ortho_scale = 2.2
    cam.location = (0, 0, 5.0)
    res = 96
    vals = render_pixels(res)
    peak = max(vals)
    sx = sy = sw = 0.0
    for j in range(res):            # Blender pixels: row 0 is the bottom
        for i in range(res):
            v = vals[j * res + i]
            if v < 0.9 * peak:
                continue
            w = v
            sx += w * ((i + 0.5) / res - 0.5)
            sy += w * ((j + 0.5) / res - 0.5)
            sw += w
    # Image +x is world +x and image +y is world +y for this camera.
    math_angle = math.degrees(math.atan2(sy, sx))          # CCW from +X
    compass_az = (90.0 - math_angle) % 360.0               # CW from +Y (north)

    print("SKY JSON " + json.dumps({
        "elevation_deg": elevation, "sun_rotation_deg": rotation,
        "horizontal_lux_direct_plus_sky": lux,
        "sun_direction_math_deg_ccw_from_x": math_angle,
        "sun_direction_compass_az_deg_cw_from_y": compass_az}))


main()
