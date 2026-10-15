"""Independent image-difference controls for renderer comparisons."""
from pathlib import Path
import sys
import unittest
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from blender52_compare import image_metrics
class ImageComparison(unittest.TestCase):
    def test_identical_images_are_zero_including_black_chromaticity_mask(self):
        a=Image.new('RGB',(4,4),(120,130,140));r=image_metrics(a,a)
        self.assertEqual(r['display_rgb_mae'],0)
        self.assertEqual(r['chromaticity']['mean_absolute_xy_difference'],[0,0])
    def test_black_pixels_do_not_invent_chromaticity(self):
        a=Image.new('RGB',(4,4),(0,0,0));r=image_metrics(a,a)
        self.assertEqual(r['chromaticity']['valid_pixels'],0)
        self.assertIsNone(r['chromaticity']['mean_absolute_xy_difference'])

    def test_known_channel_delta_and_different_shape_refused(self):
        a=Image.new('RGB',(4,4),(100,100,100));b=Image.new('RGB',(4,4),(110,100,100))
        r=image_metrics(a,b)
        self.assertAlmostEqual(r['display_rgb_mae'],10/255/3)
        self.assertAlmostEqual(r['display_rgb_absolute_error_p95'],10/255)
        self.assertGreater(r['linear_luminance']['mean_delta'],0)
        with self.assertRaisesRegex(ValueError,'dimensions'):image_metrics(a,Image.new('RGB',(3,4)))

class ClothAttribution(unittest.TestCase):
    def test_runtime_seed_confounded_replay_refused_and_clean_control_accepted(self):
        from summarize_blender52 import controlled_cloth_attribution
        import json
        from copy import deepcopy
        fixture=json.loads((ROOT/'tests/fixtures/blender52-cloth-seed-before.json').read_text())
        a,b=fixture['before'],fixture['rebaked']
        with self.assertRaisesRegex(ValueError,'seed'):controlled_cloth_attribution(a,b)
        b=deepcopy(fixture['controlled']);b['simulation']['initial_vertices_sha256']='changed'
        with self.assertRaisesRegex(ValueError,'vertices'):controlled_cloth_attribution(a,b)
        self.assertTrue(controlled_cloth_attribution(a,fixture['controlled'])['output_geometry_equal'])
        sibling=deepcopy(fixture['controlled']);sibling['simulation']['pattern_seed']+=1
        with self.assertRaisesRegex(ValueError,'seed'):controlled_cloth_attribution(a,sibling)

class TaskIdentity(unittest.TestCase):
    def test_real_repeated_task_labels_and_renamed_sibling_retain_every_point(self):
        import json
        from copy import deepcopy
        from summarize_blender52 import indexed_tasks
        points=json.loads((ROOT/'tests/fixtures/blender52-duplicate-tasks.json').read_text())
        self.assertLess(len({(p['room'],p['label']) for p in points}),len(points))
        self.assertEqual(len(indexed_tasks(points)),len(points))
        self.assertEqual(list(indexed_tasks(points).values()),points)
        sibling=deepcopy(points)
        for p in sibling:p['room']='renamed-room';p['label']='same repeated label'
        self.assertEqual(len(indexed_tasks(sibling)),len(sibling))
        self.assertEqual(len(indexed_tasks(points[:1])),1)
