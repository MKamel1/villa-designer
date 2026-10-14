"""Actual shared importer read-back: frozen small solids, siblings and inversion.

No presentation images are rendered. Run with pinned Blender in background
mode and --python-exit-code 1. Volume is in cubic metres.
"""
import gzip
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
import bpy
from archpipe.blender.villa_scene import add_mesh_batch
from archpipe.scene_reproducibility import signed_volume


class ImporterPrecision(unittest.TestCase):
    def test_real_parts_and_translated_renamed_siblings(self):
        parts = json.loads(gzip.decompress((ROOT/'tests/fixtures/garment-importer-precision-before.json.gz').read_bytes()))['parts']
        material = bpy.data.materials.new('precision-clean')
        for part in parts:
            for shift in ((0,0,0), (1000,-2000,3000)):
                faces = [[[p[i]+shift[i] for i in range(3)] for p in f] for f in part['faces']]
                spec = dict(id='renamed-'+part['id'], material='clean', faces=faces)
                warnings = []
                obj = add_mesh_batch([spec], spec['id'], material, warnings)
                self.assertEqual(warnings, [])
                actual = [[list(obj.data.vertices[i].co) for i in f.vertices] for f in obj.data.polygons]
                self.assertGreater(signed_volume(actual), 0)
                self.assertEqual(len(actual),len(faces))
                # Genuine inversion is refused by the actual importer.
                spec['faces'] = [list(reversed(f)) for f in faces]
                with self.assertRaisesRegex(ValueError,'inward'):
                    add_mesh_batch([spec], 'inverted', material, [])
                bpy.data.objects.remove(obj, do_unlink=True)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ImporterPrecision)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful(): raise RuntimeError('Importer precision regression failed')
