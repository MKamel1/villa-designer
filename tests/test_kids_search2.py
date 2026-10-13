"""Frozen search-2 mattress bounds: a plan pass cannot waive a berth datum."""
import json
from pathlib import Path
import unittest
from archpipe.beds import scaled_bed_fit

class KidsDatums(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=json.loads(Path('tests/fixtures/kids-search2-measured-datums.json').read_text())

    def test_real_ladder_bunks_keep_lower_height_refusals_under_upper_fit(self):
        for row in self.rows:
            if not row['asset'].endswith(('3ddab7a9','ea60847a','b8fb5120')):continue
            lo,hi=row['native_converted_bounds_m']
            frame={'min':[lo[0],lo[2],-hi[1]],'max':[hi[0],hi[2],-lo[1]]}
            fit=scaled_bed_fit(frame,.9,2.,'-X',length_axis='X',mattress_bounds=row['mattress_bounds_native_m'],
                mattress_top_m=1.4,height_berth='upper',height_source='ASSUMED unchanged authored upper top',
                headboard_bounds=frame,headboard_limit_m=2.4,headboard_limit_source='ASSUMED existing diagnostic cap',required_berths=2)
            self.assertTrue(fit['ok'])
            lower=(row['recipes'][0]['converted_bounds_m'][1][2]-lo[2])*fit['scale_xyz'][2]
            self.assertAlmostEqual(lower-.4,row['top_errors_m'][0])
            self.assertGreater(abs(lower-.4),1e-5)

    def test_real_single_mattress_distortion_and_source_unit_refusals(self):
        sweet=next(r for r in self.rows if r['asset'].endswith('8aeacdcd'))
        self.assertFalse(sweet['fit']['ok'])
        self.assertAlmostEqual(sweet['fit']['plan_distortion'],.3317780503758512)
        for row in self.rows:
            if row['asset'].endswith(('560110ad','7e5f290c','c7bea79b')):
                self.assertFalse(row['fit']['ok'])
                self.assertLess(row['fit']['sx'],.5)
                self.assertLess(row['fit']['sy'],.5)
