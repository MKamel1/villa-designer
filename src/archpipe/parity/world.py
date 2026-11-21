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
    tris: np.ndarray                      # (n,3,3) metres
    meshes: list = field(default_factory=list)   # mesh ids contributing
    groups: set = field(default_factory=set)
    materials: set = field(default_factory=set)

    @property
    def kind(self) -> str:
        return kind_of(self.id)

    @property
    def box(self):
        return aabb(self.tris)


@dataclass
class World:
    elements: dict
    unowned: list            # (mesh id, group, n faces) with no element id  -> findings
    source: str = ""
    sha256: str = ""

    def of(self, *kinds):
        return {k: e for k, e in self.elements.items() if e.kind in kinds}


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""):
            h.update(ch)
    return h.hexdigest()


def load_scene_json(path, hash_it: bool = True, groups=None) -> tuple[World, dict]:
    """Return (World, raw scene dict). Faces are attributed to ids via faces_by_element;
    a mesh with only element_ids owns its faces wholly (single id) or is split evenly-unknown
    (multi id without faces_by_element -> reported as unowned, never guessed)."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    s = json.loads(path.read_text())
    acc: dict = {}
    unowned = []
    for m in s["meshes"]:
        if groups and m["group"] not in groups:
            continue
        faces = m["faces"]
        fbe = m.get("faces_by_element")
        ids = m.get("element_ids") or []
        if fbe:
            owned = set()
            for eid, idx in fbe.items():
                owned.update(idx)
                _add(acc, eid, m, [faces[i] for i in idx])
            rest = [i for i in range(len(faces)) if i not in owned]
            if rest:
                unowned.append((m["id"], m["group"], len(rest)))
        elif len(ids) == 1:
            _add(acc, ids[0], m, faces)
        else:
            unowned.append((m["id"], m["group"], len(faces)))
    els = {}
    for eid, (tl, ms, gs, mats) in acc.items():
        t = np.concatenate(tl) if tl else np.zeros((0, 3, 3))
        els[eid] = Element(eid, t, sorted(ms), gs, mats)
    return World(els, unowned, str(path), sha256_file(path) if hash_it else ""), s


def _add(acc, eid, m, faces):
    tl, ms, gs, mats = acc.setdefault(eid, ([], set(), set(), set()))
    for f in faces:
        t = fan(f)
        if len(t):
            tl.append(t)
    ms.add(m["id"]); gs.add(m["group"]); mats.add(m.get("material"))


def world_from_boxes(boxes: dict, source="boxes") -> World:
    """boxes: id -> (x0,y0,z0,x1,y1,z1) metres. Used for the frozen historic reproductions."""
    return World({k: Element(k, box_tris(b)) for k, b in boxes.items()}, [], source)
