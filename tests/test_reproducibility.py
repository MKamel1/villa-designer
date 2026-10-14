"""Frozen real runtime inputs, process isolation, precision and receipt guards."""
import ast
from copy import deepcopy
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from archpipe.scene_reproducibility import stable_seed, signed_volume, require_outward, compare_receipts, randomness_findings, repository_randomness_findings

ROOT = Path(__file__).resolve().parents[1]


def parts():
    return json.loads(gzip.decompress((ROOT/'tests/fixtures/garment-importer-precision-before.json.gz').read_bytes()))['parts']


class Reproducibility(unittest.TestCase):
    def test_real_and_renamed_curtains_in_separate_hash_seed_processes(self):
        specs = json.loads((ROOT/'tests/fixtures/curtain-repro-before.json').read_text())['curtains']
        renamed = deepcopy(specs)
        for row in renamed:
            row['id'] = 'other-'+row['id']
            row['center'] = [v+100 for v in row['center']]
        script = ('import json,sys,random; from archpipe.scene_reproducibility import stable_seed; '
                  'print(json.dumps([[stable_seed(s), random.Random(stable_seed(s)).random()] '
                  'for s in json.load(sys.stdin)]))')
        outputs = []
        for seed in ('0', '987654'):
            result = subprocess.run([sys.executable, '-c', script], input=json.dumps(specs+renamed),
                                    env=dict(os.environ, PYTHONHASHSEED=seed), text=True, capture_output=True, check=True)
            outputs.append(result.stdout)
        self.assertEqual(*outputs)
        self.assertEqual(stable_seed(specs[0]), stable_seed(dict(reversed(list(specs[0].items())))))
        changed = deepcopy(specs[0]); changed['width'] += .01
        self.assertNotEqual(stable_seed(specs[0]), stable_seed(changed))
        with self.assertRaises(ValueError): stable_seed({'width':float('nan')})

    def test_real_solids_translated_siblings_and_inverted_refusal(self):
        for part in parts():
            baseline = signed_volume(part['faces'])
            self.assertGreater(baseline, 0)
            from archpipe.concept.physical_part import geometry_errors
            self.assertEqual(geometry_errors(part['faces']), [])
            self.assertEqual(require_outward(part['faces'], part['id']), baseline)
            sibling = [[[p[0]+1e6,p[1]-2e6,p[2]+3e6] for p in f] for f in part['faces']]
            self.assertAlmostEqual(signed_volume(sibling)/baseline,1,places=6)
            require_outward(sibling, 'renamed-distant-solid')
            self.assertEqual(geometry_errors(sibling), [])
            for faces in (part['faces'], sibling):
                self.assertIn('inward-facing solid', geometry_errors([list(reversed(f)) for f in faces]))
                with self.assertRaisesRegex(ValueError,'inward'):
                    require_outward([list(reversed(f)) for f in faces], 'genuinely-inverted')
        with self.assertRaisesRegex(ValueError,'zero'):
            require_outward([[[0,0,0],[1,0,0],[0,1,0]]], 'flat')

    def test_receipt_detects_runtime_mesh_drift_and_missing_binding(self):
        receipt = dict(schema='evaluated-scene/1', authored_scene_sha256='a',
                       evaluated_meshes_sha256='b', curtains={'renamed-panel':dict(mesh_sha256='c')})
        self.assertEqual(compare_receipts(receipt, deepcopy(receipt)), [])
        changed = deepcopy(receipt); changed['curtains']['renamed-panel']['mesh_sha256'] = 'd'
        self.assertTrue(compare_receipts(receipt, changed))
        changed = deepcopy(receipt); del changed['curtains']
        self.assertTrue(compare_receipts(receipt, changed))
        changed = deepcopy(receipt); changed['evaluated_meshes_sha256'] = 'e'
        self.assertTrue(compare_receipts(receipt, changed))

    def test_randomness_audit_real_old_seed_aliases_and_clean_sources(self):
        old = 'import random\nrnd = random.Random(abs(hash(spec["id"])) % (2 ** 31))'
        self.assertTrue(randomness_findings(old))
        for source in ('import random as r; rng=r.Random()',
                       'from random import Random as R; rng=R(None)',
                       'from numpy.random import default_rng as rng; x=rng()',
                       'import numpy as np; x=np.random.uniform()'):
            self.assertTrue(randomness_findings(source), source)
        self.assertEqual(randomness_findings('import random as r; rng=r.Random(11); x=rng.uniform(0,1)'), [])
        self.assertEqual(repository_randomness_findings(ROOT), [])

    def test_production_uses_construction_controls(self):
        tree = ast.parse((ROOT/'src/archpipe/blender/villa_scene.py').read_text())
        funcs = {n.name: n for n in tree.body if isinstance(n,ast.FunctionDef)}
        self.assertIn('stable_seed(spec)', ast.unparse(funcs['build_curtains']))
        importer = ast.unparse(funcs['add_mesh_batch'])
        self.assertIn("require_outward(spec['faces'], spec['id'])", importer)
        self.assertNotIn('reverse_faces', importer)
        self.assertIn('evaluated_scene_receipt', ast.unparse(funcs['render']))
        self.assertIn('scene_receipt', ast.unparse(funcs['measure_lighting']))


