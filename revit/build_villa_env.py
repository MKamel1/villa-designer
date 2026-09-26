# -*- coding: utf-8 -*-
"""Build the villa ENVIRONMENT model into a copy of omar.rvt, from the spec written by scripts/villa_env.py.

    $env:ARCHPIPE_MODEL      = "<abs>\\out\\villa\\omar-2027.rvt"     (opened, never saved over)
    $env:ARCHPIPE_ENV_SPEC   = "<abs>\\out\\villa\\env-spec.json"
    $env:ARCHPIPE_ENV_OUT    = "<abs>\\out\\villa\\omar-env.rvt"      (must not exist)
    $env:ARCHPIPE_ENV_READBACK = "<abs>\\out\\villa\\env-readback.json"
    pyrevit run <abs path to this file> --revit=2027

Adds levels, site location and true north, copies our nine columns to the basement and the apartment storey,
perimeter beams, our slabs, the sunken yards, the fence, the sister villa, the apartment above, neighbours with
windows, and the street. Context and assumed elements are DirectShapes with ApplicationId "archpipe-env" and a
name saying what they are. Then it reads everything back from the built model (bounding boxes, levels, site,
north) so the spec can be checked against geometry, not against intentions.
"""
import json
import math
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import extract_model as X                                          # noqa: E402
import clr                                                          # noqa: E402
clr.AddReference("System")
from System.Collections.Generic import List                         # noqa: E402
from Autodesk.Revit.DB import (BuiltInCategory, BuiltInParameter, CurveLoop, DirectShape, ElementId,  # noqa: E402
                               ElementTransformUtils, FailureProcessingResult, FailureSeverity,
                               FilteredElementCollector, Floor, FloorType, GeometryObject, IFailuresPreprocessor,
                               Level, Line, ProjectPosition, SaveAsOptions, Transaction, UnitTypeId, UnitUtils,
                               View3D, ViewFamily, ViewFamilyType, ViewPlan, XYZ, ImageExportOptions,
                               ExportRange, ImageFileType, ImageResolution, FitDirectionType, ZoomFitType)
from Autodesk.Revit.DB import GeometryCreationUtilities as GCU      # noqa: E402

LOG = []


def note(msg):
    LOG.append(msg)
    print("archpipe: %s" % msg)


def ft(v):
    return UnitUtils.ConvertToInternalUnits(float(v), UnitTypeId.Millimeters)


def _eid(i):
    """ElementId from an integer id. Revit 2027 has Int64, BuiltInParameter and BuiltInCategory overloads, and
    IronPython cannot choose for a plain int ("Multiple targets could match")."""
    from System import Int64
    return ElementId(Int64(i))


class Swallow(IFailuresPreprocessor):
    """Delete warnings (overlaps between context masses are expected); errors still roll back."""
    def PreprocessFailures(self, fa):
        for f in fa.GetFailureMessages():
            if f.GetSeverity() == FailureSeverity.Warning:
                fa.DeleteWarning(f)
        return FailureProcessingResult.Continue


def tx(doc, name):
    t = Transaction(doc, "archpipe env: " + name)
    opts = t.GetFailureHandlingOptions()
    opts.SetFailuresPreprocessor(Swallow())
    t.SetFailureHandlingOptions(opts)
    t.Start()
    return t


def loop_of(pts, z_mm):
    lp = CurveLoop()
    n = len(pts)
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        lp.Append(Line.CreateBound(XYZ(ft(a[0]), ft(a[1]), ft(z_mm)), XYZ(ft(b[0]), ft(b[1]), ft(z_mm))))
    return lp


CATS = {"Mass": BuiltInCategory.OST_Mass, "GenericModel": BuiltInCategory.OST_GenericModel,
        "Windows": BuiltInCategory.OST_Windows, "StructuralFraming": BuiltInCategory.OST_StructuralFraming}


def direct_shape(doc, e):
    cat = ElementId(CATS[e["category"]])
    if not DirectShape.IsValidCategoryId(cat, doc):
        note("category %s not valid for DirectShape; using Generic Models for %s" % (e["category"], e["id"]))
        cat = ElementId(BuiltInCategory.OST_GenericModel)
    loops = List[CurveLoop]()
    loops.Add(loop_of(e["pts"], e["z0"]))
    solid = GCU.CreateExtrusionGeometry(loops, XYZ.BasisZ, ft(e["z1"] - e["z0"]))
    ds = DirectShape.CreateElement(doc, cat)
    ds.ApplicationId = "archpipe-env"
    ds.ApplicationDataId = e["id"]
    geoms = List[GeometryObject]()
    geoms.Add(solid)
    ds.SetShape(geoms)
    ds.Name = "ENV %s" % e["id"]
    _comment(ds, e["note"])
    return ds


def _comment(el, text):
    try:
        p = el.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
        if p is not None and not p.IsReadOnly:
            p.Set("ENV: " + text)
    except Exception:
        pass


