"""Shared furniture scaling boundaries and measured desktop/seat contracts."""
from copy import deepcopy
import json
from pathlib import Path
import runpy
from types import MappingProxyType
import unittest

from archpipe.furniture_fit import (fit_factors, fit_furniture, native_box,
                                    plan_scale_findings, retained_model_rows, unit_scale)

ROOT = Path(__file__).resolve().parents[1]


class FurnitureFit(unittest.TestCase):
    def box(self, low, high):
        # Review faces are Z up; eight measured corners define the fixture box.
        x0,y0,z0=low; x1,y1,z1=high
        return [[[x0,y0,z0],[x1,y1,z1],[x0,y1,z1]],
                [[x1,y0,z0],[x0,y1,z0],[x1,y0,z1]]]

    def model(self, role='desk'):
        return dict(id='another-house-work-item', role=role, front_axis='+Z',
                    contents_review=dict(status='item-only', basis='all actual fixture parts inspected', extras=[]),
                    review_geometry=dict(meshes=[
                        dict(name='body',faces=self.box((-.7,-.3,0),(.7,.3,.7))),
                        dict(name='top',faces=self.box((-.7,-.3,.7),(.7,.3,.75)))]))

    def fit(self, model=None, **kwargs):
        args=dict(height_parts=['top'],height_m=.75,
                  height_source='design: author desk desktop field',height_basis='design')
        args.update(kwargs)
        return fit_furniture(model or self.model(),1.4,.6,**args)

    def test_boundary_symmetric_anisotropy_and_absolute_factors(self):
        for a,b in ((1,1.15),(1.15,1),(.5,.575),(2,2)):
            self.assertEqual(plan_scale_findings(a,b),[])
        for a,b in ((1,1.150001),(1.150001,1),(.499999,.499999),(2.000001,2.000001)):
            self.assertTrue(plan_scale_findings(a,b))
        for v in (True,0,-1,float('inf'),float('nan'),'1'):
            with self.assertRaises(ValueError):plan_scale_findings(v,1)

    def test_measured_whole_desk_exact_fit_and_height_independent_of_plan(self):
        model=self.model();before=deepcopy(model)
        fit=self.fit(model,height_m=.8)
        self.assertTrue(fit['ok']);self.assertEqual(fit['sx'],1);self.assertEqual(fit['sy'],1)
        self.assertAlmostEqual(fit['sz'],.8/.75)
        self.assertAlmostEqual(fit['overall_height_m'],.8)
        self.assertEqual(model,before)

    def test_seat_height_drives_vertical_not_overall_back_height(self):
        model=self.model('task_chair')
        model['review_geometry']['meshes']=[dict(name='body',faces=self.box((-.22,-.225,0),(.22,.225,1))),
                                           dict(name='seat',faces=self.box((-.2,-.2,.4),(.2,.2,.5)))]
        fit=fit_furniture(model,.44,.45,height_parts=['seat'],height_m=.46,
                          height_source='design: seat height',height_basis='design')
        self.assertTrue(fit['ok']);self.assertAlmostEqual(fit['sz'],.92)
        self.assertAlmostEqual(fit['overall_height_m'],.92)
        for name in ('back','renamed-other-chair-back'):
            constraints={name:dict(parts=['body'],height_m=.85,
                                  height_source='design: chair back',height_basis='design')}
            bad=fit_furniture(model,.44,.45,height_parts=['seat'],height_m=.46,
                             height_source='design: seat height',height_basis='design',
                             height_constraints=constraints)
            self.assertFalse(bad['ok']);self.assertIn('height',bad['reason'])
            constraints[name]['height_m']=.92
            good=fit_furniture(model,.44,.45,height_parts=['seat'],height_m=.46,
                              height_source='design: seat height',height_basis='design',
                              height_constraints=constraints)
            self.assertTrue(good['ok'])

    def test_units_convert_separately_from_plan_and_height(self):
        model=self.model()
        for row in model['review_geometry']['meshes']:
            row['faces']=[[[100*v for v in p] for p in face] for face in row['faces']]
        model['unit_evidence']=dict(unit='cm',source='Author states centimetres')
        fit=self.fit(model)
        self.assertEqual(fit['source_unit_factor'],.01)
        for v in fit['scale_xyz']:self.assertAlmostEqual(v,.01)
        for evidence in ({},dict(unit='cm',source=''),dict(unit='guessed',source='target')):
            with self.assertRaises(ValueError):unit_scale(evidence)

    def test_front_and_depth_axes_and_translated_geometry(self):
        model=self.model();base=self.fit(model)
        for row in model['review_geometry']['meshes']:
            row['faces']=[[[p[0]+8,p[1]-11,p[2]+3] for p in f] for f in row['faces']]
        translated=self.fit(model)
        for key in ('sx','sy','sz'):self.assertAlmostEqual(base[key],translated[key])
        native=dict(min=[0,0,0],max=[.6,.75,1.4])
        for sign in ('+X','-X'):
            swapped=fit_factors(native,1.4,.6,sign,height_bounds=native,height_m=.75,height_source='design')
            self.assertEqual(swapped['scale_xyz'],[1.,1.,1.])
        for front in (None,'+Y','unknown'):
            bad=self.model();bad['front_axis']=front
            with self.assertRaises(ValueError):self.fit(bad)

    def test_contents_omit_only_separable_recorded_extras_and_fused_refuse(self):
        for role in ('desk','task_chair','chair','unrelated-item'):
            model=self.model(role);original=self.fit(model)
            model['review_geometry']['meshes'].append(dict(name='separate-lamp',faces=self.box((20,20,0),(21,21,1))))
            model['contents_review']['extras']=['separate-lamp']
            with self.assertRaisesRegex(ValueError,'every accessory'):self.fit(model)
            model['omitted_meshes']=['separate-lamp']
            self.assertEqual(self.fit(model),original)
            model['contents_review']['fused_extras']=['fused rug']
            with self.assertRaisesRegex(ValueError,'fused extras'):self.fit(model)
        for status in ('bed-only','pending','inseparable-extras'):
            model=self.model();model['contents_review']['status']=status
            with self.assertRaisesRegex(ValueError,'item-only'):self.fit(model)

    def test_missing_height_provenance_or_geometry_refuses(self):
        for kwargs in (dict(height_basis='guess'),dict(height_source=' '),dict(height_parts=[]),
                       dict(height_parts=['unmeasured']),dict(height_parts=['top','top']),
                       dict(height_m=0),dict(height_m=True)):
            with self.assertRaises(ValueError):self.fit(**kwargs)
        self.assertTrue(self.fit(height_basis='citation',height_source='Read publication, edition and printed page')['ok'])
        bad=self.model();bad['contents_review']={}
        with self.assertRaises(ValueError):self.fit(bad)
        for row in ([],[dict(faces=[[[0,0,float('nan')]]])]):
            with self.assertRaises(ValueError):native_box(row)

    def test_duplicate_unknown_or_all_omitted_parts_refuse(self):
        for omitted in (['unknown'],['top','top'],['top','body']):
            model=self.model();model['omitted_meshes']=omitted;model['contents_review']['extras']=omitted
            with self.assertRaises(ValueError):self.fit(model)
        model=self.model();model['review_geometry']['meshes'].append(deepcopy(model['review_geometry']['meshes'][0]))
        with self.assertRaises(ValueError):retained_model_rows(model)

    def test_real_bed_factors_and_fused_extras_use_shared_control(self):
        from archpipe.beds import scaled_model_fit
        models=json.loads((ROOT/'tests/fixtures/bed-round5-measurements.json').read_text())
        for model in models:
            self.assertTrue(scaled_model_fit(model)['ok'])
            bad=deepcopy(model);bad['contents_review']['fused_extras']=['fused desk']
            with self.assertRaises(ValueError):scaled_model_fit(bad)
        worst=next(r for r in json.loads((ROOT/'tests/fixtures/bed-round4-measurements.json').read_text())
                   if r['asset']=='sf_bed3_0e134823')
        size=[b-a for a,b in zip(worst['mattress_bounds']['lower']['min'],worst['mattress_bounds']['lower']['max'])]
        self.assertTrue(plan_scale_findings(.9/size[2],2/size[0]))

    def test_real_bed_empty_units_legacy_default_and_generic_strict(self):
        from archpipe.beds import scaled_model_fit, unit_scale as bed_units
        models=json.loads((ROOT/'tests/fixtures/bed-round5-measurements.json').read_text())
        for model in models:
            baseline=scaled_model_fit(model)
            for name in (model['id'],'another-house-renamed-bed'):
                sibling=deepcopy(model);sibling['id']=name;sibling['unit_evidence']={}
                self.assertEqual(scaled_model_fit(sibling)['scale_xyz'],baseline['scale_xyz'])
                sibling['unit_evidence']=dict(unit='cm',source='')
                with self.assertRaises(ValueError):scaled_model_fit(sibling)
        self.assertEqual(bed_units({}),1)
        with self.assertRaises(ValueError):unit_scale({})
        for model in models:
            actual=dict(unit='m',source='glTF 2.0 metres; downloaded files unmodified')
            model['unit_evidence']=MappingProxyType(actual)
            self.assertTrue(scaled_model_fit(model)['ok'])
            self.assertEqual(unit_scale(MappingProxyType(actual)),1)
        for evidence in (MappingProxyType({'unit':'cm','source':''}),[], 'metres'):
            with self.assertRaises(ValueError):unit_scale(evidence)

    def test_inventory_matches_furnishing_data(self):
        inventory=runpy.run_path(str(ROOT/'scripts/inventory_desks.py'))['inventory']()
        recorded=json.loads((ROOT/'docs/desks-inventory.json').read_text())
        self.assertEqual(inventory,recorded)
        self.assertEqual(inventory,json.loads(json.dumps(inventory)))
        cinema=next(r for r in inventory['items'] if r['id']=='cinema-desk')
        self.assertEqual(cinema['world_footprint_m'],[4.66,-21.351,5.9,-20.801000000000002])
        self.assertTrue(all(type(r['world_footprint_m']) is list for r in inventory['items']))
        self.assertEqual(inventory['counts'],dict(desks=7,task_chairs=8,vanity_chairs=1))
        self.assertEqual(len({r['id'] for r in inventory['items']}),16)

    def test_shortlist_has_permitted_licences_credit_and_complete_type_coverage(self):
        inventory=json.loads((ROOT/'docs/desks-inventory.json').read_text())
        shortlist=json.loads((ROOT/'docs/desks-candidates.json').read_text())
        expected={r['id'] for r in inventory['items'] if r['type'] in ('desk','task_chair')}
        self.assertEqual({i for t in shortlist['types'].values() for i in t['item_ids']},expected)
        self.assertEqual(shortlist['search']['model_downloads'],0)
        self.assertFalse(shortlist['search']['authentication_used'])
        for group in shortlist['types'].values():
            self.assertLessEqual(len(group['candidates']),3)
            if not group['candidates']:self.assertTrue(group['search_gap'])
            for row in group['candidates']:
                self.assertIn(row['licence'],('CC Attribution','CC0 Public Domain'))
                self.assertTrue(row['downloadable'])
                self.assertEqual(len(row['uid']),32)
                self.assertIn(row['uid'],row['url'])
                self.assertIn(row['author'],row['credit'])
                self.assertTrue(row['item_only_screen'])


if __name__=='__main__':
    unittest.main()
