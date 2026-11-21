import math

import pytest

from archpipe.contracts import CheckResult
from archpipe.lightcalc import checks, synth
from archpipe.lightcalc.direct import Placement
from archpipe.lightcalc.metrics import grid_stats
from archpipe.lightcalc.sources import CARDS


def _ph(text, name="p"):
    return synth.load_text(text, name)


def test_every_source_id_used_has_a_card():
    for r in [checks.check_la1("s", 100, 100), checks.check_la2("s", 100, 100)]:
        assert all(i in CARDS for i in r.source_ids)
    assert CARDS["L6-POLICY-LA2-over-lighting-1.5x"].status == "policy"
    assert CARDS["SLL-T3.2-E3"].status == "sourced" and CARDS["SLL-T3.2-E3"].quote
    assert CARDS["IES-HB10-p33.25-avg-allowance"].status == "sourced"


# ---- LA1
def test_la1_pass_inside_band_fail_outside_both_sides():
    assert checks.check_la1("r", 105, 100).status == "pass"
    assert checks.check_la1("r", 90, 100).status == "pass"            # boundary of +/-10 %
    assert checks.check_la1("r", 89, 100).status == "fail"
    assert checks.check_la1("r", 111, 100).status == "fail"


def test_la1_minimum_gauged_task():
    assert checks.check_la1("r", 300, 200, gauge="minimum", emin=210).status == "pass"
    assert checks.check_la1("r", 300, 200, gauge="minimum", emin=150).status == "fail"


# ---- LA2
def test_la2_over_lighting_dining_like_numbers():
    r = checks.check_la2("dining", 797.0, 100.0)
    assert r.status == "fail" and r.criterion == "LA2" and r.required == 150.0 and r.achieved == 797.0
    assert "7.97" in r.message
    assert checks.check_la2("dining", 149.0, 100.0).status == "pass"
    assert checks.check_la2("dining", 150.0, 100.0).status == "pass"
    assert checks.check_la2("dining", 150.1, 100.0).status == "fail"


# ---- LA3
def test_la3_reports_and_evaluates():
    st = grid_stats([80.0, 100.0, 120.0])
    rep = checks.check_la3("r", st)
    assert len(rep) == 1 and rep[0].status == "pass" and "U0" in rep[0].message
    assert checks.check_la3("r", st, u0_min=0.6)[0].status == "pass"            # 0.8
    assert checks.check_la3("r", st, u0_min=0.9)[0].status == "fail"
    assert checks.check_la3("r", st, max_avg_limit=1.1)[0].status == "fail"
    assert checks.check_la3("r", grid_stats([0.0, 10.0]), avg_min_limit=3.0)[0].status == "fail"


# ---- LA4
def test_la4_ugr_limit_and_unverified_position_index_cannot_fail():
    assert checks.check_la4_ugr("study", 18.4, position_index_verified=True).status == "pass"     # rounds to 18
    assert checks.check_la4_ugr("study", 19.4, position_index_verified=True).status == "pass"     # rounds to 19
    assert checks.check_la4_ugr("study", 19.6, position_index_verified=True).status == "fail"
    r = checks.check_la4_ugr("study", 22.0)                    # default: not verified -> warn, never fail
    assert r.status == "warn" and "cannot gate" in r.message
    assert checks.check_la4_ugr("study", None).status == "not_evaluated"


def _sq(i0, size=0.1):
    t = synth.cosine_ies_text(i0).replace("1 -1 1 37 1 1 2 0.0 0.0 0", f"1 -1 1 37 1 1 2 {size} {size} 0")
    return _ph(t)


def test_la4_luminance_flags_bright_unshielded_source_in_sightline():
    bright = Placement("B1", _sq(1000.0), (0, 0, 2.7))          # 1000 cd / 0.01 m2 = 100,000 cd/m2 straight down
    dim = Placement("D1", _sq(10.0), (0, 0, 2.7))               # 1,000 cd/m2
    sl = [{"id": "sofa", "eye": (0.0, -1.0, 1.2), "dir": (0.0, 0.5, 1.0)}]
    bad = checks.check_la4_luminance("lounge", sl, [bright])[0]
    assert bad.status == "fail" and bad.achieved > 3000 and bad.element_ids == ("B1",)
    assert checks.check_la4_luminance("lounge", sl, [dim])[0].status == "pass"
    shielded = Placement("B2", _sq(1000.0), (0, 0, 2.7), meta={"shielded": True})
    assert checks.check_la4_luminance("lounge", sl, [shielded])[0].status == "pass"
    # outside the 45 deg cone: not counted
    far = Placement("B3", _sq(1000.0), (0, 8.0, 2.7))
    sl2 = [{"id": "x", "eye": (0.0, 0.0, 1.2), "dir": (0.0, -1.0, 0.0)}]
    assert checks.check_la4_luminance("lounge", sl2, [far])[0].status == "pass"
    # a point opening has no luminance: not_evaluated, never a pass
    pt = Placement("P", _ph(synth.cosine_ies_text(1000.0)), (0, 0, 2.7))
    assert checks.check_la4_luminance("lounge", sl, [pt])[0].status == "not_evaluated"


