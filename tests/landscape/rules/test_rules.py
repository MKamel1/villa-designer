"""Positive and negative test for every quantitative rule, plus the loader's fail-closed checks."""
import copy
import json
import unittest

from archpipe.landscape.rules import evaluate, load, validate_layout
from archpipe.landscape.rules.loader import RuleSet
from archpipe.rules import Rule

from .fixtures import good

RS = load()


def res(layout, rule):
    return [r for r in evaluate(layout, RS) if r.criterion == rule]


def statuses(layout, rule):
    return {r.status for r in res(layout, rule)}


class Loader(unittest.TestCase):
    def test_every_rule_is_a_framework_rule_with_a_source(self):
        self.assertTrue(all(isinstance(r, Rule) for r in RS.rules.values()))
        for rid, ids in RS.source_ids.items():
            self.assertTrue(ids, rid)
        self.assertEqual(len(RS.params), 23)
        self.assertEqual(len(RS.advisory_ids), 34)

    def test_advisory_rules_carry_no_measurement_and_are_advisory_kind(self):
        for i in RS.advisory_ids:
            self.assertEqual(RS.rules[i].kind, "advisory")
        data = copy.deepcopy(RS.data)
        data["advisory"][0]["params"] = {"min": 1}
        with self.assertRaises(ValueError):
            RuleSet(data)

    def test_unknown_source_and_unverified_only_computed_rule_raise(self):
        data = copy.deepcopy(RS.data)
        data["rules"][0]["sources"] = ["NO-SUCH-CARD"]
        with self.assertRaises(ValueError):
            RuleSet(data)
        data = copy.deepcopy(RS.data)
        data["rules"][0]["sources"] = ["AL-APL-numbers"]
        with self.assertRaises(ValueError):
            RuleSet(data)

    def test_a_sourced_card_needs_a_verbatim_quote(self):
        data = copy.deepcopy(RS.data)
        data["sources"][0]["quote"] = ""
        with self.assertRaises(ValueError):
            RuleSet(data)

    def test_the_koi_depth_card_is_not_wired_to_any_rule(self):
        used = {i for ids in RS.source_ids.values() for i in ids}
        self.assertNotIn("TS-530-15-depth-NOT-KOI", used)

    def test_layout_without_schema_is_refused(self):
        with self.assertRaises(ValueError):
            validate_layout({})


class GoodLayoutIsQuiet(unittest.TestCase):
    def test_no_fail_or_warn(self):
        bad = [(r.criterion, r.subject, r.status, r.message) for r in evaluate(good(), RS)
               if r.status in ("fail", "warn")]
        # the declared fire cover is reported as a warning by design (no required value is held)
        self.assertEqual([b[0] for b in bad], ["LS-FIRE-COVER"], bad)

    def test_every_computed_rule_ran(self):
        ran = {r.criterion for r in evaluate(good(), RS)}
        self.assertEqual(ran, set(RS.params))


def mutate(**kw):
    """One negative: change a good layout with a function and expect a status for a rule."""
    return kw


