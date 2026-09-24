# -*- coding: utf-8 -*-
"""Spec -> Revit. The headline requirement.

    $env:ARCHPIPE_SPEC       = "<abs>\\out\\bedroom-spec.json"
    $env:ARCHPIPE_FAMILY_DIR = "<abs>\\out\\families"
    $env:ARCHPIPE_BEDROOM_OUT= "<abs>\\out\\revit2027\\bedroom.rvt"
    pyrevit run "<abs>\\revit\\build_bedroom.py" --revit=2027

The client's framing, taken as a hard requirement: *"you prepare a mock
spec and you must be able to build it in Revit -- a project requirement we
must pass with flying flags."* Everything else in the pipeline consumes
what this produces.

Reads JSON rather than the YAML in `spec/bedroom-test.yaml`, because this
runs in IronPython 2.7 inside Revit where PyYAML is absent.
`scripts/make_bedroom_spec.py` does the conversion, so the YAML stays the
human surface and there is still exactly one authored file.

WHAT IT BUILDS, and why each piece is there

  walls    on centrelines, half a thickness outside the internal rectangle
  floor    a real slab, so the render has something to bounce off
  ceiling  REQUIRED, not decoration. Measured on this project: without a
           ceiling every upward ray escapes and inter-reflection all but
           vanishes (9.6 lx against 22.6 with one). Pendants also need it
           as a host -- the placement gate had to host them on a wall for
           want of one, which is geometrically wrong.
  room     an enclosed loop, so area and boundary extract
  openings real hosted doors and windows from the template
  furniture real families where we have them, DirectShape proxies at the
           catalogue dimensions where we do not
  lighting real families, hosted on the ceiling

PROXIES ARE LABELLED. A proxy is a DirectShape box at the Neufert
dimensions, correctly categorised and named `PROXY <type>`. It is the
right footprint and clearance for the rule engine to check, and it is
obviously not furniture to anyone who looks. Pretending a box is a bed is
how a render starts flattering a design.

UNITS. Revit is decimal feet. `ft()` and `mm()` are the only conversions;
a units bug does not raise, it silently yields geometry 304.8x wrong.
"""
import json
import hashlib
import math
import os
import traceback

from Autodesk.Revit.DB import (
    BuiltInCategory, BuiltInParameter, Ceiling, CeilingType, Curve,
    Color, CurveLoop, DirectShape, Element, ElementId, ElementTransformUtils, FilteredElementCollector,
    Floor, FloorType, Line, Level, SaveAsOptions, Solid, Structure,
    Material, Options, Transaction, UnitTypeId, UnitUtils, UV, Wall, WallType, XYZ,
    GeometryObject, TessellatedShapeBuilder, TessellatedShapeBuilderTarget,
    TessellatedShapeBuilderFallback, TessellatedFace,
)
from Autodesk.Revit.DB import GeometryCreationUtilities as GCU
from System.Collections.Generic import List

PRECISION = 3
report = {"walls": [], "openings": [], "furniture": [], "lighting": [],
          "notes": [], "errors": []}


def note(msg):
    report["notes"].append(str(msg))


def fail(what, exc):
    report["errors"].append("%s: %s" % (what, str(exc)[:240]))


def ft(value):
    """Millimetres -> Revit internal (decimal feet)."""
    return UnitUtils.ConvertToInternalUnits(float(value), UnitTypeId.Millimeters)


def mm(value):
    """Revit internal (feet) -> millimetres."""
    return round(UnitUtils.ConvertFromInternalUnits(value, UnitTypeId.Millimeters),
                 PRECISION)


def el_name(el):
    """An element's name. `FamilySymbol.Name` raises AttributeError under
    IronPython in Revit 2027 -- `Name` is declared twice and the bridge
    cannot choose. `Family.Name` is fine, so this is not blanket."""
    try:
        return el.Name
    except Exception:
        pass
    try:
        return Element.Name.GetValue(el)
    except Exception:
        pass
    try:
        p = el.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM)
        if p is not None and p.HasValue:
            return p.AsString() or "<unnamed>"
    except Exception:
        pass
    return "<name unreadable>"


