"""The villa environment spec against independent evidence: the Revit sister columns, the brief's offsets and
heights, and plain geometry. Values quoted from out/villa/omar-inventory.json (Revit 2027 read of omar.rvt)."""
import unittest

from archpipe import villa_env as V

# Revit structural columns on the SISTER side (inventory bboxes, mm), not used to build the spec.
REVIT_SISTER = {1587347: (7017, -36241, 7377, -35731), 1587354: (9227, -36241, 9567, -35731),
                1587372: (22237, -31671, 22597, -31161)}
# ...and the ours they should mirror (CAD S-COLS).
OURS_FOR = {1587347: (7017, -24101, 7377, -23591), 1587354: (9227, -24101, 9567, -23591),
            1587372: (22237, -28671, 22597, -28161)}


def inside(pt, poly):
    x, y = pt
    c = False
    for i in range(len(poly)):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % len(poly)]
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
            c = not c
    return c


class MirrorAxis(unittest.TestCase):
    def test_axis_reproduces_revit_sister_columns(self):
        for rid, sister in REVIT_SISTER.items():
            m = V.mirror_box(OURS_FOR[rid])
            for a, b in zip(m, sister):
                self.assertAlmostEqual(a, b, delta=1.0, msg=rid)

    def test_wrong_axis_fails(self):                      # negative: a 200 mm error is visible
        m = V.mirror_box(OURS_FOR[1587347], axis=V.AXIS_Y + 200)
        self.assertGreater(abs(m[1] - REVIT_SISTER[1587347][1]), 300)


class Plot(unittest.TestCase):
    def test_offsets_are_the_pdf(self):
        """Face to fence inner face as measured on the old GF PDF; the plot line is the fence's outer face."""
        px0, py0, px1, py1 = V.plot()
        t = V.FENCE_T
        self.assertEqual(V.BAR[0] - px0, 3740 + t)        # street side; the PDF prints 4.02 to the outer face
        self.assertAlmostEqual(V.BAR[0] - px0, 4020, delta=50)
        self.assertEqual(py1 - V.BAR[3], 2990 + t)        # plot-east
        self.assertEqual(px1 - V.BAR[2], 5710 + t)        # rear
        self.assertAlmostEqual(V.mirror_box(V.BAR)[1] - py0, 2990 + t, delta=1)   # sister side mirrors ours

    def test_fence_inner_faces_sit_at_the_offsets(self):
        els = {e["id"]: e for e in V.spec()["elements"]}
        self.assertEqual(V.BAR[0] - max(p[0] for p in els["fence-street"]["pts"]), 3740)
        self.assertEqual(min(p[1] for p in els["fence-east"]["pts"]) - V.BAR[3], 2990)
        self.assertEqual(min(p[0] for p in els["fence-rear"]["pts"]) - V.BAR[2], 5710)

    def test_fence_top_is_street_plus_2_20(self):
        fences = [e for e in V.spec()["elements"] if e["id"].startswith("fence-")]
        self.assertEqual(len(fences), 4)
        for f in fences:
            self.assertEqual(f["z0"], V.B)
            self.assertEqual(f["z1"] - V.STREET, 2200)

    def test_yard_area_is_half_plot_minus_building_and_core(self):
        px0, py0, px1, py1 = V.plot()
        half = (px1 - px0) * (py1 - V.AXIS_Y) / 1e6
        building_and_half_core = (V.BAR[2] - V.BAR[0]) * (V.BAR[3] - V.AXIS_Y) / 1e6
        self.assertAlmostEqual(V.polygon_area(V.yard()), half - building_and_half_core, places=3)

    def test_yard_excludes_the_building_and_the_core(self):
        y = V.yard()
        self.assertFalse(inside((12000, -26000), y))      # inside the bar
        self.assertFalse(inside((21000, -29500), y))      # inside the bathroom projection
        self.assertFalse(inside((10000, -29500), y))      # the shared core, not yard
        self.assertTrue(inside((12000, -22000), y))       # east strip
        self.assertTrue(inside((25000, -29000), y))       # rear strip, our half
        self.assertTrue(inside((2000, -29000), y))        # street strip, our half
        self.assertFalse(inside((25000, -31000), y))      # rear strip, sister's half


class Core(unittest.TestCase):
    def test_gf_core_segments_tile_the_strip_up_to_our_bathroom(self):
        segs = V.CORE_GF
        self.assertEqual(segs[0][1], V.BAR[0])
        for a, b in zip(segs, segs[1:]):
            self.assertEqual(a[2], b[1], (a[0], b[0]))
        self.assertEqual(segs[-1][2], V.BUMP[0])          # the sister's bathroom ends where ours (CAD) begins

    def test_core_is_the_gap_between_the_villas(self):
        self.assertAlmostEqual(V.BAR[1] - V.SISTER_FACE, 2489, delta=2)   # PDF: 2.51 clear between core walls

    def test_basement_outline_adds_our_halves_of_the_core_ends(self):
        bar = (V.BAR[2] - V.BAR[0]) * (V.BAR[3] - V.BAR[1]) / 1e6
        depth = (V.BAR[1] - V.AXIS_Y) / 1e3
        ends = ((V.CORE_B_OURS_FRONT[1] - V.CORE_B_OURS_FRONT[0]) + (V.CORE_B_OURS_REAR[1] - V.CORE_B_OURS_REAR[0])) / 1e3
        self.assertAlmostEqual(V.polygon_area(V.footprint_b()), bar + depth * ends, places=3)
        self.assertTrue(inside((20000, -29500), V.footprint_b()))     # under the GF bathrooms: ours to the axis
        self.assertFalse(inside((10000, -29500), V.footprint_b()))    # the stair: shared
        self.assertFalse(inside((20000, -30500), V.footprint_b()))    # beyond the axis: the sister's


