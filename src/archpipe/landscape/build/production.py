"""The decided garden in the PRODUCTION villa scene (lane GI): `garden()` returns what `villa_render._build` carries for the garden (meshes, props, notes, plan).

Replaces `villa_landscape.build` for D1. The house, its facade and openings, the neighbours and the street already come from the production scene, so the
preview's context boxes are NOT used; only what the model does not hold is added (plot fences, ground). Materials are production materials (library textures,
stated colour and reflectance) so the garden is lit and exposed like the interiors; the few procedural looks (water, leaf cutouts, matte stand-ins) are named
`garden_look` and built in `blender/garden_ldb.py`. Two variants share one id each: a deciduous plant's leaf-on / leaf-off geometry (`ld_season`) and the fire pit's
closed / open state (`ld_state`); a view hides the ones it does not show (`view_hides`). The visualisation layout is refused (`guard.refuse`).
"""
from __future__ import annotations

import math
import re
from pathlib import Path

from . import build as B
from . import context as CX
from . import guard
from . import preview as PV
from .geom import box

ROOT = Path(__file__).resolve().parents[4]
LAYOUT = ROOT / "knowledge/landscape/concept/final/layout-final.json"
SURFACE_KINDS = ("paving", "path", "gravel", "ground", "bed")
WINTER_MONTHS = (12, 1, 2)          # client 2026-11-22: "we don't mind the sun in Dec to Feb"; leaf-off from December to February (Cairo leaf-drop months are an LDG GAP)


def season_for(when: str) -> str:
    """'winter' for a view dated Dec-Feb, else 'summer'. `when` is the view's ISO date-time."""
    return "winter" if int(when[5:7]) in WINTER_MONTHS else "summer"


def _lum(rgb):
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


def _m(base, rough=0.9, asset=None, tile=None, metal=0.0, note="", **kw):
    d = dict(kind="principled", base_rgb=list(base), reflectance=round(_lum(base), 4), roughness=rough, note=note)
    if metal:
        d["metallic"] = metal
    if asset:
        d["asset"] = asset
        d["tile_m"] = tile or 1.0
    d.update(kw)
    return d


FACADE = (0.455, 0.518, 0.470)      # production 'paint-exterior-grey-green': the house's own exterior and boundary-wall finish
STONE = (0.70, 0.66, 0.58)
TONES = [(0.64, 0.60, 0.55), (0.58, 0.55, 0.51), (0.68, 0.64, 0.58)]

# LDB material name -> (production material name, spec). A name not listed here raises: no part is rendered with a guessed finish.
FIXED = {
    "wall-render": ("garden-render", _m(FACADE, 0.9, "Plaster003", 1.0, contrast=1.6, note="rendered boundary wall in the house's own exterior colour (production paint-exterior-grey-green), library Plaster003 (ambientCG, CC0) textured render; weathered base and streaks in the shader (garden_look wall)", garden_look="wall")),
    "wall-coping": ("garden-coping", _m(STONE, 0.7, "Travertine009", 0.8, note="stone coping slab (ASSUMED)")),
    "paving-joint": ("garden-joint", _m((0.30, 0.28, 0.25), 0.95, note="paving joint (ASSUMED)")),
    "bed-soil": ("garden-mulch", _m((0.30, 0.19, 0.11), 1.0, "wood_chip_path", 0.7, note="bark mulch over soil, CC0 Poly Haven wood_chip_path", procedural_stone_m=0.04)),
    "bed-edging": ("garden-edging", _m((0.06, 0.06, 0.065), 0.4, metal=0.85, note="dark steel bed edging (ASSUMED)")),
    "gravel": ("garden-gravel-chip", _m((0.55, 0.50, 0.42), 1.0, "gravel_ground_01", 0.6, note="gravel, CC0 scan (library), chip scale per metre", procedural_gravel_m=0.03)),
    "ground": ("garden-bare-ground", _m((0.40, 0.31, 0.22), 1.0, "park_dirt", 1.0, note="bare compacted ground where the layout names no surface (a labelled gap), CC0 Poly Haven park_dirt")),
    "ground-far": ("garden-ground-ours", _m((0.40, 0.31, 0.22), 1.0, "park_dirt", 1.5, note="ground under our yard")),
    "ground-neutral": ("garden-ground-neutral", _m((0.36, 0.36, 0.35), 1.0, note="NEUTRAL labelled ground outside our yard: the model holds no ground detail there (not surveyed)")),
    "trellis-timber": ("garden-trellis", _m((0.30, 0.21, 0.13), 0.7, "teak_veneer", 1.0, grain_axis="z", note="timber trellis (ASSUMED)")),
    "seat-timber": ("garden-seat-timber", _m((0.40, 0.27, 0.15), 0.6, "teak_veneer", 1.0, grain_axis="x", note="hardwood seat slats (ASSUMED teak look-alike)")),
    "terracotta": ("garden-terracotta", _m((0.60, 0.28, 0.16), 0.8, note="terracotta pot")),
    "pond-concrete": ("garden-pond-concrete", _m((0.12, 0.13, 0.125), 0.9, note="pond concrete (ASSUMED dark)")),
    "pond-edge": ("garden-pond-edge", _m((0.10, 0.10, 0.11), 0.5, note="contrasting flush lip (ASSUMED dark)")),
    "pond-liner": ("garden-pond-liner", _m((0.05, 0.10, 0.09), 0.6, note="wet liner, tinted by depth in the shader", garden_look="liner")),
    "water": ("garden-water", _m((0.80, 0.93, 0.90), 0.04, note="water surface: Fresnel mix of transparent and glossy, ripple bump (top face only)", garden_look="water")),
    "grille-steel": ("garden-grille", _m((0.025, 0.025, 0.028), 0.5, metal=0.6, note="dark mesh grille (POLICY mesh size)")),
    "pit-steel": ("garden-pit-steel", _m((0.10, 0.10, 0.10), 0.5, metal=0.8, note="fire pit steel")),
    "lava-rock": ("garden-lava", _m((0.05, 0.045, 0.045), 1.0, note="lava rock")),
    "burner": ("garden-burner", _m((0.15, 0.15, 0.15), 0.4, metal=0.9, note="gas burner")),
    "bbq-steel": ("garden-bbq-steel", _m((0.04, 0.04, 0.04), 0.45, metal=0.6, note="simple-geometry BBQ steel (only when no BBQ asset)")),
    "flame": ("garden-flame", _m((1.0, 0.4, 0.05), 0.5, note="flame: an emissive cone, not simulated fire", garden_look="flame")),
    "trunk-bark": ("garden-bark", _m((0.20, 0.15, 0.11), 0.95, note="stand-in tree bark", procedural_stone_m=0.03)),
    "root-barrier": ("garden-root-barrier", _m((0.08, 0.08, 0.09), 0.6, note="root barrier sheet")),
    "climber-stem": ("garden-climber-stem", _m((0.22, 0.15, 0.10), 0.85, note="woody climber stems (ASSUMED colour)")),
    "pergola-alu": ("garden-pergola", _m((0.09, 0.075, 0.065), 0.35, metal=0.8, note="aluminium (only when a pergola is built)")),
}
ALIAS = {"table-timber": "seat-timber", "chair-timber": "seat-timber", "cover-top": "paving-unit#0", "ctx": None}      # parts that use another row's finish ('ctx' = the production exterior render, no spec added)


