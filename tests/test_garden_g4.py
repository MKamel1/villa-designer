from archpipe.orientation import historical_aliases
"""G4 real frozen contents, independent shape failures and court generalisation."""
import copy,gzip,hashlib,json
from pathlib import Path
import unittest
from unittest.mock import patch
from archpipe.concept import villa_landscape as L, garden_shade as G,villa_r11 as R,revit_spec as RS

class NorthShade(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lay=R.design('D1');cls.spec=RS.build(cls.lay)
        cls.meshes,cls.props,_,cls.plan=L.review_candidate(cls.spec,cls.lay)
        cls.frozen=historical_aliases(json.loads(gzip.decompress(Path('tests/fixtures/garden-g4-before.json.gz').read_bytes())))

    def test_g4_frozen_bistro_pots_shade_and_translated_court(self):
        before=self.frozen
        failures=L.north_garden_violations(before['meshes'],before['props'],before['objects'])
        ids={f[0] for f in failures}
        self.assertIn('landscape-north-bistro',ids)
        self.assertIn('landscape-door-pot-planter-lounge-north-w-body',ids)
        self.assertIn('landscape-door-pot-planter-lounge-north-e-body',ids)
        self.assertEqual(L.north_garden_violations(self.meshes,self.props,self.plan['objects']),[])
        # Same defect on another plot, with renamed items and another floor.
        meshes=copy.deepcopy(before['meshes']);props=copy.deepcopy(before['props'])
        for m in meshes:
            m['id']='other-'+m['id']
            for f in m['faces']:
                for q in f:q[0]+=9;q[1]-=7;q[2]+=4
        for p in props:p['id']='other-'+p['id'];p['position']=[p['position'][0]+9,p['position'][1]-7,p['position'][2]+4]
        court=(L.NORTH_COURT[0]+9,L.NORTH_COURT[1]-7,L.NORTH_COURT[2]+9,L.NORTH_COURT[3]-7)
        self.assertTrue(L.north_garden_violations(meshes,props,court=court,ground=1,balcony_edge=L.NORTH_BALCONY_EDGE-7))
        mutant=copy.deepcopy(next(m for m in self.meshes if m['part_kind']=='soil-bed'))
        for f in mutant['faces']:
            for q in f:q[2]+=.15
        self.assertIn('ground level',str(L.north_garden_violations([mutant],[])))
        bad=copy.deepcopy(next(m for m in self.meshes if m.get('species')=='Fatsia japonica'))
        for f in bad['faces']:
            for q in f:q[1]-=2
        self.assertIn('only Aspidistra',str(L.north_garden_violations([bad],[])))
        # A flagged swing under architectural cover is still refused.
        from shapely.geometry import box
        swing=self.frozen['swing'];self.assertIn('open to sky',str(L.north_garden_violations([], [swing],cover=box(*L.NORTH_COURT))))
        unflagged=dict(swing,label='new seat');self.assertTrue(L.north_garden_violations([], [unflagged]))
        with patch.object(L,'north_garden_violations',return_value=[('other','raised soil')]):
            with self.assertRaisesRegex(ValueError,'raised soil'):L.build(self.spec,self.lay)

    def test_g4_other_gardens_unchanged_and_counts_spacing(self):
        # Old hashes include deliberately renamed metadata and obsolete sun
        # arrays. Preserve the fixture hashes and compare actual geometry with
        # the frozen committed pre-rename input by explicit recorded aliases.
        baseline=historical_aliases(json.loads(gzip.decompress(Path('tests/fixtures/orientation-before.json.gz').read_bytes())))
        for kind,items in [('meshes',self.meshes),('props',self.props),('objects',self.plan['objects'])]:
            frozen_items=baseline['plan']['objects'] if kind=='objects' else baseline[kind]
            by_id={m['id']:m for m in frozen_items}
            for item in items:
                if L._rect_overlap_area(L._rect(item),L.NORTH_COURT)>1e-6:continue
                for field in ('faces','rect','position','scale','rotation_deg','material'):
                    if field in item:
                        self.assertEqual(json.loads(json.dumps(item[field])),by_id[item['id']][field])
            self.assertTrue(self.frozen['unchanged_hashes'][kind])
        plants=[m for m in self.plan['plants'] if m.get('bed') in ('north','north-accent')]
        counts={species:sum(p['species']==species for p in plants) for species in set(p['species'] for p in plants)}
        self.assertEqual(counts,{'Fatsia japonica':3,'Aspidistra elatior':3,'Chlorophytum comosum':3,'Ophiopogon japonicus':5,'Rhapis excelsa':1})
        self.assertEqual(L.spacing_violations(plants),[]);self.assertEqual(L.layer_violations(plants,{'north':self.plan['beds']['north']}),[])
        self.assertEqual(L.drift_violations(plants,layers=('back','mid','front','edge')),[])
        self.assertEqual(self.plan['swing']['decision'],'client decision 2026-10-06; structural check pending')
        self.assertTrue(all(min(q[1] for f in p['faces'] for q in f)>=L.NORTH_BALCONY_EDGE for p in plants))
        self.assertEqual(L.require_species('Cissus alata')['light']['status'],'PARTIAL')
        self.assertEqual(L.require_species('Ophiopogon japonicus')['light']['status'],'PARTIAL')

    def test_g4_real_shape_preview_failures_and_clean_mutations(self):
        before=historical_aliases(json.loads(gzip.decompress(Path('tests/fixtures/garden-g4-form-before.json.gz').read_bytes())))
        failures=G.form_findings(before['meshes']);self.assertTrue(any('palmate' in f for f in failures));self.assertTrue(any('tiers' in f for f in failures));self.assertTrue(any('pointed' in f for f in failures));self.assertTrue(any('stone rings' in f for f in failures))
        self.assertEqual(G.form_findings(self.meshes),[])
        fatsia=copy.deepcopy(next(m for m in self.meshes if m.get('species')=='Fatsia japonica'))
        del fatsia['palmate_laminae'];self.assertTrue(G.form_findings([fatsia]))
        rhapis=copy.deepcopy(next(m for m in self.meshes if m.get('species')=='Rhapis excelsa'))
        for n in rhapis['crown_nodes']:n['point'][2]=.1
        self.assertTrue(any('tiers' in f for f in G.form_findings([rhapis])))
        for m in before['meshes']:m['id']='renamed-appearance'
        self.assertTrue(G.form_findings(before['meshes']))

    def test_g4_real_floating_ivy_and_connected_geometry(self):
        from archpipe.blender.climber_placement import grape_ivy_geometry,ivy_connection_findings
        vine=next(m for m in self.meshes if m.get('species')=='Cissus alata' and m['part_kind']=='climber')
        stem=next(m for m in self.meshes if m['id']==vine['stem_mesh'])
        points=[q for f in vine['faces'] for q in f]
        bounds=[min(q[k] for q in points) for k in range(3)]+[max(q[k] for q in points) for k in range(3)]
        leaves,petioles,contacts=grape_ivy_geometry(bounds,stem['faces'],sum(map(ord,vine['id'])))
        self.assertEqual(ivy_connection_findings(leaves,petioles,stem['faces']),[])
        self.assertTrue(ivy_connection_findings(leaves,[],stem['faces']))
        translated=lambda faces:[[[q[0]+8,q[1]-5,q[2]+4] for q in f] for f in faces]
        self.assertEqual(ivy_connection_findings(translated(leaves),translated(petioles),translated(stem['faces'])),[])
        detached=translated(petioles)
        self.assertTrue(ivy_connection_findings(leaves,detached,stem['faces']))
        with self.assertRaisesRegex(ValueError,'physical training'):grape_ivy_geometry(bounds,[])
        from archpipe.concept.physical_part import Part
        for i in range(0,len(petioles),8):Part('climber-branch',petioles[i:i+8],('x','y','z'),'trellis','authored-procedural')

    def test_g4_first_plant_door_failure_is_now_early_and_quiet(self):
        from archpipe.concept.render_support import blocked_openings
        old=self.frozen['first_fix_blocked_mesh']
        self.assertTrue(blocked_openings({'meshes':[old]},self.lay))
        renamed=copy.deepcopy(old);renamed['id']='another-wide-foliage'
        self.assertTrue(blocked_openings({'meshes':[renamed]},self.lay))
        self.assertEqual(blocked_openings({'meshes':self.meshes},self.lay),[])
        mutated=self.meshes+[renamed]
        self.assertIn('another-wide-foliage',str(L.candidate_violations(mutated,self.props,self.plan,self.lay)))
        self.assertTrue(any(not L.inside_yard(q[0],q[1]) for f in self.frozen['first_fix_gravel']['faces'] for q in f))
        gravel=next(m for m in self.meshes if m['id']=='landscape-gravel-north')
        self.assertTrue(all(L.inside_yard(q[0],q[1]) for f in gravel['faces'] for q in f))

    def test_g4_actual_coplanar_paving_soil_visibility_generalises(self):
        from archpipe.concept.garden_render_review import soil_visibility_findings
        scene=copy.deepcopy(self.frozen['covered_soil_scene'])
        self.assertEqual(len(soil_visibility_findings(scene)),2)
        soils=[m for m in scene['meshes'] if m['part_kind']=='soil-bed']
        shell=[m for m in scene['meshes'] if m['part_kind']!='soil-bed']
        L.reveal_ground_soil(shell,soils)
        self.assertEqual(soil_visibility_findings(scene),[])
        # Same geometry at another place/floor, with no D1 identifiers.
        sibling=copy.deepcopy(self.frozen['covered_soil_scene'])
        for m in sibling['meshes']:
            m['id']='other-'+m['id']
            for face in m['faces']:
                for q in face:q[0]+=11;q[1]-=7;q[2]+=4
        self.assertTrue(soil_visibility_findings(sibling))
        L.reveal_ground_soil([m for m in sibling['meshes'] if m['part_kind']!='soil-bed'],[m for m in sibling['meshes'] if m['part_kind']=='soil-bed'])
        self.assertEqual(soil_visibility_findings(sibling),[])
        # A buried substrate is permitted; a covering finish is refused.
        raised=copy.deepcopy(self.frozen['covered_soil_scene'])
        for face in raised['meshes'][0]['faces']:
            for q in face:q[2]+=.005
        self.assertTrue(soil_visibility_findings(raised))
        buried=copy.deepcopy(self.frozen['covered_soil_scene'])
        for face in buried['meshes'][0]['faces']:
            for q in face:q[2]-=.05
        self.assertEqual(soil_visibility_findings(buried),[])

    def test_g4_generic_photometry_writes_only_explicit_exports(self):
        from archpipe.concept import villa_render as V,villa_lighting as VL
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        # Exact old write branch: preserve source by value and redirect the
        # shared symlink reproduction into a disposable directory.
        with TemporaryDirectory() as tmp:
            root=Path(tmp);shared=root/'shared';shared.mkdir();link=root/'output';link.symlink_to(shared,target_is_directory=True)
            code=self.frozen['old_generic_write_branch']
            namespace=dict(OUT=link,VL=VL,products=VL.products())
            exec(compile('def old_build_write():\n'+code+'\nold_build_write()','frozen-shared-write','exec'),namespace)
            self.assertTrue((shared/'ies/generic/DESK.ies').is_file())
            with patch.object(V,'OUT',link),patch.object(Path,'write_text',side_effect=AssertionError('build wrote a file')),patch.object(Path,'write_bytes',side_effect=AssertionError('build wrote a file')):
                scene=V.build(views=[])
            self.assertTrue(any(l.get('ies')=='generic/DESK.ies' for l in scene['lights']))
            stamp=(shared/'ies/generic/DESK.ies').stat().st_mtime_ns
            V.write(root/'private/scene.json')
            self.assertEqual((shared/'ies/generic/DESK.ies').stat().st_mtime_ns,stamp)
            self.assertEqual((root/'private/ies/generic/DESK.ies').read_text(),(shared/'ies/generic/DESK.ies').read_text())
            self.assertEqual((shared/'ies/generic/DESK.ies').read_text(),VL.generic_ies(VL.KINDS['DESK']['lm'],VL.KINDS['DESK']['beam'],'DESK'))
