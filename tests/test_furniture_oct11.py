"""Real source-cover and seat-driven chair regressions, with renamed siblings."""
from copy import deepcopy
import gzip,json,sys
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from prepare_furniture_oct11 import bed_without_source_covers
from archpipe.furniture_fit import model_fit,require_furniture_geometry,native_box,review_selection,replacement_floor
from archpipe.beds import retained_model_rows,require_bed_geometry
from archpipe.concept.furniture_stage2 import derived_seats
from archpipe.blender.import_identity import namespace_objects
from types import SimpleNamespace
import tempfile
from archpipe.asset_intake import audit_scene_manifest
from unittest.mock import patch
from archpipe.concept import parents_bed
FIX=ROOT/'tests/fixtures'
def read(name):return json.loads(gzip.decompress((FIX/name).read_bytes()))
class FurnitureOctober11(unittest.TestCase):
    def apply_parent_case(self,case):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'receipt.json.gz'
            path.write_bytes(gzip.compress(json.dumps(case['receipt']).encode(),mtime=0))
            with patch.object(parents_bed,'RECEIPT',path):
                c=case['context']
                return parents_bed.apply(case['scene'],c['layout'],c['specification'],c['furniture'])

    def test_actual_accepted_parent_context_and_empty_view_subset_keep_bound_room_review(self):
        case=read('parents-bed-activation.json.gz');result=self.apply_parent_case(case)
        self.assertEqual(result['parents_bed']['status'],'active')
        self.assertEqual(result['bed_room_review']['layout_findings'],case['receipt']['room_review']['review']['layout_findings'])
        case['scene']['views']=[]
        self.assertEqual(self.apply_parent_case(case)['parents_bed']['status'],'active')

    def test_actual_parent_room_camera_cloth_and_baseline_mutations_refuse(self):
        original=read('parents-bed-activation.json.gz')
        changed=deepcopy(original);changed['scene']['meshes'][0]['faces'][0][0][0]+=.01
        with self.assertRaisesRegex(ValueError,'room inputs changed'):self.apply_parent_case(changed)
        changed=deepcopy(original);changed['scene']['views'][0]['camera']['position'][0]+=.01
        with self.assertRaisesRegex(ValueError,'camera changed'):self.apply_parent_case(changed)
        changed=deepcopy(original);cloth=next(c for c in changed['scene']['cloth'] if c['id']=='duvet-pb-bed');cloth['thickness']+=.001
        with self.assertRaisesRegex(ValueError,'cloth changed'):self.apply_parent_case(changed)
        changed=deepcopy(original);changed['receipt']['baseline_cloth'][0]['faces'][0][0][0]+=.01
        with self.assertRaisesRegex(ValueError,'room review changed'):self.apply_parent_case(changed)

    def test_real_independent_bed_scale_audit_and_renamed_sibling(self):
        case=json.loads((FIX/'bed-independent-scale-audit.json').read_text())
        for name in ('sf_bed_upholstered_cyberfox','other-villa-source-bed'):
            entry=deepcopy(case['entry']);entry['id']=name
            model=deepcopy(case['model']);model['asset']=name
            with tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'manifest.json';scene=dict(models=[model],props=[])
                path.write_text(json.dumps(dict(props=[entry])))
                failures=audit_scene_manifest(path,scene)['placed']
                self.assertIn('placement_scale_factors require code source',failures[name])
                entry['placement_scale_source']='archpipe.beds.scaled_model_fit -> Blender anchor scale_xyz'
                path.write_text(json.dumps(dict(props=[entry])))
                self.assertEqual(audit_scene_manifest(path,scene)['placed'],{})
                model['scale_xyz'][0]*=.99
                self.assertIn('placement_scale_factors disagree with built scene',audit_scene_manifest(path,scene)['placed'][name])

    def test_real_import_empty_node_names_and_renamed_sibling_are_namespaced(self):
        # Actual Leaves hierarchy nodes claimed these names before the next
        # CyberFox/leather source import. Mesh-only renaming left them behind.
        for identity in ('model-study-desk','other-room-desk'):
            empty=SimpleNamespace(name='Object_4',type='EMPTY',parent=None)
            mesh=SimpleNamespace(name='Object_4_OK-timber_0',type='MESH',parent=empty)
            namespace_objects([empty,mesh],identity)
            self.assertNotEqual(empty.name,'Object_4')
            self.assertEqual(empty.name,'model-'+identity+'-Object_4')
            self.assertIs(mesh.parent,empty)

    def test_real_basement_floor_and_translated_sibling_derive_from_fallback_bodies(self):
        case=json.loads((FIX/'chair-floor-before.json').read_text())
        self.assertEqual(replacement_floor(case['scene'],case['model']),case['actual_floor_m'])
        self.assertNotEqual(case['actual_floor_m'],case['wrong_floor_m'])
        for row in case['scene']['meshes']:
            row['faces']=[[[p[0],p[1],p[2]+6] for p in face] for face in row['faces']]
        self.assertAlmostEqual(replacement_floor(case['scene'],case['model']),case['actual_floor_m']+6)
        case['model']['replacement_mesh_ids'].append('missing-body')
        with self.assertRaisesRegex(ValueError,'every exact'):replacement_floor(case['scene'],case['model'])

    def test_real_bedding_omission_keeps_frame_and_mattress_triangles_intact(self):
        before=read('bed-source-covers-before.json.gz');after=bed_without_source_covers(before)
        protected=set(before['frame_slimming']['frame_parts'])|{p for b in before['mattress_bindings'].values() for p in b['parts']}
        self.assertEqual({r['name']:r for r in before['review_geometry']['meshes'] if r['name'] in protected},
                         {r['name']:r for r in after['review_geometry']['meshes'] if r['name'] in protected})
        self.assertEqual(sum(len(r['faces']) for r in before['review_geometry']['meshes']),sum(len(r['faces']) for r in after['review_geometry']['meshes']))
        source=next(r for r in before['review_geometry']['meshes'] if r['name']=='Object_6')
        indices=[i for key,s in after['part_selections'].items() if s['source_mesh']=='Object_6' for i in s['face_indices']]
        self.assertEqual(sorted(indices),list(range(len(source['faces']))))
        self.assertEqual(after['omitted_meshes'],['source-quilt','source-throw'])
        self.assertEqual(after['slim_fit']['scale_xy'],after['frame_slimming']['scale_xy'])
        self.assertEqual(set(after['frame_slimming']['bedding_parts']),{'source-pillow-left','source-pillow-right'})
        self.assertNotIn('source-quilt',{r['name'] for r in retained_model_rows(after)})
        require_bed_geometry(after,neutral_diagnostic=True)
        self.assertEqual(before,read('bed-source-covers-before.json.gz'))

    def test_renamed_bedding_sibling_and_fused_component_mutation(self):
        original=read('bed-source-covers-before.json.gz');changed=deepcopy(original)
        for row in changed['review_geometry']['meshes']:
            if row['name']=='Object_6':row['name']='other-source-softgoods'
        changed['frame_slimming']['bedding_parts']=['other-source-softgoods']
        result=bed_without_source_covers(changed)
        require_bed_geometry(result,neutral_diagnostic=True)
        rows=changed['review_geometry']['meshes'];soft=next(r for r in rows if r['name']=='other-source-softgoods')
        selections=result['part_selections'];quilt=selections['source-quilt']['face_indices'];pillow=selections['source-pillow-left']['face_indices']
        soft['faces'].append([soft['faces'][quilt[0]][0],soft['faces'][pillow[0]][0],soft['faces'][pillow[0]][1]])
        with self.assertRaisesRegex(ValueError,'component changed'):bed_without_source_covers(changed)
        fused=deepcopy(original);fused['frame_slimming']['bedding_parts']=['Object_4']
        with self.assertRaisesRegex(ValueError,'separable'):bed_without_source_covers(fused)

    def test_real_chair_seat_height_rule_and_back_follow_source(self):
        fixture=read('chair-seat-rule-real.json.gz')
        for name,expected in [('flannigan',.8114018107417468),('leather',.9136802908461158)]:
            model=fixture[name];fit=model_fit(model)
            self.assertAlmostEqual(fit['height_m'],.46)
            self.assertAlmostEqual(fit['back_height']['floor_top_m'],expected)
            self.assertAlmostEqual(fit['back_height']['above_seat_m'],expected-.46)
            self.assertEqual(fit['ok'],name=='leather')
            self.assertNotAlmostEqual(fit['sz'],fit['sx'])
            self.assertNotAlmostEqual(fit['sz'],fit['sy'])
            self.assertNotIn('height_constraints',model['furniture_fitting'])
            self.assertIn('ASSUMED',model['furniture_fitting']['height_source'])

    def test_real_translated_chair_same_factors_and_out_of_range_mutation(self):
        model=read('chair-seat-rule-real.json.gz')['leather'];clean=model_fit(model)
        sibling=deepcopy(model)
        for row in sibling['review_geometry']['meshes']:
            row['faces']=[[[p[0]+7,p[1]-12,p[2]+3] for p in face] for face in row['faces']]
        translated=model_fit(sibling)
        for key in ('sx','sy','sz','overall_height_m'):self.assertAlmostEqual(clean[key],translated[key])
        changed=deepcopy(model);changed['furniture_fitting']['height_m']=.4
        self.assertFalse(model_fit(changed)['ok'])
        self.assertIn('back height',model_fit(changed)['reason'])
        changed=deepcopy(model);changed['furniture_fitting']['back_height_range']['max_m']=.45
        self.assertFalse(model_fit(changed)['ok'])
        changed=deepcopy(model);changed['furniture_fitting']['back_height_range']['datum']='floor'
        with self.assertRaisesRegex(ValueError,'datum'):model_fit(changed)

    def test_task_chair_activation_needs_range_and_preserves_actual_source_ownership(self):
        model=read('chair-seat-rule-real.json.gz')['leather']
        require_furniture_geometry(model,neutral_diagnostic=True)
        bad=deepcopy(model);bad['furniture_fitting'].pop('back_height_range')
        with self.assertRaisesRegex(ValueError,'cited'):require_furniture_geometry(bad,neutral_diagnostic=True)
        bad=deepcopy(model);bad['omitted_meshes']=[]
        with self.assertRaisesRegex(ValueError,'accessory'):model_fit(bad)

    def test_derived_seat_uses_current_authoring_inputs_and_native_mesh_identity(self):
        desk=dict(id='renamed-study',type='desk',level='G',room='other-study',cx=3.,cy=4.,w=1.8,d=.7,h=.75,rot=90)
        seats=derived_seats([desk]);self.assertTrue(seats)
        for seat in seats:
            self.assertEqual(seat['parent_id'],desk['id']);self.assertEqual(seat['room'],desk['room'])
            self.assertAlmostEqual(seat['seat_h'],.46)
            self.assertEqual([seat['w'],seat['d']],[.44,.45])
            self.assertTrue(seat['id'].startswith('renamed-study#chair-'))
if __name__=='__main__':unittest.main()
