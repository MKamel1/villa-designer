"""Backfill only evidence already present in the manifest or model package.

Run from the repository root. Missing evidence remains missing. Each new value
has a field-specific citation in ``intake_sources``.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "ops/workstation/library-manifest.json"
GLTF_SPEC = "https://github.com/KhronosGroup/glTF/blob/main/specification/2.0/Specification.adoc#34-coordinate-system-and-units"
POLY_LICENCE = "https://polyhaven.com/license"

# Migration of the existing manifest. Keep the old description as `use`;
# future entries must choose a controlled role at authoring time.
ROLE_BY_ID = {
    "book_encyclopedia_set_01": "decor-small", "alarm_clock_01": "decor-small",
    "brass_vase_03": "decor-small", "throw_pillows_01": "bedding",
    "decorative_book_set_01": "decor-small", "wooden_bowl_01": "decor-small",
    "hanging_picture_frame_01": "wall-art", "hanging_picture_frame_02": "wall-art",
    "standing_picture_frame_01": "decor-small", "planter_box_01": "planter",
    "boulder_01": "boulder", "namaqualand_stones_01": "boulder",
    "sf_chelsea_bed": "bed", "sf_cinema_sofa_velvet": "sofa",
    "sf_dining_chair_boucle": "dining-chair", "sf_egg_chair": "egg-swing",
    "sf_kidschair_oak": "task-chair", "sf_minotti_aston_armchair": "armchair",
    "sf_minotti_sofa": "sofa", "sf_modern_low_sofa": "sofa",
    "sf_probber_cane_armchair": "armchair", "sf_rug_round_jute": "rug",
    "sf_wooden_bench": "bench-outdoor", "outdoor_table_chair_set_01": "bistro-set",
    "modern_arm_chair_01": "armchair", "mid_century_lounge_chair": "armchair",
    "desk_lamp_arm_01": "task-lamp",
}


def put(entry: dict, field: str, value, source: str) -> None:
    if value is None or value == "":
        return
    if field not in entry or entry[field] in (None, ""):
        entry[field] = value
        entry.setdefault("intake_sources", {})[field] = source


def model_path(asset_id: str, library: Path | None) -> Path | None:
    candidates = [ROOT / "out/villa/round3/stage-props" / asset_id / "model.gltf"]
    if library:
        candidates.insert(0, library / "props" / asset_id / "model.gltf")
    return next((p for p in candidates if p.is_file()), None)


def contents_from_names(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    names = " ".join(str(item.get("name", "")) for group in ("nodes", "meshes", "materials")
                     for item in data.get(group, [])) .lower()
    tokens = {"bedding": ("duvet", "blanket", "sheet", "quilt", "pillow", "mattress"),
              "pot": ("pot", "planter", "vase"), "root_ball": ("root_ball", "rootball", "roots")}
    return {key: True for key, words in tokens.items() if any(word in names for word in words)}


def poly_author(asset_id: str) -> str | None:
    """Read the publisher's own per-asset author data; network failure adds nothing."""
    url = f"https://api.polyhaven.com/info/{asset_id}"
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "archpipe-asset-intake/1"})
        with urllib.request.urlopen(request, timeout=10) as response:
            info = json.load(response)
        authors = info.get("authors")
        if isinstance(authors, dict):
            names = [str(name).strip() for name in authors if str(name).strip()]
        elif isinstance(authors, list):
            names = [str(a.get("name") if isinstance(a, dict) else a).strip() for a in authors]
        else:
            names = []
        return ", ".join(name for name in names if name) or None
    except (OSError, ValueError, TypeError):
        return None


