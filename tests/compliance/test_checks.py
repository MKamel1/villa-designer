"""L1 checkers: a positive and a negative test each, on fixtures built from named quantities (no out/ data)."""
from __future__ import annotations

import pytest

from archpipe.compliance import checks as C
from archpipe.compliance import sources
from archpipe.compliance.model import DesignModel, Guard, Opening, Room, Stair

# ---- named quantities for the stair fixture (mm) ---------------------------------------------------------------
FOOT_X, Y0, WIDTH, B_FLOOR, GF = 9657.0, -28421.0, 950.0, -3000.0, 0.0
OPENING_M = (5.177, -28.421, 8.887, -27.471)
SOFFIT = -300.0


def make_stair(risers=17, going=280.0, thick=60.0, overlap=0.0, has_risers=False, soffit=SOFFIT):
    rise = (GF - B_FLOOR) / risers
    boxes = []
    for i in range(1, risers):
        top = B_FLOOR + i * rise
        xa = FOOT_X - (i - 1) * going
        xb = xa - going - overlap
        boxes.append([xb, Y0, top - thick, xa, Y0 + WIDTH, top])
    return Stair("stair-test", boxes, OPENING_M, soffit, top_landing=(3.617, -28.671, 5.177, -26.371),
                 bottom_landing=(9.657, -28.671, 11.197, -26.671), has_risers=has_risers)


def model_with(**kw):
    m = DesignModel("T")
    for k, v in kw.items():
        setattr(m, k, v)
    return m


def room(rid, occ, w, d, level="GF", **kw):
    return Room(rid, level, (0.0, 0.0, w, d), occ, rid, area_m2=kw.pop("area", w * d), net_w=w, net_d=d, **kw)


def status(results, crit, subject_part, gate=None):
    rows = [r for r in results if r.criterion == crit and subject_part in r.subject
            and "[ER informative]" not in r.subject and (gate is None or r.gate == gate)]
    assert rows, (crit, subject_part, [r.subject for r in results])
    return {r.status for r in rows}


# ---- EG4 clear heights ------------------------------------------------------------------------------------------
def test_clear_height_pass_and_fail():
    ok = model_with(rooms={"a": room("a", "living", 4, 4)}, clear={"a": [2.7]})
    assert status(C.check_clear_heights(ok), "EG4", "a (", gate=True) == {"pass"}
    low = model_with(rooms={"a": room("a", "living", 4, 4)}, clear={"a": [2.0] * 100})
    assert status(C.check_clear_heights(low), "EG4", "a (", gate=True) == {"fail"}


def test_clear_height_75_percent_rule():
    prof = [2.4] * 76 + [2.0] * 24                       # 76 % of the floor at >= 2.3
    m = model_with(rooms={"a": room("a", "media", 4, 4)}, clear={"a": prof})
    assert status(C.check_clear_heights(m), "EG4", "a (", gate=True) == {"pass"}
    m.clear["a"] = [2.4] * 74 + [2.0] * 26
    assert status(C.check_clear_heights(m), "EG4", "a (", gate=True) == {"fail"}


def test_clear_height_missing_data_not_evaluated():
    m = model_with(rooms={"a": room("a", "living", 4, 4)}, clear={})
    assert status(C.check_clear_heights(m), "EG4", "a (") == {"not_evaluated"}


# ---- EG5 room sizes ---------------------------------------------------------------------------------------------
def test_bedroom_size_pass_and_fail():
    big = model_with(rooms={"b": room("b", "bedroom", 3.5, 3.6, area=12.0)})
    assert status(C.check_room_sizes(big), "EG5", "b (", gate=True) == {"pass"}
    small = model_with(rooms={"b": room("b", "bedroom", 3.0, 3.0, area=9.0)})
    assert "fail" in status(C.check_room_sizes(small), "EG5", "b (", gate=True)


def test_bedroom_area_counts_entry_alcove():
    m = model_with(rooms={"p": room("p", "bedroom", 3.5, 3.1, area=10.86),
                          "pe": room("pe", "bedroom", 1.0, 0.66, area=0.66, part_of="p")})
    res = C.check_room_sizes(m)
    area = [r for r in res if r.subject.endswith("area") and r.gate][0]
    assert area.achieved == pytest.approx(11.52) and area.status == "pass"


