"""Measured 3D asset intake record and audit of the workstation manifest.

``bounds_m`` is a file measurement in glTF coordinates (Y up). It is not
an intended placement size. An expected range needs its own cited catalogue
or held-book card; no generic range is silently supplied by this module.
"""
from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path
from typing import Callable


REQUIRED = ("id", "role", "source_url", "licence", "author", "credit",
            "units_normalised", "up_axis", "front_axis", "bounds_m",
            "expected_size_range", "contents", "preview_image")
AXES = {"+X", "-X", "+Z", "-Z"}
ALLOWED_LICENCES = {"CC0", "CC0 Public Domain", "CC-BY", "CC Attribution", "free tier"}
BOUNDS_TOLERANCE_M = 0.005


def _valid_size_override(value: object) -> bool:
    if not (isinstance(value, dict) and set(value) == {"reason", "decided_by", "date"}
            and isinstance(value["reason"], str) and bool(value["reason"].strip())
            and value["decided_by"] == "lead"
            and isinstance(value["date"], str)):
        return False
    try:
        date.fromisoformat(value["date"])
        return True
    except ValueError:
        return False

# Asset type is controlled; descriptive placement and species text belongs in `use`.
ROLES = frozenset({
    "sofa", "armchair", "dining-chair", "task-chair", "bed", "bedside-table",
    "rug", "bench-outdoor", "bistro-set", "egg-swing", "task-lamp",
    "shade-tree", "small-tree", "shrub", "climber", "groundcover",
    "ornamental-grass", "indoor-floor-plant", "indoor-table-plant",
    "decor-small", "wall-art", "boulder", "planter", "bedding",
})
INDOOR_PLANTS = {"indoor-floor-plant", "indoor-table-plant"}
GARDEN_PLANTS = {"shade-tree", "small-tree", "shrub", "climber", "groundcover", "ornamental-grass"}
PLANT_ROLES = INDOOR_PLANTS | GARDEN_PLANTS
ASSUMED_ROLES = {"decor-small", "wall-art", "boulder", "planter", "rug",
                 "bistro-set", "egg-swing", "bench-outdoor", "task-lamp", "bedding"}
DIR_ROLES = {"sofa", "armchair", "dining-chair", "task-chair", "bed", "bench-outdoor",
             "bistro-set", "egg-swing", "task-lamp", "wall-art"}
OPTIONALLY_NONDIRECTIONAL = {"bench-outdoor", "bistro-set"}

# Figure 4.3 gives plan dimensions, not height. `None` leaves that axis
# untested. These are preliminary planning ranges, so product sheets may
# replace them for a real named product.
ROLE_SIZE_RANGES: dict[str, dict] = {
    "sofa": {"min_m": [1.83, None, 0.81], "max_m": [2.49, None, 1.12],
             "source": "Mitton & Nystuen, Residential Interior Design, 4th ed., 2022, Fig. 4.3, printed p. 82: sofa plan width 183-249 cm, depth 81-112 cm"},
    "armchair": {"min_m": [0.51, None, 0.61], "max_m": [1.27, None, 1.07],
                 "source": "Mitton & Nystuen, Residential Interior Design, 4th ed., 2022, Fig. 4.3, printed p. 82: chair plan width 51-127 cm, depth 61-107 cm"},
    "dining-chair": {"min_m": [0.51, None, 0.61], "max_m": [1.27, None, 1.07],
                     "source": "Mitton & Nystuen, Residential Interior Design, 4th ed., 2022, Fig. 4.3, printed p. 82: chair plan width 51-127 cm, depth 61-107 cm; preliminary chair footprint"},
}


def role_kind(role: str) -> str:
    if role == "task-lamp":
        return "luminaire"
    if role in INDOOR_PLANTS | GARDEN_PLANTS:
        return "plant"
    if role in DIR_ROLES | {"bedside-table"}:
        return "furniture"
    return "prop"


def directional(role: str) -> bool:
    return role in DIR_ROLES


def _dimensions(bounds: object) -> list[float] | None:
    if not isinstance(bounds, dict):
        return None
    try:
        low, high = bounds["min"], bounds["max"]
        if len(low) != 3 or len(high) != 3:
            return None
        values = [float(b) - float(a) for a, b in zip(low, high)]
        return values if all(math.isfinite(v) and v > 0 for v in values) else None
    except (KeyError, TypeError, ValueError):
        return None


