"""Engine rules: each rule has a positive and a negative test (bathroom zones, circuits, protection, join checks)."""
import copy
import dataclasses
import json
from pathlib import Path

import pytest

from archpipe import contracts
from archpipe.electrical import checks, circuits, demo, placement, reference_cases, schedule, zones
from archpipe.electrical.demand import phase_balance
from archpipe.electrical.model import load_house

FIX = Path(__file__).parent / "fixtures" / "test_house.json"


@pytest.fixture()
def house():
    return load_house(FIX)


def results(h):
    devs = placement.place_devices(h)
    d = circuits.design(h, devs)
    return d, checks.run_checks(d)


def by(res, crit, status=None, subject=None):
    return [r for r in res if r.criterion == crit and (status is None or r.status == status) and (subject is None or r.subject.startswith(subject))]


def _bath_dev(kind, x, y, z):
    return placement.Device("T-1", kind, "BATH", x, y, z)


# ---- EA2 zones -------------------------------------------------------------------------------------------
@pytest.mark.parametrize("x,y,z,zone", [(6000, 7500, 100, 0), (6000, 7500, 1200, 1), (5300, 7500, 1000, 2), (5000, 7500, 1000, None), (6000, 7500, 2400, None)])
def test_zone_geometry_tray(house, x, y, z, zone):
    wets = zones.wet_areas(house.room("BATH"), house.furniture)
    assert zones.zone_at(x, y, z, wets) == zone


def test_socket_in_zone_1_fails(house):
    v = placement.validate_devices(house, [_bath_dev("socket", 6000, 7500, 1200)])
    assert [x.rule for x in v] == ["EA2-socket-in-zone"] and v[0].severity == "fail" and v[0].card == "EL-701-ZONE1"


def test_socket_in_zone_0_and_2_fail(house):
    assert placement.validate_devices(house, [_bath_dev("socket", 6000, 7500, 100)])[0].card == "EL-701-ZONE0"
    assert placement.validate_devices(house, [_bath_dev("socket", 5300, 7500, 1000)])[0].card == "EL-701-ZONE2"


def test_socket_outside_zones_but_within_2_5m_only_warns(house):
    v = placement.validate_devices(house, [_bath_dev("socket", 4400, 5000, 300)])
    assert len(v) == 1 and v[0].severity == "warn" and v[0].rule == "EA2-socket-2.5m-uk"


def test_socket_far_from_zones_is_clean(house):
    assert placement.validate_devices(house, [_bath_dev("socket", 4300, 4600, 300)]) == []


def test_shaver_unit_allowed_in_zone_2_not_zone_1(house):
    assert placement.validate_devices(house, [_bath_dev("shaver_unit", 5300, 7500, 1000)]) == []
    assert placement.validate_devices(house, [_bath_dev("shaver_unit", 6000, 7500, 1200)])[0].rule == "EA2-device-in-zone"


def test_shower_without_basin_zone_1_radius():
    w = zones.WetArea((5700, 7000, 6700, 8000), has_basin=False, outlet_xy=(6200, 7500))
    assert zones.zone_at(7300, 7500, 1000, [w]) == 1     # 1100 mm from the outlet
    assert zones.zone_at(7500, 7500, 1000, [w]) is None  # 1300 mm: no zone 2 for a basin-less shower
    assert zones.zone_at(6200, 7500, 50, [w]) == 0


def test_engine_places_nothing_in_a_zone_and_flags_nothing(house):
    devs = placement.place_devices(house)
    assert placement.validate_devices(house, devs) == []
    assert not any(d.kind in placement.SOCKET_KINDS for d in devs if d.room == "BATH")


def test_ea2_check_fails_when_a_socket_is_injected(house):
    devs = placement.place_devices(house)
    devs.append(placement.Device("BAD", "socket", "BATH", 6000, 7500, 1200))
    res = checks.run_checks(circuits.design(house, devs))
    bad = by(res, "EA2", "fail", "BATH")
    assert bad and bad[0].gate and "zone 1" in bad[0].message


def test_switch_height_band(house):
    devs = placement.place_devices(house)
    sw = next(d for d in devs if d.kind == "switch")
    assert placement.validate_devices(house, [sw]) == []
    sw.z = 1400
    assert placement.validate_devices(house, [sw])[0].rule == "EA1-switch-height"


def test_switch_on_latch_side(house):
    r = house.room("BED")
    d = next(x for x in house.doors if x.room == "BED")      # hinge 'end' -> latch at the start of the opening
    x, y = placement.switch_for_door(r, d)
    assert x == d.offset_mm - 150 and y == r.rect[1]


