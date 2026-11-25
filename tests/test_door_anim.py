"""Door-leaf animation (client 2026-11-25): a leaf that hides a feature closes (eased, ~2 s) after the camera is in, holds, and reopens before the camera leaves.

Unit and synthetic cases run anywhere; the route-level cases need out/wt/villa4/boxes.json (the obstacle boxes dumped from the scene build) and are skipped without it."""
import copy
import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np

from archpipe import door_anim as DA, flythrough as FT, walkthrough_tour as WT
from archpipe.flyaudit import core
from archpipe.flyaudit.doorblock import door_blocked
from archpipe.flyaudit.geometry import Geometry

ROOT = Path(__file__).resolve().parents[1]
BOXES = ROOT/'out/wt/villa4/boxes.json'
TH = core.thresholds()


def box(lo, hi):
    x0, y0, z0 = lo; x1, y1, z1 = hi
    c = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    q = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return [[c[a], c[b], c[d]] for a, b, cc, e in q for (a, b, d) in ((a, b, cc), (a, cc, e))]


# a 6 x 4 m room; the door leaf is 2 m long, 0.1 m thick, 2.1 m high. Closed it lies in the north wall plane (y = 3.9, x 2..4); hinge (2, 3.9), signed_open -90
# swings it into the room along x = 2 (y 3.9 -> 1.9), where it stands between a camera at x = 0.8 and a chest at x = 5.
LEAF = dict(element='door-GF-hall-x', leaf_id='door-leaf-test', hinge=[2.0, 3.9], signed_open_deg=-90.0,
            closed_faces=[[list(v) for v in t] for t in box((2, 3.85, 0), (4, 3.95, 2.1))])


def geometry():
    parts = [('wall-s', (0, 0, 0), (6, .1, 2.7), 0), ('wall-n', (0, 3.9, 0), (6, 4, 2.7), 0), ('wall-w', (0, 0, 0), (.1, 4, 2.7), 0), ('wall-e', (5.9, 0, 0), (6, 4, 2.7), 0),
             ('floor-x', (0, 0, -.1), (6, 4, 0), 0), ('furn-chest', (4.5, 2.2, 0), (5.5, 2.8, 1.0), 4)]
    tris, elem, grp, names = [], [], [], []
    for e, (n, lo, hi, g) in enumerate(parts):
        t = box(lo, hi); tris += t; elem += [e]*len(t); grp += [g]*len(t); names.append(n)
    # the leaf as the scene is built: baked OPEN (closed pose rotated -90 deg about the hinge)
    e = len(names); names.append(LEAF['element']); psi = math.radians(LEAF['signed_open_deg']); c, s = math.cos(psi), math.sin(psi); h = LEAF['hinge']
    for t in LEAF['closed_faces']:
        tris.append([[h[0]+(v[0]-h[0])*c-(v[1]-h[1])*s, h[1]+(v[0]-h[0])*s+(v[1]-h[1])*c, v[2]] for v in t]); elem.append(e); grp.append(0)
    n = len(tris)
    return Geometry(np.array(tris, np.float32), np.array(elem, np.int32), np.zeros(n, np.int32), np.zeros(n, np.int8), np.array(grp, np.int8), names, [''])


def frames(n, state=None):
    out = []
    for i in range(n):
        f = dict(index=i, level='GF', stair=False, camera=dict(position=[.8, 2.5, .8], target=[5., 2.5, .8], lens_mm=24, sensor_mm=36))
        if state is not None:
            f['doors'] = {LEAF['element']: state}
        out.append(f)
    return out


