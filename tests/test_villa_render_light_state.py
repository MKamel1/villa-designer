"""RF defect 3 guard: the lighting states the render set shows are the lighting design's own scenes, not typed numbers."""
import json
import unittest

from archpipe.concept import villa_lighting as VL, villa_r11 as R, villa_render as VR
from archpipe.critic import render_set as S


class LightState(unittest.TestCase):
    def test_basement_day_preset_is_the_design_day_scene(self):
        day = VL.SCENES["B-open"]["Day"]
        light = S.load()["light"]["basement-day"]["dimmers"]
        self.assertEqual(light, {"ambient": day["*ambient"], "accent": day["*accent"]})

    def test_design_evening_preset_is_the_design_evening_scene(self):
        ev = VL.SCENES["B-open"]["Evening"]
        d = S.load()["light"]["design-evening"]["dimmers"]
        self.assertEqual(d, {"ambient": ev["*ambient"], "accent": ev["*accent"], "decorative": ev["*decorative"]})

    def test_base_views_basement_day_reads_the_same_scene(self):
        v = {v["id"]: v for v in VR.VIEWS(R.design("D1"))}["v03-street-lounge"]
        self.assertEqual(v["dimmers"], S.load()["light"]["basement-day"]["dimmers"])

    def test_a_typed_half_would_be_caught(self):          # negative: the L9P draft values
        day = VL.SCENES["B-open"]["Day"]
        self.assertNotEqual({"ambient": 0.5, "accent": 0.5}, {"ambient": day["*ambient"], "accent": day["*accent"]})


if __name__ == "__main__":
    unittest.main()
