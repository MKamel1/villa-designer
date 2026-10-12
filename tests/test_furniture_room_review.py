"""Frozen round-6 replacement deterioration, renamed sibling and clean cases."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from archpipe.furniture_room_review import baseline_relative_review

ROOT=Path(__file__).resolve().parents[1]

class BaselineRoom(unittest.TestCase):
    def case(self):
        return json.loads((ROOT/'tests/fixtures/bed-round7-baseline-comparison.json').read_text())

    def compare(self,case):
        return baseline_relative_review(case['baseline'],case['candidate'],
            target_prefixes=case['target_prefixes'],fixed_items=case['fixed_items'])

    def test_real_round6_access_worsening_over_five_mm_refuses_and_renamed_sibling(self):
        for renamed in (False,True):
            case=self.case()
            if renamed:
                def rename(value):
                    if isinstance(value,str):return value.replace('pb-bed','other-villa-bed')
                    if isinstance(value,list):return [rename(v) for v in value]
                    if isinstance(value,dict):return {k:rename(v) for k,v in value.items()}
                    return value
                case=rename(case)
            result=self.compare(case)
            self.assertFalse(result['ok'])
            rows=[r for r in result['findings'] if r['check']=='access']
            self.assertEqual(len(rows),2)
            self.assertTrue(all(r['baseline_m']-r['candidate_m']>.005 for r in rows))

    def test_identical_inherited_findings_stay_reported_and_five_mm_boundary(self):
        case=self.case();case['candidate']=deepcopy(case['baseline'])
        case['baseline']['clearances'][0]['achieved_m']=.5
        case['candidate']['clearances'][0]['achieved_m']=.495
        result=self.compare(case);self.assertTrue(result['ok'])
        self.assertEqual(result['layout_findings'],case['baseline']['findings'])
        case['candidate']['clearances'][0]['achieved_m']-=.000001
        self.assertFalse(self.compare(case)['ok'])

    def test_missing_side_or_new_fixed_body_conflict_refuses(self):
        case=self.case();case['candidate']=deepcopy(case['baseline'])
        case['candidate']['clearances'].pop()
        self.assertFalse(self.compare(case)['ok'])
        case=self.case();case['candidate']=deepcopy(case['baseline'])
        case['candidate']['findings'].append(dict(query='body-overlap',source_id='model-pb-bed::new-part',
            reference_id='different-fixed-cabinet',achieved=.01,required=0))
        self.assertFalse(self.compare(case)['ok'])

    def test_new_boundary_overrun_refuses_even_when_access_is_unchanged(self):
        case=self.case();case['candidate']['clearances']=deepcopy(case['baseline']['clearances'])
        self.assertTrue(any(r['check']=='boundary' for r in self.compare(case)['findings']))

if __name__=='__main__':unittest.main()
