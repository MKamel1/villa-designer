"""Real complete-preview false positive and native pixel-ownership boundaries."""
import copy
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from archpipe import render_qa
from archpipe.window_qa import pack_pixels, unpack_pixels

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'tests/fixtures'


class WindowPixelOwnership(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = json.loads(gzip.decompress((FIXTURES/'walk2-window-qa-before.json.gz').read_bytes()))
        cls.pixels = json.loads((FIXTURES/'walk2-window-visible-pixels.json').read_text())['pixels']

    def context(self):
        record = self.before['records']['1210']
        return dict(record['qa_scene'], camera=dict(pitch_deg=90,shift_y=0),
                    daylight=True,sky=dict(sun=True),white_balance=True,
                    subjects=record['subjects'],exposure_locked=True,
                    lights=dict(on=True,count=62,with_ies=62))

    def corrected_context(self):
        qa = self.context()
        qa['windows'] = [dict(id='actual-visible-face-19', screen=[0,0,22/480,257/270],
                              visible_pixels=copy.deepcopy(self.pixels))]
        return qa

    def statuses(self, report, prefix):
        return [r['status'] for r in report['checks'] if r['check'].startswith(prefix)]

    def test_frozen_real_rectangle_fails_but_native_visible_glass_stays_quiet(self):
        image = FIXTURES/'walk2-window-qa-frame-1210.png'
        namespace = dict(__name__='frozen_render_qa')
        exec(compile(self.before['source']['src/archpipe/render_qa.py'],'frozen_render_qa','exec'),namespace)
        old = namespace['check'](image,self.context())
        self.assertIn('FAIL',self.statuses(old,'window_brightness'))
        actual = render_qa.check(image,self.corrected_context())
        self.assertEqual(self.statuses(actual,'window_brightness'),['PASS'])
        self.assertEqual(self.statuses(actual,'window_view'),['PASS'])
        sibling = self.corrected_context();sibling['windows'][0]['id']='another-villa-rotated-pane'
        self.assertEqual(render_qa.check(image,sibling)['passed'],actual['passed'])

    def test_real_glass_pixel_mutations_still_fire_for_dim_and_blank_windows(self):
        owned = unpack_pixels(self.pixels,480,270)
        with tempfile.TemporaryDirectory() as directory:
            for name,value,check in (('dim',(20,20,20),'window_brightness'),
                                     ('blank',(255,255,255),'window_view')):
                image = Image.open(FIXTURES/'walk2-window-qa-frame-1210.png').convert('RGB')
                for x,y in owned:image.putpixel((x,y),value)
                file=Path(directory)/(name+'.png');image.save(file)
                self.assertIn('FAIL',self.statuses(render_qa.check(file,self.corrected_context()),check))

    def test_runs_roundtrip_and_refuse_invalid_or_stale_native_grid(self):
        points={(0,0),(2,0),(6,0),(2,2)}
        packed=pack_pixels(points,8,4)
        self.assertEqual(unpack_pixels(packed,8,4),points)
        for mutated in (dict(packed,size=[10,4]),dict(packed,basis='rectangle'),
                        dict(packed,runs=[[0,0,4],[0,2,4]]),dict(packed,runs=[[1,0,4]])):
            with self.assertRaises(ValueError):unpack_pixels(mutated,8,4)
        with self.assertRaises(ValueError):pack_pixels([(1,0)],8,4)
        with self.assertRaisesRegex(ValueError,'nonempty'):pack_pixels([],8,4)
        with self.assertRaisesRegex(ValueError,'nonempty'):unpack_pixels(dict(packed,runs=[]),8,4)
        qa=self.corrected_context();qa['windows'][0]['visible_pixels']['runs']=[]
        # An invalid small declared rectangle must not hide corrupt ownership.
        qa['windows'][0]['screen']=[0,0,.01,.01]
        with self.assertRaisesRegex(ValueError,'nonempty'):
            render_qa.check(FIXTURES/'walk2-window-qa-frame-1210.png',qa)

if __name__=='__main__':unittest.main()