# ---- LA9
def test_la9_on_axis_and_off_axis_within_10mm():
    lums = [{"id": f"L{i}", "x": 1.0 + 1.5 * i, "y": 2.0, "z": 2.7, "shr_max": 1.5} for i in range(3)]
    res = checks.check_la9("room", lums, axes_x=[], axes_y=[2.0])
    assert res[0].status == "pass" and res[0].achieved == 100.0
    lums[1]["y"] = 2.009                                         # 9 mm off: inside tolerance
    assert checks.check_la9("room", lums, [], [2.0])[0].status == "pass"
    lums[1]["y"] = 2.011                                         # 11 mm off: fails
    r = checks.check_la9("room", lums, [], [2.0])[0]
    assert r.status == "fail" and r.element_ids == ("L1",) and r.achieved == pytest.approx(200 / 3)


def test_la9_grid_mode_needs_both_axes_and_empty_is_not_evaluated():
    l = [{"id": "A", "x": 1.0, "y": 5.0, "z": 2.7}]
    assert checks.check_la9("r", l, [1.0], [2.0], mode="any")[0].status == "pass"
    assert checks.check_la9("r", l, [1.0], [2.0], mode="both")[0].status == "fail"
    assert checks.check_la9("r", [], [1.0], [2.0])[0].status == "not_evaluated"


def test_la9_spacing_over_shr():
    ok = [{"id": f"L{i}", "x": 1.5 * i, "y": 0.0, "z": 2.7, "shr_max": 1.0} for i in range(2)]   # 1.5 <= 1.0*1.85? yes
    assert [r for r in checks.check_la9("r", ok, [], [0.0]) if r.subject.endswith("spacing")][0].status == "pass"
    wide = [{"id": f"L{i}", "x": 2.5 * i, "y": 0.0, "z": 2.7, "shr_max": 1.0} for i in range(2)]  # 2.5 > 1.85
    r = [r for r in checks.check_la9("r", wide, [], [0.0]) if r.subject.endswith("spacing")][0]
    assert r.status == "fail" and len(r.element_ids) == 2


def test_la9_wallwash_setback_is_unverified_so_warns_not_fails():
    poly = [(0, 0), (5, 0), (5, 4), (0, 4)]
    near = [{"id": "W1", "x": 2.0, "y": 0.3}]
    good = [{"id": "W2", "x": 2.0, "y": 0.8}]
    lum = [{"id": "x", "x": 1.0, "y": 1.0, "z": 2.7}]
    r_bad = [r for r in checks.check_la9("r", lum, [1.0], [], wallwash=near, room_polygon=poly) if "setback" in r.subject][0]
    r_ok = [r for r in checks.check_la9("r", lum, [1.0], [], wallwash=good, room_polygon=poly) if "setback" in r.subject][0]
    assert r_bad.status == "warn" and r_ok.status == "pass"


# ---- LA12
def test_la12_boundary_and_curfew_columns():
    assert checks.check_la12("site", boundary_ev=[1.0, 9.9], curfew="pre")[0].status == "pass"
    assert checks.check_la12("site", boundary_ev=[1.0, 10.1], curfew="pre")[0].status == "fail"
    assert checks.check_la12("site", boundary_ev=[1.0, 2.5], curfew="post")[0].status == "fail"
    assert checks.check_la12("site", boundary_ev=[1.0, 1.9], curfew="post")[0].status == "pass"
    assert checks.check_la12("site")[0].status == "not_evaluated"


def test_la12_intensity_and_ulr():
    down = Placement("G1", _ph(synth.cosine_ies_text(800.0)), (0, 0, 3.0))                 # peak 800 cd, no upward light
    up = Placement("U1", _ph(synth.cosine_ies_text(800.0)), (0, 0, 3.0), aim=(0, 0, 1))
    nb = [(0.0, 0.0, 0.0)]                                                                 # neighbour point straight below
    r = {x.subject.split("/")[1].split(" ")[0]: x for x in checks.check_la12("s", exterior=[down], neighbour_points=nb)}
    assert r["I"].status == "pass" and r["ULR"].status == "pass"
    r2 = {x.subject.split("/")[1].split(" ")[0]: x for x in checks.check_la12("s", exterior=[up], neighbour_points=[(0, 0, 9.0)])}
    assert r2["ULR"].status == "fail" and r2["I"].status == "pass"                         # uplight: ULR 1.0 > 0.15
    hot = Placement("H", _ph(synth.cosine_ies_text(20000.0)), (0, 0, 3.0))
    rr = checks.check_la12("s", exterior=[hot], neighbour_points=nb, curfew="pre")
    assert [x for x in rr if "I toward" in x.subject][0].status == "fail"


def test_la12_facade_luminance():
    assert checks.check_la12("s", facade_lb=9.0)[0].status == "pass"
    assert checks.check_la12("s", facade_lb=11.0)[0].status == "fail"


# ---- LA13
def test_la13_emergency_route():
    t = synth.cosine_ies_text(300.0)
    ph = _ph(t)
    lights = [Placement(f"E{i}", ph, (2.0 + 4.0 * i, 0.0, 2.5)) for i in range(2)]        # 300 cd downlights every 4 m, 2.5 m high
    route = [(0.0, 0.0, 0.0), (8.0, 0.0, 0.0)]
    ok = checks.check_la13("stair", route, lights, required_lx=1.0)
    assert ok.status == "pass" and ok.achieved >= 1.0
    far = checks.check_la13("stair", [(0, 0, 0), (30, 0, 0)], lights, required_lx=1.0)
    assert far.status == "fail" and far.achieved < 1.0
    assert checks.check_la13("stair", route, []).status == "not_evaluated"


def test_results_are_valid_contract_records():
    for r in [checks.check_la2("d", 797, 100), checks.check_la13("x", [(0, 0, 0)], [])]:
        assert isinstance(r, CheckResult) and r.lane == "L6"
