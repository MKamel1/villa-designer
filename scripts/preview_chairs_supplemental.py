"""Additional neutral room angles; original named cameras remain unchanged."""
import sys,json,hashlib,fcntl
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
import bpy
from mathutils import Vector
from archpipe.blender import villa_scene as builder
from garden_g6_preview import disable_material_emission
from copy import deepcopy
OUT=ROOT/'out/furniture-oct11';library=Path('/home/omar/archpipe/assets/library')
def main():
 data=json.loads((OUT/'current-furniture-scene.json').read_text());chairs=json.loads((OUT/'chairs-pending.json').read_text());records=[]
 requests=[('cinema','v08-cinema',dict(position=[4.4,-23.15,-1.65],target=[5.28,-21.426,-2.5],lens_mm=24,sensor_mm=36,shift_x=0.,shift_y=0.)),('kids-a','v06-kids-room',json.loads((ROOT/'out/desks/stage2/supplemental-view.json').read_text())['view']['camera'])]
 for room,original_id,camera_spec in requests:
  camera_spec=deepcopy(camera_spec)
  if room=='kids-a':camera_spec['target'][2]=.5
  bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
  meshes=[m for m in data['meshes'] if m['group'] in ('shell','context') or m.get('room')==room]
  names={m['material'] for m in meshes}|{n for m in meshes for n in m.get('face_materials',[])};warnings=[]
  materials={n:builder.add_material(n,data['materials'][n],str(library),warnings) for n in names};builder.configure_glass(materials,{n:data['materials'][n] for n in names})
  objects=builder.build_meshes(meshes,materials,data['materials'],warnings)
  models=[m for m in data['models'] if m.get('room')==room]+[m for m in chairs if m['room']==room]
  imported=builder.import_models(models,str(library),neutral_diagnostic=True)
  actual=[m for m in imported if m['role']=='task_chair'];disable_material_emission({m.name:m for m in bpy.data.materials})
  scene=bpy.context.scene;builder.configure_cycles(False);scene.cycles.samples=24;scene.render.threads_mode='FIXED';scene.render.threads=8
  scene.render.resolution_x=960;scene.render.resolution_y=640;scene.render.resolution_percentage=100
  scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.8,.8,.8,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.8
  scene.view_settings.view_transform='AgX';scene.view_settings.exposure=0;scene.render.image_settings.file_format='PNG'
  original=deepcopy(next(v for v in data['views'] if v['id']==original_id));view=deepcopy(original);view.update(id='diagnostic-'+room+'-task-chairs',subjects=[m['label'] for m in actual],camera=camera_spec)
  for mid in view.get('hide_meshes',[]):
   if mid in objects:objects[mid].hide_render=True
  camera,_=builder.configure_camera(view);scene.camera=camera;bpy.context.view_layer.update()
  subjects=builder.subjects(view,[],objects,actual)
  if not subjects or not all(s['full_frame'] for s in subjects):raise ValueError('supplemental actual chair geometry incomplete: '+str(subjects))
  center=[sum(m['position'][i] for m in actual)/len(actual) for i in range(3)];center[2]+=.46
  light=bpy.data.lights.new('recorded neutral supplemental softbox','AREA');light.energy=500;light.size=2;light.color=(1,1,1);lamp=bpy.data.objects.new(light.name,light);bpy.context.collection.objects.link(lamp);lamp.location=[center[0],center[1],center[2]+1.5];lamp.rotation_euler=(Vector(center)-lamp.location).to_track_quat('-Z','Y').to_euler()
  path=OUT/(room+'-chairs-room-supplemental-neutral.png');scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
  records.append(dict(image=str(path),image_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),view=view,original_view_unchanged=original,subjects=subjects,models=[dict(label=m['label'],selection=m['neutral_review']['selection'],source_sha256=m['review_geometry']['source_sha256'],import_transform_max_error_m=m['import_transform_max_error_m']) for m in actual],emission_disabled=True,diagnostic_light=dict(position_m=list(lamp.location),power_watts=500,size_m=2),review_status='pending'))
  (OUT/'supplemental-preview-evidence.json').write_text(json.dumps(records,indent=2)+'\n')
if __name__=='__main__':
 with Path('/home/omar/archpipe/locks/graphics.lock').open('rb') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);main()
