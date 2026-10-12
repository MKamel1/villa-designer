"""Real evaluated throw/duvet shell; numerical duplicate is not a new surface."""
import gzip,json
from pathlib import Path
import unittest
import numpy as np
from archpipe.bed_containment import (local_query_coordinates,unique_triangle_parity,
                                     closed_shell_contains,RAY_DIRECTIONS)

class ClothRayPrecision(unittest.TestCase):
    def case(self):
        return json.loads(gzip.decompress((Path(__file__).parent/'fixtures/bed-round7-ray-duplicate.json.gz').read_bytes()))

    def test_real_duplicate_ray_hits_refuse_before_fix_and_clean_local_hits_agree(self):
        case=self.case()
        self.assertEqual([len(v)%2==1 for v in case['world_bvh_face_hits']],[True,False,False])
        self.assertEqual([unique_triangle_parity(v) for v in case['world_bvh_face_hits']],[False]*3)
        self.assertEqual([unique_triangle_parity(v) for v in case['local_bvh_face_hits']],[False]*3)
        self.assertFalse(closed_shell_contains(case['triangles'],case['point_m']))

    def test_local_construction_generalises_to_translated_shell_and_real_inside_point(self):
        case=self.case();triangles=np.asarray(case['triangles']);point=np.asarray(case['point_m'])
        direction=np.asarray(RAY_DIRECTIONS[0]);direction/=np.linalg.norm(direction)
        # Midpoint of the real entering/exiting ray hits is truly enclosed.
        inside=point+direction*np.mean(case['diagnostics'][0]['ray_distances'][0])
        self.assertTrue(closed_shell_contains(triangles,inside))
        for translation in ([0,0,0],[1234,-5678,100]):
            origin,local=local_query_coordinates((triangles+translation).reshape(-1,3))
            self.assertLess(np.max(np.abs(local)),2)
            np.testing.assert_allclose(local+origin,(triangles+translation).reshape(-1,3),atol=1e-12)
            self.assertFalse(closed_shell_contains(local.reshape(-1,3,3),point+translation-origin))
            self.assertTrue(closed_shell_contains(local.reshape(-1,3,3),inside+translation-origin))
        self.assertTrue(unique_triangle_parity([7,7,9,11]))
        self.assertFalse(unique_triangle_parity([7,7,9]))

if __name__=='__main__':unittest.main()
