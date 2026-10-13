"""Frozen production sensors, clean placement and identity-independent siblings."""
import copy
import ast
import gzip
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from archpipe.task_probe import (author_bindings, bind_planes, require_clear_probes,
                                 require_clear_paths, probe_sources, _hit,
                                 resolve_surface_probes, probe_position, _inside_face)

FIXTURE = Path(__file__).parent/'fixtures/task-probe-hidden-sensors.json.gz'


class SurfaceProbeSearch(unittest.TestCase):
    """Actual evaluated table/vase, unchanged clear point and translated sibling."""
    def case(self, clean=False, shift=(0, 0, 0)):
        from archpipe.concept.render_support import _triangles
        row = json.loads(gzip.decompress((FIXTURE.parent/'task-probe-table-vase.json.gz').read_bytes()))
        point = row['clean_point'] if clean else row['point']
        scene = dict(measurement_points=[point], meshes=[row['host'], row['solid']],
                     lights=row['lights'], materials={})
        if any(shift):
            point['room'], point['label'], point['host_item'] = 'other-room', 'other-task', 'other-table'
            row['host']['id'], row['solid']['id'] = 'furn-other-table-0', 'other-decoration'
        point['position'] = [a+b for a,b in zip(point['position'], shift)]
        for mesh in scene['meshes']:
            for face in mesh['faces']:
                for vertex in face:
                    vertex[:] = [a+b for a,b in zip(vertex, shift)]
        for light in scene['lights']:
            light['position'] = [a+b for a,b in zip(light['position'], shift)]
        bounds = [[a+b for a,b in zip(vertex, shift)] for vertex in row['bounds_m']]
        author_bindings(scene)
        triangles, owners = _triangles(scene['meshes'])
        return scene, lambda start,end: _hit(triangles, owners, scene['meshes'], start,end), lambda name: bounds

    def test_actual_vase_search_records_nearest_same_surface_without_design_changes(self):
        scene, ray, bounds = self.case()
        before = copy.deepcopy(scene)
        with self.assertRaisesRegex(ValueError, 'upward view hits prop-dining-vase'):
            require_clear_probes(scene)
        points = resolve_surface_probes(scene, ray, bounds)
        self.assertEqual(scene, before)
        point = points[0]
        self.assertEqual(point['position'], before['measurement_points'][0]['position'])
        self.assertEqual(point['required_lux'], 100)
        record = point['host_surface']['surface_search']
        self.assertEqual(record['offset_m'], [-.03, .095, 0.])
        first_candidate = next(a for a in record['attempts'] if a['offset_m']==[-.025,.095,0.])
        self.assertEqual(first_candidate['obstruction']['path'], 'source marker-PATH-corridor-09')
        self.assertEqual(record['task_area']['citation']['card'], point['card'])
        self.assertGreater(record['distance_m'], 0)
        self.assertIsNone(record['attempts'][-1]['obstruction'])
        self.assertTrue(all(a['obstruction'] for a in record['attempts'][:-1]))
        distances = [sum(round(v/record['step_m'])**2 for v in a['offset_m'][:2])
                     for a in record['attempts']]
        self.assertEqual(distances, sorted(distances))
        require_clear_probes(dict(scene, measurement_points=points))
        require_clear_paths(points, probe_sources(scene), ray)
        self.assertEqual(resolve_surface_probes(dict(scene, measurement_points=points), ray, bounds), points)

    def test_clean_actual_homework_point_is_unchanged(self):
        scene, ray, bounds = self.case(clean=True)
        self.assertEqual(resolve_surface_probes(scene, ray, bounds), scene['measurement_points'])

    def test_translated_table_vase_sibling_has_same_recorded_offset(self):
        scene, ray, bounds = self.case()
        original = resolve_surface_probes(scene, ray, bounds)[0]
        shift = (7, -3, 2)
        scene, ray, bounds = self.case(shift=shift)
        sibling = resolve_surface_probes(scene, ray, bounds)[0]
        self.assertEqual(sibling['host_surface']['surface_search']['offset_m'],
                         original['host_surface']['surface_search']['offset_m'])
        for a,b,d in zip(probe_position(original), probe_position(sibling), shift):
            self.assertAlmostEqual(a+d,b)
        require_clear_probes(dict(scene, measurement_points=[sibling]))

    def test_covered_entire_task_area_fails_and_never_searches_other_furniture(self):
        scene, ray, bounds = self.case()
        point = scene['measurement_points'][0]
        x,y,z = point['position']
        # Real blocked point, injected smaller host task area: every candidate
        # remains covered by the same actual vase. Adjacent hosts cannot help.
        face = [[x-.01,y-.01,z], [x+.01,y-.01,z], [x+.01,y+.01,z], [x-.01,y+.01,z]]
        scene['meshes'][0]['faces'][point['host_surface']['face_index']] = face
        scene['meshes'].append(dict(id='other-table', faces=[[[x+.2,y-.1,z], [x+.4,y-.1,z],
                                                              [x+.4,y+.1,z], [x+.2,y+.1,z]]]))
        with self.assertRaisesRegex(ValueError, 'no unobstructed point within cited task area'):
            resolve_surface_probes(scene, ray, bounds)

    def test_overhead_obstruction_missing_citation_and_outside_face_refuse(self):
        scene, ray, bounds = self.case()
        floating = bounds('unused')
        floating[0][2] += .01
        with self.assertRaisesRegex(ValueError, 'not resting on task host'):
            resolve_surface_probes(scene, ray, lambda name: floating)
        del scene['measurement_points'][0]['host_surface']['task_area']
        with self.assertRaisesRegex(ValueError, 'no cited contact task area'):
            resolve_surface_probes(scene, ray, bounds)
        # A polygon's bounding box must never substitute for its actual area.
        self.assertFalse(_inside_face([[0,0,0], [1,0,0], [0,1,0]], .8,.8))

    def test_unrecorded_or_changed_offset_cannot_bypass_binding_guard(self):
        scene, ray, bounds = self.case(clean=True)
        point = scene['measurement_points'][0]
        point['measurement_position'] = [a+d for a,d in zip(point['position'], [.02,0,0])]
        with self.assertRaisesRegex(ValueError, 'invalid surface search record'):
            require_clear_probes(scene)

    def test_mutated_citation_does_not_poison_other_bindings(self):
        scene, ray, bounds = self.case()
        scene['measurement_points'][0]['host_surface']['task_area']['citation']['locator'] = 'invented'
        with self.assertRaisesRegex(ValueError, 'no cited contact task area'):
            resolve_surface_probes(scene, ray, bounds)
        fresh, ray, bounds = self.case()
        points = resolve_surface_probes(fresh, ray, bounds)
        self.assertIn('printed page 33.8', points[0]['host_surface']['surface_search']['task_area']['citation']['locator'])


