"""D1 furniture in 3D: the solids stay inside what the plan checked, and the post-condition catches a model that
differs from the spec (Phase 2)."""
import copy
import unittest

from archpipe.concept import villa_furnish as F
from archpipe.concept import villa_furnish3d as F3
from archpipe.concept import villa_r11 as R

LAY = R.design("D1")
SPEC = F3.spec(LAY)
ITEMS = {it["id"]: it for it in F.layout(LAY)}


def _readback(spec):
    return [{"mark": s["mark"], "category": s["category"], "bbox": list(s["envelope"])} for s in spec]


class Shapes(unittest.TestCase):
    def test_every_piece_is_built_once(self):
        marks = [s["mark"] for s in SPEC]
        self.assertEqual(len(marks), len(set(marks)))
        self.assertEqual({m for m in marks if "#" not in m}, set(ITEMS))

    def test_bodies_stay_in_the_checked_footprint_and_height(self):
        for s in SPEC:
            if s["footprint"] is None:
                continue
            fp = s["footprint"]
            for name, b in zip(s["parts"], s["boxes"]):
                self.assertTrue(fp[0] - 1e-3 <= b[0] and b[3] <= fp[2] + 1e-3 and fp[1] - 1e-3 <= b[1]
                                and b[4] <= fp[3] + 1e-3, (s["mark"], name, b, fp))
                self.assertGreaterEqual(b[2], -1e-6, (s["mark"], name))
                if name not in F3.ABOVE:
                    self.assertLessEqual(b[5], s["h"] + 1e-3, (s["mark"], name, b[5], s["h"]))
            # the plan box of the solids IS the footprint, so the as-built box can be checked against it
            env = s["envelope"]
            self.assertEqual([round(v, 3) for v in (env[0], env[1], env[3], env[4])],
                             [round(v, 3) for v in (fp[0], fp[1], fp[2], fp[3])], s["mark"])

    def test_chairs_and_stools_clear_walls_columns_and_other_pieces(self):
        from archpipe.concept import revit_spec as RS
        sp = RS.build(LAY)
        walls = {lv: F._walls(sp, lv) for lv in ("B", "GF")}
        bodies = [(s["mark"], s["level"], s["footprint"]) for s in SPEC if s["footprint"]]
        for s in SPEC:
            if s["footprint"] is not None:
                continue
            e = s["envelope"]
            plan = (e[0], e[1], e[3], e[4])
            owner = s["mark"].split("#")[0]
            for q in walls[s["level"]] + F._columns():
                self.assertFalse(F._ov(plan, q), (s["mark"], q))
            for m, lv, fp in bodies:
                if lv == s["level"] and m != owner and s["type"] == "chair":
                    self.assertFalse(F._ov(plan, fp), (s["mark"], m))

    def test_a_bunk_bed_has_two_tiers(self):
        s = next(x for x in SPEC if x["mark"] == "ka-bunk")
        self.assertIn("upper-mattress", s["parts"])
        self.assertAlmostEqual(s["envelope"][5], 1.7)


class PostCondition(unittest.TestCase):
    def test_a_model_built_to_spec_passes(self):
        self.assertEqual(F3.postcondition(SPEC, _readback(SPEC), LAY), [])

    def test_a_piece_10_mm_off_is_caught(self):
        rb = _readback(SPEC)
        next(r for r in rb if r["mark"] == "pb-bed")["bbox"][0] += 0.010
        self.assertTrue(any(p.startswith("pb-bed:") for p in F3.postcondition(SPEC, rb, LAY)))

    def test_a_missing_or_doubled_piece_is_caught(self):
        rb = _readback(SPEC)
        rb = [r for r in rb if r["mark"] != "k-island"] + [copy.deepcopy(rb[0])]
        probs = F3.postcondition(SPEC, rb, LAY)
        self.assertIn("k-island: built 0 times", probs)
        self.assertIn("%s: built 2 times" % rb[0]["mark"], probs)

    def test_the_wrong_category_is_caught(self):
        rb = _readback(SPEC)
        next(r for r in rb if r["mark"] == "pe-wc")["category"] = "furniture"
        self.assertTrue(any("pe-wc: category" in p for p in F3.postcondition(SPEC, rb, LAY)))

    def test_the_plan_checks_run_on_what_was_built(self):
        # a wardrobe built 0.3 m out from its wall, into the kids B door's swing
        rb = _readback(SPEC)
        b = next(r for r in rb if r["mark"] == "kb-wardrobe")["bbox"]
        b[0] -= 0.5; b[3] -= 0.5
        probs = F3.postcondition(SPEC, rb, LAY)
        self.assertTrue(any(p.startswith("as built, doors") or p.startswith("as built, routes") for p in probs), probs)


if __name__ == "__main__":
    unittest.main()