def material(name: str, table: dict) -> str:
    """Production material name for an LDB part material; adds its spec to `table`. Raises for an unknown name."""
    base = name.split("#")[0]
    if base == "paving-unit" or base == "path-unit":
        k = int(name.split("#")[1]) if "#" in name else 0
        n = "garden-paving-%d" % k if base == "paving-unit" else "garden-path-%d" % k
        spec = _m(TONES[k % 3] if base == "paving-unit" else (0.50, 0.46, 0.40), 0.78, "Travertine009", 0.9, contrast=0.6, procedural_stone_m=0.02,
                  note="0.6 x 0.3 m paving units, joints are geometry; light stone (ASSUMED), library Travertine009 texture (honed stone, no joint lines of its own)")
        table.setdefault(n, spec)
        return n
    if base.startswith("standin:"):
        c = tuple(float(x) for x in base[8:].split(","))
        n = "garden-standin-%02x%02x%02x" % tuple(round(255 * x) for x in c)
        c = tuple(ALBEDO * x for x in c)
        table.setdefault(n, _m(c, 1.0, note="STAND-IN plant mass: matte (no specular, no sheen), slight tonal variation in the shader", garden_look="standin", specular=0.0))
        return n
    if base.startswith("leafcut:"):
        c = tuple(float(x) for x in base.split(":")[1].split(","))
        n = "garden-leafcut-%02x%02x%02x" % tuple(round(255 * x) for x in c)
        c = tuple(ALBEDO * x for x in c)
        table.setdefault(n, _m(c, 0.8, note="STAND-IN tree foliage clumps: matte leaf cut-out (procedural)", garden_look="leafcut", specular=0.0))
        return n
    if base == "leaf-card:star-jasmine":
        table.setdefault("garden-leaf-star-jasmine", _m((0.12, 0.25, 0.09), 0.5, note="real star jasmine leaf cut-outs of the LDL atlas (Megascans, Fab Standard licence), Opacity read from the red channel", garden_look="atlas-leaf", atlas="star-jasmine"))
        return "garden-leaf-star-jasmine"
    if base.startswith("leaf-card:standin:"):
        c = tuple(float(x) for x in base.split(":")[2].split(","))
        n = "garden-leaf-standin-%02x%02x%02x" % tuple(round(255 * x) for x in c)
        c = tuple(ALBEDO * x for x in c)
        table.setdefault(n, _m(c, 0.7, note="STAND-IN generic leaf card (procedural oval cut-out), not any species' leaf", garden_look="generic-leaf", specular=0.2))
        return n
    if base in ALIAS:
        return material(ALIAS[base], table) if ALIAS[base] else "render-exterior"
    if base in FIXED:
        n, spec = FIXED[base]
        table.setdefault(n, spec)
        return n
    raise KeyError("no production finish for garden part material %r" % name)


