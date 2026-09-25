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
        # the daylight validation keeps its independent checks: sky normalisation and the Lynes formula
        self.assertIn("sky normalisation", job)
        self.assertIn("Lynes", job)


class TM59Tests(unittest.TestCase):
    """CIBSE TM59:2026 criteria (cards tm59-*): anchors, independent running-mean check,
    and each criterion's pass/fail edge."""
    REF = Path(__file__).parent / "data" / "cairo-west-trm-ladybug.json"

    def test_threshold_line_matches_tm59_anchors_and_ladybug_en15251(self):
        import json
        ref = json.loads(self.REF.read_text(encoding="utf-8"))["en15251_cat2_upper_at"]
        for trm in (10, 20, 30):
            self.assertAlmostEqual(t.cat2_threshold(trm), ref[str(trm)], places=6)
        self.assertEqual((t.cat2_threshold(5), t.cat2_threshold(35)), (25.1, 31.7))   # fixed outside 10-30

    def test_running_mean_equals_ladybug_recurrence(self):
        # Ladybug labels each value one day later; the recurrence is identical. Ours follows
        # TM59's text: Trm(1 May) from Trm(30 Apr) and the 30 April daily mean.
        import json, statistics
        epw, _ = _weather()
        db = t.read_epw(epw)["db"]
        days = [statistics.fmean(db[24 * d:24 * d + 24]) for d in range(365)]
        ours = t.running_mean_daily(days)
        lb = json.loads(self.REF.read_text(encoding="utf-8"))["trm"]
        self.assertLess(max(abs(ours[d] - lb[d + 1]) for d in range(t.MAY1, t.OCT1)), 1e-9)

    def _year(self, value):
        return [value] * 8760

    def test_criterion_c_edge(self):
        out = self._year(20.0)
        r = t.tm59(out, self._year(30.0), "living", "mechanical")
        self.assertEqual((r["occupied_hours"], r["limit_hours"]), (1989, 59))    # TM59 Table 2
        for h in range(t.MAY1 * 24 + 9, t.OCT1 * 24):
            if (h % 24) in t.TM59["living_hours"] and sum(1 for x in out if x > 26) < 59:
                out[h] = 26.5
        self.assertTrue(t.tm59(out, self._year(30.0), "living", "mechanical")["pass"])
        h = next(h for h in range(t.MAY1 * 24, t.OCT1 * 24) if (h % 24) in t.TM59["living_hours"] and out[h] <= 26)
        out[h] = 26.5
        self.assertFalse(t.tm59(out, self._year(30.0), "living", "mechanical")["pass"])

    def test_bedroom_limits_and_criterion_b(self):
        r = t.tm59(self._year(20.0), self._year(30.0), "bedroom", "mechanical")
        self.assertEqual((r["occupied_hours"], r["limit_hours"]), (3672, 110))   # TM59 Table 2
        hot = self._year(20.0)
        for d in range(t.MAY1, t.MAY1 + 5):                     # five hot nights
            for h in range(24 * d + 23, 24 * d + 32):
                hot[h] = 27.5
        b = t.tm59(hot, self._year(30.0), "bedroom", "mechanical")["b"]
        self.assertEqual((b["nights"], b["pass"]), (5, False))
        for h in range(24 * (t.MAY1 + 4) + 23, 24 * (t.MAY1 + 4) + 32):
            hot[h] = 20.0
        self.assertTrue(t.tm59(hot, self._year(30.0), "bedroom", "mechanical")["b"]["pass"])

    def test_criterion_a_rounding(self):
        # outdoor constant 30 C -> Trm 30 -> threshold 31.7; dT 0.4 rounds to 0 K, 0.5 to 1 K
        quiet = t.tm59(self._year(31.7 + 0.4), self._year(30.0), "living", "natural")
        loud = t.tm59(self._year(31.7 + 0.5), self._year(30.0), "living", "natural")
        self.assertTrue(quiet["a"]["pass"])
        self.assertFalse(loud["a"]["pass"])


if __name__ == "__main__":
    unittest.main()
