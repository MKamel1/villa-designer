"""Frozen real dominant-light assignments and policy mutation regressions."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from archpipe.exposure_groups import (APPEARANCE_KEYS, TRANSPORT_KEYS, classify, digest, freeze, group_for, measurement,
                                     require_receipts, require_record, rule, white_balances)
ROOT = Path(__file__).resolve().parents[1]


class ExposureGroups(unittest.TestCase):
    def test_pre_registered_rule_and_source_mask(self):
        self.assertIn('PRE-REGISTERED', rule()['status'])
        row = measurement([6.]*100, [4.]*100, [3.]*100)
        self.assertEqual(row['metered_pixels'], 97)
        self.assertEqual(row['lamp_fraction'], .6)
        self.assertEqual(row['solar_fraction'], .25)
        self.assertEqual(classify({'exposure':'day'}, row), 'lamp-dominant')
        self.assertEqual(classify({'exposure':'evening'}, row), 'evening')
        row = measurement([0.]*100, [4.]*100, [3.]*100)
        self.assertEqual(classify({'exposure':'exterior-day'}, row), 'exterior-shade')
        self.assertEqual(classify({'exposure':'day'}, row), 'day')
        row['solar_fraction'] = .51
        self.assertEqual(classify({'exposure':'exterior-day'}, row), 'exterior-day')
        row['lamp_fraction'] = .5
        self.assertEqual(classify({'exposure':'day'}, row), 'day')
        with self.assertRaisesRegex(ValueError, 'populations'):
            measurement([1], [1,2])
        with self.assertRaisesRegex(ValueError, 'positive'):
            measurement([0]*100, [0]*100)

    def frozen(self):
        return json.loads((ROOT/'tests/fixtures/exposure-groups-real.json').read_text())

    def test_real_v15_v29_v36_rule_and_clean_case(self):
        data = self.frozen()
        for ident in ('v15-family-bath', 'v29-under-stair-store', 'v36-north-garden', 'v01-kitchen-garden'):
            row = data['measurements'][ident]
            self.assertEqual(classify(row['view_input'], row), row['group'])
            renamed = dict(row['view_input'], id='other-villa-renamed-camera')
            self.assertEqual(classify(renamed, row), row['group'])
        self.assertEqual(len([row for row in data['measurements'].values() if row['active']]), 38)

    def real_scene(self):
        data = self.frozen()
        # Frozen source values, not a call to today's scene generator.
        scene = dict(data['transport'], views=[row['view_input'] for row in data['measurements'].values()])
        rows = {ident:{k:v for k,v in row.items() if k != 'active'} for ident,row in data['measurements'].items()}
        record = freeze(scene, rows, data['runtime'])
        scene['exposure_groups'] = record
        return scene, record

    def test_real_membership_mutation_and_renamed_sibling_refuse(self):
        scene, record = self.real_scene()
        require_record(scene, record)
        for ident in ('v15-family-bath', 'v29-under-stair-store', 'v36-north-garden'):
            broken = deepcopy(record)
            broken['measurements'][ident]['group'] = 'hand-picked'
            with self.assertRaisesRegex(ValueError, 'edited'):
                require_record(scene, broken)
            # Even refreshing the digest cannot legitimise a membership edit.
            broken['measurement_sha256'] = digest(broken['measurements'])
            with self.assertRaisesRegex(ValueError, 'membership'):
                require_record(scene, broken)
        manual = deepcopy(scene)
        manual['views'][0]['exposure_group'] = 'hand-picked'
        with self.assertRaisesRegex(ValueError, 'membership'):
            require_record(manual, record)
        renamed = deepcopy(scene)
        view = next(v for v in renamed['views'] if v['id']=='v29-under-stair-store')
        old = view['id']; view['id'] = 'sibling-store-camera'
        rows = deepcopy(record['measurements'])
        rows[view['id']] = rows.pop(old)
        sibling = freeze(renamed, rows, record['runtime'])
        require_record(renamed, sibling)
        sibling['measurements'][view['id']]['group'] = 'hand-picked'
        sibling['measurement_sha256'] = digest(sibling['measurements'])
        with self.assertRaisesRegex(ValueError, 'membership'):
            require_record(renamed, sibling)

    def reports(self, scene, record):
        reports = []
        for view in scene['views']:
            group = group_for(scene, view)
            cohort = [v['id'] for v in scene['views'] if group_for(scene,v)==group]
            reports.append(dict(view=view['id'], exposure_state=view['exposure'], exposure_group=group, exposure_stops=-7.,
                                white_balance_k=record['white_balance_k'][group], white_balance_applied=True,
                                exposure_rule_measurement=record['measurements'][view['id']],
                                exposure_rule_sha256=record['rule_sha256'],
                                exposure_measurement_sha256=record['measurement_sha256'],
                                exposure_metered_over=cohort, exposure_locked_per_group=True,
                                group_meters={ident:dict(exposure_stops=-7., log_average=1.) for ident in cohort}))
        return reports

    def test_real_receipt_wrong_group_gain_white_balance_and_subset_refuse(self):
        scene, record = self.real_scene()
        reports = self.reports(scene, record)
        require_receipts(scene, reports)
        for ident in ('v15-family-bath', 'v29-under-stair-store', 'v36-north-garden'):
            for field, value in [('exposure_group','hand-picked'), ('white_balance_k',1234),
                                 ('exposure_stops',-99), ('exposure_metered_over',[])]:
                broken = deepcopy(next(row for row in reports if row['view']==ident))
                broken[field] = value
                with self.assertRaises(ValueError):
                    require_receipts(scene, [broken])
        missing = dict(scene, exposure_group_mode='dominant-light')
        missing.pop('exposure_groups')
        with self.assertRaisesRegex(ValueError, 'Missing'):
            require_receipts(missing, reports)
        same_group = [row for row in reports if row['exposure_group']=='day']
        self.assertGreaterEqual(len(same_group), 2)
        broken = deepcopy(same_group[1]); broken['exposure_stops'] = -6.
        for row in broken['group_meters'].values():
            row['exposure_stops'] = -6.
        with self.assertRaisesRegex(ValueError, 'Multiple'):
            require_receipts(scene, [same_group[0], broken])

    def test_actual_gpu_receipts_obey_locks_and_mutations_refuse(self):
        scene, _ = self.real_scene()
        reports = self.frozen()['reports']
        declared={ident for ident,row in self.frozen()['measurements'].items() if row['active']}
        self.assertEqual({row['view'] for row in reports},declared)
        self.assertEqual(len(reports),len(declared))
        require_receipts(scene, reports)
        for ident in ('v15-family-bath', 'v29-under-stair-store', 'v36-north-garden'):
            actual = next(row for row in reports if row['view']==ident)
            for field,value in [('exposure_stops',actual['exposure_stops']+1),
                                ('white_balance_k',actual['white_balance_k']+100),
                                ('exposure_group','hand-assigned')]:
                broken=deepcopy(actual);broken[field]=value
                with self.assertRaises(ValueError):
                    require_receipts(scene,[broken])
        # Rename one real camera and every bound reference without changing photons.
        rows = deepcopy(scene['exposure_groups']['measurements'])
        old='v29-under-stair-store';new='other-villa-store'
        rows[new]=rows.pop(old)
        for view in scene['views']:
            if view['id']==old:view['id']=new
        record=freeze(scene,rows,scene['exposure_groups']['runtime']);scene['exposure_groups']=record
        sibling=deepcopy(next(row for row in reports if row['view']==old))
        sibling['view']=new
        sibling['exposure_rule_measurement']=record['measurements'][new]
        sibling['exposure_measurement_sha256']=record['measurement_sha256']
        sibling['exposure_metered_over']=[new if ident==old else ident for ident in sibling['exposure_metered_over']]
        sibling['group_meters']={new if ident==old else ident:value for ident,value in sibling['group_meters'].items()}
        require_receipts(scene,[sibling])
        sibling['exposure_group']='hand-picked'
        with self.assertRaises(ValueError):require_receipts(scene,[sibling])

    def test_stale_transport_view_fraction_and_population_refuse(self):
        scene, record = self.real_scene()
        empty = dict(scene, views=[])
        with self.assertRaisesRegex(ValueError, 'inventory'):
            require_record(empty, record)
        require_record(dict(empty, views=scene['views']), record)
        broken = deepcopy(scene); broken['lights'][0]['lumens'] *= 2
        with self.assertRaisesRegex(ValueError, 'transport'):
            require_record(broken, record)
        broken = deepcopy(scene); broken['views'][0]['camera']['position'][0] += .1
        with self.assertRaisesRegex(ValueError, 'membership'):
            require_record(broken, record)
        broken = deepcopy(record)
        broken['measurements']['v15-family-bath']['lamp_fraction'] = .999
        broken['measurement_sha256'] = digest(broken['measurements'])
        with self.assertRaisesRegex(ValueError, 'fraction'):
            require_record(scene, broken)
        broken = deepcopy(record); broken['white_balance_k']['lamp-dominant'] += 1
        with self.assertRaisesRegex(ValueError, 'white balance'):
            require_record(scene, broken)
        broken = deepcopy(record); broken['runtime']['probe']['samples'] = 24
        with self.assertRaisesRegex(ValueError, 'probe settings'):
            require_record(scene, broken)
        self.assertEqual(record['white_balance_k']['evening'],3000)
        self.assertEqual(record['white_balance_k']['exterior-dusk'],4300)
        self.assertEqual(record['white_balance_k']['exterior-shade'],5500)
        self.assertEqual(record['white_balance_k'],white_balances(record))

    def test_real_appearance_source_changes_and_sibling_refuse(self):
        scene, record = self.real_scene()
        require_record(scene,record)
        legacy_digest=lambda value:digest({key:value.get(key) for key in TRANSPORT_KEYS if key not in APPEARANCE_KEYS})
        for key in ('draped_appearances','drape_material_overrides','imported_appearances'):
            broken=deepcopy(scene)
            if isinstance(broken[key],list):
                broken[key][0]['source_faces_sha256' if key=='imported_appearances' else 'appearance_sha256']='changed-source'
            else:
                first=next(iter(broken[key]));broken[key][first]['roughness']=.12345
            self.assertEqual(legacy_digest(broken),legacy_digest(scene))
            with self.assertRaisesRegex(ValueError,'transport'):
                require_record(broken,record)
        # A different source record in the same family must also invalidate reuse.
        broken=deepcopy(scene)
        broken['draped_appearances'][-1]['id']='renamed-appearance-sibling'
        with self.assertRaisesRegex(ValueError,'transport'):
            require_record(broken,record)

    def test_real_baseline_appearance_difference_is_not_transport_equality(self):
        source=json.loads((ROOT/'tests/fixtures/exposure-groups-appearance-baseline.json').read_text())
        scene,record=self.real_scene()
        before=dict(scene,**source['before'])
        current=dict(scene,**source['after'])
        old_keys=[key for key in TRANSPORT_KEYS if key not in APPEARANCE_KEYS]
        self.assertEqual(digest({key:before.get(key) for key in old_keys}),
                         digest({key:current.get(key) for key in old_keys}))
        self.assertNotEqual(digest(before['draped_appearances']),digest(current['draped_appearances']))
        self.assertEqual(len(source['differences']),85)
        require_record(current,record)
        with self.assertRaisesRegex(ValueError,'transport'):
            require_record(before,record)

    def test_real_raw_view_declarations_omit_final_visibility_and_refuse(self):
        source=json.loads((ROOT/'tests/fixtures/exposure-groups-pre-mount-views.json').read_text())
        scene,record=self.real_scene()
        raw_scene=dict(scene,views=source['views'])
        for ident in ('v15-family-bath','v29-under-stair-store','v36-north-garden'):
            raw=next(v for v in source['views'] if v['id']==ident)
            final=record['measurements'][ident]['view_input']
            self.assertNotEqual(raw.get('hide_meshes'),final.get('hide_meshes'))
        with self.assertRaisesRegex(ValueError,'membership'):
            require_record(raw_scene,record)
        require_record(scene,record)

    def test_group_meter_is_selection_independent(self):
        from tests.test_villa_exposure_assets import load_function
        scene, _ = self.real_scene()
        views = [dict(v,exposure_group=group_for(scene,v)) for v in scene['views']]
        locks = load_function('exposure_locks')
        locks.__globals__['exposure_meter_views'] = load_function('exposure_meter_views')
        meter = lambda v: (float(len(v['id'])), .18)
        for view in views:
            alone = locks(views,{view['id']},meter)
            all_views = locks(views,{v['id'] for v in views},meter)
            group = view['exposure_group']
            self.assertEqual(alone[0][group], all_views[0][group])
            self.assertEqual(alone[2][group], all_views[2][group])


if __name__ == '__main__':
    unittest.main()
