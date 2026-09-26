# -*- coding: utf-8 -*-
"""Build each villa option as a full Revit model, export its plans and 3D views.

    $env:ARCHPIPE_MODEL        = "<abs>\\out\\villa\\omar-env.rvt"        (opened per option, never saved over)
    $env:ARCHPIPE_OPTIONS_SPEC = "<abs>\\out\\villa\\options-spec.json"   (concept/revit_spec.py)
    $env:ARCHPIPE_OPTIONS_OUT  = "<abs>\\out\\villa\\options"             (folder; models + images + read-back)
    pyrevit run <abs path to this file> --revit=2027

Per option: remove the old interior (walls, doors, windows, furniture, fixtures, casework, rooms, groups; the
structure and the environment stay), build walls / doors / windows / room-separation lines / rooms / the stair
solids / the GF slab opening, create cropped plan views with room tags and three 3D views (basement cutaway, GF
cutaway, garden view), export PNGs, save omar-option-<id>.rvt, and write a read-back of what was actually built.
"""
import json
import math
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import extract_model as X                                          # noqa: E402
from probe_villa_inventory import _write                           # noqa: E402
import clr                                                          # noqa: E402
clr.AddReference("System")
from System.Collections.Generic import List                         # noqa: E402
from Autodesk.Revit.DB import (BoundingBoxXYZ, BuiltInCategory, BuiltInParameter, CurveArray, CurveLoop,  # noqa: E402
                               DirectShape, DisplayStyle, ElementId, FailureProcessingResult, FailureSeverity,
                               FamilyInstance, FamilySymbol, FilteredElementCollector, Floor, GeometryObject, Group,
                               IFailuresPreprocessor, ImageExportOptions, ImageFileType, ImageResolution, Level, Line,
                               LinkElementId, Plane, SaveAsOptions, SketchPlane, Transaction, UnitTypeId, UnitUtils,
                               UV, View3D, ViewDetailLevel, ViewFamily, ViewFamilyType, ViewOrientation3D, ViewPlan,
                               Wall, WallKind, WallType, XYZ, ExportRange, ZoomFitType, FitDirectionType)
from Autodesk.Revit.DB.Structure import StructuralType               # noqa: E402
from Autodesk.Revit.DB import GeometryCreationUtilities as GCU      # noqa: E402

LOG = []


def note(m):
    LOG.append(m)
    print("archpipe: %s" % m)


def ft(v_m):
    return UnitUtils.ConvertToInternalUnits(float(v_m) * 1000.0, UnitTypeId.Millimeters)


class Swallow(IFailuresPreprocessor):
    def PreprocessFailures(self, fa):
        for f in fa.GetFailureMessages():
            if f.GetSeverity() == FailureSeverity.Warning:
                fa.DeleteWarning(f)
        return FailureProcessingResult.Continue


def tx(doc, name):
    t = Transaction(doc, "archpipe option: " + name)
    o = t.GetFailureHandlingOptions()
    o.SetFailuresPreprocessor(Swallow())
    t.SetFailureHandlingOptions(o)
    t.Start()
    return t


def is_env(el):
    try:
        return isinstance(el, DirectShape) and el.ApplicationId in ("archpipe-env",)
    except Exception:
        return False


CLEAR = [BuiltInCategory.OST_Walls, BuiltInCategory.OST_Doors, BuiltInCategory.OST_Windows,
         BuiltInCategory.OST_Furniture, BuiltInCategory.OST_FurnitureSystems, BuiltInCategory.OST_Casework,
         BuiltInCategory.OST_PlumbingFixtures, BuiltInCategory.OST_LightingFixtures,
         BuiltInCategory.OST_SpecialityEquipment, BuiltInCategory.OST_MechanicalEquipment,
         BuiltInCategory.OST_ElectricalFixtures, BuiltInCategory.OST_Ceilings, BuiltInCategory.OST_Rooms,
         BuiltInCategory.OST_GenericModel, BuiltInCategory.OST_CommunicationDevices]


