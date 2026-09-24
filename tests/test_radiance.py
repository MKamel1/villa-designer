"""Portable regressions for the Radiance adapter: geometry holes, units,
malformed inputs, and source placement/orientation. None of this requires
Radiance installed -- every test either exercises pure geometry/argv-
building functions directly, or replaces `archpipe.radiance._run` with a
fake that never shells out.
"""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from archpipe import radiance as rad


def bedroom_data(**overrides):
    data = {
        "units": "mm",
        "source": "test fixture",
        "levels": [{"id": "L1", "elevation": 0.0, "name": "Level 1"}],
        "rooms": [{
            "id": "R1", "name": "Bedroom", "level": "L1", "ceiling_height": 2700,
            "boundary": [[0.0, 0.0], [4000.0, 0.0], [4000.0, 3000.0], [0.0, 3000.0]],
        }],
        "walls": [
            {"id": "W-S", "level": "L1", "start": [0.0, 0.0], "end": [4000.0, 0.0],
             "thickness": 200.0, "height": 2700.0},
            {"id": "W-E", "level": "L1", "start": [4000.0, 0.0], "end": [4000.0, 3000.0],
             "thickness": 200.0, "height": 2700.0},
            {"id": "W-N", "level": "L1", "start": [4000.0, 3000.0], "end": [0.0, 3000.0],
             "thickness": 200.0, "height": 2700.0},
            {"id": "W-W", "level": "L1", "start": [0.0, 3000.0], "end": [0.0, 0.0],
             "thickness": 200.0, "height": 2700.0},
        ],
        "openings": [
            {"id": "DR-1", "kind": "door", "host": "W-S", "at": 900.0, "sill": 0.0,
             "width": 900.0, "height": 2100.0},
            {"id": "WN-1", "kind": "window", "host": "W-E", "at": 1500.0, "sill": 900.0,
             "width": 1200.0, "height": 1400.0},
        ],
        "furniture": [
            {"id": "FN-BED", "at": [2000.0, 2200.0], "bbox_center_mm": [2000.0, 2200.0],
             "base_height_mm": 0.0, "size_mm": [1600.0, 2000.0, 600.0]},
        ],
        "casework": [],
        "lighting": [
            {"id": "LT-01", "at": [2000.0, 1500.0], "mounting_height": 2400.0,
             "ies_file": "fake.ies", "output": 1.0, "rotation": 0.0},
        ],
    }
    data.update(overrides)
    return data


class VectorGeometryTests(unittest.TestCase):
    def test_rect_polygon_winds_to_requested_outward_normal(self):
        pts = rad.rect_polygon((0, 0, 0), (1, 0, 0), (0, 1, 0), 0, 0, 2, 3, (0, 0, 1))
        normal = rad.polygon_normal(pts)
        self.assertGreater(rad._dot(normal, (0, 0, 1)), 0)

        pts_down = rad.rect_polygon((0, 0, 0), (1, 0, 0), (0, 1, 0), 0, 0, 2, 3, (0, 0, -1))
        normal_down = rad.polygon_normal(pts_down)
        self.assertLess(rad._dot(normal_down, (0, 0, 1)), 0)

    def test_box_polygons_all_point_outward(self):
        box = rad.Box(0, 0, 0, 1000, 2000, 3000)
        for pts, material in rad._box_polygons(box, "furniture"):
            centre = tuple(sum(c[i] for c in pts) / len(pts) for i in range(3))
            box_centre = (rad.mm(500), rad.mm(1000), rad.mm(1500))
            outward = rad._sub(centre, box_centre)
            normal = rad.polygon_normal(pts)
            self.assertGreater(rad._dot(normal, outward), 0,
                              f"face at {centre} does not point outward")


