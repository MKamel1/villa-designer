"""Evaluation-only Blender wrapper; production defaults and inputs remain intact."""
import hashlib
import json
import os
from pathlib import Path
import sys
import bpy
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
sys.path.insert(0, str(ROOT/'scripts'))
from blender52_eval import require_gpu
from archpipe.blender import villa_scene as V
OUT = Path(os.environ['BLENDER52_JOB'])
OUT.mkdir(parents=True, exist_ok=True)

def color():
    s = bpy.context.scene
    return dict(view_transform=s.view_settings.view_transform, look=s.view_settings.look,
                display=s.display_settings.display_device, exposure=s.view_settings.exposure,
                gamma=s.view_settings.gamma)
(OUT/'factory-color.json').write_text(json.dumps(color(), indent=2))
original_import = V.import_models

def imports(specs, library, *args, **kwargs):
    rows = original_import(specs, library, *args, **kwargs)
    from archpipe.imported_appearance import digest
    report=[]
    for spec, row in zip(specs, rows):
        meshes=[]
        for obj in row.get('objects', []):
            meshes.append(dict(name=obj.get('source_part', obj.name), vertices=len(obj.data.vertices),
                               faces=len(obj.data.polygons)))
        report.append(dict(id=spec['id'], status=row.get('status'), meshes=meshes,
                           review_geometry=spec.get('review_geometry'), bounds=row.get('bounds'),
                           placement_sha256=digest(spec),
                           import_transform_max_error_m=row.get('import_transform_max_error_m')))
    (OUT/'imports.json').write_text(json.dumps(report, indent=2))
    return rows
V.import_models=imports
original_configure=V.configure_cycles

def configure(cpu):
    original_configure(cpu)
    s=bpy.context.scene
    if os.environ.get('BLENDER52_DENOISER'):
        s.cycles.denoiser=os.environ['BLENDER52_DENOISER']
    if os.environ.get('BLENDER52_MATCH_COLOR'):
        c=json.loads(Path(os.environ['BLENDER52_MATCH_COLOR']).read_text())
        s.display_settings.display_device=c['display']
        s.view_settings.gamma=c['gamma']
    devices=[dict(name=d.name,type=d.type,use=d.use) for d in bpy.context.preferences.addons['cycles'].preferences.devices]
    if not cpu:require_gpu(s.cycles.device,devices)
    (OUT/'runtime.json').write_text(json.dumps(dict(version=bpy.app.version_string,
        build_hash=bpy.app.build_hash.decode(), denoiser=s.cycles.denoiser, device=s.cycles.device,
        color=color(),devices=devices),indent=2))
V.configure_cycles=configure
saved=False

def before_render(scene, *args):
    global saved
    (OUT/'render-color.json').write_text(json.dumps(color(),indent=2))
    if os.environ.get('BLENDER52_SAVE_BLEND') and not saved:
        bpy.ops.wm.save_as_mainfile(filepath=os.environ['BLENDER52_SAVE_BLEND'],compress=True)
        saved=True
bpy.app.handlers.render_pre.append(before_render)
V.main()
