"""Product library core: layers follow checks (not_checkable is never a pass),
claims are validated, refreshes never demote, map roles come from the source,
and the swatch check catches a colour-space error. Runs without Blender."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

from archpipe.products import schema, store

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("products_worker", ROOT / "scripts" / "products_worker.py")
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


def item(key, **kw):
    return dict({"id": f"test:{key}", "kind": "appearance", "category": "surface", "source": "test", "key": key,
                 "name": key, "license": "CC0", "tags": [], "styles": [], "data": {}}, **kw)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.lib = Path(tempfile.mkdtemp())
        store.upsert_items([item("a"), item("b"), item("c")], self.lib)

    def layer(self, key):
        return next(r for r in store.search(include_unverified=True, library=self.lib) if r["key"] == key)["layer"]

    def test_only_not_checkable_is_not_verified(self):
        self.assertEqual(store.record_checks("test:a", [{"name": "x", "status": "not_checkable"}], self.lib), "catalogue")
        self.assertEqual(store.search(library=self.lib), [])

    def test_a_failure_wins_over_passes(self):
        store.record_checks("test:b", [{"name": "x", "status": "passed"}, {"name": "y", "status": "failed"}], self.lib)
        self.assertEqual(self.layer("b"), "failed")

    def test_verified_needs_a_pass_and_no_failure(self):
        store.record_checks("test:c", [{"name": "x", "status": "passed"}, {"name": "y", "status": "not_checkable"}], self.lib)
        self.assertEqual([r["key"] for r in store.search(library=self.lib)], ["c"])

    def test_refresh_never_demotes(self):
        store.record_checks("test:c", [{"name": "x", "status": "passed"}], self.lib)
        store.upsert_items([item("c", name="renamed")], self.lib)
        self.assertEqual(self.layer("c"), "verified")

    def test_unknown_state_and_claim_are_refused(self):
        with self.assertRaises(AssertionError):
            store.record_checks("test:a", [{"name": "x", "status": "ok"}], self.lib)
        with self.assertRaises(ValueError):
            store.link("p", "a", "same product", library=self.lib)
        store.link("p", "test:a", "look-alike-proxy", library=self.lib)


class SchemaTests(unittest.TestCase):
    def test_categories_and_styles_from_words(self):
        self.assertEqual(schema.categorise(["American Walnut Veneer", "wood"]), "surface")
        self.assertEqual(schema.categorise(["boucle", "fabric"]), "fabric")
        self.assertEqual(schema.categorise(["potted plant"]), "plant")
        self.assertIn("warm_contemporary", schema.styles_for(["walnut veneer"]))
        self.assertEqual(schema.styles_for(["rusty pipe"]), [])


class WorkerTests(unittest.TestCase):
    def test_source_role_beats_filename(self):
        d = Path(tempfile.mkdtemp())
        for n in ("brown_leather_albedo_2k.jpg", "brown_leather_rough_2k.jpg", "brown_leather_nor_gl_2k.jpg"):
            (d / n).write_bytes(b"x")
        files = [{"name": "brown_leather_albedo_2k.jpg", "role": "base"}]
        maps = worker.find_maps(d, files)
        self.assertEqual(maps["base"].name, "brown_leather_albedo_2k.jpg")
        self.assertEqual(sorted(maps), ["base", "normal", "rough"])
        self.assertIn("base", worker.find_maps(d))      # _albedo_ also recognised by name now

    def test_albedo_is_decoded_as_srgb(self):
        from PIL import Image
        p = Path(tempfile.mkdtemp()) / "grey.png"
        Image.new("RGB", (8, 8), (128, 128, 128)).save(p)
        self.assertAlmostEqual(worker.albedo_stats(p)["mean"], 0.2158, places=3)   # sRGB 128 -> linear 0.216

    def test_swatch_check_catches_the_measured_colour_space_error(self):
        rec = {"albedo": {"mean": 0.3503}}                     # marble_01, Pillow decode
        self.assertEqual(worker.swatch_check(rec, 0.3753)["status"], "passed")   # measured correct render
        self.assertEqual(worker.swatch_check(rec, 0.637)["status"], "failed")    # measured Non-Color render


class LightingAdapterTests(unittest.TestCase):
    def test_luminaires_appear_as_read_only_products(self):
        from archpipe.luminaires import library as lib
        from archpipe.products import lighting
        before = (lib.LIBRARY / "library.sqlite").read_bytes() if (lib.LIBRARY / "library.sqlite").is_file() else None
        rows = lighting.products(limit=5)
        for r in rows:
            self.assertEqual((r["kind"], r["category"]), ("product", "lighting"))
            self.assertTrue(r["id"].startswith("luminaire:"))
        after = (lib.LIBRARY / "library.sqlite").read_bytes() if (lib.LIBRARY / "library.sqlite").is_file() else None
        self.assertEqual(before, after)                  # the adapter never writes the luminaire library


if __name__ == "__main__":
    unittest.main()


class AlbedoLimitTests(unittest.TestCase):
    """Time-Saver p. 1636: hard finishes 0.035-0.90; pile fabrics down to 0.004 (black velour)."""

    def test_hard_and_pile_floors(self):
        from archpipe.products import schema
        self.assertEqual(schema.albedo_limits("surface", "Black marble"), (0.035, 0.90))
        self.assertEqual(schema.albedo_limits("fabric", "Leather brown"), (0.035, 0.90))   # leather is not pile
        self.assertEqual(schema.albedo_limits("fabric", "Black velvet"), (0.004, 0.90))

    def test_worker_uses_the_limits_it_is_given(self):
        import pathlib
        src = (pathlib.Path(__file__).resolve().parents[1] / "scripts" / "products_worker.py").read_text(encoding="utf-8")
        self.assertIn('it.get("albedo_limits")', src)
        self.assertNotIn("0.02 <= st", src)

