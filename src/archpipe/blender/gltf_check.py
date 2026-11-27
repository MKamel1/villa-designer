"""Box check on the imported furniture models' own geometry (lane SOFT). Reads library glTF files, so it lives in
blender/ with the other render-host asset readers (build_input_guard: no raw glTF paths in build code)."""
import json
from pathlib import Path

import numpy as np

from ..critic.furniture_realism import CHECK_WEIGHT, POLICY, SEVERITY, Finding, axis_area_fraction

def gltf_triangles(path):
    """World-of-the-asset triangles (n x 3 x 3) of a glTF 2.0 file: node hierarchy applied, no placement."""
    path = Path(path)
    g = json.loads(path.read_text(encoding="utf-8"))
    bins = [(path.parent / b["uri"]).read_bytes() for b in g.get("buffers", []) if "uri" in b and not b["uri"].startswith("data:")]

    def acc(i):
        a = g["accessors"][i]
        bv = g["bufferViews"][a["bufferView"]]
        n = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[a["type"]]
        dt = {5126: "f4", 5123: "u2", 5125: "u4", 5121: "u1"}[a["componentType"]]
        off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        return np.frombuffer(bins[bv["buffer"]], dtype=dt, count=a["count"] * n, offset=off).reshape(-1, n)

    def local(node):
        if "matrix" in node:
            return np.array(node["matrix"], float).reshape(4, 4).T
        m = np.eye(4)
        x, y, z, w = node.get("rotation", [0, 0, 0, 1])
        r = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                      [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                      [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
        m[:3, :3] = r * np.array(node.get("scale", [1, 1, 1]))
        m[:3, 3] = node.get("translation", [0, 0, 0])
        return m
    out = []

    def walk(i, parent):
        node = g["nodes"][i]
        m = parent @ local(node)
        if "mesh" in node:
            for prim in g["meshes"][node["mesh"]]["primitives"]:
                if prim.get("mode", 4) != 4 or "indices" not in prim:
                    continue
                v = acc(prim["attributes"]["POSITION"]).astype(float)
                v = v @ m[:3, :3].T + m[:3, 3]
                out.append(v[acc(prim["indices"]).ravel().astype(int)].reshape(-1, 3, 3))
        for c in node.get("children", []):
            walk(c, m)
    for r in g["scenes"][g.get("scene", 0)]["nodes"]:
        walk(r, np.eye(4))
    return np.concatenate(out) if out else np.empty((0, 3, 3))


def model_findings(scene, library_root):
    """Box check on each imported furniture model's own geometry (the scan, before placement)."""
    out = []
    seen = {}
    for m in scene.get("models", []):
        asset = m["asset"]
        if asset not in seen:
            for name in ("model.gltf", "scene.gltf"):
                f = Path(library_root, "props", asset, name)
                if f.exists():
                    seen[asset] = axis_area_fraction(gltf_triangles(f)) if f.stat().st_size < 5_000_000 else None
                    break
            else:
                seen[asset] = None
        frac = seen[asset]
        if frac is not None and frac >= POLICY["box_axis_area_fraction"] and m.get("role") not in ("rug",):
            out.append(Finding(m["id"], "case", "box", "scan %s: %.0f%% of face area on three axes" % (asset, 100 * frac),
                               "< %.0f%%" % (100 * POLICY["box_axis_area_fraction"]),
                               "replace the asset with a modelled one or bevel it at import", SEVERITY["case"] * CHECK_WEIGHT["box"]))
    return out


