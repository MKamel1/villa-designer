"""Small geometry helpers (shapely is already a dependency)."""
from __future__ import annotations

import math

from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union


def R(a0, b0, a1, b1):
    return [min(a0, a1), min(b0, b1), max(a0, a1), max(b0, b1)]


def rbox(r):
    return box(*r)


def rects_of(poly, min_area=0.02):
    """Decompose a rectilinear (multi)polygon into axis-aligned rects by horizontal slabs."""
    if poly.is_empty:
        return []
    polys = list(poly.geoms) if hasattr(poly, "geoms") else [poly]
    out = []
    for p in polys:
        ys = sorted({round(c[1], 4) for c in p.exterior.coords} | {round(c[1], 4) for i in p.interiors for c in i.coords})
        for y0, y1 in zip(ys, ys[1:]):
            mid = (y0 + y1) / 2
            line = box(p.bounds[0] - 1, mid - 1e-6, p.bounds[2] + 1, mid + 1e-6).intersection(p)
            segs = list(line.geoms) if hasattr(line, "geoms") else [line]
            for s in segs:
                if s.is_empty or s.length < 1e-3:
                    continue
                x0, _, x1, _ = s.bounds
                if (x1 - x0) * (y1 - y0) >= min_area:
                    out.append([round(x0, 3), round(y0, 3), round(x1, 3), round(y1, 3)])
    return out


def largest_rect(poly, step=0.1):
    """Largest axis-aligned rectangle inside `poly` (raster histogram method, `step` m resolution)."""
    if poly.is_empty:
        return None
    x0, y0, x1, y1 = poly.bounds
    nx, ny = int((x1 - x0) / step), int((y1 - y0) / step)
    from shapely import contains_xy
    import numpy as np
    xs = x0 + (np.arange(nx) + .5) * step
    ys = y0 + (np.arange(ny) + .5) * step
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    m = contains_xy(poly, X, Y)
    best, br = 0.0, None
    h = [0] * ny
    for i in range(nx):
        for j in range(ny):
            h[j] = h[j] + 1 if m[i, j] else 0
        st = []
        for j in range(ny + 1):
            cur = h[j] if j < ny else 0
            start = j
            while st and st[-1][1] >= cur:
                s0, hh = st.pop()
                area = hh * (j - s0)
                if area > best:
                    best, br = area, (i - hh + 1, s0, i, j - 1)
                start = s0
            st.append((start, cur))
    if not br:
        return None
    i0, j0, i1, j1 = br
    return [round(x0 + i0 * step, 3), round(y0 + j0 * step, 3), round(x0 + (i1 + 1) * step, 3), round(y0 + (j1 + 1) * step, 3)]


def circle(c, d):
    return Point(*c).buffer(d / 2, 24)


def union(shapes):
    shapes = [s for s in shapes if s is not None and not s.is_empty]
    return unary_union(shapes) if shapes else Polygon()


def area(r):
    return (r[2] - r[0]) * (r[3] - r[1])
