"""Measure a seating or bed front from glTF world-space POSITION vertices."""
from __future__ import annotations

import json
import re
import struct
from pathlib import Path

from fetch_asset_library import _apply, _mat_mult, _trs_matrix


def directional_role(role: str) -> bool:
    return bool(re.search(r"sofa|chair|\bbed\b", role, re.IGNORECASE))


def measured_or_manual_front(entry: dict, gltf_path: Path) -> None:
    if not directional_role(entry.get("role", "")):
        return
    if entry.get("front_axis"):
        if entry["front_axis"] not in ("+X", "-X", "+Z", "-Z"):
            raise ValueError(entry["id"] + ": invalid lead-verified front_axis")
        entry["front_axis_basis"] = "lead-verified"
    else:
        entry.update(front_axis=estimate_front(half_stats(world_vertices(gltf_path))),
                     front_axis_basis="auto (tall-back side)")


def world_vertices(path: Path):
    gltf = json.loads(path.read_text(encoding="utf-8"))
    buffers = [(path.parent / b["uri"]).read_bytes() for b in gltf["buffers"]]
    identity = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    def visit(index, parent):
        node = gltf["nodes"][index]
        matrix = _mat_mult(parent, _trs_matrix(node))
        if "mesh" in node:
            for primitive in gltf["meshes"][node["mesh"]]["primitives"]:
                accessor = gltf["accessors"][primitive["attributes"]["POSITION"]]
                if accessor["componentType"] != 5126 or accessor["type"] != "VEC3":
                    raise ValueError("POSITION must contain float VEC3 vertices")
                view = gltf["bufferViews"][accessor["bufferView"]]
                data = buffers[view["buffer"]]
                start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
                stride = view.get("byteStride", 12)
                for n in range(accessor["count"]):
                    yield _apply(matrix, struct.unpack_from("<fff", data, start + n * stride))
        for child in node.get("children", []):
            yield from visit(child, matrix)
    for root in gltf["scenes"][gltf.get("scene", 0)]["nodes"]:
        yield from visit(root, identity)


def half_stats(vertices):
    points = list(vertices)
    lo = [min(p[i] for p in points) for i in range(3)]
    hi = [max(p[i] for p in points) for i in range(3)]
    result = {}
    for axis, name in ((0, "X"), (2, "Z")):
        mid = (lo[axis] + hi[axis]) / 2
        for sign, selected in (("+", [p[1] for p in points if p[axis] >= mid]),
                               ("-", [p[1] for p in points if p[axis] < mid])):
            selected.sort()
            result[sign + name] = selected[int(0.98 * (len(selected) - 1))]
    return result


def estimate_front(stats, minimum_gap=0.08):
    """The tallest half is the back; return the opposite horizontal direction."""
    pairs = [(abs(stats["+X"] - stats["-X"]), "-X" if stats["+X"] > stats["-X"] else "+X"),
             (abs(stats["+Z"] - stats["-Z"]), "-Z" if stats["+Z"] > stats["-Z"] else "+Z")]
    gap, front = max(pairs)
    height = max(stats.values())
    if gap < minimum_gap * height:
        raise ValueError("no clear tall-back side; lead verification required")
    return front
