"""Real G6 candidate mutations prove support/circle/route/wall controls."""
import unittest
from copy import deepcopy
from archpipe.concept import garden_g6 as G,villa_landscape as L


class GardenG6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.meshes,cls.plants,cls.objects,cls.plan=G.build()

    def test_clean_candidate_measures_geometry_and_all_routes(self):
        self.assertEqual(G.findings(self.meshes,self.plan),[])
        self.assertEqual(L.dimension_violations(self.plants),[])
        self.assertEqual(L.route_violations(self.meshes),[])
        self.assertEqual(L.spacing_violations(self.plants),[])
        from archpipe.concept.physical_part import geometry_errors
        for m in self.meshes:self.assertEqual(geometry_errors(m['faces'],surface=m.get('surface',False),occupied_side=m.get('occupied_side')),[],m['id'])
        self.assertTrue(.5<=self.plan['roof_leaf_cover_fraction']<=.6)

    def test_real_pergola_move_into_d4_circle_fails(self):
        moved=deepcopy(self.meshes)
        for m in moved:
            if m.get('pergola_role'):
                m['faces']=[[[p[0],p[1]+2,p[2]] for p in f] for f in m['faces']]
        self.assertTrue(any('mature tree circle' in reason for _,reason in G.findings(moved,self.plan)))

    def test_real_posts_lift_and_missing_bearing_fail(self):
        raised=deepcopy(self.meshes)
        p=next(m for m in raised if m.get('pergola_role')=='post')
        for f in p['faces']:
            for q in f:q[2]+=.1
        failures=G.findings(raised,self.plan)
        self.assertTrue(any('not at grade' in r for _,r in failures))
        self.assertTrue(any('post bearings' in r for _,r in failures))
        omitted=[m for m in self.meshes if m['id']!=p['id']]
        self.assertTrue(any('post bearings' in r for _,r in G.findings(omitted,self.plan)))

    def test_real_wire_off_wall_and_root_mutations_fail(self):
        moved=deepcopy(self.meshes)
        wire=next(m for m in moved if m.get('espalier_role')=='wire')
        for f in wire['faces']:
            for p in f:p[1]-=.025
        self.assertTrue(any('wall face' in r for _,r in G.findings(moved,self.plan)))
        climber=next(m for m in moved if m.get('g6_element')=='climber');climber['root_z_m']+=.1
        self.assertTrue(any('not grounded' in r for _,r in G.findings(moved,self.plan)))

    def test_renamed_translated_pergola_guard_generalises(self):
        shifted=deepcopy(self.meshes);plan=deepcopy(self.plan)
        for m in shifted:
            m['id']='other-'+m['id']
            m['faces']=[[[p[0],p[1]+.01,p[2]] for p in f] for f in m['faces']]
            if m.get('center'):m['center']=[m['center'][0],m['center'][1]+.01]
        plan['post_centers_m']=[[x,y+.01] for x,y in plan['post_centers_m']]
        plan['assumptions']['pergola_rect_m']=[v+.01 if i in (1,3) else v for i,v in enumerate(plan['assumptions']['pergola_rect_m'])]
        findings=G.findings(shifted,plan,tree_center=(25.577,-24.401115286384),routes={k:(r[0],r[1]+.01,r[2],r[3]+.01) for k,r in L.PATHS.items()})
        # Espalier physical site face is unchanged, so the wall mutation fires;
        # renamed geometry still passes the independent pergola checks.
        self.assertTrue(any('wall face' in r for _,r in findings))
        self.assertFalse(any('pergola' in r or 'post' in r or 'rafter' in r or 'not grounded' in r for _,r in findings))

    def test_sunniest_wall_reproduces_geometry_rays(self):
        from archpipe.concept.garden_sun import default_study,DATES
        evidence=G.wall_sun_evidence(default_study())
        self.assertEqual(evidence,self.plan['sun_evidence'])
        self.assertEqual(evidence['selected_wall'],'east')
        values={r['wall']:r['means'][DATES[0]] for r in evidence['walls']}
        self.assertEqual(values,{'south':3.2,'west':3.8,'east':6.4})

    def test_actual_wall_evidence_survives_export_readback_and_mutations(self):
        import json
        from archpipe.concept.garden_sun import default_study
        actual=G.wall_sun_evidence(default_study())
        exported=json.loads(json.dumps(actual))
        self.assertEqual(actual,exported)
        for wall in exported['walls']:
            wall['points_m'][0][0]+=.01
        self.assertNotEqual(actual,exported)

    def test_actual_corner_root_audit_names_garden_not_nearest_house_face(self):
        from archpipe.concept.garden_sun import audit_plants
        class Study:
            def hours(self,*args):return [9,10,11,12]
        plant=deepcopy(next(m for m in self.meshes if m.get('species')=='Petrea volubilis'))
        self.assertEqual(plant['center'],[22.81,-29.75])
        self.assertEqual(L.geometry_zone(*plant['center']),'west')
        for name in (plant['id'],'another-garden-vine'):
            plant['id']=name
            self.assertEqual(audit_plants([plant],Study())[0]['zone'],'south')
        plant['center']=[20.,-30.]
        self.assertEqual(audit_plants([plant],Study())[0]['zone'],'west')

    def test_tag_cannot_admit_legacy_furniture_or_unknown_species(self):
        bad=dict(id='landscape-bistro',g6_element='furniture',part_kind='cafe-table')
        self.assertTrue(G.content_findings([bad]))
        bad=deepcopy(self.plants[0]);bad['species']='Bauhinia variegata'
        self.assertTrue(G.content_findings([bad]))

    def test_entire_removed_pergola_fails_closed(self):
        stripped=[m for m in self.meshes if not m.get('pergola_role')]
        self.assertTrue(any('members' in r for _,r in G.findings(stripped,self.plan)))

    def test_frozen_real_basal_leaf_gap_and_sibling(self):
        import gzip,json
        from pathlib import Path
        from archpipe.concept.garden_render_review import plant_form_findings
        path=Path(__file__).parent/'fixtures/garden-g6-leaf-gap-before.json.gz'
        before=json.loads(gzip.decompress(path.read_bytes()))
        meshes=before.get('meshes',before) if isinstance(before,dict) else before
        self.assertTrue(plant_form_findings(meshes))
        self.assertEqual(plant_form_findings(self.meshes),[])
        mutated=deepcopy(self.meshes)
        leaf=next(m for m in mutated if m.get('g6_element')=='climber')
        leaf['id']='renamed-vine'
        leaf['leaf_face_indices']=[i for i in leaf['leaf_face_indices'] if min(q[2] for q in leaf['faces'][i])>leaf['root_z_m']+.3]
        self.assertTrue(plant_form_findings(mutated))

