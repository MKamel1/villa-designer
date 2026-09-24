# -*- coding: utf-8 -*-
"""Create native review views, sheets, PDF and a read-back markup example.

ARCHPIPE_MODEL is an existing model. ARCHPIPE_VIEWS_OUT is the output
folder. This modifies that model, so run on the generated example or a
deliberately selected copy. Only views prefixed ARCHPIPE are managed here.
"""
import json
import os
import sys
import traceback

from Autodesk.Revit.DB import (
    BoundingBoxXYZ, BuiltInCategory, BuiltInParameter, Curve, ElementId, ElevationMarker,
    ElementTypeGroup,
    ExportPaperFormat, PageOrientationType, ExportRange, FilteredElementCollector,
    ImageExportOptions, ImageFileType, Line, PDFExportOptions,
    Revision, RevisionCloud, SaveOptions, TextNote, TextNoteOptions,
    Transaction, Transform, UnitTypeId, UnitUtils, View, View3D,
    ViewDetailLevel, ViewFamily, ViewFamilyType, ViewOrientation3D,
    ViewPlan, Viewport, ViewSection, ViewSheet, XYZ, ZoomType,
)
from System.Collections.Generic import List

sys.path.insert(0, os.path.dirname(__file__))
from extract_model import resolve_doc, mm


def ft(value):
    return UnitUtils.ConvertToInternalUnits(float(value), UnitTypeId.Millimeters)


def box(lo, hi):
    b = BoundingBoxXYZ()
    b.Min, b.Max = XYZ(*[ft(v) for v in lo]), XYZ(*[ft(v) for v in hi])
    return b