class TaskProbeOwnership(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frozen = json.loads(gzip.decompress(FIXTURE.read_bytes()))

    def scene(self, row, clean=False):
        point = copy.deepcopy(row['point'])
        if clean:
            point['position'] = list(row['corrected_position'])
        return dict(measurement_points=[point], meshes=[copy.deepcopy(row['host'])],
                    lights=copy.deepcopy(self.frozen['lights']), materials=self.frozen['materials'])

    def test_all_17_real_hidden_sensors_fire_and_corrected_planes_stay_quiet(self):
        self.assertEqual(len(self.frozen['records']), 17)
        for row in self.frozen['records']:
            with self.subTest(point=row['point']):
                with self.assertRaisesRegex(ValueError, row['host']['id']+'.*before sensor plane'):
                    require_clear_probes(self.scene(row))
                require_clear_probes(self.scene(row, clean=True))

    def test_renamed_translated_siblings_fire_and_stay_quiet(self):
        for clean in (False, True):
            scene = self.scene(self.frozen['records'][6], clean=clean)
            point = scene['measurement_points'][0]
            point['room'], point['label'] = 'other-villa', 'new-worktop'
            point['host_surface']['mesh_id'] = scene['meshes'][0]['id'] = 'renamed-host'
            shift = [7, -3, 2]
            point['position'] = [v+d for v, d in zip(point['position'], shift)]
            for face in scene['meshes'][0]['faces']:
                for vertex in face:
                    vertex[:] = [v+d for v, d in zip(vertex, shift)]
            for light in scene['lights']:
                light['position'] = [v+d for v, d in zip(light['position'], shift)]
            if clean:
                require_clear_probes(scene)
            else:
                with self.assertRaisesRegex(ValueError, 'new-worktop.*renamed-host'):
                    require_clear_probes(scene)

    def test_surface_construction_follows_measured_top_and_refuses_missing_ownership(self):
        scene = self.scene(self.frozen['records'][6], clean=True)
        point = scene['measurement_points'][0]
        point['host_item'] = 'replacement'
        scene['meshes'][0]['id'] = 'furn-replacement-0'
        point['card'] = 'ies-res-kitchen-cooktop-300'
        # Initial authored host datum, then an arbitrary mounting translation.
        author_bindings(scene)
        for face in scene['meshes'][0]['faces']:
            for vertex in face:
                vertex[2] += .137
        before = point['position'][2]
        bind_planes(scene)
        self.assertAlmostEqual(point['position'][2], before+.137)
        require_clear_probes(scene)
        del point['host_surface']
        with self.assertRaisesRegex(ValueError, 'missing task host'):
            require_clear_probes(scene)

    def test_foreign_solid_and_noncentral_pixel_mutations_fire(self):
        scene = self.scene(self.frozen['records'][6], clean=True)
        x, y, z = scene['measurement_points'][0]['position']
        # Off-centre solid cap: misses the centre ray but covers metered pixels.
        scene['meshes'].append(dict(id='other-solid', material='screen-black', faces=[[
            [x+.002,y-.004,z+.010], [x+.004,y-.004,z+.010],
            [x+.004,y+.004,z+.010], [x+.002,y+.004,z+.010]]]))
        with self.assertRaisesRegex(ValueError, 'upward view hits other-solid'):
            require_clear_probes(scene)

    def test_glass_solid_never_exempts_an_obstructed_probe(self):
        frozen = json.loads(gzip.decompress((FIXTURE.parent/'task-probe-evaluated-obstructions.json.gz').read_bytes()))
        row = frozen['records'][0]
        scene = dict(measurement_points=[row['point']], meshes=[row['host'], row['solid']],
                     lights=[], materials={'opaque': {'kind': 'glass'}})
        with self.assertRaisesRegex(ValueError, 'upward view hits '+row['solid']['id']):
            require_clear_probes(scene)

    def test_source_approach_fires_without_rejecting_remote_shadows(self):
        scene = self.scene(self.frozen['records'][6], clean=True)
        x, y, z = scene['measurement_points'][0]['position']
        scene['lights'] = [dict(id='grazing-source', position=[x+.4,y,z+.04])]
        scene['meshes'].append(dict(id='local-side-solid', material='screen-black', faces=[[
            [x+.010,y-.005,z], [x+.010,y+.005,z],
            [x+.010,y+.005,z+.005], [x+.010,y-.005,z+.005]]]))
        with self.assertRaisesRegex(ValueError, 'source grazing-source hits local-side-solid'):
            require_clear_probes(scene)
        for face in scene['meshes'][-1]['faces']:
            for vertex in face:
                vertex[0] += .1
        require_clear_probes(scene)

    def test_stale_or_removed_host_is_refused(self):
        scene = self.scene(self.frozen['records'][6], clean=True)
        scene['measurement_points'][0]['position'][2] += .02
        with self.assertRaisesRegex(ValueError, 'stale plane'):
            require_clear_probes(scene)
        scene['meshes'] = []
        with self.assertRaisesRegex(ValueError, 'missing host'):
            require_clear_probes(scene)

    def test_evaluated_ray_provider_checks_the_same_frozen_cases(self):
        from archpipe.concept.render_support import _triangles
        for row in self.frozen['records']:
            for clean in (False, True):
                scene = self.scene(row, clean=clean)
                triangles, owners = _triangles(scene['meshes'])
                def first_hit(start, end):
                    return _hit(triangles, owners, scene['meshes'], start, end)
                if clean:
                    require_clear_paths(scene['measurement_points'], probe_sources(scene), first_hit)
                else:
                    with self.assertRaisesRegex(ValueError, 'before sensor plane'):
                        require_clear_paths(scene['measurement_points'], probe_sources(scene), first_hit)

    def test_invalid_binding_values_refuse_before_measurement(self):
        for mutation in ('face', 'offset', 'plane'):
            scene = self.scene(self.frozen['records'][6], clean=True)
            point = scene['measurement_points'][0]
            if mutation == 'face':
                point['host_surface']['face_index'] = -1
            elif mutation == 'offset':
                point['host_surface']['offset_m'] = float('nan')
            else:
                point['position'][2] = float('nan')
            with self.assertRaisesRegex(ValueError, 'invalid task host binding'):
                require_clear_probes(scene)

    def test_all_17_host_bindings_construct_corrected_placement_after_mounting(self):
        for row in self.frozen['records']:
            scene = self.scene(row)
            point = scene['measurement_points'][0]
            point['host_item'] = row['host']['id'][5:].rsplit('-', 1)[0]
            # Frozen actual geometry before its recorded 2 mm finished-floor
            # mounting translation. No current producer values are imported.
            for face in scene['meshes'][0]['faces']:
                for vertex in face:
                    vertex[2] -= .002
            author_bindings(scene)
            self.assertEqual(point['host_surface']['offset_m'], 0)
            for face in scene['meshes'][0]['faces']:
                for vertex in face:
                    vertex[2] += .002
            bind_planes(scene)
            for achieved, expected in zip(point['position'], row['corrected_position']):
                self.assertAlmostEqual(achieved, expected)
            require_clear_probes(scene)

    def test_measurement_refuses_real_hidden_probe_before_accessing_blender(self):
        root = Path(__file__).resolve().parents[1]
        path = root/'src/archpipe/blender/villa_scene.py'
        tree = ast.parse(path.read_text())
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                        and node.name == 'measure_lighting')
        namespace = {}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), namespace)
        # No Blender objects or sensor can exist yet. The real failing input
        # must raise the named obstruction before asking for evaluated geometry.
        with self.assertRaisesRegex(ValueError, 'before sensor plane'):
            namespace['measure_lighting'](self.scene(self.frozen['records'][6]), None,
                                          None, None, None, None, None)

    def test_real_evaluated_vase_obstruction_and_renamed_sibling(self):
        frozen = json.loads(gzip.decompress((FIXTURE.parent/'task-probe-evaluated-obstructions.json.gz').read_bytes()))
        self.assertEqual(len(frozen['records']), 1)
        for renamed in (False, True):
            row = copy.deepcopy(frozen['records'][0])
            if renamed:
                row['solid']['id'] = 'other-villa-table-decoration'
                row['point']['room'], row['point']['label'] = 'other-room', 'other-task'
            scene = dict(measurement_points=[row['point']], meshes=[row['host'], row['solid']],
                         lights=[], materials={})
            with self.assertRaisesRegex(ValueError, 'upward view hits '+row['solid']['id']):
                require_clear_probes(scene)
            # Clean control changes only the test's obstruction population.
            # Production keeps the vase and leaves this point unavailable.
            scene['meshes'].pop()
            require_clear_probes(scene)

    def test_export_contract_refuses_hidden_and_missing_ownership_but_accepts_clean(self):
        from tests.test_villa_render_scene import VillaRenderContractTest
        from archpipe.villa_render_contract import validate_scene
        # Reuse the independent, minimal valid export fixture rather than
        # rebuilding a villa for each intentionally invalid probe.
        if not hasattr(VillaRenderContractTest, 'valid'):
            VillaRenderContractTest.setUpClass()
        scene = copy.deepcopy(VillaRenderContractTest.valid)
        row = self.frozen['records'][6]
        scene['meshes'].append(copy.deepcopy(row['host']))
        scene['materials'].update(self.frozen['materials'])
        scene['measurement_points'] = [copy.deepcopy(row['point'])]
        # This fixture's furniture mounting metadata belongs to the retained
        # villa, not this minimal export's independent mounting registry.
        scene['meshes'][-1].pop('mounting', None)
        with patch('archpipe.task_probe.require_clear_probes', wraps=require_clear_probes) as guard:
            self.assertTrue(any('before sensor plane' in error for error in validate_scene(scene)))
            self.assertEqual(guard.call_count, 1)
        scene['measurement_points'][0]['position'] = row['corrected_position']
        self.assertEqual(validate_scene(scene), [])
        del scene['measurement_points'][0]['host_surface']
        self.assertTrue(any('missing task host' in error for error in validate_scene(scene)))
