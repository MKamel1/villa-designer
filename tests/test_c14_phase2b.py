"""Batch B command proof; mocked native toolchains are not runtime evidence.

Blender replay uses frozen real bedroom geometry and photometry. A missing
Blender skips only the live replay, with an explicit unittest reason.
"""
import ast
from contextlib import ExitStack, redirect_stdout, redirect_stderr
import importlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/c14b'
sys.path.insert(0, str(ROOT / 'src'))
from archpipe import stage_result as SR
from archpipe.worker import cached_job, identity, sha_file


def module(name):
    with patch.object(sys, 'path', [str(ROOT / 'scripts'), str(ROOT / 'revit')] + sys.path):
        return importlib.import_module(name)


def invoke(test, action, failed=False):
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        if failed:
            with test.assertRaises(SystemExit) as exc:
                action()
            test.assertNotEqual(exc.exception.code, 0)
        else:
            test.assertEqual(action(), 0)


class CommandProofTests(unittest.TestCase):
    def assert_record(self, path, passed):
        rec = json.loads(path.read_text())
        self.assertEqual(rec['status'], 'ok' if passed else 'fail')
        self.assertEqual(rec['exit_code'] == 0, passed)
        self.assertTrue(rec['code_provenance']['source_hash'])
        for item in list(rec['inputs'].values()) + list(rec['outputs'].values()):
            if item['exists']:
                self.assertEqual(item['sha256'], sha_file(item['path']))
        if passed:
            self.assertTrue(SR.validate_stage_result(path)[0])
        return rec

    def test_thermal_validation_clean_and_failed_and_climate(self):
        m = module('thermal_job')
        for kind, passed in [('validate', True), ('validate', False), ('climate', True)]:
            with self.subTest(kind=kind, passed=passed), tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
                root = Path(tmp); inp=root/'job.json'; epw=root/'weather.epw'; tool=root/'energyplus'
                inp.write_text(json.dumps({'kind': kind})); epw.write_text('weather'); tool.write_text('binary witness')
                (root/'empty-diagnostic.log').write_bytes(b'')
                stack.enter_context(patch.object(m, 'project_context', return_value={}))
                stack.enter_context(patch.object(m, 'validate', return_value={'passed': passed, 'checks': []}))
                stack.enter_context(patch.object(m.t, 'climate_summary', return_value={'monthly': {}}))
                invoke(self, lambda: m.main(['--input', str(inp), '--epw', str(epw), '--energyplus', str(tool), '--out', str(root)]), not passed)
                rec=self.assert_record(root/'thermal-job.stage-result.json', passed)
                self.assertIn(str(tool), rec['metadata']['tool_hashes'])
                self.assertTrue((root/'thermal-results.json').is_file())

    def test_l0287_thermal_result_survives_stdout_failure(self):
        m=module('thermal_job')
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            root=Path(tmp); inp=root/'job.json'; epw=root/'weather.epw'
            inp.write_text('{"kind":"climate"}'); epw.write_text('weather')
            stack.enter_context(patch.object(m, 'project_context', return_value={}))
            stack.enter_context(patch.object(m.t, 'climate_summary', return_value={'monthly': {}}))
            stack.enter_context(patch('builtins.print', side_effect=BrokenPipeError('closed consumer')))
            with self.assertRaises(BrokenPipeError):
                m.main(['--input',str(inp),'--epw',str(epw),'--energyplus',str(root/'absent'),'--out',str(root)])
            self.assertTrue((root/'thermal-results.json').is_file())
            self.assert_record(root/'thermal-job.stage-result.json', True)

    def test_daylight_fetch_clean_failed_and_pending(self):
        m=module('villa_daylight_finished')
        for code in (0, 1, 2):
            with self.subTest(code=code), tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
                local=Path(tmp)/'job'; local.mkdir(); (local/'expectation.json').write_text('{"expected":1}')
                def fetch():
                    if code != 2:
                        (local/'report.json').write_text(json.dumps({'validation': {'all_pass':code==0}}))
                    return code
                stack.enter_context(patch.object(m,'LOCAL',local))
                stack.enter_context(patch.object(m,'project_context',return_value={}))
                stack.enter_context(patch.object(m,'fetch',side_effect=fetch))
                invoke(self, lambda: m.main(['fetch']), code!=0)
                self.assert_record(local/'daylight-fetch.stage-result.json', code==0)

    def test_daylight_run_hashes_bundle(self):
        m=module('villa_daylight_finished')
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            local=Path(tmp)/'job'
            def run():
                local.mkdir(); local.with_suffix('.tar.gz').write_bytes(b'job bundle')
                (local/'expectation.json').write_text('{}'); return 0
            stack.enter_context(patch.object(m,'LOCAL',local))
            stack.enter_context(patch.object(m,'project_context',return_value={}))
            stack.enter_context(patch.object(m,'run',side_effect=run))
            invoke(self,lambda:m.main(['run']))
            rec=self.assert_record(local/'daylight-run.stage-result.json',True)
            self.assertIn(str(local.with_suffix('.tar.gz')), [v['path'] for v in rec['outputs'].values()])

    def test_workstation_failed_worker_json_is_retained(self):
        m=module('workstation')
        for passed in (True, False):
            with self.subTest(passed=passed), tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
                root=Path(tmp); report={'passed':passed,'runtime':{'blender_version':'frozen-version'}}
                stack.enter_context(patch.object(m,'ROOT',root))
                stack.enter_context(patch.object(m,'deploy',return_value=('/remote','/release','release-id')))
                stack.enter_context(patch.object(m,'_ssh',return_value=subprocess.CompletedProcess([],0 if passed else 1,json.dumps(report).encode(),b'')))
                stack.enter_context(patch.object(sys,'argv',['workstation.py','status']))
                invoke(self,m.main,not passed)
                self.assert_record(root/'out/workstation/status.stage-result.json',passed)
                self.assertEqual(json.loads((root/'out/workstation/status-latest.json').read_text())['passed'],passed)

    def test_worker_batch_verdict_and_pre_archive_checkpoint(self):
        m=module('worker_entry')
        from archpipe import worker
        for passed, broken_archive in ((True,False),(False,False),(True,True)):
            with self.subTest(passed=passed,broken_archive=broken_archive), tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
                home=Path(tmp); root=home/'worker'; release=root/'releases/r'; release.mkdir(parents=True)
                radiance=root/'radiance'; (radiance/'bin').mkdir(parents=True); (radiance/'lib').mkdir()
                blender=root/'blender'; blender.write_bytes(b'blender binary')
                requirements=release/'requirements-worker.txt'; requirements.write_text('locked')
                environment=root/'installed.json'; environment.write_text(json.dumps({'requirements_sha256':sha_file(requirements)}))
                config={'python':os.path.abspath(sys.executable),'environment':str(environment),'blender':str(blender),'radiance':str(radiance)}
                (root/'worker-environment.json').write_text(json.dumps(config))
                (release/'release.json').write_text(json.dumps({'files':{'requirements-worker.txt':sha_file(requirements)}}))
                inp=root/'model.json'; inp.write_text('{"lighting":[]}')
                def cached(root, manifest, action):
                    attempt=Path(root)/'jobs'/identity(manifest)/'attempts/one'; attempt.mkdir(parents=True)
                    (attempt/'render.png').write_bytes(b'expensive completed image')
                    (attempt/'empty-diagnostic.log').write_bytes(b'')
                    return {'job_id':identity(manifest),'passed':passed,'reused':False,'manifest':manifest,'attempt':str(attempt)}
                stack.enter_context(patch.object(Path,'home',return_value=home))
                stack.enter_context(patch.object(m.subprocess,'check_output',return_value='runtime-version'))
                stack.enter_context(patch.object(worker,'cached_job',side_effect=cached))
                stack.enter_context(patch.object(sys,'argv',['worker','batch','--root',str(root),'--release',str(release),'--input',str(inp),'--views','bed']))
                if broken_archive:
                    stack.enter_context(patch.object(m.tarfile,'open',side_effect=OSError('archive failed')))
                    with self.assertRaises(OSError), redirect_stdout(io.StringIO()):
                        m.main()
                else:
                    invoke(self,m.main,not passed)
                records=list((root/'batches').glob('*/worker.stage-result.json'))
                self.assertEqual(len(records),1)
                rec=self.assert_record(records[0],passed)
                self.assertEqual(rec['metadata']['runtime']['blender_version'],'runtime-version')
                self.assertTrue(list((root/'jobs').glob('*/attempts/one/render.png')))

    def test_hyperreal_qa_failure_and_explicit_override(self):
        m=module('render_hyperreal')
        for passed, override in ((True,False),(False,False),(False,True)):
            with self.subTest(passed=passed,override=override), tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
                root=Path(tmp); (root/'spec').mkdir(); (root/'spec/villa-site.yaml').write_text('site: frozen')
                inp=root/'model.json'; inp.write_text('{"lighting": [{"id":"lamp","ies_file":"deployed.ies"}]}')
                def ssh(host, cmd, **kw):
                    if 'worker-environment.json' in cmd: data=b'{"blender":"/blender"}'
                    elif '--version' in cmd: data=b'Blender 4.5.14 LTS\n'
                    elif '-P ' in cmd: data=b'SCENE wrote render.png\n'
                    elif '/assets/ies/' in cmd: data=b'actual deployed IES bytes'
                    elif cmd.startswith('cat '): data=b'image bytes'
                    else: data=b''
                    return subprocess.CompletedProcess([],0,data,b'')
                def caption(out,*args,**kw): out.with_suffix('.caption.json').write_text('{}')
                stack.enter_context(patch.object(m,'ROOT',root))
                stack.enter_context(patch.object(m,'site',return_value=(30,31,2)))
                stack.enter_context(patch.object(m,'_site_note',return_value={}))
                stack.enter_context(patch.object(m,'deploy',return_value=('/remote','/release','id')))
                stack.enter_context(patch.object(m,'_ssh',side_effect=ssh))
                stack.enter_context(patch.object(m,'write_caption',side_effect=caption))
                stack.enter_context(patch.object(m.render_qa,'check',return_value={'passed':passed,'checks':[],'failed':[] if passed else ['photometry_bound']}))
                stack.enter_context(patch.object(m.render_qa,'scene_qa_from_log',return_value={}))
                stack.enter_context(patch.object(sys,'argv',['hyperreal','--input',str(inp),'--views','door']+(['--allow-qa-fail'] if override else [])))
                invoke(self,m.main,not passed and not override)
                rec=self.assert_record(root/'out/photoreal/render-hyperreal.stage-result.json',passed or override)
                self.assertEqual(rec['metadata']['renderer_version'],'Blender 4.5.14 LTS')
                self.assertEqual(rec['metadata']['qa_override'],override)
                remote_ies=[v for v in rec['inputs'].values() if v['path'].endswith('deployed.ies')]
                self.assertEqual(len(remote_ies),1)
                self.assertEqual(Path(remote_ies[0]['path']).read_bytes(),b'actual deployed IES bytes')

    def test_bedroom_early_failure_and_full_resume(self):
        m=module('run_bedroom')
        for resume in (False,True):
            with self.subTest(resume=resume), tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
                root=Path(tmp); out=root/'out'; out.mkdir(); source=root/'source.py'; source.write_text('frozen')
                runtime={'blender_version':'Blender 4.5.14 LTS'}
                fingerprint=__import__('hashlib').sha256(json.dumps(runtime,sort_keys=True).encode()).hexdigest()
                inputs={'source.py':sha_file(source)}
                previous={'passed':True,'input_hashes':inputs,'samples':512,'worker_runtime':fingerprint,'artifacts':{'image.png':{'sha256':identity('image')}}}
                (out/'image.png').write_bytes(b'image')
                previous['artifacts']['image.png']['sha256']=sha_file(out/'image.png')
                (out/'bedroom-acceptance.json').write_text(json.dumps(previous))
                def run(*args,**kw):
                    (out/'workstation').mkdir(exist_ok=True)
                    (out/'workstation/status-latest.json').write_text(json.dumps({'runtime':runtime}))
                stack.enter_context(patch.object(m,'ROOT',root))
                stack.enter_context(patch.object(m,'project_context',return_value={}))
                stack.enter_context(patch.object(m,'input_hashes',return_value=inputs))
                stack.enter_context(patch.object(m,'run',side_effect=run if resume else RuntimeError('status failed')))
                stack.enter_context(patch.object(sys,'argv',['bedroom','--skip-revit']+(['--resume'] if resume else [])))
                invoke(self,m.main,not resume)
                rec=self.assert_record(out/'bedroom.stage-result.json',resume)
                self.assertEqual(rec['metadata']['reused'],resume)


