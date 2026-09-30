"""Download CC0 / CC-BY Sketchfab models listed in a picks file, with licence provenance.

    PYTHONPATH=src python ops/workstation/fetch_sketchfab.py <picks.json> <out_dir>

The API token is read from sketchfab-api.txt at the repo root (git-ignored; created by the user) and is sent only
in the Authorization header to api.sketchfab.com; it is never printed or written anywhere else. Each model's
licence is re-read from the API at download time and anything other than CC0 / CC Attribution is refused. Each
archive is unpacked to <out_dir>/<id>/ with a provenance.json (source, author, licence, fetched-at) beside it.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API = "https://api.sketchfab.com/v3/models/"
ALLOWED = {"CC0 Public Domain", "CC Attribution"}
MANIFEST = ROOT / "ops" / "workstation" / "library-manifest.json"


def record_front(p, dest):
    from front_axis import directional_role, measured_or_manual_front
    if not directional_role(p.get("role", "")):
        return
    model = next(dest.rglob("*.gltf"), None)
    if model is None:
        raise ValueError(p["id"] + ": no glTF for front-axis measurement")
    measured_or_manual_front(p, model)


def _get(url, token=None):
    headers = {"User-Agent": "archpipe-asset-fetch/1"}
    if token:
        headers["Authorization"] = "Token " + token
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=120) as resp:
        return resp.read()


def main() -> int:
    picks = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    if MANIFEST.is_file():
        manual = {e["id"]: e["front_axis"] for e in json.loads(MANIFEST.read_text(encoding="utf-8")).get("props", [])
                  if e.get("front_axis_basis") == "lead-verified"}
        for pick in picks:
            if pick["id"] in manual:
                pick["front_axis"] = manual[pick["id"]]
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    token = (ROOT / "sketchfab-api.txt").read_text(encoding="utf-8").strip()
    for p in picks:
        dest = out / p["id"]
        if (dest / "provenance.json").is_file():
            record_front(p, dest)
            print("skip", p["id"])
            continue
        meta = json.loads(_get(API + p["uid"]))
        licence = (meta.get("license") or {}).get("label")
        if licence not in ALLOWED or not meta.get("isDownloadable"):
            print("REFUSED %s: licence %r downloadable %r" % (p["id"], licence, meta.get("isDownloadable")))
            continue
        links = json.loads(_get(API + p["uid"] + "/download", token))
        pkg = links.get("gltf") or links.get("glb")
        if not pkg:
            print("FAILED %s: no glTF package (%s)" % (p["id"], ", ".join(links)))
            continue
        zpath = out / (p["id"] + ".zip")
        zpath.write_bytes(_get(pkg["url"]))
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zpath) as zf:
            zf.extractall(dest)
        zpath.unlink()
        record_front(p, dest)
        (dest / "provenance.json").write_text(json.dumps(dict(
            id=p["id"], source=meta["viewerUrl"], uid=p["uid"], name=meta["name"], author=meta["user"]["username"],
            author_url=meta["user"].get("profileUrl"), licence=licence, faces=meta.get("faceCount"),
            role=p.get("role"), fetched=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())), indent=1), encoding="utf-8")
        print("fetched %s (%s, %s, %s faces)" % (p["id"], licence, meta["user"]["username"], meta.get("faceCount")))
        time.sleep(1.0)
    Path(sys.argv[1]).write_text(json.dumps(picks, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if MANIFEST.is_file():
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        by_id = {p["id"]: p for p in picks}
        for entry in manifest.get("props", []):
            found = by_id.get(entry["id"])
            if found and found.get("front_axis"):
                entry.update(front_axis=found["front_axis"], front_axis_basis=found["front_axis_basis"])
        MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
