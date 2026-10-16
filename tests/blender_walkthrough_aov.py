"""Isolated diagnostic: production temporal buffers preserve world units and beauty.

The factory cube is a calibration object, never walkthrough model geometry.
Run inside pinned Blender with the output directory after --.
"""
from pathlib import Path
import json
import sys
import bpy
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from archpipe.blender.walkthrough import static_position_output
from archpipe.blender.villa_scene import configure_camera
out=Path(sys.argv[sys.argv.index('--')+1]);out.mkdir(parents=True,exist_ok=True)
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=1
scene.cycles.seed=0;scene.cycles.use_animated_seed=False;scene.cycles.use_denoising=False
scene.render.resolution_x=scene.render.resolution_y=32;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_depth='8'
for material in bpy.data.materials:
 if material.use_nodes:
  for node in material.node_tree.nodes:
   if node.type=='BSDF_PRINCIPLED':node.inputs['Roughness'].default_value=.8
if '--glass' in sys.argv:
 from archpipe.blender.villa_scene import add_material,configure_glass
 spec={'kind':'glass','base_rgb':[1,1,1],'transmittance':.85,'interfaces':2,'ior':1.52,'roughness':0.}
 material=add_material('glass-clear',spec,'',[])
 configure_glass({'glass-clear':material},{'glass-clear':spec})
 bpy.ops.mesh.primitive_cube_add(size=1,location=(2,0,0))
 pane=bpy.context.object;pane.scale=(.01,5,5);pane.data.materials.append(material)
offset=(20,-25,-3) if '--translated' in sys.argv else (0,0,0)
for obj in bpy.data.objects:
 if obj.type in ('MESH','LIGHT'):
  for axis,value in enumerate(offset):obj.location[axis]+=value
configure_camera({'camera':{'position':[4+offset[0],offset[1],offset[2]],'target':list(offset),'lens_mm':24,'sensor_mm':36}})
scene.render.filepath=str(out/'before.png');bpy.ops.render.render(write_still=True)
node=static_position_output(out);node.file_slots[0].path='positions-'
scene.render.filepath=str(out/'after.png');bpy.ops.render.render(write_still=True)
values=[]
for name in ['before.png','after.png']:
 image=bpy.data.images.load(str(out/name));values.append(np.array(image.pixels[:]))
 bpy.data.images.remove(image)
image=bpy.data.images.load(str(next(out.glob('positions-*.exr'))))
positions=np.array(image.pixels[:]).reshape(32,32,4)
mask=positions[:,:,3]>.999
record=dict(blender=bpy.app.version_string,beauty_identical=bool(np.array_equal(*values)),
            static_pixels=int(mask.sum()),maximum_world_x_error=float(np.abs(positions[:,:,0][mask]-(1+offset[0])).max()) if mask.any() else None)
record['mean_world_position']=positions[:,:,:3][mask].mean(0).tolist() if mask.any() else None
record['passed']=record['beauty_identical'] and record['static_pixels']>20 and record['maximum_world_x_error']<.0001 and abs(record['mean_world_position'][1]-offset[1])<.01 and abs(record['mean_world_position'][2]-offset[2])<.01
(out/'result.json').write_text(json.dumps(record,indent=2)+'\n')
if not record['passed']:raise ValueError(record)