class NativeContractTests(unittest.TestCase):
    def test_native_files_and_shared_writer_reject_python3_only_syntax(self):
        # Portable syntax screen only; no Revit or IronPython execution is claimed.
        def check_syntax(source):
            tree = ast.parse(source)
            forbidden = (ast.JoinedStr, ast.AnnAssign, ast.NamedExpr, ast.AsyncFunctionDef, ast.Await, ast.Nonlocal)
            for node in ast.walk(tree):
                self.assertNotIsInstance(node, forbidden)
                if isinstance(node, ast.FunctionDef):
                    self.assertFalse(node.args.kwonlyargs)
                    self.assertIsNone(node.returns)
                    self.assertTrue(all(arg.annotation is None for arg in node.args.args))
                if isinstance(node, ast.Raise):
                    self.assertIsNone(node.cause)
            return tree
        files=['build_bedroom.py','extract_model.py','export_views.py','build_villa_option.py','build_villa_env.py','build_villa_stairs.py','stage_command.py']
        for name in files:
            with self.subTest(name=name):
                source=(ROOT/'revit'/name).read_text(encoding='utf-8-sig')
                tree=check_syntax(source)
                guard=[n for n in tree.body if isinstance(n,ast.If) and '__name__' in ast.unparse(n.test)]
                if name != 'stage_command.py':
                    self.assertTrue(guard)
                    self.assertIn('run_stage', ast.unparse(guard[-1]))
        check_syntax((ROOT/'src/archpipe/stage_result.py').read_text())

    def test_native_wrapper_failure_clean_and_in_place_input(self):
        m=module('stage_command')
        for passed in (True,False):
            with self.subTest(passed=passed),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp); model=root/'model.rvt'; model.write_bytes(b'original model')
                original=sha_file(model); report=root/'report.json'
                def action():
                    model.write_bytes(b'saved model'); report.write_text('{}')
                app=type('App',(),{'VersionNumber':'2027','VersionBuild':'frozen-build'})()
                invoke(self,lambda:m.run('native-test',action,str(root/'stage.json'),[str(model)],lambda value:[str(model),str(report)],lambda value:not passed,app),not passed)
                rec=json.loads((root/'stage.json').read_text())
                self.assertEqual(rec['status'],'ok' if passed else 'fail')
                self.assertEqual(next(iter(rec['inputs'].values()))['sha256'],original)
                self.assertEqual(rec['outputs'][str(model)]['sha256'],sha_file(model))
                self.assertEqual(rec['metadata']['runtime']['revit_version'],'2027')
                if passed:
                    self.assertTrue(SR.validate_stage_result(rec)[0])

    def test_native_exception_preserves_model_and_writes_failed_record(self):
        m=module('stage_command')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); dest=root/'saved.rvt'
            def action():
                dest.write_bytes(b'expensive saved model'); raise ValueError('serialization failed')
            app=type('App',(),{'VersionNumber':'2027','VersionBuild':'frozen-build'})()
            invoke(self,lambda:m.run('native-test',action,str(root/'stage.json'),[],lambda value:[str(dest)],lambda value:False,app),True)
            rec=json.loads((root/'stage.json').read_text())
            self.assertEqual(rec['status'],'fail'); self.assertTrue(dest.is_file())
            self.assertIn('serialization failed',rec['metadata']['error'])


