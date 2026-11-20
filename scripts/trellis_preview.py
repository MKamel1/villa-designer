"""Blender 4.5.14 neutral TRELLIS comparison, outside the villa scene.

Reuse the project's native mesh builder, scene reset, neutral-light sizing,
clipping and framing checks. Both appearances use one recorded camera and
one neutral lighting setup, with material emission disabled. Source meshes
remain untouched. This command never writes an appearance-admission receipt.
"""
from __future__ import annotations

import argparse
import fcntl
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]


def main():
    import bpy
    from mathutils import Vector
    from archpipe.blender import villa_scene as builder
    from archpipe.blender.scene_reset import clear_objects, scene_meshes
    from archpipe.beds import preview_clip_range, preview_datums, preview_neutral_light
    from garden_g6_preview import disable_material_emission, ortho_specimen_frame_findings
    from trellis_trial import mesh_measurement, sha256, uniform_scale
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--object', required=True, choices=['pendant', 'plant', 'stool'])
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--samples', type=int, default=128)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    if bpy.app.version[:3] != (4, 5, 14):
        raise RuntimeError('trial requires Blender 4.5.14')
    args.out.mkdir(parents=True, exist_ok=False)
    baselines = json.loads((ROOT / 'out/trellis/baselines.json').read_text())
    baseline = next(row for row in baselines['objects'] if row['id'] == args.object)
    photo = next(row for row in json.loads((ROOT / 'out/trellis/inputs/manifest.json').read_text())
                 if row['id'] == args.object)
    with Path('/home/omar/archpipe/locks/graphics.lock').open('rb') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        clear_objects(bpy)
        bpy.ops.import_scene.gltf(filepath=str(args.model.resolve()))
        generated = scene_meshes(bpy)
        if not generated:
            raise ValueError('generated file contains no actual mesh')
        vertices = []
        triangles = []
        for obj in generated:
            obj.data.calc_loop_triangles()
            offset = len(vertices)
            vertices.extend([list(obj.matrix_world @ vertex.co) for vertex in obj.data.vertices])
            triangles.extend([[offset + index for index in face.vertices]
                              for face in obj.data.loop_triangles])
        metrics = mesh_measurement(vertices, triangles)
        fit = uniform_scale(metrics['bounds'], photo['target_m'],
                            'horizontal' if args.object == 'pendant' else 'height')
        # Parent all imported roots to one common scale/translation anchor.
        roots = [obj for obj in list(bpy.context.scene.objects) if obj.parent is None]
        anchor = bpy.data.objects.new('one uniform generated appearance transform', None)
        bpy.context.collection.objects.link(anchor)
        for obj in roots:
            obj.parent = anchor
        scale = fit['scale_xyz'][0]
        low, high = metrics['bounds']
        anchor.scale = (scale,) * 3
        anchor.location = (-scale * (low[0] + high[0]) / 2,
                           -scale * (low[1] + high[1]) / 2, -scale * low[2])
        # Baseline geometry undergoes rigid isolation only, preserving its size.
        low, high = baseline['bounds_m']
        origin = [(low[0] + high[0]) / 2, (low[1] + high[1]) / 2, low[2]]
        meshes = json.loads(json.dumps(baseline['meshes']))
        for row in meshes:
            row['faces'] = [[[p[k] - origin[k] for k in range(3)] for p in face]
                            for face in row['faces']]
        warnings = []
        materials = {name: builder.add_material(name, definition,
                      '/home/omar/archpipe/assets/library', warnings)
                     for name, definition in baseline['materials'].items()}
        native = list(builder.build_meshes(meshes, materials, baseline['materials'], warnings).values())
        disable_material_emission({material.name: material for material in bpy.data.materials})
        bpy.context.view_layer.update()
        fitted_points = [obj.matrix_world @ vertex.co for obj in generated for vertex in obj.data.vertices]
        fitted_bounds = [[min(p[k] for p in fitted_points) for k in range(3)],
                         [max(p[k] for p in fitted_points) for k in range(3)]]
        fitted_dimensions = [fitted_bounds[1][k] - fitted_bounds[0][k] for k in range(3)]
        measured_datum = max(fitted_dimensions[:2]) if args.object == 'pendant' else fitted_dimensions[2]
        if abs(measured_datum - photo['target_m']) > 1e-6:
            raise ValueError('native read-back disagrees with uniform target dimension')
        points = [list(obj.matrix_world @ vertex.co) for obj in generated + native
                  for vertex in obj.data.vertices]
        datums = preview_datums(points)
        scene = bpy.context.scene
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = args.samples
        scene.cycles.seed = 0
        scene.cycles.use_animated_seed = False
        scene.cycles.use_denoising = True
        scene.cycles.max_bounces = 8
        scene.render.threads_mode = 'FIXED'
        scene.render.threads = 8
        preferences = bpy.context.preferences.addons['cycles'].preferences
        preferences.compute_device_type = 'OPTIX'
        preferences.get_devices()
        for device in preferences.devices:
            device.use = device.type == 'OPTIX'
        if not any(device.use for device in preferences.devices):
            raise RuntimeError('neutral GPU rendering unavailable')
        scene.cycles.device = 'GPU'
        scene.render.resolution_x, scene.render.resolution_y = 960, 720
        scene.render.resolution_percentage = 100
        scene.world.use_nodes = True
        scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.8, .8, .8, 1)
        scene.world.node_tree.nodes['Background'].inputs[1].default_value = .8
        scene.view_settings.view_transform = 'AgX'
        scene.view_settings.look = 'None'
        scene.view_settings.exposure = 0
        scene.render.image_settings.file_format = 'PNG'
        bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, datums['floor_z_m']))
        floor = bpy.data.materials.new('neutral diagnostic floor')
        floor.diffuse_color = (.45, .45, .45, 1)
        bpy.context.object.data.materials.append(floor)
        lighting = preview_neutral_light(points)
        light = bpy.data.lights.new('recorded project neutral softbox', 'AREA')
        light.energy, light.size, light.color = lighting['power_watts'], lighting['size_m'], (1, 1, 1)
        lamp = bpy.data.objects.new(light.name, light)
        bpy.context.collection.objects.link(lamp)
        lamp.location = lighting['position_m']
        lamp.rotation_euler = (Vector(lighting['target_m']) - lamp.location).to_track_quat('-Z', 'Y').to_euler()
        camera_data = bpy.data.cameras.new('locked comparison camera')
        camera_data.type = 'ORTHO'
        camera = bpy.data.objects.new(camera_data.name, camera_data)
        bpy.context.collection.objects.link(camera)
        low, high = datums['bounds_m']
        target = Vector([(low[k] + high[k]) / 2 for k in range(3)])
        span = max(high[k] - low[k] for k in range(3))
        camera.location = target + Vector((1.8, -3, 1.7)) * max(1, span)
        camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
        right = camera.rotation_euler.to_matrix() @ Vector((1, 0, 0))
        up = camera.rotation_euler.to_matrix() @ Vector((0, 1, 0))
        projected = [(Vector(p).dot(right), Vector(p).dot(up)) for p in points]
        xmin, xmax = min(p[0] for p in projected), max(p[0] for p in projected)
        ymin, ymax = min(p[1] for p in projected), max(p[1] for p in projected)
        camera.location += right * ((xmin + xmax) / 2 - camera.location.dot(right))
        camera.location += up * ((ymin + ymax) / 2 - camera.location.dot(up))
        camera_data.ortho_scale = max(xmax - xmin, (ymax - ymin) * 4 / 3) / .88
        target = camera.location + camera.rotation_euler.to_matrix() @ Vector((0, 0, -1))
        clipping = preview_clip_range(points, list(camera.location), list(target))
        camera_data.clip_start, camera_data.clip_end = clipping['clip_start_m'], clipping['clip_end_m']
        failures = ortho_specimen_frame_findings(points, list(camera.location), list(target),
                                               camera_data.ortho_scale, 4 / 3)
        if failures:
            raise ValueError('comparison framing refused: ' + '; '.join(failures))
        scene.camera = camera
        def camera_record():
            return dict(location=list(camera.location), rotation=list(camera.rotation_euler),
                        ortho_scale_m=camera_data.ortho_scale, clipping=dict(clipping))
        locked_camera = camera_record()
        images = []
        for name, shown, hidden in [('baseline', native, generated), ('generated', generated, native)]:
            for obj in shown:
                obj.hide_render = False
            for obj in hidden:
                obj.hide_render = True
            path = args.out / (name + '.png')
            scene.render.filepath = str(path.resolve())
            bpy.ops.render.render(write_still=True)
            images.append(dict(image=str(path), sha256=sha256(path), appearance=name))
        # A reverse diagnostic exposes the unseen side instead of judging
        # reconstruction solely from a view resembling the conditioning image.
        centre = Vector([(low[k] + high[k]) / 2 for k in range(3)])
        camera.location = centre + Vector((-1.8, 3, 1.7)) * max(1, span)
        camera.rotation_euler = (centre - camera.location).to_track_quat('-Z', 'Y').to_euler()
        right = camera.rotation_euler.to_matrix() @ Vector((1, 0, 0))
        up = camera.rotation_euler.to_matrix() @ Vector((0, 1, 0))
        projected = [(Vector(p).dot(right), Vector(p).dot(up)) for p in points]
        xmin, xmax = min(p[0] for p in projected), max(p[0] for p in projected)
        ymin, ymax = min(p[1] for p in projected), max(p[1] for p in projected)
        camera.location += right * ((xmin + xmax) / 2 - camera.location.dot(right))
        camera.location += up * ((ymin + ymax) / 2 - camera.location.dot(up))
        camera_data.ortho_scale = max(xmax - xmin, (ymax - ymin) * 4 / 3) / .88
        target = camera.location + camera.rotation_euler.to_matrix() @ Vector((0, 0, -1))
        clipping = preview_clip_range(points, list(camera.location), list(target))
        camera_data.clip_start, camera_data.clip_end = clipping['clip_start_m'], clipping['clip_end_m']
        failures = ortho_specimen_frame_findings(points, list(camera.location), list(target),
                                               camera_data.ortho_scale, 4 / 3)
        if failures:
            raise ValueError('reverse framing refused: ' + '; '.join(failures))
        path = args.out / 'generated-reverse.png'
        scene.render.filepath = str(path.resolve())
        bpy.ops.render.render(write_still=True)
        images.append(dict(image=str(path), sha256=sha256(path), appearance='generated reverse',
                           camera=camera_record()))
        # Record actual texture dimensions and material inputs; no guessed maps.
        textures = []
        for material in {material for obj in generated for material in obj.data.materials if material}:
            for node in material.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    textures.append(dict(material=material.name, image=node.image.name,
                        size=list(node.image.size), channels=node.image.channels,
                        colour_space=node.image.colorspace_settings.name,
                        links=[dict(node=link.to_node.type, socket=link.to_socket.name)
                               for socket in node.outputs for link in socket.links]))
        record = dict(schema='trellis-neutral-evaluation/1', object=args.object,
            label='generated from photos - ASSUMED', admitted=False,
            blender=bpy.app.version_string, model_sha256=sha256(args.model),
            baseline_source_scene_sha256=baselines['source_scene_sha256'],
            baseline_source_ids=baseline['source_mesh_ids'], baseline_dimensions_m=baseline['dimensions_m'],
            generated_source_metrics_z_up=metrics, uniform_fit=fit, textures=textures,
            fitted_native_bounds_m=fitted_bounds, fitted_native_dimensions_m=fitted_dimensions,
            images=images, camera=locked_camera,
            lighting=lighting, world=dict(rgb=[.8, .8, .8], strength=.8),
            exposure=0, view_transform='AgX', material_emission_disabled=True,
            samples=args.samples, resolution=[960, 720], warnings=warnings,
            review_status='pending visual review; numerical execution does not approve appearance')
        (args.out / 'measurements.json').write_text(json.dumps(record, indent=2) + '\n')


if __name__ == '__main__':
    main()
