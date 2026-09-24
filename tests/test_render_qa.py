"""Each render_qa check must fail the defect it was written for, and pass a good case."""
import random
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from archpipe import render_qa

GOOD_QA = {
    "camera": {"pitch_deg": 90.0, "shift_y": -0.05},
    "lights": {"on": True, "count": 5, "with_ies": 5, "fallback_sun": False},
    "sky": {"sun": True},
    "glass": {"architectural": 2},
    "windows": [{"id": "window-000001", "screen": [0.3, 0.4, 0.6, 0.8]}],
    "materials": [{"name": "Sash", "override": True, "saturation": 0.0}],
    "textiles": [{"name": "archpipe ivory bedding", "reflectance": 0.7}],
    "white_balance": True,
}


def scene(path, base=(150, 150, 148), window="textured", clip_fraction=0.0):
    """A neutral mid-grey room with a window region at GOOD_QA's screen rect."""
    rnd = random.Random(3)
    w, h = 400, 250
    img = Image.new("RGB", (w, h), base)
    px = img.load()
    x0, x1 = int(0.3 * w), int(0.6 * w)
    y0, y1 = int((1 - 0.8) * h), int((1 - 0.4) * h)
    for x in range(x0, x1):
        for y in range(y0, y1):
            if window == "textured":          # foliage/sky: real variation
                v = rnd.randint(40, 230)
                px[x, y] = (v // 2, v, v // 3)
            elif window == "void":            # smooth gradient, no content
                v = 200 + (y - y0) * 20 // (y1 - y0)
                px[x, y] = (v - 20, v - 10, v)
            elif window == "white":
                px[x, y] = (255, 255, 255)
    n = int(clip_fraction * w * h)
    for i in range(n):
        px[i % w, (i // w) % h] = (255, 255, 255)
    img.save(path)
    return path


class RenderQATests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def report(self, qa=None, **kw):
        return render_qa.check(scene(self.tmp / "r.png", **kw), qa or GOOD_QA)

    def status(self, report, prefix):
        return [c["status"] for c in report["checks"] if c["check"].startswith(prefix)]

    def test_good_render_passes(self):
        r = self.report()
        self.assertTrue(r["passed"], r["failed"])

    def test_void_window_fails(self):
        self.assertEqual(self.status(self.report(window="void"), "window_view"), ["FAIL"])

    def test_blown_window_fails(self):
        self.assertEqual(self.status(self.report(window="white"), "window_view"), ["FAIL"])

    def test_orange_cast_fails(self):
        self.assertEqual(self.status(self.report(base=(190, 140, 90)), "colour_cast"), ["FAIL"])

    def test_clipping_fails(self):
        self.assertEqual(self.status(self.report(clip_fraction=0.10), "highlight_clipping"), ["FAIL"])

    def test_tilted_camera_fails(self):
        qa = dict(GOOD_QA, camera={"pitch_deg": 81.0, "shift_y": 0})
        self.assertEqual(self.status(self.report(qa), "verticals_level"), ["FAIL"])

    def test_lost_photometry_fails(self):
        qa = dict(GOOD_QA, lights={"on": True, "count": 5, "with_ies": 0})
        self.assertEqual(self.status(self.report(qa), "photometry_bound"), ["FAIL"])

    def test_glass_blocking_sun_fails(self):
        qa = dict(GOOD_QA, glass={"architectural": 0})
        self.assertEqual(self.status(self.report(qa), "glass_passes_daylight"), ["FAIL"])

    def test_cad_colour_fails_but_stated_finish_passes(self):
        qa = dict(GOOD_QA, materials=[{"name": "Shade Finish Dark Bronze", "saturation": 1.0},
                                      {"name": "Sash", "override": True, "saturation": 1.0}])
        r = self.report(qa)
        self.assertEqual(self.status(r, "cad_colour"), ["FAIL"])
        self.assertIn("cad_colour:Shade Finish Dark Bronze", r["failed"])

    def test_textile_without_reflectance_fails(self):
        qa = dict(GOOD_QA, textiles=[{"name": "archpipe ivory bedding", "reflectance": None}])
        self.assertEqual(self.status(self.report(qa), "textile_reflectance"), ["FAIL"])

    def test_collapsed_or_slid_cloth_fails(self):
        slid = dict(GOOD_QA, bedding={"mattress_y": [1.64, 3.35], "mattress_top": 0.55,
                                      "duvet_y": [1.34, 2.32], "duvet_z_min": 0.006})
        self.assertEqual(self.status(self.report(slid), "cloth_plausible"), ["FAIL"])
        good = dict(GOOD_QA, bedding={"mattress_y": [1.64, 3.35], "mattress_top": 0.55,
                                      "duvet_y": [1.51, 2.90], "duvet_z_min": 0.11})
        self.assertEqual(self.status(self.report(good), "cloth_plausible"), ["PASS"])

    def test_log_parsing(self):
        log = "noise\nSCENE QA {\"camera\": {\"pitch_deg\": 90}}\nSCENE wrote x"
        self.assertEqual(render_qa.scene_qa_from_log(log)["camera"]["pitch_deg"], 90)
        with self.assertRaises(ValueError):
            render_qa.scene_qa_from_log("no qa here")


if __name__ == "__main__":
    unittest.main()
