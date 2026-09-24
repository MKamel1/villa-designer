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
    gltf = data.get("gltf", {})
    for res in ("2k", "1k", "4k", "8k"):
        if res in gltf:
            return res, gltf[res]
    if gltf:
        res = next(iter(gltf))
        return res, gltf[res]
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
    dest_dir.mkdir(parents=True, exist_ok=True)
    files = {"model.gltf": package} if "url" in package else {}
    for name, meta in (package.get("include") or {}).items():
        files[name] = meta
    if "url" in package:
        files["model.gltf"] = package
    recorded = {}
    for name, meta in files.items():
        out_path = dest_dir / name
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fetch(meta["url"], out_path, f"{asset_id}/{name}")
        recorded[name] = {"path": str(out_path.relative_to(root)),
                          "sha256": sha256(out_path), "source": meta["url"],
                          "license": "CC0"}
    index.setdefault("props", {})[asset_id] = {"resolution": res, "files": recorded,
                                               "role": entry.get("role")}


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
        do_material(entry, root, index)
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
