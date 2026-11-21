"""Own geometry code for the parity checks (numpy only).

Independence (REVIT-REPLACEMENT-PLAN principle 2): nothing here imports the
design generators (concept.revit_spec, villa_daylight, villa_render, the model
generator). Units are metres, z up.
"""
from __future__ import annotations

import numpy as np

Box = tuple  # (x0, y0, z0, x1, y1, z1) metres


def fan(poly) -> np.ndarray:
    """Triangulate one convex-ish polygon (list of xyz) by fan -> (n,3,3)."""
    p = np.asarray(poly, float)
    if len(p) < 3:
        return np.zeros((0, 3, 3))
    return np.stack([np.stack([p[0], p[i], p[i + 1]]) for i in range(1, len(p) - 1)])


def aabb(tris: np.ndarray) -> Box:
    p = tris.reshape(-1, 3)
    return (*p.min(0), *p.max(0))


def box_overlap(a: Box, b: Box, shrink: float = 0.0) -> float:
    """Overlap volume of two boxes after shrinking `b` on every side by `shrink`."""
    d = [min(a[i + 3], b[i + 3] - shrink) - max(a[i], b[i] + shrink) for i in range(3)]
    return float(d[0] * d[1] * d[2]) if min(d) > 0 else 0.0


def tris_hit_box(tris: np.ndarray, box: Box, shrink: float) -> np.ndarray:
    """Boolean per triangle: does it pass through `box` shrunk by `shrink` on all sides?
    Separating-axis test (13 axes). A surface lying ON the box boundary (touching) does
    not count: that is the `shrink` margin, i.e. the check's stated resolution."""
    lo = np.array(box[:3]) + shrink
    hi = np.array(box[3:]) - shrink
    if (hi <= lo).any() or len(tris) == 0:
        return np.zeros(len(tris), bool)
    c, h = (lo + hi) / 2, (hi - lo) / 2
    v = tris - c  # (n,3,3)
    ok = np.ones(len(tris), bool)
    # box face normals
    for i in range(3):
        ok &= ~((v[:, :, i].min(1) >= h[i]) | (v[:, :, i].max(1) <= -h[i]))
    e = np.stack([v[:, 1] - v[:, 0], v[:, 2] - v[:, 1], v[:, 0] - v[:, 2]], 1)  # (n,3 edges,3)
    # triangle normal
    n = np.cross(e[:, 0], e[:, 1])
    r = (np.abs(n) * h).sum(1)
    d = (n * v[:, 0]).sum(1)
    ok &= np.abs(d) < r
    ax = np.eye(3)
    for k in range(3):
        for i in range(3):
            a = np.cross(e[:, k], ax[i])  # (n,3)
            p = np.einsum("nvj,nj->nv", v, a)
            rr = (np.abs(a) * h).sum(1)
            ok &= ~((p.min(1) >= rr) | (p.max(1) <= -rr))
    return ok


