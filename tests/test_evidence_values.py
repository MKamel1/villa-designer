"""Numerical evidence cards: each verified value is enabled, a wrong value or
unit is refused, and -- where the original is held on this machine -- the
value is re-read from the cited page, so a mistyped transcription fails."""
import unittest

from archpipe import guidance as g
from archpipe import sources as src

# card -> (held file, 0-based page index, text that must be on that page)
ORIGINAL = {
    "ukadk-private-stair-rise-max": ("uk-ad-k/Approved_Document_K.pdf", 14, ["Private stair1, 2", "150", "220", "300"]),
    "ukadk-private-stair-going-min": ("uk-ad-k/Approved_Document_K.pdf", 14, ["Private stair1, 2", "220", "300"]),
    "ukadk-private-stair-pitch-max": ("uk-ad-k/Approved_Document_K.pdf", 14, ["maximum pitch for a private stair is 42"]),
    "ukadk-2r-plus-g-min": ("uk-ad-k/Approved_Document_K.pdf", 14, ["between 550mm and 700mm"]),
    "ukadk-2r-plus-g-max": ("uk-ad-k/Approved_Document_K.pdf", 14, ["between 550mm and 700mm"]),
    "ukadk-stair-headroom-min": ("uk-ad-k/Approved_Document_K.pdf", 16, ["Minimum headroom", "At least\n2m"]),
    "ukadm-hall-min-m42": ("uk-ad-m/BR_PDF_AD_M1_2015_with_2016_amendments_V3.pdf", 24,
                           ["minimum clear width of every hall or landing is 900mm"]),
    "ukadm-door-750-corridor-headon": ("uk-ad-m/BR_PDF_AD_M1_2015_with_2016_amendments_V3.pdf", 24,
                                       ["750 or wider\n900 (when approached head on)"]),
    "ukadm-door-750-corridor-side": ("uk-ad-m/BR_PDF_AD_M1_2015_with_2016_amendments_V3.pdf", 24,
                                     ["750\n1200 (when approach is not head-on)"]),
    "ukadm-door-775-corridor-side": ("uk-ad-m/BR_PDF_AD_M1_2015_with_2016_amendments_V3.pdf", 24,
                                     ["775\n1050 (when approach is not head-on)"]),
    "ukadm-door-800-corridor-side": ("uk-ad-m/BR_PDF_AD_M1_2015_with_2016_amendments_V3.pdf", 24,
                                     ["800\n900 (when approach is not head-on)"]),
    "ukadm-entrance-door-min": ("uk-ad-m/BR_PDF_AD_M1_2015_with_2016_amendments_V3.pdf", 14,
                                ["minimum clear opening width of 775mm"]),
}


class NumericalCardTests(unittest.TestCase):
    def setUp(self):
        self.data = g.library()
        self.cards = {k: c for k, c in self.data["evidence"].items() if "verified_value" in c}

    def test_every_numerical_card_has_an_original_page_check(self):
        self.assertEqual(set(self.cards), set(ORIGINAL))

    def test_verified_value_is_enabled_and_wrong_ones_refused(self):
        for key, c in self.cards.items():
            ok = g.numerical_target(c, self.data["sources"], c["verified_value"], c["unit"])
            self.assertTrue(ok["enabled"], (key, ok["reasons"]))
            wrong = g.numerical_target(c, self.data["sources"], c["verified_value"] + 1, c["unit"])
            self.assertFalse(wrong["enabled"], key)
            unit = g.numerical_target(c, self.data["sources"], c["verified_value"], "in")
            self.assertFalse(unit["enabled"], key)

    def test_edition_change_disables_the_card(self):
        c = self.cards["ukadk-stair-headroom-min"]
        sources = dict(self.data["sources"])
        sources["uk-ad-k"] = dict(sources["uk-ad-k"], edition="2025 edition")
        self.assertFalse(g.numerical_target(c, sources, 2000, "mm")["enabled"])

    def test_values_reread_from_the_held_original(self):
        import pymupdf
        missing = []
        for key, (rel, page, needles) in ORIGINAL.items():
            path = src.SOURCES_ROOT / rel
            if not path.is_file():
                missing.append(rel)
                continue
            with pymupdf.open(path) as doc:
                text = doc[page].get_text().replace("\t", " ")
            for n in needles:
                self.assertIn(n, text, f"{key}: '{n}' not on page index {page} of {rel}")
        if missing:
            self.skipTest("originals not held on this machine: " + ", ".join(sorted(set(missing))))


class BriefTargetTests(unittest.TestCase):
    def test_stair_headroom_target_matches_published_minimum(self):
        import json
        req = json.loads((src.ROOT / "knowledge/projects/villa-01/brief-requirements.json").read_text(encoding="utf-8"))
        r = next(x for x in req["requirements"] if x["id"] == "K-STAIR-HEAD")
        self.assertEqual(r["status"], "consistent")
        card = g.library()["evidence"]["ukadk-stair-headroom-min"]
        self.assertEqual(card["verified_value"], 2000)


if __name__ == "__main__":
    unittest.main()
