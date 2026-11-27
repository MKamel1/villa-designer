"""Bake each dress-throw as a cloth sheet dropped onto the real furniture it rests on (lane SOFT, throws).

blender -b -P soft_drape.py -- --scene scene.json [--only dress-throw-x] [--out drapes.json.gz] [--preview out.png]

Why a separate bake: the earlier attempt simulated at render time and the sheet fell through the sofa. The fixes found
by debugging in a small scene are the settings below: world-space metres, colliders as plain evaluated triangles
(no modifiers), `thickness_outer` + `distance_min`, high collision quality and substeps, a short fall onto a settled
sheet, and a post-check that no vertex is inside any host (the bake refuses otherwise). The result is stored with a
signature of the host faces (ids, triangle counts, boxes); `soft_goods.soften_throws` uses it only while the hosts are unchanged.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import sys
import zlib

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from archpipe.blender.soft_goods import THROW_PLY_MM  # noqa: E402

SHEET = (0.50, 1.00)     # a 1300 x 1700 throw folded in four, laid with its long axis along its authored axis: ours (policy)
GRID_M = 0.02
YAW_RETRIES = (0.0, 0.2, -0.2, 0.4, -0.4)
DROP_M = 0.20
RIPPLE_M = 0.03         # initial fold relief of the tossed sheet
CANOPY_M = 0.30          # host surface higher than this above the old throw is overhead, not what it lies on
REMESH_M = 0.004




def make_object(name, tris):
    tris = np.asarray(tris, float)
    me = bpy.data.meshes.new(name)
    me.from_pydata(tris.reshape(-1, 3).tolist(), [], [list(range(3 * i, 3 * i + 3)) for i in range(len(tris))])
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    return ob


def watertight(objs):
    """One closed, consistently wound shell of a product's parts: glTF parts overlap, carry fins and flipped faces, and
    a cloth tunnels through those. A voxel remesh (REMESH_M) fuses them; the drape rests on what a hand would feel."""
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    mod = ob.modifiers.new("remesh", "REMESH")
    mod.mode, mod.voxel_size = "VOXEL", REMESH_M
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    out = bpy.data.objects.new("shell-" + ob.name, me)
    bpy.context.collection.objects.link(out)
    bpy.data.objects.remove(ob)
    return out


def collide(ob):
    ob.modifiers.new("c", "COLLISION")
    ob.collision.thickness_outer = 0.002
    ob.collision.cloth_friction = 50.0


def landing_spot(hv, zref, ang, avoid, cell=0.02, reach=0.55):
    """(x, y, supported fraction): the centre within `reach` of the origin that puts the most of the throw's resting
    footprint (0.4 x 0.8 m along its axis `ang`) over host surface within -0.30..+0.12 m of height `zref`, and as little
    as possible of it over the `avoid` points (the scatter cushions: a throw that buries them hides the pillow)."""
    half = 2.0
    n = int(2 * half / cell)
    near = hv[(hv[:, 2] > zref - 0.30) & (hv[:, 2] < zref + 0.12)]
    grid = np.zeros((n, n), bool)
    ij = np.floor((near[:, :2] + half) / cell).astype(int)
    grid[ij[:, 0].clip(0, n - 1), ij[:, 1].clip(0, n - 1)] = True
    taken = np.zeros((n, n), bool)
    if len(avoid):
        ak = np.floor((avoid[:, :2] + half) / cell).astype(int)
        taken[ak[:, 0].clip(0, n - 1), ak[:, 1].clip(0, n - 1)] = True
    uu, vv = np.meshgrid(np.arange(-0.2, 0.201, cell), np.arange(-0.4, 0.401, cell), indexing="ij")
    c, s = np.cos(ang), np.sin(ang)
    off = np.stack([(c * uu - s * vv).ravel(), (s * uu + c * vv).ravel()], 1)       # footprint cell offsets, world axes
    best = (-9.0, 0.0, 0.0, 0.0)
    for dx in np.arange(-reach, reach + 1e-9, 0.04):
        for dy in np.arange(-reach, reach + 1e-9, 0.04):
            q = np.floor((off + [dx, dy] + half) / cell).astype(int).clip(0, n - 1)
            frac = grid[q[:, 0], q[:, 1]].mean()
            buried = taken[q[:, 0], q[:, 1]].mean()
            score = frac - 1.5 * buried - 0.05 * np.hypot(dx, dy)               # prefer staying where it was authored
            if score > best[0]:
                best = (score, dx, dy, frac)
    if best[3] < 0.6:
        raise SystemExit("no seat under the throw within %.1f m (best %.2f supported)" % (reach, best[3]))
    return best[1], best[2], best[3]


def drop(points, hosts, models, library_root, frames, seed, yaw=0.0, grid=GRID_M, selfcol=True, clearance=True):
    """Fall of a sheet onto the hosts. Returns world verts (m), quads, grid, solid-shell clearance report."""
    from archpipe.blender import villa_scene
    c = points.mean(0)
    _, _, vt = np.linalg.svd((points - c)[:, :2], full_matrices=False)
    ang = float(np.arctan2(vt[0][1], vt[0][0])) - np.pi / 2 + yaw        # grid y -> the throw's long axis (+ a retry turn)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    parts = []
    # simulate near the origin: at x 20, y -27 the sheet fell through every host (see the lesson); results shift back
    shift = np.array([c[0], c[1], points[:, 2].min() - 0.5])
    for name, t in hosts:
        parts.append(make_object("host-" + name, np.asarray(t) - shift))
    for spec in models:
        # world-space copies: an imported model is scaled 0.01 under an anchor, and collision distances are local
        dg0 = bpy.context.evaluated_depsgraph_get()
        for o in [o for o in villa_scene.import_models([spec], library_root)[0]["objects"] if o.type == "MESH"]:
            ev = o.evaluated_get(dg0)
            me = bpy.data.meshes.new_from_object(ev)
            me.transform(ev.matrix_world)
            me.transform(Matrix.Translation(-Vector(shift)))
            flat = bpy.data.objects.new("flat-" + o.name, me)
            bpy.context.collection.objects.link(flat)
            parts.append(flat)
            o.hide_viewport = True
    originals = []                # the hosts as authored/imported, kept to measure the result against (not colliders)
    for f in parts:
        g = bpy.data.objects.new("orig-" + f.name, f.data.copy())
        bpy.context.collection.objects.link(g)
        originals.append(g)
    colliders = [watertight(parts)]
    for ob in colliders:
        collide(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = colliders[0].evaluated_get(dg)
    hv = np.array([(ev.matrix_world @ v.co)[:] for v in ev.data.vertices])
    # The authored throw can sit mostly off its sofa (a lounge throw hangs 0.4 m past the seat front). Drop it where
    # there is a seat to land on: the centre that puts most of its footprint over host surface at the old throw's height.
    zref = points[:, 2].min() - shift[2]
    cushions = np.vstack([np.asarray(t).reshape(-1, 3) - shift for name, t in hosts if name.startswith("dress-cushion")] or [np.zeros((0, 3))])
    sx, sy, supported = landing_spot(hv, zref, ang, cushions)
    top = max(v[2] for v in hv if abs(v[0] - sx) < SHEET[1] / 2 and abs(v[1] - sy) < SHEET[1] / 2
              and v[2] < points[:, 2].max() + CANOPY_M - shift[2])
    # the floor under the hosts: a throw that slides off hangs over it (no floor = it falls out of the world)
    low = min(v.co.z for ob in colliders for v in ob.data.vertices)
    floor = make_object("floor", np.array([[[-3, -3, low], [3, -3, low], [3, 3, low]], [[-3, -3, low], [3, 3, low], [-3, 3, low]]]))
    collide(floor)
    w, l = SHEET
    nx, ny = int(w / grid), int(l / grid)
    bm = bmesh.new()
    # a tossed throw is not a flat sheet: start it gently rumpled so it lands in folds (seeded by the throw, repeatable)
    rnd = np.random.RandomState(seed)
    ph = rnd.uniform(0, 2 * np.pi, 3)
    ripple = lambda x, y: RIPPLE_M * (np.sin(2 * np.pi * x / 0.30 + ph[0]) * np.sin(2 * np.pi * y / 0.45 + ph[1]) + 0.5 * np.sin(2 * np.pi * (x + y) / 0.2 + ph[2])) + rnd.uniform(0, 0.004)
    vs = {(i, j): bm.verts.new((w * (i / nx - 0.5), l * (j / ny - 0.5), ripple(w * (i / nx - 0.5), l * (j / ny - 0.5)))) for i in range(nx + 1) for j in range(ny + 1)}
    for i in range(nx):
        for j in range(ny):
            bm.faces.new((vs[i, j], vs[i + 1, j], vs[i + 1, j + 1], vs[i, j + 1]))
    me = bpy.data.meshes.new("sheet")
    bm.to_mesh(me)
    bm.free()
    sheet = bpy.data.objects.new("sheet", me)
    bpy.context.collection.objects.link(sheet)
    sheet.location = (sx, sy, top + DROP_M + RIPPLE_M)
    sheet.rotation_euler = (0, 0, ang)
    cloth = sheet.modifiers.new("cloth", "CLOTH")
    s = cloth.settings
    s.quality = 20
    s.mass = 0.3
    s.tension_stiffness = s.compression_stiffness = 40.0
    s.shear_stiffness = 20.0
    s.bending_stiffness = 1.2
    s.air_damping = 2.0
    cs = cloth.collision_settings
    cs.use_collision = True
    cs.collision_quality = 8
    cs.distance_min = 0.004
    cs.use_self_collision = selfcol
    cs.self_distance_min = 0.003
    cloth.point_cache.frame_start, cloth.point_cache.frame_end = 1, frames
    scn.frame_start, scn.frame_end = 1, frames
    for f in range(1, frames + 1):
        scn.frame_set(f)
    ev = sheet.evaluated_get(bpy.context.evaluated_depsgraph_get())
    baked_me = bpy.data.meshes.new_from_object(ev)
    baked_me.transform(ev.matrix_world)
    baked = bpy.data.objects.new("baked", baked_me)
    bpy.context.collection.objects.link(baked)
    sheet.hide_viewport = True
    v = np.array([p.co[:] for p in baked_me.vertices]) + shift
    quads = [list(p.vertices) for p in baked_me.polygons]
    # the shell the renderer will draw: the sheet and THROW_PLY_MM above it (solidify offset +1 = along the normal)
    solid = baked.modifiers.new("thickness", "SOLIDIFY")
    solid.thickness, solid.offset = THROW_PLY_MM / 1000.0, 1.0
    clear = villa_scene.cloth_model_clearance(baked, originals) if clearance else dict(intersections=0, inside_vertices=0, uncertain_vertices=0, minimum_surface_distance_m=None)
    return v, quads, (nx, ny), clear, top, supported


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    arg = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d
    scene = json.load(open(arg("--scene")))
    library_root = os.path.expandvars(arg("--library-root") or scene["library_root"])
    from archpipe.blender import soft_goods
    from archpipe.blender.soft_goods import THROW_ID, THROW_REACH_M, throw_hosts, throw_signature
    soft_goods.soften_upholstery(scene)          # hosts exactly as the renderer has them when it places the throws
    soft_goods.soften_cushions(scene)
    out, failed = {}, []
    for m in scene["meshes"]:
        if not THROW_ID.match(m["id"]) or (arg("--only") and arg("--only") != m["id"]):
            continue
        pts = np.array([p for f in m["faces"] for p in f], float)
        procedural, models = throw_hosts(scene, pts.min(0) - THROW_REACH_M, pts.max(0) + THROW_REACH_M)
        for yaw in YAW_RETRIES:        # a sheet that tunnels through a thin fin is dropped again turned a little
            v, quads, grid, clear, top, supported = drop(pts, procedural, models, library_root, int(arg("--frames", 60)), zlib.crc32(m["id"].encode()), yaw,
                                                         float(arg("--grid", GRID_M)), arg("--selfcol", "1") == "1", arg("--clearance", "1") == "1")
            bad = clear["intersections"] or clear["inside_vertices"] or clear["uncertain_vertices"] > 0.001 * clear["evaluated_cloth_vertices"]
            print(m["id"], "yaw", yaw, "hosts", [h for h, _ in procedural], [s["id"] for s in models], "z", round(v[:, 2].min(), 3),
                  round(v[:, 2].max(), 3), "clearance", {k: clear[k] for k in
                  ("intersections", "inside_vertices", "uncertain_vertices", "minimum_surface_distance_m")},
                  "seat under footprint", round(supported, 2), flush=True)
            if not bad and v[:, 2].min() >= pts[:, 2].min() - 0.9:
                break
        else:
            failed.append(m["id"])
            continue
        out[m["id"]] = {"verts_m": np.round(v, 5).tolist(), "quads": quads, "grid": list(grid),
                        "hosts": throw_signature(procedural, models), "clearance": clear["minimum_surface_distance_m"]}
    doc = {"blender": bpy.app.version_string, "ply_mm": THROW_PLY_MM, "sheet_m": SHEET, "throws": out}
    with gzip.open(arg("--out", "soft-throw-drapes.json.gz"), "wt", encoding="utf-8") as f:
        json.dump(doc, f, separators=(",", ":"))
    if failed:
        raise SystemExit("drape refused for " + ", ".join(failed))


if __name__ == "__main__":
    main()
