"""Real rejected bed, translated siblings, and unchanged D1 fallback checks.

The mechanically accepted Chelsea-sized control proves the guard stays
quiet; it is not an accepted D1 product. No imported bed is approved yet.
"""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from archpipe.beds import fit_bed, placed_bed_findings, bed_items, label_fallbacks
from archpipe.asset_intake import validate_entry
from archpipe.concept import villa_furnish as F, villa_r11 as R, revit_spec as RS
from archpipe.geometry_topology import GeometryTopology

FROZEN = json.loads((Path(__file__).parent / 'fixtures/bed-chelsea-measured-rejection.json').read_text())
DISTORTED = json.loads((Path(__file__).parent / 'fixtures/bed-real-distortion.json').read_text())


class BedFit(unittest.TestCase):
    def test_real_fallback_label_escape_and_renamed_sibling_preserve_subject_identity(self):
        frozen = json.loads((Path(__file__).parent/'fixtures/bed-fallback-label-before.json').read_text())
        self.assertTrue(all(m['label'] != 'pb-bed' for m in frozen['meshes']))
        for mark in ('pb-bed','another-suite-bed'):
            meshes=[dict(m,id=m['id'].replace('pb-bed',mark),label=mark) for m in frozen['meshes']]
            label_fallbacks(meshes,[dict(id=mark,type='bed_double')])
            self.assertTrue(all(m['label']==mark for m in meshes))
            self.assertTrue(all(m['asset_status']=='procedural-bed-fallback' for m in meshes))
            label_fallbacks(meshes,[dict(id=mark,type='bed_double')])
            self.assertTrue(all(m['label']==mark and m['fallback_label'].count('FALLBACK')==1 for m in meshes))

    def test_real_chelsea_rejected_without_changing_d1_footprint(self):
        target = FROZEN['target']
        fit = fit_bed(FROZEN['bounds_m'], **target, front_axis=FROZEN['front_axis'])
        self.assertFalse(fit['ok'])
        self.assertIn('actual mattress geometry required', fit['reason'])
        self.assertEqual(fit['scale'], 1.)
        sibling = deepcopy(FROZEN['bounds_m'])
        for key in ('min', 'max'):
            sibling[key] = [v + d for v, d in zip(sibling[key], (8, 11, 3))]
        translated = fit_bed(sibling, **target, front_axis='+Z')
        self.assertEqual(fit['ok'], translated['ok'])
        self.assertEqual(fit['reason'], translated['reason'])
        self.assertAlmostEqual(fit['scale'], translated['scale'])

    def test_real_axis_distortion_fires_translated_sibling_and_clean_control_quiet(self):
        native = FROZEN['bounds_m']
        dimensions = [b-a for a, b in zip(native['min'], native['max'])]
        scale = min(1.6 / dimensions[0], 2.0 / dimensions[2])
        for travel in ((0, 0, 0), (8, 11, 3)):
            # Real measured model forced independently onto both plan axes:
            # its world box can fit perfectly while its mesh is distorted.
            origin = [20.33 + travel[0], -25.591 + travel[1], travel[2]]
            footprint = [origin[0]-.8, origin[1]-1, origin[0]+.8, origin[1]+1]
            # These bounds were remeasured from all 105,298 actual indexed
            # triangles after an independently scaled root-node injection,
            # not invented from the target rectangle.
            distorted = {key:[v+d for v,d in zip(values,travel)] for key,values
                         in DISTORTED['measured_distorted_world_bounds'].items()}
            found = placed_bed_findings(native, distorted, footprint, 1.05, scale)
            self.assertTrue(any('uniform scale' in f for f in found))
            # Same real model at its own true dimensions is a clean numeric
            # control, without implying its larger footprint is allowed in D1.
            low = [origin[0]-dimensions[0]/2, origin[1]-dimensions[2]/2, origin[2]]
            high = [origin[0]+dimensions[0]/2, origin[1]+dimensions[2]/2, origin[2]+dimensions[1]]
            clean = {'min': low, 'max': high}
            self.assertEqual(placed_bed_findings(native, clean, [low[0],low[1],high[0],high[1]], dimensions[1], 1, mattress_world_bounds={'lower':clean}), [])
            self.assertTrue(fit_bed(native, dimensions[0], dimensions[2], dimensions[1], '+Z', mattress_bounds={'lower':native})['ok'])

    def test_position_and_height_cannot_hide_behind_extent_fit(self):
        native = FROZEN['bounds_m']
        width, height, depth = [b-a for a, b in zip(native['min'], native['max'])]
        clean = {'min': [0,0,0], 'max': [width,depth,height]}
        shifted = {'min': [.021,0,0], 'max': [width+.021,depth,height]}
        self.assertTrue(placed_bed_findings(native, shifted, [0,0,width,depth], height, 1))
        self.assertEqual(placed_bed_findings(native, clean, [0,0,width,depth], height*.9, 1, mattress_world_bounds={'lower':clean}), [])
        too_small = {'min': [0,0,0], 'max': [width-.06,depth,height]}
        self.assertTrue(placed_bed_findings(native, too_small, [0,0,width,depth], height, 1))

    def test_measured_x_front_is_independent_of_asset_origin(self):
        native = FROZEN['bounds_m']
        width, height, depth = [b-a for a, b in zip(native['min'], native['max'])]
        self.assertTrue(fit_bed(native, depth, width, height, '-X', mattress_bounds={'lower':native})['ok'])
        self.assertEqual(placed_bed_findings(native, {'min':[0,0,0], 'max':[depth,width,height]},
                                           [0,0,depth,width], height, 1, (2,0,1), mattress_world_bounds={'lower':{'min':[0,0,0],'max':[depth,width,height]}}), [])

    def test_unmeasured_nonfinite_axiswise_or_invalid_inputs_refused(self):
        for bounds in (None, {}, {'min':[0,0,0],'max':[1,float('nan'),1]},
                       {'min':[0,0,0],'max':[1,0,1]}):
            with self.subTest(bounds=bounds), self.assertRaises(ValueError):
                fit_bed(bounds, 1.6, 2, 1.05, '+Z')
        for front in (None, 'none', '+Y'):
            with self.subTest(front=front), self.assertRaises(ValueError):
                fit_bed(FROZEN['bounds_m'], 1.6, 2, 1.05, front)
        for scale in ([1,1,1], 0, float('inf'), True):
            with self.subTest(scale=scale), self.assertRaises(ValueError):
                placed_bed_findings(FROZEN['bounds_m'], FROZEN['bounds_m'], [0,0,1,2], 1, scale)

    def test_existing_intake_refuses_bed_without_units_contents_or_credit(self):
        manifest = json.loads((Path(__file__).parents[1]/'ops/workstation/library-manifest.json').read_text())
        entry = deepcopy(next(e for e in manifest['props'] if e['id']==FROZEN['asset']))
        entry.pop('units_normalised', None)
        entry.pop('contents', None)
        self.assertIn('missing units_normalised', validate_entry(entry))
        self.assertIn('missing contents', validate_entry(entry))
        entry['credit'] = ''
        self.assertIn('CC-BY requires credit', validate_entry(entry))

    def test_absolute_twenty_mm_guard_not_relative_two_percent(self):
        # At this real bed's depth, a 30 mm deficit is under two percent;
        # the client required an absolute 20 mm boundary.
        width,height,depth = [b-a for a,b in zip(FROZEN['bounds_m']['min'],FROZEN['bounds_m']['max'])]
        self.assertFalse(fit_bed(FROZEN['bounds_m'],width,depth+.03,height,'+Z', mattress_bounds={'lower':FROZEN['bounds_m']})['ok'])
        self.assertTrue(fit_bed(FROZEN['bounds_m'],width,depth+.019,height,'+Z', mattress_bounds={'lower':FROZEN['bounds_m']})['ok'])


