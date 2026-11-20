"""Pinned native API proof: true camera transforms during the Cycles shutter.

Run with Blender -b --python-exit-code 1 -P tests/blender_walk2_camera.py.
"""
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import bpy
from archpipe.blender.walkthrough import animate_camera
from archpipe.flythrough import walking_path,policy


class NativeCameraMotion(unittest.TestCase):
    def test_real_shutter_sign_discontinuity_refuses_before_and_accepts_continuous_construction(self):
        import gzip
        from copy import deepcopy
        from unittest.mock import patch
        from archpipe.blender import walkthrough as command
        fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/walk2-shutter-quaternion-before.json.gz').read_bytes()))
        actual=fixture['path']
        check=json.loads((ROOT/'knowledge/walk2-policy.json').read_text())['camera_motion_check']
        self.assertGreater(fixture['readback']['maximum_error_degrees'],179.)
        self.assertEqual([row['index'] for row in fixture['continuity']['failures']],[1020,1635,1868])
        namespace=dict(vars(command))
        exec(compile(fixture['animate_camera_source'],'frozen-shutter-construction','exec'),namespace)
        for shift in ((0.,0.,0.),(13.,-21.,7.)):
            case=deepcopy(actual)
            for knot in case['knots']:
                knot['position']=[a+b for a,b in zip(knot['position'],shift)]
            for frame in case['frames']:
                frame['diagnostic_name']='another-villa-camera'
                for field in ('position','target'):
                    frame['camera'][field]=[a+b for a,b in zip(frame['camera'][field],shift)]
            with patch.object(command,'animate_camera',namespace['animate_camera']):
                with self.assertRaisesRegex(ValueError,'shutter orientation differs'):
                    command.validate_camera_motion(case,check)
                quiet=deepcopy(case);quiet['frames']=quiet['frames'][:20]
                self.assertTrue(command.validate_camera_motion(quiet,check)['passed'])
            result=command.validate_camera_motion(case,check)
            self.assertTrue(result['passed'])
            self.assertEqual(result['evaluated_poses'],2250*5)
            self.assertLessEqual(result['maximum_orientation_error_degrees'],check['maximum_orientation_error_degrees'])
        with self.assertRaisesRegex(ValueError,'policy is missing'):
            command.validate_camera_motion(actual)
        for settings in (dict(check,maximum_orientation_error_degrees=0),dict(check,shutter_fractions=[0])):
            with self.assertRaisesRegex(ValueError,'Invalid native'):
                command.validate_camera_motion(actual,settings)

    def test_native_reconstruction_readback_and_source_meter_isolation(self):
        from archpipe.blender.walkthrough import configure_pixel_filter
        settings=json.loads((ROOT/'knowledge/walk2-policy.json').read_text())
        self.assertEqual(configure_pixel_filter(settings),dict(type='BLACKMAN_HARRIS',width_pixels=2.5))
        self.assertEqual(configure_pixel_filter(settings,measurement=True),dict(type='BLACKMAN_HARRIS',width_pixels=1.5))
        self.assertEqual(configure_pixel_filter(settings),dict(type='BLACKMAN_HARRIS',width_pixels=2.5))

    def test_rendered_camera_exposure_spreads_a_physical_edge(self):
        import numpy as np
        from mathutils import Vector
        from archpipe.flythrough import camera_at_seconds
        bpy.ops.wm.read_factory_settings(use_empty=True)
        scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU'
        scene.cycles.samples=256;scene.cycles.use_denoising=False;scene.cycles.max_bounces=0
        scene.render.resolution_x=scene.render.resolution_y=128;scene.render.resolution_percentage=100
        scene.world=bpy.data.worlds.new('black');scene.world.use_nodes=True
        scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=0
        scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
        scene.view_settings.exposure=0;scene.render.image_settings.file_format='PNG'
        mesh=bpy.data.meshes.new('stripe')
        mesh.from_pydata([[.1,-.02,1.2],[.1,.02,1.2],[.1,.02,1.5],[.1,-.02,1.5]],[],[[0,1,2,3]])
        stripe=bpy.data.objects.new('stripe',mesh);bpy.context.collection.objects.link(stripe)
        material=bpy.data.materials.new('white-emission');material.use_nodes=True
        nodes=material.node_tree.nodes;nodes.clear();emission=nodes.new('ShaderNodeEmission')
        output=nodes.new('ShaderNodeOutputMaterial')
        material.node_tree.links.new(emission.outputs[0],output.inputs['Surface']);mesh.materials.append(material)
        data=bpy.data.cameras.new('physical-camera');camera=bpy.data.objects.new('physical-camera',data)
        bpy.context.collection.objects.link(camera);scene.camera=camera
        data.lens=24;data.sensor_width=36;data.sensor_fit='HORIZONTAL';data.clip_start=.001
        settings=policy();settings.update(fps=30,frames=60,duration_seconds=2,
            motion_blur=dict(enabled=True,shutter_frames=.5,position='CENTER'))
        path=walking_path([[0,-.2,1.35],[0,.2,1.35]],
            [dict(seconds=0,yaw_deg=0),dict(seconds=59/30,yaw_deg=0)],settings)
        directory=ROOT/'out/walk2/diagnosis/native-rendered-motion-blur';directory.mkdir(parents=True,exist_ok=True)
        rows=[]
        for enabled in (False,True):
            pose=camera_at_seconds(path,1.0);camera.location=pose['position'];camera.rotation_mode='QUATERNION'
            camera.rotation_quaternion=(Vector(pose['target'])-camera.location).to_track_quat('-Z','Y')
            path['settings']['motion_blur']['enabled']=enabled;animate_camera(camera,path,30)
            scene.render.filepath=str(directory/('blur.png' if enabled else 'sharp.png'))
            bpy.ops.render.render(write_still=True)
            image=bpy.data.images.load(scene.render.filepath)
            pixels=np.array(image.pixels[:]).reshape(128,128,4);bpy.data.images.remove(image)
            values=pixels[64,:,0]
            rows.append(dict(enabled=enabled,partial_pixels=int(((values>.1)&(values<.9)).sum())))
        # An assumed diagnostic screen counts fractional edge coverage; it is
        # independent of the API flags and production image acceptance limits.
        self.assertGreaterEqual(rows[1]['partial_pixels'],rows[0]['partial_pixels']+4)
        (directory/'receipt.json').write_text(json.dumps(dict(passed=True,
            blender=bpy.app.version_string,device='CPU',rows=rows),indent=2)+'\n')

    def test_real_same_camera_dispatch_derives_root_from_parsed_arguments(self):
        from unittest.mock import patch
        from archpipe.blender import walkthrough as command
        sibling=ROOT/'out/walk2-independent-dispatch'
        received=[]
        frozen=json.loads((ROOT/'tests/fixtures/walk2-native-dispatch-before.json').read_text())
        namespace=dict(vars(command))
        exec(compile(frozen['main_source'],'frozen-native-dispatch','exec'),namespace)
        with patch.object(sys,'argv',['walkthrough.py','--','--root',str(sibling),'--stage','same-camera']), \
             patch('runpy.run_path',return_value={'main':received.append}):
            with self.assertRaises(UnboundLocalError):namespace['main']()
            command.main()
        self.assertEqual(received,[sibling])

    def test_same_camera_diagnostic_uses_the_selected_output_root(self):
        import runpy
        from unittest.mock import patch
        module=runpy.run_path(str(ROOT/'scripts/walk2_same_camera.py'))
        class ReachedSelectedRoot(Exception):
            pass
        sibling=ROOT/'out/walk2-independent-diagnostic'
        def load(args):
            self.assertEqual(Path(args.root),sibling)
            raise ReachedSelectedRoot
        with patch.object(module['W'],'load_context',side_effect=load):
            with self.assertRaises(ReachedSelectedRoot):module['main'](sibling)

    def test_cycles_half_frame_exposure_and_actual_subframe_transform(self):
        scene=bpy.context.scene;scene.render.engine='CYCLES'
        settings=policy();settings.update(fps=30,frames=60,duration_seconds=2,
            motion_blur=dict(enabled=True,shutter_frames=.5,position='CENTER'))
        path=walking_path([[0,0,1.35],[.2,0,1.35]],
             [dict(seconds=0,yaw_deg=0),dict(seconds=59/30,yaw_deg=15)],settings)
        data=bpy.data.cameras.new('motion-test')
        camera=bpy.data.objects.new('motion-test',data);bpy.context.collection.objects.link(camera)
        animate_camera(camera,path,30)
        self.assertTrue(scene.render.use_motion_blur)
        self.assertEqual(scene.render.motion_blur_shutter,.5)
        self.assertEqual(scene.render.motion_blur_position,'CENTER')
        self.assertEqual(scene.render.fps,30)
        scene.frame_set(29,subframe=.75);before=list(camera.location)
        scene.frame_set(30,subframe=.25);after=list(camera.location)
        self.assertGreater(after[0],before[0])
        self.assertEqual(before[2],after[2])
        self.assertEqual(len(camera.animation_data.action.fcurves),7)
        receipt=dict(passed=True,blender=bpy.app.version_string,shutter_frames=scene.render.motion_blur_shutter,
                     fps=scene.render.fps,before=before,after=after,
                     mechanism='Cycles camera location and quaternion keyframes; no compositor blur')
        out=ROOT/'out/walk2/diagnosis';out.mkdir(parents=True,exist_ok=True)
        (out/'native-motion-camera.json').write_text(json.dumps(receipt,indent=2)+'\n')
        settings['motion_blur']['enabled']=False
        animate_camera(camera,path,30)
        self.assertFalse(scene.render.use_motion_blur)

suite=unittest.defaultTestLoader.loadTestsFromTestCase(NativeCameraMotion)
if not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful():raise SystemExit(1)
