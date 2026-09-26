# -*- coding: utf-8 -*-
"""Read back and picture the kept NE yard wall (client 2026-09-26) in a built option model, never saving it.

    $env:ARCHPIPE_MODEL = "<abs>\\out\\villa\\options-r7\\omar-option-P1.rvt"
    $env:ARCHPIPE_OUT   = "<abs>\\out\\villa\\yard-wall"          (folder: yard-wall-readback.json + PNGs)
    pyrevit run <abs path to this file> --revit=2027

Read-back: bounding boxes (mm) of the wall, the north-east column, the street and east fences, the ramp and the yard
floor, as Revit holds them. Views: basement plan crop, a section along the wall, a section across it, a 3D view.
"""
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from probe_villa_inventory import _write                            # noqa: E402
from Autodesk.Revit.DB import (BoundingBoxXYZ, BuiltInCategory, DirectShape, ElementId, ExportRange,  # noqa: E402
                               FilteredElementCollector, FitDirectionType, ImageExportOptions, ImageFileType,
                               ImageResolution, Level, Transaction, Transform, UnitTypeId, UnitUtils, View3D,
                               ViewDetailLevel, ViewFamily, ViewFamilyType, ViewOrientation3D, ViewPlan, ViewSection,
                               XYZ, ZoomFitType, DisplayStyle, FillPatternElement,
                               OverrideGraphicSettings, Color)
from System.Collections.Generic import List                         # noqa: E402


def ft(v_mm):
    return UnitUtils.ConvertToInternalUnits(float(v_mm), UnitTypeId.Millimeters)


def mm(v_ft):
    return round(UnitUtils.ConvertFromInternalUnits(v_ft, UnitTypeId.Millimeters), 1)


def bb(el):
    b = el.get_BoundingBox(None)
    return [mm(b.Min.X), mm(b.Min.Y), mm(b.Min.Z), mm(b.Max.X), mm(b.Max.Y), mm(b.Max.Z)]


def box(lo, hi):
    b = BoundingBoxXYZ()
    b.Min, b.Max = XYZ(*[ft(v) for v in lo]), XYZ(*[ft(v) for v in hi])
    return b


def vtype(doc, fam):
    return [v for v in FilteredElementCollector(doc).OfClass(ViewFamilyType) if v.ViewFamily == fam][0].Id


