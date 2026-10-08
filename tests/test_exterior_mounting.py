from archpipe.orientation import historical_aliases
"""Frozen rejected real hosts, distance/coverage mutations and side siblings."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from archpipe.concept.exterior_mounting import finite_face, yard_sources, exterior_host, mount_landscape
from archpipe.concept.fitting_mounting import bounds
from archpipe.concept.mounting import scene_findings
from archpipe.concept import villa_r11 as R


class ExteriorMounting(unittest.TestCase):
    def setUp(self):
        self.frozen=historical_aliases(json.loads((Path(__file__).parent/'fixtures/c4-e-rejected-hosts.json').read_text()))
        self.scene=dict(meshes=deepcopy(self.frozen['meshes']),mounting_hosts={},mounting_movements=[])

    def test_explicit_boundary_side_is_independent_of_garden_name(self):
        source=next(m for m in self.scene['meshes'] if m['id']=='landscape-trellis-east')
        sources=yard_sources(self.scene)
        renamed=deepcopy(source);renamed['id']='landscape-g6-loquat-wires'
        mount_landscape(self.scene,renamed,sources,model_side='+y')
        host=self.scene['mounting_hosts'][renamed['mounting']['host_id']]
        self.assertEqual(list(host['normal']),[0,-1,0])
        wrong=deepcopy(source);wrong['id']='another-yard-training-wires'
        with self.assertRaisesRegex(ValueError,'refused host'):
            mount_landscape(self.scene,wrong,sources,model_side='-y')

    def test_real_south_remote_rejected_boundary_resolves_and_translates(self):
        south=next(m for m in self.scene['meshes'] if m['id']=='landscape-trellis-west')
        wrong=next(m for m in self.scene['meshes'] if m.get('source_id')=='fence-west')
        self.assertAlmostEqual(next(r['mm'] for r in self.frozen['rows'] if r['id']==south['id']),9450.32)
        with self.assertRaisesRegex(ValueError,'refused host'):
            finite_face(south,[wrong],(0,1,0))
        sources=yard_sources(self.scene)
        for member in list(self.scene['meshes']):
            if member['id'].startswith('landscape-'):mount_landscape(self.scene,member,sources)
        rows=self.scene['mounting_movements']
        self.assertEqual(len(rows),12)
        self.assertTrue(all(5<r['mm']<=300 for r in rows))
        self.assertAlmostEqual(next(r['mm'] for r in rows if r['id']==south['id']),135.66)
        for travel in (0,17):
            source=deepcopy(next(s for s,h in sources if s['id']=='yard-boundary-edge-5'))
            member=deepcopy(south)
            for mesh in (source,member):
                mesh['id']='unrelated-'+mesh['id']
                for f in mesh['faces']:
                    for p in f:p[0]+=travel;p[1]-=travel
            self.assertEqual(finite_face(member,[source],(0,1,0))[0]['id'],source['id'])
            for f in source['faces']:
                for p in f:p[1]-=1
            with self.assertRaisesRegex(ValueError,'300 mm'):finite_face(member,[source],(0,1,0))

    def test_full_footprint_required_not_anchor_or_infinite_extension(self):
        sources=yard_sources(self.scene)
        source=deepcopy(next(s for s,h in sources if s['id']=='yard-boundary-edge-5'))
        member=next(m for m in self.scene['meshes'] if m['id']=='landscape-trellis-west')
        self.assertTrue(finite_face(member,[source],(0,1,0)))
        centre=(bounds(member)[0]+bounds(member)[3])/2
        for f in source['faces']:
            for p in f:p[0]=centre+(.1 if p[0]>centre else -.1)
        with self.assertRaisesRegex(ValueError,'finite fixing envelope'):finite_face(member,[source],(0,1,0))
        # A notched wall has all four item corners inside its outer envelope,
        # yet cannot support the whole fixing footprint.
        wall=dict(id='notched',faces=[[[x,0,z] for x,z in [(0,0),(4,0),(4,4),(3,4),(3,1),(1,1),(1,4),(0,4)]]])
        wall['faces'][0].reverse()
        body=dict(id='unrelated-fixing',faces=[[[x,.1,z] for x,z in [(.5,.5),(3.5,.5),(3.5,3.5),(.5,3.5)]]])
        from archpipe.concept.mounting import _on_polygon
        self.assertTrue(all(_on_polygon([p[0],0,p[2]],wall['faces'][0],(0,1,0)) for p in body['faces'][0]))
        with self.assertRaisesRegex(ValueError,'finite fixing envelope'):finite_face(body,[wall],(0,1,0))

    def test_external_grilles_choose_outdoor_side_and_reject_interior_only(self):
        lay=R.design('D1')
        for room in ('guest-wc','dirty-kitchen'):
            member=next(m for m in self.scene['meshes'] if m['id']=='detail-vent-'+room+'-grille')
            host=exterior_host(self.scene,member,lay,'external-'+room)
            self.assertEqual(host.normal,(0,1,0))
            self.assertAlmostEqual(host.structural_point[1],-20.601)
            record=self.scene['mounting_hosts'][host.id]
            self.assertIn(room,record['interior_rooms']);self.assertEqual(record['outdoor_rooms'],[])
            self.assertEqual(host.finish.thickness_m,0)
            self.assertAlmostEqual(host.structural_point[1]-bounds(member)[1],.012)
        mutant=deepcopy(self.scene)
        mutant['meshes']=[m for m in mutant['meshes'] if m['material']!='paint-exterior-grey-green']
        with self.assertRaisesRegex(ValueError,'adjacency'):exterior_host(mutant,member,lay,'no-exterior')
        # A newly adjacent room on the outward side makes this an internal wall.
        other=deepcopy(lay);other['rooms']['outdoor-now-room']=dict(other['rooms'][room],rect=[13,-20.60,14.5,-19.5])
        with self.assertRaisesRegex(ValueError,'adjacency'):exterior_host(self.scene,member,other,'internal-now')
        # Shift and rename every room and mesh; exterior selection remains
        # geometric and adjacency-based, with no villa-specific identifier.
        shifted=deepcopy(self.scene);layout=deepcopy(lay)
        for m in shifted['meshes']:
            m['id']='other-'+m['id']
            if m.get('room'):m['room']='other-'+m['room']
            for f in m['faces']:
                for p in f:p[0]+=7;p[1]+=5
        layout['rooms']={'other-'+rid:dict(r,rect=[r['rect'][0]+7,r['rect'][1]+5,r['rect'][2]+7,r['rect'][3]+5]) for rid,r in lay['rooms'].items()}
        target=next(m for m in shifted['meshes'] if m['id']=='other-'+member['id'])
        self.assertEqual(exterior_host(shifted,target,layout,'unrelated-external').normal,(0,1,0))

    def test_approval_drift_refuses_and_unapproved_geometry_is_retained(self):
        from archpipe.concept.exterior_mounting import apply_lead_review
        authority=json.loads(Path('knowledge/c4-e-lead-approvals.json').read_text())
        self.assertEqual(len(authority['rows']),45);self.assertEqual(len(authority['rejected']),14)
        approved=deepcopy(authority['rows'][0]);approved['new'][0]+=.01
        scene=dict(meshes=[dict(id=approved['id'],faces=[],mounting={})],mounting_movements=[approved],mounting_hosts={})
        with self.assertRaisesRegex(ValueError,'schedule drift'):apply_lead_review(scene)

    def test_geometry_diff_compares_coordinates_not_container_types(self):
        import sys
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
        from checkpoint_mounting_e import geometry_diff
        before=dict(meshes=[dict(id='independent-floor',room='family-bath',faces=[[[0,0,0],[1,0,0],[1,1,0]]])],views=[])
        after=deepcopy(before);after['meshes'][0]['faces']=[[(0,0,0),(1,0,0),(1,1,0)]]
        self.assertEqual(geometry_diff(after,before)['changed_original_meshes'],[])
        after['meshes'][0]['faces'][0][0]=(0,0,.005)
        self.assertEqual(geometry_diff(after,before)['changed_family_meshes'],['independent-floor'])
