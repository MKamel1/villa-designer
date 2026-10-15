"""Render the preregistered denoising ladder from copies of built view scenes.

These are evaluation images at draft resolution, not presentation releases.
The reference settings and camera come from the saved production-built scene.
"""
import argparse,json,os,sys,time
from pathlib import Path
import bpy
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--reference',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);a.out.mkdir(parents=True,exist_ok=True)
s=bpy.context.scene
s.render.threads_mode='FIXED';s.render.threads=8
s.cycles.samples=1024 if a.reference else 64
s.cycles.denoiser='OPENIMAGEDENOISE' if a.reference else 'OPTIX'
prefs=bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type='OPTIX';prefs.get_devices()
for d in prefs.devices:d.use=d.type=='OPTIX'
s.cycles.device='GPU';s.cycles.use_denoising=True
s.render.image_settings.file_format='PNG';s.render.image_settings.color_depth='8'
rows=[]
for samples in ([1024] if a.reference else [64,128,256,512,1024]):
    s.cycles.samples=samples;s.render.filepath=str(a.out/(str(samples)+'.png'))
    start=time.monotonic();bpy.ops.render.render(write_still=True);elapsed=time.monotonic()-start
    rows.append(dict(samples=samples,seconds=elapsed,denoiser=s.cycles.denoiser,version=bpy.app.version_string,
                     resolution=[s.render.resolution_x,s.render.resolution_y],exposure_stops=s.view_settings.exposure,
                     adaptive_sampling=s.cycles.use_adaptive_sampling,adaptive_threshold=s.cycles.adaptive_threshold,
                     camera=s.camera.name,view_transform=s.view_settings.view_transform,look=s.view_settings.look,
                     display=s.display_settings.display_device))
    (a.out/'timings.json').write_text(json.dumps(rows,indent=2))
