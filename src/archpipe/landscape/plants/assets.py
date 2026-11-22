"""Validate the asset grading table (knowledge/landscape/plants/assets.json) against the species library."""
from __future__ import annotations

import json
from pathlib import Path

from .library import DATA

GRADES = {"A", "B", "C", "D"}
FITS = {"species", "genus", "look-alike", "none"}
LICENCES = {"CC0", "CC Attribution"}   # free assets only; anything else is a paid or unclear licence (own table)
DRAWABLE = {"drawable", "drawable_as_genus_standin", "not drawable yet"}


def gltf_untextured_share(path) -> float:
    """Share of glTF materials with neither a base-colour texture nor a base-colour factor: such a material
    renders white (the Sketchfab banana palm). 1.0 = fully untextured."""
    g = json.loads(Path(path).read_text(encoding="utf-8"))
    mats = g.get("materials") or []
    if not mats:
        return 1.0
    bare = sum(1 for m in mats if "baseColorTexture" not in m.get("pbrMetallicRoughness", {})
               and "baseColorFactor" not in m.get("pbrMetallicRoughness", {}))
    return round(bare / len(mats), 3)


def validate_manifest(doc: dict, manifest: dict) -> list[str]:
    """Every asset stored outside git ('storage': 'shared') must be pinned by sha256 with a url."""
    errs = []
    for a in doc.get("assets", []):
        if a.get("storage") != "shared":
            continue
        files = manifest.get("assets", {}).get(a.get("manifest_key", ""), [])
        if not files:
            errs.append(f"{a['id']}: shared asset has no manifest entry")
        for f in files:
            if not (len(f.get("sha256", "")) == 64 and f.get("url", "").startswith("https://")):
                errs.append(f"{a['id']}: manifest file {f.get('file')} needs a 64-hex sha256 and an https url")
    return errs


def validate_assets(doc: dict, species_slugs, base: Path = DATA) -> list[str]:
    errs, ids = [], set()
    for a in doc.get("assets", []):
        i = a.get("id", "?")
        ids.add(i)
        if a.get("grade") not in GRADES:
            errs.append(f"{i}: grade must be one of {sorted(GRADES)}")
        if a.get("species_fit") not in FITS:
            errs.append(f"{i}: species_fit must be one of {sorted(FITS)}")
        if not a.get("rationale", "").startswith("Looked at:"):
            errs.append(f"{i}: rationale must record the preview look ('Looked at: ...')")
        if not (a.get("source", "").startswith("https://") and a.get("licence")):
            errs.append(f"{i}: source url and licence required")
        if not (base / a.get("preview", "missing")).is_file():
            errs.append(f"{i}: preview file missing")
        if a.get("licence") not in LICENCES:
            errs.append(f"{i}: licence {a.get('licence')!r} is not a free licence ({sorted(LICENCES)})")
        if a.get("untextured_material_share", 0) > 0.5 and a.get("grade") != "D":
            errs.append(f"{i}: untextured material share {a['untextured_material_share']} renders white; grade must be D")
        if a.get("misnamed_as") and (a.get("species_fit") not in ("look-alike", "none") or a.get("maps_to")):
            errs.append(f"{i}: misnamed as {a['misnamed_as']} so it must be look-alike/none and map to nothing")
        if a.get("species_fit") == "look-alike" and a.get("maps_to"):
            errs.append(f"{i}: a look-alike cannot be mapped to a species")
    rows = {r["slug"]: r for r in doc.get("species", [])}
    if set(rows) != set(species_slugs):
        errs.append(f"species rows differ from library: {sorted(set(rows) ^ set(species_slugs))}")
    by_id = {a["id"]: a for a in doc.get("assets", [])}
    for s, r in rows.items():
        b = by_id.get(r.get("best_asset")) if r.get("best_asset") else None
        if r.get("drawable") not in DRAWABLE:
            errs.append(f"{s}: drawable must be one of {sorted(DRAWABLE)}")
        elif r["drawable"] == "drawable" and not (b and b["grade"] in ("A", "B") and b["species_fit"] in ("species", "genus")):
            errs.append(f"{s}: marked drawable without a grade A/B species-or-genus asset")
        elif r["drawable"] == "not drawable yet" and b and b["grade"] in ("A", "B") and b["species_fit"] in ("species", "genus"):
            errs.append(f"{s}: has a grade {b['grade']} asset but is marked not drawable")
        if r.get("best_asset") and not b:
            errs.append(f"{s}: best_asset {r['best_asset']} is not in the asset list")
    return errs


def load_assets(base: Path = DATA) -> dict:
    return json.loads((base / "assets.json").read_text(encoding="utf-8"))
