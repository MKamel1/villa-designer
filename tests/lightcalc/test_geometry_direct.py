import math

import pytest

from archpipe.lightcalc import geometry as G
from archpipe.lightcalc import refcases, synth
from archpipe.lightcalc.direct import (Placement, direct_illuminance, luminance_toward, upward_light_ratio)
from archpipe.lightcalc.metrics import grid_stats

L_SHAPE = [(0, 0), (4, 0), (4, 2), (2, 2), (2, 4), (0, 4)]     # 12 m2, notch at the top right


def test_area_and_winding():
    assert G.area(L_SHAPE) == pytest.approx(12.0)
    assert G.area(list(reversed(L_SHAPE))) == pytest.approx(12.0)
    assert G.signed_area(G.ccw(list(reversed(L_SHAPE)))) > 0


def test_point_in_concave_polygon_positive_and_negative():
    assert G.point_in_polygon((1, 1), L_SHAPE)
    assert G.point_in_polygon((3, 1), L_SHAPE)
    assert G.point_in_polygon((1, 3), L_SHAPE)
    assert not G.point_in_polygon((3, 3), L_SHAPE)        # inside the bbox, in the notch
    assert not G.point_in_polygon((5, 1), L_SHAPE)


def test_grid_skips_the_notch_and_respects_border():
    pts, dx, dy = G.grid_in_polygon(L_SHAPE, spacing=0.5)
    assert pts and all(G.point_in_polygon(p, L_SHAPE) for p in pts)
    assert not any(p[0] > 2 and p[1] > 2 for p in pts)
    area_est = len(pts) * dx * dy
    assert area_est == pytest.approx(12.0, rel=0.05)
    inner, _, _ = G.grid_in_polygon(L_SHAPE, spacing=0.5, border=0.4)
    assert all(G.dist_to_edges(p, L_SHAPE) >= 0.4 - 1e-9 for p in inner)
    assert len(inner) < len(pts)
    with pytest.raises(ValueError):
        G.grid_in_polygon([(0, 0), (1, 0), (1, 1), (0, 1)], spacing=0.25, border=0.6)


def test_en12464_spacing_formula():
    assert G.en12464_spacing(1.0) == pytest.approx(0.2)
    assert G.en12464_spacing(10.0) == pytest.approx(1.0)


def test_outward_normals_point_away_from_centroid():
    for a, b, n in G.outward_edges(L_SHAPE):
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        probe = (mid[0] + 0.01 * n[0], mid[1] + 0.01 * n[1])
        assert not G.point_in_polygon(probe, L_SHAPE)


def test_grid_stats_definitions():
    s = grid_stats([100.0, 200.0, 300.0])
    assert s.em == 200 and s.emin == 100 and s.emax == 300
    assert s.u0 == pytest.approx(0.5) and s.max_avg == pytest.approx(1.5) and s.avg_min == pytest.approx(2.0)
    assert grid_stats([0.0, 10.0]).to_dict()["avg_min"] is None


def _iso(cd=1000.0, pos=(0, 0, 2.0), **kw):
    t = synth.isotropic_ies_text(cd)
    return Placement("S", synth.load_text(t, "iso"), pos, meta={"ies_text": t}, **kw)


def test_inverse_square_closed_form():
    # E = I / d^2 = 1000 / 4 = 250 lx directly below at 2 m (the existing radiance.physics_check case)
    assert direct_illuminance([_iso()], (0, 0, 0)) == pytest.approx(250.0, rel=1e-9)
    # doubling the distance quarters it
    assert direct_illuminance([_iso(pos=(0, 0, 4.0))], (0, 0, 0)) == pytest.approx(62.5, rel=1e-9)


def test_cosine_law_and_normal_orientation():
    p = _iso()
    # point 2 m to the side on the floor: d = 2.828 m, cos = 2/2.828 -> E = 1000 * 0.7071 / 8
    assert direct_illuminance([p], (2, 0, 0)) == pytest.approx(1000 * math.sqrt(0.5) / 8, rel=1e-9)
    # a downward-facing sensor sees nothing from a source above it
    assert direct_illuminance([p], (0, 0, 0), (0, 0, -1)) == 0.0


def test_dim_scales_linearly():
    assert direct_illuminance([_iso(dim=0.4)], (0, 0, 0)) == pytest.approx(100.0)


def test_cie171_case_5_2_transcription_self_consistent():
    # the published rows must satisfy E = I cos(i)/d^2 (guards transcription of the expected values)
    for r in refcases.case_5_2_expected_check():
        assert r["rel_err_formula"] < 0.002, r
        assert abs(r["d_from_xy"] - r["d_published"]) < 0.002, r


def test_cie171_case_5_2_analytic_reproduces_published_E():
    t = synth.cosine_ies_text(1000.0)
    p = Placement("S", synth.load_text(t, "cos"), (0, 0, refcases.CASE_5_2_H))
    for k, ((x, y), _d, _inc, _i, e_pub) in refcases.CASE_5_2_POINTS.items():
        got = direct_illuminance([p], (x, y, 0.0))
        assert got == pytest.approx(e_pub, rel=0.005), k


def test_aim_convention_narrow_beam_lands_at_h_tan_tilt():
    t = synth.narrow_beam_ies_text(5000.0, 8.0)
    ph = synth.load_text(t, "nb")
    h, tilt = 3.0, 30.0
    aim = (math.sin(math.radians(tilt)), 0.0, -math.cos(math.radians(tilt)))       # tilt toward +x
    p = Placement("S", ph, (0, 0, h), aim=aim)
    xs = [i * 0.05 for i in range(-10, 120)]
    best = max(xs, key=lambda x: direct_illuminance([p], (x, 0, 0)))
    assert best == pytest.approx(h * math.tan(math.radians(tilt)), abs=0.1)
    # and toward +y
    aim_y = (0.0, math.sin(math.radians(tilt)), -math.cos(math.radians(tilt)))
    py = Placement("S", ph, (0, 0, h), aim=aim_y)
    ys = [i * 0.05 for i in range(-10, 120)]
    assert max(ys, key=lambda y: direct_illuminance([py], (0, y, 0))) == pytest.approx(h * math.tan(math.radians(tilt)), abs=0.1)


def test_luminance_and_ulr():
    t = synth.cosine_ies_text(1000.0)
    ph = synth.load_text(t, "cos")
    down = Placement("S", ph, (0, 0, 2.7))
    up = Placement("S", ph, (0, 0, 2.7), aim=(0, 0, 1))
    assert upward_light_ratio(down) == pytest.approx(0.0, abs=1e-9)
    assert upward_light_ratio(up) == pytest.approx(1.0, abs=1e-3)
    # luminaire with a real opening: a 0.1 m x 0.1 m square, 1000 cd straight down -> L = 1000/0.01
    sq = t.replace("1 -1 1 37 1 1 2 0.0 0.0 0", "1 -1 1 37 1 1 2 0.1 0.1 0")
    pq = Placement("Q", synth.load_text(sq, "sq"), (0, 0, 2.7))
    L, a, d = luminance_toward(pq, (0, 0, 1.2))
    assert L == pytest.approx(1000 / 0.01, rel=1e-6) and a == pytest.approx(0.01) and d == pytest.approx(1.5)
    # a point opening (0 area) cannot give a luminance: refuse rather than invent one
    with pytest.raises(ValueError):
        luminance_toward(down, (0, 0, 1.2))
