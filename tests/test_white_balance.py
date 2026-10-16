"""Measured colour-path regressions; no Blender/GPU needed for portable tests."""
import ast
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from archpipe.render_qa import grey_card_check, grey_card_neutrality
from archpipe.material_basis import kelvin_to_rgb
from PIL import Image
import tempfile
import runpy
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
FROZEN = json.loads((ROOT / 'tests/fixtures/white-balance-real.json').read_text())


def production_white_balance(view):
    path = ROOT / 'src/archpipe/blender/photoreal.py'
    function = next(n for n in ast.parse(path.read_text()).body
                    if isinstance(n, ast.FunctionDef) and n.name == 'white_balance')
    namespace = {'bpy': SimpleNamespace(context=SimpleNamespace(scene=SimpleNamespace(view_settings=view)))}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace['white_balance']


class WhiteBalanceTest(unittest.TestCase):
    def test_real_2700_and_3000_sibling_fail_clean_controls_pass(self):
        for row in FROZEN['before']:
            result = grey_card_neutrality(row['display_mean'])
            self.assertAlmostEqual(result['cast'], row['cast'], places=12)
            self.assertEqual(result['ratios'], row['ratios'])
            self.assertEqual(result['passed'], row['temperature'] == 5500)
        self.assertEqual(FROZEN['before'][0]['source_rgb'],
                         [1.91421975706025, 0.8099360017988354, 0.19072924047733553])
        self.assertEqual(FROZEN['before'][0]['ratios'][1], 1.12)

    def test_corrected_complete_set_and_renamed_temperature_mutation(self):
        for row in FROZEN['after']:
            self.assertTrue(grey_card_neutrality(row['display_mean'])['passed'])
        # No view id, temperature or caption is used to waive an actual cast.
        sibling = deepcopy(FROZEN['after'][3])
        sibling.update(temperature=3200, kind='arbitrary-lamp-in-another-project')
        sibling['display_mean'][2] *= 1.2
        self.assertFalse(grey_card_neutrality(sibling['display_mean'])['passed'])
        self.assertEqual(FROZEN['before'][-1]['display_mean'], FROZEN['after'][-1]['display_mean'])

    def test_source_approximation_matches_independent_cie_reference(self):
        # CIE 018:2019 Table 6, full 1 nm observer integrated against Planck's
        # law independently; reference.py and the checksum-bound table are retained.
        for row in FROZEN['reference']:
            rgb = kelvin_to_rgb(row['temperature'])
            xyz = [sum(a*b for a, b in zip(m, rgb)) for m in
                   ((.4124, .3576, .1805), (.2126, .7152, .0722), (.0193, .1192, .9505))]
            xy = [v/sum(xyz) for v in xyz[:2]]
            for actual, expected in zip(xy, row['cie_xy']):
                self.assertLess(abs(actual-expected), .002)
            self.assertAlmostEqual(sum(a*b for a,b in zip(rgb,(.2126,.7152,.0722))),1,places=12)

    def test_production_camera_uses_planckian_zero_and_explicit_daylight(self):
        view = SimpleNamespace(white_balance_temperature=6500, white_balance_tint=10)
        apply = production_white_balance(view)
        for temperature in (2700, 3000, 4300, 5500, 3200):
            self.assertTrue(apply(temperature))
            self.assertEqual(view.white_balance_temperature, temperature)
            self.assertEqual(view.white_balance_tint, 0)
            self.assertTrue(view.use_white_balance)
        self.assertTrue(apply(5500, illuminant='daylight'))
        self.assertEqual(view.white_balance_tint, 10)
        with self.assertRaises(ValueError):
            apply(3000, illuminant='unknown')
        self.assertFalse(production_white_balance(SimpleNamespace())(3000))

    def test_all_render_callers_name_the_source_locus(self):
        paths = list((ROOT / 'scripts').glob('*.py')) + list((ROOT / 'src/archpipe/blender').glob('*.py'))
        calls = []
        for path in paths:
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'white_balance':
                    calls.append((path, node))
                    self.assertIn('illuminant', [k.arg for k in node.keywords], str(path))
        self.assertGreaterEqual(len(calls), 4)
        # Freeze the historical diagnostic's daylight model: changing a shared
        # default must not redevelop its archived daylight images as blackbodies.
        historical = next(n for p, n in calls if p.name == 'darkviews_drafts.py')
        self.assertEqual(next(k.value.value for k in historical.keywords if k.arg == 'illuminant'), 'daylight')

    def test_caption_preserves_measured_whitepoint_model(self):
        frozen = FROZEN['caption_before']
        self.assertFalse(frozen['white_balance_tint_present'])
        self.assertFalse(frozen['white_balance_illuminant_present'])
        path = ROOT / 'scripts/villa_render.py'
        function = next(n for n in ast.parse(path.read_text()).body
                        if isinstance(n, ast.FunctionDef) and n.name == 'villa_caption')
        namespace = {}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), namespace)
        scene = dict(lights=[], meshes=[], notes=[], exposure={'day': frozen['exposure']})
        for name, kelvin, tint, illuminant in ((frozen['view'], 2739, 0, 'planckian'),
                                              ('another-evening-room', 3000, 0, 'planckian'),
                                              ('another-daylit-room', 5500, 10, 'daylight')):
            report = dict(view=name, warnings=[], white_balance_k=kelvin,
                          white_balance_tint=tint, white_balance_illuminant=illuminant)
            caption = namespace['villa_caption'](scene, dict(id=name, exposure='day', layers_on=[]), report, {'checks': []})
            self.assertEqual(caption['white_balance_k'], kelvin)
            self.assertEqual(caption['white_balance_tint'], tint)
            self.assertEqual(caption['white_balance_illuminant'], illuminant)

    def test_png_guard_replays_real_values_and_refuses_unmeasurable_card(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'card.png'
            for row in (FROZEN['before'][0], FROZEN['before'][1], FROZEN['after'][0]):
                Image.new('RGB', (32, 32), tuple(round(c*255) for c in row['display_mean'])).save(path)
                result = grey_card_check(path)
                self.assertEqual(result['passed'], row['passed'])
                self.assertEqual(result['midtone_count'], 1024)
            Image.new('RGB', (32, 32), (0, 0, 0)).save(path)
            with self.assertRaisesRegex(ValueError, 'no display midtones'):
                grey_card_check(path)
        for invalid in ([0, 0, 0], [.4, float('nan'), .4], [.4, .4], [1, 1, 1]):
            with self.assertRaises(ValueError):
                grey_card_neutrality(invalid)

    def test_command_preflight_record_and_complete_guard(self):
        # The command targets Linux; isolate its platform lock along with the
        # mocked renderer so this orchestration regression remains portable.
        with patch.dict(sys.modules, {'fcntl': SimpleNamespace(LOCK_EX=2, flock=lambda *args: None)}):
            main = runpy.run_path(str(ROOT / 'scripts/check_white_balance.py'))['main']
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary)
            rows = deepcopy(FROZEN['after'])
            for row in rows:
                Image.new('RGB', (32, 32), tuple(round(c*255) for c in row['display_mean'])).save(out / row['png'])
            (out / 'readings.json').write_text(json.dumps(rows))
            lock_path = out / 'lock'
            lock_path.touch()
            original_open = Path.open

            def open_path(path, *args, **kwargs):
                if path == Path('/home/omar/archpipe/locks/graphics.lock'):
                    path = lock_path
                return original_open(path, *args, **kwargs)

            with patch.object(sys, 'argv', ['check_white_balance.py', '--out', str(out)]), \
                    patch.dict(main.__globals__, project_context=lambda *a, **k: {'schema': 'test-context'}), \
                    patch('subprocess.run', return_value=SimpleNamespace(returncode=0)), \
                    patch.object(Path, 'open', open_path):
                self.assertEqual(main(), 0)
            self.assertEqual(json.loads((out / 'execution-context.json').read_text()), {'schema': 'test-context'})
            self.assertTrue(json.loads((out / 'guard.json').read_text())['passed'])
            # Same entry point fails closed on the real pre-correction values.
            row = FROZEN['before'][0]
            Image.new('RGB', (32, 32), tuple(round(c*255) for c in row['display_mean'])).save(out / row['png'])
            with patch.object(sys, 'argv', ['check_white_balance.py', '--analyse-only', '--out', str(out)]):
                self.assertEqual(main(), 1)


if __name__ == '__main__':
    unittest.main()