class Series(unittest.TestCase):
    SCH = dict(close_start=10, close_end=58, open_start=100, open_end=148)

    def test_open_eased_closed_held_and_open_again_in_two_seconds_each_way(self):
        s = DA.state_series(self.SCH, 200)
        self.assertEqual(s[0], 1.); self.assertEqual(s[199], 1.)
        self.assertEqual(s[58], 0.); self.assertEqual(s[100], 0.)
        self.assertTrue(np.all(s[58:101] == 0.))
        self.assertEqual((self.SCH['close_end']-self.SCH['close_start'])/24, 2.0)
        self.assertTrue(np.all(np.diff(s[10:59]) <= 1e-12) and np.all(np.diff(s[100:149]) >= -1e-12))     # monotone down, then up
        # eased: the first and last frames of a swing move far less than the middle (smoothstep), so there is no snap
        step = np.abs(np.diff(s)); self.assertLess(step[10], .2*step[34]); self.assertLess(step[57], .2*step[34])
        self.assertLess(step.max(), .05)

    def test_negative_a_linear_or_instant_close_would_fail_the_easing_check(self):
        lin = np.clip(1-(np.arange(200)-10)/48., 0, 1)
        self.assertGreater(np.abs(np.diff(lin))[10], .5*np.abs(np.diff(lin))[34])

    def test_pivot_transform_is_identity_open_and_maps_the_open_leaf_back_onto_the_closed_one(self):
        psi, t = DA.pivot_transform(LEAF, 1.); self.assertEqual((psi, t), (0., (0., 0.)))
        psi, (tx, ty) = DA.pivot_transform(LEAF, 0.); c, s = math.cos(psi), math.sin(psi)
        h = LEAF['hinge']; psi0 = math.radians(LEAF['signed_open_deg']); c0, s0 = math.cos(psi0), math.sin(psi0)
        for face in LEAF['closed_faces']:
            for v in face:
                o = [h[0]+(v[0]-h[0])*c0-(v[1]-h[1])*s0, h[1]+(v[0]-h[0])*s0+(v[1]-h[1])*c0]       # the open pose the scene is built in
                back = [c*o[0]-s*o[1]+tx, s*o[0]+c*o[1]+ty]
                self.assertAlmostEqual(back[0], v[0], 9); self.assertAlmostEqual(back[1], v[1], 9)


class Clearance(unittest.TestCase):
    def path(self, cam):
        return dict(door_anim=[LEAF], frames=[dict(index=0, camera=dict(position=cam), doors={LEAF['element']: 0.0})])

    def test_camera_near_a_closing_leaf_is_found_and_far_is_quiet(self):
        self.assertEqual(DA.clearance_findings(self.path([3., 3.2, 1.35]), .3), [])                           # 0.65 m south of the closed leaf is fine
        self.assertEqual(DA.clearance_findings(self.path([3., 3.6, 1.35]), .3)[0][1], LEAF['element'])       # 0.25 m is not
        self.assertEqual(DA.clearance_findings(self.path([3., 3.9, 1.35]), .3)[0][2], 0.)                     # standing in the leaf is not

    def test_the_distance_follows_the_leaf_as_it_swings(self):
        self.assertAlmostEqual(DA.distance_to_leaf(LEAF, 0., (3., 3.5)), .35, 6)
        self.assertAlmostEqual(DA.distance_to_leaf(LEAF, 1., (2.5, 2.9)), .45, 6)        # open: the leaf stands on x = 2, 0.05 thick each side
        self.assertGreater(DA.distance_to_leaf(LEAF, 1., (3., 3.5)), .9)


