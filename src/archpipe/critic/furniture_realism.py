"""Furniture realism check (lane SOFT, client 2026-11-25: "make this check for all furniture").

Flags furniture that reads as fake in a render. Per object, from its geometry and material (pure numpy, so each
check is a unit test on real data):

  box        a pure box: almost every face normal on an axis and no bevel/rounding (severity by category)
  soft-shape a soft good (cushion, pillow, throw) whose front face is flat: it reads as a board
  flat       an object whose finish should show texture is a flat colour
  scale      a fabric whose texture feature size, in mm on the object, is outside the band for its fabric class
  float      claims to rest on something, but nothing holds it up (archpipe.concept.render_support.unsupported)
  penetrate  vertices of a soft good deeper inside its host than a cushion can sink

plus a vision-model question per object crop (`vlm_question`, `crop_for`), which adds judgement a rule cannot hold.

Thresholds are OURS (`POLICY`): the held books carry no fabric-weave, cushion-shape or edge-radius figures (knowledge
search, 2026-11-25), so these are bands that catch gross error, calibrated on the real defect (the rigid cushions of
the 2026-11-25 renders) and on a real scanned asset (Poly Haven throw_pillows_01), not standards.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

POLICY = {
    "box_axis_area_fraction": 0.80,        # share of face area on an axis, at/above which a shape reads as a box
    "axis_tol_deg": 3.0,
    "bevel_ok_m": 0.002,                   # an authored edge radius of 2 mm or more rounds a case good enough
    "soft_crown_spread_deg": 45.0,         # front-face normals must fan out this much (90th pct). Measured 2026-11-25: the rigid
                                           # cushions 31-35 deg, the baked ones 57-60, the scanned Poly Haven pillows 70-71
    "throw_crown_spread_deg": 25.0,        # a folded throw is flatter than a cushion: rigid sheet 0, baked drape 34-39
    "feature_mm_band": {"boucle": [3.0, 9.0], "linen": [0.5, 3.0], "cotton": [0.5, 3.0], "leather": [1.0, 4.0],
                        "velvet": [0.3, 2.0]},
    "penetrate_m": 0.012,                  # render_support REST tolerance: a cushion settles by a few mm
    "vlm_fail_below": 1,                   # VLM score 0 = fake/rigid, 1 = doubtful, 2 = convincing
}
SOFT_ID = re.compile(r"^dress-(cushion|pillow|throw)-")
FLAT_OK = re.compile(r"paint|plaster|glass|metal|steel|mirror|ceramic|screen|brass|chrome|white|black|garment|emiss|marble")
FABRIC_NAMES = re.compile(r"boucle|linen|fabric|cushion|throw|bedding|velvet|leather")
SEVERITY = {"soft": 3.0, "upholstered": 2.0, "case": 1.0}
CHECK_WEIGHT = {"soft-shape": 3.0, "float": 3.0, "penetrate": 3.0, "scale": 2.0, "flat": 2.0, "box": 1.0, "vlm": 2.0}


@dataclass
class Finding:
    object_id: str
    category: str
    check: str
    achieved: str
    required: str
    fix: str
    score: float = 0.0

    def row(self):
        return self.__dict__


# --------------------------------------------------------------------------------------------------- geometry
def triangles(faces):
    out = []
    for f in faces:
        for i in range(1, len(f) - 1):
            out.append((f[0], f[i], f[i + 1]))
    return np.array(out, float).reshape(-1, 3, 3)


def normals_areas(tris):
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    a = np.linalg.norm(n, axis=1)
    keep = a > 1e-12
    return n[keep] / a[keep][:, None], a[keep] / 2


def axis_area_fraction(tris, tol_deg=POLICY["axis_tol_deg"]):
    """Share of face area whose normal is within tol of one of the shape's three principal axes."""
    n, a = normals_areas(tris)
    if len(n) == 0:
        return 0.0
    # principal axes of the (area-weighted) normal covariance: a box has three, a pillow has no stable triple
    cov = (n * a[:, None]).T @ n
    _, vec = np.linalg.eigh(cov)
    cosines = np.abs(n @ vec)
    on = (cosines.max(axis=1) >= math.cos(math.radians(tol_deg)))
    return float(a[on].sum() / a.sum())


