"""Proof (RV2 step 1): Grease Pencil Line Art can be baked headless in Blender 4.5 and read back as 3D polylines.

Run on the workstation:  ~/opt/blender/blender -b --factory-startup -P src/archpipe/blender/lineart_probe.py

Fixture: three boxes (a: 4x4x2 at the origin; b: 2x2x2 on top of a, toward the viewer; c: 2x2x2 behind a).
Orthographic camera at y = -30 looking along +y (an elevation of the fixture from -y).
Writes nothing; prints `LINEART-PROBE ok strokes=N` or raises.  The same recipe is what the section/elevation
generator (`archpipe.drawings2d`, not built yet) will use on the real scene: strokes come out in world coordinates,
so depth along the view axis is known per point (cut / projection / beyond weights are classified in Python).

Facts measured with this script (Blender 4.5.14 LTS):
- the new Grease Pencil type is `bpy.data.grease_pencils_v3` (`bpy.data.grease_pencils` is the legacy type and
  cannot be linked to an object);
- the modifier is `obj.modifiers.new(name, "LINEART")`; the evaluated object exposes
  `layer.frames[i].drawing.strokes[j].points[k].position` (world space, offset slightly toward the camera);
- occluded edges are removed (the part of c hidden by a does not appear).
"""
import math

import bpy


def _box(sc, name, c, s):
    me = bpy.data.meshes.new(name)
    x, y, z = c
    a, b, h = s
    v = [(x + sx * a / 2, y + sy * b / 2, z + sz * h / 2) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    me.from_pydata(v, [], f)
    o = bpy.data.objects.new(name, me)
    sc.collection.objects.link(o)
    return o


def bake(sc, thickness=2):
    cam = sc.camera
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
    m.use_intersection = True
    m.use_material = False
    m.use_edge_mark = False
    m.thickness = thickness
    bpy.context.view_layer.update()
    ev = go.evaluated_get(bpy.context.evaluated_depsgraph_get())
    out = []
    for layer in ev.data.layers:
        for fr in layer.frames:
            for s in fr.drawing.strokes:
                out.append([tuple(p.position) for p in s.points])
    return out


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    _box(sc, "a", (0, 0, 1), (4, 4, 2))
    _box(sc, "b", (0, -1.5, 3), (2, 2, 2))
    _box(sc, "c", (0, 6, 1), (2, 2, 2))
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 12
    cam.data.clip_start = 0.01
    cam.data.clip_end = 200
    sc.collection.objects.link(cam)
    cam.location = (0, -30, 2)
    cam.rotation_euler = (math.radians(90), 0, 0)
    sc.camera = cam
    strokes = bake(sc)
    assert strokes, "Line Art produced no strokes"
    ys = sorted({round(p[1], 1) for s in strokes for p in s})
    assert ys[0] < -2.4, "box b (nearest) outline missing"
    far = [s for s in strokes if all(p[1] > 6 for p in s)]
    assert far and all(p[2] < 0.01 for s in far for p in s), "hidden top/sides of c must be removed, base visible"
    print("LINEART-PROBE ok strokes=%d depths=%s" % (len(strokes), ys))


main()
