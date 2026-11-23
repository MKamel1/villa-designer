"""Fetch a CC0 look-alike PBR material (ambientCG or Poly Haven, 2K JPG) into the shared library, idempotently.

Files land in <library>/materials/<id>/ named so villa_scene.add_material finds '_Color'. A CREDITS.txt records
source URL and licence. Only CC0 sources are used here.
"""
from __future__ import annotations

import io
import json
import urllib.request
import zipfile
from pathlib import Path

LIB = Path.home() / "archpipe" / "assets" / "library" / "materials"
UA = {"User-Agent": "villa-finish-lookalike-fetch/1.0"}


def _get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return r.read()


def fetch(site: str, mid: str, lib: Path = LIB) -> Path:
    dest = lib / mid
    if any(dest.glob("*_Color.jpg")):
        return dest
    dest.mkdir(parents=True, exist_ok=True)
    if site == "ambientCG":
        z = zipfile.ZipFile(io.BytesIO(_get(f"https://ambientcg.com/get?file={mid}_2K-JPG.zip")))
        for n in z.namelist():
            if n.lower().endswith((".jpg", ".png")):
                (dest / Path(n).name).write_bytes(z.read(n))
        url = f"https://ambientcg.com/view?id={mid}"
    elif site == "Poly Haven":
        files = json.loads(_get(f"https://api.polyhaven.com/files/{mid}"))
        for key, suffix in (("Diffuse", "Color"), ("Rough", "Roughness"), ("nor_gl", "NormalGL")):
            u = files[key]["2k"]["jpg"]["url"]
            (dest / f"{mid}_2K_{suffix}.jpg").write_bytes(_get(u))
        url = f"https://polyhaven.com/a/{mid}"
    else:
        raise ValueError(f"unknown look-alike site {site!r}")
    (dest / "CREDITS.txt").write_text(f"{mid}: {site}, CC0 1.0. {url}\nFetched by L4 (finishes palettes), 2026-11-22.\n")
    return dest


def published_scan_mm(site: str, mid: str):
    """The look-alike's own published scan size in mm [x, y], or None when the source does not publish one.
    ambientCG: dimensionX/Y (cm, 0 = unknown). Poly Haven: info 'dimensions' (mm)."""
    if site == "ambientCG":
        d = json.loads(_get(f"https://ambientcg.com/api/v2/full_json?id={mid}&include=dimensionsData"))
        a = d["foundAssets"][0]
        x, y = a.get("dimensionX") or 0, a.get("dimensionY") or 0
        return [x * 10, y * 10] if x and y else None
    if site == "Poly Haven":
        dim = json.loads(_get(f"https://api.polyhaven.com/info/{mid}")).get("dimensions")
        return list(dim[:2]) if dim else None
    raise ValueError(site)


def enrich_palette(path: Path) -> dict:
    """Fetch every look-alike of a palette file and write its published scan size back. Returns id -> scan."""
    pal = json.loads(Path(path).read_text(encoding="utf-8"))
    seen: dict[str, object] = {}
    for it in pal["items"]:
        la = it.get("lookalike")
        if not la:
            continue
        key = (la["maker_site"], la["id"])
        if key not in seen:
            fetch(*key)
            seen[key] = published_scan_mm(*key)
        la["physical_scan_mm"] = seen[key]
        la["on_disk"] = True
    Path(path).write_text(json.dumps(pal, indent=1, ensure_ascii=False), encoding="utf-8")
    return {k[1]: v for k, v in seen.items()}