class IntegrationReproductions(unittest.TestCase):
    def test_actual_raised_container_sun_sampling_and_translated_sibling(self):
        import json
        from pathlib import Path
        from archpipe.concept.garden_sun import audit_plants,DATES
        frozen=json.loads(Path('tests/fixtures/garden-g6-root-sample-before.json').read_text())
        class Study:
            def __init__(self):self.samples=[]
            def hours(self,x,y,z,date):self.samples.append((x,y,z,date));return [10,11,12,13]
        for plant in frozen:
            self.assertEqual(plant['root_z_m'],plant['actual_base_m'])
            self.assertNotEqual(plant['root_z_m'],plant['reported_ground_m'])
        for shift in (0.,7.):
            plants=deepcopy(frozen)
            for plant in plants:plant['root_z_m']+=shift;plant['id']='independent-'+plant['id']
            study=Study();report=audit_plants(plants,study)
            for plant,row in zip(plants,report):
                self.assertEqual(row['ground_m'],plant['root_z_m'])
                self.assertEqual([s for s in study.samples if s[:2]==tuple(plant['center'])],
                                 [(*plant['center'],plant['root_z_m'],d) for d in DATES])
        fallback=deepcopy(frozen[0]);fallback.pop('root_z_m')
        self.assertEqual(audit_plants([fallback],Study())[0]['ground_m'],-3.)

    def test_actual_post_door_failure_clean_and_renamed_sibling(self):
        import json
        from pathlib import Path
        from archpipe.concept.render_support import blocked_openings
        frozen=json.loads((Path(__file__).parent/'fixtures/garden-g6-door-post-before.json').read_text())
        self.assertTrue(blocked_openings(dict(meshes=[frozen])))
        frozen['id']='other-project-timber-post'
        self.assertTrue(blocked_openings(dict(meshes=[frozen])))
        meshes,_,_,_=G.build()
        self.assertEqual(blocked_openings(dict(meshes=meshes)),[])

    def test_actual_soil_cut_preserves_soil_and_removes_thin_caps(self):
        from archpipe.concept.garden_render_review import soil_visibility_findings
        meshes,_,_,_=G.build()
        soil=deepcopy(next(m for m in meshes if m['part_kind']=='soil-bed'))
        cap=deepcopy(soil);cap.update(id='landscape-actual-thin-cap',material='artificial-grass',part_kind='finish-layer')
        for f in cap['faces']:
            for p in f:p[2]+=.003
        case=[soil,cap]
        self.assertTrue(soil_visibility_findings(dict(meshes=case)))
        original=deepcopy(soil)
        L.reveal_ground_soil(case,case)
        self.assertEqual(soil,original)
        self.assertEqual(soil_visibility_findings(dict(meshes=case)),[])
        # A translated soil datum and renamed material/member use the same construction.
        for m in case:
            for f in m['faces']:
                for p in f:p[2]+=8
        L.reveal_ground_soil(case,case)
        self.assertTrue(soil['faces'])

    def test_missing_entire_g6_cannot_bypass_scene_guard(self):
        _,_,_,plan=G.build()
        # Detection occurs before needing enclosure rays on an empty case.
        self.assertTrue(G.findings([],plan))

    def test_actual_live_clear_height_and_missing_loquat_fail(self):
        meshes,_,_,plan=G.build()
        mutant=deepcopy(meshes)
        for m in mutant:
            if m.get('pergola_role')=='beam':
                for f in m['faces']:
                    for p in f:p[2]+=.05
        self.assertTrue(any('physical clear height' in r for _,r in G.findings(mutant,plan)))
        self.assertTrue(any('loquat required' in r for _,r in G.findings([m for m in meshes if m.get('species')!='Eriobotrya japonica'],plan)))

