# -*- coding: utf-8 -*-
"""Build the stair options as solids in a COPY of the environment model and let Revit find the clashes.

    $env:ARCHPIPE_MODEL          = "<abs>\\out\\villa\\omar-env.rvt"          (opened, never saved over)
    $env:ARCHPIPE_STAIRS_SPEC    = "<abs>\\out\\villa\\stairs-spec.json"      (scripts/villa_stairs.py spec)
    $env:ARCHPIPE_STAIRS_OUT     = "<abs>\\out\\villa\\omar-stairs.rvt"       (must not exist)
    $env:ARCHPIPE_STAIRS_READBACK= "<abs>\\out\\villa\\stairs-readback.json"
    pyrevit run <abs path to this file> --revit=2027

Treads and landings are DirectShapes in the Stairs category (Generic Models if refused); the 2.0 m headroom
envelopes are Generic Models named "HEADROOM". For every solid, ElementIntersectsSolidFilter lists the structural
columns, structural framing and floors it intersects: Revit's own geometry test, independent of the Python boxes.
"""
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import extract_model as X                                          # noqa: E402
from probe_villa_inventory import _write                           # noqa: E402
import clr                                                          # noqa: E402
clr.AddReference("System")
from System.Collections.Generic import List                         # noqa: E402
from Autodesk.Revit.DB import (BoundingBoxXYZ, BuiltInCategory, CurveLoop, DirectShape, ElementId,  # noqa: E402
                               ElementIntersectsSolidFilter, FilteredElementCollector, GeometryObject, Line,
                               SaveAsOptions, Transaction, UnitTypeId, UnitUtils, View3D, ViewFamily, ViewFamilyType,
                               XYZ, ImageExportOptions, ExportRange, ImageFileType, ImageResolution, ZoomFitType,
                               FitDirectionType, DisplayStyle)
from Autodesk.Revit.DB import GeometryCreationUtilities as GCU      # noqa: E402


def ft(v):
    return UnitUtils.ConvertToInternalUnits(float(v), UnitTypeId.Millimeters)


def solid(b):
    x0, y0, z0, x1, y1, z1 = b
    lp = CurveLoop()
    pts = [XYZ(ft(x0), ft(y0), ft(z0)), XYZ(ft(x1), ft(y0), ft(z0)), XYZ(ft(x1), ft(y1), ft(z0)),
           XYZ(ft(x0), ft(y1), ft(z0))]
    for i in range(4):
        lp.Append(Line.CreateBound(pts[i], pts[(i + 1) % 4]))
    loops = List[CurveLoop]()
    loops.Add(lp)
    return GCU.CreateExtrusionGeometry(loops, XYZ.BasisZ, ft(z1 - z0))


def shape(doc, cat, name, solids):
    cid = ElementId(cat)
    if not DirectShape.IsValidCategoryId(cid, doc):
        cid = ElementId(BuiltInCategory.OST_GenericModel)
    ds = DirectShape.CreateElement(doc, cid)
    ds.ApplicationId = "archpipe-stairs"
    ds.ApplicationDataId = name
    g = List[GeometryObject]()
    for s in solids:
        g.Add(s)
    ds.SetShape(g)
    ds.Name = name
    return ds


