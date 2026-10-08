"""C8: real historical values, current clean controls and renamed/shifted siblings.

No failure fixture imports current design constants. Historical complete inputs
are compressed frozen JSON; measurement-only evidence is explicitly separated.
"""
import copy
from dataclasses import FrozenInstanceError
import gzip
import importlib.util
import json
from pathlib import Path
import unittest

import numpy as np
from archpipe.geometry_topology import (
    GeometryTopology as Topology, Host, Obstacle, Opening, Route, Requirement,
    bounds_of, landscape_route_findings, pitch_headroom_findings,
)
from archpipe.concept import villa_r11 as R, villa_furnish as F, revit_spec as RS
from archpipe.concept import villa as V, villa_landscape as L, stairs as S
from archpipe.units import mm_to_m

FIXTURES = Path(__file__).parent/'fixtures'
MEASURED = json.loads((FIXTURES/'c8-measured-lessons.json').read_text())


def historical(name):
    with gzip.open(FIXTURES/('c8-'+name+'.json.gz'), 'rt') as stream:
        return json.load(stream)['payload']


def scene_shift(scene, delta=(8, 11, 1)):
    """Translate every actual face and prop; replace all identities consistently."""
    result = copy.deepcopy(scene)
    for mesh in result['meshes']:
        mesh['id'] = 'sibling-'+mesh['id']
        mesh['faces'] = [[[p[i]+delta[i] for i in range(3)] for p in face] for face in mesh['faces']]
    for prop in result.get('props', ()):
        prop['id'] = 'sibling-'+prop['id']
        prop['position'] = [prop['position'][i]+delta[i] for i in range(3)]
    return result


def layout_shift(layout, delta=(8,11), rename=True):
    result = copy.deepcopy(layout)
    mapping = {name: 'sibling-'+name if rename else name for name in result['rooms']}
    for room in result['rooms'].values():
        rect=room['rect']
        room['rect']=[rect[0]+delta[0],rect[1]+delta[1],rect[2]+delta[0],rect[3]+delta[1]]
        room['ends']=[[axis,line+delta[1 if axis=='h' else 0],low+delta[0 if axis=='h' else 1],high+delta[0 if axis=='h' else 1]] for axis,line,low,high in room.get('ends',())]
    result['rooms']={mapping[name]:room for name,room in result['rooms'].items()}
    return result