class FingerprintTests(unittest.TestCase):
    def test_refactor_keeps_branch_start_computation_functions(self):
        import hashlib
        audit=json.loads((FIXTURE/'refactor-audit.json').read_text())
        for script, functions in audit['unchanged_functions'].items():
            tree=ast.parse((ROOT/script).read_text(encoding='utf-8-sig'))
            current={n.name:n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
            for name, digest in functions.items():
                with self.subTest(script=script,function=name):
                    self.assertEqual(hashlib.sha256(ast.dump(current[name],include_attributes=False).replace(', type_params=[]', '').encode()).hexdigest(),digest)

    def test_frozen_renderer_mutation_and_unrelated_edit(self):
        worker=module('worker_entry')
        data=json.loads((FIXTURE/'real-replay.json').read_text())
        before=data['manifest']
        clean=worker.job_manifest(before['kind'],before['parameters'],before['model'],data['runtime'],data['code'])
        self.assertEqual(identity(clean),data['job_id'])
        unrelated={**data['code'],'src/archpipe/guidance.py':'unrelated engine edit','docs/ROADMAP.md':'unrelated doc edit'}
        self.assertEqual(identity(worker.job_manifest('render',before['parameters'],before['model'],data['runtime'],unrelated)),data['job_id'])
        changed={**data['runtime'],'blender_version':data['runtime']['blender_version']+' [mutation]'}
        self.assertNotEqual(identity(worker.job_manifest('render',before['parameters'],before['model'],changed,data['code'])),data['job_id'])
        for kind in ('probe','radiance'):
            self.assertNotEqual(identity(worker.job_manifest(kind,{},before['model'],changed,data['code'])),identity(worker.job_manifest(kind,{},before['model'],data['runtime'],data['code'])))

    def test_l0068_real_five_fixture_fallback_record_fails_closed(self):
        from archpipe import render_qa
        measured=json.loads((FIXTURE/'photometry-probe.json').read_text())
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            image=Path(tmp)/'render.png'; Image.new('RGB',(128,128),(100,100,100)).save(image)
            for name, failed in (('clean',False),('missing',True)):
                qa=render_qa.check(image,{'lights':measured[name]})
                check=next(c for c in qa['checks'] if c['check']=='photometry_bound')
                self.assertEqual(check['status'],'FAIL' if failed else 'PASS')
                rec=SR.write_stage_result('photometry-proof',record_path=Path(tmp)/'stage.json',
                    inputs=[FIXTURE/'photometry-probe.json'],outputs=[image],
                    exit_code=1 if check['status']=='FAIL' else 0)
                invoke(self,lambda:SR.enforce_clean_verdict(rec),failed)

    def test_empty_optional_diagnostic_is_hashed_without_new_failure_predicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); primary=root/'report.json'; primary.write_text('{}')
            diagnostic=root/'tool-stderr.log'; diagnostic.write_bytes(b'')
            rec=SR.write_stage_result('diagnostics',record_path=root/'stage.json',outputs=[primary,diagnostic],
                expected_outputs=[primary],root=root)
            self.assertTrue(SR.validate_stage_result(rec,root=root)[0])
            diagnostic.write_text('changed diagnostic')
            with self.assertRaises(SR.IncompleteOutputError): SR.validate_stage_result(rec,root=root)
            diagnostic.write_bytes(b''); primary.write_bytes(b'')
            with self.assertRaises(SR.IncompleteOutputError): SR.validate_stage_result(rec,root=root)

    def test_in_place_revision_accepts_saved_output_and_rejects_source_and_output_mutations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); model=root/'model'; model.write_text('before')
            source=root/'spec'; source.write_text('source')
            snapshot=SR.build_file_manifest([model,source],root)
            model.write_text('saved')
            rec=SR.write_stage_result('in-place',record_path=root/'stage.json',inputs=[model,source],
                input_manifest=snapshot,outputs=[model],root=root)
            self.assertTrue(SR.validate_stage_result(rec,root=root)[0])
            self.assertEqual(rec['overwritten_inputs'],['model'])
            source.write_text('changed source')
            # A forged marker cannot turn an input-only source into an output.
            rec['overwritten_inputs'].append('spec')
            with self.assertRaises(SR.StaleInputError): SR.validate_stage_result(rec,root=root)
            source.write_text('source'); model.write_text('damaged save')
            with self.assertRaises(SR.IncompleteOutputError): SR.validate_stage_result(rec,root=root)

    def test_l0089_code_snapshot_rejects_concurrent_edit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); code=root/'builder.py'; code.write_text('version one')
            prov=SR.compute_code_provenance(root,[code])
            output=root/'output'; output.write_text('real output')
            record=SR.write_stage_result('snapshot',record_path=root/'stage.json',inputs=[],outputs=[output],root=root,code_paths=[code],code_provenance=prov)
            self.assertTrue(SR.validate_stage_result(record,root=root,check_code_provenance=True)[0])
            (root/'unrelated.py').write_text('unrelated source change')
            self.assertTrue(SR.validate_stage_result(record,root=root,check_code_provenance=True)[0])
            code.write_text('concurrent edit')
            with self.assertRaises(SR.CodeDriftError):
                SR.validate_stage_result(record,root=root,check_code_provenance=True)

    def test_text_only_worker_release_materializes_exact_frozen_ies(self):
        from scripts.reproduce_c14b import frozen_ies
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); fixture=root/'fixture'; fixture.mkdir()
            shutil.copyfile(FIXTURE/'ies-text.json',fixture/'ies-text.json')
            paths=frozen_ies(fixture,root/'photometry')
            for name,path in paths.items():
                self.assertEqual(path.read_bytes(),(FIXTURE/name).read_bytes())

    def test_live_blender_reuse(self):
        blender=os.environ.get('ARCHPIPE_BLENDER') or shutil.which('blender')
        if not blender:
            candidate=Path.home()/'opt/blender/blender'
            blender=str(candidate) if candidate.is_file() else None
        if not blender:
            self.skipTest('Blender absent; frozen fingerprint regression still runs without native renderer')
        from scripts.reproduce_c14b import replay
        with tempfile.TemporaryDirectory() as tmp:
            result=replay(Path(tmp),blender)
            self.assertEqual(result['unchanged_reused'],3)
            self.assertTrue(result['legacy_stale_reused'])
            self.assertNotEqual(result['legacy_recorded_renderer'], result['requested_renderer_mutation'])
            self.assertFalse(result['version_mutation_reused'])
            self.assertFalse(result['corrupt_output_reused'])
            self.assertTrue(all(result['passed']))
            self.assertEqual(result['photometry']['clean']['with_ies'],5)
            self.assertEqual(result['photometry']['missing']['with_ies'],0)


if __name__=='__main__':
    unittest.main()
