# -*- coding: utf-8 -*-
"""Export a Revit model to the L0 text extract. ADR-0001 / ADR-0002.

Revit is the single authored artifact; this file is what everything else
reads. It is GENERATED and must never be hand-edited.

Two constraints shape every line here:

1. **Determinism.** Same model in, byte-identical file out (ADR-0002).
   Otherwise every export is a noisy diff and the whole reviewability
   argument collapses. Everything is sorted by a stable key and floats
   are rounded to a fixed precision.

2. **Units.** Revit's internal units are decimal FEET. The rest of this
   project is millimetres. Every length crosses that boundary exactly
   once, through `mm()`. Getting this wrong would not raise -- it would
   silently produce a model 305x too small.

Runs under pyRevit's IronPython 2.7 engine, so: no f-strings, no type
hints, no pathlib.

    pyrevit run revit\\extract_model.py <model.rvt> --revit=2026
or  the "Extract Model" button in the pyRevit ribbon.
"""
import json
import math
import os
import sys

from Autodesk.Revit.DB import (
    BuiltInCategory, BuiltInParameter, Element, FilteredElementCollector, Level,
    LocationCurve, LocationPoint, SpatialElementBoundaryOptions,
    UnitTypeId, UnitUtils, Wall, WallType, XYZ,
)

PRECISION = 3          # mm, to 3 dp -- far below drawing tolerance
SCHEMA_VERSION = 1


# --------------------------------------------------------------------------
# units
# --------------------------------------------------------------------------
def mm(value):
    """Revit internal (feet) -> millimetres. The single unit boundary."""
    return round(UnitUtils.ConvertFromInternalUnits(value, UnitTypeId.Millimeters),
                 PRECISION)


def pt_mm(p):
    return [mm(p.X), mm(p.Y)]


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _name(el):
    """An element's name.

    `FamilySymbol.Name` raises `AttributeError: Name` under IronPython in
    Revit 2027 -- `Name` is declared twice and the bridge cannot choose.
    `Family.Name` is unaffected. The first version of this swallowed the
    exception and returned "", so every `type_name` in the extract came
    back empty and nothing said why. Found by building a real room and
    reading it back.
    """
    if el is None:
        return ""
    try:
        return el.Name
    except Exception:
        pass
    try:
        return Element.Name.GetValue(el)
    except Exception:
        pass
    try:
        prm = el.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM)
        if prm is not None and prm.HasValue:
            return prm.AsString() or ""
    except Exception:
        pass
    return ""


def _param_str(el, bip):
    try:
        p = el.get_Parameter(bip)
        return p.AsString() or "" if p else ""
    except Exception:
        return ""


def _collect(doc, bic):
    return (FilteredElementCollector(doc)
            .OfCategory(bic)
            .WhereElementIsNotElementType()
            .ToElements())


def _sorted_by_uid(elements):
    """Stable ordering. ElementId is not stable across sessions; UniqueId is."""
    return sorted(elements, key=lambda e: e.UniqueId)


# --------------------------------------------------------------------------
# extractors
# --------------------------------------------------------------------------
def extract_levels(doc):
    levels = _sorted_by_uid(
        FilteredElementCollector(doc).OfClass(Level).ToElements())
    out = []
    ordered = sorted(levels, key=lambda l: l.Elevation)
    for i, lv in enumerate(ordered):
        nxt = ordered[i + 1] if i + 1 < len(ordered) else None
        height = mm(nxt.Elevation - lv.Elevation) if nxt else None
        out.append({
            "id": lv.UniqueId,
            "name": _name(lv),
            "elevation": mm(lv.Elevation),
            "height": height,
        })
    return out


def extract_wall_types(doc):
    types = _sorted_by_uid(
        FilteredElementCollector(doc).OfClass(WallType).ToElements())
    out = []
    for wt in types:
        entry = {
            "id": wt.UniqueId,
            "name": _name(wt),
            "thickness": None,
            "layers": [],
            "bearing": None,
        }
        try:
            cs = wt.GetCompoundStructure()
            if cs:
                entry["thickness"] = mm(cs.GetWidth())
                for layer in cs.GetLayers():
                    mat = doc.GetElement(layer.MaterialId)
                    entry["layers"].append({
                        "material": _name(mat) if mat else "",
                        "thickness": mm(layer.Width),
                        "function": str(layer.Function),
                    })
        except Exception as exc:
            entry["error"] = "%s: %s" % (type(exc).__name__, exc)
        out.append(entry)
    return out


