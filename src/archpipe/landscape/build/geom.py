"""Mesh primitives and the object model of the garden build. Pure Python + numpy (no Blender).

Units metres, model frame (x east, y north, z up), as the layout. A `Part` is one closed solid (or a flat patch):
verts (n,3) and polygon faces (CCW seen from outside). An `Obj` is one built element carrying its `ld-*` id.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Part:
    material: str
    verts: np.ndarray                  # (n, 3)
    faces: list                        # list of index lists
    envelope: tuple | None = None      # plants: (cx, cy, cz, rx, ry, rz) ellipsoid used for clip tests
    poly: list | None = None           # plan outline for prisms (exact clip tests)

    def bounds(self):
        if self.envelope:
            cx, cy, cz, rx, ry, rz = self.envelope
            return (cx - rx, cy - ry, cz - rz, cx + rx, cy + ry, cz + rz)
        lo, hi = self.verts.min(0), self.verts.max(0)
        return (*lo, *hi)


@dataclass
class Obj:
    id: str                            # ld-* element id (RV1 / P2)
    kind: str                          # paving, bed, pergola-post, ...
    label: str                         # what it is, incl. ASSUMED / stand-in wording
    parts: list = field(default_factory=list)
    layout_id: str | None = None       # id in the landscape-layout/1 source
    footprint: tuple | None = None     # declared plan rect (x0,y0,x1,y1) from the layout
    footprint_poly: object = None      # shapely geometry, for non-rectangular declared footprints
    footprint_mode: str | None = "bbox"   # bbox | within | poly | None
    rests_on: tuple = ("ground",)      # 'ground' or ids of supporting objects
    state: str | None = None           # None = always, else 'closed'/'open' (fire pit cover)
    standin: bool = False              # generic mass for a species with no drawable asset
    asset: dict | None = None          # drawn from a graded 3D asset (placement spec)
    meta: dict = field(default_factory=dict)

    def bounds(self):
        b = np.array([p.bounds() for p in self.parts]) if self.parts else None
        if b is not None:
            return (*b[:, :3].min(0), *b[:, 3:].max(0))
        if self.asset:
            return tuple(self.asset["bounds"])
        raise ValueError("object %s has no geometry" % self.id)


def _prism_faces(n):
    top = list(range(n, 2 * n))
    return [list(range(n - 1, -1, -1)), top] + [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]


def prism(material, poly, z0, z1):
    """Extruded CCW polygon (no holes)."""
    poly = list(poly)
    area = sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))
    if area < 0:
        poly = poly[::-1]
    v = np.array([(x, y, z0) for x, y in poly] + [(x, y, z1) for x, y in poly], float)
    return Part(material, v, _prism_faces(len(poly)), poly=poly)


def box(material, x0, y0, z0, x1, y1, z1):
    return prism(material, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1)


def rbox(material, x0, y0, x1, y1, z0, z1):
    """Box from a plan rect (x0,y0,x1,y1) and a z range."""
    return box(material, x0, y0, z0, x1, y1, z1)


def cyl(material, cx, cy, r, z0, z1, n=24, r_top=None):
    """Cylinder / frustum; vertices at 0, 90, 180, 270 degrees so the plan bbox is exactly 2r."""
    rt = r if r_top is None else r_top
    v = np.array([(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n), z0) for i in range(n)] +
                 [(cx + rt * math.cos(2 * math.pi * i / n), cy + rt * math.sin(2 * math.pi * i / n), z1) for i in range(n)], float)
    return Part(material, v, _prism_faces(n), poly=[tuple(p[:2]) for p in v[:n]])


def slanted_slat(material, s0, s1, pos, z, width, thick, tilt_deg, axis="x"):
    """A louvre blade running along `axis` between s0 and s1, centred at (pos, z) across it, tilted about its long axis."""
    c, s = math.cos(math.radians(tilt_deg)), math.sin(math.radians(tilt_deg))
    pts = []
    for dy, dz in ((-width / 2, -thick / 2), (width / 2, -thick / 2), (width / 2, thick / 2), (-width / 2, thick / 2)):
        pts.append((pos + dy * c - dz * s, z + dy * s + dz * c))
    if axis == "x":
        v = [(s0, py, pz) for py, pz in pts] + [(s1, py, pz) for py, pz in pts]
    else:
        v = [(py, s0, pz) for py, pz in pts] + [(py, s1, pz) for py, pz in pts]
    faces = [[3, 2, 1, 0], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
    if axis == "y":
        faces = [f[::-1] for f in faces]
    return Part(material, np.array(v, float), faces)


def ellipsoid(material, cx, cy, cz, rx, ry, rz, nu=16, nv=10):
    """Closed ellipsoid mesh whose extents are exactly 2rx, 2ry, 2rz (poles on z; equator vertices on the axes)."""
    v = [(cx, cy, cz - rz)]
    for j in range(1, nv):
        phi = -math.pi / 2 + math.pi * j / nv
        for i in range(nu):
            th = 2 * math.pi * i / nu
            v.append((cx + rx * math.cos(phi) * math.cos(th), cy + ry * math.cos(phi) * math.sin(th), cz + rz * math.sin(phi)))
    v.append((cx, cy, cz + rz))
    top = len(v) - 1
    f = [[0, 1 + (i + 1) % nu, 1 + i] for i in range(nu)]
    for j in range(nv - 2):
        a, b = 1 + j * nu, 1 + (j + 1) * nu
        f += [[a + i, a + (i + 1) % nu, b + (i + 1) % nu, b + i] for i in range(nu)]
    last = 1 + (nv - 2) * nu
    f += [[last + i, last + (i + 1) % nu, top] for i in range(nu)]
    return Part(material, np.array(v, float), f, envelope=(cx, cy, cz, rx, ry, rz))
