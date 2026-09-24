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
