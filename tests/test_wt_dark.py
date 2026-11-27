"""scripts/wt_dark.py: runs of near-black lookdev frames (revision 8 guard)."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import wt_dark as D


class Runs(unittest.TestCase):
    def test_a_black_stretch_of_a_second_or_more_is_reported_with_its_extent(self):
        v = {i: 80. for i in range(0, 40, 2)}; v.update({i: 2. for i in range(10, 36, 2)})      # 26 frames of route = 1.08 s
        self.assertEqual(D.runs(v, 2), [(10, 34, (34-10+2)/24)])

    def test_negatives_a_short_dark_dip_a_dim_but_lit_room_and_a_gap_do_not_count(self):
        short = {i: 80. for i in range(0, 40, 2)}; short.update({i: 2. for i in range(10, 22, 2)})
        self.assertEqual(D.runs(short, 2), [])                                              # 0.5 s
        dim = {i: 30. for i in range(0, 80, 2)}                                              # the amber pantry reads 30+: lit, not black
        self.assertEqual(D.runs(dim, 2), [])
        gap = {i: 2. for i in range(0, 12, 2)}; gap.update({i: 2. for i in range(40, 52, 2)})   # two dark pieces with unrendered frames between are not one run
        self.assertEqual(D.runs(gap, 2), [])


if __name__ == '__main__':
    unittest.main()
