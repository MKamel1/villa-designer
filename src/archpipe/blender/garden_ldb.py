"""Blender side of the decided garden in the production villa scene (lane GI). Used by `villa_scene.py`; the Python side is `archpipe.landscape.build.production`.

Three jobs: (1) `apply_look` builds the few procedural finishes a scene material names with `garden_look` (water, pond liner, wall weathering, matte stand-in masses, leaf
cut-outs); (2) `finish_meshes` gives leaf-card solids their UVs, keeps only the top face of the water solid and shades stand-in masses smooth; (3) `import_prop` places a graded asset
(Fab FBX with the archive's maps, red-channel opacity, or a glTF) by height / xyz / box / fish, seats it on its base point, and measures where it ended up.
"""
import functools
import glob
import math
import os

import bmesh
import bpy
from mathutils import Vector

from archpipe.landscape.build import fab_blender


def _bsdf(mat):
    return mat.node_tree.nodes["Principled BSDF"]


def _noise_bump(mat, scale, strength, detail=6.0, coord="Object"):
    nt = mat.node_tree
    tc, n, b = (nt.nodes.new("ShaderNodeTexCoord"), nt.nodes.new("ShaderNodeTexNoise"), nt.nodes.new("ShaderNodeBump"))
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    b.inputs["Strength"].default_value = strength
    nt.links.new(tc.outputs[coord], n.inputs["Vector"])
    nt.links.new(n.outputs["Fac"], b.inputs["Height"])
    nt.links.new(b.outputs["Normal"], _bsdf(mat).inputs["Normal"])


def _tint_base(mat, fn):
    """Insert `fn(nt, colour_socket) -> socket` between whatever feeds Base Color and Base Color (or the constant colour)."""
    nt = mat.node_tree
    b = _bsdf(mat)
    link = b.inputs["Base Color"].links[0] if b.inputs["Base Color"].links else None
    if link:
        src = link.from_socket
        nt.links.remove(link)
    else:
        rgb = nt.nodes.new("ShaderNodeRGB")
        rgb.outputs[0].default_value = b.inputs["Base Color"].default_value
        src = rgb.outputs[0]
    nt.links.new(fn(nt, src), b.inputs["Base Color"])


def _mix(nt, op, a, b, fac=1.0):
    m = nt.nodes.new("ShaderNodeMix")
    m.data_type = "RGBA"
    m.blend_type = op
    m.inputs[0].default_value = fac
    if isinstance(a, bpy.types.NodeSocket):
        nt.links.new(a, m.inputs[6])
    else:
        m.inputs[6].default_value = a
    if isinstance(b, bpy.types.NodeSocket):
        nt.links.new(b, m.inputs[7])
    else:
        m.inputs[7].default_value = b
    return m