class RecordsAndQueries(unittest.TestCase):
    def test_snapshot_is_read_only_and_unknown_obstacles_survive(self):
        item=dict(id='unknown-chair',kind='unmapped',rect=(1,1,2,2),bottom_m=0,top_m=.9)
        topology=Topology.from_inputs(items=[item],routes={'route':(1,0,2,3)},route_ground={'route':0})
        item['rect']=(8,8,9,9)
        self.assertEqual(len(topology.obstacles),1)
        self.assertEqual(topology.object_in_route()[0].source_id,'unknown-chair')
        with self.assertRaises(FrozenInstanceError):
            topology.obstacles[0].kind='dropped'
        with self.assertRaises(TypeError):
            topology.obstacles[0].record['rect']=(0,0,0,0)
        self.assertEqual(topology.object_in_route()[0].required,0)

    def test_l0013_native_unmapped_chair_is_still_a_measured_obstacle(self):
        native=json.loads((FIXTURES/'bedroom-from-revit.json').read_text())
        from archpipe.from_extract import convert
        from archpipe.rules import _furniture_poly
        project=convert(native).project
        chair=next(f for f in project.furniture if f.id=='FN-CHR')
        rect=tuple(mm_to_m(v) for v in _furniture_poly(chair).bounds)
        item=dict(id=chair.id,rect=rect,bottom_m=0,top_m=1)
        requirement=Requirement(0,'native measured footprint remains an obstacle even without an access catalogue entry')
        for shift in ((0,0),(8,11)):
            x,y=shift; shifted=(rect[0]+x,rect[1]+y,rect[2]+x,rect[3]+y)
            topology=Topology.from_inputs(items=[dict(item,id='renamed-unknown',rect=shifted)])
            self.assertTrue(topology.access_zone_findings('unrelated-piece',shifted,requirement))
            clear=(shifted[0]+2,shifted[1]+2,shifted[2]+2,shifted[3]+2)
            self.assertEqual(topology.access_zone_findings('unrelated-piece',clear,requirement),[])

    def test_accessories_only_exempt_parent_access_never_body_or_unrelated_route(self):
        # Frozen native bedroom supplies actual measured desk/chair sizes.
        data=json.loads((FIXTURES/'bedroom-from-revit.json').read_text())
        from archpipe.from_extract import convert
        project=convert(data).project
        from archpipe.rules import _furniture_poly
        # Use authoritative native-footprint function, then one unit boundary.
        objects=[]
        for item in project.furniture:
            rect=_furniture_poly(item).bounds
            objects.append(dict(id=item.id,rect=[mm_to_m(v) for v in rect],bottom_m=0,top_m=1,
                                accessory_to=item.accessory_to))
        topology=Topology.from_inputs(items=objects)
        desk=next(o for o in topology.obstacles if o.source_id=='FN-DSK')
        chair=next(o for o in topology.obstacles if o.source_id=='FN-CHR')
        self.assertEqual(chair.accessory_to,'FN-DSK')
        bb=chair.bounds;zone=(bb[0],bb[1],bb[3],bb[4])
        requirement=Requirement(0,'Explicit native accessory_to parent access intent')
        self.assertFalse(any(f.source_id=='FN-CHR' for f in topology.access_zone_findings('FN-DSK',zone,requirement)))
        self.assertTrue(any(f.source_id=='FN-CHR' for f in topology.access_zone_findings('other-desk',zone,requirement)))
        # Physical collision cannot be exempted by accessory intent.
        overlapping=dict(id='chair-in-desk',rect=(desk.bounds[0],desk.bounds[1],desk.bounds[3],desk.bounds[4]),bottom_m=0,top_m=1,accessory_to='FN-DSK')
        actual=dict(id='FN-DSK',rect=overlapping['rect'],bottom_m=0,top_m=1)
        self.assertTrue(Topology.from_inputs(items=[actual,overlapping]).object_overlaps())
        self.assertTrue(Topology.from_inputs(items=[dict(overlapping,id='renamed-chair')],routes={'unrelated':actual['rect']},route_ground={'unrelated':0}).object_in_route())

    def test_exact_walking_triangles_and_legacy_numeric_policy_match_frozen_algorithm(self):
        spec=importlib.util.spec_from_file_location('c8_route_before',FIXTURES/'c8-route-before.py')
        old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
        # Unknown pieces, rect height boundaries, actual old props and a canopy
        # with no low geometry; order and messages must be identical.
        history=historical('round2-render')
        from archpipe.asset_route_record import read_record
        covered=read_record()['assets']
        props=[p for p in history['props'] if p['asset'] in covered]
        cases=[[],[MEASURED['l0834']],props,
               [dict(id='boundary',rect=(1,1,2,2),bottom_m=2,top_m=3)],
               [dict(id='canopy-only',faces=[[[1,1,3],[2,1,3],[1,2,3]]])],
               [dict(id='low-branch',faces=[[[1,1,1],[2,1,1],[1,2,1]]])]]
        for items in cases:
            for routes,ground in ((L.PATHS,None),({'other-route':(0,0,3,3)},{'other-route':0})):
                with self.subTest(items=len(items),routes=len(routes)):
                    self.assertEqual(L.route_violations(items,routes,ground),old.route_violations(items,routes,ground))
        missing=next(p for p in history['props'] if p['asset'] not in covered)
        for function in (L.route_violations,old.route_violations):
            with self.assertRaisesRegex(ValueError,'tracked route geometry'):
                function([missing],{'far':(100,100,101,101)})
        # A declared rect used by legacy callers takes precedence over faces.
        item=dict(id='declared-rect',rect=(5,5,6,6),faces=[[[1,1,1],[2,1,1],[1,2,1]]])
        self.assertEqual(L.route_violations([item],{'a':(0,0,3,3)},{'a':0}),[])

    def test_tilt_and_unknown_asset_fail_closed(self):
        item=copy.deepcopy(next(p for p in historical('round2-render')['props'] if p['asset']=='jacaranda_tree'))
        item['rotation_deg']=[10,0,0]
        with self.assertRaisesRegex(ValueError,'tilted'):
            landscape_route_findings([item],{'far':(100,100,101,101)})
        with self.assertRaises(KeyError):
            Topology.from_inputs(items=[dict(item,asset='unmeasured-asset')])
        with self.assertRaisesRegex(ValueError,'finite'):
            bounds_of([[[float('nan'),0,0],[1,0,0],[0,1,0]]])

    def test_swing_real_frozen_seat_envelope_clean_sibling_and_other_storey(self):
        before=json.loads((FIXTURES/'garden-g1-before.json').read_text())
        seat=next(p for p in before['props'] if p['asset']=='sf_egg_chair')
        x0,y0,x1,y1=L._rect(seat)
        # Existing real regression chair placed in the 0.25 m ASSUMED motion
        # allowance, not a new ergonomic threshold. Missing source stays open.
        for shift in ((0,0),(8,11)):
            x,y=shift
            envelope=(x0-.25+x,y0-.25+y,x1+.25+x,y1+.25+y)
            obstacle=Obstacle('another-chair','chair',(x1+.05+x,y0+y,-3,x1+.25+x,y1+y,-2))
            opening=Opening('renamed-seat','swing',(envelope,),(),x1-x0,(),'B','ASSUMED 0.25 m original villa_landscape.swing_violations allowance',-3,-2)
            topology=Topology(openings=(opening,),obstacles=(obstacle,))
            finding=topology.swing_envelope_vs_obstacle()[0]
            self.assertEqual(finding.status,'needs-source');self.assertGreater(finding.achieved,0)
            above=Obstacle('upper-floor-chair','chair',(obstacle.bounds[0],obstacle.bounds[1],0,obstacle.bounds[3],obstacle.bounds[4],1))
            self.assertEqual(Topology(openings=(opening,),obstacles=(above,)).swing_envelope_vs_obstacle(),[])
            self.assertEqual(Topology(openings=(opening,)).swing_envelope_vs_obstacle(),[])

    def test_finished_faces_finite_coverage_and_support_identity(self):
        wall=[[0,0,0],[2,0,0],[2,0,3],[0,0,3]]
        item=dict(id='rail',group='fixture',material='metal',faces=[[[.5,-.04,1],[1.5,-.04,1],[1.5,-.03,1.1],[.5,-.03,1.1]]],mounting=dict(host_id='wall',kind='wall-hung',offset_m=0))
        scene=dict(mounting_hosts={'wall':dict(id='wall',kind='wall',normal=[0,1,0],finish={'thickness_m':.013},source_faces=[wall],source_mesh='wall-source')},meshes=[item])
        model=Topology.from_inputs(scene=scene)
        self.assertEqual(model.hosts[0].finished_faces[0][0][1],.013)
        self.assertTrue(model.supports[0].contact)
        self.assertAlmostEqual(model.object_penetrating_host()[0].achieved,-.053)
        self.assertEqual(model.element_against_wrong_host('rail','wall'),[])
        self.assertEqual(model.element_against_wrong_host('rail','another-wall')[0].achieved,0)
        # A remote point behind an infinite plane is outside this finite wall.
        scene['meshes'][0]['faces']=[[[8,-.04,1],[9,-.04,1],[9,-.03,1.1],[8,-.03,1.1]]]
        self.assertEqual(Topology.from_inputs(scene=scene).object_penetrating_host(),[])

    def test_diagnostic_host_faces_are_already_finished_and_infinite_planes_refuse(self):
        for delta in ((0,0,0),(9,10,4)):
            x,y,z=delta
            face=[[x,.013+y,z],[2+x,.013+y,z],[2+x,.013+y,3+z],[x,.013+y,3+z]]
            host=dict(id='other-wall',kind='wall',normal=[0,1,0],structural_point=[x,y,z],finish={'thickness_m':.013})
            scene=dict(mounting_hosts={'other-wall':host},meshes=[],diagnostic_meshes=[dict(id='finite-face',finished_host_id='other-wall',faces=[face])])
            topology=Topology.from_inputs(scene=scene)
            self.assertEqual(topology.hosts[0].finished_faces[0],tuple(tuple(p) for p in face))
            scene['diagnostic_meshes']=[]
            with self.assertRaisesRegex(ValueError,'finite finished host'):
                Topology.from_inputs(scene=scene)

    def test_missing_numeric_source_is_reported_without_threshold(self):
        finding=Topology().clearance_from_fixed_reference('plant','window',.3,Requirement(None,'No held plant/window access figure',needs_source=True))[0]
        self.assertEqual(finding.status,'needs-source');self.assertIsNone(finding.required)
        scene=Topology(openings=(Opening('w','window',(),(),1,('room',),'GF','Window envelope absent: needs-source'),))
        self.assertEqual(scene.needs_source_findings()[0].status,'needs-source')


