"""Actual QA-only correction is reusable; rendering/threshold changes refuse."""
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from scripts.walk2_reuse_qa import prove_qa_only

FIXTURE=Path(__file__).parent/'fixtures/walk2-qa-reuse-source.json.gz'

class AnalysisOnlyReuse(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.root=Path(self.directory.name);self.old=self.root/'old';self.new=self.root/'new'
        value=json.loads(gzip.decompress(FIXTURE.read_bytes()))
        self.inventory={}
        for side,contents in value.items():
            directory=self.old if side=='before' else self.new
            self.inventory[side]={}
            for name,source in contents.items():
                target=directory/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(source)
                self.inventory[side][name]=hashlib.sha256(target.read_bytes()).hexdigest()

    def prove(self):
        return prove_qa_only(self.inventory['before'],self.inventory['after'],self.old,self.new)

    def mutate(self,name,old,new):
        file=self.new/name;source=file.read_text();self.assertIn(old,source)
        file.write_text(source.replace(old,new,1));self.inventory['after'][name]=hashlib.sha256(file.read_bytes()).hexdigest()

    def test_actual_postrender_qa_correction_is_quiet_and_binds_all_sources(self):
        result=self.prove();self.assertTrue(result['passed'])
        self.assertEqual(len(result['changed_sources']),4)
        self.assertEqual(result['added_sources'],['src/archpipe/window_qa.py'])

    def test_real_renderer_and_meter_mutations_fire(self):
        name='src/archpipe/blender/walkthrough.py'
        self.mutate(name,"s.cycles.seed=0;","s.cycles.seed=1;")
        with self.assertRaisesRegex(ValueError,'non-QA source'):self.prove()

    def test_prerender_identity_keyword_is_not_misclassified_as_postrender_qa(self):
        self.mutate('src/archpipe/blender/walkthrough.py',
                    'resolution=resolution,samples=samples,policy=digest(policy())',
                    "resolution=resolution,samples=samples,policy=digest(policy()),qa_scene='changed-pre-render-cache-key'")
        with self.assertRaisesRegex(ValueError,'non-QA source'):self.prove()

    def test_threshold_sibling_and_unknown_source_changes_fire(self):
        self.mutate('src/archpipe/render_qa.py','WINDOW_MAX_CLIP = 0.60','WINDOW_MAX_CLIP = 0.99')
        with self.assertRaisesRegex(ValueError,'non-QA source'):self.prove()
        self.inventory['after']['knowledge/another-villa-route.json']='changed'
        with self.assertRaisesRegex(ValueError,'addition/removal'):self.prove()

    def test_corrupt_original_source_snapshot_fires(self):
        file=self.old/'src/archpipe/render_qa.py';file.write_text(file.read_text()+'\n# corruption\n')
        with self.assertRaisesRegex(ValueError,'snapshot differs'):self.prove()

    def test_exact_postrender_room_ownership_adapter_field_only(self):
        name='scripts/villa_render.py'
        old=gzip.decompress((FIXTURE.parent/'walk2-room-adapter-before.py.gz').read_bytes())
        new=old.replace(b'"sky": {"sun": day}, "windows": measured["windows"],',
                        b'"sky": {"sun": day}, "windows": measured["windows"],\n'
                        b'            "room_glazing_pixels": measured.get("room_glazing_pixels"),')
        self.assertNotEqual(old,new)
        for side,data,directory in (('before',old,self.old),('after',new,self.new)):
            target=directory/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            self.inventory[side][name]=hashlib.sha256(data).hexdigest()
        self.assertEqual(len(self.prove()['changed_sources']),5)
        self.mutate(name,'measured.get("room_glazing_pixels")','None')
        with self.assertRaisesRegex(ValueError,'adapter ownership value differs'):self.prove()

if __name__=='__main__':unittest.main()