def _look_wall(mat, spec):
    """Weathered render: a darker, damper splash zone at the foot (soil spatter and rising damp), large soft stains, and faint vertical run-off streaks. Mean colour stays the stated one."""
    z0 = spec.get("ground_z", -3.0)

    def fn(nt, src):
        g = nt.nodes.new("ShaderNodeNewGeometry")
        sp = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(g.outputs["Position"], sp.inputs["Vector"])
        mr = nt.nodes.new("ShaderNodeMapRange")                 # 0 at the ground, 1 from 0.55 m up
        mr.inputs["From Min"].default_value = z0
        mr.inputs["From Max"].default_value = z0 + 0.55
        mr.clamp = True
        nt.links.new(sp.outputs["Z"], mr.inputs["Value"])
        foot = nt.nodes.new("ShaderNodeMath")
        foot.operation = "SUBTRACT"
        foot.inputs[0].default_value = 1.0
        nt.links.new(mr.outputs["Result"], foot.inputs[1])
        stain = nt.nodes.new("ShaderNodeTexNoise")
        stain.inputs["Scale"].default_value = 0.9
        stain.inputs["Detail"].default_value = 3.0
        nt.links.new(g.outputs["Position"], stain.inputs["Vector"])
        streak = nt.nodes.new("ShaderNodeTexNoise")             # stretched in z by scaling the vector: vertical run-off streaks
        streak.inputs["Scale"].default_value = 5.0
        streak.inputs["Detail"].default_value = 2.0
        vm = nt.nodes.new("ShaderNodeVectorMath")
        vm.operation = "MULTIPLY"
        vm.inputs[1].default_value = (1.0, 1.0, 0.08)
        nt.links.new(g.outputs["Position"], vm.inputs[0])
        nt.links.new(vm.outputs[0], streak.inputs["Vector"])
        w = nt.nodes.new("ShaderNodeMath")                      # darkening weight: foot band 0.50 + stains 0.20 + streaks 0.10
        w.operation = "MULTIPLY_ADD"
        w.inputs[1].default_value = 0.50
        nt.links.new(foot.outputs[0], w.inputs[0])
        w.inputs[2].default_value = 0.0
        w2 = nt.nodes.new("ShaderNodeMath")
        w2.operation = "MULTIPLY_ADD"
        w2.inputs[1].default_value = 0.20
        nt.links.new(stain.outputs["Fac"], w2.inputs[0])
        nt.links.new(w.outputs[0], w2.inputs[2])
        w3 = nt.nodes.new("ShaderNodeMath")
        w3.operation = "MULTIPLY_ADD"
        w3.inputs[1].default_value = 0.10
        nt.links.new(streak.outputs["Fac"], w3.inputs[0])
        nt.links.new(w2.outputs[0], w3.inputs[2])
        m = _mix(nt, "MULTIPLY", src, (0.55, 0.52, 0.47, 1.0))
        nt.links.new(w3.outputs[0], m.inputs[0])
        return m.outputs[2]
    _tint_base(mat, fn)


def _look_standin(mat, spec):
    """Matte stand-in mass: no specular, no sheen, a gentle two-scale tonal variation so it does not read as one flat colour. Still labelled a stand-in; no foliage is invented."""
    b = _bsdf(mat)
    b.inputs["Roughness"].default_value = 1.0
    for k in ("Specular IOR Level", "Specular"):
        if k in b.inputs:
            b.inputs[k].default_value = 0.0
    nt = mat.node_tree

    def fn(nt_, src):
        tc = nt_.nodes.new("ShaderNodeTexCoord")
        n1 = nt_.nodes.new("ShaderNodeTexNoise")
        n1.inputs["Scale"].default_value = 5.0
        n1.inputs["Detail"].default_value = 4.0
        nt_.links.new(tc.outputs["Object"], n1.inputs["Vector"])
        ramp = nt_.nodes.new("ShaderNodeMapRange")
        ramp.inputs["To Min"].default_value = 0.70
        ramp.inputs["To Max"].default_value = 1.20
        nt_.links.new(n1.outputs["Fac"], ramp.inputs["Value"])
        vm = nt_.nodes.new("ShaderNodeVectorMath")
        vm.operation = "SCALE"
        nt_.links.new(src, vm.inputs[0])
        nt_.links.new(ramp.outputs["Result"], vm.inputs["Scale"])
        return vm.outputs[0]
    _tint_base(mat, fn)
    _noise_bump(mat, 55.0, 0.25, 6)


def _fresh(mat):
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    return nt, nt.nodes.new("ShaderNodeOutputMaterial")