class SeatingAccess(unittest.TestCase):
    def test_real_four_chair_aisle_conflict_current_family_seating_and_sibling(self):
        import json
        from pathlib import Path
        meshes,_,_,plan=G.build()
        accesses={k:plan['assumptions'][k] for k in ('seating_access_rect_m','seating_cross_access_rect_m')}
        before=json.loads((Path(__file__).parent/'fixtures/garden-g6-seating-before.json').read_text())
        self.assertTrue(L.route_violations(before,accesses))
        for m in before:m['id']='another-villa-'+m['id']
        self.assertTrue(L.route_violations(before,accesses))
        self.assertEqual(G.findings(meshes,plan),[])
        seating=[m for m in meshes if m.get('g6_element')=='furniture']
        self.assertEqual(sum(m['seats'] for m in seating),4)
        self.assertEqual(len(seating),3)
        moved=deepcopy(seating)
        for m in moved:
            for f in m['faces']:
                for p in f:p[0]+=.2
        self.assertTrue(L.route_violations(moved,accesses))

class RetainedEdging(unittest.TestCase):
    def test_real_cut_edging_siblings_and_clean_construction(self):
        import gzip,json
        from pathlib import Path
        from archpipe.concept.physical_part import geometry_errors
        before=json.loads(gzip.decompress((Path(__file__).parent/'fixtures/garden-g6-edging-cut-before.json.gz').read_bytes()))
        self.assertTrue(all(geometry_errors(m['faces']) for m in before))
        record=json.loads(L.PALETTE.read_text())['design_assumptions']['north_garden_g4']
        x0,y0,x1,y1=record['beds']['north'];g=L.GROUND
        edge=L._mesh('real-north-edging','ground','trellis',L._box(x0,y0,g,x1,y0+.015,g+.018),'actual north slim edging',kind='bed-edge')
        bed=L._mesh('real-north-soil','ground','garden-soil',L._quad(x0,y0,x1,y1,g),'actual north soil',kind='soil-bed',surface=True,occupied_side=(0,0,1))
        original=deepcopy(edge);L.reveal_ground_soil([edge],[bed])
        self.assertEqual(edge,original);self.assertEqual(geometry_errors(edge['faces']),[])
        edge['id']='renamed-intentional-bed-edge';bed['id']='renamed-soil'
        for m in (edge,bed):
            for f in m['faces']:
                for p in f:p[2]+=5
        original=deepcopy(edge);L.reveal_ground_soil([edge],[bed])
        self.assertEqual(edge,original)