def _mark(el, text):
    try:
        p = el.get_Parameter(BuiltInParameter.ALL_MODEL_MARK)
        if p is not None and not p.IsReadOnly:
            p.Set(text)
    except Exception:
        pass


def levels(doc, spec):
    existing = list(FilteredElementCollector(doc).OfClass(Level))
    by_name = {}
    for want in spec["levels"]:
        z = ft(want["z"])
        match = [l for l in existing if abs(l.Elevation - z) < ft(1)]
        lv = match[0] if match else Level.Create(doc, z)
        try:
            lv.Name = want["name"]
        except Exception as exc:
            note("level rename failed %s: %s" % (want["name"], exc))
        by_name[want["name"]] = lv
    return by_name


def site(doc, spec):
    s = spec["site"]
    sl = doc.SiteLocation
    sl.Latitude = math.radians(s["latitude"])
    sl.Longitude = math.radians(s["longitude"])
    sl.TimeZone = s["time_zone"]
    try:
        sl.PlaceName = "Sheikh Zayed, Giza"
    except Exception:
        pass
    loc = doc.ActiveProjectLocation
    pos = loc.GetProjectPosition(XYZ.Zero)
    want = s["street_facade_azimuth"]
    best = None
    for sign in (-1, 1):                  # choose the rotation whose read-back gives the wanted azimuth
        ang = sign * math.radians((want - 270.0) % 360.0)
        loc.SetProjectPosition(XYZ.Zero, ProjectPosition(pos.EastWest, pos.NorthSouth, pos.Elevation, ang))
        az = street_azimuth(doc, spec)
        err = abs(((az - want) + 180) % 360 - 180)
        if best is None or err < best[0]:
            best = (err, ang)
    loc.SetProjectPosition(XYZ.Zero, ProjectPosition(pos.EastWest, pos.NorthSouth, pos.Elevation, best[1]))
    note("true north set: angle %.3f deg, street facade azimuth %.2f" % (math.degrees(best[1]),
                                                                          street_azimuth(doc, spec)))


def street_azimuth(doc, spec):
    """Azimuth (deg from true north, clockwise) of the street facade's outward normal, read from the model."""
    d = spec["site"]["street_facade_direction"]
    v = doc.ActiveProjectLocation.GetTotalTransform().OfVector(XYZ(d[0], d[1], 0))
    return math.degrees(math.atan2(v.X, v.Y)) % 360.0


def floor_type(doc):
    types = list(FilteredElementCollector(doc).OfClass(FloorType))
    for t in types:
        if "200" in X._name(t) and "Slab" in X._name(t):
            return t
    return types[0]


def columns(doc, spec, lv):
    col = spec["columns"]
    ids = [_eid(i) for i in col["revit_ids"]]
    gf = [doc.GetElement(i) for i in ids]
    missing = [col["revit_ids"][k] for k, e in enumerate(gf) if e is None]
    if missing:
        raise Exception("columns missing from the model: %s" % missing)

    def bind(c, base, top):
        c.get_Parameter(BuiltInParameter.FAMILY_BASE_LEVEL_PARAM).Set(lv[base].Id)
        c.get_Parameter(BuiltInParameter.FAMILY_BASE_LEVEL_OFFSET_PARAM).Set(0.0)
        c.get_Parameter(BuiltInParameter.FAMILY_TOP_LEVEL_PARAM).Set(lv[top].Id)
        c.get_Parameter(BuiltInParameter.FAMILY_TOP_LEVEL_OFFSET_PARAM).Set(0.0)

    for c in gf:
        bind(c, col["gf"]["base"], col["gf"]["top"])
        _comment(c, "existing column, KEEP (client)")
    made = []
    for cp in col["copies"]:
        idl = List[ElementId]()
        for i in ids:
            idl.Add(i)
        new = ElementTransformUtils.CopyElements(doc, idl, XYZ(0, 0, ft(cp["dz"])))
        doc.Regenerate()
        for nid in new:
            c = doc.GetElement(nid)
            bind(c, cp["base"], cp["top"])
            _comment(c, "column repeated from GF (client: same structure on every floor)")
            made.append(c)
    return gf + made