class RectDecompositionTests(unittest.TestCase):
    def test_hole_fully_inside_gives_four_pieces_with_no_overlap_and_full_area(self):
        outer = (0.0, 0.0, 10.0, 10.0)
        hole = (3.0, 3.0, 7.0, 7.0)
        pieces = rad.rect_minus_rect(outer, hole)
        self.assertEqual(len(pieces), 4)
        area = sum((x1 - x0) * (y1 - y0) for x0, y0, x1, y1 in pieces)
        outer_area = (outer[2] - outer[0]) * (outer[3] - outer[1])
        hole_area = (hole[2] - hole[0]) * (hole[3] - hole[1])
        self.assertAlmostEqual(area, outer_area - hole_area)
        for i, a in enumerate(pieces):
            for b in pieces[i + 1:]:
                overlap = (max(a[0], b[0]) < min(a[2], b[2])
                          and max(a[1], b[1]) < min(a[3], b[3]))
                self.assertFalse(overlap, f"{a} overlaps {b}")

    def test_hole_touching_two_edges_leaves_one_remaining_piece(self):
        outer = (0.0, 0.0, 10.0, 10.0)
        hole = (0.0, 0.0, 4.0, 10.0)          # spans full height, flush left
        pieces = rad.rect_minus_rect(outer, hole)
        self.assertEqual(len(pieces), 1)
        self.assertEqual(pieces[0], (4.0, 0.0, 10.0, 10.0))

    def test_non_overlapping_hole_returns_outer_unchanged(self):
        outer = (0.0, 0.0, 10.0, 10.0)
        hole = (20.0, 20.0, 25.0, 25.0)
        self.assertEqual(rad.rect_minus_rect(outer, hole), [outer])

    def test_decompose_with_two_holes_preserves_total_area(self):
        outer = (0.0, 0.0, 10.0, 5.0)
        holes = [(1.0, 1.0, 2.0, 2.0), (7.0, 1.0, 8.0, 4.0)]
        pieces = rad.decompose_rect(outer, holes)
        area = sum((x1 - x0) * (y1 - y0) for x0, y0, x1, y1 in pieces)
        expected = 10.0 * 5.0 - 1.0 - 3.0
        self.assertAlmostEqual(area, expected)

    def test_holes_overlap_detection(self):
        self.assertTrue(rad._holes_overlap([(0, 0, 5, 5), (4, 4, 8, 8)]))
        self.assertFalse(rad._holes_overlap([(0, 0, 5, 5), (5, 5, 8, 8)]))