def _look_water(mat, spec):
    """A SURFACE: transparent mixed with a Fresnel-weighted glossy reflection and a ripple bump (the depth tint is the liner's). Top face only (`finish_meshes`)."""
    nt, out = _fresh(mat)
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    tr.inputs["Color"].default_value = (0.72, 0.89, 0.84, 1)
    gl = nt.nodes.new("ShaderNodeBsdfGlossy")
    gl.inputs["Roughness"].default_value = 0.04
    fr = nt.nodes.new("ShaderNodeFresnel")
    fr.inputs["IOR"].default_value = 1.333
    mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(fr.outputs["Fac"], mx.inputs["Fac"])
    nt.links.new(tr.outputs["BSDF"], mx.inputs[1])
    nt.links.new(gl.outputs["BSDF"], mx.inputs[2])
    nt.links.new(mx.outputs["Shader"], out.inputs["Surface"])
    tc = nt.nodes.new("ShaderNodeTexCoord")
    w1 = nt.nodes.new("ShaderNodeTexNoise")
    w1.inputs["Scale"].default_value = 7.0
    w1.inputs["Detail"].default_value = 3.0
    bm = nt.nodes.new("ShaderNodeBump")
    bm.inputs["Strength"].default_value = 0.10
    bm.inputs["Distance"].default_value = 0.01
    nt.links.new(tc.outputs["Object"], w1.inputs["Vector"])
    nt.links.new(w1.outputs["Fac"], bm.inputs["Height"])
    nt.links.new(bm.outputs["Normal"], gl.inputs["Normal"])
    nt.links.new(bm.outputs["Normal"], fr.inputs["Normal"])


