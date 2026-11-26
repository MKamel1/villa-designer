"""Render the real scanned throw pillows (Poly Haven throw_pillows_01, CC0) on a bare seat: the negative control for the
furniture VLM question. blender -b -P soft_ref_render.py -- <library_root> <out.png>"""
import math
import sys

import bpy

lib, out = sys.argv[sys.argv.index("--") + 1:][:2]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=lib + "/props/throw_pillows_01/model.gltf")
for o in bpy.context.scene.objects:
    if o.type == "MESH":
        o.rotation_euler = (math.radians(90) if o.parent is None else 0, 0, 0)
bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 0, -0.45))
bpy.context.object.data.materials.append(bpy.data.materials.new("seat"))
bpy.context.object.data.materials[0].diffuse_color = (0.55, 0.5, 0.42, 1)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
bpy.context.collection.objects.link(cam)
cam.location = (0.0, -2.2, 0.35)
cam.rotation_euler = (math.radians(80), 0, 0)
bpy.context.scene.camera = cam
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "AREA"))
sun.data.energy, sun.data.size = 600, 3
sun.location = (1.5, -1.5, 2.5)
sun.rotation_euler = (math.radians(45), 0, math.radians(30))
bpy.context.collection.objects.link(sun)
w = bpy.data.worlds.new("w")
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[1].default_value = 0.6
bpy.context.scene.world = w
s = bpy.context.scene
s.render.engine = "CYCLES"
s.cycles.samples = 64
s.cycles.device = "CPU"
s.render.resolution_x, s.render.resolution_y = 800, 600
s.render.filepath = out
bpy.ops.render.render(write_still=True)
