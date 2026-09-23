# -*- coding: utf-8 -*-
"""The gate: can a downloaded family be loaded, ACTIVATED, placed, read back?

    $env:ARCHPIPE_MODEL      = "<abs>\\out\\revit2027\\test2027.rvt"
    $env:ARCHPIPE_FAMILY_DIR = "<abs>\\out\\families"
    $env:ARCHPIPE_PLACE_OUT  = "<abs>\\out\\place_families.json"
    pyrevit run "<abs>\\revit\\place_families_test.py" --revit=2027

Deliberately separate from building the bedroom. If families cannot be
placed programmatically then `build_bedroom.py` and everything downstream
needs rethinking, and that is worth discovering in a 60-line test rather
than inside a 600-line one.

THE TRAP THIS EXISTS TO CATCH

A `FamilySymbol` that is loaded but **not activated** makes
`NewFamilyInstance` return `None` *without raising*. Nothing errors. The
script carries on and reports success having placed nothing -- the same
shape of failure as the relative script path and the headless AutoCAD
hang already recorded in this project.

So this does not merely activate and hope. For the first family it
attempts placement **without** activating, records exactly what happens,
rolls that transaction back, and only then activates and places properly.
If the un-activated attempt turns out to succeed, the belief is wrong and
the report says so rather than quietly agreeing with the plan.

UNITS. Revit works in decimal feet. `ft()` and `mm()` are the only two
places that conversion happens; a units bug does not raise, it silently
produces geometry 304.8x wrong.
"""
import json
import os
import traceback

from Autodesk.Revit.DB import (BuiltInParameter, BuiltInCategory, Family,
                               FamilySymbol, FilteredElementCollector, Level,
                               Structure, Transaction, UnitTypeId, UnitUtils,
                               Wall, XYZ)

PRECISION = 3
MAX_FAMILIES = int(os.environ.get("ARCHPIPE_PLACE_MAX") or 8)


def el_name(el):
    """An element's name, robustly.

    `FamilySymbol.Name` raises `AttributeError: Name` under IronPython in
    Revit 2027 -- `Name` is declared on both `Element` and the symbol's own
    interface and the bridge cannot choose. Measured: `Family.Name` works
    fine, only the symbol is affected, so this is not a blanket problem to
    paper over everywhere.

    Invoking the `Element.Name` property descriptor explicitly resolves the
    ambiguity; `SYMBOL_NAME_PARAM` is the fallback. Returning "" would hide
    the failure, so an unreadable name is reported as such.
    """
    try:
        return el.Name
    except Exception:
        pass
    try:
        from Autodesk.Revit.DB import Element as _Element
        return _Element.Name.GetValue(el)
    except Exception:
        pass
    try:
        prm = el.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM)
        if prm is not None and prm.HasValue:
            return prm.AsString() or "<unnamed>"
    except Exception:
        pass
    return "<name unreadable>"


def mm(value):
    """Revit internal (feet) -> millimetres."""
    return round(UnitUtils.ConvertFromInternalUnits(value, UnitTypeId.Millimeters),
                 PRECISION)


def ft(value):
    """Millimetres -> Revit internal (feet)."""
    return UnitUtils.ConvertToInternalUnits(float(value), UnitTypeId.Millimeters)


def pt_mm(p):
    return [mm(p.X), mm(p.Y), mm(p.Z)]


# --------------------------------------------------------------------------
def resolve_doc():
    """The model document, in whichever context this is running.

    Same three contexts as `extract_model.resolve_doc`: ribbon button,
    `pyrevit run <model>` (where `revit.doc` returns **None** rather than
    raising), and a headless run that must open the file itself.
    """
    try:
        from pyrevit import revit
        if revit.doc is not None:
            return revit.doc
    except Exception:
        pass

    app = None
    try:
        app = __revit__.Application                     # noqa: F821
        for d in app.Documents:
            if d is None or d.IsFamilyDocument or d.IsLinked:
                continue
            return d
    except Exception as exc:
        raise RuntimeError("could not reach the Revit application: %s" % exc)

    path = os.environ.get("ARCHPIPE_MODEL")
    if path and app is not None:
        if not os.path.isfile(path):
            raise RuntimeError("model file not found: %s" % path)
        print("archpipe: opening %s" % path)
        return app.OpenDocumentFile(path)
    return None


def first_level(doc):
    levels = list(FilteredElementCollector(doc).OfClass(Level))
    levels.sort(key=lambda l: l.Elevation)
    return levels[0] if levels else None


def longest_wall(doc):
    """A host for wall-hosted families, and the longest one so a window
    fits inside it with room to spare."""
    best, best_len = None, 0.0
    for w in FilteredElementCollector(doc).OfClass(Wall):
        try:
            crv = w.Location.Curve
        except Exception:
            continue
        if crv.Length > best_len:
            best, best_len = w, crv.Length
    return best