def _look_liner(mat, spec):
    """Wet liner: lighter on the shelf and entry slope, darker and greener with depth (the depth tint of the water above it)."""
    nt = mat.node_tree
    b = _bsdf(mat)
    gp, sp, mr, cr = (nt.nodes.new("ShaderNodeNewGeometry"), nt.nodes.new("ShaderNodeSeparateXYZ"), nt.nodes.new("ShaderNodeMapRange"), nt.nodes.new("ShaderNodeValToRGB"))
    lo, hi = spec.get("water_range") or [-4.05, -3.15]
    mr.inputs["From Min"].default_value = lo
    mr.inputs["From Max"].default_value = hi
    cr.color_ramp.elements[0].position = 0.0
    cr.color_ramp.elements[0].color = (0.015, 0.045, 0.045, 1)
    cr.color_ramp.elements[1].position = 1.0
    cr.color_ramp.elements[1].color = (0.075, 0.125, 0.105, 1)
    nt.links.new(gp.outputs["Position"], sp.inputs["Vector"])
    nt.links.new(sp.outputs["Z"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.6
    _noise_bump(mat, 40.0, 0.3, 4)


def _look_flame(mat, spec):
    b = _bsdf(mat)
    b.inputs["Base Color"].default_value = (1, 0.4, 0.05, 1)
    b.inputs["Emission Color"].default_value = (1.0, 0.35, 0.05, 1)
    b.inputs["Emission Strength"].default_value = 25.0


def _cutout(mat, alpha_socket_fn, shader_fn):
    """Principled colour mixed with Transparent by an alpha; leaves are two-sided cut-outs."""
    nt, out = _fresh(mat)
    pb = nt.nodes.new("ShaderNodeBsdfPrincipled")
    tp = nt.nodes.new("ShaderNodeBsdfTransparent")
    mx = nt.nodes.new("ShaderNodeMixShader")
    shader_fn(nt, pb)
    nt.links.new(alpha_socket_fn(nt), mx.inputs[0])
    nt.links.new(tp.outputs[0], mx.inputs[1])
    nt.links.new(pb.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])


def _look_generic_leaf(mat, spec):
    """STAND-IN leaf card: a procedural pointed oval (width = sin(pi v)^0.7) with a midrib tone; not any species' leaf."""
    base = tuple(spec["base_rgb"])

    def alpha(nt):
        uv = nt.nodes.new("ShaderNodeUVMap")
        sp = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(uv.outputs["UV"], sp.inputs["Vector"])
        s = nt.nodes.new("ShaderNodeMath")
        s.operation = "MULTIPLY"
        s.inputs[1].default_value = math.pi
        nt.links.new(sp.outputs["Y"], s.inputs[0])
        sn = nt.nodes.new("ShaderNodeMath")
        sn.operation = "SINE"
        nt.links.new(s.outputs[0], sn.inputs[0])
        pw = nt.nodes.new("ShaderNodeMath")
        pw.operation = "POWER"
        pw.inputs[1].default_value = 0.7
        nt.links.new(sn.outputs[0], pw.inputs[0])
        half = nt.nodes.new("ShaderNodeMath")
        half.operation = "MULTIPLY"
        half.inputs[1].default_value = 0.48
        nt.links.new(pw.outputs[0], half.inputs[0])
        d = nt.nodes.new("ShaderNodeMath")
        d.operation = "SUBTRACT"
        d.inputs[1].default_value = 0.5
        nt.links.new(sp.outputs["X"], d.inputs[0])
        ab = nt.nodes.new("ShaderNodeMath")
        ab.operation = "ABSOLUTE"
        nt.links.new(d.outputs[0], ab.inputs[0])
        lt = nt.nodes.new("ShaderNodeMath")
        lt.operation = "LESS_THAN"
        nt.links.new(ab.outputs[0], lt.inputs[0])
        nt.links.new(half.outputs[0], lt.inputs[1])
        return lt.outputs[0]

    def shader(nt, pb):
        pb.inputs["Base Color"].default_value = (*base, 1)
        pb.inputs["Roughness"].default_value = 0.65
        for k in ("Specular IOR Level", "Specular"):
            if k in pb.inputs:
                pb.inputs[k].default_value = 0.2
        tc = nt.nodes.new("ShaderNodeTexNoise")
        tc.inputs["Scale"].default_value = 30.0
        uv = nt.nodes.new("ShaderNodeUVMap")
        nt.links.new(uv.outputs["UV"], tc.inputs["Vector"])
        m = _mix(nt, "MULTIPLY", (*base, 1.0), (1.35, 1.35, 1.2, 1.0))
        nt.links.new(tc.outputs["Fac"], m.inputs[0])
        lv = nt.nodes.new("ShaderNodeUVMap")
        lv.uv_map = "LeafVar"
        ls = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(lv.outputs["UV"], ls.inputs["Vector"])
        tone = nt.nodes.new("ShaderNodeMapRange")                  # 0.65 (dark, old) .. 1.25 (young, pale) of the stated colour, with a yellow-green shift in the pale ones
        tone.inputs["To Min"].default_value = 0.65
        tone.inputs["To Max"].default_value = 1.25
        nt.links.new(ls.outputs["X"], tone.inputs["Value"])
        m2 = nt.nodes.new("ShaderNodeVectorMath")
        m2.operation = "SCALE"
        nt.links.new(m.outputs[2], m2.inputs[0])
        nt.links.new(tone.outputs["Result"], m2.inputs["Scale"])
        nt.links.new(m2.outputs[0], pb.inputs["Base Color"])
    _cutout(mat, alpha, shader)


def _look_leafcut(mat, spec):
    """Foliage clumps of a stand-in tree: a leaf-blob cut-out (Voronoi cells with holes), matte. Same construction as the preview's `climber_material`, leaf-on."""
    base = tuple(spec["base_rgb"])
    nt, out = _fresh(mat)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    wp = nt.nodes.new("ShaderNodeTexNoise")
    wp.inputs["Scale"].default_value = 2.5
    wp.inputs["Detail"].default_value = 1.0
    vm = nt.nodes.new("ShaderNodeVectorMath")
    vm.operation = "MULTIPLY_ADD"
    vm.inputs[1].default_value = (0.35, 0.35, 0.35)
    vo = nt.nodes.new("ShaderNodeTexVoronoi")
    vo.voronoi_dimensions = "3D"
    vo.feature = "F1"
    vo.inputs["Scale"].default_value = 26.0
    no = nt.nodes.new("ShaderNodeTexNoise")
    no.inputs["Scale"].default_value = 3.2
    no.inputs["Detail"].default_value = 4.0
    cr = nt.nodes.new("ShaderNodeValToRGB")
    ncr = nt.nodes.new("ShaderNodeValToRGB")
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    pb = nt.nodes.new("ShaderNodeBsdfPrincipled")
    mix = nt.nodes.new("ShaderNodeMixShader")
    cvar = nt.nodes.new("ShaderNodeTexNoise")
    cvar.inputs["Scale"].default_value = 18.0
    cc = nt.nodes.new("ShaderNodeMixRGB")
    nt.links.new(tc.outputs["Object"], wp.inputs["Vector"])
    nt.links.new(wp.outputs["Color"], vm.inputs[0])
    nt.links.new(tc.outputs["Object"], vm.inputs[2])
    nt.links.new(vm.outputs["Vector"], vo.inputs["Vector"])
    nt.links.new(tc.outputs["Object"], no.inputs["Vector"])
    nt.links.new(tc.outputs["Object"], cvar.inputs["Vector"])
    cr.color_ramp.elements[0].position = 0.0
    cr.color_ramp.elements[0].color = (1, 1, 1, 1)
    cr.color_ramp.elements[1].position = 0.62
    cr.color_ramp.elements[1].color = (0, 0, 0, 1)
    nt.links.new(vo.outputs["Distance"], cr.inputs["Fac"])
    ncr.color_ramp.elements[0].position = 0.20
    ncr.color_ramp.elements[1].position = 0.34
    nt.links.new(no.outputs["Fac"], ncr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], mul.inputs[0])
    nt.links.new(ncr.outputs["Color"], mul.inputs[1])
    cc.inputs[1].default_value = (*[0.55 * x for x in base], 1)
    cc.inputs[2].default_value = (*[min(1.0, 1.25 * x) for x in base], 1)
    nt.links.new(cvar.outputs["Fac"], cc.inputs[0])
    nt.links.new(cc.outputs["Color"], pb.inputs["Base Color"])
    pb.inputs["Roughness"].default_value = 0.8
    nt.links.new(mul.outputs["Value"], mix.inputs["Fac"])
    nt.links.new(tr.outputs["BSDF"], mix.inputs[1])
    nt.links.new(pb.outputs["BSDF"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])


