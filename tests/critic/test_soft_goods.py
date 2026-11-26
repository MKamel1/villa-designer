"""soft_goods: the baked cushions are closed, outward, rest on their host and keep the fabric colours."""
import gzip
import json
import re
import unittest
from collections import Counter
from pathlib import Path

import numpy as np

from archpipe.blender import soft_goods

FIX = Path(__file__).parent / "fixtures" / "rigid_soft_goods.json.gz"


def scene():
    return json.load(gzip.open(FIX, "rt"))


def volume(faces):
    v = 0.0
    for f in faces:
        p = np.array(f)
        c = p.mean(0)
        for i in range(len(p)):
            v += np.dot(c, np.cross(p[i], p[(i + 1) % len(p)])) / 6.0
    return v


class Baked(unittest.TestCase):
    def setUp(self):
        self.sc = scene()
        self.old = {m["id"]: m["faces"] for m in self.sc["meshes"]}
        self.report = soft_goods.soften_scene(self.sc)
        self.soft = [m for m in self.sc["meshes"] if m["id"].startswith("dress-")]

    def test_counts(self):
        self.assertEqual((self.report["cushions"], self.report["throws"]), (2, 1))

    def test_every_soft_good_is_a_closed_outward_shell(self):
        for m in self.soft:
            edges = Counter()
            for f in m["faces"]:
                k = [tuple(np.round(p, 5)) for p in f]
                for i in range(len(k)):
                    edges[frozenset((k[i], k[(i + 1) % len(k)]))] += 1
            self.assertEqual(set(edges.values()), {2}, m["id"])
            self.assertGreater(volume(m["faces"]), 0, m["id"])

    def test_cushion_is_no_thicker_than_the_rigid_one(self):
        m = next(m for m in self.soft if m["id"] == "dress-cushion-pb-bed-0")
        _, _, _, _, (_, _, t_new) = soft_goods.footprint(np.array([p for f in m["faces"] for p in f]))
        _, _, _, _, (_, _, t_old) = soft_goods.footprint(np.array([p for f in self.old[m["id"]] for p in f]))
        self.assertLessEqual(t_new, t_old * 1.05)

    def test_lowest_point_unchanged_when_nothing_to_sink_into(self):
        m = next(m for m in self.soft if m["id"] == "dress-cushion-pb-bed-0")
        low = lambda faces: min(p[2] for f in faces for p in f)
        self.assertAlmostEqual(low(m["faces"]), low(self.old[m["id"]]), delta=0.003)

    def test_fabric_gets_class_tile_and_keeps_colour(self):
        spec = self.sc["materials"][next(m["material"] for m in self.soft if m["id"] == "dress-cushion-pb-bed-0")]
        self.assertEqual(spec["fabric_class"], "boucle")
        self.assertAlmostEqual(spec["tile_m"], 0.853, delta=0.01)       # Carpet016: feature 5.86 mm per 1 m of tile
        self.assertGreaterEqual(spec["roughness"], 0.85)
        self.assertEqual(spec["base_rgb"], scene()["materials"][next(m["material"] for m in scene()["meshes"] if m["id"] == "dress-cushion-pb-bed-0")]["base_rgb"])


class RenderWiring(unittest.TestCase):
    src = (Path(__file__).parents[2] / "src/archpipe/blender/villa_scene.py").read_text(encoding="utf-8")

    def test_softening_is_skipped_in_the_measuring_modes(self):
        """SOFT-rebuild-1: a record measured on softened geometry failed the transport digest of the authored scene."""
        self.assertRegex(self.src, r"not \(args\.no_soft or args\.measure_exposure_groups or args\.measure_lighting")

    def test_post_condition_is_called_after_softening(self):
        self.assertTrue(re.search(r"soften_scene\(scene_data\)\s+print\(.*\)\s+soft_goods\.assert_soft_goods_real", self.src))


if __name__ == "__main__":
    unittest.main()
