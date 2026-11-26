"""Soft furnishings: cushions, pillows, sofa seat/back cushions and fabric finish (lane SOFT, client 2026-11-25).

Pure numpy, no Blender: `soften_scene(scene)` rewrites a scene dict (as `villa_render.write` produced it) so the
renderer and the realism check see the same soft geometry. The rigid sources are left in the scene file untouched;
this runs on the loaded dict, like the cloth duvets do.

Root cause being fixed (docs/lessons/SOFT.md): scatter cushions were a formula shell with a knife-edge rim and a
dead-flat crown, lying on a symmetric mid-plane; their fabric was a carpet photo stretched to 21 mm loops with
roughness 0.5 and no sheen or fuzz. The sofa seat/back cushions were bevelled boxes.

Geometry: a cushion's rigid mesh is only used for its footprint (principal axes, extents, lowest edge). The shape
is a pressure-inflated two-panel cloth baked once (`soft_bake.py`, knowledge/soft-cushion-bakes.json.gz), fitted to
that footprint with its base on the old rear plane, so nothing moves farther from the sofa than it did.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import re
from functools import lru_cache
from pathlib import Path

import numpy as np

KNOWLEDGE = Path(__file__).resolve().parents[3] / "knowledge"
CUSHION_ID = re.compile(r"^dress-(cushion|pillow)-")
THROW_ID = re.compile(r"^dress-throw-")
# the sofa and armchair meshes whose seat/back islands become soft cushions
UPHOLSTERED = re.compile(r"sofa|armchair|loveseat|daybed|lounge_chair|chair_upholstered")


@lru_cache(maxsize=1)
def bakes():
    with gzip.open(KNOWLEDGE / "soft-cushion-bakes.json.gz", "rt", encoding="utf-8") as f:
        doc = json.load(f)
    out = {}
    for key, b in doc["bakes"].items():
        fmt, seed = key.split(":")
        w, h, t = (int(v) for v in fmt.split("x"))
        out[(w, h, t, int(seed))] = (np.array(b["verts_mm"], float), b["quads"])
    return out


@lru_cache(maxsize=1)
def throw_bakes():
    with gzip.open(KNOWLEDGE / "soft-cushion-bakes.json.gz", "rt", encoding="utf-8") as f:
        doc = json.load(f)
    return {int(k.split(":")[1]): (np.array(b["verts_mm"], float), b["quads"], b["grid"]) for k, b in doc["throws"].items()}


@lru_cache(maxsize=1)
def fabric_classes():
    with gzip.open(KNOWLEDGE / "soft-fabric-classes.json.gz", "rt", encoding="utf-8") as f:
        return json.load(f)


def _seed(identifier, n=3):
    return int(hashlib.sha1(identifier.encode()).hexdigest(), 16) % n + 1


def _smooth(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def _wrinkle(x, y, seed):
    r = np.array([((seed * 2654435761 + k * 40503) % 1000) / 1000.0 for k in range(9)])
    return sum(np.sin((8 + 14 * r[3 * k]) * x + (-9 + 18 * r[3 * k + 1]) * y + 6.28 * r[3 * k + 2]) for k in range(3)) / 3


def footprint(points):
    """(centre, e_a, e_b, e_t, extents (A, B, T), t_min) of a flat object: e_t is the thin axis, pointing up
    (a cushion's soft face looks into the room, never down)."""
    c = points.mean(0)
    _, _, vt = np.linalg.svd(points - c, full_matrices=False)
    e_a, e_b, e_t = vt
    if e_t[2] < 0:
        e_t = -e_t
    # a standing cushion keeps its width horizontal; a lying one keeps its principal axes
    horizontal = np.cross([0.0, 0.0, 1.0], e_t)
    if np.linalg.norm(horizontal) > 0.2:
        e_a = horizontal / np.linalg.norm(horizontal)
        e_b = np.cross(e_t, e_a)
    elif np.dot(np.cross(e_a, e_b), e_t) < 0:
        e_b = -e_b
    def proj(e):
        d = points @ e
        return d.min(), d.max()
    (a0, a1), (b0, b1), (t0, t1) = proj(e_a), proj(e_b), proj(e_t)
    ctr = e_a * (a0 + a1) / 2 + e_b * (b0 + b1) / 2 + e_t * t0
    return ctr, e_a, e_b, e_t, (a1 - a0, b1 - b0, t1 - t0)


def shape_cushion(identifier, a_m, b_m, t_m, dent=None):
    """Baked cushion verts (mm, local x width / y height / z up from the base) fitted to an a x b x t footprint (m)."""
    if a_m < b_m:
        raise ValueError("long axis first")
    A, B, T = a_m * 1000, b_m * 1000, t_m * 1000
    keys = sorted({(w, h, t) for (w, h, t, _s) in bakes()})
    w, h, t = min(keys, key=lambda k: abs(math.log(A / k[0])) + abs(math.log(B / k[1])))
    seed = _seed(identifier)
    v, quads = bakes()[(w, h, t, seed)]
    v = v.copy()
    crown = v[:, 2].max()
    v[:, 0] *= A / w
    v[:, 1] *= B / h
    # never thicker than the rigid thing it replaces
    v[:, 2] *= min(1.0, 0.96 * T / crown)
    z = v[:, 2] / max(v[:, 2].max(), 1e-9)
    xn, yn = v[:, 0] / (A / 2), v[:, 1] / (B / 2)
    # small asymmetric slump toward one side plus a soft wrinkle field: a stuffed cushion is never symmetric
    amp = v[:, 2].max()
    v[:, 2] += amp * 0.06 * _wrinkle(xn, yn, seed) * z * _smooth(1 - np.abs(xn) * np.abs(yn), 0.02, 0.3)
    v[:, 2] -= amp * 0.10 * np.maximum(0, yn) * z * (seed % 2)            # the top sags on alternate cushions
    if dent is None:
        dent = seed == 2                                                   # a karate-chop dent on one in three
    if dent:
        chop = np.exp(-(xn / 0.22) ** 2) * _smooth(yn, 0.25, 0.97) * z
        v[:, 2] -= amp * 0.34 * chop
    v[:, 2] = np.maximum(v[:, 2], 0)
    return v, quads


def _closed_outward(verts, quads):
    """Quads wound so the shell's normals point out (volume > 0)."""
    vol = 0.0
    for q in quads:
        p = verts[q]
        c = p.mean(0)
        for i in range(4):
            a, b = p[i], p[(i + 1) % 4]
            vol += np.dot(c, np.cross(a, b)) / 6.0
    return quads if vol >= 0 else [q[::-1] for q in quads]


def soft_cushion_faces(identifier, points):
    """World faces (m) of the baked cushion replacing a rigid one with vertices `points` (n x 3, m)."""
    ctr, e_a, e_b, e_t, (A, B, T) = footprint(points)
    swap = A < B
    if swap:
        e_a, e_b = e_b, -e_a          # keep right-handed with e_t
        A, B = B, A
    v_mm, quads = shape_cushion(identifier, A, B, T)
    world = ctr + (v_mm[:, 0:1] / 1000) * e_a + (v_mm[:, 1:2] / 1000) * e_b + (v_mm[:, 2:3] / 1000) * e_t
    # ground it as the rigid one was: same lowest point, moved along its rear plane (never into the back)
    dz = points[:, 2].min() - world[:, 2].min()
    up = np.array([0, 0, 1.0]) - e_t * e_t[2]
    if np.linalg.norm(up) > 0.25:
        world = world + up / np.dot(up, [0, 0, 1.0]) * dz
    else:
        world[:, 2] += dz
    quads = _closed_outward(world, quads)
    return [[world[i].round(6).tolist() for i in q] for q in quads]


THROW_THICK_MM = 20.0       # a throw folded in three, loosely: ours (policy), not a product figure
THROW_MAX_MM = 70.0


def soft_throw_faces(identifier, points):
    """World faces (m) of the baked loosely-draped throw, fitted to the old throw's footprint."""
    ctr, e_a, e_b, e_t, (A, B, T) = footprint(points)
    # footprint() keeps the width horizontal for a standing object; a throw lies, so use the principal axes
    c = points.mean(0)
    _, _, vt = np.linalg.svd((points - c)[:, :2], full_matrices=False)
    e_b = np.array([*vt[0], 0.0])            # long axis in plan
    e_a = np.array([*vt[1], 0.0])
    e_t = np.array([0.0, 0.0, 1.0])
    if np.dot(np.cross(e_a, e_b), e_t) < 0:
        e_a = -e_a
    a = np.ptp(points @ e_a)
    b = np.ptp(points @ e_b)
    v, quads, (nx, ny) = throw_bakes()[_seed(identifier)]
    v = v.copy()
    v[:, 0] *= a * 1000 / 410.0
    v[:, 1] *= b * 1000 / 570.0
    v[:, 2] = np.minimum(v[:, 2], THROW_MAX_MM)
    # cloth creases fold sharply in a coarse sim; a few Laplacian passes on the height give rounded folds
    h = v[:, 2].reshape(nx + 1, ny + 1)
    for _ in range(4):
        pad = np.pad(h, 1, mode="edge")
        h = 0.5 * h + 0.125 * (pad[:-2, 1:-1] + pad[2:, 1:-1] + pad[1:-1, :-2] + pad[1:-1, 2:])
    v[:, 2] = h.ravel()
    bottom, top = v.copy(), v.copy()
    top[:, 2] += THROW_THICK_MM
    n = len(v)
    verts = np.vstack([bottom, top])
    faces = [q[::-1] for q in quads] + [[i + n for i in q] for q in quads]
    # rim: the sheet is a (nx+1) x (ny+1) grid, row-major in i then j
    idx = lambda i, j: i * (ny + 1) + j
    ring = [idx(i, 0) for i in range(nx)] + [idx(nx, j) for j in range(ny)] + \
           [idx(i, ny) for i in range(nx, 0, -1)] + [idx(0, j) for j in range(ny, 0, -1)]
    for k, i0 in enumerate(ring):
        i1 = ring[(k + 1) % len(ring)]
        faces.append([i0, i1, i1 + n, i0 + n])
    lo = np.array([(points @ e_a).min(), (points @ e_b).min()])
    world = np.array([c[:2] * 0 for _ in verts])
    cx, cy = (points @ e_a).min() + a / 2, (points @ e_b).min() + b / 2
    pw = (cx + verts[:, 0] / 1000.0)[:, None] * e_a + (cy + verts[:, 1] / 1000.0)[:, None] * e_b
    pw[:, 2] = points[:, 2].min() + verts[:, 2] / 1000.0
    faces = _closed_outward(pw, faces)
    return [[pw[i].round(6).tolist() for i in q] for q in faces]


def soften_throws(scene):
    n = 0
    hosts = host_shells(scene)
    for m in scene["meshes"]:
        if THROW_ID.match(m["id"]):
            pts = np.array([p for f in m["faces"] for p in f], float)
            m["faces"], moved = rest_on_hosts(soft_throw_faces(m["id"], pts), hosts)
            m["soft_goods_moved_m"] = [round(float(v), 3) for v in moved]
            m["smooth_shaded"] = True
            m["subdivide"] = 2
            m.pop("bevel_m", None)
            m["soft_goods"] = "baked cloth-drop throw"
            n += 1
    return n


def host_shells(scene):
    """(bbox, triangles) of every closed shell of the visible solid furniture a soft good can rest on."""
    from ..concept.render_support import _islands
    from ..critic.furniture_realism import triangles
    out = []
    for m in scene["meshes"]:
        if m["group"] != "furniture" or not m.get("visibility", {}).get("camera", True) or m["material"].startswith("glass"):
            continue
        for isl in _islands(m["faces"]):
            t = triangles(isl)
            pts = t.reshape(-1, 3)
            out.append((pts.min(0), pts.max(0), t))
    return out


def rest_on_hosts(faces, hosts, tol=0.004, step=0.004, limit=0.16):
    """Move a soft good out of any host it sinks into, a few mm at a time: straight up out of a seat (a host whose
    thin axis is vertical), forward along the soft good's own horizontal normal out of a back. A cushion rests ON its
    seat; it does not sink into it, and a cushion never climbs a back to dodge a seat."""
    from ..critic.furniture_realism import inside_mask
    pts = np.array([p for f in faces for p in f], float)
    ctr, e_a, e_b, e_t, _ = footprint(pts)
    fwd = np.array([e_t[0], e_t[1], 0.0])
    fwd = fwd / np.linalg.norm(fwd) if np.linalg.norm(fwd) > 0.2 else np.zeros(3)
    sample = np.unique(pts.round(4), axis=0)
    lo0, hi0 = pts.min(0) - limit, pts.max(0) + limit
    near = [(hlo, hhi, tris) for hlo, hhi, tris in hosts if not (np.any(hhi < lo0) or np.any(hlo > hi0))]
    axes = []
    for hlo, hhi, tris in near:
        thin = int(np.argmin(hhi - hlo))
        if thin == 2:
            axes.append(np.array([0, 0, 1.0]))
            continue
        out = np.zeros(3)                                # horizontal, perpendicular to the back, towards the soft good
        out[thin] = 1.0 if ctr[thin] >= (hlo[thin] + hhi[thin]) / 2 else -1.0
        axes.append(out)

    def sunk(k, off):
        hlo, hhi, tris = near[k]
        q = sample + off
        if np.any(hhi < q.min(0)) or np.any(hlo > q.max(0)):
            return False
        return bool(inside_mask(q - np.array([0, 0, tol]), tris).any())
    off = np.zeros(3)
    for _ in range(2):                                   # a second pass: a lift can bring a back into contact
        for k, axis in enumerate(axes):
            if not np.any(axis):
                continue
            for _ in range(int(limit / step)):
                if not sunk(k, off):
                    break
                off = off + axis * step
    if np.any(off):
        faces = [[(np.array(p) + off).round(6).tolist() for p in f] for f in faces]
    return faces, off


def soften_cushions(scene):
    n = 0
    hosts = host_shells(scene)
    for m in scene["meshes"]:
        if not CUSHION_ID.match(m["id"]):
            continue
        pts = np.array([p for f in m["faces"] for p in f], float)
        m["faces"], moved = rest_on_hosts(soft_cushion_faces(m["id"], pts), hosts)
        m["soft_goods_moved_m"] = [round(float(v), 3) for v in moved]
        m["smooth_shaded"] = True
        m["subdivide"] = 1
        m.pop("bevel_m", None)
        m["soft_goods"] = "baked cloth-pressure cushion"
        n += 1
    return n


# ----------------------------------------------------------------------------------- sofa seat and back cushions
def _islands(faces):
    parent = {}

    def find(a):
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    keys = [[tuple(np.round(p, 4)) for p in f] for f in faces]
    for ks in keys:
        for k in ks[1:]:
            parent[find(ks[0])] = find(k)
    groups = {}
    for i, ks in enumerate(keys):
        groups.setdefault(find(ks[0]), []).append(i)
    return list(groups.values())


def puff_upholstery(mesh):
    """Inflate the seat and back cushion islands of a sofa/armchair mesh in place; returns how many."""
    faces = mesh["faces"]
    isl = _islands(faces)
    allp = np.array([p for f in faces for p in f], float)
    centre = allp.mean(0)
    done = 0
    for idx in isl:
        P = np.array([p for i in idx for p in faces[i]], float)
        ctr, e_a, e_b, e_t, (A, B, T) = footprint(P)
        if not (0.10 <= T <= 0.32 and A >= 0.45 and B >= 0.45 and len(idx) >= 60):
            continue
        # an island is a seat cushion when its thin axis is vertical, a back cushion when it is horizontal
        toward = e_t if e_t[2] > 0.7 else (e_t if np.dot(e_t[:2], (centre - ctr)[:2]) >= 0 else -e_t)
        crown_m = 0.045 if e_t[2] > 0.7 else 0.06
        keys = {}
        for i in idx:
            for p in faces[i]:
                keys[tuple(np.round(p, 4))] = np.array(p)
        out = {}
        a_half, b_half = A / 2, B / 2
        t_hi = (P @ toward).max()
        for k, p in keys.items():
            d = p - ctr
            ua, ub = np.dot(d, e_a) / a_half, np.dot(d, e_b) / b_half
            on_front = (p @ toward) > t_hi - 0.02              # only the face the sitter sees is inflated
            prof = max(0.0, 1 - abs(ua) ** 2.4) * max(0.0, 1 - abs(ub) ** 2.4)
            corner = 1 - 0.55 * (abs(ua) * abs(ub)) ** 2
            seed = _seed(str(k))
            wr = _wrinkle(ua, ub, seed) * 0.012
            push = (crown_m * prof * corner + wr * prof) if on_front else 0.0
            # corners of a stuffed cushion fall away
            sag = -0.018 * (abs(ua) * abs(ub)) ** 3 if on_front else 0.0
            out[k] = p + toward * push + np.array([0, 0, sag]) if on_front else p
        for i in idx:
            faces[i] = [out[tuple(np.round(p, 4))].round(6).tolist() for p in faces[i]]
        done += 1
    if done:
        mesh["subdivide"] = max(mesh.get("subdivide", 0), 2)
        mesh["smooth_shaded"] = True
        mesh["bevel_m"] = max(mesh.get("bevel_m", 0), 0.010)
        mesh["soft_goods"] = "inflated seat/back cushions"
    return done


def soften_upholstery(scene):
    n = 0
    for m in scene["meshes"]:
        if not m.get("visibility", {}).get("camera", True):
            continue                      # a proxy replaced by an imported model: nothing to see
        if m["id"].startswith("furn-") and UPHOLSTERED.search(m.get("part_kind", "") + " " + m.get("assembly_kind", "")):
            n += puff_upholstery(m)
    return n


# ---------------------------------------------------------------------------------------------------- fabric finish
LOOKALIKE_CLASS = {"Carpet016": "boucle", "rough_linen": "linen", "Fabric066": "cotton", "Fabric036": "linen",
                   "Fabric081C": "cotton", "Fabric082A": "boucle", "Fabric030": "cotton", "Leather035A": "leather"}


def soften_materials(scene):
    """Give soft-goods materials a fabric class, the tile that puts the measured weave at the class pitch,
    and fabric roughness. Colours (the maker image's mean linear colour) are not touched."""
    cls = fabric_classes()
    n = 0
    used = {m["material"] for m in scene["meshes"] if CUSHION_ID.match(m["id"]) or THROW_ID.match(m["id"])}
    for name in used:
        spec = scene["materials"].get(name)
        if not spec or spec.get("kind") != "principled":
            continue
        fclass = LOOKALIKE_CLASS.get(spec.get("asset", ""), "cotton")
        table = cls["classes"][fclass]
        frac = cls["feature_fraction_of_tile"].get(spec.get("asset", ""))
        if frac:
            # the texture's measured feature size is frac x tile; put it at the class target
            spec["tile_m"] = round(table["feature_mm"] / (frac * 1000.0), 4)
        spec["fabric_class"] = fclass
        spec["roughness"] = table["roughness"]
        spec["sheen"] = table["sheen"]
        spec["fuzz"] = table["fuzz"]
        n += 1
    return n


def soften_scene(scene):
    """Entry point: returns the same dict, softened, with a record of what changed."""
    # upholstery first: the soft goods must rest on the inflated seat, not on the rigid one it replaces
    report = {"upholstery_islands": soften_upholstery(scene)}
    report.update(cushions=soften_cushions(scene), throws=soften_throws(scene), materials=soften_materials(scene))
    scene["soft_goods"] = report
    return report


def assert_soft_goods_real(scene):
    """Render post-condition: after softening, no soft good may fail the furniture realism check (shape, fabric scale,
    floating or sinking). A rigid cushion cannot reach a presentation render again."""
    from ..critic import furniture_realism as F
    found = [f for f in F.check_scene(scene, F.fabric_table()) if f.category == "soft"] + F.penetration_findings(scene)
    if found:
        raise ValueError("soft goods fail the realism check: " + "; ".join(
            "%s %s (%s)" % (f.object_id, f.check, f.achieved) for f in found[:8]))
    return len(found)