# ---- EA1 provision -----------------------------------------------------------------------------------------
def test_ea1_bed_gets_both_sides(house):
    devs = placement.place_devices(house)
    bs = [d for d in devs if d.rule == "EA1-bedside-both-sides"]
    xs = sorted(d.x for d in bs)
    bed = next(f for f in house.furniture if f.kind == "bed")
    assert len(bs) == 2 and xs[0] < bed.rect[0] < bed.rect[2] < xs[1]


def test_ea1_fails_when_bedside_sockets_are_removed(house):
    devs = [d for d in placement.place_devices(house) if d.rule != "EA1-bedside-both-sides"]
    res = checks.run_checks(circuits.design(house, devs))
    assert by(res, "EA1", "fail", "BED")


def test_ea1_worktop_pitch(house):
    devs = placement.place_devices(house)
    wt = [d for d in devs if d.rule == "EA1-worktop-pitch"]
    xs = sorted(d.x for d in wt)
    assert len(wt) == 3 and max(b - a for a, b in zip(xs, xs[1:])) <= placement.WORKTOP_PITCH_MM


# ---- EA3 circuits -------------------------------------------------------------------------------------------
def test_every_zone_on_exactly_one_circuit_and_lighting_under_10A(house):
    d, res = results(house)
    assert not by(res, "EA3", "fail")
    assert all(c.ib_a <= 10.0 for c in d.circuits if c.kind == "lighting")


def test_zone_over_10A_is_flagged(house):
    h = copy.deepcopy(house)
    i = next(i for i, z in enumerate(h.zones) if z.id == "Z-LIV-1")
    h.zones[i] = dataclasses.replace(h.zones[i], watts=3000.0)
    d, res = results(h)
    assert by(res, "EA3", "fail", "DB-GF/L")


def test_many_zones_are_packed_without_splitting(house):
    h = copy.deepcopy(house)
    h.zones = [dataclasses.replace(z, watts=800.0) if z.room == "LIV" else z for z in h.zones]
    d, res = results(h)
    liv = [c for c in d.circuits if c.kind == "lighting" and c.rooms == ["LIV"]]
    assert len(liv) == 2 and all(len(c.zone_ids) >= 1 for c in liv)
    assert sorted(z for c in liv for z in c.zone_ids) == ["Z-LIV-1", "Z-LIV-2", "Z-LIV-3"]


# ---- EA5/EA6 ---------------------------------------------------------------------------------------------------
def test_all_cables_satisfy_ib_in_iz(house):
    d, res = results(house)
    assert all(c.ib_a <= c.in_a <= c.size.iz_a + 1e-9 for c in d.circuits)
    assert not by(res, "EA5", "fail")


def test_hotter_roof_lowers_lighting_factor(house):
    h = copy.deepcopy(house)
    h.supply = dataclasses.replace(h.supply, roof_ambient_c=55.0)
    d1, _ = results(house)
    d2, _ = results(h)
    f1 = next(c for c in d1.circuits if c.kind == "lighting").size.factor
    f2 = next(c for c in d2.circuits if c.kind == "lighting").size.factor
    assert f2 < f1


def test_long_runs_are_upsized_for_voltage_drop(house):
    h = copy.deepcopy(house)
    h.supply = dataclasses.replace(h.supply, board_xy=(-40000.0, 4500.0))
    d, _ = results(h)
    d0, _ = results(house)
    assert sum(c.csa_mm2 for c in d.circuits) > sum(c.csa_mm2 for c in d0.circuits)


# ---- EA7/EA8 -------------------------------------------------------------------------------------------------------
def test_tt_without_ra_is_not_evaluated(house):
    h = copy.deepcopy(house)
    h.supply = dataclasses.replace(h.supply, ra_ohm=None)
    _, res = results(h)
    assert by(res, "EA7", "not_evaluated") and not by(res, "EA7", "pass") and not by(res, "EA7", "fail")


def test_tn_loop_impedance_pass_and_fail(house):
    h = copy.deepcopy(house)
    h.supply = dataclasses.replace(h.supply, earthing="TN", ze_ohm=0.8, ra_ohm=None)
    _, res = results(h)
    assert not by(res, "EA7", "fail") and by(res, "EA7", "pass")
    h.supply = dataclasses.replace(h.supply, ze_ohm=6.0)
    _, res2 = results(h)
    assert by(res2, "EA7", "fail")                       # 220 / 6 = 36 A < 5 x 16 A


def test_disconnection_limit_is_0_4s_tn_and_0_2s_tt(house):
    d, _ = results(house)
    assert d.circuits[0].disconnect_limit_s == 0.2
    h = copy.deepcopy(house)
    h.supply = dataclasses.replace(h.supply, earthing="TN", ze_ohm=0.8)
    d2, _ = results(h)
    assert d2.circuits[0].disconnect_limit_s == 0.4


