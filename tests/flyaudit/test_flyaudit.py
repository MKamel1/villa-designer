"""Positive and negative cases for the walkthrough audit, on a synthetic 6 x 4 x 2.7 m room (no scene file needed)."""
import math, unittest
import numpy as np
from archpipe.flyaudit import core
from archpipe.flyaudit.geometry import Geometry

TH = core.thresholds()
ROOMS = {'hall': dict(level='GF', rect=[0, 0, 6, 4])}
SETTINGS = dict(fps=24, final_resolution=[1920, 1080])


def box_tris(lo, hi):
    x0, y0, z0 = lo; x1, y1, z1 = hi
    c = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    q = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return [[c[a], c[b], c[d]] for a, b, cc, e in q for (a, b, d) in ((a, b, cc), (a, cc, e))]


def room_geometry():
    tris, elem, names = [], [], ['wall-n', 'wall-s', 'wall-w', 'wall-e', 'floor-x']
    for e, (lo, hi) in enumerate([((0, 3.9, 0), (6, 4, 2.7)), ((0, 0, 0), (6, .1, 2.7)), ((0, 0, 0), (.1, 4, 2.7)),
                                  ((5.9, 0, 0), (6, 4, 2.7)), ((0, 0, -.1), (6, 4, 0))]):
        t = box_tris(lo, hi); tris += t; elem += [e] * len(t)
    n = len(tris)
    return Geometry(np.array(tris, np.float32), np.array(elem, np.int32), np.zeros(n, np.int32), np.zeros(n, np.int8),
                    np.zeros(n, np.int8), names, [''])


def frame(i, pos, yaw_deg, level='GF'):
    y = math.radians(yaw_deg); p = list(pos)
    return dict(index=i, level=level, stair=False, segment='interior', room='hall',
                camera=dict(position=p, target=[p[0] + math.cos(y), p[1] + math.sin(y), p[2]], lens_mm=24, sensor_mm=36))


def audit(frames):
    g = room_geometry()
    recs, st, _ = core.analyse_frames(g, frames, SETTINGS, ROOMS, TH)
    core.classify(recs, TH, set())
    return recs, st, g


class FrameTests(unittest.TestCase):
    def test_facing_wall_at_half_metre_is_wall_dominated(self):
        recs, _, _ = audit([frame(0, (3, 3.4, 1.35), 90)])           # north wall face is at y = 3.9
        self.assertEqual(recs[0]['cat'], 'wall_dominated', recs[0])
        self.assertGreaterEqual(recs[0]['near_share'], .5)

    def test_backward_frame_is_flagged(self):
        fr = [frame(i, (1 + i * .05, 2, 1.35), 180) for i in range(120)]   # walks +x while looking -x
        recs, _, _ = audit(fr)
        mid = [r for r in recs if 20 < r['i'] < 100]
        self.assertTrue(all(r['cat'] == 'backward' for r in mid), {r['cat'] for r in mid})

    def test_forward_walk_is_not_backward(self):
        fr = [frame(i, (1 + i * .03, 2, 1.35), 0) for i in range(120)]
        recs, _, _ = audit(fr)
        self.assertFalse(any(r['cat'] == 'backward' for r in recs))

    def test_middle_of_room_looking_across_passes(self):
        recs, st, g = audit([frame(0, (1, 2, 1.35), 0)])               # 4.9 m to the east wall
        self.assertEqual(recs[0]['cat'], 'informative', recs[0])
        self.assertGreater(st['frames'][g.elem_names.index('wall-e')], 0)

    def test_stationary_frames_are_never_backward(self):
        recs, _, _ = audit([frame(i, (1, 2, 1.35), 0) for i in range(40)])
        self.assertFalse(any(r['cat'] == 'backward' for r in recs))

    def test_close_obstruction_in_centre_is_blocked(self):
        g = room_geometry()
        t = box_tris((2.7, 1.2, 0), (2.9, 2.8, 2.7))                    # a wardrobe 0.5 m in front of the camera
        n = len(g.tris)
        g2 = Geometry(np.concatenate([g.tris, np.array(t, np.float32)]), np.concatenate([g.elem, np.full(len(t), 5, np.int32)]),
                      np.zeros(n + len(t), np.int32), np.zeros(n + len(t), np.int8), np.zeros(n + len(t), np.int8), g.elem_names + ['pillar'], [''])
        recs, _, _ = core.analyse_frames(g2, [frame(0, (2.2, 2, 1.35), 0)], SETTINGS, ROOMS, TH)
        core.classify(recs, TH, set())
        self.assertEqual(recs[0]['cat'], 'blocked')


class ThreeSixtyTests(unittest.TestCase):
    def spin(self, degrees, n=240):
        fr = [frame(i, (3, 2, 1.35), degrees * i / n) for i in range(n)]
        recs, _, _ = audit(fr)
        return core.full_360(recs, 'hall', TH, 24, 2)

    def test_full_turn_from_the_centre_counts(self):
        r = self.spin(360)
        self.assertTrue(r['full'], r)

    def test_half_turn_does_not_count(self):
        r = self.spin(150)
        self.assertFalse(r['full'], r)

    def test_two_far_apart_half_turns_do_not_add_up(self):
        fr = [frame(i, (1, 2, 1.35), 180 * i / 60) for i in range(60)] + [frame(60 + i, (5, 2, 1.35), 180 + 180 * i / 60) for i in range(60)]
        recs, _, _ = audit(fr)
        self.assertFalse(core.full_360(recs, 'hall', TH, 24, 2)['full'])


class RunTests(unittest.TestCase):
    def test_run_over_one_second_is_reported_but_short_one_is_not(self):
        mk = lambda i, c: dict(i=i, cat=c, room='hall', level='GF')
        recs = [mk(i, 'wall_dominated' if 10 <= i < 60 else 'informative') for i in range(0, 200, 2)]
        self.assertEqual(len(core.runs(recs, 24, 2, 1.0)), 1)
        short = [mk(i, 'wall_dominated' if 10 <= i < 30 else 'informative') for i in range(0, 200, 2)]
        self.assertEqual(core.runs(short, 24, 2, 1.0), [])


if __name__ == '__main__':
    unittest.main()


class OldRouteRegression(unittest.TestCase):
    """Real reproduction: frames the lead called wall (contact sheet of the first villa preview) must stay flagged."""
    def test_by_eye_wall_frames_are_flagged_and_good_ones_are_not(self):
        import json
        p = core.ROOT / 'knowledge/flyaudit/villa-route-wt-villa3/frames.json'
        if not p.exists():
            self.skipTest('no committed audit of the old route')
        by = {r['i']: r for r in json.loads(p.read_text())}
        bad = {540, 720, 810, 900, 990, 1080, 1170, 1620, 1710, 1980, 2430, 2700}
        good = {0, 180, 270, 1350, 1440, 1530, 1890, 2340, 2610, 2970, 3060}
        ok = lambda i: by.get(i) or by[i + 1]
        self.assertEqual([i for i in sorted(bad) if ok(i)['cat'] == 'informative'], [])
        self.assertEqual([i for i in sorted(good) if ok(i)['cat'] != 'informative'], [])