ATLAS_ROOT = os.path.expanduser("~/archpipe/shared/assets/user/landscape/fab/unzipped")
ATLASES = {"star-jasmine": ("star_jasmine_pjycl2_4k", "Star_Jasmine_pjycl2_4K")}


def _look_atlas_leaf(mat, spec):
    """Real leaf cut-outs of an LDL atlas (Megascans): BaseColor, Roughness and Opacity from the archive's own JPGs, single-channel maps read from the RED channel (LDL's measured
    defect: read as colour the leaves come out about five times too transparent); a 30 % translucent mix for the backlit leaf."""
    folder, prefix = ATLASES[spec["atlas"]]
    d = os.path.join(ATLAS_ROOT, folder)
    maps = fab_blender.maps_of(d)
    nt, out = _fresh(mat)
    pb = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bc = fab_blender._tex(nt, maps["BaseColor"], False)
    lv = nt.nodes.new("ShaderNodeUVMap")
    lv.uv_map = "LeafVar"
    ls = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(lv.outputs["UV"], ls.inputs["Vector"])
    tone = nt.nodes.new("ShaderNodeMapRange")                      # a little per-leaf tone (0.8-1.1): the scan's own colour stays the base
    tone.inputs["To Min"].default_value = 0.8
    tone.inputs["To Max"].default_value = 1.1
    nt.links.new(ls.outputs["X"], tone.inputs["Value"])
    tm = nt.nodes.new("ShaderNodeVectorMath")
    tm.operation = "SCALE"
    nt.links.new(bc.outputs["Color"], tm.inputs[0])
    nt.links.new(tone.outputs["Result"], tm.inputs["Scale"])
    nt.links.new(tm.outputs[0], pb.inputs["Base Color"])
    nt.links.new(fab_blender._red(nt, fab_blender._tex(nt, maps["Roughness"], True)), pb.inputs["Roughness"])
    sh = pb.outputs["BSDF"]
    tb = nt.nodes.new("ShaderNodeBsdfTranslucent")
    nt.links.new(tm.outputs[0], tb.inputs["Color"])
    ms = nt.nodes.new("ShaderNodeMixShader")
    ms.inputs[0].default_value = 0.3
    nt.links.new(sh, ms.inputs[1])
    nt.links.new(tb.outputs[0], ms.inputs[2])
    tp = nt.nodes.new("ShaderNodeBsdfTransparent")
    mo = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(fab_blender._red(nt, fab_blender._tex(nt, maps["Opacity"], True)), mo.inputs[0])
    nt.links.new(tp.outputs[0], mo.inputs[1])
    nt.links.new(ms.outputs[0], mo.inputs[2])
    nt.links.new(mo.outputs[0], out.inputs["Surface"])