def extract_walls(doc):
    walls = _sorted_by_uid(_collect(doc, BuiltInCategory.OST_Walls))
    out = []
    for w in walls:
        if not isinstance(w, Wall):
            continue
        loc = w.Location
        if not isinstance(loc, LocationCurve):
            continue                      # non-linear or in-place; skipped, reported
        curve = loc.Curve
        try:
            a, b = curve.GetEndPoint(0), curve.GetEndPoint(1)
        except Exception:
            continue
        lvl = doc.GetElement(w.LevelId)
        out.append({
            "id": w.UniqueId,
            "level": lvl.UniqueId if lvl else None,
            "type": w.WallType.UniqueId,
            "type_name": _name(w.WallType),
            "start": pt_mm(a),
            "end": pt_mm(b),
            "thickness": mm(w.Width),
            "height": mm(w.get_Parameter(
                BuiltInParameter.WALL_USER_HEIGHT_PARAM).AsDouble())
            if w.get_Parameter(BuiltInParameter.WALL_USER_HEIGHT_PARAM) else None,
            "structural": bool(w.get_Parameter(
                BuiltInParameter.WALL_STRUCTURAL_SIGNIFICANT).AsInteger())
            if w.get_Parameter(BuiltInParameter.WALL_STRUCTURAL_SIGNIFICANT) else None,
            "is_curved": curve.GetType().Name != "Line",
        })
    return out


def _distance_along(host_wall, point):
    """Where an opening sits along its host wall, in mm from the wall start.

    This is the `at` value the L0 schema uses. Projecting onto the curve
    rather than measuring straight-line distance matters for curved walls.
    """
    try:
        loc = host_wall.Location
        curve = loc.Curve
        res = curve.Project(point)
        return mm(res.Parameter - curve.GetEndParameter(0)) if res else None
    except Exception:
        return None


def extract_openings(doc):
    out = []
    for bic, kind in ((BuiltInCategory.OST_Doors, "door"),
                      (BuiltInCategory.OST_Windows, "window")):
        for inst in _sorted_by_uid(_collect(doc, bic)):
            host = getattr(inst, "Host", None)
            loc = inst.Location
            pt = loc.Point if isinstance(loc, LocationPoint) else None
            sym = inst.Symbol
            entry = {
                "id": inst.UniqueId,
                "kind": kind,
                "family": _name(sym.Family) if sym else "",
                "type_name": _name(sym) if sym else "",
                "host": host.UniqueId if host else None,
                "at": _distance_along(host, pt) if (host and pt) else None,
                "point": pt_mm(pt) if pt else None,
                "width": None,
                "height": None,
                "sill": None,
            }
            for key, bip in (("width", BuiltInParameter.DOOR_WIDTH),
                             ("height", BuiltInParameter.DOOR_HEIGHT)):
                try:
                    p = sym.get_Parameter(bip) if sym else None
                    if p:
                        entry[key] = mm(p.AsDouble())
                except Exception:
                    pass
            try:
                p = inst.get_Parameter(BuiltInParameter.INSTANCE_SILL_HEIGHT_PARAM)
                if p:
                    entry["sill"] = mm(p.AsDouble())
            except Exception:
                pass
            out.append(entry)
    return out


def extract_rooms(doc):
    opts = SpatialElementBoundaryOptions()
    out = []
    for room in _sorted_by_uid(_collect(doc, BuiltInCategory.OST_Rooms)):
        try:
            if room.Area <= 0:               # unplaced or unenclosed
                continue
        except Exception:
            continue
        boundary = []
        try:
            loops = room.GetBoundarySegments(opts)
            if loops and len(loops) > 0:
                for seg in loops[0]:         # outer loop only
                    boundary.append(pt_mm(seg.GetCurve().GetEndPoint(0)))
        except Exception:
            pass
        lvl = doc.GetElement(room.LevelId)
        out.append({
            "id": room.UniqueId,
            "level": lvl.UniqueId if lvl else None,
            "name": _param_str(room, BuiltInParameter.ROOM_NAME),
            "number": _param_str(room, BuiltInParameter.ROOM_NUMBER),
            "area_m2": round(UnitUtils.ConvertFromInternalUnits(
                room.Area, UnitTypeId.SquareMeters), PRECISION),
            "boundary": boundary,
        })
    return out


