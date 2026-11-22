"""Blender (headless): build climber panels from Megascans LEAF ATLASES (LDL pass 6) and render the 5 m / 15 m grading views.

    blender -b --python-exit-code 1 -P atlas_panel.py -- --out DIR [--samples 64]

Atlases are not plants: star jasmine / bougainvillea flower are sheets of cut-out leaves / bracts (Opacity map), creeping fig is
a tileable top-down scan of a fig-covered wall. Built here (every texture from the archive's own JPGs via megascans_mat):
  star_jasmine_trellis   1.2 m x 2.1 m timber trellis, ~900 jasmine leaf cut-outs (the 20 atlas leaves, real scan size)
                         scattered along 6 vine stems, tilted off the wall, bottom 0.1 m bare
  creeping_fig_wall      the tileable fig scan on a plain plaster wall, 1.2 m x 2.1 m, scan scale, irregular noise edge
  bougainvillea_dressing the 10 whole bracts of the flower atlas in clumps over the jasmine foliage panel (flowers only; the
                         foliage under them is jasmine, not bougainvillea)
Outputs <id>_d{5,15}_az{0,45}.png, <id>_wide_d{5,15}.png (3 panels side by side), <id>_close.png and <id>.stats.json.
Cut-out rectangles come from tools/atlas_rects.py (rects.json next to --out or --rects)."""
import json, math, os, random, sys, time
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from megascans_mat import maps_of, tex, red, build_material, reset_scene  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
A = dict(zip(argv[::2], argv[1::2]))
OUT = A["--out"]; os.makedirs(OUT, exist_ok=True)
SAMPLES = int(A.get("--samples", 64))
FAB = os.path.expanduser("~/archpipe/shared/assets/user/landscape/fab/unzipped/")
RECTS = json.load(open(A.get("--rects", OUT + "/rects.json")))
W, H = 1.2, 2.1          # trellis panel, m
PX = 4096


def load(d):
    meta = json.load(open([os.path.join(FAB + d, f) for f in os.listdir(FAB + d) if f.endswith(".json")][0]))
    return maps_of(FAB + d)[0], meta


def cutouts(mat, rects, scan, name):
    """one quad mesh per rect (origin at the bottom centre = the petiole end), UV = that rect of the atlas, real size."""
    k = scan / PX; out = []
    for i, (x0, y0, x1, y1, *_r) in enumerate(rects):
        w, h = (x1 - x0) * k, (y1 - y0) * k
        me = bpy.data.meshes.new(f"{name}{i}")
        me.from_pydata([(-w / 2, 0, 0), (w / 2, 0, 0), (w / 2, h, 0), (-w / 2, h, 0)], [], [(0, 1, 2, 3)])
        uv = me.uv_layers.new(name="UV")
        for lp, (u, v) in zip(me.loops, [(x0, y1), (x1, y1), (x1, y0), (x0, y0)]):
            uv.data[lp.index].uv = (u / PX, 1 - v / PX)
        me.materials.append(mat)
        out.append((me, w, h))
    return out


def plaster(sc, width=4.0):
    m = bpy.data.materials.new("plaster"); m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.78, 0.73, 0.64, 1)
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
    bpy.ops.mesh.primitive_cube_add(size=1); w = bpy.context.object
    w.scale = (width, 0.2, 3.2); w.location = (0, 0.1, 1.6); w.data.materials.append(m)


def timber(mat_name="timber", col=(0.16, 0.10, 0.06, 1)):
    m = bpy.data.materials.new(mat_name); m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs[0].default_value = col
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.7
    return m


def trellis(cx):
    m = timber()
    for i in range(7):            # 25 mm verticals every 0.2 m
        x = cx - W / 2 + i * W / 6
        bpy.ops.mesh.primitive_cube_add(size=1); o = bpy.context.object; o.scale = (0.025, 0.02, H); o.location = (x, -0.01, H / 2); o.data.materials.append(m)
    for j in range(8):            # horizontals every 0.3 m
        bpy.ops.mesh.primitive_cube_add(size=1); o = bpy.context.object; o.scale = (W, 0.02, 0.025); o.location = (cx, -0.03, 0.05 + j * 0.3); o.data.materials.append(m)


