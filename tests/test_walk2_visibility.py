"""Real topology-induced false refusal; stable leaves and opaque blockers."""
import gzip
import json
from pathlib import Path
import unittest
import numpy as np
from archpipe.concept.garden_render_review import visibility_sample_points,visibility_sample_vertices,subject_visibility_evidence


class FoliageVisibility(unittest.TestCase):
    def test_real_flower_topology_changes_legacy_samples_but_same_leaves_are_stable(self):
        data=json.loads(gzip.decompress((Path(__file__).parent/'fixtures/garden-walk2-visibility-before.json.gz').read_bytes()))
        self.assertEqual(data['old_leaf_points_m'],data['current_leaf_points_m'])
        self.assertNotEqual(data['old_sample_points_m'],data['current_sample_points_m'])
        for shift in ([0,0,0],[37,-29,8]):
            old=np.asarray(data['old_leaf_points_m'])+shift
            current=np.asarray(data['current_leaf_points_m'])+shift
            np.testing.assert_array_equal(visibility_sample_vertices(old),visibility_sample_vertices(current))
            samples=visibility_sample_vertices(old)
            np.testing.assert_allclose(samples-np.asarray(shift),visibility_sample_vertices(data['old_leaf_points_m']),atol=1e-12)

    def test_actual_current_jasmine_foliage_visible_and_existing_beams_still_occlude(self):
        from archpipe.concept import garden_g6 as G,villa_render as V
        meshes,_,_,_=G.build()
        # G.build already supplies the actual exported target identifiers.
        view=next(v for v in V.VIEWS(resolve=False) if v['id']=='v41-south-garden-terrace')
        scene=dict(meshes=meshes,materials=V.M)
        evidence=subject_visibility_evidence(view,scene)
        jasmine=next(r for r in evidence if r['subject']=='landscape-g6-jasmine-roof')
        self.assertGreaterEqual(jasmine['visible'],7)
        self.assertTrue(any(hit and hit!=jasmine['subject'] for hit in jasmine['first_hits']))
        # A missing declared form population must refuse rather than silently
        # revert to the topology-sensitive all-face population.
        target=next(m for m in meshes if m['id']==jasmine['subject'])
        target['visibility_face_indices']=[]
        with self.assertRaises(ValueError):visibility_sample_points([target])

    def test_sampling_uses_declared_physical_faces_and_rejects_invalid_populations(self):
        mesh=dict(id='another-villa-plant',faces=[[[0,0,0],[1,0,0],[0,1,0]],[[5,5,5],[6,5,5],[5,6,5]]],visibility_face_indices=[0])
        first=visibility_sample_points([mesh])
        mesh['faces'].append([[100,100,100],[101,100,100],[100,101,100]])
        np.testing.assert_array_equal(first,visibility_sample_points([mesh]))
        mesh['visibility_face_indices']=[90]
        with self.assertRaises(ValueError):visibility_sample_points([mesh])