def _instance_rotation(inst):
    """Rotation in degrees CCW, from the instance's transform."""
    try:
        bx = inst.GetTransform().BasisX
        return round(math.degrees(math.atan2(bx.Y, bx.X)), PRECISION)
    except Exception:
        return None


def _bbox_centre_and_size(el):
    """Plan centre and size from an element's bounding box, in mm.

    Needed because a `DirectShape` has no `LocationPoint` -- its position
    lives in its geometry. The proxy furniture `build_bedroom.py` creates
    for pieces we have no family for is exactly that, and without this the
    extract reported `at: None` for every one of them, which would leave
    the clearance rules with nothing to check.
    """
    try:
        bb = el.get_BoundingBox(None)
        if bb is None:
            return None, None
        return ([mm((bb.Min.X + bb.Max.X) / 2.0),
                 mm((bb.Min.Y + bb.Max.Y) / 2.0)],
                [mm(bb.Max.X - bb.Min.X), mm(bb.Max.Y - bb.Min.Y),
                 mm(bb.Max.Z - bb.Min.Z)])
    except Exception:
        return None, None


def extract_instances(doc, bic, tag):
    out = []
    for inst in _sorted_by_uid(_collect(doc, bic)):
        loc = inst.Location
        pt = loc.Point if isinstance(loc, LocationPoint) else None
        sym = getattr(inst, "Symbol", None)
        lvl = doc.GetElement(inst.LevelId) if hasattr(inst, "LevelId") else None

        at = pt_mm(pt) if pt else None
        centre, size = _bbox_centre_and_size(inst)
        source = "location_point"
        if at is None and centre is not None:
            # Say WHERE the position came from. A bounding-box centre is a
            # good answer for an axis-aligned box and a poor one for a
            # rotated L-shape, and a downstream rule deserves to know which
            # it is holding.
            at = centre
            source = "bounding_box_centre"

        rec = {
            "id": inst.UniqueId,
            "category": tag,
            "family": _name(sym.Family) if sym else "",
            "type_name": _name(sym) if sym else "",
            "level": lvl.UniqueId if lvl else None,
            "at": at,
            "at_source": source if at is not None else None,
            "rotation": _instance_rotation(inst),
        }
        if size is not None:
            rec["size_mm"] = size
        # A DirectShape carries the id archpipe stamped on it, which is how
        # a proxy is traced back to the spec item it stands for.
        for attr in ("ApplicationId", "ApplicationDataId"):
            try:
                val = getattr(inst, attr, None)
                if val:
                    rec[attr.lower()] = str(val)
            except Exception:
                pass
        if not rec["family"]:
            rec["is_proxy"] = str(getattr(inst, "ApplicationId", "")) == "archpipe"
        out.append(rec)
    return out


def extract_site(doc):
    """North angle and the project base point.

    True north versus project north is the value every orientation rule
    depends on, so it is extracted explicitly rather than assumed to be
    zero.
    """
    info = {"north_angle": None, "latitude": None, "longitude": None,
            "place": ""}
    try:
        pl = doc.ActiveProjectLocation
        pp = pl.GetProjectPosition(XYZ.Zero)
        info["north_angle"] = round(math.degrees(pp.Angle), PRECISION)
        info["base_point"] = [mm(pp.EastWest), mm(pp.NorthSouth)]
        info["elevation"] = mm(pp.Elevation)
    except Exception as exc:
        info["north_error"] = "%s: %s" % (type(exc).__name__, exc)
    try:
        site = doc.SiteLocation
        info["latitude"] = round(math.degrees(site.Latitude), 6)
        info["longitude"] = round(math.degrees(site.Longitude), 6)
        info["place"] = site.PlaceName or ""
    except Exception as exc:
        info["site_error"] = "%s: %s" % (type(exc).__name__, exc)
    return info


