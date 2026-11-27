"""Bake soft-cushion shapes ONCE with Blender's cloth solver (pressure-inflated), for reuse by soft_goods.

Run inside Blender:  blender -b -P soft_bake.py -- --out knowledge/soft-cushion-bakes.json.gz

Why a solver and not a formula: a real scatter cushion is two panels sewn at the rim and stuffed. Inflating a
two-panel cloth reproduces what a hand-written profile cannot: puckered seam, corner "ears", a crown that is
not symmetric, and a base that flattens where it lies. The old formula (interior/soft_dressing.pillow) gave a
board with a knife-edge rim; see docs/lessons/SOFT.md.

Each bake is keyed by "<w_mm>x<h_mm>x<thick_mm>:<seed>" and stores quads in the cushion's local frame:
x = width, y = height (long axis), z = thickness from the lying base (z = 0 at the lowest point). Millimetres.
The solver is Blender-version bound; the bake records the version, so a rebake is a deliberate act.
"""
from __future__ import annotations

import gzip
import json
import math
import sys

import bmesh
import bpy
from mathutils import Vector

# (w_mm, h_mm, thick_mm) formats in the villa: SANELA 500x500, LAGERPOPPEL 580x400 (as it lies: 580 wide, 400 tall),
# and the bed's sleeping pillow (not scheduled; the library bed model carries its own, see soft_goods.BED_PILLOW).
FORMATS = [(500, 500, 150), (580, 400, 140), (450, 450, 140), (600, 400, 130)]
SEEDS = (1, 2, 3)
N = 34                      # quads per panel side; cloth cost is trivial at this size


def _panel_mesh(w, h):
    bm = bmesh.new()
    xs = [w / 2 * (2 * i / N - 1) for i in range(N + 1)]
    ys = [h / 2 * (2 * j / N - 1) for j in range(N + 1)]
    top, bot = {}, {}
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            rim = i in (0, N) or j in (0, N)
            top[i, j] = bm.verts.new((x, y, 0.002))
            bot[i, j] = top[i, j] if rim else bm.verts.new((x, y, -0.002))
    for i in range(N):
        for j in range(N):
            bm.faces.new((top[i, j], top[i + 1, j], top[i + 1, j + 1], top[i, j + 1]))
            bm.faces.new((bot[i, j], bot[i, j + 1], bot[i + 1, j + 1], bot[i + 1, j]))
    bm.normal_update()
    mesh = bpy.data.meshes.new("pillow")
    bm.to_mesh(mesh)
    bm.free()
    return mesh


