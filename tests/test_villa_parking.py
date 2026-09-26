"""Round 7 parking options (revised after the client review): a ramp up to a GF-level deck in the east yard, rooms
underneath, the study opening onto the deck, the U-stair along the party wall."""
import unittest

from archpipe.concept import revit_spec as RS
from archpipe.concept import stairs as S
from archpipe.concept import villa as V
from archpipe.concept import villa_parking as P


class ParkingGeometry(unittest.TestCase):
    def test_ramp_profile(self):
        # gate +0.00, 1.0 m at 10 %, 20 % main slope, 1.0 m at 10 %, GF level +1.20 at the ramp top
        (x0, z0), (x1, z1), (x2, z2), (x3, z3) = P.ramp_profile()
        self.assertEqual((x0, z0), (V.FENCE_N, 0.0))
        self.assertAlmostEqual((z1 - z0) / (x1 - x0), 0.10, places=6)
        self.assertAlmostEqual((z2 - z1) / (x2 - x1), 0.20, places=6)
        self.assertAlmostEqual((z3 - z2) / (x3 - x2), 0.10, places=6)
        self.assertAlmostEqual(z3, P.DECK_TOP, places=6)
        self.assertAlmostEqual(P.DECK_TOP, V.LEVELS["GF"], places=6)          # level with the GF

    def test_clear_height_under_the_ramp_and_deck(self):
        # gate: 0.00 - 0.35 build-up over the -1.80 floor = 1.45 m; deck: 1.20 - 0.35 + 1.80 = 2.65 m
        self.assertAlmostEqual(P.clear_at(P.RAMP_X0), 1.45, places=3)
        self.assertAlmostEqual(P.clear_at(P.RAMP_X1), 2.65, places=3)
        self.assertGreaterEqual(P.clear_at(P.X_LOW), 2.0)
        self.assertLess(P.clear_at(P.X_LOW - 0.002), 2.0)

    def test_the_ramp_reaches_the_gf_before_the_study_door(self):
        self.assertLessEqual(P.RAMP_X1, P.STUDY_DOOR[0])


class ParkingOptions(unittest.TestCase):
    def setUp(self):
        self.opts = P.options()

    def test_four_options_pass_the_critic(self):
        self.assertEqual([o["id"] for o in self.opts], ["P3", "P4"])   # P1/P2 and P5 dropped (client r9)
        for lay in self.opts:
            self.assertEqual(V.critique(lay)["fails"], [], lay["id"])

    def test_under_rooms_reach_the_fence_without_gaps(self):
        for lay in self.opts:
            under = sorted((r for r in lay["rooms"].values() if r.get("ext")), key=lambda r: r["rect"][0])
            self.assertAlmostEqual(under[0]["rect"][0], V.FENCE_N, places=3)
            for a, b in zip(under, under[1:]):
                self.assertAlmostEqual(a["rect"][2], b["rect"][0], places=3, msg=lay["id"])
            self.assertAlmostEqual(under[-1]["rect"][2], max(lay["parking2"]["deck"][2], P.EXT_MIN_END), places=3)
            for r in under:
                self.assertAlmostEqual(r["rect"][3], V.FENCE_E, places=3)

    def test_rooms_under_the_ramp_have_their_working_height(self):
        need = {"utility": 2.0, "wc": 2.3, "store": 0.0, "media": 2.0}
        for lay in self.opts:
            for r in lay["rooms"].values():
                if r.get("ext"):
                    self.assertGreaterEqual(P.clear_at(r["rect"][0]) + 1e-6, need[r["occupancy"]], r["name"])

    def test_dirty_kitchen_opens_off_the_kitchen(self):
        for lay in self.opts:
            self.assertIn(("kitchen", "dirty-kitchen"), [tuple(l) for l in lay["links"]])

    def test_parking_elevation_rows_have_no_failure(self):
        for lay in self.opts:
            rows = V.elevation_checks(lay)
            self.assertFalse([e for e in rows if e["status"] == "fail"], lay["id"])

    def test_the_gradient_over_the_mh_limit_is_a_recorded_waiver(self):
        rows = {e["item"]: e for e in V.elevation_checks(P.option("u", 1))}
        mh = rows["parking ramp: main gradient vs garage-ramp limit"]
        self.assertEqual(mh["status"], "waived")
        self.assertIn("client 2026-09-26", mh["note"])
        self.assertEqual(rows["parking ramp: main gradient vs private basement-garage maximum"]["status"], "pass")

    def test_spec_has_ramp_deck_cars_rails_and_high_sills(self):
        for lay in self.opts:
            sp = RS.build(lay)
            pk = sp["parking2"]
            self.assertEqual(len(pk["cars"]), lay["parking2"]["cars"])
            self.assertAlmostEqual(pk["deck"]["z_top"], -1.2 + P.DECK_TOP, places=3)
            self.assertEqual(len(pk["ramp"]["profile"]), 4)
            for car in pk["cars"]:
                self.assertLessEqual(car[2], pk["deck"]["x1"] + 1e-6)
            over = [w for w in sp["windows"] if w["level"] == "GF" and abs(w["y"] - V.YE) < 1e-6
                    and P.RAMP_X0 <= w["x"] <= pk["deck"]["x1"]]
            self.assertTrue(over)
            self.assertTrue(all(w["sill"] >= 1.6 + 0.1 - 1e-9 for w in over))        # eye 1.6 above the deck
            beyond = lay["parking2"]["roof_beyond_deck"]
            self.assertEqual(sp["roofs"], [beyond] if beyond else [])
            self.assertEqual(len(sp["rails"]), 3)

    def test_study_opens_onto_the_deck_between_the_columns(self):
        for lay in self.opts:
            sp = RS.build(lay)
            d = [d for d in sp["doors"] if d.get("sliding")]
            self.assertEqual(len(d), 1)
            d = d[0]
            self.assertEqual((d["level"], d["rooms"][0], d["width"]), ("GF", "study-game", 1.8))
            self.assertGreaterEqual(d["x"] - d["width"] / 2, 7.377 - 1e-6)
            self.assertLessEqual(d["x"] + d["width"] / 2, 9.227 + 1e-6)
            study = lay["rooms"]["study-game"]["rect"]
            self.assertLessEqual(study[0], d["x"] - d["width"] / 2)
            self.assertGreaterEqual(study[2], d["x"] + d["width"] / 2)


