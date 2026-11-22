"""Procedural shrub PROTOTYPE (feasibility only): Pittosporum tobira from sourced habit + CC0 textures.

    blender -b --python-exit-code 1 -P proto_shrub.py -- --out DIR --tex DIR

Habit inputs (sourced, see knowledge/landscape/plants/species/pittosporum_tobira.json):
  height 2.4-4.0 m, spread 1.2-2.4 m, "dense, compact ... rounded", sympodial (NC State Plant Toolbox);
  leaves obovate, entire, leathery, glossy dark above, up to 10 cm (Wikipedia, Pittosporum tobira).
  Reference photo: Wikimedia Commons "Pittosporum tobira - Flickr - peganum.jpg" (CC BY-SA 2.0):
  leaves in whorls at branch tips, flower clusters terminal.
Textures: ambientCG Leaf001 (CC0) colour map for the leaf surface only (its toothed outline is NOT used:
the outline is our obovate entire mesh), Poly Haven bark_brown_01 (CC0) for twigs.
Writes DIR/pittosporum_proto.glb. Deterministic (seeded).
"""
import math
import os
import sys

import bpy
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
args = dict(zip(argv[::2], argv[1::2]))
OUT, TEX = args["--out"], args["--tex"]
rng = np.random.default_rng(7)

H, SPREAD = 3.0, 2.0          # mid of sourced ranges
RX, RZ = SPREAD / 2, H / 2 * 0.95
LEAF_L, LEAF_W = 0.085, 0.036  # obovate, up to 10 cm


def leaf_template(nu=6, nv=3):
    """Obovate leaf, widest beyond the middle, midrib fold + length arch (leathery, edges curl under)."""
    v, uv, f = [], [], []
    for i in range(nu + 1):
        t = i / nu
        w = LEAF_W / 2 * (math.sin(math.pi * t ** 0.75) ** 0.9) * (0.55 + 0.45 * t)  # obovate: wider distally
        for j in range(nv + 1):
            s = j / nv * 2 - 1
            x = s * w
            y = t * LEAF_L
            z = 0.014 * abs(s) ** 1.5 * (w / (LEAF_W / 2)) - 0.020 * t * t   # edges curl, tip droops
            v.append((x, y, z))
            uv.append((0.30 + 0.13 * (s * 0.5 + 0.5), 0.36 + 0.22 * t))
    for i in range(nu):
        for j in range(nv):
            a = i * (nv + 1) + j
            f.append((a, a + 1, a + nv + 2, a + nv + 1))
    return np.array(v), np.array(uv), f


LV, LUV, LF = leaf_template()


def rot_to(axis_from, axis_to):
    a = axis_from / np.linalg.norm(axis_from); b = axis_to / np.linalg.norm(axis_to)
    c = np.cross(a, b); d = float(np.dot(a, b))
    if np.linalg.norm(c) < 1e-9:
        return np.eye(3) if d > 0 else -np.eye(3)
    k = np.array([[0, -c[2], c[1]], [c[2], 0, -c[0]], [-c[1], c[0], 0]])
    return np.eye(3) + k + k @ k / (1 + d)


all_v, all_uv, all_f = [], [], []


def add_leaf(base, direction, roll, scale):
    """Leaf whose +Y (blade axis) points along direction, upper surface (+Z) toward the sky."""
    R = rot_to(np.array([0, 1.0, 0]), direction)
    up = R @ np.array([0, 0, 1.0])
    sky = np.array([0, 0, 1.0])
    # roll about the blade axis so the upper surface faces as skyward as the direction allows
    ax = direction / np.linalg.norm(direction)
    p_up = up - ax * np.dot(up, ax); p_sky = sky - ax * np.dot(sky, ax)
    if np.linalg.norm(p_sky) > 1e-6:
        ang = math.atan2(np.dot(np.cross(p_up, p_sky), ax), np.dot(p_up, p_sky)) * 0.6 + roll
    else:
        ang = roll
    K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
    Rr = np.eye(3) + math.sin(ang) * K + (1 - math.cos(ang)) * K @ K
    verts = (LV * scale) @ (Rr @ R).T + base
    n = sum(len(x) for x in all_v)
    all_v.append(verts); all_uv.append(LUV)
    all_f.extend([tuple(i + n for i in f) for f in LF])


twigs = []  # list of polylines


def ellipsoid_point(r_lo, r_hi):
    while True:
        p = rng.normal(size=3); p /= np.linalg.norm(p)
        if p[2] > -0.92:
            break
    r = rng.uniform(r_lo, r_hi) ** (1 / 3)
    return np.array([p[0] * RX * r, p[1] * RX * r, RZ * 1.0 + 0.1 + p[2] * RZ * r])


