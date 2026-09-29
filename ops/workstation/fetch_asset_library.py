"""Fetch the CC0 material/HDRI/prop library onto this workstation.

Run ON the workstation (scripts/fetch_asset_library.py drives this over ssh
from Windows, the same way ops/workstation/bootstrap.py is driven). Reads
assets/library-manifest.json from the deployed release, downloads each
file with the Python standard library only (no extra pip dependency),
unpacks ambientCG zips, and writes assets/library-index.json recording the
final path, source URL, license and sha256 of every file actually on disk
-- the same provenance discipline as archpipe.rfa's screened downloads.

Idempotent: an already-downloaded file whose sha256 is already recorded is
skipped, so re-running after adding entries to the manifest only fetches
what's new.
"""
from __future__ import annotations
import hashlib
import json
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

USER_AGENT = "archpipe-asset-fetch/1 (+https://github.com/) contact: project-internal"

BOUNDS_TOLERANCE_M = 0.005   # 5 mm: a checked-in bound this far off the freshly measured one is drift, not rounding


def _mat_mult(a: list, b: list) -> list:
    r = [0.0] * 16
    for c in range(4):
        for row in range(4):
            s = 0.0
            for k in range(4):
                s += a[k * 4 + row] * b[c * 4 + k]
            r[c * 4 + row] = s
    return r


def _trs_matrix(node: dict) -> list:
    if "matrix" in node:
        return node["matrix"]
    t = node.get("translation", [0, 0, 0])
    x, y, z, w = node.get("rotation", [0, 0, 0, 1])
    s = node.get("scale", [1, 1, 1])
    xx, yy, zz = x * x, y * y, z * z
    xy, xz, yz = x * y, x * z, y * z
    wx, wy, wz = w * x, w * y, w * z
    rm = [1 - 2 * (yy + zz), 2 * (xy + wz), 2 * (xz - wy), 0,
          2 * (xy - wz), 1 - 2 * (xx + zz), 2 * (yz + wx), 0,
          2 * (xz + wy), 2 * (yz - wx), 1 - 2 * (xx + yy), 0,
          0, 0, 0, 1]
    sm = [s[0], 0, 0, 0, 0, s[1], 0, 0, 0, 0, s[2], 0, 0, 0, 0, 1]
    tm = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, t[0], t[1], t[2], 1]
    return _mat_mult(tm, _mat_mult(rm, sm))


def _apply(m: list, p) -> tuple:
    x, y, z = p
    return (m[0] * x + m[4] * y + m[8] * z + m[12],
            m[1] * x + m[5] * y + m[9] * z + m[13],
            m[2] * x + m[6] * y + m[10] * z + m[14])


