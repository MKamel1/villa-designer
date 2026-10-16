"""Freeze actual runtime materials wrongly admitted by the initial static mask."""
import bpy,json,sys,hashlib
ROOT=__import__('pathlib').Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from archpipe.blender.walkthrough import static_position_output
from pathlib import Path
blend=Path(sys.argv[sys.argv.index('--')+1]);out=Path(sys.argv[sys.argv.index('--')+2])
bpy.ops.wm.open_mainfile(filepath=str(blend))
rows=[]
for material in bpy.data.materials:
 if not material.use_nodes:continue
 bsdfs=[n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED']
 old=bool(bsdfs) and all(n.inputs['Roughness'].default_value>=.7 and n.inputs['Metallic'].default_value==0 and n.inputs['Transmission Weight'].default_value==0 for n in bsdfs)
 old&=not any(n.type in ('EMISSION','BSDF_TRANSPARENT','BSDF_GLASS','BSDF_TRANSLUCENT') for n in material.node_tree.nodes)
 if not old or not any(n.inputs['Alpha'].is_linked for n in bsdfs):continue
 records=[]
 for n in bsdfs:
  r={'type':n.type}
  for key,socket in [('roughness','Roughness'),('metallic','Metallic'),('transmission','Transmission Weight'),('alpha','Alpha'),('emission_strength','Emission Strength')]:
   r[key]=float(n.inputs[socket].default_value);r[key+'_linked']=n.inputs[socket].is_linked
  r['emission_color_max']=max(n.inputs['Emission Color'].default_value[:3]);r['emission_color_linked']=n.inputs['Emission Color'].is_linked
  records.append(r)
 rows.append(dict(material=material.name,nodes=records,old_static_eligible=bool(old),expected_static_eligible=False))
 if len(rows)==4:break
out.parent.mkdir(parents=True,exist_ok=True)
static_position_output(out.parent)
for row in rows:
 nodes=bpy.data.materials[row['material']].node_tree.nodes
 mask=next(n for n in nodes if n.type=='OUTPUT_AOV' and n.aov_name=='walk-static')
 row['actual_static_mask']=float(mask.inputs['Value'].default_value)
out.write_text(json.dumps(dict(source=str(blend),materials=rows),indent=2)+'\n')
if not rows:raise ValueError('No actual linked-opacity reproduction found')
if any(r['actual_static_mask']!=0 for r in rows):raise ValueError('Nonopaque actual material admitted to static temporal mask')
