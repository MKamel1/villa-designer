"""Renderer evaluations cannot reuse production identity or bypass version checks."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import villa_render as V
from archpipe.execution_context import ContextError

class RendererVersions(unittest.TestCase):
    def test_real_missing_photometry_and_sibling_fail_before_render(self):
        from prove_reproducibility import optical_file_hashes
        scene={'lights':[{'type':'ies','ies':'generic/GARDEN-UP.ies'},{'type':'ies','ies':'generic/DESK.ies'}]}
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'generic').mkdir()
            with self.assertRaisesRegex(FileNotFoundError,'GARDEN-UP'):optical_file_hashes({'lights':scene['lights'][:1]},root)
            (root/'generic/GARDEN-UP.ies').write_text('frozen optical input')
            with self.assertRaisesRegex(FileNotFoundError,'DESK'):optical_file_hashes(scene,root)
            (root/'generic/DESK.ies').write_text('sibling optical input')
            self.assertEqual(len(optical_file_hashes(scene,root)),2)
            with self.assertRaises(FileNotFoundError):optical_file_hashes({'lights':[{'type':'ies','ies':'../escape.ies'}]},root)

    def test_gpu_receipt_refuses_cpu_fallback_and_disabled_gpu(self):
        from blender52_eval import require_gpu
        # Actual sandbox class: CPU is available, while no graphics device is.
        for device,devices in [('CPU',[dict(name='AMD Ryzen 9 9950X 16-Core Processor',type='CPU',use=True)]),
                               ('GPU',[dict(type='CPU',use=False)]),
                               ('GPU',[dict(type='OPTIX',use=False)])]:
            with self.assertRaisesRegex(RuntimeError,'refusing CPU timings'):require_gpu(device,devices)
        require_gpu('GPU',[dict(type='OPTIX',use=True),dict(type='CPU',use=False)])
        require_gpu('GPU',[dict(type='CUDA',use=True)])

    def test_selection_binds_cache_and_default_stays_pinned(self):
        with tempfile.TemporaryDirectory() as folder:
            scene=Path(folder)/'scene.json'
            scene.write_text(json.dumps(dict(provenance=dict(source_hash='frozen'),views=[dict(id='view')],lights=[])))
            with patch.object(V,'project_context',return_value={}),patch.object(V,'source_provenance',return_value=dict(source_hash='frozen')),patch.object(V,'validate_scene',return_value=[]):
                def run(**kwargs):return V.run(scene,'view',256,None,'unused',Path(folder),dry_run=True,**kwargs)
                baseline=run()
                self.assertEqual(baseline['renderer']['expected_version'],'4.5.14')
                self.assertEqual(run()['job_id'],baseline['job_id'])
                selected=run(blender='/opt/5.2/blender',expected_version='5.2.2')
                self.assertNotEqual(selected['job_id'],baseline['job_id'])
                self.assertNotEqual(selected['job_id'],run(blender='/opt/other/blender',expected_version='5.2.2')['job_id'])
                self.assertNotEqual(selected['job_id'],run(blender='/opt/5.2/blender',expected_version='5.2.3')['job_id'])
                with self.assertRaisesRegex(ValueError,'absolute'):run(blender='blender')

    def test_sky_adapter_source_changes_render_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            scene=Path(folder)/'scene.json'
            scene.write_text(json.dumps(dict(provenance=dict(source_hash='frozen'),views=[dict(id='view')],lights=[])))
            with patch.object(V,'project_context',return_value={}),patch.object(V,'source_provenance',return_value=dict(source_hash='frozen')),patch.object(V,'validate_scene',return_value=[]):
                def job():return V.run(scene,'view',256,None,'unused',Path(folder),dry_run=True)['job_id']
                baseline=job()
                self.assertEqual(job(),baseline)
                original=Path.read_bytes
                def mutation(path):
                    raw=original(path)
                    return raw+b'\n# changed sky implementation\n' if path.name=='sky_compat.py' else raw
                with patch.object(Path,'read_bytes',mutation):self.assertNotEqual(job(),baseline)

    def test_remote_evaluation_requires_exact_expected_version(self):
        record=dict(schema='execution-context/1',working_directory='/release',tools=dict(blender=dict(requested_path='/5.2/blender',version='5.2.2')),environment=dict(NO_COLOR='1'),scripts=['/release/src/archpipe/blender/villa_scene.py'])
        responses=[subprocess.CompletedProcess([],0,b'',b''),subprocess.CompletedProcess([],0,json.dumps(record).encode(),b'')]
        with patch.object(V,'_ssh',side_effect=responses) as ssh:
            self.assertEqual(V.remote_preflight('host','/release','/job','/5.2/blender','5.2.2'),record)
            self.assertIn('--tool blender /5.2/blender 5.2.2',ssh.call_args_list[0].args[1])
        for expected in ['4.5.14','5.2.3']:
            with patch.object(V,'_ssh',side_effect=responses):
                with self.assertRaisesRegex(ContextError,'mismatched'):V.remote_preflight('host','/release','/job','/5.2/blender',expected)
