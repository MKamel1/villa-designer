"""Trial measurement controls, including the actual faceted villa globe."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest

from scripts.trellis_trial import (cuda_root, mesh_measurement, uniform_scale,
                                 require_local_extensions, require_model_dependencies)


class TrialMeasurements(unittest.TestCase):
    def test_real_auxiliary_checkpoint_uses_recorded_revision_instead_of_latest(self):
        from unittest.mock import patch
        from scripts import trellis_trial
        requested = []
        class StopBeforeDownloads(Exception):
            pass
        def capture(url):
            requested.append(url)
            if 'TRELLIS-image-large' in url:
                raise StopBeforeDownloads
            return {}
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(trellis_trial, 'OUT', Path(temporary)), \
                    patch.object(trellis_trial, 'fetch_json', capture):
                with self.assertRaises(StopBeforeDownloads):
                    trellis_trial.download()
        self.assertEqual(requested[-1],
            'https://huggingface.co/api/models/microsoft/TRELLIS-image-large/'
            'revision/25e0d31ffbebe4b5a97464dd851910efc3002d96?blobs=true')
        self.assertIn('/revision/af44b45f2e35a493886929c6d786e563ec68364d?', requested[0])

    def test_actual_birefnet_import_and_sibling_fail_before_gpu_clean_case_passes(self):
        # Frozen unconditional imports from the actual failed BiRefNet loader,
        # model revision e2bf8e4460fc8fa32bba5ea4d94b3233d367b0e4.
        source = ('import torch\nfrom transformers import PreTrainedModel\n'
                  'from kornia.filters import laplacian\nfrom einops import rearrange\n'
                  'from .BiRefNet_config import BiRefNetConfig\n')
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'downloaded-model.py'
            path.write_text(source)
            expected = ['einops', 'kornia', 'torch', 'transformers']
            visited = []
            self.assertEqual(require_model_dependencies([path], visited.append), expected)
            self.assertEqual(visited, expected)
            for absent in ('einops', 'kornia'):
                def unavailable(name):
                    if name == absent:
                        raise ImportError('real missing package class: ' + name)
                with self.subTest(absent=absent), self.assertRaisesRegex(ValueError, absent):
                    require_model_dependencies([path], unavailable)
            path.write_text(source + 'import different_model_dependency\n')
            def added_dependency(name):
                if name == 'different_model_dependency':
                    raise ImportError(name)
            with self.assertRaisesRegex(ValueError, 'different_model_dependency'):
                require_model_dependencies([path], added_dependency)

    def test_actual_transitive_git_source_and_changed_sibling_refuse(self):
        root = Path('/trial-isolation')
        sources = {name: dict(url=(root / relative).as_uri()) for name, relative in
                   [('nvdiffrast', 'nvdiffrast'), ('nvdiffrec-render', 'nvdiffrec'),
                    ('cumesh', 'CuMesh'), ('flex-gemm', 'FlexGEMM'), ('o-voxel', 'repo/o-voxel')]}
        require_local_extensions(sources, root)
        for name, url in [('cumesh', 'https://github.com/JeffreyXiang/CuMesh.git'),
                          ('flex-gemm', 'https://github.com/JeffreyXiang/FlexGEMM.git'),
                          ('o-voxel', 'file:///another-trial/repo/o-voxel')]:
            changed = copy.deepcopy(sources)
            changed[name]['url'] = url
            with self.subTest(name=name), self.assertRaises(ValueError):
                require_local_extensions(changed, root)
        with self.assertRaises(ValueError):
            require_local_extensions({}, root)

    def test_cuda_root_requires_actual_compiler_and_matching_prefix_headers(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'bin').mkdir()
            (root / 'include').mkdir()
            compiler = root / 'bin/nvcc'
            compiler.write_text('#!/bin/sh\necho "Cuda compilation tools, release 12.4, V12.4.131"\n')
            compiler.chmod(0o755)
            with self.assertRaises(ValueError):
                cuda_root(compiler)
            (root / 'include/cuda.h').write_text('// header fixture\n')
            self.assertEqual(cuda_root(compiler), root)
            if os.name == 'posix':
                self.assertEqual(cuda_root(compiler, '12.4'), root)
                with self.assertRaises(ValueError):
                    cuda_root(compiler, '12.0')
            # Real failure class and sibling: populated include-only toolkit
            # prefix, or an executable whose own prefix lacks the headers.
            with self.assertRaises(ValueError):
                cuda_root(root / 'lib/cuda/bin/nvcc')
            (root / 'include/cuda.h').unlink()
            with self.assertRaises(ValueError):
                cuda_root(compiler)

    @classmethod
    def setUpClass(cls):
        fixture = Path(__file__).parent / 'fixtures/trellis-globe-baseline.json'
        faces = json.loads(fixture.read_text())['faces']
        cls.vertices = []
        cls.triangles = []
        for face in faces:
            start = len(cls.vertices)
            cls.vertices.extend(face)
            cls.triangles.extend([[start, start + i, start + i + 1]
                                  for i in range(1, len(face) - 1)])

    def test_actual_globe_closes_geometrically_but_has_split_face_indices(self):
        result = mesh_measurement(self.vertices, self.triangles)
        self.assertFalse(result['indexed_topology']['closed'])
        self.assertTrue(result['geometric_topology']['closed'])
        for extent in result['dimensions']:
            self.assertAlmostEqual(extent, .3)

    def test_actual_missing_face_and_nonmanifold_duplicate_refuse_closure(self):
        opened = mesh_measurement(self.vertices, self.triangles[1:])
        duplicate = mesh_measurement(self.vertices, self.triangles + [self.triangles[0]])
        self.assertFalse(opened['geometric_topology']['closed'])
        self.assertGreater(opened['geometric_topology']['boundary_edges'], 0)
        self.assertFalse(duplicate['geometric_topology']['closed'])
        self.assertGreater(duplicate['geometric_topology']['nonmanifold_edges'], 0)

    def test_translated_and_resized_sibling_stays_closed_without_mutating_source(self):
        original = copy.deepcopy(self.vertices)
        sibling = [[v * 3 + 17 for v in p] for p in self.vertices]
        result = mesh_measurement(sibling, self.triangles)
        self.assertTrue(result['geometric_topology']['closed'])
        for extent in result['dimensions']:
            self.assertAlmostEqual(extent, .9)
        self.assertEqual(original, self.vertices)

    def test_invalid_geometry_refuses(self):
        for vertices, triangles in (([], []), ([[0, 0, float('nan')]], [[0, 0, 0]]),
                                    ([[0, 0, 0]], [[0, 1, 2]])):
            with self.subTest(vertices=vertices), self.assertRaises(ValueError):
                mesh_measurement(vertices, triangles)

    def test_height_fit_is_one_uniform_scale_and_retains_unseen_proportions(self):
        result = uniform_scale([[-.4, -.3, -.5], [.4, .3, .5]], .45, 'height')
        self.assertEqual(result['scale_xyz'], [.45] * 3)
        for actual, expected in zip(result['dimensions_m'], [.36, .27, .45]):
            self.assertAlmostEqual(actual, expected, places=12)

    def test_pendant_uses_horizontal_datum_without_forcing_a_sphere(self):
        result = uniform_scale([[-.5, -.4, 0], [.5, .4, .75]], .3, 'horizontal')
        self.assertEqual(result['scale_xyz'], [.3] * 3)
        for actual, expected in zip(result['dimensions_m'], [.3, .24, .225]):
            self.assertAlmostEqual(actual, expected, places=12)

    def test_precision_control_still_detects_a_real_scale_mutation(self):
        result = uniform_scale([[-.4, -.3, -.5], [.4, .3, .5]], .45, 'height')
        # A 1 mm error is not numerical representation noise.
        for expected in (.451, .449):
            with self.assertRaises(AssertionError):
                self.assertAlmostEqual(result['dimensions_m'][2], expected, places=12)

    def test_invalid_target_or_degenerate_extent_refuses(self):
        for target in (0, -1, float('nan'), float('inf'), True):
            with self.subTest(target=target), self.assertRaises(ValueError):
                uniform_scale([[0, 0, 0], [1, 1, 1]], target, 'height')
        with self.assertRaises(ValueError):
            uniform_scale([[0, 0, 0], [1, 1, 0]], .45, 'height')
        with self.assertRaises(ValueError):
            uniform_scale([[0, 0, 0], [1, 1, 1]], .45, 'unspecified')


if __name__ == '__main__':
    unittest.main()