LOOKS = {"wall": _look_wall, "standin": _look_standin, "water": _look_water, "liner": _look_liner, "flame": _look_flame, "generic-leaf": _look_generic_leaf,
         "leafcut": _look_leafcut, "atlas-leaf": _look_atlas_leaf}


def apply_look(mat, spec):
    """Called by `villa_scene.add_material` for a material spec that names a `garden_look`."""
    LOOKS[spec["garden_look"]](mat, spec)


# ---------------------------------------------------------------- meshes

def finish_meshes(mesh_specs, objects, material_specs):
    """After `build_meshes`: UVs for leaf-card solids (six faces a card: front, back, four edges), the water solid reduced to its top face, stand-in masses shaded smooth."""
    for spec in mesh_specs:
        look = material_specs[spec["material"]].get("garden_look")
        if not look:
            continue
        obj = objects[spec["id"]]
        me = obj.data
        if spec.get("leaf_rects") is not None:
            if not spec.get("leaf_uv"):          # a card set without UV windows renders every leaf black (the first draft did): fail closed
                raise ValueError("%s: leaf cards without UV windows" % spec["id"])
            _leaf_uv(me, spec)
        elif look == "water":
            bm = bmesh.new()
            bm.from_mesh(me)
            bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z < 0.9], context="FACES")
            bm.to_mesh(me)
            bm.free()
        elif look in ("standin", "leafcut"):
            for p in me.polygons:
                p.use_smooth = True


def _leaf_uv(me, spec):
    """Per face: card = i // 6, role = i % 6 (0 front, 1 back, 2..5 edges). Front corners bl, br, tr, tl take the card's UV window (u0, v0, u1, v1); the back, wound the other way, takes
    the same window so the leaf reads on both sides."""
    uv = me.uv_layers.new(name="UVMap")
    rects = spec["leaf_uv"]
    ids = spec["leaf_rects"]
    var = me.uv_layers.new(name="LeafVar")             # one random value per card (u = v), for per-leaf tone in the shader: leaves of one plant are not one colour
    import random
    rnd = [random.Random(k * 7919 + 13).random() for k in range(len(ids))]
    for poly in me.polygons:
        k, role = divmod(poly.index, 6)
        for li in poly.loop_indices:
            var.data[li].uv = (rnd[k], rnd[k])
        u0, v0, u1, v1 = rects[ids[k]]
        corners = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
        if role == 1:
            corners = corners[::-1]
        elif role > 1:
            corners = [(u0, v0)] * 4
        for li, c in zip(poly.loop_indices, corners):
            uv.data[li].uv = c


# ---------------------------------------------------------------- assets

def _world_bbox(objs):
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for o in objs:
        if o.type != "MESH":
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    return lo, hi


def _cached_materials():
    """`build_plant` makes a new material (and loads its 4k maps again) for every plant; sixty-five plants would load the same few atlases sixty-five times. One per bank / bark kind."""
    from archpipe.landscape.foliage import blender_build as BB
    if not getattr(BB, "_gi_cached", False):
        BB.leaf_material = functools.lru_cache(None)(BB.leaf_material)
        BB.wood_material = functools.lru_cache(None)(BB.wood_material)
        BB._gi_cached = True
    return BB