class HistoricalRelationships(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layout=R.design('D1');cls.specification=RS.build(cls.layout);cls.furniture=F.layout(cls.layout)
        cls.clean=Topology.from_inputs(layout=cls.layout,specification=cls.specification,furniture=cls.furniture)

    def test_l0200_measured_bath_edge_fragment_clean_and_translated_sibling(self):
        old=json.loads((FIXTURES/'c8-bath-v1-fragment.json').read_text())
        self.assertTrue(any(f.query=='unbuilt-link' for f in Topology.from_inputs(layout=old).room_connectivity()))
        self.assertTrue(any(f.query=='room-reachability' for f in Topology.from_inputs(layout=old).room_connectivity()))
        clean=copy.deepcopy(old);clean['rooms']['bath']['rect'][2]=1.8
        self.assertEqual(Topology.from_inputs(layout=clean).room_connectivity(),[])
        sibling=layout_shift(old)
        sibling['links']=[['sibling-corridor','sibling-bath']];sibling['entrance']='sibling-corridor'
        self.assertTrue(Topology.from_inputs(layout=sibling).room_connectivity())

    def test_route_body_is_ast_identical_to_starting_commit(self):
        # Tests the frozen former raster, rather than mirroring new wrappers.
        import ast
        source=(FIXTURES/'c8-furnished-route-before.py').read_text()
        before=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='route_problems')
        current=Path(F.__file__).read_text()
        after=next(n for n in ast.parse(current).body if isinstance(n,ast.FunctionDef) and n.name=='_route_problems')
        after.name='route_problems'
        self.assertEqual(ast.dump(before,include_attributes=False),ast.dump(after,include_attributes=False))

    def test_other_villa_options_stair_relationships_use_their_inputs(self):
        for design in ('D1','D2','D3'):
            layout=R.design(design)
            self.assertEqual(Topology.from_inputs(layout=layout).stair_end_access(),[])
        # Related defect at a different end in a different option.
        other=R.design('D3');other['rooms']['stair-gf']['ends']=[]
        self.assertTrue(Topology.from_inputs(layout=other).stair_end_access())

    def test_l0307_l0310_l0319_real_round2_stair_missing_ends_and_shifted_sibling(self):
        old=historical('round2')
        self.assertEqual({f.source_id for f in Topology.from_inputs(layout=old).stair_end_access()},{'stair-b','stair-gf'})
        self.assertEqual(self.clean.stair_end_access(),[])
        sibling=layout_shift(old)
        self.assertEqual(len(Topology.from_inputs(layout=sibling).stair_end_access()),2)
        # Ends explicitly placed on the historic straight flight's street edge:
        # derive from its real rectangle, retaining the actual circulation rooms.
        stair=old['rooms']['stair-b'];x0,y0,x1,y1=stair['rect']
        stair['ends']=[['v',x0,y0,y1]]
        findings=Topology.from_inputs(layout=old).stair_end_access()
        self.assertTrue(any(f.source_id=='stair-b' and f.achieved==0 and f.unit=='circulation neighbours' for f in findings))
        self.assertTrue(Topology.from_inputs(layout=layout_shift(old)).stair_end_access())

    def test_l0504_real_pitch_headroom_clean_and_translated_host_sibling(self):
        old=MEASURED['l0504'];stair=json.loads((FIXTURES/'c8-pitch-line-stair.json').read_text())['payload']
        found=pitch_headroom_findings(stair,old['opening_mm'])
        self.assertAlmostEqual(found[0].achieved,1.824,delta=.005)
        self.assertEqual(found[0].required,2)
        clean=[v*1000 for v in self.specification['gf_opening']]
        self.assertEqual(pitch_headroom_findings(stair,clean),[])
        # Same real limiting pitch-line sample and real -0.30 m soffit, with
        # all geometry translated (including vertical datum), not just ids.
        achieved,x=S.pitch_headroom(stair,old['opening_mm']);p=stair['pitch_line']
        ratio=(x-p['x_low'])/(p['x_high']-p['x_low']);z=p['z_low']+ratio*(p['z_high']-p['z_low'])
        floor=(mm_to_m(x),mm_to_m((p['y0']+p['y1'])/2),mm_to_m(z))
        for shift in ((0,0,0),(10,17,4)):
            sx,sy,sz=shift;xx,yy,zz=floor
            face=((xx-.01+sx,yy-.01+sy,-.3+sz),(xx+.01+sx,yy-.01+sy,-.3+sz),(xx+.01+sx,yy+.01+sy,-.3+sz),(xx-.01+sx,yy+.01+sy,-.3+sz))
            host=Host('translated-slab','slab',(face,),bounds_of([face]))
            result=Topology(hosts=(host,)).headroom('renamed-flight',[(xx+sx,yy+sy,zz+sz)],Requirement.card('ukadk-stair-headroom-min'))
            self.assertAlmostEqual(result[0].achieved,found[0].achieved)

    def test_l0512_frozen_round8_hall_geometry_clean_and_translated_sibling(self):
        old=historical('round8-P3')
        findings=Topology.from_inputs(layout=old['layout'],specification=old['specification']).hall_route_clearance()
        self.assertLess(findings[0].achieved,.9);self.assertEqual(findings[0].required,.9)
        self.assertEqual(self.clean.hall_route_clearance(),[])
        layout=layout_shift(old['layout'],delta=(8,11),rename=False)
        specification=copy.deepcopy(old['specification'])
        for key in ('gf_opening',):
            rect=specification[key];specification[key]=[rect[0]+8,rect[1]+11,rect[2]+8,rect[3]+11]
        specification['gf_voids']=[[r[0]+8,r[1]+11,r[2]+8,r[3]+11] for r in specification.get('gf_voids',[])]
        self.assertTrue(Topology.from_inputs(layout=layout,specification=specification).hall_route_clearance())

    def test_l0531_real_measured_909_gap_is_never_rounded_to_900(self):
        requirement=Requirement.card('mitton-path-of-travel-min')
        for identifier in ('two-beds-first-draft','renamed-translated-gap'):
            found=self.clean.clearance_from_fixed_reference(identifier,'opposing-bed-front',MEASURED['l0531']['achieved_m'],requirement)
            self.assertEqual(found[0].achieved,.909);self.assertEqual(found[0].required,.914)
        self.assertEqual(self.clean.clearance_from_fixed_reference('clean-path','fixed-front',.914,requirement),[])

    def test_l0536_traffic_requirement_reuses_held_card(self):
        requirement=Requirement.card('nkba-seating-walk-past-1118')
        # Recorded 813 mm was the wrong no-traffic requirement, not a measured
        # historical aisle. This proves threshold selection only, explicitly.
        self.assertEqual(requirement.value,1.118)
        self.assertTrue(self.clean.clearance_from_fixed_reference('seated-island','fixed-front',.813,requirement))
        self.assertTrue(self.clean.clearance_from_fixed_reference('other-island','other-fixed-front',.813,requirement))
        self.assertEqual(self.clean.clearance_from_fixed_reference('current-island','tall-wall',1.31,requirement),[])

    def test_l0557_l0720_real_door_position_and_current_clean(self):
        historical_scene=historical('draft9')
        historical_spec=copy.deepcopy(historical_scene['topology_specification'])
        old_door=next(d for d in historical_spec['doors'] if set(d['rooms'])=={'parents-bed','parents-dressing'})
        for position,width,lost in ((22.1,.9,.153),(22.05,.8,.053)):
            old_door.update(x=position,width=width)
            found=Topology.from_inputs(layout=historical_scene['topology_layout'],specification=historical_spec).opening_host_collisions()
            finding=next(f for f in found if 'parents-bed/parents-dressing' in f.source_id)
            self.assertAlmostEqual(finding.required-finding.achieved,lost)
        spec=copy.deepcopy(self.specification)
        door=next(d for d in spec['doors'] if set(d['rooms'])=={'parents-bed','parents-dressing'})
        door['x']=MEASURED['l0557']['center_x_m']
        t=Topology.from_inputs(layout=self.layout,specification=spec)
        self.assertTrue(any('parents-bed/parents-dressing' in f.source_id for f in t.opening_host_collisions()))
        self.assertEqual(self.clean.opening_host_collisions(),[])
        door['rooms']=['renamed-bedroom','renamed-dressing']
        self.assertTrue(t.opening_host_collisions())
        self.assertTrue(Topology.from_inputs(layout=self.layout,specification=spec).opening_host_collisions())
        door['x']=MEASURED['l0720']['door_center_x_m']
        self.assertTrue(Topology.from_inputs(layout=self.layout,specification=spec).opening_host_collisions())

    def test_l0570_pocket_approaches_survive_no_swing(self):
        pocket=next(o for o in self.clean.openings if set(o.rooms)=={'corridor','parents-entry'})
        self.assertEqual(pocket.envelope,());self.assertEqual(len(pocket.clear_route),2)
        item=dict(id='chest',room='parents-entry',type='sideboard',cx=18.977,cy=-26.95,rot=0,w=.9,d=.45,h=.8,level='GF',why='frozen regression')
        for identifier in ('historical-chest','renamed-chest'):
            modified=self.furniture+[dict(item,id=identifier)]
            findings=Topology.from_inputs(layout=self.layout,specification=self.specification,furniture=modified).furnished_routes('GF')
            self.assertTrue(any('parents-entry' in f.detail for f in findings))
        self.assertEqual(self.clean.furnished_routes('GF'),[])

    def test_l0542_stair_foot_real_console_and_renamed_sibling(self):
        item=dict(id='console',room='hall-b',type='sideboard',cx=10.1,cy=-28,rot=90,w=1.2,d=.45,h=.8,level='B',why='tests/test_villa_furnish.py historical negative')
        for identifier in ('console','another-console'):
            found=Topology.from_inputs(layout=self.layout,specification=self.specification,furniture=self.furniture+[dict(item,id=identifier)]).furnished_routes('B')
            self.assertTrue(any('stair end of stair-b' in f.detail for f in found))
        self.assertEqual(self.clean.furnished_routes('B'),[])

    def test_l0576_disc_corner_clean_and_actual_700_aisle_mutation(self):
        self.assertEqual(self.clean.furnished_routes('GF'),[])
        for identifier in ('pd-hang-2','sibling-hanging-rail'):
            items=copy.deepcopy(self.furniture);rail=next(i for i in items if i['id']=='pd-hang-2')
            rail['cy']+=.24;rail['id']=identifier
            found=Topology.from_inputs(layout=self.layout,specification=self.specification,furniture=items).furnished_routes('GF')
            self.assertTrue(any('parents-dressing' in f.detail for f in found))

    def test_l0591_real_40mm_overrun_and_4mm_sibling_use_existing_1mm_tolerance(self):
        self.assertEqual(self.clean.module_run_overflow(),[])
        # Original layouts committed after the fix; LEARNINGS preserves 40 mm.
        for extra in (.04,.004):
            items=copy.deepcopy(self.furniture);item=next(i for i in items if i['id']=='dk-run')
            kind,width=item['modules'][-1];item['modules'][-1]=(kind,width+extra);item['id']='renamed-run'
            findings=Topology.from_inputs(layout=self.layout,specification=self.specification,furniture=items).module_run_overflow()
            self.assertAlmostEqual(findings[0].achieved-findings[0].required,extra)

    def test_l0695_real_draft9_support_and_all_geometry_translated(self):
        old=historical('draft9')
        found=Topology.from_inputs(scene=old).unsupported_floating()
        self.assertTrue(any(f.source_id.startswith('marker-STEP-stair-b') for f in found))
        sibling=Topology.from_inputs(scene=scene_shift(old)).unsupported_floating()
        self.assertEqual({f.source_id for f in sibling},{'sibling-'+f.source_id for f in found})
        clean=historical('round2-render')
        self.assertEqual(Topology.from_inputs(scene=clean).unsupported_floating(),[])

    def test_l0713_real_saved_slats_and_pendants_current_clean_and_renamed_sibling(self):
        old=historical('draft9')
        topology=Topology.from_inputs(scene=old,layout=old['topology_layout'],specification=old['topology_specification'])
        found=topology.passage_obstructions()
        self.assertTrue(any(f.source_id=='detail-headboard-slats' and 'parents-entry' in f.reference_id for f in found))
        self.assertTrue(any(f.source_id.startswith('lamp-PEN-SMALL-parents-bed') for f in found))
        current=historical('round2-render')
        self.assertEqual(Topology.from_inputs(scene=current,layout=current['topology_layout'],specification=current['topology_specification']).passage_obstructions(),[])
        sibling=copy.deepcopy(old)
        for mesh in sibling['meshes']:
            # Preserve the existing guard's declared detail/fixture role prefix,
            # while removing every specific furniture/room instance identity.
            prefix,_,suffix=mesh['id'].partition('-')
            mesh['id']=prefix+'-other-'+suffix
        result=Topology.from_inputs(scene=sibling,layout=sibling['topology_layout'],specification=sibling['topology_specification']).passage_obstructions()
        self.assertTrue(any(f.source_id=='detail-other-headboard-slats' for f in result))

    def test_l0849_real_duct_wrong_chimney_and_fixed_reference_numbers(self):
        data=MEASURED['l0849']
        # A fan must remain within its actual chimney footprint. Clearance to
        # its fixed right/left edges becomes negative when its centre exits it.
        achieved=data['half_width_m']-abs(data['old_fan_x_m']-data['chimney_center_x_m'])
        requirement=Requirement(0,'tests/test_d1_wp1.py: authored hood chimney half-width 0.115 m; physical containment, not a services clearance standard')
        found=self.clean.clearance_from_fixed_reference('old-duct','hood-chimney-edge',achieved,requirement)
        self.assertAlmostEqual(found[0].achieved,-.412)
        self.assertTrue(self.clean.clearance_from_fixed_reference('renamed-duct','translated-chimney-edge',achieved,requirement))
        vent=next(v for v in self.specification['ventilation'] if v['room']=='dirty-kitchen')
        run=next(i for i in self.furniture if i['id']=='dk-run')
        from archpipe.concept import villa_furnish3d as F3, villa_furniture_detail as detail
        left,right=next((a,b) for kind,a,b in F3._local_modules(run) if kind=='hob')
        centre=detail.to_world_point(run,(left+right)/2,0,0,0)[0]
        clearance=data['half_width_m']-abs(vent['fan'][0]-centre)
        self.assertEqual(self.clean.clearance_from_fixed_reference('current-duct','actual-chimney-edge',clearance,requirement),[])

    def test_l0820_real_basement_shrub_current_extent_control_and_renamed_sibling(self):
        old=MEASURED['l0820']
        for identifier in ('draft-searsia','another-searsia'):
            found=Topology.from_inputs(layout=self.layout,items=[dict(old,id=identifier)]).occupied_room_intrusions()
            self.assertTrue(any(f.reference_id=='dirty-kitchen' for f in found))
        clear=dict(old,id='outside-room',position=[24,-26,-3],scale=.02)
        self.assertEqual(Topology.from_inputs(layout=self.layout,items=[clear]).occupied_room_intrusions(),[])

    def test_l0834_real_route_sofa_and_all_geometry_translated_sibling(self):
        old=MEASURED['l0834'];route=L.PATHS['living-south']
        self.assertTrue(landscape_route_findings([old],{'living-south':route}))
        shift=(8,12);rect=old['rect']
        shifted=dict(old,id='another-sofa',rect=[rect[0]+shift[0],rect[1]+shift[1],rect[2]+shift[0],rect[3]+shift[1]])
        shifted_route=(route[0]+shift[0],route[1]+shift[1],route[2]+shift[0],route[3]+shift[1])
        self.assertTrue(landscape_route_findings([shifted],{'another-route':shifted_route}))
        self.assertEqual(landscape_route_findings([dict(id='clear',rect=(26,-28,26.5,-27.5))],{'living-south':route}),[])

    def test_l0856_real_buried_rail_finished_face_clean_and_shifted_sibling(self):
        # Exact historical polygon from BuriedFixtures, not a generated new rail.
        polygon=[[5.317,-28.611,.70],[9.517,-28.611,-1.95],[9.517,-28.581,-1.95],[5.317,-28.581,.70]]
        for delta in ((0,0,0),(9,10,4)):
            points=tuple(tuple(p[i]+delta[i] for i in range(3)) for p in polygon)
            face=tuple((x+delta[0],-28.471+delta[1],z+delta[2]) for x,z in ((5.177,-3),(10.2,-3),(10.2,3),(5.177,3)))
            host=Host('party-wall','wall',(face,),bounds_of([face]),(0,1,0))
            obstacle=Obstacle('renamed-rail','handrail',bounds_of([points]),(points,))
            found=Topology(hosts=(host,),obstacles=(obstacle,)).object_penetrating_host('renamed-rail','party-wall')
            self.assertAlmostEqual(found[0].achieved,-.14)
            clean_points=tuple((p[0],p[1]+.20,p[2]) for p in points)
            clean=Obstacle('clean-rail','handrail',bounds_of([clean_points]),(clean_points,))
            self.assertEqual(Topology(hosts=(host,),obstacles=(clean,)).object_penetrating_host('clean-rail','party-wall'),[])


if __name__ == '__main__':
    unittest.main()