class NumericalReplay(unittest.TestCase):
    def test_real_receipt_task_keys_and_declared_allowance(self):
        sys.path.insert(0,str(ROOT/'scripts'))
        from prove_reproducibility import compare_measurements
        rows=json.loads((ROOT/'tests/fixtures/repro-task-readings-before.json').read_text())
        receipt=dict(schema='evaluated-scene/1',authored_scene_sha256='a',evaluated_meshes_sha256='b',curtains={})
        first=dict(points=rows,scene_receipt=receipt,all_targets_met=True)
        self.assertTrue(compare_measurements(first,deepcopy(first))['passed'])
        changed=deepcopy(first);changed['points'][0]['total_lux']*=1.00101
        self.assertFalse(compare_measurements(first,changed)['passed'])
        changed=deepcopy(first);changed['points'][0]['total_lux']*=1.00099
        self.assertTrue(compare_measurements(first,changed)['passed'])
        changed=deepcopy(first);changed['points'][0]['position'][0]+=.001
        self.assertFalse(compare_measurements(first,changed)['passed'])
        for row in first['points']:
            row['room']='renamed-'+row['room'];row['label']='renamed-'+row['label']
        self.assertTrue(compare_measurements(first,deepcopy(first))['passed'])

    def test_optical_preflight_real_references_missing_sibling_and_clean(self):
        import tempfile
        sys.path.insert(0,str(ROOT/'scripts'))
        from prove_reproducibility import optical_file_hashes
        scene=dict(lights=[dict(type='ies',ies='iguzzini/LSEVO-AAK3EW.ies')])
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            with self.assertRaises(FileNotFoundError): optical_file_hashes(scene,folder)
            # Clean file is a frozen text specimen, not a dependency on shared output.
            (folder/'iguzzini').mkdir()
            (folder/'iguzzini/LSEVO-AAK3EW.ies').write_bytes(b'IESNA:LM-63-2002\nTILT=NONE\n')
            self.assertEqual(len(optical_file_hashes(scene,folder)),1)
            scene['lights'][0]['ies']='renamed/missing.ies'
            with self.assertRaises(FileNotFoundError): optical_file_hashes(scene,folder)
            scene['lights'][0]['ies']='../escaping.ies'
            with self.assertRaises(FileNotFoundError): optical_file_hashes(scene,folder)

    def test_render_job_identity_changes_with_shared_runtime_helper(self):
        import tempfile
        from unittest.mock import patch
        sys.path.insert(0,str(ROOT/'scripts'))
        import villa_render
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'scene.json'
            path.write_text(json.dumps(dict(provenance=dict(source_hash='frozen'),
                                           views=[dict(id='test-view')],lights=[])))
            def job():
                return villa_render.run(path,'test-view',256,None,'unused',Path(temp),
                                        dry_run=True)['job_id']
            with patch.object(villa_render,'project_context',return_value={}), \
                 patch.object(villa_render,'source_provenance',return_value=dict(source_hash='frozen')), \
                 patch.object(villa_render,'validate_scene',return_value=[]):
                baseline=job()
                self.assertEqual(job(),baseline)
                original=Path.read_bytes
                def changed(candidate):
                    raw=original(candidate)
                    return raw+b'\n# changed seed/volume implementation\n' if candidate.name=='scene_reproducibility.py' else raw
                with patch.object(Path,'read_bytes',changed):
                    self.assertNotEqual(job(),baseline)