def backfill_entry(entry: dict, library: Path | None = None, api: bool = False) -> dict:
    e = dict(entry)
    asset_id = e["id"]
    e.setdefault("use", e.get("role", ""))
    if asset_id in ROLE_BY_ID and e.get("role") != ROLE_BY_ID[asset_id]:
        e.setdefault("use", e.get("role"))
        e["role"] = ROLE_BY_ID[asset_id]
    elif e.get("role") not in ROLE_BY_ID.values():
        old = e.get("role", "").lower()
        from archpipe.asset_intake import ROLES
        if old not in ROLES:
            e.setdefault("use", e.get("role"))
            if asset_id.startswith("potted_plant") or old in ("villa: plant", "villa: table plant"):
                e["role"] = "indoor-table-plant"
            elif old in ("floor corner", "villa: floor plant", "villa: large floor plant"):
                e["role"] = "indoor-floor-plant"
            elif "tree" in old:
                e["role"] = "shade-tree" if "shade" in old or "specimen" in old else "small-tree"
            elif "bougainvillea" in old:
                e["role"] = "climber"
            elif "grass" in old:
                e["role"] = "ornamental-grass"
            elif "ground" in old or "flower" in old:
                e["role"] = "groundcover"
            elif "shrub" in old or "lavender" in old:
                e["role"] = "shrub"
            elif any(word in old for word in ("vase", "bowl", "books", "frame", "decorative")):
                e["role"] = "decor-small"
            else:
                raise ValueError(f"no controlled role mapping for {asset_id}: {old}")
    poly = e.get("api") == "polyhaven-model" or str(e.get("url", "")).startswith("https://polyhaven.com/a/")
    if poly:
        put(e, "source_url", e.get("url") or f"https://polyhaven.com/a/{asset_id}",
            "Poly Haven asset page identified by manifest id")
        put(e, "licence", "CC0", POLY_LICENCE)
        put(e, "credit", "Poly Haven", POLY_LICENCE + " (credit optional for CC0)")
        if api and not e.get("author"):
            put(e, "author", poly_author(asset_id), f"https://api.polyhaven.com/info/{asset_id}: authors")
    elif e.get("source") == "sketchfab":
        put(e, "source_url", e.get("url"), "fetch_sketchfab.py API viewerUrl recorded as manifest url")
        for field in ("author", "licence", "credit"):
            if e.get(field):
                e.setdefault("intake_sources", {}).setdefault(field, "fetch_sketchfab.py recorded API metadata")
    put(e, "up_axis", "+Y", GLTF_SPEC + "; Blender glTF import converts (x,y,z) to (x,-z,y), villa_landscape.py")
    if poly:
        put(e, "units_normalised", {"scale_factor": 1.0,
            "reason": "glTF specifies metres; Blender glTF importer uses file coordinates without unit rescale"},
            GLTF_SPEC + "; villa_scene.import_props")
    # Existing furnishing code is the only evidence of a distinct native
    # scale for these assets. Its basis explicitly says inferred/assumed.
    if asset_id == "sf_minotti_sofa" and e.get("bounds_m"):
        width = e["bounds_m"]["max"][0] - e["bounds_m"]["min"][0]
        put(e, "units_normalised", {"scale_factor": 0.01,
            "reason": f"villa_furnish.product applies 0.01, inferred centimetres from {width:.4f} native X units"},
            "src/archpipe/concept/villa_furnish.py:product")
    role = e.get("role", "").lower()
    from archpipe.asset_intake import directional, role_kind
    if not directional(role):
        put(e, "front_axis", "none", "nondirectional role recorded in manifest")
        put(e, "front_axis_reason", "display object has no functional front", "role: " + e.get("role", ""))
    path = model_path(asset_id, library)
    if path:
        flags = contents_from_names(path)
        if flags:
            put(e, "contents", flags, str(path) + ": node, mesh and material names")
    if e.get("role") not in ("bed", "indoor-floor-plant", "indoor-table-plant"):
        e.setdefault("contents", {})
    return e


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    api = "--api" in argv
    argv = [arg for arg in argv if arg != "--api"]
    library = Path(argv[0]) if argv else None
    sys.path.insert(0, str(ROOT / "src"))
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    data["props"] = [backfill_entry(p, library, api=api) for p in data["props"]]
    MANIFEST.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for p in data["props"]:
        missing = [key for key in ("source_url", "licence", "author", "credit", "units_normalised", "up_axis",
                                    "front_axis", "bounds_m", "expected_size_range", "contents", "preview_image")
                   if key not in p]
        print(p["id"] + ": " + (", ".join(missing) or "complete"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