class LengthwiseU(unittest.TestCase):
    """Client review r7: the U across the bar left a 1.30 m passage and blocked the open plan."""

    def test_no_clash_and_the_passage_beside_it(self):
        st = S.u_lengthwise_party()
        self.assertEqual(S.clashes(st)["hits"], [])
        beside = V.YE - st["landing"][3] / 1000
        self.assertGreater(beside, 2.9)                                   # was 1.30 with the U across the bar

    def test_u_options_use_it_and_reach_the_pantry_under_the_upper_flight(self):
        for lay in (P.option("u", 1), P.option("u", 2)):
            self.assertEqual(lay["stair"], "u-length")
            self.assertIn(("pass-stair", "pantry"), [tuple(l) for l in lay["links"]])
            st = S.u_lengthwise_party()
            x_pass = lay["rooms"]["pass-stair"]["rect"][0] * 1000
            under = [p["box"][2] for p in st["parts"] if "flight 2 tread" in p["what"] and p["box"][3] > x_pass]
            self.assertGreaterEqual(min(under) - 150 - S.B_FFL, 2000)      # 150 waist ASSUMED


class RevitStairCompare(unittest.TestCase):
    """Round 8: the Python clash check passed the lengthwise U while Revit found its landing touching column 1590377
    (Revit holds the column face at x 3977.2, CAD at 3977; the 1 mm tolerance hid it). Every stair an option uses
    must be in the Revit comparison, and the comparison must agree."""

    def test_option_stairs_are_revit_compared(self):
        for lay in P.options():
            self.assertIn(lay["stair"], V.REVIT_STAIR_COMPARED, lay["id"])

    def test_revit_readback_agrees_where_held(self):
        import json
        from pathlib import Path
        rb = Path(__file__).resolve().parents[1] / "out" / "villa" / "stairs-readback.json"
        if not rb.exists():
            self.skipTest("no Revit stair read-back on this machine (run scripts/villa_stairs.py + Revit)")
        data = json.loads(rb.read_text(encoding="utf-8"))
        for key in ("u-length", "party-r8"):
            st = V.stair_model(key)
            rv = [o for o in data["options"] if o["name"] == st["name"]]
            self.assertTrue(rv, st["name"])
            rv_cols = {r["id"] for r in rv[0]["intersections"] if r["kind"] == "column"}
            py_cols = {h["structure"] for h in S.clashes(st)["hits"] if h["kind"] == "column"}
            self.assertEqual((rv_cols, py_cols), (set(), set()), st["name"])