def symbol_size_mm(sym):
    """Nominal width/height from the type, where the family declares them.

    `family_map.py` will compare these against the Neufert figures in
    `catalogue.py`; a family whose real width differs from the assumed one
    makes every downstream clearance check measure a fiction.
    """
    out = {}
    for label, bip in (("width_mm", BuiltInParameter.FAMILY_WIDTH_PARAM),
                       ("height_mm", BuiltInParameter.FAMILY_HEIGHT_PARAM),
                       ("rough_width_mm", BuiltInParameter.FAMILY_ROUGH_WIDTH_PARAM),
                       ("rough_height_mm", BuiltInParameter.FAMILY_ROUGH_HEIGHT_PARAM)):
        try:
            p = sym.get_Parameter(bip)
            if p is not None and p.HasValue:
                out[label] = mm(p.AsDouble())
        except Exception:
            pass
    return out


def place(doc, sym, level, host, point):
    """One placement attempt, dispatched on the family's placement type.

    Returns (instance_or_None, how). `how` records which overload was
    used, because "it placed" and "it placed the way we intended" are
    different claims.
    """
    ptype = str(sym.Family.FamilyPlacementType)
    create = doc.Create
    if "Hosted" in ptype:
        if host is None:
            return None, "hosted family but no host wall in the model"
        return (create.NewFamilyInstance(
            point, sym, host, level, Structure.StructuralType.NonStructural),
            "hosted on wall %s" % host.Id)
    if "OneLevelBased" in ptype or "TwoLevels" in ptype:
        return (create.NewFamilyInstance(
            point, sym, level, Structure.StructuralType.NonStructural),
            "level-based")
    return None, "unsupported placement type %s" % ptype


def read_back(inst, requested):
    """What the model actually contains, not what we asked for."""
    rec = {"id": str(inst.Id)}
    try:
        rec["family"] = el_name(inst.Symbol.Family)
        rec["type"] = el_name(inst.Symbol)
        rec["category"] = inst.Category.Name if inst.Category else None
    except Exception:
        pass
    try:
        loc = inst.Location
        pt = getattr(loc, "Point", None)
        if pt is not None:
            rec["placed_at_mm"] = pt_mm(pt)
            rec["requested_mm"] = requested
            rec["delta_mm"] = [round(a - b, PRECISION)
                               for a, b in zip(rec["placed_at_mm"], requested)]
    except Exception:
        pass
    try:
        bb = inst.get_BoundingBox(None)
        if bb is not None:
            rec["bbox_size_mm"] = [mm(bb.Max.X - bb.Min.X),
                                   mm(bb.Max.Y - bb.Min.Y),
                                   mm(bb.Max.Z - bb.Min.Z)]
    except Exception:
        pass
    return rec


