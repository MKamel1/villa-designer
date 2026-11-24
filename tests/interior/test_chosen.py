"""The client's chosen finish schedule (2026-11-23): complete, source-quoted, price-free, and what the scene really draws."""
import copy
import unittest
from pathlib import Path

from archpipe.interior import chosen as CH, finishes as F

LIB = Path.home() / "archpipe/assets/library"
PALS = {p: F.load_palette(p) for p in "BC"}


def design_rooms():
    from archpipe.concept import villa_render as V
    return V.R.design("D1")["rooms"]


class Schedule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ch = CH.load()
        cls.rooms = design_rooms()

    def test_no_problems(self):
        self.assertEqual(CH.problems(self.ch, self.rooms, PALS), [])

    def test_the_client_mix(self):
        s = self.ch["slots"]
        want = {"worktop": "B-worktop", "backsplash": "B-backsplash", "kitchen-front": "B-kitchen-front",
                "kitchen-joinery": "B-joinery-light", "floor-basement": "C-floor-living", "floor-gf": "C-floor-gf",
                "door": "C-door", "floor-wet": "C-floor-wet", "wall-tile-wet": "C-bath-tile",
                "wall-paint-main": "B-wall-paint", "wall-feature-parents": "C-wall-paint"}
        self.assertEqual({k: s[k]["item_id"] for k in want}, want)
        self.assertIn("Gris Fleury", s["floor-basement"]["item"]["product"]["name"])
        self.assertEqual(s["wall-paint-main"]["item"]["product"]["colour_name"], "Off White")
        self.assertEqual(s["wall-feature-parents"]["item"]["product"]["colour_name"], "Nile Clay")
        # Nile Clay is the feature wall behind the bed only
        self.assertEqual(s["wall-feature-parents"]["applies_to"]["rooms"], ["parents-bed"])
        self.assertEqual([r for r, c in self.ch["rooms"].items() if c.get("feature_wall")], ["parents-bed"])

    def test_every_room_has_floor_and_wall_and_wet_rooms_are_wet(self):
        self.assertEqual(set(self.ch["rooms"]), set(self.rooms))
        for rid, r in self.rooms.items():
            c = self.ch["rooms"][rid]
            if c.get("retained"):
                self.assertTrue(c["retained"]["reason"], rid)
                continue
            self.assertIn(c["floor"], self.ch["slots"]); self.assertIn(c["wall"], self.ch["slots"])
            if r["occupancy"] in ("bathroom", "ensuite", "wc"):
                self.assertEqual((c["floor"], c["wall"]), ("floor-wet", "wall-tile-wet"), rid)

    def test_no_slot_is_unassigned_and_no_geometry_is_reported_not_hidden(self):
        for sid, s in self.ch["slots"].items():
            self.assertTrue(s["applies_to"]["rooms"] or s.get("no_geometry"), sid)
        self.assertIn("no backsplash zone", self.ch["slots"]["backsplash"]["no_geometry"])

    def test_cushion_schedule_has_a_slot_per_scheduled_cushion_and_throw(self):
        ids = [i["id"] for i in PALS["C"]["items"] if i["slot"].startswith(("cushion", "throw")) and i["group"] == "soft"]
        self.assertEqual(sorted("C-" + sid for sid in self.ch["slots"] if sid.startswith(("cushion", "throw"))), sorted(ids))

    def test_lookalikes_are_labelled_and_scale_is_the_product_format(self):
        for sid, s in self.ch["slots"].items():
            la = s["item"].get("lookalike")
            if la and s.get("render"):
                self.assertEqual(la["label"], F.LOOKALIKE_LABEL, sid)
                self.assertAlmostEqual(s["render"]["tile_m"], round(F.texture_scale_m(s["item"])[0], 4))
        self.assertEqual(self.ch["slots"]["floor-basement"]["render"]["tile_m"], 1.2)   # 600 x 1200 tile: long side

    @unittest.skipUnless(LIB.is_dir(), "render library not on this host")
    def test_generated_file_is_current(self):
        import importlib.util, sys
        spec = importlib.util.spec_from_file_location("build_chosen", Path(__file__).resolve().parents[2] / "scripts/build_chosen.py")
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        self.assertEqual(m.build(LIB), self.ch)