class Openings(unittest.TestCase):
    def test_no_opening_overlaps_a_kept_column(self):
        for lay in P.options():
            self.assertEqual(RS.opening_problems(RS.build(lay)), [], lay["id"])

    def test_a_window_on_a_column_is_caught(self):
        sp = RS.build(P.option("u", 1))
        w = [w for w in sp["windows"] if abs(w["y"] - V.YE) < 1e-6][0]
        w["x"] = 11.367                                                   # centre of the column at x 11.197-11.537
        self.assertTrue(RS.opening_problems(sp))


class WindowCredit(unittest.TestCase):
    """Round 8: the column pass dropped the P1 kitchen window while the critic still credited the kitchen as lit."""

    def test_every_credited_room_has_a_built_window(self):
        for lay in P.options():
            sp = RS.build(lay)
            self.assertEqual(RS.window_credit_problems(lay, sp["windows"], sp["doors"]), [], lay["id"])

    def test_the_real_false_credit_is_caught(self):
        lay = P.option("u", 1)
        sp = RS.build(lay)                                   # the kitchen's face is split by a column: no window
        orig = V._minus_columns
        try:
            V._minus_columns = lambda faces, margin=0.1: faces   # the critic as it was: columns ignored
            probs = RS.window_credit_problems(lay, sp["windows"], sp["doors"])
        finally:
            V._minus_columns = orig
        self.assertTrue(any(p.startswith("kitchen") for p in probs), probs)


class FullHeightGlazing(unittest.TestCase):
    """Client r8 review: the basement's street face has a floor-to-beam window today, and the end of the east-yard
    extension must have one in every option (P1 had a 0.8 m utility window there, P2/P4 none: a store was at the
    end; P3/P4's street door was capped at 2.4 m on a 3.2 m run)."""

    def test_every_option_glazes_both_faces_floor_to_beam(self):
        for lay in P.options():
            sp = RS.build(lay)
            self.assertEqual(RS.glazing_problems(lay, sp["windows"], sp["doors"]), [], lay["id"])
            end = [w for w in sp["windows"] if w.get("full_height") and w["room"] == "dirty-kitchen"]
            self.assertEqual(len(end), 1, lay["id"])
            # the extension is 2.99 m deep (fence offset): 2.99 - 2 x 0.20 reveal
            self.assertAlmostEqual(end[0]["width"], 2.59, places=2)
            self.assertEqual((end[0]["sill"], end[0]["height"]), (0.0, RS.HEAD))

    def test_the_dirty_kitchen_is_the_last_room_of_the_extension(self):
        for lay in P.options():
            ext = [r for r in lay["rooms"].values() if r.get("ext")]
            last = max(ext, key=lambda r: r["rect"][2])
            self.assertEqual(last["id"], "dirty-kitchen", lay["id"])

    def test_the_round7_builds_are_caught(self):
        # what Revit actually built in round 7/8 (out/villa/options-r7/readback.json)
        built = {"P1": ([{"level": "B", "room": "dirty-kitchen", "x": 14.5, "y": -22.096, "width": 0.8, "sill": 1.5}],
                        [{"level": "B", "x": 3.617, "y": -25.411, "width": 1.92, "height": 2.2, "garden": True,
                          "rooms": ["lounge", "yard"]}]),
                 "P2": ([], [{"level": "B", "x": 3.617, "y": -25.411, "width": 1.92, "height": 2.2, "garden": True,
                              "rooms": ["lounge", "yard"]}]),
                 "P3": ([{"level": "B", "room": "dirty-kitchen", "x": 14.5, "y": -22.096, "width": 0.8, "sill": 1.5}],
                        [{"level": "B", "x": 3.617, "y": -25.861, "width": 2.4, "height": 2.2, "garden": True,
                          "rooms": ["lounge", "yard"]}])}
        lays = {l["id"]: l for l in [P.option("u", 1), P.option("u", 2), P.option("straight", 1)]}   # round-7 builds
        for oid, (wins, doors) in built.items():
            probs = RS.glazing_problems(lays[oid], wins, doors)
            self.assertTrue(any("end face" in p for p in probs), (oid, probs))
        self.assertTrue(any("street face" in p for p in RS.glazing_problems(lays["P3"], *built["P3"])))
        # and it stays quiet on the P1 street door, which already fills its run (1.92 = 2.32 - 2 x 0.20)
        self.assertFalse(any("street face" in p for p in RS.glazing_problems(lays["P1"], *built["P1"])))


