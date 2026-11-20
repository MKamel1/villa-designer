"""Walk2 authored motion and room coverage, retaining the frozen v1 route.

Frames are zero-indexed. Positions and distances are metres; time is seconds;
yaw is degrees anticlockwise from the model's positive x axis.
"""
from copy import deepcopy
import json
import math
from pathlib import Path
import unittest

from archpipe import flythrough as W
from archpipe.concept import villa_r11

ROOT = Path(__file__).resolve().parents[1]


class Walk2Route(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.route = json.loads((ROOT/'knowledge/walk2-route.json').read_text())
        cls.settings = deepcopy(json.loads((ROOT/'knowledge/flythrough-policy.json').read_text()))
        cls.settings.update(fps=30, frames=2250, duration_seconds=75)
        cls.path = W.walking_path(cls.route['points_m'], cls.route['yaw_knots'],
                                 cls.settings, travel_seconds=cls.route['travel_seconds'])

    def test_longer_clip_keeps_registered_speed_yaw_and_level_rules(self):
        self.assertEqual(len(self.path['frames']), 2250)
        self.assertEqual(self.path['frames'][-1]['seconds'], 2249/30)
        self.assertEqual(self.route['level'], 'B')
        self.assertEqual(self.settings['maximum_speed_m_s'], .8)
        self.assertEqual(self.settings['maximum_yaw_rate_deg_s'], 20)
        self.assertFalse(any(r['failures'] for r in W.motion_findings(
            self.path['frames'], self.settings)))
        for f in self.path['frames']:
            self.assertAlmostEqual(f['camera']['position'][2], -3+1.35)
            self.assertEqual(f['camera']['position'][2], f['camera']['target'][2])
        self.assertGreater(self.path['distance_m'], W.authored_path()['distance_m']*2)

    def test_real_room_coverage_and_closed_garden_stop(self):
        rooms = villa_r11.design('D1')['rooms']
        occupied = set()
        for frame in self.path['frames']:
            x,y,_ = frame['camera']['position']
            occupied.update(name for name, room in rooms.items() if room['level']=='B'
                            and room['rect'][0]<x<room['rect'][2]
                            and room['rect'][1]<y<room['rect'][3])
        self.assertTrue({'entry-b','kitchen','lounge','hall-b','dining','living'} <= occupied)
        # Stair foot is viewed from the adjacent hall; the actual flight is
        # an obstacle, never a level walking corridor.
        self.assertTrue(any(math.dist(f['camera']['position'],[10.1,-27.7,-1.65])<.01
                            for f in self.path['frames']))
        endpoint=self.path['frames'][-1]['camera']['position']
        self.assertEqual(endpoint,[21.95,-26.13,-1.65])
        self.assertLess(endpoint[0],22.597)  # measured closed garden-pane plane
        stopped=[f for f in self.path['frames'] if f['seconds']>=self.route['travel_seconds']]
        self.assertGreaterEqual(len(stopped),89)
        self.assertTrue(all(f['camera']['position']==endpoint for f in stopped))
        self.assertIn('closed',self.route['closed_threshold_context'].lower())

    def test_subject_periods_cover_each_frame_once_and_name_real_rooms(self):
        periods=self.route['subject_periods']
        rooms=villa_r11.design('D1')['rooms']
        for index in range(self.settings['frames']):
            found=[p for p in periods if p['first_frame']<=index<=p['last_frame']]
            self.assertEqual(len(found),1)
            self.assertTrue(found[0]['subjects'])
        named=set()
        for period in periods:
            for query in period['subjects']:
                if query.startswith('room:'):
                    selected=query.removeprefix('room:').split(',')
                    self.assertTrue(all(r in rooms for r in selected))
                    named.update(selected)
        self.assertTrue({'kitchen','kitchen-island','dining','living','lounge','stair-b','bar-alcove'}<=named)

    def test_south_threshold_tail_preserves_proven_v1_position_yaw_relation(self):
        old_route=json.loads((ROOT/'knowledge/flythrough-route.json').read_text())
        old_settings=json.loads((ROOT/'knowledge/flythrough-policy.json').read_text())
        old=W.walking_path(old_route['points_m'],old_route['yaw_knots'],old_settings,
                           travel_seconds=old_route['travel_seconds'])
        factor=(self.route['travel_seconds']/self.path['distance_m'])/(old['travel_seconds']/old['distance_m'])
        self.assertGreater(factor,1.)
        self.assertEqual(self.route['points_m'][-3:],old_route['points_m'][-3:])
        for new_knot,old_knot in zip(self.path['knots'][-4:-1],old['knots'][-4:-1]):
            self.assertAlmostEqual(new_knot['seconds'],self.route['travel_seconds']+
                                   factor*(old_knot['seconds']-old['travel_seconds']))
        new_yaw=next(k for k in self.route['yaw_knots'] if k['yaw_deg']==260)
        self.assertAlmostEqual(new_yaw['seconds'],self.route['travel_seconds']+
                               factor*(15-old['travel_seconds']))
        self.assertEqual(self.route['yaw_knots'][-2]['yaw_deg'],318)
        self.assertEqual(self.route['yaw_knots'][-2]['seconds'],self.route['travel_seconds'])

    def test_v1_timing_input_is_preserved_by_value(self):
        old=json.loads((ROOT/'knowledge/flythrough-policy.json').read_text())
        self.assertEqual((old['fps'],old['frames'],old['duration_seconds']),(24,720,30))
        route=json.loads((ROOT/'knowledge/flythrough-route.json').read_text())
        self.assertEqual(route['points_m'][0],[15.5,-27.1,-1.65])
        self.assertEqual(route['travel_seconds'],27)


if __name__ == '__main__':
    unittest.main()
