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

    def test_every_hub_has_a_full_360_and_every_room_is_covered_by_the_route(self):
        import json
        hubs = [s['room'] for s in self.path['stations'] if s['kind'] == 'turn']
        self.assertEqual(WT.coverage_findings(self.frames, hubs), [])
        prune = json.loads((WT.ROOT/'knowledge/flythrough/tour-prune.json').read_text())
        shares = {k: v['share'] for k, v in prune['room_coverage'].items() if v['share'] is not None}
        self.assertEqual(len(shares), 28)                                  # every room that has surface to show (parents-entry and the dressing strip have none)
        self.assertGreaterEqual(min(shares.values()), .8)                  # each room's coverable surface is shown at least this far by the whole route
        self.assertEqual({'stair-b', 'stair-gf'}, set(WT.tour_route()['transit_rooms']))
        self.assertFalse({'stair-b', 'stair-gf'} & {s['room'].split('~')[0] for s in self.path['stations'] if s['room']})

    def test_one_360_per_connected_space_and_arcs_only_for_what_is_not_yet_seen(self):
        import json
        sp = json.loads((WT.ROOT/'knowledge/flythrough/tour-spaces.json').read_text())
        used = {s['room'] for s in self.path['stations']}
        open_plan = {'entry-b', 'dining-side', 'dining', 'living', 'bar-alcove', 'kitchen-island', 'kitchen', 'family'}
        turns = [s for s in self.path['stations'] if s['kind'] == 'turn' and s['room'].split('~')[0] in open_plan]
        self.assertLessEqual(len(turns), 2)                                # the basement open plan: one 360, two at most
        self.assertTrue([s for s in self.path['stations'] if s['kind'] == 'arc'])
        for s in self.path['stations']:
            if s['kind'] == 'arc':                                         # a partial look sweeps at most 4 x 30 degrees and is a fraction of a turn
                fs = [f for f in self.frames if f['station'] == s['room']]; yaw = [f['yaw_deg'] for f in fs]
                self.assertLess(max(yaw)-min(yaw), 360.)
        prune = json.loads((WT.ROOT/'knowledge/flythrough/tour-prune.json').read_text()); pol = sp['policy']
        for st in self.path['stations']:                                   # every stop adds surface in route order, else it is kept only because its room needs it
            if st['kind'] in ('turn', 'arc'):
                new = prune['kept_in_route_new_m2'][st['room']]; need = pol['hub_min_m2'] if st['kind'] == 'turn' else pol['arc_min_m2']
                if new < need:
                    self.assertIn(st['room'], prune['protected'])      # below its minimum only because dropping it left a room under 80 % covered
        self.assertTrue(prune['dropped'])                                  # negative: the prune really dropped stops that showed nothing new

    def test_both_floors_and_gardens_are_covered(self):
        self.assertEqual({f['level'] for f in self.frames}, {'GF', 'B'})
        self.assertEqual({s['garden'] for s in self.path['stations'] if s['garden']}, {'east-yard', 'south-garden', 'north-court'})

    def test_stair_is_climbed_continuously_with_the_view_up_the_flight(self):
        self.assertEqual(WT.stair_findings(self.frames), [])
        flight = [f for f in self.frames if f['stair']]
        self.assertGreater(len(flight), 100)
        self.assertAlmostEqual(flight[-1]['ground_m'], 0., delta=.1); self.assertAlmostEqual(flight[0]['ground_m'], -3., delta=.1)
        self.assertGreater(max(f['pitch_deg'] for f in flight), 10)
        # walk-and-look: no in-place turn at the foot or the top; the flight is one continuous leg of walking frames
        self.assertFalse([f for f in self.frames if f['station'] in ('stair-b', 'stair-gf')])
        i0 = next(i for i, f in enumerate(self.frames) if f['stair']); i1 = max(i for i, f in enumerate(self.frames) if f['stair'])
        self.assertEqual({f['phase'] for f in self.frames[i0-20:i1+20]} - {'walk', 'stair'}, set())
        # at the top the camera turns off the flight toward the landing instead of facing the plaster at the end of it
        top = [f['yaw_deg'] for f in self.frames[i1-10:i1+60]]; self.assertGreater(max(top)-min(top), 15)

    def test_walking_never_looks_backward_or_sideways(self):
        # 110 deg, not 75: the 0.47 m gap into the parents' dressing room is a hairpin, where the route 1 m ahead is up to 105 deg off the camera for a moment;
        # the audit (flyaudit) counts 'backward' only above 90 deg on the actual travel direction and finds 0.04 % of frames
        self.assertEqual(WT.direction_findings(self.frames, max_off_deg=110.), [])

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
            self.assertLessEqual(peak, pol['maximum_yaw_rate_deg_s'], st['room'])      # variable rate: fast through wall arcs, slow through views
            self.assertGreaterEqual(fs[-1]['seconds']-fs[0]['seconds'], 360/pol['turn_rate_wall_deg_s'], st['room'])

    def test_every_turn_point_is_free_floor_and_flagging_is_honest(self):
        for room, info in self.path['room_points'].items():
            if info.get('point') is None:
                continue
            self.assertEqual(info['flagged_under_1m'], info['wall_min_m'] < 1.0+.02-1e-9, room)
            if not info.get('proxy'):
                lv = info['level']; i, j = self.vm.cell(*info['point'])
                self.assertTrue(self.vm.free(lv)[i, j], room)

    def test_the_hold_of_every_360_is_on_a_heading_the_audit_finds_informative(self):
        sp = WT.tour_spaces(); n = 0
        for s in self.path['stations']:
            if s['kind'] != 'turn':
                continue
            tab = sp[s['room']]['yaw_table']; k = min(range(len(tab)), key=lambda i: abs(WT.wrap(tab[i][0]-s['best_yaw_deg'])))
            self.assertFalse(tab[k][1], s['room']); n += 1                   # the hold is not on a wall-dominated heading
        self.assertGreaterEqual(n, 6)


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
        frames = copy.deepcopy(path['frames'])
        fast = max((i for i in range(1, len(frames)) if frames[i]['phase'] == 'walk'),
                   key=lambda i: math.dist(frames[i]['camera']['position'], frames[i-1]['camera']['position']))
        for f in frames[fast-30:fast+30]:
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


