"""Integration-7 dark views frozen by value, plus renamed and clean controls."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from PIL import Image

from archpipe.render_evidence import caption_evidence, require_subject_bindings
from archpipe.villa_render_contract import subject_meshes
from archpipe.concept.garden_render_review import subject_frame_findings
from archpipe.render_qa import check
from tests.test_villa_exposure_assets import load_function

FIXTURE = Path(__file__).parent / 'fixtures/darkviews-real.json.gz'


def frozen():
    return json.loads(gzip.decompress(FIXTURE.read_bytes()))


class DarkViews(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = frozen()

    def test_real_assembly_binding_refuses_plinth_only_and_accepts_complete(self):
        d = deepcopy(self.data); scene = d['scene']
        report = d['now']['reports']['v29-under-stair-store']
        # Capture order is frozen: the complete retained storage geometry
        # precedes the four plant meshes. This expectation is independent
        # of today's selector, so a shared partial selector cannot pass.
        expected_storage = {m['id'] for m in scene['meshes'][:d['provenance']['storage_mesh_count']]}
        with self.assertRaisesRegex(ValueError, 'omits assembly'):
            require_subject_bindings(scene, report)
        for row in report['subjects']:
            matched = subject_meshes(row['id'], scene['meshes'])
            self.assertGreater(len(matched), 1)
            row['matched_objects'] = [m['id'] for m in matched]
        self.assertEqual({ident for row in report['subjects'] for ident in row['matched_objects']}, expected_storage)
        require_subject_bindings(scene, report)
        # The same real assembly at a different villa, with unrelated names.
        for m in scene['meshes']:
            m['id'] = 'other-' + m['id']
            if m.get('label') in ('stair-flight-store', 'stair-landing-store'):
                m['label'] = 'other-' + m['label']
            if m.get('mounting', {}).get('assembly_root'):
                m['mounting']['assembly_root'] = 'other-' + m['mounting']['assembly_root']
        for row in report['subjects']:
            row['id'] = 'other-' + row['id']
            row['matched_objects'] = ['other-' + x for x in row['matched_objects']]
        view = next(v for v in scene['views'] if v['id'] == report['view'])
        view['subjects'] = ['other-' + s for s in view['subjects']]
        self.assertEqual({m['id'] for row in report['subjects'] for m in subject_meshes(row['id'], scene['meshes'])},
                         {'other-' + ident for ident in expected_storage})
        require_subject_bindings(scene, report)
        report['subjects'][0]['matched_objects'] = report['subjects'][0]['matched_objects'][:1]
        with self.assertRaisesRegex(ValueError, 'omits assembly'):
            require_subject_bindings(scene, report)
        self.assertEqual(subject_meshes('missing-clean-subject', scene['meshes']), [])

    def test_real_plant_vertices_fit_without_camera_motion_and_renamed_sibling(self):
        scene = deepcopy(self.data['scene'])
        v = next(v for v in scene['views'] if v['id'] == 'v36-north-garden')
        original = deepcopy(v['camera']);v['require_full_subject_frame'] = True
        self.assertEqual(subject_frame_findings(v, scene), [])
        self.assertEqual(v['camera'], original)
        # Conservative bounding boxes were the false-positive crop claim.
        rows = self.data['now']['reports'][v['id']]['subjects']
        self.assertEqual(sum(not r['full_frame'] for r in rows), 2)
        v['id'] = 'another-court';v['subjects'] = ['other-' + x for x in v['subjects']]
        for m in scene['meshes']:m['id'] = 'other-' + m['id']
        for m in scene['meshes']:
            for face in m['faces']:
                for point in face:point[0] += 40
        for field in ('position', 'target'):v['camera'][field][0] += 40
        self.assertEqual(subject_frame_findings(v, scene), [])
        v['camera']['shift_y'] += 1
        self.assertTrue(subject_frame_findings(v, scene))

    def test_real_missing_subject_row_and_renamed_sibling_refuse(self):
        data = deepcopy(self.data)
        scene = data['scene']
        report = data['now']['reports']['v29-under-stair-store']
        view = next(v for v in scene['views'] if v['id'] == report['view'])
        for row in report['subjects']:
            row['matched_objects'] = [m['id'] for m in subject_meshes(row['id'], scene['meshes'])]
        require_subject_bindings(scene, report)
        complete = deepcopy(report['subjects'])
        for incomplete in ([], complete[:1], complete + complete[:1], complete + [{'id': 'unexpected'}]):
            report['subjects'] = incomplete
            with self.assertRaisesRegex(ValueError, 'declared subjects'):
                require_subject_bindings(scene, report)
        view['id'] = report['view'] = 'other-storage-view'
        view['subjects'] = ['other-' + s for s in view['subjects']]
        for mesh in scene['meshes']:
            mesh['id'] = 'other-' + mesh['id']
            if mesh.get('label') in ('stair-flight-store', 'stair-landing-store'):
                mesh['label'] = 'other-' + mesh['label']
            if mesh.get('mounting', {}).get('assembly_root'):
                mesh['mounting']['assembly_root'] = 'other-' + mesh['mounting']['assembly_root']
        for row in complete:
            row['id'] = 'other-' + row['id']
            row['matched_objects'] = ['other-' + ident for ident in row['matched_objects']]
        report['subjects'] = complete
        require_subject_bindings(scene, report)
        report['subjects'] = complete[:1]
        with self.assertRaisesRegex(ValueError, 'declared subjects'):
            require_subject_bindings(scene, report)

    def test_qa_obeys_explicit_whole_subject_intent(self):
        # Frozen actual partial report: without intent this is a partial view;
        # with whole-subject intent it must not silently pass as complete.
        rows = deepcopy(self.data['now']['reports']['v36-north-garden']['subjects'])
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'probe.png';Image.new('RGB', (4, 4), (128, 128, 128)).save(p)
            qa = check(p, {'subjects': rows, 'require_full_subject_frame': True})
            checks = {r['check']: r['status'] for r in qa['checks']}
            self.assertEqual(checks['view_subject:landscape-north-back-00'], 'FAIL')
            self.assertEqual(checks['view_subject:landscape-north-mid-00'], 'PASS')
            self.assertEqual(checks['view_subject:landscape-north-front-00'], 'FAIL')
            qa = check(p, {'subjects': rows})
            self.assertTrue(all(r['status'] == 'PASS' for r in qa['checks'] if r['check'].startswith('view_subject:')))

    def test_actual_cohort_meters_are_selection_independent(self):
        d = self.data;views = d['scene']['views']
        meter_views = load_function('exposure_meter_views');locks = load_function('exposure_locks')
        locks.__globals__['exposure_meter_views'] = meter_views
        # Frozen final view meters for the two diagnosed views; other cohort
        # readings are irrelevant here: prove membership, not an invented lock.
        meter = lambda v: (0., 1.)
        for vid in ('v29-under-stair-store', 'v36-north-garden'):
            alone = locks(views, {vid}, meter);all_views = locks(views, {v['id'] for v in views}, meter)
            state = d['now']['reports'][vid]['exposure_state']
            self.assertEqual(alone[2][state], d['now']['reports'][vid]['exposure_metered_over'])
            self.assertEqual(alone[0][state], all_views[0][state])

    def test_real_failure_caption_discloses_actual_lock_and_keeps_failure(self):
        d = deepcopy(self.data);scene = d['scene']
        for vid in ('v29-under-stair-store', 'v36-north-garden'):
            view = next(v for v in scene['views'] if v['id'] == vid)
            report = d['now']['reports'][vid]
            for row in report['subjects']:
                row['matched_objects'] = [m['id'] for m in subject_meshes(row['id'], scene['meshes'])]
            qa = d['now']['qa'][vid]
            result = caption_evidence(scene, view, report, qa)
            self.assertTrue(result['whole_set_lock_verified'])
            self.assertFalse(result['qa_passed'])
            self.assertEqual(result['exposure_stops'], report['exposure_stops'])
            self.assertTrue(any(r['check'] == 'crushed_shadows' and r['status'] == 'FAIL' for r in result['nonpassing_checks']))
            clean = deepcopy(qa)
            for row in clean['checks']:row['status'] = 'PASS'
            self.assertTrue(caption_evidence(scene, view, report, clean)['qa_passed'])
            qa['passed'] = True  # Forged summary cannot waive recorded failures.
            self.assertFalse(caption_evidence(scene, view, report, qa)['qa_passed'])
            report['exposure_metered_over'] = [vid]
            with self.assertRaisesRegex(ValueError, 'complete authored cohort'):
                caption_evidence(scene, view, report, qa)
            # A renamed view/cohort with the same defect also refuses.
            report['view'] = view['id'] = 'other-' + vid
            with self.assertRaisesRegex(ValueError, 'complete authored cohort'):
                caption_evidence(scene, view, report, qa)

    def test_historical_brightness_does_not_establish_equal_exposure(self):
        d = self.data;vid = 'v29-under-stair-store'
        now = d['now']['reports'][vid];old = d['j2']['reports'][vid]
        self.assertAlmostEqual(now['exposure_stops'] - old['exposure_stops'], -4.11563777923584)
        self.assertAlmostEqual(old['exposure_stops'], old['view_meter']['exposure_stops'], places=6)
        self.assertNotIn('exposure_metered_over', old)
        scene = d['scene'];view = next(v for v in scene['views'] if v['id'] == vid)
        result = caption_evidence(scene, view, old, {'checks': []})
        self.assertFalse(result['whole_set_lock_verified'])
        self.assertIn('unverified', result['exposure_evidence'])
        vid = 'v36-north-garden';now = d['now']['reports'][vid];old = d['j9']['reports'][vid]
        self.assertAlmostEqual(now['exposure_stops'] - old['exposure_stops'], -.612823486328125)
        self.assertGreater(now['log_average_linear'], old['log_average_linear'])

    def test_live_intent_preserves_camera_lights_and_exposure(self):
        from archpipe.concept.villa_render import VIEWS
        live = {v['id']: v for v in VIEWS(resolve=False)}
        for vid in ('v29-under-stair-store', 'v36-north-garden'):
            old = next(v for v in self.data['scene']['views'] if v['id'] == vid)
            for key in ('subjects', 'state', 'layers_on', 'exposure'):
                self.assertEqual(live[vid][key], old[key])
            for key in ('position', 'target', 'lens_mm', 'shift_y'):
                self.assertEqual(live[vid]['camera'][key], old['camera'][key])
            self.assertIn('render_evidence', ' '.join(live[vid]['caption_notes']))
        self.assertTrue(live['v36-north-garden']['require_full_subject_frame'])

    def test_local_and_worker_photometry_roots_clean_missing_and_renamed(self):
        from scripts.garden_view_probes import resolve_probe_photometry
        # Exact real failed relative input, frozen in the archive record.
        data = {'lights': [{'ies': 'iguzzini/LSEVO-AAK3EW.ies'}]}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder);generated = root/'generated';local = root/'bundle/ies';worker = root/'job/ies'
            generated.mkdir();local.mkdir(parents=True);worker.mkdir(parents=True)
            with self.assertRaises(FileNotFoundError):
                resolve_probe_photometry(data, generated, worker)
            target = local / data['lights'][0]['ies'];target.parent.mkdir();target.write_text('frozen-path-resolution-only')
            self.assertEqual(resolve_probe_photometry(data, generated, local, worker)[data['lights'][0]['ies']], target.resolve())
            renamed = {'lights': [{'ies': 'other-maker/another.ies'}]}
            with self.assertRaises(FileNotFoundError):resolve_probe_photometry(renamed, generated, local, worker)
            moved = worker / renamed['lights'][0]['ies'];moved.parent.mkdir();moved.write_bytes(target.read_bytes())
            self.assertEqual(resolve_probe_photometry(renamed, generated, local, worker)[renamed['lights'][0]['ies']], moved.resolve())
            self.assertEqual(resolve_probe_photometry({'lights': []}, generated, local, worker), {})
            with self.assertRaises(ValueError):resolve_probe_photometry({'lights': [{'ies': '../escape.ies'}]}, generated, local, worker)

    def test_real_unavailable_graphics_cannot_silently_fall_back_to_cpu(self):
        select = load_function('select_cycles_device')
        missing = json.loads((FIXTURE.parent/'darkviews-device-before.json').read_text())

        class Preferences:
            def __init__(self, inventory):self.inventory = inventory
            def get_devices(self):pass
            def get_devices_for_type(self, backend):
                return [SimpleNamespace(**d, use=True) for d in self.inventory[backend]['devices']]

        with self.assertRaisesRegex(RuntimeError, 'GPU requested'):
            select(Preferences(missing))
        sibling = {'OPTIX': {'devices': [{'name': 'another CPU host', 'type': 'CPU'}]},
                   'CUDA': {'devices': []}}
        with self.assertRaisesRegex(RuntimeError, 'GPU requested'):
            select(Preferences(sibling))
        clean = deepcopy(sibling)
        clean['OPTIX']['devices'].append({'name': 'NVIDIA GeForce RTX 3090', 'type': 'OPTIX'})
        result = select(Preferences(clean))
        self.assertEqual(result['device'], 'GPU')
        self.assertEqual(result['backend'], 'OPTIX')
        self.assertEqual(result['devices'], ['NVIDIA GeForce RTX 3090'])
        clean['OPTIX']['devices'] = []
        clean['CUDA']['devices'] = [{'name': 'another GPU', 'type': 'CUDA'}]
        self.assertEqual(select(Preferences(clean))['backend'], 'CUDA')
        explicit = select(None, cpu=True)
        self.assertEqual(explicit['device'], 'CPU')
        self.assertTrue(explicit['explicit_cpu'])
