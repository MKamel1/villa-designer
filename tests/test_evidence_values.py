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
    "ndss-single-bedroom-area": ("metric-handbook/Buxton - Metric Handbook Planning and Design Data (7th ed, 2022).pdf", 447,
                                 ["single bedroom has a floor area of at least 7.5 m2"]),
    "ndss-single-bedroom-width": ("metric-handbook/Buxton - Metric Handbook Planning and Design Data (7th ed, 2022).pdf", 447,
                                  ["is at least 2.15 m wide"]),
    "ndss-double-bedroom-area": ("metric-handbook/Buxton - Metric Handbook Planning and Design Data (7th ed, 2022).pdf", 447,
                                 ["has a floor area of at least 11.5 m2"]),
    "ndss-first-double-bedroom-width": ("metric-handbook/Buxton - Metric Handbook Planning and Design Data (7th ed, 2022).pdf", 447,
                                        ["is at least 2.75 m wide"]),
    "ndss-other-double-bedroom-width": ("metric-handbook/Buxton - Metric Handbook Planning and Design Data (7th ed, 2022).pdf", 447,
                                        ["at least 2.55 m wide"]),
    "tm59-crit-a-cat2-floor": ("cibse-tm59/TM59 Overheating risk in dwellings - a design stage methodology (2026).pdf", 14, ["25.1 °C for Category II dwellings"]),
    "tm59-crit-a-cat2-cap": ("cibse-tm59/TM59 Overheating risk in dwellings - a design stage methodology (2026).pdf", 14, ["31.7 °C for Category II dwellings"]),
    "tm59-exceed-3pct": ("cibse-tm59/TM59 Overheating risk in dwellings - a design stage methodology (2026).pdf", 14, ["shall not be more than 3% of the occupied hours"]),
    "tm59-crit-b-4-nights": ("cibse-tm59/TM59 Overheating risk in dwellings - a design stage methodology (2026).pdf", 15, ["shall not be more than four nights"]),
    "tm59-crit-b-tn-cat2": ("cibse-tm59/TM59 Overheating risk in dwellings - a design stage methodology (2026).pdf", 16, ["for Category II dwelling the operative temperature threshold, Tn, is 27 °C"]),
    "tm59-crit-c-26": ("cibse-tm59/TM59 Overheating risk in dwellings - a design stage methodology (2026).pdf", 15, ["shall not exceed 26 °C"]),
    "ukadm-bed-principal-750": ("uk-ad-m/BR_PDF_AD_M1_2015_with_2016_amendments_V3.pdf", 25, ["750mm wide to both sides and the foot of the bed"]),
    "ukadm-bed-other-double-750": ("uk-ad-m/BR_PDF_AD_M1_2015_with_2016_amendments_V3.pdf", 25, ["750mm wide to one side and the foot of the bed"]),
    "ukadm-bed-single-750": ("uk-ad-m/BR_PDF_AD_M1_2015_with_2016_amendments_V3.pdf", 25, ["750mm wide to one side of each bed"]),
    "ukadm-wc-access-zone-1100": ("uk-ad-m/BR_PDF_AD_M1_2015_with_2016_amendments_V3.pdf", 27, ["WC access zone", "1100mm"]),
    "ukadm-basin-access-zone-1100": ("uk-ad-m/BR_PDF_AD_M1_2015_with_2016_amendments_V3.pdf", 27, ["1100mm", "700mm"]),
    "ukadm-bath-access-zone-700": ("uk-ad-m/BR_PDF_AD_M1_2015_with_2016_amendments_V3.pdf", 27, ["700mm", "1100mm"]),
    "tss-front-of-storage-914": ("time-saver-interior/DeChiara, Panero, Zelnik - Time-Saver Standards for Interior Design and Space Planning (2nd ed).pdf", 107, ["36 in in front of dresser, closet, and chest of drawers"]),
    "tss-dining-chair-access-813": ("time-saver-interior/DeChiara, Panero, Zelnik - Time-Saver Standards for Interior Design and Space Planning (2nd ed).pdf", 101, ["32 in for chair plus access thereto"]),
    "irc-r303-glazing-8pct": ("residential-interior-design/Mitton, Nystuen - Residential Interior Design (4th ed, 2021).pdf", 103,
                              ["not less than 8 percent of the floor area"]),
    "mitton-path-of-travel-min": ("residential-interior-design/Mitton, Nystuen - Residential Interior Design (4th ed, 2021).pdf", 79,
                                  ["paths of travel must be a minimum of", "36 inches (914 mm) wide"]),
    "nkba-work-aisle-one-cook": ("nkba-kitchen-guidelines-free/NKBA - Kitchen Planning Guidelines with Access Standards (free edition).pdf", 5, ["work aisle should be at least 42″ (1067 mm) for one cook"]),
    "nkba-work-aisle-multi-cook": ("nkba-kitchen-guidelines-free/NKBA - Kitchen Planning Guidelines with Access Standards (free edition).pdf", 5, ["at least 48″ (1219 mm) for multiple cooks"]),
    "nkba-walkway-min": ("nkba-kitchen-guidelines-free/NKBA - Kitchen Planning Guidelines with Access Standards (free edition).pdf", 7, ["width of a walkway should be at least 36″ (914 mm)"]),
    "nkba-walkway-perpendicular": ("nkba-kitchen-guidelines-free/NKBA - Kitchen Planning Guidelines with Access Standards (free edition).pdf", 7, ["one walkway should be at least 42″ (1067 mm) wide"]),
    "nkba-seating-no-traffic": ("nkba-kitchen-guidelines-free/NKBA - Kitchen Planning Guidelines with Access Standards (free edition).pdf", 7, ["allow 32″ (813 mm) of clearance"]),
    "nkba-dishwasher-to-sink-max": ("nkba-kitchen-guidelines-free/NKBA - Kitchen Planning Guidelines with Access Standards (free edition).pdf", 14, ["dishwasher within 36″ (914 mm) of the nearest edge"]),
    "nkba-dishwasher-standing-space": ("nkba-kitchen-guidelines-free/NKBA - Kitchen Planning Guidelines with Access Standards (free edition).pdf", 14, ["(533 mm) of standing space"]),
    "sll-min-adf-bedroom": ("sll-code/SLL - Code for Lighting (2012).pdf", 127, ["Table 5.2 Minimum average daylight factor", "Bedrooms 1.0"]),
    "sll-min-adf-living": ("sll-code/SLL - Code for Lighting (2012).pdf", 127, ["Table 5.2 Minimum average daylight factor", "Living rooms 1.5"]),
    "sll-min-adf-kitchen": ("sll-code/SLL - Code for Lighting (2012).pdf", 127, ["Table 5.2 Minimum average daylight factor", "Kitchens 2.0"]),
    "ukadm-entrance-door-min": ("uk-ad-m/BR_PDF_AD_M1_2015_with_2016_amendments_V3.pdf", 14,
                                ["minimum clear opening width of 775mm"]),
}