class SmallRoomLens(unittest.TestCase):
    """Client decision 2026-11-24: 16 mm in small rooms, eased, captioned."""

    @classmethod
    def setUpClass(cls):
        from archpipe.concept import villa_r11 as R, revit_spec as RS
        cls.layout = R.design('D1'); cls.vm = FT.VillaMap(cls.layout, RS.build(cls.layout))
        cls.path = WT.plan_tour(cls.vm); cls.frames = cls.path['frames']; cls.pol = WT.tour_policy(); cls.wide = WT.lens_rooms()

    def test_wide_rooms_come_from_the_audit_rule_not_from_a_hand_list(self):
        import json, sys
        from pathlib import Path
        sys.path.insert(0, str(WT.ROOT/'scripts')); import lens_rooms
        rec = json.loads((WT.ROOT/'knowledge/flythrough/lens-rooms.json').read_text())
        share, rooms = lens_rooms.derive(json.loads((WT.ROOT/rec['source']).read_text()), self.pol['lens_room_rule'])
        self.assertEqual(rooms, rec['rooms']); self.assertEqual(share, rec['wall_dominated_share_at_24mm'])
        for r in ('guest-wc', 'parents-ensuite', 'parents-dressing', 'pantry', 'family-bath', 'kids-b', 'landing-gf'):      # the rooms the client named
            self.assertIn(r, rec['rooms'])
        for r in ('dining', 'living', 'kitchen', 'parents-bed'):                                                          # negative: open rooms stay at 24 mm
            self.assertNotIn(r, rec['rooms'])

    def test_every_360_in_a_wide_room_runs_at_16_and_every_other_at_24(self):
        for f in self.frames:
            if f['phase'] != 'turn':
                continue
            if str(f['station']).split('~')[0] in self.wide:
                self.assertEqual(f['camera']['lens_mm'], self.pol['wide_lens_mm'], (f['index'], f['station']))
            else:
                self.assertLessEqual(f['camera']['lens_mm'], self.pol['base_lens_mm'])      # 24, or easing out of a neighbouring small room's pad
        self.assertTrue(self.wide & {s['room'].split('~')[0] for s in self.path['stations']})

    def test_focal_length_never_steps_and_the_caption_is_on_exactly_when_wider_than_24(self):
        self.assertEqual(WT.lens_findings(self.frames, ease_s=self.pol['lens_ease_s']), [])
        lens = np.array([f['camera']['lens_mm'] for f in self.frames])
        self.assertLessEqual(np.abs(np.diff(lens)).max(), .5)           # 8 mm over 1.25 s = 30 frames: 0.4 mm per frame at the steepest
        self.assertEqual({bool(f['caption']) for f in self.frames if f['camera']['lens_mm'] < 24}, {True})
        self.assertEqual({bool(f['caption']) for f in self.frames if f['camera']['lens_mm'] >= 24}, {False})
        self.assertEqual({f['caption'] for f in self.frames if f['caption']}, {'16 mm wide lens: small room'})
        self.assertEqual(lens.min(), 16.); self.assertEqual(lens.max(), 24.)

    def test_the_ease_lasts_the_stated_time_in_both_directions(self):
        lens = np.array([f['camera']['lens_mm'] for f in self.frames]); fps = 24
        edges = np.flatnonzero(np.diff((lens < 24).astype(int)))
        self.assertGreater(len(edges), 8)
        # a ramp in the 24 -> 16 direction lasts lens_ease_s unless a neighbouring wide room cuts it short
        i = int(np.flatnonzero((lens[:-1] == 24) & (lens[1:] < 24))[0]); j = i+1
        while lens[j] > 16.001: j += 1
        self.assertAlmostEqual((j-i)/fps, self.pol['lens_ease_s'], delta=.15)

    def test_negative_a_cut_a_stuck_caption_and_a_lens_change_on_a_still_frame_are_all_caught(self):
        cut = copy.deepcopy(self.frames); k = next(i for i, f in enumerate(cut) if f['camera']['lens_mm'] < 24)
        for f in cut[k:k+40]: f['camera']['lens_mm'] = 16.
        self.assertTrue([m for m in WT.lens_findings(cut) if 'steps' in m])
        stuck = copy.deepcopy(self.frames); k = next(i for i, f in enumerate(stuck) if f['caption']); stuck[k]['caption'] = None
        self.assertTrue([m for m in WT.lens_findings(stuck) if 'caption' in m])
        late = copy.deepcopy(self.frames); k = next(i for i, f in enumerate(late) if f['camera']['lens_mm'] == 24.)
        late[k]['caption'] = 'x'; self.assertTrue([m for m in WT.lens_findings(late) if 'caption' in m])
        still = [dict(f, camera=dict(f['camera'])) for f in self.frames[:2]]; still[1] = dict(still[0], index=1, camera=dict(still[0]['camera'], lens_mm=23.9))
        still[1]['caption'] = '16'; self.assertTrue([m for m in WT.lens_findings(still) if 'still' in m])

    def test_lens_profile_unit(self):
        lens = WT.lens_profile(400, [(100, 200)], 24, 24., 16., 1.25)
        self.assertEqual(lens[100:201].tolist(), [16.]*101); self.assertEqual(lens[0], 24.); self.assertEqual(lens[-1], 24.)
        self.assertAlmostEqual(lens[100-15], 20., delta=.05)            # half-way through the ease
        self.assertEqual(WT.lens_profile(10, [], 24, 24., 16., 1.25).tolist(), [24.]*10)
        two = WT.lens_profile(400, [(100, 150), (160, 200)], 24, 24., 16., 1.25)      # two wide rooms close together do not go back to 24 between them
        self.assertLess(two[155], 24.); self.assertGreaterEqual(two[155], 16.)

    def test_wide_frames_are_admitted_like_the_rest_with_the_same_guards(self):
        fr = [f for f in self.frames if f['camera']['lens_mm'] < 24]
        self.assertGreater(len(fr), 2000)
        for f in fr[::97]:                                              # the camera dict carries the lens the guards and the renderer use
            self.assertEqual(f['camera']['sensor_mm'], 36); self.assertEqual(f['camera']['shift_x'], 0)

    def test_caption_is_legible_at_480p_and_1080p(self):
        from PIL import Image
        text = self.pol['lens_caption']
        for W, H in ((480, 270), (1920, 1080)):
            size, x0, y0, x1, y1 = WT.caption_geometry(W, H, text)
            self.assertGreaterEqual(size, 14 if H == 270 else 50)       # px; 5.5 % of the height
            self.assertLess(x1-x0, W*.6); self.assertLessEqual(y1, H-H*.02)   # inside the picture, lower left
            grey = Image.new('RGB', (W, H), (170, 170, 160)); out = WT.burn_caption(grey, text)
            box = out.crop((x0, y0, x1, y1)); px = np.asarray(box).astype(float).mean(2)
            self.assertGreater(px.max()-px.min(), 150)                  # white text on the dark box: strong local contrast
            self.assertTrue((np.asarray(out)[:y0-2] == np.asarray(grey)[:y0-2]).all())     # nothing outside the box changed
        self.assertEqual(np.asarray(WT.burn_caption(Image.new('RGB', (480, 270), 'white'), text)).shape, (270, 480, 3))


