# -*- coding: utf-8 -*-
"""L5 probe: can Revit 2027 run headless from the shell and open a copy of the D1 model?

ARCHPIPE_MODEL = absolute path of a COPY; ARCHPIPE_PROBE_OUT = json path.
Read-only: opens, counts, closes without saving.
"""
import json
import os
import traceback

from Autodesk.Revit.DB import BuiltInCategory, FilteredElementCollector, Level, View, ViewSheet


def main():
    out = os.environ["ARCHPIPE_PROBE_OUT"]
    res = {"stage": "start"}
    try:
        app = __revit__.Application  # noqa: F821
        res["revit_version"] = app.VersionNumber
        res["docs_open_before"] = len(list(app.Documents))
        doc = app.OpenDocumentFile(os.environ["ARCHPIPE_MODEL"])
        res["title"] = doc.Title
        res["levels"] = [l.Name for l in FilteredElementCollector(doc).OfClass(Level)]

        def n(c):
            return len(list(FilteredElementCollector(doc).OfCategory(c).WhereElementIsNotElementType()))
        for k, c in [("rooms", BuiltInCategory.OST_Rooms), ("doors", BuiltInCategory.OST_Doors),
                     ("windows", BuiltInCategory.OST_Windows), ("walls", BuiltInCategory.OST_Walls),
                     ("grids", BuiltInCategory.OST_Grids)]:
            res[k] = n(c)
        res["views"] = len([v for v in FilteredElementCollector(doc).OfClass(View) if not v.IsTemplate])
        res["sheets"] = len(list(FilteredElementCollector(doc).OfClass(ViewSheet)))
        res["titleblock_types"] = len(list(FilteredElementCollector(doc).OfCategory(
            BuiltInCategory.OST_TitleBlocks).WhereElementIsElementType()))
        doc.Close(False)
        res["stage"] = "done"
    except Exception:
        res["error"] = traceback.format_exc()
    with open(out, "w") as f:
        json.dump(res, f, indent=2)
    print("L5 PROBE " + json.dumps(res))


main()
