"""The source point must come from the fitting's geometry, not its insertion point."""
import json
import unittest
from pathlib import Path

from archpipe.fixture_source import source_point

ROOT = Path(__file__).resolve().parents[1]
# The fixture meshes of the model built BEFORE the fix, frozen so the
# reproduction survives rebuilds (the live extract now emits at spec).
PRE_FIX = Path(__file__).resolve().parent / "data/bedroom-fixture-meshes-pre-fix.json"


def box(z0, z1, name="Matte Black", role="physical", x=(0, 100), y=(0, 100)):
    return {"geometry_role": role, "material": {"name": name},
            "vertices_mm": [[x[0], y[0], z0], [x[1], y[1], z1]]}


class SourcePointTests(unittest.TestCase):
    def test_symbol_apex_wins(self):
        meshes = [box(1633, 2243, "Revit unspecified", "light_source_symbol"),
                  box(2244, 2246, "Lens Glass"), box(2243, 2548)]
        self.assertEqual(source_point(meshes), (50.0, 50.0, 2243, "light_source_symbol apex"))

    def test_lens_centre_without_symbol(self):
        x, y, z, basis = source_point([box(1920, 2250, "Shade"), box(1932, 1935, "Lens -White")])
        self.assertEqual((z, basis), (1933.5, "lens centre"))

    def test_no_evidence_is_none(self):
        self.assertIsNone(source_point([box(2243, 2548)]))

    def test_real_bedroom_fixtures(self):
        """The measured emitters of the real pre-fix model (the defect's reproduction):
        insertion heights 2000/2400/2400 were what every consumer used."""
        data = json.loads(PRE_FIX.read_text(encoding="utf-8"))
        got = {k: source_point(meshes) for k, meshes in data.items()}
        self.assertAlmostEqual(got["LT-02"][2], 2243, delta=2)   # drum: symbol apex
        self.assertAlmostEqual(got["LT-01"][2], 1933.5, delta=2)  # cone: lens, inside the shade
        self.assertAlmostEqual(got["LT-04"][2], 2600, delta=2)    # linear: lens at the ceiling
        for k in data:
            self.assertIsNotNone(got[k], k)


if __name__ == "__main__":
    unittest.main()