class WallGeometryHolesTests(unittest.TestCase):
    def test_wall_with_one_opening_produces_a_real_hole_and_reveals(self):
        wall = {"id": "W-S", "start": [0.0, 0.0], "end": [4000.0, 0.0],
               "thickness": 200.0, "height": 2700.0}
        openings = [{"id": "DR-1", "kind": "door", "host": "W-S", "at": 900.0,
                    "sill": 0.0, "width": 900.0, "height": 2100.0}]
        polys, windows = rad.wall_polygons(wall, openings, 0.0, fill_doors=False)
        self.assertEqual(windows, [])
        # Two faces, each split into 3 pieces around one opening that touches
        # neither vertical edge but does touch the sill (v=0), plus 3 reveal
        # quads (no sill reveal since sill is flush with the wall base).
        self.assertGreater(len(polys), 6)

        # No polygon may pass through the opening's own rectangle in wall-
        # local space -- i.e. the hole is a genuine absence of geometry.
        for pts, material in polys:
            xs = [p[0] for p in pts]
            zs = [p[2] for p in pts]
            spans_hole_x = min(xs) < rad.mm(1350.0) and max(xs) > rad.mm(450.0)
            spans_hole_z = min(zs) < rad.mm(2100.0) and max(zs) > 0.0
            is_reveal = abs(max(p[1] for p in pts) - min(p[1] for p in pts)) > 1e-9
            if spans_hole_x and spans_hole_z and not is_reveal:
                self.fail(f"a wall-face polygon spans the opening: {pts}")

    def test_fill_doors_leaves_the_wall_solid(self):
        wall = {"id": "W-S", "start": [0.0, 0.0], "end": [4000.0, 0.0],
               "thickness": 200.0, "height": 2700.0}
        openings = [{"id": "DR-1", "kind": "door", "host": "W-S", "at": 900.0,
                    "sill": 0.0, "width": 900.0, "height": 2100.0}]
        polys_open, _ = rad.wall_polygons(wall, openings, 0.0, fill_doors=False)
        polys_filled, _ = rad.wall_polygons(wall, openings, 0.0, fill_doors=True)
        self.assertLess(len(polys_filled), len(polys_open))
        # Filled: just the two full-rectangle faces, no reveals.
        self.assertEqual(len(polys_filled), 2)

    def test_window_kind_is_returned_for_glazing(self):
        wall = {"id": "W-E", "start": [4000.0, 0.0], "end": [4000.0, 3000.0],
               "thickness": 200.0, "height": 2700.0}
        openings = [{"id": "WN-1", "kind": "window", "host": "W-E", "at": 1500.0,
                    "sill": 900.0, "width": 1200.0, "height": 1400.0}]
        polys, windows = rad.wall_polygons(wall, openings, 0.0, fill_doors=True)
        self.assertEqual(len(windows), 1)
        self.assertEqual(windows[0].id, "WN-1")
        # A window hole is still cut even though fill_doors=True.
        self.assertGreater(len(polys), 2)

    def test_overlapping_openings_raise(self):
        wall = {"id": "W-S", "start": [0.0, 0.0], "end": [4000.0, 0.0],
               "thickness": 200.0, "height": 2700.0}
        openings = [
            {"id": "A", "kind": "window", "host": "W-S", "at": 1000.0, "sill": 900.0,
             "width": 800.0, "height": 1000.0},
            {"id": "B", "kind": "window", "host": "W-S", "at": 1200.0, "sill": 900.0,
             "width": 800.0, "height": 1000.0},
        ]
        with self.assertRaises(rad.RadianceError):
            rad.wall_polygons(wall, openings, 0.0, fill_doors=False)

    def test_opening_outside_wall_bounds_raises(self):
        wall = {"id": "W-S", "start": [0.0, 0.0], "end": [4000.0, 0.0],
               "thickness": 200.0, "height": 2700.0}
        openings = [{"id": "A", "kind": "window", "host": "W-S", "at": 3900.0,
                    "sill": 0.0, "width": 800.0, "height": 1000.0}]
        with self.assertRaises(rad.RadianceError):
            rad.wall_polygons(wall, openings, 0.0, fill_doors=False)

    def test_zero_thickness_wall_raises(self):
        wall = {"id": "W-S", "start": [0.0, 0.0], "end": [4000.0, 0.0],
               "thickness": 0.0, "height": 2700.0}
        with self.assertRaises(rad.RadianceError):
            rad.wall_polygons(wall, [], 0.0, fill_doors=False)

    def test_missing_height_raises(self):
        wall = {"id": "W-S", "start": [0.0, 0.0], "end": [4000.0, 0.0],
               "thickness": 200.0, "height": None}
        with self.assertRaises(rad.RadianceError):
            rad.wall_polygons(wall, [], 0.0, fill_doors=False)


class UnitsTests(unittest.TestCase):
    def test_mm_conversion_is_exact(self):
        self.assertEqual(rad.mm(1000.0), 1.0)
        self.assertEqual(rad.mm(1.0), 0.001)

    def test_room_rectangle_converts_axis_aligned_only(self):
        room = {"boundary": [[0.0, 0.0], [4000.0, 0.0], [4000.0, 3000.0], [0.0, 3000.0]]}
        self.assertEqual(rad.room_rectangle(room), (0.0, 0.0, 4000.0, 3000.0))

    def test_non_rectangular_room_raises(self):
        room = {"boundary": [[0.0, 0.0], [4000.0, 0.0], [4000.0, 3000.0], [500.0, 3000.0]]}
        with self.assertRaises(rad.RadianceError):
            rad.room_rectangle(room)

    def test_wrong_vertex_count_raises(self):
        room = {"boundary": [[0.0, 0.0], [4000.0, 0.0], [4000.0, 3000.0]]}
        with self.assertRaises(rad.RadianceError):
            rad.room_rectangle(room)

    def test_multi_level_walls_raise(self):
        data = bedroom_data(levels=[{"id": "L1", "elevation": 0.0},
                                    {"id": "L2", "elevation": 3000.0}])
        data["walls"][0]["level"] = "L2"
        with self.assertRaises(rad.RadianceError):
            rad.single_level_elevation_mm(data, data["rooms"][0])