def _mask_leaves(plant, M, keepouts, pad=0.04):
    """Drop the leaves whose base falls inside a keep-out box (a bench, table or pot standing against the wall) after the plant's local frame is placed by `M` (4x4, local -> world)."""
    import numpy as np
    L = plant.leaves
    if not keepouts or not len(L.get("length", ())):
        return 0
    w = (np.c_[L["base"], np.ones(len(L["base"]))] @ np.array(M).T)[:, :3]
    bad = np.zeros(len(w), bool)
    for x0, y0, x1, y1 in keepouts:
        bad |= (w[:, 0] > x0 - pad) & (w[:, 0] < x1 + pad) & (w[:, 1] > y0 - pad) & (w[:, 1] < y1 + pad) & (w[:, 2] < 1.2)
    if bad.any():
        keep = ~bad
        for k, v in list(L.items()):
            L[k] = [e for e, kk in zip(v, keep) if kk] if isinstance(v, list) else v[keep]
    return int(bad.sum())


def _import_fg(spec):
    """A generated plant of lane FG (`ldb.mode == 'fg'`): grown here from the species, size, leaf state and the element-id seed, parented to an anchor at the layout point, turned about +z.
    A wall climber grows in the wall's plane facing +y; it is turned so +y is the wall's garden-side normal and pushed off the face until its nearest leaf or stem is `lift` away."""
    import numpy as np
    BB = _cached_materials()
    from archpipe.landscape.foliage import library as FL
    L = spec["ldb"]
    F = L["fg"]
    eid = spec["element_ids"][0]
    plant = FL.plant_for(F["species"], eid, F["height_m"], F["spread_m"], F["state"], F.get("lod", 0), tuple(F.get("lean") or (0, 0)), F.get("clear_stem"))
    at = L["at"]
    th = math.radians(F["yaw_deg"])
    c, s_ = math.cos(th), math.sin(th)
    M = [[c, -s_, 0, at[0]], [s_, c, 0, at[1]], [0, 0, 1, at[2]], [0, 0, 0, 1]]
    cl = F.get("climbing")
    dropped = _mask_leaves(plant, M, cl["keepouts"], 0.04) if cl else 0
    new = BB.build_plant(plant, name="fg-" + spec["id"])
    anchor = bpy.data.objects.new("prop-anchor-" + spec["id"], None)
    bpy.context.collection.objects.link(anchor)
    anchor.rotation_euler = (0, 0, th)
    anchor.location = tuple(at)
    for o in new:
        o.parent = anchor
    bpy.context.view_layer.update()
    lo, hi = _world_bbox(new)
    if cl:                                            # nearest point to the wall face along its normal
        ax, sg, face = cl["axis"], cl["sgn"], cl["face"]
        k = 1 if ax == "x" else 0
        near = (lo[k] - face) * sg if sg > 0 else (face - hi[k]) * 1.0
        push = (cl["lift"] - near) * sg
        loc = list(anchor.location)
        loc[k] += push
        anchor.location = tuple(loc)
        bpy.context.view_layer.update()
        lo, hi = _world_bbox(new)
    for i, o in enumerate(new):
        o.name = "prop-%s-%03d" % (spec["id"], i)
    qa = dict(native=[round(F["spread_m"], 4), round(F["spread_m"], 4), round(F["height_m"], 4)], scale=[1.0, 1.0, 1.0], measured_min=[round(x, 4) for x in lo], measured_max=[round(x, 4) for x in hi],
              base_z_error_m=round(lo.z - at[2], 4), height_m=round(hi.z - lo.z, 4), spread_m=round(max(hi.x - lo.x, hi.y - lo.y), 4), garden_ldb=True, generated_foliage=F["label"], leaves_dropped_keepout=dropped)
    return {"id": spec["id"], "asset": spec["asset"], "label": spec["label"], "objects": [o for o in new if o.type == "MESH"], "material_qa": qa}