ALBEDO = 0.5      # ASSUMED: the stand-in colour read from the sourced foliage text is a display colour; a leaf's linear diffuse reflectance is about half of it (green channel 0.1-0.25), so masses and cards are rendered at this fraction


def _faces(part):
    v = part.verts
    return [[[float(x) for x in v[i]] for i in f] for f in part.faces]


LEAF_T = 0.0004      # a leaf card is a closed solid 0.4 mm thick (the scene admits closed solids only); six faces per card: front, back, four edges (`villa_scene` reads the roles for UV)


def _card_solids(part):
    """Each quad card -> a thin closed solid [front, back, 4 sides] (front = the authored face, wound as authored)."""
    import numpy as np
    out = []
    for f in part.faces:
        q = part.verts[f]
        n = np.cross(q[1] - q[0], q[3] - q[0])
        n = n / np.linalg.norm(n)
        b = q - n * LEAF_T
        P = lambda a: [float(x) for x in a]
        out += [[P(q[0]), P(q[1]), P(q[2]), P(q[3])], [P(b[3]), P(b[2]), P(b[1]), P(b[0])],
                [P(q[0]), P(b[0]), P(b[1]), P(q[1])], [P(q[1]), P(b[1]), P(b[2]), P(q[2])], [P(q[2]), P(b[2]), P(b[3]), P(q[3])], [P(q[3]), P(b[3]), P(b[0]), P(q[0])]]
    return out


def _mesh(oid, mid, mat, faces, o, group, **kw):
    d = dict(id=mid, group=group, material=mat, faces=faces, label=o.label, part_kind=BOX_PART_KIND.get(o.kind, "ld-" + o.kind), surface=False, occupied_side=None,
             element_ids=[oid], ld_state=o.state, ld_standin=o.standin, keep_object=bool(o.state or o.winter_parts))
    d.update(kw)
    return d


# Part kinds the scene's physical-part guard admits for single rectangular solids (concept/physical_part.BOX_KINDS): a planar render, paving or ground build-up is a
# 'finish-layer'; soil fill in a straight bed is 'planter-soil'; a masonry seat wall is a 'plinth'. Everything else keeps an 'ld-' kind (closed solids of any shape).
BOX_PART_KIND = {"paving": "finish-layer", "path": "finish-layer", "gravel": "finish-layer", "ground": "finish-layer", "wall": "finish-layer", "coping": "finish-layer",
                 "bed": "planter-soil", "bench": "plinth"}

GROUPS = {"bench": "furniture", "table": "furniture", "chair": "furniture", "bbq": "furniture", "pot": "furniture", "plant": "dressing", "koi": "dressing"}


def _leaf_uv(spec):
    """UV window [u0, v0, u1, v1] per leaf cut-out: the atlas rectangles (px of the 4096 square, origin top-left) for a real atlas, the whole card for a procedural stand-in leaf."""
    if not spec.get("atlas"):
        return [[0.0, 0.0, 1.0, 1.0]]
    from . import planting as PL
    return [[x0 / 4096, 1 - y1 / 4096, x1 / 4096, 1 - y0 / 4096] for x0, y0, x1, y1 in PL.leaf_rects()[0]]


def _object_meshes(o, table, parts, season, tag):
    by, out = {}, []
    for i, p in enumerate(parts):
        m = material("paving-unit#%d" % ((i * 7919) % 3) if p.material == "paving-unit" else p.material, table)      # three paver tones, by part, as the preview did
        e = by.setdefault(m, dict(faces=[], rects=None))
        if p.leaf_rects is not None:
            e["faces"].extend(_card_solids(p))
            e["rects"] = (e["rects"] or []) + list(p.leaf_rects)
        else:
            e["faces"].extend(_faces(p))
    group = GROUPS.get(o.kind, "ground" if o.kind in SURFACE_KINDS else "dressing")      # never 'shell' or 'context': the furniture receipts hash those groups (architecture), and the garden is not architecture
    for m, e in by.items():
        faces = e["faces"]
        mid = o.id + tag if len(by) == 1 else "%s%s.%s" % (o.id, tag, m)
        kw = {}
        if season:
            kw["ld_season"] = season
            kw["keep_object"] = True
        if e["rects"] is not None:
            kw.update(leaf_atlas=table[m].get("atlas", ""), leaf_rects=e["rects"], leaf_uv=_leaf_uv(table[m]), explicit_geometry=True, part_kind="ld-climber-leaf-cards")
        out.append(_mesh(o.id, mid, m, faces, o, group, **kw))
    return out