# ---- EG6 doors --------------------------------------------------------------------------------------------------
def test_doors_pass_and_fail():
    m = model_with(openings=[Opening("d1", "door", "GF", 0.9, 2.1, rooms=("a", "b")),
                             Opening("d2", "door", "GF", 0.6, 2.1, rooms=("a", "c"))])
    res = {r.element_ids[0]: r.status for r in C.check_doors(m) if "[ER" not in r.subject and "height" not in r.subject}
    assert res == {"d1": "pass", "d2": "fail"}


# ---- CL2 / EG7 daylight -----------------------------------------------------------------------------------------
def test_daylight_pass_fail_and_missing():
    m = model_with(rooms={"l": room("l", "living", 4, 4, level="B"), "k": room("k", "kitchen", 3, 3, level="B"),
                          "g": room("g", "bedroom", 4, 4, level="GF")}, df={"l": 2.0, "k": 0.3})
    res = C.check_daylight(m)
    assert status(res, "CL2", "l (", gate=False) == {"pass"}
    assert status(res, "CL2", "k (", gate=False) == {"fail"}
    assert status(res, "CL2", "g (", gate=True) == {"not_evaluated"}


def test_glazing_ratio():
    m = model_with(rooms={"l": room("l", "living", 4, 4, level="B")},
                   openings=[Opening("w", "window", "B", 2.0, 1.0, 0.9, ("l",), True)], df={"l": 2.0})
    assert status(C.check_daylight(m), "EG7", "glazing", gate=False) == {"pass"}      # 2 m2 / 16 m2 = 12.5 %
    m.openings = []
    assert status(C.check_daylight(m), "EG7", "glazing", gate=False) == {"fail"}


# ---- EG9 sills --------------------------------------------------------------------------------------------------
def test_sills_pass_and_fail():
    m = model_with(openings=[Opening("w1", "window", "GF", 1, 1.4, 0.9, ("a",), True),
                             Opening("w2", "window", "GF", 1, 1.4, 0.5, ("a",), True)])
    res = {r.element_ids[0]: r.status for r in C.check_sills(m) if "[ER" not in r.subject}
    assert res == {"w1": "pass", "w2": "fail"}


# ---- stair geometry (LS1) ---------------------------------------------------------------------------------------
def test_stair_measured_from_boxes():
    g = C.stair_geometry(make_stair())
    assert g["risers"] == 17 and g["rise"] == pytest.approx(176.47, abs=0.01) and g["going"] == 280
    assert g["width"] == 950 and g["gap"] == pytest.approx(116.47, abs=0.01) and g["overlap_min"] == 0


def test_stair_geometry_pass_and_fail():
    ok = model_with(stair=make_stair())
    assert status(C.check_stair_geometry(ok), "LS1", "stair rise", gate=True) == {"pass"}
    assert status(C.check_stair_geometry(ok), "LS1", "stair headroom", gate=True) == {"pass"}
    steep = model_with(stair=make_stair(risers=12))                  # rise 250 mm
    assert status(C.check_stair_geometry(steep), "LS1", "stair rise", gate=True) == {"fail"}


def test_stair_headroom_fail_when_soffit_low():
    m = model_with(stair=make_stair(soffit=-420.0))                  # 120 mm lower soffit: 2038 - 120 < 2000
    assert status(C.check_stair_geometry(m), "LS1", "stair headroom", gate=True) == {"fail"}


def test_stair_missing_not_evaluated():
    assert C.check_stair_geometry(model_with(stair=None))[0].status == "not_evaluated"


def test_headroom_agrees_with_pitch_headroom_for_r8():
    from archpipe.concept import revit_spec as RS
    from archpipe.concept import stairs as S
    from archpipe.concept import villa_r11 as R
    spec = RS.build(R.design("D1"))
    st = Stair("r8", [list(b) for b in spec["stair"]], tuple(spec["gf_opening"]), S.SLAB_SOFFIT)
    ours, _ = C.stair_headroom_mm(st, C.stair_geometry(st))
    theirs, _ = S.pitch_headroom(S.party_flight_r8(), [v * 1000 for v in spec["gf_opening"]])
    assert ours == pytest.approx(theirs, abs=20.0)           # 5 mm sampling step vs 10 mm, beams not under the flight


