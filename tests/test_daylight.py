"""The whole-building daylight engine: geometry and bookkeeping (Radiance itself runs on the compute node)."""
import unittest

from archpipe import daylight as D


class Geometry(unittest.TestCase):
    def test_wall_along_any_direction_keeps_its_length_and_height(self):
        faces = D.wall((0, 0), (3, 4), 0.0, 2.8, 0.2)            # a 5 m wall at 53 degrees
        zs = [p[2] for f in faces for p in f.points]
        self.assertAlmostEqual(max(zs), 2.8)
        self.assertAlmostEqual(min(zs), 0.0)
        far = max(((p[0] ** 2 + p[1] ** 2) ** 0.5 for f in faces for p in f.points))
        self.assertAlmostEqual(far, (5 ** 2 + 0.1 ** 2) ** 0.5, places=6)

    def test_window_is_one_glass_pane_and_leaves_a_hole(self):
        faces = D.wall((0, 0), (4, 0), 0.0, 2.8, 0.2,
                       [{"offset": 1.0, "width": 2.0, "sill": 0.9, "head": 2.4, "kind": "window"}])
        glass = [f for f in faces if f.material == "glass"]
        self.assertEqual(len(glass), 1)                            # two coincident panes would square T
        xs = sorted({round(p[0], 6) for p in glass[0].points})
        zs = sorted({round(p[2], 6) for p in glass[0].points})
        self.assertEqual((xs, zs), ([1.0, 3.0], [0.9, 2.4]))

    def test_a_closed_door_is_opaque_and_a_hole_is_open(self):
        door = D.wall((0, 0), (4, 0), 0.0, 2.8, 0.2, [{"offset": 1, "width": 1, "sill": 0, "head": 2.1, "kind": "door"}])
        hole = D.wall((0, 0), (4, 0), 0.0, 2.8, 0.2, [{"offset": 1, "width": 1, "sill": 0, "head": 2.1, "kind": "hole"}])
        self.assertTrue(any(f.material == "door" for f in door))
        self.assertFalse(any(f.material in ("door", "glass") for f in hole))
        self.assertGreater(len(door), len(hole))

    def test_polygon_with_a_hole_is_one_ring(self):
        ring = D.with_holes([(0, 0), (10, 0), (10, 10), (0, 10)], [[(4, 4), (6, 4), (6, 6), (4, 6)]])
        self.assertEqual(len(ring), 4 + 4 + 2)                     # outer + hole + the two seam vertices
        self.assertAlmostEqual(abs(D._signed_area(ring)), 100 - 4, places=6)

    def test_section_prism_follows_its_profile(self):
        prof = [(0, 0), (8, 1.2), (8, 0.85), (0, -0.35)]           # a ramp 0.35 thick rising 1.2 m over 8 m
        faces = D.prism_section(prof, "y", -23.6, -20.6)
        zs = [p[2] for f in faces for p in f.points]
        ys = [p[1] for f in faces for p in f.points]
        self.assertAlmostEqual(max(zs), 1.2)
        self.assertAlmostEqual(min(zs), -0.35)
        self.assertEqual((min(ys), max(ys)), (-23.6, -20.6))


class Sensors(unittest.TestCase):
    def test_grid_stays_inside_an_l_shaped_room(self):
        L = [(0, 0), (6, 0), (6, 2), (2, 2), (2, 6), (0, 6)]
        pts = D.grid({"polygon": L, "z": -3.0}, spacing=0.5, inset=0.3)
        self.assertTrue(pts)
        for x, y, z in pts:
            self.assertTrue(D.inside((x, y), L))
            self.assertFalse(x > 2.0 and y > 2.0)                  # never in the missing quadrant
            self.assertAlmostEqual(z, -3.0 + 0.85)

    def test_a_tiny_room_gets_its_centroid(self):
        pts = D.grid({"polygon": [(0, 0), (0.4, 0), (0.4, 0.4), (0, 0.4)], "z": 0.0}, inset=0.3)
        self.assertEqual(len(pts), 1)


class Validation(unittest.TestCase):
    def test_formula_is_the_metric_handbook_equation(self):
        # df = T W theta M / [A (1 - R^2)]: 0.7 x 3 x 90 = 189; 84.64 x (1 - 0.478^2) = 65.30; 189 / 65.30 = 2.894 %
        self.assertAlmostEqual(D.mh_adf(0.70, 3.0, 90.0, 84.64, 0.478), 2.894, places=3)

    def test_validation_gate_fails_closed(self):
        res = {"v-open": {"rooms": {"open": {"adf": 100.2}}}, "v-dark": {"rooms": {"room": {"adf": 0.0}}},
               "v-box": {"rooms": {"room": {"adf": 4.2}}}}                        # 45 % off the formula
        self.assertFalse(D.validate(res, {"v-box": 2.90})["all_pass"])
        res["v-box"]["rooms"]["room"]["adf"] = 3.1
        self.assertTrue(D.validate(res, {"v-box": 2.90})["all_pass"])


if __name__ == "__main__":
    unittest.main()


class VillaScene(unittest.TestCase):
    def test_every_opening_lands_on_exactly_one_wall(self):
        from archpipe.concept import villa_daylight as VD
        from archpipe.concept import villa_options as VO
        from archpipe.concept import villa_parking as P
        for lay in [VO.s1(), VO.s5()] + P.options():
            sc = VD.scene(lay)
            self.assertEqual(sc.openings["placed"], sc.openings["spec"], lay["id"])