def crown_spread_deg(tris):
    """90th percentile angle (deg) between front-face normals and their mean: a board scores ~0, a plump cushion tens."""
    n, a = normals_areas(tris)
    if len(n) == 0:
        return 0.0
    cov = (n * a[:, None]).T @ n
    _, vec = np.linalg.eigh(cov)
    thin = vec[:, 0]                      # the axis the normals vary least along... is the in-plane one; use largest
    front_axis = vec[:, 2]                # dominant normal direction (the cushion face)
    d = n @ front_axis
    for sign in (1, -1):
        sel = sign * d > 0.2
        if sel.sum() >= 8:
            break
    sel = d > 0.2 if (d > 0.2).sum() >= (d < -0.2).sum() else d < -0.2
    nn, aa = n[sel], a[sel]
    mean = (nn * aa[:, None]).sum(0)
    mean /= np.linalg.norm(mean)
    ang = np.degrees(np.arccos(np.clip(nn @ mean, -1, 1)))
    order = np.argsort(ang)
    cum = np.cumsum(aa[order]) / aa.sum()
    return float(ang[order][np.searchsorted(cum, 0.9)])


def feature_fraction(path):
    """Feature size of a texture as a fraction of its tile: twice the 1/e correlation length of the albedo."""
    from PIL import Image
    im = np.asarray(Image.open(path).convert("L"), float)
    n = min(im.shape[0], im.shape[1], 1024)
    im = im[:n, :n] - im[:n, :n].mean()
    ac = np.fft.ifft2(np.abs(np.fft.fft2(im)) ** 2).real
    ac /= ac[0, 0]
    prof = (ac[0, : n // 2] + ac[: n // 2, 0]) / 2
    lag = int(np.argmax(prof < 1 / np.e))
    return 2.0 * lag / n


def measure_fabrics(library_root, assets):
    out = {}
    for a in assets:
        files = sorted(Path(library_root, "materials", a).glob("*_Color.*"))
        if files:
            out[a] = round(feature_fraction(files[0]), 6)
    return out


# ------------------------------------------------------------------------------------------------ the checks
def categorise(mesh):
    mid = mesh["id"]
    kind = (mesh.get("part_kind") or "") + " " + (mesh.get("assembly_kind") or "")
    if SOFT_ID.match(mid):
        return "soft"
    if re.search(r"sofa|armchair|chair|stool|daybed|mattress|pillow|cushion|bench|headboard", kind + " " + mesh["material"]) \
            or FABRIC_NAMES.search(mesh["material"]):
        return "upholstered"
    return "case"


def check_mesh(mesh, materials, fabric_table):
    """Findings for one scene mesh record (a dict with id, material, faces, optional bevel_m/subdivide/smooth_shaded)."""
    out = []
    cat = categorise(mesh)
    tris = triangles(mesh["faces"])
    if len(tris) < 4:
        return out
    rounded = (mesh.get("bevel_m", 0) >= POLICY["bevel_ok_m"] or mesh.get("subdivide", 0) > 0
               or mesh.get("smooth_shaded"))
    frac = axis_area_fraction(tris)
    if cat == "soft":
        spread = crown_spread_deg(tris)
        need = POLICY["throw_crown_spread_deg"] if "-throw-" in mesh["id"] else POLICY["soft_crown_spread_deg"]
        if spread < need:
            out.append(Finding(mesh["id"], cat, "soft-shape", "front-face normal spread %.1f deg" % spread,
                               ">= %.0f deg" % need,
                               "bake a pressure-inflated cloth cushion (blender/soft_goods.soften_cushions)"))
    elif frac >= POLICY["box_axis_area_fraction"] and not rounded:
        fix = {"upholstered": "inflate the cushion and round the arris (puff_upholstery / bevel >= 6 mm)",
               "case": "ease the edges: authored bevel_m >= 2 mm"}[cat]
        out.append(Finding(mesh["id"], cat, "box", "%.0f%% of face area on three axes, no bevel" % (100 * frac),
                           "< %.0f%% or bevel >= %.0f mm" % (100 * POLICY["box_axis_area_fraction"],
                                                             1000 * POLICY["bevel_ok_m"]),
                           fix))
    spec = materials.get(mesh["material"], {})
    if spec.get("kind") in ("principled", None) and not spec.get("asset") and not spec.get("emission_lm_per_m2") \
            and not FLAT_OK.search(mesh["material"]) and (cat != "case" or "walnut" in mesh["material"]
                                                          or "oak" in mesh["material"]):
        out.append(Finding(mesh["id"], cat, "flat", "material '%s' is a flat colour" % mesh["material"],
                           "a textured library finish", "assign a library texture at its true scale, colour from the palette"))
    fclass = spec.get("fabric_class") or fabric_class_of(spec)
    if spec.get("asset") and fclass and not (mesh["id"].startswith("rug") or mesh["material"].startswith(("rug", "carpet"))):    # a carpet is meant to be coarse
        frac_tile = fabric_table.get(spec["asset"])
        if frac_tile:
            mm = frac_tile * spec.get("tile_m", 1.0) * 1000.0
            lo, hi = POLICY["feature_mm_band"][fclass]
            if not lo <= mm <= hi:
                want = math.sqrt(lo * hi)
                out.append(Finding(mesh["id"], cat, "scale", "%s texture feature %.1f mm (tile %.2f m)" % (fclass, mm, spec.get("tile_m", 1.0)),
                                   "%.1f-%.1f mm" % (lo, hi),
                                   "set tile_m to %.3f m (soft_goods.soften_materials)" % (want / (frac_tile * 1000.0))))
    for f in out:
        f.score = SEVERITY[cat] * CHECK_WEIGHT[f.check]
    return out


LOOKALIKE_CLASS = {"Carpet016": "boucle", "rough_linen": "linen", "Fabric066": "cotton", "Fabric036": "linen",
                   "Fabric081C": "cotton", "Fabric082A": "boucle", "Fabric030": "cotton", "Leather035A": "leather"}


def fabric_class_of(spec):
    return LOOKALIKE_CLASS.get(spec.get("asset", ""))


def check_scene(scene, fabric_table, float_items=None):
    """All findings for the visible furniture and soft dressing of a scene dict."""
    mats = scene["materials"]
    out = []
    for m in scene["meshes"]:
        if m["group"] not in ("furniture", "dressing") or not m.get("visibility", {}).get("camera", True):
            continue
        if m["id"].startswith(("ld-", "gl-", "detail-stair", "detail-guard")) or "glass" in m["material"]:
            continue
        if m.get("part_kind") in ("garment", "folded-fabric", "hanger", "shoe", "rail-bracket", "hanging-rail"):
            continue                          # garments are the C3 package's, with their own checks
        out += check_mesh(m, mats, fabric_table)
    for oid, box in (float_items or []):
        out.append(Finding(oid, "case", "float", "nothing supports it (box %s)" % box, "supported or fixed",
                           "place it on its host (render_support.unsupported)", CHECK_WEIGHT["float"] * 2))
    return out


def rank(findings):
    return sorted(findings, key=lambda f: (-f.score, f.object_id, f.check))


# ----------------------------------------------------------------------------------------- penetration (soft goods)
def inside_mask(points, host_tris):
    """Which of `points` (n x 3) lie inside the closed shell `host_tris` (m x 3 x 3): z-ray parity, vectorised."""
    if len(points) == 0 or len(host_tris) == 0:
        return np.zeros(len(points), bool)
    t = host_tris
    a, b, c = t[:, 0], t[:, 1], t[:, 2]
    d = (b[:, 1] - c[:, 1]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 1] - c[:, 1])
    ok = np.abs(d) > 1e-12
    dd = np.where(ok, d, 1.0)
    out = np.zeros(len(points), bool)
    for lo in range(0, len(points), 256):
        p = points[lo:lo + 256, None, :]
        w1 = ((b[:, 1] - c[:, 1]) * (p[..., 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (p[..., 1] - c[:, 1])) / dd
        w2 = ((c[:, 1] - a[:, 1]) * (p[..., 0] - c[:, 0]) + (a[:, 0] - c[:, 0]) * (p[..., 1] - c[:, 1])) / dd
        w3 = 1 - w1 - w2
        hit = ok & (w1 >= 0) & (w2 >= 0) & (w3 >= 0)
        z = w1 * a[:, 2] + w2 * b[:, 2] + w3 * c[:, 2]
        out[lo:lo + 256] = ((hit & (z > p[..., 2])).sum(axis=1) % 2) == 1
    return out


def inside_depth(points, host_tris):
    """(count, max depth m) of the vertices inside the closed host; depth = distance to its nearest face."""
    inside = inside_mask(points, host_tris)
    if not inside.any():
        return 0, 0.0
    from ..concept.render_support import _point_triangle_distance
    sample = points[inside][:: max(1, int(inside.sum()) // 40)]
    return int(inside.sum()), float(_point_triangle_distance(sample, host_tris).min(axis=1).max())


def penetration_findings(scene):
    """Soft goods sunk into a visible solid furniture mesh (not their own sofa's soft inner)."""
    meshes = [m for m in scene["meshes"] if m["group"] == "furniture" and m.get("visibility", {}).get("camera", True)
              and not m["material"].startswith("glass")]
    out = []
    for s in scene["meshes"]:
        if not SOFT_ID.match(s["id"]):
            continue
        pts = np.array([p for f in s["faces"] for p in f], float)
        lo, hi = pts.min(0), pts.max(0)
        for h in meshes:
            hp = np.array([p for f in h["faces"] for p in f], float)
            if np.any(hp.max(0) < lo) or np.any(hp.min(0) > hi):
                continue
            count, depth = 0, 0.0
            from ..concept.render_support import _islands
            for island in _islands(h["faces"]):          # one closed shell at a time: overlapping shells cancel in a parity test
                c_, d_ = inside_depth(pts, triangles(island))
                count, depth = count + c_, max(depth, d_)
            if count and depth > POLICY["penetrate_m"]:
                out.append(Finding(s["id"], "soft", "penetrate", "%d vertices %.0f mm inside %s" % (count, 1000 * depth, h["id"]),
                                   "<= %.0f mm" % (1000 * POLICY["penetrate_m"]),
                                   "lift the cushion off the host by %.0f mm" % (1000 * depth),
                                   CHECK_WEIGHT["penetrate"] * SEVERITY["soft"]))
    return out


# --------------------------------------------------------------------------------------------- the VLM question
VLM_SCHEMA = {"type": "object",
              "properties": {"evidence": {"type": "string"},
                             "outline_is_stiff_straight_lines_like_a_board": {"type": "boolean"},
                             "soft_creases_or_sag_visible": {"type": "boolean"},
                             "fabric_texture_looks_plausible_at_real_size": {"type": "boolean"}},
              "required": ["evidence", "outline_is_stiff_straight_lines_like_a_board", "soft_creases_or_sag_visible",
                           "fabric_texture_looks_plausible_at_real_size"]}


def vlm_question(kind):
    """Observable features, not an overall 'is it real' (a 12B model scored every crop 0 on that, a real scan included)."""
    return ("This is a close crop from a rendered interior. Look only at the %s. Answer three questions about what you see. "
            "(1) Is its outline stiff, with straight edges and sharp corners like a board or box? "
            "(2) Are there soft creases, sag, puckering or a rounded crown, as stuffed fabric has? "
            "(3) Does the fabric texture look plausible at the real size of this object, not blown up or smeared? "
            "Describe the evidence first." % kind)


def vlm_score(answer):
    """0 = fake/rigid, 1 = doubtful, 2 = convincing, from the three answers."""
    stiff = answer.get("outline_is_stiff_straight_lines_like_a_board")
    soft = answer.get("soft_creases_or_sag_visible")
    tex = answer.get("fabric_texture_looks_plausible_at_real_size")
    if stiff is None or soft is None or tex is None:
        return None
    good = (not stiff) + soft + tex
    return 0 if good <= 1 else 1 if good == 2 else 2


def project(view, points):
    """Pixel (u, v) of world points for a view dict (the camera of blender/villa_scene.configure_camera, level + shift)."""
    c = view["camera"]
    pos = np.array(c["position"] + ([c["height_m"]] if len(c["position"]) == 2 else []), float) if len(c["position"]) == 2 \
        else np.array(c["position"], float)
    tgt = np.array(c["target"], float)
    d = tgt - pos
    hor = np.array([d[0], d[1], 0.0])
    fwd = hor / np.linalg.norm(hor)
    right = np.cross(fwd, [0, 0, 1.0])
    rel = points - pos
    z = rel @ fwd
    k = c["lens_mm"] / c["sensor_mm"]
    shift_y = c.get("shift_y", 0) + d[2] / np.linalg.norm(hor) * k
    x = (rel @ right) / z * k + c.get("shift_x", 0)
    y = (rel[:, 2]) / z * k + shift_y
    W, H = view["resolution"]
    return np.stack([(x + 0.5) * W, H / 2 - y * W], axis=1), z


def crop_for(view, points, image_path, out_path, pad=0.25, min_px=96):
    """Crop the render around an object's projected bounds; None when it is not in frame."""
    from PIL import Image
    uv, z = project(view, points)
    if (z <= 0.05).any():
        return None
    im = Image.open(image_path)
    W, H = im.size
    sx, sy = W / view["resolution"][0], H / view["resolution"][1]
    u0, v0 = uv.min(0)
    u1, v1 = uv.max(0)
    w, h = u1 - u0, v1 - v0
    x0, x1 = max(0, (u0 - pad * w) * sx), min(W, (u1 + pad * w) * sx)
    y0, y1 = max(0, (v0 - pad * h) * sy), min(H, (v1 + pad * h) * sy)
    if x1 - x0 < min_px or y1 - y0 < min_px or (u1 - u0) * (v1 - v0) <= 0:
        return None
    if (u0 < 0 or v0 < 0 or u1 > view["resolution"][0] or v1 > view["resolution"][1]):
        return None                           # object cut by the frame: no fair verdict
    im.crop((int(x0), int(y0), int(x1), int(y1))).save(out_path)
    return out_path


# ------------------------------------------------------------------------------- imported models (scanned assets)
def gltf_triangles(path):
    """World-of-the-asset triangles (n x 3 x 3) of a glTF 2.0 file: node hierarchy applied, no placement."""
    path = Path(path)
    g = json.loads(path.read_text(encoding="utf-8"))
    bins = [(path.parent / b["uri"]).read_bytes() for b in g.get("buffers", []) if "uri" in b and not b["uri"].startswith("data:")]

    def acc(i):
        a = g["accessors"][i]
        bv = g["bufferViews"][a["bufferView"]]
        n = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[a["type"]]
        dt = {5126: "f4", 5123: "u2", 5125: "u4", 5121: "u1"}[a["componentType"]]
        off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        return np.frombuffer(bins[bv["buffer"]], dtype=dt, count=a["count"] * n, offset=off).reshape(-1, n)

    def local(node):
        if "matrix" in node:
            return np.array(node["matrix"], float).reshape(4, 4).T
        m = np.eye(4)
        x, y, z, w = node.get("rotation", [0, 0, 0, 1])
        r = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                      [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                      [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
        m[:3, :3] = r * np.array(node.get("scale", [1, 1, 1]))
        m[:3, 3] = node.get("translation", [0, 0, 0])
        return m
    out = []

    def walk(i, parent):
        node = g["nodes"][i]
        m = parent @ local(node)
        if "mesh" in node:
            for prim in g["meshes"][node["mesh"]]["primitives"]:
                if prim.get("mode", 4) != 4 or "indices" not in prim:
                    continue
                v = acc(prim["attributes"]["POSITION"]).astype(float)
                v = v @ m[:3, :3].T + m[:3, 3]
                out.append(v[acc(prim["indices"]).ravel().astype(int)].reshape(-1, 3, 3))
        for c in node.get("children", []):
            walk(c, m)
    for r in g["scenes"][g.get("scene", 0)]["nodes"]:
        walk(r, np.eye(4))
    return np.concatenate(out) if out else np.empty((0, 3, 3))


def model_findings(scene, library_root):
    """Box check on each imported furniture model's own geometry (the scan, before placement)."""
    out = []
    seen = {}
    for m in scene.get("models", []):
        asset = m["asset"]
        if asset not in seen:
            for name in ("model.gltf", "scene.gltf"):
                f = Path(library_root, "props", asset, name)
                if f.exists():
                    seen[asset] = axis_area_fraction(gltf_triangles(f)) if f.stat().st_size < 5_000_000 else None
                    break
            else:
                seen[asset] = None
        frac = seen[asset]
        if frac is not None and frac >= POLICY["box_axis_area_fraction"] and m.get("role") not in ("rug",):
            out.append(Finding(m["id"], "case", "box", "scan %s: %.0f%% of face area on three axes" % (asset, 100 * frac),
                               "< %.0f%%" % (100 * POLICY["box_axis_area_fraction"]),
                               "replace the asset with a modelled one or bevel it at import", SEVERITY["case"] * CHECK_WEIGHT["box"]))
    return out


def markdown(findings, title):
    rows = ["# " + title, "", "| rank | object | category | check | achieved | required | fix |", "|---|---|---|---|---|---|---|"]
    for i, f in enumerate(findings, 1):
        rows.append("| %d | `%s` | %s | %s | %s | %s | %s |" % (i, f.object_id, f.category, f.check, f.achieved, f.required, f.fix))
    return "\n".join(rows) + "\n"


# ------------------------------------------------------------------------------------------------------- driver
def fabric_table():
    import gzip
    root = Path(__file__).resolve().parents[3] / "knowledge" / "soft-fabric-classes.json.gz"
    with gzip.open(root, "rt", encoding="utf-8") as f:
        return json.load(f)["feature_fraction_of_tile"]


def run(scene, with_float=True, with_penetration=True):
    float_items = []
    if with_float:
        from ..concept.render_support import unsupported
        float_items = unsupported(scene)
    found = check_scene(scene, fabric_table(), float_items)
    if with_penetration:
        found += penetration_findings(scene)
    return rank(found)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="furniture realism check over a scene.json")
    ap.add_argument("--scene", required=True)
    ap.add_argument("--soft", action="store_true", help="apply blender.soft_goods.soften_scene first (the render's geometry)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-float", action="store_true")
    ap.add_argument("--library-root", help="also check the imported models' own geometry (library props)")
    ap.add_argument("--md", help="write the ranked list as a markdown table")
    ap.add_argument("--md-title", default="Furniture realism: flagged items, ranked")
    a = ap.parse_args(argv)
    scene = json.loads(Path(a.scene).read_text(encoding="utf-8"))
    if a.soft:
        from ..blender import soft_goods
        soft_goods.soften_scene(scene)
    found = run(scene, with_float=not a.no_float)
    if a.library_root:
        found = rank(found + model_findings(scene, a.library_root))
    if a.md:
        Path(a.md).write_text(markdown(found, a.md_title), encoding="utf-8")
    Path(a.out).write_text(json.dumps([f.row() for f in found], indent=1) + "\n", encoding="utf-8")
    print(len(found), "findings;", len({f.object_id for f in found}), "objects")
    for f in found[:25]:
        print("%5.1f %-34s %-10s %s" % (f.score, f.object_id, f.check, f.achieved))
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