# ---- LS2 open risers --------------------------------------------------------------------------------------------
def test_open_riser_stair_fails():
    res = C.check_open_risers(model_with(stair=make_stair()))
    assert status(res, "LS2", "sphere", gate=True) == {"fail"}
    assert status(res, "LS2", "overlap", gate=True) == {"fail"}


def test_d1_spec_without_infill_fails_sphere_but_has_overlap():
    from archpipe.concept import revit_spec as RS
    from archpipe.concept import villa_r11 as R
    spec = RS.build(R.design("D1"))
    st = Stair("d1", [list(b) for b in spec["stair"]], tuple(spec["gf_opening"]), -300.0)
    res = C.check_open_risers(model_with(stair=st))
    assert status(res, "LS2", "sphere", gate=True) == {"fail"}          # 116.5 mm gap, no infill given
    assert status(res, "LS2", "overlap", gate=True) == {"pass"}         # G1: treads 296 wide on a 280 going = 16 mm
    assert C.stair_geometry(st)["going"] == pytest.approx(280.0, abs=0.5)    # nosing pitch, not the 296 box width


def test_riser_infill_passes_and_closed_risers_becomes_info():
    st = make_stair(thick=60.0, overlap=16.0)
    st.riser_infill = {"present": True, "max_clear_opening_mm": 38.24, "bar_h_mm": 40, "type": "horizontal flat bar"}
    res = C.check_open_risers(model_with(stair=st))
    assert status(res, "LS2", "sphere", gate=True) == {"pass"}
    closed = [r for r in res if "closed risers" in r.subject][0]
    assert closed.gate is False and closed.status == "fail" and "g1-safety-decisions-2026-11-21" in closed.source_ids
    assert "G1" in closed.message
    st.riser_infill["max_clear_opening_mm"] = 110.0
    assert status(C.check_open_risers(model_with(stair=st)), "LS2", "sphere", gate=True) == {"fail"}


def test_closed_risers_row_is_a_gate_without_the_decision():
    res = C.check_open_risers(model_with(stair=make_stair()))
    assert [r.gate for r in res if "closed risers" in r.subject] == [True]


def test_under_flight_cupboard_clears_the_warning():
    st = make_stair()
    st.under_flight = {"enclosed": True, "treads_enclosed": 11, "cupboard_id": "cup"}
    res = C.check_stair_geometry(model_with(stair=st))
    assert status(res, "LS1", "space under", gate=True) == {"pass"}
    st.under_flight = {"enclosed": True, "treads_enclosed": 5, "cupboard_id": "cup"}     # covers too few treads
    assert status(C.check_stair_geometry(model_with(stair=st)), "LS1", "space under", gate=True) == {"warn"}
    st.under_flight = None
    assert status(C.check_stair_geometry(model_with(stair=st)), "LS1", "space under", gate=True) == {"warn"}


def test_closed_risers_pass():
    res = C.check_open_risers(model_with(stair=make_stair(has_risers=True)))
    assert {r.status for r in res} == {"pass"}


def test_open_risers_pass_with_thick_overlapping_treads():
    res = C.check_open_risers(model_with(stair=make_stair(thick=80.0, overlap=16.0)))
    assert status(res, "LS2", "sphere", gate=True) == {"pass"}          # gap 96.5 mm
    assert status(res, "LS2", "overlap", gate=True) == {"pass"}