class FurnishedBeds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from archpipe.concept import villa_render as VR
        cls.layout = R.design('D1')
        cls.items = F.layout(cls.layout)
        cls.scene = VR.build()
        cls.specification = RS.build(cls.layout)

    def test_all_four_beds_keep_layout_sizes_and_explicit_fallbacks(self):
        beds = bed_items(self.items)
        self.assertEqual({b['id']:(b['w'],b['d']) for b in beds},
                         {'pb-bed':(1.6,2.0),'kb-bed':(1.2,2.0),'ka-bunk':(.9,2.0),'library-daybed':(2.0,.95)})
        self.assertFalse(any(m['asset']==FROZEN['asset'] for m in self.scene['models']))
        self.assertIn('actual mattress geometry required', ' '.join(self.scene['notes']))
        for bed in beds:
            parts = [m for m in self.scene['meshes'] if m['id'].startswith('furn-'+bed['id']+'-')]
            self.assertTrue(parts, bed['id'])
            self.assertTrue(all('PROCEDURAL BED FALLBACK (stand-in)' in m['fallback_label'] for m in parts))
            replaced=any(m.get('role')=='bed' and m.get('label')==bed['id'] for m in self.scene['models'])
            self.assertTrue(all(m.get('visibility',{}).get('camera',True)==(not replaced) for m in parts))

    def test_fallback_labels_generalise_without_mutating_geometry(self):
        item={'id':'other-rest','type':'daybed_nook'}
        mesh={'id':'furn-other-rest-0','label':'mattress','faces':[[[0,0,0],[1,0,0],[1,1,0]]]}
        before=deepcopy(mesh['faces'])
        label_fallbacks([mesh],[item])
        self.assertIn('FALLBACK',mesh['fallback_label'])
        self.assertEqual(mesh['label'],'mattress')
        self.assertEqual(mesh['faces'],before)

    def test_support_routes_and_swings_on_the_actual_furnished_scene(self):
        topology = GeometryTopology.from_inputs(scene=self.scene,layout=self.layout,
                                                specification=self.specification,furniture=self.items)
        self.assertEqual(topology.unsupported_floating(), [])
        self.assertEqual(topology.furnished_routes('GF'), [])
        self.assertEqual(topology.furnished_routes('B'), [])
        bed_prefixes = tuple('furn-'+b['id']+'-' for b in bed_items(self.items))
        self.assertEqual([f for f in topology.swing_envelope_vs_obstacle()
                          if f.source_id.startswith(bed_prefixes) or f.source_id in {b['id'] for b in bed_items(self.items)}], [])

    def test_real_bed_floating_and_route_mutations_fire(self):
        # Move the whole real assembly into open air, far from walls;
        # adjacent furniture must not falsely ground the lifted bed.
        from archpipe.concept.villa_render import LZ
        actual=next((m for m in self.scene['models'] if m.get('role')=='bed' and m.get('label')=='pb-bed'),None)
        if actual:
            lifted=deepcopy(actual);lifted['position'][0]+=100;lifted['position'][2]+=1
            bad=dict(self.scene,models=[lifted if m['id']==actual['id'] else m for m in self.scene['models']])
            prefix=actual['id']+'::'
        else:
            bad=deepcopy(self.scene);prefix='furn-pb-bed-'
            bed_parts=[m for m in bad['meshes'] if m['id'].startswith(prefix)]
            for mesh in bed_parts:
                mesh.pop('mounting',None)
                for face in mesh['faces']:
                    for p in face:p[0]+=100;p[2]+=1
        self.assertTrue(any(f.source_id.startswith(prefix) for f in
                            GeometryTopology.from_inputs(scene=bad).unsupported_floating()))
        bed=next(b for b in self.items if b['id']=='pb-bed')
        rect=F.footprint(bed)
        topology=GeometryTopology.from_inputs(items=[dict(id='renamed-real-bed',rect=rect,
            bottom_m=LZ[bed['level']],top_m=LZ[bed['level']]+1.05)],
            routes={'other-required-route':rect},route_ground={'other-required-route':LZ[bed['level']]})
        self.assertTrue(topology.object_in_route())