def main():
    doc = resolve_doc()
    if doc is None:
        raise RuntimeError('Set ARCHPIPE_MODEL to a saved project')
    dest = os.environ['ARCHPIPE_VIEWS_OUT']
    if not os.path.isdir(dest):
        os.makedirs(dest)
    report = {'views': [], 'sheets': [], 'errors': []}
    tx = Transaction(doc, 'archpipe: native review deliverables')
    tx.Start()
    # Re-running replaces only our generated presentation views, never
    # client-created views or annotations in them.
    old = [v.Id for v in FilteredElementCollector(doc).OfClass(View)
           if not v.IsTemplate and v.Name.startswith('ARCHPIPE ')]
    for vid in old:
        if doc.GetElement(vid):
            doc.Delete(vid)
    types = list(FilteredElementCollector(doc).OfClass(ViewFamilyType))
    def vtype(family):
        return next(t.Id for t in types if t.ViewFamily == family)
    rooms = list(FilteredElementCollector(doc).OfCategory(
        BuiltInCategory.OST_Rooms).WhereElementIsNotElementType())
    room = next(r for r in rooms if r.Area > 0)
    rb = room.get_BoundingBox(None)
    x0, y0 = mm(rb.Min.X), mm(rb.Min.Y)
    x1, y1 = mm(rb.Max.X), mm(rb.Max.Y)
    h = 2700.0
    views = []
    for family, label in [(ViewFamily.FloorPlan, 'Floor plan'),
                          (ViewFamily.CeilingPlan, 'Reflected ceiling plan')]:
        v = ViewPlan.Create(doc, vtype(family), room.LevelId)
        v.Name = 'ARCHPIPE ' + label
        v.Scale = 50
        v.CropBox = box((x0-500, y0-500, -500), (x1+500, y1+500, h+500))
        v.CropBoxActive, v.CropBoxVisible = True, False
        views.append(v)
    plan = views[0]
    # Sections use local right/up/view axes. The first two look at the
    # inside wall faces; the third cuts across the bed.
    for label, origin, right, direction, width, depth in [
        ('Bedroom section', ((x0+x1)/2, (y0+y1)/2, 0), XYZ(1,0,0), XYZ(0,1,0), x1-x0+600, (y1-y0)/2+400),
    ]:
        tr = Transform.Identity
        tr.Origin = XYZ(*[ft(v) for v in origin])
        tr.BasisX, tr.BasisY, tr.BasisZ = right, XYZ.BasisZ, direction
        b = box((-width/2, -400, 0), (width/2, h+400, depth))
        b.Transform = tr
        v = ViewSection.CreateSection(doc, vtype(ViewFamily.Section), b)
        v.Name, v.Scale = 'ARCHPIPE ' + label, 50
        v.CropBoxVisible = False
        views.append(v)
    marker = ElevationMarker.CreateElevationMarker(
        doc, vtype(ViewFamily.Elevation),
        XYZ(ft((x0+x1)/2), ft((y0+y1)/2), 0), 50)
    for index in range(4):
        ev = marker.CreateElevation(doc, plan.Id, index)
        direction = ev.ViewDirection
        # ViewDirection points toward the viewer, opposite the wall
        # being viewed. Choosing its positive direction mislabels walls.
        label = ('North' if direction.Y < -0.9 else
                 'East' if direction.X < -0.9 else None)
        if label is None:
            doc.Delete(ev.Id)
            continue
        ev.Name = 'ARCHPIPE ' + label + ' interior elevation'
        ev.CropBoxVisible = False
        views.insert(-1, ev)
    v = View3D.CreateIsometric(doc, vtype(ViewFamily.ThreeDimensional))
    v.Name = 'ARCHPIPE 3D cutaway'
    v.SetSectionBox(box((x0-250, y0-250, -450), (x1+250, y1+250, 1800)))
    v.IsSectionBoxActive = True
    direction = XYZ(-1, 1, -0.8).Normalize()
    right = direction.CrossProduct(XYZ.BasisZ).Normalize()
    up = right.CrossProduct(direction).Normalize()
    v.SetOrientation(ViewOrientation3D(XYZ(ft(x1+5000), ft(y0-5000), ft(5000)), up, direction))
    v.Scale = 50
    views.append(v)

    # A synthetic client note is labelled as a test, never attributed to
    # the client. Its text and cloud boundary must survive extraction.
    text_type = doc.GetDefaultElementTypeId(ElementTypeGroup.TextNoteType)
    text = 'PIPELINE TEST\nReview wardrobe clearance.\nSynthetic; not client approval.'
    note = TextNote.Create(doc, plan.Id, XYZ(ft(x0+1800), ft(y0-400), 0),
                           text, TextNoteOptions(text_type))
    rev = Revision.Create(doc)
    rev.Description = 'archpipe synthetic round-trip test'
    rev.RevisionDate = '2026-09-22'
    pts = [(x0+50,y0+1400), (x0+800,y0+1400), (x0+800,y0+2650), (x0+50,y0+2650)]
    curves = List[Curve]()
    for a, b in zip(pts, pts[1:]+pts[:1]):
        curves.Add(Line.CreateBound(XYZ(ft(a[0]),ft(a[1]),0), XYZ(ft(b[0]),ft(b[1]),0)))
    cloud = RevisionCloud.Create(doc, plan, rev.Id, curves)
    report['markup'] = {'text_id': note.UniqueId, 'cloud_id': cloud.UniqueId,
                        'text': text, 'boundary_mm': pts}
    for index, view in enumerate(views):
        view.DetailLevel = ViewDetailLevel.Fine
        fixture_category = doc.Settings.Categories.get_Item(BuiltInCategory.OST_LightingFixtures)
        for category in fixture_category.SubCategories:
            if category.Name.lower() == 'light source' and view.CanCategoryBeHidden(category.Id):
                view.SetCategoryHidden(category.Id, True)
        # Keep the native title family on one line; its default fixed
        # label box otherwise wraps over the scale annotation.
        title = view.Name[len('ARCHPIPE '):].replace('interior ', '').replace('Reflected ceiling', 'Ceiling')
        view.get_Parameter(BuiltInParameter.VIEW_DESCRIPTION).Set(title)
        sheet = ViewSheet.Create(doc, ElementId.InvalidElementId)
        sheet.Name = 'ARCHPIPE ' + view.Name[len('ARCHPIPE '):]
        sheet.SheetNumber = 'AP-%03d' % (index+1)
        # A blank sheet has no title-block extent. A native paper frame
        # gives PDF centering a stable A3 landscape boundary.
        corners = [(10,10), (410,10), (410,287), (10,287)]
        for a, b in zip(corners, corners[1:]+corners[:1]):
            doc.Create.NewDetailCurve(sheet, Line.CreateBound(
                XYZ(ft(a[0]),ft(a[1]),0), XYZ(ft(b[0]),ft(b[1]),0)))
        TextNote.Create(doc, sheet.Id, XYZ(ft(20),ft(275),0),
                        sheet.SheetNumber + ' | ' + view.Name + ' | 1:50 | CAPABILITY TEST',
                        TextNoteOptions(text_type))
        viewport = Viewport.Create(doc, sheet.Id, view.Id, XYZ(ft(210),ft(150),0))
        # The plan note is below the room crop. Reserve paper space for
        # it before the title; vector count alone cannot detect overlap.
        viewport.LabelOffset = XYZ(0,ft(-25),0)
        report['views'].append({'id': view.UniqueId, 'name': view.Name,
                                'scale': view.Scale, 'type': str(view.ViewType),
                                'direction_toward_viewer': [view.ViewDirection.X,
                                    view.ViewDirection.Y, view.ViewDirection.Z]})
        report['sheets'].append({'id': sheet.UniqueId, 'number': sheet.SheetNumber})
    tx.Commit()
    doc.Save(SaveOptions())
    ids = List[ElementId]()
    for item in report['sheets']:
        ids.Add(doc.GetElement(item['id']).Id)
    opts = PDFExportOptions()
    opts.Combine, opts.FileName = True, 'bedroom-native-views'
    opts.PaperFormat = ExportPaperFormat.ISO_A3
    opts.PaperOrientation = PageOrientationType.Landscape
    opts.ZoomType, opts.ZoomPercentage = ZoomType.Zoom, 100
    opts.StopOnError = True
    report['pdf_exported'] = doc.Export(dest, ids, opts)
    report['pdf'] = os.path.join(dest, opts.FileName + '.pdf')
    report['saved_model'] = doc.PathName
    with open(os.path.join(dest, 'views-report.json'), 'w') as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
    print('ARCHPIPE VIEWS ' + json.dumps(report, sort_keys=True))
    doc.Close(False)


try:
    main()
except Exception:
    print('ARCHPIPE VIEWS FAILED\n' + traceback.format_exc())
    raise