def _prop(o, species, water_z=None):
    a = o.asset
    pos = list(a["at"])
    at = list(pos)
    if a.get("mode") == "fish" and water_z is not None:       # a koi is carried by the water: the scene's support guard wants a surface under every prop, so the prop's support point is the water surface (its swimming depth stays in `ldb.at`)
        pos[2] = water_z
    nx, ny, nz = a["native_size_m"]
    mode = a.get("mode", "height")
    scale = {"height": lambda: (a["bounds"][5] - a["bounds"][2]) / nz, "xyz": lambda: list(a["scale_xyz"]), "box": lambda: [a["box_m"][0] / nx, a["box_m"][1] / ny, a["box_m"][2] / nz],
             "fish": lambda: a["length_m"] / max(nx, ny, nz)}[mode]()
    d = dict(id=o.id, asset="ldb-" + a["asset_id"].replace("plant", "flora"), label="dressing: " + o.label, position=pos, rotation_deg=[0, 0, a.get("yaw_deg", 0.0)], scale=scale, zone="lower", element_ids=[o.id],
             ldb=dict(at=at, asset_id=a["asset_id"], native_size_m=list(a["native_size_m"]), gltf=a["gltf"], mode=a.get("mode", "height"), scale_to_height_m=a["bounds"][5] - a["bounds"][2], scale_xyz=a.get("scale_xyz"), box_m=a.get("box_m"),
                      length_m=a.get("length_m"), yaw_deg=a.get("yaw_deg", 0.0), tiles=a.get("tiles"), kind=o.kind),
             grade=a["grade"], licence=a["licence"], author=a["author"], source=a["source"])
    if species:
        d["species"] = species
    return d


def _fg_props(o):
    """A generated plant (lane FG) as scene props: one per leaf state (a deciduous plant is two props under one element id, `ld_season` summer / winter; a view hides the one it does not
    show). The plant itself is built inside the Blender job from `ldb.fg` (species, size, state, seed from the element id); the fidelity label rides on the prop."""
    a = o.asset
    fg = a["fg"]
    out = []
    for i, st in enumerate(fg["states"]):
        pid = o.id if i == 0 else o.id + ".winter"
        d = dict(id=pid, asset="ldb-flora-fg-" + fg["species"], label="dressing: " + o.label, position=list(a["at"]), rotation_deg=[0, 0, fg["yaw_deg"]], scale=1.0, zone="lower", element_ids=[o.id],
                 ldb=dict(at=list(a["at"]), asset_id=a["asset_id"], native_size_m=list(a["native_size_m"]), gltf="", mode="fg", yaw_deg=fg["yaw_deg"], kind="plant", fg=dict(fg, state=st)),
                 grade="generated", licence=a["licence"], author=a["author"], source=a["source"], species=fg["species"], fidelity=fg["label"]["fidelity"], caption=fg["label"]["caption"])
        if len(fg["states"]) > 1:
            d["ld_season"] = "summer" if st == "leaf-on" else "winter"
        out.append(d)
    return out


def _fence_meshes(scene, table):
    """The plot fences the layout's own walls do not cover (the sister half), as rendered walls with coping. House, neighbours and street are the production scene's own."""
    from . import elements as E
    from .geom import box
    out, g = [], scene.ground_z
    for c in scene.context:
        if not c["id"].startswith("ctx-site-fence"):
            continue
        x0, y0, x1, y1 = c["rect"]
        o = E.wall(c["id"].replace("ctx-site-", "ld-ctx-"), "ctx", (x0, y0, x1, y1), c["z1"] - g, g)
        o.label = "plot fence (villa_env, 4 m) outside the layout's own walls"
        cp = E.coping(o.id + "-coping", o.id, (x0, y0, x1, y1), c["z1"] - g, g)
        out += _object_meshes(o, table, o.parts, None, "") + _object_meshes(cp, table, cp.parts, None, "")
    return out


def _ground_meshes(scene, table):
    ponds = [list(o.meta["rect"]) for o in scene.objects if o.kind == "pond"]
    ours, neutral = PV.ground_split(ponds)
    z = scene.ground_z - 0.06
    out = []
    for name, quads, mat in (("ours", ours, "ground-far"), ("neutral", neutral, "ground-neutral")):
        faces = []
        for x0, y0, x1, y1 in quads:                  # a closed slab 0.1 m deep per cell (the scene admits closed solids only)
            faces += _faces(box("x", x0, y0, z - 0.1, x1, y1, z))
        out.append(dict(id="ld-ctx-ground-" + name, group="ground", material=material(mat, table), faces=faces, label="ground under the plot (%s); neutral = labelled, not surveyed" % name,
                        part_kind="finish-layer", surface=False, occupied_side=None, element_ids=["ld-ctx-ground-" + name]))
    return out


