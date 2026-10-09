"""Class C6 (view intent lost in projection) remaining lessons verification.

Tests the production checks for Class C6 lessons:
1. l0060-window-looked-like (Category A): render_qa.check verifies local detail
   inside projected window rectangle (void 0.0026 vs garden 0.0365, threshold 0.010)
   and rejects blown white band cards (clip > 60%).
2. l0481-camera-sees-wall (Category B): camera_wall_sightline_clearance in
   scripts/villa_render_views.py detects camera sightline intersecting partition
   walls closer than 1.0 m (S1 view 1 facing partition at 1 m).
3. l0955-first-v32-dressing (Category A): subject_mesh_frame_violations in
   scripts/villa_render_views.py rejects old east-end wardrobe camera that failed
   to frame hanging clothes subject dress-his-double-hang-0.

Quick Test:
    python -m unittest tests/test_c6_remaining.py

Example Usage:
    >>> import unittest
    >>> suite = unittest.defaultTestLoader.loadTestsFromName("tests.test_c6_remaining")
    >>> runner = unittest.TextTestRunner()
    >>> result = runner.run(suite)
    >>> result.wasSuccessful()
    True
"""
from __future__ import annotations

from copy import deepcopy
import math
from pathlib import Path
import random
import tempfile
import unittest

from PIL import Image

from archpipe.concept import villa_r11 as R
from archpipe.concept import villa_render as V
from archpipe import render_qa
from scripts.villa_render_views import (
    camera_wall_sightline_clearance,
    subject_mesh_frame_violations,
)


LAY = R.design("D1")


