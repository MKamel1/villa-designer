"""Walking-envelope geometry from tracked records, in scene metres.

Native glTF axes are converted to scene x/-z/y by the render-host generator.
The record retains walking-band triangle topology at declared precision and
unrounded full-height convex-hull vertices for framing.
"""
import numpy as np
from ..asset_route_record import recorded_geometry


def _placed_geometry(prop, framing=False, walking_top_m=None):
    """Apply a covered scale/yaw and seat using the original asset base."""
    if any(abs(v)>1e-9 for v in prop.get('rotation_deg',[0,0,0])[:2]):
        raise ValueError('tilted prop route geometry not supported')
    from math import cos,sin,radians
    triangles, vertices, row = recorded_geometry(prop['asset'])
    scale = np.asarray(prop.get('scale',1.0), dtype=float)
    minimum, maximum = row['scale_range']
    if (scale.shape not in ((), (3,)) or not np.isfinite(scale).all()
            or np.any(scale < minimum) or np.any(scale > maximum)
            or (row['scale_mode'] == 'uniform' and scale.shape != ())):
        raise ValueError(f"asset {prop['asset']}: scale outside recorded range {row['scale_range']} "
                         f"or unsupported nonuniform scale; regenerate with a covering policy")
    vertical_scale = float(scale if scale.shape == () else scale[2])
    covered_top = prop['position'][2] + (row['walking_band_native']['top'] -
                                       row['walking_band_native']['base']) * vertical_scale
    if walking_top_m is not None and walking_top_m > covered_top + 1e-9:
        raise ValueError(f"asset {prop['asset']}: walking envelope exceeds recorded band; regenerate with a covering policy")
    native = vertices if framing else triangles
    triangles=native*scale
    yaw=radians(prop.get('rotation_deg',[0,0,0])[2]);c,s=cos(yaw),sin(yaw)
    triangles=triangles@np.array([[c,s,0],[-s,c,0],[0,0,1]])
    triangles[...,2]-=row['walking_band_native']['base'] * vertical_scale
    return triangles+np.array(prop['position'])


def prop_triangles(prop, walking_top_m=None):
    """Exact walking triangles; supplied world envelope top must be covered."""
    if walking_top_m is None:
        walking_top_m = prop['position'][2] + 2.0
    return _placed_geometry(prop, walking_top_m=walking_top_m)


def prop_framing_points(prop):
    """Exact full-height hull vertices for convex framing and plan extrema."""
    return _placed_geometry(prop, framing=True)


def nearest_clear_translation(triangles, bounds, routes, route_ground, height=2.0, clearance=1e-6):
    """Nearest horizontal translation of actual triangles in a bounded domain.

    bounds is (minimum x shift, minimum y shift, maximum x shift, maximum
    y shift), in metres. routes maps names to walking rectangles; route_ground
    maps those names to floor heights. Clip triangles to each walking height
    band, then subtract every forbidden translation polygon from the domain.
    A forbidden polygon is all rectangle corners minus all clipped triangle
    vertices, joined by their convex hull. This searches the continuous domain,
    including disconnected clear regions, rather than a local sampled grid.
    clearance separates touching geometry by one micrometre by default; it is
    a numerical separation, not an ergonomic allowance. None means no solution.
    """
    from shapely.geometry import MultiPoint, Point, box
    from shapely.ops import nearest_points, unary_union

    if bounds[0] >= bounds[2] or bounds[1] >= bounds[3]:
        return None
    domain = box(*bounds)
    forbidden = []
    for name, rect in routes.items():
        floor = route_ground[name]
        corners = np.array([(rect[0],rect[1]), (rect[0],rect[3]),
                            (rect[2],rect[1]), (rect[2],rect[3])])
        nearby = ((triangles[:,:,2].min(axis=1) <= floor+height) &
                  (triangles[:,:,2].max(axis=1) >= floor) &
                  (triangles[:,:,0].min(axis=1)+bounds[0] <= rect[2]) &
                  (triangles[:,:,0].max(axis=1)+bounds[2] >= rect[0]) &
                  (triangles[:,:,1].min(axis=1)+bounds[1] <= rect[3]) &
                  (triangles[:,:,1].max(axis=1)+bounds[3] >= rect[1]))
        for triangle in triangles[nearby]:
            polygon = list(triangle)
            for limit, above in ((floor, True), (floor+height, False)):
                clipped = []
                for a,b in zip(polygon, polygon[1:]+polygon[:1]):
                    a_in = a[2] >= limit if above else a[2] <= limit
                    b_in = b[2] >= limit if above else b[2] <= limit
                    if a_in:
                        clipped.append(a)
                    if a_in != b_in:
                        clipped.append(a+(b-a)*((limit-a[2])/(b[2]-a[2])))
                polygon = clipped
                if not polygon:
                    break
            if polygon:
                points = (corners[:,None,:]-np.array(polygon)[None,:,:2]).reshape(-1,2)
                forbidden.append(MultiPoint(points).convex_hull)
    occupied = unary_union(forbidden)
    clear = domain.difference(occupied.buffer(clearance, join_style=2))
    if clear.is_empty:
        return None
    nearest = nearest_points(Point(0,0), clear)[1]
    return dict(translation_m=[nearest.x,nearest.y], distance_m=nearest.distance(Point(0,0)),
                boundary_distance_m=Point(0,0).distance(domain.difference(occupied)),
                clearance_m=clearance, bounds_m=list(bounds), forbidden_polygons=len(forbidden))
