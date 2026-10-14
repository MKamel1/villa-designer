"""Real rejected cloth values, siblings and fail-closed appearance admission."""
from copy import deepcopy
import gzip
import json
import os
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
        for mutation in ('missing','corrupt','escape','proof','unbound-proof','skin'):
            cache=deepcopy(self.cache)
            if mutation=='missing':cache['entries'].pop(key)
            elif mutation=='corrupt':cache['entries'][key]['faces'][0][0][0]+=.001
            elif mutation=='proof':cache['entries'][key]['independent_process_sha256']=['bad','different']
            elif mutation=='unbound-proof':cache['entries'][key]['independent_process_sha256']=['0'*64]*2
            elif mutation=='skin':cache['entries'][key]['skin_vertices'][0][0]+=.001
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
            rows=deepcopy(D.rendered_meshes(scene))
            rows[1]['faces']=[[[q[0],q[1],q[2]-.001] for q in f] for f in rows[1]['faces']]
            self.assertTrue(D.collision_findings(scene,rows))
            b['contents_support']='missing-support'
            self.assertTrue(D.collision_findings(scene))

    def test_neighbour_appearance_expansion_is_checked_on_real_layers_and_sibling(self):
        case=json.loads(gzip.decompress((ROOT/'tests/fixtures/drape-neighbour-gap-before.json.gz').read_bytes()))
        self.assertEqual(case['before_findings'],[])
        self.assertTrue(all(m['maximum_escape_m']<D.policy()['spacing_m'] for m in case['enclosure']))
        for translated in (False,True):
            scene=deepcopy(case['scene'])
            if translated:
                for row in scene['meshes']+scene['draped_appearances']:
                    row['id']='another-'+row['id']
                    row['faces']=[[[p[0]+4,p[1]-7,p[2]+3] for p in f] for f in row['faces']]
            self.assertTrue(D.collision_findings(scene))
            # Removing the proposed cloth translations keeps the same real
            # shapes and physical gap quiet; no new clearance is imposed.
            for row,delta in zip(scene['draped_appearances'],(-.0025,.0025)):
                row['faces']=[[[p[0],p[1],p[2]+delta] for p in f] for f in row['faces']]
            self.assertEqual(D.collision_findings(scene),[])

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
                    '--','--input',str(source),'--output',str(target)],cwd=ROOT,capture_output=True,text=True,
                    env=dict(os.environ,PYTHONHASHSEED=str(0 if i==1 else 987654)))
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
            stale=deepcopy(data);stale['dependencies_sha256']['stable_seed']='0'*64
            source.write_text(json.dumps(stale))
            result=subprocess.run([str(blender),'-b','-t','1','--python-exit-code','1','-P',str(D.GENERATOR_PATH),
                '--','--input',str(source),'--output',str(root/'stale-dependency.json')],cwd=ROOT,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('pattern dependency changed after cloth input was hashed',result.stdout+result.stderr)
            self.assertFalse((root/'stale-dependency.json').exists())

    def test_warm_cache_never_launches_solver_and_mutable_results_are_independent(self):
        from unittest.mock import patch
        physical=next(p for p in self.before['parts'] if p.get('garment_type')=='dress')
        with patch('subprocess.run',side_effect=AssertionError('solver launched in scene build')):
            a=D.make(physical);b=D.make(physical)
            self.assertEqual(a,b)
            a['faces'][0][0][0]+=.001
            self.assertNotEqual(a,b)
            self.assertEqual(D.make(physical),b)

    def test_compact_reference_readback_and_pose_mutations_refuse(self):
        physical=deepcopy(next(p for p in self.before['parts'] if p.get('garment_type')=='dress'))
        scene=dict(meshes=[physical],materials={});D.bind_scene(scene)
        row=scene['draped_appearances'][0]
        self.assertTrue(row['appearance_reference'])
        self.assertNotIn('faces',row)
        D.require_scene(scene)
        readback=json.loads(json.dumps(scene));D.require_scene(readback)
        for mutation in ('origin','bounds','hash','faces','reference'):
            changed=deepcopy(readback);r=changed['draped_appearances'][0]
            if mutation=='origin':r['origin_m'][0]+=.001
            elif mutation=='bounds':r['render_bounds_m'][0]+=.001
            elif mutation=='hash':r['appearance_sha256']='0'*64
            elif mutation=='reference':r.pop('appearance_reference')
            else:r['faces']=D.make(physical)['faces']
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):D.require_scene(changed)
        physical['label']='changed physical record'
        with self.assertRaises(ValueError):D.require_scene(scene)

    def test_changed_pattern_helper_requires_a_fresh_cache(self):
        from unittest.mock import patch
        physical=next(p for p in self.before['parts'] if p.get('garment_type')=='dress')
        changed=D.generator_dependencies();changed['stable_seed']='0'*64
        with patch.object(D,'generator_dependencies',return_value=changed),self.assertRaises(ValueError):
            D.make_reference(physical)

    def test_material_appearance_preserves_physical_and_shared_material_values(self):
        case=json.loads((ROOT/'tests/fixtures/drape-materials-before.json').read_text())
        self.assertNotEqual(case['physical'],case['appearance'])
        physical=deepcopy(next(p for p in self.before['parts'] if p.get('garment_type')=='dress'))
        materials={'garment-ivory':deepcopy(case['physical'])}
        scene=dict(meshes=[physical],materials=materials)
        before=digest(materials);D.bind_scene(scene)
        self.assertEqual(digest(materials),before)
        self.assertEqual(D.render_materials(scene)['garment-ivory'],case['appearance'])
        self.assertEqual(digest(materials),before)
        scene['drape_material_overrides']['garment-ivory']['roughness']=.2
        with self.assertRaises(ValueError):D.render_materials(scene)

    def test_topology_float_snapshot_preserves_real_faces_and_nonfloat_siblings(self):
        from archpipe.geometry_topology import _faces
        # Literal frozen former conversion, replayed on actual rejected bodies.
        def before(faces):return tuple(tuple(tuple(float(v) for v in p) for p in f) for f in faces)
        for physical in self.before['parts']:
            self.assertEqual(_faces(physical['faces']),before(physical['faces']))
        import numpy as np
        for faces in ([[[-0.,1.,2.],[1.,2.,3.],[2.,3.,4.]]],
                      [[[0,1,2],[np.float32(1),np.float32(2),np.float32(3)],[True,False,1]]]):
            a,b=_faces(faces),before(faces)
            self.assertEqual([[v.hex() for p in f for v in p] for f in a],
                             [[v.hex() for p in f for v in p] for f in b])

    def test_cache_key_precision_never_relaxes_actual_world_enclosure(self):
        physical=deepcopy(next(p for p in self.before['parts'] if p['part_kind']=='folded-fabric'))
        data,_=D.local_input(physical);key=digest(data)
        template=deepcopy(self.cache['entries'][key]);offset=D.policy()['spacing_m']-2e-8
        for face in template['faces']:
            for p in face:p[2]+=offset
        for p in template['skin_vertices']:p[2]+=offset
        template['mesh_sha256']=digest(template['faces'])
        template['enclosure']=D.enclosure_measurement(template,dict(faces=data['faces']))
        process={k:v for k,v in template.items() if k not in ('enclosure','independent_process_sha256')}
        template['independent_process_sha256']=[digest(process)]*2
        cache=dict(schema='drape-cloth-cache/1',entries={key:template})
        D.make(physical,cache)
        sibling=deepcopy(physical);box=D.bounds(sibling);height=box[5]-box[2]
        for face in sibling['faces']:
            for p in face:p[2]=box[2]+(p[2]-box[2])*(1-4e-8/height)
        self.assertEqual(digest(D.local_input(sibling)[0]),key)
        with self.assertRaises(ValueError):D.make(sibling,cache)



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
            elif mutation=='stale':rows[0]['origin_m'][0]+=.001
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
            # A completely enclosed real shell has no face crossings.
            enclosing=[v-.1 for v in box[:3]]+[v+.1 for v in box[3:]]
            obstacle=dict(obstacle,faces=box_faces(*enclosing))
            scene=dict(self.scene,meshes=list(self.scene['meshes'])+[obstacle])
            self.assertTrue(D.collision_findings(scene,[row]),'enclosed '+kind)
        self.assertEqual(D.collision_findings(self.scene,[row]),[])

    def test_real_joinery_air_cavity_is_not_enclosed_material_and_sibling(self):
        from archpipe.concept.villa_render import box_faces
        case=json.loads(gzip.decompress((ROOT/'tests/fixtures/drape-cavity-before.json.gz').read_bytes()))
        for translated in (False,True):
            scene=deepcopy(case)
            if translated:
                for row in scene['meshes']+scene['draped_appearances']:
                    row['id']='another-'+row['id']
                    row['faces']=[[[p[0]+4,p[1]-7,p[2]+3] for p in f] for f in row['faces']]
            self.assertEqual(D.collision_findings(scene),[])
            row=scene['draped_appearances'][0];box=D.bounds(row)
            enclosing=[v-.1 for v in box[:3]]+[v+.1 for v in box[3:]]
            scene['meshes'].append(dict(id='occupied-body',part_kind='joinery',faces=box_faces(*enclosing)))
            self.assertTrue(D.collision_findings(scene))

    def test_opening_prefilter_preserves_real_review_and_translated_intrusion(self):
        import importlib.util
        from archpipe.concept.render_support import blocked_openings
        from archpipe.concept.villa_render import LZ
        spec_before=importlib.util.spec_from_file_location('archpipe.concept._frozen_openings',
            ROOT/'tests/fixtures/drape-openings-before.py')
        module=importlib.util.module_from_spec(spec_before);spec_before.loader.exec_module(module)
        before=module.blocked_openings
        self.assertEqual(blocked_openings(self.scene),before(self.scene))
        door=deepcopy(self.scene['authoring_room_context']['specification']['doors'][0])
        part=deepcopy(next(p for p in frozen()['parts'] if p.get('garment_type')=='dress'))
        box=D.bounds(part);origin=[(box[0]+box[3])/2,(box[1]+box[4])/2,box[2]]
        shift=[door['x']-origin[0],door['y']-origin[1],LZ[door['level']]+.10-origin[2]]
        part['faces']=[[[p[k]+shift[k] for k in range(3)] for p in f] for f in part['faces']]
        for sibling in (False,True):
            p,d=deepcopy(part),deepcopy(door)
            if sibling:
                p['id']='another-cloth';d['rooms']=['another-room']
                d['x']+=4;d['y']-=7
                p['faces']=[[[v[0]+4,v[1]-7,v[2]] for v in f] for f in p['faces']]
            scene=dict(meshes=[p]);lay=dict(rooms={});spec=dict(doors=[d])
            a,b=blocked_openings(scene,lay,specification=spec),before(scene,lay,specification=spec)
            self.assertTrue(a);self.assertEqual(a,b)

if __name__=='__main__':unittest.main()