class Audit(unittest.TestCase):
    def setUp(self):
        self.g = geometry(); self.et = core.element_table(self.g); self.rooms = {'hall': dict(level='GF', rect=[0, 0, 6, 4])}
        self.ga = self.g.animate([LEAF])

    def hit(self, g, state):
        d, t, _, _ = g.cast(np.array([[.8, 2.5, .8]]), np.array([[1., 0., 0.]]), doors={LEAF['element']: state} if state is not None else None)
        return g.elem_names[g.tri_elem(t)[0]]

    def test_the_leaf_is_cast_at_its_per_frame_state_and_never_removed(self):
        self.assertEqual(self.hit(self.g, None), LEAF['element'])             # as built (open) it stands in the sight line
        self.assertEqual(self.hit(self.ga, 1.), LEAF['element'])              # animated copy, open: same hit
        self.assertEqual(self.hit(self.ga, 0.), 'furn-chest')                 # closed: the chest behind it is hit
        mid = self.hit(self.ga, .5); self.assertIn(mid, (LEAF['element'], 'furn-chest'))
        self.assertIn(LEAF['element'], self.ga.elem_names)

    def test_a_blocked_feature_becomes_visible_when_the_leaf_closes(self):
        open_ = door_blocked(self.ga, frames(8, 1.), self.rooms, self.et, TH, [LEAF])
        closed = door_blocked(self.ga, frames(8, 0.), self.rooms, self.et, TH, [LEAF])
        self.assertEqual([x['feature'] for x in open_['blocked']], ['furn-chest'])          # open: in view, hidden by the leaf, never seen
        self.assertEqual(open_['blocked'][0]['door'], LEAF['element']); self.assertTrue(open_['blocked'][0]['animated'])
        self.assertEqual(closed['blocked'], []); self.assertEqual(closed['partly'], [])      # closed: nothing hidden by a door leaf
        self.assertEqual(open_['blocked_features'], 1); self.assertEqual(closed['blocked_features'], 0)

    def test_negative_a_feature_no_door_hides_is_not_reported(self):
        fr = frames(8, 1.)
        for f in fr: f['camera'].update(position=[.8, 1.0, .8], target=[5., 1.0, .8])       # looking along the south wall: nothing in view
        self.assertEqual(door_blocked(self.ga, fr, self.rooms, self.et, TH, [LEAF])['blocked'], [])


class Scene(unittest.TestCase):
    def build(self):
        el = LEAF['element']
        leaf = dict(id=LEAF['leaf_id'], part_kind='door-leaf', group='shell', material='door-oak', element_ids=[el], faces=[[list(v) for v in tri] for tri in box((2, 3.85, 0), (4, 3.95, 2.1))])
        handle = dict(id='detail-door-handles', part_kind='door-handle', group='fixture', material='brass', faces=[[[2.1+i, 3.8, 1.0], [2.2+i, 3.8, 1.0], [2.2+i, 3.8, 1.1]] for i in range(4)],
                      faces_by_element={el: [0, 1], 'door-GF-other': [2, 3]}, element_ids=[el, 'door-GF-other'])
        return dict(meshes=[leaf, handle])

    def test_open_interior_doors_turns_the_leaf_and_splits_its_handle_never_hides_anything(self):
        from archpipe.concept import villa_r11 as R, revit_spec as RS
        layout = R.design('D1'); vm = FT.VillaMap(layout, RS.build(layout)); scene = self.build(); closed = copy.deepcopy(scene['meshes'][0]['faces'])
        report = FT.open_interior_doors(scene, vm, [], door_anim=[LEAF])
        leaf = next(m for m in scene['meshes'] if m['id'] == LEAF['leaf_id'])
        self.assertEqual(len(leaf['faces']), len(closed)); self.assertFalse(leaf.get('hidden') or leaf.get('hide'))
        self.assertTrue(report[0]['animated']); self.assertEqual((report[0]['angle_deg'], report[0]['swing_sign']), (90.0, -1))
        h = LEAF['hinge']; c, s = 0., -1.                                          # R(-90 deg)
        for fo, fc in zip(leaf['faces'], closed):
            for vo, vc in zip(fo, fc):
                self.assertAlmostEqual(vo[0], h[0]+(vc[0]-h[0])*c-(vc[1]-h[1])*s, 9); self.assertAlmostEqual(vo[1], h[1]+(vc[0]-h[0])*s+(vc[1]-h[1])*c, 9)
        ids = [m['id'] for m in scene['meshes']]; self.assertIn('door-handle-'+LEAF['element'], ids)
        own = next(m for m in scene['meshes'] if m['id'] == 'door-handle-'+LEAF['element']); rest = next(m for m in scene['meshes'] if m['id'] == 'detail-door-handles')
        self.assertEqual((len(own['faces']), len(rest['faces'])), (2, 2))          # the handle moved with the leaf; the other door's handle stayed
        self.assertEqual(rest['element_ids'], ['door-GF-other']); self.assertEqual(rest['faces_by_element'], {'door-GF-other': [0, 1]})


