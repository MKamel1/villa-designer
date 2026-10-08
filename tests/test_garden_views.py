"""Actual overlapping stones and immutable render-union sibling proofs."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import unittest
from shapely.geometry import Polygon,box
from shapely.ops import unary_union
from archpipe.blender import stone_union as S

class StoneUnion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=json.loads(Path('tests/fixtures/garden-views-stones-before.json').read_text())

    def assert_union(self,stones):
        retained=deepcopy(stones);prepared,aliases=S.prepare(stones)
        self.assertEqual(stones,retained)
        self.assertEqual(S.overlap_findings(prepared),[])
        for fused in prepared:
            if 'fused_source_ids' not in fused:continue
            old=[m for m in stones if m['id'] in fused['fused_source_ids']]
            self.assertTrue(all(aliases[m['id']]==fused['id'] for m in old))
            b=S.bounds(fused)
            original_union=unary_union([box(v[0],v[1],v[3],v[4]) for v in map(S.bounds,old)])
            tops=[Polygon([p[:2] for p in f]) for f in fused['faces'] if all(p[2]==b[5] for p in f)]
            self.assertAlmostEqual(sum(p.area for p in tops),original_union.area,places=10)
            self.assertAlmostEqual(unary_union(tops).symmetric_difference(original_union).area,0,places=10)
            edges=Counter(tuple(sorted((tuple(f[i]),tuple(f[(i+1)%len(f)])))) for f in fused['faces'] for i in range(len(f)))
            self.assertEqual(set(edges.values()),{2},'closed manifold surface')
            self.assertEqual(len(fused['faces']),len(fused['face_materials']))
            for face,material in zip(fused['faces'],fused['face_materials']):
                self.assertEqual(material,'stone-substrate' if all(p[2]==b[2] for p in face) else fused['material'])
        return prepared,aliases

    def test_actual_black_stripe_overlap_and_all_route_siblings(self):
        failures=S.overlap_findings(self.before)
        self.assertIn(('landscape-stone-living-south-end-0','landscape-stone-living-south-00'),failures)
        self.assertIn(('landscape-stone-living-south-end-1','landscape-stone-living-south-02'),failures)
        prepared,aliases=self.assert_union(self.before)
        self.assertGreater(len(failures),2)
        self.assertGreater(len(aliases),4)
        # Frozen real stones without construction control still fire.
        self.assertTrue(S.overlap_findings(self.before))

    def test_renamed_translated_stones_and_isolated_clean_case(self):
        for offset in (0.,40.):
            sibling=deepcopy(self.before)
            for m in sibling:
                m['id']='another-villa-'+m['id']
                for f in m['faces']:
                    for p in f:p[0]+=offset;p[1]-=offset;p[2]+=offset
            self.assertTrue(S.overlap_findings(sibling));self.assert_union(sibling)
        isolated=self.before[:1]
        self.assertEqual(S.prepare(isolated),(isolated,{}))
        self.assertEqual(S.overlap_findings(isolated),[])


class GardenIntent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import gzip
        cls.scene=json.loads(gzip.decompress(Path('tests/fixtures/garden-views-east-context-before.json.gz').read_bytes()))
        cls.before=json.loads(Path('tests/fixtures/garden-views-cameras-before.json').read_text())

    def test_whole_court_intent_keeps_old_plants_and_frames_context(self):
        from archpipe.concept import villa_render as V
        from archpipe.concept.garden_render_review import subject_frame_findings,subject_visibility_findings,garden_camera_findings,opening_frame_findings
        from scripts.villa_render_views import camera_proximity_violations
        view=next(v for v in V.VIEWS(resolve=False) if v['id']=='v27-east-yard-above')
        old=next(v for v in self.before if v['id']==view['id'])
        self.assertTrue(set(old['subjects'])<=set(view['subjects']))
        self.assertTrue({'landscape-bed-east','landscape-trellis-east','landscape-climber-east','landscape-stone-living-east'}<=set(view['subjects']))
        self.assertEqual(view['visibility_targets'],old['visibility_targets'])
        self.assertTrue(view['require_full_subject_frame'])
        self.assertEqual(view['camera']['lens_mm'],24)
        self.assertEqual(view['camera']['position'][2],view['camera']['target'][2])
        self.assertEqual(view['standing_room'],'dirty-kitchen')
        for check in (subject_frame_findings,subject_visibility_findings,garden_camera_findings,opening_frame_findings):
            self.assertEqual(check(view,self.scene),[],check.__name__)
        self.assertEqual(camera_proximity_violations(view,self.scene,{}),[])
        # The real rejected close-up cannot hold the newly declared context.
        old['subjects']=view['subjects']
        self.assertTrue(subject_frame_findings(old,self.scene))
        # Actual first ground candidate read well but screened two target
        # plant groups; the original 7/13 criterion must still refuse it.
        screened=deepcopy(view)
        screened['camera'].update(position=[14.2,-21.6,-1.65],target=[19.198898902889077,-21.704927397253446,-1.65],shift_y=-.06411647691435263)
        self.assertTrue(subject_visibility_findings(screened,self.scene))
        bad=deepcopy(view);bad['camera']['shift_y']+=.5
        self.assertTrue(subject_frame_findings(bad,self.scene))

    def test_court_guards_generalise_to_translated_renamed_sibling(self):
        from archpipe.concept import villa_render as V
        from archpipe.concept.garden_render_review import subject_frame_findings,subject_visibility_findings,garden_camera_findings
        scene=deepcopy(self.scene);view=next(v for v in V.VIEWS(resolve=False) if v['id']=='v27-east-yard-above')
        view['id']='another-villa-whole-court'
        for m in scene['meshes']:
            m['id']=m['id'].replace('landscape-','landscape-another-')
            for f in m['faces']:
                for p in f:p[0]+=40
        view['subjects']=[v.replace('landscape-','landscape-another-') for v in view['subjects']]
        view['visibility_targets']=[v.replace('landscape-','landscape-another-') for v in view['visibility_targets']]
        for field in ('position','target'):view['camera'][field][0]+=40
        for room in scene['garden_camera_domain']['rooms'].values():
            room['rect_m'][0]+=40;room['rect_m'][2]+=40
        for point in scene['garden_camera_domain']['yard_polygon_m']:point[0]+=40
        for check in (subject_frame_findings,subject_visibility_findings,garden_camera_findings):self.assertEqual(check(view,scene),[])
        view['camera']['shift_y']+=.5
        self.assertTrue(subject_frame_findings(view,scene))

class PresentationDecisions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from archpipe.concept import villa_render as V
        cls.scene = V.build()
        cls.views = {v['id']: v for v in cls.scene['views']}

    def test_retirements_and_final_candidate_keep_diagnostic_definitions(self):
        from archpipe.villa_render_contract import presentation_view_ids
        retired = {'v07-terrace-dusk', 'v38-north-garden-floor-bed', 'v42-north-garden-evening'}
        self.assertEqual({k for k, v in self.views.items() if v.get('presentation_retired')}, retired)
        for review in (False, True):
            self.assertFalse(retired.intersection(presentation_view_ids(self.views, review=review)))
        for ident in retired:
            self.assertRegex(self.views[ident]['presentation_decision'], r'^Lead decision 2026-10-0[78]')
        for ident in ('v19-garden-facade', 'v40-south-garden-espalier',
                      'v41-south-garden-terrace', 'v36-north-garden',
                      'v37-north-garden-lounge', 'v39-north-garden-hanging-retreat'):
            self.assertIn(ident, presentation_view_ids(self.views))
        proposal = json.loads(Path('knowledge/garden-views-terrace-proposal.json').read_text())
        view = self.views['v41-south-garden-terrace']
        for field in ('position', 'target', 'lens_mm', 'sensor_mm', 'shift_y'):
            self.assertEqual(view['camera'][field], proposal['camera'][field])
        for field in ('subjects', 'visibility_targets', 'caption_notes', 'visibility_allowances'):
            self.assertEqual(view[field], proposal[field])

    def test_integrated_candidate_retains_reviewed_preview_geometry(self):
        import hashlib
        # Frozen by value from the accepted neutral preview receipt, rather
        # than regenerated from the current scene or an optional output path.
        # G4e replaced the Rhapis and Aspidistra appearances; G4f rebuilt the
        # nine Aspidistra as the oval loose fountain. Lead accepted the G4f
        # neutral previews (out/garden-g4f/after-oval-*) on 2026-10-08.
        reviewed = '172370e5b14a4711d4f11a4036dc44232596c0c8749ccb9a387abb46e24bc838'
        data = json.dumps(self.scene['meshes'], sort_keys=True, separators=(',', ':')).encode()
        self.assertEqual(hashlib.sha256(data).hexdigest(), reviewed)

    def test_actual_candidate_has_only_reviewed_rear_chair_allowance(self):
        from archpipe.concept.garden_render_review import subject_visibility_evidence, subject_visibility_findings
        view = self.views['v41-south-garden-terrace']
        chair = 'landscape-g6-seating-chair-1'
        self.assertEqual([(v['id'], list(v['visibility_allowances']))
                          for v in self.scene['views'] if v.get('visibility_allowances')], [('v37-north-garden-lounge', ['landscape-north-feature-stone']), (view['id'], [chair])])
        evidence = subject_visibility_evidence(view, self.scene)
        self.assertEqual([r['visible'] for r in evidence], [11, 13, 13, 6, 8, 7])
        self.assertEqual(subject_visibility_findings(view, self.scene), [])
        original = deepcopy(view)
        original.pop('visibility_allowances')
        self.assertEqual(subject_visibility_findings(original, self.scene),
                         [view['id']+': named subject obscured '+chair])

    def test_integrated_caption_uses_measured_camera_side_without_waiver(self):
        from archpipe.orientation_guard import scene_findings
        view = deepcopy(self.views['v41-south-garden-terrace'])
        scene = dict(self.scene, views=[view])
        self.assertEqual(scene_findings(scene), [])
        proposal = json.loads(Path('knowledge/garden-views-terrace-proposal.json').read_text())
        view['caption_notes'] = [proposal['caption_before_naming_check']]
        self.assertTrue(any('names west' in f for f in scene_findings(scene)))
        view['caption_notes'] = proposal['caption_notes']
        del view['caption_camera_garden']
        self.assertTrue(any('names east' in f for f in scene_findings(scene)))

    def test_five_rays_fail_and_every_other_subject_still_requires_seven(self):
        from unittest.mock import patch
        from archpipe.concept import garden_render_review as review
        view = self.views['v41-south-garden-terrace']
        evidence = review.subject_visibility_evidence(view, self.scene)
        for record in evidence:
            altered = deepcopy(evidence)
            result = next(r for r in altered if r['subject'] == record['subject'])
            result['visible'] = 5 if record['subject'] in view['visibility_allowances'] else 6
            with patch.object(review, 'subject_visibility_evidence', return_value=altered):
                self.assertEqual(review.subject_visibility_findings(view, self.scene),
                                 [view['id']+': named subject obscured '+record['subject']])
        other = deepcopy(view)
        other['id'] = 'another-villa-terrace'
        with patch.object(review, 'subject_visibility_evidence', return_value=evidence):
            self.assertTrue(any('invalid visibility allowance' in f
                                for f in review.subject_visibility_findings(other, self.scene)))
            other.pop('visibility_allowances')
            self.assertEqual(review.subject_visibility_findings(other, self.scene),
                             [other['id']+': named subject obscured landscape-g6-seating-chair-1'])

    def test_v37_stone_allowance_is_subject_and_view_bound_and_five_still_fails(self):
        from unittest.mock import patch
        from archpipe.concept import garden_render_review as review
        view=self.views['v37-north-garden-lounge'];stone='landscape-north-feature-stone'
        self.assertEqual(list(view['visibility_allowances']),[stone])
        self.assertIn('lead decision 2026-10-08',view['visibility_allowances'][stone]['reason'])
        evidence=review.subject_visibility_evidence(view,self.scene)
        self.assertEqual(next(r['visible'] for r in evidence if r['subject']==stone),6)
        self.assertEqual(review.subject_visibility_findings(view,self.scene),[])
        for record in evidence:
            altered=deepcopy(evidence)
            next(r for r in altered if r['subject']==record['subject'])['visible']=5 if record['subject']==stone else 6
            with patch.object(review,'subject_visibility_evidence',return_value=altered):
                self.assertEqual(review.subject_visibility_findings(view,self.scene),[view['id']+': named subject obscured '+record['subject']])
        copied=deepcopy(view);copied['id']='other-view'
        with patch.object(review,'subject_visibility_evidence',return_value=evidence):
            self.assertTrue(any('invalid visibility allowance' in f for f in review.subject_visibility_findings(copied,self.scene)))
            copied.pop('visibility_allowances')
            self.assertEqual(review.subject_visibility_findings(copied,self.scene),[copied['id']+': named subject obscured '+stone])

    def test_blender_direct_batches_share_retirement_selection(self):
        import ast
        from types import SimpleNamespace
        from archpipe import villa_render_contract as contract
        # Execute the production selection expression without loading Blender.
        tree = ast.parse(Path('src/archpipe/blender/villa_scene.py').read_text())
        render = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'render')
        expression = next(n.value for n in render.body if isinstance(n, ast.Assign)
                          and any(isinstance(t, ast.Name) and t.id == 'selected' for t in n.targets))
        for requested in ('all', 'review', 'v07-terrace-dusk', 'v38-north-garden-floor-bed'):
            selected = eval(compile(ast.Expression(expression), '<production view selector>', 'eval'),
                            {'contract': contract, 'scene_data': self.scene,
                             'args': SimpleNamespace(views=requested)})
            expected = (set(contract.presentation_view_ids(self.views, review=requested == 'review'))
                        if requested in ('all', 'review') else {requested})
            self.assertEqual(selected, expected)


class ProbeInputs(unittest.TestCase):
    def test_actual_missing_manufacturer_bundle_and_generated_precedence(self):
        from tempfile import TemporaryDirectory
        from scripts.garden_view_probes import resolve_probe_photometry
        # Actual failed producer path/name: numerical-probes.log retained.
        data={'lights':[{'ies':'iguzzini/LSEVO-AAK3EW.ies'}, {'ies':'generic/GARDEN-UP.ies'}]}
        with TemporaryDirectory() as folder:
            generated=Path(folder)/'generated';archive=Path(folder)/'archive'
            generated.mkdir();archive.mkdir()
            with self.assertRaisesRegex(FileNotFoundError,'LSEVO-AAK3EW'):
                resolve_probe_photometry(data,generated,archive)
            for name in ('iguzzini/LSEVO-AAK3EW.ies','generic/GARDEN-UP.ies'):
                path=archive/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('retained source')
            current=generated/'generic/GARDEN-UP.ies';current.parent.mkdir();current.write_text('current generated source')
            resolved=resolve_probe_photometry(data,generated,archive)
            self.assertEqual(resolved['generic/GARDEN-UP.ies'],current)
            self.assertEqual(resolved['iguzzini/LSEVO-AAK3EW.ies'],archive/'iguzzini/LSEVO-AAK3EW.ies')
            sibling={'lights':[{'ies':'another-manufacturer/missing.ies'}]}
            with self.assertRaises(FileNotFoundError):resolve_probe_photometry(sibling,generated,archive)
            with self.assertRaises(ValueError):resolve_probe_photometry({'lights':[{'ies':'../outside.ies'}]},generated,archive)
            self.assertEqual(resolve_probe_photometry({'lights':[]},generated,archive),{})

if __name__=='__main__':unittest.main()
