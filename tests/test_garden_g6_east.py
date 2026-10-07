"""By-value G5 planting failure and G6 east-yard replacement proofs."""
import copy
import json
from pathlib import Path
import unittest

from archpipe.concept import garden_g6_east as G, villa_landscape as L
from archpipe.concept.garden_sun import DATES, default_study
from archpipe.concept.physical_part import geometry_errors
from archpipe.concept.garden_render_review import plant_form_findings


class EastG6(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=L._plant_data()
        cls.meshes,cls.plants,cls.beds,cls.report=G.build()
        cls.old=json.loads((Path(__file__).parent/'fixtures/garden-g6-east-before.json').read_text())['plants']

    def test_real_committed_sun_mismatch_and_identifier_sibling(self):
        findings=G.quote_match_findings(self.old)
        by_id={p['id']:p['species'] for p in self.old}
        self.assertEqual({by_id[identifier] for identifier,_ in findings},
                         {'Bougainvillea glabra','Ixora coccinea','Strelitzia reginae'})
        sibling=copy.deepcopy(self.old)
        for p in sibling:p['id']='another-project-'+p['id'];p['bed']='renamed-bed'
        self.assertEqual(len(G.quote_match_findings(sibling)),len(findings))
        self.assertEqual(G.quote_match_findings(self.plants),[])

    def test_general_guard_refuses_real_species_mutation_and_missing_quote(self):
        plant=copy.deepcopy(next(p for p in self.plants if p['species']=='Fatsia japonica'))
        plant['species']='Strelitzia reginae';plant['id']='independent-plant'
        self.assertIn('>6',G.quote_match_findings([plant])[0][1])
        data=copy.deepcopy(self.data);data['Fatsia japonica']['light']['status']='UNVERIFIED'
        clean=next(p for p in self.plants if p['species']=='Fatsia japonica')
        self.assertIn('missing',G.quote_match_findings([clean],data=data)[0][1])

    def test_any_zone_and_moved_geometry_use_live_sun_not_identity(self):
        class Study:
            def __init__(self,count):self.count=count
            def hours(self,*args):return list(range(self.count))
        source=dict(id='new-villa-species',species='Strelitzia reginae',center=[100,200],bed='remote-ground')
        self.assertTrue(G.quote_match_findings([source],study=Study(6)))
        self.assertEqual(G.quote_match_findings([source],study=Study(7)),[])
        source['species']=G.MONA
        self.assertTrue(G.quote_match_findings([source],study=Study(1)))
        self.assertEqual(G.quote_match_findings([source],study=Study(2)),[])

    def test_complete_three_layer_drifts_spacing_routes_and_ground(self):
        self.assertEqual({p['species'] for p in self.plants},
                         {'Fatsia japonica','Aspidistra elatior',G.DWARF,G.MONA,G.JASMINE})
        self.assertEqual(L.layer_violations(self.plants,beds=('east',)),[])
        self.assertEqual(L.drift_violations(self.plants,layers=('back','mid','front','edge')),[])
        self.assertEqual(L.spacing_violations(self.plants),[])
        self.assertEqual(L.route_violations(self.meshes,L.PATHS),[])
        self.assertEqual(plant_form_findings(self.meshes),[])
        for mesh in self.meshes:
            self.assertEqual(geometry_errors(mesh['faces'],surface=mesh.get('surface',False),occupied_side=mesh.get('occupied_side')),[],mesh['id'])
        for p in self.plants:self.assertAlmostEqual(min(v[2] for f in p['faces'] for v in f),L.GROUND)

    def test_frame_stays_open_and_jasmine_geometry_is_explicit(self):
        vine=next(p for p in self.plants if p['species']==G.JASMINE)
        self.assertTrue(vine['explicit_geometry'])
        self.assertEqual(vine['frame_id'],'landscape-trellis-east')
        self.assertTrue(vine['leaf_connections'])
        self.assertGreater(vine['coverage_fraction'],0)
        self.assertLess(vine['coverage_fraction'],.5)  # Chosen young appearance keeps most timber visible.
        self.assertIn('whole timber frame',vine['coverage_denominator'])
        self.assertIn('g6-white-flower',vine['face_materials'])
        self.assertFalse(any(p['species'] in ('Ixora coccinea','Bougainvillea glabra','Strelitzia reginae') for p in self.plants))

    def test_real_sloped_basal_cap_failure_and_translated_sibling(self):
        frozen=json.loads((Path(__file__).parent/'fixtures/garden-g6-east-before.json').read_text())['jasmine_ground_before']
        real=dict(id=frozen['id'],root_z_m=frozen['root_z_m'],faces=frozen['first_stem_faces'])
        self.assertTrue(G.root_datum_findings([real]))
        sibling=copy.deepcopy(real);sibling['id']='other-villa-grounded-stem';sibling['root_z_m']+=7
        for face in sibling['faces']:
            for point in face:point[2]+=7
        self.assertTrue(G.root_datum_findings([sibling]))
        self.assertEqual(G.root_datum_findings(self.plants),[])
        mutant=copy.deepcopy(next(p for p in self.plants if p['species']==G.JASMINE))
        for face in mutant['faces']:
            for point in face:point[2]+=.01
        self.assertTrue(G.root_datum_findings([mutant]))

    def test_light_table_recomputes_live_dates_and_discloses_winter(self):
        study=default_study()
        for row in self.report:
            for day in DATES:
                self.assertEqual(row['sunlit_local_standard_hours'][day],study.hours(*row['center_m'],row['ground_m'],day))
            if row['species'] in (G.JASMINE,G.MONA):
                self.assertIn('Winter',row['seasonal_limits'])
            if row['species']==G.DWARF:
                self.assertEqual(row['status'],'SUPPORTED_BY_MIDSUMMER_SCREEN')
                self.assertIn('heavy shade',row['seasonal_limits'])
            if row['species']=='Aspidistra elatior':
                self.assertEqual(row['status'],'UNRESOLVED')
                self.assertIn('neighbouring foliage shade is excluded',row['reason'])

    def test_toxicity_absence_and_conflict_not_rewritten_as_safe(self):
        for name in ('Petrea volubilis',G.MONA):
            self.assertEqual(self.data[name]['human_toxicity']['status'],'NOT STATED')
            self.assertEqual(self.data[name]['source_evidence']['toxicity']['status'],'NOT STATED')
        jasmine=self.data[G.JASMINE]['human_toxicity']
        self.assertIn('Poisonous',jasmine['value']);self.assertIn('client accepted 2026-10-06',jasmine['value'])
        self.assertEqual(jasmine['details_status'],'NOT STATED')
        loquat=self.data['Eriobotrya japonica']
        self.assertIn('seeds only',loquat['human_toxicity']['value'])
        self.assertEqual(loquat['root_behaviour_over_basement_slab']['status'],'UNVERIFIED')
        self.assertIn('not a guarantee',loquat['source_evidence']['roots']['applicability'])

    def test_every_new_species_has_zone_quotes_url_and_explicit_envelope(self):
        for name in ('Petrea volubilis','Eriobotrya japonica','Pittosporum tobira',G.DWARF,G.MONA):
            row=self.data[name]
            self.assertIn('south garden (part sun)',row['zones']['value'])
            self.assertEqual(row['source_url']['status'],'VERIFIED')
            self.assertIn('source_evidence',row)
            self.assertEqual(row['egypt_performance']['status'],'UNVERIFIED')
        loquat=self.data['Eriobotrya japonica']
        self.assertGreater(loquat['height']['range_m'][0],6)
        self.assertEqual(loquat['placement_assumptions']['procedural-espalier']['height']['status'],'ASSUMED')
        record=json.loads(L.PALETTE.read_text())
        south=record['design_assumptions']['south_garden_g6']
        self.assertEqual(south['decision'],'lead decision 2026-10-06')
        self.assertIn('no-pots exception',south['bowl_reason'])
        self.assertTrue(all(f['status']=='ASSUMED' for f in south['field_evidence'].values()))


if __name__=='__main__':unittest.main()
