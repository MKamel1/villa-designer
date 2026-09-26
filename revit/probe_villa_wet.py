# -*- coding: utf-8 -*-
"""Read-only: where the wet rooms of the existing GF are (plumbing fixtures, casework, mechanical equipment, rooms).

The apartment above repeats our GF plan (client), so its bathrooms and kitchen drain down at these positions.

    $env:ARCHPIPE_MODEL = "<abs>\\out\\villa\\omar-2027.rvt"
    $env:ARCHPIPE_WET_OUT = "<abs>\\out\\villa\\omar-wet.json"
    pyrevit run <abs path to this file> --revit=2027
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import extract_model as X                                          # noqa: E402
from probe_villa_inventory import _items, _write                  # noqa: E402
from Autodesk.Revit.DB import BuiltInCategory, FilteredElementCollector, SpatialElement  # noqa: E402


def main():
    doc = X.resolve_doc()
    data = {"plumbing": _items(doc, BuiltInCategory.OST_PlumbingFixtures),
            "casework": _items(doc, BuiltInCategory.OST_Casework),
            "mechanical": _items(doc, BuiltInCategory.OST_MechanicalEquipment),
            "specialty": _items(doc, BuiltInCategory.OST_SpecialityEquipment),
            "rooms": []}
    for r in FilteredElementCollector(doc).OfClass(SpatialElement).ToElements():
        try:
            bb = r.get_BoundingBox(None)
            data["rooms"].append({"name": X._name(r), "area_m2": r.Area * 0.09290304,
                                  "bbox": None if bb is None else [X.mm(bb.Min.X), X.mm(bb.Min.Y), X.mm(bb.Max.X),
                                                                   X.mm(bb.Max.Y)]})
        except Exception as exc:
            data["rooms"].append({"error": str(exc)})
    _write(os.environ["ARCHPIPE_WET_OUT"], data)
    print("archpipe: wrote %s" % os.environ["ARCHPIPE_WET_OUT"])


if __name__ == "__main__":
    main()