def find_template():
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


# --------------------------------------------------------------------------
# symbols
# --------------------------------------------------------------------------
def symbols(doc, bic):
    return list(FilteredElementCollector(doc).OfCategory(bic)
                .WhereElementIsElementType().ToElements())


def best_opening_symbol(doc, bic, want_w, want_h):
    """The template's closest door/window type, or a resized duplicate.

    The template ships fixed sizes (doors 0762-0915 wide, windows up to
    0915 x 1830). The spec asks for 1500 x 1400, which no stock type
    matches, so the nearest is duplicated and its dimension parameters are
    set. Choosing "close enough" silently would put the wrong hole in the
    wall and every daylight and clearance number downstream would be about
    a different room.
    """
    syms = symbols(doc, bic)
    if not syms:
        return None, "no types of this category in the template"

    def dims(s):
        w = s.get_Parameter(BuiltInParameter.FAMILY_WIDTH_PARAM)
        h = s.get_Parameter(BuiltInParameter.FAMILY_HEIGHT_PARAM)
        return (mm(w.AsDouble()) if w and w.HasValue else None,
                mm(h.AsDouble()) if h and h.HasValue else None)

    exact = None
    scored = []
    for s in syms:
        w, h = dims(s)
        if w is None or h is None:
            continue
        if abs(w - want_w) < 1.0 and abs(h - want_h) < 1.0:
            exact = s
            break
        scored.append((abs(w - want_w) + abs(h - want_h), s, w, h))
    if exact is not None:
        return exact, "stock type %s matches exactly" % el_name(exact)
    if not scored:
        return syms[0], "no dimensioned types; using %s as-is" % el_name(syms[0])

    scored.sort(key=lambda r: r[0])
    _, base, bw, bh = scored[0]
    try:
        dup = base.Duplicate("archpipe %.0f x %.0fmm" % (want_w, want_h))
        dup.get_Parameter(BuiltInParameter.FAMILY_WIDTH_PARAM).Set(ft(want_w))
        dup.get_Parameter(BuiltInParameter.FAMILY_HEIGHT_PARAM).Set(ft(want_h))
        return dup, ("duplicated %s (%.0f x %.0f) and set to %.0f x %.0f"
                     % (el_name(base), bw, bh, want_w, want_h))
    except Exception as exc:
        return base, "could not resize (%s); using %s at %.0f x %.0f" % (
            str(exc)[:80], el_name(base), bw, bh)


def activate(doc, sym):
    """Activate a symbol and regenerate.

    Measured in Revit 2027: placing an INACTIVE symbol raises
    `Exception: The symbol is not active`, it does not return None
    silently. Every family loads inactive, so this is never optional.
    """
    if not sym.IsActive:
        sym.Activate()
        doc.Regenerate()
    return sym


def load_family(doc, directory, filename):
    """Load a .rfa and return its first symbol, or (None, reason)."""
    if not filename:
        return None, "no family named in the spec"
    path = os.path.join(directory or "", filename)
    if not os.path.isfile(path):
        return None, "family file not found: %s" % filename
    try:
        res = doc.LoadFamily(path)
        fam = res[1] if isinstance(res, tuple) else None
        if fam is None:
            stem = os.path.splitext(filename)[0].lower()
            for f in FilteredElementCollector(doc).OfClass(
                    __import__("Autodesk.Revit.DB", fromlist=["Family"]).Family):
                if el_name(f).lower() in stem or stem in el_name(f).lower():
                    fam = f
                    break
        if fam is None:
            return None, "loaded but the Family could not be found again"
        ids = list(fam.GetFamilySymbolIds())
        if not ids:
            return None, "family declares no types"
        return doc.GetElement(ids[0]), "loaded %s" % el_name(fam)
    except Exception as exc:
        return None, "load failed: %s" % str(exc)[:160]


