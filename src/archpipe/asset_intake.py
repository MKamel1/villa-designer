"""Measured 3D asset intake record and audit of the workstation manifest.

``bounds_m`` is a file measurement in glTF coordinates (Y up). It is not
an intended placement size. An expected range needs its own cited catalogue
or held-book card; no generic range is silently supplied by this module.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Callable


REQUIRED = ("id", "role", "source_url", "licence", "author", "credit",
            "units_normalised", "up_axis", "front_axis", "bounds_m",
            "expected_size_range", "contents", "preview_image")
AXES = {"+X", "-X", "+Z", "-Z"}
ALLOWED_LICENCES = {"CC0", "CC0 Public Domain", "CC-BY", "CC Attribution", "free tier"}
BOUNDS_TOLERANCE_M = 0.005


def role_kind(role: str) -> str:
    role = role.lower()
    if any(word in role for word in ("lamp", "luminaire", "pendant", "sconce")):
        return "luminaire"
    if any(word in role for word in ("tree", "plant", "shrub", "flower", "grass", "succulent", "groundcover", "ground cover")):
        return "plant"
    if re.search(r"\b(bed|sofa|chair|armchair|seat|bench|desk|table|stool)s?\b", role):
        return "furniture"
    return "prop"


def directional(role: str) -> bool:
    role = role.lower()
    if role_kind(role) == "plant":
        return False
    return bool(re.search(r"\b(bed|sofa|chair|armchair|seat|bench|desk|swing|lamp|luminaire)s?\b", role)
                and not re.search(r"books|cushions|bedside table", role))


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
              if key not in entry or entry[key] in (None, "") or (entry[key] == {} and key != "contents")]
    role = str(entry.get("role") or "")
    axis = entry.get("front_axis")
    if directional(role):
        if axis not in AXES:
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
    expected = entry.get("expected_size_range")
    if isinstance(expected, dict):
        low, high, citation = expected.get("min_m"), expected.get("max_m"), expected.get("source")
        try:
            valid = (len(low) == len(high) == 3 and bool(citation) and
                     all(0 <= float(a) <= float(b) and math.isfinite(float(b)) for a, b in zip(low, high)))
        except (TypeError, ValueError):
            valid = False
        if not valid:
            errors.append("expected_size_range needs min_m, max_m and cited source")
        elif dimensions and isinstance(units, dict) and isinstance(units.get("scale_factor"), (int, float)) and units["scale_factor"] > 0:
            for name, raw, minimum, maximum in zip(("X", "Y", "Z"), dimensions, low, high):
                actual = raw * units["scale_factor"]
                if not float(minimum) <= actual <= float(maximum):
                    errors.append(f"bounds_m {name} extent {actual:.4f} m outside cited range {minimum}-{maximum} m")
    elif expected is not None:
        errors.append("expected_size_range must be a cited range")
    contents = entry.get("contents")
    if isinstance(contents, dict):
        if re.search(r"\bbed\b", role.lower()) and not re.search(r"cushions|for the bed", role.lower()) and contents.get("bedding") is not True:
            errors.append("bed requires bedding")
        if role_kind(role) == "plant" and not (contents.get("pot") is True or contents.get("root_ball") is True):
            errors.append("plant requires pot or root_ball")
    elif contents is not None:
        errors.append("contents must be recorded flags")
    if model_path is not None and model_path.is_file():
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
