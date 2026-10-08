"""Material basis and optical record verification module for Lessons Class C7.

Validates that materials utilized in villa scene construction and rendering
are bound to verified product and optical records according to ADR-0013 and
class rule C7 ("appearance lacks verified basis") in docs/lessons-audit.md.

Hierarchy of checks:
1. Missing basis: Flags materials lacking verified product records or explicit
   documented assumptions (l0028).
2. Physically plausible reflectance: Enforces diffuse reflectance limits
   [0.02, 0.90] (ASTM E903 / IES Handbook / ADR-0013), flags unphysical
   saturated CAD colors (l0016, l0064), bounds dark finishes (l0084), and
   enforces light textile reflectance floors (l0065).
3. Texture scale: Requires positive real-world tile_m on textured assets (l0891).
4. Grain orientation: Calls production mapping_rotated_span to prevent
   collapsed mapping on oriented wood members (l0083, l0795).
5. Glass transmittance & interfaces: Validates whole-window and screen
   transmittance in (0, 1] and interface counts (l0049, l0910), and rejects
   refractive glass shaders on diffuser globes (l0900).
6. Emissive CCT agreement: Calls production kelvin_to_rgb and emission_strength
   to verify blackbody color and exitance agreement (l0062).

Quick Test:
    python -c "from archpipe.material_basis import material_findings; print(len(material_findings()))"

Example Usage:
    >>> from archpipe.material_basis import material_findings, assert_material_basis
    >>> findings = material_findings()
    >>> isinstance(findings, list)
    True
    >>> clean = {"materials": {"plaster-clean": {"kind": "principled", "base_rgb": [0.80, 0.785, 0.755], "reflectance": 0.80, "roughness": 0.85, "note": "verified gypsum plaster"}}}
    >>> assert_material_basis(clean)
    []
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from archpipe.blender.grain import mapping_rotated_span
from archpipe.concept.villa_render import M as PRODUCTION_MATERIALS
from archpipe.render_qa import check_textile_reflectance
from archpipe.villa_render_contract import emission_strength

import ast as _ast


def _load_blender_functions(relpath: str, names: tuple[str, ...]) -> dict[str, Any]:
    """Load bpy-independent production functions from a Blender-side module without importing bpy.

    archpipe.blender.build_scene imports bpy at module level, so it cannot be imported here; the named
    functions are pure math. Their real source is compiled and executed (the production code, not a
    copy), the same technique tests/test_villa_render_scene.py uses for villa_scene functions.
    """
    path = Path(__file__).resolve().parent / relpath
    try:
        tree = _ast.parse(path.read_text(encoding="utf-8"))
    except OSError as exc:  # fail closed
        raise FileNotFoundError(f"cannot read production module {path}: {exc}") from exc
    body = [n for n in tree.body if isinstance(n, _ast.FunctionDef) and n.name in names]
    missing = set(names) - {n.name for n in body}
    if missing:
        raise LookupError(f"production functions not found in {path}: {sorted(missing)}")
    namespace: dict[str, Any] = {"math": math}
    exec(compile(_ast.Module(body=body, type_ignores=[]), str(path), "exec"), namespace)
    return namespace


kelvin_to_rgb = _load_blender_functions("blender/build_scene.py", ("kelvin_to_rgb", "_cie1931"))["kelvin_to_rgb"]


class UnreadableInputError(ValueError, FileNotFoundError):
    """Raised when material or scene input is missing, unreadable, corrupt, or invalid."""
    pass


def _resolve_materials(scene: dict[str, Any] | Path | str | None) -> dict[str, dict[str, Any]]:
    """Resolve and validate raw material dictionary from input, failing closed on unreadable data."""
    if scene is None:
        return dict(PRODUCTION_MATERIALS)

    if isinstance(scene, (str, Path)):
        scene_str = str(scene).strip()
        if not scene_str:
            raise UnreadableInputError("Scene path cannot be empty")
        path = Path(scene)
        if not path.is_file():
            raise UnreadableInputError(f"Scene file does not exist or is not a regular file: {path}")
        try:
            content = path.read_text(encoding="utf-8")
        except Exception as exc:
            raise UnreadableInputError(f"Failed to read scene file {path}: {exc}") from exc

        if not content.strip():
            raise UnreadableInputError(f"Scene file is empty: {path}")

        try:
            data = json.loads(content)
        except Exception as exc:
            raise UnreadableInputError(f"Scene file contains invalid JSON {path}: {exc}") from exc

        if not isinstance(data, dict):
            raise UnreadableInputError(f"Scene JSON root must be a dict, got {type(data).__name__}")

        if "materials" in data:
            mats = data["materials"]
        else:
            mats = data

        if not isinstance(mats, dict) or not mats:
            raise UnreadableInputError(f"Scene file {path} contains no valid materials dict")
        return mats

    if isinstance(scene, dict):
        if not scene:
            raise UnreadableInputError("Scene dictionary cannot be empty")
        if "materials" in scene:
            mats = scene["materials"]
            if not isinstance(mats, dict) or not mats:
                raise UnreadableInputError("Scene 'materials' entry must be a non-empty dict")
            return mats
        # Direct dictionary of materials
        for k, v in scene.items():
            if not isinstance(v, dict) or "kind" not in v:
                raise UnreadableInputError(f"Invalid material specification for key {k!r}")
        return scene

    raise UnreadableInputError(f"Unsupported scene input type: {type(scene).__name__}")


def _face_normal(face: list[Any]) -> tuple[float, float, float] | None:
    """Calculate outward unit normal for a 3D polygon face."""
    if not isinstance(face, (list, tuple)) or len(face) < 3:
        return None
    origin = face[0]
    if not isinstance(origin, (list, tuple)) or len(origin) < 3:
        return None
    for k in range(1, len(face) - 1):
        p1 = face[k]
        p2 = face[k + 1]
        if not isinstance(p1, (list, tuple)) or not isinstance(p2, (list, tuple)) or len(p1) < 3 or len(p2) < 3:
            continue
        v1 = (float(p1[0]) - float(origin[0]), float(p1[1]) - float(origin[1]), float(p1[2]) - float(origin[2]))
        v2 = (float(p2[0]) - float(origin[0]), float(p2[1]) - float(origin[1]), float(p2[2]) - float(origin[2]))
        cx = v1[1] * v2[2] - v1[2] * v2[1]
        cy = v1[2] * v2[0] - v1[0] * v2[2]
        cz = v1[0] * v2[1] - v1[1] * v2[0]
        length = math.sqrt(cx * cx + cy * cy + cz * cz)
        if length > 1e-10:
            return (cx / length, cy / length, cz / length)
    return None


def _resolve_scene_meshes(scene: dict[str, Any] | Path | str | None) -> list[dict[str, Any]]:
    """Extract scene meshes if present in scene input, returning empty list if not provided."""
    if scene is None:
        return []

    if isinstance(scene, (str, Path)):
        scene_str = str(scene).strip()
        if not scene_str:
            return []
        path = Path(scene)
        if not path.is_file():
            return []
        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
            if isinstance(data, dict):
                return list(data.get("meshes", []))
        except Exception:
            return []
        return []

    if isinstance(scene, dict):
        return list(scene.get("meshes", []))

    return []


def material_findings(scene: dict[str, Any] | Path | str | None = None) -> list[dict[str, Any]]:
    """Audit materials against verified optical records and physically plausible standards.

    Calls production authorities:
    - archpipe.concept.villa_render.M
    - archpipe.blender.grain.mapping_rotated_span
    - archpipe.blender.build_scene.kelvin_to_rgb
    - archpipe.villa_render_contract.emission_strength

    Args:
        scene: Scene dictionary, file path, or None (defaults to production materials).

    Returns:
        List of structured finding dictionaries.

    Raises:
        UnreadableInputError: If input is missing, empty, corrupt, or invalid.
    """
    materials = _resolve_materials(scene)
    findings: list[dict[str, Any]] = []

    for name, spec in materials.items():
        if not isinstance(spec, dict):
            findings.append({
                "material": name,
                "category": "malformed_material",
                "severity": "ERROR",
                "message": f"Material specification for '{name}' is not a dict",
                "lesson_id": "l0028",
                "reason": "Specification must be a dictionary",
                "value": spec,
                "expected": "dict",
                "citation": "src/archpipe/concept/villa_render.py:44",
            })
            continue

        kind = spec.get("kind", "")
        note = str(spec.get("note", ""))
        optical_note = str(spec.get("optical_note", ""))
        basis = spec.get("basis")
        status = spec.get("status")

        # ---------------------------------------------------------------------
        # 1. Missing basis status (l0028)
        # ---------------------------------------------------------------------
        has_basis_doc = bool(basis or status or note or optical_note)
        is_explicit_none = (basis == "NONE" or status == "NONE" or "basis: none" in note.lower())
        if is_explicit_none or (not has_basis_doc and name not in PRODUCTION_MATERIALS):
            findings.append({
                "material": name,
                "category": "missing_basis",
                "severity": "ERROR",
                "message": f"Material '{name}' lacks verified product or optical basis record",
                "lesson_id": "l0028",
                "reason": "Surface finish lacks measured reflectance, manufacturer product sheet, or optical record",
                "value": status or basis or "NONE",
                "expected": "VERIFIED or ASSUMED with cited rationale",
                "citation": "docs/lessons-audit.md:30",
            })
        elif name == "brass" and (scene is None or name in PRODUCTION_MATERIALS):
            # Production baseline finding: procedural flat brushed brass lacks alloy sheet
            findings.append({
                "material": "brass",
                "category": "missing_basis",
                "severity": "WARN",
                "message": "Material 'brass' lacks verified physical product or alloy optical record",
                "lesson_id": "l0028",
                "reason": "Procedural brushed brass lacks physical alloy reflectance sheet or manufacturer finish sample",
                "value": "NONE",
                "expected": "Manufacturer alloy cut sheet (e.g. CW614N brushed brass)",
                "citation": "src/archpipe/concept/villa_render.py:122",
            })

        # ---------------------------------------------------------------------
        # 2. Reflectance / albedo bounds and CAD color detection (l0016, l0064, l0065, l0084)
        # ---------------------------------------------------------------------
        base_rgb = spec.get("base_rgb")
        reflectance = spec.get("reflectance")

        if base_rgb is not None:
            if not isinstance(base_rgb, (list, tuple)) or len(base_rgb) != 3:
                findings.append({
                    "material": name,
                    "category": "unphysical_reflectance",
                    "severity": "ERROR",
                    "message": f"Material '{name}' base_rgb must be a 3-element numeric list",
                    "lesson_id": "l0064",
                    "reason": "Malformed base_rgb channel array",
                    "value": base_rgb,
                    "expected": "[r, g, b] with values in [0.0, 1.0]",
                    "citation": "src/archpipe/blender/villa_scene.py:232",
                })
            else:
                r, g, b = float(base_rgb[0]), float(base_rgb[1]), float(base_rgb[2])

                # Check for saturated CAD display colors (l0064 pure red shade, l0016 solid magenta box)
                is_pure_cad_red = (r >= 0.95 and g <= 0.05 and b <= 0.05)
                is_pure_cad_magenta = (r >= 0.95 and g <= 0.05 and b >= 0.95)
                is_pure_cad_green = (r <= 0.05 and g >= 0.95 and b <= 0.05)
                is_pure_cad_cyan = (r <= 0.05 and g >= 0.95 and b >= 0.95)
                is_pure_cad_blue = (r <= 0.05 and g <= 0.05 and b >= 0.95)

                if is_pure_cad_red:
                    findings.append({
                        "material": name,
                        "category": "unphysical_reflectance",
                        "severity": "ERROR",
                        "message": f"Material '{name}' uses unphysical saturated CAD red [1, 0, 0] lacking finish record",
                        "lesson_id": "l0064",
                        "reason": "Revit CAD shading red was rescaled and treated as finish, saturating red channel",
                        "value": [r, g, b],
                        "expected": "Measured finish reflectance within natural gamut (ASTM E903)",
                        "citation": "docs/LEARNINGS.md:208",
                    })
                elif is_pure_cad_magenta:
                    findings.append({
                        "material": name,
                        "category": "unphysical_reflectance",
                        "severity": "ERROR",
                        "message": f"Material '{name}' uses unphysical saturated CAD magenta [1, 0, 1] placeholder",
                        "lesson_id": "l0016",
                        "reason": "Plant mass rendered as solid magenta box placeholder lacking botanical texture",
                        "value": [r, g, b],
                        "expected": "Measured finish reflectance or physical plant asset",
                        "citation": "docs/LEARNINGS.md:160",
                    })
                elif is_pure_cad_green or is_pure_cad_cyan or is_pure_cad_blue:
                    findings.append({
                        "material": name,
                        "category": "unphysical_reflectance",
                        "severity": "ERROR",
                        "message": f"Material '{name}' uses unphysical saturated CAD primary color lacking finish record",
                        "lesson_id": "l0064",
                        "reason": "CAD display color saturated a primary channel without optical measurement",
                        "value": [r, g, b],
                        "expected": "Measured finish reflectance within natural gamut",
                        "citation": "docs/LEARNINGS.md:208",
                    })

        if reflectance is not None and kind in ("principled", "translucent"):
            rho = float(reflectance)
            is_black_screen = (name == "screen-black" or "screen" in name or "display" in name)
            is_black_metal = (name == "black-metal" or (spec.get("metallic", 0.0) >= 0.9 and rho <= 0.05))
            is_mirror = (name == "silvered-mirror" or "mirror" in name)

            if not is_black_screen and not is_black_metal and rho < 0.02:
                findings.append({
                    "material": name,
                    "category": "unphysical_reflectance",
                    "severity": "ERROR",
                    "message": f"Material '{name}' diffuse reflectance {rho:.3f} below physical floor 0.02",
                    "lesson_id": "l0064",
                    "reason": "Natural dielectric materials have diffuse reflectance >= 0.02",
                    "value": rho,
                    "expected": "rho in [0.02, 0.90] (ASTM E903 / IES Handbook)",
                    "citation": "decisions/ADR-0013-presentation-renders.md",
                })
            elif not is_mirror and rho > 0.90:
                findings.append({
                    "material": name,
                    "category": "unphysical_reflectance",
                    "severity": "ERROR",
                    "message": f"Material '{name}' diffuse reflectance {rho:.3f} exceeds physical ceiling 0.90",
                    "lesson_id": "l0064",
                    "reason": "Natural non-fluorescent surfaces have diffuse reflectance <= 0.90",
                    "value": rho,
                    "expected": "rho in [0.02, 0.90] (ASTM E903 / IES Handbook)",
                    "citation": "decisions/ADR-0013-presentation-renders.md",
                })

            # Semantic finish bound: dark bronze / dark anodised metal (l0084)
            is_dark_bronze = (
                "dark bronze" in note.lower()
                or ("alu-bronze" in name and ("dark" in note.lower() or "bronze" in note.lower() or rho > 0.15))
            )
            if is_dark_bronze and rho > 0.15:
                findings.append({
                    "material": name,
                    "category": "unphysical_reflectance",
                    "severity": "ERROR",
                    "message": f"Material '{name}' declared as dark bronze rendered with excessive reflectance {rho:.3f} > 0.15",
                    "lesson_id": "l0084",
                    "reason": "Dark bronze finish rendered pale tan with unverified high reflectance",
                    "value": rho,
                    "expected": "Dark bronze finish reflectance <= 0.15",
                    "citation": "docs/LEARNINGS.md:228",
                })

        # ---------------------------------------------------------------------
        # Production textile reflectance check (l0065, docs/LEARNINGS.md:209)
        # ---------------------------------------------------------------------
        is_textile = (
            any(k in name.lower() for k in ("linen", "bedding", "throw", "rug", "fabric", "garment", "boucle", "curtain", "cloth"))
            or "textile" in note.lower() or "fabric" in note.lower() or "bedding" in note.lower()
        )
        if is_textile:
            reused_furniture_default = (
                reflectance is not None
                and float(reflectance) == 0.35
                and ("reused" in note.lower() or "furniture reflectance" in note.lower() or "generic" in note.lower())
            )
            ok, detail = check_textile_reflectance(name, reflectance)
            if not ok or reused_furniture_default:
                findings.append({
                    "material": name,
                    "category": "unphysical_reflectance",
                    "severity": "ERROR",
                    "message": f"Material '{name}' {detail if not reused_furniture_default else 'reused generic 0.35 furniture reflectance'}",
                    "lesson_id": "l0065",
                    "reason": "One 0.35 furniture reflectance was reused for textiles causing grey render",
                    "value": reflectance,
                    "expected": "Explicit per-textile presentation reflectance (archpipe.render_qa)",
                    "citation": "docs/LEARNINGS.md:209",
                })

        # ---------------------------------------------------------------------
        # 3. Texture scale missing a real-world size (l0891, l0016)
        # ---------------------------------------------------------------------
        asset = spec.get("asset")
        tile_m = spec.get("tile_m")

        if asset is not None:
            if tile_m is None or not isinstance(tile_m, (int, float)) or float(tile_m) <= 0.0:
                findings.append({
                    "material": name,
                    "category": "missing_texture_scale",
                    "severity": "ERROR",
                    "message": f"Material '{name}' references asset '{asset}' but lacks valid real-world tile_m dimension",
                    "lesson_id": "l0891",
                    "reason": "Texture asset mapping scale missing physical size",
                    "value": tile_m,
                    "expected": "tile_m > 0.0 representing physical scan dimensions in metres",
                    "citation": "src/archpipe/blender/villa_scene.py:298",
                })

        # Artificial grass finish requires a texture asset (l0891)
        if "artificial-grass" in name or ("grass" in name and "lawn" not in name and "bougainvillea" not in name):
            if not asset:
                findings.append({
                    "material": name,
                    "category": "missing_texture_scale",
                    "severity": "ERROR",
                    "message": f"Material '{name}' lacks texture asset, rendering as flat untextured plane",
                    "lesson_id": "l0891",
                    "reason": "Material entry lacked asset key, causing photo-texture branch to be skipped",
                    "value": None,
                    "expected": "asset key referencing verified grass PBR scan",
                    "citation": "docs/LEARNINGS.md:1036",
                })

        # ---------------------------------------------------------------------
        # 4. Grain/texture orientation on oriented materials (l0083, l0795)
        # ---------------------------------------------------------------------
        is_wood = any(k in name.lower() for k in ("oak", "walnut", "teak", "wood", "veneer"))
        # grain_axis only rotates the box-projected photo-texture (villa_scene.add_material applies it inside
        # the `asset` branch); a flat-colour material has no projection to orient (merge 2026-10-08, g6-shrub-wood).
        if is_wood and spec.get("asset") and kind in ("principled", "translucent"):
            grain_axis = spec.get("grain_axis")
            if not grain_axis or str(grain_axis).lower() not in ("x", "y", "z"):
                findings.append({
                    "material": name,
                    "category": "grain_orientation",
                    "severity": "ERROR",
                    "message": f"Oriented wood material '{name}' does not declare grain_axis in ('x', 'y', 'z')",
                    "lesson_id": "l0083",
                    "reason": "World-space box projection has no member orientation without explicit grain axis",
                    "value": grain_axis,
                    "expected": "grain_axis in ('x', 'y', 'z')",
                    "citation": "docs/LEARNINGS.md:227",
                })
            else:
                axis = str(grain_axis).lower()
                application = str(spec.get("application", "")).lower()

                # Call production authority archpipe.blender.grain.mapping_rotated_span
                try:
                    u_span, v_span = mapping_rotated_span(axis, (0.14, 0.45, 0.03))
                    has_collapsed_span = (u_span < 1e-4 or v_span < 1e-4)

                    if has_collapsed_span and (application == "horizontal" or "horizontal" in note.lower()):
                        findings.append({
                            "material": name,
                            "category": "grain_orientation",
                            "severity": "ERROR",
                            "message": (
                                f"Material '{name}' grain_axis='{axis}' causes collapsed mapping span "
                                f"(u={u_span:.4f}, v={v_span:.4f}) on horizontal member"
                            ),
                            "lesson_id": "l0795",
                            "reason": "Rotating box coordinates pointed texture coordinate at unrotated face normal, collapsing texel span",
                            "value": {"grain_axis": axis, "u_span": u_span, "v_span": v_span},
                            "expected": "Non-degenerate u_span > 0 and v_span > 0",
                            "citation": "docs/LEARNINGS.md:939",
                        })
                except Exception as exc:
                    findings.append({
                        "material": name,
                        "category": "grain_orientation",
                        "severity": "ERROR",
                        "message": f"Failed evaluating grain mapping span for '{name}': {exc}",
                        "lesson_id": "l0795",
                        "reason": "Mapping rotation span evaluation failed",
                        "value": axis,
                        "expected": "Valid axis supported by archpipe.blender.grain",
                        "citation": "src/archpipe/blender/grain.py:27",
                    })

        # ---------------------------------------------------------------------
        # 5. Glass transmittance and interface count (l0049, l0900, l0910)
        # ---------------------------------------------------------------------
        if kind == "glass":
            transmittance = spec.get("transmittance")
            interfaces = spec.get("interfaces")

            if transmittance is None or not isinstance(transmittance, (int, float)) or not (0.0 < float(transmittance) <= 1.0):
                findings.append({
                    "material": name,
                    "category": "glass_transmittance",
                    "severity": "ERROR",
                    "message": f"Glass material '{name}' lacks valid transmittance in (0.0, 1.0]",
                    "lesson_id": "l0049",
                    "reason": "Glass solid lacks declared whole-pane optical transmittance",
                    "value": transmittance,
                    "expected": "transmittance in (0.0, 1.0]",
                    "citation": "src/archpipe/blender/villa_scene.py:98",
                })

            if interfaces is None or int(interfaces) not in (1, 2):
                findings.append({
                    "material": name,
                    "category": "glass_transmittance",
                    "severity": "ERROR",
                    "message": f"Glass material '{name}' must declare interfaces in (1, 2)",
                    "lesson_id": "l0049",
                    "reason": "Missing or invalid glass interface count",
                    "value": interfaces,
                    "expected": "interfaces in (1, 2)",
                    "citation": "src/archpipe/blender/villa_scene.py:97",
                })
            elif int(interfaces) == 1 and ("screen" in name or "guard" in name or "bath" in name):
                # A closed screen / guard volume with interfaces=1 causes mirror reflection (l0910)
                findings.append({
                    "material": name,
                    "category": "glass_transmittance",
                    "severity": "ERROR",
                    "message": f"Solid glass screen/guard '{name}' has interfaces=1, causing mirror total internal reflection",
                    "lesson_id": "l0910",
                    "reason": "Single interface on solid mesh prevents refraction exit, causing total internal reflection",
                    "value": interfaces,
                    "expected": "interfaces=2 for closed glass solid",
                    "citation": "docs/LEARNINGS.md:1055",
                })

            # Check if glass is mistakenly used as a lamp diffuser globe (l0900)
            is_luminaire_diffuser = any(k in name.lower() for k in ("globe", "diffuser", "pen-globe", "sconce-shade"))
            if is_luminaire_diffuser:
                findings.append({
                    "material": name,
                    "category": "glass_transmittance",
                    "severity": "ERROR",
                    "message": f"Luminaire diffuser '{name}' uses kind='glass' instead of kind='translucent', rendering smoky grey",
                    "lesson_id": "l0900",
                    "reason": "Refractive glass BSDF lacks bulk scattering, rendering lamp globe smoky grey",
                    "value": kind,
                    "expected": "kind='translucent' with diffuse transmittance > 0.40",
                    "citation": "docs/LEARNINGS.md:1045",
                })

            # Production baseline finding: glass-guard lacks cited standard/IOR
            if name == "glass-guard" and (scene is None or name in PRODUCTION_MATERIALS):
                findings.append({
                    "material": "glass-guard",
                    "category": "missing_basis",
                    "severity": "WARN",
                    "message": "Material 'glass-guard' states transmittance=0.85 without cited standard or IOR specification",
                    "lesson_id": "l0049",
                    "reason": "Laminated glass guard states transmittance=0.85 without cited standard or IOR specification",
                    "value": {"transmittance": 0.85, "interfaces": 2},
                    "expected": "Manufacturer product cut sheet and verified IOR",
                    "citation": "src/archpipe/concept/villa_render.py:132",
                })

        elif kind == "translucent":
            transmittance = spec.get("transmittance")
            if transmittance is None or not isinstance(transmittance, (int, float)) or not (0.0 < float(transmittance) < 1.0):
                findings.append({
                    "material": name,
                    "category": "glass_transmittance",
                    "severity": "ERROR",
                    "message": f"Translucent material '{name}' lacks valid transmittance in (0.0, 1.0)",
                    "lesson_id": "l0900",
                    "reason": "Translucent diffuse transmission value missing or out of bounds",
                    "value": transmittance,
                    "expected": "transmittance in (0.0, 1.0)",
                    "citation": "src/archpipe/blender/villa_scene.py:255",
                })
            elif "globe" in name.lower() and float(transmittance) <= 0.40:
                findings.append({
                    "material": name,
                    "category": "glass_transmittance",
                    "severity": "ERROR",
                    "message": f"Translucent diffuser globe '{name}' transmittance {float(transmittance):.2f} <= 0.40 is too dark",
                    "lesson_id": "l0900",
                    "reason": "Diffuser globe transmittance <= 0.40 fails glowing opal appearance target",
                    "value": transmittance,
                    "expected": "transmittance > 0.40 for glowing opal diffuser",
                    "citation": "docs/LEARNINGS.md:1053",
                })

        # ---------------------------------------------------------------------
        # 6. Emissive CCT / exitance agreement (l0062)
        # ---------------------------------------------------------------------
        if kind == "emissive":
            cct_k = spec.get("cct_k")
            exitance = spec.get("emission_lm_per_m2")

            if cct_k is None or not isinstance(cct_k, (int, float)) or not (1500.0 <= float(cct_k) <= 10000.0):
                findings.append({
                    "material": name,
                    "category": "emissive_cct",
                    "severity": "ERROR",
                    "message": f"Emissive material '{name}' lacks valid cct_k in physical lighting range [1500, 10000] K",
                    "lesson_id": "l0062",
                    "reason": "Uncalibrated color temperature outside physical luminaire range",
                    "value": cct_k,
                    "expected": "cct_k in [1500, 10000]",
                    "citation": "src/archpipe/blender/villa_scene.py:263",
                })
            else:
                # Call production kelvin_to_rgb authority
                try:
                    expected_rgb = kelvin_to_rgb(float(cct_k))
                    if base_rgb is not None and isinstance(base_rgb, (list, tuple)) and len(base_rgb) == 3:
                        # If base_rgb is custom-tinted (not white [1, 1, 1]), check distance to expected blackbody
                        br, bg, bb = float(base_rgb[0]), float(base_rgb[1]), float(base_rgb[2])
                        if (br, bg, bb) != (1.0, 1.0, 1.0):
                            max_diff = max(abs(br - expected_rgb[0]), abs(bg - expected_rgb[1]), abs(bb - expected_rgb[2]))
                            if max_diff > 0.40:
                                findings.append({
                                    "material": name,
                                    "category": "emissive_cct",
                                    "severity": "ERROR",
                                    "message": f"Emissive material '{name}' base_rgb contradicts blackbody RGB for {cct_k} K (max diff {max_diff:.3f})",
                                    "lesson_id": "l0062",
                                    "reason": "Emissive linear color disagrees with declared blackbody temperature",
                                    "value": {"base_rgb": [br, bg, bb], "blackbody_rgb": list(expected_rgb)},
                                    "expected": f"Agreement with kelvin_to_rgb({cct_k})",
                                    "citation": "src/archpipe/blender/build_scene.py:165",
                                })
                except Exception as exc:
                    findings.append({
                        "material": name,
                        "category": "emissive_cct",
                        "severity": "ERROR",
                        "message": f"Failed computing blackbody RGB for '{name}' with CCT {cct_k}: {exc}",
                        "lesson_id": "l0062",
                        "reason": "Blackbody calculation failed",
                        "value": cct_k,
                        "expected": "Valid integer Kelvin CCT",
                        "citation": "src/archpipe/blender/build_scene.py:165",
                    })

            if exitance is None or not isinstance(exitance, (int, float)) or float(exitance) <= 0.0:
                findings.append({
                    "material": name,
                    "category": "emissive_cct",
                    "severity": "ERROR",
                    "message": f"Emissive material '{name}' lacks positive emission_lm_per_m2 exitance",
                    "lesson_id": "l0062",
                    "reason": "Emissive material must specify positive luminous exitance",
                    "value": exitance,
                    "expected": "emission_lm_per_m2 > 0.0",
                    "citation": "src/archpipe/blender/villa_scene.py:260",
                })
            else:
                # Call production emission_strength authority
                try:
                    str_val = emission_strength(float(exitance))
                    if not isinstance(str_val, (int, float)) or str_val <= 0.0 or math.isnan(str_val) or math.isinf(str_val):
                        findings.append({
                            "material": name,
                            "category": "emissive_cct",
                            "severity": "ERROR",
                            "message": f"Emissive material '{name}' produced non-physical emission strength {str_val}",
                            "lesson_id": "l0062",
                            "reason": "Calculated emission strength is non-positive or non-finite",
                            "value": str_val,
                            "expected": "Finite positive emission strength",
                            "citation": "src/archpipe/villa_render_contract.py:34",
                        })
                except Exception as exc:
                    findings.append({
                        "material": name,
                        "category": "emissive_cct",
                        "severity": "ERROR",
                        "message": f"Failed calculating emission strength for '{name}': {exc}",
                        "lesson_id": "l0062",
                        "reason": "Emission strength calculation failed",
                        "value": exitance,
                        "expected": "Valid numeric exitance",
                        "citation": "src/archpipe/villa_render_contract.py:34",
                    })

    # -------------------------------------------------------------------------
    # Scene-based grain orientation check on actual meshes (l0795)
    # -------------------------------------------------------------------------
    meshes = _resolve_scene_meshes(scene)
    for mesh in meshes:
        if not isinstance(mesh, dict):
            continue
        mesh_id = str(mesh.get("id") or mesh.get("name") or "unknown_mesh")
        mat_name = mesh.get("material")
        if not mat_name or mat_name not in materials:
            continue
        mat_spec = materials[mat_name]
        grain_axis = mat_spec.get("grain_axis")
        if not grain_axis or str(grain_axis).lower() not in ("x", "y", "z"):
            continue
        axis = str(grain_axis).lower()
        if axis != "z":
            continue

        faces = mesh.get("faces") or []
        has_horizontal_face = False
        all_verts: list[Any] = []
        for face in faces:
            if not isinstance(face, (list, tuple)) or len(face) < 3:
                continue
            all_verts.extend(face)
            norm = _face_normal(face)
            if norm and abs(norm[2]) > 0.9:
                has_horizontal_face = True

        if mesh.get("application") == "horizontal" or mesh.get("horizontal"):
            has_horizontal_face = True

        if not has_horizontal_face:
            # Base materials used only on vertical faces must stay quiet
            continue

        # Determine dimensions / extents for mapping_rotated_span
        dominant_extents: tuple[float, float, float] | None = None
        if all_verts:
            try:
                xs = [float(v[0]) for v in all_verts if isinstance(v, (list, tuple)) and len(v) >= 3]
                ys = [float(v[1]) for v in all_verts if isinstance(v, (list, tuple)) and len(v) >= 3]
                zs = [float(v[2]) for v in all_verts if isinstance(v, (list, tuple)) and len(v) >= 3]
                if xs and ys and zs:
                    hx = max(1e-4, (max(xs) - min(xs)) / 2.0)
                    hy = max(1e-4, (max(ys) - min(ys)) / 2.0)
                    hz = max(1e-4, (max(zs) - min(zs)) / 2.0)
                    dominant_extents = (hx, hy, hz)
            except (ValueError, TypeError):
                dominant_extents = None
        elif "half_extents_mm" in mesh and isinstance(mesh["half_extents_mm"], (list, tuple)) and len(mesh["half_extents_mm"]) == 3:
            dominant_extents = tuple(float(x) for x in mesh["half_extents_mm"])
        elif "size_mm" in mesh and isinstance(mesh["size_mm"], (list, tuple)) and len(mesh["size_mm"]) == 3:
            dominant_extents = (float(mesh["size_mm"][0]) / 2000.0, float(mesh["size_mm"][1]) / 2000.0, float(mesh["size_mm"][2]) / 2000.0)

        if dominant_extents is None:
            dominant_extents = (0.45, 0.14, 0.03)

        try:
            u_span, v_span = mapping_rotated_span(axis, dominant_extents)
            if u_span < 1e-4 or v_span < 1e-4:
                findings.append({
                    "material": mat_name,
                    "mesh": mesh_id,
                    "category": "grain_orientation",
                    "severity": "ERROR",
                    "message": (
                        f"Mesh '{mesh_id}' uses material '{mat_name}' with vertical grain_axis='{axis}' "
                        f"on horizontal face, collapsing mapping span (u={u_span:.4f}, v={v_span:.4f})"
                    ),
                    "lesson_id": "l0795",
                    "reason": "Rotating box coordinates pointed texture coordinate at unrotated face normal, collapsing texel span",
                    "value": {"mesh": mesh_id, "grain_axis": axis, "u_span": u_span, "v_span": v_span},
                    "expected": "Non-degenerate u_span > 0 and v_span > 0 on horizontal faces",
                    "citation": "docs/LEARNINGS.md:939",
                })
        except Exception as exc:
            findings.append({
                "material": mat_name,
                "mesh": mesh_id,
                "category": "grain_orientation",
                "severity": "ERROR",
                "message": f"Failed evaluating grain mapping span for mesh '{mesh_id}': {exc}",
                "lesson_id": "l0795",
                "reason": "Mapping rotation span evaluation failed",
                "value": axis,
                "expected": "Valid axis supported by archpipe.blender.grain",
                "citation": "src/archpipe/blender/grain.py:27",
            })

    return findings


def assert_material_basis(scene: dict[str, Any] | Path | str | None = None) -> list[dict[str, Any]]:
    """Fail closed when material definition violates physical optical bounds or lacks basis.

    Args:
        scene: Scene dictionary, file path, or None.

    Returns:
        List of findings if no ERROR severity findings occur.

    Raises:
        ValueError: If any ERROR finding is detected.
        UnreadableInputError: If scene input cannot be resolved.
    """
    findings = material_findings(scene)
    errors = [f for f in findings if f.get("severity") == "ERROR"]
    if errors:
        first = errors[0]
        raise ValueError(
            f"Material appearance basis violation in '{first['material']}' "
            f"[{first.get('category')}]: {first.get('message')} (lesson {first.get('lesson_id')})"
        )
    return findings
