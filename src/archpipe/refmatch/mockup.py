"""Add proposal geometry to a COPY of a render-set scene.json (never the production scene).

A mock-up is the render-set scene plus boxes, slat runs, emissive strips and line lights.
Materials added here are labelled look-alikes: a flat colour or a CC0 texture standing for a
maker's product, never the product itself.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from archpipe.scene_reproducibility import require_outward


def box_faces(x0, x1, y0, y1, z0, z1):
    """Six outward-wound quads (counter-clockwise seen from outside)."""
    a, b = sorted((x0, x1)), sorted((y0, y1))
    x0, x1, y0, y1 = a[0], a[1], b[0], b[1]
    z0, z1 = sorted((z0, z1))
    faces = [
        [[x0, y0, z0], [x0, y1, z0], [x1, y1, z0], [x1, y0, z0]],      # -z
        [[x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]],      # +z
        [[x0, y0, z0], [x1, y0, z0], [x1, y0, z1], [x0, y0, z1]],      # -y
        [[x0, y1, z0], [x0, y1, z1], [x1, y1, z1], [x1, y1, z0]],      # +y
        [[x0, y0, z0], [x0, y0, z1], [x0, y1, z1], [x0, y1, z0]],      # -x
        [[x1, y0, z0], [x1, y1, z0], [x1, y1, z1], [x1, y0, z1]],      # +x
    ]
    return faces


class Mockup:
    def __init__(self, scene: dict):
        self.s = copy.deepcopy(scene)
        self.added = []

    @classmethod
    def load(cls, path):
        return cls(json.loads(Path(path).read_text()))

    def material(self, name, **spec):
        self.s["materials"][name] = spec

    def remove_meshes(self, *ids):
        gone = set(ids)
        self.s["meshes"] = [m for m in self.s["meshes"] if m["id"] not in gone]
        self.s["lights"] = [m for m in self.s["lights"] if m["id"] not in gone]

    def box(self, mid, room, material, x0, x1, y0, y1, z0, z1, label=""):
        faces = box_faces(x0, x1, y0, y1, z0, z1)
        require_outward(faces, mid)
        self.s["meshes"].append({
            "id": mid, "group": "furniture", "material": material, "room": room,
            "label": label or f"RM mock-up: {mid}", "faces": faces, "part_kind": "wall-panel",
            "local_axes": ["x", "y", "z"], "basis": "refmatch-mockup"})
        self.added.append(mid)

    def slats(self, mid, room, material, axis, a0, a1, c0, c1, z0, z1, width, pitch, depth, face_pos, face_dir=1):
        """Vertical slats. axis 'x': run along x at plane y=face_pos, slats from c0..c1 depth along +/-y."""
        n = int((c1 - c0 - width) / pitch) + 1
        for i in range(n):
            s0 = c0 + i * pitch
            if axis == "x":
                self.box(f"{mid}-{i:03d}", room, material, s0, s0 + width, face_pos, face_pos + face_dir * depth, z0, z1)
            else:
                self.box(f"{mid}-{i:03d}", room, material, face_pos, face_pos + face_dir * depth, s0, s0 + width, z0, z1)

    def line_light(self, lid, room, pos, aim, length, length_dir, lumens, cct=2700, layer="decorative", width=0.012):
        self.s["lights"].append({
            "id": lid, "room": room, "layer": layer, "type": "line", "position": list(pos), "aim": list(aim),
            "size": [width, length], "length_dir": list(length_dir), "spread_deg": 120, "lumens": lumens,
            "cct_k": cct, "cri": 90, "product": {"manufacturer": "generic", "code": "COVE", "generic": True},
            "dimmer": 1.0})

    def save(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(self.s))


def sphere_faces(cx, cy, cz, r, n=14):
    """Closed UV sphere (quads, triangles at the poles), outward wound."""
    import math
    rings = [(-math.pi / 2 + math.pi * i / n) for i in range(n + 1)]
    segs = 2 * n

    def pt(i, j):
        la, lo = rings[i], 2 * math.pi * (j % segs) / segs
        return [round(cx + r * math.cos(la) * math.cos(lo), 5), round(cy + r * math.cos(la) * math.sin(lo), 5),
                round(cz + r * math.sin(la), 5)]
    faces = []
    for i in range(n):
        for j in range(segs):
            a, b, c, d = pt(i, j), pt(i, j + 1), pt(i + 1, j + 1), pt(i + 1, j)
            if i == 0:
                faces.append([a, c, d])
            elif i == n - 1:
                faces.append([a, b, d])
            else:
                faces.append([a, b, c, d])
    return faces