class StairHeadroomAndRoute(unittest.TestCase):
    """Client r9: the stair must reach GF level to best practice and leave room to pass under the slab. The headroom
    envelope was drawn from the tread tops, and the GF slab soffit taken 100 mm too high; together they passed a
    flight with 1.82 m under the slab edge. And the turn from the stair top round the void into the bedroom corridor
    was 0.69 m wide (0.59 with a balustrade), which no check measured."""

    def test_soffit_matches_the_slab_and_build_up(self):
        self.assertAlmostEqual(S.SLAB_SOFFIT, S.GF_FFL - (V.FLOOR_BUILDUP + V.SLAB) * 1000, places=6)

    def test_the_flight_climbs_the_full_storey_to_the_cards(self):
        st = S.party_flight_r8()
        self.assertAlmostEqual(st["rise"] * st["risers"], S.GF_FFL - S.B_FFL, places=6)       # 3.00 m exactly

    def test_pitch_line_headroom_passes_with_the_spec_opening(self):
        st = S.party_flight_r8()
        op = [v * 1000 for v in RS.build(P.options()[0])["gf_opening"]]
        self.assertGreaterEqual(S.pitch_headroom(st, op)[0], S.HEAD)

    def test_the_round8_opening_is_caught(self):
        # what round 8 built: the opening to x 8.537 (from the tread-top envelope)
        hr, x = S.pitch_headroom(S.party_flight_r8(), [5177, -28421, 8537, -27471])
        self.assertLess(hr, S.HEAD)
        self.assertAlmostEqual(hr, 1824, delta=5)

    def test_route_round_the_void_is_a_full_hall(self):
        for lay in P.options():
            self.assertGreaterEqual(V.gf_route_width(lay), 0.9, lay["id"])

    def test_the_round8_pinch_is_caught(self):
        import copy
        lay = copy.deepcopy(P.options()[0])
        r = lay["rooms"]
        r["kids-a"]["rect"][0] = r["study-game"]["rect"][2] = 9.227          # the round-8 GF
        r["gallery-end"]["rect"] = [8.657, -27.371, 9.227, -26.371]
        r["stair-gf"]["rect"][2] = r["corridor"]["rect"][0] = 8.657
        r["study-game"].pop("open")
        orig = RS.build
        try:
            RS.build = lambda l: dict(orig(l), gf_opening=[5.177, -28.421, 8.537, -27.471])
            self.assertLess(V.gf_route_width(lay), 0.9)
        finally:
            RS.build = orig

    def test_the_study_is_open_to_the_stair(self):
        for lay in P.options():
            sp = RS.build(lay)
            self.assertFalse([d for d in sp["doors"] if set(d.get("rooms") or []) & {"study-game"}
                              and set(d["rooms"]) & {"stair-gf", "gallery-end"}], lay["id"])
            seg = [s for s in RS.segments(lay, "GF") if set(s["rooms"]) == {"study-game", "stair-gf"}]
            self.assertTrue(seg and all(RS._kind(lay, s) == "sep" for s in seg), lay["id"])

    def test_the_cinema_sits_under_the_ramp_with_its_ceiling_and_a_door(self):
        for lay in P.options():
            c = lay["rooms"]["cinema"]
            self.assertTrue(c.get("ext"))
            self.assertEqual(c["occupancy"], "media")
            row = [e for e in V.elevation_checks(lay) if e["item"].startswith(c["name"])][0]
            self.assertEqual(row["status"], "pass", row)
            self.assertGreaterEqual(row["achieved"], 75)
            doors = [d for d in RS.build(lay)["doors"] if "cinema" in (d.get("rooms") or [])]
            self.assertTrue(doors, lay["id"])

    def test_the_ceiling_row_fails_a_room_too_far_down_the_ramp(self):
        import copy
        lay = copy.deepcopy(P.options()[0])
        lay["rooms"]["cinema"]["rect"][0] = V.FENCE_N                  # from the gate: 1.45 m at its low end
        row = [e for e in V.elevation_checks(lay) if e["item"].startswith(lay["rooms"]["cinema"]["name"])][0]
        self.assertEqual(row["status"], "fail")

    def test_the_bath_beside_the_stair_frees_the_kids_rooms(self):
        north, east = P.option("straight", 1), P.option("straight", 1, bath_north=False)
        sn, se = V.critique(north)["sizes"], V.critique(east)["sizes"]
        self.assertGreater(sn["kids-a"]["net_m2"], se["kids-a"]["net_m2"])
        self.assertGreaterEqual(sn["family-bath"]["net_w"], 2.15 - 1e-6)           # card mh-bathroom-m42-4.30
        self.assertIn(("gallery-end", "family-bath"), [tuple(l) for l in north["links"]])

    def test_the_lounge_is_glazed_across_the_whole_street_run(self):
        for lay in P.options():
            sp = RS.build(lay)
            d = [d for d in sp["doors"] if d.get("full_height") and d["rooms"][0] == "lounge"]
            self.assertEqual(len(d), 1)
            self.assertAlmostEqual(d[0]["width"], 3.81 - 2 * RS.REVEAL, places=2)   # column to column, less reveals


