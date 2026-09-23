# -*- coding: utf-8 -*-
"""Build a Revit model with KNOWN dimensions, to test the extractor against.

The point is not to have a model. It is to have a model whose true
measurements are known independently of the thing being tested. An
extractor checked only against "it did not crash" can be silently wrong
by a factor of 304.8 (feet vs millimetres) and look perfectly healthy.

Geometry, all on wall CENTRELINES, in millimetres:

    (0,0) ---- 6000 ---- (6000,0)
      |                     |
     4000                  4000
      |                     |
    (0,4000) -- 6000 -- (6000,4000)

So: 4 walls, 2 of length 6000 and 2 of length 4000, one enclosed room.
The room's area depends on the template's default wall thickness, so the
checker derives the expected area from the extracted thickness rather
than hard-coding it.

    pyrevit run revit\\build_test_model.py --revit=2027

Writes the .rvt to ARCHPIPE_TEST_MODEL, else the user profile.
IronPython 2.7: no f-strings, no type hints.
"""
import os

from Autodesk.Revit.DB import (
    FilteredElementCollector, Level, Line, SaveAsOptions, Transaction,
    UnitTypeId, UnitUtils, UV, Wall, XYZ,
)

def _find_template():
    """Locate a metric project template, without hard-coding a machine.

    ARCHPIPE_REVIT_TEMPLATE overrides. Otherwise take the newest RVT
    version folder that has the metric English template.
    """
    override = os.environ.get("ARCHPIPE_REVIT_TEMPLATE")
    if override:
        return override
    root = r"C:\ProgramData\Autodesk"
    found = []
    if os.path.isdir(root):
        for name in os.listdir(root):
            if not name.startswith("RVT "):
                continue
            cand = os.path.join(root, name, "Templates", "Default_M_ENU.rte")
            if os.path.isfile(cand):
                found.append((name, cand))
    found.sort(reverse=True)
    return found[0][1] if found else ""


TEMPLATE = _find_template()

# The known truth this test rests on.
WIDTH_MM = 6000.0
DEPTH_MM = 4000.0


def ft(mm_value):
    """Millimetres -> Revit internal units (decimal feet)."""
    return UnitUtils.ConvertToInternalUnits(mm_value, UnitTypeId.Millimeters)


def main():
    app = __revit__.Application                       # noqa: F821
    dest = os.environ.get("ARCHPIPE_TEST_MODEL")
    if not dest:
        dest = os.path.join(os.path.expanduser("~"), "archpipe_test.rvt")

    if not os.path.isfile(TEMPLATE):
        print("archpipe: template not found: %s" % TEMPLATE)
        return

    doc = app.NewProjectDocument(TEMPLATE)

    levels = sorted(
        FilteredElementCollector(doc).OfClass(Level).ToElements(),
        key=lambda l: l.Elevation)
    if not levels:
        print("archpipe: template has no levels")
        return
    base = levels[0]

    w, d = ft(WIDTH_MM), ft(DEPTH_MM)
    corners = [XYZ(0, 0, 0), XYZ(w, 0, 0), XYZ(w, d, 0), XYZ(0, d, 0)]

    t = Transaction(doc, "archpipe test geometry")
    t.Start()
    made = []
    try:
        for i in range(4):
            line = Line.CreateBound(corners[i], corners[(i + 1) % 4])
            made.append(Wall.Create(doc, line, base.Id, False))
        doc.Regenerate()

        # A room needs an enclosed loop and a phase; put it at the centre.
        try:
            room = doc.Create.NewRoom(base, UV(w / 2.0, d / 2.0))
            if room is not None:
                room.Name = "Test Room"
        except Exception as exc:
            print("archpipe: room creation failed: %s" % exc)
        t.Commit()
    except Exception as exc:
        t.RollBack()
        print("archpipe: geometry failed: %s: %s" % (type(exc).__name__, exc))
        return

    opts = SaveAsOptions()
    opts.OverwriteExistingFile = True
    doc.SaveAs(dest, opts)
    doc.Close(False)

    print("archpipe: wrote %s" % dest)
    print("archpipe: %d walls, expected lengths %.0f x %.0f mm on centrelines"
          % (len(made), WIDTH_MM, DEPTH_MM))


main()
