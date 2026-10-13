"""Actual C3 door bucket split: source solids cannot depend on camera captions."""
from copy import deepcopy
from pathlib import Path
import gzip,json
import unittest
from archpipe.concept.construction_solids import complete_shell,close_skin
from archpipe.concept.physical_part import geometry_errors
from archpipe.concept.furniture_stage2 import physical_architecture

class DoorComponents(unittest.TestCase):
    def case(self):
        return json.loads(gzip.decompress(Path('tests/fixtures/integration5-door-buckets.json.gz').read_bytes()))

    def test_real_camera_buckets_change_old_backing_but_new_physical_sources_match(self):
        c=self.case()
        def old(scene):return sum(len(close_skin(r['faces'])) if geometry_errors(r['faces']) else len(r['faces']) for r in scene['meshes'])
        self.assertEqual(old(c['empty'])-old(c['full']),180)
        for s in c.values():
            complete_shell(s)
            self.assertEqual(len(s['meshes']),12)
            self.assertEqual(sum(len(r['faces']) for r in s['meshes']),72)
            self.assertTrue(all(not geometry_errors(r['faces']) for r in s['meshes']))
        self.assertEqual(physical_architecture(c['full']['meshes']),physical_architecture(c['empty']['meshes']))

    def test_translated_renamed_sources_and_complete_leaf_hiding(self):
        c=self.case()
        for s in c.values():
            for row in s['meshes']:
                row['id']='other-'+row['id']
                for face in row['faces']:
                    for p in face:p[0]+=40;p[2]+=3
            for v in s['views']:v['hide_meshes']=['other-'+i for i in v['hide_meshes']]
            complete_shell(s)
        self.assertEqual(physical_architecture(c['full']['meshes']),physical_architecture(c['empty']['meshes']))
        ids={r['id'] for r in c['full']['meshes']}
        self.assertTrue(any(any(i in ids for i in v['hide_meshes']) for v in c['full']['views']))
        before=deepcopy(c['full']);complete_shell(c['full'])
        self.assertEqual(before,c['full'])

    def test_actual_source_geometry_change_remains_a_physical_change(self):
        c=self.case();complete_shell(c['full']);baseline=physical_architecture(c['full']['meshes'])
        c['empty']['meshes'][0]['faces'][0][0][0]+=.01
        complete_shell(c['empty'])
        self.assertNotEqual(baseline,physical_architecture(c['empty']['meshes']))