def validate_entry(entry: dict, model_path: Path | None = None,
                   measure: Callable[[Path], dict] | None = None) -> list[str]:
    """Return all known violations; missing evidence never counts as a pass."""
    errors = [f"missing {key}" for key in REQUIRED
              if (key not in entry and not (key == "expected_size_range" and entry.get("role") in ROLE_SIZE_RANGES))
              or (key in entry and (entry[key] in (None, "") or (entry[key] == {} and key != "contents")))]
    role = str(entry.get("role") or "")
    if role and role not in ROLES:
        errors.append(f"unknown role {role!r}")
    if role in PLANT_ROLES and not entry.get("species"):
        errors.append("plant requires species")
    axis = entry.get("front_axis")
    if directional(role):
        if axis == "none" and role in OPTIONALLY_NONDIRECTIONAL and entry.get("front_axis_reason"):
            pass
        elif axis not in AXES:
            errors.append("directional role requires measured or lead-verified front_axis")
    elif axis == "none" and not entry.get("front_axis_reason"):
        errors.append("front_axis none requires a reason")
    elif axis is not None and axis not in AXES | {"none"}:
        errors.append("invalid front_axis")
    if entry.get("up_axis") is not None and entry["up_axis"] not in {"+X", "-X", "+Y", "-Y", "+Z", "-Z"}:
        errors.append("invalid up_axis")
    licence = entry.get("licence")
    if licence is not None and licence not in ALLOWED_LICENCES:
        errors.append(f"licence {licence!r} is not allowed")
    if licence in {"CC-BY", "CC Attribution"} and not entry.get("credit"):
        errors.append("CC-BY requires credit")
    units = entry.get("units_normalised")
    if isinstance(units, dict):
        factor, reason = units.get("scale_factor"), units.get("reason")
        if not isinstance(factor, (int, float)) or isinstance(factor, bool) or not math.isfinite(factor) or factor <= 0 or not reason:
            errors.append("units_normalised needs a positive scale_factor and reason")
    elif units is not None:
        errors.append("units_normalised must record scale_factor and reason")
    dimensions = _dimensions(entry.get("bounds_m"))
    if entry.get("bounds_m") is not None and dimensions is None:
        errors.append("bounds_m must have measured, finite min/max triples")
    expected = entry.get("expected_size_range", ROLE_SIZE_RANGES.get(role))
    size_override = entry.get("size_override")
    if size_override is not None and not _valid_size_override(size_override):
        errors.append("size_override requires reason, decided_by lead and ISO date")
    placed_scale = entry.get("placed_scale")
    if placed_scale is not None and (not isinstance(placed_scale, (int, float)) or isinstance(placed_scale, bool)
                                     or not math.isfinite(placed_scale) or placed_scale <= 0):
        errors.append("placed_scale must be positive and finite")
    placement_scales = entry.get("placement_scale_factors")
    if placement_scales is not None:
        valid_scales = isinstance(placement_scales, list) and bool(placement_scales)
        if valid_scales:
            for scale in placement_scales:
                factors = scale if isinstance(scale, list) else [scale]
                if len(factors) not in (1, 3) or any(
                    not isinstance(v, (int, float)) or isinstance(v, bool)
                    or not math.isfinite(v) or v <= 0 for v in factors
                ):
                    valid_scales = False
                    break
        if not valid_scales:
            errors.append("placement_scale_factors must contain positive scalar or XYZ scales")
    if isinstance(expected, dict):
        low, high, citation = expected.get("min_m"), expected.get("max_m"), expected.get("source")
        assumed = expected.get("basis") == "ASSUMED"
        try:
            valid = (len(low) == len(high) == 3 and (bool(citation) or assumed) and
                     any(a is not None for a in low) and
                     all((a is None and b is None) or
                         (a is not None and b is not None and 0 <= float(a) <= float(b)
                          and math.isfinite(float(b))) for a, b in zip(low, high)))
        except (TypeError, ValueError):
            valid = False
        if not valid:
            errors.append("expected_size_range needs valid min_m, max_m and cited source or allowed assumption")
        if assumed and (role not in ASSUMED_ROLES or not expected.get("reason") or citation):
            errors.append("ASSUMED range requires an allowed role, reason and no citation")
        if role in PLANT_ROLES and (assumed or expected.get("basis") != "species" or not citation):
            errors.append("plant requires cited species range")
        if expected.get("basis") == "product" and not str(citation).startswith(("https://", "http://")):
            errors.append("product dimensions require published source URL")
        elif valid and dimensions and isinstance(units, dict) and isinstance(units.get("scale_factor"), (int, float)) and units["scale_factor"] > 0:
            scales = placement_scales if placement_scales is not None and valid_scales else [placed_scale or 1]
            for scale in scales:
                # The stored vector is Blender XYZ; native glTF is X, Y up, Z.
                native_factors = [scale[0], scale[2], scale[1]] if isinstance(scale, list) else [scale] * 3
                for name, raw, factor, minimum, maximum in zip(("X", "Y", "Z"), dimensions, native_factors, low, high):
                    if minimum is None:
                        continue
                    actual = raw * units["scale_factor"] * factor
                    within_range = (actual <= float(maximum) if role in PLANT_ROLES
                                    else float(minimum) <= actual <= float(maximum))
                    if not within_range and not _valid_size_override(size_override):
                        errors.append(f"bounds_m {name} extent {actual:.4f} m outside {'assumed' if assumed else 'cited'} range {minimum}-{maximum} m")
    elif expected is not None:
        errors.append("expected_size_range must be a cited range")
    contents = entry.get("contents")
    if isinstance(contents, dict):
        if role == "bed" and contents.get("bedding") is not True:
            errors.append("bed requires bedding")
        if role in INDOOR_PLANTS and contents.get("pot") is not True:
            errors.append("indoor plant requires pot")
    elif contents is not None:
        errors.append("contents must be recorded flags")
    if model_path is not None and model_path.is_file():
        preview = entry.get("preview_image")
        if preview:
            relative = Path(str(preview))
            if relative.is_absolute() or ".." in relative.parts or not (model_path.parents[2] / relative).is_file():
                errors.append("preview_image does not exist beside the local library")
        if dimensions is None:
            errors.append("local model exists but recorded bounds are missing or invalid")
        else:
            try:
                measured = (measure or measure_gltf_bounds)(model_path)
                drift = max(abs(float(a) - float(b)) for key in ("min", "max")
                            for a, b in zip(entry["bounds_m"][key], measured[key]))
                if drift > BOUNDS_TOLERANCE_M:
                    errors.append(f"bounds_m disagrees with local file by {drift:.4f} m")
            except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
                errors.append(f"could not re-measure local model: {exc}")
    return errors


