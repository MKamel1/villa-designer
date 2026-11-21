"""The daylight option table runs from the measured summaries and orders the options as documented (needs out/villa/daylight)."""
import importlib.util
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUMMARY = Path(r"C:\Users\mmbka\arch-pipeline\out\villa\daylight\summary-r12.json")


@unittest.skipUnless(SUMMARY.is_file(), "daylight summaries not available")
class Daylight(unittest.TestCase):
    def test_table(self):
        spec = importlib.util.spec_from_file_location("daylight_options", HERE / "daylight_options.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules["daylight_options"] = mod
        spec.loader.exec_module(mod)
        from archpipe.model import load
        areas = {e.id[5:]: e.params["net_area_m2"] for e in load("D1") if e.kind == "room"}
        rows = {r["option"][:1]: r for r in mod.table(areas)}
        self.assertEqual(rows["0"]["lounge"], 0.59)                          # the L1 CL2 figure
        self.assertEqual(rows["0"]["kitchen"], 0.33)
        self.assertGreater(rows["1"]["lounge"], rows["0"]["lounge"])         # the implemented option raises the lounge a little
        self.assertLess(rows["1"]["lounge"] - rows["0"]["lounge"], 0.1)      # ... and only a little: glazing is already at its limit
        self.assertEqual(rows["4"]["lounge"], rows["0"]["lounge"])           # blocked rooflight gains nothing


if __name__ == "__main__":
    unittest.main()