# Revit's own photometric parameters on a light fixture. Setting these
# makes Revit the source of truth for the lighting scheme (ADR-0001)
# rather than a second copy living in the spec: the extract then carries
# everything the lux engine and the renderer need, and the spec is not
# consulted again downstream.
# Names verified by dumping a placed fixture's parameters, because the
# obvious guesses are wrong: colour temperature is
# FBX_LIGHT_INITIAL_COLOR_TEMPERATURE, not FBX_LIGHT_COLOR_TEMPERATURE,
# and Autodesk's own spelling of "luminous" is inconsistent.
PHOTOMETRIC_PARAMS = {
    "ies": ("FBX_LIGHT_PHOTOMETRIC_FILE",),
    "lumens": ("FBX_LIGHT_LUMINOUS_FLUX", "FBX_LIGHT_LIMUNOUS_FLUX"),
    "kelvin": ("FBX_LIGHT_INITIAL_COLOR_TEMPERATURE",),
    "watts": ("FBX_LIGHT_WATTAGE",),
}


def stamp_mark(el, ident):
    """Write the spec id into Revit's Mark parameter.

    The join key between the model and the spec. Measured on this project:
    writes to the photometric parameters of third-party light families
    report success and then do NOT survive the save, because those
    families carry a read-only Light Source Definition that drives the
    photometric web. Mark is plain text Revit always holds, so the scheme
    can be rejoined to its photometry without either side guessing
    (ADR-0012).
    """
    for nm in ("ALL_MODEL_MARK", "DOOR_NUMBER", "ALL_MODEL_INSTANCE_COMMENTS"):
        bip = getattr(BuiltInParameter, nm, None)
        if bip is None:
            continue
        try:
            prm = el.get_Parameter(bip)
            if prm is not None and not prm.IsReadOnly:
                prm.Set(str(ident))
                return nm
        except Exception:
            continue
    return None


def set_photometrics(inst, lt, ies_dir):
    """Write the spec's photometry onto the placed fixture.

    Parameters live on the fixture's TYPE in most families and on the
    instance in some, so both are tried. What actually took is reported --
    a silently-unset IES file would leave the renderer lighting the room
    with a default it invented.
    """
    applied, missed = {}, []
    for key, names in PHOTOMETRIC_PARAMS.items():
        want = lt.get(key)
        if want is None:
            continue
        if key == "ies":
            want = os.path.join(ies_dir or "", str(want))
            if not os.path.isfile(want):
                missed.append("%s: file not found %s" % (key, want))
                continue
        done = False
        for holder in (inst, getattr(inst, "Symbol", None)):
            if holder is None or done:
                continue
            for nm in names:
                bip = getattr(BuiltInParameter, nm, None)
                if bip is None:
                    continue
                try:
                    prm = holder.get_Parameter(bip)
                    if prm is None or prm.IsReadOnly:
                        continue
                    if key == "ies":
                        prm.Set(str(want))
                    elif key == "lumens":
                        prm.Set(UnitUtils.ConvertToInternalUnits(
                            float(want), UnitTypeId.Lumens))
                    elif key == "watts":
                        prm.Set(UnitUtils.ConvertToInternalUnits(
                            float(want), UnitTypeId.Watts))
                    else:
                        prm.Set(UnitUtils.ConvertToInternalUnits(
                            float(want), UnitTypeId.Kelvin))
                    applied[key] = want if key != "ies" else os.path.basename(want)
                    done = True
                    break
                except Exception as exc:
                    missed.append("%s via %s: %s" % (key, nm, str(exc)[:70]))
        if not done and key not in applied:
            missed.append("%s: no writable parameter found" % key)
    return applied, missed


# --------------------------------------------------------------------------
# geometry
# --------------------------------------------------------------------------
def rect_loop(x0, y0, x1, y1, z):
    """A CurveLoop rectangle in internal units."""
    pts = [XYZ(x0, y0, z), XYZ(x1, y0, z), XYZ(x1, y1, z), XYZ(x0, y1, z)]
    loop = CurveLoop()
    for i in range(4):
        loop.Append(Line.CreateBound(pts[i], pts[(i + 1) % 4]))
    return loop


