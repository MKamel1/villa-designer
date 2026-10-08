"""Frozen route implementation at starting commit f8f8cc6; differential evidence only."""
from archpipe.concept.villa_landscape import PATHS, TOP_SURFACE, GROUND, _rect, _rect_overlap_area
def route_violations(items, routes=PATHS, route_ground=None):
    """Physical walking envelopes from ground to 2.0 m, for every prop/mesh.

    Height basis: render_support.blocked_openings uses the same 2.0 m
    passage height. Prop triangles (including node transforms and floor
    seating) are intersected with each envelope; high canopy alone cannot
    obstruct walking. Rect-only legacy objects conservatively occupy the
    envelope unless explicit bottom/top elevations are supplied.
    route_ground optionally maps route names to floor elevations in metres.
    """
    import numpy as np
    from archpipe.concept.route_geometry import prop_triangles
    from archpipe.concept.render_support import _tri_box_overlap, _triangles
    out = []
    for item in items:
        # Validate every placed asset, including props clear of all routes.
        triangles = prop_triangles(item) if "asset" in item else None
        rect = _rect(item)
        candidates = [(name, route) for name, route in routes.items()
                      if _rect_overlap_area(rect, route) > 1e-6]
        if not candidates:
            continue
        if "faces" in item and "asset" not in item:
            triangles, _ = _triangles([item])
        for name, route in candidates:
            ground = (route_ground or {}).get(name, TOP_SURFACE if name in ("study", "gate-link") else GROUND)
            if "asset" in item:
                # A lower placement/higher route floor may reach omitted canopy.
                prop_triangles(item, walking_top_m=ground+2.0)
            low = np.array([route[0], route[1], ground])
            high = np.array([route[2], route[3], ground+2.0])
            if triangles is not None:
                nearby = np.all(triangles.min(axis=1) <= high, axis=1) & np.all(triangles.max(axis=1) >= low, axis=1)
                blocked = nearby.any() and _tri_box_overlap(triangles[nearby], (low+high)/2, (high-low)/2).any()
            else:
                blocked = item.get("bottom_m", ground) < high[2] and item.get("top_m", high[2]) > low[2]
            if blocked:
                out.append((item["id"], name))
    return out
