"""Guards for the reference-match lane: proposal schema, product sourcing, no reference images."""
import hashlib
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RM = ROOT / "knowledge" / "refmatch"
ROOMS = ("living", "media", "bedroom", "dining")
IMG = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
PRICE_KEYS = re.compile(r"price|cost|eur|usd|gbp|egp|aed|currency|\bvat\b", re.I)
PRICE_TEXT = re.compile(r"[$€£]\s?\d|\b\d[\d,.]*\s?(EGP|USD|EUR|GBP|AED|kr)\b", re.I)


def _rooms():
    return [r for r in ROOMS if (RM / r / "proposals.json").exists()]


def _walk(o):
    if isinstance(o, dict):
        for k, v in o.items():
            yield k, v
            yield from _walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from _walk(v)


class ProposalSchema(unittest.TestCase):
    def test_some_room_delivered(self):
        self.assertTrue(_rooms())

    def test_gaps_and_proposals_shape(self):
        for room in _rooms():
            gaps = json.loads((RM / room / "gaps.json").read_text())
            props = json.loads((RM / room / "proposals.json").read_text())
            self.assertEqual(gaps["room"], room)
            self.assertEqual(props["room"], room)
            ids = {g["id"] for g in gaps["gaps"]}
            self.assertTrue(ids)
            self.assertGreaterEqual(len(gaps["references"]), 2)
            for g in gaps["gaps"]:
                for k in ("id", "rank", "feature", "refs_showing_it", "present_in_scene", "visual_weight"):
                    self.assertIn(k, g, f"{room} gap {g.get('id')}")
                self.assertTrue(g["refs_showing_it"], f"{room} {g['id']} cites no reference")
            for p in props["proposals"]:
                for k in ("id", "gap", "title", "location", "change", "effect", "architecture_change"):
                    self.assertIn(k, p, f"{room} {p.get('id')}")
                self.assertIn(p["gap"], ids)
                loc = p["location"]
                self.assertTrue(loc.get("wall_or_zone") and loc.get("basis"), p["id"])
                self.assertIsInstance(p["architecture_change"]["flag"], bool)
                self.assertTrue(p.get("product") or p.get("lighting_ask"), f"{p['id']} has neither product nor lighting ask")
                if p.get("lighting_ask"):
                    self.assertTrue(p["lighting_ask"].get("effect"), p["id"])
            for m in props["mockup"]["renders"]:
                self.assertTrue((RM / room / m).exists(), m)


class ProductSourcing(unittest.TestCase):
    def test_every_product_has_maker_source_and_no_price(self):
        n = 0
        for room in _rooms():
            props = json.loads((RM / room / "proposals.json").read_text())
            for p in props["proposals"]:
                for prod in ([p["product"]] if p.get("product") else []) + p.get("extra_products", []):
                    n += 1
                    for k in ("maker", "range", "colour_or_finish", "maker_url", "maker_quote"):
                        self.assertTrue(prod.get(k), f"{room} {p['id']} product missing {k}")
                    self.assertRegex(prod["maker_url"], r"^https://")
                    self.assertIn(prod["label"] if "label" in prod else "look-alike-proxy",
                                  ("look-alike-proxy", "manufacturer-supplied", "scan-of-product"))
        self.assertGreater(n, 0)

    def test_no_price_anywhere(self):
        for f in RM.rglob("*.json"):
            data = json.loads(f.read_text())
            for k, v in _walk(data):
                self.assertIsNone(PRICE_KEYS.search(str(k)), f"{f.name}: key {k}")
                if isinstance(v, str):
                    self.assertIsNone(PRICE_TEXT.search(v), f"{f.name}: {v[:60]}")


class NoReferenceImages(unittest.TestCase):
    def test_no_reference_image_hash_under_knowledge(self):
        ref = set(json.loads((RM / "reference-hashes.json").read_text())["sha256"].values())
        self.assertEqual(len(ref), 33)
        for f in (ROOT / "knowledge").rglob("*"):
            if f.is_file() and f.suffix.lower() in IMG:
                self.assertNotIn(hashlib.sha256(f.read_bytes()).hexdigest(), ref, str(f))

    def test_negative_control_detects_a_copy(self):
        # A byte-identical copy must be caught: prove the hash set is not vacuous.
        d = ROOT.parent.parent / "lead" / "docs" / "brief" / "villa_01_guidelines_images"
        if not d.exists():
            self.skipTest("reference directory not present")
        ref = set(json.loads((RM / "reference-hashes.json").read_text())["sha256"].values())
        first = sorted(d.iterdir())[0]
        self.assertIn(hashlib.sha256(first.read_bytes()).hexdigest(), ref)

    def test_mockups_are_small(self):
        for f in RM.rglob("*"):
            if f.suffix.lower() in IMG:
                self.assertLess(f.stat().st_size, 600_000, f.name)


if __name__ == "__main__":
    unittest.main()
