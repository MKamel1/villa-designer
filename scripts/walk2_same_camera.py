"""Native diagnostic: rebuilt plants at the exact rejected v1 cameras.

Run inside pinned Blender after the walk2 assembly is admitted. This preserves
the original exposure and scene state to prevent a route change from hiding
the reproduced planting failure. It is not the new route's sample selection.
"""
from pathlib import Path
import hashlib
import json
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import bpy
import numpy as np
from archpipe.blender import walkthrough as W
from archpipe.flythrough import digest


def main(root=None):
    from types import SimpleNamespace
    root=Path(root or ROOT/'out/walk2').resolve()
    args=SimpleNamespace(root=str(root))
    path,scene,context=W.load_context(args)
    original=json.loads((ROOT/'out/flythrough/path.json').read_text())
    lock=json.loads((ROOT/'out/flythrough/exposure/lock.json').read_text())
    if original['sha256']!=lock['path_sha256']:raise ValueError('Original camera lock differs')
    # Keep original timed motion, but expose for half a frame at the new rate.
    original['settings'].update(fps=path['settings']['fps'],motion_blur=path['settings']['motion_blur'])
    output=root/'same-camera';output.mkdir(exist_ok=True)
    rows=[]
    for index in range(588,605):
        frame=original['frames'][index]
        view=dict(scene['views'][0],id=f'frame-{index:04d}',camera=frame['camera'],subjects=['landscape-g6-terrace'])
        camera,pitch,emissive=W.setup(scene,context,view)
        # Retain original timestamps while using the selected policy rate
        # to express camera keyframes and the physical shutter interval.
        W.animate_camera(camera,original,frame['seconds']*path['settings']['fps'])
        pixel_filter=W.configure_pixel_filter(path['settings'])
        s=bpy.context.scene
        s.render.resolution_x,s.render.resolution_y=1920,1080;s.render.resolution_percentage=100
        s.cycles.samples=64;s.cycles.max_bounces=16;s.cycles.use_adaptive_sampling=False
        s.cycles.use_denoising=True;s.cycles.seed=0;s.cycles.use_animated_seed=False
        s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast'
        s.view_settings.exposure=lock['exposure_stops']
        W.V.photoreal.white_balance(lock['white_balance_k'],illuminant=lock['white_balance_illuminant'])
        file=output/f'frame-{index:04d}.png'
        s.render.image_settings.file_format='PNG';s.render.image_settings.color_depth='8';s.render.filepath=str(file)
        start=time.monotonic();bpy.ops.render.render(write_still=True)
        rows.append(dict(index=index,seconds=time.monotonic()-start,camera=frame['camera'],
             png_sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
        W.remove_camera(camera)
    W.save(output/'receipt.json',dict(frames=rows,original_path_sha256=original['sha256'],
        original_exposure_lock_sha256=lock['sha256'],new_path_sha256=path['sha256'],
        evaluated_meshes_sha256=context['receipt']['evaluated_meshes_sha256'],
        settings=dict(samples=64,shutter_frames=path['settings']['motion_blur']['shutter_frames'],fps=path['settings']['fps'],pixel_filter=pixel_filter),
        scope='original camera samples at their original timestamps, with the selected policy shutter exposure; no route-dependent acceptance'))


if __name__=='__main__':main()
