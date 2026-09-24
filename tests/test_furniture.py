"""Independent geometry checks for archpipe.furniture.

Abbreviations used below: CCW = anticlockwise (counter-clockwise);
AABB = axis-aligned bounding box (the box [min_x,max_x] x [min_y,max_y] x
[min_z,max_z] that just encloses a set of points).

These tests do not call any helper from `furniture.py` other than
`build_furniture` and `FurnitureError` -- every geometric check (manifold
edges, outward winding, triangle area, bounding boxes) is computed here
from the raw `vertices_mm`/`triangles` output, so a bug in a shared helper
inside furniture.py cannot hide from both the code and its test.
"""
import math
import unittest

from archpipe.furniture import build_furniture, FurnitureError

REAL_BED = {
    "id": "bed-1", "type": "bed_double", "at": [2250, 2600],
    "size": [1600, 2000], "height": 1100, "rotation": 180,
    "detail": "warm-contemporary-v1",
}
REAL_BEDSIDE = {
    "id": "bedside-1", "type": "bedside_table", "at": [500, 500],
    "size": [450, 400], "height": 500, "rotation": 0,
    "detail": "warm-contemporary-v1",
}
REAL_WARDROBE = {
    "id": "wardrobe-1", "type": "wardrobe", "at": [3800, 900],
    "size": [1200, 600], "height": 2100, "rotation": 270,
    "detail": "warm-contemporary-v1",
}
REAL_DESK = {
    "id": "desk-1", "type": "desk", "at": [3800, 3000],
    "size": [1200, 600], "height": 750, "rotation": 0,
    "detail": "warm-contemporary-v1",
}
ALL_REAL_ITEMS = [REAL_BED, REAL_BEDSIDE, REAL_WARDROBE, REAL_DESK]

EPS = 1e-4


def _triangle_area(a, b, c):
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    cx = uy * vz - uz * vy
    cy = uz * vx - ux * vz
    cz = ux * vy - uy * vx
    return 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)


def _signed_volume(verts, tris):
    total = 0.0
    for i, j, k in tris:
        ax, ay, az = verts[i]
        bx, by, bz = verts[j]
        cx, cy, cz = verts[k]
        total += (ax * (by * cz - bz * cy)
                  - ay * (bx * cz - bz * cx)
                  + az * (bx * cy - by * cx))
    return total / 6.0


def _assert_closed_manifold(test, component):
    name = component["name"]
    verts = component["vertices_mm"]
    tris = component["triangles"]
    test.assertGreater(len(tris), 0, f"{name}: no triangles")
    test.assertLess(len(tris), 6000, f"{name}: triangle budget exceeded")

    directed = set()
    for tri in tris:
        test.assertEqual(len(tri), 3, f"{name}: triangle must have 3 indices")
        i, j, k = tri
        for a, b in ((i, j), (j, k), (k, i)):
            edge = (a, b)
            test.assertNotIn(edge, directed,
                              f"{name}: directed edge {edge} repeated -- not manifold")
            directed.add(edge)
        area = _triangle_area(verts[i], verts[j], verts[k])
        test.assertGreater(area, 1e-6, f"{name}: degenerate triangle {tri}")

    for (a, b) in directed:
        test.assertIn((b, a), directed,
                       f"{name}: edge {(a, b)} has no reverse -- mesh is not closed")

    vol = _signed_volume(verts, tris)
    test.assertGreater(vol, 0.0, f"{name}: signed volume <= 0 -- winding is not outward")


def _bounds(verts):
    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    zs = [v[2] for v in verts]
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)


class ManifoldTests(unittest.TestCase):
    def test_all_real_items_are_closed_outward_manifolds(self):
        for item in ALL_REAL_ITEMS:
            for component in build_furniture(item):
                with self.subTest(item=item["id"], component=component["name"]):
                    _assert_closed_manifold(self, component)


class LocalBoundsTests(unittest.TestCase):
    def test_unrotated_origin_bounds_match_declared_size(self):
        for item in ALL_REAL_ITEMS:
            local_item = dict(item, at=[0, 0], rotation=0)
            w, d = local_item["size"]
            h = local_item["height"]
            components = build_furniture(local_item)
            all_verts = [v for c in components for v in c["vertices_mm"]]
            x0, x1, y0, y1, z0, z1 = _bounds(all_verts)
            with self.subTest(item=item["id"]):
                self.assertAlmostEqual(x0, -w / 2.0, delta=EPS)
                self.assertAlmostEqual(x1, w / 2.0, delta=EPS)
                self.assertAlmostEqual(y0, -d / 2.0, delta=EPS)
                self.assertAlmostEqual(y1, d / 2.0, delta=EPS)
                self.assertAlmostEqual(z0, 0.0, delta=EPS)
                self.assertAlmostEqual(z1, h, delta=EPS)
                for c in components:
                    for x, y, z in c["vertices_mm"]:
                        self.assertGreaterEqual(x, -w / 2.0 - EPS)
                        self.assertLessEqual(x, w / 2.0 + EPS)
                        self.assertGreaterEqual(y, -d / 2.0 - EPS)
                        self.assertLessEqual(y, d / 2.0 + EPS)
                        self.assertGreaterEqual(z, -EPS)
                        self.assertLessEqual(z, h + EPS)


