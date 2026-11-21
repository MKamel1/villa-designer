"""The design model's spec-derived elements against their source data (fast: ~1 s, no scene build)."""
import math
import unittest
from collections import Counter

from archpipe.concept import revit_spec as RS
from archpipe.concept import villa_r11 as R
from archpipe.contracts import DesignElement
from archpipe.model import schema, spec_source as S


class SpecDerived(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lay = R.design("D1")
        cls.sp = RS.build(cls.lay)
        cls.els = S.all_from_spec(cls.lay, cls.sp)
        cls.by = {e.id: e for e in cls.els}
        cls.kinds = Counter(e.kind for e in cls.els)

    def test_well_formed(self):
        self.assertEqual(schema.validate(self.els), [])
        self.assertTrue(all(isinstance(e, DesignElement) for e in self.els))

    def test_counts_equal_source_counts(self):
        self.assertEqual(self.kinds["room"], len(self.lay["rooms"]))
        self.assertEqual(self.kinds["wall"], len(self.sp["walls"]))
        self.assertEqual(self.kinds["door"], len(self.sp["doors"]))
        self.assertEqual(self.kinds["window"], len(self.sp["windows"]))
        self.assertEqual(self.kinds["stair"], 1)
        self.assertEqual(self.kinds["column"], 9)
        self.assertEqual(self.kinds["beam"], 24)

    def test_rooms_on_both_levels(self):
        levels = Counter(e.level for e in self.els if e.kind == "room")
        self.assertEqual(set(levels), {"B", "GF"})
        self.assertEqual(sum(levels.values()), 30)

    def test_lounge_polygon_and_area(self):
        r = self.by["room-lounge"]
        x0, y0, x1, y1 = self.lay["rooms"]["lounge"]["rect"]
        self.assertAlmostEqual(r.params["area_m2"], (x1 - x0) * (y1 - y0), places=2)
        self.assertEqual(len(r.params["polygon_mm"]), 4)
        self.assertEqual(r.level, "B")
        self.assertGreater(r.params["clear_height_mm"], 2600)       # 2.70 m false ceiling (2.80 m in the field)

    def test_ramp_cinema_clear_height_is_lower_than_lounge(self):
        # the cinema sits under the car ramp (2.0-2.65 m ceiling) -- villa_r11 room name
        self.assertLess(self.by["room-cinema"].params["clear_height_mm"],
                        self.by["room-lounge"].params["clear_height_mm"])

    def test_stair_dimensions(self):
        st = self.by["stair-main"]
        p = st.params
        self.assertEqual((p["risers"], p["treads"]), (17, 16))
        self.assertAlmostEqual(p["riser_mm"], 3000 / 17, places=2)     # 176.47 mm
        self.assertEqual(p["tread_mm"], 280.0)
        self.assertEqual(p["width_mm"], 950.0)
        self.assertEqual(p["rise_mm"], 3000)
        self.assertEqual(len(p["tread_boxes_mm"]), len(self.sp["stair"]))

    def test_stair_guards(self):
        open_glass = self.by["rail-stair-open-glass"]
        self.assertEqual(open_glass.params["guard_height_mm"], 900.0)
        self.assertTrue(open_glass.params["glazed"])
        self.assertEqual(open_glass.host, "stair-main")
        self.assertEqual(self.by["rail-stair-wall-handrail"].params["guard_height_mm"], 900.0)

    def test_every_opening_has_a_host_wall_on_its_level(self):
        for e in self.els:
            if e.kind in ("door", "window"):
                if e.host:
                    self.assertEqual(self.by[e.host].level, e.level, e.id)
        hosted = [e for e in self.els if e.kind in ("door", "window") and e.host]
        self.assertGreaterEqual(len(hosted), 0.8 * (self.kinds["door"] + self.kinds["window"]))

    def test_door_and_window_sizes_match_spec(self):
        d0 = self.sp["doors"][0]
        door = next(e for e in self.els if e.kind == "door" and e.level == d0["level"]
                    and e.params["rooms"] == list(d0["rooms"]))
        self.assertEqual(door.size[0], d0["width"] * 1000)
        self.assertEqual(door.size[2], d0["height"] * 1000)
        w0 = self.sp["windows"][0]
        win = next(e for e in self.els if e.kind == "window" and e.room == w0["room"])
        self.assertEqual(win.params["sill_mm"], w0["sill"] * 1000)

    def test_walls_geometry(self):
        for i, w in enumerate(self.sp["walls"]):
            e = self.by[S._wall_id(i, w)]
            self.assertAlmostEqual(e.size[0], math.hypot(w["x1"] - w["x0"], w["y1"] - w["y0"]) * 1000, places=0)
            self.assertEqual(e.size[2], w["height"] * 1000)

    def test_levels_table(self):
        self.assertEqual(S.LEVELS["B"]["ffl_scene_mm"], -3000)
        self.assertEqual(S.LEVELS["GF"]["ffl_revit_mm"] - S.LEVELS["B"]["ffl_revit_mm"], 3000)

    def test_sunken_north_patio(self):
        g = self.by["garden-north-patio"]
        self.assertTrue(g.params["sunken"])
        self.assertEqual(g.level, "SITE")


class SchemaRejects(unittest.TestCase):
    def test_duplicate_and_unknown(self):
        a = DesignElement(id="x", kind="wall", level="GF", params=dict(thickness_mm=1, height_mm=1, x0_mm=0, y0_mm=0, x1_mm=1, y1_mm=0))
        b = DesignElement(id="x", kind="spaceship", level="Z")
        errs = schema.validate([a, b])
        self.assertTrue(any("duplicate" in e for e in errs))
        self.assertTrue(any("unknown kind" in e for e in errs))
        self.assertTrue(any("unknown level" in e for e in errs))

    def test_missing_params_and_dangling_host(self):
        d = DesignElement(id="d", kind="door", level="GF", host="nowhere")
        errs = schema.validate([d])
        self.assertTrue(any("lacks param" in e for e in errs))
        self.assertTrue(any("host" in e for e in errs))


if __name__ == "__main__":
    unittest.main()