# Presence cards (no number): the requirement text is re-read from the original too.
PRESENCE = {
    "ukadg-dwelling-wc-entrance-storey": ("uk-ad-g/ADG_with_2024_amendments.pdf", 30,
                                          ["least one sanitary convenience", "principal/"]),
    "ukadm-wc-entrance-or-principal-storey": ("uk-ad-m/BR_PDF_AD_M1_2015_with_2016_amendments_V3.pdf", 15,
                                              ["where there are no habitable rooms on the entrance storey, on the principal storey"]),
    "ukadg-dwelling-bathroom": ("uk-ad-g/ADG_with_2024_amendments.pdf", 34, ["at least one bathroom with a fxed bath or shower"]),
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
        for key, (rel, page, needles) in {**ORIGINAL, **PRESENCE}.items():
            path = src.SOURCES_ROOT / rel
            if not path.is_file():
                missing.append(rel)
                continue
            with pymupdf.open(path) as doc:
                text = " ".join(doc[page].get_text().split())   # layout whitespace is not content
            for n in needles:
                self.assertIn(" ".join(n.split()), text, f"{key}: '{n}' not on page index {page} of {rel}")
        if missing:
            self.skipTest("originals not held on this machine: " + ", ".join(sorted(set(missing))))


class RuleAuditTests(unittest.TestCase):
    """The audit reports what the rule engine actually uses, against verified cards."""

    def test_verified_bedroom_areas_are_the_values_in_use(self):
        rows = {r["id"]: r for r in g.rule_audit()}
        p = rows["AREA-01"]["parameters"]
        self.assertTrue(p["MIN_AREA_M2.bedroom"]["verified"])
        self.assertEqual(p["MIN_AREA_M2.bedroom"]["used"], 11.5)
        self.assertFalse(p["MIN_AREA_M2.living"]["verified"])
        self.assertEqual(rows["AREA-01"]["status"], "partly verified")
        # only rules whose every number is verified AND whose mapping is complete; CIRC-03 by client decision 2026-09-25
        self.assertEqual({k for k, r in rows.items() if r["enabled_for_approval"]}, {"CIRC-03", "LIGHT-01", "SAN-01", "DOOR-01"})

    def test_a_changed_catalogue_value_unverifies_the_parameter(self):
        from archpipe import catalogue as cat
        old = cat.MIN_AREA_M2["bedroom"]
        try:
            cat.MIN_AREA_M2["bedroom"] = (12.0, old[1])
            p = {r["id"]: r for r in g.rule_audit()}["AREA-01"]["parameters"]["MIN_AREA_M2.bedroom"]
            self.assertFalse(p["verified"])
        finally:
            cat.MIN_AREA_M2["bedroom"] = old

    def test_map_values_match_the_engine(self):
        import json
        m = json.loads((src.ROOT / "knowledge/rule-evidence.json").read_text(encoding="utf-8"))["rules"]
        for rule, entry in m.items():
            for key, p in entry["parameters"].items():
                self.assertEqual(g.catalogue_value(key), p["value"], f"{rule} {key}")


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