class MalformedInputTests(unittest.TestCase):
    def test_missing_opening_fields_raise(self):
        wall = {"id": "W-S", "start": [0.0, 0.0], "end": [4000.0, 0.0],
               "thickness": 200.0, "height": 2700.0}
        openings = [{"id": "A", "kind": "door", "host": "W-S", "at": 900.0, "sill": 0.0,
                    "width": 900.0}]        # no height
        with self.assertRaises(rad.RadianceError):
            rad.wall_polygons(wall, openings, 0.0, fill_doors=False)

    def test_mesh_with_out_of_range_triangle_raises(self):
        mesh = {"vertices_mm": [[0, 0, 0], [1, 0, 0], [0, 1, 0]], "triangles": [[0, 1, 5]]}
        with self.assertRaises(rad.RadianceError):
            rad._mesh_polygons(mesh, "furniture")

    def test_empty_mesh_raises(self):
        with self.assertRaises(rad.RadianceError):
            rad._mesh_polygons({"vertices_mm": [], "triangles": []}, "furniture")

    def test_non_positive_furniture_dimension_raises(self):
        data = bedroom_data()
        data["furniture"][0]["size_mm"] = [0.0, 2000.0, 600.0]
        with self.assertRaises(rad.RadianceError):
            rad.furniture_geometry(data)

    def test_unsafe_ies_name_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            ies_dir = Path(tmp)
            (ies_dir / "real.ies").write_text("x")
            with self.assertRaises(rad.RadianceError):
                rad._validate_ies_name("../real.ies", ies_dir)
            with self.assertRaises(rad.RadianceError):
                rad._validate_ies_name("missing.ies", ies_dir)
            self.assertTrue(
                rad._validate_ies_name("real.ies", ies_dir).samefile(ies_dir / "real.ies"))

    def test_workers_clamped_to_1_and_8(self):
        self.assertEqual(rad.clamp_workers(0), 1)
        self.assertEqual(rad.clamp_workers(-5), 1)
        self.assertEqual(rad.clamp_workers(99), 8)
        self.assertEqual(rad.clamp_workers(4), 4)

    def test_glazing_transmittance_out_of_range_raises(self):
        with self.assertRaises(rad.RadianceError):
            rad.tn_to_transmissivity(0.0)
        with self.assertRaises(rad.RadianceError):
            rad.tn_to_transmissivity(1.5)

    def test_malformed_rtrace_output_raises(self):
        with self.assertRaises(rad.RadianceError):
            rad.parse_rtrace_output("1.0 2.0 not-a-number", 1)
        with self.assertRaises(rad.RadianceError):
            rad.parse_rtrace_output("1.0 2.0 3.0 4.0", 1)   # wrong count

    def test_grid_all_cells_excluded_raises(self):
        boxes = [rad.Box(0, 0, 0, 10000, 10000, 3000)]
        with self.assertRaises(rad.RadianceError):
            rad.grid_points(0, 0, 4000, 3000, inset=150, spacing=250,
                           plane_mm=850, boxes=boxes)

    def test_inset_larger_than_room_raises(self):
        with self.assertRaises(rad.RadianceError):
            rad.grid_points(0, 0, 200, 200, inset=150, spacing=250, plane_mm=850, boxes=[])


