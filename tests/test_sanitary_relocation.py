"""Frozen west-wall collision, rigid wall changes and current native intent."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from archpipe.concept import villa_render as VR, villa_r11 as R, villa_furnish as F, villa_furnish3d as F3, revit_spec as RS
from archpipe.concept.mounting_clearances import review, measured_items, front_distance, wc_side_clearances
from archpipe.concept.sanitary_relocation import relocate, input_revision
from archpipe.concept.mounting import Host, Finish, check_mesh, scene_findings
from archpipe.concept.fitting_mounting import bounds


class SanitaryRelocation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scene=VR.build(views=[])
        cls.lay=R.design('D1')
        cls.frozen=json.loads(Path('tests/fixtures/c4-family-west-before.json').read_text())

    def test_frozen_full_zone_fires_clean_current_quiet_and_wrong_pose_fires(self):
        broken=deepcopy(self.scene)
        originals={m['id']:m for m in self.frozen['meshes']}
        broken['meshes']=[deepcopy(originals.get(m['id'],m)) for m in broken['meshes']]
        broken['sanitary_placements']={}
        failures={r['check']:r for r in review(broken)['failures']}
        self.assertEqual(failures['fb-basin front approach']['achieved_mm'],0)
        self.assertEqual(failures['fb-wc centreline side 350']['achieved_mm'],197)
        self.assertEqual(failures['fb-wc centreline side 1000']['achieved_mm'],200)
        report=review(self.scene)
        self.assertEqual(report['failures'],[])
        self.assertEqual(scene_findings(self.scene),[])
        rows={r['check']:r for r in report['rows'] if r['room']=='family-bath'}
        self.assertEqual(rows['fb-wc front approach']['achieved_mm'],1104)
        self.assertEqual(rows['fb-basin front approach']['achieved_mm'],1104)
        self.assertEqual(rows['fb-wc centreline side 350']['achieved_mm'],478.5)
        self.assertEqual(rows['fb-wc centreline side 1000']['achieved_mm'],1128.5)
        self.assertEqual(rows['shower entry clear-floor width']['achieved_mm'],1630)
        mutant=deepcopy(self.scene)
        for mesh in mutant['meshes']:
            if mesh['id'].startswith('furn-fb-wc-'):
                for face in mesh['faces']:
                    for point in face: point[1]-=.3
        mutant['sanitary_placements']['fb-wc']['cy']-=.3
        self.assertTrue(any(r['check']=='fb-wc centreline side 350' for r in review(mutant)['failures']))

    def test_rigid_members_and_reverse_host_generalise(self):
        # Real pan and flush plate; renamed/translated siblings retain the same proof.
        wc=next(i for i in self.frozen['items'] if i['id']=='fb-wc')
        wc=dict(wc,cx=9.575,cy=-26.101)
        for travel in (0,7):
            meshes=deepcopy(self.frozen['meshes']);item=dict(wc,id='other-wc',cx=wc['cx']+travel)
            for m in meshes:
                m['id']=m['id'].replace('fb-wc','other-wc')
                m['mounting']['assembly_root']='furn-other-wc-0'
                for f in m['faces']:
                    for p in f: p[0]+=travel
            s=dict(meshes=meshes,mounting_movements=[])
            host=Host('unrelated-east','wall',(11.427+travel,0,0),(-1,0,0),Finish('marble',.023))
            before=deepcopy(meshes)
            relocate(s,item,host,[11.129+travel,-25.8195],90)
            for old,new in zip(before,meshes):
                self.assertEqual(check_mesh(new,{host.id:host}),[])
                for a,b in zip([p for f in old['faces'] for p in f],[p for f in new['faces'] for p in f]):
                    self.assertAlmostEqual(b[0],11.129+travel-(a[0]-item['cx']))
                    self.assertAlmostEqual(b[1],-25.8195-(a[1]-item['cy']))
                    self.assertEqual(a[2],b[2])
            mutant=deepcopy(meshes[1])
            for f in mutant['faces']:
                for p in f:p[0]-=.01
            self.assertTrue(check_mesh(mutant,{host.id:host}))
            from archpipe.concept.attached_assembly import findings
            self.assertEqual(findings(s),[])
            for f in meshes[1]['faces']:
                for p in f:p[1]+=.01
            self.assertTrue(findings(s))

    def test_current_layout_native_parts_and_drainage_note_match_measured_scene(self):
        current=next(i for i in F.layout(self.lay) if i['id']=='fb-wc')
        measured=next(i for i in measured_items(self.scene,self.lay) if i['id']=='fb-wc')
        for key in ('cx','cy','rot'):self.assertAlmostEqual(current[key],measured[key])
        sp=RS.build(self.lay)
        self.assertEqual(sp['sanitary_placements']['fb-wc']['drainage_note'],'services coordination pending')
        parts=next(i for i in F3.spec(self.lay) if i['mark']=='fb-wc')
        self.assertEqual(parts['parts'],['pan','seat','flush-plate'])
        meshes=[m for m in self.scene['meshes'] if m['id'].startswith('furn-fb-wc-')]
        body=parts['boxes'][:2]
        boxes=[[min(b[i] for b in body) for i in range(3)]+[max(b[i] for b in body) for i in range(3,6)],parts['boxes'][2]]
        for box,mesh in zip(boxes,meshes):
            for wanted,actual in zip(box,bounds(mesh)):self.assertAlmostEqual(wanted,actual)
        with input_revision(True):
            historical=next(i for i in F.layout(self.lay) if i['id']=='fb-wc')
        self.assertEqual(historical['rot'],-90)
        self.assertEqual(current['rot'],90)

    def test_support_finish_layers_remain_and_wc_view_has_measured_subject(self):
        from archpipe.concept import render_support
        from archpipe.concept.finish_layers import surface_findings,solid_findings
        self.assertEqual(render_support.unsupported(self.scene),[])
        self.assertEqual(surface_findings(self.scene),[])
        self.assertEqual(solid_findings(self.scene),[])
        view=next(v for v in VR.VIEWS(self.lay) if v['id']=='v35-family-bath-wc')
        self.assertEqual(view['subjects'],['fb-wc'])
        self.assertEqual(view['camera']['home_room'],'family-bath')


if __name__=='__main__':unittest.main()