def clear_interior(doc):
    n = 0
    groups = list(FilteredElementCollector(doc).OfClass(Group).ToElementIds())
    for g in groups:
        try:
            doc.Delete(g)
            n += 1
        except Exception:
            pass
    for bic in CLEAR:
        ids = [e.Id for e in FilteredElementCollector(doc).OfCategory(bic).WhereElementIsNotElementType().ToElements()
               if not is_env(e)]
        for i in ids:
            try:
                if doc.GetElement(i) is not None:
                    doc.Delete(i)
                    n += 1
            except Exception:
                pass
    return n


def wall_types(doc):
    basic = [w for w in FilteredElementCollector(doc).OfClass(WallType) if w.Kind == WallKind.Basic]

    def pick(target):
        return min(basic, key=lambda w: abs(UnitUtils.ConvertFromInternalUnits(w.Width, UnitTypeId.Millimeters) - target))
    return pick(200.0), pick(100.0)


def symbols(doc, bic):
    out = []
    for s in FilteredElementCollector(doc).OfClass(FamilySymbol).OfCategory(bic):
        w = None
        for bip in (BuiltInParameter.DOOR_WIDTH, BuiltInParameter.WINDOW_WIDTH, BuiltInParameter.FAMILY_WIDTH_PARAM):
            p = s.get_Parameter(bip)
            if p is not None and p.AsDouble() > 0:
                w = UnitUtils.ConvertFromInternalUnits(p.AsDouble(), UnitTypeId.Millimeters) / 1000.0
                break
        out.append((s, w))
    return out


def nearest_symbol(syms, width):
    known = [(s, w) for s, w in syms if w]
    if not known:
        return syms[0][0] if syms else None
    return min(known, key=lambda sw: abs(sw[1] - width))[0]


def host_at(walls, level_name, x, y):
    best, bd = None, 1e9
    for w, spec in walls:
        if spec["level"] != level_name:
            continue
        x0, y0, x1, y1 = spec["x0"], spec["y0"], spec["x1"], spec["y1"]
        if abs(x0 - x1) < 1e-6:                        # vertical wall
            d = abs(x - x0) if min(y0, y1) - 0.05 <= y <= max(y0, y1) + 0.05 else 1e9
        else:
            d = abs(y - y0) if min(x0, x1) - 0.05 <= x <= max(x0, x1) + 0.05 else 1e9
        if d < bd:
            best, bd = (w, spec), d
    return best if bd < 0.2 else None


def solid_box(b_mm):
    x0, y0, z0, x1, y1, z1 = [UnitUtils.ConvertToInternalUnits(v, UnitTypeId.Millimeters) for v in b_mm]
    lp = CurveLoop()
    pts = [XYZ(x0, y0, z0), XYZ(x1, y0, z0), XYZ(x1, y1, z0), XYZ(x0, y1, z0)]
    for i in range(4):
        lp.Append(Line.CreateBound(pts[i], pts[(i + 1) % 4]))
    loops = List[CurveLoop]()
    loops.Add(lp)
    return GCU.CreateExtrusionGeometry(loops, XYZ.BasisZ, z1 - z0)


