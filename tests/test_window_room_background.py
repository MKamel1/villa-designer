"""Actual room-percentile contamination, quiet controls and multi-pane siblings."""
import copy
import gzip
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image
from archpipe import render_qa
from archpipe.window_qa import pack_pixels, room_background_pixels, unpack_pixels

FIXTURES = Path(__file__).parent / 'fixtures'


class RoomBackgroundOwnership(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = json.loads(gzip.decompress((FIXTURES / 'walk2-window-room-before.json.gz').read_bytes()))
        cls.exact = {row['frame']: row for row in json.loads(gzip.decompress(
            (FIXTURES / 'walk2-exact-room-native.json.gz').read_bytes()))['frames']}

    def context(self, index):
        record = self.before['cases'][str(index)]
        context = dict(copy.deepcopy(record['qa_scene']), camera=dict(pitch_deg=90, shift_y=0),
                    daylight=True, sky=dict(sun=True), white_balance=True,
                    subjects=record['subjects'], exposure_locked=True,
                    lights=dict(on=True, count=62, with_ies=62))
        if index in self.exact:
            context['room_glazing_pixels'] = pack_pixels(
                self.exact[index]['glazing_pixels'], 480, 270, step=3)
        return context

    @staticmethod
    def brightness_failures(report):
        return [row for row in report['checks']
                if row['check'].startswith('window_brightness') and row['status'] == 'FAIL']

    def test_real_other_window_is_not_inside_room_and_camera_sibling_generalises(self):
        old = dict(__name__='frozen_room_background')
        exec(compile(self.before['source'], 'frozen_room_background', 'exec'), old)
        for index in (1370, 1390):
            image = FIXTURES / f'walk2-room-frame-{index}.png'
            context = self.context(index)
            self.assertTrue(self.brightness_failures(old['check'](image, context)))
            self.assertFalse(self.brightness_failures(render_qa.check(image, context)))
            for window in context['windows']:
                window['id'] = 'another-villa-' + window['id']
            self.assertFalse(self.brightness_failures(render_qa.check(image, context)))

    def test_real_dim_window_mutation_still_fires_and_clipping_is_not_waived(self):
        context = self.context(1370)
        target = next(window for window in context['windows'] if window['id'].endswith('face-25'))
        with Image.open(FIXTURES / 'walk2-room-frame-1370.png') as source:
            image = source.convert('RGB')
        for point in unpack_pixels(target['visible_pixels'], *image.size):
            image.putpixel(point, (50, 50, 50))
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'dim-actual-window.png'
            image.save(file)
            self.assertTrue(self.brightness_failures(render_qa.check(file, context)))
        report = render_qa.check(FIXTURES / 'walk2-room-frame-1217.png', self.context(1217))
        self.assertTrue(any(row['status'] == 'FAIL' and row['check'].startswith('window_view')
                            for row in report['checks']))

    def test_all_native_panes_excluded_including_small_and_corrupt_ownership_refuses(self):
        large = dict(screen=[0, 0, .5, 1], visible_pixels=pack_pixels(
            [(x, y) for x in range(0, 6, 2) for y in range(0, 12, 2)], 12, 12))
        small = dict(screen=[.99, .99, 1, 1], visible_pixels=pack_pixels([(8, 8)], 12, 12))
        self.assertNotIn((9, 9), room_background_pixels([large, small], 12, 12))
        self.assertIn((9, 9), room_background_pixels([large], 12, 12))
        invalid = copy.deepcopy(small)
        invalid['visible_pixels']['runs'] = []
        with self.assertRaisesRegex(ValueError, 'nonempty'):
            room_background_pixels([large, invalid], 12, 12)

    def test_legacy_all_rectangles_and_unrelated_sizes_keep_the_same_room(self):
        for width, height in ((120, 60), (270, 180)):
            windows = [dict(screen=[0, 0, .25, 1]), dict(screen=[.75, 0, 1, 1])]
            pixels = room_background_pixels(windows, width, height)
            self.assertTrue(pixels)
            self.assertTrue(all(int(width * .25) <= x < int(width * .75) for x, y in pixels))
            self.assertEqual(pixels, room_background_pixels(list(reversed(windows)), width, height))

    def test_exact_native_room_grid_and_adapter_refuse_missing_or_wrong_grid(self):
        # Enter through the actual host driver, which establishes its sibling
        # CLI-module import context before loading the post-render adapter.
        from scripts import flythrough
        from scripts.villa_render import villa_qa_context
        context = self.context(1370)
        exact = {tuple(point) for point in self.exact[1370]['glazing_pixels']}
        background = set(room_background_pixels(context['windows'], 480, 270,
                                                context['room_glazing_pixels']))
        self.assertEqual(background, {(x, y) for x in range(0, 480, 3)
                                      for y in range(0, 270, 3)} - exact)
        record = copy.deepcopy(self.before['cases']['1370'])
        record['qa_scene']['room_glazing_pixels'] = context['room_glazing_pixels']
        actual = villa_qa_context(dict(lights=[]), dict(state='day', layers_on=[],
            exposure='daylight', camera={}), record)
        self.assertEqual(actual['room_glazing_pixels'], context['room_glazing_pixels'])
        image = FIXTURES / 'walk2-room-frame-1370.png'
        with self.assertRaisesRegex(ValueError, 'ownership is missing'):
            render_qa.check(image, dict(context, room_glazing_pixels=None))
        with self.assertRaisesRegex(ValueError, 'mismatches'):
            render_qa.check(image, dict(context, room_glazing_pixels=pack_pixels([(0, 0)], 480, 270)))

    def test_real_full_image_room_mask_cannot_silently_omit_required_comparison(self):
        frozen = json.loads(gzip.decompress((FIXTURES / 'walk2-room-empty-background-before.json.gz').read_bytes()))
        old = dict(__name__='frozen_empty_room_population')
        exec(compile(frozen['source'], 'frozen_empty_room_population', 'exec'), old)
        image = FIXTURES / 'walk2-room-frame-1370.png'
        escaped = old['check'](image, frozen['context'])
        self.assertTrue(escaped['passed'])
        self.assertFalse(any(row['check'].startswith('window_brightness') for row in escaped['checks']))
        with self.assertRaisesRegex(ValueError, 'brightness population is empty'):
            render_qa.check(image, frozen['context'])
        exterior = render_qa.check(image, dict(frozen['context'], exterior_camera=True))
        self.assertFalse(any(row['check'].startswith('window_brightness') for row in exterior['checks']))

    def test_real_legacy_rectangle_adapter_is_not_a_missing_native_mask(self):
        import io
        from scripts import flythrough
        from scripts.villa_render import villa_qa_context
        frozen = json.loads(gzip.decompress((FIXTURES / 'walk2-legacy-room-before.json.gz').read_bytes()))
        old = dict(__name__='frozen_legacy_room_declaration')
        exec(compile(frozen['source'], 'frozen_legacy_room_declaration', 'exec'), old)
        image = io.BytesIO()
        Image.new('RGB', (120, 80), (150, 150, 150)).save(image, format='PNG')
        image.seek(0)
        with self.assertRaisesRegex(ValueError, 'native room glazing ownership is missing'):
            old['check'](image, frozen['context'])
        record = copy.deepcopy(self.before['cases']['1370'])
        record['qa_scene']['windows'] = frozen['context']['windows']
        record['qa_scene'].pop('room_glazing_pixels', None)
        context = villa_qa_context(dict(lights=[]), dict(state='day', layers_on=[],
            exposure='daylight', camera={}), record)
        image.seek(0)
        result = render_qa.check(image, context)
        self.assertTrue(any(row['check'].startswith('window_brightness') for row in result['checks']))
        self.assertTrue(any(row['check'].startswith('window_view') for row in result['checks']))


if __name__ == '__main__':
    unittest.main()
