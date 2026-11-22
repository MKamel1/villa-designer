import copy
import unittest

from archpipe.landscape.plants import library as L
from archpipe.landscape.plants.assets import load_assets, validate_assets


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


if __name__ == "__main__":
    unittest.main()
