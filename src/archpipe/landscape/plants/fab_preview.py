"""Blender (headless): import Megascans FBX plants / wire Megascans surfaces from the archive's own JPG maps and render
the 5 m / 15 m grading sheets (LDL pass 5).

    blender -b --python-exit-code 1 -P fab_preview.py -- --spec spec.json --out DIR

spec.json: [{"id": "fab_<archive>", "kind": "plant"|"lawn", "dir": "/abs/archive/dir"}]  (hero variation = largest bbox)
plant: writes <id>_s_d{5,15}_az{0,90,180,270}.png (single plant) and <id>_dr_d{5,15}_az{0,90}.png (3 m x 3 m instanced drift
       of all variations, LOD0), plus <id>.stats.json (tris, bbox, texture size, seconds).
lawn:  <id>_su_* (continuous tiled surface 3 m x 3 m) and <id>_dr_* (instanced displaced scan patches over 3 m x 3 m).
Textures are wired ONLY from the archive's JPGs, by the map types the archive's JSON lists: BaseColor -> colour,
Roughness -> roughness (else 1-Gloss), Normal -> normal map, Opacity -> cut-out, Translucency x the JSON's
"Translucency Tint" -> backlight (translucent BSDF, 30 %), Displacement -> displace (lawn only). AO/Cavity/Bump/Specular are not wired
(Cycles computes occlusion; Normal supersedes Bump). The FBX's own texture paths (a Windows .exr atlas) are discarded.
"""
import glob, json, math, os, random, sys, time
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
A = dict(zip(argv[::2], argv[1::2]))
OUT = A["--out"]
os.makedirs(OUT, exist_ok=True)
RES = 400
SAMPLES = int(A.get("--samples", 64))


def reset():
    return reset_scene(RES, SAMPLES)


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from megascans_mat import maps_of, tex, red, build_material, reset_scene  # noqa: E402


def bbox(o):
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return Vector(map(min, *[tuple(v) for v in bb])), Vector(map(max, *[tuple(v) for v in bb]))


def tris(o):
    o.data.calc_loop_triangles(); return len(o.data.loop_triangles)


def cams(sc, cam, tag, targets, dists, azs, cx=0.0, cy=0.0, tz=0.4):
    for d in dists:
        for az in azs:
            r = math.radians(az)
            cam.location = (cx + d * math.sin(r), cy - d * math.cos(r), 1.6)
            cam.rotation_euler = (Vector((cx, cy, tz)) - cam.location).to_track_quat("-Z", "Y").to_euler()
            sc.render.filepath = f"{OUT}/{tag}_d{d}_az{az}.png"
            bpy.ops.render.render(write_still=True)


def close(sc, cam, tag, dist, eye, tz):
    """one near view (not part of the 5 m / 15 m rubric): is the scan itself good, or only small?"""
    cam.location = (0, -dist, eye)
    cam.rotation_euler = (Vector((0, 0, tz)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = f"{OUT}/{tag}.png"
    bpy.ops.render.render(write_still=True)


def import_variants(d, meta, maps):
    """one object per variation (LOD0), each moved to the origin, standing on z=0, materials rebuilt from the maps"""
    vs = []
    for f in sorted(glob.glob(d + "/*_LOD0.fbx")):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=f)
        new = [o for o in bpy.data.objects if o not in before]
        ms = [o for o in new if o.type == "MESH"]
        assert len(ms) == 1, (f, len(ms))
        o = ms[0]
        mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
        for e in new:
            if e is not o:
                bpy.data.objects.remove(e)
        lo, hi = bbox(o)
        o.location -= Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z)); bpy.context.view_layer.update()
        lo, hi = bbox(o)
        for s in o.material_slots:
            build_material(s.material, maps, meta)
        o.hide_render = True
        vs.append({"name": os.path.basename(f), "obj": o, "tris": tris(o), "size": [round(hi[i] - lo[i], 3) for i in range(3)]})
    return vs


