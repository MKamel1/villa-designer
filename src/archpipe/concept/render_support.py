"""Nothing in a presentation render may float (client 2026-09-27: "flying plants", "duvet flying"; draft 9 still had
desk-lamp shades hanging in a window, step markers 70 mm off the stair wall, downlights 155 mm below a slab and a
sconce off its wall). A built thing stands on something, hangs from something, or is fixed to the building.

`unsupported(scene)` returns every furniture / fixture / dressing part and every prop with no support. Meshes are
split into their connected parts first (one mesh can hold every door handle in the house, and its joint bounding box
"touched" everything). Touching parts share support (a shade on its stem on its base on a desk). A part is supported
when:
  - its lowest points lie on an upward-facing building surface (a floor, a tread, a sill), or it touches a piece
    that is supported (a cushion on a sofa, a lamp on a desk) -- pieces never support each other in a circle;
  - its top meets a downward-facing surface above its centre (a ceiling, flat or sloped);
  - it touches a building surface that is not glass (a wall, a door leaf, a column, a beam).
Props are placed by their base point: on an upward surface under their footprint; art may hang on a building
surface.

Tolerances, PRE-REGISTERED 2026-09-27 before the first run: 12 mm for resting and hanging (a duvet or a cushion
settles by a few mm), 15 mm for fixing to the building, 10 mm for two parts touching.
"""
from __future__ import annotations

import numpy as np

REST, FIX, TOUCH = 0.012, 0.015, 0.010
ITEM_GROUPS = ("furniture", "fixture", "dressing")


def _islands(faces):
    """Faces grouped into connected parts (shared vertices, to 0.1 mm)."""
    parent = {}

    def find(a):
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    keys = []
    rounded = {}
    for f in faces:
        ks = []
        for v in f:
            point = tuple(v)
            if point not in rounded:
                rounded[point] = tuple(round(c * 10000) for c in v)
            ks.append(rounded[point])
        keys.append(ks[0])
        root = find(ks[0])
        for k in ks[1:]:
            target = find(k)
            parent[root] = target
            root = target
    groups = {}
    for f, k in zip(faces, keys):
        groups.setdefault(find(k), []).append(f)
    return list(groups.values())


def _ear_clip(face):
    """Triangles of a planar polygon, convex or not. Walls around windows are KEYHOLE polygons (the opening joined to
    the outline by a zero-width slit); a fan over them covers the opening, and a lamp arm ending in the glass read as
    fixed to the wall."""
    n = len(face)
    if n == 3:
        return [tuple(face)]
    P = np.array(face, dtype=float)
    nrm = np.zeros(3)
    for k in range(n):                                   # Newell normal
        a, b = P[k], P[(k + 1) % n]
        nrm += [(a[1] - b[1]) * (a[2] + b[2]), (a[2] - b[2]) * (a[0] + b[0]), (a[0] - b[0]) * (a[1] + b[1])]
    ax = int(np.argmax(np.abs(nrm)))
    u, v = [(1, 2), (2, 0), (0, 1)][ax]
    sign = 1.0 if nrm[ax] >= 0 else -1.0
    q = [(P[k][u], P[k][v]) for k in range(n)]

    def cross(o, a, b):
        return ((a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])) * sign

    def inside(p_, a, b, c):
        return cross(a, b, p_) > 1e-12 and cross(b, c, p_) > 1e-12 and cross(c, a, p_) > 1e-12
    idx = list(range(n))
    out = []
    guard = 0
    while len(idx) > 3 and guard < 10 * n:
        guard += 1
        for j in range(len(idx)):
            i0, i1, i2 = idx[j - 1], idx[j], idx[(j + 1) % len(idx)]
            a, b, c = q[i0], q[i1], q[i2]
            if cross(a, b, c) <= 1e-12:
                continue
            if any(inside(q[k], a, b, c) for k in idx if k not in (i0, i1, i2) and q[k] not in (a, b, c)):
                continue
            out.append((face[i0], face[i1], face[i2]))
            idx.pop(j)
            break
        else:
            break
    if len(idx) == 3 and cross(q[idx[0]], q[idx[1]], q[idx[2]]) > 1e-12:
        out.append(tuple(face[k] for k in idx))
    return out


def _triangle_faces(faces):
    """Immutable triangles keyed by exact live float bits and face boundaries."""
    from .build_cache import immutable
    lengths = tuple(len(face) for face in faces)
    points = np.array([p for face in faces for p in face], dtype=float)
    # Binary values retain signed zero, which matters to geometry content
    # hashes even when coordinates compare numerically equal.
    key = (lengths, points.shape, points.tobytes())

    def compute():
        if all(length == 3 for length in lengths):
            result = points.reshape(-1,3,3)
        else:
            triangles = []
            start = 0
            for length in lengths:
                face = points[start:start+length]
                triangles.extend([(face[0], face[k], face[k+1]) for k in range(1,length-1)]
                                 if length <= 4 else _ear_clip(face))
                start += length
            result = np.array(triangles, dtype=float).reshape(-1,3,3)
        result.setflags(write=False)
        return result
    return immutable("face-triangles", key, compute)