class SourcePlacementAndOrientationTests(unittest.TestCase):
    def test_xform_rotates_then_translates_with_no_azimuth_offset(self):
        tools = rad.Tools(bin={"xform": Path("/opt/radiance/bin/xform")}, lib=Path("/opt/lib"))
        argv = rad.xform_argv(tools, Path("/tmp/fx.rad"), 90.0, (2.0, 3.0, 2.4))
        self.assertEqual(argv[0], tools["xform"])
        self.assertIn("-rz", argv)
        self.assertEqual(argv[argv.index("-rz") + 1], "90.000000")
        self.assertLess(argv.index("-rz"), argv.index("-t"))
        self.assertEqual(argv[argv.index("-t") + 1:argv.index("-t") + 4],
                         ["2.000000", "3.000000", "2.400000"])
        self.assertEqual(argv[-1], Path("/tmp/fx.rad"))
        # No 90-degree Blender-style correction anywhere in the argument list.
        self.assertNotIn("92.500000", argv)

    def test_ies2rad_argv_uses_dm_t_default_and_explicit_multiplier(self):
        tools = rad.Tools(bin={"ies2rad": Path("/opt/radiance/bin/ies2rad")}, lib=Path("/lib"))
        argv = rad.ies2rad_argv(tools, Path("/ies/lamp.ies"), 0.5, "fx00")
        self.assertIn("-dm", argv)
        self.assertEqual(argv[argv.index("-t") + 1], "default")
        self.assertEqual(argv[argv.index("-m") + 1], "0.500000")
        self.assertEqual(argv[argv.index("-o") + 1], "fx00")
        self.assertEqual(argv[-1], Path("/ies/lamp.ies"))

    def test_convert_fixture_places_at_mounting_height_above_floor(self):
        calls = []

        def fake_run(argv, *, cwd, timeout, stdout_path, stdin_path=None):
            calls.append(argv)
            if argv[0] == tools["ies2rad"]:
                self.assertNotIn('-l',argv)
                prefix=Path(argv[argv.index('-o')+1])
                self.assertTrue(prefix.is_absolute())
                self.assertTrue(prefix.is_relative_to(cwd))
                prefix.with_suffix('.rad').write_text("void plastic m 0 0 5 .5 .5 .5 0 0\n")
            elif argv[0] == tools["xform"]:
                stdout_path.write_text("placed geometry\n")

        with tempfile.TemporaryDirectory() as tmp:
            ies_dir = Path(tmp) / "ies"
            ies_dir.mkdir()
            (ies_dir / "lamp.ies").write_text("fake")
            tools = rad.Tools(bin={"ies2rad": Path("/bin/ies2rad"), "xform": Path("/bin/xform")},
                             lib=Path("/lib"))
            fixture = {"id": "LT-01", "ies_file": "lamp.ies", "at": [2000.0, 1500.0],
                      "mounting_height": 2400.0, "output": 1.0, "rotation": 30.0}
            placed = rad.convert_fixture(tools, ies_dir, fixture, 0.0, Path(tmp), "fx00",
                                         run=fake_run)
            self.assertTrue(placed.is_file())
            xform_call = calls[1]
            z_index = xform_call.index("-t") + 3
            self.assertEqual(xform_call[z_index], f"{rad.mm(2400.0):.6f}")
            self.assertEqual(xform_call[xform_call.index("-rz") + 1], "30.000000")

    def test_rejects_output_outside_0_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            ies_dir = Path(tmp)
            (ies_dir / "lamp.ies").write_text("fake")
            tools = rad.Tools(bin={"ies2rad": Path("/bin/ies2rad"), "xform": Path("/bin/xform")},
                             lib=Path("/lib"))
            fixture = {"id": "LT-01", "ies_file": "lamp.ies", "at": [0.0, 0.0],
                      "mounting_height": 2400.0, "output": 1.5}
            with self.assertRaises(rad.RadianceError):
                rad.convert_fixture(tools, ies_dir, fixture, 0.0, Path(tmp), "fx00",
                                    run=lambda *a, **k: None)


class LuxConversionTests(unittest.TestCase):
    def test_achromatic_reflectance_recovers_itself(self):
        # Weights sum to 1.0, so equal R=G=B irradiance divided back through
        # WHTEFFICACY*weights at unit incident lux should reproduce the same
        # figure -- the reasoning `_plastic()` relies on.
        r = g = b = 0.6 / rad.WHTEFFICACY
        self.assertAlmostEqual(rad._lux(r, g, b), 0.6, places=9)

    def test_weights_sum_to_one(self):
        self.assertAlmostEqual(rad.CIE_RF + rad.CIE_GF + rad.CIE_BF, 1.0, places=6)


