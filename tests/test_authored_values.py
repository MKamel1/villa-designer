"""Authored fields survive later passes unless the change is explained."""

import copy
import unittest
from unittest.mock import patch

from archpipe.concept.authored_guard import unexplained_changes
from archpipe.concept.authored_values import fill_defaults, override
from archpipe.concept import revit_spec as RS, villa_furnish as F, villa_r11 as R, villa_render as VR


class AuthoredValues(unittest.TestCase):
    def test_defaults_preserve_explicit_values_and_override_requires_reason(self):
        record = {"none": None, "zero": 0, "empty": []}
        fill_defaults(record, {"none": 1, "zero": 2, "empty": [3], "absent": 4})
        self.assertEqual(record, {"none": None, "zero": 0, "empty": [], "absent": 4})
        with self.assertRaises(ValueError):
            override(record, "zero", 2, " ")
        override(record, "zero", 2, "measured replacement")
        self.assertEqual(record["overrides"], [{"field": "zero", "prior": 0, "new": 2,
                                                 "reason": "measured replacement"}])
        self.assertEqual(unexplained_changes({"zero": 0}, record, ("zero",)), [])

    def test_frozen_camera_failures_and_sibling_mutation_fire(self):
        # Frozen historical declarations and failed exports, independent of today's view builder.
        self.assertEqual(unexplained_changes({"lens_mm": 16}, {"lens_mm": 24}, ("lens_mm",)), ["lens_mm"])
        self.assertEqual(unexplained_changes({"shift_y": 0.10}, {"shift_y": 0}, ("shift_y",)), ["shift_y"])
        declared = {"width": 0.9, "sliding": False}
        written = copy.deepcopy(declared)
        written["width"] = 0.8
        self.assertEqual(unexplained_changes(declared, written, ("width", "sliding")), ["width"])

    def test_every_exported_camera_field_has_declared_value_or_override(self):
        lay = R.design("D1")
        declared = {v["id"]: v for v in VR.VIEWS(lay, resolve=False)}
        exported = {v["id"]: v for v in VR.build(lay)["views"]}
        self.assertEqual(set(declared), set(exported))
        for vid, view in exported.items():
            source = declared[vid]
            self.assertEqual(unexplained_changes(source["camera"], view["camera"], source["camera"]), [], vid)
            self.assertEqual(unexplained_changes(source, view,
                             ("dimmers", "exposure", "layers_on", "hide_meshes")), [], vid)

    def test_door_width_and_type_track_initial_spec_on_supported_options(self):
        for option in ("D1", "D2", "D3"):
            with self.subTest(option=option):
                lay = R.design(option)
                with patch.object(RS, "_clear_columns", lambda spec: None), \
                     patch.object(RS, "_d1_details", lambda lay, spec: None):
                    declared = RS.build(lay)["doors"]
                written = RS.build(lay)["doors"]
                def identity(door):
                    return (door["level"], tuple(door["rooms"]), door.get("garden", False),
                            door.get("entrance", False), tuple(door.get("span", [])))
                sources = {identity(door): door for door in declared}
                self.assertEqual(len(sources), len(declared))
                for after in written:
                    before = sources[identity(after)]
                    self.assertEqual(unexplained_changes(before, after,
                                     ("width", "sliding", "slide_type", "leaf_count", "panel_width")), [],
                                     (option, after["rooms"]))

    def test_furniture_dimensions_match_catalogue_or_reasoned_product_fit(self):
        lay = R.design("D1")
        declared = {item["id"]: item for item in F.layout(lay, products=False)}
        written = {item["id"]: item for item in F.layout(lay)}
        self.assertEqual(set(declared), set(written))
        for iid, item in written.items():
            self.assertEqual(unexplained_changes(declared[iid], item, ("w", "d", "h")), [], iid)
            if item.get("product"):
                source = F.PRODUCT[iid]
                for field in ("w", "d", "h"):
                    self.assertEqual(item[field], source[field], (iid, field))


if __name__ == "__main__":
    unittest.main()