# ---- LS3 guards -------------------------------------------------------------------------------------------------
def test_guard_heights():
    m = model_with(guards=[Guard("g9", "stair open side", 0.9), Guard("g8", "stair other", 0.8),
                           Guard("r11", "ramp edge", 1.1, drop_m=1.8, level="street"),
                           Guard("r10", "deck edge", 1.0, drop_m=1.8, level="street")])
    res = C.check_guards(m)
    by = {r.element_ids[0]: r for r in res if r.gate and "sphere" not in r.subject and "target" not in r.subject}
    assert by["g9"].status == "pass" and by["g8"].status == "fail" and by["r11"].status == "pass"
    tgt = {r.element_ids[0]: r.status for r in res if "target" in r.subject}
    assert tgt == {"r11": "pass", "r10": "fail"} and all(r.gate for r in res if "target" in r.subject)


def test_guard_sphere_and_unmodelled_edges():
    m = model_with(guards=[Guard("g", "stair", 1.0, solid=False)],
                   needed_but_unmodelled=[("GF void edge", "no element")])
    res = C.check_guards(m)
    assert any(r.status == "warn" and "openings" in r.subject for r in res)
    assert any(r.status == "not_evaluated" and r.subject == "GF void edge" for r in res)


def test_handrail_height_range():
    ok = C.check_guards(model_with(guards=[Guard("h", "wall", 0.9, kind="handrail")]))
    assert ok[0].status == "pass"
    bad = C.check_guards(model_with(guards=[Guard("h", "wall", 1.2, kind="handrail")]))
    assert bad[0].status == "fail"


# ---- LS4 door near the flight -----------------------------------------------------------------------------------
def door_at(x, swing, direction=""):
    return Opening("core", "door", "GF", 1.0, 2.1, rooms=("landing-gf", "core"), x=x, swing_known=swing,
                   swing_direction=direction)


def test_door_close_to_top_step_warns_when_swing_unknown_and_fails_when_known():
    near = model_with(stair=make_stair(), openings=[door_at(4.602, False)])
    assert {r.status for r in C.check_door_near_flight(near) if r.gate} == {"warn"}
    near_known = model_with(stair=make_stair(), openings=[door_at(4.602, True)])
    assert {r.status for r in C.check_door_near_flight(near_known) if r.gate} == {"fail"}


def test_outward_swing_passes_even_close_to_the_step():
    m = model_with(stair=make_stair(), openings=[door_at(4.602, True, "outward")])
    assert {r.status for r in C.check_door_near_flight(m) if r.gate} == {"pass"}
    m = model_with(stair=make_stair(), openings=[door_at(4.602, True, "inward")])
    assert {r.status for r in C.check_door_near_flight(m) if r.gate} == {"fail"}


def test_door_far_from_top_step_passes():
    far = model_with(stair=make_stair(), openings=[door_at(3.9, True)])      # jamb at 4.4 m: 0.777 m from 5.177
    assert {r.status for r in C.check_door_near_flight(far) if r.gate} == {"pass"}


# ---- LS5 escape -------------------------------------------------------------------------------------------------
def test_inner_room_fails_and_external_door_passes():
    inner = model_with(rooms={"c": room("c", "media", 3, 3, level="B")}, links=[("lounge", "c")])
    assert status(C.check_escape(inner), "LS5", "c (", gate=True) == {"fail"}
    ok = model_with(rooms={"c": room("c", "living", 3, 3, level="B")},
                    openings=[Opening("gd", "door", "B", 2.4, 2.2, rooms=("c", "yard"), exterior=True)])
    assert status(C.check_escape(ok), "LS5", "c (", gate=True) == {"pass"}


def test_escape_window_limits():
    small = model_with(rooms={"b": room("b", "bedroom", 3, 4)},
                       openings=[Opening("w", "window", "GF", 0.5, 0.5, 0.9, ("b",), True)])       # 0.25 m2
    assert status(C.check_escape(small), "LS5", "b (", gate=True) == {"fail"}
    high = model_with(rooms={"b": room("b", "bedroom", 3, 4)},
                      openings=[Opening("w", "window", "GF", 1.2, 1.0, 1.3, ("b",), True)])         # sill 1.3 m
    assert status(C.check_escape(high), "LS5", "b (", gate=True) == {"fail"}
    good = model_with(rooms={"b": room("b", "bedroom", 3, 4)},
                      openings=[Opening("w", "window", "GF", 1.2, 1.0, 0.9, ("b",), True)])
    assert status(C.check_escape(good), "LS5", "b (", gate=True) == {"pass"}


