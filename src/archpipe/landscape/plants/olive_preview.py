"""Blender (headless): import the Fab olive FBX (game-optimised, 2 materials) and render the 5 m / 15 m grading views (LDL pass 6).

    blender -b --python-exit-code 1 -P olive_preview.py -- --out DIR [--samples 64]

Writes olive_d{5,15}_az{0,90,180,270}.png, olive_d25_az0.png (whole tree, not part of the rubric) and olive.stats.json.
FBX is in centimetres with a 0.01 object scale: Blender reports 9.82 x 9.90 x 7.27 m, i.e. metres are right with no extra scale.
Foliage: Olive_D colour + its ALPHA cut-out, Olive_N normal, AORM green channel = roughness (Unreal ORM). Trunk: Tronco_D, Olivio_N.
The UCX_ collision hull in the FBX is deleted."""
import json, math, os, sys, time
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from megascans_mat import reset_scene  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
A = dict(zip(argv[::2], argv[1::2])); OUT = A["--out"]; os.makedirs(OUT, exist_ok=True)
D = os.path.expanduser("~/archpipe/shared/assets/user/landscape/fab/unzipped/olive_tree_source/")
t0 = time.time()
sc, cam = reset_scene(500, int(A.get("--samples", 64)))
sc.cycles.transparent_max_bounces = 32
bpy.ops.import_scene.fbx(filepath=D + "SM_ItalianTress_Olive.FBX")
for o in [o for o in bpy.data.objects if o.name.startswith("UCX_")]:
    bpy.data.objects.remove(o)
tree = bpy.data.objects["SM_ItalianTress_Olive"]


def img(name, nc):
    i = bpy.data.images.load(D + name); i.colorspace_settings.name = "Non-Color" if nc else "sRGB"; return i


def mat(m, color, normal, alpha, rough_from=None):
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); pb = nt.nodes.new("ShaderNodeBsdfPrincipled")
    c = nt.nodes.new("ShaderNodeTexImage"); c.image = img(color, False); nt.links.new(c.outputs["Color"], pb.inputs["Base Color"])
    n = nt.nodes.new("ShaderNodeTexImage"); n.image = img(normal, True); nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(n.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], pb.inputs["Normal"])
    if rough_from:
        r = nt.nodes.new("ShaderNodeTexImage"); r.image = img(rough_from, True); sp = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(r.outputs["Color"], sp.inputs["Color"]); nt.links.new(sp.outputs["Green"], pb.inputs["Roughness"])
    sh = pb.outputs["BSDF"]
    if alpha:
        tp = nt.nodes.new("ShaderNodeBsdfTransparent"); mx = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(c.outputs["Alpha"], mx.inputs[0]); nt.links.new(tp.outputs[0], mx.inputs[1]); nt.links.new(sh, mx.inputs[2]); sh = mx.outputs[0]
    nt.links.new(sh, out.inputs["Surface"])


mat(tree.material_slots[0].material, "T_ItalianTress_Olive_D.PNG", "T_ItalianTress_Olive_N.PNG", True, "T_ItalianTress_Olive_AORM.PNG")
mat(tree.material_slots[1].material, "T_ItalianTress_Olivio_Tronco_D.PNG", "T_ItalianTress_Olivio_N.PNG", False)
bb = [tree.matrix_world @ Vector(c) for c in tree.bound_box]
lo = Vector(map(min, *[tuple(v) for v in bb])); hi = Vector(map(max, *[tuple(v) for v in bb]))
tree.location -= Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z)); bpy.context.view_layer.update()
size = [round(hi[i] - lo[i], 3) for i in range(3)]
for d, azs in ((5, (0, 90, 180, 270)), (15, (0, 90, 180, 270)), (25, (0,))):
    for az in azs:
        r = math.radians(az); cam.location = (d * math.sin(r), -d * math.cos(r), 1.6)
        cam.rotation_euler = (Vector((0, 0, size[2] / 2)) - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = f"{OUT}/olive_d{d}_az{az}.png"; bpy.ops.render.render(write_still=True)
tree.data.calc_loop_triangles()
json.dump({"id": "fab_olive_tree_source", "size_m": size, "tris": len(tree.data.loop_triangles), "seconds": round(time.time() - t0, 1)}, open(f"{OUT}/olive.stats.json", "w"), indent=1)
print("OK olive", size)
