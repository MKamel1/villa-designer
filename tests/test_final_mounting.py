"""Frozen final-C4 defects and complete rigid assembly construction proofs."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from archpipe.concept import villa_render as VR, villa_r11 as R
from archpipe.concept.attached_assembly import bind, translate, findings
from archpipe.concept.final_mounting import trim_panel
from archpipe.concept.fitting_mounting import bounds
from archpipe.concept.mounting import scene_findings


class FinalMounting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scene = VR.build(views=[])
        cls.frozen = json.loads(Path('tests/fixtures/c4-final-before.json').read_text())

    def test_real_final_candidate_only_family_clearances(self):
        from archpipe.concept.mounting_clearances import review
        self.assertEqual(scene_findings(self.scene), [])
        report = review(self.scene)
        self.assertEqual(len(report['failures']), 3)
        self.assertTrue(all(r['room']=='family-bath' for r in report['failures']))
        self.assertEqual(report['unresolved'], [])
        split = deepcopy(self.scene)
        root = next(m for m in split['meshes'] if m['id']=='appliance-coffee-main-body')
        for face in root['faces']:
            for point in face: point[2]+=.012
        self.assertEqual(sum('attached assembly split movement' in f for f in scene_findings(split)),3)
        final = self.scene['c4_final']
        self.assertEqual(len(final['applied']), 14)
        self.assertAlmostEqual(final['headboard']['old_width_mm'], 1980)
        self.assertAlmostEqual(final['headboard']['new_width_mm'], 1586)
        self.assertEqual(final['headboard']['basis'], 'Symmetric about unchanged bed centreline')
        for coffee in final['coffee']:
            self.assertAlmostEqual(coffee['delta'][2], .012)
            self.assertEqual(len(coffee['members']), 4)
            for record in coffee['members']:
                for before,after in zip(record['old_faces'],record['new_faces']):
                    for a,b in zip(before,after):
                        for axis in range(3):
                            self.assertAlmostEqual(b[axis]-a[axis],record['delta'][axis])

    def test_real_split_move_fires_rigid_move_quiet_and_renamed_hood_sibling(self):
        for root_id in ('appliance-coffee-main-body','appliance-coffee-dirty-body','appliance-hood-dirty-canopy'):
            original = deepcopy(self.frozen)
            children = [m['id'] for m in original['meshes'] if m.get('associated_mounting_root')==root_id]
            bind(original, root_id, children)
            self.assertEqual(findings(original), [])
            split = deepcopy(original)
            root = next(m for m in split['meshes'] if m['id']==root_id)
            for face in root['faces']:
                for point in face: point[2]+=.012
            self.assertEqual(len(findings(split)), len(children))
            for member in original['meshes']:
                member['id']='other-'+member['id']
                if member.get('associated_mounting_root'):
                    member['associated_mounting_root']='other-'+member['associated_mounting_root']
                member['faces']=[[[p[0]+7,p[1]-3,p[2]+2] for p in f] for f in member['faces']]
            records = translate(original,'other-'+root_id,[.031,-.022,.012])
            self.assertEqual(len(records),len(children)+1)
            self.assertEqual(findings(original), [])
            child = next(m for m in original['meshes'] if m['id']=='other-'+children[0])
            for face in child['faces']:
                for point in face: point[0]+=.005
            self.assertTrue(findings(original))

    def test_frozen_penetrations_and_wall_edge_fire_trim_generalises(self):
        failures = scene_findings(self.frozen)
        self.assertEqual(sum('associated assembly body penetrates support face 12.000 mm' in f for f in failures),2)
        self.assertIn('detail-headboard-slats: MISSING finite host coverage at fixing footprint',failures)
        panel = next(m for m in self.frozen['meshes'] if m['id']=='detail-headboard-slats')
        for travel in (0,17):
            sibling = deepcopy(panel)
            host = deepcopy(self.frozen['mounting_hosts'][panel['mounting']['host_id']])
            for face in sibling['faces']+host['source_faces']:
                for point in face: point[0]+=travel
            result = trim_panel(sibling,host,20.33+travel,.010)
            self.assertAlmostEqual(bounds(sibling)[0],19.537+travel)
            self.assertAlmostEqual(result['new_width_mm'],1586)

    def test_final_approval_drift_refuses_before_any_application(self):
        from archpipe.concept.final_mounting import apply
        scene = deepcopy(self.frozen)
        row = next(r for r in scene['mounting_movements'] if r['id']=='landscape-trellis-east')
        row['new'][0] += .005
        before = deepcopy(scene['meshes'])
        with self.assertRaisesRegex(ValueError,'final approved schedule drift'):
            apply(scene,R.design('D1'))
        self.assertEqual(scene['meshes'],before)

    def test_small_automatic_parent_move_carries_real_attached_children(self):
        from archpipe.concept.fitting_mounting import package, points
        from archpipe.concept.mounting import Host, Finish
        for root_id in ('appliance-coffee-main-body','appliance-hood-dirty-canopy'):
            scene = deepcopy(self.frozen)
            root = next(m for m in scene['meshes'] if m['id']==root_id)
            children = [m['id'] for m in scene['meshes'] if m.get('associated_mounting_root')==root_id]
            bind(scene,root_id,children)
            outward = (0,0,1) if 'coffee' in root_id else (0,-1,0)
            fixing = min(sum(p[i]*outward[i] for i in range(3)) for p in points(root))
            host = Host('unrelated-small-move','joinery-panel',tuple((fixing+.003)*v for v in outward),outward,Finish('modeled',0))
            before = {m['id']:bounds(m) for m in scene['meshes'] if m['id'] in children}
            package(scene,[root],host,fixing,'small-move',root_id)
            self.assertEqual(findings(scene),[])
            for child in scene['meshes']:
                if child['id'] in before:
                    for axis in range(3):
                        self.assertAlmostEqual(bounds(child)[axis]-before[child['id']][axis],.003*outward[axis])
            # Mixed packages defer an explicitly supplied child to its own
            # iteration; the root must not move that child twice.
            if len(children)>1:
                child=next(m for m in scene['meshes'] if m['id']==children[0])
                fixing=min(sum(p[i]*outward[i] for i in range(3)) for p in points(root))
                host=Host('mixed-small-move','joinery-panel',tuple((fixing+.003)*v for v in outward),outward,Finish('modeled',0))
                package(scene,[root,child],host,fixing,'mixed-small-move',root_id)
                self.assertEqual(findings(scene),[])


if __name__=='__main__': unittest.main()
