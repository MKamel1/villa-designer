"""A result must fail on wrong physics, scope, or stale evidence."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import run_bedroom
from archpipe import photometry


class PipelineTests(unittest.TestCase):
    def test_worker_failure_replaces_previous_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'out').mkdir()
            report = root/'out/bedroom-acceptance.json'
            report.write_text(json.dumps({'passed':True}))
            with patch.object(run_bedroom,'ROOT',root), \
                 patch.object(run_bedroom,'input_hashes',return_value={}), \
                 patch.object(run_bedroom,'run',side_effect=RuntimeError('worker unavailable')), \
                 patch.object(sys,'argv',['run_bedroom.py','--resume']):
                self.assertEqual(run_bedroom.main(),1)
            result = json.loads(report.read_text())
            self.assertFalse(result['passed'])
            self.assertEqual(result['stage'],'worker_status')

    def test_stale_or_missing_artifacts_are_not_reused(self):
        self.assertFalse(run_bedroom.artifacts_match({}))
        self.assertFalse(run_bedroom.artifacts_match({'no-such-artifact': {'sha256':'x'}}))
        self.assertFalse(run_bedroom.artifacts_match({'bedroom-from-revit.json': {'sha256':'wrong'}}))

    def test_photometry_gate_rejects_reflected_light(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'probe.json'
            p.write_text(json.dumps({'working_plane_mm':850,'bounces':16}))
            result = subprocess.run([sys.executable, str(ROOT/'scripts/compare_lux.py'), str(p),
                '--extract', str(ROOT/'tests/fixtures/bedroom-from-revit.json')], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('reflected light', result.stdout)

    def test_photometry_gate_rejects_dark_render(self):
        if photometry.revit_ies_dir() is None:
            self.skipTest('Local photometric library is required for this comparison')
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'probe.json'
            extract = Path(tmp)/'extract.json'
            extract.write_text(json.dumps({'rooms':[{'boundary':[[0,0],[4200,0],[4200,3600],[0,3600]]}],
                'lighting':[{'id':'known_lamp','ies_file':'PLD1A21.ies','at':[2100,1800],
                             'mounting_height':2400}]}))
            p.write_text(json.dumps({'working_plane_mm':850,'bounces':0,
                'furniture_included':False,'points':[[2100,1800,0],[2100,2000,0]]}))
            result = subprocess.run([sys.executable, str(ROOT/'scripts/compare_lux.py'), str(p),
                '--extract', str(extract)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('VERDICT: FAIL', result.stdout)


if __name__ == '__main__':
    unittest.main()
