"""Evaluation batch: original scene, per-view reference exposures, post-render probes.

The shared builder is reused unchanged; evaluation overrides are explicit in
receipts. Reference exposures avoid a changed meter hiding renderer drift.
"""
import json,os,runpy,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from archpipe.blender import villa_scene as V
OUT=Path(os.environ['BLENDER52_JOB']);OUT.mkdir(parents=True,exist_ok=True)
references=json.loads((ROOT/'out/blender52/reference-views.json').read_text())
current={};captured={}
original_camera=V.configure_camera

def camera(view):
    current['view']=view['id']
    return original_camera(view)
V.configure_camera=camera
class Locks(dict):
    def __getitem__(self,key):return references[current['view']]['exposure_stops']

def locks(views,selected,meter):
    states={v['exposure'] for v in views if v['id'] in selected}
    return Locks({k:0 for k in states}),{},{}
V.exposure_locks=locks
initial_visibility={}
original_receipt=V.evaluated_scene_receipt

def receipt(*args,**kwargs):
    initial_visibility.update({obj.name:obj.hide_render for obj in bpy.data.objects})
    local=sys._getframe(1).f_locals
    for key in ('scene_data','args','lights','full_power','emissive_sources','mesh_by_id','switched_emitters'):
        captured[key]=local[key]
    return original_receipt(*args,**kwargs)
V.evaluated_scene_receipt=receipt
representatives={'v01-kitchen-garden','v08-cinema','v36-north-garden'}
saved=set()

def save_reference(scene,*unused):
    ident=current.get('view')
    if ident in representatives and ident not in saved:
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(ident+'.blend')),compress=True)
        saved.add(ident)
bpy.app.handlers.render_pre.append(save_reference)
runpy.run_path(str(ROOT/'scripts/blender52_scene.py'),run_name='__main__')
bpy.app.handlers.render_pre.remove(save_reference)
for name,hidden in initial_visibility.items():
    if name in bpy.data.objects:bpy.data.objects[name].hide_render=hidden
# The task-point method disables display transforms and builds linear meters.
V.measure_lighting(captured['scene_data'],captured['args'],captured['lights'],captured['full_power'],
                   captured['emissive_sources'],captured['mesh_by_id'],captured['switched_emitters'])