def measure_gltf_bounds(path: Path) -> dict:
    """Measure world-space glTF mesh bounds using vertex accessor boxes and node transforms."""
    data = json.loads(path.read_text(encoding="utf-8"))
    lo, hi = [math.inf] * 3, [-math.inf] * 3
    identity = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]

    def multiply(a, b):
        return [sum(a[k * 4 + row] * b[col * 4 + k] for k in range(4))
                for col in range(4) for row in range(4)]

    def visit(index, parent):
        node = data["nodes"][index]
        if "matrix" in node:
            local = node["matrix"]
        else:
            x, y, z, w = node.get("rotation", [0, 0, 0, 1])
            sx, sy, sz = node.get("scale", [1, 1, 1])
            tx, ty, tz = node.get("translation", [0, 0, 0])
            rotation = [1-2*(y*y+z*z), 2*(x*y+z*w), 2*(x*z-y*w), 0,
                        2*(x*y-z*w), 1-2*(x*x+z*z), 2*(y*z+x*w), 0,
                        2*(x*z+y*w), 2*(y*z-x*w), 1-2*(x*x+y*y), 0,
                        0, 0, 0, 1]
            local = [rotation[col*4+row] * (sx, sy, sz)[col] if col < 3 else (tx, ty, tz, 1)[row]
                     for col in range(4) for row in range(4)]
        matrix = multiply(parent, local)
        if "mesh" in node:
            for primitive in data["meshes"][node["mesh"]]["primitives"]:
                accessor = data["accessors"][primitive["attributes"]["POSITION"]]
                for px in accessor["min"][0], accessor["max"][0]:
                    for py in accessor["min"][1], accessor["max"][1]:
                        for pz in accessor["min"][2], accessor["max"][2]:
                            point = (px, py, pz)
                            for row in range(3):
                                value = sum(matrix[col*4+row] * point[col] for col in range(3)) + matrix[12+row]
                                lo[row], hi[row] = min(lo[row], value), max(hi[row], value)
        for child in node.get("children", []):
            visit(child, matrix)

    for root in data["scenes"][data.get("scene", 0)]["nodes"]:
        visit(root, identity)
    if not all(math.isfinite(v) for v in lo + hi):
        raise ValueError("no measured POSITION bounds")
    return {"min": lo, "max": hi}


