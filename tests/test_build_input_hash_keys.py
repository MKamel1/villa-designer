"""Source-digest keys are metadata; literal glTF reads still refuse."""
from pathlib import Path
import unittest

from archpipe.build_input_guard import source_findings, build_input_findings


class HashMetadata(unittest.TestCase):
    def test_real_source_hash_lookup_and_renamed_sibling_are_quiet(self):
        frozen="if geometry['source_sha256']['model.gltf'] != entry['source_sha256']:\n    raise ValueError('stale source')\n"
        self.assertEqual(source_findings(frozen,'imported_appearance.py'),[])
        self.assertEqual(source_findings(frozen.replace('model.gltf','renamed-source.gltf'),'unrelated.py'),[])
        self.assertEqual(build_input_findings(),[])

    def test_actual_raw_path_read_or_nonhash_lookup_still_fires(self):
        for source in ("source = Path('props/source/model.gltf').read_bytes()",
                       "source = metadata['files']['model.gltf']",
                       "source = Path.home() / 'model.gltf'",
                       "from archpipe.asset_route_generator import asset_triangles"):
            self.assertTrue(source_findings(source,'unrelated.py'),source)
