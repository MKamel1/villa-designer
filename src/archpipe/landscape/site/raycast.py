"""Vectorised ray/segment tests against the project's opaque enclosure triangles.

The triangles are exactly those `concept.garden_sun.default_study()` uses (glass excluded; plants and
furniture absent), so sun results agree with the earlier garden sun studies. Two-sided Moller-Trumbore.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np


@lru_cache(maxsize=1)
def triangles():
    from ...concept import garden_sun
    return garden_sun.default_study().triangles


def inside_solid(points, tris=None):
    """Odd-parity test: a point inside a closed solid meets an odd number of triangles along any ray.
    Used to drop cells whose centre lies inside a thin modelled solid (a 50 mm guard rail), which would read as 0 h of sun."""
    tris = triangles() if tris is None else tris
    a = tris[:, 0]; e1 = tris[:, 1] - a; e2 = tris[:, 2] - a
    d = np.array([0.0131, 0.0071, 1.0]) * 50.0
    out = []
    for o in np.asarray(points, float):
        p = np.cross(d, e2)
        det = e1 @ d * 0 + np.einsum("mk,mk->m", e1, p)
        ok = np.abs(det) > 1e-10
        inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
        tv = o - a
        u = np.einsum("mk,mk->m", tv, p) * inv
        q = np.cross(tv, e1)
        v = (q @ d) * inv
        t = np.einsum("mk,mk->m", e2, q) * inv
        out.append(int((ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-6) & (t < 1)).sum()) % 2 == 1)
    return np.array(out)


def blocked(origins, directions, tmin, tmax, tris=None, chunk=128):
    """True where origin + t*direction hits a triangle for tmin < t < tmax (direction is NOT normalised)."""
    tris = triangles() if tris is None else tris
    a = tris[:, 0]
    e1 = tris[:, 1] - a
    e2 = tris[:, 2] - a
    o = np.asarray(origins, float).reshape(-1, 3)
    d = np.asarray(directions, float).reshape(-1, 3)
    tmin = np.broadcast_to(np.asarray(tmin, float), (len(o),))
    tmax = np.broadcast_to(np.asarray(tmax, float), (len(o),))
    out = np.zeros(len(o), bool)
    for s in range(0, len(o), chunk):
        sl = slice(s, s + chunk)
        dd, oo = d[sl][:, None, :], o[sl][:, None, :]
        p = np.cross(dd, e2[None])                       # (n, m, 3)
        det = np.einsum("mk,nmk->nm", e1, p)
        ok = np.abs(det) > 1e-10
        inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
        tv = oo - a[None]
        u = np.einsum("nmk,nmk->nm", tv, p) * inv
        q = np.cross(tv, e1[None])
        v = np.einsum("nmk,nmk->nm", dd * np.ones_like(q), q) * inv
        t = np.einsum("mk,nmk->nm", e2, q) * inv
        hit = ok & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9) & (t > tmin[sl][:, None]) & (t < tmax[sl][:, None])
        out[sl] = hit.any(axis=1)
    return out