def build_walls(doc, level, w_mm, d_mm, t_mm):
    """Four walls on centrelines, half a thickness outside the room.

    Returns a dict keyed by compass point so an opening can name its host
    readably instead of by index.
    """
    h = t_mm / 2.0
    x0, y0 = ft(-h), ft(-h)
    x1, y1 = ft(w_mm + h), ft(d_mm + h)
    z = level.Elevation
    corners = {
        "south": (XYZ(x0, y0, z), XYZ(x1, y0, z)),
        "east":  (XYZ(x1, y0, z), XYZ(x1, y1, z)),
        "north": (XYZ(x1, y1, z), XYZ(x0, y1, z)),
        "west":  (XYZ(x0, y1, z), XYZ(x0, y0, z)),
    }
    made = {}
    for name, (a, b) in corners.items():
        wall = Wall.Create(doc, Line.CreateBound(a, b), level.Id, False)
        try:
            p = wall.get_Parameter(BuiltInParameter.WALL_USER_HEIGHT_PARAM)
            if p is not None:
                p.Set(ft(2700.0))
        except Exception:
            pass
        made[name] = wall
        report["walls"].append({
            "side": name, "id": str(wall.Id),
            "length_mm": mm(wall.Location.Curve.Length),
            "thickness_mm": mm(wall.Width)})
    return made


def build_floor(doc, level, w_mm, d_mm):
    loop = rect_loop(ft(0), ft(0), ft(w_mm), ft(d_mm), level.Elevation)
    loops = List[CurveLoop]()
    loops.Add(loop)
    ftypes = list(FilteredElementCollector(doc).OfClass(FloorType))
    ftype = None
    for f in ftypes:
        if "Generic" in el_name(f):
            ftype = f
            break
    ftype = ftype or (ftypes[0] if ftypes else None)
    if ftype is None:
        return None, "no floor type in the template"
    fl = Floor.Create(doc, loops, ftype.Id, level.Id)
    return fl, "floor type %s" % el_name(ftype)


def build_ceiling(doc, level, w_mm, d_mm, height_mm):
    """A ceiling at the specified height.

    Not decoration. Without one, every ray leaving a fitting upward
    escapes: measured 9.6 lx of inter-reflection without a ceiling against
    22.6 lx with one, and pendants have nothing to host on.
    """
    loop = rect_loop(ft(0), ft(0), ft(w_mm), ft(d_mm), level.Elevation)
    loops = List[CurveLoop]()
    loops.Add(loop)
    ctypes = list(FilteredElementCollector(doc).OfClass(CeilingType))
    ctype = None
    for c in ctypes:
        if el_name(c) in ("Generic", "GWB on Mtl Stud"):
            ctype = c
            break
    ctype = ctype or (ctypes[0] if ctypes else None)
    if ctype is None:
        return None, "no ceiling type in the template"
    ceil = Ceiling.Create(doc, loops, ctype.Id, level.Id)
    try:
        p = ceil.get_Parameter(BuiltInParameter.CEILING_HEIGHTABOVELEVEL_PARAM)
        if p is not None:
            p.Set(ft(height_mm))
    except Exception as exc:
        note("ceiling height not set: %s" % str(exc)[:120])
    return ceil, "ceiling type %s at %.0f mm" % (el_name(ctype), height_mm)


def wall_point(wall, along_mm, z_mm, level):
    """A point on a wall's centreline, `along_mm` from its start."""
    crv = wall.Location.Curve
    p = crv.Evaluate(ft(along_mm) / crv.Length, True)
    return XYZ(p.X, p.Y, level.Elevation + ft(z_mm))


