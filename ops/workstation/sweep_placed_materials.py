"""Inspect source materials for every asset placed by a villa scene.

Run in Blender: blender -b --python-exit-code 1 --python sweep_placed_materials.py -- SCENE_JSON LIBRARY_ROOT
Prints one JSON line per material, then a count. This is a diagnostic sweep;
flags describe source materials before villa_scene normalises them.
"""
import json
import sys
from pathlib import Path

import bpy


def main(scene_path, library_root):
    scene = json.loads(Path(scene_path).read_text(encoding="utf-8"))
    placed = {}
    for spec in scene.get("props", []) + scene.get("models", []):
        placed.setdefault(spec["asset"], set()).add(spec.get("asset_kind", "appearance"))
    flagged = 0
    for asset in sorted(placed):
        path = Path(library_root) / "props" / asset / "model.gltf"
        if not path.is_file():
            print(json.dumps({"asset": asset, "flags": ["missing-model"], "path": str(path)}))
            flagged += 1
            continue
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)
        bpy.ops.import_scene.gltf(filepath=str(path))
        meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
        materials = {mat.name: mat for obj in meshes for mat in obj.data.materials if mat}
        if not meshes or any(not obj.data.materials for obj in meshes):
            print(json.dumps({"asset": asset, "flags": ["mesh-without-material"]}))
            flagged += 1
        for name, mat in sorted(materials.items()):
            nodes = list(mat.node_tree.nodes) if mat.use_nodes else []
            types = sorted({node.type for node in nodes})
            emissions = [node for node in nodes if node.type == "EMISSION"]
            principals = [node for node in nodes if node.type == "BSDF_PRINCIPLED"]
            images = [node for node in nodes if node.type == "TEX_IMAGE"]
            flags = []
            if emissions and "luminaire" not in placed[asset]:
                flags.append("emission-non-luminaire")
            if emissions and not principals:
                flags.append("unlit-or-emission-only")
            if not principals and not emissions:
                flags.append("no-colour-shader")
            base_colours = [p.inputs["Base Color"].default_value for p in principals]
            base_colours += [e.inputs["Color"].default_value for e in emissions]
            if not images and not any(max(colour[:3]) > 0.001 for colour in base_colours):
                flags.append("no-colour-source")
            row = {"asset": asset, "material": name, "asset_kinds": sorted(placed[asset]),
                   "nodes": types, "images": [n.image.filepath if n.image else None for n in images],
                   "flags": flags}
            print(json.dumps(row, sort_keys=True))
            flagged += bool(flags)
    print(json.dumps({"placed_assets": len(placed), "flagged_materials_or_assets": flagged}))


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(args) != 2:
        raise SystemExit("usage: sweep_placed_materials.py -- SCENE_JSON LIBRARY_ROOT")
    main(*args)
