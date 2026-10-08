from archpipe.orientation import historical_aliases
"""Real suspended retreat, frozen cushion failures and adverse view mutations."""
from copy import deepcopy
import gzip,json
from pathlib import Path
import unittest
from archpipe.concept import garden_swing as S,villa_render as V,villa_r11 as R
from archpipe.concept.mounting import scene_findings as mounting_findings


class HangingRetreat(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scene=V.build(views=[])
        cls.record=cls.scene['north_swing']
        cls.parts=[m for m in cls.scene['meshes'] if m.get('hanging_swing')]

    def test_real_clean_support_and_physical_cushion_regressions(self):
        self.assertEqual(S.scene_findings(deepcopy(self.scene)),[])
        self.assertEqual(mounting_findings(self.scene),[])
        self.assertEqual(S.cushion_findings(self.parts),[])
        for name in ('seat','support'):
            bad=historical_aliases(json.loads(gzip.decompress(Path('tests/fixtures/garden-g4c-'+name+'-before.json.gz').read_bytes())))
            self.assertIn('missing physical cushion bearing',str(S.cushion_findings(bad)))
        bad=deepcopy(self.parts)
        for m in bad:
            m['id']='another-project-'+m['part_kind']
            if m['part_kind']=='swing-bearing':
                for f in m['faces']:
                    for p in f:p[2]-=.08
        self.assertIn('lacks physical bearing',str(S.cushion_findings(bad)))
        self.assertIn('no physical cage joints',str(S.cushion_findings(bad)))
        reordered=deepcopy(self.parts)
        for m in reordered:m['faces'].reverse()
        self.assertEqual(S.cushion_findings(reordered),[])
        raised=deepcopy(self.parts)
        for m in raised:
            if m['part_kind']=='swing-cushion':
                for f in m['faces']:
                    for p in f:p[2]+=.08
        self.assertIn('lacks physical bearing',str(S.cushion_findings(raised)))

    def test_real_curved_faces_are_triangles_and_new_bed_ids_unique(self):
        from archpipe.villa_render_contract import validate_scene
        frozen=historical_aliases(json.loads(gzip.decompress(Path('tests/fixtures/garden-g4c-topology-before.json.gz').read_bytes())))
        bad=dict(self.scene,meshes=frozen)
        self.assertIn('nonplanar',str(validate_scene(bad)))
        self.assertTrue(all(len(face)==3 for m in self.parts for face in m['faces']))
        self.assertEqual(len({m['id'] for m in self.scene['meshes']}),len(self.scene['meshes']))

    def test_actual_retreat_bed_cannot_cover_walking_stones(self):
        from archpipe.concept.garden_render_review import soil_visibility_findings
        from archpipe.concept import villa_landscape as L, revit_spec as RS
        before=historical_aliases(json.loads(Path('tests/fixtures/garden-g4c-soil-before.json').read_text()))
        self.assertEqual(len(soil_visibility_findings(before)),2)
        self.assertEqual(soil_visibility_findings(self.scene),[])
        meshes,props,_,plan=L.review_candidate(RS.build(R.design('D1')))
        soil=next(m for m in meshes if m['id']=='landscape-accent-bed-north')
        soil['faces']=deepcopy(before['meshes'][0]['faces'])
        self.assertIn('soil obscured',str(L.candidate_violations(meshes,props,plan,R.design('D1'))))

    def test_real_rear_soil_cannot_alias_main_bed_subject(self):
        from scripts.villa_render_views import subject_mesh_frame_violations
        frozen=historical_aliases(json.loads(Path('tests/fixtures/garden-g4c-subject-prefix-before.json').read_text()))
        self.assertIn('behind camera',subject_mesh_frame_violations(frozen['view'],frozen,'landscape-bed-north'))
        matched=[m for m in self.scene['meshes'] if m['id'].startswith('landscape-bed-north')]
        self.assertEqual([m['id'] for m in matched],['landscape-bed-north'])
        self.assertEqual(subject_mesh_frame_violations(frozen['view'],self.scene,'landscape-bed-north'),[])

    def test_real_framed_but_occluded_garden_subjects_and_sibling(self):
        from archpipe.concept.garden_render_review import subject_visibility_findings,subject_visibility_evidence
        frozen=historical_aliases(json.loads(gzip.decompress(Path('tests/fixtures/garden-g4c-visibility-before.json.gz').read_bytes())))
        targets=['landscape-north-feature-stone','landscape-north-rhapis-accent','landscape-north-back-02']
        frozen['view']['visibility_targets']=targets
        from scripts.villa_render_views import subject_mesh_frame_violations
        for subject in targets:self.assertEqual(subject_mesh_frame_violations(frozen['view'],frozen,subject),[])
        self.assertEqual(len(subject_visibility_findings(frozen['view'],frozen)),3)
        view=next(v for v in V.VIEWS(R.design('D1')) if v['id'].startswith('v37-'))
        self.assertEqual(view['visibility_targets'],targets)
        self.assertEqual(subject_visibility_findings(view,self.scene),[])
        rows=subject_visibility_evidence(view,self.scene)
        # G4f restored the original v37 camera; the denser G4e Rhapis screens
        # the stone to 6 of 13 rays, accepted by the recorded per-subject
        # allowance (lead decision 2026-10-08). Other subjects keep 7 of 13.
        self.assertEqual([r['visible'] for r in rows],[6,12,9])
        # Rename and translate real failing geometry: no villa IDs/coordinates
        # participate in the ray guard's rule.
        sibling=deepcopy(frozen)
        for m in sibling['meshes']:
            m['id']='sibling-'+m['id']
            for f in m['faces']:
                for p in f:p[0]+=10;p[1]-=8
        sibling['view']['id']='sibling-garden-view'
        sibling['view']['visibility_targets']=['sibling-'+t for t in targets]
        sibling['view']['camera']['position'][0]+=10
        sibling['view']['camera']['position'][1]-=8
        self.assertEqual(len(subject_visibility_findings(sibling['view'],sibling)),3)
        # Face order cannot change the deterministic actual-vertex samples.
        clean=deepcopy(self.scene)
        for m in clean['meshes']:m['faces'].reverse()
        self.assertEqual(subject_visibility_findings(view,clean),[])

    def test_real_lounge_door_mutation_and_translated_sibling_cones(self):
        openings=self.record['opening_centers_m'];center=[1.622,-26.7535]
        self.assertEqual(S.view_findings(self.parts,self.record,openings,center),[])
        bad=deepcopy(self.record);bad['center']=[3.0,openings[0][1]];meshes,_=S.build(bad)
        self.assertIn('lounge sightline cone',str(S.view_findings(meshes,bad,openings,center)))
        for m in meshes:
            for f in m['faces']:
                for p in f:p[0]+=11;p[1]-=8
        translated=deepcopy(bad);translated['center']=[14.0,bad['center'][1]-8];translated['id']='other-villa-chair'
        self.assertTrue(S.view_findings(meshes,translated,[(x+11,y-8) for x,y in openings],[center[0]+11,center[1]-8]))

    def test_real_seat_rotated_to_house_wall(self):
        self.assertEqual(S.seat_findings(deepcopy(self.scene),self.record),[])
        bad=deepcopy(self.record);bad['yaw_deg']=270.
        meshes,_=S.build(bad);scene=deepcopy(self.scene)
        scene['meshes']=[m for m in scene['meshes'] if not m.get('hanging_swing')]+meshes
        failures=S.seat_findings(scene,bad)
        self.assertIn('cannot see feature stone',str(failures))
        self.assertIn('central field filled',str(failures))
        self.assertGreater(scene['swing_view_evidence']['blocked_fraction'],.5)

    def test_live_soffit_rope_route_and_missing_part_mutations(self):
        missing=deepcopy(self.scene);missing['meshes']=[m for m in missing['meshes'] if m.get('part_kind')!='suspension-line']
        self.assertIn('missing suspension part',str(S.scene_findings(missing)))
        bad=deepcopy(self.scene)
        rope=next(m for m in bad['meshes'] if m.get('part_kind')=='suspension-line')
        for f in rope['faces']:
            for p in f:p[0]+=.2
        self.assertIn('disconnected',str(S.scene_findings(bad)))
        bad=deepcopy(self.scene);host=bad['mounting_hosts']['north-swing-balcony-soffit']
        source=next(m for m in bad['meshes'] if m['id']==host['source_mesh'])
        source['faces']=[f for f in source['faces'] if not all(abs(p[2]-self.record['soffit_m'])<1e-8 for p in f)]
        self.assertIn('live soffit',str(S.scene_findings(bad)))
        from archpipe.concept import villa_landscape as L
        envelope=S.envelope(self.parts,self.record)
        self.assertTrue(S.placement_findings(self.parts,self.record,[dict(id='other-option-walking-envelope',rect=envelope)]))
        self.assertTrue(all(m['mounting']['kind']=='suspended' for m in self.parts))

    def test_retreat_view_is_level_open_sky_24mm_and_framed(self):
        from scripts.villa_render_views import subject_mesh_frame_violations,camera_proximity_violations
        from archpipe.concept.garden_render_review import garden_camera_findings
        views=V.VIEWS(R.design('D1'))
        view=next(v for v in views if v['id'].startswith('v39'))
        self.assertEqual(view['camera']['lens_mm'],24)
        self.assertEqual(view['camera']['position'][2],view['camera']['target'][2])
        self.assertEqual(garden_camera_findings(view,self.scene),[])
        self.assertEqual(camera_proximity_violations(view,self.scene,{}),[])
        for subject in view['subjects']:self.assertEqual(subject_mesh_frame_violations(view,self.scene,subject),[])
        self.assertEqual([row['status'] for row in self.record['open_construction_items']],['UNVERIFIED']*3)
        self.assertEqual(self.record['decision'],S.DECISION)

if __name__=='__main__':unittest.main()
