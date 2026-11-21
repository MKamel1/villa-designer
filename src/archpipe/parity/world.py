"""World = per-element surfaces (metres), loaded from a built scene, boxes, or an IFC.

Kinds come from the element-id prefix the scene carries (P2), never from geometry.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .geom import aabb, box_tris, fan

KINDS = ("wall", "door", "window", "column", "beam", "slab", "stair", "rail", "furn", "lum",
         "fixture", "plant", "room", "ctx", "env", "spec", "floor", "ceiling", "joinery", "detail")


def kind_of(eid: str) -> str:
    p = eid.split("-")[0]
    return "rail" if p in ("rail",) else p


@dataclass
class Element:
    id: str
    parts: list = field(default_factory=list)   # (mesh_id, group, material, part_kind, tris (n,3,3))
    _all: object = None

    @property
    def tris(self) -> np.ndarray:
        if self._all is None:
            ts = [p[4] for p in self.parts]
            self._all = np.concatenate(ts) if ts else np.zeros((0, 3, 3))
        return self._all

    def sel(self, material=None, group=None, part_kind=None, mesh_prefix=None) -> np.ndarray:
        ts = [p[4] for p in self.parts
              if (material is None or p[2] == material) and (group is None or p[1] == group)
              and (part_kind is None or p[3] == part_kind)
              and (mesh_prefix is None or p[0].startswith(mesh_prefix))]
        return np.concatenate(ts) if ts else np.zeros((0, 3, 3))

    @property
    def kind(self) -> str:
        return kind_of(self.id)

    @property
    def meshes(self):
        return sorted({p[0] for p in self.parts})

    @property
    def groups(self):
        return {p[1] for p in self.parts}

    @property
    def box(self):
        return aabb(self.tris)


@dataclass
class World:
    elements: dict
    unowned: list            # (mesh id, group, n faces) with no element id  -> findings
    source: str = ""
    sha256: str = ""
    mesh_tris: dict = field(default_factory=dict)   # mesh id -> (n,3,3), every mesh, owned or not

    def of(self, *kinds):
        return {k: e for k, e in self.elements.items() if e.kind in kinds}


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""):
            h.update(ch)
    return h.hexdigest()


def load_scene_json(path, hash_it: bool = True) -> tuple[World, dict]:
    """Return (World, raw scene dict). Faces are attributed to ids via faces_by_element;
    a mesh with several ids and no faces_by_element is reported as unowned, never guessed."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    s = json.loads(path.read_text())
    els: dict = {}
    unowned, mesh_tris = [], {}
    for m in s["meshes"]:
        faces = m["faces"]
        allt = [fan(f) for f in faces]
        mesh_tris[m["id"]] = np.concatenate([t for t in allt if len(t)]) if any(len(t) for t in allt) else np.zeros((0, 3, 3))
        fbe = m.get("faces_by_element")
        ids = m.get("element_ids") or []

        def add(eid, idx):
            ts = [allt[i] for i in idx if len(allt[i])]
            if ts:
                els.setdefault(eid, Element(eid)).parts.append(
                    (m["id"], m["group"], m.get("material"), m.get("part_kind"), np.concatenate(ts)))
        if fbe:
            owned = set()
            for eid, idx in fbe.items():
                owned.update(idx)
                add(eid, idx)
            rest = [i for i in range(len(faces)) if i not in owned]
            if rest:
                unowned.append((m["id"], m["group"], len(rest)))
        elif len(ids) == 1:
            add(ids[0], range(len(faces)))
        else:
            unowned.append((m["id"], m["group"], len(faces)))
    return World(els, unowned, str(path), sha256_file(path) if hash_it else "", mesh_tris), s


def world_from_boxes(boxes: dict, source="boxes") -> World:
    """boxes: id -> (x0,y0,z0,x1,y1,z1) metres. Used for the frozen historic reproductions."""
    return World({k: Element(k, [(k, "box", None, None, box_tris(b))]) for k, b in boxes.items()}, [], source)
