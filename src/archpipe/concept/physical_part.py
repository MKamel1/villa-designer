"""Typed physical boundary for presentation-scene mesh parts.

Collection mode is used only while migrating the existing scene in C3 phase 1.
The constructor itself always rejects a malformed or proxy part.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections import Counter
import math


# Each admitted kind has a physical reason to retain a rectangular solid.
BOX_KINDS = {
    "cabinet-carcass": "Planar cabinet boards and rectangular enclosure are the finished joinery shape.",
    "shelf": "A straight shelf is a rectangular board with stated thickness.",
    "worktop": "A straight worktop is a rectangular slab with stated thickness.",
    "wall-panel": "A flat wall panel is a rectangular construction layer.",
    "plinth": "A joinery plinth is a rectangular support block.",
    "door-leaf": "A flush door leaf has a rectangular solid core.",
    "stair-stringer": "A straight steel stair stringer is a rectangular structural member.",
    "wall-plate": "A flat fixing plate is a rectangular steel member.",
    "rail-bracket": "A simple rail bracket is a rectangular support member.",
    "glass-pane": "A flat glazed pane needs two faces and closed thickness for refraction.",
    "finish-layer": "A planar wall, floor, ceiling, render, paving or turf build-up has rectangular extent.",
    "led-strip": "A straight LED strip has a rectangular diffuser and housing.",
    "tv-panel": "A flat television panel has a rectangular enclosure.",
    "mirror-panel": "A silvered mirror panel has a rectangular substrate.",
    "appliance-front": "An integrated appliance front is a rectangular fascia.",
    "stepping-stone": "A cut rectangular paving stone has a rectangular solid body.",
    "bench-slab": "A thin rectangular paving slab physically supports a garden bench without a plinth.",
    "planter-soil": "Soil fill in a straight rectangular raised bed has a closed rectangular volume.",
}


class PartError(ValueError):
    pass


def _points(faces):
    return [tuple(float(x) for x in p) for face in faces for p in face]


def _cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def _sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def _dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def _key(p):
    return tuple(round(x, 6) for x in p)


def _rectangular_proxy(faces):
    points = _points(faces)
    if not points:
        return False
    axes = [set(round(p[i], 6) for p in points) for i in range(3)]
    # Includes a closed box, an open slab, and a single flat plate.
    return all(len(axis) <= 2 for axis in axes)


def geometry_errors(faces, *, surface=False, occupied_side=None):
    """Check triangle area, closed directed edges, and outward signed volume."""
    if not faces:
        return ["no faces"]
    errors = []
    edges = Counter()
    volume = 0.0
    for face in faces:
        if len(face) < 3:
            errors.append("face has fewer than three vertices")
            continue
        pts = [tuple(map(float, p)) for p in face]
        for a, b in zip(pts, pts[1:] + pts[:1]):
            edges[(_key(a), _key(b))] += 1
        for i in range(1, len(pts)-1):
            a, b, c = pts[0], pts[i], pts[i+1]
            area2 = math.sqrt(_dot(_cross(_sub(b, a), _sub(c, a)),
                                        _cross(_sub(b, a), _sub(c, a))))
            if area2 <= 1e-10:
                errors.append("zero-area triangle")
            volume += _dot(a, _cross(b, c)) / 6.0
    if surface:
        if occupied_side is None or len(occupied_side) != 3 or not any(abs(v) > 1e-9 for v in occupied_side):
            errors.append("surface requires occupied-side direction")
        else:
            for face in faces:
                if len(face) >= 3:
                    normal = _cross(_sub(face[1], face[0]), _sub(face[2], face[0]))
                    if _dot(normal, occupied_side) <= 1e-10:
                        errors.append("surface normal faces away from occupied side")
        return list(dict.fromkeys(errors))
    closed = not any(edges[e] != edges.get((e[1], e[0]), 0) for e in edges)
    if not closed:
        errors.append("open or inconsistently wound edges")
    if closed and abs(volume) <= 1e-10:
        errors.append("zero enclosed volume")
    elif closed and volume < 0:
        errors.append("inward-facing solid")
    return list(dict.fromkeys(errors))


@dataclass(frozen=True)
class Part:
    kind: str
    solid: object
    local_axes: tuple[str, str, str]
    material: str
    basis: str
    support: object = None
    surface: bool = False
    occupied_side: object = None

    def __post_init__(self):
        if not self.kind or not self.material or not self.basis:
            raise PartError("part requires kind, material, and provenance basis")
        if self.local_axes != ("x", "y", "z"):
            raise PartError("part requires declared local x, y, z axes")
        if self.kind == "glass-pane" and self.surface:
            raise PartError("glass pane must be a closed solid")
        if self.basis == "measured-gltf":
            return  # C2 asset intake owns mesh validation and measured dimensions.
        errors = geometry_errors(self.solid, surface=self.surface, occupied_side=self.occupied_side)
        if not self.surface and _rectangular_proxy(self.solid) and self.kind not in BOX_KINDS:
            errors.insert(0, "bare rectangular proxy for " + self.kind)
        if self.support and self.kind == "duvet":
            points = _points(self.solid)
            if len(self.support) == 4:
                x0, y0, x1, y1 = self.support
                support_top = None
            elif len(self.support) == 6:
                x0, y0, _, x1, y1, support_top = self.support
            else:
                raise PartError("support needs four footprint or six solid bounds")
            if any(not (x0 <= p[0] <= x1 and y0 <= p[1] <= y1) for p in points):
                errors.append("duvet leaves mattress footprint")
            if support_top is not None and any(p[2] < support_top - 0.002 for p in points):
                errors.append("duvet intersects mattress support")
        if errors:
            raise PartError("; ".join(dict.fromkeys(errors)))


class PartMeshList(list):
    """One admission path for all scene meshes; report mode preserves failures."""
    def __init__(self, *, collect=False):
        super().__init__()
        self.collect = collect
        self.failures = []

    def append(self, record):
        record = dict(record)
        kind = record.get("part_kind")
        if not kind:
            raise PartError(record.get("id", "unnamed-part") + ": undeclared part kind")
        record["part_kind"] = kind
        record.setdefault("local_axes", ["x", "y", "z"])
        record.setdefault("basis", "authored-procedural")
        try:
            Part(kind, record["faces"], tuple(record["local_axes"]), record["material"],
                 record["basis"], record.get("support"), record.get("surface", False),
                 record.get("occupied_side"))
        except PartError as exc:
            if not self.collect:
                raise PartError(record["id"] + ": " + str(exc)) from exc
            self.failures.append({"id": record["id"], "kind": kind,
                                  "room": record.get("room") or "unassigned", "reason": str(exc)})
        super().append(record)

    def extend(self, records):
        for record in records:
            self.append(record)
