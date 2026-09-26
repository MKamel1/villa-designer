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
    "ukadk-guarding-drop-dwelling": ("uk-ad-k/Approved_Document_K.pdf", 31,
                                     ["in dwellings: provide pedestrian guarding", "falling from a height of more than 600mm"]),
    "ukadk-guarding-height-internal": ("uk-ad-k/Approved_Document_K.pdf", 33, ["Single family dwellings", "900mm for all"]),
    "ukadk-guarding-height-external": ("uk-ad-k/Approved_Document_K.pdf", 33, ["External balconies, including Juliette", "1100mm"]),
    "mh-dwelling-ceiling-min": ("metric-handbook/Buxton - Metric Handbook Planning and Design Data (7th ed, 2022).pdf", 456,
                                ["minimum reasonable ceiling height for domestic buildings", "2.4 m is preferable"]),
    # garage sizes are dimension text inside the drawing, not the text layer: the caption is re-checked, the value was
    # read from the page image (mh-garage-* cards say so)
    "mh-garage-ramp-max": ("metric-handbook/Buxton - Metric Handbook Planning and Design Data (7th ed, 2022).pdf", 785,
                           ["car parking garages are lim", "10 per cent", "15 per cent"]),
    "neufert-private-garage-slope-max": ("neufert/Neufert - Architects' Data (2nd English ed, 1980).pdf", 112,
                                         ["access slope not", "more than 20%", "where unavoidable, slope not more than 20%"]),
    "ies-udi-useful-min": ("ies-handbook/IES - The Lighting Handbook (10th ed, 2011).pdf", 535, ["between 100 and 2000 lux (UDI100-2000)", "insufficient daylight"]),
    "ies-udi-useful-max": ("ies-handbook/IES - The Lighting Handbook (10th ed, 2011).pdf", 535, ["between 100 and 2000 lux (UDI100-2000)", "excessive daylight"]),
    "ies-sda-illuminance": ("ies-handbook/IES - The Lighting Handbook (10th ed, 2011).pdf", 535, ["(typically 300 lux)", "locked-in at 50% of the time"]),
    "ies-sda-area-acceptable": ("ies-handbook/IES - The Lighting Handbook (10th ed, 2011).pdf", 535, ["acceptable when sDA300 > 50%"]),
    "mh-garage-min-width": ("metric-handbook/Buxton - Metric Handbook Planning and Design Data (7th ed, 2022).pdf", 788,
                            ["38.26", "A domestic garage of minimum dimensions"]),
    "mh-garage-min-length": ("metric-handbook/Buxton - Metric Handbook Planning and Design Data (7th ed, 2022).pdf", 788,
                             ["38.26", "A domestic garage of minimum dimensions"]),
    "mh-garage-passenger-width": ("metric-handbook/Buxton - Metric Handbook Planning and Design Data (7th ed, 2022).pdf", 788,
                                  ["38.27", "permitting passenger access"]),
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
    "irc-r304-habitable-area": ("residential-interior-design/Mitton, Nystuen - Residential Interior Design (4th ed, 2021).pdf", 154, ["not less than 70 square feet (6.5 m2)"]),
    "irc-r304-habitable-width": ("residential-interior-design/Mitton, Nystuen - Residential Interior Design (4th ed, 2021).pdf", 154, ["7 feet (2,134 mm) in any horizontal dimension"]),
    "nkba-shower-clear-floor-762": ("nkba-guidelines/NKBA - Kitchen and Bathroom Planning Guidelines with Access Standards (2nd ed).pdf", 99, ["clear floor space of 30″ × 48″ (762 mm × 1219 mm)", "24″ (610 mm) must be planned in front of a shower entry"]),
    "mitton-sofa-coffee-table-457": ("residential-interior-design/Mitton, Nystuen - Residential Interior Design (4th ed, 2021).pdf", 95, ["dimension shown (1) is a minimum and only pos"]),
    "mitton-desk-chair-access-864": ("residential-interior-design/Mitton, Nystuen - Residential Interior Design (4th ed, 2021).pdf", 246, ["10–20 inches (254–508mm) clear space provided in addition to the dimension of chair",
                                                    "24 inches by 24 inches (610 x 610 mm)"]),
    "ukadm-clear-opening-90deg": ("uk-ad-m/BR_PDF_AD_M1_2015_with_2016_amendments_V3.pdf", 58, ["face of the door when open at 90 degrees"]),
    "mitton-tv-uhd-min": ("residential-interior-design/Mitton, Nystuen - Residential Interior Design (4th ed, 2021).pdf", 97, ["1 to 1½ the screen size"]),
    "mitton-tv-uhd-max": ("residential-interior-design/Mitton, Nystuen - Residential Interior Design (4th ed, 2021).pdf", 97, ["1 to 1½ the screen size"]),
    "mh-bathroom-m42-4.30": ("metric-handbook/Buxton - Metric Handbook Planning and Design Data (7th ed, 2022).pdf", 454, ["Accessible and adaptable dwelling bathroom", "Minimum recommended sizes for bathrooms"]),
    "mh-wc-m42-2.61": ("metric-handbook/Buxton - Metric Handbook Planning and Design Data (7th ed, 2022).pdf", 454, ["Accessible and adaptable dwelling WC", "Minimum recommended sizes for bathrooms"]),
    "adb-escape-window-area": ("uk-ad-b1/Approved_Document_B_volume_1_-_Dwellings_2019_edition_incorporating_2020_and_2022_amendments_collated_with_2025_2026_and_2029_amendments.pdf", 26, ["A minimum area of 0.33m2"]),
    "adb-escape-window-min": ("uk-ad-b1/Approved_Document_B_volume_1_-_Dwellings_2019_edition_incorporating_2020_and_2022_amendments_collated_with_2025_2026_and_2029_amendments.pdf", 26, ["A minimum height of 450mm and a minimum width of 450mm"]),
    "adb-escape-window-sill": ("uk-ad-b1/Approved_Document_B_volume_1_-_Dwellings_2019_edition_incorporating_2020_and_2022_amendments_collated_with_2025_2026_and_2029_amendments.pdf", 26, ["bottom of the openable area is a maximum of 1100mm above the floor"]),
    "adb-inner-room-storey-max": ("uk-ad-b1/Approved_Document_B_volume_1_-_Dwellings_2019_edition_incorporating_2020_and_2022_amendments_collated_with_2025_2026_and_2029_amendments.pdf", 26, ["a maximum of 4.5m above ground level which is provided with an emergency escape window"]),
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
    "tss-reflectance-table": ("time-saver-interior/DeChiara, Panero, Zelnik - Time-Saver Standards for Interior Design and Space Planning (2nd ed).pdf", 1656, ["Dull or flat white 75–90", "Ultramarine blue 3.5", "Black velour 0.4"]),
    "aecom-villa-rates-2025": ("aecom-meh-2026/MEH 2026 Digital.pdf", 119, ["Villas 1,700 3,000 1,300 2,600 1,300 2,600 1,000 1,800"]),
    "mitton-foyer-transition": ("residential-interior-design/Mitton, Nystuen - Residential Interior Design (4th ed, 2021).pdf", 68, ["as a transition space from outside to inside"]),
    "mitton-air-lock-buffer": ("residential-interior-design/Mitton, Nystuen - Residential Interior Design (4th ed, 2021).pdf", 70, ["an air lock will serve as a buffer between outside and inside air"]),
    "ching-view-framing": ("form-space-order/Ching - Architecture Form Space and Order (5th ed, 2023).pdf", 228, ["frame a view so that we see it as a painting on a wall"]),
    "ukadm-furniture-layout-demonstrable": ("uk-ad-m/BR_PDF_AD_M1_2015_with_2016_amendments_V3.pdf", 25, ["It can be demonstrated (for example by providing dimensioned bedroom layouts"]),
    "adb-inner-room-2-11": ("uk-ad-b1/Approved_Document_B_volume_1_-_Dwellings_2019_edition_incorporating_2020_and_2022_amendments_collated_with_2025_2026_and_2029_amendments.pdf", 26, ["An inner room is permitted when it is one of the following"]),
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
        self.assertTrue(p["MIN_AREA_M2.living"]["verified"])         # IRC R304.1 floor, 2026-09-25
        self.assertTrue(p["MIN_AREA_M2.bathroom"]["verified"])       # Metric Handbook Fig. 22.12d (M4(2))
        self.assertNotIn("MIN_AREA_M2.kitchen", p)                   # IRC excepts kitchens
        self.assertEqual(rows["AREA-01"]["status"], "verified")
        # only rules whose every number is verified AND whose mapping is complete; CIRC-03 by client decision 2026-09-25
        self.assertEqual({k for k, r in rows.items() if r["enabled_for_approval"]}, {"CIRC-03", "LIGHT-01", "SAN-01", "DOOR-01", "DIM-01", "FURN-02", "DOOR-02", "TV-01", "AREA-01", "FIRE-01", "CIRC-02", "VIEW-01", "FURN-01", "FURN-03"})

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
