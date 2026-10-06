"""Stair mounting from the structural datum that also locates the treads.

All distances are metres. The near structural face points into the room in
positive model y. The retained 85 mm rail clearance and 30 mm plate clearance
are existing design projections, not published construction requirements.
"""
from .mounting import Host, finish_from_record


def return_host(spec):
    """The actual partition return, selected from the authored wall model."""
    datum = spec["stair_wall_datum"]
    outer = datum["outer_face_mm"] / 1000
    wall = next(w for w in spec["walls"] if w["level"] == "B" and w["kind"] == "int"
                and abs(w["y0"] - outer) < 1e-8 and abs(w["y1"] - outer) < 1e-8)
    return Host("stair-core-return", "wall", (0, wall["y0"] + wall["thickness"] / 2, 0),
                (0, 1, 0), finish_from_record("interior-plaster")), max(wall["x0"], wall["x1"])


def wall_host(spec):
    datum = spec["stair_wall_datum"]
    near_face = datum["outer_face_mm"] / 1000 + datum["structural_thickness_m"]
    return Host("stair-party-wall", "wall", (0.0, near_face, 0.0),
                (0.0, 1.0, 0.0), finish_from_record("interior-plaster"))


def finished_y(host):
    return host.structural_point[1] + host.finish.thickness_m


RAIL_CLEARANCE_M = 0.085
RAIL_WIDTH_M = 0.040
PLATE_CLEARANCE_M = 0.030
PLATE_WIDTH_M = 0.030


def _clip_x(points, edge, keep_greater):
    """Clip a planar wall polygon at a model-x plane, preserving its winding."""
    result = []
    for a, b in zip(points, points[1:] + points[:1]):
        inside_a = a[0] >= edge if keep_greater else a[0] <= edge
        inside_b = b[0] >= edge if keep_greater else b[0] <= edge
        if inside_a:
            result.append(list(a))
        if inside_a != inside_b:
            fraction = (edge - a[0]) / (b[0] - a[0])
            result.append([a[i] + fraction * (b[i] - a[i]) for i in range(3)])
    return result if len(result) >= 3 and max(p[0] for p in result) - min(p[0] for p in result) > 1e-9 else []


def plaster_faces(points, host, start_x, end_x):
    """Only finish the wall beside this flight; adjacent packages remain unchanged."""
    unchanged = [face for face in (_clip_x(points, start_x, False), _clip_x(points, end_x, True)) if face]
    middle = _clip_x(_clip_x(points, start_x, True), end_x, False)
    return unchanged, [[p[0], finished_y(host), p[2]] for p in middle]
