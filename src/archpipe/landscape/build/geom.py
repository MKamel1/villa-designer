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
    winter_parts: list = field(default_factory=list)   # a deciduous plant's leaf-off geometry (stems and twigs); empty = evergreen, one geometry all year

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


def tube(material, p0, p1, r0, r1=None, n=6):
    """Tapered round stem from p0 to p1 (any direction), n sides. A limb or twig: no envelope, bounds from its vertices."""
    r1 = r0 if r1 is None else r1
    a = np.array(p0, float); b = np.array(p1, float)
    d = b - a
    L = float(np.linalg.norm(d))
    d = d / L
    h = np.array([1.0, 0, 0]) if abs(d[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(d, h); u /= np.linalg.norm(u)
    w = np.cross(d, u)
    ring = lambda c, r: [c + r * (math.cos(2 * math.pi * i / n) * u + math.sin(2 * math.pi * i / n) * w) for i in range(n)]
    v = np.array(ring(a, r0) + ring(b, r1), float)
    return Part(material, v, _prism_faces(n))


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


def extrude_profile(material, prof, a0, a1, across="y", origin=0.0, flip=False):
    """Closed solid from a (s, z) profile polygon extruded along the other plan axis from a0 to a1.

    `across` is the plan axis s runs along ('y': section across y, extruded along x; 'x': the reverse); s is measured from `origin`
    (or from `origin` downwards when `flip`). Used for pond sections: the profile is the measured cross-section, not a box stack.
    """
    pts = [((origin - s) if flip else (origin + s), z) for s, z in prof]
    n = len(pts)
    def v(a, i):
        s, z = pts[i]
        return (a, s, z) if across == "y" else (s, a, z)
    verts = np.array([v(a0, i) for i in range(n)] + [v(a1, i) for i in range(n)], float)
    area = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
    ccw = (area > 0) != (across == "x")                 # orientation of (s, z) seen along the extrusion axis
    side = [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    faces = [list(range(n - 1, -1, -1)), list(range(n, 2 * n))] + side
    if not ccw:
        faces = [f[::-1] for f in faces]
    return Part(material, verts, faces)


def half_frustum(material, cx, cy, r, z0, z1, r_top=None, axis="y", sign=1, n=24):
    """Half of a cylinder / frustum: the side of the line through (cx, cy) along `axis` where the other coordinate has the given `sign`."""
    rt = r if r_top is None else r_top
    a0 = {("y", 1): 0.0, ("y", -1): math.pi, ("x", 1): -math.pi / 2, ("x", -1): math.pi / 2}[(axis, sign)]
    ang = [a0 + math.pi * i / n for i in range(n + 1)]
    v = np.array([(cx + r * math.cos(a), cy + r * math.sin(a), z0) for a in ang] + [(cx + rt * math.cos(a), cy + rt * math.sin(a), z1) for a in ang], float)
    return Part(material, v, _prism_faces(n + 1), poly=[tuple(p[:2]) for p in v[:n + 1]])


def shifted(part, dx=0.0, dy=0.0, dz=0.0):
    v = part.verts + np.array([dx, dy, dz])
    return Part(part.material, v, part.faces, poly=[(x + dx, y + dy) for x, y in part.poly] if part.poly else None)
