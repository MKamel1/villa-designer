"""Thermal adapter, the parts that run without EnergyPlus: weather reading,
climate summary against the weather converter's own statistics, the hand
solar-geometry check, and assumption handling. The EnergyPlus runs are
validated on the workstation (`workstation.py thermal --job
spec/thermal/validate.json`); ADR-0017 records the measured result."""
import tempfile
import unittest
import zipfile
from pathlib import Path

from archpipe import sources as src
from archpipe import thermal as t

ZIP = src.SOURCES_ROOT / "cairo-epw" / "EGY_QH_Cairo.West.AP.623680_TMYx.zip"


def _weather():
    if not ZIP.is_file():
        raise unittest.SkipTest("Cairo West weather file not held on this machine")
    d = Path(tempfile.mkdtemp())
    with zipfile.ZipFile(ZIP) as z:
        z.extractall(d)
    return next(d.glob("*.epw")), next(d.glob("*.stat"))


class ClimateTests(unittest.TestCase):
    def test_summary_matches_weather_converter_statistics(self):
        epw, stat = _weather()
        ours = [v["mean_c"] for v in t.climate_summary(epw)["monthly"].values()]
        theirs = t.stat_monthly_means(stat)
        self.assertEqual(len(theirs), 12)
        self.assertLessEqual(max(abs(a - b) for a, b in zip(ours, theirs)), 0.15)

    def test_summary_location_and_ranges(self):
        epw, _ = _weather()
        c = t.climate_summary(epw)
        self.assertEqual(c["location"]["wmo"], "623680")
        self.assertAlmostEqual(c["location"]["lat"], 30.117, places=3)
        self.assertGreater(c["cooling_degree_days_18c"], c["heating_degree_days_18c"])   # a cooling climate
        self.assertGreater(c["hours_above_c"]["28"], c["hours_above_c"]["32"])

    def test_hand_geometry_south_beam_exceeds_north(self):
        epw, _ = _weather()
        north, south = t.hand_vertical_incident(epw, 0), t.hand_vertical_incident(epw, 180)
        self.assertGreater(south["beam"], 10 * north["beam"])
        self.assertAlmostEqual(north["sky"], south["sky"])       # isotropic: same sky on every vertical
        self.assertAlmostEqual(south["total"], south["beam"] + south["sky"] + south["ground"])


class AssumptionTests(unittest.TestCase):
    def test_override_is_recorded_and_defaults_untouched(self):
        a = t._merged({"glass": {"shgc": 0.25}, "wall_u_w_m2k": 0.35})
        self.assertEqual((a["glass"]["shgc"], a["glass"]["u_w_m2k"]), (0.25, 1.8))
        self.assertEqual(t.ASSUMPTIONS["glass"]["shgc"], 0.40)

    def test_validation_asserts_the_model_free_component(self):
        # The hand check can only be exact for direct (beam) radiation; totals
        # differ by the sky model. Guard against someone switching back to
        # totals and loosening the tolerance until it passes.
        job = (src.ROOT / "scripts" / "thermal_job.py").read_text(encoding="utf-8")
        self.assertIn('facade_beam_kwh_m2', job)
        self.assertIn('abs(diff) <= 0.02', job)


if __name__ == "__main__":
    unittest.main()