def _triangles(meshes):
    # Each call owns fresh writable arrays; cached per-mesh geometry never
    # leaks to a caller. Mesh order, face order and owner indices are unchanged.
    triangles, owners = [], []
    for index, mesh in enumerate(meshes):
        array = _triangle_faces(mesh["faces"])
        triangles.append(array)
        owners.append(np.full(len(array), index, dtype=int))
    return (np.concatenate(triangles) if triangles else np.empty((0,3,3)),
            np.concatenate(owners) if owners else np.empty(0,dtype=int))


class _Surfaces:
    def __init__(self, tris, owner):
        self.t, self.owner = tris, owner
        a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
        n = np.cross(b - a, c - a)
        ln = np.linalg.norm(n, axis=1)
        nz = np.where(ln > 1e-12, n[:, 2] / np.maximum(ln, 1e-12), 0)
        self.up, self.down = nz > 0.5, nz < -0.5
        self.lo, self.hi = tris.min(axis=1), tris.max(axis=1)
        d = (b[:, 1] - c[:, 1]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 1] - c[:, 1])
        self.d = np.where(np.abs(d) < 1e-12, np.nan, d)

    def meets(self, mask, x, y, z, pad=0.003):
        """Any triangle in `mask` under / over (x, y) whose surface passes within REST of z."""
        m = mask & (self.lo[:, 0] - pad <= x) & (x <= self.hi[:, 0] + pad) & (self.lo[:, 1] - pad <= y) & \
            (y <= self.hi[:, 1] + pad) & (self.lo[:, 2] - REST <= z) & (z <= self.hi[:, 2] + REST)
        if not m.any():
            return False
        t, d = self.t[m], self.d[m]
        a, b, c = t[:, 0], t[:, 1], t[:, 2]
        with np.errstate(invalid="ignore"):
            l1 = ((b[:, 1] - c[:, 1]) * (x - c[:, 0]) + (c[:, 0] - b[:, 0]) * (y - c[:, 1])) / d
            l2 = ((c[:, 1] - a[:, 1]) * (x - c[:, 0]) + (a[:, 0] - c[:, 0]) * (y - c[:, 1])) / d
            l3 = 1 - l1 - l2
            e = -0.02
            inside = (l1 >= e) & (l2 >= e) & (l3 >= e)
            zz = l1 * a[:, 2] + l2 * b[:, 2] + l3 * c[:, 2]
            return bool(np.any(inside & (np.abs(zz - z) < REST)))

    def touches(self, mask, box, tol):
        """The part's box, grown by `tol`, intersects a triangle in `mask` (exact: separating-axis test). Exact
        because a wall triangulated around a window has triangles whose bounding boxes span the glass (a box-only
        test passed a lamp arm bracketed to the window), and sampled points missed a handle entering its door leaf."""
        lo, hi = np.array(box[:3]) - tol, np.array(box[3:]) + tol
        m = mask & np.all(self.lo <= hi, axis=1) & np.all(self.hi >= lo, axis=1)
        if not m.any():
            return False
        return bool(_tri_box_overlap(self.t[m], (lo + hi) / 2, (hi - lo) / 2).any())


def _tri_box_overlap(t, c, h):
    """Triangles t (T, 3, 3) against the box centre c, half-sizes h: Akenine-Moller's 13 separating axes."""
    v = t - c
    e = [v[:, 1] - v[:, 0], v[:, 2] - v[:, 1], v[:, 0] - v[:, 2]]
    keep = np.ones(len(t), dtype=bool)
    axes = []
    for ei in e:
        for k in range(3):
            u = np.zeros(3)
            u[k] = 1
            axes.append(np.cross(np.broadcast_to(u, ei.shape), ei))
    for k in range(3):
        a = np.zeros((len(t), 3))
        a[:, k] = 1
        axes.append(a)
    axes.append(np.cross(e[0], e[1]))
    for a in axes:
        p = np.einsum("tij,tj->ti", v, a)
        r = (np.abs(a) * h).sum(axis=1)
        keep &= ~((p.min(axis=1) > r + 1e-12) | (p.max(axis=1) < -r - 1e-12))
    return keep


