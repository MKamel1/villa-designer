"""Real rejected crop, quiet controls, siblings and policy-driven format checks."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import tempfile
import numpy as np
from PIL import Image
from archpipe.walkthrough_quality import isolated_mask,speckle_frame,encoding_error
from archpipe import flythrough as W

FIXTURES=Path(__file__).parent/'fixtures'


class MovingImageQuality(unittest.TestCase):
    def test_native_reconstruction_is_policy_bound_and_metering_keeps_original(self):
        settings=json.loads((W.ROOT/'knowledge/walk2-policy.json').read_text())
        self.assertEqual(W.pixel_filter_settings(settings),dict(type='BLACKMAN_HARRIS',width_pixels=2.5))
        self.assertEqual(W.pixel_filter_settings(settings,measurement=True),dict(type='BLACKMAN_HARRIS',width_pixels=1.5))
        self.assertEqual(W.pixel_filter_settings({'fps':25}),dict(type='BLACKMAN_HARRIS',width_pixels=1.5))
        for width in (0,11,float('nan'),True):
            with self.assertRaises(ValueError):W.pixel_filter_settings(dict(pixel_filter=dict(beauty=dict(type='BLACKMAN_HARRIS',width_pixels=width))))
        with self.assertRaises(ValueError):W.pixel_filter_settings(dict(pixel_filter=dict(beauty=dict(type='POST_BLUR',width_pixels=2.5))))
        value=W.pixel_filter_settings(settings);value['width_pixels']=9
        self.assertEqual(W.pixel_filter_settings(settings)['width_pixels'],2.5)

    def test_sample_registration_precedes_graphics_in_fresh_and_retained_directory(self):
        from scripts import flythrough as command
        class ReachedGraphics(Exception):
            pass
        settings=json.loads((W.ROOT/'knowledge/walk2-policy.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            for name in ('fresh','renamed-sibling'):
                out=Path(directory)/name
                for retry in range(2):
                    def graphics(*args):
                        receipt=json.loads((out/'sampling/registration.json').read_text())
                        self.assertEqual(receipt['path_sha256'],'registered-path')
                        self.assertEqual(receipt['policy_sha256'],W.digest(settings))
                        self.assertEqual(receipt['early_pair_ends'],[12,36])
                        raise ReachedGraphics
                    with patch.object(command,'require_inputs',return_value={'sha256':'registered-path'}), \
                         patch.object(command,'require_preview_review'), \
                         patch.object(command,'policy',return_value=settings), \
                         patch.object(command,'early_temporal_indices',return_value=[12,36]), \
                         patch.object(command,'graphics',side_effect=graphics):
                        with self.assertRaises(ReachedGraphics):
                            command.choose_samples(out,Path('unused-blender'))

    def test_complete_preview_receipt_gates_all_final_resolution_entrypoints(self):
        from scripts import flythrough as command
        settings=json.loads((W.ROOT/'knowledge/walk2-policy.json').read_text())
        path={'sha256':'reviewed-path'}
        with tempfile.TemporaryDirectory() as temporary,patch.object(command,'policy',return_value=settings):
            for name in ('fresh','independent-sibling'):
                out=Path(temporary)/name
                with patch.object(command,'require_inputs',return_value=path),patch.object(command,'graphics') as graphics:
                    with self.assertRaises(FileNotFoundError):command.choose_samples(out,Path('unused'))
                    graphics.assert_not_called()
                    self.assertFalse((out/'sampling/registration.json').exists())
                (out/'preview').mkdir(parents=True)
                video=out/'preview/walkthrough.mp4';video.write_bytes(b'reviewed-preview-bytes')
                review=dict(passed=True,path_sha256=path['sha256'],video_sha256=command.file_hash(video))
                receipt=out/'preview/visual-review.json'
                receipt.write_text(json.dumps(review))
                command.require_preview_review(out,path)
                for field,value in (('passed',False),('path_sha256','other-path'),('video_sha256','other-bytes')):
                    receipt.write_text(json.dumps(dict(review,**{field:value})))
                    for stage in ('reference','sampling','final'):
                        with patch.object(command,'require_inputs',return_value=path),patch.object(command,'project_context') as native:
                            with self.assertRaisesRegex(ValueError,'review missing or stale'):
                                command.graphics(out,stage,Path('unused'))
                            native.assert_not_called()
                receipt.write_text(json.dumps(review));video.write_bytes(b'changed-preview')
                with self.assertRaisesRegex(ValueError,'review missing or stale'):
                    command.require_preview_review(out,path)

    def test_real_lavender_crop_and_adjacent_pair_refuse(self):
        masks=[]
        for index in (599,600):
            with Image.open(FIXTURES/f'walk2-frame-{index}-crop.png') as image:rgb=np.array(image.convert('RGB'))
            result,mask=speckle_frame(rgb,masks[-1] if masks else None)
            self.assertFalse(result['passed'])
            masks.append(mask)
        self.assertGreater(result['flicker_per_10000'],8)
        # The actual rejected full-frame values are frozen, independent of builders.
        before=json.loads((FIXTURES/'walk2-speckle-before.json').read_text())
        self.assertFalse(before['passed'])
        self.assertEqual(len(before['frames']),17)
        self.assertAlmostEqual(before['frames'][12]['density_per_10000'],15.573581788388879)

    def test_actual_closed_attached_first_fix_still_refuses_fine_foliage_speckle(self):
        first=json.loads((FIXTURES/'walk2-speckle-first-fix.json').read_text())
        self.assertFalse(first['passed'])
        self.assertEqual(len(first['frames']),17)
        self.assertTrue(all(not row['passed'] for row in first['frames']))
        with Image.open(FIXTURES/'walk2-frame-600-first-fix-crop.png') as im:
            measured,_=speckle_frame(np.array(im.convert('RGB')))
        self.assertFalse(measured['passed'])
        self.assertGreater(measured['density_per_10000'],5)

    def test_clean_gradient_quiet_noise_and_moved_sibling_fire(self):
        image=np.repeat(np.tile(np.arange(160,dtype=np.uint8),(100,1))[:,:,None],3,axis=2)
        result,mask=speckle_frame(image)
        self.assertTrue(result['passed']);self.assertEqual(result['density_per_10000'],0)
        for row,column in ((20,30),(50,80)):
            noisy=image.copy();noisy[row:row+30:3,column:column+30:3]=255
            result,_=speckle_frame(noisy,mask)
            self.assertFalse(result['passed']);self.assertGreater(result['flicker_per_10000'],8)
        with self.assertRaises(ValueError):isolated_mask(image.astype(float))
        with self.assertRaises(ValueError):speckle_frame(image,np.zeros((1,1),bool))

    def test_real_encoding_method_quiet_and_artifact_sibling(self):
        with Image.open(FIXTURES/'walk2-frame-600-crop.png') as image:original=np.array(image.convert('RGB'))
        self.assertTrue(encoding_error(original,original)['passed'])
        bad=original.copy();bad[20:40,30:50]=0
        self.assertFalse(encoding_error(original,bad)['passed'])
        with self.assertRaises(ValueError):encoding_error(original,bad[:-1])

    def test_format_uses_registered_frame_count_and_rate(self):
        from scripts.flythrough import require_video_format
        settings=W.policy();settings.update(fps=30,frames=2250,duration_seconds=75)
        stream=dict(nb_frames='2250',r_frame_rate='30/1',duration='75.000000',pix_fmt='yuv420p',codec_name='h264')
        self.assertTrue(require_video_format(stream,settings))
        for key,value in [('nb_frames','720'),('r_frame_rate','24/1'),('duration','30'),('pix_fmt','rgb24')]:
            with self.assertRaises(ValueError):require_video_format(dict(stream,**{key:value}),settings)
        # A different bounded job is accepted from policy, without a 2250/30 special case.
        settings.update(fps=25,frames=250,duration_seconds=10)
        self.assertTrue(require_video_format(dict(stream,nb_frames='250',r_frame_rate='25/1',duration='10'),settings))

    def test_subframe_camera_matches_samples_and_eased_endpoint(self):
        settings=W.policy();settings.update(fps=30,frames=120,duration_seconds=4)
        points=[[0,0,1.35],[.3,0,1.35],[.3,.1,1.35]]
        yaws=[dict(seconds=0,yaw_deg=0),dict(seconds=119/30,yaw_deg=30)]
        path=W.walking_path(points,yaws,settings,travel_seconds=3)
        for frame in path['frames']:
            pose=W.camera_at_seconds(path,frame['seconds'])
            np.testing.assert_allclose(pose['position'],frame['camera']['position'],atol=1e-12)
            np.testing.assert_allclose(pose['target'],frame['camera']['target'],atol=1e-12)
        self.assertEqual(W.camera_at_seconds(path,-1)['position'],points[0])
        self.assertEqual(W.camera_at_seconds(path,8)['position'],points[-1])
        self.assertGreater(W.camera_at_seconds(path,.5+.25/30)['position'][0],W.camera_at_seconds(path,.5-.25/30)['position'][0])

    def test_final_packages_cover_policy_once_and_keep_preview_checkpoint(self):
        from scripts.walk2_queue import commands,packages
        for count,size in ((2250,48),(719,37),(1,1)):
            groups=packages(count,size)
            self.assertEqual([i for group in groups for i in group],list(range(count)))
            self.assertTrue(all(0<len(group)<=size for group in groups))
        settings=json.loads((W.ROOT/'knowledge/walk2-policy.json').read_text())
        preview=dict(commands('preview',settings))
        frames=preview['all-preview-qa'][-1].split(',')
        self.assertEqual(len(frames),settings['frames'])
        final=commands('final',settings)
        self.assertEqual(final[-4][0],'all-adjacent-temporal')
        self.assertEqual(final[-3][0],'all-frame-speckle')
        self.assertEqual(final[-1][0],'encode-web')
