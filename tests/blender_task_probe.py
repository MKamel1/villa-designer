"""Run the frozen ownership cases through Blender's evaluated ray provider.

Run with the pinned Blender binary in background mode and --python-exit-code
1. This integration check needs no product library, graphics device or render.
"""
import copy
import gzip
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
import bpy
from archpipe.blender.villa_scene import evaluated_probe_ray
from archpipe.task_probe import require_clear_paths, probe_sources


def install(meshes):
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for spec in meshes:
        vertices, faces = [], []
        for face in spec['faces']:
            faces.append(list(range(len(vertices), len(vertices)+len(face))))
            vertices.extend(face)
        mesh = bpy.data.meshes.new(spec['id'])
        mesh.from_pydata(vertices, [], faces)
        obj = bpy.data.objects.new(spec['id'], mesh)
        bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.update()


class EvaluatedTaskProbes(unittest.TestCase):
    def test_frozen_evaluated_vase_and_clear_control(self):
        frozen = json.loads(gzip.decompress((ROOT/'tests/fixtures/task-probe-evaluated-obstructions.json.gz').read_bytes()))
        for row in frozen['records']:
            for obstructed in (True, False):
                meshes = [row['host']] + ([row['solid']] if obstructed else [])
                install(meshes)
                # The same frozen solid remains an obstruction when declared
                # and assigned a glass material; no material exemption is safe.
                material = bpy.data.materials.get('opaque') or bpy.data.materials.new('opaque')
                if obstructed:
                    bpy.data.objects[row['solid']['id']].data.materials.append(material)
                scene = dict(meshes=meshes, materials={'opaque': {'kind': 'glass'}}, lights=[])
                ray = evaluated_probe_ray(scene)
                if obstructed:
                    with self.assertRaisesRegex(ValueError, 'upward view hits '+row['solid']['id']):
                        require_clear_paths([row['point']], [], ray)
                else:
                    require_clear_paths([row['point']], [], ray)

    def test_frozen_17_hidden_and_17_clean_probes(self):
        frozen = json.loads(gzip.decompress((ROOT/'tests/fixtures/task-probe-hidden-sensors.json.gz').read_bytes()))
        self.assertEqual(len(frozen['records']), 17)
        for row in frozen['records']:
            install([row['host']])
            scene = dict(meshes=[row['host']], materials=frozen['materials'], lights=frozen['lights'])
            point = copy.deepcopy(row['point'])
            ray = evaluated_probe_ray(scene)
            with self.subTest(point=point):
                with self.assertRaisesRegex(ValueError, 'before sensor plane'):
                    require_clear_paths([point], probe_sources(scene), ray)
                point['position'] = row['corrected_position']
                require_clear_paths([point], probe_sources(scene), ray)


if __name__ == '__main__':
    result = unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(EvaluatedTaskProbes))
    if not result.wasSuccessful():
        raise RuntimeError('Blender evaluated task-probe regression failed')