# --------------------------------------------------------------------------
def main():
    out = {"families": [], "notes": [], "activation_trap": None}

    doc = resolve_doc()
    if doc is None:
        raise RuntimeError("no document; set ARCHPIPE_MODEL to a .rvt path")
    out["document"] = doc.Title

    level = first_level(doc)
    host = longest_wall(doc)
    out["level"] = level.Name if level else None
    out["host_wall"] = str(host.Id) if host is not None else None
    if host is not None:
        crv = host.Location.Curve
        mid = crv.Evaluate(0.5, True)
        out["host_wall_length_mm"] = mm(crv.Length)
    else:
        mid = XYZ(0, 0, 0)

    directory = os.environ.get("ARCHPIPE_FAMILY_DIR")
    if not directory or not os.path.isdir(directory):
        raise RuntimeError("set ARCHPIPE_FAMILY_DIR to the folder of .rfa files")
    files = sorted(f for f in os.listdir(directory) if f.lower().endswith(".rfa"))
    out["candidates"] = len(files)

    # Spread the sample across categories rather than taking the first N
    # alphabetically, which would be eight refrigerators.
    picked, seen = [], set()
    for f in files:
        key = f.split("_")[0].lower()
        if key in seen:
            continue
        seen.add(key)
        picked.append(f)
        if len(picked) >= MAX_FAMILIES:
            break
    out["tested"] = picked

    trap_done = False

    for fname in picked:
        path = os.path.join(directory, fname)
        rec = {"file": fname, "loaded": False, "placed": False}
        try:
            t = Transaction(doc, "load %s" % fname[:40])
            t.Start()
            fam = None
            try:
                res = doc.LoadFamily(path)
                if isinstance(res, tuple):
                    ok, fam = res
                else:
                    ok = bool(res)
            except Exception as exc:
                ok = False
                rec["load_error"] = str(exc)[:300]
            t.Commit()
            rec["loaded"] = bool(ok) or fam is not None

            if not rec["loaded"]:
                # Already loaded from a previous run is not a failure.
                for f2 in FilteredElementCollector(doc).OfClass(Family):
                    if f2.Name.lower() in fname.lower():
                        fam, rec["loaded"] = f2, True
                        rec["note"] = "already present in the document"
                        break
            if not rec["loaded"]:
                out["families"].append(rec)
                continue

            if fam is None:
                for f2 in FilteredElementCollector(doc).OfClass(Family):
                    fam = f2
            sym_ids = list(fam.GetFamilySymbolIds())
            rec["family_name"] = el_name(fam)
            rec["symbol_count"] = len(sym_ids)
            rec["placement_type"] = str(fam.FamilyPlacementType)
            try:
                rec["category"] = fam.FamilyCategory.Name
            except Exception:
                rec["category"] = None
            if not sym_ids:
                rec["error"] = "family loaded but declares no types"
                out["families"].append(rec)
                continue

            sym = doc.GetElement(sym_ids[0])
            rec["type_name"] = el_name(sym)
            rec["was_active_on_load"] = bool(sym.IsActive)
            rec["size_mm"] = symbol_size_mm(sym)

            # Where to put it: on the host wall's midpoint for hosted
            # families, otherwise a clear spot on the level.
            if "Hosted" in rec["placement_type"]:
                target = XYZ(mid.X, mid.Y, level.Elevation + ft(900.0))
            else:
                target = XYZ(ft(1000.0), ft(1000.0), level.Elevation)
            requested = pt_mm(target)

            # ---------------------------------------------------- the trap
            # Once, on the first family that is not already active: try to
            # place it WITHOUT activating, and record the truth.
            if not trap_done and not sym.IsActive:
                trap_done = True
                t = Transaction(doc, "trap: place without activating")
                t.Start()
                trap = {"family": el_name(fam), "type": el_name(sym),
                        "is_active_before": bool(sym.IsActive)}
                try:
                    inst, how = place(doc, sym, level, host, target)
                    trap["raised"] = False
                    trap["returned_none"] = inst is None
                    trap["placed_anyway"] = inst is not None
                    trap["how"] = how
                except Exception as exc:
                    trap["raised"] = True
                    trap["exception"] = "%s: %s" % (type(exc).__name__,
                                                    str(exc)[:220])
                    trap["returned_none"] = False
                    trap["placed_anyway"] = False
                # Roll back so the real test starts from a clean model.
                t.RollBack()
                trap["verdict"] = (
                    "CONFIRMED: returns None without raising"
                    if trap.get("returned_none") else
                    "raised an exception -- at least it is loud"
                    if trap.get("raised") else
                    "NOT a trap here: it placed without activation")
                out["activation_trap"] = trap

            # ------------------------------------------------ the real one
            t = Transaction(doc, "activate and place %s" % el_name(fam)[:30])
            t.Start()
            if not sym.IsActive:
                sym.Activate()
                doc.Regenerate()          # Activate alone is not enough
            rec["activated"] = bool(sym.IsActive)
            inst, how = place(doc, sym, level, host, target)
            rec["how"] = how
            if inst is None:
                rec["error"] = "NewFamilyInstance returned None after activation"
                t.RollBack()
            else:
                doc.Regenerate()
                rec["placed"] = True
                rec["read_back"] = read_back(inst, requested)
                t.Commit()

        except Exception:
            rec["error"] = traceback.format_exc()[-600:]
            try:
                if t.HasStarted() and not t.HasEnded():
                    t.RollBack()
            except Exception:
                pass

        out["families"].append(rec)

    placed = [f for f in out["families"] if f.get("placed")]
    out["placed_count"] = len(placed)
    out["ok"] = len(placed) > 0

    save_as = os.environ.get("ARCHPIPE_PLACE_SAVE_AS")
    if save_as and placed:
        try:
            from Autodesk.Revit.DB import SaveAsOptions
            opts = SaveAsOptions()
            opts.OverwriteExistingFile = True
            doc.SaveAs(save_as, opts)
            out["saved_as"] = save_as
        except Exception as exc:
            out["notes"].append("save failed: %s" % str(exc)[:200])

    dest = os.environ.get("ARCHPIPE_PLACE_OUT") or os.path.join(
        os.environ.get("USERPROFILE", "."), "archpipe_place_families.json")
    with open(dest, "w") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
    print("archpipe: wrote %s" % dest)
    print("archpipe: placed %d of %d tested"
          % (out["placed_count"], len(out["tested"])))
    if out["activation_trap"]:
        print("archpipe: activation trap -> %s"
              % out["activation_trap"]["verdict"])


if __name__ == "__main__":
    main()
