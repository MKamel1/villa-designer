"""Frozen D1 numeric evidence for the C5 record re-expression."""
import json
from dataclasses import asdict, FrozenInstanceError, replace
from pathlib import Path
import unittest
from copy import deepcopy

from archpipe import fixture_record as FR
from archpipe.concept import villa_lighting as VL, villa_r11 as R, revit_spec as RS

ROOT = Path(__file__).resolve().parents[1]
BEFORE = json.loads((ROOT / 'tests/fixtures/c5_phase2_before.json').read_text())


class UnifiedRecord(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lay = R.design('D1')
        cls.fixtures = VL.design(cls.lay)

    @staticmethod
    def corrected_before_fixtures():
        # Explicit exception values: two complete pair corrections, no other change.
        expected = json.loads(json.dumps(BEFORE['fixtures']))
        corrected = {'SCONCE-guest-wc-03': (9.36,-23.476),
                     'SCONCE-guest-wc-04': (9.36,-22.526),
                     'VSCONCE-parents-ensuite-04': (19.887,-29.916),
                     'VSCONCE-parents-ensuite-05': (19.887,-28.966)}
        for f in expected:
            if f['id'] in corrected:
                f['x'],f['y'] = corrected[f['id']]
                f['extra']['vanity_pair_source_correction'] = True
        return expected

    def test_pair_construction_generalises_and_refuses_impossible_wall(self):
        # Same measured room, renamed/translated sibling, no special identifiers.
        for name, centre, kind in [('guest-wc',-23.150,'SCONCE'),
                                    ('parents-ensuite',-29.281,'VSCONCE')]:
            from archpipe.concept import villa_furnish as F
            rect = F.clear_rect(self.lay,name)
            fixed, changed = FR.vanity_pair_datum(rect,centre,kind)
            self.assertTrue(changed)
            shifted = tuple(v+7 for v in rect)
            sibling,_ = FR.vanity_pair_datum(shifted,centre+7,kind)
            self.assertAlmostEqual(sibling,fixed+7)
            self.assertEqual(FR.vanity_pair_datum(rect,fixed,kind),(fixed,False))
        with self.assertRaisesRegex(ValueError,'cannot hold'):
            FR.vanity_pair_datum((0,0,1,.5),.25,'SCONCE')

    def test_kind_requirements_and_geometry_are_immutable(self):
        for kind in FR.FIXTURE_KINDS.values():
            with self.assertRaises(TypeError):
                kind.spec['mount'] = 'pendant'
            with self.assertRaises(TypeError):
                kind.housing['width'] = 1
        record = self.fixtures[0].record
        with self.assertRaises(FrozenInstanceError):
            record.flux_lm = 4300

    def test_record_owns_nested_authored_metadata(self):
        fixture=VL.Fixture('renamed-reading-arm','SWING','another-room','GF',1,1,1,
                           extra={'wall_plate':[1.,2.]})
        record=fixture.record
        fixture.extra['wall_plate'][0]=3.
        self.assertEqual(dict(record.extra)['wall_plate'],(1.,2.))

    def test_records_preserve_all_legacy_fixture_inputs(self):
        actual = json.loads(json.dumps([asdict(f) for f in self.fixtures]))
        expected = self.corrected_before_fixtures()
        retired = {fid for ids in FR.VANITY_DECISIONS.values() for fid in ids}
        self.assertEqual([f for f in actual if not f['extra'].get('over_mirror')],
                         [f for f in expected if f['id'] not in retired])

    def test_lux_reexpression_matches_frozen_real_before(self):
        frozen = [VL.Fixture(**fixture) for fixture in self.corrected_before_fixtures()]
        actual, old = VL.check(self.lay, self.fixtures), VL.check(self.lay, frozen)
        self.assertEqual([t for t in actual['tasks'] if t['room'] not in FR.VANITY_DECISIONS],
                         [t for t in old['tasks'] if t['room'] not in FR.VANITY_DECISIONS])
        self.assertEqual([r for r in actual['rooms'] if r['room'] not in FR.VANITY_DECISIONS],
                         [r for r in old['rooms'] if r['room'] not in FR.VANITY_DECISIONS])

    def test_all_effective_flux_and_colour_values_match_branch_start(self):
        retired = {fid for ids in FR.VANITY_DECISIONS.values() for fid in ids}
        retained = [f for f in self.fixtures if not f.extra.get('over_mirror')]
        self.assertEqual({f.id:f.record.flux_lm for f in retained},
                         {k:v for k,v in BEFORE['effective_flux_lm'].items() if k not in retired})
        self.assertEqual({f.id:f.record.cct_k for f in retained},
                         {k:v for k,v in BEFORE['effective_cct_k'].items() if k not in retired})

    def test_shell_revit_spec_is_unchanged_and_lighting_uses_records(self):
        self.assertEqual(json.loads(json.dumps(RS.build(self.lay))), BEFORE['spec'])
        native = RS.lighting_spec(self.lay)
        self.assertEqual(len(native), len(self.fixtures))
        for f, entry in zip(self.fixtures, native):
            record = f.record
            self.assertEqual(entry, record.native_spec())
            self.assertEqual(entry['mounting_height'], f.z * 1000)
            self.assertEqual(entry['lumens'], f.lumens)
            self.assertEqual(entry['housing'], dict(record.housing))

    def test_all_record_photometry_shapes_are_identical_for_renamed_sibling(self):
        for f in self.fixtures:
            record = f.record
            renamed = replace(record, id='other-villa-' + record.id, room='another-room')
            p, generic = record.photometry()
            q, sibling_generic = renamed.photometry()
            self.assertEqual(generic, sibling_generic)
            self.assertEqual(p.integrated_flux(), q.integrated_flux())
            self.assertEqual(p.illuminance_at(.3,.2,1.5),q.illuminance_at(.3,.2,1.5))

    def test_real_built_pair_guard_fires_quiet_and_renamed_sibling(self):
        from copy import deepcopy
        data = json.loads((ROOT/'tests/fixtures/c5_pair_scene.json').read_text())
        # Keep the exact rejected historical migration proof after retirement.
        records = [VL.Fixture(**f).record for f in self.corrected_before_fixtures()
                   if f['extra'].get('vanity_pair_source_correction')]
        self.assertEqual(len(FR.vanity_scene_findings(data['before'],records)),4)
        self.assertEqual(FR.vanity_scene_findings(data['after'],records),[])
        renamed = deepcopy(data['after'])
        for m in renamed['meshes']:
            m['id'] = m['id'].replace('SCONCE-','SCONCE-sibling-')
        siblings = [replace(r,id=r.id.replace('SCONCE-','SCONCE-sibling-')) for r in records]
        self.assertEqual(FR.vanity_scene_findings(renamed,siblings),[])
        moved = next(m for m in renamed['meshes'] if m['id'].startswith('lamp-'))
        for face in moved['faces']:
            for p in face:p[1]+=.005
        self.assertEqual(len(FR.vanity_scene_findings(renamed,siblings)),1)
        renamed['meshes'].remove(moved)
        self.assertIn('missing built vanity emitter',FR.vanity_scene_findings(renamed,siblings)[0])

    def test_real_checkpoint_tuple_arrays_normalise_without_hiding_numeric_drift(self):
        from copy import deepcopy
        from scripts.checkpoint_c5_phase2 import numeric_findings
        data=json.loads((ROOT/'tests/fixtures/c5_pair_scene.json').read_text())
        before={key:BEFORE[key] for key in ('fixtures','lighting','lights','spec')}
        before['fixture_meshes']=data['before']['meshes']
        after=deepcopy(before)
        after['fixtures']=[asdict(VL.Fixture(**f)) for f in self.corrected_before_fixtures()]
        after['lighting']=data['after']['lighting']
        after['fixture_meshes']=deepcopy(data['after']['meshes'])
        line=next(m for m in after['fixture_meshes'] if m['id']=='lamp-PEN-LIN-dining-01')
        line['occupied_side']=tuple(line['occupied_side'])  # real builder representation
        self.assertEqual(numeric_findings(before,before,after),[])
        line['faces'][0][0][2]+=.005
        self.assertIn('unrelated fixture changed: lamp-PEN-LIN-dining-01',numeric_findings(before,before,after))

    def test_real_preview_missing_sensor_is_prevented_by_complete_camera_copy(self):
        from scripts.checkpoint_c5_phase2 import neutral_input
        from archpipe.concept import villa_render as VR
        frozen = json.loads((ROOT/'tests/fixtures/c5_preview_camera_before.json').read_text())
        with self.assertRaisesRegex(ValueError,'sensor_mm'):
            neutral_input({'meshes':[],'materials':{}},'guest-wc',frozen)
        camera = VR.VIEWS(resolve=False)[0]['camera']
        clean = neutral_input({'meshes':[],'materials':{}},'guest-wc',camera)
        self.assertEqual(clean['views'][0]['camera']['sensor_mm'],camera['sensor_mm'])
        sibling = dict(frozen,label='renamed corner')
        with self.assertRaisesRegex(ValueError,'sensor_mm'):
            neutral_input({'meshes':[],'materials':{}},'other-bath',sibling)

    def test_frozen_pre_fix_real_mounts_fire_and_renamed_siblings_fire(self):
        bad = [f for f in BEFORE['fixtures'] if f['id'] in
               ('SCONCE-guest-wc-03','VSCONCE-parents-ensuite-05')]
        failures = FR.fixture_findings(layout=self.lay, spec={'fixtures': bad})
        self.assertEqual({f.fixture_id for f in failures if f.status == 'FAIL'}, {f['id'] for f in bad})
        for fixture in bad:
            fixture = dict(fixture,id='unrelated-villa-corner')
            result = FR.fixture_findings(layout=self.lay,spec={'fixtures':[fixture]})
            self.assertEqual([f.rule for f in result],['fitting_room_containment'])
            self.assertEqual(result[0].fixture_id,'unrelated-villa-corner')


class ClientVanityDecision(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from archpipe.concept import villa_render as VR
        cls.fixtures = [f for f in VL.design(R.design('D1')) if f.extra.get('over_mirror')]
        cls.before = json.loads((ROOT/'tests/fixtures/c5_client_vanity_scene.json').read_text())
        cls.scene = deepcopy(cls.before)
        VR.apply_vanity_decision(cls.scene,cls.fixtures)

    def test_real_single_bars_are_symmetric_clear_and_retire_complete_pairs(self):
        from archpipe.concept.fitting_mounting import bounds
        records = [f.record for f in self.fixtures]
        self.assertEqual(FR.vanity_scene_findings(self.scene,records),[])
        self.assertEqual(len(records),2)
        ids = {m['id'] for m in self.scene['meshes']}
        for f in self.fixtures:
            self.assertEqual(f.record.cct_k,3000)
            self.assertEqual(f.extra['decision_source'],'CLIENT DECISION 2026-10-08')
            self.assertIn('ASSUMED',f.record.native_spec()['assumptions'])
            self.assertEqual(f.record.flux_lm,100*(.4 if f.room=='parents-ensuite' else 1))
            for retired in f.extra['retired_fixture_ids']:
                self.assertFalse(any(mid.endswith('-'+retired) for mid in ids))
            mirror = next(m for m in self.scene['meshes'] if m['id']==f.extra['mirror_id'])
            original = next(m for m in self.before['meshes'] if m['id']==mirror['id'])
            self.assertEqual(mirror,original)
            b = bounds(next(m for m in self.scene['meshes'] if m['id']=='body-'+f.id))
            mb = bounds(mirror)
            self.assertAlmostEqual(b[4]-b[1],.5)
            self.assertAlmostEqual(mb[4]-mb[1],.56)
            self.assertAlmostEqual((b[2]+b[5])/2-mb[5],.1)
            self.assertAlmostEqual(b[2]-mb[5],.08)

    def test_real_missing_off_axis_overlap_and_off_wall_fittings_fail(self):
        records = [f.record for f in self.fixtures]
        for prefix,coordinate,delta,expected in (
                ('body-',1,.005,'symmetry'),('body-',2,-.081,'mirror_overlap'),
                ('body-',0,.005,'mount'),('lamp-',1,.005,'emitter differs')):
            mutant=deepcopy(self.scene)
            m=next(m for m in mutant['meshes'] if m['id']==prefix+records[0].id)
            for face in m['faces']:
                for p in face:p[coordinate]+=delta
            self.assertTrue(any(expected in f for f in FR.vanity_scene_findings(mutant,records)))
        mutant=deepcopy(self.scene)
        mutant['meshes']=[m for m in mutant['meshes'] if m['id']!='body-'+records[0].id]
        self.assertTrue(any('missing mirror or complete fitting body' in f
                            for f in FR.vanity_scene_findings(mutant,records)))

    def test_renamed_and_translated_room_sibling_stays_quiet_and_mutation_fires(self):
        scene=deepcopy(self.scene); offset=7.
        records=[]
        for fixture in self.fixtures:
            r=fixture.record; extra=dict(fixture.extra)
            extra['mirror_id']='renamed-'+extra['mirror_id']
            extra['room_rect']=tuple(v+offset for v in extra['room_rect'])
            extra['finished_wall']+=offset; extra['ceiling_z']+=offset
            records.append(replace(r,id='renamed-'+r.id,room='other-villa-'+r.room,
                                   position=tuple(v+offset for v in r.position),extra=FR._freeze_value(extra)))
        for m in scene['meshes']:
            for f in self.fixtures:
                if m['id'] in ('body-'+f.id,'lamp-'+f.id):
                    prefix=m['id'].split('-',1)[0]+'-'; m['id']=prefix+'renamed-'+f.id
                elif m['id']==f.extra['mirror_id']:m['id']='renamed-'+m['id']
            for face in m['faces']:
                for p in face:
                    for i in range(3):p[i]+=offset
        self.assertEqual(FR.vanity_scene_findings(scene,records),[])
        m=next(m for m in scene['meshes'] if m['id']=='body-'+records[1].id)
        for face in m['faces']:
            for p in face:p[1]+=.005
        self.assertTrue(any('symmetry' in f for f in FR.vanity_scene_findings(scene,records)))

    def test_centred_single_never_excuses_a_missing_or_frozen_shifted_pair(self):
        rejected=json.loads((ROOT/'tests/fixtures/c5_lead_rejected_pairs.json').read_text())
        for row in rejected['rooms']:
            arguments=dict(clear_interval=(row['room_rect'][1],row['room_rect'][3]),axis=row['axis'],
                mirror_interval=row['mirror_interval'],half_width=.25,minimum_gap=0,over_mirror=(2.,1.9,.02))
            self.assertEqual(FR.vanity_pair_findings([row['axis']],**arguments),[])
            self.assertTrue(FR.vanity_pair_findings([row['axis']+.005],**arguments))
            self.assertTrue(FR.vanity_pair_findings([row['axis']],**dict(arguments,over_mirror=None)))
            self.assertTrue(FR.vanity_pair_findings([f['y'] for f in row['fixtures']],
                **dict(arguments,half_width=row['half_width'],minimum_gap=row['minimum_gap'],over_mirror=None)))
        self.assertTrue(FR.vanity_pair_findings([float('nan')],**arguments))

    def test_datum_generalises_to_the_opposite_finished_wall_and_refuses_overlong_bar(self):
        basin=(.3,.2,.9,.8)
        for normal,wall in ((1,.023),(-1,1.977)):
            x,y,z=FR.over_mirror_datum((0,0,2,2),basin,.56,1.8,wall,normal)
            self.assertAlmostEqual(x,wall+normal*.02)
            self.assertAlmostEqual(y,.5)
            self.assertAlmostEqual(z,1.9)
        with self.assertRaisesRegex(ValueError,'length'):
            FR.over_mirror_datum((0,0,2,2),basin,.4,1.8,.023,1)
        with self.assertRaisesRegex(ValueError,'boundary'):
            FR.over_mirror_datum((0,.49,2,2),basin,.56,1.8,.023,1)

    def test_full_scene_checkpoint_compares_json_contract_and_still_finds_real_changes(self):
        from scripts.checkpoint_c5_phase2 import scene_preservation_findings
        # Real snapshot shape: source wall occupied_side is a Python tuple;
        # the saved scene has the same JSON array, not a geometry difference.
        current=dict(meshes=[dict(self.before['meshes'][0],group='shell',occupied_side=(1,0,0))],
                     props=[dict(position=(1,2,3))],models=[],cloth=[],curtains=[])
        frozen=json.loads(json.dumps(current))
        self.assertEqual(scene_preservation_findings(frozen,current),[])
        current['meshes'][0]['faces']=deepcopy(current['meshes'][0]['faces'])
        current['meshes'][0]['faces'][0][0][0]+=.005
        self.assertIn('unrelated shell geometry or metadata changed',scene_preservation_findings(frozen,current))
        current=deepcopy(frozen);current['props'][0]['position'][1]+=.005
        self.assertIn('unrelated props changed',scene_preservation_findings(frozen,current))


if __name__ == '__main__':
    unittest.main()
