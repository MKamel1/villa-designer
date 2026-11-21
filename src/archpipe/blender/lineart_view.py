"""Blender side of the 2D sections/elevations: bake Grease Pencil Line Art for one orthographic view.

Run:  blender -b --factory-startup -P lineart_view.py -- IN.json OUT.json
IN  = {"faces": [[[x,y,z],...], ...] (metres), "dir": [dx,dy,dz] unit view direction (camera looks along it),
       "origin": [x,y,z] a point the camera aims at, "ortho_scale": m, "back": m camera distance behind origin}
OUT = {"strokes": [[[x,y,z],...], ...]} world-space polylines (occluded edges removed; see lineart_probe.py).
"""
import json
import math
import sys

import bpy
from mathutils import Vector


def main():
    a = sys.argv[sys.argv.index("--") + 1:]
    spec = json.load(open(a[0]))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    verts, faces = [], []
    for f in spec["faces"]:
        i0 = len(verts)
        verts += [tuple(v) for v in f]
        faces.append(tuple(range(i0, i0 + len(f))))
    me = bpy.data.meshes.new("scene")
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new("scene", me)
    sc.collection.objects.link(ob)
    d = Vector(spec["dir"]).normalized()
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = spec["ortho_scale"]
    cam.data.clip_start = 0.001
    cam.data.clip_end = spec["back"] * 2 + 200
    sc.collection.objects.link(cam)
    cam.location = Vector(spec["origin"]) - d * spec["back"]
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    sc.render.resolution_x = sc.render.resolution_y = 1000
    gp = bpy.data.grease_pencils_v3.new("LA")
    go = bpy.data.objects.new("LA", gp)
    sc.collection.objects.link(go)
    gp.layers.new("lines")
    mat = bpy.data.materials.new("lm")
    bpy.data.materials.create_gpencil_data(mat)
    gp.materials.append(mat)
    m = go.modifiers.new("LA", "LINEART")
    m.source_type = "SCENE"
    m.target_layer = "lines"
    m.target_material = mat
    m.use_contour = True
    m.use_crease = True
    m.crease_threshold = math.radians(140)       # edges turning more than 40 degrees (box edges are 90)
    m.use_intersection = True
    m.use_material = False
    m.use_edge_mark = False
    m.use_loose = False
    m.thickness = 2
    bpy.context.view_layer.update()
    ev = go.evaluated_get(bpy.context.evaluated_depsgraph_get())
    out = []
    for layer in ev.data.layers:
        for fr in layer.frames:
            for s in fr.drawing.strokes:
                out.append([[round(c, 4) for c in p.position] for p in s.points])
    json.dump({"strokes": out}, open(a[1], "w"))
    print("LINEART-VIEW ok strokes=%d faces=%d" % (len(out), len(faces)))


main()
