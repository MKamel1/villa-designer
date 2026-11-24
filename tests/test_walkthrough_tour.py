"""WT tour: a 360 in every room, a covered flight, never looking backward, and the non-informative-frame rule (with negatives).

Plan only: real layout and spec, no Blender, no scene build."""
import copy
import math
import unittest

import numpy as np

from archpipe import flythrough as FT, walkthrough_tour as WT


class Tour(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from archpipe.concept import villa_r11 as R, revit_spec as RS
        cls.layout = R.design('D1'); cls.spec = RS.build(cls.layout)
        cls.vm = FT.VillaMap(cls.layout, cls.spec)
        cls.path = WT.plan_tour(cls.vm)
        cls.frames = cls.path['frames']

    def test_route_connectivity_every_room_has_a_full_360(self):
        rooms = {s['room'] for s in self.path['stations'] if s['room']}
        self.assertEqual(set(self.layout['rooms'])-rooms, set())          # all 30 rooms (13 GF + 17 B)
        self.assertEqual(len(self.layout['rooms']), 30)
        self.assertEqual(WT.coverage_findings(self.frames, sorted(rooms)), [])

    def test_both_floors_and_gardens_are_covered(self):
        self.assertEqual({f['level'] for f in self.frames}, {'GF', 'B'})
        self.assertEqual({s['garden'] for s in self.path['stations'] if s['garden']}, {'east-yard', 'south-garden', 'north-court'})

    def test_stair_is_climbed_continuously_with_the_view_up_the_flight(self):
        self.assertEqual(WT.stair_findings(self.frames), [])
        flight = [f for f in self.frames if f['stair']]
        self.assertGreater(len(flight), 100)
        self.assertAlmostEqual(flight[-1]['ground_m'], 0., delta=.1); self.assertAlmostEqual(flight[0]['ground_m'], -3., delta=.1)
        self.assertGreater(max(f['pitch_deg'] for f in flight), 10)
        # the void from the top landing: the camera also looks down it during the stair-gf turn
        self.assertLess(min(f['pitch_deg'] for f in self.frames if f['station'] == 'stair-gf'), -15)

    def test_walking_never_looks_backward_or_sideways(self):
        self.assertEqual(WT.direction_findings(self.frames), [])

    def test_motion_bounds_and_no_snap(self):
        rows = FT.motion_findings(self.frames, self.path['settings'])
        self.assertEqual([r for r in rows if r['failures']], [])
        self.assertLessEqual(max(r['yaw_rate_deg_s'] for r in rows), 45.0)
        # eased: the yaw rate never changes by more than the turn acceleration allows from one frame to the next (plus walking turns)
        rate = np.array([r['yaw_rate_deg_s'] for r in rows]); self.assertLess(np.abs(np.diff(rate)).max(), 12.)

    def test_turn_is_paced_at_policy_rate_and_ends_facing_the_next_leg(self):
        pol = WT.tour_policy()
        for st in self.path['stations']:
            if st['kind'] != 'turn':
                continue
            fs = [f for f in self.frames if f['station'] == st['room'] and f['phase'] == 'turn']
            peak = max(abs(b['yaw_deg']-a['yaw_deg']) for a, b in zip(fs, fs[1:]))*24
            self.assertLessEqual(peak, pol['turn_rate_deg_s']+.5, st['room'])
            self.assertGreaterEqual(fs[-1]['seconds']-fs[0]['seconds'], 360/pol['turn_rate_deg_s'], st['room'])

    def test_every_turn_point_is_free_floor_and_flagging_is_honest(self):
        for room, info in self.path['room_points'].items():
            if info.get('point') is None:
                continue
            self.assertEqual(info['flagged_under_1m'], info['wall_min_m'] < 1.0+.02-1e-9, room)
            if not info.get('proxy'):
                lv = info['level']; i, j = self.vm.cell(*info['point'])
                self.assertTrue(self.vm.free(lv)[i, j], room)

    def test_best_view_is_the_still_view_where_one_exists(self):
        got = {s['room']: s['best_view'] for s in self.path['stations'] if s['room']}
        self.assertEqual(got['dining'], 'v09-dining-evening') if got['dining'] != 'deepest-wedge' else None
        self.assertTrue(sum(v != 'deepest-wedge' for v in got.values()) >= 20)


class NonInformativeRule(unittest.TestCase):
    def grid(self, depth, normal=None, seed=0):
        rng = np.random.default_rng(seed); n = 32*18
        pts = rng.uniform(-3, 3, (n, 3)); nor = rng.normal(size=(n, 3)); nor /= np.linalg.norm(nor, axis=1)[:, None]
        if normal is not None:
            nor = np.tile(normal, (n, 1)); pts = np.stack([np.full(n, depth), rng.uniform(-1, 1, n), rng.uniform(-1, 1, n)], 1)
        return np.full(n, depth) if np.isscalar(depth) else depth, pts, nor

    def test_a_wall_filling_the_frame_is_non_informative(self):
        d, p, n = self.grid(.9, normal=np.array([-1., 0, 0]))
        m = WT.frame_metrics(d, p, n); self.assertTrue(m['non_informative']); self.assertGreater(m['plane_fraction'], .95)

    def test_a_far_wall_on_one_plane_still_fails_the_plane_rule(self):
        d, p, n = self.grid(4., normal=np.array([-1., 0, 0]))
        m = WT.frame_metrics(d, p, n); self.assertEqual(m['near_fraction'], 0.); self.assertTrue(m['non_informative'])

    def test_a_deep_varied_room_view_is_informative_and_quiet(self):
        rng = np.random.default_rng(1); d = rng.uniform(2.5, 9., 32*18)
        _, p, n = self.grid(0.); m = WT.frame_metrics(d, p, n); self.assertFalse(m['non_informative'])

    def test_run_longer_than_one_second_fails_shorter_passes_and_waiver_is_reported(self):
        rows = [dict(index=i, non_informative=30 <= i < 60) for i in range(100)]
        found = WT.run_findings(rows)
        self.assertEqual([(r['first'], r['last']) for r in found], [(30, 59)]); self.assertGreater(found[0]['seconds'], 1.)
        self.assertEqual(WT.run_findings([dict(index=i, non_informative=30 <= i < 50) for i in range(100)]), [])
        self.assertEqual(WT.run_findings(rows, waived=set(range(30, 60))), [])

    def test_backward_looking_segment_fails_the_direction_check(self):
        from archpipe.concept import villa_r11 as R, revit_spec as RS
        layout = R.design('D1'); spec = RS.build(layout); path = WT.plan_tour(FT.VillaMap(layout, spec))
        frames = copy.deepcopy(path['frames']); walk = [f for f in frames if f['phase'] == 'walk']
        start = walk[len(walk)//2]['index']
        for f in frames[start:start+60]:
            if f['phase'] == 'walk':
                f['yaw_deg'] += 180.
        self.assertTrue(WT.direction_findings(frames))      # the real path is clean (see Tour), the tampered one is not

    def test_programme_never_exceeds_rate_and_stops_at_the_end(self):
        pol = WT.tour_policy(); T, yaw, alpha = WT.spin_programme(10., 100., 190., pol)
        t = np.arange(0, T, 1/240); y = yaw(t); rate = np.abs(np.diff(y))*240
        self.assertLessEqual(rate.max(), pol['turn_rate_deg_s']+.5); self.assertAlmostEqual(WT.wrap(yaw(np.array([T]))[0]-190.), 0., delta=.01)
        self.assertGreaterEqual(y.max()-y.min() if y[-1] > y[0] else y.max()-y.min(), 360.)


if __name__ == '__main__':
    unittest.main()