class RealSizeBeds(unittest.TestCase):
    def real_model(self, name='other-suite-bed', yaw=0, position=(8,11,3)):
        import gzip
        geometry=json.loads(gzip.decompress((Path(__file__).parent/'fixtures/bed-scandi-geometry.json.gz').read_bytes()))
        return dict(id=name,asset=geometry['asset'],role='bed',scale=1.,position=list(position),
            rotation_deg=[0,0,yaw],replaces='furn-'+name+'-',review_geometry=geometry,
            contents_review=dict(status='bed-only',basis='all seven actual bed meshes inspected',extras=[]),
            mattress_bindings=dict(lower=dict(parts=['Object_14'],head_at_max=False)))

    def test_round2_scales_are_refused_in_fit_and_portable_review_renamed_sibling(self):
        from archpipe.beds import model_review_meshes
        rows=json.loads((Path(__file__).parent/'fixtures/bed-round2-measurements.json').read_text())
        for row in rows:
            result=fit_bed(row['bounds_m'],*row['target'],row['front_axis'],row['length_axis'],scale=row['fit']['scale'])
            self.assertFalse(result['ok'])
            self.assertIn('scaled bed refused',result['reason'])
            for name in (row['id'],'renamed-'+row['id']):
                model=self.real_model(name);model['scale']=row['fit']['scale']
                with self.assertRaisesRegex(ValueError,'scaled bed refused'):
                    model_review_meshes([model])

    def test_real_mattress_forty_mm_short_fails_correct_and_renamed_pass(self):
        from archpipe.beds import model_mattress_bounds
        for name in ('actual-scandi','another-villa-bed'):
            model=self.real_model(name)
            mattress=model_mattress_bounds(model)['lower']
            width=mattress['max'][2]-mattress['min'][2]
            length=mattress['max'][0]-mattress['min'][0]
            frame=dict(min=[-2.164110,.017163,-1.304135],max=[2.283993,1.317586,1.225815])
            good=fit_bed(frame,width,length,None,'+X',mattress_bounds={'lower':mattress})
            self.assertTrue(good['ok'])
            short=fit_bed(frame,width,length+.04,None,'+X',mattress_bounds={'lower':mattress})
            self.assertFalse(short['ok']);self.assertIn('40.000 mm',short['reason'])
            missing=fit_bed(frame,width,length,None,'+X')
            self.assertFalse(missing['ok'])

    def test_real_asymmetric_frame_anchors_mattress_and_frame_proxy_preserves_other_items(self):
        from archpipe.beds import model_mattress_bounds,model_review_meshes,bed_frame_items
        for yaw in (0,90,180,270):
            model=self.real_model(yaw=yaw)
            # Inject an asymmetric head extension sibling into this frozen model.
            model['review_geometry']['meshes'].append(dict(name='asymmetric-frame-extension',
                faces=[[[4,-.8,0],[4,.8,0],[4,.8,1]]]))
            native=deepcopy(model['review_geometry'])
            world=model_mattress_bounds(model,world=True)['lower']
            self.assertAlmostEqual((world['min'][0]+world['max'][0])/2,8)
            self.assertAlmostEqual((world['min'][1]+world['max'][1])/2,11)
            faces=model_review_meshes([model]);points=[p for row in faces for face in row['faces'] for p in face]
            self.assertAlmostEqual(min(p[2] for p in points),3)
            axis=0 if yaw in (0,180) else 1
            self.assertGreater(abs((min(p[axis] for p in points)+max(p[axis] for p in points))/2-model['position'][axis]),.5)
            furniture=[dict(id=model['id'],type='bed_single',w=1.,d=2.,cx=8.,cy=11.,rot=0),
                       dict(id='fixed-wardrobe',type='wardrobe',w=1.5,d=.6,cx=14.,cy=14.,rot=0)]
            before=deepcopy(furniture)
            frame_items=bed_frame_items(dict(models=[model]),furniture)
            self.assertEqual(frame_items[1],before[1]);self.assertEqual(furniture,before)
            self.assertGreater(frame_items[0]['w']*frame_items[0]['d'],2.)
            self.assertEqual(native,model['review_geometry'])

    def test_separable_extras_omitted_in_every_consumer_inseparable_or_unrecorded_refused(self):
        from archpipe.beds import model_review_meshes,model_mattress_bounds,model_native_bounds
        model=self.real_model()
        original_bounds=model_native_bounds(model)
        accessory=dict(name='separate-bedside',faces=[[[20,20,0],[21,20,0],[21,21,1]]])
        model['review_geometry']['meshes'].append(accessory)
        with self.assertRaisesRegex(ValueError,'every accessory'):
            model['contents_review']['extras']=['separate-bedside'];model_review_meshes([model])
        model['omitted_meshes']=['separate-bedside']
        rows=model_review_meshes([model])
        self.assertFalse(any('separate-bedside' in row['id'] for row in rows))
        self.assertEqual(model_native_bounds(model),original_bounds)
        self.assertLess(model_mattress_bounds(model,world=True)['lower']['max'][0],20)
        model['contents_review']['status']='inseparable-extras'
        with self.assertRaisesRegex(ValueError,'bed-only'):
            model_review_meshes([model])

    def test_source_unit_conversion_is_only_permitted_scale(self):
        from archpipe.beds import real_size_findings,unit_scale
        self.assertEqual(real_size_findings(1),[])
        self.assertTrue(real_size_findings(.01))
        evidence=dict(unit='cm',source='Author listing explicitly states centimetres')
        self.assertEqual(unit_scale(evidence),.01)
        self.assertEqual(real_size_findings(.01,evidence),[])
        self.assertTrue(real_size_findings(.0101,evidence))
        feet=dict(unit='ft',source='Author explicitly states feet for this file')
        self.assertEqual(real_size_findings(.3048,feet),[])
        with self.assertRaisesRegex(ValueError,'source'):
            unit_scale(dict(unit='cm',source=''))

    def test_real_frame_overhang_has_no_old_height_or_edge_limit(self):
        frame=dict(min=[-1.0,0,-1.3],max=[1.,1.8,1.3])
        mattress=dict(min=[-.8,.5,-1],max=[.8,.75,1])
        self.assertTrue(fit_bed(frame,1.6,2,1.05,'+Z',mattress_bounds={'lower':mattress})['ok'])
        world=dict(min=[-1,-1.3,0],max=[1,1.3,1.8])
        actual_mattress=dict(min=[-.8,-1,.5],max=[.8,1,.75])
        self.assertEqual(placed_bed_findings(frame,world,[-.8,-1,.8,1],1.05,1,
            mattress_world_bounds={'lower':actual_mattress}),[])
        shifted=deepcopy(actual_mattress);shifted['min'][0]+=.001;shifted['max'][0]+=.001
        self.assertTrue(placed_bed_findings(frame,world,[-.8,-1,.8,1],1.05,1,mattress_world_bounds={'lower':shifted}))

    def test_native_frame_c8_reports_shortfall_and_clean_room_stays_quiet(self):
        from archpipe.beds import bed_room_review
        model=self.real_model(position=(0,0,0));model['room']='another-bedroom'
        item=dict(id=model['id'],type='bed_small_double',cx=0,cy=0,w=2.4124317169189453,
            d=4.241483449935913,h=1.3,rot=-90,room='another-bedroom',level='GF')
        floor=dict(id='floor',group='shell',material='floor-oak',faces=[
            [[-5,-5,0],[5,-5,0],[5,5,0],[-5,5,0]]])
        scene=dict(meshes=[floor],models=[model]);spec=dict(walls=[],doors=[],windows=[],stairs=[])
        layout=dict(rooms={'another-bedroom':dict(rect=[-5,-5,5,5],level='GF',occupancy='room',kind='bedroom')})
        before=deepcopy((scene,layout,[item]))
        clean=bed_room_review(scene,layout,spec,[item])
        self.assertTrue(clean['ok'],clean['findings'])
        self.assertEqual((scene,layout,[item]),before)
        layout['rooms']['another-bedroom']['rect']=[-5,-1.7062159,5,1.7062159]
        tight=bed_room_review(scene,layout,spec,[item])
        self.assertFalse(tight['ok'])
        for row in tight['clearances']:
            self.assertAlmostEqual(row['achieved_m'],.44124077,places=6)
            self.assertEqual(row['required_m'],.750)
            self.assertAlmostEqual(row['shortfall_m'],.30875923,places=6)
            self.assertIn('printed page 18',row['source'])
        # Only a review proxy grew: the planned mattress and existing camera/layout persist.
        self.assertEqual(item,before[2][0])
        self.assertEqual(scene,before[0])

    def test_each_bunk_berth_required_and_measured(self):
        frame=dict(min=[-.6,0,-1.2],max=[.6,1.7,1.2])
        lower=dict(min=[-.45,.3,-1],max=[.45,.5,1])
        upper=dict(min=[-.45,1.3,-1],max=[.45,1.5,1])
        self.assertFalse(fit_bed(frame,.9,2,None,'+Z',mattress_bounds={'lower':lower},required_berths=2)['ok'])
        self.assertTrue(fit_bed(frame,.9,2,None,'+Z',mattress_bounds={'lower':lower,'upper':upper},required_berths=2)['ok'])
        upper['max'][2]-=.04
        self.assertFalse(fit_bed(frame,.9,2,None,'+Z',mattress_bounds={'lower':lower,'upper':upper},required_berths=2)['ok'])


if __name__ == '__main__':
    unittest.main()