class Structure(unittest.TestCase):
    def test_beams_sit_inside_the_footprint(self):
        beams = [e for e in V.spec()["elements"] if e["category"] == "StructuralFraming"]
        self.assertEqual(len(beams), 8 * 3)
        fp = V.footprint()
        for b in beams:
            cx = sum(p[0] for p in b["pts"]) / 4
            cy = sum(p[1] for p in b["pts"]) / 4
            self.assertTrue(inside((cx, cy), fp), b["id"])
            self.assertEqual(b["z1"] - b["z0"], V.BEAM_D)

    def test_columns_are_ours_only(self):
        for x0, y0, x1, y1 in V.COLUMNS:
            self.assertTrue(inside(((x0 + x1) / 2, (y0 + y1) / 2), V.footprint()))


class Neighbours(unittest.TestCase):
    def test_heights_and_gaps(self):
        els = {e["id"]: e for e in V.spec()["elements"]}
        east, rear = els["neighbour-east"], els["neighbour-rear"]
        self.assertEqual(east["z1"] - east["z0"], 12000)
        self.assertEqual(min(p[1] for p in east["pts"]) - V.plot()[3], V.OFFSET_E)   # set back like us
        self.assertEqual(min(p[0] for p in rear["pts"]) - V.plot()[2], V.OFFSET_S)

    def test_neighbour_windows_face_us(self):
        els = [e for e in V.spec()["elements"] if e["id"].startswith("neighbour-east-w")]
        self.assertEqual(len(els), len(V.EAST_FACE_WINDOWS_X) * 4)
        for w in els:                                     # proud of the face, on our side
            self.assertLessEqual(max(p[1] for p in w["pts"]), V.plot()[3] + V.OFFSET_E)


class ReadbackCheck(unittest.TestCase):
    """scripts/villa_env.py check: passes a faithful read-back and catches a wrong one."""

    @staticmethod
    def faithful():
        import copy
        s = V.spec()
        zs = {l["name"]: l["z"] for l in s["levels"]}
        bb = lambda pts, z0, z1: [min(p[0] for p in pts), min(p[1] for p in pts), z0,  # noqa: E731
                                  max(p[0] for p in pts), max(p[1] for p in pts), z1]
        cols = []
        for base, z0, z1 in (("B -1.80", V.B, V.GF), ("GF +1.20", V.GF, V.APT), ("APT +4.20 (not ours)", V.APT, V.ROOF)):
            cols += [{"id": i, "base": base, "bbox": [c[0], c[1], z0, c[2], c[3], z1]} for i, c in enumerate(V.COLUMNS)]
        rb = {"levels": copy.deepcopy(s["levels"]),
              "site": {"latitude": V.LATITUDE, "longitude": V.LONGITUDE, "street_facade_azimuth": 290.0},
              "shapes": [{"id": e["id"], "bbox": bb(e["pts"], e["z0"], e["z1"])} for e in s["elements"]],
              "floors": [{"id": f["id"], "area_m2": V.polygon_area(f["pts"]),
                          "bbox": bb(f["pts"], zs[f["level"]] - 200, zs[f["level"]])} for f in s["slabs"]],
              "columns": cols}
        return s, rb

    def setUp(self):
        import importlib.util
        from pathlib import Path
        p = Path(__file__).resolve().parents[1] / "scripts" / "villa_env.py"
        spec = importlib.util.spec_from_file_location("villa_env_cli", p)
        self.cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.cli)

    def test_faithful_readback_passes(self):
        self.assertEqual(self.cli.check(*self.faithful()), [])

    def test_each_kind_of_drift_is_caught(self):
        for mutate, word in ((lambda rb: rb["site"].__setitem__("street_facade_azimuth", 250.0), "azimuth"),
                             (lambda rb: rb["shapes"][0]["bbox"].__setitem__(5, 0.0), "fence-street"),
                             (lambda rb: rb["floors"].pop(), "missing slab"),
                             (lambda rb: rb["columns"][0]["bbox"].__setitem__(5, 2800.0), "column"),
                             (lambda rb: rb["levels"][1].__setitem__("z", -2800), "level")):
            s, rb = self.faithful()
            mutate(rb)
            bad = self.cli.check(s, rb)
            self.assertTrue(any(word in b for b in bad), (word, bad))


if __name__ == "__main__":
    unittest.main()
