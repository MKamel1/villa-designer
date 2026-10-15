"""Replay rejected real garments, shifted siblings and construction mutations."""
from copy import deepcopy
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch
import unittest
import numpy as np
from archpipe import drape_appearance as D, drape_polish as P
from archpipe.imported_appearance import digest
from archpipe.concept.physical_part import geometry_errors

ROOT=Path(__file__).resolve().parents[1]


def frozen():
    return json.loads(gzip.decompress((ROOT/'tests/fixtures/drape-polish-before.json.gz').read_bytes()))


class Polish(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case=frozen()
        cls.rows=[D.make(p) for p in cls.case['parts']]

    def test_actual_thin_profiles_and_renamed_translated_siblings_fire_clean_shapes_quiet(self):
        for p,before,after in zip(self.case['parts'],self.case['appearances'],self.rows):
            with self.subTest(part=p['id']):
                self.assertTrue(P.findings(before))
                self.assertEqual(P.findings(after),[])
                self.assertEqual(geometry_errors(after['faces']),[])
                self.assertEqual(D.enclosure_measurement(after,p)['maximum_escape_m'],0)
                sibling=deepcopy(p);sibling['id']='another-'+p['id']
                sibling['faces']=[[[q[0]+4,q[1]-7,q[2]+3] for q in f] for f in p['faces']]
                old=deepcopy(before);old['id']=sibling['id']
                old['faces']=[[[q[0]+4,q[1]-7,q[2]+3] for q in f] for f in old['faces']]
                old['skin_vertices']=[[q[0]+4,q[1]-7,q[2]+3] for q in old['skin_vertices']]
                self.assertTrue(P.findings(old))
                self.assertEqual(P.findings(D.make(sibling)),[])

    def test_real_first_fix_straight_returns_and_buried_lapels_fail_revised_construction_passes(self):
        before=json.loads(gzip.decompress((ROOT/'tests/fixtures/drape-polish-first-fix.json.gz').read_bytes()))
        before['garment_type']='jacket';before['body_front_faces']=self.rows[1]['body_front_faces']
        before['id']='frozen-first-fix'
        # Capture actual straight bridge faces as sections; two endpoints
        # cannot establish a curved shoulder. Do not synthesize a bad mesh.
        top=max(p[2] for p in before['skin_vertices'])
        before['shoulder_return_sections']=[[i] for i,f in enumerate(before['faces'])
            if len(f)==4 and min(p[2] for p in f)>top-.08 and
            max(p[0] for p in f)-min(p[0] for p in f)>.02 and
            max(p[1] for p in f)-min(p[1] for p in f)<.03]
        self.assertTrue(before['shoulder_return_sections'])
        m=P.metrics(before)
        self.assertLess(m['shoulder_return_curvature_m'],P.policy()['minimum_shoulder_return_curvature_m'])
        self.assertLess(m['tailoring_exterior_offset_m'],0)
        self.assertTrue(P.findings(before))
        shifted=deepcopy(before);shifted['id']='renamed-first-fix'
        shifted['faces']=[[[q[0]+4,q[1]-7,q[2]+3] for q in f] for f in before['faces']]
        shifted['skin_vertices']=[[q[0]+4,q[1]-7,q[2]+3] for q in before['skin_vertices']]
        self.assertTrue(P.findings(shifted))
        self.assertEqual(P.findings(self.rows[1]),[])

    def test_body_collar_placket_lapel_and_fold_mutations_fire(self):
        jacket=self.rows[1]
        thin=deepcopy(jacket)
        cx=sum(D.bounds(thin)[::3])/2
        for f in thin['faces']:
            for q in f:q[0]=cx+(q[0]-cx)*.1
        self.assertTrue(any('torso_depth' in f for f in P.findings(thin)))
        for feature,axis in (('collar_stand',2),('collar_fall',2),('placket',1),('lapel_-1',1)):
            row=deepcopy(jacket);a,b=row['tailoring_features'][feature]
            target=row['faces'][a][0][axis]
            for f in row['faces'][a:b]:
                for q in f:q[axis]=target
            self.assertTrue(any(feature.split('_')[0] in f for f in P.findings(row)),feature)
        buried=deepcopy(jacket);a,b=buried['tailoring_features']['lapel_1']
        for f in buried['faces'][a:b]:
            for q in f:q[0]-=.01
        self.assertTrue(any('exterior' in f for f in P.findings(buried)))
        straight=deepcopy(jacket)
        for section in straight['shoulder_return_sections']:
            first=straight['faces'][section[0]][1];last=straight['faces'][section[-1]][2]
            for j,i in enumerate(section):
                for k,t in ((1,j/len(section)),(2,(j+1)/len(section))):
                    straight['faces'][i][k][1:]=[(1-t)*first[axis]+t*last[axis] for axis in (1,2)]
        self.assertTrue(any('curvature' in f for f in P.findings(straight)))
        folded=deepcopy(self.rows[2]);a,b=folded['fold_top_faces']
        top=max(q[2] for f in folded['faces'] for q in f)
        for f in folded['faces'][a:b]:
            for q in f:q[2]=top
        self.assertTrue(any('fold_top_relief' in f for f in P.findings(folded)))
        for axis,screen in ((2,'fold_hem_return_height'),(1,'fold_hem_return_depth')):
            row=deepcopy(self.rows[2]);a,b=row['fold_hem_faces'];value=row['faces'][a][0][axis]
            for face in row['faces'][a:b]:
                for point in face:point[axis]=value
            self.assertTrue(any(screen in finding for finding in P.findings(row)))
        self.assertEqual(P.findings(jacket),[])

    def test_folded_items_have_deterministic_individual_offsets_without_moving_envelopes(self):
        p=self.case['parts'][2];shapes=[];variants=set()
        for i in range(16):
            item=deepcopy(p);item['id']='independent-fold-'+str(i)
            a=D.make(item);b=D.make(item)
            self.assertEqual(a,b)
            variants.add(json.loads(P.binding(item))['variant'])
            self.assertEqual(P.findings(a),[])
            self.assertEqual(D.enclosure_measurement(a,item)['maximum_escape_m'],0)
            shapes.append(a['appearance_sha256'])
        self.assertGreater(len(variants),1)
        self.assertEqual(len(set(shapes)),len(variants))
        self.assertEqual(D.make(p),self.rows[2])

    def test_every_actual_local_shape_and_all_bounded_fold_variants_fit_exact_envelopes(self):
        cache=json.loads(gzip.decompress(D.CACHE_PATH.read_bytes()))
        old=json.loads(gzip.decompress((ROOT/'tests/fixtures/drape-boards-before.json.gz').read_bytes()))
        seen=set()
        from archpipe.imported_appearance import encoded
        for part in old['parts']:
            data,_=D.local_input(part);key=digest(data)
            if key in seen:continue
            seen.add(key)
            for variant in range(8) if part['part_kind']=='folded-fabric' else (0,):
                binding=json.loads(P.binding(part));binding['variant']=variant
                result=P.apply(data,cache['entries'][key],encoded(binding))
                if part.get('garment_type') in ('shirt','jacket',None):
                    self.assertEqual(result['enclosure']['maximum_escape_m'],0,(part['id'],variant))
                    self.assertEqual(P.findings(dict(result,garment_type=part.get('garment_type'))),[])

    def test_polished_zero_escape_uses_exact_live_bounds_beyond_rounded_cache_key(self):
        original=deepcopy(self.case['parts'][2]);data,_=D.local_input(original);bb=D.bounds(original)
        self.assertEqual(D.enclosure_measurement(D.make(original),original)['maximum_escape_m'],0)
        shorter=deepcopy(original);shorter['id']='renamed-exact-envelope'
        height=bb[5]-bb[2]
        for face in shorter['faces']:
            for p in face:p[2]=bb[2]+(p[2]-bb[2])*(1-4e-8/height)
        self.assertEqual(D.local_input(shorter)[0],data)
        with self.assertRaisesRegex(ValueError,'actual physical envelope'):D.make(shorter)

    def test_actual_pad_perimeter_and_translated_sibling_fail_fold_edge_contrast(self):
        before=json.loads(gzip.decompress((ROOT/'tests/fixtures/drape-polish-fold-before.json.gz').read_bytes()))
        for row in before['meshes']:
            self.assertLess(P.metrics(row)['fold_edge_contrast_m'],P.policy()['minimum_fold_edge_contrast_m'])
            self.assertTrue(P.findings(row))
            sibling=deepcopy(row);sibling['id']='other-'+row['id']
            sibling['faces']=[[[q[0]+4,q[1]-7,q[2]+3] for q in f] for f in row['faces']]
            self.assertTrue(P.findings(sibling))
        for row in self.rows[2:]:self.assertEqual(P.findings(row),[])

    def test_preserves_actual_gravity_cache_and_physical_values(self):
        self.assertEqual(hashlib.sha256(D.CACHE_PATH.read_bytes()).hexdigest(),self.case['cache_sha256'])
        p=deepcopy(self.case['parts'][0]);before=digest(p)
        data,_=D.local_input(p);raw=json.loads(gzip.decompress(D.CACHE_PATH.read_bytes()))['entries'][digest(data)];old=digest(raw)
        out=P.apply(data,raw,P.binding(p))
        self.assertNotEqual(out['mesh_sha256'],raw['mesh_sha256'])
        self.assertEqual(digest(raw),old);self.assertEqual(digest(p),before)
        self.assertEqual(out['simulation'],raw['simulation'])

    def test_independent_process_hash_salts_and_binding_mutations(self):
        code="""import json,gzip;from pathlib import Path;from archpipe.drape_appearance import make;from archpipe.imported_appearance import digest
case=json.loads(gzip.decompress(Path('tests/fixtures/drape-polish-before.json.gz').read_bytes()))
print(json.dumps([digest(make(p)) for p in case['parts']]))"""
        outputs=[]
        for salt in ('0','987654'):
            result=subprocess.run([os.sys.executable,'-c',code],cwd=ROOT,env=dict(os.environ,PYTHONHASHSEED=salt),capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr);outputs.append(result.stdout)
        self.assertEqual(outputs[0],outputs[1])
        scene=dict(meshes=[deepcopy(self.case['parts'][0])],materials={});D.bind_scene(scene);D.require_scene(scene)
        for field in ('drape_polish_policy_sha256',):
            changed=deepcopy(scene);changed[field]='0'*64
            with self.assertRaises(ValueError):D.require_scene(changed)
        changed=deepcopy(scene);changed['draped_appearances'][0]['template_sha256']='0'*64
        with self.assertRaises(ValueError):D.require_scene(changed)

    def test_portable_cache_replaces_runtime_reconstruction_and_invalidates_on_file_changes(self):
        case=json.loads((ROOT/'tests/fixtures/drape-polish-runtime-before.json').read_text())
        self.assertNotEqual(case['python_template_sha256'],case['blender_template_sha256'])
        self.assertTrue(case['differences'])
        self.assertLess(max(abs(a-b) for _,a,b in case['differences'] if isinstance(a,(int,float))),1e-16)
        physical=self.case['parts'][0]
        D._trusted_template.cache_clear()
        with patch.object(P,'apply',side_effect=AssertionError('runtime reconstruction')):
            good=D.make_reference(physical)
        cache=json.loads(gzip.decompress(P.CACHE_PATH.read_bytes()))
        data,_=D.local_input(physical);raw=json.loads(gzip.decompress(D.CACHE_PATH.read_bytes()))['entries'][digest(data)]
        key=digest(P.cache_input(data,raw,P.binding(physical)))
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'polish.json.gz'
            target.write_bytes(P.CACHE_PATH.read_bytes())
            with patch.object(P,'CACHE_PATH',target):
                self.assertEqual(D.make_reference(physical),good)
                for mutation in ('missing','faces','proof','source-bounds','construction'):
                    bad=deepcopy(cache)
                    if mutation=='missing':bad['entries'].pop(key)
                    elif mutation=='faces':bad['entries'][key]['template']['faces'][0][0][0]+=.001
                    elif mutation=='proof':bad['entries'][key]['process_sha256']=['0'*64]*2
                    else:
                        entry=bad['entries'][key]
                        if mutation=='source-bounds':entry['template']['source_enclosure_bounds_m'][0]+=.001
                        else:entry['template']['polish']['variant']=99
                        entry['process_sha256']=[digest(entry['template'])]*2
                    target.write_bytes(gzip.compress(json.dumps(bad).encode(),mtime=0))
                    with self.subTest(mutation=mutation),self.assertRaises(ValueError):D.make_reference(physical)
                target.write_bytes(gzip.compress(json.dumps(cache).encode(),mtime=0))
                self.assertEqual(D.make_reference(physical),good)

    def test_live_blender_reads_identical_stored_geometry_references(self):
        blender=Path('/home/omar/opt/blender/blender')
        if not blender.is_file():self.skipTest('pinned workstation Blender unavailable')
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'input.json';output=Path(directory)/'readback.json'
            source.write_text(json.dumps(dict(parts=self.case['parts'],references=[D.make_reference(p) for p in self.case['parts']])))
            result=subprocess.run([str(blender),'-b','-t','1','--python-exit-code','1','-P',str(ROOT/'tests/blender_drape_polish.py'),
                                   '--','--input',str(source),'--output',str(output)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout[-2000:]+result.stderr[-2000:])
            self.assertTrue(json.loads(output.read_text())['exact_match'])

    def test_actual_rail_gap_mutation_and_shifted_sibling_fire_clean_gap_quiet(self):
        old=json.loads(gzip.decompress((ROOT/'tests/fixtures/drape-boards-before.json.gz').read_bytes()))
        parts=old['parts'];garments=[p for p in parts if p.get('garment_type') in ('shirt','jacket')]
        # The fixture contains eligible parts only; preserve actual hanger/rail
        # metadata from the saved value-bound garment support identities.
        rows=[D.make(p) for p in garments]
        hangers=[dict(id=p['contents_support'],contents_support='actual-rail') for p in garments]
        first,second=garments[:2];selected=[first,second]+hangers[:2];rendered=rows[:2]
        self.assertEqual(P.gap_findings(selected,rendered),[])
        gap=P.hanging_gaps(selected,rendered)[0]['gap_m'];self.assertGreaterEqual(gap,.027)
        for shifted in (False,True):
            bad=deepcopy(rendered);physical=deepcopy(selected)
            for f in bad[1]['faces']:
                for q in f:q[0]-=gap-.026
            self.assertTrue(P.gap_findings(physical,bad))
            if shifted:
                remap={p['id']:'other-'+p['id'] for p in physical}
                for p in physical:
                    p['id']=remap[p['id']]
                    if p.get('contents_support') in remap:p['contents_support']=remap[p['contents_support']]
                for p in bad:
                    p['id']=remap[p['id']]
                    p['faces']=[[[q[0]+4,q[1]-7,q[2]+3] for q in f] for f in p['faces']]
                self.assertTrue(P.gap_findings(physical,bad))
