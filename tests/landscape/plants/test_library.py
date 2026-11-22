"""Plant-library validator: positive and negative cases (synthetic) + the shipped data."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from archpipe.landscape.plants import library as L

SRC = {"source_id": "RHS", "url": "https://www.rhs.org.uk/plants/x", "accessed": "2026-11-22",
       "locator": "Key features", "quote": "short verbatim extract"}


def s(value):
    return {"status": "SOURCED", "value": value, "source": dict(SRC)}


def record(**over):
    at = {
        "accepted_name": s({"name": "Genus species L.", "family": "Fam"}),
        "height_m": s({"min": 2, "max": 4}), "spread_m": s({"min": 1, "max": 3}),
        "growth_rate": s({"class": "moderate"}),
        "sun": s({"classes": ["full_sun"], "hours_text": "6+ h"}),
        "water": s({"hydrozone": "low", "text": "low"}),
        "heat": s({"class": "high", "text": "t"}), "drought": s({"class": "high", "text": "t"}),
        "alkaline_soil": s({"class": "tolerant", "text": "t"}), "salt": s({"class": "moderate", "text": "t"}),
        "frost": s({"usda_zone_min": "9b", "min_temp_c": None}),
        "flowering": s({"months": [5], "colours": ["red"]}),
        "foliage": s({"habit": "evergreen", "character": "c"}),
        "root_behaviour": s({"class": "benign", "text": "t"}),
        "toxicity_people": s({"class": "non_toxic", "text": "t"}),
        "toxicity_fish": {"status": "NA", "reason": "not pond-relevant"},
        "litter": s({"leaf": "low", "text": "t"}),
        "maintenance": s({"level": "low", "text": "t"}),
        "egypt_availability": {"status": "POLICY", "value": {"text": "unknown — supplier check"}},
    }
    rec = {"slug": "genus_species", "layers": ["flowering_shrub"], "pond_relevant": False, "attributes": at}
    rec.update(over)
    return rec


class Validator(unittest.TestCase):
    def test_valid_record_passes(self):
        self.assertEqual(L.validate_species(record()), [])

    def test_missing_attribute_fails(self):
        r = record(); del r["attributes"]["salt"]
        self.assertTrue(any("salt: required attribute missing" in e for e in L.validate_species(r)))

    def test_sourced_without_source_fails(self):
        r = record(); del r["attributes"]["heat"]["source"]
        self.assertTrue(any("heat" in e for e in L.validate_species(r)))

    def test_sourced_without_https_url_or_date_fails(self):
        r = record(); r["attributes"]["heat"]["source"].update(url="rhs.org.uk", accessed="yesterday")
        errs = " ".join(L.validate_species(r))
        self.assertIn("url", errs); self.assertIn("accessed", errs)

    def test_bare_value_without_status_fails(self):
        r = record(); r["attributes"]["heat"] = {"value": {"class": "high"}}
        self.assertTrue(L.validate_species(r))

    def test_explicit_gap_passes(self):
        r = record(); r["attributes"]["salt"] = {"status": "GAP", "reason": "no source states it", "searched": ["RHS", "NCSU"]}
        self.assertEqual(L.validate_species(r), [])

    def test_gap_needs_reason_and_searched(self):
        r = record(); r["attributes"]["salt"] = {"status": "GAP"}
        self.assertEqual(len([e for e in L.validate_species(r) if e.startswith("salt")]), 2)

    def test_bad_enum_and_range_fail(self):
        r = record(); r["attributes"]["heat"]["value"]["class"] = "hot-ish"
        r["attributes"]["height_m"]["value"] = {"min": 5, "max": 2}
        errs = L.validate_species(r)
        self.assertTrue(any(e.startswith("heat") for e in errs) and any(e.startswith("height_m") for e in errs))

    def test_quote_too_long_fails(self):
        r = record(); r["attributes"]["heat"]["source"]["quote"] = "x" * 500
        self.assertTrue(any("quote longer" in e for e in L.validate_species(r)))

    def test_fish_toxicity_na_only_when_not_pond_relevant(self):
        r = record(pond_relevant=True)
        self.assertTrue(any("toxicity_fish" in e for e in L.validate_species(r)))
        r["attributes"]["toxicity_fish"] = {"status": "GAP", "reason": "silent", "searched": ["RHS"]}
        self.assertEqual(L.validate_species(r), [])

    def test_na_not_allowed_elsewhere(self):
        r = record(); r["attributes"]["salt"] = {"status": "NA", "reason": "n/a"}
        self.assertTrue(any(e.startswith("salt") for e in L.validate_species(r)))

    def test_availability_cannot_be_guessed(self):
        r = record(); r["attributes"]["egypt_availability"] = {"status": "POLICY", "value": {"text": "widely sold in Cairo"}}
        self.assertTrue(any("egypt_availability" in e for e in L.validate_species(r)))
        r["attributes"]["egypt_availability"] = s({"text": "sold"}); r["attributes"]["egypt_availability"]["source"]["url"] = "held:landscape-timesaver"
        self.assertTrue(any("held book" in e for e in L.validate_species(r)))

    def test_unknown_layer_fails(self):
        self.assertTrue(L.validate_species(record(layers=["meadow"])))


class Viability(unittest.TestCase):
    def test_hardy_heat_tolerant_is_viable(self):
        self.assertEqual(L.site_viability(record())["verdict"], "viable")

    def test_frost_tender_plant_not_viable(self):
        r = record(); r["attributes"]["frost"] = s({"min_temp_c": 10})
        v = L.site_viability(r); self.assertEqual(v["verdict"], "not_viable"); self.assertTrue(v["reasons"])

    def test_marginal_frost_is_conditional(self):
        r = record(); r["attributes"]["frost"] = s({"min_temp_c": 3})
        self.assertEqual(L.site_viability(r)["verdict"], "viable_with_conditions")

    def test_zone_11a_is_conditional_not_viable_silently(self):
        r = record(); r["attributes"]["frost"] = s({"usda_zone_min": "11a"})
        self.assertEqual(L.site_viability(r)["verdict"], "viable_with_conditions")

    def test_low_heat_tolerance_fails_and_alkaline_intolerance_conditional(self):
        r = record(); r["attributes"]["heat"] = s({"class": "low"})
        self.assertEqual(L.site_viability(r)["verdict"], "not_viable")
        r = record(); r["attributes"]["alkaline_soil"] = s({"class": "intolerant"})
        self.assertEqual(L.site_viability(r)["verdict"], "viable_with_conditions")

    def test_gap_gives_unverified_never_viable(self):
        r = record(); r["attributes"]["frost"] = {"status": "GAP", "reason": "r", "searched": ["x"]}
        v = L.site_viability(r)
        self.assertEqual(v["verdict"], "unverified"); self.assertEqual(v["factors"]["frost"], "unknown")

    def test_a_fail_outranks_a_gap(self):
        r = record(); r["attributes"]["frost"] = {"status": "GAP", "reason": "r", "searched": ["x"]}
        r["attributes"]["heat"] = s({"class": "low"})
        self.assertEqual(L.site_viability(r)["verdict"], "not_viable")


class Loader(unittest.TestCase):
    def test_loader_rejects_invalid_file_and_slug_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            bad = record(); del bad["attributes"]["salt"]
            (Path(d) / "genus_species.json").write_text(json.dumps(bad))
            with self.assertRaises(L.SpeciesError):
                L.load_species(Path(d))
            (Path(d) / "genus_species.json").write_text(json.dumps(record(slug="other")))
            with self.assertRaises(L.SpeciesError):
                L.load_species(Path(d))

    def test_loader_accepts_valid(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "genus_species.json").write_text(json.dumps(record()))
            self.assertEqual(list(L.load_species(Path(d))), ["genus_species"])


class ShippedData(unittest.TestCase):
    """The real library: every file valid, enough species, committed plants.json in step with the files."""

    @classmethod
    def setUpClass(cls):
        cls.species = L.load_species()

    def test_every_species_file_valid_and_count(self):
        self.assertGreaterEqual(len(self.species), 50)

    def test_every_layer_of_the_brief_is_covered(self):
        got = {l for r in self.species.values() for l in r["layers"]}
        self.assertEqual(got, L.LAYERS)

    def test_pond_species_have_fish_toxicity_sourced_or_gap(self):
        for slug, r in self.species.items():
            if r["pond_relevant"]:
                self.assertIn(r["attributes"]["toxicity_fish"]["status"], ("SOURCED", "GAP"), slug)

    def test_every_sourced_attribute_was_rechecked_and_failures_are_few(self):
        doc = json.loads((L.DATA / "plants.json").read_text(encoding="utf-8"))
        sourced = [o for r in doc["species"] for o in r["attributes"].values()
                   if isinstance(o, dict) and o.get("status") == "SOURCED" and o["source"]["url"].startswith("https://")]
        self.assertTrue(all("quote_check" in o for o in sourced))
        bad = [o for o in sourced if o["quote_check"] == "quote_not_found"]
        self.assertLessEqual(len(bad), 0.02 * len(sourced))   # the checker flags stitched quotes; keep them rare

    def test_plants_json_matches_species_files(self):
        doc = json.loads((L.DATA / "plants.json").read_text(encoding="utf-8"))
        self.assertEqual([x["slug"] for x in doc["species"]], sorted(self.species))
        for x in doc["species"]:
            self.assertEqual(x["site_viability"], L.site_viability(self.species[x["slug"]]), x["slug"])
        self.assertIn("PLACEHOLDER", doc["site_climate"]["coordinates_status"])


if __name__ == "__main__":
    unittest.main()
