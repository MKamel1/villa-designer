"""Real build-cost inputs retain values, independent copies and strict admission."""
from copy import deepcopy
import gzip,json
import os,pickle,subprocess,sys,tempfile
from pathlib import Path
import unittest
from archpipe import imported_appearance as I
from archpipe.concept import physical_part as P

ROOT=Path(__file__).resolve().parents[1]


class BuildCost(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case=json.loads(gzip.decompress((ROOT/'tests/fixtures/drape-polish-pair-copy-before.json.gz').read_bytes()))
        namespace=dict(I.__dict__,deepcopy=deepcopy)
        exec((ROOT/'tests/fixtures/drape-polish-with-models-before.py').read_text(),namespace)
        cls.old=staticmethod(namespace['with_models'])

    def test_real_pair_copy_matches_frozen_selector_and_is_independent(self):
        for sibling in (False,True):
            scene=deepcopy(self.case)
            if sibling:
                model=scene['models'][0];model['id']='renamed-pair'
                model['position']=[model['position'][i]+(4,-7,3)[i] for i in range(3)]
                I.bind_scene(scene)
            model=scene['models'][0];before=I.digest(scene)
            expected=self.old(scene,[model]);actual=I.with_models(scene,[model])
            self.assertEqual(actual,expected)
            self.assertEqual(I.digest(actual),I.digest(expected))
            self.assertEqual(I.digest(scene),before)
            I.require_scene(actual)
            part=actual['physical_model_meshes'][0]
            part['faces'][0][0][0]+=.001
            part['components'][0]['source_face_indices'].append(-999)
            actual['imported_appearances'][0]['source_sha256']['mutation']='wrong'
            self.assertEqual(I.digest(scene),before)
            with self.assertRaises(ValueError):I.require_scene(actual)
            changed=deepcopy(scene);changed['physical_model_meshes'][0]['faces'][0][0][0]+=.001
            with self.assertRaises(ValueError):I.with_models(changed,[changed['models'][0]])

    def test_face_snapshot_hash_and_cached_review_match_real_uncached_arithmetic(self):
        fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/drape-boards-before.json.gz').read_bytes()))
        from archpipe.concept.build_cache import scope
        parts=fixture['parts']+self.case['physical_model_meshes']
        with scope():
            for row in parts:
                faces=row['faces'];frozen=P._freeze_faces(faces)
                self.assertEqual(frozen,tuple(tuple(tuple(p) for p in f) for f in faces))
                self.assertEqual(frozen.__hash__(),tuple.__hash__(frozen))
                self.assertEqual(P.geometry_errors(frozen),P._geometry_errors(frozen))
                with self.assertRaises(TypeError):frozen._value_hash=0
                changed=deepcopy(faces);changed[0][0][0]+=.001
                self.assertNotEqual(P._freeze_faces(changed),frozen)
                self.assertEqual(P.geometry_errors(changed),P._geometry_errors(P._freeze_faces(changed)))
                self.assertEqual(P.geometry_errors(frozen),P._geometry_errors(frozen))

    def test_actual_model_binary_value_key_matches_original_json_construction_and_mutations(self):
        model=deepcopy(self.case['models'][0]);before=I.digest(model)
        def original(value):
            raw=I.encoded(value)
            return json.loads(I._cached_pair(__import__('hashlib').sha256(raw).hexdigest(),raw))
        self.assertIsNotNone(I._binary_model_input(model))
        self.assertEqual(I.digest(I.build_model(model)),I.digest(original(model)))
        self.assertEqual(I.digest(model),before)
        # Preserve face order, unrounded coordinates, pose, arbitrary metadata,
        # and representation distinctions that the former JSON key retained.
        for mutation in ('coordinate','face-order','pose','metadata','integer','signed-zero'):
            changed=deepcopy(model)
            row=changed['review_geometry']['meshes'][0]
            if mutation=='coordinate':row['faces'][0][0][0]+=4e-8
            elif mutation=='face-order':row['faces'][0]=row['faces'][0][1:]+row['faces'][0][:1]
            elif mutation=='pose':changed['position'][0]+=4
            elif mutation=='metadata':changed['label']='renamed-sibling'
            elif mutation=='integer':row['faces'][0][0][0]=int(row['faces'][0][0][0])
            else:row['faces'][0][0][0]=-0.0
            with self.subTest(mutation=mutation):
                if mutation=='integer':self.assertIsNone(I._binary_model_input(changed))
                else:self.assertNotEqual(I._binary_model_input(changed),I._binary_model_input(model))
                self.assertEqual(I.digest(I.build_model(changed)),I.digest(original(changed)))
        a=I.build_model(model);a[1][0]['faces'][0][0][0]+=.01
        self.assertEqual(I.digest(I.build_model(model)),I.digest(original(model)))

    def test_snapshot_transport_recomputes_process_local_hash_for_numeric_string_sibling(self):
        faces=P._freeze_faces([[['0',0.,0.],[1.,0.,0.],[0.,1.,0.]]])
        self.assertEqual(deepcopy(faces),faces)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'faces.pickle';path.write_bytes(pickle.dumps(faces))
            code="import pickle,sys;from pathlib import Path;v=pickle.loads(Path(sys.argv[1]).read_bytes());assert v.__hash__()==tuple.__hash__(v)"
            for salt in ('0','987654'):
                result=subprocess.run([sys.executable,'-c',code,str(path)],cwd=ROOT,env=dict(os.environ,PYTHONHASHSEED=salt),capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