def garden(layout_path=LAYOUT, age=3):
    """-> dict(meshes, props, notes, plan, materials, ids, summary). Builds both seasons and both fire-pit states; views choose with `view_hides`."""
    L = B.load_layout(layout_path)
    sc = B.build_scene(L, age=age, season="summer", site_context=True)
    guard.refuse(sc, "the production villa scene")
    table, meshes, props, plants = {}, [], [], []
    water = {o.id: o.meta["water_z"] for o in sc.objects if o.kind == "pond"}
    for o in sc.objects:
        if o.parts:
            meshes += _object_meshes(o, table, o.parts, "summer" if o.winter_parts else None, ("." + o.state) if o.state else "")      # the fire pit cover has two states under one id
            if o.winter_parts:
                meshes += _object_meshes(o, table, o.winter_parts, "winter", ".winter")
        if o.asset and o.asset.get("mode") == "fg":
            props += _fg_props(o)
        elif o.asset:
            props.append(_prop(o, o.meta.get("species"), water.get(o.rests_on[0]) if o.kind == "koi" else None))
        if o.kind == "plant":
            plants.append(dict(id=o.id, species=o.meta.get("species", ""), standin=o.standin, generated=bool(o.meta.get("fg")), fidelity=(o.meta.get("fg") or {}).get("fidelity"), label=o.label))
    meshes += _fence_meshes(sc, table) + _ground_meshes(sc, table)
    from . import lights as LT          # lane LG: fitting bodies; the lights themselves go to the scene through `lights()`
    meshes += LT.bodies()
    gen = sum(1 for p in plants if p["generated"])
    drawn = sum(1 for p in plants if not p["standin"]) - gen
    spec_ = sum(1 for p in plants if p["fidelity"] == "species")
    notes = ["Garden (lane GI): the decided layout %s built into the production scene at age %s: %d plants, %d drawn from graded assets, %d GENERATED from leaf scans (lane FG: %d species-fidelity, %d form-class), "
             "%d labelled STAND-INS (generic masses); house, facade, neighbours and street are the production scene's own." % (L["meta"]["layout_id"], age, len(plants), drawn, gen, spec_, gen - spec_, len(plants) - drawn - gen)] + ["garden build: " + w for w in sc.warnings]
    return dict(meshes=meshes, props=props, notes=notes, materials=table, scene=sc, plants=plants,
                plan=dict(g6=None, beds={}, accent_beds={}, paths={}, plants=[], plant_light_review=[], layout_id=L["meta"]["layout_id"]),
                summary=dict(plants=len(plants), drawn=drawn, generated=gen, generated_species_fidelity=spec_, standins=len(plants) - drawn - gen))


def lights():
    """Scene lights of the garden lighting design (lane LG), one per live fitting at the render scene's levels. The scene builder appends them to `scene["lights"]` and, at write time, calls `write_ies`."""
    from . import lights as LT
    return LT.lights()


def write_ies(light, target):
    from . import lights as LT
    LT.write_ies(light, target)


DUSK_STATES = ("exterior-dusk",)


def view_hides(garden_meshes, season, state="closed"):
    """Mesh ids a view must hide: the other season's variant of a deciduous plant, and the other fire-pit state."""
    return [m["id"] for m in garden_meshes if (m.get("ld_season") and m["ld_season"] != season) or (m.get("ld_state") and m["ld_state"] != state)]


GARDEN_VIEW_DATA = ROOT / "knowledge/render-set/views.json"
SUBJECT_KINDS = ("bench", "pond-lip", "firepit", "firepit-cover", "pot", "plant", "screen", "wall", "water")


def garden_view_ids():
    """Ids of the garden views: the 12 `garden: true` rows of the render set plus the lane's own (knowledge/landscape/build/garden-views.json, if present)."""
    import json
    ids = {e["id"] for e in json.loads(GARDEN_VIEW_DATA.read_text())["views"] if e.get("garden")} | set(KEY_VIEWS)
    extra = ROOT / "knowledge/landscape/build/garden-views.json"
    if extra.exists():
        ids |= {e["id"] for e in json.loads(extra.read_text())["views"]}
    return ids


def is_garden_view(v):
    """A render-set garden view, a key view, or any view whose authored subjects name the previous garden's meshes (`landscape-*`: those no longer exist)."""
    return v["id"] in garden_view_ids() or any(str(x).startswith("landscape-") for x in v.get("subjects", []))


def _in_frame(cam, p, aspect):
    """Is the point inside the camera's field of view? (position, target, lens, sensor, shift; yaw and pitch from the target)."""
    px, py, pz = cam["position"]
    tx, ty, tz = cam["target"]
    fx, fy, fz = tx - px, ty - py, tz - pz
    n = math.sqrt(fx * fx + fy * fy + fz * fz)
    f = (fx / n, fy / n, fz / n)
    r = (f[1], -f[0], 0.0)
    rn = math.hypot(r[0], r[1]) or 1.0
    r = (r[0] / rn, r[1] / rn, 0.0)
    u = (r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0])
    d = (p[0] - px, p[1] - py, p[2] - pz)
    z = d[0] * f[0] + d[1] * f[1] + d[2] * f[2]
    if z <= 0.3:
        return None
    x = (d[0] * r[0] + d[1] * r[1] + d[2] * r[2]) / z * cam["lens_mm"] / cam["sensor_mm"] - cam.get("shift_x", 0.0)
    y = (d[0] * u[0] + d[1] * u[1] + d[2] * u[2]) / z * cam["lens_mm"] / cam["sensor_mm"] * aspect - cam.get("shift_y", 0.0) * aspect
    return (x, y, z) if abs(x) <= 0.5 and abs(y) <= 0.5 else None


def subjects_in_frame(view, g, limit=3):
    """Garden element ids in this view's frame, largest on screen first (size over distance). The authored subject lists named the previous garden's meshes."""
    aspect = view["resolution"][1] / view["resolution"][0]
    out = []
    for o in g["scene"].objects:
        if o.kind not in SUBJECT_KINDS or o.state == "open":
            continue
        b = o.bounds()
        c = ((b[0] + b[3]) / 2, (b[1] + b[4]) / 2, (b[2] + b[5]) / 2)
        hit = _in_frame(view["camera"], c, aspect)
        if hit:
            size = max(b[3] - b[0], b[4] - b[1], b[5] - b[2])
            out.append((-size / hit[2], o.id))
    return [i for _, i in sorted(out)[:limit]]


