"""Real rejected cloth values, siblings and fail-closed appearance admission."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from archpipe import drape_appearance as D
from archpipe.imported_appearance import digest
from archpipe.concept.physical_part import geometry_errors

ROOT=Path(__file__).resolve().parents[1]


def frozen():
    return json.loads(gzip.decompress((ROOT/'tests/fixtures/drape-boards-before.json.gz').read_bytes()))


class Appearance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=frozen()
        cls.cache=json.loads(gzip.decompress(D.CACHE_PATH.read_bytes()))

    def test_real_board_values_fail_preregistered_screens_new_shells_pass(self):
        for typ in ('dress','abaya','shirt','jacket','trousers'):
            physical=next(p for p in self.before['parts'] if p.get('garment_type')==typ)
            with self.subTest(typ=typ):
                self.assertTrue(D.appearance_findings(D.frozen_appearance(physical)))
                row=D.make(physical,self.cache)
                self.assertEqual(D.appearance_findings(row),[])
                self.assertEqual(row['standin_sha256'],digest(physical))
                self.assertEqual(row['physical_part'],False)

    def test_renamed_translated_real_sibling_reuses_shape_and_keeps_binding(self):
        for typ in ('dress','abaya','shirt','jacket','trousers'):
            physical=next(p for p in self.before['parts'] if p.get('garment_type')==typ)
            sibling=deepcopy(physical);sibling['id']='alternate-'+typ
            sibling['faces']=[[[p[0]+4,p[1]-7,p[2]+3] for p in f] for f in sibling['faces']]
            self.assertTrue(D.appearance_findings(D.frozen_appearance(sibling)))
            a=D.make(physical,self.cache);b=D.make(sibling,self.cache)
            self.assertEqual(a['input_sha256'],b['input_sha256'])
            self.assertNotEqual(a['standin_sha256'],b['standin_sha256'])
            self.assertEqual(D.appearance_findings(b),[])
            self.assertAlmostEqual(D.measure(a['skin_vertices'],a['boundary_indices'])['plumb_angle_deg'],
                                   D.measure(b['skin_vertices'],b['boundary_indices'])['plumb_angle_deg'])

    def test_every_cached_shell_closed_and_inside_unchanged_physical_envelope(self):
        seen=set()
        for physical in self.before['parts']:
            data,_=D.local_input(physical);key=digest(data)
            if key in seen:continue
            seen.add(key);row=D.make(physical,self.cache)
            self.assertEqual(geometry_errors(row['faces']),[],physical['id'])
            measured=D.enclosure_measurement(row,physical)
            self.assertLessEqual(measured['maximum_escape_m'],D.policy()['spacing_m'])
            self.assertEqual(len(set(row['simulation'].get('pins',[]))),len(row['simulation'].get('pins',[])))
        self.assertEqual(len(seen),len(self.cache['entries']))

    def test_real_mutations_refuse_cache_and_envelope(self):
        physical=next(p for p in self.before['parts'] if p.get('garment_type')=='dress')
        data,_=D.local_input(physical);key=digest(data)
        for mutation in ('missing','corrupt','escape','proof'):
            cache=deepcopy(self.cache)
            if mutation=='missing':cache['entries'].pop(key)
            elif mutation=='corrupt':cache['entries'][key]['faces'][0][0][0]+=.001
            elif mutation=='proof':cache['entries'][key]['independent_process_sha256']=['bad','different']
            else:
                entry=cache['entries'][key]
                entry['faces'][0][0][0]+=.20
                entry['mesh_sha256']=digest(entry['faces'])
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):D.make(physical,cache)
        changed=deepcopy(physical);changed['faces'][0][0][0]+=.001
        with self.assertRaises(ValueError):D.make(changed,self.cache)

    def test_pre_registered_morphology_mutations_fire(self):
        physical=next(p for p in self.before['parts'] if p.get('garment_type')=='dress')
        good=D.make(physical,self.cache)
        for mutation in ('flat','lean','hem'):
            row=deepcopy(good);points=row['skin_vertices']
            if mutation=='flat':
                for p in points:p[0]=0
            elif mutation=='lean':
                top=max(p[2] for p in points)
                for p in points:p[0]+=.30*(top-p[2])
            else:
                low=min(p[2] for p in points)
                for i in row['boundary_indices']:
                    if points[i][2]<low+.02:points[i][2]=low
            self.assertTrue(D.appearance_findings(row),mutation)
        self.assertEqual(D.appearance_findings(good),[])

    def test_independent_process_receipts_for_every_unique_input(self):
        for entry in self.cache['entries'].values():
            proof=entry['independent_process_sha256']
            self.assertEqual(len(proof),2)
            self.assertEqual(proof[0],proof[1])
            self.assertEqual(entry['mesh_sha256'],digest(entry['faces']))
            if entry['simulation']['method'].startswith('Blender'):
                self.assertEqual(entry['simulation']['frames'],D.policy()['frames'])
                self.assertEqual(entry['simulation']['gravity'],[0,0,-9.81])
                self.assertEqual(entry['simulation']['threads'],1)
                self.assertTrue(entry['simulation']['pins'])

    def test_real_stack_support_contact_is_bidirectional_and_never_penetration(self):
        parts=deepcopy(self.before['parts']);by={p['id']:p for p in parts}
        upper=next(p for p in parts if p.get('contents_support') in by and by[p['contents_support']]['part_kind']=='folded-fabric')
        lower=by[upper['contents_support']]
        for sibling in (False,True):
            a,b=deepcopy(lower),deepcopy(upper)
            if sibling:
                b['contents_support']='renamed-lower';a['id']='renamed-lower';b['id']='renamed-upper'
                for p in (a,b):p['faces']=[[[q[0]+4,q[1]-7,q[2]+3] for q in f] for f in p['faces']]
            scene=dict(meshes=[a,b],materials={});D.bind_scene(scene)
            self.assertEqual(D.collision_findings(scene),[])
            rows=deepcopy(scene['draped_appearances'])
            rows[1]['faces']=[[[q[0],q[1],q[2]-.001] for q in f] for f in rows[1]['faces']]
            self.assertTrue(D.collision_findings(scene,rows))
            b['contents_support']='missing-support'
            self.assertTrue(D.collision_findings(scene))

    def test_live_two_process_trouser_determinism(self):
        # Fastest hanging input; all other inputs have recorded two-process
        # receipts generated by the same command, never in-process rebakes.
        blender=Path('/home/omar/opt/blender/blender')
        if not blender.is_file():self.skipTest('pinned workstation Blender unavailable')
        p=next(p for p in self.before['parts'] if p.get('garment_type')=='trousers')
        data,_=D.local_input(p)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'input.json';source.write_text(json.dumps(data));outputs=[]
            for i in (1,2):
                target=root/f'process-{i}.json'
                result=subprocess.run([str(blender),'-b','-t','1','--python-exit-code','1','-P',str(D.GENERATOR_PATH),
                    '--','--input',str(source),'--output',str(target)],cwd=ROOT,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stdout[-2000:]+result.stderr[-2000:])
                outputs.append(json.loads(target.read_text()))
            self.assertEqual(digest(outputs[0]),digest(outputs[1]))
            self.assertEqual(outputs[0]['mesh_sha256'],self.cache['entries'][digest(data)]['mesh_sha256'])
            stale=dict(data,generator_sha256='0'*64)
            source.write_text(json.dumps(stale))
            result=subprocess.run([str(blender),'-b','-t','1','--python-exit-code','1','-P',str(D.GENERATOR_PATH),
                '--','--input',str(source),'--output',str(root/'stale.json')],cwd=ROOT,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('generator changed after cloth input was hashed',result.stdout+result.stderr)
            self.assertFalse((root/'stale.json').exists())



class SceneAdmission(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tests.test_render_standard import SCENE
        cls.scene=SCENE

    def test_render_replacements_do_not_change_c3_c4_c8_physical_values(self):
        from archpipe.concept import garments as G
        from archpipe.concept.mounting import scene_findings
        scene=self.scene;physical_hash=digest(scene['meshes'])
        self.assertEqual(G.contents_findings(scene['dressing_wardrobes'],scene['meshes']),[])
        self.assertEqual([f for f in scene_findings(scene) if f.startswith('dress-')],[])
        rendered=D.rendered_meshes(scene)
        self.assertEqual(physical_hash,digest(scene['meshes']))
        self.assertEqual([p['id'] for p in rendered],[p['id'] for p in scene['meshes']])
        self.assertEqual(D.collision_findings(scene),[])
        baseline={p['id']:p for p in frozen()['parts']}
        for part in scene['meshes']:
            if D.eligible(part):self.assertEqual(part['faces'],baseline[part['id']]['faces'])

    def test_missing_stale_or_relabelled_appearance_refuses_render(self):
        # Copy only affected lists, retaining read-only architectural rows.
        for mutation in ('missing','stale','physical','duplicate'):
            scene=dict(self.scene,draped_appearances=deepcopy(self.scene['draped_appearances']))
            rows=scene['draped_appearances']
            if mutation=='missing':rows.pop()
            elif mutation=='stale':rows[0]['faces'][0][0][0]+=.001
            elif mutation=='physical':rows[0]['physical_part']=True
            else:rows[-1]=deepcopy(rows[0])
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):D.rendered_meshes(scene)

    def test_neighbour_joinery_and_door_mutations_fire_on_real_shell(self):
        from archpipe.concept.villa_render import box_faces
        row=next(p for p in self.scene['draped_appearances'] if p.get('garment_type')=='dress')
        box=D.bounds(row)
        for kind in ('neighbour','joinery','door'):
            obstacle=dict(id='renamed-'+kind,faces=box_faces(*box),material='oak',part_kind='garment' if kind=='neighbour' else kind)
            scene=dict(self.scene,meshes=list(self.scene['meshes'])+[obstacle])
            self.assertTrue(D.collision_findings(scene,[row]),kind)
        self.assertEqual(D.collision_findings(self.scene,[row]),[])

if __name__=='__main__':unittest.main()
