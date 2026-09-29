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


def _get(url, token=None):
    headers = {"User-Agent": "archpipe-asset-fetch/1"}
    if token:
        headers["Authorization"] = "Token " + token
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=120) as resp:
        return resp.read()


def main() -> int:
    picks = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    token = (ROOT / "sketchfab-api.txt").read_text(encoding="utf-8").strip()
    for p in picks:
        dest = out / p["id"]
        if (dest / "provenance.json").is_file():
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
        (dest / "provenance.json").write_text(json.dumps(dict(
            id=p["id"], source=meta["viewerUrl"], uid=p["uid"], name=meta["name"], author=meta["user"]["username"],
            author_url=meta["user"].get("profileUrl"), licence=licence, faces=meta.get("faceCount"),
            role=p.get("role"), fetched=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())), indent=1), encoding="utf-8")
        print("fetched %s (%s, %s, %s faces)" % (p["id"], licence, meta["user"]["username"], meta.get("faceCount")))
        time.sleep(1.0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
