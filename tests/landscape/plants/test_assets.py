import copy
import unittest

from archpipe.landscape.plants import library as L
import json
import tempfile
from pathlib import Path

from archpipe.landscape.plants.assets import gltf_untextured_share, load_assets, validate_assets, validate_manifest


class AssetTable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc, cls.slugs = load_assets(), list(L.load_species())

    def test_shipped_table_valid(self):
        self.assertEqual(validate_assets(self.doc, self.slugs), [])

    def test_every_species_has_a_row_and_unmatched_ones_are_not_drawable(self):
        rows = {r["slug"]: r for r in self.doc["species"]}
        self.assertEqual(set(rows), set(self.slugs))
        self.assertGreater(sum(r["drawable"] == "not drawable yet" for r in rows.values()), 50)

    def test_drawable_without_a_good_asset_fails(self):
        d = copy.deepcopy(self.doc)
        row = next(r for r in d["species"] if r["drawable"] == "not drawable yet")
        row["drawable"] = "drawable"
        self.assertTrue(any("without a grade A/B" in e for e in validate_assets(d, self.slugs)))

    def test_good_asset_marked_not_drawable_fails(self):
        d = copy.deepcopy(self.doc)
        next(r for r in d["species"] if r["slug"] == "jacaranda_mimosifolia")["drawable"] = "not drawable yet"
        self.assertTrue(any("marked not drawable" in e for e in validate_assets(d, self.slugs)))

    def test_grade_c_asset_never_makes_a_species_drawable(self):
        rows = {r["slug"]: r for r in self.doc["species"]}
        self.assertEqual(rows["olea_europaea"]["grade"], "C")
        self.assertEqual(rows["olea_europaea"]["drawable"], "not drawable yet")

    def test_look_alike_cannot_map_to_species_and_missing_preview_fails(self):
        d = copy.deepcopy(self.doc)
        a = next(x for x in d["assets"] if x["species_fit"] == "look-alike")
        a["maps_to"] = ["olea_europaea"]; a["preview"] = "asset-previews/nope.jpg"
        e = " ".join(validate_assets(d, self.slugs))
        self.assertIn("look-alike", e); self.assertIn("preview file missing", e)

    def test_grade_without_looked_at_fails(self):
        d = copy.deepcopy(self.doc)
        d["assets"][0]["rationale"] = "fine"
        self.assertTrue(any("Looked at" in e for e in validate_assets(d, self.slugs)))


class PassTwoGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc, cls.slugs = load_assets(), list(L.load_species())

    def test_misnamed_jacaranda_is_a_look_alike_that_maps_to_nothing(self):
        a = next(x for x in self.doc["assets"] if x["id"] == "jacaranda_tree")
        self.assertEqual(a["misnamed_as"], "jacaranda_mimosifolia"); self.assertEqual(a["maps_to"], [])
        d = copy.deepcopy(self.doc); next(x for x in d["assets"] if x["id"] == "jacaranda_tree")["maps_to"] = ["jacaranda_mimosifolia"]
        self.assertTrue(any("misnamed" in e for e in validate_assets(d, self.slugs)))

    def test_untextured_asset_above_grade_d_fails(self):
        d = copy.deepcopy(self.doc)
        a = next(x for x in d["assets"] if x["id"] == "skf_fd421074"); self.assertEqual(a["grade"], "D")
        a["grade"] = "B"
        self.assertTrue(any("renders white" in e for e in validate_assets(d, self.slugs)))

    def test_untextured_share_measured_from_gltf(self):
        with tempfile.TemporaryDirectory() as t:
            bare, tex = Path(t, "bare.gltf"), Path(t, "tex.gltf")
            bare.write_text(json.dumps({"materials": [{"pbrMetallicRoughness": {"metallicFactor": 0}}]}))
            tex.write_text(json.dumps({"materials": [{"pbrMetallicRoughness": {"baseColorTexture": {"index": 0}}}]}))
            self.assertEqual(gltf_untextured_share(bare), 1.0)
            self.assertEqual(gltf_untextured_share(tex), 0.0)   # negative: a textured asset is not flagged
        banana = Path.home() / "archpipe/library/sketchfab/fd4210743fb644d0a2c5452637ffc5d4/gltf/scene.gltf"
        if banana.is_file():
            self.assertEqual(gltf_untextured_share(banana), 1.0)

    def test_non_free_licence_fails(self):
        d = copy.deepcopy(self.doc); d["assets"][0]["licence"] = "Royalty Free Store License"
        self.assertTrue(any("not a free licence" in e for e in validate_assets(d, self.slugs)))

    def test_shared_assets_are_pinned_in_the_manifest(self):
        m = json.loads((L.DATA / "asset-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(validate_manifest(self.doc, m), [])
        m2 = copy.deepcopy(m); k = next(iter(m2["assets"])); m2["assets"][k][0]["sha256"] = "abc"
        self.assertTrue(validate_manifest(self.doc, m2))
        self.assertTrue(validate_manifest(self.doc, {"assets": {}}))

    def test_manifest_hashes_match_the_files_when_the_store_exists(self):
        import hashlib
        root = Path.home() / "archpipe/shared/assets/user/landscape/polyhaven"
        if not root.is_dir():
            self.skipTest("shared asset store not on this machine")
        m = json.loads((L.DATA / "asset-manifest.json").read_text(encoding="utf-8"))
        for key, files in m["assets"].items():
            for f in files:
                self.assertEqual(hashlib.sha256((root / key.split("/")[1] / f["file"]).read_bytes()).hexdigest(), f["sha256"], f["file"])

    def test_ixora_asset_no_longer_maps_to_a_species(self):
        self.assertEqual(next(x for x in self.doc["assets"] if x["id"] == "sf_ixora")["maps_to"], [])
    def test_gazania_is_drawable_only_via_a_drift_test(self):
        a = next(x for x in self.doc["assets"] if x["id"] == "ph_flower_gazania")
        self.assertIn("DRIFT TEST", a["rationale"]); self.assertTrue((L.DATA / a["drift_preview"]).is_file())


if __name__ == "__main__":
    unittest.main()
