"""Regression cases found by reviewing the real bedroom, not the input spec."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from archpipe.from_extract import convert
from archpipe.model import SpecError
from archpipe.review_extract import review_model


class ExtractReviewTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'tests/fixtures/bedroom-from-revit.json').read_text())

    def item(self, mark):
        return next(f for f in self.data['furniture'] if f['mark'] == mark)

    def test_all_measured_pieces_survive(self):
        p = convert(self.data).project
        self.assertEqual(len(p.furniture), 6)
        by_id = {f.id: f for f in p.furniture}
        self.assertEqual(by_id['FN-BST-L'].type, 'bedside_table')
        self.assertEqual(by_id['FN-DSK'].size, (1200, 600))
        self.assertEqual(by_id['FN-WRD'].size, (1200, 600))
        self.assertAlmostEqual(by_id['FN-CHR'].size[0], 555.469, places=2)

    def test_unknown_furniture_still_blocks(self):
        f = self.item('FN-CHR')
        f.update(type_name='custom sculpture', family='', archpipe={},
                 bbox_center_mm=self.item('FN-BED')['at'])
        result = review_model(self.data, scope='room')
        self.assertTrue(any(x['rule'] == 'FURN-03' for x in result['findings']))

    def test_accessory_is_not_exempt_from_physical_collision(self):
        table = self.item('FN-BST-L')
        table['bbox_center_mm'] = self.item('FN-BED')['at']
        self.assertTrue(any(f['rule'] == 'FURN-03'
                            for f in review_model(self.data, scope='room')['findings']))

    def test_unrelated_chair_still_blocks_bed_access(self):
        f = self.item('FN-CHR')
        f['bbox_center_mm'] = [2250, 1250]
        self.assertTrue(any(x['rule'] == 'FURN-02' and x['where'] == 'FN-BED'
                            for x in review_model(self.data, scope='room')['findings']))

    def test_scope_is_explicit_and_keeps_context_evidence(self):
        room = review_model(self.data, scope='room')
        dwelling = review_model(self.data)
        self.assertTrue(any(f['rule'] == 'SAN-01' for f in dwelling['findings']))
        self.assertTrue(any(f['rule'] == 'SAN-01' for f in room['context_findings']))
        self.assertFalse(any(f['rule'] == 'SAN-01' for f in room['findings']))

    def test_units_and_unrecoverable_rotation_fail_closed(self):
        bad = copy.deepcopy(self.data)
        bad['units'] = 'feet'
        with self.assertRaises(SpecError):
            convert(bad)
        self.item('FN-CHR')['rotation'] = 45
        with self.assertRaises(SpecError):
            convert(self.data)

    def test_larger_measured_bed_is_not_replaced_by_catalogue(self):
        self.item('FN-BED')['size_mm'][0] = 2100
        result = review_model(self.data, scope='room')
        self.assertTrue(any(f['rule'] in ('FURN-02', 'FURN-03')
                            for f in result['findings']))


if __name__ == '__main__':
    unittest.main()
