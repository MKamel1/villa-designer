"""Frozen real round-5 scaled fits and round-4 worst distortion refusals."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from archpipe.beds import (scaled_bed_fit,scaled_model_fit,model_transform,
    model_mattress_bounds,model_native_bounds,model_review_meshes,
    placed_bed_findings,review_selection,require_bed_geometry,plan_scale_findings)
FIXTURES=Path(__file__).parent/'fixtures'


class ScaledBeds(unittest.TestCase):
    def test_activation_cannot_override_real_upper_height_shortfall_or_failed_room(self):
        from unittest.mock import patch
        from archpipe.beds import integrate_bed_models
        for m in self.models():
            m=deepcopy(m);mark=m['replaces'].removeprefix('furn-').removesuffix('-')
            m['orientation_evidence']=dict(front_axis=m['front_axis'],basis='frozen measured head')
            m['neutral_review']=dict(status='accepted',source_sha256=m['review_geometry']['source_sha256'],
                orientation_evidence=deepcopy(m['orientation_evidence']),selection=review_selection(m))
            item=dict(id=mark,w=m['planned_mattress_m'][0],d=m['planned_mattress_m'][1],
                cx=m['position'][0],cy=m['position'][1],rot=m['layout_rotation_deg'],berths=m['required_berths'])
            actual=model_mattress_bounds(m,world=True)
            cloth=[dict(id='duvet-'+mark+('-upper' if b=='upper' else ''),
                mattress_top=1.402 if b=='upper' else box['max'][2]) for b,box in actual.items()]
            scene=dict(models=[],meshes=[dict(id=m['replaces']+'fallback',faces=[
                [[0,0,m['position'][2]],[1,0,m['position'][2]],[0,1,m['position'][2]]]])],cloth=cloth)
            with patch('archpipe.beds.bed_room_review',return_value=dict(ok=False,findings=['unchanged room shortfall'])) as gate:
                message='every design mattress-top height' if m['required_berths']==2 else 'current slim-frame contract'
                with self.assertRaisesRegex(ValueError,message):integrate_bed_models(scene,[m],{}, {},[item])
                gate.assert_not_called()

    def test_heading_envelope_removes_real_suspended_pins_and_covers_subdivision_ring(self):
        import gzip
        import numpy as np
        from archpipe.beds import cloth_support_envelope
        rows=json.loads(gzip.decompress((FIXTURES/'bed-round5-heading-support.json.gz').read_bytes()))
        for row in rows:
            old=np.asarray(row['points']);faces=np.asarray(row['faces']);spacing=np.asarray(row['cell_size_m'])
            for travel in (np.zeros(3),np.array([8.,11.,3.])):
                points=old+travel;source=faces+travel
                heights=cloth_support_envelope(points,source,spacing)
                self.assertLess(max(heights),max(points[:,2]))
                for point,height in zip(points,heights):
                    matches=(np.all(source.max(1)[:,:2]>=point[:2]-spacing,axis=1)&
                             np.all(source.min(1)[:,:2]<=point[:2]+spacing,axis=1))
                    self.assertAlmostEqual(height-source[matches,:,2].max(),.008)
                # Reconstructed supported anchors are stable; no new lift.
                clean=points.copy();clean[:,2]=heights
                np.testing.assert_allclose(cloth_support_envelope(clean,source,spacing),heights)
        with self.assertRaises(ValueError):cloth_support_envelope([[0,0,1]],[],[.03,.03])

    def test_throw_and_renamed_soft_goods_bind_real_model_without_changing_authored_cut(self):
        from archpipe.beds import bind_model_cloth
        for model in self.models():
            model=deepcopy(model);model['replaces']='furn-another-suite-';model['id']='renamed-model'
            specs=[dict(id='duvet-another-suite'),dict(id='throw-another-suite',center=[8,11],size=[2.1,.55]),
                   dict(id='throw-unrelated-room')]
            result=bind_model_cloth(specs,[model])
            self.assertEqual(result[0]['model_cloth_kind'],'duvet')
            self.assertEqual(result[1]['model_cloth_kind'],'throw')
            self.assertEqual(result[1]['mattress_parts'],model['mattress_bindings']['lower']['parts'])
            self.assertEqual(result[1]['center'],specs[1]['center'])
            self.assertEqual(result[1]['size'],specs[1]['size'])
            self.assertNotIn('model_instance',result[2])
            self.assertNotIn('model_instance',specs[1])

    def test_replacement_option_is_forwarded_through_scoped_scene_builder(self):
        from unittest.mock import patch
        from archpipe.concept import villa_render
        options=dict(lay={'other-villa':'fixture'},views=[],collect_part_failures=False,bed_replacements=['reviewed-model'])
        with patch.object(villa_render,'_build',return_value='bounded-builder-result') as scoped:
            self.assertEqual(villa_render.build(**options),'bounded-builder-result')
            scoped.assert_called_once_with(options['lay'],options['views'],
                collect_part_failures=False,bed_replacements=options['bed_replacements'])

    def test_model_pins_stay_on_actual_mattress_width_overhangs_free(self):
        import numpy as np
        from archpipe.beds import mattress_pin_indices
        for model in self.models():
            rows=model_review_meshes([model])
            faces=[f for r in rows if r['id'].endswith('::measured-lower-mattress') for f in r['faces']]
            points=np.asarray([p for f in faces for p in f]);lo,hi=points.min(0),points.max(0)
            axis='y';long=1;across=0;value=(lo[long]+hi[long])/2
            vertices=[[lo[across]-.26,value,hi[2]+.08],[(lo[across]+hi[across])/2,value,hi[2]+.08],
                      [hi[across]+.26,value,hi[2]+.08]]
            spec=dict(pin=[axis,value,.03])
            self.assertEqual(mattress_pin_indices(spec,faces,vertices),[1])
            travel=np.array([8.,11.,3.]);translated=[(np.asarray(f)+travel).tolist() for f in faces]
            self.assertEqual(mattress_pin_indices(dict(pin=[axis,value+11.,.03]),translated,
                (np.asarray(vertices)+travel).tolist()),[1])

    def test_real_neutral_preview_refusal_cannot_report_success_renamed_or_clean(self):
        import runpy
        require=runpy.run_path(str(Path(__file__).parents[1]/'scripts/preview_beds.py'))['require_neutral_cloth']
        frozen=json.loads((FIXTURES/'bed-round5-preview-refusal.json').read_text())
        for name in (frozen['bed'],'another-villa-bedroom'):
            failed=dict(frozen,bed=name)
            with self.assertRaisesRegex(ValueError,'refused'):require([failed])
        require([dict(bed='clean',cloth_report=[dict(model_clearance=dict(intersections=0,inside_vertices=0))])])

    def test_scoped_c8_preserves_real_body_conflicts_without_own_proxy_or_unrelated_route_intake(self):
        from archpipe.beds import bed_room_review
        m=self.models()[0];m['id']='another-bed';m['replaces']='furn-other-bed-';m['room']='other-room'
        m['position']=[0,0,.002]
        item=dict(id='other-bed',room='other-room',type='bed_double',cx=0,cy=0,w=1.6,d=2.,h=1.05,rot=0,level='GF')
        floor=dict(id='actual-floor',group='shell',material='floor-oak',faces=[
            [[-10,-10,.002],[10,-10,.002],[10,10,.002],[-10,10,.002]]])
        scene=dict(models=[m],meshes=[floor],props=[dict(id='unchanged-decor',asset='wooden_bowl_01',
            label='unchanged decorative bowl',position=[100,100,0],scale=1.,rotation_deg=[0,0,0])])
        layout=dict(rooms={'other-room':dict(rect=[-10,-10,10,10],level='GF',occupancy='room',kind='bedroom')})
        spec=dict(walls=[],doors=[],windows=[],stairs=[])
        result=bed_room_review(scene,layout,spec,[item])
        self.assertFalse(any(f['query']=='body-overlap' for f in result['findings']))
        scene['meshes'].append(dict(id='fixed-other-obstacle',group='furniture',material='wood',
            faces=[[[-.2,-.2,.002],[.2,-.2,.002],[.2,.2,1.]]]))
        blocked=bed_room_review(scene,layout,spec,[item])
        self.assertTrue(any(f['query']=='body-overlap' and 'fixed-other-obstacle' in (f['source_id'],f['reference_id'])
                            for f in blocked['findings']))

    def test_source_bedding_initial_height_clears_real_faces_and_rotated_siblings(self):
        from archpipe.beds import mattress_cloth
        for m in self.models():
            for yaw,travel in [(m['rotation_deg'][2],[0,0,0]),(0,[8,11,3])]:
                m=deepcopy(m);m['rotation_deg'][2]=yaw;m['position']=[a+b for a,b in zip(m['position'],travel)]
                rows=model_review_meshes([m]);faces=[f for r in rows for f in r['faces']]
                mattress=[f for r in rows if r['id'].endswith('::measured-lower-mattress') for f in r['faces']]
                axis='x' if m['length_axis']=='X' and yaw%180==0 or m['length_axis']=='Z' and yaw%180==90 else 'y'
                spec=dict(length_axis=axis,cut=dict(head_to_pin_m=.55,foot_overhang_m=.26,side_overhang_m=.26))
                head_max=yaw%360==0
                upper=[p[2] for r in rows if r['id'].endswith('::measured-upper-mattress') for f in r['faces'] for p in f]
                ceiling=min(upper) if upper else None
                old=mattress_cloth(spec,mattress,head_max)
                fixed=mattress_cloth(spec,mattress,head_max,collider_faces=faces,collider_ceiling_m=ceiling,
                    initialization_ceiling_m=(old['mattress_top']+ceiling)/2 if ceiling else None)
                self.assertGreaterEqual(fixed['z_start'],old['z_start'])
                for key in ('center','size','pin','mattress_top'):self.assertEqual(fixed[key],old[key])
                naked=mattress_cloth(spec,mattress,head_max,collider_faces=mattress)
                self.assertEqual(naked['z_start'],old['z_start'])
                if m['asset']=='sf_bed_upholstered_cyberfox' and yaw==m['rotation_deg'][2]:
                    self.assertGreater(fixed['z_start'],old['z_start']+.1)
                if ceiling:
                    self.assertLess(fixed['z_start'],ceiling)
                    with self.assertRaisesRegex(ValueError,'own bunk berth'):
                        mattress_cloth(spec,mattress,head_max,collider_faces=faces,collider_ceiling_m=old['mattress_top']+.01)

    def test_real_upper_duvet_outside_concave_shell_quiet_inside_and_siblings_fire(self):
        import gzip
        import numpy as np
        from archpipe.bed_containment import closed_shell_contains, face_shells
        fixture=json.loads(gzip.decompress((FIXTURES/'bed-round5-upper-containment.json.gz').read_bytes()))
        triangle=np.asarray(fixture['nearest_plane_sample']['model_triangle'])
        p=np.asarray(fixture['outside_point']);nearest=np.asarray(fixture['nearest_plane_sample']['nearest_m'])
        normal=np.asarray(fixture['nearest_plane_sample']['normal'])
        self.assertLess((p-nearest)@normal,-.0001)  # real old false positive
        shell=np.asarray(fixture['triangles'])
        for travel in (np.zeros(3),np.array([8.,11.,3.])):
            faces=np.arange(len(shell)*3).reshape(-1,3).tolist()
            self.assertTrue(face_shells((shell+travel).reshape(-1,3),faces)[0]['closed'])
            self.assertIs(closed_shell_contains(shell+travel,p+travel),False)
            self.assertIs(closed_shell_contains(shell+travel,np.asarray(fixture['inside_point'])+travel),True)

    def models(self):
        return json.loads((FIXTURES/'bed-round5-measurements.json').read_text())

    def test_chosen_real_scaled_fits_accept_original_renamed_and_rotated_siblings(self):
        import numpy as np
        for model in self.models():
            for renamed,yaw,travel in [('original',model['rotation_deg'][2],(0,0,0)),('other-villa',90,(8,11,3))]:
                m=deepcopy(model);m['id']=renamed;m['rotation_deg'][2]=yaw
                m['position']=[a+b for a,b in zip(m['position'],travel)]
                frozen=deepcopy(m['review_geometry'])
                fit=scaled_model_fit(m);self.assertTrue(fit['ok'],fit['reason'])
                self.assertLessEqual(fit['plan_distortion'],.15)
                actual=model_mattress_bounds(m,world=True)
                for box in actual.values():
                    sizes=sorted([box['max'][i]-box['min'][i] for i in (0,1)])
                    np.testing.assert_allclose(sizes,sorted(m['planned_mattress_m']),atol=1e-6)
                    for i in (0,1):self.assertLess(abs((box['min'][i]+box['max'][i])/2-m['position'][i]),1e-5)
                self.assertAlmostEqual(actual['lower']['max'][2],m['position'][2]+m['scaling']['mattress_top_m'])
                faces=model_review_meshes([m]);p=np.asarray([p for r in faces for f in r['faces'] for p in f])
                world=dict(min=p.min(0).tolist(),max=p.max(0).tolist())
                lower=actual['lower'];foot=[lower['min'][0],lower['min'][1],lower['max'][0],lower['max'][1]]
                self.assertEqual(placed_bed_findings(m['native_bounds'],world,foot,m['reference_h'],1,
                    mattress_world_bounds=actual,scaled_model=m),[])
                moved=deepcopy(world);moved['max'][2]+=.02
                self.assertTrue(placed_bed_findings(m['native_bounds'],moved,foot,m['reference_h'],1,
                    mattress_world_bounds=actual,scaled_model=m))
                wrong_mattress=deepcopy(actual);wrong_mattress['lower']['max'][0]+=.02
                refused=placed_bed_findings(m['native_bounds'],world,foot,m['reference_h'],1,
                    mattress_world_bounds=wrong_mattress,scaled_model=m)
                self.assertTrue(any('Client bed scaling decision 2026-10-09' in f for f in refused))
                self.assertEqual(m['review_geometry'],frozen)

    def test_real_worst_round4_anisotropy_refused_and_renamed_translated_sibling(self):
        rows=json.loads((FIXTURES/'bed-round4-measurements.json').read_text())
        row=next(r for r in rows if r['asset']=='sf_bed3_0e134823')
        for name,travel in [('actual',0.),('renamed-other-villa',3.)]:
            frame={k:[v+travel for v in values] for k,values in row['bounds_m'].items()}
            mattresses={key:{k:[v+travel for v in values] for k,values in b.items()} for key,b in row['mattress_bounds'].items()}
            fit=scaled_bed_fit(frame,.9,2.,row['front_axis'],length_axis=row['length_axis'],
                mattress_bounds=mattresses,mattress_top_m=.4,height_source='ASSUMED existing lower bunk',
                headboard_bounds=frame,headboard_limit_m=2.4,headboard_limit_source='ASSUMED review cap',required_berths=2)
            self.assertFalse(fit['ok'],name);self.assertIn('exceeds 15%',fit['reason'])
            self.assertGreater(fit['plan_distortion'],.39)
        self.assertEqual(plan_scale_findings(1.,1.15),[])
        self.assertTrue(plan_scale_findings(1.,1.15001))
        self.assertTrue(plan_scale_findings(1.15001,1.))
        self.assertTrue(plan_scale_findings(.497421755, .47153314))

    def test_real_fused_extras_refused_in_original_and_renamed_consumers(self):
        for model in self.models():
            self.assertTrue(model_review_meshes([model]))
            for name in ('real-candidate','renamed-other-suite'):
                bad=deepcopy(model);bad['id']=name
                bad['contents_review']['fused_extras']=['bench fused to retained frame']
                with self.assertRaisesRegex(ValueError,'bed-only'):model_review_meshes([bad])
                with self.assertRaisesRegex(ValueError,'bed-only'):scaled_model_fit(bad)

    def test_height_uses_vertical_factor_not_plan_and_reports_bunk_upper_shortfall(self):
        for m in self.models():
            fit=scaled_model_fit(m)
            self.assertNotAlmostEqual(fit['sz'],fit['sx'],places=3)
            self.assertNotAlmostEqual(fit['sz'],fit['sy'],places=3)
            self.assertGreaterEqual(fit['headboard_height_m'],max(r['top_m'] for r in fit['mattresses'].values()))
            self.assertLessEqual(fit['headboard_height_m'],fit['headboard_limit_m'])
            bad=deepcopy(m);bad['scaling']['headboard_limit_m']=.1
            self.assertFalse(scaled_model_fit(bad)['ok'])
            if m['required_berths']==2:
                self.assertAlmostEqual(1.402-(fit['mattresses']['upper']['top_m']+.002),.2773634658)

    def test_scaled_receipt_invalidates_factor_content_face_and_placement_mutations(self):
        for m in self.models():
            m['orientation_evidence']=dict(front_axis=m['front_axis'],basis='frozen actual head/pillows')
            m['native_bounds']=model_native_bounds(m)
            m['neutral_review']=dict(status='accepted',source_sha256=m['review_geometry']['source_sha256'],
                orientation_evidence=deepcopy(m['orientation_evidence']),selection=review_selection(m))
            require_bed_geometry(m)
            for key in ('position','scaling','contents_review','review_geometry'):
                bad=deepcopy(m)
                if key=='position':bad[key][0]+=.1
                elif key=='scaling':bad[key]['height_source']+=' changed'
                elif key=='contents_review':bad[key]['basis']+=' changed'
                else:bad[key]['meshes'][0]['faces'].reverse()
                with self.assertRaisesRegex(ValueError,'not bound'):require_bed_geometry(bad)
            bad=deepcopy(m);bad['scale_xyz'][2]=bad['scale_xyz'][0]
            with self.assertRaisesRegex(ValueError,'factors disagree'):model_transform(bad)
            pending=deepcopy(m);pending['neutral_review']['status']='pending'
            with self.assertRaisesRegex(ValueError,'accepted'):require_bed_geometry(pending)
            require_bed_geometry(pending,neutral_diagnostic=True)

if __name__=='__main__':unittest.main()
