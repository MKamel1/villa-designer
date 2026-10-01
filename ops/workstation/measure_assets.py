"""Run inside headless Blender: measure all props and make neutral 512 px previews.

Usage: blender -b --python ops/workstation/measure_assets.py -- MANIFEST LIBRARY
The manifest is written only with newly measured bounds and preview paths.
Recorded bounds disagreements are reported and cause a nonzero exit.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from archpipe.asset_intake import BOUNDS_TOLERANCE_M, measure_gltf_bounds


def preview(model: Path, target: Path) -> None:
    if target.is_file():
        return
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(model))
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not meshes:
        raise ValueError("no meshes for preview")
    points = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
    low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    center = (low + high) / 2
    span = max((high - low).length, 0.01)
    bpy.ops.object.camera_add(location=center + Vector((span, -span * 1.5, span * 0.8)))
    camera = bpy.context.object
    direction = center - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = span * 1.35
    bpy.context.scene.camera = camera
    bpy.ops.object.light_add(type="AREA", location=center + Vector((span, -span, span * 1.5)))
    bpy.context.object.data.energy = 500
    bpy.context.object.data.shape = "DISK"
    bpy.context.object.data.size = span * 1.5
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)


def main(args: list[str]) -> int:
    if len(args) != 2:
        raise SystemExit("usage: measure_assets.py -- MANIFEST LIBRARY")
    manifest_path, library = Path(args[0]), Path(args[1])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    violations = []
    changed = False
    for entry in manifest.get("props", []):
        asset_id = entry["id"]
        model = library / "props" / asset_id / "model.gltf"
        if not model.is_file():
            violations.append(f"{asset_id}: missing {model}")
            continue
        try:
            measured = measure_gltf_bounds(model)
            recorded = entry.get("bounds_m")
            if recorded:
                drift = max(abs(float(a) - float(b)) for key in ("min", "max")
                            for a, b in zip(recorded[key], measured[key]))
                if drift > BOUNDS_TOLERANCE_M:
                    violations.append(f"{asset_id}: recorded bounds disagree by {drift:.4f} m; recorded value kept")
                    continue
            else:
                entry["bounds_m"] = measured
                entry.setdefault("intake_sources", {})["bounds_m"] = str(model) + ": glTF node-transformed POSITION bounds"
                changed = True
            rel = f"previews/{asset_id}.png"
            target = library / rel
            preview(model, target)
            if not target.is_file():
                raise ValueError("render produced no preview")
            if not entry.get("preview_image"):
                entry["preview_image"] = rel
                entry.setdefault("intake_sources", {})["preview_image"] = str(target) + ": Blender neutral preview"
                changed = True
            elif entry["preview_image"] != rel:
                violations.append(f"{asset_id}: recorded preview path differs; recorded value kept")
        except Exception as exc:
            violations.append(f"{asset_id}: {exc}")
    if changed:
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for violation in violations:
        print("VIOLATION " + violation, file=sys.stderr)
    print(f"measured {len(manifest.get('props', []))} entries; {len(violations)} violations")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []))
