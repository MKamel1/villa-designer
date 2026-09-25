"""Workstation side of the product-library pilot. Two phases, two interpreters:

    <worker python> products_worker.py fetch  --job job.json --lib ~/archpipe/library --out stage1.json
    blender -b --factory-startup -P products_worker.py -- render --job stage1.json --out stage2.json

fetch   downloads each file (archpipe.fetch: robots.txt obeyed), verifies the
        published md5 or size, and measures each texture's albedo with Pillow:
        an sRGB decode that does not involve Blender, so the render check
        below is compared against something independent.
render  Blender 4.5. A texture becomes a 1 x 1 m plane lit ONLY by a uniform
        white environment (radiance 1), seen by an orthographic camera,
        Standard view transform, 32-bit EXR. A diffuse surface under uniform
        radiance L reflects albedo x L, so the rendered mean must equal the
        texture's albedo plus a small specular term. A colour-space mistake
        (base colour read as Non-Color, or a roughness map read as sRGB)
        shifts it far outside tolerance. A negative control does exactly
        that on purpose and must fail.
        A model is imported from glTF; its bounding box is compared with the
        source's published dimensions, and missing textures are detected.
"""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path


def md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------ fetch phase

def srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def albedo_stats(path: Path) -> dict:
    """Mean linear albedo (Rec.709 luminance) of a base-colour map, via Pillow."""
    from PIL import Image
    img = Image.open(path).convert("RGB")
    img.thumbnail((512, 512))
    lut = [srgb_to_linear(i / 255.0) for i in range(256)]
    lum = [0.2126 * lut[r] + 0.7152 * lut[g] + 0.0722 * lut[b] for r, g, b in img.getdata()]
    lum.sort()
    n = len(lum)
    return {"mean": sum(lum) / n, "p01": lum[int(0.01 * n)], "p99": lum[int(0.99 * n) - 1]}


def fetch_phase(job: dict, lib: Path) -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from archpipe import fetch
    out = []
    for it in job["items"]:
        d = lib / it["source"] / it["key"]
        rec = dict(it, dir=str(d), checks=[])
        ok = True
        for f in it["files"]:
            dest = d / f["name"]
            try:
                fetch.download(f["url"], dest)
            except Exception as exc:
                ok = False
                rec["checks"].append({"name": "download_integrity", "status": "failed", "detail": f"{f['name']}: {exc}"})
                break
            if f.get("md5") and md5(dest) != f["md5"]:
                ok = False
                rec["checks"].append({"name": "download_integrity", "status": "failed", "expected": f["md5"],
                                      "measured": md5(dest), "detail": f["name"]})
            elif f.get("size") and dest.stat().st_size != f["size"]:
                ok = False
                rec["checks"].append({"name": "download_integrity", "status": "failed", "expected": f["size"],
                                      "measured": dest.stat().st_size, "detail": f["name"]})
            if dest.suffix == ".zip":
                with zipfile.ZipFile(dest) as z:
                    z.extractall(d)
        if ok:
            basis = "md5 published by the source" if all(f.get("md5") for f in it["files"]) else "size published by the source"
            rec["checks"].append({"name": "download_integrity", "status": "passed", "detail": basis})
        if ok and it["asset_type"] == "texture":
            maps = find_maps(d, it["files"])
            rec["maps"] = {k: str(v) for k, v in maps.items()}
            missing = [m for m in ("base", "rough", "normal") if m not in maps]
            rec["checks"].append({"name": "maps_complete", "status": "failed" if missing else "passed",
                                  "expected": ["base", "rough", "normal"], "measured": sorted(maps),
                                  "detail": ("missing " + ", ".join(missing)) if missing else ""})
            if "base" in maps:
                st = albedo_stats(maps["base"])
                rec["albedo"] = st
                # Physically plausible non-metal albedo: roughly charcoal (~0.03) to fresh snow (~0.9).
                inside = 0.02 <= st["mean"] <= 0.90
                rec["checks"].append({"name": "albedo_physical_range", "status": "passed" if inside else "failed",
                                      "expected": [0.02, 0.90], "measured": round(st["mean"], 4),
                                      "detail": "mean linear luminance of the base-colour map (Pillow sRGB decode)"})
        out.append(rec)
    return {"items": out}


