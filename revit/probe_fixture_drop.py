# -*- coding: utf-8 -*-
"""Which parameter actually moves each fitting's light source?

The host offset does not: the bedroom's drum pendants had offsets of -700
and -400 mm and both emitted from exactly 2243 mm, the cord always running
to the ceiling. So nudge every writable length parameter by +100 mm, one at
a time inside a rolled-back transaction, and measure where the source goes.
The parameter that moves it is the lever build_bedroom.py must drive.
"""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extract_model as extract
from Autodesk.Revit.DB import (BuiltInCategory, BuiltInParameter, StorageType,
                               Transaction, UnitTypeId, UnitUtils, SpecTypeId)


def source_z(doc, fixture):
    """Same rule as archpipe.fixture_source: symbol apex, else lens centre."""
    meshes, _ = extract.extract_meshes(doc, fixture)
    sym = [v[2] for m in meshes if m['geometry_role'] == 'light_source_symbol' for v in m['vertices_mm']]
    if sym:
        return max(sym)
    lens = [v[2] for m in meshes if 'lens' in m['material']['name'].lower() for v in m['vertices_mm']]
    if lens:
        return (min(lens) + max(lens)) / 2.0
    return None


def lengths(holder):
    out = []
    for p in holder.Parameters:
        try:
            if p.StorageType != StorageType.Double or p.IsReadOnly:
                continue
            if p.Definition.GetDataType() != SpecTypeId.Length:
                continue
            out.append(p)
        except Exception:
            continue
    return out


doc = extract.resolve_doc()
records = []
step = UnitUtils.ConvertToInternalUnits(100.0, UnitTypeId.Millimeters)
for fixture in extract._collect(doc, BuiltInCategory.OST_LightingFixtures):
    mark = extract._param_str(fixture, BuiltInParameter.ALL_MODEL_MARK)
    base = source_z(doc, fixture)
    rec = {'mark': mark, 'source_mm': base, 'effects': []}
    for label, holder in (('instance', fixture), ('type', fixture.Symbol)):
        for p in lengths(holder):
            name = p.Definition.Name
            row = {'where': label, 'name': name, 'value': p.AsValueString()}
            t = Transaction(doc, 'probe ' + name)
            t.Start()
            try:
                p.Set(p.AsDouble() + step)
                doc.Regenerate()
                z = source_z(doc, fixture)
                row['source_delta_mm'] = None if (z is None or base is None) else round(z - base, 1)
            except Exception as exc:
                row['error'] = str(exc)[:120]
            t.RollBack()
            rec['effects'].append(row)
    records.append(rec)
dest = os.environ.get('ARCHPIPE_DROP_PROBE_OUT') or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'out', 'fixture-drop-probe.json')
with open(dest, 'w') as fh:
    json.dump(records, fh, indent=2)
print('archpipe: wrote ' + dest)