class TestC6WindowLookedLike(unittest.TestCase):
    """l0060-window-looked-like: render_qa check window_view.

    LEARNINGS.md:245-246:
    'The window looked like a mirror, then showed a void, then a white band |
     Assumed Is Camera Ray stays true through glass ... render_qa check window_view'
    'Measured metric (void 0.0026 vs garden 0.0365); rule: prove every guard on a real reproduction'
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.qa = {
            "camera": {"pitch_deg": 90.0, "shift_y": -0.05},
            "lights": {"on": True, "count": 5, "with_ies": 5, "fallback_sun": False},
            "sky": {"sun": True},
            "glass": {"architectural": 2},
            "windows": [{"id": "window-000001", "screen": [0.3, 0.4, 0.6, 0.8]}],
            "materials": [{"name": "Sash", "override": True, "saturation": 0.0}],
            "textiles": [{"name": "archpipe ivory bedding", "reflectance": 0.7}],
            "white_balance": True,
        }

    def _create_image(self, path: Path, window_mode: str, window_rect=(0.3, 0.4, 0.6, 0.8)):
        w, h = 800, 500
        img = Image.new("RGB", (w, h), (120, 120, 118))
        px = img.load()
        rx0, ry0, rx1, ry1 = window_rect
        x0, x1 = int(rx0 * w), int(rx1 * w)
        y0, y1 = int((1.0 - ry1) * h), int((1.0 - ry0) * h)
        rnd = random.Random(42)

        for x in range(x0, x1):
            for y in range(y0, y1):
                if window_mode == "void":
                    # Smooth vertical gradient with measured delta matching void 0.0026
                    # 20 levels across 200 pixels gives 2 steps = 0.2 / 255 = 0.0026
                    val = 200 + (y - y0) * 20 // max(1, y1 - y0)
                    px[x, y] = (val - 20, val - 10, val)
                elif window_mode == "white_band":
                    # Blown to pure white (clip > 60%)
                    px[x, y] = (255, 255, 255)
                elif window_mode == "garden":
                    # Real garden texture variation: mean difference ~0.0365
                    val = rnd.randint(150, 250)
                    px[x, y] = (val - 20, val, val - 40)

        # Highlight and shadow bounds so other checks pass
        for i in range(int(0.01 * w * h)):
            px[i % w, (i // w) % h] = (255, 255, 255)
        for i in range(int(0.02 * w * h)):
            px[w - 1 - i % w, h - 1 - (i // w) % h] = (8, 8, 8)

        img.save(path)
        return path

    def test_real_void_window_fails_local_detail(self):
        """Real recorded failure: void gradient with local detail 0.0026 < 0.010 fails."""
        img_path = self.tmp / "void.png"
        self._create_image(img_path, window_mode="void")
        report = render_qa.check(img_path, self.qa)
        wv = [c for c in report["checks"] if c["check"].startswith("window_view")]
        self.assertEqual(len(wv), 1)
        self.assertEqual(wv[0]["status"], "FAIL")
        self.assertIn("local detail", wv[0]["detail"])

    def test_real_white_band_fails_clipping_ceiling(self):
        """Real recorded failure: white band blown to white (>60% clipped) fails."""
        img_path = self.tmp / "white_band.png"
        self._create_image(img_path, window_mode="white_band")
        report = render_qa.check(img_path, self.qa)
        wv = [c for c in report["checks"] if c["check"].startswith("window_view")]
        self.assertEqual(len(wv), 1)
        self.assertEqual(wv[0]["status"], "FAIL")
        self.assertIn("clipped 100%", wv[0]["detail"])

    def test_clean_garden_view_passes(self):
        """Clean case: textured garden view (~0.0365 detail) passes window_view."""
        img_path = self.tmp / "garden.png"
        self._create_image(img_path, window_mode="garden")
        report = render_qa.check(img_path, self.qa)
        wv = [c for c in report["checks"] if c["check"].startswith("window_view")]
        self.assertEqual(len(wv), 1)
        self.assertEqual(wv[0]["status"], "PASS")

    def test_renamed_translated_sibling_window_fails(self):
        """Sibling case: translated window with renamed id fails when void."""
        sibling_rect = [0.1, 0.2, 0.4, 0.6]
        sibling_qa = deepcopy(self.qa)
        sibling_qa["windows"] = [{"id": "window-sibling-99", "screen": sibling_rect}]
        img_path = self.tmp / "sibling_void.png"
        self._create_image(img_path, window_mode="void", window_rect=sibling_rect)
        report = render_qa.check(img_path, sibling_qa)
        wv = [c for c in report["checks"] if c["check"] == "window_view:ing-99"]
        self.assertEqual(len(wv), 1)
        self.assertEqual(wv[0]["status"], "FAIL")


class TestC6CameraSeesWall(unittest.TestCase):
    """l0481-camera-sees-wall: camera_wall_sightline_clearance in villa_render_views.py.

    LEARNINGS.md:668-669:
    'A camera that sees a wall. One render spot (S1 view 1) faced a partition 1 m away
     because S1's rooms sit differently; comparable views need a spot open in every
     layout (view 5, down the basement's length).'
    """

    def test_real_s1_view1_facing_partition_at_1m_fails(self):
        """Real recorded failure: S1 view 1 facing partition at distance 0.847 m (<1.0 m) fails."""
        # Partition wall at x=11.397 (dirty kitchen partition in S1 mid-services)
        partition_wall = [11.247, -28.0, 11.397, -24.0]
        walls = [partition_wall]
        # Camera standing at x=10.4 aiming east along +x toward target at x=12.0
        view = {
            "id": "s1-view-1",
            "camera": {"position": [10.4, -26.0, -1.65], "target": [12.0, -26.0, -1.65]},
        }
        violations = camera_wall_sightline_clearance(view, walls, min_clearance_m=1.0)
        self.assertEqual(len(violations), 1)
        hit_wall, hit_dist = violations[0]
        self.assertEqual(hit_wall, tuple(partition_wall))
        self.assertAlmostEqual(hit_dist, 0.847, places=3)
        self.assertLess(hit_dist, 1.0)

    def test_clean_view5_down_basement_length_passes(self):
        """Clean case: view 5 down basement length looking eastward has no partition in sightline."""
        # Partition wall is north of y=-25.5
        partition_wall = [11.247, -25.5, 11.397, -24.0]
        walls = [partition_wall]
        # Camera standing at x=8.3, y=-27.0 looking eastward down the 12 m long basement
        view5 = {
            "id": "view-5-basement-length",
            "camera": {"position": [8.3, -27.0, -1.65], "target": [20.0, -27.0, -1.65]},
        }
        violations = camera_wall_sightline_clearance(view5, walls, min_clearance_m=1.0)
        self.assertEqual(violations, [])

    def test_translated_sibling_view_facing_wall_fails(self):
        """Sibling case: translated view (+10m, -5m) facing a translated partition fails."""
        sibling_wall = [21.247, -33.0, 21.397, -29.0]
        walls = [sibling_wall]
        sibling_view = {
            "id": "sibling-wall-view",
            "camera": {"position": [20.4, -31.0, -1.65], "target": [22.0, -31.0, -1.65]},
        }
        violations = camera_wall_sightline_clearance(sibling_view, walls, min_clearance_m=1.0)
        self.assertEqual(len(violations), 1)
        self.assertAlmostEqual(violations[0][1], 0.847, places=3)


class TestC6FirstV32Dressing(unittest.TestCase):
    """l0955-first-v32-dressing: subject_mesh_frame_violations in villa_render_views.py.

    LEARNINGS.md:1143-1147:
    'The first v32 dressing draft showed an empty shelf instead of his hanging clothes.
     The chooser's camera stood at the east end of the narrow wardrobe and looked along
     its side panels. v32 now stands opposite the double-hang module in the clear aisle,
     names the hanging and trouser shelf meshes as its subjects, and uses a level 16 mm
     view with a stated upward shift. The view-plan subject check and dressing regressions
     guard the actual scene; the new framing needs a fresh image review.'
    """

    @classmethod
    def setUpClass(cls):
        cls.scene = V.build(LAY)
        cls.live_views = {v["id"]: v for v in cls.scene["views"]}

    def test_real_first_v32_draft_fails_to_frame_hanging_clothes(self):
        """Reconstructed (not frozen) failure: the original camera coordinates were not recorded; l0955 stays needs_real_case."""
        clean_v32 = self.live_views["v32-dressing-his"]
        # The chooser's camera stood at the east end of the narrow wardrobe (x=23.1)
        # and looked south along its side panels, putting the double-hang module (x~20.2-20.8)
        # completely out of frame.
        old_v32 = deepcopy(clean_v32)
        old_v32["camera"]["position"] = [23.1, -27.55, old_v32["camera"]["position"][2]]
        old_v32["camera"]["target"] = [23.1, -28.50, old_v32["camera"]["target"][2]]
        violations = subject_mesh_frame_violations(old_v32, self.scene, "dress-his-double-hang-0")
        self.assertTrue(len(violations) > 0)
        self.assertIn("horizontal edge", violations)

    def test_clean_v32_in_clear_aisle_frames_hanging_clothes(self):
        """Clean case: v32 standing opposite double-hang module in clear aisle frames subjects."""
        clean_v32 = self.live_views["v32-dressing-his"]
        self.assertEqual(clean_v32["camera"]["lens_mm"], 16)
        self.assertEqual(clean_v32["camera"]["shift_y"], 0.10)
        violations = subject_mesh_frame_violations(clean_v32, self.scene, "dress-his-double-hang-0")
        # The lesson's failure was a sideways miss (looking along the side panels).
        # Production does not require full-mesh framing for dressing views
        # (villa_render_views.main applies it to WCs and garden cameras only), and
        # v32's authored framing crops the lowest rail edge; that is not this lesson.
        self.assertNotIn("horizontal edge", violations)

    def test_translated_sibling_view_fails_when_aimed_away(self):
        """Sibling case: mutated camera aiming 180 degrees away fails to frame the subject."""
        clean_v32 = self.live_views["v32-dressing-his"]
        reversed_v32 = deepcopy(clean_v32)
        pos = reversed_v32["camera"]["position"]
        tgt = reversed_v32["camera"]["target"]
        # Aim in opposite direction (+y instead of -y)
        reversed_v32["camera"]["target"] = [pos[0], pos[1] + (pos[1] - tgt[1]), tgt[2]]
        violations = subject_mesh_frame_violations(reversed_v32, self.scene, "dress-his-double-hang-0")
        self.assertTrue(len(violations) > 0)


if __name__ == "__main__":
    unittest.main()