def render_plant(spec):
    d = spec["dir"]; sid = spec["id"]; t0 = time.time()
    meta = json.load(open(glob.glob(d + "/*.json")[0]))
    maps, stem = maps_of(d)
    sc, cam = reset()
    vs = import_variants(d, meta, maps)
    hero = max(vs, key=lambda v: v["size"][0] * v["size"][1] * v["size"][2])
    h = hero["obj"]; h.hide_render = False
    cams(sc, cam, sid + "_s", None, (5, 15), (0, 90, 180, 270), 0, 0, max(0.3, min(hero["size"][2] / 2, 3.0)))
    close(sc, cam, sid + "_s_close", max(1.0, 1.8 * max(hero["size"])), min(1.6, 0.6 * hero["size"][2] + 0.3), hero["size"][2] / 2)
    t1 = time.time()
    h.hide_render = True
    # drift: all variations, 3 m x 3 m, coverage ~1.3 x
    rnd = random.Random(11)
    foot = sum(v["size"][0] * v["size"][1] for v in vs) / len(vs)
    n = max(3, min(150, int(round(1.3 * 9.0 / max(foot, 1e-3)))))
    for i in range(n):
        src = rnd.choice(vs)["obj"]
        inst = bpy.data.objects.new(f"i{i}", src.data)
        inst.location = (rnd.uniform(-1.5, 1.5), rnd.uniform(-1.5, 1.5), src.location.z)
        inst.rotation_euler = (src.rotation_euler.x, src.rotation_euler.y, rnd.uniform(0, 6.283))
        s = rnd.uniform(0.85, 1.15); inst.scale = (s * src.scale.x, s * src.scale.y, s * src.scale.z)
        inst.hide_render = False
        sc.collection.objects.link(inst)
    cams(sc, cam, sid + "_dr", None, (5, 15), (0, 90), 0, 0, 0.3)
    close(sc, cam, sid + "_dr_close", 1.5, 1.0, 0.1)
    t2 = time.time()
    st = {"id": sid, "texture_stem": stem, "maps_in_archive": sorted(maps), "maps_wired": [k for k in ("BaseColor", "Roughness", "Gloss", "Normal", "Opacity", "Translucency", "Displacement") if k in maps and not (k == "Gloss" and "Roughness" in maps)], "texture_res": os.path.basename(maps["BaseColor"]).split("_")[-2],
          "variations": {v["name"]: {"tris": v["tris"], "size_m": v["size"]} for v in vs},
          "hero": hero["name"], "hero_tris": hero["tris"], "hero_size_m": hero["size"],
          "mean_tris": round(sum(v["tris"] for v in vs) / len(vs)), "drift_instances": n,
          "single_sheet_s": round(t1 - t0, 1), "drift_sheet_s": round(t2 - t1, 1), "sampling": SAMPLES}
    json.dump(st, open(f"{OUT}/{sid}.stats.json", "w"), indent=1)


def scan_m(meta):
    s = next(m["value"] for m in meta["meta"] if m["key"] == "scanArea")
    return float(s.split("x")[0]), next(float(m["value"].split()[0]) for m in meta["meta"] if m["key"] == "height")


