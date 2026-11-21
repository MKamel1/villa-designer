"""Plan geometry for the lighting engine: arbitrary (non-convex) polygon rooms.

Pure standard library. Units: metres, z up. A polygon is a list of (x, y)
vertices, not repeated at the end, either winding.
"""
from __future__ import annotations

import math

Point = tuple[float, float]


def signed_area(poly: list[Point]) -> float:
    s = 0.0
    for i, (x0, y0) in enumerate(poly):
        x1, y1 = poly[(i + 1) % len(poly)]
        s += x0 * y1 - x1 * y0
    return s / 2.0


def area(poly: list[Point]) -> float:
    return abs(signed_area(poly))


def perimeter(poly: list[Point]) -> float:
    return sum(math.dist(poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly)))


def bbox(poly: list[Point]) -> tuple[float, float, float, float]:
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


def ccw(poly: list[Point]) -> list[Point]:
    return list(poly) if signed_area(poly) > 0 else list(reversed(poly))


def point_in_polygon(pt: Point, poly: list[Point]) -> bool:
    """Even-odd rule; points exactly on an edge count as inside."""
    x, y = pt
    n = len(poly)
    inside = False
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        # on-edge test
        cross = (x1 - x0) * (y - y0) - (y1 - y0) * (x - x0)
        if abs(cross) < 1e-12 and min(x0, x1) - 1e-12 <= x <= max(x0, x1) + 1e-12 \
                and min(y0, y1) - 1e-12 <= y <= max(y0, y1) + 1e-12:
            return True
        if (y0 > y) != (y1 > y):
            xin = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
            if x < xin:
                inside = not inside
    return inside


def dist_to_edges(pt: Point, poly: list[Point]) -> float:
    best = float("inf")
    px, py = pt
    for i in range(len(poly)):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % len(poly)]
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
        best = min(best, math.hypot(px - (ax + t * dx), py - (ay + t * dy)))
    return best


def en12464_spacing(d: float) -> float:
    """Grid cell size p = 0.2 * 5^log10(d) (EN 12464-1 Annex / CIE 5.x guidance;
    d = longer side of the area, metres). STD: the standard is not held, so the
    rule is recorded as a policy default in the report, never as a verdict."""
    return 0.2 * 5.0 ** math.log10(max(d, 0.1))


def grid_in_polygon(poly: list[Point], *, spacing: float | None = None,
                    border: float = 0.0) -> tuple[list[Point], float, float]:
    """Cell-centred sample points inside a polygon (any shape), at least
    `border` metres from every edge. Returns (points, dx, dy).

    With spacing=None the EN 12464-1 cell size for the bounding box's longer
    side is used. The fitted per-axis spacing never exceeds the request.
    """
    x0, y0, x1, y1 = bbox(poly)
    if spacing is None:
        spacing = en12464_spacing(max(x1 - x0, y1 - y0))
    nx = max(1, math.ceil((x1 - x0) / spacing - 1e-9))
    ny = max(1, math.ceil((y1 - y0) / spacing - 1e-9))
    dx, dy = (x1 - x0) / nx, (y1 - y0) / ny
    pts = []
    for j in range(ny):
        for i in range(nx):
            p = (x0 + (i + 0.5) * dx, y0 + (j + 0.5) * dy)
            if point_in_polygon(p, poly) and (border <= 0 or dist_to_edges(p, poly) >= border - 1e-9):
                pts.append(p)
    if not pts:
        raise ValueError("no grid point falls inside the polygon (border too large?)")
    return pts, dx, dy


def outward_edges(poly: list[Point]) -> list[tuple[Point, Point, Point]]:
    """(start, end, outward unit normal) per edge, for any winding."""
    p = ccw(poly)
    out = []
    for i in range(len(p)):
        a, b = p[i], p[(i + 1) % len(p)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        out.append((a, b, (dy / L, -dx / L)))   # CCW polygon: outward = right of the edge
    return out