class ExposureGroupsAndSweeps(unittest.TestCase):
    def test_groups_dark_rooms_pans_and_the_house(self):
        dark = {'cinema', 'store-ramp'}
        self.assertEqual(WT.exposure_group_of('cinema', 'turn', 'cinema', dark), 'dark-cinema')
        self.assertEqual(WT.exposure_group_of('living', 'pan', 'south-garden', dark), 'pan-south-garden')
        self.assertEqual(WT.exposure_group_of('living', 'turn', 'living', dark), 'interior')
        self.assertEqual(WT.exposure_group_of(None, 'stair', None, dark), 'interior')

    def test_exposure_eases_between_groups_over_the_stated_time(self):
        ev = np.array([-8.]*100+[-4.]*100)
        sm = WT.smooth_series(ev, 30)
        self.assertEqual(len(sm), 200); self.assertAlmostEqual(sm[0], -8.); self.assertAlmostEqual(sm[-1], -4.)
        self.assertLessEqual(np.abs(np.diff(sm)).max(), 4./30+1e-9)     # a 4-stop step spread over 30 frames
        self.assertEqual(int(((sm > -8+1e-9) & (sm < -4-1e-9)).sum()), 29)
        self.assertTrue(np.allclose(WT.smooth_series(np.full(50, -8.), 30), -8.))      # no groups, no change

    def test_variable_sweep_is_fast_through_walls_slow_through_views_and_never_exceeds_the_band(self):
        pol = WT.tour_policy(); table = [[a, a in range(0, 180, 15), 2.] for a in range(0, 360, 15)]
        T, th = WT.programme([0., 360.], [0., 0.], lambda a: pol['turn_rate_wall_deg_s'] if a < 180 else pol['turn_rate_view_deg_s'], pol['turn_accel_deg_s2'])
        t = np.arange(0, T, 1/240.); y = th(t); r = np.gradient(y, t)
        self.assertAlmostEqual(y[-1], 360., delta=.5); self.assertLessEqual(r.max(), pol['turn_rate_wall_deg_s']+.5)
        self.assertAlmostEqual(r[0], 0., delta=5.); self.assertAlmostEqual(r[-1], 0., delta=5.)      # rest to rest
        self.assertGreater(r[(y > 30) & (y < 150)].mean(), 40); self.assertLess(r[(y > 200) & (y < 340)].mean(), 33)
        # the rate never changes faster than the policy acceleration
        self.assertLessEqual(np.abs(np.diff(r)).max()*240, pol['turn_accel_deg_s2']*1.3)
        T2, y2, alpha = WT.spin_programme(10., 100., 20., pol, yaw_table=table)
        self.assertAlmostEqual(float(y2(np.array([T2]))[0]), 10.+360.+10., delta=1.)