def render_lawn(spec):
    d = spec["dir"]; sid = spec["id"]; t0 = time.time()
    meta = json.load(open(glob.glob(d + "/*.json")[0]))
    maps, stem = maps_of(d)
    scan, height = scan_m(meta)
    # (1) continuous surface: a 3 m x 3 m plane, UV tiled so one scan = one tile
    sc, cam = reset()
    bpy.ops.mesh.primitive_plane_add(size=3.0); pl = bpy.context.object
    mat = bpy.data.materials.new("lawn"); pl.data.materials.append(mat)
    build_material(mat, maps, meta, uvscale=3.0 / scan)
    nt = mat.node_tree; pb = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    if "Displacement" in maps:      # bump only (true displacement of a 3 m plane at blade size is not affordable)
        di = tex(nt, maps["Displacement"], True, "Displacement"); mp = next(n for n in nt.nodes if n.type == "MAPPING")
        nt.links.new(mp.outputs["Vector"], di.inputs["Vector"])
        bm = nt.nodes.new("ShaderNodeBump"); bm.inputs["Distance"].default_value = height; bm.inputs["Strength"].default_value = 1.0
        nt.links.new(red(nt, di), bm.inputs["Height"])
        nn = next((l.from_node for l in pb.inputs["Normal"].links), None)
        if nn: nt.links.new(nn.outputs["Normal"], bm.inputs["Normal"])
        nt.links.new(bm.outputs["Normal"], pb.inputs["Normal"])
    cams(sc, cam, sid + "_su", None, (5, 15), (0, 90), 0, 0, 0.0)
    sc.render.filepath = f"{OUT}/{sid}_su_close.png"       # 1.2 m camera, 45 deg down: does a blade pattern exist?
    cam.location = (0, -1.2, 1.0); cam.rotation_euler = (Vector((0, 0, 0)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.render.render(write_still=True)
    t1 = time.time()
    # (2) instanced drift: heightfield patches (real displacement) of one scan each, random turn and jitter, shared mesh data
    sc, cam = reset()
    cells = int(min(scan / 0.0015, 512))
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=cells, y_subdivisions=cells, size=scan); g = bpy.context.object
    mat = bpy.data.materials.new("lawn"); g.data.materials.append(mat)
    build_material(mat, maps, meta)
    tx = bpy.data.textures.new("disp", "IMAGE"); tx.image = bpy.data.images.load(maps["Displacement"]); tx.image.colorspace_settings.name = "Non-Color"
    import numpy as np
    px = np.empty(len(tx.image.pixels), dtype=np.float32); tx.image.pixels.foreach_get(px)
    px = px.reshape(-1, 4); px[:, 1] = px[:, 0]; px[:, 2] = px[:, 0]; tx.image.pixels.foreach_set(px.ravel())   # red -> grey, in memory only
    md = g.modifiers.new("d", "DISPLACE"); md.texture = tx; md.texture_coords = "UV"; md.mid_level = 0.5; md.strength = height
    bpy.ops.object.modifier_apply(modifier="d")
    g.hide_render = True
    rnd = random.Random(5)
    n = min(int(math.ceil(3.5 * 9.0 / (scan * scan))), 400)   # dense: overlapping patches, no bare ground
    for i in range(n):
        inst = bpy.data.objects.new(f"p{i}", g.data)
        inst.location = (rnd.uniform(-1.5, 1.5), rnd.uniform(-1.5, 1.5), 0.0005 * i)
        inst.rotation_euler = (0, 0, rnd.uniform(0, 6.283)); sc.collection.objects.link(inst)
    cams(sc, cam, sid + "_dr", None, (5, 15), (0, 90), 0, 0, 0.0)
    sc.render.filepath = f"{OUT}/{sid}_dr_close.png"
    cam.location = (0, -1.2, 1.0); cam.rotation_euler = (Vector((0, 0, 0)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.render.render(write_still=True)
    t2 = time.time()
    json.dump({"id": sid, "kind": "lawn", "maps_in_archive": sorted(maps), "maps_wired": [k for k in ("BaseColor", "Roughness", "Gloss", "Normal", "Opacity", "Translucency", "Displacement") if k in maps and not (k == "Gloss" and "Roughness" in maps)], "scan_m": scan, "height_m": height, "patch_cells": cells,
               "patch_tris": cells * cells * 2, "drift_instances": n, "surface_sheet_s": round(t1 - t0, 1), "drift_sheet_s": round(t2 - t1, 1)},
              open(f"{OUT}/{sid}.stats.json", "w"), indent=1)


for spec in json.load(open(A["--spec"])):
    try:
        (render_lawn if spec["kind"] == "lawn" else render_plant)(spec)
        print("OK", spec["id"], flush=True)
    except Exception as e:
        import traceback; traceback.print_exc(); print("FAIL", spec["id"], e, flush=True)