def import_prop(spec):
    """Place one graded asset (`spec["ldb"]`): import, scale (height | xyz | box | fish), yaw, seat the base centroid (the mean of the lowest 5 % of vertices: a trunk, stem or leg
    position) on `spec["position"]`. Returns the record `villa_scene.import_props` keeps, with the measured placement."""
    L = spec["ldb"]
    if L["mode"] == "fg":
        return _import_fg(spec)
    path = L["gltf"]
    if path.lower().endswith(".fbx"):
        new = fab_blender.import_fbx(path)
    else:
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=path)
        new = [o for o in bpy.data.objects if o not in before]
    roots = [o for o in new if o.parent is None]
    anchor = bpy.data.objects.new("prop-anchor-" + spec["id"], None)       # one wrapper: a non-uniform scale and the yaw act in WORLD axes, whatever rotation the roots carry
    bpy.context.collection.objects.link(anchor)
    for o in roots:
        o.parent = anchor
        o.matrix_parent_inverse = anchor.matrix_world.inverted()
    bpy.context.view_layer.update()
    lo, hi = _world_bbox(new)
    nat = hi - lo
    mode = L["mode"]
    if mode == "height":
        u = L["scale_to_height_m"] / nat.z
        sv = (u, u, u)
    elif mode == "xyz":
        sv = tuple(L["scale_xyz"])
    elif mode == "box":
        b = L["box_m"]
        sv = (b[0] / nat.x, b[1] / nat.y, b[2] / nat.z)
    elif mode == "fish":
        u = L["length_m"] / max(nat.x, nat.y, nat.z)
        sv = (u, u, u)
    else:
        raise ValueError("garden asset %s: placement mode %r not supported" % (spec["id"], mode))
    anchor.scale = sv
    anchor.rotation_euler = (0, 0, math.radians(L.get("yaw_deg", 0.0)))
    bpy.context.view_layer.update()
    lo, hi = _world_bbox(new)
    at = L.get("at") or spec["position"]          # a koi's `position` is its support point (the water surface); `ldb.at` is where its centre swims
    if mode == "fish":
        c = (lo + hi) / 2
        d = Vector((at[0] - c.x, at[1] - c.y, at[2] - c.z))
    else:
        pts = []
        for o in new:
            if o.type == "MESH":
                for v in o.data.vertices:
                    w = o.matrix_world @ v.co
                    if w.z < lo.z + 0.05 * (hi.z - lo.z):
                        pts.append(w)
        d = Vector((at[0] - sum(p.x for p in pts) / len(pts), at[1] - sum(p.y for p in pts) / len(pts), at[2] - lo.z))
    anchor.location = d
    bpy.context.view_layer.update()
    lo, hi = _world_bbox(new)
    meshes = [o for o in new if o.type == "MESH"]
    for i, o in enumerate(new):
        o.name = "prop-%s-%03d" % (spec["id"], i)
    qa = dict(native=[round(x, 4) for x in nat], scale=[round(x, 4) for x in sv], measured_min=[round(x, 4) for x in lo], measured_max=[round(x, 4) for x in hi],
              base_z_error_m=round(lo.z - at[2], 4), height_m=round(hi.z - lo.z, 4), spread_m=round(max(hi.x - lo.x, hi.y - lo.y), 4), garden_ldb=True)
    return {"id": spec["id"], "asset": spec["asset"], "label": spec["label"], "objects": meshes, "material_qa": qa}


class _Group:
    """Several objects that hide together: the `hide_render` the per-view loop of `villa_scene` sets on a mesh, set on each of a prop's objects."""

    def __init__(self, objs):
        self.objs = objs

    @property
    def hide_render(self):
        return all(o.hide_render for o in self.objs)

    @hide_render.setter
    def hide_render(self, v):
        for o in self.objs:
            o.hide_render = v
            o.hide_viewport = v


def hideable_props(imported_props, hideable):
    """{prop id: _Group} for the imported props a view may hide."""
    return {p["id"]: _Group(p["objects"]) for p in imported_props if p["id"] in hideable}
