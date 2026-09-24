"""Where a light fixture actually emits, measured from its modelled geometry.

A family's insertion point is not its light source. The bedroom's pendants
were placed so their INSERTION points sat at the spec heights, and every
consumer (render, lux engine, Radiance) read that same insertion height, so
render and calculation agreed while the light sat 240-470 mm away from the
fittings: a drum lamp floated below its drum, a cone lamp above its shade
(render_critic, 2026-09-24). This is the one definition of the source point.

Basis, in order of preference:
1. `light_source_symbol`: Revit's Light Source subcategory geometry. For a
   downlight it is the cone the family draws from its source, so the source
   is its apex: top z, centre x/y.
2. The lens: a mesh whose material name contains "lens". The luminous
   opening; LM-63 photometric centre convention. Centre x/y, mid z.
3. None: no evidence in the geometry; the caller must say so.
"""
from __future__ import annotations


def _bbox(vertices):
    xs = [v[0] for v in vertices]
    ys = [v[1] for v in vertices]
    zs = [v[2] for v in vertices]
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)


def source_point(meshes):
    """(x_mm, y_mm, z_mm, basis) from extract meshes, or None."""
    symbol = [m for m in meshes or [] if m.get("geometry_role") == "light_source_symbol"
              and m.get("vertices_mm")]
    if symbol:
        pts = [v for m in symbol for v in m["vertices_mm"]]
        x0, x1, y0, y1, _, z1 = _bbox(pts)
        return ((x0 + x1) / 2.0, (y0 + y1) / 2.0, z1, "light_source_symbol apex")
    lens = [m for m in meshes or [] if "lens" in str((m.get("material") or {}).get("name", "")).lower()
            and m.get("vertices_mm")]
    if lens:
        pts = [v for m in lens for v in m["vertices_mm"]]
        x0, x1, y0, y1, z0, z1 = _bbox(pts)
        return ((x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0, "lens centre")
    return None


def lens_extent(meshes):
    """Plan extent (long, short) in mm of the fitting's lens, or None."""
    pts = [v for m in meshes or [] if "lens" in str((m.get("material") or {}).get("name", "")).lower()
           for v in m.get("vertices_mm") or []]
    if not pts:
        return None
    x0, x1, y0, y1, _, _ = _bbox(pts)
    return max(x1 - x0, y1 - y0), min(x1 - x0, y1 - y0)


def photometry_matches_fitting(ies_dims_mm, meshes, size_ratio=2.0, aspect_ratio=3.0):
    """Problems (list of str) when the IES luminous opening cannot be this fitting.

    A photometric file describes one real product. Measured on the bedroom:
    a 594 x 24 mm strip file was on a 1826 mm linear (LT-04) and on a 276 mm
    round drum (LT-05); nothing compared the two, so a drum was lit as a
    strip. Limits are deliberately loose (x2 size, x3 aspect): this catches
    a different product, not a tolerance.
    """
    lens = lens_extent(meshes)
    dims = sorted((abs(v) for v in ies_dims_mm[:2] if abs(v) > 0.5), reverse=True)
    if lens is None or not dims:
        return []
    out = []
    ies_long = dims[0]
    ies_short = dims[1] if len(dims) > 1 else dims[0]   # a single dimension is round
    if not (1 / size_ratio <= ies_long / lens[0] <= size_ratio):
        out.append("IES opening %.0f mm vs fitting lens %.0f mm" % (ies_long, lens[0]))
    ies_aspect = ies_long / max(ies_short, 1.0)
    lens_aspect = lens[0] / max(lens[1], 1.0)
    if max(ies_aspect, lens_aspect) / min(ies_aspect, lens_aspect) > aspect_ratio:
        out.append("IES shape %.0f:1 vs fitting lens %.0f:1" % (ies_aspect, lens_aspect))
    return out