class WorldBoundsTests(unittest.TestCase):
    def test_quarter_rotations_swap_width_and_depth_about_at(self):
        at = [1000.0, 1500.0]
        for item in ALL_REAL_ITEMS:
            w, d = item["size"]
            for rotation, (half_x, half_y) in (
                (0, (w / 2.0, d / 2.0)),
                (90, (d / 2.0, w / 2.0)),
                (180, (w / 2.0, d / 2.0)),
                (270, (d / 2.0, w / 2.0)),
            ):
                rotated = dict(item, at=at, rotation=rotation)
                all_verts = [v for c in build_furniture(rotated) for v in c["vertices_mm"]]
                x0, x1, y0, y1, _z0, _z1 = _bounds(all_verts)
                with self.subTest(item=item["id"], rotation=rotation):
                    self.assertAlmostEqual(x0, at[0] - half_x, delta=EPS)
                    self.assertAlmostEqual(x1, at[0] + half_x, delta=EPS)
                    self.assertAlmostEqual(y0, at[1] - half_y, delta=EPS)
                    self.assertAlmostEqual(y1, at[1] + half_y, delta=EPS)


class RealBedroomTests(unittest.TestCase):
    def test_headboard_reaches_the_declared_north_edge_and_full_height(self):
        components = build_furniture(REAL_BED)
        headboard = next(c for c in components if "headboard" in c["name"])
        ys = [v[1] for v in headboard["vertices_mm"]]
        zs = [v[2] for v in headboard["vertices_mm"]]
        self.assertAlmostEqual(max(ys), 3600.0, delta=EPS)
        self.assertAlmostEqual(max(zs), 1100.0, delta=EPS)
        hb_depth = 3600.0 - min(ys)
        for y in ys:
            self.assertGreaterEqual(y, 3600.0 - hb_depth - EPS)

    def test_mattress_top_and_pillow_top_are_plausible(self):
        components = build_furniture(REAL_BED)
        mattress = next(c for c in components if c["name"].endswith(":mattress"))
        pillow = next(c for c in components if "pillow" in c["name"])
        mattress_top = max(v[2] for v in mattress["vertices_mm"])
        pillow_top = max(v[2] for v in pillow["vertices_mm"])
        self.assertAlmostEqual(mattress_top, 550.0, delta=40.0)
        self.assertAlmostEqual(pillow_top, 700.0, delta=60.0)

    def test_desk_preserves_an_open_knee_space(self):
        components = build_furniture(REAL_DESK)
        at = REAL_DESK["at"]
        w, d = REAL_DESK["size"]
        # World-space knee box: centred under the desk, in front, from the
        # floor to a generous clear height.
        kx0, kx1 = at[0] - w / 4.0, at[0] + w / 4.0
        ky0, ky1 = at[1], at[1] + d / 2.0
        kz0, kz1 = 0.0, 600.0
        for c in components:
            x0, x1, y0, y1, z0, z1 = _bounds(c["vertices_mm"])
            intersects = (x0 < kx1 and x1 > kx0 and y0 < ky1 and y1 > ky0
                          and z0 < kz1 and z1 > kz0)
            self.assertFalse(intersects,
                              f"{c['name']} AABB intersects the desk knee space")

    def test_distinct_material_names_cover_all_five(self):
        names = set()
        for item in ALL_REAL_ITEMS:
            for c in build_furniture(item):
                names.add(c["material"]["name"])
        expected = {"archpipe oak", "archpipe warm linen", "archpipe ivory bedding",
                    "archpipe muted taupe throw", "archpipe dark metal"}
        self.assertEqual(names, expected)

    def test_material_dicts_are_not_shared_mutable_state(self):
        c1 = build_furniture(REAL_BED)[0]
        c2 = build_furniture(REAL_BED)[0]
        c1["material"]["rgb"][0] = 0
        self.assertNotEqual(c1["material"]["rgb"][0], c2["material"]["rgb"][0])


class InvalidInputTests(unittest.TestCase):
    def test_unknown_type_raises(self):
        with self.assertRaises(FurnitureError):
            build_furniture(dict(REAL_BED, type="sofa"))

    def test_nonpositive_dimensions_raise(self):
        for size in ([0, 2000], [1600, -1], [-5, -5]):
            with self.assertRaises(FurnitureError):
                build_furniture(dict(REAL_BED, size=size))
        with self.assertRaises(FurnitureError):
            build_furniture(dict(REAL_BED, height=0))

    def test_nonfinite_inputs_raise(self):
        for at in ([float("nan"), 0], [float("inf"), 0]):
            with self.assertRaises(FurnitureError):
                build_furniture(dict(REAL_BED, at=at))
        for size in ([float("nan"), 2000], [1600, float("inf")]):
            with self.assertRaises(FurnitureError):
                build_furniture(dict(REAL_BED, size=size))
        with self.assertRaises(FurnitureError):
            build_furniture(dict(REAL_BED, height=float("nan")))
        with self.assertRaises(FurnitureError):
            build_furniture(dict(REAL_BED, rotation=float("inf")))

    def test_missing_field_raises(self):
        item = dict(REAL_BED)
        del item["height"]
        with self.assertRaises(FurnitureError):
            build_furniture(item)

    def test_wrong_length_size_raises(self):
        with self.assertRaises(FurnitureError):
            build_furniture(dict(REAL_BED, size=[1600, 2000, 100]))
        with self.assertRaises(FurnitureError):
            build_furniture(dict(REAL_BED, at=[1]))

    def test_string_and_bool_values_raise(self):
        with self.assertRaises(FurnitureError):
            build_furniture(dict(REAL_BED, height="1100"))
        with self.assertRaises(FurnitureError):
            build_furniture(dict(REAL_BED, rotation=True))


if __name__ == "__main__":
    unittest.main()
