"""A worker must never reuse failed, changed, missing or escaping artifacts."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from archpipe.worker import artifacts_valid, cached_job, identity


class WorkerTests(unittest.TestCase):
    def test_cache_checks_actual_output_and_dependency_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls=[]
            def action(folder):
                calls.append(folder)
                (folder/'value.txt').write_text('verified')
                return {'value':42}
            first=cached_job(tmp,{'asset':'one','runtime':'one'},action)
            self.assertTrue(first['passed'])
            self.assertTrue(cached_job(tmp,first['manifest'],action)['reused'])
            (Path(first['attempt'])/'value.txt').write_text('tampered')
            self.assertFalse(cached_job(tmp,first['manifest'],action)['reused'])
            self.assertFalse(cached_job(tmp,{'asset':'two','runtime':'one'},action)['reused'])
            self.assertFalse(cached_job(tmp,{'asset':'two','runtime':'two'},action)['reused'])
            self.assertEqual(len(calls),4)

    def test_failed_attempt_is_preserved_and_never_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            def failing(folder):
                (folder/'failure.log').write_text('diagnostic')
                raise ValueError('deliberate failure')
            first=cached_job(tmp,{'input':1},failing)
            second=cached_job(tmp,{'input':1},failing)
            self.assertFalse(second['passed'])
            self.assertFalse(second['reused'])
            self.assertNotEqual(first['attempt'],second['attempt'])
            self.assertTrue((Path(first['attempt'])/'failure.log').is_file())

    def test_artifact_paths_cannot_escape_job_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(artifacts_valid(tmp,{'../outside.txt':'bad'}))
            self.assertFalse(artifacts_valid(tmp,{}))
            with self.assertRaises(ValueError):
                identity({'invalid':float('nan')})


if __name__=='__main__':
    unittest.main()
