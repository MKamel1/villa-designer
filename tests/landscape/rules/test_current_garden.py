"""Method guard (docs/quality/LANDSCAPE-METHOD.md): the rules must fail the CURRENT garden for real reasons,
and the snapshot must still match the garden code, so the proof cannot go stale."""
import unittest

from archpipe.landscape.rules import evaluate, load
from archpipe.landscape.rules import current_garden as CG

RS = load()


def by(rule, results):
    return [r for r in results if r.criterion == rule]


class CurrentGarden(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layout = CG.load_snapshot()
        cls.results = evaluate(cls.layout, RS)

    def test_capacity_fails_with_numbers(self):
        r = by("LS-CAPACITY", self.results)[0]
        self.assertEqual((r.status, r.achieved, r.required), ("fail", 4, 10))

    def test_all_four_briefed_features_are_missing(self):
        failed = {r.subject for r in by("LS-BRIEF-FEATURES", self.results) if r.status == "fail"}
        self.assertEqual(failed, {"firepit", "bbq", "pond", "herb_bed"})

    def test_frangipani_mature_dripline_reaches_the_facade(self):
        r = by("LS-ROOTZONE", self.results)
        warn = [x for x in r if x.status == "warn"]
        self.assertEqual(len(warn), 1)
        self.assertAlmostEqual(warn[0].achieved, 2.0, delta=0.2)

    def test_what_cannot_be_judged_is_not_a_pass(self):
        for rid in ("LS-HYDROZONE",):
            self.assertTrue(all(r.status == "not_evaluated" for r in by(rid, self.results)))
        self.assertTrue(any(r.status == "not_evaluated" for r in by("LS-SOIL-DEPTH", self.results)))

    def test_quiet_where_the_garden_is_fine(self):       # negative: no false positives
        self.assertTrue(all(r.status == "pass" for r in by("LS-PATH-SECONDARY", self.results)))
        self.assertTrue(all(r.status == "pass" for r in by("LS-SCREEN", self.results)))
        self.assertTrue(all(r.status == "pass" for r in by("LS-ENCLOSURE", self.results)))

    def test_snapshot_matches_the_live_garden(self):
        live = CG.build()
        self.assertEqual(live, self.layout, "garden code changed: rerun `python -m archpipe.landscape.rules.current_garden --write`")


if __name__ == "__main__":
    unittest.main()