@unittest.skipUnless(BOXES.is_file(), 'needs out/wt/villa4/boxes.json (the scene build dumps it)')
class Route(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(ROOT/'scripts'))
        from wt_plan import vmap
        cls.layout, cls.spec, cls.vm = vmap(); cls.path = WT.plan_tour(cls.vm); cls.spec_doors = WT.tour_doors()

    def test_the_client_example_is_animated_the_parents_dressing_wardrobe_behind_its_door(self):
        doors = {d['record']['element']: d for d in self.spec_doors['doors']}
        self.assertIn('furn-pd-hang-2', doors['door-GF-parents-dressing-ext-parents-ensuite']['features'])
        self.assertEqual({r['element'] for r in self.path['door_anim']}, set(doors))

    def test_every_animated_leaf_starts_and_ends_open_closes_fully_and_holds(self):
        for rec in self.path['door_anim']:
            s = [f.get('doors', {}).get(rec['element'], 1.) for f in self.path['frames']]; sch = rec['schedule']
            self.assertEqual((s[0], s[-1]), (1., 1.)); self.assertEqual(min(s), 0.)
            self.assertGreaterEqual((sch['open_start']-sch['close_end'])/24, 1.0)           # held closed at least 1 s
            self.assertAlmostEqual((sch['close_end']-sch['close_start'])/24, 2.0, 6); self.assertAlmostEqual((sch['open_end']-sch['open_start'])/24, 2.0, 6)

    def test_the_leaf_is_fully_open_before_the_camera_walks_out_and_closes_only_after_it_is_in(self):
        fr = self.path['frames']
        for rec in self.path['door_anim']:
            sch = rec['schedule']; room = next(f['room'] for f in fr[sch['close_end']:] if f['room'])
            entry = sch['close_end']
            while entry > 0 and fr[entry-1]['room'] == fr[sch['close_end']]['room']: entry -= 1
            self.assertGreater(sch['close_start'], entry)                                   # the camera is already in the room
            leave = next(f['index'] for f in fr[sch['close_end']:] if f['phase'] == 'walk')
            self.assertLessEqual(sch['open_end'], leave)

    def test_the_camera_keeps_clear_of_every_leaf_in_every_frame_of_the_animation(self):
        self.assertEqual(DA.clearance_findings(self.path, self.path['settings']['door_leaf_clearance_m']), [])
        bad = copy.deepcopy(self.path); rec = bad['door_anim'][0]; i = rec['schedule']['close_end']+5
        x, y = rec['hinge']; bad['frames'][i]['camera']['position'][:2] = [x+.3*math.cos(math.radians(rec['signed_open_deg'])), y]      # negative: the camera standing at the hinge is caught
        self.assertTrue(DA.clearance_findings(bad, self.path['settings']['door_leaf_clearance_m']))

    def test_villa_admission_fails_a_frame_where_the_camera_is_at_a_closing_leaf(self):
        bad = copy.deepcopy(self.path); rec = bad['door_anim'][0]; i = rec['schedule']['close_end']+5
        found = DA.clearance_findings(dict(bad, frames=[dict(bad['frames'][i], camera=dict(bad['frames'][i]['camera'], position=[*rec['hinge'], 1.35]))]), .3)
        self.assertTrue(found)

    def test_a_schedule_planned_on_another_camera_path_is_refused(self):
        rec = copy.deepcopy(self.path); rec['frames'][100]['camera']['position'][0] += .5; rec.pop('door_anim')
        for f in rec['frames']: f.pop('doors', None)
        with self.assertRaises(ValueError):
            WT.attach_doors(rec)


if __name__ == '__main__':
    unittest.main()