def _point_triangle_distance(p, t):
    """Distances (P x T) from points p (P, 3) to triangles t (T, 3, 3): the closest-point regions of Ericson,
    Real-Time Collision Detection 5.1.5, vectorised."""
    P = p[:, None, :]
    a, b, c = t[None, :, 0], t[None, :, 1], t[None, :, 2]
    ab, ac, ap = b - a, c - a, P - a
    d1, d2 = (ab * ap).sum(-1), (ac * ap).sum(-1)
    bp = P - b
    d3, d4 = (ab * bp).sum(-1), (ac * bp).sum(-1)
    cp = P - c
    d5, d6 = (ab * cp).sum(-1), (ac * cp).sum(-1)
    va, vb, vc = d3 * d6 - d5 * d4, d5 * d2 - d1 * d6, d1 * d4 - d3 * d2
    with np.errstate(divide="ignore", invalid="ignore"):
        denom = va + vb + vc
        v = np.where(denom != 0, vb / denom, 0)
        w = np.where(denom != 0, vc / denom, 0)
        q = a + ab * v[..., None] + ac * w[..., None]                                    # inside the face
        vab = d1 / (d1 - d3)
        q = np.where(((vc <= 0) & (d1 >= 0) & (d3 <= 0))[..., None], a + ab * vab[..., None], q)
        vac = d2 / (d2 - d6)
        q = np.where(((vb <= 0) & (d2 >= 0) & (d6 <= 0))[..., None], a + ac * vac[..., None], q)
        vbc = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        q = np.where(((va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0))[..., None], b + (c - b) * vbc[..., None], q)
    q = np.where(((d1 <= 0) & (d2 <= 0))[..., None], a, q)
    q = np.where(((d3 >= 0) & (d4 <= d3))[..., None], b, q)
    q = np.where(((d6 >= 0) & (d5 <= d6))[..., None], c, q)
    return np.linalg.norm(P - q, axis=-1)


