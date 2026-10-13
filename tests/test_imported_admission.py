"""Frozen integration-5 source identity, real twelve refusals and siblings."""
from copy import deepcopy
from pathlib import Path
import gzip
import json
import unittest

import numpy as np

from archpipe.beds import model_review_meshes, model_transform, scene_with_model_geometry
from archpipe.imported_appearance import (APPEARANCE_CLASS, ENCLOSURE_TOLERANCE_M,
    bind_scene, build_pairs, digest, require_scene)
from archpipe.concept.physical_part import PartError, PartMeshList, geometry_errors


class ImportedAdmission(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        receipt = json.loads(gzip.decompress(Path('knowledge/furniture-stage2.json.gz').read_bytes()))
        bed = json.loads(gzip.decompress(Path('knowledge/parents-bed.json.gz').read_bytes()))
        cls.models = [dict(m, review_geometry=receipt['geometry'][m['asset']]) for m in receipt['models']]+bed['models']
        cls.before = json.loads(Path('tests/fixtures/imported-admission-before.json').read_text())
        cls.scene = bind_scene(dict(models=cls.models, meshes=[]))

    def test_real_twelve_refusals_get_strict_closed_component_standins_without_face_edits(self):
        self.assertEqual(sum(bool(r['physical_errors']) for r in self.before['cases']), 12)
        for model, frozen in zip(self.models, self.before['cases']):
            with self.subTest(model=model['id']):
                self.assertEqual(digest(model['review_geometry']), frozen['geometry_sha256'])
                self.assertEqual(model['review_geometry']['source_sha256'], frozen['source_sha256'])
                rows = model_review_meshes([model])
                if frozen['physical_errors']:
                    self.assertTrue(geometry_errors([f for r in rows for f in r['faces']]))
                with self.assertRaisesRegex(PartError, 'appearance mesh cannot'):
                    PartMeshList().extend(rows)
        physical = require_scene(self.scene)
        self.assertEqual(len(physical), 363)
        self.assertEqual(sum(len(p['components']) for p in physical), 680)
        self.assertFalse(PartMeshList().extend(physical))
        self.assertTrue(all(p['render'] is False and not p.get('proxy_exemption') for p in physical))
        self.assertTrue(all(a['mesh_class'] == APPEARANCE_CLASS and a['physical_part'] is False
                            for a in self.scene['imported_appearances']))

    def test_every_real_component_vertex_is_inside_actual_outward_standin_faces(self):
        parts = {p['id']:p for p in self.scene['physical_model_meshes']}
        for model in self.models:
            rows, matrix, offset = model_transform(model)
            for row in rows:
                part = parts[model['id']+'::'+row['name']]
                seen = []
                for component in part['components']:
                    indices = component['source_face_indices'];seen.extend(indices)
                    vertices = np.asarray([p for i in indices for p in row['faces'][i]])@matrix.T+offset
                    start = component['standin_face_start']
                    for face in part['faces'][start:start+component['standin_face_count']]:
                        a,b,c = np.asarray(face[:3]);normal = np.cross(b-a,c-a);normal /= np.linalg.norm(normal)
                        self.assertLessEqual(float(((vertices-a)@normal).max()), ENCLOSURE_TOLERANCE_M)
                self.assertEqual(sorted(seen), list(range(len(row['faces']))))

    def test_missing_standin_shrunken_stale_or_rendering_pair_fails_closed(self):
        for change in ('missing', 'shrunk', 'render', 'source', 'appearance', 'physical-class',
                       'physical-model', 'source-vertex'):
            with self.subTest(change=change):
                scene = bind_scene(dict(models=[deepcopy(self.models[0])], meshes=[]))
                if change == 'missing':scene['physical_model_meshes'].pop()
                elif change == 'shrunk':
                    part = scene['physical_model_meshes'][0]
                    for face in part['faces']:
                        for p in face:p[2] += .010
                    scene['imported_appearances'][0]['standin_sha256'] = digest(part)
                elif change == 'render':scene['physical_model_meshes'][0]['render'] = True
                elif change == 'source':scene['models'][0]['review_geometry']['source_sha256']['model.gltf'] = '0'*64
                elif change == 'appearance':scene['imported_appearances'].pop()
                elif change == 'physical-model':scene['models'][0]['physical_part'] = True
                elif change == 'source-vertex':scene['models'][0]['review_geometry']['meshes'][0]['faces'][0][0][0] += .01
                else:scene['imported_appearances'][0]['physical_part'] = True
                with self.assertRaises(ValueError):require_scene(scene)
                with self.assertRaises(ValueError):scene_with_model_geometry(scene)

    def test_renamed_translated_sibling_preserves_enclosure_and_refuses_missing_pair(self):
        model = deepcopy(self.models[-1]);model['id'] = 'unrelated-villa-bed';model['label'] = 'unrelated-item'
        model['position'] = [v+t for v,t in zip(model['position'], [30,-40,2])]
        scene = bind_scene(dict(models=[model], meshes=[]))
        require_scene(scene)
        self.assertTrue(all(p['id'].startswith(model['id']+'::') for p in scene['physical_model_meshes']))
        scene['physical_model_meshes'].clear()
        with self.assertRaises(ValueError):require_scene(scene)

    def test_physical_consumers_keep_appearance_out_and_preserve_fallback(self):
        from archpipe.task_probe import task_geometry
        model = self.models[0]
        original = dict(models=[model], meshes=[dict(id='unrelated', faces=[])])
        scene = bind_scene(deepcopy(original))
        actual = task_geometry(scene)
        self.assertTrue(all(p.get('mesh_class') != APPEARANCE_CLASS for p in actual['meshes']))
        self.assertEqual(actual['meshes'][1: ], scene['physical_model_meshes'])
        self.assertEqual(scene_with_model_geometry(actual)['meshes'], actual['meshes'])
        from archpipe.geometry_topology import _freeze
        frozen_expansion=scene_with_model_geometry(_freeze(actual))
        self.assertEqual(digest(frozen_expansion['meshes']),digest(actual['meshes']))
        rendered = deepcopy(scene)
        rendered['meshes'].extend(rendered['physical_model_meshes'])
        with self.assertRaises(ValueError):require_scene(rendered)
        self.assertEqual(len(scene['meshes']), 1)
        fallback = dict(models=[dict(model, status='procedural-bed-fallback')], meshes=original['meshes'])
        self.assertEqual(task_geometry(fallback)['meshes'], original['meshes'])

    def test_orphaned_import_rows_refuse_after_models_and_metadata_are_removed(self):
        from archpipe.imported_appearance import needs_scene_admission
        from archpipe.villa_render_contract import validate_scene
        rows = [self.scene['physical_model_meshes'][0],
                dict(id='orphaned-appearance', mesh_class=APPEARANCE_CLASS, faces=[])]
        for row in rows:
            orphan = dict(models=[], meshes=[deepcopy(row)])
            self.assertTrue(needs_scene_admission(orphan))
            with self.assertRaises(ValueError):require_scene(orphan)
            with self.assertRaises(ValueError):scene_with_model_geometry(orphan)
            self.assertTrue(any('imported admission' in e for e in validate_scene(orphan)))
        self.assertFalse(needs_scene_admission(dict(models=[],meshes=[])))
        self.assertFalse(needs_scene_admission(dict(models=[],meshes=None)))

    def test_real_five_legacy_imports_and_unknown_or_changed_sibling_fail_closed(self):
        models = json.loads(Path('tests/fixtures/imported-legacy-before.json').read_text())['models']
        scene = bind_scene(dict(models=models, meshes=[]))
        physical = require_scene(scene)
        self.assertEqual({p['model_instance'] for p in physical}, {m['id'] for m in models})
        self.assertTrue(all(p['render'] is False and not p.get('proxy_exemption') for p in physical))
        changed = deepcopy(scene);changed['models'][0]['scale'] *= 1.1
        with self.assertRaises(ValueError):require_scene(changed)
        unknown = deepcopy(models[0]);unknown['id'] = 'unrelated-import';unknown['asset'] = 'unmeasured-new-asset'
        with self.assertRaisesRegex(ValueError, 'no measured physical stand-in'):
            bind_scene(dict(models=[unknown], meshes=[]))
        rotated = deepcopy(models[0]);rotated['id'] = 'unrelated-rotated-import';rotated['rotation_deg'][2] = 37
        with self.assertRaisesRegex(ValueError, 'source anchor'):
            bind_scene(dict(models=[rotated],meshes=[]))

    def test_real_open_structural_frame_keeps_reading_sensor_clear_and_translated_sibling(self):
        from archpipe.task_probe import bind_planes, require_clear_probes
        frozen=json.loads(gzip.decompress(Path('tests/fixtures/imported-open-frame-reading.json.gz').read_bytes()))['scene']
        for shift in ([0,0,0],[30,-20,3]):
            scene=deepcopy(frozen)
            model=scene['models'][0];model['id']='unrelated-cane-reading-item'
            model['position']=[v+d for v,d in zip(model['position'],shift)]
            for mesh in scene['meshes']:
                for face in mesh['faces']:
                    for p in face:p[:]=[v+d for v,d in zip(p,shift)]
            for light in scene['lights']:light['position']=[v+d for v,d in zip(light['position'],shift)]
            point=scene['measurement_points'][0]
            point['position']=[v+d for v,d in zip(point['position'],shift)]
            point['host_surface']['authored_plane_m']=[v+d for v,d in zip(point['host_surface']['authored_plane_m'],shift)]
            nominal=deepcopy(point['position'])
            bind_scene(scene);bind_planes(scene);require_clear_probes(scene)
            self.assertEqual(point['position'],nominal)
            self.assertEqual(point['host_surface']['model_instance'],model['id'])
            self.assertGreater(len(scene['physical_model_meshes'][0]['components']),20)

    def test_real_sofa_contained_dressing_support_and_floating_translated_sibling(self):
        from archpipe.concept.render_support import unsupported
        frozen = json.loads(gzip.decompress(Path('tests/fixtures/imported-sofa-support.json.gz').read_bytes()))
        for shift in ([0,0,0], [30,-20,3]):
            scene = deepcopy(frozen)
            model = scene['models'][0];model['id'] = 'unrelated-imported-sofa'
            model['position'] = [v+d for v,d in zip(model['position'], shift)]
            prop = scene['props'][0];prop['id'] = 'unrelated-dressing'
            prop['position'] = [v+d for v,d in zip(prop['position'], shift)]
            for mesh in scene['meshes']:
                for face in mesh['faces']:
                    for point in face:point[:] = [v+d for v,d in zip(point,shift)]
            bind_scene(scene)
            self.assertEqual(unsupported(scene), [])
            lifted = deepcopy(scene);lifted['props'][0]['position'][2] += 2
            self.assertIn(prop['id'], [identifier for identifier,_ in unsupported(lifted)])
            # An embedded base cannot borrow support from a floating body.
            floating = deepcopy(scene);floating['meshes'] = []
            self.assertIn(prop['id'], [identifier for identifier,_ in unsupported(floating)])


if __name__ == '__main__':
    unittest.main()
