import numpy as np

from archpipe.parity.geom import box_tris, fan, penetration, ray_up, tri_cross_segments


def area(t):
    return 0.5 * np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1).sum()


def test_fan_triangulates_a_concave_polygon_without_covering_the_notch():
    L = [[0, 0, 0], [2, 0, 0], [2, 1, 0], [1, 1, 0], [1, 2, 0], [0, 2, 0]]
    assert abs(area(fan(L)) - 3.0) < 1e-9 and abs(area(fan(L[::-1])) - 3.0) < 1e-9


def test_fan_handles_a_bridged_hole():
    H = [[0, 0, 0], [4, 0, 0], [4, 4, 0], [0, 4, 0], [0, 0, 0], [1, 1, 0], [1, 3, 0], [3, 3, 0], [3, 1, 0], [1, 1, 0]]
    assert abs(area(fan(H)) - 12.0) < 1e-9          # the stair-opening class of defect: a naive fan gave 16


def test_overlapping_boxes_cross_and_report_the_depth():
    a, b = box_tris((0, 0, 0, 1, 1, 1)), box_tris((0.9, 0.2, 0.2, 2, 0.8, 0.8))
    seg, dep = tri_cross_segments(a, b)
    d, _ = penetration(seg, dep)
    assert abs(d - 0.1) < 1e-9


def test_touching_boxes_do_not_cross():
    seg, dep = tri_cross_segments(box_tris((0, 0, 0, 1, 1, 1)), box_tris((1, 0, 0, 2, 1, 1)))
    assert len(seg) == 0


def test_ray_up_finds_the_first_surface_above():
    t = np.concatenate([box_tris((0, 0, 1, 1, 1, 1.1)), box_tris((0, 0, 3, 1, 1, 3.1))])
    assert abs(ray_up(t, (0.5, 0.5, 0.0)) - 1.0) < 1e-9