class NegativeControls(unittest.TestCase):
    """Stays quiet on the real file (above) and speaks on each defect."""

    def setUp(self):
        self.ch = copy.deepcopy(CH.load()); self.rooms = design_rooms()

    def probs(self):
        return CH.problems(self.ch, self.rooms, PALS)

    def test_unassigned_room(self):
        del self.ch["rooms"]["kitchen"]
        self.assertTrue(any("room kitchen: no finish" in p for p in self.probs()))

    def test_wet_room_with_dry_finish(self):
        self.ch["rooms"]["family-bath"].update(floor="floor-gf")
        self.assertTrue(any("wet room" in p for p in self.probs()))

    def test_room_not_in_model(self):
        self.ch["rooms"]["ghost"] = dict(zone="x", floor="floor-gf", wall="wall-paint-main")
        self.assertTrue(any("not in the design model" in p for p in self.probs()))

    def test_slot_assigned_to_nothing(self):
        self.ch["slots"]["backsplash"].pop("no_geometry")
        self.assertTrue(any("backsplash" in p and "no room" in p for p in self.probs()))

    def test_price_key_is_refused(self):
        self.ch["slots"]["worktop"]["item"]["product"]["extra"] = {"price_egp": 1}
        self.assertTrue(any("price-like" in p for p in self.probs()))

    def test_edited_item_differs_from_palette(self):
        self.ch["slots"]["door"]["item"]["product"]["maker"] = "Someone else"
        self.assertTrue(any("differs from palette" in p for p in self.probs()))

    def test_unlabelled_lookalike(self):
        self.ch["slots"]["door"]["item"]["lookalike"]["label"] = "exact"
        self.assertTrue(any("not labelled" in p for p in self.probs()))


class SceneUsesTheSchedule(unittest.TestCase):
    def test_scene_materials_and_room_finishes(self):
        from archpipe.concept import villa_render as V
        ch = CH.load()
        for name, spec in CH.materials(ch).items():
            self.assertEqual(V.M[name], spec, name)
        for rid, (fl, wl) in CH.room_finish(ch).items():
            self.assertEqual(V.FINISH[rid][:2], (fl, wl), rid)
        self.assertEqual(V.FINISH["cinema"][1], "taupe-fabric")      # the retained design finish


if __name__ == "__main__":
    unittest.main()


class MakerColour(unittest.TestCase):
    """Colours come from the maker's own image (guard for the Frappuccino defect, 2026-11-23)."""

    @classmethod
    def setUpClass(cls):
        cls.ch = CH.load()

    def test_every_chosen_product_has_a_sourced_colour(self):
        bad = [p for sid, s in self.ch["slots"].items() for p in CH.colour_problems(sid, s)]
        self.assertEqual(bad, [])
        self.assertEqual(set(CH.UNSOURCED), {"C-door"})        # the one documented gap; never grows silently

    def test_name_based_estimate_fails(self):
        s = copy.deepcopy(self.ch["slots"]["worktop"])
        s["colour_source"] = dict(hex="#b8a58e", basis="estimate from the maker's colour name (not a maker-published value)", url="x")
        self.assertEqual(len(CH.colour_problems("worktop", s)), 1)
        del s["colour_source"]
        self.assertEqual(len(CH.colour_problems("worktop", s)), 1)

    @unittest.skipUnless((LIB / "materials").exists(), "needs library")
    def test_lookalike_pattern_is_the_makers_kind(self):
        """Pattern contrast (luma spread) of the look-alike within 4x of the maker swatch; Marble015 (cream, cv 0.02) for the
        dark veined Frappuccino (cv 0.78) was 39x off and rendered as a flat panel."""
        from archpipe.interior import palette_scene as PS
        cols = PS.load_colours()
        for sid, s in self.ch["slots"].items():
            la, c = s["item"].get("lookalike"), cols.get(s["item_id"], {})
            if la and c.get("mode") == "swatch":
                r = c["luma_cv"] / PS.lookalike_luma_cv(LIB / "materials" / la["id"])
                self.assertTrue(0.25 <= r <= 4, f"{sid}: {la['id']} pattern contrast {r:.1f}x the maker's")
        r = cols["C-bath-tile"]["luma_cv"] / PS.lookalike_luma_cv(LIB / "materials" / "Marble015")
        self.assertGreater(r, 4)                                # the real defect fails the same check
