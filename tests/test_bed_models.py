"""Real downloaded bed geometry, immutable placement, support and route proofs.

Frozen faces are unedited Blender imports. These mechanically placed controls
are capability tests; all five downloaded candidates remain rejected for D1.
"""
from copy import deepcopy
import gzip
import json
from pathlib import Path
import unittest
from archpipe.beds import (fit_bed, mattress_cloth, model_review_meshes, bind_model_cloth,
                            scene_with_model_geometry, preview_datums, require_bed_geometry)
from archpipe.geometry_topology import GeometryTopology

FIXTURES=Path(__file__).parent/'fixtures'

class BedModelGeometry(unittest.TestCase):
    def geometry(self):
        return json.loads(gzip.decompress((FIXTURES/'bed-scandi-geometry.json.gz').read_bytes()))

    def scene(self,travel=(0,0,0),yaw=0):
        model=dict(id='another-bed',asset='sf_bed_scandi_bare',role='bed',scale=.45,
                   position=list(travel),rotation_deg=[0,0,yaw],review_geometry=self.geometry())
        floor=dict(id='actual-floor',group='shell',material='floor-oak',faces=[
            [[-10,-10,0],[10,-10,0],[10,10,0],[-10,10,0]]])
        return dict(meshes=[floor],models=[model])

    def test_real_candidates_reject_after_semantic_axis_correction(self):
        rows=json.loads((FIXTURES/'bed-round2-measurements.json').read_text())
        for row in rows:
            fit=fit_bed(row['bounds_m'],*row['target'],row['front_axis'],row['length_axis'])
            self.assertFalse(fit['ok'],row['id'])
            self.assertAlmostEqual(fit['scale'],row['fit']['scale'])
        cyber=next(r for r in rows if 'cyberfox' in r['id'])
        self.assertEqual(cyber['front_axis'],'-X')
        self.assertGreater(cyber['fit']['footprint_error_m'][1],.59)

    def test_actual_geometry_c8_support_quiet_lifted_and_renamed_sibling_fire(self):
        for yaw in (0,90):
            scene=self.scene(yaw=yaw)
            before=deepcopy(scene)
            self.assertEqual(GeometryTopology.from_inputs(scene=scene).unsupported_floating(),[])
            scene['models'][0]['position']=[0,0,1]
            findings=GeometryTopology.from_inputs(scene=scene).unsupported_floating()
            self.assertTrue(findings)
            self.assertTrue(all(f.source_id.startswith('another-bed::') for f in findings))
            self.assertEqual(before['models'][0]['review_geometry'],scene['models'][0]['review_geometry'])

    def test_model_faces_in_route_and_outside_route_quiet(self):
        scene=self.scene()
        route={'clear-path':[-.4,-.4,.4,.4]}
        self.assertTrue(GeometryTopology.from_inputs(scene=scene,routes=route,route_ground={'clear-path':0}).object_in_route())
        scene['models'][0]['position']=[5,5,0]
        self.assertEqual(GeometryTopology.from_inputs(scene=scene,routes=route,route_ground={'clear-path':0}).object_in_route(),[])

    def test_real_legacy_model_envelope_uses_centred_floor_anchor(self):
        rows=json.loads((FIXTURES/'bed-round2-measurements.json').read_text())
        measured=next(r for r in rows if r['id']=='sf_bed_forssa')['bounds_m']
        extents=[b-a for a,b in zip(measured['min'],measured['max'])]
        for yaw,position in [(0,[5,8,3]),(90,[-9,15,-3])]:
            model=dict(id='legacy-renamed-bed-control',asset='sf_bed_forssa',scale=.5,
                       position=position,rotation_deg=[0,0,yaw])
            obstacle=GeometryTopology.from_inputs(scene=dict(meshes=[],models=[model])).obstacles[0]
            box=obstacle.bounds
            self.assertAlmostEqual((box[0]+box[3])/2,position[0])
            self.assertAlmostEqual((box[1]+box[4])/2,position[1])
            self.assertAlmostEqual(box[2],position[2])
            self.assertAlmostEqual(box[5]-box[2],extents[1]*.5,places=5)

    def test_expansion_is_idempotent_and_removes_only_selected_fallback(self):
        scene=self.scene()
        scene['models'][0]['replaces']='old-bed-'
        scene['meshes']+=[dict(id='old-bed-mattress',faces=[]),dict(id='other-bed',faces=[])]
        first=scene_with_model_geometry(scene)
        self.assertEqual(first,scene_with_model_geometry(first))
        self.assertNotIn('old-bed-mattress',[m['id'] for m in first['meshes']])
        self.assertIn('other-bed',[m['id'] for m in first['meshes']])
        self.assertIn('old-bed-mattress',[m['id'] for m in scene['meshes']])
        scene['models'][0]['status']='procedural-bed-fallback'
        restored=scene_with_model_geometry(scene)
        self.assertEqual(restored['meshes'],scene['meshes'])

    def test_bed_missing_receipt_and_pending_review_fail_closed(self):
        scene=self.scene();scene['models'][0].pop('review_geometry')
        with self.assertRaisesRegex(ValueError,'review_geometry'):
            GeometryTopology.from_inputs(scene=scene)
        spec=self.scene()['models'][0]
        spec.update(front_axis='+X',orientation_evidence=dict(front_axis='+X',basis='measured pillow'))
        with self.assertRaisesRegex(ValueError,'accepted neutral review'):
            require_bed_geometry(spec,'/unused')

    def test_both_bunk_mattresses_require_independent_measured_bindings(self):
        model=dict(id='other-bunk-model',role='bed',replaces='furn-other-bunk-',
                   mattress_bindings=dict(lower=dict(parts=['lower-real'],head_at_max=True)))
        cloth=[dict(id='duvet-other-bunk'),dict(id='duvet-other-bunk-upper')]
        with self.assertRaisesRegex(ValueError,'upper mattress binding'):
            bind_model_cloth(cloth,[model])
        model['mattress_bindings']['upper']=dict(parts=['upper-real'],head_at_max=False)
        bound=bind_model_cloth(cloth,[model])
        self.assertEqual([s['mattress_parts'] for s in bound],[['lower-real'],['upper-real']])
        self.assertEqual([s['head_at_max'] for s in bound],[True,False])
        self.assertEqual(cloth,[dict(id='duvet-other-bunk'),dict(id='duvet-other-bunk-upper')])

    def test_real_review_binding_invalidates_changed_axis_or_source(self):
        spec=self.scene()['models'][0]
        spec.update(front_axis='+X',orientation_evidence=dict(front_axis='+X',basis='actual pillow at -X'))
        spec['neutral_review']=dict(status='accepted',
            source_sha256=deepcopy(spec['review_geometry']['source_sha256']),
            orientation_evidence=deepcopy(spec['orientation_evidence']))
        require_bed_geometry(spec)
        spec['orientation_evidence']['basis']='different semantic part claim'
        with self.assertRaisesRegex(ValueError,'not bound'):
            require_bed_geometry(spec)
        spec['orientation_evidence']=deepcopy(spec['neutral_review']['orientation_evidence'])
        spec['review_geometry']['source_sha256']['scene.bin']='changed-buffer'
        with self.assertRaisesRegex(ValueError,'not bound'):
            require_bed_geometry(spec)

    def test_real_forssa_mattress_cut_rotated_sibling(self):
        geometry=json.loads(gzip.decompress((FIXTURES/'bed-forssa-mattress.json.gz').read_bytes()))
        spec=dict(length_axis='y',cut=dict(head_to_pin_m=.55,foot_overhang_m=.26,side_overhang_m=.26))
        faces=geometry['meshes'][0]['faces']
        cut=mattress_cloth(spec,faces,True)
        self.assertAlmostEqual(cut['mattress_top'],.5077964067459106)
        self.assertAlmostEqual(cut['size'][0],2.014246404+.52)
        rotated=[[[p[1]+8,-p[0]+11,p[2]+3] for p in f] for f in faces]
        sibling=mattress_cloth(dict(spec,length_axis='x'),rotated,True)
        self.assertAlmostEqual(sibling['size'][1],cut['size'][0])
        self.assertAlmostEqual(sibling['mattress_top'],cut['mattress_top']+3)

    def test_actual_preview_floor_datums_ignore_rotated_envelope(self):
        rows=json.loads((FIXTURES/'bed-round2-measurements.json').read_text())
        home=next(r for r in rows if r['id']=='sf_bunk_home_series')
        bounds=home['bounds_m'];scale=home['fit']['scale']
        points=[[x*scale,-z*scale,y*scale] for x in bounds['min'][0:1]+bounds['max'][0:1]
                for y in bounds['min'][1:2]+bounds['max'][1:2] for z in bounds['min'][2:3]+bounds['max'][2:3]]
        datums=preview_datums(points)
        self.assertAlmostEqual(datums['floor_z_m'],bounds['min'][1]*scale-.005)
        self.assertAlmostEqual(datums['figure_foot_z_m']-datums['floor_z_m'],.005)
        shifted=preview_datums([[x+5,y+3,z+2] for x,y,z in points])
        self.assertAlmostEqual(shifted['floor_z_m'],datums['floor_z_m']+2)