def find_maps(d: Path, files: list[dict] = ()) -> dict:
    """Texture role -> file. The source's own role label wins (Poly Haven's
    file API names the role: Diffuse, Rough, nor_gl, Metal); a filename is
    only a fallback (ambientCG zips: _Color, _Roughness, _NormalGL). The
    filename-only version missed Poly Haven's brown_leather, whose base map
    is called _albedo_, and failed a good asset."""
    found = {f["role"]: d / f["name"] for f in files if f.get("role")}
    roles = {"base": ("_diff_", "_albedo_", "_col_", "_color.", "_basecolor."), "rough": ("_rough_", "_roughness."),
             "normal": ("_nor_gl_", "_normalgl.", "_normal."), "metal": ("_metal_", "_metalness."),
             "disp": ("_disp_", "_displacement.")}
    for p in sorted(d.rglob("*")):
        if p.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            continue
        name = p.name.lower()
        for role, keys in roles.items():
            if role not in found and any(k in name for k in keys):
                found[role] = p
    return found


# ------------------------------------------------------------------ render phase (Blender)

def _reset():
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    import os
    sc.cycles.device = "GPU"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    if os.environ.get("ARCHPIPE_RENDER_CPU"):      # e.g. while a RAG ingest holds the GPU
        sc.cycles.device = "CPU"
    try:
        if sc.cycles.device == "CPU":
            raise RuntimeError("CPU requested")
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = True
    except Exception:
        sc.cycles.device = "CPU"
    sc.cycles.samples = 64
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0
    w = bpy.data.worlds.new("uniform")
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (1, 1, 1, 1)
    bg.inputs[1].default_value = 1.0
    sc.world = w
    return sc


def swatch(rec: dict, out_dir: Path, base_colorspace: str = "sRGB") -> dict:
    import bpy
    import numpy as np
    sc = _reset()
    bpy.ops.mesh.primitive_plane_add(size=1.0)
    plane = bpy.context.active_object
    mat = bpy.data.materials.new("m")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    maps = rec["maps"]

    def tex(path, cs):
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(path)
        n.image.colorspace_settings.name = cs
        return n
    nt.links.new(tex(maps["base"], base_colorspace).outputs[0], bsdf.inputs["Base Color"])
    if "rough" in maps:
        nt.links.new(tex(maps["rough"], "Non-Color").outputs[0], bsdf.inputs["Roughness"])
    if "metal" in maps:
        nt.links.new(tex(maps["metal"], "Non-Color").outputs[0], bsdf.inputs["Metallic"])
    if "normal" in maps:
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(tex(maps["normal"], "Non-Color").outputs[0], nm.inputs["Color"])
        nt.links.new(nm.outputs[0], bsdf.inputs["Normal"])
    plane.data.materials.append(mat)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 1.0
    cam.location = (0, 0, 2)
    sc.collection.objects.link(cam)
    sc.camera = cam
    sc.render.resolution_x = sc.render.resolution_y = 256
    sc.render.image_settings.file_format = "OPEN_EXR"
    sc.render.image_settings.color_depth = "32"
    path = out_dir / f"{rec['source']}-{rec['key']}-{base_colorspace}.exr"
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(str(path))
    px = np.array(img.pixels[:], dtype=np.float32).reshape(-1, 4)
    lum = 0.2126 * px[:, 0] + 0.7152 * px[:, 1] + 0.0722 * px[:, 2]
    return {"rendered_mean": float(lum.mean()), "exr": str(path)}


def swatch_check(rec: dict, rendered: float) -> dict:
    a = rec["albedo"]["mean"]
    # Diffuse albedo plus the dielectric specular reflection of a uniform white
    # environment (~0.04 at normal incidence, more at grazing, less when rough):
    # accept rendered in [0.90 a, 1.10 a + 0.08]. A colour-space swap moves the
    # mean by a factor of 2-4 for typical materials.
    lo, hi = 0.90 * a, 1.10 * a + 0.08
    ok = lo <= rendered <= hi
    return {"name": "swatch_albedo_match", "status": "passed" if ok else "failed",
            "expected": [round(lo, 4), round(hi, 4)], "measured": round(rendered, 4),
            "detail": "Cycles swatch under uniform white environment vs Pillow-decoded albedo"}


