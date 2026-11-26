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


CUBE = [[[0, 0, 0], [0, 1, 0], [1, 1, 0], [1, 0, 0]], [[0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]],
        [[0, 0, 0], [1, 0, 0], [1, 0, 1], [0, 0, 1]], [[0, 1, 0], [0, 1, 1], [1, 1, 1], [1, 1, 0]],
        [[0, 0, 0], [0, 0, 1], [0, 1, 1], [0, 1, 0]], [[1, 0, 0], [1, 1, 0], [1, 1, 1], [1, 0, 1]]]


def box_mesh(mid, material, **kw):
    return dict(id=mid, group="dressing", material=material, faces=CUBE, bevel_m=0, subdivide=0, **kw)


class EasedEdges(unittest.TestCase):
    """Case goods and upholstered boxes lose their knife edge in one place (ease_edges), and only those."""

    def run_rule(self, *meshes, materials=None):
        from archpipe.critic import furniture_realism as F
        sc = {"meshes": list(meshes), "materials": materials or {}}
        soft_goods.ease_edges(sc)
        return sc, F

    def test_case_good_gets_two_mm_and_passes_the_box_check(self):
        sc, F = self.run_rule(box_mesh("dress-x-shelf-0", "walnut-grain-x", part_kind="shelf"))
        self.assertGreaterEqual(sc["meshes"][0]["bevel_m"], 0.002)
        self.assertEqual([f for f in F.check_mesh(sc["meshes"][0], {}, {}) if f.check == "box"], [])

    def test_a_1_5_mm_cabinet_edge_is_raised(self):
        sc, _ = self.run_rule(dict(box_mesh("furn-x-cabinet-0", "oak"), bevel_m=0.0015, group="furniture"))
        self.assertEqual(sc["meshes"][0]["bevel_m"], 0.002)

    def test_upholstered_box_gets_six_mm(self):
        sc, F = self.run_rule(dict(box_mesh("furn-kb-bed-2", "linen"), group="furniture"))
        self.assertEqual(sc["meshes"][0]["bevel_m"], 0.006)
        self.assertEqual([f for f in F.check_mesh(sc["meshes"][0], {}, {}) if f.check == "box"], [])

    def test_glass_garments_and_a_proxy_replaced_by_a_model_are_left_alone(self):
        hidden = dict(box_mesh("furn-sofa-0", "linen"), visibility={"camera": False})
        sc, _ = self.run_rule(box_mesh("dress-x-glass", "glass-clear"), box_mesh("dress-x-shirt", "linen", part_kind="garment"), hidden)
        self.assertEqual([m["bevel_m"] for m in sc["meshes"]], [0, 0, 0])

    def test_already_rounded_is_not_overwritten(self):
        sc, _ = self.run_rule(dict(box_mesh("furn-x-chair-0", "linen"), bevel_m=0.02, subdivide=1))
        self.assertEqual(sc["meshes"][0]["bevel_m"], 0.02)


class FabricScaleEverywhere(unittest.TestCase):
    """The weave rule is one rule for every fabric on furniture, not only cushions and throws."""

    def scene_with_chair(self, material="boucle", mid="furn-dining-table-chair-1-1", group="furniture"):
        sc = scene()
        sc["materials"]["boucle-x"] = dict(sc["materials"][next(m["material"] for m in sc["meshes"] if m["id"] == "dress-cushion-pb-bed-0")])
        sc["materials"]["boucle-x"]["tile_m"] = 0.30
        sc["meshes"].append(dict(box_mesh(mid, "boucle-x", part_kind="chair"), group=group))
        return sc

    def test_dining_chair_boucle_loops_land_in_the_band(self):
        from archpipe.critic import furniture_realism as F
        sc = self.scene_with_chair()
        table = F.fabric_table()
        chair = sc["meshes"][-1]
        self.assertTrue([f for f in F.check_mesh(chair, sc["materials"], table) if f.check == "scale"])
        soft_goods.soften_materials(sc)
        self.assertEqual([f for f in F.check_mesh(chair, sc["materials"], table) if f.check == "scale"], [])

    def test_a_fabric_on_a_hidden_proxy_is_not_retiled_by_it(self):
        sc = self.scene_with_chair(mid="furn-hidden-0")
        sc["meshes"][-1]["visibility"] = {"camera": False}
        sc["meshes"] = [m for m in sc["meshes"] if not m["id"].startswith("dress-")]
        soft_goods.soften_materials(sc)
        self.assertEqual(sc["materials"]["boucle-x"]["tile_m"], 0.30)


class ThrowDrape(unittest.TestCase):
    """A throw is the cloth drop baked onto its real hosts, used only while those hosts are unchanged."""

    def setUp(self):
        self.drapes = soft_goods.throw_drapes()

    def test_every_committed_drape_is_a_closed_outward_shell_lying_up(self):
        self.assertTrue(self.drapes, "no drape bake committed")
        for tid, rec in self.drapes.items():
            faces = soft_goods.drape_faces(rec)
            edges = Counter()
            for f in faces:
                k = [tuple(np.round(p, 5)) for p in f]
                for i in range(len(k)):
                    edges[frozenset((k[i], k[(i + 1) % len(k)]))] += 1
            self.assertEqual(set(edges.values()), {2}, tid)
            self.assertGreater(volume(faces), 0, tid)
            self.assertAlmostEqual(np.ptp([p[2] for f in faces for p in f]) > 0.02, True, msg=tid)   # it drapes, it is not a plate

    def test_signature_follows_the_hosts_within_tolerance(self):
        from archpipe.critic.furniture_realism import triangles
        sig = lambda t: soft_goods.throw_signature([("furn-a-0", t)], [])
        base = triangles(CUBE)
        self.assertTrue(soft_goods.signature_matches(sig(base), sig(base + [0.0005, 0, 0])))     # numpy noise: same hosts
        self.assertFalse(soft_goods.signature_matches(sig(base), sig(base + [0.01, 0, 0])))      # a host moved 1 cm
        self.assertFalse(soft_goods.signature_matches(sig(base), sig(base[:-1])))                # a host changed shape

    def test_a_throw_whose_hosts_changed_falls_back_and_is_named(self):
        sc = scene()
        tid = next(m["id"] for m in sc["meshes"] if m["id"].startswith("dress-throw-"))
        soft_goods.throw_drapes.cache_clear()
        real = soft_goods.throw_drapes
        try:
            soft_goods.throw_drapes = lambda: {tid: dict(self.drapes[next(iter(self.drapes))], hosts={"hosts": [], "models": []})}
            report = soft_goods.soften_scene(sc)
        finally:
            soft_goods.throw_drapes = real
        self.assertEqual(report["stale_throw_drapes"], [tid])


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless((Path.home() / "archpipe/assets/library/props/throw_pillows_01/model.gltf").exists(), "render-host library absent")
class ScannedAsset(unittest.TestCase):
    def test_gltf_reader_agrees_with_the_committed_fixture(self):
        from archpipe.blender.gltf_check import gltf_triangles
        tris = gltf_triangles(Path.home() / "archpipe/assets/library/props/throw_pillows_01/model.gltf")
        self.assertEqual(len(tris), 3124 + 3238)

    def test_scanned_pillows_are_not_a_box(self):
        from archpipe.blender.gltf_check import model_findings
        scene = {"models": [{"id": "model-x", "asset": "throw_pillows_01", "role": "cushion"}]}
        self.assertEqual(model_findings(scene, Path.home() / "archpipe/assets/library"), [])
