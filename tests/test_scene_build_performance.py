"""Performance controls must preserve frozen geometry and scalar camera scoring."""
import copy
import json
import math
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from archpipe.concept import physical_part as P, render_views as RV, villa_landscape as L
from archpipe.concept.build_cache import scope
from archpipe.concept.wc_slides import _trial
from archpipe.concept.villa_render import box_faces
from archpipe.orientation import historical_aliases


class SceneBuildPerformance(unittest.TestCase):
    def test_whole_camera_batch_matches_scalar_all_yaws_on_real_wc_and_siblings(self):
        frozen = historical_aliases(json.loads((Path(__file__).parent / 'fixtures/c4-family-wc-lens-before.json').read_text()))
        points = np.asarray(frozen['wc_vertices'])
        yaws = [(math.radians(d), math.cos(math.radians(d)), math.sin(math.radians(d)))
                for d in range(0, 360, RV.YAW_STEP)]
        for shift in ((0, 0, 0), (7, -4, 3)):
            vertices = points + np.array(shift)
            for x, y in ((9.727, -24.971), (9.602, -24.846), (11.0, -26.0)):
                x += shift[0]; y += shift[1]; eye = 1.35 + shift[2]
                expected = [max(abs(math.atan2(p[2]-eye, (p[0]-x)*c+(p[1]-y)*s))
                                for p in vertices) for _, c, s in yaws]
                self.assertEqual(RV._whole_needs(vertices, x, y, eye, yaws), expected)
        self.assertEqual(RV._whole_needs(np.empty((0, 3)), 0, 0, 1.35, yaws), [0.0]*len(yaws))

    def test_validation_cache_follows_values_and_keeps_kind_side_support_guards(self):
        faces = box_faces(0, 0, 0, 1, 1, 1)
        real = P._geometry_errors
        with scope(), patch.object(P, '_geometry_errors', wraps=real) as check, \
             patch.object(P, '_key', wraps=P._key) as rounded:
            self.assertEqual(P.geometry_errors(faces), [])
            self.assertEqual(rounded.call_count, 8, 'round each shared box vertex only once')
            self.assertEqual(P.geometry_errors(copy.deepcopy(faces)), [])
            self.assertEqual(check.call_count, 1)
            with self.assertRaisesRegex(P.PartError, 'bare rectangular proxy'):
                P.Part('planter', faces, ('x','y','z'), 'soil', 'authored-procedural')
            P.Part('planter-soil', faces, ('x','y','z'), 'soil', 'authored-procedural')
            with self.assertRaisesRegex(P.PartError, 'duvet leaves'):
                P.Part('duvet', faces, ('x','y','z'), 'cloth', 'authored-procedural', support=(0,0,.5,.5))
            faces[0] = faces[0][::-1]
            errors = P.geometry_errors(faces)
            self.assertIn('open or inconsistently wound edges', errors)
            errors.clear()
            self.assertTrue(P.geometry_errors(faces))
            self.assertEqual(check.call_count, 2)
            floor = [[[0,0,0],[1,0,0],[1,1,0],[0,1,0]]]
            self.assertEqual(P.geometry_errors(floor, surface=True, occupied_side=(0,0,1)), [])
            self.assertTrue(P.geometry_errors(floor, surface=True, occupied_side=(0,0,-1)))
        with scope(), patch.object(P, '_geometry_errors', wraps=real) as check:
            P.geometry_errors(faces)
            self.assertEqual(check.call_count, 1)

    def test_wc_trial_copies_only_mutated_members_and_matches_deepcopy(self):
        for identifier, side in (('gwc-wc', 0), ('renamed-pan', 1)):
            scene = dict(meshes=[dict(id='furn-'+identifier+'-pan', faces=box_faces(0,0,0,.4,.6,.4)),
                                 dict(id='unrelated', faces=box_faces(1,1,0,2,2,1))],
                         wc_slides={'previous': dict(delta=[.1,0,0])}, materials={'stone': {}},
                         mounting_movements=[])
            before = copy.deepcopy(scene)
            trial, delta, members = _trial(scene, identifier, side, .125)
            expected = copy.deepcopy(scene)
            expected['wc_slides'][identifier] = dict(delta=delta)
            expected['meshes'][0]['faces'] = [[[p[i]+delta[i] for i in range(3)] for p in f]
                                             for f in expected['meshes'][0]['faces']]
            self.assertEqual(trial, expected)
            self.assertEqual(scene, before)
            self.assertIs(trial['materials'], scene['materials'])
            self.assertIs(trial['meshes'][1], scene['meshes'][1])
            members[0]['faces'][0][0][0] += 999
            trial['wc_slides'][identifier]['delta'][side] += 999
            self.assertEqual(scene, before)

    def test_route_rect_computed_once_per_mesh_for_many_routes(self):
        mesh = dict(id='physical-plant', faces=box_faces(0,0,-3,.5,.5,-2))
        routes = {'crossing': (0,0,1,1), 'far': (3,3,4,4), 'sibling': (.1,.1,.4,.4)}
        with patch.object(L, '_mesh_rect', wraps=L._mesh_rect) as rect:
            self.assertEqual(L.route_violations([mesh], routes), [('physical-plant','crossing'),
                                                                  ('physical-plant','sibling')])
            self.assertEqual(rect.call_count, 1)
        moved = copy.deepcopy(mesh)
        for face in moved['faces']:
            for p in face: p[0] += 10
        self.assertEqual(L.route_violations([moved], routes), [])

    def test_botanical_batch_preserves_face_values_lengths_and_winding(self):
        from archpipe.concept.garden_g6 import _transform_faces
        faces = box_faces(-.1,-.3,0,.2,.4,.7) + [[[0,0,0],[.1,0,.3],[0,.2,.4]]]
        points = np.asarray([p for face in faces for p in face])
        origin = np.array([.05,-.03,0]); factors = np.array([1.125,.625,.75])
        for offset in (np.array([22.81,-29.75,-3]), np.array([7,-4,5])):
            expected = [[(offset+(np.array(p)-origin)*factors).tolist() for p in face] for face in faces]
            self.assertEqual(_transform_faces(faces,points,origin,factors,offset), expected)

    def test_mesh_rectangle_cache_follows_exact_live_xy_values(self):
        mesh = dict(faces=box_faces(0,0,0,1,1,1))
        with scope():
            self.assertEqual(L._mesh_rect(mesh), (0,0,1,1))
            clone = copy.deepcopy(mesh)
            self.assertEqual(L._mesh_rect(clone), (0,0,1,1))
            clone['faces'][0][0][0] = -2
            self.assertEqual(L._mesh_rect(clone), (-2,0,1,1))
            self.assertEqual(L._mesh_rect(mesh), (0,0,1,1))

    def test_shared_vertex_islands_match_frozen_algorithm_and_disconnected_siblings(self):
        from archpipe.concept import render_support as S
        namespace = {}
        exec((Path(__file__).parent/'fixtures/scene-islands-before.py').read_text(), namespace)
        old = namespace['_islands']
        a = box_faces(0,0,0,.1,.1,.3)
        for separation in (0, .00004, .00006, .5):
            b = box_faces(.1+separation,0,0,.2+separation,.1,.3)
            faces = a+b
            self.assertEqual(S._islands(faces), old(faces))
            shifted = [[[p[0]+7,p[1]-4,p[2]+3] for p in face] for face in faces]
            self.assertEqual(S._islands(shifted), old(shifted))
        self.assertEqual(len(S._islands(a+box_faces(.6,0,0,.7,.1,.3))), 2)
        self.assertEqual(S._islands([]), [])

    def test_bearing_batches_match_scalar_at_frame_edges_and_real_wc_points(self):
        yaws = [(math.radians(d), math.cos(math.radians(d)), math.sin(math.radians(d)))
                for d in range(0,360,RV.YAW_STEP)]
        half = math.atan(36/2/24)
        bearings = [-math.pi, math.pi, -half, half, half-1e-15, half+1e-15, 0., 2.3, -2.8]
        frozen = historical_aliases(json.loads((Path(__file__).parent/'fixtures/c4-family-wc-lens-before.json').read_text()))
        for x,y in ((9.727,-24.971),(9.602,-24.846),(11.,-26.)):
            actual = [math.atan2(p[1]-y,p[0]-x) for p in frozen['wc_vertices']]
            for subjects,room,openings,nearby in ((bearings,actual,bearings,[actual[:5],bearings,[]]),
                                                 ([],[],[],[])):
                miss, seen, wins, looming = RV._bearing_batches(subjects,room,openings,nearby,yaws,half)
                for index,(yaw,_,_) in enumerate(yaws):
                    self.assertEqual(miss[index],sum(max(0.,abs(RV._bearing_angle(b,yaw))-half) for b in subjects))
                    self.assertEqual(seen[index],sum(abs(RV._bearing_angle(b,yaw))<=half for b in room))
                    self.assertEqual(wins[index],sum(abs(RV._bearing_angle(b,yaw))<=half for b in openings))
                    self.assertEqual(looming[index],sum(any(abs(RV._bearing_angle(b,yaw))<half for b in piece) for piece in nearby))

    def test_dot_product_retains_python_sum_compensation(self):
        a = (1e16, 1., -1e16); b = (1., 1., 1.)
        self.assertEqual(P._dot(a,b), sum(x*y for x,y in zip(a,b)))
        self.assertEqual(P._dot(a,b), 1.)

    def test_mound_template_is_local_value_keyed_and_caller_records_are_independent(self):
        from archpipe.concept import garden_g6 as G, garden_g6b as B
        # Use the real generator once; no fabricated placeholder geometry.
        original = B.mound
        with scope(), patch.object(B, 'mound', wraps=original) as counted:
            a = G._mound_template(False)
            b = G._mound_template(False)
            self.assertIs(a, b)
            self.assertEqual(counted.call_count, 1)
            c = G._mound_template(True)
            self.assertEqual(counted.call_count, 2)
            self.assertEqual(a, c)  # Both current generator modes emit the same form.
            records = json.loads(a[3]); records[0]['length_m'] = -999
            self.assertGreater(json.loads(G._mound_template(False)[3])[0]['length_m'], 0)
        with scope(), patch.object(B, 'mound', wraps=original) as counted:
            G._mound_template(False)
            self.assertEqual(counted.call_count, 1)

    def test_triangles_preserve_frozen_order_owners_and_mutable_caller_isolation(self):
        from archpipe.concept import render_support as S
        namespace = dict(np=np,_ear_clip=S._ear_clip)
        exec((Path(__file__).parent/'fixtures/scene-triangles-before.py').read_text(), namespace)
        old = namespace['_triangles']
        meshes = [dict(faces=box_faces(0,0,0,1,1,1)), dict(faces=[]),
                  dict(faces=[[[0,0,0],[2,0,0],[2,2,0],[1,1,0],[0,2,0]]])]
        with scope(), patch.object(S,'_ear_clip',wraps=S._ear_clip) as clipped:
            actual,owners = S._triangles(meshes)
            before,before_owners = old(meshes)
            self.assertTrue(np.array_equal(actual,before))
            self.assertTrue(np.array_equal(owners,before_owners))
            count = clipped.call_count
            actual[0,0,0] = -999
            owners[0] = -999
            again,again_owners = S._triangles(copy.deepcopy(meshes))
            self.assertTrue(np.array_equal(again,before))
            self.assertTrue(np.array_equal(again_owners,before_owners))
            self.assertEqual(clipped.call_count,count)
            meshes[0]['faces'][0][0][0] -= 7
            changed,_ = S._triangles(meshes)
            self.assertFalse(np.array_equal(changed,before))
            reversed_tri,reversed_owners = S._triangles(meshes[::-1])
            expected,expected_owners = old(meshes[::-1])
            self.assertTrue(np.array_equal(reversed_tri,expected))
            self.assertTrue(np.array_equal(reversed_owners,expected_owners))
        empty,owners = S._triangles([])
        self.assertEqual(empty.shape,(0,3,3))
        self.assertEqual(owners.shape,(0,))

    def test_triangle_cache_preserves_signed_zero_content_bits(self):
        from archpipe.concept import render_support as S
        positive = [[[0.,0.,0.],[1.,0.,0.],[0.,1.,0.]]]
        negative = copy.deepcopy(positive); negative[0][0][0] = -0.
        with scope():
            a,_ = S._triangles([dict(faces=positive)])
            b,_ = S._triangles([dict(faces=negative)])
            self.assertFalse(np.signbit(a[0,0,0]))
            self.assertTrue(np.signbit(b[0,0,0]))
            self.assertNotEqual(a.tobytes(),b.tobytes())

    def test_part_snapshots_geometry_once_for_both_validations(self):
        faces = box_faces(0,0,0,1,1,1)
        with scope(), patch.object(P._FrozenFaces,'__new__', wraps=P._FrozenFaces.__new__) as frozen:
            P.Part('cabinet-carcass',faces,('x','y','z'),'oak','authored-procedural')
            self.assertEqual(frozen.call_count,1)
        snapshot = P._freeze_faces(faces)
        self.assertIs(P._freeze_faces(snapshot),snapshot)
        faces[0][0][0] -= 7
        self.assertNotEqual(P._freeze_faces(faces),snapshot)
