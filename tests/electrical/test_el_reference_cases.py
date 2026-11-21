"""Published worked examples reproduced by the engine (inputs and expected values are the source's own)."""
import math

import pytest

from archpipe.electrical import data
from archpipe.electrical.demand import DemandItem, apartment_diversity, max_demand
from archpipe.electrical.sizing import (Segment, TableSpec, phase_equivalent, size_cable, vd_percent, vd_volts)


def within(got, expected, tol):
    return abs(got - expected) <= tol * abs(expected)


# ---- Maximum demand ------------------------------------------------------------------------
def test_whitfield_example_6_1_shop_486A_162A():
    """EL-EX-WHIT-6.1: shop, 415 V 3-phase, 240 V per phase; expected total 486.2 A, line 162 A (+-2 %)."""
    kw = lambda p: p * 1000.0 / 240.0
    items = []
    items += [DemandItem(f"wh6-{i}", "thermo_wh", kw(6)) for i in range(2)] + [DemandItem(f"wh3-{i}", "thermo_wh", kw(3)) for i in range(7)]
    items += [DemandItem(f"iwh-{i}", "inst_wh", kw(3)) for i in range(2)]
    items += [DemandItem("ck6a", "cooker", kw(6)), DemandItem("ck6b", "cooker", kw(6)), DemandItem("ck4", "cooker", kw(4))]
    items += [DemandItem("disch", "lighting", kw(12), multiplier=1.8)]
    items += [DemandItem(f"ring{i}", "sockets", 30.0) for i in range(8)]
    # shop column: cookers ranked 100/80/60 (the book's table), so use the shop premises rules
    r = max_demand(items, premises="shop", v_phase=240.0)
    assert within(r.total_a, 486.2, 0.02), r.total_a
    assert within(r.line_a_3ph, 162.0, 0.02), r.line_a_3ph
    # category-level cross-checks against the book's own sub-totals
    assert within(r.by_cat["thermo_wh"]["demand_a"], 137.6, 0.01)
    assert within(r.by_cat["cooker"]["demand_a"], 55.0, 0.01)
    assert within(r.by_cat["lighting"]["demand_a"], 81.1, 0.01)
    assert within(r.by_cat["sockets"]["demand_a"], 187.5, 0.001)


def test_whitfield_example_6_2_cooker_29_5A():
    """EL-EX-WHIT-6.2: 14 kW cooker, 240 V, socket on the control unit -> 29.5 A."""
    r = max_demand([DemandItem("cooker", "cooker", 14000 / 240.0, socket_on_cooker=True)], "household", 240.0)
    assert within(r.total_a, 29.5, 0.01), r.total_a


def test_eig_apartment_block_69kVA_100A():
    """EL-EX-EIG-A12: 25 consumers x 6 kVA -> 150 kVA x 0.46 = 69 kVA, 100 A at 400 V."""
    ks = apartment_diversity(25)
    assert ks == 0.46
    kva = 150 * ks
    assert within(kva, 69.0, 0.02)
    assert within(kva * 1000 / (400 * math.sqrt(3)), 100.0, 0.02)


def test_demand_negative_unknown_category_raises():
    with pytest.raises(KeyError):
        max_demand([DemandItem("x", "teleporter", 10.0)])


# ---- Cable sizing -------------------------------------------------------------------------
def test_whitfield_example_4_1_roof_space_50C():
    """EL-EX-WHIT-4.1: 15 A MCB, 50 C roof space, 8 circuits bunched through 50 mm insulation -> 10 mm2 (6 mm2 = 32 A fails);
    two bunches of four -> 6 mm2."""
    spec = TableSpec("whit_t47", col="in_insulation_2")
    roof = Segment("roof", 10, ambient_c=50)
    eight = size_cable(12.5, 15, [roof, Segment("cavity", 0.05, group_circuits=8, insulation_mm=50)], spec)
    assert eight.ok and eight.csa_mm2 == 10 and within(eight.factor, 0.52 * 0.89, 0.001)
    six = size_cable(12.5, 15, [roof, Segment("cavity", 0.05, group_circuits=8, insulation_mm=50)], spec, min_csa=6)
    assert six.i_tab_a == 43  # 6 mm2 (32 A x 0.463 = 14.8 A < 15 A) was rejected
    four = size_cable(12.5, 15, [roof, Segment("cavity", 0.05, group_circuits=4, insulation_mm=50)], spec)
    assert four.ok and four.csa_mm2 == 6


