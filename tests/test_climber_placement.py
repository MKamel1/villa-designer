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
