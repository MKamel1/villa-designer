"""Frozen real G4e morphology, camera and independent interpretation proofs."""
from copy import deepcopy
import gzip,json
from pathlib import Path
import unittest
import numpy as np
from archpipe.concept import garden_g4e as E,villa_landscape as L
from archpipe.concept.garden_render_review import plant_form_findings


class ShadeHabit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=json.loads(gzip.decompress(Path('tests/fixtures/garden-g4e-before.json.gz').read_bytes()))
        cls.clean=[E.clump(m['id'],m['species'],m['center'],m['root_z_m'],L._plant_data(),bed=m['bed'],layer=m['planting_layer']) for m in cls.before['plants']]

    def test_actual_old_habits_fire_and_all_shared_builder_siblings_stay_quiet(self):
        self.assertEqual(len({f.split(':')[0] for f in E.habit_findings(self.before['plants'])}),10)
        self.assertEqual(plant_form_findings(self.clean),[])
        for old,new in zip(self.before['plants'],self.clean):
            self.assertEqual(old['id'],new['id']);self.assertEqual(old['center'],new['center']);self.assertEqual(old['root_z_m'],new['root_z_m'])
            for field in ('species','bed','planting_layer','spread_m'):self.assertEqual(old[field],new[field])
            old_points=np.array([p for f in old['faces'] for p in f]);new_points=np.array([p for f in new['faces'] for p in f])
            self.assertAlmostEqual(np.ptp(old_points[:,2]),np.ptp(new_points[:,2]),places=6)
            expected_spread=max(np.ptp(old_points,axis=0)[:2]) if new['species']=='Rhapis excelsa' else .5
            self.assertAlmostEqual(expected_spread,max(np.ptp(new_points,axis=0)[:2]),places=6)
            self.assertAlmostEqual(new_points[:,2].min(),new['root_z_m'],places=6)

    def test_actual_cane_tip_and_basal_stalk_mutations_fire(self):
        palm=deepcopy(next(m for m in self.clean if m['species']=='Rhapis excelsa'))
        for i in palm['canes'][0]['face_indices']:
            for p in palm['faces'][i]:p[2]+=.5
        self.assertTrue(any('bare cane' in f for f in E.habit_findings([palm])))
        leaf=deepcopy(next(m for m in self.clean if m['species']=='Aspidistra elatior'))
        for record in leaf['basal_leaves']:
            for i in record['petiole_face_indices']:
                for p in leaf['faces'][i]:p[:2]=leaf['center'][:]
        self.assertTrue(any('common basal stalk' in f for f in E.habit_findings([leaf])))
        leaf=deepcopy(next(m for m in self.clean if m['species']=='Aspidistra elatior'))
        for i in leaf['leaf_face_indices']:
            for p in leaf['faces'][i]:p[2]+=.7
        self.assertTrue(any('leaf mass' in f for f in plant_form_findings([leaf])))

    def test_identity_boundary_and_translated_other_villa_generalise(self):
        for species in ('Rhapis excelsa','Aspidistra elatior'):
            a=E.clump('other',species,[8,9],2,L._plant_data(),bed='other',layer='other')
            b=E.clump('landscape-other',species,[8,9],2,L._plant_data(),bed='other',layer='other')
            self.assertEqual(a,b);self.assertEqual(a['id'],'landscape-other');self.assertEqual(plant_form_findings([a]),[])
        old=deepcopy(self.before['plants'][0]);old['id']='other-villa-plant';old['root_z_m']+=8
        for face in old['faces']:
            for p in face:p[2]+=8
        self.assertTrue(E.habit_findings([old]))

    def test_real_g4e_vases_fail_physical_fountain_metrics_and_all_nine_stay_quiet(self):
        rejected=json.loads(gzip.decompress(Path('tests/fixtures/garden-g4f-rejected.json.gz').read_bytes()))['plants']
        self.assertEqual(len(rejected),9)
        for old in rejected:
            findings=E.habit_findings([old])
            self.assertTrue(any('outward tip lean' in f for f in findings))
            self.assertTrue(any('narrow strap' in f for f in findings))
            self.assertTrue(any('arch-over' in f for f in findings))
        for clean in (m for m in self.clean if m['species']=='Aspidistra elatior'):
            self.assertEqual(E.habit_findings([clean]),[])
            # Metadata cannot disguise real narrow faces; translated sibling
            # already exercises construction away from the D1 coordinates.
            thin=deepcopy(clean)
            axis=np.asarray(thin['center'])
            for i in thin['leaf_face_indices']:
                for p in thin['faces'][i]:p[:2]=(axis+(np.asarray(p[:2])-axis)*.3).tolist()
            self.assertTrue(any('narrow strap' in f for f in E.habit_findings([thin])))
            declared=deepcopy(clean)
            for record in declared['basal_leaves']:record['centreline']=[[0,0,0]]
            self.assertEqual(E.aspidistra_habit_metrics(declared),E.aspidistra_habit_metrics(clean))

    def test_whole_habit_detail_crop_fires_on_real_rejected_geometry_and_quiet_on_all_siblings(self):
        from scripts.garden_g6_preview import ortho_specimen_frame_findings
        rejected=json.loads(gzip.decompress(Path('tests/fixtures/garden-g4f-rejected.json.gz').read_bytes()))['plants']
        for mesh in rejected+[m for m in self.clean if m['species']=='Aspidistra elatior']:
            p=np.asarray(mesh['faces']).reshape(-1,3)
            origin=np.array([*(p[:,:2].min(0)+p[:,:2].max(0))/2,p[:,2].min()])
            local=p-origin
            self.assertTrue(ortho_specimen_frame_findings(local,[.7,-.9,.85],[0,0,.02],.65,4/3))
            self.assertEqual(ortho_specimen_frame_findings(local,[.7,-.9,.85],[0,0,.25],.82,4/3),[])
            offset=np.array([8.,-5.,2.])
            self.assertEqual(ortho_specimen_frame_findings(local+offset,np.array([.7,-.9,.85])+offset,
                np.array([0,0,.25])+offset,.82,4/3),[])


