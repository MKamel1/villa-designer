# -*- coding: utf-8 -*-
"""Probe a manufacturer luminaire family before designing its installation.

    set ARCHPIPE_PROBE_RFA=<path to .rfa>   (its .txt type catalogue beside it)
    pyrevit run <ABSOLUTE path>/probe_product_family.py --revit=2027

In a throwaway project (never saved): load the family and its catalogue
types, place one instance under a ceiling, and report what installation
must know -- the types that load, the placement type, whether the geometry
carries a Light Source symbol or a lens (the emitter rule in
archpipe.fixture_source), the photometric parameters, and which writable
length parameter moves the emitter (nudged +100 mm and rolled back).
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from Autodesk.Revit.DB import (BuiltInParameter, CeilingType, Element, FamilySymbol, FilteredElementCollector,
                               Level, Options, SpecTypeId, StorageType, Structure, SubTransaction, Transaction,
                               UnitTypeId, UnitUtils, ViewDetailLevel, XYZ, Ceiling, CurveLoop, Line)

app = __revit__.Application                                     # noqa: F821

# An unattended run must never wait on a modal dialog. Loading a manufacturer's
# type catalogue raised "The parameter Apparent Load doesn't exist in the
# Family. It will be ignored." and the probe hung until a person clicked OK.
# Every dialog is answered OK and its text kept as a finding, not lost.
DIALOGS = []


def _on_dialog(sender, args, _store=DIALOGS):
    # `_store` is bound now: a dialog that fires after the script's scope is
    # torn down found `DIALOGS` undefined, the handler failed, and the dialog
    # stayed up (journal: UnboundNameException in DialogBoxShowing).
    _store.append({"id": getattr(args, "DialogId", ""), "message": getattr(args, "Message", "")})
    try:
        args.OverrideResult(1)                                   # IDOK
    except Exception:
        pass


__revit__.DialogBoxShowing += _on_dialog                         # noqa: F821

from Autodesk.Revit.DB import IFailuresPreprocessor, FailureProcessingResult, FailureSeverity


class _KeepWarnings(IFailuresPreprocessor):
    """Record transaction warnings and let the transaction continue."""
    store = DIALOGS

    def PreprocessFailures(self, accessor):
        for f in accessor.GetFailureMessages():
            if f.GetSeverity() == FailureSeverity.Warning:
                self.store.append({"id": "warning", "message": f.GetDescriptionText()})
                accessor.DeleteWarning(f)
        return FailureProcessingResult.Continue


def mm(v):
    return round(UnitUtils.ConvertFromInternalUnits(v, UnitTypeId.Millimeters), 1)


def ft(v):
    return UnitUtils.ConvertToInternalUnits(float(v), UnitTypeId.Millimeters)


def name(el):
    try:
        return Element.Name.GetValue(el)
    except Exception:
        try:
            return el.Name
        except Exception:
            return "?"


def template():
    root = r"C:\ProgramData\Autodesk"
    found = sorted((os.path.join(root, n, "Templates", "Default_M_ENU.rte") for n in os.listdir(root)
                    if n.startswith("RVT ")), reverse=True)
    return [f for f in found if os.path.isfile(f)][0]


def geometry(doc, inst):
    """Mesh groups by subcategory and material, with z bounds (mm)."""
    groups = {}
    opt = Options()
    opt.DetailLevel = ViewDetailLevel.Fine

    def cat(obj):
        try:
            st = doc.GetElement(obj.GraphicsStyleId)
            return name(st.GraphicsStyleCategory) if st else ""
        except Exception:
            return ""

    def visit(g):
        for o in g:
            if o.GetType().Name == "GeometryInstance":
                visit(o.GetInstanceGeometry())
            elif o.GetType().Name == "Solid":
                for f in o.Faces:
                    m = doc.GetElement(f.MaterialElementId)
                    key = "%s | %s" % (cat(f) or cat(o) or "-", name(m) if m else "unspecified")
                    zs = [p.Z for p in f.Triangulate().Vertices]
                    xs = [p.X for p in f.Triangulate().Vertices]
                    ys = [p.Y for p in f.Triangulate().Vertices]
                    b = groups.setdefault(key, [1e9, -1e9, 1e9, -1e9, 1e9, -1e9])
                    b[:] = [min(b[0], min(xs)), max(b[1], max(xs)), min(b[2], min(ys)), max(b[3], max(ys)),
                            min(b[4], min(zs)), max(b[5], max(zs))]
    g = inst.get_Geometry(opt)
    if g:
        visit(g)
    return {k: [mm(v) for v in b] for k, b in groups.items()}


def emitter_z(geo):
    sym = [b for k, b in geo.items() if k.lower().startswith("light source")]
    if sym:
        return max(b[5] for b in sym), "light_source_symbol apex"
    lens = [b for k, b in geo.items() if any(w in k.lower().split("|")[-1] for w in
            ("lens", "luminance", "luminous", "diffuser", "opal", "emitting"))]
    if lens:
        return (min(b[4] for b in lens) + max(b[5] for b in lens)) / 2.0, "luminous surface centre"
    return None, "no light-source or lens geometry"


rfa = os.environ["ARCHPIPE_PROBE_RFA"]
out = {"rfa": rfa}
doc = app.NewProjectDocument(template())
t = None


def run():
    global t
    t = Transaction(doc, "probe")
    opts = t.GetFailureHandlingOptions()
    opts.SetFailuresPreprocessor(_KeepWarnings())
    t.SetFailureHandlingOptions(opts)
    t.Start()
    level = sorted(FilteredElementCollector(doc).OfClass(Level).ToElements(), key=lambda l: l.Elevation)[0]
    # a 4 x 4 m ceiling at 2700 so ceiling-hosted families have a host
    ctype = [c for c in FilteredElementCollector(doc).OfClass(CeilingType)][0]
    loop = CurveLoop()
    pts = [XYZ(0, 0, 0), XYZ(ft(4000), 0, 0), XYZ(ft(4000), ft(4000), 0), XYZ(0, ft(4000), 0)]
    for a, b in zip(pts, pts[1:] + pts[:1]):
        loop.Append(Line.CreateBound(a, b))
    ceiling = Ceiling.Create(doc, [loop], ctype.Id, level.Id)
    ceiling.get_Parameter(BuiltInParameter.CEILING_HEIGHTABOVELEVEL_PARAM).Set(ft(2700))
    doc.Regenerate()
    res = doc.LoadFamily(rfa)
    fam = res[1] if isinstance(res, tuple) else None
    if fam is None:
        stem = os.path.splitext(os.path.basename(rfa))[0].lower()
        fam = [f for f in FilteredElementCollector(doc).OfClass(__import__("Autodesk.Revit.DB", fromlist=["Family"]).Family)
               if name(f).lower() == stem or stem in name(f).lower()][0]
    syms = [doc.GetElement(i) for i in fam.GetFamilySymbolIds()]
    out["family"] = name(fam)
    out["placement_type"] = str(fam.FamilyPlacementType)
    out["types_loaded_by_LoadFamily"] = [name(s) for s in syms]
    txt = os.path.splitext(rfa)[0] + ".txt"
    if not os.path.isfile(txt):
        txt = os.path.splitext(rfa)[0] + ".TXT"
    catalogue_types = []
    if os.path.isfile(txt):
        with open(txt, "rb") as fh:                     # IronPython's io.open returned '' for UTF-16
            rows = fh.read().decode("utf-16").splitlines()
        out["catalogue_header"] = rows[0][:2000]
        catalogue_types = [r.split(",")[0].strip('"') for r in rows[1:] if r.split(",")[0].strip('" ')]
        out["catalogue_types"] = catalogue_types
        for tn in catalogue_types[:3]:
            try:
                ok = doc.LoadFamilySymbol(rfa, tn)
                out.setdefault("LoadFamilySymbol", {})[tn] = bool(ok[0] if isinstance(ok, tuple) else ok)
            except Exception as exc:
                out.setdefault("LoadFamilySymbol", {})[tn] = "error: %s" % str(exc)[:120]
        syms = [doc.GetElement(i) for i in fam.GetFamilySymbolIds()]
        out["types_after_catalogue"] = [name(s) for s in syms]
    sym = syms[0]
    if not sym.IsActive:
        sym.Activate()
        doc.Regenerate()
    pt = XYZ(ft(2000), ft(2000), ft(2700))
    ptype = str(fam.FamilyPlacementType)
    if "Hosted" in ptype or "Face" in ptype or "WorkPlane" in ptype:
        try:
            inst = doc.Create.NewFamilyInstance(pt, sym, ceiling, level, Structure.StructuralType.NonStructural)
        except Exception as exc:
            out["hosted_place_error"] = str(exc)[:200]
            inst = doc.Create.NewFamilyInstance(pt, sym, level, Structure.StructuralType.NonStructural)
    else:
        inst = doc.Create.NewFamilyInstance(pt, sym, level, Structure.StructuralType.NonStructural)
    doc.Regenerate()
    geo = geometry(doc, inst)
    out["geometry_groups"] = geo
    z0, basis = emitter_z(geo)
    out["emitter_mm"], out["emitter_basis"] = z0, basis
    bb = inst.get_BoundingBox(None)
    out["bbox_mm"] = [mm(bb.Min.X), mm(bb.Min.Y), mm(bb.Min.Z), mm(bb.Max.X), mm(bb.Max.Y), mm(bb.Max.Z)]
    params = {}
    for label, holder in (("instance", inst), ("type", sym)):
        for p in holder.Parameters:
            try:
                v = p.AsValueString() or p.AsString()
            except Exception:
                v = None
            params["%s:%s" % (label, p.Definition.Name)] = {"value": v, "readonly": p.IsReadOnly,
                                                            "storage": str(p.StorageType)}
    out["parameters"] = params
    effects = []
    if z0 is not None:
        for p in inst.Parameters:
            try:
                if p.IsReadOnly or p.StorageType != StorageType.Double or p.Definition.GetDataType() != SpecTypeId.Length:
                    continue
            except Exception:
                continue
            st = SubTransaction(doc)
            st.Start()
            try:
                p.Set(p.AsDouble() + ft(100))
                doc.Regenerate()
                z1, _ = emitter_z(geometry(doc, inst))
                effects.append({"parameter": p.Definition.Name, "emitter_delta_mm": None if z1 is None else round(z1 - z0, 1)})
            except Exception as exc:
                effects.append({"parameter": p.Definition.Name, "error": str(exc)[:120]})
            st.RollBack()
            doc.Regenerate()
    out["emitter_levers"] = effects
    out["dialogs_answered"] = DIALOGS


import traceback
try:
    run()
except Exception:
    out["error"] = traceback.format_exc()[-2000:]
finally:
    try:
        if t is not None and t.HasStarted() and not t.HasEnded():
            t.RollBack()
    except Exception:
        pass
    out["dialogs_answered"] = DIALOGS
    try:
        doc.Close(False)
    except Exception as exc:
        out["close_error"] = str(exc)

dest = os.environ.get("ARCHPIPE_PROBE_OUT") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out", "product-family-probe.json")
# Serialise BEFORE opening the file, ASCII-escaped: IronPython died writing a
# non-ASCII catalogue header mid-stream and left a truncated JSON (the same
# trap extract_model.py records).
def _ascii(v):
    """Manufacturer text carries bytes like 0xAE (the registered sign) that
    IronPython's json cannot decode; escape every non-ASCII character."""
    if isinstance(v, dict):
        return dict((_ascii(k), _ascii(x)) for k, x in v.items())
    if isinstance(v, (list, tuple)):
        return [_ascii(x) for x in v]
    if isinstance(v, basestring):                                # noqa: F821 (IronPython 2)
        return "".join(c if ord(c) < 128 else "\u%04x" % ord(c) for c in v)
    return v


text = json.dumps(_ascii(out), indent=2, sort_keys=True, default=str)
with open(dest, "w") as fh:
    fh.write(text)
print("archpipe: wrote " + dest)
__revit__.DialogBoxShowing -= _on_dialog                         # noqa: F821