def proxy_box(doc, ident, kind, cx_mm, cy_mm, w_mm, d_mm, h_mm, rot_deg, level):
    """A DirectShape box at the catalogue dimensions, obviously a proxy.

    Correct category and correct footprint, so the clearance rules check
    something real; named PROXY so nobody mistakes it for furniture.
    """
    import math
    a = math.radians(rot_deg or 0.0)
    ca, sa = math.cos(a), math.sin(a)
    hw, hd = w_mm / 2.0, d_mm / 2.0
    corners = []
    for dx, dy in ((-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd)):
        corners.append(XYZ(ft(cx_mm + dx * ca - dy * sa),
                           ft(cy_mm + dx * sa + dy * ca),
                           level.Elevation))
    loop = CurveLoop()
    for i in range(4):
        loop.Append(Line.CreateBound(corners[i], corners[(i + 1) % 4]))
    loops = List[CurveLoop]()
    loops.Add(loop)
    solid = GCU.CreateExtrusionGeometry(loops, XYZ.BasisZ, ft(h_mm))

    ds = DirectShape.CreateElement(doc, ElementId(BuiltInCategory.OST_Furniture))
    ds.ApplicationId = "archpipe"
    ds.ApplicationDataId = ident
    geoms = List[object]()
    geoms.Add(solid)
    ds.SetShape(geoms)
    try:
        # The type AND the rotation, because a DirectShape reports neither:
        # its geometry is baked and it has no Symbol. The extractor reads
        # this name back and `from_extract` parses both out of it.
        ds.Name = "PROXY %s @%g" % (kind, rot_deg or 0.0)
    except Exception:
        pass
    return ds


# --------------------------------------------------------------------------
def detailed_furniture(doc, item, level):
    """Author the recipe's real component meshes in the native model.

    World millimetres become internal feet here. Saved-model extraction,
    not this authoring payload, supplies downstream rendering geometry.
    """
    materials = {el_name(m): m.Id for m in FilteredElementCollector(doc).OfClass(Material)}
    geometries = List[GeometryObject]()
    for component in item['meshes']:
        material = component['material']
        name = material['name']
        if name not in materials:
            materials[name] = Material.Create(doc, name)
            mat = doc.GetElement(materials[name])
            mat.Color = Color(*[int(v) for v in material['rgb']])
            mat.UseRenderAppearanceForShading = False
        builder = TessellatedShapeBuilder()
        builder.OpenConnectedFaceSet(True)
        vertices = [XYZ(ft(p[0]), ft(p[1]), level.Elevation + ft(p[2]))
                    for p in component['vertices_mm']]
        for triangle in component['triangles']:
            points = List[XYZ]()
            for index in triangle:
                points.Add(vertices[index])
            builder.AddFace(TessellatedFace(points, materials[name]))
        builder.CloseConnectedFaceSet()
        builder.Target = TessellatedShapeBuilderTarget.AnyGeometry
        builder.Fallback = TessellatedShapeBuilderFallback.Mesh
        builder.Build()
        for geometry in builder.GetBuildResult().GetGeometricalObjects():
            geometries.Add(geometry)
    if geometries.Count == 0:
        raise RuntimeError('Detailed furniture produced no native geometry')
    ds = DirectShape.CreateElement(doc, ElementId(BuiltInCategory.OST_Furniture))
    ds.ApplicationId = 'archpipe.detailed'
    ds.ApplicationDataId = item['id']
    ds.Name = 'DETAILED %s @%g' % (item['type'], float(item.get('rotation') or 0))
    ds.SetShape(geometries)
    stamp_mark(ds, item['id'])
    return ds