# main stems (sympodial, 3 leaders) then tips: every tip connected to a stem through a mid node
stems = []
for k in range(3):
    a = rng.uniform(0, 2 * math.pi); off = np.array([math.cos(a) * 0.12, math.sin(a) * 0.12, 0])
    top = np.array([math.cos(a) * 0.35, math.sin(a) * 0.35, H * 0.42])
    stems.append((off, top))
    twigs.append([off, off + (top - off) * 0.4 + np.array([0.04, 0, 0]), top])

N_TIPS = 700
for _ in range(N_TIPS):
    tip = ellipsoid_point(0.25, 1.0)          # biased to the outer shell: dense, rounded canopy
    off, top = stems[rng.integers(3)]
    mid = (top * (0.5 + rng.uniform(-.1, .1)) + tip * 0.5)
    sub = top + (tip - top) * rng.uniform(.35, .6)
    twigs.append([top, sub, tip])
    d = tip - sub; d = d / np.linalg.norm(d)
    d = d + np.array([0, 0, 0.5]); d /= np.linalg.norm(d)
    # terminal whorl: ~8 leaves, 35-75 degrees from the shoot axis, evenly spread in azimuth
    n_w = rng.integers(7, 10)
    base_ang = rng.uniform(0, 2 * math.pi)
    for i in range(n_w):
        az = base_ang + 2 * math.pi * i / n_w
        e1 = np.cross(d, [0.3, 0.9, 0.2]); e1 /= np.linalg.norm(e1); e2 = np.cross(d, e1)
        out = e1 * math.cos(az) + e2 * math.sin(az)
        t = math.radians(rng.uniform(35, 75))
        ld = d * math.cos(t) + out * math.sin(t)
        add_leaf(tip, ld, rng.uniform(-.2, .2), rng.uniform(0.8, 1.15))
    # a few older leaves along the last 10 cm below the whorl (leaves persist behind the tip)
    for i in range(3):
        b = tip - d * rng.uniform(0.04, 0.12)
        az = rng.uniform(0, 2 * math.pi)
        e1 = np.cross(d, [0.3, 0.9, 0.2]); e1 /= np.linalg.norm(e1); e2 = np.cross(d, e1)
        ld = d * 0.35 + (e1 * math.cos(az) + e2 * math.sin(az)) * 0.9
        add_leaf(b, ld, rng.uniform(-.3, .3), rng.uniform(0.85, 1.1))

# ---- build scene objects
bpy.ops.wm.read_factory_settings(use_empty=True)
V = np.concatenate(all_v); UV = np.concatenate(all_uv)
me = bpy.data.meshes.new("leaves")
me.from_pydata(V.tolist(), [], all_f)
me.update()
uvl = me.uv_layers.new(name="UV")
for li, loop in enumerate(me.loops):
    uvl.data[li].uv = UV[loop.vertex_index % len(LUV)] if False else UV[loop.vertex_index]
me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
leaf_obj = bpy.data.objects.new("pittosporum_leaves", me)
bpy.context.scene.collection.objects.link(leaf_obj)


def mat_leaf():
    m = bpy.data.materials.new("leaf"); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    img = nt.nodes.new("ShaderNodeTexImage"); img.image = bpy.data.images.load(os.path.join(TEX, "Leaf001_1K-JPG_Color.jpg"))
    hsv = nt.nodes.new("ShaderNodeHueSaturation")
    hsv.inputs["Hue"].default_value = 0.46; hsv.inputs["Saturation"].default_value = 0.9; hsv.inputs["Value"].default_value = 0.34
    nt.links.new(img.outputs["Color"], hsv.inputs["Color"]); nt.links.new(hsv.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.32
    m.use_backface_culling = False
    return m


def mat_bark():
    m = bpy.data.materials.new("bark"); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    img = nt.nodes.new("ShaderNodeTexImage"); img.image = bpy.data.images.load(os.path.join(TEX, "bark_diff.jpg"))
    nt.links.new(img.outputs["Color"], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.85
    return m


me.materials.append(mat_leaf())

cu = bpy.data.curves.new("twigs", "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = 0.006; cu.bevel_resolution = 2
for pl in twigs:
    sp = cu.splines.new("POLY"); sp.points.add(len(pl) - 1)
    for p, c in zip(sp.points, pl):
        p.co = (*c, 1)
# stems thicker via a second curve
cu2 = bpy.data.curves.new("stems", "CURVE"); cu2.dimensions = "3D"; cu2.bevel_depth = 0.035; cu2.bevel_resolution = 3
for off, top in stems:
    sp = cu2.splines.new("POLY"); sp.points.add(2)
    for p, c in zip(sp.points, [off, off + (top - off) * 0.5, top]):
        p.co = (*c, 1)
for nm, c in (("twigs", cu), ("stems", cu2)):
    o = bpy.data.objects.new(nm, c); c.materials.append(mat_bark()); bpy.context.scene.collection.objects.link(o)
    # UV-less curves: bark colour only; glTF export keeps the material

bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "pittosporum_proto.glb"), export_format="GLB", use_selection=False)
print("tris", sum(len(f) - 2 for f in all_f), "leaves", len(all_f) // 18)
