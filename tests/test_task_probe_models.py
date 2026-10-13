"""Actual accepted desktop replacement, hidden fallback and translated sibling."""
from copy import deepcopy
import gzip,json
from pathlib import Path
import unittest
import numpy as np
from archpipe.task_probe import bind_planes, task_geometry

class ModelTaskHost(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        receipt=json.loads(gzip.decompress(Path('knowledge/furniture-stage2.json.gz').read_bytes()))
        m=next(m for m in receipt['models'] if m['label']=='ka-desk-1')
        cls.model=dict(m,review_geometry=receipt['geometry'][m['asset']])

    def scene(self):
        m=deepcopy(self.model);x,y,z=m['position'];h=m['furniture_fitting']['height_m']+z
        fallback=dict(id=m['replacement_mesh_ids'][0],group='furniture',room=m['room'],material='oak',
                      faces=[[[x-1,y-1,h],[x+1,y-1,h],[x+1,y+1,h],[x-1,y+1,h]]])
        point=dict(room=m['room'],label='homework',host_item=m['label'],position=[x,y,h],
                   host_surface=dict(mesh_id=fallback['id'],face_index=0,offset_m=0))
        return dict(meshes=[fallback],models=[m],measurement_points=[point])

    def test_real_model_binding_ignores_changed_hidden_fallback_and_follows_source(self):
        scene=self.scene();bind_planes(scene);p=scene['measurement_points'][0]
        self.assertEqual(p['host_surface']['model_instance'],self.model['id'])
        self.assertIn(p['host_surface']['mesh_id'],[r['id'] for r in task_geometry(scene)['meshes']])
        original=p['position'][2]
        for face in scene['meshes'][0]['faces']:
            for v in face:v[2]+=2
        bind_planes(scene);self.assertEqual(p['position'][2],original)
        scene['models'][0]['position'][2]+=.137
        bind_planes(scene);self.assertAlmostEqual(p['position'][2],original+.137)

    def test_missing_source_fallback_rebinds_to_exact_native_host(self):
        scene=self.scene();native=deepcopy(scene['measurement_points'][0]['host_surface'])
        bind_planes(scene);scene['models'][0]['status']='procedural-bed-fallback'
        bind_planes(scene)
        self.assertEqual(scene['measurement_points'][0]['host_surface']['mesh_id'],native['mesh_id'])
        self.assertNotIn('model_instance',scene['measurement_points'][0]['host_surface'])

    def test_renamed_translated_model_and_missing_semantic_datum(self):
        scene=self.scene();m=scene['models'][0];p=scene['measurement_points'][0]
        m['id']='other-desk';m['label']='other-item';p['host_item']='other-item'
        m['position'][0]+=40;p['position'][0]+=40
        bind_planes(scene);self.assertTrue(p['host_surface']['mesh_id'].startswith('other-desk::'))
        m['furniture_fitting']['height_parts']=['nonexistent-source-part']
        with self.assertRaisesRegex(ValueError,'height datum requires measured retained parts'):bind_planes(scene)

class ParentReadingDatum(unittest.TestCase):
    def test_retained_reading_datum_preserves_renamed_translated_sibling(self):
        from archpipe.task_probe import require_clear_probes
        frozen=json.loads(gzip.decompress(Path('tests/fixtures/task-probe-parent-replacement.json.gz').read_bytes()))
        scene=deepcopy(frozen);shift=[30,-20,3]
        model=scene['models'][0];model['id']='unrelated-reading-bed';model['label']='unrelated-reading-item'
        model['position']=[v+d for v,d in zip(model['position'],shift)]
        for mesh in scene['meshes']:
            for face in mesh['faces']:
                for vertex in face:vertex[:]=[v+d for v,d in zip(vertex,shift)]
        for light in scene['lights']:
            light['position']=[v+d for v,d in zip(light['position'],shift)]
        for cloth in scene['cloth']:
            cloth['id']='duvet-'+model['label'];cloth['mattress_top']+=shift[2]
        point=scene['measurement_points'][0];point['host_item']=model['label']
        point['position']=[v+d for v,d in zip(point['position'],shift)]
        before=json.loads(Path('tests/fixtures/imported-reading-datum-before.json').read_text())
        original=[v+d for v,d in zip(before['bound_position_m'],shift)]
        bind_planes(scene);require_clear_probes(scene)
        np.testing.assert_allclose(point['position'],original,atol=1e-8,rtol=0)
        self.assertEqual(point['host_surface']['model_instance'],model['id'])

    def test_real_parent_reading_clearance_and_frozen_wrong_pillow_offset(self):
        from archpipe.task_probe import require_clear_probes, _surface
        scene=json.loads(gzip.decompress(Path('tests/fixtures/task-probe-parent-replacement.json.gz').read_bytes()))
        before=json.loads(Path('tests/fixtures/imported-reading-datum-before.json').read_text())
        p=scene['measurement_points'][0];original=before['bound_position_m'][2]
        bind_planes(scene)
        self.assertAlmostEqual(p['host_surface']['replacement_datum_offset_m'],.375)
        self.assertAlmostEqual(p['position'][2],original,delta=1e-8)
        self.assertIn('owned by measured stand-in', p['host_surface']['reading_datum_basis'])
        require_clear_probes(scene)
        wrong=deepcopy(scene);p=wrong['measurement_points'][0];binding=p['host_surface']
        face=next(r for r in task_geometry(wrong)['meshes'] if r['id']==binding['mesh_id'])['faces'][binding['face_index']]
        binding['offset_m']=binding['native_offset_m']
        p['position'][2]=_surface(face,*p['position'][:2])+binding['offset_m']
        with self.assertRaisesRegex(ValueError,'upward view hits .*source-pillow'):require_clear_probes(wrong)
