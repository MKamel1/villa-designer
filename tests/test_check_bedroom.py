"""check_bedroom's fixture-source guard, proven on the REAL pre-fix fitting meshes."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_bedroom as cb                                     # noqa: E402

PRE_FIX = json.loads((ROOT / "tests/data/bedroom-fixture-meshes-pre-fix.json").read_text(encoding="utf-8"))


def shifted(meshes, dz):
    return [dict(m, vertices_mm=[[v[0], v[1], v[2] + dz] for v in m["vertices_mm"]]) for m in meshes]


def rows(lt, meshes):
    c = cb.Check()
    cb.check_light_source(c, lt, meshes, 2700.0)
    return {label.strip().split(" ", 1)[1]: ok for ok, label, _ in c.rows}


class FixtureSourceGuard(unittest.TestCase):
    def test_insertion_height_model_fails(self):
        """The model that passed the old circular check: drum emitter at 2243 vs spec 2000."""
        r = rows({"id": "LT-02", "at": [1725, 3300], "mounting_height": 2000}, PRE_FIX["LT-02"])
        self.assertFalse(r["light source height"])

    def test_emitter_at_spec_passes(self):
        lt = {"id": "LT-02", "at": [1725, 3300], "mounting_height": 2000}
        r = rows(lt, shifted(PRE_FIX["LT-02"], -243))
        self.assertTrue(r["light source height"])

    def test_forcing_an_impossible_height_fails_the_ceiling(self):
        """LT-01 moved to the old 2400 spec: shade top at ~3167 with this cord, above 2700."""
        lt = {"id": "LT-01", "at": [2100, 1800], "mounting_height": 2400}
        r = rows(lt, shifted(PRE_FIX["LT-01"], 467))
        self.assertTrue(r["light source height"])
        self.assertFalse(r["housing below the ceiling"])

    def test_recessed_body_above_the_ceiling_is_a_note_not_a_fail(self):
        """Measured on Signify CoreLine: body top 2732 over a 2700 ceiling, by design."""
        body = [{"geometry_role": "physical", "material": {"name": "Laminate, White"},
                 "vertices_mm": [[1850, 1400, 2688], [2150, 2600, 2732]]},
                {"geometry_role": "physical", "material": {"name": "Glass, White, High Luminance"},
                 "vertices_mm": [[1947, 1442, 2699], [2052, 2557, 2700]]}]
        c = cb.Check()
        cb.check_light_source(c, {"id": "LT-01", "at": [2000, 2000], "mounting_height": 2700,
                                  "product": {"mount": "recessed"}}, body, 2700.0)
        self.assertEqual([ok for ok, label, _ in c.rows if "ceiling" in label], [None])   # a NOTE
        c = cb.Check()
        cb.check_light_source(c, {"id": "LT-01", "at": [2000, 2000], "mounting_height": 2700}, body, 2700.0)
        self.assertEqual([ok for ok, label, _ in c.rows if "ceiling" in label], [False])  # a pendant would clash


if __name__ == "__main__":
    unittest.main()