class DaylightVariants(unittest.TestCase):
    def test_the_slot_has_one_grating_face_per_span_and_the_car_only_when_asked(self):
        from archpipe.concept import villa_daylight as VD
        lays = VD.variant_layouts()
        base = VD.scene(*lays["P3-slot"])
        car = VD.scene(*lays["P3-slot-car"])
        g = [f for f in base.faces if f.material == "grating"]
        self.assertTrue(g)
        spans = {(round(min(p[0] for p in f.points), 3), round(max(p[0] for p in f.points), 3)) for f in g}
        self.assertEqual(len(spans), len(g))                  # no two coincident panes (T would be squared)
        self.assertFalse([f for f in base.faces if f.material == "car"])
        self.assertTrue([f for f in car.faces if f.material == "car"])
        # the bar's east face is glazed onto the slot; the rooms under the deck start beyond it
        self.assertTrue(all(r["polygon"][0][1] >= V.YE + 0.9 for r in base.rooms
                            if r["id"] in ("guest-wc", "store-mid", "dirty-kitchen")))

    def test_the_open_variant_gives_the_kitchen_its_east_window(self):
        sp = RS.build(P.option("u", 1, open_beyond=True))
        self.assertTrue([w for w in sp["windows"] if w["room"] == "kitchen" and abs(w["y"] - V.YE) < 1e-6])
        self.assertFalse([w for w in RS.build(P.option("u", 1))["windows"] if w["room"] == "kitchen"])


class YardWall(unittest.TestCase):
    """The kept NE yard wall (client 2026-09-26): NE column to the street fence, 1.40 m from the basement floor."""

    def test_wall_runs_from_the_street_fence_to_the_ne_column(self):
        from archpipe import villa_env as E
        x0, y0, x1, y1 = E.YARD_WALL
        self.assertEqual(x1, E.BAR[0])
        self.assertEqual(x0, E.BAR[0] - E.OFFSET_N)
        self.assertEqual(y1, E.BAR[3])                           # east face flush with the villa's (client)
        self.assertEqual(y1 - y0, 250)

    def test_ramp_clears_the_wall_and_the_gate_fits_a_car(self):
        rows = {e["item"].split(" (")[0].split(":")[0]: e for e in V.elevation_checks(P.option("u", 1))}
        self.assertEqual(rows["NE yard wall top"]["status"], "pass")
        self.assertEqual(rows["car gate"]["status"], "pass")

    def test_a_higher_wall_would_hit_the_ramp(self):
        from archpipe import villa_env as E
        old = E.YARD_WALL_H
        try:
            E.YARD_WALL_H = 1500                                   # top at -0.30: above the -0.35 soffit at the gate
            rows = [e for e in V.elevation_checks(P.option("u", 1)) if e["item"].startswith("NE yard wall")]
            self.assertEqual(rows[0]["status"], "fail")
        finally:
            E.YARD_WALL_H = old

    def test_store_side_on_the_wall_is_not_a_window(self):
        lay = P.option("u", 1)
        faces = V.window_faces("B", lay["extension"])
        self.assertFalse([f for f in faces if f[0] == "h" and abs(f[1] - V.YE) < 1e-6 and f[2] < V.X0])

    def test_store_uses_the_kept_wall_with_an_infill_to_the_ramp(self):
        from archpipe import villa_env as E
        sp = RS.build(P.option("u", 1))
        wx0, wx1 = E.YARD_WALL[0] / 1000, E.YARD_WALL[2] / 1000
        on_wall = [w for w in sp["walls"] if w["level"] == "B" and abs(w["y0"] - w["y1"]) < 1e-6
                   and abs(w["y0"] - V.YE) < 0.2 and max(w["x0"], w["x1"]) <= wx1 + 1e-6]
        self.assertEqual(on_wall, [])
        prof = {tuple(p) for p in sp["infill"]["profile"]}
        top = -3.0 + E.YARD_WALL_H / 1000
        self.assertIn((wx0, top), prof)                                      # starts on the wall top
        self.assertIn((wx0, round(-3.0 + P.clear_at(wx0), 3)), prof)       # 50 mm at the gate
        self.assertIn((wx1, round(-3.0 + P.clear_at(wx1), 3)), prof)       # up to the soffit at the villa
        self.assertAlmostEqual(P.clear_at(wx0) - E.YARD_WALL_H / 1000, 0.05, places=3)

    def test_non_parking_spec_has_no_infill(self):
        from archpipe.concept import villa_options as VO
        self.assertNotIn("infill", RS.build(VO.s1()))


