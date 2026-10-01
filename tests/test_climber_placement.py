import importlib.util
import math
import unittest
from pathlib import Path


path = Path(__file__).resolve().parents[1] / "src/archpipe/blender/climber_placement.py"
spec = importlib.util.spec_from_file_location("climber_placement", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ClimberPlacement(unittest.TestCase):
    def test_density_mix_and_envelope(self):
        box = (1.0, 2.0, 0.0, 2.5, 2.1, 2.0)
        points = module.placements(box, density=120)
        self.assertEqual(len(points), math.ceil(1.5 * 2.0 * 120))
        self.assertEqual(sum(p[3] == "leaf" for p in points), 252)
        self.assertEqual(sum(p[3] == "bract" for p in points), 108)
        for x, y, z, _ in points:
            self.assertLessEqual(box[0], x)
            self.assertLessEqual(x, box[3])
            self.assertLessEqual(box[1], y)
            self.assertLessEqual(y, box[4])
            self.assertLessEqual(box[2], z)
            self.assertLessEqual(z, box[5])

    def test_invalid_envelope_fails(self):
        with self.assertRaises(ValueError):
            module.placements((0, 0, 0, 1, 0, 2))

    # Client round-3 (v01/v02/v24): the climbers read as "almost invisible: too sparse/small" at the old
    # density=120 default. Reproduce that on the real east-trellis envelope (villa_landscape.py mass box,
    # 0.08 x 1.34 x 2.05 m) and show it fails an 80% coverage target -- the density_for_coverage() fix must
    # not just raise SOME density, it must clear the stated bar.
    def test_old_density_fails_80_percent_coverage_on_real_envelope(self):
        self.assertLess(module.coverage_estimate(120), 0.80)

    def test_density_for_coverage_clears_80_percent(self):
        density = module.density_for_coverage(target=0.80)
        self.assertGreaterEqual(module.coverage_estimate(density), 0.80)

    def test_young_planting_default_leaves_most_lattice_open(self):
        self.assertEqual(module.COVERAGE_TARGET, 0.35)
        estimated = module.coverage_estimate(module.density_for_coverage())
        self.assertGreaterEqual(estimated, module.COVERAGE_TARGET)
        self.assertLess(estimated, 0.50)

    def test_instance_sizes_in_the_requested_range(self):
        # leaf ~5-8 cm, bract ~3-4 cm (full span = 2 * half-extent)
        self.assertTrue(0.05 <= 2 * module.SIZE["leaf"] <= 0.08)
        self.assertTrue(0.03 <= 2 * module.SIZE["bract"] <= 0.04)

    def test_70_30_leaf_bract_mix_at_the_render_density(self):
        box = (1.0, 2.0, 0.0, 2.5, 2.1, 2.0)
        density = module.density_for_coverage(target=0.80)
        points = module.placements(box, density=density)
        leaf = sum(p[3] == "leaf" for p in points)
        bract = sum(p[3] == "bract" for p in points)
        self.assertAlmostEqual(leaf / len(points), 0.70, delta=0.02)
        self.assertAlmostEqual(bract / len(points), 0.30, delta=0.02)

    def test_render_density_covers_the_real_east_trellis_envelope(self):
        # villa_landscape.py's east climber mass box (not editable here): a shallow, real envelope, not a
        # synthetic square one -- the earlier version of this suite only checked a synthetic box and would have
        # missed a fix that worked there but not on the thin real trellis.
        box = (28.42 - .17, -24.0 + .08, -3.0, 28.42 - .05, -24.0 + 1.42, -0.95)
        self.assertTrue(0.10 <= box[3] - box[0] <= 0.20)
        density = module.density_for_coverage(target=0.80)
        self.assertGreaterEqual(module.coverage_estimate(density), 0.80)
        points = module.placements(box, density=density)
        for x, y, z, _ in points:
            self.assertLessEqual(box[0], x); self.assertLessEqual(x, box[3])
            self.assertLessEqual(box[1], y); self.assertLessEqual(y, box[4])
            self.assertLessEqual(box[2], z); self.assertLessEqual(z, box[5])
