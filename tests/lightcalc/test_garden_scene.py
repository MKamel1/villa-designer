"""Garden lights in the production scene (lane LG): the lights, their bodies, the dusk layer on the dusk garden views only, the camera clearing that v07 needed."""
import math
import unittest

from archpipe.landscape.build import lights as LT, production as PRD
from archpipe.lightcalc import garden as GD
from archpipe.villa_render_contract import LAYERS


class Lights(unittest.TestCase):
    def test_one_light_per_live_fitting_at_the_render_scene_levels(self):
        ls = LT.lights()
        levels = GD.SCENES[GD.RENDER_SCENE]["levels"]
        live = [f for f in GD.FIXTURES if levels[f.zone] > 0]
        self.assertEqual(sorted(l["id"] for l in ls), sorted("gl-" + f.id for f in live))
        for l in ls:
            self.assertEqual(l["layer"], "evening-garden")
            self.assertIn("evening-garden", LAYERS)
            self.assertAlmostEqual(math.sqrt(sum(c * c for c in l["aim"])), 1.0, places=4)
            self.assertTrue(l["ies"].startswith("garden/") and ".." not in l["ies"])

    def test_iku_lights_carry_the_product_and_unverified_ones_say_so(self):
        by = {l["id"]: l for l in LT.lights()}
        iku = by["gl-NP-1"]
        self.assertEqual((iku["product"]["manufacturer"], iku["product"]["code"], iku["product"]["generic"]), ("erco", "B0000184", False))
        self.assertEqual(iku["lumens"], 676.0)
        self.assertEqual(iku["cct_k"], 2700)                       # the 2700 K variant on request; the 3000 K file is the photometry (caveat in the record)
        self.assertIn("3000 K", iku["garden_lg"]["caveat"])
        up = by["gl-UP-1"]
        self.assertTrue(up["product"]["generic"])
        self.assertTrue(up["garden_lg"]["status"].startswith("UNVERIFIED"))

    def test_negative_a_zone_at_level_zero_has_no_light(self):
        self.assertFalse([l for l in LT.lights("quiet-north-court") if l["garden_lg"]["zone"] in ("dining", "graze", "uplight")])

    def test_dimmer_is_the_scene_level_and_within_the_contract(self):
        for l in LT.lights():
            self.assertTrue(0 < l["dimmer"] <= 1)
            self.assertAlmostEqual(l["dimmer"], GD.SCENES[GD.RENDER_SCENE]["levels"][l["garden_lg"]["zone"]], places=3)

    def test_ies_files_are_the_manufacturers_and_the_assumed_one(self):
        import tempfile, pathlib
        from archpipe.photometry import parse
        with tempfile.TemporaryDirectory() as d:
            by = {l["id"]: l for l in LT.lights()}
            for lid in ("gl-NP-1", "gl-UP-1"):
                t = pathlib.Path(d) / by[lid]["ies"]
                PRD.write_ies(by[lid], t)
                ph = parse(t.read_text(encoding="utf-8"))
                self.assertGreater(ph.integrated_flux if not callable(ph.integrated_flux) else ph.integrated_flux(), 200)
            self.assertIn("ERCO", (pathlib.Path(d) / by["gl-NP-1"]["ies"]).read_text(encoding="utf-8"))


class Bodies(unittest.TestCase):
    def test_a_closed_body_at_every_iku_and_none_for_the_uplights(self):
        bs = LT.bodies()
        ids = {b["id"] for b in bs}
        self.assertIn("gl-body-NP-1", ids)
        self.assertFalse([i for i in ids if "UP-" in i])
        for b in bs:
            edges = {}
            for f in b["faces"]:
                for i in range(len(f)):
                    e = tuple(sorted((tuple(f[i]), tuple(f[(i + 1) % len(f)]))))
                    edges[e] = edges.get(e, 0) + 1
            self.assertTrue(all(n == 2 for n in edges.values()), b["id"])      # watertight: every edge shared by exactly two faces
            self.assertTrue(b["label"].startswith("dressing: "))


class DuskLayer(unittest.TestCase):
    def view(self, state, vid="v07-terrace-dusk"):
        return dict(id=vid, state=state, layers_on=["ambient"], when="2026-10-15T18:35:00+03:00", resolution=[1920, 1280], camera=dict(position=[0, 0, 5], target=[1, 0, 5], lens_mm=24, sensor_mm=36), hide_meshes=[], subjects=[])

    G = None

    @classmethod
    def setUpClass(cls):
        cls.G = PRD.garden()

    def test_dusk_garden_view_gets_the_layer(self):
        v = self.view("exterior-dusk")
        PRD.prepare_view(v, self.G)
        self.assertIn("evening-garden", v["layers_on"])

    def test_negative_a_day_garden_view_does_not(self):
        v = self.view("exterior-day", "v41-south-garden-terrace")
        PRD.prepare_view(v, self.G)
        self.assertNotIn("evening-garden", v["layers_on"])

    def test_negative_an_interior_dusk_view_does_not(self):
        v = self.view("exterior-dusk", "v09-dining-evening")
        PRD.prepare_view(v, self.G)
        self.assertNotIn("evening-garden", v["layers_on"])

    def test_the_two_dusk_key_views_exist_and_clone_a_dusk_template(self):
        self.assertIn("gi-dining-firepit-dusk", PRD.KEY_VIEWS)
        self.assertIn("gi-north-court-pond-dusk", PRD.KEY_VIEWS)
        self.assertEqual(PRD.KEY_VIEWS["gi-dining-firepit-dusk"]["tpl"], "v07-terrace-dusk")
        self.assertNotIn("tpl", PRD.KEY_VIEWS["gi-dining-firepit"])         # the day key views still clone v41


class CameraClearing(unittest.TestCase):
    def test_search_radius_covers_the_v07_corner(self):
        self.assertGreaterEqual(PRD.CLEAR_SEARCH_M, 4)        # v07's corner has no clear point within 3.5 m; the first dusk render showed a plant leaf across the frame

    def test_no_production_garden_view_is_left_uncleared(self):
        import copy
        import json
        from archpipe.concept import villa_r11 as R, villa_render as VR
        lay = R.design("D1")
        views = copy.deepcopy(VR.VIEWS(lay))
        g = PRD.garden()
        for v in views:
            PRD.prepare_view(v, g)
        self.assertEqual(PRD.uncleared(views), [], "a camera is left inside a garden solid")

    def test_negative_the_old_3_m_search_leaves_v07_inside_a_plant(self):
        import copy
        from unittest.mock import patch
        from archpipe.concept import villa_r11 as R, villa_render as VR
        views = copy.deepcopy(VR.VIEWS(R.design("D1")))
        g = PRD.garden()
        with patch.object(PRD, "CLEAR_SEARCH_M", 3):
            for v in views:
                PRD.prepare_view(v, g)
        self.assertIn("v07-terrace-dusk", PRD.uncleared(views))


if __name__ == "__main__":
    unittest.main()
