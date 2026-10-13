"""Real rejected symmetry, infeasibility, clean and translated-room proofs."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from archpipe.fixture_record import centred_vanity_pair, vanity_pair_findings
from scripts.checkpoint_c5_phase2 import lead_review, preview_receipt_findings

ROOT = Path(__file__).resolve().parents[1]
REJECTED = json.loads((ROOT/'tests/fixtures/c5_lead_rejected_pairs.json').read_text())


def arguments(row):
    return dict(clear_interval=(row['room_rect'][1],row['room_rect'][3]),
                axis=row['axis'], mirror_interval=row['mirror_interval'],
                half_width=row['half_width'], minimum_gap=row['minimum_gap'],
                edge_allowance=row['edge_allowance'])


class LeadReview(unittest.TestCase):
    def test_real_zero_view_receipt_fails_and_clean_renamed_sibling_passes(self):
        # Actual receipt from omitted --views: Blender exited zero with [].
        self.assertTrue(preview_receipt_findings([], 'guest-wc'))
        image=ROOT/'tests/fixtures/c5_preview_camera_before.json'  # held artifact, no rendering dependency
        clean=[dict(id='guest-wc',image=str(image))]
        self.assertEqual(preview_receipt_findings(clean,'guest-wc'),[])
        self.assertTrue(preview_receipt_findings(clean,'another-room'))
        sibling=[dict(id='another-room',image=str(image))]
        self.assertEqual(preview_receipt_findings(sibling,'another-room'),[])
        self.assertTrue(preview_receipt_findings([dict(id='another-room',image=str(image)+'.missing')],'another-room'))

    def test_real_block_shift_fails_symmetry_and_mirror_gap(self):
        for row in REJECTED['rooms']:
            with self.subTest(room=row['room']):
                centres=[f['y'] for f in row['fixtures']]
                findings=vanity_pair_findings(centres,**arguments(row))
                self.assertTrue(any('vanity_pair_symmetry' in f for f in findings))
                self.assertTrue(any('vanity_pair_mirror_gap' in f for f in findings))
                self.assertFalse(any('vanity_pair_boundary' in f for f in findings))

    def test_real_rooms_refuse_measured_shortfalls_without_moving_anything(self):
        for row,shortfall in zip(REJECTED['rooms'],(596,640)):
            original=deepcopy(row)
            with self.assertRaisesRegex(ValueError,f'shortfall {shortfall:.3f} mm'):
                centred_vanity_pair(**arguments(row))
            self.assertEqual(row,original)

    def test_original_intact_gap_is_also_infeasible(self):
        for row,gap,shortfall in zip(REJECTED['rooms'],(.135,.165),(298,320)):
            args=arguments(row)
            args['minimum_gap']=gap
            with self.assertRaisesRegex(ValueError,f'shortfall {shortfall:.3f} mm'):
                centred_vanity_pair(**args)

    def test_clean_feasible_pair_retains_authored_separation(self):
        # A separate feasible wall; this is not a correction to the blocked rooms.
        args=dict(clear_interval=(-1,1), axis=0, mirror_interval=(-.28,.28),
                  half_width=.06, minimum_gap=.135)
        centres=centred_vanity_pair(**args)
        self.assertEqual(centres,(-.475,.475))
        self.assertEqual(vanity_pair_findings(centres,**args),[])

    def test_clean_constrained_pair_uses_largest_separation_and_equal_gaps(self):
        args=dict(clear_interval=(-.5,.9), axis=0, mirror_interval=(-.28,.28),
                  half_width=.06, minimum_gap=.02)
        centres=centred_vanity_pair(**args)
        self.assertAlmostEqual(centres[1]-centres[0],.870)
        self.assertEqual(vanity_pair_findings(centres,**args),[])
        larger=(centres[0]-.001,centres[1]+.001)
        self.assertTrue(any('vanity_pair_boundary' in f for f in vanity_pair_findings(larger,**args)))
        shifted=[v+.005 for v in centres]
        self.assertTrue(any('vanity_pair_symmetry' in f for f in vanity_pair_findings(shifted,**args)))

    def test_translated_real_room_and_clean_sibling(self):
        for row in REJECTED['rooms']:
            args=arguments(row)
            translated=dict(args,clear_interval=tuple(v+7 for v in args['clear_interval']),
                            mirror_interval=tuple(v+7 for v in args['mirror_interval']),axis=args['axis']+7)
            centres=[f['y']+7 for f in row['fixtures']]
            self.assertTrue(any('vanity_pair_symmetry' in f for f in vanity_pair_findings(centres,**translated)))
            with self.assertRaisesRegex(ValueError,'No centred vanity pair'):
                centred_vanity_pair(**translated)
        args=dict(clear_interval=(6.5,7.9),axis=7,mirror_interval=(6.72,7.28),
                  half_width=.06,minimum_gap=.02)
        self.assertEqual(vanity_pair_findings(centred_vanity_pair(**args),**args),[])

    def test_solver_refuses_mismatched_axes_and_nonpositive_gap(self):
        args=dict(clear_interval=(-1,1),axis=0,mirror_interval=(-.28,.28),half_width=.06,minimum_gap=.02)
        with self.assertRaisesRegex(ValueError,'axes disagree'):
            centred_vanity_pair(**dict(args,axis=.005))
        with self.assertRaisesRegex(ValueError,'positive'):
            centred_vanity_pair(**dict(args,minimum_gap=0))

    def test_full_numeric_preservation_never_implies_design_acceptance(self):
        from tests.test_fixture_record_phase2 import BEFORE
        from archpipe.concept import villa_lighting as VL, villa_r11 as R
        from dataclasses import asdict
        data=json.loads((ROOT/'tests/fixtures/c5_pair_scene.json').read_text())
        before=deepcopy(BEFORE)
        before['fixture_meshes']=data['before']['meshes']
        current=deepcopy(before)
        current['fixture_meshes']=data['after']['meshes']
        current['lighting']=data['after']['lighting']
        from tests.test_fixture_record_phase2 import UnifiedRecord
        current['fixtures']=[asdict(VL.Fixture(**f)) for f in UnifiedRecord.corrected_before_fixtures()]
        report=lead_review(before,current,REJECTED)
        self.assertEqual(report['unexpected_numeric_differences'],[])
        self.assertFalse(report['design_passed'])
        self.assertFalse(report['placement_changed'])
        self.assertEqual([round(r['separation_shortfall_mm']) for r in report['rooms']],[596,640])
        self.assertTrue(all(r['refusal'] for r in report['rooms']))
        current['fixtures'][0]['z']+=.005
        self.assertTrue(lead_review(before,current,REJECTED)['unexpected_numeric_differences'])
        current['fixture_meshes']=[m for m in current['fixture_meshes']
                                   if m['id']!='lamp-SCONCE-guest-wc-03']
        report=lead_review(before,current,REJECTED)
        self.assertTrue(any('vanity_pair_members' in f for f in report['rooms'][0]['findings']))


if __name__=='__main__':
    unittest.main()
