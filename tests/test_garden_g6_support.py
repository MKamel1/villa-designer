"""Exact-mask acceleration preserves physical support on real G6 assemblies."""
from copy import deepcopy
from pathlib import Path
import unittest
from archpipe.concept import garden_g6 as G,render_support as S


class SupportMaskEquivalence(unittest.TestCase):
    def test_actual_building_mask_matches_frozen_support_and_mutations(self):
        meshes,_,_,_=G.build()
        # Use actual current at-grade frame, bowl and seating with the actual
        # terrace surface; exclude the dense plants from this bounded parity
        # test. Full botanical support is exercised by authoritative acceptance.
        actual=[deepcopy(m) for m in meshes if m.get('g6_element') in ('pergola','furniture') or m['id'].endswith('centrepiece-bowl') or m['id'].endswith('centrepiece-rim')]
        scene=dict(meshes=actual,props=[])
        namespace=dict(vars(S))
        exec((Path(__file__).parent/'fixtures/garden-g6-support-before.py').read_text(),namespace)
        old=namespace['unsupported']
        self.assertEqual(S.unsupported(scene),old(scene))
        self.assertEqual(S.unsupported(scene),[])
        floated=deepcopy(scene)
        chair=next(m for m in floated['meshes'] if m.get('g6_element')=='furniture')
        chair['id']='other-villa-floating-chair'
        for f in chair['faces']:
            for p in f:p[2]+=4
        self.assertEqual(S.unsupported(floated),old(floated))
        self.assertTrue(any(mid==chair['id'] for mid,_ in S.unsupported(floated)))
        # A prop may rest on furniture; only assembly grounding excludes
        # item faces. The complete separate prop surface query is retained.
        seated=deepcopy(scene);bench=next(m for m in seated['meshes'] if m.get('seats')==2)
        points=[p for f in bench['faces'] for p in f]
        seated['props']=[dict(id='actual-seat-prop',position=[23.15,-28.31,-2.58],label='prop on actual furniture')]
        self.assertEqual(S.unsupported(seated),old(seated))
