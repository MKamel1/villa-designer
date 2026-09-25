"""Indexers for appearance sources with open APIs (CC0, no account).

    Poly Haven  api.polyhaven.com   textures (real size in mm) and models
                                    (dimensions in mm); per-file md5 published
    ambientCG   ambientcg.com/api   PBR materials (real size in cm)

Both are fetched through archpipe.fetch (robots.txt obeyed, cached, polite).
Manufacturer catalogues (products) get their own modules as they are added.
"""
from __future__ import annotations

import json
from pathlib import Path

from archpipe import fetch
from archpipe.products import schema
from archpipe.products.store import LIBRARY

PH_API = "https://api.polyhaven.com"
ACG_API = "https://ambientcg.com/api/v2/full_json"
CACHE = LIBRARY / "_cache"


def polyhaven(kind: str = "textures") -> list[dict]:
    """Every Poly Haven texture or model as an appearance record."""
    assets = json.loads(fetch.get_text(f"{PH_API}/assets?t={kind}", CACHE))
    out = []
    for key, a in assets.items():
        words = a.get("tags", []) + a.get("categories", []) + [a.get("name", ""), a.get("category", "")]
        cat = schema.categorise(words) or ("surface" if kind == "textures" else "decor")
        dims = a.get("dimensions")
        data = {"asset_type": "texture" if kind == "textures" else "model",
                "max_resolution": a.get("max_resolution"), "files_hash": a.get("files_hash"),
                "source_category": a.get("category")}
        if dims and kind == "textures":
            data["real_size_mm"] = dims                     # width, height of the tile
        elif dims:
            data["dimensions_mm"] = dims                    # x, y, z of the model
        if a.get("polycount"):
            data["polycount"] = a["polycount"]
        out.append({"id": f"polyhaven:{key}", "kind": "appearance", "category": cat, "source": "polyhaven",
                    "key": key, "name": a.get("name", key), "brand": None, "license": "CC0",
                    "url": f"https://polyhaven.com/a/{key}", "tags": a.get("tags", []),
                    "styles": schema.styles_for(words), "data": data})
    return out


def polyhaven_files(key: str) -> dict:
    return json.loads(fetch.get_text(f"{PH_API}/files/{key}", CACHE))


def ambientcg(page_size: int = 100, max_pages: int = 60) -> tuple[list[dict], int]:
    """Every ambientCG material as an appearance record; also returns the listed total."""
    out, offset, total = [], 0, None
    for _ in range(max_pages):
        page = json.loads(fetch.get_text(
            f"{ACG_API}?type=Material&limit={page_size}&offset={offset}&include=displayData,dimensionsData,tagData",
            CACHE))
        total = page.get("numberOfResults", total)
        found = page.get("foundAssets", [])
        for a in found:
            words = a.get("tags", []) + [a.get("displayName", ""), a.get("displayCategory", "")]
            cat = schema.categorise(words) or "surface"
            data = {"asset_type": "texture", "creation": a.get("creationMethod")}
            if a.get("dimensionX") and a.get("dimensionY"):
                data["real_size_mm"] = [a["dimensionX"] * 10, a["dimensionY"] * 10]   # API gives cm
                data["real_size_basis"] = "ambientCG dimensionX/Y (cm), converted"
            out.append({"id": f"ambientcg:{a['assetId']}", "kind": "appearance", "category": cat,
                        "source": "ambientcg", "key": a["assetId"], "name": a.get("displayName", a["assetId"]),
                        "brand": None, "license": "CC0", "url": a.get("shortLink"), "tags": a.get("tags", []),
                        "styles": schema.styles_for(words), "data": data})
        offset += page_size
        if not found or (total is not None and offset >= total):
            break
    return out, (total or len(out))