class UnderRampFit(unittest.TestCase):
    """Client review r7: walls came through the ramp and a 2.1 m door opened under a 1.9 m soffit."""

    def test_every_option_fits_under_the_soffit(self):
        for lay in P.options():
            sp = RS.build(lay)
            self.assertEqual(RS.clearance_problems(lay, sp["walls"], sp["doors"], sp["infills"]), [], lay["id"])

    def test_a_full_height_cross_wall_is_caught(self):
        lay = P.option("u", 2)
        sp = RS.build(lay)
        cross = [w for w in sp["walls"] if w["level"] == "B" and abs(w["y0"] - w["y1"]) > 1e-6
                 and w["y1"] > V.YE + 0.3 and w["x0"] < P.RAMP_X1]
        self.assertTrue(cross)
        cross[0]["height"] = RS.WALL_H                                   # the as-built defect
        self.assertTrue(RS.clearance_problems(lay, sp["walls"], sp["doors"], sp["infills"]))

    def test_a_flat_fence_wall_without_infill_is_caught(self):
        lay = P.option("u", 2)
        sp = RS.build(lay)
        self.assertTrue(any("open under the soffit" in p
                            for p in RS.clearance_problems(lay, sp["walls"], sp["doors"], [])))

    def test_a_room_door_under_the_low_ramp_is_caught(self):
        lay = P.option("u", 1)
        sp = RS.build(lay)
        d = [d for d in sp["doors"] if d.get("rooms") == ["laundry", "store-ramp"]][0]
        d["height"] = 2.10                                               # a room door where only a cupboard fits
        self.assertTrue(any(p.startswith("door") for p in
                            RS.clearance_problems(lay, sp["walls"], sp["doors"], sp["infills"])))

    def test_door_fit_kinds(self):
        self.assertEqual(P.door_fit(0.0, 2.5, 0.8, "store")[3], "low")          # clear 1.70 at the low jamb
        self.assertEqual(P.door_fit(0.0, 2.5, 0.8, "utility")[3], "none")
        self.assertEqual(P.door_fit(2.9, 4.6, 0.8, "utility")[3], "reduced")    # clear 2.11: a 2.01 leaf
        self.assertEqual(P.door_fit(9.3, 11.2, 0.8, "wc")[3], "full")


class Negative(unittest.TestCase):
    def test_a_closed_windowless_room_still_fails_window(self):
        lay = P.option("u", 1)
        lay["rooms"]["laundry"]["occupancy"] = "bedroom"          # habitable, closed door, no window to the fence
        self.assertIn("window", V.critique(lay)["fails"])

    def test_a_ramp_steeper_than_the_private_maximum_fails(self):
        lay = P.option("u", 1)
        lay["parking2"] = dict(lay["parking2"], gradient=0.25)
        rows = [e for e in V.elevation_checks(lay) if "private basement-garage maximum" in e["item"]]
        self.assertEqual(rows[0]["status"], "fail")

    def test_non_parking_layout_keeps_block_roofs(self):
        from archpipe.concept import villa_options as VO
        sp = RS.build(VO.s5())
        self.assertNotIn("parking2", sp)
        self.assertTrue(sp["roofs"])


if __name__ == "__main__":
    unittest.main()