def model_check(rec: dict, out_dir: Path) -> list[dict]:
    import bpy
    _reset()
    gltf = next(iter(sorted(Path(rec["dir"]).glob("*.gltf")) + sorted(Path(rec["dir"]).glob("*.glb"))))
    bpy.ops.import_scene.gltf(filepath=str(gltf))
    scale = rec.get("scale")
    if scale:
        # recorded unit correction (knowledge/products/sketchfab-scale-fixes.json); every use must apply it
        for o in bpy.context.scene.objects:
            if o.parent is None:
                o.scale = [v * scale for v in o.scale]
        bpy.context.view_layer.update()
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    from mathutils import Vector
    pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    mins = [min(p[i] for p in pts) for i in range(3)]
    maxs = [max(p[i] for p in pts) for i in range(3)]
    dims = sorted((maxs[i] - mins[i]) * 1000.0 for i in range(3))
    checks = []
    declared = rec.get("declared", {}).get("dimensions_mm")
    if declared:
        want = sorted(declared)
        err = max(abs(a - b) / b for a, b in zip(dims, want))
        checks.append({"name": "dimensions_match", "status": "passed" if err <= 0.03 else "failed",
                       "expected": [round(x) for x in want], "measured": [round(x) for x in dims],
                       "detail": f"sorted bounding-box extents, max relative error {err:.3f} (tolerance 0.03)"})
    else:
        checks.append({"name": "dimensions_match", "status": "not_checkable", "detail": "no published dimensions"})
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in meshes)
    # Poly Haven's published polycount does not say whether it counts the base
    # mesh or the exported (possibly subdivided) file: ceramic_vase_01 imports
    # with 10296 triangles against 2548 published (one subdivision level) while
    # its size matches. A number whose definition is unknown verifies nothing.
    checks.append({"name": "polycount", "status": "not_checkable", "expected": rec.get("declared", {}).get("polycount"),
                   "measured": tris, "detail": "published count's definition (base vs exported mesh) not stated"})
    missing = [i.name for i in bpy.data.images if i.source == "FILE" and not i.has_data and not Path(bpy.path.abspath(i.filepath)).is_file()]
    checks.append({"name": "textures_resolved", "status": "failed" if missing else "passed", "measured": missing})
    sane = 10 <= dims[-1] <= 10000
    checks.append({"name": "units_scale_sane", "status": "passed" if sane else "failed", "expected": [10, 10000],
                   "measured": round(dims[-1]), "detail": "largest extent in mm must be 1 cm to 10 m"
                   + (f"; measured after the recorded unit correction x{scale}" if scale else "")})
    return checks


def render_phase(stage: dict, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    for rec in stage["items"]:
        if any(c["status"] == "failed" and c["name"] == "download_integrity" for c in rec["checks"]):
            continue
        try:
            if rec["asset_type"] == "texture" and "base" in rec.get("maps", {}):
                r = swatch(rec, out_dir)
                rec["swatch"] = r
                rec["checks"].append(swatch_check(rec, r["rendered_mean"]))
                if rec.get("negative_control"):
                    bad = swatch(rec, out_dir, base_colorspace="Non-Color")
                    c = swatch_check(rec, bad["rendered_mean"])
                    rec["negative_control_result"] = {"rendered_mean": bad["rendered_mean"],
                                                      "check_status": c["status"],
                                                      "caught": c["status"] == "failed"}
            elif rec["asset_type"] == "model":
                rec["checks"] += model_check(rec, out_dir)
        except Exception as exc:
            rec["checks"].append({"name": "render_or_import", "status": "failed", "detail": repr(exc)[:500]})
    return stage


def main(argv: list[str]) -> int:
    mode = argv[0]
    args = dict(zip(argv[1::2], argv[2::2]))
    if mode == "fetch":
        res = fetch_phase(json.loads(Path(args["--job"]).read_text()), Path(args["--lib"]))
    elif mode == "render":
        res = render_phase(json.loads(Path(args["--job"]).read_text()), Path(args["--out"]).parent / "swatches")
    else:
        raise SystemExit("mode must be fetch or render")
    Path(args["--out"]).write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    raise SystemExit(main(a))