NOT_CLEARED = "GI: NOT CLEARED: "
CLEAR_M = 0.6          # a garden camera keeps at least this far from any garden solid (a camera inside a stand-in mass renders black: v40 did)


def _box_dist(p, b):
    d = [max(b[i] - p[i], 0.0, p[i] - b[i + 3]) for i in range(3)]
    return math.sqrt(sum(x * x for x in d))


def camera_clearance(pos, g):
    """-> (distance to the nearest garden solid, its id) for a camera position; solids = every built object except flat ground surfaces."""
    best = (1e9, None)
    for o in g["scene"].objects:
        if o.state == "open" or o.kind in SURFACE_KINDS or o.kind in ("path", "koi", "water", "grille", "pond"):
            continue
        d = _box_dist(pos, o.bounds())
        if d < best[0]:
            best = (d, o.id)
    return best


CLEAR_SEARCH_M = 6        # lane LG: was 3.5 m; v07 and v19 stood in the south-east bed corner (0.00 m from a plant) and found no clear point within 3.5 m: the first dusk render showed a black plant leaf across the frame


def clear_camera(view, g):
    """Move a garden camera the least distance (in plan, 0.1 m grid, within 3.5 m) to a spot CLEAR_M from every garden solid, inside the plot and outside the house footprints;
    the target is kept. Recorded in the camera's `overrides` with the reason. A camera already clear is untouched; none found raises."""
    cam = view["camera"]
    pos = list(cam["position"])
    if camera_clearance(pos, g)[0] >= CLEAR_M:
        return False
    (x0, y0, x1, y1), _ = CX.ground_plan()
    from . import build as _B
    blds = [_B.R(b) for b in _B.load_layout(LAYOUT)["buildings"]] if pos[2] < -0.5 else []
    inside = lambda r, p: r[0] - 0.2 <= p[0] <= r[2] + 0.2 and r[1] - 0.2 <= p[1] <= r[3] + 0.2
    cands = sorted(((dx * 0.1, dy * 0.1) for dx in range(-CLEAR_SEARCH_M * 10, CLEAR_SEARCH_M * 10 + 1) for dy in range(-CLEAR_SEARCH_M * 10, CLEAR_SEARCH_M * 10 + 1)), key=lambda d: d[0] ** 2 + d[1] ** 2)
    for dx, dy in cands:
        q = [pos[0] + dx, pos[1] + dy, pos[2]]
        if x0 + 0.5 < q[0] < x1 - 0.5 and y0 + 0.5 < q[1] < y1 - 0.5 and not any(inside(b, q) for b in blds) and camera_clearance(q, g)[0] >= CLEAR_M:
            why = camera_clearance(pos, g)
            cam.setdefault("overrides", []).append(dict(field="position", prior=pos, new=q, reason="GI: the authored standing point is %.2f m from %s (inside or touching a garden solid of the decided layout); moved %.2f m, target kept" % (why[0], why[1], math.hypot(dx, dy))))
            cam["position"] = q
            return True
    cam.setdefault("overrides", []).append(dict(field="position", prior=pos, new=pos, reason="%s%s: no clear standing point within %d m (the authored point is %.2f m from %s); camera left where it is" % (NOT_CLEARED, view["id"], CLEAR_SEARCH_M, camera_clearance(pos, g)[0], camera_clearance(pos, g)[1])))
    return False      # fail closed where it matters: `uncleared()` is asserted over the production view set (tests, gi_scene); the legacy view list of `villa_render.VIEWS` also passes through here and must still build


def uncleared(views):
    """Ids of views whose camera `clear_camera` could not move to a clear standing point."""
    return [v["id"] for v in views if any(str(o.get("reason", "")).startswith(NOT_CLEARED) for o in v["camera"].get("overrides", []))]


