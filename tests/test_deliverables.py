"""W6 deliverables: schedules, quantities, relative cost and IFC, checked against the spec they come from.

The IFC test reads the written file back through the IfcOpenShell geometry engine (an independent code
path) and compares every space and wall with the spec. It exists because the first export was 1000x too
large (the api's representation helpers take SI metres) and passed every count check."""
import math
import tempfile
import unittest
from pathlib import Path

from archpipe import deliverables as D, model

SPEC = Path(__file__).resolve().parents[1] / "spec" / "apartment.yaml"


class DeliverableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = model.load(SPEC)

    def test_schedules_cover_every_element_once(self):
        s = D.schedules(self.p)
        self.assertEqual(len(s["rooms"]), len(self.p.rooms))
        self.assertEqual(len(s["doors"]) + len(s["windows"]), len(self.p.openings))
        self.assertEqual(sum(1 for d in s["doors"] if d["external"]), 1)
        self.assertTrue(all(w["facing"] in ("north", "south", "east", "west") for w in s["windows"]))

    def test_quantities_add_up(self):
        q = D.quantities(self.p)["L00"]
        self.assertAlmostEqual(q["net_floor_m2"], round(sum(r.area_m2 for r in self.p.rooms), 2))
        walls = q["walls"]
        self.assertAlmostEqual(sum(v["length_m"] for v in walls.values()), round(sum(w.length for w in self.p.walls) / 1000, 2), 1)
        for v in walls.values():
            self.assertAlmostEqual(v["net_area_m2"], round(v["gross_area_m2"] - v["openings_m2"], 2), 1)

    def test_spec_book_shows_each_items_verification(self):
        from archpipe.products import store
        verified = store.search(limit=1)[0]["id"]
        book = D.spec_book([{"room": "Living", "element": "floor", "product_id": verified},
                            {"room": "Living", "element": "rug", "product_id": "nope:missing"}])
        self.assertIn("layer **verified**", book)
        self.assertIn("NOT IN LIBRARY", book)

    def test_relative_cost_ranks_by_area(self):
        r = D.relative_cost({"a": 300.0, "b": 360.0})
        self.assertEqual([x["option"] for x in r], ["a", "b"])
        self.assertEqual((r[0]["index"], r[1]["index"]), (1.0, 1.2))
        self.assertEqual(r[0]["usd_low"], 300 * D.AECOM_VILLA_USD_M2["Dubai"][0])

    def test_ifc_geometry_matches_the_spec(self):
        import numpy as np
        import ifcopenshell
        import ifcopenshell.geom
        with tempfile.TemporaryDirectory() as d:
            f = ifcopenshell.open(str(D.to_ifc(self.p, Path(d) / "m.ifc")))
            s = ifcopenshell.geom.settings()
            s.set("use-world-coords", True)

            def bbox(el):
                sh = ifcopenshell.geom.create_shape(s, el)       # keep the shape alive while reading its buffer
                v = np.array(sh.geometry.verts).reshape(-1, 3) * 1000.0
                return v.min(0), v.max(0)
            self.assertEqual(len(f.by_type("IfcSpace")), len(self.p.rooms))
            self.assertEqual(len(f.by_type("IfcDoor")) + len(f.by_type("IfcWindow")), len(self.p.openings))
            lv = {l.id: l for l in self.p.levels}
            for sp in f.by_type("IfcSpace"):
                r = next(x for x in self.p.rooms if x.id == sp.Name)
                lo, hi = bbox(sp)
                xs, ys = [q[0] for q in r.boundary], [q[1] for q in r.boundary]
                self.assertLess(max(abs(lo[0] - min(xs)), abs(lo[1] - min(ys)), abs(hi[0] - max(xs)), abs(hi[1] - max(ys)),
                                    abs(hi[2] - lv[r.level].elevation - lv[r.level].height)), 0.5, sp.Name)
            for wl in f.by_type("IfcWall"):
                w = self.p.wall(wl.Name)
                lo, hi = bbox(wl)
                self.assertAlmostEqual(math.dist(lo[:2], hi[:2]),
                                       math.hypot(w.length, self.p.wall_type(w.type).thickness), delta=0.5)


if __name__ == "__main__":
    unittest.main()