# --------------------------------------------------------------------------
def build(doc):
    return {
        "schema_version": SCHEMA_VERSION,
        "source": "revit",
        "units": "mm",
        "project": {
            "name": doc.Title,
            "path": doc.PathName,
            "number": _param_str(doc.ProjectInformation,
                                 BuiltInParameter.PROJECT_NUMBER),
        },
        "site": extract_site(doc),
        "levels": extract_levels(doc),
        "wall_types": extract_wall_types(doc),
        "walls": extract_walls(doc),
        "openings": extract_openings(doc),
        "rooms": extract_rooms(doc),
        "furniture": extract_instances(doc, BuiltInCategory.OST_Furniture,
                                       "furniture"),
        "casework": extract_instances(doc, BuiltInCategory.OST_Casework,
                                      "casework"),
        "lighting": extract_instances(doc, BuiltInCategory.OST_LightingFixtures,
                                      "lighting"),
    }


def destination(doc):
    env = os.environ.get("ARCHPIPE_EXTRACT_OUT")
    if env:
        return env
    path = doc.PathName
    if path:
        return os.path.splitext(path)[0] + ".model.json"
    return os.path.join(os.path.expanduser("~"), "model.json")


def resolve_doc():
    """Find the model document, in whichever context this is running.

    Three contexts, and they do NOT agree:

      * ribbon button  -- `revit.doc` is the active document.
      * `pyrevit run <model>` -- the model IS open, but there is no UI, so
        `revit.doc` returns **None** and `ActiveUIDocument` is unavailable.
        The document has to be taken from the Application's document set.
      * `pyrevit run` with no model -- nothing to extract; say so plainly.

    The first version of this only caught an *exception* from `revit.doc`,
    not a None return, and died on `None.Title` with nothing useful said.
    """
    try:
        from pyrevit import revit
        if revit.doc is not None:
            return revit.doc
    except Exception:
        pass

    try:
        uidoc = __revit__.ActiveUIDocument              # noqa: F821
        if uidoc is not None and uidoc.Document is not None:
            return uidoc.Document
    except Exception:
        pass

    # Headless run: take the first real project document. Family and linked
    # documents are skipped -- extracting a family would produce a model
    # shaped like a project and quietly wrong.
    app = None
    try:
        app = __revit__.Application                     # noqa: F821
        for d in app.Documents:
            if d is None or d.IsFamilyDocument or d.IsLinked:
                continue
            return d
    except Exception as exc:
        raise RuntimeError("could not reach the Revit application: %s" % exc)

    # Nothing open. Measured fact about `pyrevit run <model.rvt>`: it hands
    # the script a UIApplication with ZERO documents -- it does not open the
    # model for you, despite taking one as an argument. So open it here.
    # This also makes the script identical from the ribbon button, where a
    # document is already open and this branch never runs.
    path = _model_path_argument()
    if path and app is not None:
        if not os.path.isfile(path):
            raise RuntimeError("model file not found: %s" % path)
        print("archpipe: opening %s" % path)
        return app.OpenDocumentFile(path)

    return None


def _model_path_argument():
    """The model to open, from the environment or the command line."""
    path = os.environ.get("ARCHPIPE_MODEL")
    if path:
        return path
    for arg in sys.argv[1:]:
        if arg.lower().endswith(".rvt"):
            return arg
    return None


def main():
    doc = resolve_doc()
    if doc is None:
        print("archpipe: no project document open. Pass a model:")
        print("archpipe:   pyrevit run extract_model.py <model.rvt> --revit=2027")
        return None

    data = build(doc)
    dest = destination(doc)
    # sort_keys makes the output order-independent; the explicit separators
    # keep it stable across Python versions. Both serve determinism.
    with open(dest, "w") as fh:
        json.dump(data, fh, indent=2, sort_keys=True, separators=(",", ": "))

    counts = dict((k, len(v)) for k, v in data.items() if isinstance(v, list))
    print("archpipe: wrote %s" % dest)
    print("archpipe: %s" % json.dumps(counts, sort_keys=True))
    return dest


if __name__ == "__main__":
    main()
