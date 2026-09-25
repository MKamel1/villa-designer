"""Calibration gate for the concept critic (ADR-0016, method step 7).

The critic must stay quiet on published good plans (no false positives),
and each seeded defect must turn a good plan into a failure. The graph half
runs on room graphs read from Mitton & Nystuen (knowledge/precedents/mitton-*);
the geometric half needs a labelled, dimensioned published plan, which no held
book provides yet, so it is skipped with that reason rather than passed.
"""
import copy
import unittest

from archpipe.concept import critic

GRAPH_CHECKS = ("private_access", "wc_access", "reachability")


def _fails(graph):
    return {c["check"] for c in critic.graph_checks(graph) if c["status"] == "fail"}


def _mutations(g):
    """Seeded-bad variants, each a known planning defect, named for the report."""
    out = []
    public = [r for r, k in g["rooms"].items() if k == "public"]
    private = [r for r, k in g["rooms"].items() if k == "private"]
    if public and private:
        m = copy.deepcopy(g)                     # private rooms reached only through a living space
        hub = public[0]
        m["connections"] = [e for e in m["connections"] if not set(e) & set(private)]
        m["connections"] += [[hub, p] for p in private]
        out.append(("private rooms through a public room", m, "private_access"))
    if g["sanitary"] and private:
        m = copy.deepcopy(g)                     # the only WCs entered through a bedroom
        bed = private[0]
        m["connections"] = [e for e in m["connections"] if not set(e) & set(g["sanitary"])]
        m["connections"] += [[bed, s] for s in g["sanitary"]]
        out.append(("WC only through a bedroom", m, "wc_access"))
    leaf = next((r for r in g["rooms"] if r != g["entrance"]), None)
    if leaf:
        m = copy.deepcopy(g)                     # a room with no door
        m["connections"] = [e for e in m["connections"] if leaf not in e]
        out.append(("room with no door", m, "reachability"))
    return out


class GraphCalibration(unittest.TestCase):
    def setUp(self):
        self.records = critic.room_graph_precedents()
        if len(self.records) < 3:
            self.skipTest("fewer than 3 room-graph precedents held")

    def test_quiet_on_every_published_plan(self):
        for rec in self.records:
            with self.subTest(rec["id"]):
                self.assertEqual(_fails(critic.precedent_graph(rec)), set())

    def test_every_seeded_defect_fails_its_check(self):
        n = 0
        for rec in self.records:
            for name, graph, check in _mutations(critic.precedent_graph(rec)):
                with self.subTest(rec["id"], mutation=name):
                    self.assertIn(check, _fails(graph))
                    n += 1
        self.assertGreaterEqual(n, 2 * len(self.records))

    def test_separation(self):
        good = [bool(_fails(critic.precedent_graph(r))) for r in self.records]
        bad = [bool(_fails(g)) for r in self.records for _, g, _ in _mutations(critic.precedent_graph(r))]
        self.assertEqual(sum(good), 0)
        self.assertEqual(sum(bad), len(bad))


class PilotConcepts(unittest.TestCase):
    def test_pilot_pavilion_is_the_one_that_fails(self):
        # independent data authored before the critic: the pilot's pavilion puts the bedroom off the living room
        import json
        pilot = json.loads((critic.ROOT / "knowledge/projects/villa-pilot.json").read_text(encoding="utf-8"))
        got = {c["id"]: _fails(dict(c, sanitary=[])) for c in pilot["concepts"]}
        self.assertEqual(got, {"garden-bar": set(), "courtyard": set(), "pavilion": {"private_access"}})


class GeometryCalibration(unittest.TestCase):
    def test_geometric_checks_against_published_plans(self):
        self.skipTest("not runnable: no labelled, dimensioned published house plan is held (Precedents in "
                      "Architecture plans are unlabelled at print scale; Floor Plan Manual keys rooms by number). "
                      "Generated concepts stay diagnostic until this runs.")


if __name__ == "__main__":
    unittest.main()
