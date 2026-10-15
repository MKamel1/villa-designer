"""Exercise the real sky nodes and daylight builder under each Blender runtime."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import bpy
from archpipe.blender.photoreal import daylight_world
for altitude,azimuth in [(35.,0.),(12.,120.)]:
    result=daylight_world(altitude,azimuth)
    sky=next(n for n in bpy.context.scene.world.node_tree.nodes if n.type=='TEX_SKY')
    supported={i.identifier for i in sky.bl_rna.properties['sky_type'].enum_items}
    assert sky.sky_type==('NISHITA' if 'NISHITA' in supported else 'SINGLE_SCATTERING')
    assert sky.altitude==0 and sky.air_density==1 and sky.ozone_density==1
print('DAYLIGHT API PASS',bpy.app.version_string)