def stems(cx, rnd, xs):
    """dark vine stems, one per x (relative to cx), wandering up the trellis"""
    m = timber("stem", (0.12, 0.09, 0.05, 1))
    for x0 in xs:
        pts = []; x = x0
        for k in range(15):
            x += rnd.uniform(-0.03, 0.03); pts.append((cx + max(-W / 2, min(W / 2, x)), -0.045 - 0.02 * math.sin(k), 0.05 + k * H / 14.5))
        cu = bpy.data.curves.new("s", "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = 0.004
        sp = cu.splines.new("POLY"); sp.points.add(len(pts) - 1)
        for p, c in zip(sp.points, pts):
            p.co = (*c, 1)
        o = bpy.data.objects.new("s", cu); o.data.materials.append(m); bpy.context.scene.collection.objects.link(o)


def scatter(cx, leaves, n, rnd, xs, y_range, spin, tilt, clump=None, zr=(0.1, H - 0.05)):
    """n instances of the cut-outs, along vine stems xs (sigma 0.13 m, 20 % uniform) or around clump centres (x, z, radius).
    spin(rnd) = in-plane turn about the wall normal; tilt = lean off the wall in degrees. Returns leaf area, m^2."""
    from mathutils import Matrix
    area = 0.0
    for _ in range(n):
        if clump:
            ccx, ccz, rad = rnd.choice(clump); x = ccx + rnd.gauss(0, rad); z = ccz + rnd.gauss(0, rad)
        else:
            x = (rnd.choice(xs) + rnd.gauss(0, 0.13)) if rnd.random() < 0.8 else rnd.uniform(-W / 2, W / 2)
            z = rnd.uniform(*zr)
        x = max(-W / 2 - 0.02, min(W / 2 + 0.02, x)); z = max(zr[0], min(zr[1], z))
        me, w, h = rnd.choice(leaves)
        o = bpy.data.objects.new("l", me)
        o.location = (cx + x, rnd.uniform(*y_range), z)
        # stand the quad up facing -Y, lean it off the wall, then spin it about the wall normal
        o.rotation_euler = (Matrix.Rotation(spin(rnd), 4, "Y") @ Matrix.Rotation(math.radians(90 - rnd.uniform(*tilt)), 4, "X")).to_euler()
        s = rnd.uniform(0.9, 1.1); o.scale = (s, s, s)
        bpy.context.scene.collection.objects.link(o); area += w * h * s * s * 0.65
    return area


def fig_material(maps, meta):
    """creeping-fig wall scan on a W x H plane with an irregular noise edge (transparent -> bare wall)."""
    mat = bpy.data.materials.new("fig")
    build_material(mat, maps, meta, uvscale=1.0)
    nt = mat.node_tree
    mp = next(n for n in nt.nodes if n.type == "MAPPING"); mp.inputs["Scale"].default_value = (W / 0.85, H / 0.85, 1)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"); sh = out.inputs["Surface"].links[0].from_socket
    g = nt.nodes.new("ShaderNodeTexCoord"); sx = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(g.outputs["Generated"], sx.inputs[0])

    def m(op, a, b, clamp=False):
        n = nt.nodes.new("ShaderNodeMath"); n.operation = op; n.use_clamp = clamp
        for i, v in enumerate((a, b)):
            if isinstance(v, (int, float)): n.inputs[i].default_value = v
            else: nt.links.new(v, n.inputs[i])
        return n.outputs[0]
    dx = m("MULTIPLY", m("MINIMUM", sx.outputs["X"], m("SUBTRACT", 1.0, sx.outputs["X"])), W)
    dy = m("MULTIPLY", m("MINIMUM", sx.outputs["Y"], m("SUBTRACT", 1.0, sx.outputs["Y"])), H)
    d = m("MINIMUM", dx, dy)
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 7.0; nz.inputs["Detail"].default_value = 6
    mp2 = nt.nodes.new("ShaderNodeMapping"); mp2.inputs["Scale"].default_value = (W, H, 1)
    nt.links.new(g.outputs["Generated"], mp2.inputs[0]); nt.links.new(mp2.outputs[0], nz.inputs["Vector"])
    mask = m("DIVIDE", m("SUBTRACT", d, m("ADD", 0.03, m("MULTIPLY", nz.outputs["Fac"], 0.22))), 0.05, True)
    tp = nt.nodes.new("ShaderNodeBsdfTransparent"); mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(mask, mx.inputs[0]); nt.links.new(tp.outputs[0], mx.inputs[1]); nt.links.new(sh, mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    return mat


def views(sc, cam, sid, cx, zc):
    for d in (5, 15):
        for az in (0, 45):
            r = math.radians(az)
            cam.location = (cx + d * math.sin(r), -d * math.cos(r), 1.6)
            cam.rotation_euler = (Vector((cx, 0, zc)) - cam.location).to_track_quat("-Z", "Y").to_euler()
            sc.render.filepath = f"{OUT}/{sid}_d{d}_az{az}.png"; bpy.ops.render.render(write_still=True)
    for d in (5, 15):
        cam.location = (cx, -d, 1.6); cam.rotation_euler = (Vector((cx, 0, zc)) - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = f"{OUT}/{sid}_wide_d{d}.png"; bpy.ops.render.render(write_still=True)
    cam.location = (cx, -1.5, 1.4); cam.rotation_euler = (Vector((cx, 0, 1.3)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = f"{OUT}/{sid}_close.png"; bpy.ops.render.render(write_still=True)


def build(sid):
    t0 = time.time(); sc, cam = reset_scene(500, SAMPLES)
    sc.cycles.transparent_max_bounces = 32
    rnd = random.Random({"star_jasmine_trellis": 3, "creeping_fig_wall": 4, "bougainvillea_dressing": 5}[sid])
    panels = [-W - 0.1, 0.0, W + 0.1]    # the middle one is the single-panel subject; the outer two give the "wide" views context
    plaster(sc, width=3 * W + 1.0)
    st = {"id": sid, "panel_m": [W, H]}
    jm, jmeta = load("star_jasmine_pjycl2_4k"); jmat = bpy.data.materials.new("jasmine"); build_material(jmat, jm, jmeta)
    jl = cutouts(jmat, [x for x in RECTS["star_jasmine"]["rects"] if x[5] >= 1.0], RECTS["star_jasmine"]["scan_m"], "jl")
    st["leaf_cutouts"] = len(jl)
    for pi, cx in enumerate(panels):
        r2 = random.Random(100 * pi + 7)
        if sid == "creeping_fig_wall":
            fm, fmeta = load("creeping_fig_ompjv0_4k"); mat = fig_material(fm, fmeta)
            bpy.ops.mesh.primitive_plane_add(size=1); o = bpy.context.object; o.scale = (W, H, 1); o.rotation_euler = (math.radians(90), 0, 0)
            o.location = (cx, -0.01, H / 2); o.data.materials.append(mat)
        else:
            trellis(cx)
            xs = [-0.5, -0.3, -0.1, 0.1, 0.3, 0.5]
            stems(cx, r2, xs)
            a = scatter(cx, jl, 900, r2, xs, (-0.15, -0.04), lambda r: r.gauss(0, 1.0) if r.random() < 0.5 else r.gauss(math.pi, 1.0),
                        (5, 55), zr=(0.1, H - 0.05))
            st["leaf_area_m2_per_panel"] = round(a, 2)
            if sid == "bougainvillea_dressing":
                bl = [x for x in RECTS["bougainvillea_flower"]["rects"]
                      if x[5] < 0.6 and (x[2] - x[0]) * 0.25 / PX >= 0.02 and 0.03 <= (x[3] - x[1]) * 0.25 / PX < 0.06]
                bm, bmeta = load("bougainvillea_flower_phfeffeh2_4k"); bmat = bpy.data.materials.new("bougainvillea"); build_material(bmat, bm, bmeta)
                bq = cutouts(bmat, bl, RECTS["bougainvillea_flower"]["scan_m"], "bq")
                st["bract_cutouts"] = len(bq)
                cl = [(r2.uniform(-0.45, 0.45), r2.uniform(0.7, 2.0), r2.uniform(0.07, 0.14)) for _ in range(16)]
                ba = scatter(cx, bq, 1700, r2, xs, (-0.26, -0.17), lambda r: r.uniform(-math.pi, math.pi), (10, 60), clump=cl, zr=(0.3, H - 0.05))
                st["bract_area_m2_per_panel"] = round(ba, 2)
    if sid == "creeping_fig_wall":
        st["scan_m"] = 0.85
    views(sc, cam, sid, 0.0, 1.05)
    st["seconds"] = round(time.time() - t0, 1); st["sampling"] = SAMPLES
    json.dump(st, open(f"{OUT}/{sid}.stats.json", "w"), indent=1)


for sid in ("star_jasmine_trellis", "creeping_fig_wall", "bougainvillea_dressing"):
    try:
        build(sid); print("OK", sid, flush=True)
    except Exception:
        import traceback; traceback.print_exc(); print("FAIL", sid, flush=True)