class IntegrationRegressionTests(unittest.TestCase):
    def test_grid_stays_inside_inset_and_reports_fitted_spacing(self):
        points,excluded,total,dx,dy=rad.grid_points(0,0,4200,3600,inset=150,
            spacing=250,plane_mm=850,boxes=[])
        self.assertTrue(all(150<x<4050 and 150<y<3450 for x,y in points))
        self.assertLessEqual(dx,250)
        self.assertLessEqual(dy,250)
        self.assertEqual(len(points),total-excluded)

    def test_mixed_mesh_and_box_obstacles_survive(self):
        data=bedroom_data()
        data['furniture'].append({'id':'real','meshes':[{'vertices_mm':[[0,0,0],[100,0,0],[0,100,0]],
            'triangles':[[0,1,2]],'material':{'name':'oak'}}]})
        polygons,boxes,proxy_count,missing=rad.furniture_geometry(data)
        self.assertEqual(proxy_count,1)
        self.assertEqual(len(polygons),7)
        self.assertEqual(missing,[])

    def test_nonfinite_output_and_unmeasurable_obstacles_fail(self):
        for output in ('nan 0 0','inf 0 0','-1 0 0'):
            with self.assertRaises(rad.RadianceError):
                rad.parse_rtrace_output(output,1)
        with self.assertRaises(rad.RadianceError):
            rad.furniture_geometry({'furniture':[{'id':'missing'}]})

    def test_joined_rtrace_format_and_explicit_receiver_mode(self):
        argv=rad.rtrace_argv(rad.Tools({'rtrace':Path('/bin/rtrace')},Path('/lib')),Path('/job/scene.oct'),0,1)
        self.assertIn('-faa',argv)
        self.assertIn('-I+',argv)
        self.assertNotIn('-f',argv)
        self.assertNotIn('-i',argv)

    def test_glass_solid_transmittance_is_not_applied_twice(self):
        mesh={'vertices_mm':[[0,0,0],[1000,0,0],[1000,0,1000],[0,0,1000],
                             [0,10,0],[1000,10,0],[1000,10,1000],[0,10,1000]],
              'triangles':[[0,1,2],[0,2,3],[4,6,5],[4,7,6]]}
        surface=rad._glazing_surface(mesh,{'start':[0,0],'end':[1000,0]})
        self.assertEqual(len(surface),2)
        area=sum((rad._dot(rad.polygon_normal(points),rad.polygon_normal(points))**.5)/2
                 for points,_ in surface)
        self.assertAlmostEqual(area,1.0)


class OvercastSkyTests(unittest.TestCase):
    def test_normalization_uses_irradiance_units_and_full_sky(self):
        tools=rad.Tools(bin={'gensky':Path('/bin/gensky')},lib=Path('/lib'))
        argv=rad.gensky_argv(tools,45,0,.2)
        self.assertAlmostEqual(float(argv[argv.index('-B')+1])*179,10000,places=3)
        self.assertIn('sky_glow source sky',rad.sky_glow_text())
        self.assertIn('4 0 0 1 180',rad.sky_glow_text())

    def test_sky_discrepancy_is_a_failed_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            tools=rad.Tools(bin={'oconv':Path('/bin/oconv'),'rtrace':Path('/bin/rtrace')},lib=Path('/lib'))
            def run(argv,*,stdout_path,**kwargs):
                stdout_path.write_text('0 0 0' if Path(argv[0]).name=='rtrace' else 'octree')
            with self.assertRaisesRegex(rad.RadianceError,'sky normalisation'):
                rad.sky_check(tools,root/'sky.rad',root,60,run=run)


