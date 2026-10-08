"""Actual committed garden preservation, new optical/mount records and defects."""
import ast
from copy import deepcopy
import gzip
import json
import math
from pathlib import Path
from types import SimpleNamespace
import unittest

from archpipe.concept import garden_g4d as G
from archpipe.concept.garden_render_review import (
    garden_camera_findings,subject_frame_findings,downward_ground_findings,plant_form_findings)
from archpipe.concept.mounting import scene_findings as mounting_findings
from scripts.garden_g6_preview import input_findings,staging_findings,receipt_findings,canonical_hash

FIXTURES=Path(__file__).parent/'fixtures'


class GardenBrightening(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=json.loads(gzip.decompress((FIXTURES/'garden-g4d-input-before.json.gz').read_bytes()))
        cls.scene=deepcopy(cls.before)
        cls.scene['lights']=[]
        G.integrate(cls.scene)

    def test_real_layout_faces_routes_plants_swing_and_undersides_unchanged(self):
        by={m['id']:m for m in self.scene['meshes']}
        for old in self.before['meshes']:
            self.assertEqual(old['faces'],by[old['id']]['faces'])
            if old.get('species') or old.get('hanging_swing'):
                self.assertEqual(old,by[old['id']])
        self.assertEqual(len(self.scene['garden_g4d']['changed_finishes']),7)
        self.assertEqual(downward_ground_findings(self.scene),[])
        self.assertEqual(plant_form_findings(self.scene['meshes']),[])
        south=next(m for m in self.scene['meshes'] if m['id']=='landscape-tree-pit-south')
        self.assertEqual(south['material'],'garden-gravel')

    def test_live_fixture_material_and_c4_mount_records_clean(self):
        self.assertEqual(G.material_basis(self.scene),[])
        self.assertEqual(G.fixture_record(self.scene),[])
        self.assertEqual(G.scene_findings(self.scene),[])
        focused=dict(self.scene,meshes=[m for m in self.scene['meshes'] if m.get('garden_g4d')])
        self.assertEqual(mounting_findings(focused),[])
        self.assertEqual(len(self.scene['garden_g4d']['fixtures']),4)
        from archpipe import photometry as P
        from archpipe.concept.villa_lighting import generic_ies
        distribution=P.parse(generic_ies(G.FLUX_LM,G.BEAM_DEG,'ASSUMED GARDEN-UP'))
        self.assertGreater(distribution.candela[0][0],distribution.candela[3][0])

    def test_reflectance_basis_and_texture_scale_fail_closed(self):
        for field in ('basis_status','reflectance_basis','reflectance'):
            bad=deepcopy(self.scene);del bad['materials'][G.GRAVEL][field]
            self.assertTrue(G.material_basis(bad),field)
        bad=deepcopy(self.scene);bad['materials'][G.GRAVEL]['procedural_gravel_m']=1.
        self.assertTrue(G.material_basis(bad))
        bad=deepcopy(self.scene);bad['materials'][G.STONE]['base_rgb']=[.1,.1,.1]
        self.assertTrue(G.material_basis(bad))

    def test_actual_source_flux_is_not_shielded_fitting_output(self):
        from archpipe.photometry import parse
        old=json.loads((FIXTURES/'garden-g4d-photometry-before.json').read_text())
        record=self.scene['garden_g4d']['fixtures'][0]
        self.assertEqual(old['record']['flux_lm'],record['flux_lm'])
        self.assertNotIn('shield_output',old['record'])
        estimate=G.shield_output(old['ies'],record['flux_lm'],record['shielding'])
        self.assertEqual(estimate,record['shield_output'])
        self.assertEqual(estimate['status'],'ASSUMED')
        low,high=estimate['emitted_flux_lm_bounds']
        self.assertTrue(92.<low<high<94.)
        # Independent 5000-interval solid-angle midpoint integration of the
        # retained real source distribution (angles radians, intensity candela).
        source=parse(old['ies'])
        def integrate(degrees):
            step=math.radians(degrees)/5000
            return sum(source.intensity(math.degrees((i+.5)*step),0)*math.sin((i+.5)*step)*math.tau*step for i in range(5000))
        for cutoff,value in zip(estimate['cutoff_deg'],(low,high)):
            self.assertAlmostEqual(value,120.*integrate(cutoff)/integrate(180.),delta=.005)
        wider=G.shield_output(old['ies'],120.,dict(record['shielding'],aperture_radius_m=.07,facet_count=32))
        self.assertGreater(wider['emitted_flux_lm_bounds'][0],high)
        for defect in ('missing-basis','missing-output','fake-output','missing-facets'):
            bad=deepcopy(self.scene);r=bad['garden_g4d']['fixtures'][0]
            if defect=='missing-basis':r.pop('flux_basis')
            elif defect=='missing-output':r.pop('shield_output')
            elif defect=='fake-output':r['shield_output']['emitted_flux_lm_bounds']=[120.,120.]
            else:r['shielding'].pop('facet_count')
            next(l for l in bad['lights'] if l['id']==r['id'])['fixture_record']=deepcopy(r)
            self.assertTrue(G.fixture_record(bad),defect)
    def test_shifted_missing_lens_shield_and_light_record_fire(self):
        for defect in ('position','lumens','missing-lens','shifted-lens','short-shield','missing-source','missing-record'):
            bad=deepcopy(self.scene);record=bad['garden_g4d']['fixtures'][0]
            light=next(l for l in bad['lights'] if l['id']==record['id'])
            if defect=='position':light['position']=[0,0,0]
            elif defect=='lumens':light['lumens']=1200
            elif defect=='missing-lens':bad['meshes']=[m for m in bad['meshes'] if m['id']!=record['lens_id']]
            elif defect in ('shifted-lens','short-shield'):
                mid=record['lens_id'] if defect=='shifted-lens' else record['body_ids'][1]
                mesh=next(m for m in bad['meshes'] if m['id']==mid)
                for face in mesh['faces']:
                    for point in face:point[0]+=.08
            elif defect=='missing-source':
                body=next(m for m in bad['meshes'] if m['id']==record['body_ids'][0])
                source=bad['mounting_hosts'][body['mounting']['host_id']]['source_mesh']
                bad['meshes']=[m for m in bad['meshes'] if m['id']!=source]
            else:del bad['garden_g4d']
            self.assertTrue(G.scene_findings(bad),defect)
        bad=deepcopy(self.scene)
        rogue=deepcopy(next(m for m in bad['meshes'] if m.get('garden_g4d')))
        rogue['id']='unregistered-uplight-part';bad['meshes'].append(rogue)
        self.assertTrue(G.fixture_record(bad))

    def test_glare_eye_envelopes_and_on_axis_negative_control(self):
        records=self.scene['garden_g4d']['fixtures']
        rows=G.glare_evidence(records,G.observers(self.scene))
        self.assertEqual(len(rows),116)
        self.assertTrue(all(r['visible_lens_samples']==0 for r in rows))
        first=records[0]
        eye=[p+2*a for p,a in zip(first['emitter_m'],first['aim'])]
        self.assertEqual(G.glare_evidence([first],{'on-axis':eye})[0]['visible_lens_samples'],17)
        bad=deepcopy(first);bad['shielding']['snoot_depth_m']=.005
        self.assertTrue(any(r['visible_lens_samples'] for r in G.glare_evidence([bad],G.observers(self.scene))))

    def test_new_camera_full_actual_frame_open_sky_and_evening_only(self):
        view=G.evening_view()
        self.assertEqual(garden_camera_findings(view,self.scene),[])
        self.assertEqual(subject_frame_findings(view,self.scene),[])
        self.assertEqual(view['camera']['lens_mm'],24)
        self.assertEqual(view['camera']['position'][2],view['camera']['target'][2])
        self.assertEqual(view['layers_on'],[G.LAYER])
        bad=deepcopy(view);bad['camera']['position']=[2.85,-26.4,-1.65]
        self.assertTrue(garden_camera_findings(bad,self.scene))
        bad=deepcopy(view);bad['camera']['shift_y']+=.5
        self.assertTrue(subject_frame_findings(bad,self.scene))
        bad=deepcopy(self.scene);bad['views'][0]['layers_on'].append(G.LAYER)
        self.assertTrue(G.scene_findings(bad))

    def test_renamed_translated_fixture_sibling(self):
        before=deepcopy(self.before)
        before['lights']=[]
        # Translate the actual physical garden and rename its plants;
        # fixture construction and finite support must use data, not D1 IDs.
        for mesh in before['meshes']:
            for face in mesh['faces']:
                for point in face:point[0]+=5.;point[1]+=8.;point[2]+=2.
            if mesh.get('species') and mesh.get('bed','').startswith('north'):
                mesh['id']='other-'+mesh['id'];mesh['center']=[mesh['center'][0]+5.,mesh['center'][1]+8.]
                mesh['root_z_m']+=2.
        G.integrate(before)
        self.assertEqual(G.fixture_record(before),[])
        light=before['lights'][0];light['position'][2]+=.1
        self.assertTrue(G.fixture_record(before))


class PreviewControls(unittest.TestCase):
    def test_real_prop_delivery_boundary_preserves_coordinates_and_refuses_moves(self):
        from scripts.garden_g4d_evidence import delivery_value
        delivered=json.loads((FIXTURES/'garden-g4d-delivery-prop.json').read_text())
        native=deepcopy(delivered)
        native['position']=tuple(native['position'])
        native['mounting']['finished_face']=tuple(native['mounting']['finished_face'])
        self.assertNotEqual(native,delivered)
        self.assertEqual(delivery_value(native),delivered)
        native['position']=(native['position'][0]+.001,*native['position'][1:])
        self.assertNotEqual(delivery_value(native),delivered)

    def test_actual_fixture_consumer_metadata_omission_and_sibling(self):
        light=json.loads((FIXTURES/'garden-g4d-fixture-metadata-before.json').read_text())
        self.assertEqual(len(G.fixture_metadata_findings([light])),2)
        light['id']='other-uplight'
        self.assertEqual(len(G.fixture_metadata_findings([light])),2)
        light.update(cri=90,product=dict(manufacturer='GENERIC',code='ASSUMED GARDEN-UP',generic=True))
        self.assertEqual(G.fixture_metadata_findings([light]),[])

    def test_real_coincident_floor_and_missing_runtime_material_siblings(self):
        old=json.loads((FIXTURES/'garden-g4d-preview-before.json').read_text())
        ground=old['ground'];origin=old['staging_origin']
        self.assertTrue(staging_findings([ground],origin,old['floor_z']))
        self.assertEqual(staging_findings([ground],origin,-.005),[])
        sibling=deepcopy(ground);sibling['id']='other-ground'
        for face in sibling['faces']:
            for point in face:point[2]+=7.
        self.assertTrue(staging_findings([sibling],[0,0,4.],0.))
        data=dict(materials={n:{} for n in old['material_names']},assemblies=[dict(id='actual-old-lens',meshes=[dict(material=old['missing_material'])])])
        self.assertTrue(input_findings(data))
        data['materials'][old['missing_material']]={}
        self.assertEqual(input_findings(data),[])

    def test_preview_receipt_rejects_changed_geometry_light_and_material(self):
        ground=json.loads((FIXTURES/'garden-g4d-preview-before.json').read_text())['ground']
        data=dict(materials={ground['material']:{'reflectance':.7}},assemblies=[dict(id='ground',meshes=[ground],lights=[{'lumens':120}])])
        receipt=[dict(id='ground',source_geometry_sha256=canonical_hash([ground]),source_lights_sha256=canonical_hash([{'lumens':120}]),
                      source_materials_sha256=canonical_hash(data['materials']),staging=dict(origin=[0,0,-3.],floor_z=-.005))]
        self.assertEqual(receipt_findings(data,receipt),[])
        for field in ('source_geometry_sha256','source_lights_sha256','source_materials_sha256'):
            bad=deepcopy(receipt);bad[0][field]='stale';self.assertTrue(receipt_findings(data,bad))

    def test_actual_vertex_consumer_does_not_project_empty_bound_corners(self):
        tree=ast.parse(Path('src/archpipe/blender/villa_scene.py').read_text())
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='subjects')
        class Identity:
            def __matmul__(self,p):return p
        mesh=dict(id='plant',faces=[[[.2,.1,1],[.8,.1,1],[.5,.9,1]]])
        obj=SimpleNamespace(matrix_world=Identity())
        namespace=dict(bpy=SimpleNamespace(context=SimpleNamespace(scene=SimpleNamespace(camera=None))),
            Vector=lambda p:SimpleNamespace(x=p[0],y=p[1],z=p[2]),
            world_to_camera_view=lambda scene,camera,p:p,
            contract=SimpleNamespace(mesh_bbox_corners=lambda m:[[.2,-.3,1],[.8,1.1,1]]))
        exec(compile(ast.fix_missing_locations(ast.Module(body=[function],type_ignores=[])),'actual-function','exec'),namespace)
        old=namespace['subjects']({'subjects':['plant']},[mesh],{'plant':obj})
        self.assertTrue(old[0]['in_frame']);self.assertFalse(old[0]['full_frame'])
        clean=namespace['subjects']({'subjects':['plant'],'require_full_subject_frame':True},[mesh],{'plant':obj})
        self.assertTrue(clean[0]['full_frame']);self.assertEqual(clean[0]['screen'],[.2,.1,.8,.9])


if __name__=='__main__':unittest.main()
