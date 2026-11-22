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
        self.assertEqual(len(RS.params), 41)
        self.assertEqual(len(RS.advisory_ids), 44)

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
        data["sources"].append({**data["sources"][0], "id": "UNV", "status": "unverified"})
        data["rules"][0]["sources"] = ["UNV"]
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

    def test_pattern_language_is_held_and_every_pattern_is_advisory(self):
        self.assertEqual(RS.withdrawn, {})
        ver = RS.data["apl_verification"]["patterns"]
        self.assertEqual(len(ver), 29)  # 27 first-pass + 2 added
        self.assertTrue(all(v["name_match"] in (True, None) for v in ver))
        apl = [i for i in RS.rules if i.startswith("AD-APL")]
        self.assertEqual(len(apl), 14)
        self.assertTrue(set(apl) <= set(RS.advisory_ids))
        for w in (105, 172, 71, 246, 177, 170, 125, 245, 247, 168, 104, 60):
            self.assertIn(f"AD-APL-{w}", RS.rules)
        # the 15 re-grounded keep the held-book source and gain the Alexander cards
        for rid in ("AD-COMP-ENCLOSURE", "AD-COMP-HIERARCHY", "AD-COMP-REFUGE"):
            ids = RS.source_ids[rid]
            self.assertTrue(any(i.startswith("APL-") for i in ids), rid)
            self.assertTrue(any(not i.startswith("APL-") for i in ids), rid)

    def _mutated(self, fn):
        data = copy.deepcopy(RS.data)
        fn(data)
        with self.assertRaises(ValueError):
            RuleSet(data)

    def test_loader_refuses_a_pattern_rule_with_a_number(self):
        adv = lambda d: next(a for a in d["advisory"] if a["id"] == "AD-APL-247")
        for key in ("measurement", "params", "threshold", "value"):
            self._mutated(lambda d, k=key: adv(d).update({k: 25}))

    def test_loader_refuses_a_wrong_pattern_name_or_foreign_card(self):
        adv = lambda d: next(a for a in d["advisory"] if a["id"] == "AD-APL-247")
        self._mutated(lambda d: adv(d).update(title="Paving With Gaps"))
        self._mutated(lambda d: adv(d).update(sources=["APL-60-therefore"]))
        self._mutated(lambda d: next(s for s in d["sources"] if s["id"] == "APL-247-problem").update(pattern=248))
        self._mutated(lambda d: next(s for s in d["sources"] if s["id"] == "APL-247-therefore").pop("therefore_pdf_page"))

    def test_loader_refuses_a_withdrawn_rule_with_the_wrong_status_or_also_active(self):
        data = copy.deepcopy(RS.data)
        data["withdrawn"] = [dict(id="AD-APL-9", status="unverified")]
        with self.assertRaises(ValueError):
            RuleSet(data)
        data["withdrawn"] = [dict(id=RS.advisory_ids[0], status="unverified — not used")]
        with self.assertRaises(ValueError):
            RuleSet(data)

    def test_crowd_maximum_and_lily_pool_cards_are_not_wired_to_any_rule(self):
        used = {i for ids in RS.source_ids.values() for i in ids}
        for k in ("MH-15-6-tableIII-crowd-max-NOT-COMFORT", "NF-113-lily-pool-NOT-KOI", "H-adk-k2-600"):
            self.assertIn(k, RS.sources)
            self.assertNotIn(k, used)

    def test_every_web_and_held_card_is_a_sourced_quote(self):
        for s in RS.sources.values():
            if s.status == "sourced":
                self.assertTrue(s.quote.strip(), s.id)

    def test_closed_gaps_name_their_rule(self):
        for g in RS.data["closed_gaps"]:
            self.assertNotIn(g["id"], RS.gaps)
            for part in g["closed_by"].replace(",", " ").split():
                if part.startswith(("LS-", "AD-")) and not part.endswith("*"):
                    self.assertIn(part, RS.rules, g["id"])

    def test_layout_without_schema_is_refused(self):
        with self.assertRaises(ValueError):
            validate_layout({})