def test_whitfield_example_4_1_negative_product_method_is_stricter():
    spec = TableSpec("whit_t47", col="in_insulation_2")
    segs = [Segment("roof", 10, ambient_c=50), Segment("cavity", 0.05, group_circuits=4, insulation_mm=50)]
    prod = size_cable(12.5, 15, segs, spec, combine="product")
    assert prod.csa_mm2 > 6          # 0.71 x 0.65 x 0.89 = 0.41: 32 A x 0.41 < 15 A


def test_whitfield_example_4_5_voltage_drop_1_28V_105m():
    """EL-EX-WHIT-4.5: 6 mm2 twin, 7.3 mV/A/m, 12.5 A, 14 m -> 1.28 V; max length 105 m for 9.6 V."""
    v = vd_volts(6, 12.5, 14, "1ph")
    assert within(v, 1.28, 0.01)
    assert within(9.6 * 14 / v, 105.0, 0.01)


@pytest.mark.parametrize("name,ib,ir,par,expect", [("C1", 909, 920, 2, 240), ("C3", 526, 526, 2, 120), ("C7", 238, 238, 1, 95)])
def test_schneider_worked_example_sizes(name, ib, ir, par, expect):
    """EL-EX-EIG-WEX (method F, 3 PVC copper); the same page's Ecodial run gives the same csa (2x240, 2x120, 1x95)."""
    r = size_cable(ib, ir, [], TableSpec("iec_c521_F"), parallel=par)
    assert r.ok and r.csa_mm2 == expect, (name, r)


def test_schneider_worked_example_voltage_drop_G72():
    """Fig G72: 0.12 / 0.47 / 0.13 %, total 0.73 % at 400 V (three-phase 'motor, cos phi 0.8' column)."""
    v1 = vd_volts(240, 909, 5, "3ph", "motor", parallel=2)
    v3 = vd_volts(120, 526, 20, "3ph", "motor", parallel=2)
    v7 = vd_volts(95, 238, 5, "3ph", "motor")
    assert [round(v, 2) for v in (v1, v3, v7)] == [0.50, 1.89, 0.51]
    assert [round(vd_percent(v, "3ph", 400 / math.sqrt(3)), 2) for v in (v1, v3, v7)] == [0.12, 0.47, 0.13]
    assert within(vd_percent(v1 + v3 + v7, "3ph", 400 / math.sqrt(3)), 0.73, 0.02)


def test_schneider_example_2_feeder_plus_final_10_1V_4_4pct():
    """EL-EX-EIG-G32 (feeder 3ph lighting column + single-phase lighting circuit, source G30 for both)."""
    feeder = vd_volts(70, 150, 50, "3ph", "light", source="g30")
    final = vd_volts(2.5, 20, 20, "1ph", "light", source="g30")
    total = phase_equivalent(feeder, "3ph") + final
    assert within(feeder, 4.4, 0.01) and within(final, 7.6, 0.001)
    assert within(total, 10.1, 0.01)
    assert round(100 * total / 230, 1) == 4.4


def test_sizing_negative_in_below_ib_and_no_table_cell():
    spec = TableSpec("whit_t47", col="clipped_2")
    assert not size_cable(20, 16, [], spec).ok
    assert not size_cable(500, 500, [], spec).ok     # table stops at 16 mm2


def test_cards_for_reference_cases_exist_and_status():
    for cid in ("EL-EX-WHIT-6.1", "EL-EX-WHIT-6.2", "EL-EX-WHIT-4.1", "EL-EX-WHIT-4.5", "EL-EX-EIG-A12", "EL-EX-EIG-WEX", "EL-EX-EIG-G32"):
        assert data.card(cid).status == "sourced"