def prepare_view(view, g):
    """Hide the other season's and the other state's meshes in this view; for a garden view drop the authored old-garden subject lists and name the garden objects in frame."""
    hid = view_hides(g["meshes"] + g["props"], season_for(view["when"]), view.get("ld_state", "closed"))
    from ...concept.authored_values import override
    view.setdefault("hide_meshes", [])
    override(view, "hide_meshes", list(dict.fromkeys(view["hide_meshes"] + hid)), "GI: hide the other season's and the other state's garden meshes in this view")
    if view.get("state") in DUSK_STATES and is_garden_view(view) and "evening-garden" not in view.get("layers_on", []):
        view.setdefault("layers_on", [])
        override(view, "layers_on", view["layers_on"] + ["evening-garden"], "lane LG: the garden's lights are on in every garden view at dusk")
    if not is_garden_view(view):
        return
    if view["camera"]["position"][2] < -0.5:
        clear_camera(view, g)
    first = {}
    for m in g["meshes"]:
        first.setdefault(m["element_ids"][0], m["id"])
    for k in ("visibility_targets", "visibility_allowances", "require_full_subject_frame", "caption_camera_garden") + (() if view.get("presentation_retired") else ("presentation_decision",)):
        view.pop(k, None)
    prop_ids = [p["id"] for p in g["props"]]      # a subject is a MESH of the garden: the scene guard resolves a prop subject through the library's route-geometry record, which holds none of these
    view["subjects"] = [first[i] for i in subjects_in_frame(view, g) if i in first and not any(q.startswith(first[i]) for q in prop_ids)] or []
    upper = view["camera"]["position"][2] > -0.5           # a camera on the ground-floor terrace: the decided layout is the garden level only, so nothing there is a subject (and the house windows stand between)
    if upper:
        view["subjects"] = []
    view["caption_notes"] = ["Garden view in the PRODUCTION scene (lane GI): the decided layout %s with the real house facade, production exposure group and 24 mm camera. "
                             "Labelled stand-ins stand for plants with no graded asset; boundary walls, coping, edging, mulch and furniture details are ASSUMED. Not a procurement or planting specification." % g["plan"]["layout_id"]
                             + (" This camera stands on the ground-floor terrace: the decided layout has no planting up here (the previous top garden is gone), so the view shows the terrace and the garden below." if upper else "")]


# The three key garden views (lane GI): level 24 mm cameras at the production eye height (1.35 m above the garden), shift for the framing. Positions follow the LDB review
# set (`preview.default_views`): from the living door; seated at the dining table's east end looking along the table to the fire pit and the screen opening; the north court
# pond from the lounge side (the preview's high camera needs the house hidden, which the production scene does not do).
KEY_VIEWS = {
    "gi-living-door": dict(title="South garden from the living door", position=[22.85, -26.13, -1.65], target=[27.5, -26.33, -1.65], shift_y=0.02),
    "gi-dining-firepit": dict(title="South garden: dining table, fire pit and the screen opening", position=[27.4, -25.0, -1.75], target=[25.1, -29.6, -1.75], shift_y=-0.04),
    "gi-north-court-pond": dict(title="North court: the koi pond from the lounge side, standing close so the fish are seen through the water", position=[3.2, -25.0, -1.65], target=[0.4, -25.0, -1.65], shift_y=-0.25),
    "gi-dining-firepit-dusk": dict(title="South garden at dusk: dining table, fire pit and the screen opening, garden lit", position=[27.4, -25.0, -1.75], target=[25.1, -29.6, -1.75], shift_y=-0.04, tpl="v07-terrace-dusk"),
    "gi-north-court-pond-dusk": dict(title="North court at dusk: the koi pond from the lounge side, edge lit", position=[3.2, -25.0, -1.65], target=[0.4, -25.0, -1.65], shift_y=-0.25, tpl="v07-terrace-dusk"),
    # the same camera twice, October and January: the shade tree's two leaf states (client: sun welcome Dec-Feb)
    "gi-dining-crown-summer": dict(title="Dining under the crape: leaf-on (October)", position=[23.3, -27.6, -1.65], target=[26.4, -24.4, -1.65], shift_y=0.05),
    "gi-dining-crown-winter": dict(title="Dining under the crape: leaf-off (January)", position=[23.3, -27.6, -1.65], target=[26.4, -24.4, -1.65], shift_y=0.05, when="2027-01-15T10:30:00+02:00"),
}


def key_views(base_views):
    """The key views as scene views, cloned from a garden view of the production set (state, exposure group, sun, resolution, layers) with their own camera; a `when` re-dates the clone and
    recomputes its sun (that is what picks the season)."""
    import copy
    import yaml
    from ...concept.villa_render import sun_for_timestamp
    tpls = {v["id"]: v for v in base_views}
    loc = yaml.safe_load((ROOT / "spec/villa-site.yaml").read_text(encoding="utf-8"))["location"]
    out = []
    for vid, k in KEY_VIEWS.items():
        v = copy.deepcopy(tpls[k.get("tpl", "v41-south-garden-terrace")])
        v.update(id=vid, title=k["title"], final_only=False)
        for stale in ("presentation_retired", "presentation_decision", "overrides"):
            v.pop(stale, None)   # a clone is a NEW client-decided camera: the template's retirement (old-garden v07 clipping, Lead 2026-10-07) and its audit chain are about that other camera
        v["camera"] = dict(position=k["position"], target=k["target"], lens_mm=24, sensor_mm=36, shift_x=0.0, shift_y=k["shift_y"])
        v["samples"] = 1024
        if k.get("when"):
            v["when"] = k["when"]
            v["sun"] = sun_for_timestamp(v["when"], loc)
        out.append(v)
    return out