def main():
    spec_path = os.environ.get("ARCHPIPE_SPEC")
    if not spec_path or not os.path.isfile(spec_path):
        raise RuntimeError("set ARCHPIPE_SPEC to the bedroom spec JSON")
    with open(spec_path) as fh:
        spec = json.load(fh)
    report["spec"] = os.path.basename(spec_path)
    with open(spec_path, 'rb') as fh:
        report['spec_sha256'] = hashlib.sha256(fh.read()).hexdigest()

    fam_dir = os.environ.get("ARCHPIPE_FAMILY_DIR") or ""
    dest = os.environ.get("ARCHPIPE_BEDROOM_OUT") or os.path.join(
        os.environ.get("USERPROFILE", "."), "archpipe_bedroom.rvt")

    template = find_template()
    if not os.path.isfile(template):
        raise RuntimeError("no metric template found")
    report["template"] = template

    app = __revit__.Application                        # noqa: F821
    doc = app.NewProjectDocument(template)

    rm = spec["room"]
    w_mm, d_mm = float(rm["width"]), float(rm["depth"])
    t_mm = float(rm.get("wall_thickness") or 200.0)
    ch_mm = float(rm.get("ceiling_height") or 2700.0)

    levels = sorted(FilteredElementCollector(doc).OfClass(Level).ToElements(),
                    key=lambda l: l.Elevation)
    level = levels[0]
    report["level"] = el_name(level)

    t = Transaction(doc, "archpipe: bedroom shell")
    t.Start()
    walls = build_walls(doc, level, w_mm, d_mm, t_mm)
    doc.Regenerate()

    floor, why = build_floor(doc, level, w_mm, d_mm)
    report["floor"] = why if floor is not None else None
    ceiling, why = build_ceiling(doc, level, w_mm, d_mm, ch_mm)
    report["ceiling"] = why if ceiling is not None else None
    doc.Regenerate()

    try:
        room = doc.Create.NewRoom(level, UV(ft(w_mm / 2.0), ft(d_mm / 2.0)))
        if room is not None:
            # `room.Name = ...` raises `AttributeError: Name` under
            # IronPython here, the same ambiguity as FamilySymbol.Name.
            # Setting ROOM_NAME goes through the parameter system instead,
            # and the area is captured FIRST so a naming failure cannot
            # cost us the measurement.
            report["room"] = {
                "area_m2": round(UnitUtils.ConvertFromInternalUnits(
                    room.Area, UnitTypeId.SquareMeters), 3)}
            want = spec.get("name") or "Bedroom"
            try:
                prm = room.get_Parameter(BuiltInParameter.ROOM_NAME)
                if prm is not None:
                    prm.Set(want)
                    report["room"]["name"] = want
            except Exception as exc:
                note("room named failed: %s" % str(exc)[:120])
        else:
            fail("room", "NewRoom returned None -- the loop may not enclose")
    except Exception as exc:
        fail("room", exc)
    t.Commit()

    # ---------------------------------------------------------- openings
    for op in spec.get("openings", []):
        rec = {"id": op["id"], "kind": op["kind"], "placed": False}
        t = Transaction(doc, "archpipe: opening %s" % op["id"])
        t.Start()
        try:
            bic = (BuiltInCategory.OST_Doors if op["kind"] == "door"
                   else BuiltInCategory.OST_Windows)
            sym, why = best_opening_symbol(doc, bic, float(op["width"]),
                                           float(op["height"]))
            rec["symbol"] = why
            if sym is None:
                raise RuntimeError(why)
            activate(doc, sym)
            host = walls.get(op["host"])
            if host is None:
                raise RuntimeError("no wall named %r" % op["host"])
            # `at` is measured from the room's corner; the wall centreline
            # starts half a thickness earlier.
            along = float(op["at"]) + t_mm / 2.0
            pt = wall_point(host, along, float(op.get("sill") or 0.0), level)
            inst = doc.Create.NewFamilyInstance(
                pt, sym, host, level, Structure.StructuralType.NonStructural)
            if inst is None:
                raise RuntimeError("NewFamilyInstance returned None")
            if op["kind"] == "window":
                p = inst.get_Parameter(BuiltInParameter.INSTANCE_SILL_HEIGHT_PARAM)
                if p is not None:
                    p.Set(ft(float(op.get("sill") or 0.0)))
            doc.Regenerate()
            rec["placed"] = True
            rec["element"] = str(inst.Id)
            rec["type"] = el_name(inst.Symbol)
            t.Commit()
        except Exception as exc:
            rec["error"] = str(exc)[:200]
            t.RollBack()
        report["openings"].append(rec)

    # --------------------------------------------------------- furniture
    for fn in spec.get("furniture", []):
        rec = {"id": fn["id"], "type": fn["type"], "placed": False,
               "proxy": bool(fn.get("proxy"))}
        t = Transaction(doc, "archpipe: furniture %s" % fn["id"])
        t.Start()
        try:
            size = fn.get("size") or [600, 600]
            at = fn["at"]
            if fn.get('detail'):
                inst = detailed_furniture(doc, fn, level)
                rec.update(element=str(inst.Id), proxy=False,
                           detail=fn['detail'], components=len(fn['meshes']))
            elif fn.get("family") and not fn.get("proxy"):
                sym, why = load_family(doc, fam_dir, fn["family"])
                rec["family"] = why
                if sym is None:
                    raise RuntimeError(why)
                activate(doc, sym)
                pt = XYZ(ft(at[0]), ft(at[1]), level.Elevation)
                inst = doc.Create.NewFamilyInstance(
                    pt, sym, level, Structure.StructuralType.NonStructural)
                if inst is None:
                    raise RuntimeError("NewFamilyInstance returned None")
                angle = math.radians(float(fn.get('rotation') or 0.0))
                if angle:
                    ElementTransformUtils.RotateElement(
                        doc, inst.Id, Line.CreateBound(pt, pt + XYZ.BasisZ), angle)
                rec["element"] = str(inst.Id)
                rec["mark"] = stamp_mark(inst, fn["id"])
            else:
                h = float(fn.get("height") or 800.0)
                ds = proxy_box(doc, fn["id"], fn["type"], float(at[0]),
                               float(at[1]), float(size[0]), float(size[1]),
                               h, float(fn.get("rotation") or 0.0), level)
                rec["element"] = str(ds.Id)
                rec["proxy"] = True
                inst = ds
            # Intent lives in the authored model as well as in the input.
            # A desk chair and bedside tables intentionally share their
            # parent's use space, but must still pass physical clash checks.
            metadata = {'type': fn['type'],
                        'accessory_to': fn.get('accessory_to') or '',
                        'detail': fn.get('detail') or '',
                        'rotation': float(fn.get('rotation') or 0)}
            prm = inst.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
            if prm is not None and not prm.IsReadOnly:
                prm.Set('archpipe:' + json.dumps(metadata, sort_keys=True))
            doc.Regenerate()
            rec["placed"] = True
            t.Commit()
        except Exception as exc:
            rec["error"] = str(exc)[:200]
            t.RollBack()
        report["furniture"].append(rec)

    # ---------------------------------------------------------- lighting
    for lt in spec.get("lighting", []):
        rec = {"id": lt["id"], "layer": lt.get("layer"), "placed": False,
               "host": lt.get("host")}
        t = Transaction(doc, "archpipe: light %s" % lt["id"])
        t.Start()
        try:
            sym, why = load_family(doc, fam_dir, lt.get("family"))
            rec["family"] = why
            if sym is None:
                raise RuntimeError(why)
            activate(doc, sym)
            at = lt["at"]
            z = float(lt.get("mounting_height") or 2400.0)
            pt = XYZ(ft(at[0]), ft(at[1]), level.Elevation + ft(z))
            host_el = None
            if lt.get("host") == "ceiling":
                host_el = ceiling
            elif str(lt.get("host", "")).startswith("wall_"):
                host_el = walls.get(str(lt["host"]).split("_", 1)[1])
            ptype = str(sym.Family.FamilyPlacementType)
            if "Hosted" in ptype:
                if host_el is None:
                    raise RuntimeError("hosted family but host %r unavailable"
                                       % lt.get("host"))
                inst = doc.Create.NewFamilyInstance(
                    pt, sym, host_el, level,
                    Structure.StructuralType.NonStructural)
            else:
                inst = doc.Create.NewFamilyInstance(
                    pt, sym, level, Structure.StructuralType.NonStructural)
            if inst is None:
                raise RuntimeError("NewFamilyInstance returned None")
            # A ceiling-hosted fitting sits at its host unless offset. The
            # spec gives the height of the FITTING, so a pendant at 1200 mm
            # under a 2700 ceiling needs a -1500 offset. Without this every
            # luminaire would silently sit at ceiling level and the whole
            # lux grid would describe a different scheme.
            angle = math.radians(float(lt.get('rotation') or 0))
            if angle:
                ElementTransformUtils.RotateElement(doc, inst.Id,
                    Line.CreateBound(pt, pt + XYZ.BasisZ), angle)
            if lt.get("host") == "ceiling":
                drop = z - ch_mm
                if abs(drop) > 1.0:
                    for bip in (BuiltInParameter.INSTANCE_FREE_HOST_OFFSET_PARAM,
                                BuiltInParameter.INSTANCE_ELEVATION_PARAM):
                        try:
                            prm = inst.get_Parameter(bip)
                            if prm is not None and not prm.IsReadOnly:
                                prm.Set(ft(drop))
                                rec["host_offset_mm"] = drop
                                break
                        except Exception:
                            continue
                    if "host_offset_mm" not in rec:
                        rec["warning"] = ("could not offset from host; the "
                                          "fitting sits at ceiling level, not "
                                          "%.0f mm" % z)
            doc.Regenerate()
            rec["placed"] = True
            rec["element"] = str(inst.Id)
            rec["placement_type"] = ptype
            rec["mark"] = stamp_mark(inst, lt["id"])
            applied, missed = set_photometrics(
                inst, lt, os.environ.get("ARCHPIPE_IES_DIR"))
            rec["photometrics"] = applied
            if missed:
                rec["photometrics_missed"] = missed[:4]
            try:
                loc = inst.Location
                pt2 = getattr(loc, "Point", None)
                if pt2 is not None:
                    rec["at_mm"] = [mm(pt2.X), mm(pt2.Y), mm(pt2.Z)]
            except Exception:
                pass
            t.Commit()
        except Exception as exc:
            rec["error"] = str(exc)[:200]
            t.RollBack()
        report["lighting"].append(rec)

    # Paint actual model faces, so the selected finishes can be read back.
    # Colour is a design choice. Reflectance is a simulation assumption,
    # recorded separately in the render specification, not inferred from RGB.
    tx = Transaction(doc, 'archpipe: specified finishes')
    tx.Start()
    palette = {'painted': (235, 232, 220), 'timber': (145, 105, 65),
               'plaster': (245, 245, 245)}
    report['materials'] = []
    for role, elements in [('walls', list(walls.values())),
                           ('floor', [floor]), ('ceiling', [ceiling])]:
        finish = spec.get('materials', {}).get(role)
        if not finish:
            continue
        mat_id = Material.Create(doc, 'archpipe ' + finish)
        mat = doc.GetElement(mat_id)
        rgb = palette.get(finish, (200, 200, 200))
        mat.Color = Color(*rgb)
        mat.UseRenderAppearanceForShading = False
        count = 0
        for element in elements:
            if element is None:
                continue
            for geom in element.get_Geometry(Options()):
                if isinstance(geom, Solid):
                    for face in geom.Faces:
                        doc.Paint(element.Id, face, mat_id)
                        count += 1
        report['materials'].append({'role': role, 'name': el_name(mat),
                                    'painted_faces': count})
    tx.Commit()

    opts = SaveAsOptions()
    opts.OverwriteExistingFile = True
    doc.SaveAs(dest, opts)
    doc.Close(False)
    report["saved"] = dest

    out = os.environ.get("ARCHPIPE_BUILD_REPORT") or (dest + ".build.json")
    with open(out, "w") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)

    print("archpipe: wrote %s" % dest)
    print("archpipe: walls %d  openings %d/%d  furniture %d/%d  lighting %d/%d"
          % (len(report["walls"]),
             sum(1 for o in report["openings"] if o["placed"]),
             len(report["openings"]),
             sum(1 for f in report["furniture"] if f["placed"]),
             len(report["furniture"]),
             sum(1 for l in report["lighting"] if l["placed"]),
             len(report["lighting"])))
    if report["errors"]:
        print("archpipe: errors %s" % report["errors"][:3])


try:
    main()
except Exception:
    print("archpipe: BUILD FAILED\n%s" % traceback.format_exc()[-1500:])
