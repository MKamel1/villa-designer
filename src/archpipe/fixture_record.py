"""Fixture record consistency and cross-subsystem verification.

In accordance with the Class C5 rule established in docs/lessons-audit.md:
"One fixture record owns photometry, emitter, housing and mount."

This module cross-checks luminaire data across:
1. Photometry declared flux and CCT vs render emitter & design requirements (l0123, l0080).
2. Emitter position vs housing geometry (emitter inside housing, l0095).
3. Mounting height in specification vs built emitter (l0095, l0096).
4. Housing clearance vs finished ceiling (l0119, l0096).
5. Fitting label vs room containment and product records (l0610).

Quick Test:
    python -c "from archpipe.fixture_record import fixture_findings; print(callable(fixture_findings))"

Example Usage:
    >>> from archpipe.fixture_record import fixture_findings, check_fixture_record_consistency
    >>> findings = fixture_findings({"spec": {"lighting": []}})
    >>> isinstance(findings, list)
    True
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any

from archpipe import fixture_source
from archpipe.concept import villa_furnish as F
from archpipe.concept import villa_lighting as VL
from archpipe.luminaires import install
from archpipe.luminaires import library as lib
from archpipe import photometry as ph


class UnreadableFixtureRecordError(FileNotFoundError, ValueError):
    """Raised when fixture record input is missing, unreadable, or invalid."""
    pass


class FixtureConsistencyError(ValueError):
    """Raised when fixture consistency checks find discrepancies."""
    pass


@dataclass(frozen=True)
class FixtureFinding:
    """A single finding from fixture consistency inspection."""
    fixture_id: str
    rule: str
    lesson_id: str
    status: str  # "FAIL", "WARN", "NOTE", "PASS"
    message: str
    declared: Any = None
    actual: Any = None


def fixture_findings(
    scene_or_spec: Any = None,
    *,
    spec: dict | None = None,
    scene: dict | None = None,
    meshes: dict | None = None,
    layout: dict | None = None,
    ceiling_mm: float = 2700.0,
) -> list[FixtureFinding]:
    """Inspect luminaire records and report discrepancies across subsystems.

    Calls authoritative production functions to evaluate:
    - Photometry declared flux / CCT vs render emitter (l0123, l0080).
    - Emitter position vs housing geometry (l0095).
    - Specification mounting height vs built emitter (l0096).
    - Housing penetration vs ceiling height, distinguishing recessed (l0119).
    - Fitting label vs room clear rectangle containment (l0610).

    Args:
        scene_or_spec: Path to spec/scene JSON/YAML, or dictionary containing
            spec, scene, meshes, layout, or lighting entries.
        spec: Explicit specification dictionary with lighting list.
        scene: Explicit render scene dictionary with lights and meshes.
        meshes: Explicit mapping of fixture ID to extract mesh lists.
        layout: Explicit architectural layout dictionary (rooms, clear rects).
        ceiling_mm: Finished ceiling elevation in millimetres.

    Returns:
        List of FixtureFinding records detailing PASS, NOTE, WARN, or FAIL.

    Raises:
        UnreadableFixtureRecordError: If inputs are missing, unreadable, empty,
            or corrupt.
    """
    if (
        scene_or_spec is None
        and spec is None
        and scene is None
        and meshes is None
        and layout is None
    ):
        raise UnreadableFixtureRecordError(
            "Missing fixture record input: no scene, spec, meshes, or layout provided"
        )

    # Resolve file path input if provided
    if isinstance(scene_or_spec, (str, Path)):
        path = Path(scene_or_spec)
        if not str(path).strip():
            raise UnreadableFixtureRecordError("Fixture record input path cannot be empty")
        if not path.exists():
            raise UnreadableFixtureRecordError(f"Fixture record file not found: {path}")
        if not path.is_file():
            raise UnreadableFixtureRecordError(f"Fixture record path is not a file: {path}")

        try:
            raw_text = path.read_text(encoding="utf-8")
        except Exception as exc:
            raise UnreadableFixtureRecordError(f"Could not read fixture record file {path}: {exc}") from exc

        if not raw_text.strip():
            raise UnreadableFixtureRecordError(f"Fixture record file is empty: {path}")

        if path.suffix.lower() in (".yaml", ".yml"):
            try:
                import yaml
                data = yaml.safe_load(raw_text)
            except Exception as exc:
                raise UnreadableFixtureRecordError(f"Failed to parse YAML from {path}: {exc}") from exc
        elif path.suffix.lower() == ".json":
            try:
                data = json.loads(raw_text)
            except Exception as exc:
                raise UnreadableFixtureRecordError(f"Failed to parse JSON from {path}: {exc}") from exc
        else:
            raise UnreadableFixtureRecordError(f"Unsupported fixture record format: {path.suffix}")

        if not isinstance(data, (dict, list)):
            raise UnreadableFixtureRecordError(
                f"Parsed fixture record must be dict or list, got {type(data).__name__}"
            )
        scene_or_spec = data

    # Unpack composite dict if provided
    if isinstance(scene_or_spec, dict):
        if "_metadata" in scene_or_spec and len(scene_or_spec) == 1:
            raise UnreadableFixtureRecordError("Fixture record file contains metadata only with no fixture data")
        if "spec" in scene_or_spec and spec is None:
            spec = scene_or_spec["spec"]
        if "scene" in scene_or_spec and scene is None:
            scene = scene_or_spec["scene"]
        if "meshes" in scene_or_spec and meshes is None:
            meshes = scene_or_spec["meshes"]
        if "layout" in scene_or_spec and layout is None:
            layout = scene_or_spec["layout"]
        if "ceiling_mm" in scene_or_spec:
            ceiling_mm = float(scene_or_spec["ceiling_mm"])

        # If scene_or_spec itself is a spec dict (e.g. contains lighting list)
        if "lighting" in scene_or_spec and spec is None:
            spec = scene_or_spec
        # If scene_or_spec itself is a scene dict (e.g. contains lights list)
        if "lights" in scene_or_spec and scene is None:
            scene = scene_or_spec

    findings: list[FixtureFinding] = []

    # -------------------------------------------------------------------------
    # 1. Spec Lighting Consistency (Flux, CCT, Mounting Height, Geometry)
    # -------------------------------------------------------------------------
    if spec is not None:
        if not isinstance(spec, dict):
            raise UnreadableFixtureRecordError(f"Spec must be a dictionary, got {type(spec).__name__}")

        lighting_list = spec.get("lighting", [])
        if not isinstance(lighting_list, list):
            raise UnreadableFixtureRecordError(
                f"Spec lighting must be a list, got {type(lighting_list).__name__}"
            )

        for item in lighting_list:
            if not isinstance(item, dict):
                raise UnreadableFixtureRecordError(
                    f"Lighting entry must be a dictionary, got {type(item).__name__}"
                )
            fid = str(item.get("id", "unknown"))

            # 1.1 Luminaire Flux vs Requirement (l0123)
            req = item.get("requirement")
            prod = item.get("product")
            if req and isinstance(req, dict) and "lumens" in req:
                req_lo, req_hi = req["lumens"]
                actual_lm = None
                if isinstance(prod, dict) and "luminaire_lm" in prod:
                    actual_lm = float(prod["luminaire_lm"])
                elif "lumens" in item:
                    actual_lm = float(item["lumens"])

                if actual_lm is not None and not (req_lo <= actual_lm <= req_hi):
                    findings.append(FixtureFinding(
                        fixture_id=fid,
                        rule="photometry_flux_requirement",
                        lesson_id="l0123-swapping-4300-lm",
                        status="FAIL",
                        message=(
                            f"Luminaire flux {actual_lm:.1f} lm outside required range "
                            f"[{req_lo}, {req_hi}] lm (l0123)"
                        ),
                        declared=[req_lo, req_hi],
                        actual=actual_lm,
                    ))

            # 1.2 Hand-typed vs Product Record Clashes
            if isinstance(prod, dict) and "manufacturer" in prod and "sku" in prod:
                mfr = str(prod["manufacturer"]).lower()
                sku = str(prod["sku"])
                lamp_set = int(prod.get("lamp_set", 0))
                row = lib.get(mfr, sku, lamp_set)
                if row:
                    if "lumens" in item:
                        spec_lm = float(item["lumens"])
                        want_lm = float(row["lamp_lm"])
                        if abs(spec_lm - want_lm) > max(1.0, 0.05 * want_lm):
                            findings.append(FixtureFinding(
                                fixture_id=fid,
                                rule="spec_lumens_product_agreement",
                                lesson_id="l0123-swapping-4300-lm",
                                status="FAIL",
                                message=(
                                    f"Spec lumens {spec_lm:.1f} lm contradicts library product "
                                    f"{want_lm:.1f} lm from {mfr}/{sku}"
                                ),
                                declared=spec_lm,
                                actual=want_lm,
                            ))
                    if "kelvin" in item:
                        spec_k = float(item["kelvin"])
                        want_k = float(row["cct_k"])
                        if abs(spec_k - want_k) > 50:
                            findings.append(FixtureFinding(
                                fixture_id=fid,
                                rule="spec_cct_product_agreement",
                                lesson_id="l0080-lamps-rendered-far",
                                status="FAIL",
                                message=(
                                    f"Spec CCT {spec_k:.0f} K contradicts library product "
                                    f"{want_k:.0f} K from {mfr}/{sku}"
                                ),
                                declared=spec_k,
                                actual=want_k,
                            ))

            # 1.3 Extracted Meshes vs Emitter Datum & Housing (l0095, l0096, l0119)
            if meshes and fid in meshes:
                fx_meshes = meshes[fid]
                if not isinstance(fx_meshes, list):
                    raise UnreadableFixtureRecordError(f"Meshes for fixture {fid} must be a list")

                src = fixture_source.source_point(fx_meshes)
                if src is None:
                    findings.append(FixtureFinding(
                        fixture_id=fid,
                        rule="emitter_geometry_measured",
                        lesson_id="l0095-lamp-sources-sat",
                        status="FAIL",
                        message=f"Fitting {fid} has no measurable Light Source symbol or luminous face geometry",
                    ))
                else:
                    sx, sy, sz, basis = src
                    mh = item.get("mounting_height")
                    if mh is not None:
                        mh_val = float(mh)
                        dz = abs(sz - mh_val)
                        if dz > 25.0:
                            findings.append(FixtureFinding(
                                fixture_id=fid,
                                rule="emitter_mounting_height_agreement",
                                lesson_id="l0095-lamp-sources-sat",
                                status="FAIL",
                                message=(
                                    f"Measured emitter height {sz:.1f} mm differs by {dz:.1f} mm "
                                    f"from spec mounting_height {mh_val:.1f} mm (tol 25.0 mm) (l0095)"
                                ),
                                declared=mh_val,
                                actual=round(sz, 1),
                            ))

                    at_pt = item.get("at")
                    if at_pt and len(at_pt) >= 2:
                        d_plan = math.hypot(sx - at_pt[0], sy - at_pt[1])
                        if d_plan > 25.0:
                            findings.append(FixtureFinding(
                                fixture_id=fid,
                                rule="emitter_plan_offset_agreement",
                                lesson_id="l0095-lamp-sources-sat",
                                status="FAIL",
                                message=(
                                    f"Measured emitter plan offset {d_plan:.1f} mm exceeds "
                                    f"tolerance 25.0 mm (l0095)"
                                ),
                                declared=at_pt,
                                actual=[round(sx, 1), round(sy, 1)],
                            ))

                # Body geometry vs Ceiling clearance (l0119, l0096)
                body_pts = [
                    p
                    for m in fx_meshes
                    if m.get("geometry_role") != "light_source_symbol"
                    for p in m.get("vertices_mm", [])
                ]
                if body_pts:
                    top_z = max(p[2] for p in body_pts)
                    mount = (
                        (item.get("product") or {}).get("mount")
                        or item.get("mount")
                        or item.get("host")
                    )
                    tol_ceiling = 5.0
                    if mount == "recessed":
                        if top_z > ceiling_mm:
                            recess_needed = top_z - ceiling_mm
                            findings.append(FixtureFinding(
                                fixture_id=fid,
                                rule="housing_ceiling_clearance",
                                lesson_id="l0119-housing-below-ceiling",
                                status="NOTE",
                                message=(
                                    f"Recessed luminaire body top {top_z:.1f} mm requires "
                                    f"{recess_needed:.1f} mm recess depth above {ceiling_mm:.1f} mm "
                                    f"ceiling (coordination note) (l0119)"
                                ),
                                declared=ceiling_mm,
                                actual=round(top_z, 1),
                            ))
                    else:
                        if top_z > ceiling_mm + tol_ceiling:
                            findings.append(FixtureFinding(
                                fixture_id=fid,
                                rule="housing_ceiling_clearance",
                                lesson_id="l0096-two-spec-heights",
                                status="FAIL",
                                message=(
                                    f"Housing penetrates ceiling: body top {top_z:.1f} mm "
                                    f"exceeds finished ceiling {ceiling_mm:.1f} mm by "
                                    f"{top_z - ceiling_mm:.1f} mm (l0096, l0119)"
                                ),
                                declared=ceiling_mm,
                                actual=round(top_z, 1),
                            ))

    # -------------------------------------------------------------------------
    # 2. Render Scene Emitter Consistency (Flux, CCT, Position)
    # -------------------------------------------------------------------------
    if scene is not None:
        if not isinstance(scene, dict):
            raise UnreadableFixtureRecordError(f"Scene must be a dictionary, got {type(scene).__name__}")

        lights = scene.get("lights", [])
        if not isinstance(lights, list):
            raise UnreadableFixtureRecordError(f"Scene lights must be a list, got {type(lights).__name__}")

        scene_meshes = {
            m["id"]: m
            for m in scene.get("meshes", [])
            if isinstance(m, dict) and "id" in m
        }

        for L in lights:
            if not isinstance(L, dict):
                raise UnreadableFixtureRecordError(f"Light entry must be a dictionary, got {type(L).__name__}")
            lid = str(L.get("id", "unknown"))
            cct = L.get("cct_k")
            lm = L.get("lumens")
            prod = L.get("product", {})

            # Check verified product CCT and flux agreement (l0080, l0123)
            if isinstance(prod, dict) and not prod.get("generic"):
                mfr = prod.get("manufacturer")
                sku = prod.get("code")
                lamp_set = int(prod.get("lamp_set", 0))
                if mfr and sku:
                    row = lib.get(mfr, sku, lamp_set)
                    if row:
                        if cct is not None and abs(cct - row["cct_k"]) > 50:
                            findings.append(FixtureFinding(
                                fixture_id=lid,
                                rule="render_cct_agreement",
                                lesson_id="l0080-lamps-rendered-far",
                                status="FAIL",
                                message=(
                                    f"Render emitter CCT {cct} K differs from verified product "
                                    f"CCT {row['cct_k']} K (l0080)"
                                ),
                                declared=row["cct_k"],
                                actual=cct,
                            ))
                        if lm is not None and abs(lm - row["luminaire_lm"]) > 0.05 * row["luminaire_lm"]:
                            findings.append(FixtureFinding(
                                fixture_id=lid,
                                rule="render_flux_agreement",
                                lesson_id="l0123-swapping-4300-lm",
                                status="FAIL",
                                message=(
                                    f"Render emitter flux {lm:.1f} lm differs from verified product "
                                    f"flux {row['luminaire_lm']:.1f} lm (l0123)"
                                ),
                                declared=row["luminaire_lm"],
                                actual=lm,
                            ))

            # Check emitter position vs corresponding fixture mesh in scene
            mesh_id = "fix-" + lid
            if mesh_id in scene_meshes:
                fix_mesh = scene_meshes[mesh_id]
                faces = fix_mesh.get("faces", [])
                if faces and faces[0] and len(faces[0][0]) >= 3:
                    mesh_z = faces[0][0][2]
                    light_pos = L.get("position", [0, 0, 0])
                    if len(light_pos) >= 3:
                        dz = abs(light_pos[2] - mesh_z)
                        if dz > 0.10:  # 100 mm offset threshold
                            findings.append(FixtureFinding(
                                fixture_id=lid,
                                rule="emitter_mesh_offset",
                                lesson_id="l0095-lamp-sources-sat",
                                status="FAIL",
                                message=(
                                    f"Render emitter at z={light_pos[2]:.3f} sits {dz*1000:.0f} mm "
                                    f"from housing trim at z={mesh_z:.3f} (l0095)"
                                ),
                                declared=mesh_z,
                                actual=light_pos[2],
                            ))

    # -------------------------------------------------------------------------
    # 3. Room Containment and Fitting Labeling (l0610)
    # -------------------------------------------------------------------------
    fixtures_for_rooms: list[Any] = []
    if isinstance(scene_or_spec, list):
        fixtures_for_rooms = scene_or_spec
    elif isinstance(spec, dict) and "fixtures" in spec:
        fixtures_for_rooms = spec["fixtures"]
    elif layout and "fixtures" in layout:
        fixtures_for_rooms = layout["fixtures"]

    target_layout = layout
    if target_layout is None and isinstance(scene_or_spec, dict) and "rooms" in scene_or_spec:
        target_layout = scene_or_spec

    if fixtures_for_rooms and target_layout is not None:
        if not isinstance(target_layout, dict):
            raise UnreadableFixtureRecordError(
                f"Target layout must be a dictionary, got {type(target_layout).__name__}"
            )
        rooms_dict = target_layout.get("rooms", {})

        for fx in fixtures_for_rooms:
            fx_id = getattr(fx, "id", None) or (fx.get("id", "unknown") if isinstance(fx, dict) else "unknown")
            fx_room = getattr(fx, "room", None) or (fx.get("room") if isinstance(fx, dict) else None)
            if hasattr(fx, "x") and hasattr(fx, "y"):
                fx_x, fx_y = fx.x, fx.y
            elif isinstance(fx, dict):
                fx_x = fx.get("x") if "x" in fx else (fx.get("at", [None])[0] if "at" in fx else None)
                fx_y = fx.get("y") if "y" in fx else (fx.get("at", [None, None])[1] if "at" in fx else None)
            else:
                fx_x, fx_y = None, None

            if fx_room and fx_x is not None and fx_y is not None and fx_room in rooms_dict:
                rc_x0, rc_y0, rc_x1, rc_y1 = F.clear_rect(target_layout, fx_room)
                tol = 1e-4
                if not (rc_x0 - tol <= fx_x <= rc_x1 + tol and rc_y0 - tol <= fx_y <= rc_y1 + tol):
                    # Outside assigned room clear rect: measure distance and check cluster neighbours
                    dx = max(0.0, rc_x0 - fx_x, fx_x - rc_x1)
                    dy = max(0.0, rc_y0 - fx_y, fx_y - rc_y1)
                    dist_outside_mm = math.hypot(dx, dy) * 1000.0
                    dist_str = (
                        f"{dist_outside_mm:.0f} mm"
                        if abs(dist_outside_mm - round(dist_outside_mm)) < 0.05
                        else f"{dist_outside_mm:.1f} mm"
                    )

                    contained_in = None
                    for other in F._cluster(target_layout, fx_room):
                        if other != fx_room and other in rooms_dict:
                            qx0, qy0, qx1, qy1 = F.clear_rect(target_layout, other)
                            if qx0 - tol <= fx_x <= qx1 + tol and qy0 - tol <= fx_y <= qy1 + tol:
                                contained_in = other
                                break

                    findings.append(FixtureFinding(
                        fixture_id=str(fx_id),
                        rule="fitting_room_containment",
                        lesson_id="l0610-fitting-labelled-wrong",
                        status="FAIL",
                        message=(
                            f"Fitting {fx_id} labelled with room '{fx_room}' at ({fx_x:.3f}, {fx_y:.3f}) "
                            f"sits {dist_str} outside {fx_room} clear rect"
                            + (f" and inside '{contained_in}'" if contained_in else "")
                            + " (l0610)"
                        ),
                        declared=fx_room,
                        actual=contained_in or "outside",
                    ))

    # If no findings were added, record baseline pass
    if not findings:
        findings.append(FixtureFinding(
            fixture_id="all",
            rule="fixture_record_consistency",
            lesson_id="clean",
            status="PASS",
            message="All checked fixture records are consistent with physical and photometric contracts",
        ))

    return findings


def check_fixture_record_consistency(target: Any = None, **kwargs) -> list[FixtureFinding]:
    """Guard registry adapter: runs fixture_findings and fails closed on FAIL findings.

    Args:
        target: File path, specification dict, scene dict, or composite payload.
        **kwargs: Optional spec, scene, meshes, layout, ceiling_mm parameters.

    Returns:
        List of FixtureFinding records if all pass or only generate notes.

    Raises:
        UnreadableFixtureRecordError: If target cannot be found, read, or parsed.
        FixtureConsistencyError: If any consistency check generates a FAIL finding.
    """
    findings = fixture_findings(target, **kwargs)
    fails = [f for f in findings if f.status == "FAIL"]
    if fails:
        msg = "; ".join(f"{f.fixture_id} [{f.lesson_id}]: {f.message}" for f in fails)
        raise FixtureConsistencyError(
            f"Fixture consistency guard failed ({len(fails)} issues): {msg}"
        )
    return findings
