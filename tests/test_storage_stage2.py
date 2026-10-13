"""Real storage-front dispatch and importer helper contamination regressions."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from archpipe.beds import bed_room_review
from archpipe.blender.scene_reset import clear_objects, scene_meshes
from archpipe.furniture_room_review import baseline_relative_review
from archpipe.furniture_fit import fit_furniture

ROOT = Path(__file__).resolve().parents[1]


class StorageFront(unittest.TestCase):
    def case(self):
        return json.loads(gzip.decompress((ROOT / 'tests/fixtures/storage-sideboard-real.json.gz').read_bytes()))

    def review(self, case, mark):
        return bed_room_review(case['scene'], case['layout'], case['specification'],
                               case['furniture'], target_marks=[mark], absolute=True)

    def test_real_preview_rejects_wrong_room_and_preserves_authored_cluster(self):
        from scripts.preview_beds import preview_scope
        case = self.case()
        scene = dict(case['scene'], authoring_room_context=case)
        with self.assertRaisesRegex(ValueError, 'actual authored item room'):
            preview_scope(scene, 'dining-sideboard', 'dining')
        parts, meshes, models = preview_scope(scene, 'dining-sideboard', 'dining-side')
        self.assertEqual(parts, case['scene']['meshes'])
        self.assertTrue(all(p in meshes for p in parts))
        neighbour = dict(parts[0], id='other-dining-furniture', room='dining')
        scene['meshes'] = parts + [neighbour]
        self.assertIn(neighbour, preview_scope(scene, 'dining-sideboard', 'dining-side')[1])
        scene['meshes'] = [dict(p, id=p['id'].replace('dining-sideboard', 'other-store'), room='another-room') for p in parts]
        layout = scene['authoring_room_context']['layout']
        layout['rooms']['another-room'] = dict(layout['rooms']['dining-side'], rect=[100, 100, 102, 102])
        self.assertEqual(len(preview_scope(scene, 'other-store', 'another-room')[0]), len(parts))

    def test_actual_sideboard_uses_storage_card_and_keeps_inherited_findings(self):
        case = self.case()
        report = self.review(case, 'dining-sideboard')
        side = next(r for r in report['clearances'] if r['item'] == 'dining-sideboard')
        self.assertEqual(side['required_m'], .914)
        self.assertIn('87', side['source'])
        result = baseline_relative_review(report, report,
            target_prefixes=('dining-sideboard::', 'furn-dining-sideboard-'))
        self.assertTrue(result['ok'])
        self.assertEqual(result['layout_findings'], report['findings'])
        changed = deepcopy(report)
        next(r for r in changed['clearances'] if r['item'] == 'dining-sideboard')['achieved_m'] -= .006
        self.assertFalse(baseline_relative_review(report, changed,
            target_prefixes=('dining-sideboard::', 'furn-dining-sideboard-'))['ok'])

    def test_renamed_bookcase_and_pantry_siblings_use_storage_card(self):
        for kind in ('bookcase', 'pantry_shelving', 'wardrobe'):
            case = self.case()
            item = next(i for i in case['furniture'] if i['id'] == 'dining-sideboard')
            item.update(id='another-villa-store', type=kind)
            for row in case['scene']['meshes']:
                row['id'] = row['id'].replace('dining-sideboard', item['id'])
            report = self.review(case, item['id'])
            self.assertEqual(next(r for r in report['clearances'] if r['item']==item['id'])['required_m'], .914)

    def test_bed_card_and_no_own_access_units_stay_unchanged(self):
        for kind in ('bed_single', 'bedside_table', 'tv_unit'):
            case = self.case()
            next(i for i in case['furniture'] if i['id']=='dining-sideboard')['type'] = kind
            report = self.review(case, 'dining-sideboard')
            sides = [r for r in report['clearances'] if r['item']=='dining-sideboard']
            if kind == 'bed_single':
                self.assertTrue(sides)
                self.assertTrue(all(r['required_m']==.750 for r in sides))
            else:
                self.assertEqual(sides, [])


class ImportIsolation(unittest.TestCase):
    def test_real_armature_custom_shape_references_never_become_item_geometry(self):
        # Exact real import probe identities, plus a renamed helper sibling.
        for name in ('Icosphere', 'renamed-editor-shape'):
            helper = SimpleNamespace(name=name, type='MESH')
            actual = SimpleNamespace(name='Desk_Oak_0', type='MESH')
            armature = SimpleNamespace(type='ARMATURE', pose=SimpleNamespace(
                bones=[SimpleNamespace(custom_shape=helper)]))
            # Blender objects are identity-hashable; use a small stand-in with
            # the same identity semantics rather than comparing mesh names.
            class Object:
                def __init__(self, source): self.__dict__.update(source.__dict__)
            helper, actual, armature = map(Object, (helper, actual, armature))
            armature.pose.bones[0].custom_shape = helper
            objects = [actual, helper, armature]
            bpy = SimpleNamespace(data=SimpleNamespace(objects=objects),
                context=SimpleNamespace(scene=SimpleNamespace(objects=objects)))
            self.assertEqual(scene_meshes(bpy), [actual])
            armature.pose.bones[0].custom_shape = None
            self.assertEqual(scene_meshes(bpy), [actual, helper])  # Real source mesh named Icosphere stays.

    def test_hidden_and_renamed_inherited_objects_removed_without_selection(self):
        class Objects(list):
            def remove(self, value, *, do_unlink):
                self.asserted_unlink = do_unlink
                super().remove(value)
        objects = Objects([SimpleNamespace(name='Icosphere', hidden=True),
                           SimpleNamespace(name='renamed-sibling', hidden=True),
                           SimpleNamespace(name='visible-clean-body', hidden=False)])
        clear_objects(SimpleNamespace(data=SimpleNamespace(objects=objects)))
        self.assertEqual(objects, [])
        self.assertTrue(objects.asserted_unlink)
        clear_objects(SimpleNamespace(data=SimpleNamespace(objects=objects)))
        self.assertEqual(objects, [])


class StorageIntake(unittest.TestCase):
    def test_real_loose_source_distortion_and_item_omissions(self):
        from scripts.prepare_storage_stage2 import measured_candidate
        cases = json.loads(gzip.decompress((ROOT/'tests/fixtures/storage-fit-real-extrema.json.gz').read_bytes()))
        for case in cases:
            model, rows = measured_candidate(case['geometry'], case['suffix'])
            item = case['item']
            parts = ['Body1_Oak Honey Matte_0'] if case['suffix']=='79138881' else [r['name'] for r in rows]
            fit = fit_furniture(model, item['w'], item['d'], height_parts=parts,
                                height_m=item['h'], height_source='Frozen real authored design height', height_basis='design')
            self.assertEqual(fit['ok'], case['suffix'] in ('c5046eb6', '0999a8a7', '48bd85b3'))
            if case['suffix']=='65c10ad6':
                self.assertAlmostEqual(fit['plan_distortion'], .732561720778387, places=6)
            if case['suffix']=='79138881':
                self.assertAlmostEqual(fit['overall_height_m'], 1.275, places=5)
                self.assertAlmostEqual(fit['plan_distortion'], .2, places=5)
            if case['suffix']=='c5046eb6':
                self.assertEqual(model['omitted_meshes'], ['Object_7'])
                self.assertNotIn('Object_7', [r['name'] for r in rows])
            if case['suffix']=='0999a8a7':
                self.assertEqual(len(model['omitted_meshes']), 6)
                self.assertEqual(len(rows), 6)


if __name__ == '__main__':
    unittest.main()