class EveningScope(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from archpipe.concept import villa_render as V
        cls.scene=V.build()
        cls.before=json.loads(gzip.decompress(Path('tests/fixtures/garden-g4e-before.json.gz').read_bytes()))
        cls.view=next(v for v in cls.scene['views'] if v['id']=='v42-north-garden-evening')

    def test_real_foreground_fitting_camera_mutation_and_clear_other_name(self):
        old=self.before['view'];self.assertTrue(E.foreground_fixture_findings(old,self.scene))
        self.assertEqual(E.foreground_fixture_findings(self.view,self.scene),[])
        renamed=deepcopy(self.view);renamed['id']='other-garden-evening'
        self.assertEqual(E.foreground_fixture_findings(renamed,self.scene),[])
        renamed['camera']=deepcopy(old['camera'])
        self.assertTrue(E.foreground_fixture_findings(renamed,self.scene))
        without=dict(self.scene,meshes=[m for m in self.scene['meshes'] if not m.get('garden_g4d')])
        self.assertEqual(E.foreground_fixture_findings(old,without),[])

    def test_view_number_alias_and_duplicate_sibling_fail_closed(self):
        from archpipe.villa_render_contract import validate_scene
        self.assertEqual(self.view['aliases'],['v41-north-garden-evening'])
        self.assertEqual(validate_scene(self.scene),[])
        bad=dict(self.scene,views=[dict(v,id='v41-another-garden') if v['id']==self.view['id'] else v for v in self.scene['views']])
        self.assertTrue(any('unique view number' in f for f in validate_scene(bad)))
        bad=dict(self.scene,views=[dict(v,id='v07-another-garden') if v['id']==self.view['id'] else v for v in self.scene['views']])
        self.assertTrue(any('unique view number' in f for f in validate_scene(bad)))

    def test_fixture_record_material_basis_and_locked_inputs_unchanged(self):
        from archpipe.concept import garden_g4d as D
        self.assertEqual(D.fixture_record(self.scene),[]);self.assertEqual(D.material_basis(self.scene),[])
        self.assertEqual(self.scene['garden_g4d']['fixtures'],self.before['fixtures'])
        self.assertEqual(self.scene['sky'],self.before['sky'])
        self.assertEqual(self.scene['materials']['north-pale-gravel'],self.before['materials']['north-pale-gravel'])
        self.assertEqual(self.view['dimmers'],self.before['view']['dimmers']);self.assertEqual(self.view['layers_on'],self.before['view']['layers_on'])
        from archpipe.concept.garden_render_review import garden_camera_findings
        self.assertEqual(garden_camera_findings(dict(id='other-interior',subjects=[]),{}),[])

    def test_faithful_dusk_cast_is_disclosed_fail_with_unchanged_locked_policy(self):
        disclosure=self.view['faithful_colour_cast']
        self.assertEqual(disclosure['colour_cast_status'],'FAIL')
        self.assertEqual(disclosure['highlights_status'],'WARN')
        self.assertEqual(disclosure['sky_blue_red_ratio'],1.379)
        self.assertEqual(disclosure['lamp_blue_red_ratio'],.0996)
        self.assertEqual(disclosure['colour_cast_limit'],.02)
        caption=' '.join(self.view['caption_notes'])
        for required in ('Faithful cool cast','1.379','0.0996','colour_cast FAIL','highlights WARN','docs/garden-g4e-report.md'):
            self.assertIn(required,caption)
        self.assertNotIn('qa_allowances',self.view)

    def test_neutral_context_disables_actual_emission_and_principled_sibling(self):
        from types import SimpleNamespace
        from scripts.garden_g6_preview import disable_material_emission
        a=SimpleNamespace(default_value=5);b=SimpleNamespace(default_value=12);c=SimpleNamespace(default_value=.7)
        nodes=[SimpleNamespace(type='EMISSION',inputs={'Strength':a}),SimpleNamespace(type='BSDF_PRINCIPLED',inputs={'Emission Strength':b,'Roughness':c})]
        material=SimpleNamespace(use_nodes=True,node_tree=SimpleNamespace(nodes=nodes))
        disable_material_emission({'actual-runtime-lens':material})
        self.assertEqual((a.default_value,b.default_value,c.default_value),(0,0,.7))
        disable_material_emission({'renamed-sibling':material})
        self.assertEqual((a.default_value,b.default_value),(0,0))
