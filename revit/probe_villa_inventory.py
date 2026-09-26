# -*- coding: utf-8 -*-
"""Read-only inventory of the real villa model (a COPY of omar.rvt).

    $env:ARCHPIPE_MODEL = "<abs path to out\\villa\\omar-copy.rvt>"
    $env:ARCHPIPE_INVENTORY_OUT = "<abs path to out\\villa\\omar-inventory.json>"
    pyrevit run <abs path to this file> --revit=2027

Adds what extract_model.py does not read: structural columns and framing (the elements the client
says must be kept), floors, roofs, stairs, grids, CAD imports and links, levels with elevations,
counts by category, and bounding boxes, all in millimetres through extract_model.mm(). Never saves.
"""
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import extract_model as X                                          # noqa: E402
from Autodesk.Revit.DB import (BuiltInCategory, FilteredElementCollector, ImportInstance,  # noqa: E402
                               RevitLinkInstance)


def _bbox(el):
    try:
        bb = el.get_BoundingBox(None)
        if bb is None:
            return None
        return {"min": [X.mm(bb.Min.X), X.mm(bb.Min.Y), X.mm(bb.Min.Z)],
                "max": [X.mm(bb.Max.X), X.mm(bb.Max.Y), X.mm(bb.Max.Z)]}
    except Exception:
        return None


def _level_name(doc, el):
    try:
        lid = el.LevelId
        lv = doc.GetElement(lid)
        return X._name(lv) if lv is not None else None
    except Exception:
        return None


def _items(doc, bic, extra=None):
    out = []
    for el in X._collect(doc, bic):
        row = {"id": el.Id.IntegerValue if hasattr(el.Id, "IntegerValue") else el.Id.Value,
               "name": X._name(el), "level": _level_name(doc, el), "bbox": _bbox(el)}
        try:
            sym = doc.GetElement(el.GetTypeId())
            row["type"] = X._name(sym) if sym is not None else None
        except Exception:
            row["type"] = None
        if extra:
            row.update(extra(el))
        out.append(row)
    return out


def _save_upgraded(doc):
    """Save the upgraded copy FIRST: the 2021->2027 upgrade takes ~17 min, so a later failure must not waste it."""
    upgraded = os.environ.get("ARCHPIPE_SAVE_UPGRADED")
    if upgraded and not os.path.exists(upgraded):   # a NEW file; the source copy and the original stay as they are
        from Autodesk.Revit.DB import SaveAsOptions
        opts = SaveAsOptions()
        opts.OverwriteExistingFile = False
        try:
            doc.SaveAs(upgraded, opts)
            print("archpipe: saved upgraded copy %s" % upgraded)
        except Exception as exc:
            print("archpipe: save upgraded failed: %s: %s" % (type(exc).__name__, exc))


def main():
    doc = X.resolve_doc()
    _save_upgraded(doc)
    cats = {}
    for el in FilteredElementCollector(doc).WhereElementIsNotElementType().ToElements():
        c = el.Category
        if c is not None:
            cats[c.Name] = cats.get(c.Name, 0) + 1
    data = {
        "source": "revit", "units": "mm", "project": {"name": doc.Title, "path": doc.PathName},
        "site": X.extract_site(doc),
        "levels": X.extract_levels(doc),
        "structural_columns": _items(doc, BuiltInCategory.OST_StructuralColumns),
        "architectural_columns": _items(doc, BuiltInCategory.OST_Columns),
        "structural_framing": _items(doc, BuiltInCategory.OST_StructuralFraming),
        "floors": _items(doc, BuiltInCategory.OST_Floors),
        "roofs": _items(doc, BuiltInCategory.OST_Roofs),
        "stairs": _items(doc, BuiltInCategory.OST_Stairs),
        "walls_count": len(list(X._collect(doc, BuiltInCategory.OST_Walls))),
        "grids": [{"name": X._name(g), "bbox": _bbox(g)} for g in X._collect(doc, BuiltInCategory.OST_Grids)],
        "imports": [{"name": X._name(i), "linked": bool(i.IsLinked), "bbox": _bbox(i)}
                    for i in FilteredElementCollector(doc).OfClass(ImportInstance).ToElements()],
        "revit_links": [{"name": X._name(i), "bbox": _bbox(i)}
                        for i in FilteredElementCollector(doc).OfClass(RevitLinkInstance).ToElements()],
        "counts_by_category": cats,
    }
    dest = os.environ.get("ARCHPIPE_INVENTORY_OUT")
    _write(dest, data)
    print("archpipe: wrote %s" % dest)
    extract_dest = os.environ.get("ARCHPIPE_EXTRACT_OUT")
    if extract_dest:                        # the standard extract too, in the same (slow) session
        try:
            _write(extract_dest, X.build(doc))
            print("archpipe: wrote %s" % extract_dest)
        except Exception as exc:
            print("archpipe: extract failed: %s: %s" % (type(exc).__name__, exc))


def _clean(v):
    """Make every value JSON-safe: the model holds Arabic text, and Revit 2027 ElementId.Value is a .NET Int64,
    both of which IronPython's json encoder rejects."""
    if v is None or isinstance(v, bool):
        return v
    if isinstance(v, dict):
        return dict((_clean(k), _clean(x)) for k, x in v.items())
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    if isinstance(v, str) or type(v).__name__ in ("unicode", "String"):
        try:
            return u"%s" % v
        except Exception:
            return repr(v)
    if isinstance(v, float):
        return v
    if isinstance(v, int) and type(v).__name__ == "int":
        return v
    try:                                            # long, Int64, Int32, Double and the like
        f = float(v)
        return int(f) if f == int(f) and abs(f) < 2 ** 53 else f
    except Exception:
        return repr(v)


def _write(path, data):
    import codecs
    with codecs.open(path, "w", "utf-8") as fh:
        fh.write(json.dumps(_clean(data), indent=1, sort_keys=True, ensure_ascii=True))


if __name__ == "__main__":
    main()