class GoodLayoutIsQuiet(unittest.TestCase):
    def test_no_fail_or_warn(self):
        bad = [(r.criterion, r.subject, r.status, r.message) for r in evaluate(good(), RS)
               if r.status in ("fail", "warn")]
        self.assertEqual(bad, [], bad)

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

    def test_brief_features(self):
        self.case("LS-BRIEF-FEATURES", lambda L: L["features"].pop(0))                 # drop the fire pit
        self.case("LS-BRIEF-FEATURES", lambda L: L["features"].remove(L["features"][2]))  # drop the herb bed
        L = good(); L["features"][0]["kind"] = "heater"                                # heater is an allowed alternative
        self.assertNotIn("fail", statuses(L, "LS-BRIEF-FEATURES"))
        self.assertEqual(statuses(good(), "LS-BRIEF-FEATURES"), {"pass"})

    def test_path_main(self):
        self.case("LS-PATH-MAIN", lambda L: L["paths"][0].update(width_m=0.9))
        r = res(good(), "LS-PATH-MAIN")[0]
        self.assertEqual((r.status, r.achieved, r.required), ("pass", 1400, 1200))

    def test_path_secondary(self):
        self.case("LS-PATH-SECONDARY", lambda L: L["paths"][1].update(width_m=0.5))
        self.assertEqual(statuses(good(), "LS-PATH-SECONDARY"), {"pass"})

    def test_service_path(self):
        self.case("LS-PATH-SERVICE", lambda L: L["paths"][2].update(width_m=0.4))                 # below a wheelbarrow
        self.case("LS-PATH-SERVICE", lambda L: L["paths"][2].update(width_m=0.7), status="warn")  # 600-900
        self.assertEqual(statuses(good(), "LS-PATH-SERVICE"), {"pass"})
        L = good(); L["paths"][2]["class"] = "weird"
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

    def test_fire_cover_load(self):
        self.case("LS-FIRE-COVER", lambda L: L["features"][0]["cover"].update(load_rating_kN=5))
        r = res(good(), "LS-FIRE-COVER")[0]
        self.assertEqual((r.status, r.achieved, r.required), ("pass", 15, 15.0))
        L = good(); del L["features"][0]["cover"]
        self.assertEqual(statuses(L, "LS-FIRE-COVER"), {"not_evaluated"})

    def test_fire_overhead(self):
        self.case("LS-FIRE-OVERHEAD", lambda L: L["features"][0].update(overhead_clear_m=1.5))
        self.assertEqual(statuses(good(), "LS-FIRE-OVERHEAD"), {"pass"})
        L = good(); del L["features"][0]["overhead_clear_m"]
        self.assertEqual(statuses(L, "LS-FIRE-OVERHEAD"), {"not_evaluated"})

    def test_fire_distance_to_structure_and_wood_tier(self):
        self.case("LS-FIRE-STRUCT", lambda L: L["buildings"].append([16, 11.2, 20, 14]))   # 0.7 m from the pit edge
        self.case("LS-FIRE-STRUCT", lambda L: L["features"][0].update(fuel="wood"))        # tree 3.8 m < 4.57 m
        self.assertEqual(statuses(good(), "LS-FIRE-STRUCT"), {"pass"})                     # gas: nearest is the tree at ~3.8 m

    def test_flush_lip_and_opening(self):
        self.case("LS-FLUSH-LIP", lambda L: L["features"][0]["cover"].update(lip_mm=10))                 # needs a bevel
        self.case("LS-FLUSH-LIP", lambda L: L["features"][0]["cover"].update(lip_mm=20, bevelled=True))
        L = good(); L["features"][0]["cover"].update(lip_mm=10, bevelled=True)
        self.assertEqual(statuses(L, "LS-FLUSH-LIP"), {"pass"})
        self.assertEqual(statuses(good(), "LS-FLUSH-LIP"), {"pass"})
        self.case("LS-FLUSH-OPENING", lambda L: L["features"][0]["cover"].update(max_opening_mm=25))
        self.assertEqual(statuses(good(), "LS-FLUSH-OPENING"), {"pass"})

    def test_pond_child_protection(self):
        self.case("LS-POND-GUARD", lambda L: L["features"][3].pop("child_protection"))
        self.case("LS-POND-GUARD", lambda L: L["features"][3].update(child_protection="fence", fence_height_mm=900))
        self.case("LS-POND-GUARD", lambda L: L["features"][3].update(child_protection="net"))
        L = good(); L["features"][3].update(child_protection="fence", fence_height_mm=1100)
        self.assertEqual(statuses(L, "LS-POND-GUARD"), {"pass"})
        L = good(); L["features"][3]["flush"] = False                                      # raised pond: rule silent
        self.assertEqual(statuses(L, "LS-POND-GUARD"), set())
        self.assertEqual(statuses(good(), "LS-POND-GUARD"), {"pass"})

    def test_pond_edge_slope_and_light(self):
        self.case("LS-POND-EDGE-SLOPE", lambda L: L["features"][3].update(edge_slope_run_per_rise=2))
        self.case("LS-POND-EDGE-LIGHT", lambda L: L["features"][3].update(edge_lux=1))
        self.case("LS-POND-EDGE-LIGHT", lambda L: L["features"][0].update(edge_lux=0.5))
        self.assertEqual(statuses(good(), "LS-POND-EDGE-SLOPE") | statuses(good(), "LS-POND-EDGE-LIGHT"), {"pass"})
        L = good(); del L["features"][3]["edge_lux"]
        self.assertIn("not_evaluated", statuses(L, "LS-POND-EDGE-LIGHT"))

    def test_pond_depth_stock_shade(self):
        self.case("LS-POND-DEPTH", lambda L: L["features"][3].update(depth_mm=500))
        self.case("LS-POND-STOCK", lambda L: L["features"][3].update(koi_count=20, koi_adult_length_cm=60))   # 472 in / 6 m2
        L = good(); L["features"][3].update(koi_count=20, koi_adult_length_cm=60, aerated=True)            # 78.7 in/m2 > 43.1
        self.assertIn("warn", statuses(L, "LS-POND-STOCK"))
        L = good(); L["features"][3].update(koi_count=12, koi_adult_length_cm=40, aerated=True)           # 189 in / 6 = 31.5 <= 43.1
        self.assertEqual(statuses(L, "LS-POND-STOCK"), {"pass"})
        L = good(); L["features"][3].update(koi_count=12, koi_adult_length_cm=40, aerated=False)          # 31.5 > 28.7
        self.assertIn("warn", statuses(L, "LS-POND-STOCK"))
        self.case("LS-POND-SHADE", lambda L: L["features"][3].update(surface_shade_pct=20))
        self.case("LS-POND-SHADE", lambda L: L["features"][3].update(surface_shade_pct=90))
        self.assertEqual(statuses(good(), "LS-POND-DEPTH") | statuses(good(), "LS-POND-STOCK") | statuses(good(), "LS-POND-SHADE"), {"pass"})

    def test_lounge_and_standing_area(self):
        self.case("LS-LOUNGE-AREA", lambda L: L["seating"][0].update(seats=25))                 # 36 / 25 = 1.44
        self.case("LS-LOUNGE-CLUSTER", lambda L: L["zones"][1].update(rect=[8, 0, 11, 6]))      # 3 m wide
        self.case("LS-STAND-AREA", lambda L: L["zones"][2].update(design_people=40))            # 36 / 40
        self.assertEqual(statuses(good(), "LS-LOUNGE-AREA") | statuses(good(), "LS-LOUNGE-CLUSTER") | statuses(good(), "LS-STAND-AREA"), {"pass"})
        L = good(); L["zones"] = [z for z in L["zones"] if z["use"] != "standing"]
        self.assertEqual(statuses(L, "LS-STAND-AREA"), {"not_evaluated"})                       # no standing zone is visible, not silent

    def test_tree_distance_to_building(self):
        self.case("LS-TREE-BUILDING", lambda L: L["trees"][0].update(mature_height_m=20, water_demand="high"))   # 25 m > 12 m
        L = good(); L["trees"][0].update(mature_height_m=10); del L["trees"][0]["water_demand"]                  # unknown: assume high, 12.5 m
        r = res(L, "LS-TREE-BUILDING")[0]
        self.assertEqual((r.status, r.required), ("warn", 12.5))
        self.assertIn("assume high", r.message)
        L = good(); del L["trees"][0]["mature_height_m"]
        self.assertEqual(statuses(L, "LS-TREE-BUILDING"), {"not_evaluated"})
        self.assertEqual(statuses(good(), "LS-TREE-BUILDING"), {"pass"})

    def test_hedge_spacing_and_herb_sun(self):
        self.case("LS-HEDGE-SPACING", lambda L: L["boundary"][1].update(row_spacing_mm=900))
        self.case("LS-HEDGE-SPACING", lambda L: L["boundary"][1].update(row_spacing_mm=150))
        self.assertEqual(statuses(good(), "LS-HEDGE-SPACING"), {"pass"})
        self.case("LS-HERB-SUN", lambda L: L["features"][2].update(midsummer_sun_hours=3))
        L = good(); del L["features"][2]["midsummer_sun_hours"]
        self.assertEqual(statuses(L, "LS-HERB-SUN"), {"not_evaluated"})
        self.assertEqual(statuses(good(), "LS-HERB-SUN"), {"pass"})

    def test_pond_freeboard(self):
        self.case("LS-POND-FREEBOARD", lambda L: L["features"][3].update(freeboard_mm=100))
        self.case("LS-POND-FREEBOARD", lambda L: L["features"][3].update(edge="hard", freeboard_mm=50))
        self.assertEqual(statuses(good(), "LS-POND-FREEBOARD"), {"pass"})
        L = good(); L["features"][3]["edge"] = "hard"; L["features"][3]["freeboard_mm"] = 75
        self.assertEqual(statuses(L, "LS-POND-FREEBOARD"), {"pass"})

    def test_pond_flush_margin(self):
        self.case("LS-POND-FLUSH-MARGIN", lambda L: L["features"][3].update(margin_slope_back_mm=300), status="warn")
        L = good(); L["features"][3]["flush"] = False
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
        self.case("LS-SLOPE", lambda L: L["zones"][3].update(slope_pct=9))
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
