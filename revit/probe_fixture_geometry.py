# -*- coding: utf-8 -*-
"""Read fixture geometry categories and writable dimensions in a saved model."""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extract_model as extract
from Autodesk.Revit.DB import BuiltInCategory, BuiltInParameter, StorageType

doc = extract.resolve_doc()
records = []
for fixture in extract._collect(doc, BuiltInCategory.OST_LightingFixtures):
    record = {'mark':extract._param_str(fixture,BuiltInParameter.ALL_MODEL_MARK),
              'parameters':{},'mesh_groups':[]}
    for label, holder in [('instance',fixture),('type',fixture.Symbol)]:
        rows=[]
        for parameter in holder.Parameters:
            name=parameter.Definition.Name
            if any(word in name.lower() for word in ('length','height','offset','source','drop','size')):
                rows.append({'name':name,'read_only':parameter.IsReadOnly,
                             'display_value':parameter.AsValueString()})
        record['parameters'][label]=sorted(rows,key=lambda r:r['name'])
    meshes,_ = extract.extract_meshes(doc,fixture)
    for mesh in meshes:
        record['mesh_groups'].append({'subcategory':mesh.get('subcategory'),
            'material':mesh['material']['name'],'triangles':len(mesh['triangles']),
            'height_bounds_mm':[min(v[2] for v in mesh['vertices_mm']),max(v[2] for v in mesh['vertices_mm'])]})
    records.append(record)
dest=os.environ['ARCHPIPE_GEOMETRY_PROBE_OUT']
with open(dest,'w') as output:
    json.dump(records,output,indent=2)
print('archpipe: wrote '+dest)