def main():
    spec = json.load(open(os.environ["ARCHPIPE_ENV_SPEC"]))
    dest = os.environ["ARCHPIPE_ENV_OUT"]
    if os.path.exists(dest):
        raise Exception("refusing to overwrite %s" % dest)
    doc = X.resolve_doc()
    note("opened %s" % doc.PathName)

    t = tx(doc, "levels, site, delete whole-plot floors")
    lv = levels(doc, spec)
    site(doc, spec)
    gone = []
    for rid in spec["delete_revit_ids"]:
        el = doc.GetElement(_eid(rid))
        if el is not None:
            gone += [i.IntegerValue if hasattr(i, "IntegerValue") else int(i.Value) for i in doc.Delete(el.Id)]
    note("deleted %d elements for %s" % (len(gone), spec["delete_revit_ids"]))
    t.Commit()

    t = tx(doc, "columns")
    cols = columns(doc, spec, lv)
    t.Commit()

    t = tx(doc, "slabs and yards")
    ftype = floor_type(doc)
    floors = []
    for s in spec["slabs"]:
        lvl = lv[s["level"]]
        loops = List[CurveLoop]()
        loops.Add(loop_of(s["pts"], X.mm(lvl.Elevation)))
        fl = Floor.Create(doc, loops, ftype.Id, lvl.Id)
        _mark(fl, "ENV " + s["id"])
        _comment(fl, s["note"])
        floors.append((s["id"], fl))
    t.Commit()

    t = tx(doc, "context and beams")
    shapes = [(e["id"], direct_shape(doc, e)) for e in spec["elements"]]
    t.Commit()

    t = tx(doc, "views")
    views = make_views(doc, lv)
    t.Commit()

    opts = SaveAsOptions()
    opts.OverwriteExistingFile = False
    doc.SaveAs(dest, opts)
    note("saved %s" % dest)
    export_images(doc, views, os.path.dirname(os.environ["ARCHPIPE_ENV_READBACK"]))
    readback(doc, spec, cols, floors, shapes, gone)


def make_views(doc, lv):
    out = []
    vft = [v for v in FilteredElementCollector(doc).OfClass(ViewFamilyType)]
    plan_t = [v for v in vft if v.ViewFamily == ViewFamily.FloorPlan][0]
    for name in ("B -1.80", "GF +1.20", "APT +4.20 (not ours)"):
        v = ViewPlan.Create(doc, plan_t.Id, lv[name].Id)
        try:
            v.Name = "ENV plan %s" % name
        except Exception:
            pass
        out.append(v)
    t3 = [v for v in vft if v.ViewFamily == ViewFamily.ThreeDimensional][0]
    v3 = View3D.CreateIsometric(doc, t3.Id)
    try:
        v3.Name = "ENV 3D"
    except Exception:
        pass
    try:
        from Autodesk.Revit.DB import DisplayStyle
        v3.DisplayStyle = DisplayStyle.ShadingWithEdges
    except Exception as exc:
        note("3D display style not set: %s" % exc)
    out.append(v3)
    return out


def export_images(doc, views, folder):
    try:
        for v in views:
            o = ImageExportOptions()
            o.ExportRange = ExportRange.SetOfViews
            ids = List[ElementId]()
            ids.Add(v.Id)
            o.SetViewsAndSheets(ids)
            o.FilePath = os.path.join(folder, "env-view")
            o.HLRandWFViewsFileType = ImageFileType.PNG
            o.ImageResolution = ImageResolution.DPI_150
            o.ZoomType = ZoomFitType.FitToPage
            o.FitDirection = FitDirectionType.Horizontal
            o.PixelSize = 2400
            doc.ExportImage(o)
        note("exported %d view images to %s" % (len(views), folder))
    except Exception as exc:
        note("image export failed: %s: %s" % (type(exc).__name__, exc))


def _bb(el):
    bb = el.get_BoundingBox(None)
    return None if bb is None else [X.mm(bb.Min.X), X.mm(bb.Min.Y), X.mm(bb.Min.Z),
                                    X.mm(bb.Max.X), X.mm(bb.Max.Y), X.mm(bb.Max.Z)]


def readback(doc, spec, cols, floors, shapes, gone):
    lvls = sorted([{"name": X._name(l), "z": X.mm(l.Elevation)} for l in FilteredElementCollector(doc).OfClass(Level)],
                  key=lambda r: r["z"])
    sl = doc.SiteLocation

    def lvname(c, bip):
        e = doc.GetElement(c.get_Parameter(bip).AsElementId())
        return X._name(e) if e is not None else None

    data = {
        "levels": lvls,
        "site": {"latitude": math.degrees(sl.Latitude), "longitude": math.degrees(sl.Longitude),
                 "time_zone": sl.TimeZone, "street_facade_azimuth": street_azimuth(doc, spec)},
        "columns": [{"id": int(str(c.Id)), "bbox": _bb(c),
                     "base": lvname(c, BuiltInParameter.FAMILY_BASE_LEVEL_PARAM),
                     "top": lvname(c, BuiltInParameter.FAMILY_TOP_LEVEL_PARAM)} for c in cols],
        "floors": [{"id": i, "bbox": _bb(f), "area_m2": f.get_Parameter(BuiltInParameter.HOST_AREA_COMPUTED).AsDouble()
                    * 0.09290304} for i, f in floors],
        "shapes": [{"id": i, "category": s.Category.Name, "bbox": _bb(s)} for i, s in shapes],
        "deleted_count": len(gone),
        "log": LOG,
    }
    path = os.environ["ARCHPIPE_ENV_READBACK"]
    from probe_villa_inventory import _write            # Int64 ids and non-ASCII text are JSON-safe there
    _write(path, data)
    note("wrote %s" % path)


if __name__ == "__main__":
    main()