def main():
    app = __revit__.Application                                    # noqa: F821
    out = os.environ["ARCHPIPE_OUT"]
    if not os.path.isdir(out):
        os.makedirs(out)
    doc = app.OpenDocumentFile(os.environ["ARCHPIPE_MODEL"])
    rb = {"model": os.environ["ARCHPIPE_MODEL"], "elements": {}}
    for ds in FilteredElementCollector(doc).OfClass(DirectShape):
        key = ds.ApplicationDataId
        if key in ("yard-wall-ne", "fence-street", "fence-east", "ramp", "deck", "car-0"):
            rb["elements"][key] = bb(ds)
    cols = []
    for c in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_StructuralColumns) \
            .WhereElementIsNotElementType():
        b = bb(c)
        if 3500 < b[0] < 3700 and b[4] > -24300 and b[4] < -23500:
            cols.append({"id": int(str(c.Id)), "bbox": b})
    rb["ne_columns"] = cols
    for f in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Floors).WhereElementIsNotElementType():
        try:
            b = bb(f)
        except Exception:
            continue
        if b[0] < 0 and b[4] > -23000 and b[5] < -2000:             # the sunken yard floor under the NE corner
            rb["elements"].setdefault("yard-floor", b)
    rb["levels"] = dict((l.Name, mm(l.Elevation)) for l in FilteredElementCollector(doc).OfClass(Level))

    t = Transaction(doc, "archpipe yard wall views")
    t.Start()
    views = {}
    lv = [l for l in FilteredElementCollector(doc).OfClass(Level) if l.Name == "B -1.80"][0]
    p = ViewPlan.Create(doc, vtype(doc, ViewFamily.FloorPlan), lv.Id)
    p.CropBox = box((-1500, -29000, -10000), (8000, -20000, 10000))
    p.CropBoxActive, p.CropBoxVisible = True, False
    p.Scale, p.DetailLevel = 50, ViewDetailLevel.Fine
    views["plan"] = p
    # sections: BasisX = right, BasisY = up, BasisZ = looking direction (right x up = direction)
    for key, origin, right, direction, w_lo, w_hi, depth in (
            ("section-along", (1747, -23766, 0), XYZ(1, 0, 0), XYZ(0, -1, 0), -3500, 6500, 2500),
            ("section-across", (1800, -23300, 0), XYZ(0, 1, 0), XYZ(1, 0, 0), -3500, 3300, 2500)):
        tr = Transform.Identity
        tr.Origin = XYZ(*[ft(v) for v in origin])
        tr.BasisX, tr.BasisY, tr.BasisZ = right, XYZ.BasisZ, direction
        b = box((w_lo, -3600, 0), (w_hi, 1800, depth))
        b.Transform = tr
        v = ViewSection.CreateSection(doc, vtype(doc, ViewFamily.Section), b)
        v.Scale, v.DetailLevel = 50, ViewDetailLevel.Fine
        v.CropBoxVisible = False
        views[key] = v
    v = View3D.CreateIsometric(doc, vtype(doc, ViewFamily.ThreeDimensional))
    d = XYZ(0.55, -1.0, -0.9).Normalize()        # from the east yard, above
    centre = XYZ(ft(2000), ft(-23500), ft(-2000))
    eye = centre - d * ft(20000)
    up = (XYZ.BasisZ - d * XYZ.BasisZ.DotProduct(d)).Normalize()
    v.SetOrientation(ViewOrientation3D(eye, up, d))
    v.SetSectionBox(box((-600, -27500, -3300), (7000, -20400, -1050)))   # cut just above street level
    v.DisplayStyle = DisplayStyle.ShadingWithEdges
    try:
        v.SetCategoryHidden(ElementId(BuiltInCategory.OST_Levels), True)
    except Exception:
        pass
    hide = List[ElementId]()
    for ds in FilteredElementCollector(doc).OfClass(DirectShape):
        if ds.ApplicationId == "archpipe-env" and ds.ApplicationDataId != "yard-wall-ne":
            hide.Add(ds.Id)                                      # context blocks, fences and beams: clutter here
    v.HideElements(hide)                                         # only the wall, the villa and the ramp remain
    solid = [f for f in FilteredElementCollector(doc).OfClass(FillPatternElement) if f.GetFillPattern().IsSolidFill][0]
    for ds in FilteredElementCollector(doc).OfClass(DirectShape):
        o = OverrideGraphicSettings()
        if ds.ApplicationDataId == "yard-wall-ne":                 # the wall in solid red, unmistakable
            o.SetSurfaceForegroundPatternId(solid.Id)
            o.SetSurfaceForegroundPatternColor(Color(210, 35, 35))
            v.SetElementOverrides(ds.Id, o)
        elif ds.ApplicationDataId in ("ramp", "deck"):             # see-through, so the wall under it shows
            o.SetSurfaceTransparency(65)
            v.SetElementOverrides(ds.Id, o)
    views["3d"] = v
    t.Commit()
    for key, view in views.items():
        o = ImageExportOptions()
        o.ExportRange = ExportRange.SetOfViews
        ids = List[ElementId]()
        ids.Add(view.Id)
        o.SetViewsAndSheets(ids)
        o.FilePath = os.path.join(out, "yard-wall-" + key)
        o.HLRandWFViewsFileType = o.ShadowViewsFileType = ImageFileType.PNG
        o.ImageResolution = ImageResolution.DPI_300
        o.ZoomType = ZoomFitType.FitToPage
        o.FitDirection = FitDirectionType.Horizontal
        o.PixelSize = 2400
        try:
            doc.ExportImage(o)
        except Exception as exc:
            rb.setdefault("failed", []).append({"image": key, "error": str(exc)})
    doc.Close(False)                                              # never saved
    _write(os.path.join(out, "yard-wall-readback.json"), rb)
    print("archpipe: yard wall read-back %s" % json.dumps(rb["elements"].get("yard-wall-ne")))


main()
