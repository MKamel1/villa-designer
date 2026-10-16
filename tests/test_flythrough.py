"""Real architecture, between-frame glass, speed and content-binding regressions."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
import numpy as np
from archpipe import flythrough as W
from archpipe.concept.render_views import CameraSweep

FIXTURE=Path(__file__).parent/'fixtures/flythrough-real.json'


class Walkthrough(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.real=json.loads(FIXTURE.read_text())

    def test_walking_camera_retains_actual_still_sun_and_curtain_state(self):
        path=W.sample_path(self.real['clear_knots'])
        scene={'curtains':[{'id':'actual-curtain'}]}
        view=W.frame_views(path,scene)[0]
        self.assertEqual(view['sun'],{'altitude_deg':40.07,'azimuth_true_deg':135.34})
        self.assertEqual(view['hide_meshes'],['actual-curtain-heavy-closed'])
        from archpipe.concept.villa_render import sun_for_timestamp
        self.assertEqual(sun_for_timestamp('2026-10-15T10:30:00+03:00'),sun_for_timestamp('2026-10-15T07:30:00+00:00'))
        self.assertEqual(sun_for_timestamp('2026-10-15T18:35:00+03:00'),sun_for_timestamp('2026-10-15T15:35:00+00:00'))
        with self.assertRaises(ValueError):sun_for_timestamp('2026-10-15T10:30:00')

    def test_renderer_consumes_prepared_real_camera_state_without_host_packages(self):
        from unittest.mock import patch
        path=W.sample_path(self.real['clear_knots'])
        views=[dict(id='frame-%04d'%f['index'],camera=f['camera']) for f in path['frames']]
        with patch.dict('sys.modules',{'yaml':None,'matplotlib':None}):
            self.assertEqual(W.frame_views(path,{'views':views}),views)
        views[35]['camera']=deepcopy(views[35]['camera'])
        views[35]['camera']['position'][0]+=1
        with self.assertRaises(ValueError):W.frame_views(path,{'views':views})

    def test_actual_command_bootstrap_resolves_siblings_from_unrelated_directory(self):
        import subprocess,sys,tempfile
        root=Path(__file__).resolve().parents[1]
        program="import runpy; runpy.run_path(%r,run_name='entry_probe'); from scripts.villa_render import villa_qa_context; from scripts.villa_render_views import camera_proximity_violations"%str(root/'scripts/flythrough.py')
        with tempfile.TemporaryDirectory() as directory:
            result=subprocess.run([sys.executable,'-c',program],cwd=directory,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_actual_linked_opacity_and_optical_siblings_cannot_enter_static_mask(self):
        frozen=json.loads((FIXTURE.parent/'flythrough-materials.json').read_text())
        for row in frozen['materials']:
            self.assertEqual(row['actual_static_mask'],1.)
            self.assertFalse(W.static_material_eligible(row['nodes']))
        clean=deepcopy(frozen['materials'][0]['nodes']);clean[0]['alpha_linked']=False
        self.assertTrue(W.static_material_eligible(clean))
        for key in ('transmission','roughness','metallic'):
            sibling=deepcopy(clean);sibling[0][key+'_linked']=True
            self.assertFalse(W.static_material_eligible(sibling))
        emitting=deepcopy(clean);emitting[0]['emission_strength']=1
        self.assertFalse(W.static_material_eligible(emitting))
        mixed=deepcopy(clean)+[{'type':'BSDF_REFRACTION'}]
        self.assertFalse(W.static_material_eligible(mixed))

    def test_real_leaf_clip_rejects_old_curve_and_delivered_turn_passes(self):
        frozen=json.loads((FIXTURE.parent/'flythrough-plant-clip.json').read_text())
        sweep=CameraSweep({'meshes':[frozen['plant']]})
        old=frozen['path']['frames'];hits=[]
        for a,b in zip(old,old[1:]):
            if sweep.findings(a['camera']['position'],b['camera']['position'],ground_m=-3):hits.append(b['index'])
        self.assertTrue(set(frozen['failed_indices']).issubset(hits))
        delivered=W.authored_path()
        for a,b in zip(delivered['frames'],delivered['frames'][1:]):
            self.assertEqual(sweep.findings(a['camera']['position'],b['camera']['position'],ground_m=-3),[])
        self.assertFalse(any(r['failures'] for r in W.motion_findings(delivered['frames'],delivered['settings'])))
        # Every coordinate remains inside its adjacent controls, including a
        # stationary-axis turn; the earlier averaged tangents overshot this.
        self.assertLessEqual(max(f['camera']['position'][0] for f in delivered['frames']),21.95)
        stopped=[f['camera']['position'] for f in delivered['frames'] if f['seconds']>=27]
        self.assertTrue(stopped)
        self.assertTrue(all(p==stopped[0] for p in stopped))

    def test_proximity_preparation_preserves_real_obstacle_clean_and_scene_refusal(self):
        from scripts.villa_render_views import camera_proximity_violations,CameraProximityGeometry
        scene=deepcopy(self.real['scene']);scene['props']=[]
        mesh=next(m for m in scene['meshes'] if m['id']=='landscape-door-pot-dining-n')
        point=mesh['faces'][0][0]
        view={'camera':{'position':point},'standing_room':'test'}
        prepared=CameraProximityGeometry(scene)
        before=camera_proximity_violations(view,scene,{})
        self.assertTrue(before)
        self.assertEqual(before,camera_proximity_violations(view,scene,{},geometry=prepared))
        clean={'camera':{'position':[100,100,100]},'standing_room':'test'}
        self.assertEqual(camera_proximity_violations(clean,scene,{},geometry=prepared),[])
        with self.assertRaises(ValueError):camera_proximity_violations(view,deepcopy(scene),{},geometry=prepared)

    def test_real_room_subject_is_distinct_from_prop_prefix_and_explicit_prop_still_refuses(self):
        from archpipe.villa_render_contract import subject_meshes
        from archpipe.concept.garden_render_review import opening_frame_findings
        scene=json.loads((FIXTURE.parent/'flythrough-room-subjects.json').read_text())['scene']
        query='room:dining,dining-side'
        self.assertEqual({m['id'] for m in subject_meshes(query,scene['meshes'])},
                         {'shell-051-plaster-warm-white','floor-dining-side'})
        frame=W.authored_path()['frames'][300]
        view=dict(frame,id='actual-room',subjects=[query],resolution=[1920,1080])
        self.assertEqual(opening_frame_findings(view,scene),[])
        with self.assertRaises(ValueError):subject_meshes('room:unresolved',scene['meshes'])
        view['subjects']=['dining-vase']
        with self.assertRaises(ValueError):opening_frame_findings(view,scene)

    def test_real_unresolved_export_subject_refuses_before_opening_admission(self):
        from archpipe.concept.garden_render_review import opening_frame_findings
        frozen=json.loads((FIXTURE.parent/'flythrough-unresolved-subject.json').read_text())
        scene={'meshes':frozen['meshes'],'props':[]}
        self.assertEqual(frozen['failed_receipt'][0]['matched_objects'],[])
        with self.assertRaisesRegex(ValueError,'unresolved built subject'):
            opening_frame_findings(frozen['view'],scene)
        clean=dict(frozen['view'],subjects=['landscape-g6-terrace'])
        self.assertEqual(opening_frame_findings(clean,scene),[])
        sibling=deepcopy(scene)
        sibling['meshes'][0]['id']='another-villa-paving'
        with self.assertRaisesRegex(ValueError,'unresolved built subject'):
            opening_frame_findings(clean,sibling)
        renamed=dict(clean,subjects=['another-villa-paving'])
        self.assertEqual(opening_frame_findings(renamed,sibling),[])

    def test_delivered_path_passes_actual_frozen_geometry_and_hash(self):
        import gzip
        frozen=json.loads(gzip.decompress((FIXTURE.parent/'flythrough-delivered-geometry.json.gz').read_bytes()))
        path=W.authored_path()
        self.assertEqual(path['sha256'],frozen['path_sha256'])
        self.assertEqual(W.digest(path['frames']),frozen['frame_list_sha256'])
        runtime=[{'id':m['id'].removeprefix('runtime-'),'faces':m['faces']}
                 for m in frozen['scene']['meshes'] if m['id'].startswith('runtime-')]
        self.assertEqual(W.digest(runtime),frozen['evaluated_meshes_sha256'])
        self.assertTrue(W.guard_path(path,frozen['scene'],ground_m=-3)['passed'])

    def test_frozen_real_wall_and_transparent_pane_refuse_clean_path_passes(self):
        for name in ('wall_knots','glass_knots','clear_knots'):
            path=W.sample_path(self.real[name]);result=W.guard_path(path,self.real['scene'],ground_m=-3)
            self.assertEqual(result['passed'],name=='clear_knots',name)
        # The actual pane is still physical after an arbitrary translation and rename.
        scene=deepcopy(self.real['scene']);knots=deepcopy(self.real['glass_knots'])
        for mesh in scene['meshes']:
            mesh['id']='renamed-'+mesh['id']
            for face in mesh['faces']:
                for point in face:point[0]+=31;point[1]-=14
        for knot in knots:knot['position'][0]+=31;knot['position'][1]-=14
        self.assertFalse(W.guard_path(W.sample_path(knots),scene,ground_m=-3)['passed'])

    def test_real_thin_glass_tunnelling_is_rejected_between_clear_endpoints(self):
        sweep=CameraSweep(self.real['scene'])
        start,end=[17.5,-24.15,-1.65],[17.5,-23.15,-1.65]
        self.assertNotIn('shell-022-glass-clear',sweep.findings(start,start,ground_m=-3))
        self.assertNotIn('shell-022-glass-clear',sweep.findings(end,end,ground_m=-3))
        self.assertIn('shell-022-glass-clear',sweep.findings(start,end,ground_m=-3))

    def test_fast_segment_and_yaw_fail_and_normal_motion_stays_quiet(self):
        path=W.sample_path(self.real['clear_knots']);frames=deepcopy(path['frames'])
        frames[1]['camera']['position'][0]+=1
        self.assertTrue(W.motion_findings(frames,path['settings'])[1]['failures'])
        fast=deepcopy(path);fast['frames']=frames
        fast['sha256']=W.digest({k:v for k,v in fast.items() if k!='sha256'})
        result=W.guard_path(fast,self.real['scene'],ground_m=-3)
        self.assertFalse(result['passed'])
        self.assertIn('linear speed exceeds registered bound',result['frames'][1]['failures'])
        frames=deepcopy(path['frames']);frames[1]['yaw_deg']+=30
        self.assertTrue(W.motion_findings(frames,path['settings'])[1]['failures'])
        self.assertFalse(any(r['failures'] for r in W.motion_findings(path['frames'],path['settings'])))

    def test_path_hash_is_deterministic_and_mutations_refuse(self):
        points=[[1,2,-1.65],[2,3,-1.65],[3,2,-1.65]]
        yaws=[dict(seconds=0,yaw_deg=0),dict(seconds=719/24,yaw_deg=45)]
        first=W.walking_path(points,yaws);second=W.walking_path(points,yaws)
        self.assertEqual(first,second);W.require_path_hash(first)
        first['frames'][350]['camera']['position'][0]+=.001
        with self.assertRaises(ValueError):W.require_path_hash(first)

    def test_early_physical_gate_cannot_authorize_rendering(self):
        path=W.sample_path(self.real['clear_knots'])
        result=W.guard_path(path,self.real['scene'],ground_m=-3)
        self.assertTrue(result['passed'])
        with self.assertRaises(ValueError):W.require_renderable(result)
        with self.assertRaises(ValueError):W.require_renderable({'passed':False,'acceptance_scope':'complete per-frame render admission'})

    def test_source_rule_uses_all_frames_and_clip_population(self):
        row=dict(lamp_luminance_sum=1.,daylight_luminance_sum=3.,lamp_population=[])
        rows=[deepcopy(row) for _ in range(720)]
        self.assertEqual(W.clip_source_group(rows)['group'],'day')
        rows[0]['lamp_luminance_sum']=99999
        rows[0]['lamp_population']=[dict(flux_lm=100,cct_k=3000)]
        self.assertEqual(W.clip_source_group(rows)['group'],'lamp-dominant')
        with self.assertRaises(ValueError):W.clip_source_group(rows[:-1])

    def test_temporal_clean_static_surface_noise_and_missing_coverage(self):
        h,w=270,400;yy,xx=np.mgrid[:h,:w];camera=dict(position=[0,0,0],target=[1,0,0],lens_mm=24,sensor_mm=36)
        positions=np.ones((h,w,4));positions[:,:,0]=3
        positions[:,:,1]=-(xx+.5-w/2)*3/(w*24/36)
        positions[:,:,2]=-(yy+.5-h/2)*3/(w*24/36)
        image=np.full((h,w,3),120,dtype=np.uint8)
        settings=deepcopy(W.policy());settings['temporal_difference']['minimum_static_pixels']=500
        self.assertTrue(W.temporal_pair(image,image,positions,positions,camera,settings)['passed'])
        self.assertFalse(W.temporal_pair(image,image+10,positions,positions,camera,settings)['passed'])
        positions[:,:,3]=0
        self.assertFalse(W.temporal_pair(image,image,positions,positions,camera,settings)['passed'])

    def test_real_glazed_endpoint_refuses_early_static_coverage(self):
        frozen=json.loads((FIXTURE.parent/'flythrough-static-coverage.json').read_text())
        for row in frozen['frames']:
            result=W.static_coverage(row['eligible_opaque_pixels'],row['pixels'])
            self.assertEqual(result['passed'],row['index']!=719)
        self.assertFalse(W.static_coverage(0,1920*1080)['passed'])
        self.assertTrue(W.static_coverage(1000,1920*1080)['passed'])
        self.assertFalse(W.static_coverage(999,1920*1080)['passed'])
        with self.assertRaises(ValueError):W.static_coverage(1,0)

    def test_exposure_command_refuses_failed_or_stale_native_coverage(self):
        import tempfile
        from unittest.mock import patch
        from scripts import flythrough as command
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'coverage').mkdir();(root/'assembly').mkdir()
            assembly={'receipt':{'evaluated_meshes_sha256':'actual-meshes'}}
            (root/'assembly/assembly.json').write_text(json.dumps(assembly))
            base={'passed':True,'path_sha256':'actual-path','policy_sha256':W.digest(W.policy()),
                  'evaluated_meshes_sha256':'actual-meshes'}
            for changed in ({'passed':False},{'path_sha256':'old-path'},
                            {'policy_sha256':'old-policy'},{'evaluated_meshes_sha256':'old-meshes'}):
                row=dict(base,**changed);row['sha256']=W.digest(row)
                (root/'coverage/summary.json').write_text(json.dumps(row))
                with patch.object(command,'require_inputs',return_value={'sha256':'actual-path'}),patch.object(command,'project_context') as context:
                    with self.assertRaisesRegex(ValueError,'coverage checkpoint'):
                        command.graphics(root,'exposure',Path('/unused/blender'))
                    context.assert_not_called()


if __name__=='__main__':unittest.main()
