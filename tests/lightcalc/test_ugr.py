import math

import pytest

from archpipe.lightcalc import synth, ugr
from archpipe.lightcalc.direct import Placement


def test_guth_index_is_one_on_the_line_of_sight_and_grows_with_angle():
    assert ugr.guth_position_index(0.0, 0.0) == pytest.approx(1.0)
    assert ugr.guth_position_index(0.0, 45.0) == pytest.approx(1.0)
    vals = [ugr.guth_position_index(s, 30.0) for s in (10, 20, 40, 60)]
    assert vals == sorted(vals) and vals[0] > 1.0


def test_position_index_against_sll_table_12_10():
    """K = pi/(4 p^2 D^2) from our Guth index vs the 27 transcribed K cells of the held SLL table."""
    rows = ugr.position_index_vs_sll_table_12_10()
    assert len(rows) == 27
    errs = [abs(r["rel_err"]) for r in rows]
    assert max(errs) < 0.08                     # K is ~1/p^2, so p is within ~4 %
    assert sum(errs) / len(errs) < 0.05


def test_flux_correction_matches_sll_table_12_6():
    for lm, printed in ugr.SLL_T12_6.items():
        assert ugr.flux_correction(lm) == pytest.approx(printed, abs=0.06), lm


def _array(i0, lm_scale=1.0):
    t = synth.cosine_ies_text(i0 * lm_scale).replace("1 -1 1 37 1 1 2 0.0 0.0 0", "1 -1 1 37 1 1 2 0.3 0.3 0")
    ph = synth.load_text(t, "sq")
    return [Placement(f"L{i}{j}", ph, (x, y, 3.2)) for i, x in enumerate((-1.0, 1.0)) for j, y in enumerate((2.0, 4.0))]


def test_ugr_hand_arithmetic_single_source():
    t = synth.cosine_ies_text(500.0).replace("1 -1 1 37 1 1 2 0.0 0.0 0", "1 -1 1 37 1 1 2 0.2 0.2 0")
    p = Placement("S", synth.load_text(t, "sq"), (0.0, 3.0, 3.2))
    eye, view = (0.0, 0.0, 1.2), (0.0, 1.0, 0.0)
    lb = 40.0
    out = ugr.ugr(eye, view, [p], lb)
    d = math.sqrt(9 + 4)
    cos_t = 2.0 / d
    a = 0.04 * cos_t
    L = 500.0 * cos_t / a                       # I(theta) = 500 cos(theta)
    omega = a / d ** 2
    sigma = math.degrees(math.acos(3.0 / d))
    pidx = ugr.guth_position_index(sigma, 0.0)  # directly above the line of sight: tau = 0
    expected = 8 * math.log10(0.25 / lb * L * L * omega / pidx ** 2)
    assert out["ugr"] == pytest.approx(expected, abs=0.01)


def test_ugr_scales_as_8_log10_of_flux_like_sll_correction():
    """Doubling lamp flux (I and the background luminance both x2) must raise UGR by 8 log10 2 = 2.41,
    the published correction (SLL Table 12.6: 1000 -> 2000 lm = +2.4)."""
    eye, view = (0.0, 0.0, 1.2), (0.0, 1.0, 0.0)
    base = ugr.ugr(eye, view, _array(300.0), 30.0)["ugr"]
    dbl = ugr.ugr(eye, view, _array(300.0, 2.0), 60.0)["ugr"]
    assert dbl - base == pytest.approx(ugr.SLL_T12_6[2000], abs=0.06)
    assert dbl - base == pytest.approx(8 * math.log10(2), abs=1e-5)
    half = ugr.ugr(eye, view, _array(300.0, 0.5), 15.0)["ugr"]
    assert half - base == pytest.approx(ugr.SLL_T12_6[500] - ugr.SLL_T12_6[1000], abs=0.06)


def test_ugr_background_and_behind_observer_edge_cases():
    eye, view = (0.0, 0.0, 1.2), (0.0, 1.0, 0.0)
    assert ugr.ugr(eye, view, _array(300.0), 0.0)["ugr"] is None
    behind = [Placement("B", _array(300.0)[0].photometry, (0.0, -3.0, 3.2))]
    assert ugr.ugr(eye, view, behind, 30.0)["ugr"] is None                    # behind the observer: excluded
    assert ugr.background_luminance(100 * math.pi) == pytest.approx(100.0)
    # a brighter background lowers UGR
    assert ugr.ugr(eye, view, _array(300.0), 60.0)["ugr"] < ugr.ugr(eye, view, _array(300.0), 30.0)["ugr"]


def test_omega_validity_is_flagged():
    eye, view = (0.0, 0.0, 1.2), (0.0, 1.0, 0.0)
    near = [Placement("N", _array(300.0)[0].photometry, (0.0, 0.2, 1.7))]       # tiny distance, large omega
    out = ugr.ugr(eye, view, near, 30.0)
    assert out["warnings"] and "outside the formula" in out["warnings"][0]
