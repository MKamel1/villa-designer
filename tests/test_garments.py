"""Real l0923 by-value reproduction, sibling and independent physical proofs."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
import unittest

from archpipe.concept import garments as G
from archpipe.concept.physical_part import PartMeshList, geometry_errors

ROOT=Path(__file__).resolve().parents[1]


def frozen():
    return json.loads(gzip.decompress((ROOT/'tests/fixtures/l0923-dressing-before.json.gz').read_bytes()))


def clean_package():
    before=frozen();sources=[]
    for row in before['meshes']:
        if not row['id'].startswith('furn-pd-hang'):continue
        faces=[];names=[]
        for i,name in enumerate(row['physical_components']):
            if name in ('plinth','divider','back'):
                faces+=row['faces'][i*6:i*6+6];names.append(name)
        sources.append(dict(row,faces=faces,physical_components=names))
    meshes,modules=G.build(before['wardrobes'],.002)
    return before['wardrobes'],sources+meshes


class PhysicalGarments(unittest.TestCase):
    def test_actual_l0923_empty_and_proxy_contents_frozen_by_value_fail(self):
        before=frozen()
        self.assertTrue(any(m.get('proxy_exemption') for m in before['meshes']))
        self.assertTrue(G.contents_findings(before['wardrobes'],before['meshes']))
        wardrobes,meshes=clean_package()
        self.assertEqual(G.contents_findings(wardrobes,meshes),[])

    def test_renamed_and_translated_real_sibling(self):
        def renamed(wardrobes,meshes):
            mapping={w['id']:'alternate-'+str(i) for i,w in enumerate(wardrobes)}
            for w in wardrobes:
                w['id']=mapping[w['id']];w['cx']+=4;w['cy']+=7
            refs={m['id']:m['id'].replace('furn-pd-hang-1','furn-alternate-0').replace('furn-pd-hang-2','furn-alternate-1') for m in meshes}
            for m in meshes:
                m['id']=refs[m['id']]
                if m.get('wardrobe_id'):m['wardrobe_id']=mapping[m['wardrobe_id']]
                for key in ('contents_support','contents_joint','associated_mounting_root'):
                    if m.get(key) in refs:m[key]=refs[m[key]]
                m['faces']=[[[p[0]+4,p[1]+7,p[2]+3] for p in f] for f in m['faces']]
            return wardrobes,meshes
        before=frozen();w,m=renamed(before['wardrobes'],before['meshes'])
        self.assertTrue(G.contents_findings(w,m))
        w,m=renamed(*clean_package());self.assertEqual(G.contents_findings(w,m),[])
        body=next(m for m in m if m.get('garment_type')=='shirt')
        body['faces']=[[[p[0],p[1]+.7,p[2]] for p in f] for f in body['faces']]
        self.assertTrue(G.contents_findings(w,m))

    def test_strict_closed_outward_axes_no_exemptions(self):
        w,m=clean_package();rows=[r for r in m if r.get('wardrobe_id')]
        admitted=PartMeshList();admitted.extend(rows)
        self.assertFalse(admitted.collect);self.assertEqual(admitted.failures,[])
        for row in rows:
            self.assertEqual(geometry_errors(row['faces']),[],row['id'])
            self.assertFalse(row.get('proxy_exemption'));self.assertEqual(row['local_axes'],['x','y','z'])
        broken=deepcopy(rows[0]);broken['faces'].pop()
        with self.assertRaises(ValueError):PartMeshList().append(broken)

    def test_every_rail_drawer_shelf_box_and_shoe_slot_required(self):
        w,m=clean_package()
        mutations=[lambda r:r.get('garment_type')=='trousers',
                   lambda r:r.get('drawer_front_id'),
                   lambda r:r.get('contents_role','').startswith('folded '),
                   lambda r:r.get('contents_role')=='lidded top box',
                   lambda r:r.get('contents_role')=='shoe']
        for remove in mutations:
            with self.subTest(remove=remove):
                self.assertTrue(G.contents_findings(w,[r for r in m if not remove(r)]))
        self.assertEqual(G.contents_findings(w,m),[])

    def test_separation_and_named_support_mutations_fire(self):
        w,m=clean_package()
        for change in ('float','collision','joinery','broken-chain','cycle','proxy','drop'):
            rows=deepcopy(m);body=next(r for r in rows if r.get('garment_type')=='dress')
            if change=='float':body['faces']=[[[p[0],p[1],p[2]-.10] for p in f] for f in body['faces']]
            elif change=='collision':
                other=next(r for r in rows if r.get('garment_type')=='abaya')
                body['faces']=deepcopy(other['faces'])
            elif change=='joinery':body['faces']=[[[p[0],p[1]+.30,p[2]] for p in f] for f in body['faces']]
            elif change=='broken-chain':body['contents_support']='missing-hanger'
            elif change=='cycle':body['contents_support']=body['id']
            elif change=='proxy':
                from archpipe.concept.villa_render import box_faces
                bb=G.bounds(body);body['faces']=box_faces(*bb)
            else:body['rail_drop_m']=.1
            with self.subTest(change=change):self.assertTrue(G.contents_findings(w,rows))
        self.assertEqual(G.contents_findings(w,m),[])

    def test_built_density_and_hanging_lengths_have_physical_gaps(self):
        w,m=clean_package()
        for rail in (r for r in m if r.get('contents_role')=='rail'):
            bodies=sorted([r for r in m if r.get('rail_id')==rail['id']],key=lambda r:G.bounds(r)[0])
            self.assertTrue(bodies)
            for a,b in zip(bodies,bodies[1:]):
                self.assertGreater(G.bounds(b)[0]-G.bounds(a)[3],.020)
            for row in bodies:
                drop=(G.bounds(rail)[2]+G.bounds(rail)[5])/2-G.bounds(row)[2]
                if row['garment_type'] in ('dress','abaya'):self.assertTrue(1.45<=drop<=1.60)
                elif row['garment_type']=='jacket':self.assertAlmostEqual(drop,.85)
                elif row['garment_type']=='trousers':self.assertAlmostEqual(drop,.900)
                else:self.assertIn('ASSUMED',row['drop_basis'])

    def test_frozen_l0923_body_and_first_fix_slabs_fail_morphology(self):
        before=frozen()
        bodies=[r for r in before['meshes'] if r['part_kind']=='garment' and 'long-hang' in r['id']]
        self.assertTrue(bodies)
        for row in bodies:
            self.assertTrue(G.sleeve_findings(dict(row,garment_type='dress')))
        from archpipe.concept.villa_render import box_faces
        first_fix=dict(id='renamed-sleeveless-sibling',garment_type='shirt',faces=box_faces(0,0,0,.05,.45,.75))
        self.assertTrue(G.sleeve_findings(first_fix))
        w,m=clean_package()
        for row in m:
            if row.get('garment_type'):self.assertEqual(G.sleeve_findings(row),[],row['id'])

    def test_actual_first_fix_hanger_intrusion_and_clean_contact(self):
        before=json.loads(gzip.decompress((ROOT/'tests/fixtures/garment-hanger-before.json.gz').read_bytes()))
        self.assertTrue(G.hanger_penetrations(before['hanger'],before['body']))
        self.assertGreater(G.contact_gap(before['hanger'],before['rail']),.001)
        w,m=clean_package();by={r['id']:r for r in m}
        for body in m:
            if body.get('part_kind')=='garment':
                self.assertEqual(G.hanger_penetrations(by[body['contents_support']],body),[],body['id'])
                self.assertLess(G.contact_gap(by[body['contents_support']],by[body['rail_id']]),1e-7)
        sibling=deepcopy(before)
        for row in sibling.values():
            row['id']='renamed-'+row['id']
            row['faces']=[[[p[0]+4,p[1]-7,p[2]+3] for p in f] for f in row['faces']]
        self.assertTrue(G.hanger_penetrations(sibling['hanger'],sibling['body']))

    def test_actual_context_plank_profile_and_clean_draped_siblings(self):
        before=json.loads(gzip.decompress((ROOT/'tests/fixtures/garment-hanger-before.json.gz').read_bytes()))
        self.assertTrue(G.profile_findings(before['body']))
        sibling=deepcopy(before['body']);sibling['id']='renamed-profile'
        sibling['faces']=[[[p[0]+2,p[1]-4,p[2]+3] for p in f] for f in sibling['faces']]
        self.assertTrue(G.profile_findings(sibling))
        w,m=clean_package()
        for body in m:
            if body.get('part_kind')=='garment':self.assertEqual(G.profile_findings(body),[],body['id'])

    def test_folded_trouser_drop_is_the_reread_900_mm_figure(self):
        self.assertTrue(G.TROUSER_CARD['original_page_checked'])
        self.assertEqual(G.TROUSER_CARD['unit'],'mm')
        self.assertEqual(G.TROUSER_CARD['verified_value'],900)
        self.assertAlmostEqual(G.DROP['trousers'],.900)
        self.assertIn('page 74',G.TROUSER_CARD['locator'])
        for rail_z in (1.08,2.02):
            body=G.body(0,0,rail_z,'trousers')
            self.assertAlmostEqual(rail_z-min(p[2] for f in body for p in f),.900)

    def test_real_thin_rounded_hem_cannot_self_cross(self):
        before=json.loads(gzip.decompress((ROOT/'tests/fixtures/garment-rounded-profile-before.json.gz').read_bytes()))
        self.assertTrue(G.horizontal_profile_findings(before))
        for width,depth,radius in ((.00928,.112,.008),(.012,.25,.013),(.25,.012,.013)):
            ring=G.rounded_ring(0,0,width,depth,0,radius)
            self.assertEqual(G.horizontal_profile_findings(dict(id='renamed-small-profile',faces=[ring])),[])
        w,m=clean_package()
        for row in m:self.assertEqual(G.horizontal_profile_findings(row),[],row['id'])

    def test_historical_retirement_is_exact_and_scoped(self):
        rows=json.loads((ROOT/'knowledge/garment-mounting-retirements.json').read_text())['rows']
        for row in rows:
            self.assertFalse(G.retire_historical_approval({},row))
            scene=dict(garment_contents_version='closed/1',mounting_movements=[])
            self.assertTrue(G.retire_historical_approval(scene,row))
            self.assertTrue(G.retire_historical_approval(scene,row))
            self.assertEqual(scene['garment_retired_approvals'], [row['id']])
            changed=deepcopy(row);changed['old'][0]+=.001
            with self.assertRaises(ValueError):G.retire_historical_approval(scene,changed)
            scene['mounting_movements']=[dict(id=row['id'])]
            with self.assertRaises(ValueError):G.retire_historical_approval(scene,row)


    def test_frozen_outward_parts_reproduce_shared_importer_float32_reversal(self):
        # Historical single-precision reproduction; production fix is proved
        # by tests.test_reproducibility and tests/blender_reproducibility.py.
        # Volume is in cubic metres. Float32 means single precision; float64
        # means double precision. A positive signed volume indicates outward
        # winding. Local subtraction changes arithmetic, not design geometry.
        import numpy as np
        before=json.loads(gzip.decompress((ROOT/'tests/fixtures/garment-importer-precision-before.json.gz').read_bytes()))
        self.assertTrue(before['actual_blender_warnings'])
        for part in before['parts']:
            self.assertEqual(geometry_errors(part['faces']),[])
            def volume(dtype,local):
                origin=np.array(part['faces'][0][0],dtype=dtype) if local else np.zeros(3,dtype=dtype)
                return sum(float(np.dot(np.array(face[0],dtype=dtype)-origin,
                    np.cross(np.array(face[i],dtype=dtype)-origin,
                             np.array(face[i+1],dtype=dtype)-origin)))/6
                    for face in part['faces'] for i in range(1,len(face)-1))
            self.assertGreater(volume(np.float64,False),0)
            self.assertLess(volume(np.float32,False),0)
            self.assertGreater(volume(np.float32,True),0)

    def test_frozen_scoped_scene_rebinds_pairs_and_keeps_stale_refusal(self):
        from archpipe.imported_appearance import bind_scene, require_scene
        before=json.loads(gzip.decompress((ROOT/'tests/fixtures/garment-scoped-admission-before.json.gz').read_bytes()))
        for renamed in (False,True):
            stale=deepcopy(before)
            if renamed:
                for key in ('imported_appearances','physical_model_meshes'):
                    for row in stale[key]: row['id']='other-'+row['id']
            with self.assertRaisesRegex(ValueError,'missing, stale'):
                require_scene(stale)
            clean=bind_scene(deepcopy(stale))
            self.assertEqual(require_scene(clean),[])
            self.assertEqual(clean['meshes'],before['meshes'])



class FreshDressingScene(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Acceptance runs test_render_standard too; share its fresh strict build.
        from tests.test_render_standard import SCENE
        cls.scene=SCENE

    def test_real_build_contents_and_c4_support(self):
        from archpipe.concept.mounting import scene_findings
        self.assertEqual(G.contents_findings(self.scene['dressing_wardrobes'],self.scene['meshes']),[])
        self.assertEqual([f for f in scene_findings(self.scene) if f.startswith('dress-')],[])
        self.assertEqual(len(self.scene['garment_retired_approvals']),10)

    def test_real_build_c8_support_openings_and_strict_admission(self):
        from archpipe.concept import render_support as S, villa_r11 as R
        # Existing complete-scene tests prove the same checks globally.
        rooms={w['room'] for w in self.scene['dressing_wardrobes']}
        selected=[m for m in self.scene['meshes'] if m.get('room') in rooms]
        from archpipe.imported_appearance import bind_scene
        sub=bind_scene(dict(self.scene,meshes=selected,props=[],cloth=[],models=[]))
        self.assertEqual(S.unsupported(sub),[])
        self.assertEqual([f for f in S.blocked_openings(self.scene,R.design('D1')) if 'dress-' in str(f)],[])
        admitted=PartMeshList();admitted.extend(selected)
        self.assertEqual(admitted.failures,[])


if __name__=='__main__':unittest.main()
