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
    def test_real_embedded_softbox_reproduction_and_clear_scaled_siblings(self):
        import numpy as np
        from archpipe.beds import preview_neutral_light
        frozen=json.loads((FIXTURES/'bed-round4-softbox-intersection.json').read_text())
        triangle=np.asarray(frozen['triangle'])
        corners=np.asarray(frozen['old_emitter_corners_m'])
        def intersections(triangle,corners):
            across=corners[1]-corners[0];up=corners[3]-corners[0]
            normal=np.cross(across,up);normal/=np.linalg.norm(normal)
            depths=(triangle-corners[0])@normal
            hits=[]
            for start,end in ((0,1),(1,2),(2,0)):
                if depths[start]*depths[end]>=0:continue
                point=triangle[start]+(triangle[end]-triangle[start])*depths[start]/(depths[start]-depths[end])
                delta=point-corners[0]
                if 0<=delta@across/(across@across)<=1 and 0<=delta@up/(up@up)<=1:
                    hits.append(point)
            return hits
        self.assertEqual(len(intersections(triangle,corners)),2)
        for scale,travel in [(1.,np.zeros(3)),(.001,np.array([5.,-6.,3.])),
                             (100.,np.array([-8.,7.,-9.]))]:
            self.assertEqual(len(intersections(triangle*scale+travel,corners*scale+travel)),2)
            points=np.asarray(frozen['extreme_vertices_m'])*scale+travel
            light=preview_neutral_light(points)
            self.assertGreater(light['minimum_emitter_z_bound_m'],points[:,2].max())
            position=np.asarray(light['position_m'])
            direction=np.asarray(light['target_m'])-position;direction/=np.linalg.norm(direction)
            right=np.cross(direction,[0,0,1]);right/=np.linalg.norm(right)
            up=np.cross(right,direction)
            new_corners=np.asarray([position+light['size_m']/2*(a*right+b*up)
                                    for a,b in ((-1,-1),(1,-1),(1,1),(-1,1))])
            self.assertGreater(new_corners[:,2].min(),points[:,2].max())
            self.assertEqual(intersections(triangle*scale+travel,new_corners),[])

    def test_seven_real_round4_candidates_fail_without_fit_scaling(self):
        rows=json.loads((FIXTURES/'bed-round4-measurements.json').read_text())
        self.assertEqual(len(rows),7)
        for row in rows:
            fit=fit_bed(row['bounds_m'],*row['target_m'],None,row['front_axis'],row['length_axis'],
                        mattress_bounds=row['mattress_bounds'],required_berths=row['required_berths'])
            self.assertFalse(fit['ok'],row['asset'])
            self.assertEqual(fit['scale'],1.)
            if not row['mattress_bounds']:
                self.assertIn('actual mattress geometry required',fit['reason'])
                continue
            # The same actual geometry at its own dimensions is a quiet
            # mechanical control, with no room or product acceptance claim.
            for berth,mattress in fit['mattresses'].items():
                control=fit_bed(row['bounds_m'],*mattress['size_m'],None,row['front_axis'],row['length_axis'],
                                mattress_bounds={'lower':row['mattress_bounds'][berth]})
                self.assertTrue(control['ok'],row['asset'])
            renamed=dict(row,asset='other-house-'+row['asset'])
            translated={name:dict(min=[v+3 for v in box['min']],max=[v+3 for v in box['max']])
                        for name,box in renamed['mattress_bounds'].items()}
            self.assertFalse(fit_bed(row['bounds_m'],*row['target_m'],None,row['front_axis'],row['length_axis'],
                                    mattress_bounds=translated,required_berths=row['required_berths'])['ok'])
        closest=next(r for r in rows if r['asset']=='sf_bed3_2cabd354')
        for mattress in closest['fit']['mattresses'].values():
            self.assertAlmostEqual(mattress['error_m'][0],.065484,places=5)
            self.assertAlmostEqual(mattress['error_m'][1],.170206,places=5)

    def test_real_tiny_preview_floor_gap_and_scale_siblings(self):
        import numpy as np
        frozen=json.loads((FIXTURES/'bed-round4-tiny-staging.json').read_text())
        points=np.asarray(frozen['points_m'])
        self.assertGreater(frozen['old_gap_m']/(points.max(0)[2]-points.min(0)[2]),.27)
        for scale,travel in [(1.,np.zeros(3)),(.1,np.array([4.,8.,3.])),
                             (1000.,np.array([-7.,5.,-3.]))]:
            actual=points*scale+travel
            datums=preview_datums(actual)
            span=float((actual.max(0)-actual.min(0)).max())
            self.assertLessEqual(datums['staging_gap_m'],span*.0025)
            self.assertAlmostEqual(datums['figure_foot_z_m'],actual.min(0)[2])
            self.assertAlmostEqual(datums['floor_z_m'],actual.min(0)[2]-datums['staging_gap_m'])
        self.assertEqual(preview_datums(points*1000.)['staging_gap_m'],.005)

    def test_real_oversize_preview_clipping_and_translated_small_siblings(self):
        import numpy as np
        from archpipe.beds import preview_clip_range
        frozen=json.loads((FIXTURES/'bed-round4-camera-clipping.json').read_text())
        points=np.asarray(frozen['points_m'])
        camera=np.asarray(frozen['camera_position_m'])
        target=np.asarray(frozen['camera_target_m'])
        direction=(target-camera)/np.linalg.norm(target-camera)
        depths=(points-camera)@direction
        self.assertTrue((depths>frozen['old_clip_end_m']).all())
        for scale,travel in [(1.,np.zeros(3)),(.001,np.array([17.,-20.,4.])),
                             (.000001,np.array([-5.,7.,-3.]))]:
            actual=points*scale+travel
            position=camera*scale+travel
            aim=target*scale+travel
            clips=preview_clip_range(actual,position,aim)
            direction=(aim-position)/np.linalg.norm(aim-position)
            depths=(actual-position)@direction
            self.assertTrue((depths>clips['clip_start_m']).all())
            self.assertTrue((depths<clips['clip_end_m']).all())
        with self.assertRaisesRegex(ValueError,'behind'):
            preview_clip_range(points,camera,2*camera-target)

    def test_real_cloth_refusal_cannot_report_success_renamed_or_clean(self):
        import runpy
        require_proof=runpy.run_path(str(Path(__file__).parents[1]/'scripts/check_bed_import.py'))['require_complete_proof']
        failed=json.loads((FIXTURES/'bed-round3-cloth-refusal.json').read_text())
        with self.assertRaisesRegex(ValueError,'cloth proof failed'):
            require_proof(failed)
        sibling=deepcopy(failed)
        sibling['cloth']['refused']=sibling['cloth']['refused'].replace('mechanical-scandi','other-villa-bed')
        with self.assertRaisesRegex(ValueError,'cloth proof failed'):
            require_proof(sibling)
        clean=deepcopy(failed);clean['cloth']=dict(passed=True,records=[])
        require_proof(clean)

    def geometry(self):
        return json.loads(gzip.decompress((FIXTURES/'bed-scandi-geometry.json.gz').read_bytes()))

    def scene(self,travel=(0,0,0),yaw=0):
        model=dict(id='another-bed',asset='sf_bed_scandi_bare',role='bed',scale=1.,
                   contents_review=dict(status='bed-only',basis='frozen seven bed meshes',extras=[]),
                   mattress_bindings=dict(lower=dict(parts=['Object_14'],head_at_max=False)),
                   position=list(travel),rotation_deg=[0,0,yaw],review_geometry=self.geometry())
        floor=dict(id='actual-floor',group='shell',material='floor-oak',faces=[
            [[-10,-10,0],[10,-10,0],[10,10,0],[-10,10,0]]])
        return dict(meshes=[floor],models=[model])

    def test_real_candidates_reject_after_semantic_axis_correction(self):
        rows=json.loads((FIXTURES/'bed-round2-measurements.json').read_text())
        for row in rows:
            fit=fit_bed(row['bounds_m'],*row['target'],row['front_axis'],row['length_axis'],scale=row['fit']['scale'])
            self.assertFalse(fit['ok'],row['id'])
            self.assertEqual(fit['scale'],1.)
            self.assertIn('scaled bed refused',fit['reason'])
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
        from archpipe.beds import model_mattress_bounds
        mattress=model_mattress_bounds(spec)['lower']
        spec.update(native_bounds=dict(min=[-2.164110,.017163,-1.304135],max=[2.283993,1.317586,1.225815]),
                    length_axis='X',planned_mattress_m=[mattress['max'][2]-mattress['min'][2],mattress['max'][0]-mattress['min'][0]])
        spec['neutral_review']['selection']=dict(omitted_meshes=[],mattress_bindings=deepcopy(spec['mattress_bindings']),unit_evidence=None)
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
        self.assertAlmostEqual(datums['figure_foot_z_m'],bounds['min'][1]*scale)
        self.assertGreater(datums['staging_gap_m'],0)
        self.assertLessEqual(datums['staging_gap_m'],.005)
        self.assertAlmostEqual(datums['figure_foot_z_m']-datums['floor_z_m'],datums['staging_gap_m'])
        shifted=preview_datums([[x+5,y+3,z+2] for x,y,z in points])
        self.assertAlmostEqual(shifted['floor_z_m'],datums['floor_z_m']+2)
