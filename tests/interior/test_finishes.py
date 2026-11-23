"""Finish palettes: schedule schema, maker source, no price, labelled look-alikes, derived texture scale."""
import copy
import json
import unittest
from pathlib import Path

from archpipe.interior import finishes as F

ROOT = Path(__file__).resolve().parents[2]
PALETTES = [p for p in "ABC" if (F.PALETTE_DIR / f"{p}.json").exists()]


def good_item():
    return {"id": "A-floor-living", "slot": "floor-living", "group": "hard", "use": "living",
            "product": {"maker": "M", "range": "R", "colour_code": "X1", "format_mm": {"w": 600, "l": 1200, "t": 12},
                        "finish": "honed", "lrv": 55, "lrv_source": "maker page"},
            "source": {"url": "https://example.com/p", "quote": "verbatim"},
            "egypt": {"available": False, "gap": "no Egypt distributor cited"},
            "lookalike": {"label": "look-alike-proxy", "maker_site": "ambientCG", "id": "Travertine001",
                          "url": "https://ambientcg.com/view?id=Travertine001", "licence": "CC0", "on_disk": True,
                          "physical_scan_mm": None}}


class SyntheticRules(unittest.TestCase):
    def test_good_item_clean(self):
        self.assertEqual(F.item_problems(good_item()), [])

    def test_missing_maker_source_is_a_problem(self):
        it = good_item(); it["source"]["quote"] = ""
        self.assertTrue(any("maker source" in p for p in F.item_problems(it)))

    def test_price_key_anywhere_is_refused(self):
        for key in ("price_egp", "unit_cost"):
            it = good_item(); it["product"]["extra"] = {key: 5}
            self.assertTrue(any("price-like key" in p for p in F.item_problems(it)), key)

    def test_unlabelled_lookalike_refused(self):
        it = good_item(); it["lookalike"]["label"] = "exact"
        self.assertTrue(any("not labelled" in p for p in F.item_problems(it)))

    def test_non_open_licence_refused(self):
        it = good_item(); it["lookalike"]["licence"] = "Royalty-free"
        self.assertTrue(any("licence" in p for p in F.item_problems(it)))

    def test_egypt_gap_must_be_marked(self):
        it = good_item(); it["egypt"] = {"available": False}
        self.assertTrue(any("no gap" in p for p in F.item_problems(it)))

    def test_texture_scale_from_format(self):
        self.assertEqual(F.texture_scale_m(good_item()), (1.2, "format-long-side"))
        it = good_item(); it["product"]["format_mm"] = {"w": 600, "l": 600}
        self.assertEqual(F.texture_scale_m(it)[0], 0.6)

    def test_texture_scale_falls_back_to_published_scan_size(self):
        it = good_item(); it["slot"] = "joinery-timber"; it["product"]["format_mm"] = None
        it["lookalike"]["physical_scan_mm"] = [1000, 1000]
        self.assertEqual(F.texture_scale_m(it), (1.0, "lookalike-scan-size"))

    def test_range_format_uses_longest_published_side(self):
        it = good_item(); it["product"]["format_mm"] = {"w": 242, "l": "1750-2350"}
        self.assertEqual(F.texture_scale_m(it)[0], 2.35)

    def test_small_format_on_large_scan_uses_scan_size(self):
        it = good_item(); it["product"]["format_mm"] = {"w": 100, "l": 100}; it["lookalike"]["physical_scan_mm"] = [2000, 2000]
        self.assertEqual(F.texture_scale_m(it), (2.0, "lookalike-scan-size"))

    def test_negative_scale_is_never_assumed(self):
        it = good_item(); it["slot"] = "joinery-timber"; it["product"]["format_mm"] = None
        with self.assertRaises(ValueError):
            F.texture_scale_m(it)
        self.assertTrue(any("texture scale cannot be derived" in p for p in F.item_problems(it)))

    def test_lrv_needs_source(self):
        it = good_item(); it["product"]["lrv_source"] = None
        self.assertTrue(any("lrv_source" in p for p in F.item_problems(it)))


@unittest.skipUnless(PALETTES, "no palette files yet")
class RealPalettes(unittest.TestCase):
    def test_every_palette_is_clean(self):
        for pid in PALETTES:
            pal = F.load_palette(pid)
            self.assertEqual(F.palette_problems(pal), [], pid)

    def test_schedule_covers_required_slots_and_sofas(self):
        need = {"floor-living", "floor-wet", "bath-tile", "worktop", "backsplash", "joinery-timber", "door",
                "wall-paint"}
        for pid in PALETTES:
            slots = {i["slot"] for i in F.load_palette(pid)["items"]}
            self.assertFalse(need - slots, f"{pid} missing {need - slots}")

    def test_no_price_text_in_file(self):
        for pid in PALETTES:
            txt = (F.PALETTE_DIR / f"{pid}.json").read_text().lower()
            for bad in ("price_egp", '"price"', '"cost"'):
                self.assertNotIn(bad, txt)

    def test_every_hard_item_scale_derives_from_product(self):
        for pid in PALETTES:
            for it in F.load_palette(pid)["items"]:
                if it.get("lookalike"):
                    tm, basis = F.texture_scale_m(it)
                    self.assertGreater(tm, 0)
                    if basis == "format-long-side":
                        fmt = it["product"]["format_mm"]
                        self.assertEqual(tm, max(F._mm(fmt.get("w")) or 0, F._mm(fmt.get("l")) or 0) / 1000)


if __name__ == "__main__":
    unittest.main()
