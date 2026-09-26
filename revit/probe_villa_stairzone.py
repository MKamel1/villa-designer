# -*- coding: utf-8 -*-
"""Read-only: what the built model says about the stair zone and the street strip (omar-2027.rvt).

Floor sketch loops (outer + openings), opening elements, and every element whose bounding box touches the street
strip (x 1.6-4.2 m) or the old stair bay (x 7.0-9.6 m), with category, type, levels and z range.

    $env:ARCHPIPE_MODEL = "<abs>\\out\\villa\\omar-2027.rvt"
    $env:ARCHPIPE_STAIRZONE_OUT = "<abs>\\out\\villa\\omar-stairzone.json"
    pyrevit run <abs path to this file> --revit=2027
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import extract_model as X                                          # noqa: E402
from probe_villa_inventory import _write                           # noqa: E402
from Autodesk.Revit.DB import (BuiltInCategory, ElementId, FilteredElementCollector, Floor, Opening)  # noqa: E402


def _eid(i):
    from System import Int64
    return ElementId(Int64(i))


def bb(el):
    b = el.get_BoundingBox(None)
    return None if b is None else [X.mm(b.Min.X), X.mm(b.Min.Y), X.mm(b.Min.Z), X.mm(b.Max.X), X.mm(b.Max.Y),
                                   X.mm(b.Max.Z)]


def loops_of(doc, fl):
    out = []
    try:
        sk = doc.GetElement(fl.SketchId)
        for arr in sk.Profile:
            pts = []
            for c in arr:
                p = c.GetEndPoint(0)
                pts.append([X.mm(p.X), X.mm(p.Y)])
            out.append(pts)
    except Exception as exc:
        out.append({"error": str(exc)})
    return out


def main():
    doc = X.resolve_doc()
    data = {"floors": [], "openings": [], "strip": [], "stair_bay": []}
    for fl in FilteredElementCollector(doc).OfClass(Floor).ToElements():
        data["floors"].append({"id": int(str(fl.Id)), "type": X._name(doc.GetElement(fl.GetTypeId())),
                               "bbox": bb(fl), "loops": loops_of(doc, fl)})
    for op in FilteredElementCollector(doc).OfClass(Opening).ToElements():
        data["openings"].append({"id": int(str(op.Id)), "category": op.Category.Name if op.Category else None,
                                 "bbox": bb(op)})
    for el in FilteredElementCollector(doc).WhereElementIsNotElementType().ToElements():
        b = bb(el)
        if b is None or el.Category is None:
            continue
        cat = el.Category.Name
        if cat in ("Views", "Sun Path", "Cameras", "Elevations", "Section Boxes", "Levels", "Lines"):
            continue
        row = {"id": int(str(el.Id)), "category": cat, "name": X._name(el), "bbox": [round(v) for v in b]}
        try:
            t = doc.GetElement(el.GetTypeId())
            row["type"] = X._name(t) if t is not None else None
        except Exception:
            pass
        if b[3] > 1600 and b[0] < 4200 and b[4] > -29000 and b[1] < -23000:
            data["strip"].append(row)
        if b[3] > 7000 and b[0] < 9600 and b[4] > -29000 and b[1] < -23000:
            data["stair_bay"].append(row)
    _write(os.environ["ARCHPIPE_STAIRZONE_OUT"], data)
    print("archpipe: wrote %s" % os.environ["ARCHPIPE_STAIRZONE_OUT"])


if __name__ == "__main__":
    main()
