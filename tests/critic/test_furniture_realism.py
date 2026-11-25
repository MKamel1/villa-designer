"""Furniture realism check: positive tests on the REAL defect (the rigid 2026-11-25 cushions) and negative tests on a
real scanned asset (Poly Haven throw_pillows_01, CC0) and on the baked cushions that replace the defect."""
import gzip
import json
import unittest
from pathlib import Path

import numpy as np

from archpipe.blender import soft_goods
from archpipe.critic import furniture_realism as F

FIX = Path(__file__).parent / "fixtures"


def real():
    return json.load(gzip.open(FIX / "rigid_soft_goods.json.gz", "rt"))


def checks(mesh, scene):
    return {f.check for f in F.check_mesh(mesh, scene["materials"], F.fabric_table())}


class RigidCushionsAreFlagged(unittest.TestCase):
    def test_rigid_cushion_fails_soft_shape(self):
        sc = real()
        m = next(m for m in sc["meshes"] if m["id"] == "dress-cushion-lounge-sofa-0")
        self.assertIn("soft-shape", checks(m, sc))

    def test_rigid_throw_fails_soft_shape(self):
        sc = real()
        m = next(m for m in sc["meshes"] if m["id"] == "dress-throw-lounge-sofa-0")
        self.assertIn("soft-shape", checks(m, sc))

    def test_carpet_photo_stretched_to_boucle_fails_scale(self):
        sc = real()
        m = next(m for m in sc["meshes"] if m["id"] == "dress-cushion-pb-bed-0")
        found = [f for f in F.check_mesh(m, sc["materials"], F.fabric_table()) if f.check == "scale"]
        self.assertTrue(found, "Carpet016 at 1.7 m reads 10 mm loops; boucle is 3-9 mm")
        self.assertIn("tile_m", found[0].fix)

    def test_rigid_cushion_sinks_into_its_sofa(self):
        found = F.penetration_findings(real())
        self.assertTrue(any(f.object_id == "dress-cushion-lounge-sofa-0" for f in found), found)


class GoodAssetsStayQuiet(unittest.TestCase):
    def test_scanned_pillow_is_not_flagged(self):
        tris = np.load(FIX / "scanned_pillow.npz")["tris"].astype(float)
        mesh = {"id": "dress-pillow-scan-0", "group": "dressing", "material": "m", "faces": tris.tolist()}
        self.assertEqual(F.check_mesh(mesh, {"m": {"kind": "principled", "asset": "x", "tile_m": 1}}, {}), [])
        self.assertGreater(F.crown_spread_deg(tris), 60)

    def test_baked_cushions_are_not_flagged(self):
        sc = real()
        soft_goods.soften_scene(sc)
        for m in sc["meshes"]:
            if m["id"].startswith("dress-cushion"):
                self.assertEqual(checks(m, sc), set(), m["id"])
        self.assertEqual(F.penetration_findings(sc), [])

    def test_baked_throw_is_not_flagged(self):
        sc = real()
        soft_goods.soften_scene(sc)
        m = next(m for m in sc["meshes"] if m["id"].startswith("dress-throw"))
        self.assertEqual(checks(m, sc), set())


def box(x0, x1, y0, y1, z0, z1):
    p = lambda x, y, z: [x, y, z]
    q = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return [[list(q[i]) for i in face] for face in f]


class BoxCheck(unittest.TestCase):
    mats = {"boucle": {"kind": "principled", "asset": "Fabric082A", "tile_m": 1.0}}

    def mesh(self, **kw):
        return dict(id="furn-x-0", group="furniture", material="boucle", part_kind="sofa_3seat", faces=box(0, .8, 0, .8, 0, .4), **kw)

    def test_pure_box_upholstery_flagged(self):
        self.assertIn("box", {f.check for f in F.check_mesh(self.mesh(), self.mats, {})})

    def test_bevelled_box_quiet(self):
        self.assertNotIn("box", {f.check for f in F.check_mesh(self.mesh(bevel_m=0.006), self.mats, {})})

    def test_flat_colour_wood_flagged_but_paint_quiet(self):
        wood = dict(id="furn-d-0", group="furniture", material="walnut", faces=box(0, 1, 0, .5, 0, .7), bevel_m=0.004)
        self.assertIn("flat", {f.check for f in F.check_mesh(wood, {"walnut": {"kind": "principled"}}, {})})
        paint = dict(wood, material="white-paint-joinery")
        self.assertNotIn("flat", {f.check for f in F.check_mesh(paint, {"white-paint-joinery": {"kind": "principled"}}, {})})


class Penetration(unittest.TestCase):
    def test_inside_flagged_resting_quiet(self):
        host = dict(id="furn-h-0", group="furniture", material="m", faces=box(0, 1, 0, 1, 0, .4))
        sunk = dict(id="dress-cushion-h-0", group="dressing", material="m", faces=box(.3, .6, .3, .6, .30, .5))
        rest = dict(id="dress-cushion-h-1", group="dressing", material="m", faces=box(.3, .6, .3, .6, .40, .6))
        self.assertTrue(F.penetration_findings({"meshes": [host, sunk]}))
        self.assertFalse(F.penetration_findings({"meshes": [host, rest]}))

    def test_soft_goods_rest_resolver_lifts_out(self):
        host = dict(id="furn-h-0", group="furniture", material="m", faces=box(0, 1, 0, 1, 0, .4))
        sunk = dict(id="dress-cushion-h-0", group="dressing", material="m", faces=box(.3, .6, .3, .6, .30, .5))
        faces, moved = soft_goods.rest_on_hosts(sunk["faces"], soft_goods.host_shells({"meshes": [host]}))
        self.assertGreaterEqual(moved[2], 0.08)


class Ranking(unittest.TestCase):
    def test_soft_goods_outrank_case_goods(self):
        sc = real()
        found = F.rank(F.check_scene(sc, F.fabric_table()) + F.penetration_findings(sc))
        self.assertEqual(found[0].category, "soft")


class VlmCrop(unittest.TestCase):
    def test_question_names_the_object_and_the_scale(self):
        q = F.vlm_question("scatter cushion")
        self.assertIn("scatter cushion", q)
        self.assertIn("0 = clearly fake", q)

    def test_projection_puts_target_at_centre(self):
        view = {"camera": {"position": [0, 0, 1.2], "target": [5, 0, 1.2], "lens_mm": 24, "sensor_mm": 36}, "resolution": [1600, 1000]}
        uv, z = F.project(view, np.array([[5.0, 0, 1.2]]))
        self.assertAlmostEqual(uv[0][0], 800, delta=1)
        self.assertAlmostEqual(uv[0][1], 500, delta=1)


if __name__ == "__main__":
    unittest.main()