def main():
    spec = json.load(open(os.environ["ARCHPIPE_STAIRS_SPEC"]))
    dest = os.environ["ARCHPIPE_STAIRS_OUT"]
    if os.path.exists(dest):
        raise Exception("refusing to overwrite %s" % dest)
    doc = X.resolve_doc()
    t = Transaction(doc, "archpipe: stair options")
    t.Start()
    built = []
    for opt in spec["options"]:
        body = [p for p in opt["parts"] if "headroom" not in p["what"]]
        head = [p for p in opt["parts"] if "headroom" in p["what"]]
        ds_body = shape(doc, BuiltInCategory.OST_Stairs, "STAIR " + opt["name"], [solid(p["box"]) for p in body])
        ds_head = shape(doc, BuiltInCategory.OST_GenericModel, "HEADROOM " + opt["name"],
                        [solid(p["box"]) for p in head])
        built.append((opt, ds_body, ds_head, body, head))
    t.Commit()

    out = {"options": []}
    cats = [("column", BuiltInCategory.OST_StructuralColumns), ("framing", BuiltInCategory.OST_StructuralFraming),
            ("floor", BuiltInCategory.OST_Floors)]
    for opt, ds_body, ds_head, body, head in built:
        rows = []
        for part in body + head:
            s = solid(part["box"])
            for kind, bic in cats:
                ids = FilteredElementCollector(doc).OfCategory(bic).WhereElementIsNotElementType().WherePasses(
                    ElementIntersectsSolidFilter(s)).ToElementIds()
                for i in ids:
                    el = doc.GetElement(i)
                    rows.append({"part": part["what"], "kind": kind, "id": int(str(i)),
                                 "name": X._name(el), "comment": _comment(el)})
        out["options"].append({"name": opt["name"], "body_id": int(str(ds_body.Id)), "head_id": int(str(ds_head.Id)),
                               "intersections": rows})
    opts = SaveAsOptions()
    opts.OverwriteExistingFile = False
    doc.SaveAs(dest, opts)
    out["saved"] = dest
    t = Transaction(doc, "archpipe: stair views")
    t.Start()
    views = []
    vft = [v for v in FilteredElementCollector(doc).OfClass(ViewFamilyType) if v.ViewFamily == ViewFamily.ThreeDimensional][0]
    for opt, ds_body, ds_head, body, head in built:
        xs = [p["box"][0] for p in opt["parts"]] + [p["box"][3] for p in opt["parts"]]
        ys = [p["box"][1] for p in opt["parts"]] + [p["box"][4] for p in opt["parts"]]
        v = View3D.CreateIsometric(doc, vft.Id)
        try:
            v.Name = "STAIR " + opt["name"][:40]
        except Exception:
            pass
        bb = BoundingBoxXYZ()
        bb.Min = XYZ(ft(min(xs) - 1200), ft(-28900), ft(-3300))
        bb.Max = XYZ(ft(max(xs) + 1200), ft(-23300), ft(-250))       # cut just under the GF slab: stairs visible
        v.SetSectionBox(bb)
        v.DisplayStyle = DisplayStyle.ShadingWithEdges
        for hide in (BuiltInCategory.OST_GenericModel, BuiltInCategory.OST_Mass):
            try:
                v.SetCategoryHidden(ElementId(hide), True)           # headroom envelopes and context masses
            except Exception:
                pass
        others = List[ElementId]()
        for o2, b2, h2, _, _ in built:
            if o2 is not opt:
                others.Add(b2.Id)
                others.Add(h2.Id)
        if others.Count:
            v.HideElements(others)                                    # one stair option per view
        views.append(v)
    t.Commit()
    folder = os.path.dirname(os.environ["ARCHPIPE_STAIRS_READBACK"])
    for v in views:
        try:
            o = ImageExportOptions()
            o.ExportRange = ExportRange.SetOfViews
            ids = List[ElementId]()
            ids.Add(v.Id)
            o.SetViewsAndSheets(ids)
            o.FilePath = os.path.join(folder, "stairs-view")
            o.HLRandWFViewsFileType = ImageFileType.PNG
            o.ShadowViewsFileType = ImageFileType.PNG
            o.ImageResolution = ImageResolution.DPI_150
            o.ZoomType = ZoomFitType.FitToPage
            o.FitDirection = FitDirectionType.Horizontal
            o.PixelSize = 1800
            doc.ExportImage(o)
        except Exception as exc:
            out.setdefault("image_errors", []).append(str(exc))
    _write(os.environ["ARCHPIPE_STAIRS_READBACK"], out)
    print("archpipe: wrote %s" % os.environ["ARCHPIPE_STAIRS_READBACK"])


def _comment(el):
    try:
        from Autodesk.Revit.DB import BuiltInParameter
        p = el.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
        return p.AsString() if p is not None else None
    except Exception:
        return None


if __name__ == "__main__":
    main()