def reveal_ground(shell_meshes, g):
    """The production shell already carries a flat 'paving' yard floor at the garden level (shell-039, both yards). The garden's own surfaces are coplanar with it (z-fighting: the
    first render showed a second stone pattern through the pavers) and its ponds are closed over by it. Cut that floor back under every flat surface of the garden (paving, paths,
    gravel, ground, beds) and each pond opening, with the same routine the previous garden used for its soil beds; what remains of the floor is the unspecified yard.
    Returns the number of garden footprints cut."""
    from shapely.geometry import box as sbox
    from shapely.ops import unary_union
    from ...concept import villa_landscape as LAND
    z = g["scene"].ground_z
    cuts = []
    for o in g["scene"].objects:
        if o.kind in SURFACE_KINDS:
            polys = [sbox(*p.bounds()[:2], *p.bounds()[3:5]) if p.poly is None else __import__("shapely.geometry", fromlist=["Polygon"]).Polygon(p.poly) for p in o.parts]
            geo = unary_union([q.buffer(0) for q in polys])
        elif o.kind == "pond":
            geo = sbox(*o.meta["rect"])
        else:
            continue
        for q in (geo.geoms if hasattr(geo, "geoms") else [geo]):
            if q.area > 1e-6:
                cuts.append(dict(id="cut-" + o.id, part_kind="soil-bed", faces=[[[x, y, z] for x, y in list(q.exterior.coords)[:-1]]]))
    LAND.reveal_ground_soil(shell_meshes, cuts)
    ponds = [sbox(*o.meta["rect"]) for o in g["scene"].objects if o.kind == "pond"]
    return len(cuts) + _cut_slab_under_ponds(shell_meshes, ponds, z)


SLAB_BAND_M = 0.30      # the yard slab (finish layers, structural slab underside, their thin stacked duplicates) lies within this depth under the garden surface


def _cut_slab_under_ponds(shell_meshes, ponds, ground_z):
    """The pond is a hole in the yard slab: the basin solid goes down to -4.15 but the shell's slab layers (the 1 mm stacked `ceiling-white` finish at z = ground - 0.2, 157 m2, and any other
    horizontal face in the band under the finish) still span the pond opening, and their faces are two-sided in the renderer: from above they were a floor 49 mm under the water that hid the
    liner and every koi (found with a ray cast from the pond camera: the first hit under the water was `villa-merged-0000` at z = -3.199). Cut those horizontal faces back at every pond rect.
    Returns the number of faces cut."""
    import shapely
    from ...concept.garden_render_review import normal
    from shapely.geometry import Polygon
    n = 0
    for m in shell_meshes:
        if m.get("group") not in ("shell", "ground", "context"):
            continue
        slots = m.get("face_materials", [m["material"]] * len(m["faces"]))
        faces, materials, changed = [], [], False
        for face, material in zip(m["faces"], slots):
            z = face[0][2]
            if abs(normal(face)[2]) < 0.999 or max(q[2] for q in face) - min(q[2] for q in face) > 1e-6 or not ground_z - SLAB_BAND_M <= z <= ground_z - 0.02:
                faces.append(face); materials.append(material)
                continue
            poly = Polygon([q[:2] for q in face]).buffer(0)
            rest = poly
            for pond in ponds:
                rest = rest.difference(pond)
            if abs(rest.area - poly.area) < 1e-9:
                faces.append(face); materials.append(material)
                continue
            changed = True
            n += 1
            up = normal(face)[2] > 0
            for tri in shapely.constrained_delaunay_triangles(rest).geoms:       # constrained: a plain Delaunay triangulation plus a `covers` filter drops the triangles that span a concave corner (it lost 15 m2 of a 157 m2 L-shaped slab face)
                pts = [[x, y, z] for x, y in list(tri.exterior.coords)[:-1]]
                faces.append(pts if _ccw(pts) == up else pts[::-1]); materials.append(material)      # wound as the original: counter-clockwise for an up face, clockwise for a down face
        if changed:
            m["faces"], m["face_materials"] = faces, materials
            m["label"] = m.get("label", "") + "; slab layers cut back at the garden ponds"
    return n


def _ccw(pts):
    return sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts))) > 0


BOUNDS_FILE = ROOT / "knowledge/landscape/build/ldb-prop-bounds.json"
SCHEDULE_FILE = ROOT / "knowledge/landscape/build/production/schedule.json"


def prop_bounds(props):
    """{asset: [[gx0, gy0, gz0], [gx1, gy1, gz1]]}: each garden asset's native extent in the glTF Y-up frame `villa_landscape.prop_world_box` reads (scene x = gx, y = -gz, z = gy), centred
    on the placement point, so the geometry-topology review (which takes every prop's box from PROP_BOUNDS x scale) sees the placed size. Native size is measured in Blender's Z-up frame."""
    out = {}
    for p in props:
        nx, ny, nz = p["ldb"]["native_size_m"]
        out[p["asset"]] = [[-nx / 2, 0.0, -ny / 2], [nx / 2, nz, ny / 2]]
    return out


if __name__ == "__main__":      # python -m archpipe.landscape.build.production  -> rewrite knowledge/landscape/build/ldb-prop-bounds.json
    import json
    g = garden()
    BOUNDS_FILE.write_text(json.dumps(prop_bounds(g["props"]), indent=1, sort_keys=True))
    print("wrote", BOUNDS_FILE)
    SCHEDULE_FILE.write_text(json.dumps(g["scene"].schedule, indent=1, sort_keys=True, default=float))      # one row per planted individual: status asset | generated, fidelity, label fields, sizes and their basis
    print("wrote", SCHEDULE_FILE, "(%d rows)" % len(g["scene"].schedule))