def test_waived_inner_room_stays_fail_but_is_not_a_gate():
    m = model_with(rooms={"cinema": room("cinema", "media", 3, 3, level="B")}, links=[("lounge", "cinema")],
                   waivers={("LS5", "cinema"): "WAIVED by client (G1 2026-11-21): accepted risk"})
    row = [r for r in C.check_escape(m) if "cinema" in r.subject][0]
    assert row.status == "fail" and row.gate is False
    assert row.message.startswith("WAIVED by client (G1 2026-11-21)")
    assert "g1-safety-decisions-2026-11-21" in row.source_ids


def test_guard_infill_opening_and_missing_guard_stays_not_evaluated():
    glass = Guard("g1", "void", 1.1, drop_m=3.0, level="street", max_opening_mm=0.0, climbable=False)
    bars = Guard("g2", "steps", 1.1, drop_m=1.8, level="street", max_opening_mm=75.0, climbable=False)
    wide = Guard("g3", "steps", 1.1, drop_m=1.8, level="street", max_opening_mm=120.0, climbable=False)
    res = C.check_guards(model_with(guards=[glass, bars, wide], needed_but_unmodelled=[("edge x", "no element")]))
    sph = {r.element_ids[0]: r.status for r in res if "sphere" in r.subject}
    assert sph == {"g1": "pass", "g2": "pass", "g3": "fail"}
    assert any(r.status == "not_evaluated" and r.subject == "edge x" for r in res)


def test_unproven_escape_gates_are_not_evaluated():
    m = model_with(not_evaluated_gates=[("LS5", "dead end", "no limit held")])
    assert [r.status for r in C.check_escape(m)] == ["not_evaluated"]


# ---- sources ----------------------------------------------------------------------------------------------------
def test_er_cards_are_unverified_and_all_cited_cards_exist():
    cards = sources.load_cards()
    assert all(c.status == "unverified" for k, c in cards.items() if k.startswith("er119-"))
    assert {"er119-art93", "er119-art94", "er119-art96-openings", "er119-art97", "er119-art98", "er119-art100",
            "er119-art103-railing", "er119-art106"} <= set(cards)
    m = model_with(stair=make_stair(), guards=[Guard("g", "s", 0.9)],
                   rooms={"a": room("a", "bedroom", 3.5, 3.6, area=12.0), "l": room("l", "living", 4, 4, level="B")},
                   clear={"a": [2.7], "l": [2.7]}, df={"l": 1.0},
                   openings=[Opening("w", "window", "GF", 1.2, 1.0, 0.9, ("a",), True),
                             Opening("d", "door", "GF", 0.9, 2.1, rooms=("a", "b"))])
    res = C.run_all(m)
    assert sources.missing_sources(res, cards) == []
    assert all(r.source_ids for r in res if r.status in ("pass", "fail"))


def test_policy_cards_are_marked_policy():
    cards = sources.load_cards()
    assert cards["policy-stair-rise-uniform-5mm"].status == "policy"


# ---- D1 end to end (no out/ data needed: missing read-backs degrade to not_evaluated) ---------------------------
def test_d1_loads_g1_fields_and_has_no_failed_or_warned_gate(tmp_path):
    from archpipe.compliance.model import load_d1
    m = load_d1(tmp_path)
    assert m.stair.riser_infill and m.stair.under_flight and m.stair.under_flight["enclosed"]
    ids = {g.id for g in m.guards}
    assert {"rail-gf-stair-void", "rail-gf-terrace-edge", "rail-patio-steps-edge"} <= ids
    assert m.needed_but_unmodelled == []
    res = C.run_all(m)
    assert {r.status for r in res if r.gate} <= {"pass", "not_evaluated"}
    assert any(r.status == "fail" and not r.gate and "WAIVED" in r.message for r in res)
    door = [r for r in res if r.criterion == "LS4" and r.gate][0]
    assert door.status == "pass" and "OUTWARD" in door.message
    assert sources.missing_sources(res, sources.load_cards()) == []
