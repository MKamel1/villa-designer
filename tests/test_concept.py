"""Concept generator and geometric critic: unit tests with positive and negative cases.

These prove each check fires on a seeded defect and stays quiet otherwise.
They are not calibration (see test_concept_calibration.py)."""
import copy
import tempfile
import unittest
from pathlib import Path

import yaml

from archpipe import model, rules
from archpipe.concept import critic, generator as G, layout as L


def _status(res, name):
    return next(c["status"] for c in res["checks"] if c["check"] == name)


def _grid(center_occ="study", enclose=True):
    """3 x 3 rooms of 4 m; the centre room is enclosed unless `enclose` is False (north row removed)."""
    rooms = {}
    names = {(0, 0): "store-sw", (1, 0): "entry", (2, 0): "store-se", (0, 1): "store-w", (1, 1): "centre",
             (2, 1): "store-e", (0, 2): "store-nw", (1, 2): "store-n", (2, 2): "store-ne"}
    for (i, j), n in names.items():
        if not enclose and j == 2:
            continue
        occ = {"entry": "entrance", "centre": center_occ}.get(n, "store")
        rooms[n] = {"level": "L00", "rect": [5 + 4 * i, 5 + 4 * j, 9 + 4 * i, 9 + 4 * j], "occupancy": occ}
    links = [["entry", "centre"]] + [["centre", r] for r in rooms if r not in ("entry", "centre")
                                     and critic._overlap(rooms[r]["rect"], rooms["centre"]["rect"]) == 0
                                     and G._touch(rooms[r]["rect"], rooms["centre"]["rect"])]
    return {"id": "grid", "parti": "test", "plot": {"width_m": 30.0, "depth_m": 40.0}, "levels": {"L00": 0.0},
            "rooms": rooms, "links": links, "vertical": [], "entrance": "entry"}


class GeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.areas, cls.available, _ = G.programme()
        cls.best = {p: G.search(p, 300)[:2] for p in ("bar", "L")}

    def test_deterministic(self):
        self.assertEqual(G.build("bar", 7, self.areas), G.build("bar", 7, self.areas))

    def test_best_variants_pass_structural_checks_and_specs_load(self):
        # area_match may fail: the 1.8 m minimum frontage stretches the 6 m2 ground bath (reported, not hidden)
        for parti, (lay, res) in self.best.items():
            with self.subTest(parti):
                self.assertEqual(set(res["fails"]) - {"area_match"}, set())
                with tempfile.TemporaryDirectory() as d:
                    p = model.load(L.write_spec(lay, Path(d) / "c.yaml"))
                    self.assertEqual({r.id for r in p.rooms}, set(lay["rooms"]))

    def test_wet_stack_fails_when_bath_moves_off_the_stack(self):
        lay = copy.deepcopy(self.best["bar"][0])
        r = lay["rooms"]
        r["bath-family"]["rect"], r["bed-2"]["rect"] = r["bed-2"]["rect"], r["bath-family"]["rect"]
        self.assertEqual(_status(critic.critique(lay, self.available), "wet_stack"), "fail")

    def test_living_north_fails_when_living_faces_the_road(self):
        lay = copy.deepcopy(self.best["bar"][0])
        r = lay["rooms"]
        south = next(k for k, v in r.items() if v["level"] == "L00" and v["rect"][1] == r["stair"]["rect"][1]
                     and k not in ("stair", "entry"))
        r["living"]["rect"], r[south]["rect"] = r[south]["rect"], r["living"]["rect"]
        self.assertEqual(_status(critic.critique(lay, self.available), "living_north"), "fail")

    def test_gross_area_fails_over_allowance(self):
        lay, _ = self.best["bar"]
        self.assertEqual(_status(critic.critique(lay, 100), "gross_area"), "fail")
        self.assertEqual(_status(critic.critique(lay, self.available), "gross_area"), "pass")


    def test_upper_room_without_ground_below_fails(self):
        lay = copy.deepcopy(self.best["bar"][0])
        r = lay["rooms"]["bed-2"]["rect"]
        lay["rooms"]["bed-2"]["rect"] = [r[0], r[1], r[2], r[3] + 2.0]      # 2 m past the ground floor
        self.assertEqual(_status(critic.critique(lay), "upper_supported"), "fail")
        self.assertEqual(_status(critic.critique(self.best["bar"][0]), "upper_supported"), "pass")

    def test_stretched_room_fails_area_match(self):
        lay = copy.deepcopy(self.best["bar"][0])
        lay["rooms"]["living"]["target_m2"] = 20
        self.assertIn("living", next(c for c in critic.critique(lay)["checks"] if c["check"] == "area_match")["rooms"])


class GeometryCheckTests(unittest.TestCase):
    def test_enclosed_habitable_room_has_no_window(self):
        self.assertEqual(_status(critic.critique(_grid(enclose=True)), "window"), "fail")
        self.assertEqual(_status(critic.critique(_grid(enclose=False)), "window"), "pass")

    def test_enclosed_store_is_not_flagged(self):
        self.assertEqual(_status(critic.critique(_grid("store", enclose=True)), "window"), "pass")

    def test_link_without_a_shared_wall_is_unbuilt(self):
        g = _grid(enclose=False)
        g["links"].append(["store-sw", "store-se"])            # not touching
        self.assertEqual(_status(critic.critique(g), "links_built"), "fail")
        self.assertEqual(_status(critic.critique(_grid(enclose=False)), "links_built"), "pass")

    def test_outside_the_plot_fails(self):
        g = _grid(enclose=False)
        g["rooms"]["store-se"]["rect"] = [13, 5, 31, 9]
        self.assertEqual(_status(critic.critique(g), "within_plot"), "fail")

    def test_rule_engine_runs_on_emitted_spec(self):
        # negative control: strip the windows and the legacy daylight rule must fire
        lay = G.search("bar", 50)[0]
        with tempfile.TemporaryDirectory() as d:
            path = L.write_spec(lay, Path(d) / "c.yaml")
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            self.assertFalse(any(f["rule"] == "LIGHT-01" for f in critic.rule_findings(path)))
            data["openings"] = [o for o in data["openings"] if o["kind"] != "window"]
            path.write_text(yaml.safe_dump(data), encoding="utf-8")
            self.assertTrue(any(f["rule"] == "LIGHT-01" for f in critic.rule_findings(path)))


if __name__ == "__main__":
    unittest.main()
