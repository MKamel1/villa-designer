"""Frozen committed naming/solar failures and independent scene-ray evidence."""
import copy
import gzip
import json
import math
from datetime import datetime,timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import numpy as np
from archpipe import orientation as O, solar, villa_env as E
from archpipe.orientation_guard import scene_findings, document_findings, geometry_side
from archpipe.concept import villa_render as V,villa_landscape as L
from archpipe.concept.garden_sun import SunStudy,DATES


class Orientation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=json.loads(gzip.decompress(Path('tests/fixtures/orientation-before.json.gz').read_bytes()))
        cls.scene=V.build()
        cls.study=SunStudy(cls.scene)

    def test_committed_names_fail_and_current_names_stay_quiet(self):
        before=dict(meshes=self.before['meshes'],props=self.before['props'],views=self.before['views'])
        findings=scene_findings(before)
        self.assertIn('landscape-bed-west',str(findings))
        self.assertIn('v36-west-court',str(findings))
        self.assertEqual(scene_findings(self.scene),[])
        # Frozen evidence is unchanged; aliases are an explicit recorded operation.
        migrated=O.historical_aliases(before)
        self.assertIn('label',str(scene_findings(dict(migrated,views=[]))), 'ID aliases must not hide historical wrong labels')
        self.assertTrue(scene_findings(migrated), "ID aliases must not hide historical caption failures")
        self.assertEqual(self.before['plan']['beds'].keys(),{'west','north'})

    def test_names_generalise_to_translated_geometry_and_mutated_text(self):
        sibling=copy.deepcopy(self.scene)
        for m in sibling['meshes']:
            m['faces']=[[[p[0]+40,p[1]-13,p[2]] for p in f] for f in m['faces']]
        for p in sibling['props']:p['position'][0]+=40;p['position'][1]-=13
        for v in sibling['views']:
            if v.get('camera'):
                for key in ('position','target'):
                    if key in v['camera']:v['camera'][key][0]+=40;v['camera'][key][1]-=13
        sibling['garden_zones']={name:[rect[0]+40,rect[1]-13,rect[2]+40,rect[3]-13] for name,rect in sibling['garden_zones'].items()}
        bounds=tuple(v/1000 for v in E.BAR);bounds=(bounds[0]+40,bounds[1]-13,bounds[2]+40,bounds[3]-13)
        top=(L.TOP[0]+40,L.TOP[1]-13,L.TOP[2]+40,L.TOP[3]-13)
        self.assertEqual(scene_findings(sibling,building_bounds=bounds,top_bounds=top),[])
        bed=next(m for m in sibling['meshes'] if m['id']=='landscape-bed-north')
        bed['id']='landscape-bed-w'
        self.assertIn('expected north',str(scene_findings(sibling,building_bounds=bounds,top_bounds=top)))
        mutant=copy.deepcopy(self.scene)
        v=next(v for v in mutant['views'] if v['id']=='v36-north-garden')
        v['caption_notes'][0]='West garden with shade foliage'
        self.assertIn('caption',str(scene_findings(mutant)))
        v['title']='West garden'
        self.assertIn('title',str(scene_findings(mutant)))
        with TemporaryDirectory() as tmp:
            p=Path(tmp)/'garden.md';p.write_text('<!-- garden-side: -x; name: west -->\nWest court')
            self.assertTrue(document_findings([p]))
            p.write_text('<!-- garden-side: -x; name: north -->\nNorth garden')
            self.assertEqual(document_findings([p]),[])
            p.write_text('| West bed | (-.05, -28.5, 3.45, -26.9) |'.replace('(-.05','(-0.05'))
            self.assertIn('coordinate table',str(document_findings([p])))
            p.write_text('| North bed | (-0.05, -28.5, 3.45, -26.9) |')
            self.assertEqual(document_findings([p]),[])
        self.assertEqual(document_findings(),[])
        self.assertEqual(O.side_name('-x'),'north');self.assertEqual(O.side_name('+y'),'east')

    def test_true_sun_rotation_and_actual_changed_enclosure(self):
        self.assertEqual(E.STREET_FACADE_AZIMUTH,O.record()["true_north"]["street_facade_azimuth"])
        direction=O.sun_direction(20,45)
        np.testing.assert_allclose(direction,(0,2**-.5,2**-.5),atol=1e-12)
        open_scene=dict(meshes=[dict(id='ground',group='ground',material='opaque',faces=L._quad(-20,-20,20,20,-3))],materials={'opaque':{'kind':'principled'}})
        from archpipe.concept.garden_sun import scene_findings as sun_findings
        self.assertEqual(sun_findings(open_scene),[])
        landscape=copy.deepcopy(next(p for p in self.scene['props'] if p.get('species')=='Plumeria rubra'))
        landscape['id']='renamed-plant'
        self.assertIn('no recorded garden sun evidence',str(sun_findings(dict(open_scene,props=[landscape]))))
        open_study=SunStudy(open_scene)
        point=(0,0,-2.95);self.assertTrue(open_study.clear(point,(0,1,1)))
        wall=dict(id='actual-wall',group='context',material='opaque',faces=L._box(-2,1,-3,2,1.25,12))
        blocked=SunStudy(dict(open_scene,meshes=open_scene['meshes']+[wall]))
        self.assertFalse(blocked.clear(point,(0,1,1)))
        self.assertNotEqual(blocked.geometry_sha256,open_study.geometry_sha256)
        self.assertEqual(len(open_study.hours(0,0)),sum(solar.sun_position(datetime(2026,6,21,h)-__import__('datetime').timedelta(hours=E.TIME_ZONE),E.LATITUDE,E.LONGITUDE).altitude>0 for h in range(24)))
        with self.assertRaisesRegex(ValueError,'true north'):SunStudy(dict(open_scene,north={'model_y_bearing_deg':0}))

    def test_real_scene_reproduces_lead_and_old_proxy_disagrees(self):
        # Predeclared tolerance: half of the one-hour step, not fit to outcomes.
        tolerance=.5
        reference=json.loads(Path('tests/fixtures/orientation-sun-reference.json').read_text())
        zones={'north':(-.123,-28.671,3.617,-23.591),'south':(22.597,E.AXIS_Y/1000,28.307,-20.601)}
        measured={}
        for name,rect in zones.items():
            points=[(float(x),float(y)) for x in np.arange(rect[0]+.5,rect[2],1) for y in np.arange(rect[1]+.5,rect[3],1)]
            self.assertEqual(len(points),20 if name=='north' else 54)
            measured[name]={d:float(np.mean([len(self.study.hours(x,y,-3,d)) for x,y in points])) for d in DATES}
        self.assertAlmostEqual(measured['north'][DATES[0]],reference['NORTH garden (street side), open part'][1]['21 Jun'][1],delta=tolerance)
        for day,key in ((DATES[0],'21 Jun'),(DATES[2],'21 Dec')):
            self.assertAlmostEqual(measured['south'][day],reference['SOUTH garden (rear)'][1][key][1],delta=tolerance)
        # Execute the committed proxy by value; never import current implementation.
        scope=dict(solar=solar,datetime=datetime,timezone=timezone,E=E,BUILDING_HEIGHT=3,inside_yard=L.inside_yard,
                   sin=math.sin,cos=math.cos,radians=math.radians,tan=math.tan)
        exec(self.before['legacy_sun_source'],scope)
        rect=zones['north'];old=[len(scope['direct_sun_hours'](float(x),float(y))) for x in np.arange(rect[0]+.5,rect[2],1) for y in np.arange(rect[1]+.5,rect[3],1)]
        self.assertGreater(np.mean(old)-measured['north'][DATES[0]],1.)

    def assert_rename_snapshot(self, scene):
        # Keep the frozen baseline. Later decisions permit only exact material
        # transitions, never geometry, transforms or arbitrary current values.
        changes=json.loads(Path('tests/fixtures/orientation-approved-appearance-changes.json').read_text())
        approved={}
        for row in changes:
            self.assertEqual(row['field'],'material')
            self.assertTrue(row['decision'])
            key=(row['item_id'],row['field'])
            self.assertNotIn(key,approved)
            approved[key]=row
        used=set()
        old=O.historical_aliases(dict(meshes=self.before['meshes'],props=self.before['props']))
        for kind in ('meshes','props'):
            current={m['id']:m for m in scene[kind]}
            for item in old[kind]:
                # Existing G6 scope: replanted east/south assemblies have their
                # own fixed-geometry proofs; retained gardens/tree stay here.
                if item.get('zone')!='top' and item.get('id')!='landscape-tree-south' and (item['id'].startswith(('landscape-east-','landscape-bed-east','landscape-grass-east','landscape-grass-south','landscape-climber-east','landscape-climber-branches-east','landscape-trellis-east','landscape-door-pot-'))):continue
                new=current[item['id']]
                for field in ('faces','position','scale','rotation_deg','material'):
                    if field not in item:continue
                    key=(item['id'],field)
                    if key in approved:
                        row=approved[key]
                        np.testing.assert_equal(item[field],row['old'])
                        np.testing.assert_equal(new[field],row['new'])
                        used.add(key)
                    else:
                        np.testing.assert_equal(new[field],item[field],err_msg=str(key))
                if item.get('part_kind') in ('climber','climber-branch'):
                    self.assertEqual(new['appearance_seed'],O.appearance_seed(new['id']))
        self.assertEqual(used,set(approved),'stale or mistyped approved transition')

    def test_unlisted_appearance_and_geometry_changes_still_fail(self):
        # Mutate actual current items without copying the entire large scene.
        self.assert_rename_snapshot(self.scene)
        for item_id,field in (('landscape-stone-lounge-north-end-0','material'),
                              ('landscape-gravel-north','material'),
                              ('landscape-stone-lounge-north-end-0','faces')):
            original=next(m for m in self.scene['meshes'] if m['id']==item_id)
            changed=copy.deepcopy(original)
            if field=='material':changed[field]='unlisted-finish'
            else:changed['faces'][0][0][0]+=.001
            mutant=dict(self.scene,meshes=[changed if m['id']==item_id else m for m in self.scene['meshes']])
            with self.assertRaises(AssertionError):self.assert_rename_snapshot(mutant)
        # An item absent from the decision must still compare to the baseline.
        old=O.historical_aliases(dict(meshes=self.before['meshes'],props=[]))
        source=next(m for m in old['meshes'] if m.get('part_kind')=='climber')
        original=next(m for m in self.scene['meshes'] if m['id']==source['id'])
        changed=dict(original,material='unlisted-finish')
        mutant=dict(self.scene,meshes=[changed if m['id']==source['id'] else m for m in self.scene['meshes']])
        with self.assertRaises(AssertionError):self.assert_rename_snapshot(mutant)

    def test_rename_preserves_actual_geometry_and_climber_appearance(self):
        self.assert_rename_snapshot(self.scene)
        from archpipe.concept.garden_sun import scene_findings as sun_findings
        self.assertEqual(sun_findings(self.scene),[])
        mutated=copy.deepcopy(self.scene)
        mutated['garden_sun_evidence']['plants'][0]['sunlit_local_standard_hours'][DATES[0]]=[9,10,11,12,13,14,15,16,17]
        self.assertTrue(sun_findings(mutated))
        mutated['garden_sun_evidence']['plants'].pop()
        self.assertIn('every actual landscape plant',str(sun_findings(mutated)))
        evidence=self.scene['garden_sun_evidence']['plants']
        self.assertEqual(len(evidence),len({r["id"] for r in evidence}))
        self.assertTrue(all(set(p['sunlit_local_standard_hours'])==set(DATES) for p in evidence))
        self.assertTrue(any(p['species']=='Ixora coccinea' and p['status']=='MISMATCH' for p in evidence))
        self.assertFalse(any(p['species'] in ('Bougainvillea glabra','Strelitzia reginae') and p['zone']=='east' for p in evidence))
        self.assertTrue(any(p['species']=='Trachelospermum jasminoides' and p['zone']=='east' for p in evidence))

if __name__=='__main__':unittest.main()