def test_ea8_every_circuit_30mA_type_A_and_negative(house):
    d, _ = results(house)
    assert all(c.rcd_ma == 30.0 and c.rcd_type == "A" for c in d.circuits)
    d.circuits[0].rcd_ma = 300.0
    assert by(checks.run_checks(d), "EA8", "fail", d.circuits[0].id)


# ---- EA11/EA12/EA13 --------------------------------------------------------------------------------------------------
def test_phase_balance_unit():
    assert phase_balance({"L1": 100, "L2": 105, "L3": 95})[0]
    assert not phase_balance({"L1": 100, "L2": 140, "L3": 60})[0]


def test_demo_phases_within_10_percent(house):
    _, res = results(house)
    assert by(res, "EA11", "pass")


def test_ea12_detects_missing_circuit_in_sld(house):
    d = circuits.design(house, placement.place_devices(house))
    svg = schedule.sld_svg(d).replace('<g id="DB-GF/S1">', '<g id="X">')
    assert by(checks.run_checks(d, svg), "EA12", "fail", "schedule")


def test_ea13_luminaire_in_two_zones_and_watt_mismatch(house):
    h = copy.deepcopy(house)
    z = h.zones[1]
    h.zones[1] = dataclasses.replace(z, luminaire_ids=z.luminaire_ids + (h.zones[0].luminaire_ids[0],))
    _, res = results(h)
    assert by(res, "EA13", "fail")
    h2 = copy.deepcopy(house)
    h2.luminaires[0] = dataclasses.replace(h2.luminaires[0], watts=50.0)
    _, res2 = results(h2)
    assert by(res2, "EA13", "fail", "DB-GF/L")


# ---- outputs -----------------------------------------------------------------------------------------------------------
def test_reference_cases_all_within_tolerance():
    rc = reference_cases.run()
    assert len(rc) >= 15 and all(r.ok for r in rc), [(r.name, r.expected, r.achieved) for r in rc if not r.ok]


def test_demo_writes_contract_results_and_no_failures(tmp_path):
    r = demo.run(FIX, tmp_path / "o", tmp_path / "checks")
    assert (tmp_path / "o" / "sld.svg").read_text(encoding="utf-8").startswith("<svg")
    data = json.loads((tmp_path / "checks" / "L7.json").read_text(encoding="utf-8"))
    assert data["lane"] == "L7" and data["contract"] == contracts.CONTRACT_VERSION
    assert "fail" not in {x["status"] for x in data["results"]}
    assert len(contracts.read_all_results(tmp_path / "checks")) == len(data["results"])
    assert all(isinstance(c, contracts.Circuit) for c in circuits.to_contract(r["design"]))


def test_not_evaluated_criteria_never_pass(house):
    _, res = results(house)
    for crit in ("EA9", "EA10", "EA14", "EA15"):
        assert by(res, crit) and all(r.status == "not_evaluated" for r in by(res, crit))


# ---- fail-closed paths -----------------------------------------------------------------------------------------------
def test_ea2_not_evaluated_when_bathroom_has_no_wet_area(house):
    h = copy.deepcopy(house)
    h.furniture = [f for f in h.furniture if f.kind not in ("shower", "bath")]
    _, res = results(h)
    r = by(res, "EA2", subject="BATH")
    assert r and all(x.status == "not_evaluated" for x in r)


def test_ea2_applies_to_a_wet_room_not_named_bathroom(house):
    h = copy.deepcopy(house)
    h.rooms = [dataclasses.replace(r, kind="ensuite") if r.id == "BATH" else r for r in h.rooms]
    devs = placement.place_devices(h)
    devs.append(placement.Device("BAD", "socket", "BATH", 6000, 7500, 1200))
    res = checks.run_checks(circuits.design(h, devs))
    assert by(res, "EA2", "fail", "BATH")


def test_ca_beyond_the_table_gives_no_rating():
    from archpipe.electrical import sizing
    assert sizing.ca_factor(65, "PVC") == 0.0 and sizing.ca_factor(90, "XLPE_EPR") == 0.0
    assert sizing.ca_factor(65, "XLPE_EPR") == 0.65
    r = sizing.size_cable(10, 16, [sizing.Segment("hot", 5, ambient_c=65)], sizing.TableSpec("whit_t47", col="clipped_2"))
    assert not r.ok


def test_ea13_zone_naming_unknown_luminaire_fails_not_raises(house):
    h = copy.deepcopy(house)
    z = h.zones[0]
    h.zones[0] = dataclasses.replace(z, luminaire_ids=z.luminaire_ids + ("GHOST-1",))
    _, res = results(h)
    assert by(res, "EA13", "fail", "Z-LIV-1") and by(res, "EA13", "fail", "DB-GF/L1")