def bake_one(w_mm, h_mm, thick_mm, seed):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    w, h = w_mm / 1000.0, h_mm / 1000.0
    obj = bpy.data.objects.new("pillow", _panel_mesh(w, h))
    bpy.context.collection.objects.link(obj)
    obj.location.z = 0.0
    # a floor the cushion settles on: the base flattens where it lies
    floor = bpy.data.objects.new("floor", bpy.data.meshes.new("floor"))
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=2, y_segments=2, size=2.0)
    bm.to_mesh(floor.data)
    bm.free()
    bpy.context.collection.objects.link(floor)
    floor.location.z = -0.0005
    floor.modifiers.new("col", "COLLISION")
    floor.collision.thickness_outer = 0.001
    cloth = obj.modifiers.new("cloth", "CLOTH")
    s = cloth.settings
    s.quality = 12
    s.mass = 0.25
    s.tension_stiffness = 28 + 4 * seed
    s.compression_stiffness = 28
    s.shear_stiffness = 14
    s.bending_stiffness = 0.35 + 0.25 * seed       # seeds differ in how plump / how limp the fill sits
    s.use_pressure = True
    s.uniform_pressure_force = 20.0 + 3.0 * seed
    s.pressure_factor = 1.0
    s.use_pressure_volume = False
    cloth.collision_settings.use_collision = True
    cloth.collision_settings.use_self_collision = False
    cloth.collision_settings.distance_min = 0.002
    cloth.point_cache.frame_start, cloth.point_cache.frame_end = 1, 90
    scene = bpy.context.scene
    scene.use_gravity = True
    scene.frame_start, scene.frame_end = 1, 90
    for f in range(1, 91):
        scene.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    verts = [(v.co.x * 1000, v.co.y * 1000, v.co.z * 1000) for v in me.vertices]
    quads = [list(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
    zmin = min(v[2] for v in verts)
    verts = [(round(x, 2), round(y, 2), round(z - zmin, 2)) for x, y, z in verts]
    return {"verts_mm": verts, "quads": quads,
            "height_mm": round(max(v[2] for v in verts), 1)}


THROW = (410, 570)          # MYRULL 1300 x 1700 folded in three, as soft_dressing.folded_throw draws it


def bake_throw(w_mm, l_mm, seed):
    """A folded throw dropped loosely over a rolled lump: one end flat, the rest folding over it. Open sheet; the
    shell (thickness, rim) is added by soft_goods. z is the sheet's height above the lying base, mm."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    w, l = w_mm / 1000.0, l_mm / 1000.0
    nx, ny = 34, 46
    bm = bmesh.new()
    vs = {}
    for i in range(nx + 1):
        for j in range(ny + 1):
            vs[i, j] = bm.verts.new((w * (i / nx - 0.5), l * (j / ny - 0.5), 0.06))
    for i in range(nx):
        for j in range(ny):
            bm.faces.new((vs[i, j], vs[i + 1, j], vs[i + 1, j + 1], vs[i, j + 1]))
    mesh = bpy.data.meshes.new("throw")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("throw", mesh)
    bpy.context.collection.objects.link(obj)
    floor = bpy.data.objects.new("floor", bpy.data.meshes.new("floor"))
    bmf = bmesh.new()
    bmesh.ops.create_grid(bmf, x_segments=2, y_segments=2, size=2.0)
    bmf.to_mesh(floor.data)
    bmf.free()
    bpy.context.collection.objects.link(floor)
    floor.modifiers.new("c", "COLLISION")
    lump = bpy.data.objects.new("lump", bpy.data.meshes.new("lump"))
    bml = bmesh.new()
    bmesh.ops.create_uvsphere(bml, u_segments=24, v_segments=16, radius=1.0)
    bml.to_mesh(lump.data)
    bml.free()
    bpy.context.collection.objects.link(lump)
    lump.scale = (0.16, 0.04 + 0.006 * seed, 0.024 + 0.007 * seed)
    lump.location = (0.02 * (seed - 2), 0.07 * (seed - 2), 0.016)
    lump.rotation_euler = (0, 0, 0.35 * seed)
    lump.modifiers.new("c", "COLLISION")
    cloth = obj.modifiers.new("cloth", "CLOTH")
    s = cloth.settings
    s.quality = 12
    s.mass = 0.35
    s.tension_stiffness = 12
    s.compression_stiffness = 12
    s.shear_stiffness = 6
    s.bending_stiffness = 3.0
    cloth.collision_settings.use_collision = True
    cloth.collision_settings.use_self_collision = True
    cloth.collision_settings.distance_min = 0.004
    cloth.collision_settings.self_distance_min = 0.004
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, 110
    cloth.point_cache.frame_start, cloth.point_cache.frame_end = 1, 110
    for f in range(1, 111):
        scene.frame_set(f)
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    verts = [(v.co.x * 1000, v.co.y * 1000, v.co.z * 1000) for v in me.vertices]
    quads = [list(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
    zmin = min(v[2] for v in verts)
    verts = [(round(x, 2), round(y, 2), round(z - zmin, 2)) for x, y, z in verts]
    return {"verts_mm": verts, "quads": quads, "grid": [nx, ny], "height_mm": round(max(v[2] for v in verts), 1)}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = argv[argv.index("--out") + 1] if "--out" in argv else "soft-cushion-bakes.json.gz"
    only = argv[argv.index("--only") + 1] if "--only" in argv else None
    throws_only = "--throws-only" in argv
    bakes = {}
    for w, h, t in ([] if throws_only else FORMATS):
        for seed in SEEDS:
            key = "%dx%dx%d:%d" % (w, h, t, seed)
            if only and only != key:
                continue
            bakes[key] = bake_one(w, h, t, seed)
            print(key, "crown mm", bakes[key]["height_mm"], "verts", len(bakes[key]["verts_mm"]), flush=True)
    throws = {}
    if not only or throws_only:
        for seed in SEEDS:
            throws["%dx%d:%d" % (THROW[0], THROW[1], seed)] = bake_throw(THROW[0], THROW[1], seed)
            print("throw", seed, "height mm", throws["%dx%d:%d" % (THROW[0], THROW[1], seed)]["height_mm"], flush=True)
    doc = {"throws": throws, "blender": bpy.app.version_string, "solver": "cloth pressure inflation, two panels sewn at the rim",
           "frame": "x width, y height, z thickness above the lying base, mm", "bakes": bakes}
    if throws_only:                       # keep the cushion bakes already in the file
        with gzip.open(out, "rt", encoding="utf-8") as f:
            old = json.load(f)
        old["throws"] = throws
        doc = old
    with gzip.open(out, "wt", encoding="utf-8") as f:
        json.dump(doc, f, separators=(",", ":"))


if __name__ == "__main__":
    main()