def validate_manifest(path: Path, local_root: Path | None = None) -> dict[str, list[str]]:
    """Audit 3D props. Materials and environment maps need different evidence."""
    manifest = json.loads(path.read_text(encoding="utf-8"))
    root = local_root or path.resolve().parents[2]
    findings = {}
    for entry in manifest.get("props", []):
        asset_id = entry.get("id", "<missing id>")
        candidates = (root / "out/villa/round3/stage-props" / asset_id / "model.gltf",
                      root / "assets/props" / asset_id / "model.gltf")
        model = next((p for p in candidates if p.is_file()), None)
        errors = validate_entry(entry, model)
        if errors:
            findings[asset_id] = errors
    return findings


def manifest_assumptions(path: Path) -> list[dict]:
    """List every declared size assumption separately from intake failures."""
    manifest = json.loads(path.read_text(encoding="utf-8"))
    return [{"id": entry.get("id"), "role": entry.get("role"),
             "expected_size_range": entry["expected_size_range"]}
            for entry in manifest.get("props", [])
            if isinstance(entry.get("expected_size_range"), dict)
            and entry["expected_size_range"].get("basis") == "ASSUMED"]


def manifest_overrides(path: Path) -> list[dict]:
    """List every deliberate size exception, including invalid ones for audit."""
    manifest = json.loads(path.read_text(encoding="utf-8"))
    return [{"id": entry.get("id"), "size_override": entry["size_override"]}
            for entry in manifest.get("props", []) if "size_override" in entry]


def audit_scene_manifest(path: Path, scene: dict, local_root: Path | None = None) -> dict:
    """Classify manifest props from a built scene and gate only placed assets."""
    manifest = json.loads(path.read_text(encoding="utf-8"))
    entries = {entry["id"]: entry for entry in manifest.get("props", [])}
    instances = scene.get("props", []) + scene.get("models", [])
    placed = {item["asset"] for item in instances}
    findings = validate_manifest(path, local_root)
    for asset_id in placed - entries.keys():
        findings[asset_id] = ["placed asset has no manifest entry"]
    for asset_id in placed & entries.keys():
        recorded = entries[asset_id].get("placed_scale")
        if recorded is not None:
            if not entries[asset_id].get("placed_scale_reason"):
                findings.setdefault(asset_id, []).append("placed_scale requires reason")
            scales = [item.get("scale", 1.0) for item in instances if item["asset"] == asset_id]
            if any(not isinstance(scale, (int, float)) or abs(scale - recorded) > 1e-5 for scale in scales):
                findings.setdefault(asset_id, []).append("placed_scale disagrees with built scene")
        alternatives = entries[asset_id].get("placement_scale_factors")
        if alternatives is not None:
            if not entries[asset_id].get("placement_scale_source"):
                findings.setdefault(asset_id, []).append("placement_scale_factors require code source")
            for item in instances:
                if item["asset"] != asset_id:
                    continue
                actual = item.get("scale", 1.0)
                if not any(
                    isinstance(actual, (int, float)) and isinstance(factor, (int, float))
                    and abs(actual - factor) <= 1e-5
                    or isinstance(actual, (list, tuple)) and isinstance(factor, list)
                    and len(actual) == len(factor) == 3
                    and all(abs(a - b) <= 1e-5 for a, b in zip(actual, factor))
                    for factor in alternatives
                ):
                    findings.setdefault(asset_id, []).append("placement_scale_factors disagree with built scene")
    return {
        "placed": {asset_id: findings[asset_id] for asset_id in sorted(placed) if asset_id in findings},
        "candidates": {asset_id: {"status": "candidate", "violations": findings.get(asset_id, [])}
                       for asset_id in sorted(entries.keys() - placed)},
    }


def require_registered_asset(asset_id: str, manifest_path: Path, model_path: Path | None = None) -> dict:
    """One fail-closed boundary for every scene importer."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    matches = [entry for entry in manifest.get("props", []) if entry.get("id") == asset_id]
    if len(matches) != 1:
        raise ValueError(f"asset {asset_id}: unregistered or duplicate manifest entry")
    entry = matches[0]
    violations = validate_entry(entry, model_path)
    if violations:
        raise ValueError(f"asset {asset_id}: " + "; ".join(violations))
    return entry
