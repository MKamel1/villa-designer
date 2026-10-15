"""Small production-path grey-card measurement; run with pinned Blender.

The caller holds the workstation graphics lock. PNG development and exposure
use the same helpers as villa_scene; this is a diagnostic, not a villa gate.
"""
import json
import math
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
from archpipe.blender import build_scene, photoreal, villa_scene


def main():
    out = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for kind, temperature in [('lamp', t) for t in (2700, 3000, 4300, 5500)] + [('daylight', 5500)]:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        scene = bpy.context.scene
        scene.render.engine = 'CYCLES'
        villa_scene.configure_cycles(False)
        scene.render.resolution_x = scene.render.resolution_y = 128
        scene.render.resolution_percentage = 100
        scene.cycles.samples = 64
        scene.cycles.seed = 0
        scene.cycles.use_denoising = False
        scene.render.dither_intensity = 0
        photoreal.presentation_render_settings('AgX - Medium High Contrast')
        scene.cycles.use_denoising = False
        scene.view_settings.view_transform = 'AgX'
        scene.view_settings.look = 'AgX - Medium High Contrast'
        bpy.ops.mesh.primitive_plane_add(size=200)
        card = bpy.context.object
        material = bpy.data.materials.new('equal-channel-0.5-diffuse')
        material.use_nodes = True
        nodes = material.node_tree.nodes
        nodes.clear()
        diffuse = nodes.new('ShaderNodeBsdfDiffuse')
        diffuse.inputs['Color'].default_value = (0.5, 0.5, 0.5, 1)
        material.node_tree.links.new(diffuse.outputs[0], nodes.new('ShaderNodeOutputMaterial').inputs['Surface'])
        card.data.materials.append(material)
        bpy.ops.object.camera_add(location=(0, 0, 3))
        camera = bpy.context.object
        camera.data.type = 'ORTHO'
        camera.data.ortho_scale = 1
        scene.camera = camera
        source_rgb = None
        if kind == 'lamp':
            world = bpy.data.worlds.new('black')
            world.use_nodes = True
            world.node_tree.nodes.get('Background').inputs['Strength'].default_value = 0
            scene.world = world
            light = bpy.data.lights.new('single-lamp', 'SUN')
            source_rgb = build_scene.kelvin_to_rgb(temperature)
            light.color = source_rgb
            light.energy = 10
            obj = bpy.data.objects.new('single-lamp', light)
            scene.collection.objects.link(obj)
        else:
            photoreal.daylight_world(40.07, 135.34)
        exposure, log_average = photoreal.camera_meter(bias_stops=-0.4, look='AgX - Medium High Contrast')
        scene.view_settings.exposure = exposure
        illuminant = 'planckian' if kind == 'lamp' else 'daylight'
        assert photoreal.white_balance(temperature, illuminant=illuminant)
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_depth = '8'
        name = f'{kind}-{temperature}'
        scene.render.filepath = str(out / (name + '.png'))
        bpy.ops.render.render(write_still=True)
        scene.render.image_settings.file_format = 'OPEN_EXR'
        scene.render.image_settings.color_depth = '32'
        path = out / (name + '.exr')
        bpy.data.images['Render Result'].save_render(str(path), scene=scene)
        linear = bpy.data.images.load(str(path))
        pixels = linear.pixels[:]
        mean = [sum(pixels[i::4]) / (len(pixels) // 4) for i in range(3)]
        rows.append(dict(kind=kind, temperature=temperature, source_rgb=source_rgb,
                         linear_mean=mean, exposure=exposure, log_average=log_average,
                         tint=scene.view_settings.white_balance_tint, illuminant=illuminant,
                         whitepoint=list(scene.view_settings.white_balance_whitepoint),
                         version=bpy.app.version_string,
                         look=scene.view_settings.look, png=name + '.png'))
        (out / 'readings.json').write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    main()