class Negatives(unittest.TestCase):
    def case(self, rule, fn, status="fail", positive=None):
        L = good()
        fn(L)
        if status == "fail" and RS.severity[rule] == "warning":
            status = "warn"      # a warning-grade rule that is not met reports `warn`
        self.assertIn(status, statuses(L, rule), rule)
        if positive:
            self.assertNotIn("fail", statuses(good(), rule))

    def test_path_main(self):
        self.case("LS-PATH-MAIN", lambda L: L["paths"][0].update(width_m=0.9))
        r = res(good(), "LS-PATH-MAIN")[0]
        self.assertEqual((r.status, r.achieved, r.required), ("pass", 1400, 1200))

    def test_path_secondary(self):
        self.case("LS-PATH-SECONDARY", lambda L: L["paths"][1].update(width_m=0.5))
        self.assertEqual(statuses(good(), "LS-PATH-SECONDARY"), {"pass"})

    def test_service_path_is_a_gap_not_a_pass(self):
        L = good(); L["paths"].append({"id": "p-svc", "class": "service", "width_m": 0.3})
        self.assertIn("not_evaluated", statuses(L, "LS-PATH-SECONDARY"))

    def test_step_riser(self):
        self.case("LS-STEP-RISER", lambda L: L["steps"][0].update(riser_mm=190))
        self.case("LS-STEP-RISER", lambda L: L["steps"][0].update(riser_mm=100))
        self.case("LS-STEP-RISER", lambda L: L["steps"][0].update(riser_mm=170), status="warn")  # utilitarian band
        self.assertEqual(statuses(good(), "LS-STEP-RISER"), {"pass"})

    def test_step_2rg(self):
        self.case("LS-STEP-2RG", lambda L: L["steps"][0].update(going_mm=250))   # 530
        self.case("LS-STEP-2RG", lambda L: L["steps"][0].update(going_mm=450))   # 730
        self.assertEqual(statuses(good(), "LS-STEP-2RG"), {"pass"})              # 2*140+380 = 660

    def test_step_count_single_step(self):
        self.case("LS-STEP-COUNT", lambda L: L["steps"][0].update(count=1))
        self.assertEqual(statuses(good(), "LS-STEP-COUNT"), {"pass"})

    def test_step_width_and_landing(self):
        self.case("LS-STEP-WIDTH", lambda L: L["steps"][0].update(width_mm=900))
        self.case("LS-STEP-LANDING", lambda L: L["steps"][0].update(count=12, riser_mm=150))
        self.assertEqual(statuses(good(), "LS-STEP-WIDTH") | statuses(good(), "LS-STEP-LANDING"), {"pass"})

    def test_seatwall(self):
        self.case("LS-SEATWALL", lambda L: L["seatwalls"][0].update(height_mm=600))
        self.assertEqual(statuses(good(), "LS-SEATWALL"), {"pass"})

    def test_dining_area_per_seat(self):
        self.case("LS-DINE-AREA", lambda L: L["tables"][0].update(seats=12))   # 36 m2 / 12 = 3.0
        r = res(good(), "LS-DINE-AREA")[0]
        self.assertEqual((r.status, r.achieved), ("pass", 6.0))                # 36 / 6

    def test_dining_clear_strip(self):
        self.case("LS-DINE-CLEAR", lambda L: L["obstacles"].append({"id": "o", "rect": [3.7, 2, 4.5, 4]}))
        r = [x for x in res(good(), "LS-DINE-CLEAR")][0]
        self.assertEqual(r.status, "pass")

    def test_capacity(self):
        self.case("LS-CAPACITY", lambda L: L["seating"].clear())               # 6 seats < 10
        self.assertEqual(statuses(good(), "LS-CAPACITY"), {"pass"})

    def test_fire_clear_fail_warn_pass(self):
        self.case("LS-FIRE-CLEAR", lambda L: L["obstacles"].append({"id": "o", "rect": [16.9, 9, 18, 11]}))  # 0.4 m
        self.case("LS-FIRE-CLEAR", lambda L: L["obstacles"].append({"id": "o", "rect": [17.5, 9, 19, 11]}), status="warn")  # 1.0 m: above 900, below 1200
        self.assertEqual(statuses(good(), "LS-FIRE-CLEAR"), {"pass"})

    def test_fire_plants_and_facade_count(self):
        L = good(); L["buildings"].append([16, 10.9, 20, 14])                  # facade 0.4 m from the pit edge
        r = res(L, "LS-FIRE-CLEAR")[0]
        self.assertEqual((r.status, r.achieved), ("fail", 400))

    def test_fire_seat_distance(self):
        self.case("LS-FIRE-SEAT", lambda L: L["seating"].append({"id": "s", "zone": "z-lounge", "rect": [16.9, 9, 17.5, 10], "seats": 1}), status="fail")
        self.assertEqual(statuses(good(), "LS-FIRE-SEAT"), {"pass"})

    def test_fire_product_clearance(self):
        self.case("LS-FIRE-PRODUCT", lambda L: L["features"][0].update(product_clearance_mm=5000))
        L = good(); del L["features"][0]["product_clearance_mm"]
        self.assertEqual(statuses(L, "LS-FIRE-PRODUCT"), {"not_evaluated"})

    def test_fire_cover_never_passes(self):
        self.assertEqual(statuses(good(), "LS-FIRE-COVER"), {"warn"})
        L = good(); del L["features"][0]["cover"]
        self.assertEqual(statuses(L, "LS-FIRE-COVER"), {"not_evaluated"})

    def test_pond_freeboard(self):
        self.case("LS-POND-FREEBOARD", lambda L: L["features"][1].update(freeboard_mm=100))
        self.case("LS-POND-FREEBOARD", lambda L: L["features"][1].update(edge="hard", freeboard_mm=50))
        self.assertEqual(statuses(good(), "LS-POND-FREEBOARD"), {"pass"})
        L = good(); L["features"][1]["edge"] = "hard"; L["features"][1]["freeboard_mm"] = 75
        self.assertEqual(statuses(L, "LS-POND-FREEBOARD"), {"pass"})

    def test_pond_flush_margin(self):
        self.case("LS-POND-FLUSH-MARGIN", lambda L: L["features"][1].update(margin_slope_back_mm=300), status="warn")
        L = good(); L["features"][1]["flush"] = False
        self.assertEqual(statuses(L, "LS-POND-FLUSH-MARGIN"), set())

    def test_soil_depth(self):
        self.case("LS-SOIL-DEPTH", lambda L: L["planting_groups"][0].update(soil_depth_mm=300))
        L = good(); L["planting_groups"][0].pop("soil_depth_mm")
        self.assertEqual(statuses(L, "LS-SOIL-DEPTH"), {"not_evaluated"})
        L = good(); L["planting_groups"][0]["over_structure"] = False; L["planting_groups"][0]["soil_depth_mm"] = 50
        self.assertEqual(statuses(L, "LS-SOIL-DEPTH"), set())                  # on grade: rule does not apply

    def test_slopes(self):
        self.case("LS-SLOPE", lambda L: L["paved_areas"][0].update(slope_pct=4))
        self.case("LS-SLOPE", lambda L: L["paved_areas"][0].update(slope_pct=0))    # ponds water
        self.case("LS-SLOPE", lambda L: L["paths"][0].update(cross_slope_pct=3))    # main path: accessible 2 %
        self.case("LS-SLOPE", lambda L: L["zones"][2].update(slope_pct=9))
        self.assertEqual(statuses(good(), "LS-SLOPE"), {"pass"})

    def test_hydrozone(self):
        self.case("LS-HYDROZONE", lambda L: L["planting_groups"][0]["plants"].append({"species": "C", "water_need": "high", "form": "shrub"}))
        self.assertEqual(statuses(good(), "LS-HYDROZONE"), {"pass"})

    def test_enclosure(self):
        self.case("LS-ENCLOSURE", lambda L: L["zones"][0].update(enclosure_height_m=1.0), status="warn")  # 1/6
        self.assertEqual(statuses(good(), "LS-ENCLOSURE"), {"pass"})

    def test_screen(self):
        self.case("LS-SCREEN", lambda L: L["boundary"][0].update(height_m=1.2))
        self.case("LS-SCREEN", lambda L: L["boundary"][0].update(kind="hedge"), status="warn")
        L = good(); L["boundary"][0].update(side="street", height_m=1.0)
        self.assertEqual(statuses(L, "LS-SCREEN"), set())

    def test_rootzone(self):
        self.case("LS-ROOTZONE", lambda L: L["paved_areas"].append({"id": "pv", "rect": [9, 11, 11, 13], "material": "brick", "slope_pct": 1}))
        L = good(); L["zones"].append({"id": "tz", "use": "other", "rect": [8, 10, 12, 14], "surface": "artificial-turf"})
        self.assertIn("not_evaluated", statuses(L, "LS-ROOTZONE"))
        self.assertEqual(statuses(good(), "LS-ROOTZONE"), {"pass"})


if __name__ == "__main__":
    unittest.main()
