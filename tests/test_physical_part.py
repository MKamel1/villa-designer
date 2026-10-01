"""C3 constructor regressions using frozen shapes from villa scene parts."""
import unittest

from archpipe.concept.physical_part import Part, PartError, PartMeshList
from archpipe.concept.villa_render import box_faces, disc_down


class PhysicalPartBoundary(unittest.TestCase):
    def part(self, kind, faces, **kwargs):
        return Part(kind, faces, ("x", "y", "z"), "brass", "authored-procedural", **kwargs)

    def test_historical_rectangular_proxies_fire(self):
        cases = (
            ("climber", box_faces(0, 0, 0.30, 0.08, 0.08, 2.0)),
            ("garment", box_faces(0, 0, 0, 0.42, 0.025, 0.80)),
            ("rain-head", box_faces(-0.16, -0.16, -0.014, 0.16, 0.16, 0.014)),
        )
        for kind, faces in cases:
            with self.subTest(kind=kind), self.assertRaisesRegex(PartError, "bare rectangular proxy"):
                self.part(kind, faces)

    def test_zero_area_triangle_and_inward_headboard_fire(self):
        collapsed = box_faces(0, 0, 0, 1, 1, 1)
        collapsed[0] = [collapsed[0][0], collapsed[0][0], collapsed[0][2]]
        with self.assertRaisesRegex(PartError, "zero-area triangle"):
            self.part("headboard", collapsed)
        # The historical headboard had a closed connected surface with reversed winding.
        inward = [face[::-1] for face in box_faces(0, 0, 0, 1, 0.1, 1)]
        with self.assertRaisesRegex(PartError, "inward-facing solid"):
            self.part("headboard", inward)

    def test_duvet_stays_on_its_declared_mattress(self):
        with self.assertRaisesRegex(PartError, "duvet leaves mattress footprint"):
            self.part("duvet", box_faces(0.6, 0, 0.5, 1.6, 1, 0.6), support=(0, 0, 1, 1))
        with self.assertRaisesRegex(PartError, "duvet intersects mattress support"):
            self.part("duvet", box_faces(0, 0, 0.45, 1, 1, 0.55), support=(0, 0, 0, 1, 1, 0.5))

    def test_real_rectangular_carcass_and_measured_gltf_are_quiet(self):
        self.part("cabinet-carcass", box_faces(0, 0, 0, 0.6, 0.4, 2.0))
        self.part("door-leaf", box_faces(0, 0, 0, 0.9, 0.04, 2.1))
        Part("plant", None, ("x", "y", "z"), "leaf", "measured-gltf")

    def test_undeclared_kind_and_box_rail_fail(self):
        with self.assertRaisesRegex(PartError, "requires kind"):
            self.part(None, box_faces(0, 0, 0, 1, 1, 1))
        with self.assertRaisesRegex(PartError, "undeclared part kind"):
            PartMeshList(collect=True).append(dict(id="wardrobe-rail", material="brass",
                                                   faces=box_faces(0, 0, 0, 1, .02, .02)))
        with self.assertRaisesRegex(PartError, "bare rectangular proxy for hanging-rail"):
            self.part("hanging-rail", box_faces(0, 0, 0, 1, .02, .02))

    def test_single_sided_surface_faces_occupied_side(self):
        floor = [[[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]]]
        self.part("finish-layer", floor, surface=True, occupied_side=(0, 0, 1))
        with self.assertRaisesRegex(PartError, "surface normal faces away"):
            self.part("finish-layer", [floor[0][::-1]],
                      surface=True, occupied_side=(0, 0, 1))

    def test_real_downlight_trim_generator_is_closed_and_outward(self):
        # The D1 downlight trim used to be a single open disc; freeze its measured radius.
        self.part("downlight-trim", disc_down(17.2, -27.1, 2.6985, 0.0415))
        inward = [face[::-1] for face in disc_down(17.2, -27.1, 2.6985, 0.0415)]
        with self.assertRaisesRegex(PartError, "inward-facing solid"):
            self.part("downlight-trim", inward)

    def test_glass_pane_requires_closed_thickness(self):
        pane = box_faces(0, 0, 0, 1, .01, 2)
        self.part("glass-pane", pane)
        with self.assertRaisesRegex(PartError, "glass pane must be a closed solid"):
            self.part("glass-pane", [pane[0]], surface=True, occupied_side=(0, 0, -1))
        with self.assertRaisesRegex(PartError, "open or inconsistently wound edges"):
            self.part("glass-pane", pane[:-1])

    def test_sink_collects_every_failure_and_strict_sink_raises(self):
        record = dict(id="detail-gwc-rain-head-plate", label="ASSUMED ceiling rain-head plate",
                      room="guest-wc", material="brass", part_kind="rain-head",
                      faces=box_faces(0, 0, 0, .32, .32, .028))
        sink = PartMeshList(collect=True)
        sink.append(record)
        self.assertEqual(sink.failures[0]["kind"], "rain-head")
        self.assertEqual(sink.failures[0]["room"], "guest-wc")
        with self.assertRaises(PartError):
            PartMeshList().append(record)


if __name__ == "__main__":
    unittest.main()