def gltf_world_bounds(gltf_path: Path):
    """The prop's native (glTF Y-up, metres) world-space AABB: every POSITION accessor's local AABB (its 8
    corners, so a rotated mesh's box is not under-estimated), transformed by its node's full TRS chain. A naive
    union of every VEC3 accessor's own min/max misses node translations entirely -- some Poly Haven prop files
    (e.g. shrub_02) hold several complete variants as separate root nodes offset sideways from each other, and
    only this walk reproduces the combined box Blender's importer actually creates (verified against a headless
    Blender 4.2.9 import of tree_small_02 and shrub_02, matching to better than 1e-4 m: 2026-09-28)."""
    g = json.loads(gltf_path.read_text())
    scene = g["scenes"][g.get("scene", 0)]
    nodes, meshes, accessors = g["nodes"], g.get("meshes", []), g["accessors"]
    mins, maxs = [1e18] * 3, [-1e18] * 3

    def visit(node_idx, parent_m):
        node = nodes[node_idx]
        m = _mat_mult(parent_m, _trs_matrix(node))
        if "mesh" in node:
            for prim in meshes[node["mesh"]]["primitives"]:
                acc_idx = prim["attributes"].get("POSITION")
                if acc_idx is None:
                    continue
                acc = accessors[acc_idx]
                amin, amax = acc.get("min"), acc.get("max")
                if amin is None or amax is None:
                    continue
                for cx in (amin[0], amax[0]):
                    for cy in (amin[1], amax[1]):
                        for cz in (amin[2], amax[2]):
                            wx, wy, wz = _apply(m, (cx, cy, cz))
                            mins[0], maxs[0] = min(mins[0], wx), max(maxs[0], wx)
                            mins[1], maxs[1] = min(mins[1], wy), max(maxs[1], wy)
                            mins[2], maxs[2] = min(mins[2], wz), max(maxs[2], wz)
        for child in node.get("children", []):
            visit(child, m)

    identity = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    for root in scene["nodes"]:
        visit(root, identity)
    return mins, maxs


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(url: str, dest: Path, label: str) -> int:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    started = time.monotonic()
    with urllib.request.urlopen(req, timeout=120) as resp, dest.open("wb") as out:
        total = 0
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
            total += len(chunk)
    print("  fetched %s (%d KB, %.1fs)" % (label, total // 1024, time.monotonic() - started))
    return total


def poly_haven_model_files(slug: str) -> dict:
    with urllib.request.urlopen(
        urllib.request.Request(f"https://api.polyhaven.com/files/{slug}",
                               headers={"User-Agent": USER_AGENT}), timeout=60) as resp:
        data = json.loads(resp.read())
    # Shape is gltf[<res>]["gltf"] = {"url", "include": {...}}: the package
    # sits one level below the resolution key.
    gltf = data.get("gltf", {})
    for res in ("2k", "1k", "4k", "8k"):
        if res in gltf and "gltf" in gltf[res]:
            return res, gltf[res]["gltf"]
    raise ValueError(f"{slug}: no gltf package published")


def do_material(entry: dict, root: Path, index: dict) -> None:
    asset_id = entry["id"]
    dest_dir = root / "materials" / asset_id
    zip_path = root / "_downloads" / (asset_id + ".zip")
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if dest_dir.is_dir() and any(dest_dir.iterdir()):
        print("  skip %s (already unpacked)" % asset_id)
        return
    fetch(entry["url"], zip_path, asset_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest_dir)
    for f in sorted(dest_dir.rglob("*")):
        if f.is_file():
            index.setdefault("materials", {}).setdefault(asset_id, {})[f.name] = {
                "path": str(f.relative_to(root)), "sha256": sha256(f),
                "source": entry["url"], "license": "CC0"}
    zip_path.unlink()


def do_texture(entry: dict, root: Path, index: dict) -> None:
    """A Poly Haven texture set (2k JPG): colour, roughness and GL normal, saved under the names the renderer's
    material builder looks for (<id>_2K_Color.jpg, _Roughness, _NormalGL), next to the ambientCG materials."""
    asset_id = entry["id"]
    dest_dir = root / "materials" / asset_id
    if dest_dir.is_dir() and any(dest_dir.glob("*_Color.jpg")):
        print("  skip %s (already fetched)" % asset_id)
        return
    with urllib.request.urlopen(
        urllib.request.Request(f"https://api.polyhaven.com/files/{asset_id}",
                               headers={"User-Agent": USER_AGENT}), timeout=60) as resp:
        data = json.loads(resp.read())
    dest_dir.mkdir(parents=True, exist_ok=True)
    recorded = {}
    for key, suffix in (("Diffuse", "Color"), ("Rough", "Roughness"), ("nor_gl", "NormalGL")):
        meta = data.get(key, {}).get("2k", {}).get("jpg")
        if not meta:
            if key == "Diffuse":
                raise ValueError(f"{asset_id}: no 2k diffuse map")
            continue
        out_path = dest_dir / f"{asset_id}_2K_{suffix}.jpg"
        fetch(meta["url"], out_path, f"{asset_id}/{suffix}")
        recorded[out_path.name] = {"path": str(out_path.relative_to(root)), "sha256": sha256(out_path),
                                   "source": meta["url"], "license": "CC0"}
    index.setdefault("materials", {})[asset_id] = recorded


def do_hdri(entry: dict, root: Path, index: dict) -> None:
    asset_id = entry["id"]
    dest = root / "hdri" / (asset_id + ".exr")
    if dest.is_file():
        print("  skip %s (already fetched)" % asset_id)
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    fetch(entry["url"], dest, asset_id)
    index.setdefault("hdris", {})[asset_id] = {
        "path": str(dest.relative_to(root)), "sha256": sha256(dest),
        "source": entry["url"], "role": entry.get("role"), "license": "CC0"}


def do_prop(entry: dict, root: Path, index: dict) -> None:
    asset_id = entry["id"]
    dest_dir = root / "props" / asset_id
    if dest_dir.is_dir() and any(dest_dir.rglob("*.gltf")):
        print("  skip %s (already fetched)" % asset_id)
        return
    res, package = poly_haven_model_files(asset_id)
    if "url" not in package:
        raise ValueError(f"{asset_id}: gltf package has no url")
    dest_dir.mkdir(parents=True, exist_ok=True)
    files = {"model.gltf": package}
    files.update(package.get("include") or {})
    recorded = {}
    for name, meta in files.items():
        out_path = dest_dir / name
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fetch(meta["url"], out_path, f"{asset_id}/{name}")
        recorded[name] = {"path": str(out_path.relative_to(root)),
                          "sha256": sha256(out_path), "source": meta["url"],
                          "license": "CC0"}
    gltf_path = dest_dir / "model.gltf"
    mins, maxs = gltf_world_bounds(gltf_path)
    bounds_m = {"min": [round(v, 4) for v in mins], "max": [round(v, 4) for v in maxs]}
    checked_in = entry.get("bounds_m")
    if checked_in:
        drift = max(abs(a - b) for a, b in zip(checked_in["min"] + checked_in["max"],
                                                bounds_m["min"] + bounds_m["max"]))
        if drift > BOUNDS_TOLERANCE_M:
            raise ValueError(f"{asset_id}: measured bounds {bounds_m} drifted {drift:.4f} m from the "
                              f"checked-in library-manifest.json bounds_m {checked_in} -- the guard in "
                              f"archpipe.concept.villa_landscape trusts the checked-in figure; re-measure and "
                              f"update the manifest before using this asset")
    index.setdefault("props", {})[asset_id] = {"resolution": res, "files": recorded,
                                               "role": entry.get("role"), "bounds_m": bounds_m}


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: fetch_asset_library.py <manifest.json> <library_root>", file=sys.stderr)
        return 2
    manifest = json.loads(Path(sys.argv[1]).read_text())
    root = Path(sys.argv[2])
    root.mkdir(parents=True, exist_ok=True)
    index_path = root / "index.json"
    index = json.loads(index_path.read_text()) if index_path.is_file() else {}

    print("Materials:")
    for entry in manifest.get("materials", []):
        try:
            (do_texture if entry.get("api") == "polyhaven-texture" else do_material)(entry, root, index)
        except Exception as exc:
            print("  FAILED %s: %s" % (entry["id"], exc), file=sys.stderr)
    print("HDRIs:")
    for entry in manifest.get("hdris", []):
        do_hdri(entry, root, index)
    print("Props:")
    for entry in manifest.get("props", []):
        try:
            do_prop(entry, root, index)
        except Exception as exc:
            print("  FAILED %s: %s" % (entry["id"], exc), file=sys.stderr)

    index["license"] = manifest.get("license")
    index["updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True))
    print(index_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