def unsupported(scene, lay=None):
    meshes = scene["meshes"]
    tris, owner = _triangles(meshes)
    all_surfaces = _Surfaces(tris, owner)
    is_item = np.array([m["group"] in ITEM_GROUPS for m in meshes])
    glass = np.array([m["material"].startswith("glass") for m in meshes])
    building = (~is_item[owner]) & (~glass[owner])
    # Item triangles cannot ground an assembly. Restrict these repeated
    # contact queries to the exact existing building mask, preserving all
    # faces and tolerances; dense botanical triangles remain in island
    # connectivity and in the separate prop support query below.
    S = _Surfaces(tris[building], owner[building])
    building = np.ones(len(S.t), dtype=bool)
    parts = {}
    for i, m in enumerate(meshes):
        if not is_item[i]:
            continue
        for k, faces in enumerate(_islands(m["faces"])):
            pts = np.array([p for f in faces for p in f], dtype=float)
            box = list(pts.min(axis=0)) + list(pts.max(axis=0))
            low = pts[pts[:, 2] <= box[2] + 0.005]
            parts[(i, k)] = (box, low[:: max(1, len(low) // 8)])
    ok = {}
    for (i, k), (b, low) in parts.items():
        # only the BUILDING grounds a group; resting on another piece only joins its group (the first version let a
        # lamp arm "rest" on its own shade while the shade hung from the arm: circular support)
        ok[(i, k)] = (any(S.meets(S.up & building, x, y, z) for x, y, z in low)
                      or S.meets(S.down & building, (b[0] + b[3]) / 2, (b[1] + b[4]) / 2, b[5])
                      or S.touches(building, b, FIX))
    keys = list(parts)
    parent = {k: k for k in keys}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    boxes = np.array([parts[k][0] for k in keys])
    for n, key in enumerate(keys):
        b = boxes[n]
        near = np.where(np.all(np.minimum(boxes[:, 3:], b[3:]) - np.maximum(boxes[:, :3], b[:3]) > -TOUCH, axis=1))[0]
        for j in near:
            if j != n:
                parent[find(key)] = find(keys[j])
    grounded = {find(k) for k in keys if ok[k]}
    out = [(meshes[i]["id"], [round(float(v), 3) for v in parts[(i, k)][0]]) for (i, k) in keys
           if find((i, k)) not in grounded]
    S = all_surfaces
    building = (~is_item[owner]) & (~glass[owner])
    for p in scene.get("props", []):
        x, y, z = p["position"]
        if any(S.meets(S.up, x + dx, y + dy, z) for dx, dy in ((0, 0), (0.1, 0), (-0.1, 0), (0, 0.1), (0, -0.1))):
            continue
        if "art" in p["label"] and S.touches(building, [x - 0.05, y - 0.05, z, x + 0.05, y + 0.05, z + 0.5], 0.06):
            continue
        out.append((p["id"], p["position"]))
    return out


def blocked_openings(scene, lay=None):
    """Every door must be passable: no furniture, dressing or render detail inside a door's passage (its clear width
    less 20 mm, 0.35 m either side of the wall line, from 50 mm to 2.0 m above the floor). Found after the client saw
    the parents' entrance closed by a slatted headboard panel that also covered the dressing door."""
    from . import revit_spec as RS
    from . import villa_furnish as F
    from . import villa_r11 as R
    from .villa_render import LZ
    lay = lay or R.design("D1")
    sp = RS.build(lay)
    out = []
    parts = []
    for m in scene["meshes"]:
        if m["group"] not in ITEM_GROUPS or "handle" in m["id"]:
            continue
        for faces in _islands(m["faces"]):
            pts = np.array([p for f in faces for p in f], dtype=float)
            parts.append((m["id"], pts.min(axis=0), pts.max(axis=0)))
    # doorless openings: where two rooms of a storey share an edge and no wall stands on it (the parents' entry)
    openings = []
    rooms = [(rid, r) for rid, r in lay["rooms"].items()]
    for i, (ra, a_) in enumerate(rooms):
        for rb, b_ in rooms[i + 1:]:
            if a_["level"] != b_["level"]:
                continue
            A, B = a_["rect"], b_["rect"]
            walls = F._walls(sp, a_["level"])
            for horiz, line, s0, s1 in (
                    (True, A[3], max(A[0], B[0]), min(A[2], B[2])) if abs(A[3] - B[1]) < 0.02 else (None,) * 4,
                    (True, A[1], max(A[0], B[0]), min(A[2], B[2])) if abs(A[1] - B[3]) < 0.02 else (None,) * 4,
                    (False, A[2], max(A[1], B[1]), min(A[3], B[3])) if abs(A[2] - B[0]) < 0.02 else (None,) * 4,
                    (False, A[0], max(A[1], B[1]), min(A[3], B[3])) if abs(A[0] - B[2]) < 0.02 else (None,) * 4):
                if horiz is None or s1 - s0 < 0.6:
                    continue
                run = []
                v = s0 + 0.025
                while v < s1:
                    x, y = (v, line) if horiz else (line, v)
                    free = not any(w[0] - 0.01 <= x <= w[2] + 0.01 and w[1] - 0.06 <= y <= w[3] + 0.06 for w in walls)                         if horiz else not any(w[0] - 0.06 <= x <= w[2] + 0.06 and w[1] - 0.01 <= y <= w[3] + 0.01
                                              for w in walls)
                    if free:
                        run.append(v)
                    elif run:
                        openings.append((a_["level"], horiz, line, run[0], run[-1], ra + "/" + rb))
                        run = []
                    v += 0.05
                if run:
                    openings.append((a_["level"], horiz, line, run[0], run[-1], ra + "/" + rb))
    for lv, horiz, line, v0, v1, name in openings:
        # a PASSAGE is 0.6-1.6 m wide; wider shared edges are zones of one open-plan space, not openings
        if not 0.6 <= v1 - v0 + 0.05 <= 1.6:
            continue
        z0 = LZ[lv]
        lo = np.array([v0, line - 0.35, z0 + 0.05]) if horiz else np.array([line - 0.35, v0, z0 + 0.05])
        hi = np.array([v1, line + 0.35, z0 + 2.0]) if horiz else np.array([line + 0.35, v1, z0 + 2.0])
        for mid, a, b in parts:
            # the furnished-plan route check (villa_furnish, 914 mm body) already clears furniture in passages; it
            # cannot see render-only details or hanging fixtures, which is how the slat panel closed the entry
            if not (mid.startswith("detail-") or mid.split("-")[0] in ("lamp", "cord", "canopy", "fix", "bracket")):
                continue
            if mid.startswith("detail-stair-") and "stair-" in name:
                continue  # the stringers and handrails define the stair edge and its access, not a room passage
            if np.all(np.minimum(b, hi) - np.maximum(a, lo) > 0.005):
                out.append((mid, "opening %s" % name))
    for d in sp["doors"]:
        h = F._door_axis(d) == "h"
        hw = d["width"] / 2 - 0.02
        z0 = LZ[d["level"]]
        lo = np.array([d["x"] - hw, d["y"] - 0.35, z0 + 0.05]) if h else np.array([d["x"] - 0.35, d["y"] - hw, z0 + 0.05])
        hi = np.array([d["x"] + hw, d["y"] + 0.35, z0 + 2.0]) if h else np.array([d["x"] + 0.35, d["y"] + hw, z0 + 2.0])
        for mid, a, b in parts:
            if np.all(np.minimum(b, hi) - np.maximum(a, lo) > 0.005):
                out.append((mid, "door %s at (%.2f, %.2f)" % ("/".join(d.get("rooms") or []), d["x"], d["y"])))
    return sorted(set(out))
