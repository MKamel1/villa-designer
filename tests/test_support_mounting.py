"""Real C4(e) reproduction, independent roots, pending authority and slides."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from archpipe.concept import villa_render as VR, villa_r11 as R
from archpipe.concept.mounting import scene_findings, check_mesh, Host, Finish
from archpipe.concept.fitting_mounting import bounds
from archpipe.concept.support_mounting import floor_assembly, nearest
from archpipe.concept.wc_slides import continuous_candidates


class SupportMounting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Retained package-f regressions deliberately evaluate that historical stage.
        from unittest.mock import patch
        with patch('archpipe.concept.final_mounting.apply'):
            cls.scene=VR.build(views=[])

    def test_real_missing_sites_now_bound_and_only_pending_findings(self):
        frozen=json.loads((Path(__file__).parent/'fixtures/c4-e-before.json').read_text())
        self.assertTrue(any('MISSING mounting host' in f for f in scene_findings(frozen)))
        self.assertEqual(len(self.scene['support_inventory_before']),300)
        findings=scene_findings(self.scene)
        self.assertFalse(any('MISSING mounting host' in f for f in findings))
        pending={r['id'] for r in self.scene['mounting_movements'] if r['approval']=='PENDING'}
        self.assertTrue(findings)
        self.assertTrue(all(f.split(':')[0] in pending or 'associated assembly body penetrates support face' in f or
                            f=='detail-headboard-slats: MISSING finite host coverage at fixing footprint'
                            for f in findings),findings)
        render_meshes = {m['id']: m for m in self.scene['meshes']}
        diag_meshes = {m['id']: m for m in self.scene.get('diagnostic_meshes', [])}
        last = {r['id']: r for r in self.scene['mounting_movements'] if r['package'] == 'e-support'}
        for row in last.values():
            rid = row['id']
            target = render_meshes.get(rid) or diag_meshes[rid]
            if row['approval'] == 'PENDING':
                self.assertGreater(row['mm'], 5)
                self.assertEqual(bounds(target), row['old'])
            else:
                if row['approval'].startswith('APPLIED <='):
                    self.assertLessEqual(row['mm'], 5 + 1e-9)
                else:
                    self.assertIn(row['id'], self.scene['e_lead_review']['applied'])
                self.assertEqual(target['faces'], row['proposed_faces'])
        from archpipe.villa_render_contract import validate_scene
        self.assertEqual(validate_scene(dict(self.scene,views=VR.VIEWS(R.design('D1')))),[])
        proposal=deepcopy(self.scene);by={m['id']:m for m in proposal['meshes']}
        for row in proposal['mounting_movements']:
            if row['approval']=='PENDING':by[row['id']]['faces']=row['proposed_faces']
        proposed_findings=scene_findings(proposal)
        self.assertEqual(len(proposed_findings),3)
        self.assertIn('detail-headboard-slats: MISSING finite host coverage at fixing footprint',proposed_findings)
        self.assertEqual(sum('associated assembly body penetrates' in f for f in proposed_findings),2)

    def test_generated_child_cannot_invent_floor_support_and_generalises(self):
        frozen=json.loads((Path(__file__).parent/'fixtures/c4-e-before.json').read_text())
        originals=[m for m in frozen['meshes'] if m['id'] in ('furn-study-desk-0','furn-study-desk-1')]
        for travel in (.005,.005001):
            scene=dict(meshes=deepcopy(originals),mounting_hosts={},mounting_movements=[])
            floor=deepcopy(next(m for m in frozen['meshes'] if m['id']=='floor-study-game'))
            # Translation and renaming prove that neither IDs nor coordinates
            # provide an exemption; support is measured from the actual floor.
            for m in scene['meshes']+[floor]:
                m['id']='other-'+m['id']
                for f in m['faces']:
                    for p in f: p[0]+=7;p[1]+=4
            for f in floor['faces']:
                for p in f:p[2]=travel
            scene['meshes'].append(floor)
            members=scene['meshes'][:2]
            host=nearest(scene,[11,-21,0],(0,0,1),[floor],'unrelated-floor','floor')
            floor_assembly(scene,members,host,'unrelated')
            if travel>.005:
                self.assertTrue(all(r['approval']=='PENDING' for r in scene['mounting_movements']))
                self.assertTrue(scene_findings(scene));continue
            self.assertEqual(scene_findings(scene),[])
            child=members[0]
            mutant=deepcopy(scene)
            mutant['meshes']=[m for m in mutant['meshes'] if m['id']!=members[1]['id']]
            self.assertTrue(any('independent floor-bearing' in f for f in scene_findings(mutant)))
            mutant=deepcopy(scene)
            target=next(m for m in mutant['meshes'] if m['id']==child['id'])
            for f in target['faces']:
                for p in f:p[2]+=.01
            mutant=deepcopy(scene)
            mutant['diagnostic_meshes']=[m for m in mutant.get('diagnostic_meshes',[]) if not m.get('finished_host_id')]
            mutant['meshes']=[m for m in mutant['meshes'] if not m.get('finished_host_id')]
            self.assertTrue(any('finite host coverage' in f for f in scene_findings(mutant)))

    def test_wc_slides_full_tables_and_family_geometry_retained(self):
        from archpipe.concept.mounting_clearances import review
        scene=self.scene
        decisions={d['id']:d for d in scene['wc_slide_decisions']}
        self.assertAlmostEqual(decisions['gwc-wc']['delta'][0]*1000,-100.490138306)
        self.assertAlmostEqual(decisions['pe-wc']['delta'][1]*1000,40)
        report=review(scene)
        self.assertTrue(all(r['room']=='family-bath' for r in report['failures']))
        self.assertEqual(len(report['failures']),3)
        self.assertEqual(report['unresolved'],[])
        self.assertTrue(all(r['status'] in ('PASS','CONSTRUCTION REQUIREMENT') for r in report['rows'] if r['room']!='family-bath'))
        old=json.loads((Path(__file__).parent/'fixtures/c4-e-before.json').read_text())
        # Shell ordinal IDs vary when doors open for a different view set;
        # stable authored fixtures/floors identify the unchanged family case.
        before={m['id']:m for m in old['family_meshes'] if not m['id'].startswith('shell-')}
        for m in scene['meshes']:
            if m['id'] in before:self.assertEqual(m['faces'],before[m['id']]['faces'])
        # Narrow room has no continuous interval, so no search step hides a
        # result; translated unrelated room retains the same feasible slide.
        item=dict(cx=2,cy=2,rot=180,w=.4,d=.55)
        self.assertEqual(continuous_candidates(item,[],[1.5,0,2.5,4])[1],[])
        axis,candidates=continuous_candidates(item,[],[0,0,4,4]);self.assertEqual(axis,0);self.assertIn(0,candidates)

    def test_joinery_recess_lights_and_support_siblings_fail_closed(self):
        scene=self.scene
        trim=next(m for m in scene['meshes'] if m['id']=='fix-DLN-bar-alcove-11')
        host=scene['mounting_hosts'][trim['mounting']['host_id']]
        self.assertEqual(host['kind'],'joinery-panel');self.assertEqual(host['source_mesh'],'furn-library-daybed-0')
        self.assertEqual(host['void_status'],'requirement');self.assertAlmostEqual(host['void_depth_m'],.120)
        for mid in ('fix-DLN-bar-alcove-11','fix-DLN-bar-alcove-12'):
            mutant=deepcopy(scene);m=next(m for m in mutant['meshes'] if m['id']==mid)
            mutant['mounting_hosts'][m['mounting']['host_id']]['void_depth_m']=.09
            self.assertTrue(any('void' in f for f in scene_findings(mutant) if f.startswith(mid+':')))
        rail=next(m for m in scene['meshes'] if m.get('mounting',{}).get('support_parts'))
        mutant=deepcopy(scene);support_id=rail['mounting']['support_parts'][0]
        mutant['meshes']=[m for m in mutant['meshes'] if m['id']!=support_id]
        self.assertTrue(any('MISSING declared supporting part' in f for f in scene_findings(mutant)))
        self.assertEqual(len(scene['support_light_movements']),7)
        self.assertTrue(scene['support_associated_movements'])
        self.assertEqual(len(scene['e_approved_light_movements']),8)
        self.assertEqual(len(scene['e_approved_associated_movements']),7)
        meshes={m['id']:m for m in scene['meshes']}
        for record in scene['e_approved_associated_movements']:
            self.assertEqual(meshes[record['id']]['faces'],record['new_faces'])
            for before,after in zip(record['old_faces'],record['new_faces']):
                for a,b in zip(before,after):
                    for axis in range(3):self.assertAlmostEqual(b[axis]-a[axis],record['delta'][axis])
        lights={l['id']:l for l in scene['lights']}
        for record in scene['e_approved_light_movements']:
            self.assertEqual(lights[record['id']]['position'],record['new'])
            for axis in range(3):self.assertAlmostEqual(record['new'][axis]-record['old'][axis],record['delta'][axis])
        for mid in ('appliance-coffee-main-drip-tray','appliance-coffee-dirty-drip-tray'):
            self.assertIn(mid+': associated assembly body penetrates support face 12.000 mm',scene_findings(scene))
            mutant=deepcopy(scene);child=next(m for m in mutant['meshes'] if m['id']==mid)
            child['id']='unrelated-appliance-child'
            for f in child['faces']:
                for p in f:p[2]+=.012
            self.assertFalse(any(f.startswith(child['id']+': associated assembly body penetrates') for f in scene_findings(mutant)))
            self.assertIn(child['id']+': attached assembly split movement', scene_findings(mutant))
            for f in child['faces']:
                for p in f:p[2]-=.020
            self.assertTrue(any(f.startswith(child['id']+': associated assembly body penetrates') for f in scene_findings(mutant)))

    def test_actual_boundary_mismatch_stays_pending_and_full_span_edges_generalise(self):
        frozen=json.loads((Path(__file__).parent/'fixtures/c4-e-before.json').read_text())
        before={m['id']:m for m in frozen['trellis_meshes']}
        for m in self.scene['meshes']:
            if m['id'].startswith(('landscape-trellis-','landscape-climber')):
                self.assertEqual(m['faces'],before[m['id']]['faces'])
                host=self.scene['mounting_hosts'][m['mounting']['host_id']]
                source=next(mm for mm in self.scene['meshes'] if mm['id']==host['source_mesh'])
                self.assertTrue(source['id'].startswith('yard-boundary-edge-'))
                self.assertLessEqual(host['maximum_authored_travel_m'],.300)
                self.assertEqual(m['mounting']['approval'],'PENDING')
        south=next(r for r in self.scene['mounting_movements'] if r['id']=='landscape-trellis-south')
        self.assertAlmostEqual(south['mm'],135.66)
        for travel in (0,8):
            members=deepcopy(frozen['pantry_meshes'][:1]);floor=deepcopy(frozen['pantry_meshes'][1])
            for m in members+[floor]:
                m['id']='translated-'+m['id']
                for f in m['faces']:
                    for p in f:p[0]+=travel;p[1]-=travel
            scene=dict(meshes=members+[floor],mounting_hosts={},mounting_movements=[])
            bb=bounds(members[0]);host=nearest(scene,[(bb[0]+bb[3])/2,(bb[1]+bb[4])/2,bb[2]],
                (0,0,1),[floor],'other-floor','floor')
            # Original real footprint is outside by 0.5 mm; merely raising it
            # to the floor would still fail finite coverage.
            floor_assembly(scene,members,host,'other')
            self.assertAlmostEqual(scene['mounting_movements'][0]['new'][1]-bb[1],-.0005)
            self.assertEqual(scene_findings(scene),[])


if __name__=='__main__':unittest.main()
