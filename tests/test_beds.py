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
        self.assertIn('scale-distortion', fit['reason'])
        self.assertAlmostEqual(fit['footprint_error_m'][1], .1595549104)
        self.assertGreater(fit['height_err'], .18)
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
            self.assertEqual(placed_bed_findings(native, clean, [low[0],low[1],high[0],high[1]], dimensions[1], 1), [])
            self.assertTrue(fit_bed(native, dimensions[0], dimensions[2], dimensions[1], '+Z')['ok'])

    def test_position_and_height_cannot_hide_behind_extent_fit(self):
        native = FROZEN['bounds_m']
        width, height, depth = [b-a for a, b in zip(native['min'], native['max'])]
        clean = {'min': [0,0,0], 'max': [width,depth,height]}
        shifted = {'min': [.021,0,0], 'max': [width+.021,depth,height]}
        self.assertTrue(placed_bed_findings(native, shifted, [0,0,width,depth], height, 1))
        self.assertTrue(placed_bed_findings(native, clean, [0,0,width,depth], height*.9, 1))
        too_small = {'min': [0,0,0], 'max': [width-.06,depth,height]}
        self.assertTrue(placed_bed_findings(native, too_small, [0,0,width,depth], height, 1))

    def test_measured_x_front_is_independent_of_asset_origin(self):
        native = FROZEN['bounds_m']
        width, height, depth = [b-a for a, b in zip(native['min'], native['max'])]
        self.assertTrue(fit_bed(native, depth, width, height, '-X')['ok'])
        self.assertEqual(placed_bed_findings(native, {'min':[0,0,0], 'max':[depth,width,height]},
                                           [0,0,depth,width], height, 1, (2,0,1)), [])

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
        self.assertFalse(fit_bed(FROZEN['bounds_m'],width,depth+.03,height,'+Z')['ok'])
        self.assertTrue(fit_bed(FROZEN['bounds_m'],width,depth+.019,height,'+Z')['ok'])


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
        self.assertIn('scale-distortion', ' '.join(self.scene['notes']))
        for bed in beds:
            parts = [m for m in self.scene['meshes'] if m['id'].startswith('furn-'+bed['id']+'-')]
            self.assertTrue(parts, bed['id'])
            self.assertTrue(all('PROCEDURAL BED FALLBACK (stand-in)' in m['fallback_label'] for m in parts))
            self.assertTrue(all(m.get('visibility',{}).get('camera',True) for m in parts))

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
        bad=deepcopy(self.scene)
        bed_parts=[m for m in bad['meshes'] if m['id'].startswith('furn-pb-bed-')]
        for mesh in bed_parts:
            mesh.pop('mounting',None)
            for face in mesh['faces']:
                for p in face:
                    p[0]+=100
                    p[2]+=1
        self.assertTrue(any(f.source_id.startswith('furn-pb-bed-') for f in
                            GeometryTopology.from_inputs(scene=bad).unsupported_floating()))
        bed=next(b for b in self.items if b['id']=='pb-bed')
        rect=F.footprint(bed)
        topology=GeometryTopology.from_inputs(items=[dict(id='renamed-real-bed',rect=rect,
            bottom_m=LZ[bed['level']],top_m=LZ[bed['level']]+1.05)],
            routes={'other-required-route':rect},route_ground={'other-required-route':LZ[bed['level']]})
        self.assertTrue(topology.object_in_route())


if __name__ == '__main__':
    unittest.main()