def ray_up(tris: np.ndarray, origin, zmin: float = 0.0):
    """Nearest hit height of a +z ray from `origin` against triangles (Moller-Trumbore, vertical ray)."""
    o = np.asarray(origin, float)
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    # project to xy: barycentric test, then solve z on the plane
    d = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (c[:, 0] - a[:, 0]) * (b[:, 1] - a[:, 1])
    ok = np.abs(d) > 1e-12
    d = np.where(ok, d, 1.0)
    u = ((o[0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (c[:, 0] - a[:, 0]) * (o[1] - a[:, 1])) / d
    v = ((b[:, 0] - a[:, 0]) * (o[1] - a[:, 1]) - (o[0] - a[:, 0]) * (b[:, 1] - a[:, 1])) / d
    ok &= (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9)
    z = a[:, 2] + u * (b[:, 2] - a[:, 2]) + v * (c[:, 2] - a[:, 2])
    ok &= z > o[2] + zmin
    return float(z[ok].min()) if ok.any() else None


def poly_area_xy(poly) -> float:
    p = np.asarray(poly, float)
    x, y = p[:, 0], p[:, 1]
    return float(abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2)


def box_tris(b: Box) -> np.ndarray:
    """12 triangles of an axis-aligned box (used to turn frozen bounding boxes into solids)."""
    x0, y0, z0, x1, y1, z1 = b
    v = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                  [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]])
    f = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
         (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    return v[np.array(f)]


def _bb(t):
    return t.min(1), t.max(1)


def tri_cross_segments(A: np.ndarray, B: np.ndarray, eps: float = 1e-6, chunk: int = 4_000_000):
    """Proper surface crossings between triangle sets A (n,3,3) and B (m,3,3).

    Returns (m_pairs, 2, 3) segments where a triangle of A passes through a triangle of B:
    each triangle must have vertices strictly on both sides (> eps) of the other's plane, so
    coplanar contact, edge contact and vertex contact are NOT crossings (touching is allowed).
    """
    if len(A) == 0 or len(B) == 0:
        return np.zeros((0, 2, 3)), np.zeros(0)
    alo, ahi = _bb(A)
    blo, bhi = _bb(B)
    out, dep = [], []
    # candidate pairs by AABB, in A-blocks to bound memory
    step = max(1, chunk // max(len(B), 1))
    for s in range(0, len(A), step):
        sl = slice(s, s + step)
        hit = ((alo[sl, None, :] <= bhi[None] + eps) & (ahi[sl, None, :] >= blo[None] - eps)).all(2)
        ia, ib = np.nonzero(hit)
        if len(ia) == 0:
            continue
        a, b = A[sl][ia], B[ib]
        seg, d = _pair_segments(a, b, eps)
        if len(seg):
            out.append(seg); dep.append(d)
    if not out:
        return np.zeros((0, 2, 3)), np.zeros(0)
    return np.concatenate(out), np.concatenate(dep)


def _plane(t):
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    n = n / np.where(ln > 0, ln, 1)
    return n, (n * t[:, 0]).sum(1), ln[:, 0] > 1e-12


def _pair_segments(a, b, eps):
    na, da, oka = _plane(a)
    nb, db, okb = _plane(b)
    dab = np.einsum("nj,nvj->nv", na, b) - da[:, None]   # b verts vs plane a
    dba = np.einsum("nj,nvj->nv", nb, a) - db[:, None]
    ok = oka & okb
    ok &= (dab.max(1) > eps) & (dab.min(1) < -eps) & (dba.max(1) > eps) & (dba.min(1) < -eps)
    if not ok.any():
        return np.zeros((0, 2, 3)), np.zeros(0)
    a, b, na, nb, dab, dba = a[ok], b[ok], na[ok], nb[ok], dab[ok], dba[ok]

    def cut(t, d):  # points where triangle edges cross the other plane -> (n,2,3)
        pts = []
        for i, j in ((0, 1), (1, 2), (2, 0)):
            di, dj = d[:, i], d[:, j]
            cr = (di * dj < 0)
            tt = np.where(cr, di / np.where(cr, di - dj, 1), np.nan)
            p = t[:, i] + tt[:, None] * (t[:, j] - t[:, i])
            pts.append(p)
        pts = np.stack(pts, 1)  # (n,3,3) with nan for no-crossing edges
        res = np.full((len(t), 2, 3), np.nan)
        for k in range(len(t)):
            v = pts[k][~np.isnan(pts[k][:, 0])]
            if len(v) >= 2:
                res[k] = v[:2]
        return res

    sa = cut(a, dba)   # segment of triangle a on plane b
    sb = cut(b, dab)   # segment of triangle b on plane a
    d = np.cross(na, nb)
    dn = np.linalg.norm(d, axis=1)
    good = dn > 1e-9
    d = d / np.where(good, dn, 1)[:, None]
    ta = np.einsum("nsj,nj->ns", sa, d)
    tb = np.einsum("nsj,nj->ns", sb, d)
    lo = np.maximum(np.sort(ta, 1)[:, 0], np.sort(tb, 1)[:, 0])
    hi = np.minimum(np.sort(ta, 1)[:, 1], np.sort(tb, 1)[:, 1])
    good &= (hi - lo > eps) & ~np.isnan(lo) & ~np.isnan(hi)
    if not good.any():
        return np.zeros((0, 2, 3)), np.zeros(0)
    # depth: how far the shorter side of either triangle pokes through the other's plane
    dep = np.minimum(np.minimum(dab.max(1), -dab.min(1)), np.minimum(dba.max(1), -dba.min(1)))[good]
    # points on the common line: take sa's start projected: p = sa0 + (t - ta0) d
    sa0 = sa[good, 0]
    t0 = np.einsum("nj,nj->n", sa0, d[good])
    p0 = sa0 + (lo[good] - t0)[:, None] * d[good]
    p1 = sa0 + (hi[good] - t0)[:, None] * d[good]
    return np.stack([p0, p1], 1), dep


def penetration(seg: np.ndarray, dep: np.ndarray):
    """(depth, region): depth = deepest crossing (see tri_cross_segments), region = AABB of the crossing lines."""
    if len(seg) == 0:
        return 0.0, None
    p = seg.reshape(-1, 3)
    return float(dep.max()), (*p.min(0), *p.max(0))