def build_option(app, model, spec, folder):
    doc = app.OpenDocumentFile(model)
    lv = dict((X._name(l), l) for l in FilteredElementCollector(doc).OfClass(Level))
    rb = {"id": spec["id"], "built": {}, "failed": []}

    t = tx(doc, "clear old interior")
    rb["deleted"] = clear_interior(doc)
    t.Commit()

    t = tx(doc, "walls")
    ext_t, int_t = wall_types(doc)
    walls = []
    for w in spec["walls"]:
        level = lv[spec["levels"][w["level"]]]
        wt = ext_t if w["kind"] == "ext" else int_t
        try:
            line = Line.CreateBound(XYZ(ft(w["x0"]), ft(w["y0"]), level.Elevation),
                                    XYZ(ft(w["x1"]), ft(w["y1"]), level.Elevation))
            wall = Wall.Create(doc, line, wt.Id, level.Id, ft(w["height"]), 0.0, False, False)
            walls.append((wall, dict(w, level=spec["levels"][w["level"]])))
        except Exception as exc:
            rb["failed"].append({"wall": w, "error": str(exc)})
    rb["built"]["walls"] = len(walls)
    t.Commit()

    t = tx(doc, "doors and windows")
    dsyms, wsyms = symbols(doc, BuiltInCategory.OST_Doors), symbols(doc, BuiltInCategory.OST_Windows)
    nd = nw = 0
    for d in spec["doors"]:
        ln = spec["levels"][d["level"]]
        h = host_at(walls, ln, d["x"], d["y"])
        if h is None:
            rb["failed"].append({"door": d, "error": "no host wall"})
            continue
        sym = nearest_symbol(dsyms, d["width"])
        try:
            if not sym.IsActive:
                sym.Activate()
                doc.Regenerate()
            doc.Create.NewFamilyInstance(XYZ(ft(d["x"]), ft(d["y"]), lv[ln].Elevation), sym, h[0], lv[ln],
                                         StructuralType.NonStructural)
            nd += 1
        except Exception as exc:
            rb["failed"].append({"door": d, "error": str(exc)})
    for wdw in spec["windows"]:
        ln = spec["levels"][wdw["level"]]
        h = host_at(walls, ln, wdw["x"], wdw["y"])
        if h is None:
            rb["failed"].append({"window": wdw, "error": "no host wall"})
            continue
        sym = nearest_symbol(wsyms, wdw["width"])
        try:
            if not sym.IsActive:
                sym.Activate()
                doc.Regenerate()
            inst = doc.Create.NewFamilyInstance(XYZ(ft(wdw["x"]), ft(wdw["y"]), lv[ln].Elevation), sym, h[0], lv[ln],
                                                StructuralType.NonStructural)
            p = inst.get_Parameter(BuiltInParameter.INSTANCE_SILL_HEIGHT_PARAM)
            if p is not None and not p.IsReadOnly:
                p.Set(ft(wdw["sill"]))
            nw += 1
        except Exception as exc:
            rb["failed"].append({"window": wdw, "error": str(exc)})
    rb["built"]["doors"], rb["built"]["windows"] = nd, nw
    t.Commit()

    t = tx(doc, "stair and slab opening")
    cid = ElementId(BuiltInCategory.OST_Stairs)
    if not DirectShape.IsValidCategoryId(cid, doc):
        cid = ElementId(BuiltInCategory.OST_GenericModel)
    ds = DirectShape.CreateElement(doc, cid)
    ds.ApplicationId = "archpipe-option"
    ds.ApplicationDataId = "stair"
    g = List[GeometryObject]()
    for b in spec["stair"]:
        g.Add(solid_box(b))
    ds.SetShape(g)
    ds.Name = "STAIR " + spec["stair_name"]
    rb["built"]["stair_id"] = int(str(ds.Id))
    roofs = 0
    ftypes = [f for f in FilteredElementCollector(doc).OfClass(Floor).ToElements()]
    ftype_id = ftypes[0].GetTypeId() if ftypes else None
    for r in spec.get("roofs", []):
        try:
            z = lv[spec["levels"]["GF"]].Elevation
            loop = CurveLoop()
            pts = [XYZ(ft(r[0]), ft(r[1]), z), XYZ(ft(r[2]), ft(r[1]), z), XYZ(ft(r[2]), ft(r[3]), z),
                   XYZ(ft(r[0]), ft(r[3]), z)]
            for i in range(4):
                loop.Append(Line.CreateBound(pts[i], pts[(i + 1) % 4]))
            loops = List[CurveLoop]()
            loops.Add(loop)
            Floor.Create(doc, loops, ftype_id, lv[spec["levels"]["GF"]].Id)
            roofs += 1
        except Exception as exc:
            rb["failed"].append({"roof": r, "error": str(exc)})
    rb["built"]["block_roofs"] = roofs
    op = spec["gf_opening"]
    gf_floor = None
    for fl in FilteredElementCollector(doc).OfClass(Floor):
        p = fl.get_Parameter(BuiltInParameter.ALL_MODEL_MARK)
        if p is not None and p.AsString() == "ENV slab-GF":
            gf_floor = fl
    if op and gf_floor is not None:
        ca = CurveArray()
        z = lv[spec["levels"]["GF"]].Elevation
        pts = [XYZ(ft(op[0]), ft(op[1]), z), XYZ(ft(op[2]), ft(op[1]), z), XYZ(ft(op[2]), ft(op[3]), z),
               XYZ(ft(op[0]), ft(op[3]), z)]
        for i in range(4):
            ca.Append(Line.CreateBound(pts[i], pts[(i + 1) % 4]))
        try:
            o = doc.Create.NewOpening(gf_floor, ca, True)
            rb["built"]["gf_opening_id"] = int(str(o.Id))
        except Exception as exc:
            rb["failed"].append({"opening": op, "error": str(exc)})
    t.Commit()

    t = tx(doc, "plan views, rooms, tags")
    vft = list(FilteredElementCollector(doc).OfClass(ViewFamilyType))
    plan_t = [v for v in vft if v.ViewFamily == ViewFamily.FloorPlan][0]
    plans = {}
    for key in ("B", "GF"):
        v = ViewPlan.Create(doc, plan_t.Id, lv[spec["levels"][key]].Id)
        try:
            v.Name = "%s plan %s" % (spec["id"], spec["levels"][key])
        except Exception:
            pass
        v.Scale = 100
        v.DetailLevel = ViewDetailLevel.Medium
        bb = BoundingBoxXYZ()
        bb.Min = XYZ(ft(0.6), ft(-31.8), ft(-10))
        bb.Max = XYZ(ft(28.0), ft(-20.6), ft(10))
        v.CropBox = bb
        v.CropBoxActive = True
        v.CropBoxVisible = False
        plans[key] = v
    doc.Regenerate()
    for s in spec["separations"]:
        level = lv[spec["levels"][s["level"]]]
        try:
            sp = SketchPlane.Create(doc, Plane.CreateByNormalAndOrigin(XYZ.BasisZ, XYZ(0, 0, level.Elevation)))
            ca = CurveArray()
            ca.Append(Line.CreateBound(XYZ(ft(s["x0"]), ft(s["y0"]), level.Elevation),
                                       XYZ(ft(s["x1"]), ft(s["y1"]), level.Elevation)))
            doc.Create.NewRoomBoundaryLines(sp, ca, plans[s["level"]])
        except Exception as exc:
            rb["failed"].append({"separation": s, "error": str(exc)})
    doc.Regenerate()
    rooms = []
    for r in spec["rooms"]:
        level = lv[spec["levels"][r["level"]]]
        try:
            room = doc.Create.NewRoom(level, UV(ft(r["x"]), ft(r["y"])))
            room.Name = r["name"]
            doc.Regenerate()
            doc.Create.NewRoomTag(LinkElementId(room.Id), UV(ft(r["x"]), ft(r["y"])), plans[r["level"]].Id)
            rooms.append({"id": r["id"], "name": r["name"], "level": r["level"],
                          "area_m2": round(room.Area * 0.09290304, 2)})
        except Exception as exc:
            rb["failed"].append({"room": r["id"], "error": str(exc)})
    rb["rooms"] = rooms
    t.Commit()

    t = tx(doc, "3D views")
    v3t = [v for v in vft if v.ViewFamily == ViewFamily.ThreeDimensional][0]
    views3d = {}
    eye_dir = XYZ(-1.0, -0.9, -0.75).Normalize()           # from the garden (rear, east) looking toward the street
    for key, zmax, hide_generic in (("basement cutaway", -0.25, True), ("GF cutaway", 2.55, True),
                                    ("garden view", 12.0, False)):
        v = View3D.CreateIsometric(doc, v3t.Id)
        try:
            v.Name = "%s %s" % (spec["id"], key)
        except Exception:
            pass
        centre = XYZ(ft(12.5), ft(-26.5), ft(-1.0))
        eye = centre - eye_dir * ft(40)
        up = XYZ.BasisZ - eye_dir * XYZ.BasisZ.DotProduct(eye_dir)
        v.SetOrientation(ViewOrientation3D(eye, up.Normalize(), eye_dir))
        if key != "garden view":
            bb = BoundingBoxXYZ()
            bb.Min = XYZ(ft(1.5), ft(-31.6), ft(-3.4))
            bb.Max = XYZ(ft(23.0), ft(-23.3), ft(zmax))
            v.SetSectionBox(bb)
        v.DisplayStyle = DisplayStyle.ShadingWithEdges
        if hide_generic:
            try:
                v.SetCategoryHidden(ElementId(BuiltInCategory.OST_GenericModel), True)
            except Exception:
                pass
        try:
            v.SetCategoryHidden(ElementId(BuiltInCategory.OST_Levels), True)     # no level lines in 3D exports
        except Exception:
            pass
        views3d[key] = v
    t.Commit()

    dest = os.path.join(folder, "omar-option-%s.rvt" % spec["id"])
    if os.path.exists(dest):
        os.remove(dest)
    so = SaveAsOptions()
    so.OverwriteExistingFile = True
    doc.SaveAs(dest, so)
    rb["saved"] = dest
    for key, v, px in [("plan-B", plans["B"], 3000), ("plan-GF", plans["GF"], 3000)] + \
            [(k.replace(" ", "-"), v, 2400) for k, v in views3d.items()]:
        try:
            o = ImageExportOptions()
            o.ExportRange = ExportRange.SetOfViews
            ids = List[ElementId]()
            ids.Add(v.Id)
            o.SetViewsAndSheets(ids)
            o.FilePath = os.path.join(folder, "%s-%s" % (spec["id"], key))
            o.HLRandWFViewsFileType = ImageFileType.PNG
            o.ShadowViewsFileType = ImageFileType.PNG
            o.ImageResolution = ImageResolution.DPI_300
            o.ZoomType = ZoomFitType.FitToPage
            o.FitDirection = FitDirectionType.Horizontal
            o.PixelSize = px
            doc.ExportImage(o)
        except Exception as exc:
            rb["failed"].append({"image": key, "error": str(exc)})
    doc.Close(False)
    note("%s: walls %s doors %s windows %s rooms %d failed %d" % (spec["id"], rb["built"].get("walls"),
                                                                   rb["built"].get("doors"), rb["built"].get("windows"),
                                                                   len(rb.get("rooms", [])), len(rb["failed"])))
    return rb


def main():
    specs = json.load(open(os.environ["ARCHPIPE_OPTIONS_SPEC"]))
    folder = os.environ["ARCHPIPE_OPTIONS_OUT"]
    if not os.path.isdir(folder):
        os.makedirs(folder)
    only = os.environ.get("ARCHPIPE_OPTIONS_ONLY")
    app = __revit__.Application                                    # noqa: F821
    out = []
    for spec in specs:
        if only and spec["id"] not in only.split(","):
            continue
        out.append(build_option(app, os.environ["ARCHPIPE_MODEL"], spec, folder))
    _write(os.path.join(folder, "readback.json"), {"options": out, "log": LOG})
    print("archpipe: wrote readback")


if __name__ == "__main__":
    main()