class SimulateOrchestrationTests(unittest.TestCase):
    """End-to-end orchestration with a fake `run`, so no Radiance binary is
    required. Exercises geometry-holes, units, source placement and
    physics-check gating all the way through `simulate()`."""

    def _tools_and_install(self, tmp):
        install = Path(tmp) / "install"
        for name in rad.REQUIRED_TOOLS:
            p = install / "bin" / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("#!/bin/sh\n")
        (install / "lib").mkdir(parents=True, exist_ok=True)
        return install

    def _fake_run(self, physics_lux):
        """A fake Radiance toolchain: ies2rad/xform/gensky write plausible
        text, oconv writes a stub octree, rtrace returns canned RGB
        triplets consistent with `physics_lux` and a flat 100 lx room."""

        def run(argv, *, cwd, timeout, stdout_path, stdin_path=None):
            tool = Path(argv[0]).name
            if tool == "ies2rad":
                out_name = argv[argv.index("-o") + 1]
                (cwd / f"{out_name}.rad").write_text("void plastic m 0 0 5 .5 .5 .5 0 0\n")
            elif tool == "xform":
                stdout_path.write_text("void plastic m2 0 0 5 .5 .5 .5 0 0\n")
            elif tool == "oconv":
                stdout_path.write_bytes(b"FAKEOCT")
            elif tool == "gensky":
                stdout_path.write_text("skyfunc glow skyglow\n0\n0\n4 1 1 1 0\n"
                                       "skyglow source sky\n0\n0\n4 0 0 1 180\n")
            elif tool == "rtrace":
                n = len((stdin_path.read_text() if stdin_path else "").splitlines())
                lux=10000 if stdin_path.name=='sky_check_points.txt' else physics_lux
                r = lux / rad.WHTEFFICACY
                stdout_path.write_text(("%.6f %.6f %.6f\n" % (r, r, r)) * max(n, 1))
            else:
                stdout_path.write_text("ok\n")
        return run

    def test_full_pipeline_with_fake_toolchain(self):
        with tempfile.TemporaryDirectory() as tmp:
            install = self._tools_and_install(tmp)
            ies_dir = Path(tmp) / "ies"
            ies_dir.mkdir()
            (ies_dir / "fake.ies").write_text("fake")
            folder = Path(tmp) / "job"
            data = bedroom_data()
            result = rad.simulate(data, folder, install, ies_dir, workers=99,
                                  run=self._fake_run(250.0))
            self.assertTrue(result["passed"])
            self.assertTrue(result["physics_check_passed"])
            self.assertTrue(Path(result["report"]).is_file())
            report = json.loads(Path(result["report"]).read_text())
            self.assertIn("no_compliance_claim", report)
            self.assertEqual(report["workers"], 8)     # clamped from 99
            grid = json.loads(Path(result["electric_ab0_grid"]).read_text())
            self.assertGreater(len(grid["points"]), 0)
            self.assertIn("furniture_proxy_count", grid)

    def test_physics_check_failure_aborts_before_any_grid(self):
        with tempfile.TemporaryDirectory() as tmp:
            install = self._tools_and_install(tmp)
            ies_dir = Path(tmp) / "ies"
            ies_dir.mkdir()
            (ies_dir / "fake.ies").write_text("fake")
            folder = Path(tmp) / "job"
            data = bedroom_data()
            with self.assertRaises(rad.RadianceError):
                rad.simulate(data, folder, install, ies_dir, workers=2,
                            run=self._fake_run(9999.0))   # wildly wrong physics
            self.assertFalse((folder / "electric").is_dir())

    def test_missing_tool_raises_before_touching_the_extract(self):
        with tempfile.TemporaryDirectory() as tmp:
            install = Path(tmp) / "incomplete_install"
            (install / "bin").mkdir(parents=True)
            (install / "bin" / "rtrace").write_text("x")
            (install / "lib").mkdir(parents=True)
            with self.assertRaises(rad.RadianceError):
                rad.Tools.resolve(install)

    def test_wrong_units_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            install = self._tools_and_install(tmp)
            data = bedroom_data(units="feet")
            with self.assertRaises(rad.RadianceError):
                rad.simulate(data, Path(tmp) / "job", install, Path(tmp), run=lambda *a, **k: None)

    def test_multi_room_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            install = self._tools_and_install(tmp)
            data = bedroom_data()
            data["rooms"].append(dict(data["rooms"][0]))
            with self.assertRaises(rad.RadianceError):
                rad.simulate(data, Path(tmp) / "job", install, Path(tmp), run=lambda *a, **k: None)

    def test_real_bedroom_render_schema_is_accepted(self):
        """`out/bedroom-render.json` is the actual joined Revit-geometry-plus-
        photometry extract this module was built to read (per the task's
        schema pointer). If its shape ever drifts from what this adapter
        expects, this is the regression that should catch it."""
        extract_path = (Path(__file__).resolve().parents[1]
                        / "out" / "bedroom-render.json")
        if not extract_path.is_file():
            self.skipTest("out/bedroom-render.json not present in this checkout")
        data = json.loads(extract_path.read_text())
        with tempfile.TemporaryDirectory() as tmp:
            install = self._tools_and_install(tmp)
            ies_dir = Path(tmp) / "ies"
            ies_dir.mkdir()
            for fx in data["lighting"]:
                (ies_dir / fx["ies_file"]).write_text("fake")
            result = rad.simulate(data, Path(tmp) / "job", install, ies_dir, workers=2,
                                  run=self._fake_run(250.0))
            self.assertTrue(result["passed"])

    def test_light_asset_must_be_deployed_basename(self):
        with tempfile.TemporaryDirectory() as tmp:
            install = self._tools_and_install(tmp)
            ies_dir = Path(tmp) / "ies"
            ies_dir.mkdir()
            data = bedroom_data()
            data["lighting"][0]["ies_file"] = "../escape.ies"
            with self.assertRaises(rad.RadianceError):
                rad.simulate(data, Path(tmp) / "job", install, ies_dir, workers=2,
                            run=self._fake_run(250.0))


if __name__ == "__main__":
    unittest.main()
