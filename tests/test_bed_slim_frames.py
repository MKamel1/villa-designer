"""Frozen actual extremal triangles prove contents transforms and edge guards."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
import numpy as np
from archpipe.beds import (scaled_model_fit, slim_frame_fit, slim_frame_findings,
    model_review_meshes, model_mattress_bounds, review_selection, require_bed_geometry,
    model_transform, integrate_bed_models)
FIXTURE=Path(__file__).parent/'fixtures/bed-round6-extremal-faces.json'


def proposed(model):
    model=deepcopy(model)
    names={r['name'] for r in model['review_geometry']['meshes']}
    mattresses={n for b in model['mattress_bindings'].values() for n in b['parts']}
    frame=['Object_4'] if model['required_berths']==1 else ['Bunk_cgt_bunk_bed_f_house_wood_0']
    model['frame_slimming']=dict(decision_date='2026-10-09',frame_parts=frame,
        bedding_parts=sorted(names-mattresses-set(frame)),basis='frozen real measured parts')
    if model['required_berths']==2:
        model['scaling'].update(height_berth='upper',mattress_top_m=1.4,height_source='ASSUMED unchanged upper design datum')
    model['scale_xyz']=scaled_model_fit(model)['scale_xyz']
    model['frame_slimming']['scale_xy']=slim_frame_fit(model)['scale_xy']
    model['neutral_review']=dict(status='accepted',source_sha256=model['review_geometry']['source_sha256'],
        orientation_evidence=deepcopy(model['orientation_evidence']),selection=review_selection(model))
    return model


class SlimFrames(unittest.TestCase):
    def models(self):
        return json.loads(FIXTURE.read_text())

    def test_real_frame_over_fifty_mm_fails_and_renamed_rotated_sibling(self):
        old=self.models()[0]
        for yaw,travel,name in [(old['rotation_deg'][2],[0,0,0],old['id']),(37,[8,11,3],'renamed-other-villa')]:
            historical=deepcopy(old);historical['id']=name;historical['rotation_deg'][2]=yaw
            historical['position']=(np.array(historical['position'])+travel).tolist()
            model=proposed(historical)
            self.assertTrue(any('slim-frame' in f for f in slim_frame_findings(model,model_review_meshes([historical]))))
            self.assertEqual(slim_frame_findings(model,model_review_meshes([model])),[])
            require_bed_geometry(model)
            mutated=model_review_meshes([model])
            for row in mutated:
                if row['id'].endswith('::Object_4'):
                    row['faces']=(np.asarray(row['faces'])+[.2,0,0]).tolist()
            self.assertTrue(slim_frame_findings(model,mutated))

    def test_real_frame_factor_below_half_refuses_even_neutral_renamed_and_parent_quiet(self):
        parent,bunk=map(proposed,self.models())
        require_bed_geometry(parent,neutral_diagnostic=True)
        for name in (bunk['id'],'renamed-bunk'):
            bad=deepcopy(bunk);bad['id']=name
            fit=slim_frame_fit(bad)
            self.assertFalse(fit['ok']);self.assertAlmostEqual(fit['width_factor'],.4560006116531947)
            with self.assertRaisesRegex(ValueError,'below 0.5'):require_bed_geometry(bad,neutral_diagnostic=True)

    def test_bedding_mattress_and_vertical_faces_unchanged_by_frame_plan_fit(self):
        for old in self.models():
            model=proposed(old);before=deepcopy(model['review_geometry'])
            common=deepcopy(model);common.pop('frame_slimming')
            original={r['id']:r for r in model_review_meshes([common])}
            for row in model_review_meshes([model]):
                if row['id'].split('::')[-1] not in model['frame_slimming']['frame_parts']:
                    np.testing.assert_allclose(row['faces'],original[row['id']]['faces'],atol=1e-12)
                else:
                    np.testing.assert_allclose(np.asarray(row['faces'])[:,:,2],np.asarray(original[row['id']]['faces'])[:,:,2])
            self.assertEqual(model['review_geometry'],before)
            for box in model_mattress_bounds(model,world=True).values():
                for axis in (0,1):self.assertAlmostEqual((box['min'][axis]+box['max'][axis])/2,model['position'][axis],places=5)

    def test_upper_drives_vertical_factor_and_one_factor_cannot_meet_both_datums(self):
        model=proposed(self.models()[1]);fit=scaled_model_fit(model)
        actual=model_mattress_bounds(model,world=True)
        self.assertAlmostEqual(actual['upper']['max'][2],1.402)
        self.assertAlmostEqual(fit['sz'],.8622326508847344,places=9)
        self.assertGreater(actual['lower']['max'][2]-.402,.09)
        self.assertGreater(actual['upper']['min'][2]-actual['lower']['max'][2],.8)
        # Frame refusal occurs before any room gate; a valid-frame sibling still
        # must retain BOTH heights, independently of frame acceptance.
        from unittest.mock import patch
        with patch('archpipe.beds.require_bed_geometry'),patch('archpipe.beds.bed_room_review') as room:
            item=dict(id='ka-bunk',w=.9,d=2.,cx=model['position'][0],cy=model['position'][1],rot=model['layout_rotation_deg'],berths=2)
            scene=dict(models=[],meshes=[dict(id='furn-ka-bunk-fallback',faces=[[[0,0,.002],[1,0,.002],[0,1,.002]]])],
                cloth=[dict(id='duvet-ka-bunk',mattress_top=.402),dict(id='duvet-ka-bunk-upper',mattress_top=1.402)])
            with self.assertRaisesRegex(ValueError,'every design mattress-top height'):
                integrate_bed_models(scene,[model],{}, {},[item])
            room.assert_not_called()

    def test_classification_factor_and_review_mutations_refuse(self):
        model=proposed(self.models()[0])
        bad=deepcopy(model);bad['frame_slimming']['bedding_parts']=[]
        with self.assertRaisesRegex(ValueError,'identification'):model_transform(bad)
        bad=deepcopy(model);bad['frame_slimming']['scale_xy'][0]+=.02
        with self.assertRaisesRegex(ValueError,'factors disagree'):model_transform(bad)
        bad=deepcopy(model);bad['frame_slimming']['basis']+=' changed'
        with self.assertRaisesRegex(ValueError,'not bound'):require_bed_geometry(bad)
        bad=deepcopy(model);bad['frame_slimming']['decision_date']='2026-10-08'
        with self.assertRaisesRegex(ValueError,'2026-10-09'):model_transform(bad)

    def test_current_slim_parent_still_requires_passing_fixed_room(self):
        from unittest.mock import patch
        model=proposed(self.models()[0]);mark=model['label']
        item=dict(id=mark,w=1.6,d=2.,cx=model['position'][0],cy=model['position'][1],
            rot=model['layout_rotation_deg'],berths=1)
        scene=dict(models=[],meshes=[dict(id=model['replaces']+'fallback',faces=[[[0,0,.002],[1,0,.002],[0,1,.002]]])],
            cloth=[dict(id='duvet-'+mark,mattress_top=.527)])
        with patch('archpipe.beds.bed_room_review',return_value=dict(ok=False,findings=['fixed room failure'])) as room:
            with self.assertRaisesRegex(ValueError,'fails fixed room'):
                integrate_bed_models(scene,[model],{}, {},[item])
            room.assert_called_once()

    def test_slim_planning_frame_excludes_bedding_but_c8_keeps_its_real_faces(self):
        from archpipe.beds import bed_frame_items
        model=proposed(self.models()[0])
        item=dict(id=model['label'],w=1.6,d=2.,h=1.05,cx=model['position'][0],cy=model['position'][1],rot=0)
        frame=bed_frame_items(dict(models=[model]),[item])[0]
        self.assertAlmostEqual(frame['w'],1.6864677834368154,places=5)
        self.assertAlmostEqual(frame['d'],2.1,places=5)
        actual=model_review_meshes([model])
        self.assertTrue(any(r['id'].endswith('::Object_6') for r in actual))
        points=np.asarray([p for r in actual for f in r['faces'] for p in f])
        self.assertGreater(points[:,0].max()-points[:,0].min(),frame['w']+.5)

    def test_real_round6_throw_refusal_remains_failure_renamed_and_clean_quiet(self):
        import runpy
        require=runpy.run_path(str(Path(__file__).parents[1]/'scripts/preview_beds.py'))['require_neutral_cloth']
        actual=json.loads((FIXTURE.parent/'bed-round6-throw-refusal.json').read_text())
        for name in (actual['bed'],'renamed-other-villa'):
            bad=deepcopy(actual);bad['bed']=name
            with self.assertRaisesRegex(ValueError,'refused'):require([bad])
        clean=deepcopy(actual);clean['cloth_report']=dict(passed=True)
        require([clean])

    def test_real_joined_room_frame_and_bedding_boundary_renamed_clean_and_concave(self):
        from archpipe.beds import bed_room_boundary_findings
        cases=json.loads((FIXTURE.parent/'bed-round6-boundary-faces.json').read_text())
        for case in cases:
            for name,travel in [(case['model']['id'],np.zeros(3)),('other-villa-bed',np.array([8.,11.,3.]))]:
                model=dict(case['model'],id=name,room='other-room')
                mesh=dict(case['mesh'],id=name+'::part',model_instance=name,
                    faces=(np.asarray(case['mesh']['faces'])+travel).tolist())
                rect=np.asarray(case['room_rect'])+np.tile(travel[:2],2)
                # The real parents joined-room escape also occurs in a renamed
                # cluster: the extra room does not enclose the protruding head.
                layout=dict(rooms={'other-room':dict(rect=rect.tolist(),level='GF',occupancy='bedroom'),
                    'entry':dict(rect=[rect[0],rect[3],rect[2],rect[3]+1],level='GF',occupancy='bedroom',part_of='other-room')})
                bad=bed_room_boundary_findings(dict(models=[model]),layout,[mesh])
                self.assertEqual(len(bad),1)
                self.assertGreater(bad[0].achieved,0)
                clean=deepcopy(layout);clean['rooms']['other-room']['rect']=[rect[0]-1,rect[1]-1,rect[2]+1,rect[3]+1]
                self.assertEqual(bed_room_boundary_findings(dict(models=[model]),clean,[mesh]),[])
        # All four bounding corners lie in this concave room cluster, but the
        # middle crosses a missing room area: a corner-only guard must refuse.
        model=dict(id='concave-bed',room='left',role='bed')
        mesh=dict(id='concave-bed::frame',faces=[[[0,0,0],[3,0,0],[3,3,0],[0,3,0]]])
        layout=dict(rooms={name:dict(rect=rect,level='GF',occupancy='corridor') for name,rect in
                    [('left',[0,0,1,3]),('right',[2,0,3,3]),('bridge',[1,0,2,1])]})
        self.assertAlmostEqual(bed_room_boundary_findings(dict(models=[model]),layout,[mesh])[0].achieved,2.)

    def test_real_parent_cluster_boundary_runs_in_c8(self):
        from contextlib import ExitStack
        from unittest.mock import patch
        from archpipe.beds import bed_room_review
        from archpipe.geometry_topology import GeometryTopology
        from archpipe.concept import villa_r11 as R, villa_furnish as F
        model=proposed(self.models()[0]);full=R.design('D1')
        layout=dict(rooms={name:full['rooms'][name] for name in ('parents-bed','parents-entry')})
        item=next(i for i in F.layout(full) if i['id']==model['label'])
        scene=dict(models=[model],meshes=[])
        with ExitStack() as stack:
            # Isolate boundary ownership; the real measured model, room cluster
            # and C8 dispatcher remain. Other queries have independent tests.
            for name in ('unsupported_floating','swing_envelope_vs_obstacle','passage_obstructions',
                         'occupied_room_intrusions','object_overlaps','object_in_route','furnished_routes'):
                empty=lambda *args,**kwargs: []
                empty.__name__=name
                stack.enter_context(patch.object(GeometryTopology,name,new=empty))
            result=bed_room_review(scene,layout,dict(walls=[],doors=[]),[item])
        self.assertTrue(any(f['query']=='bed-part-room-boundary' for f in result['findings']))

if __name__=='__main__':unittest.main()
