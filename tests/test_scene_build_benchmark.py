"""Benchmark capture refuses source drift and any scene-byte difference."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('scene_build_benchmark',Path(__file__).parents[1]/'scripts/benchmark_scene_build.py')
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


class SceneBuildBenchmark(unittest.TestCase):
    def test_real_frozen_source_change_refuses_before_writing_a_baseline(self):
        # Actual pre-refactor triangulation is held by value, unlike a mocked
        # source name. Its changed current source produces a different digest.
        original = (Path(__file__).parent/'fixtures/scene-triangles-before.py').read_bytes()
        changed = (Path(__file__).parents[1]/'src/archpipe/concept/render_support.py').read_bytes()
        before,after = [{'source_hash':hashlib.sha256(data).hexdigest()} for data in (original,changed)]
        self.assertNotEqual(before,after)
        with tempfile.TemporaryDirectory() as tmp:
            baseline=Path(tmp)/'scene.json'
            with patch('sys.argv',['benchmark','--baseline',str(baseline),'--record-baseline']), \
                 patch.object(benchmark.villa_render,'source_provenance',side_effect=[before,after]), \
                 patch.object(benchmark.villa_render,'build',return_value={}), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(benchmark.main(),1)
            self.assertFalse(baseline.exists())

    def test_stable_source_accepts_exact_bytes_and_refuses_changed_scene_or_truncation(self):
        source={'source_hash':'stable'}
        scene={'id':'D1','meshes':[],'views':[]}
        raw=json.dumps(scene,sort_keys=True).encode()
        with tempfile.TemporaryDirectory() as tmp:
            baseline=Path(tmp)/'scene.json'
            for data,expected in ((raw,0),(raw+b' ',1),(raw[:-1],1),(raw.replace(b'D1',b'D2'),1)):
                baseline.write_bytes(data)
                with patch('sys.argv',['benchmark','--baseline',str(baseline)]), \
                     patch.object(benchmark.villa_render,'source_provenance',return_value=source), \
                     patch.object(benchmark.villa_render,'build',return_value=scene), \
                     contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(benchmark.main(),expected)
