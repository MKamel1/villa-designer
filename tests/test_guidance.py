"""Evidence and approval failure cases, including real measured bedroom geometry."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from archpipe import guidance as g


class GuidanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root/'knowledge').mkdir()
        self.lib = json.loads((ROOT/'knowledge/library.json').read_text(encoding='utf-8'))
        self.project = json.loads((ROOT/'knowledge/projects/villa-pilot.json').read_text(encoding='utf-8'))
        self.save()

    def save(self):
        (self.root/'knowledge/library.json').write_text(json.dumps(self.lib), encoding='utf-8')
        (self.root/'project.json').write_text(json.dumps(self.project), encoding='utf-8')

    def review(self, stage):
        return g.review_stage(stage, 'project.json', self.root)

    def card(self):
        # Synthetic transcribed source to exercise checks, not architectural evidence.
        return dict(id='fixture', source_id='fixture', edition='test-1', locator='Table fixture, row A',
                    status='verified', category='professional_recommendation', unit='mm',
                    conditions='Synthetic test only', verification='Synthetic original checked',
                    applies_when={'climate':['hot-dry'], 'hemisphere':['north']},
                    original_page_checked=True, verified_value=750, regression_test='test fixture')

    def test_wrong_edition_units_and_misread_dimension(self):
        source = {'fixture': {'edition':'test-1','status':'content_verified'}}
        facts = {'climate':{'value':'hot-dry','status':'confirmed'},
                 'hemisphere':{'value':'north','status':'confirmed'}}
        card = self.card()
        self.assertTrue(g.numerical_target(card, source, 750, 'mm', facts)['enabled'])
        self.assertFalse(g.numerical_target(card, source, 75, 'mm', facts)['enabled'])
        self.assertFalse(g.numerical_target(card, source, 750, 'cm', facts)['enabled'])
        card['edition'] = 'test-2'
        self.assertFalse(g.numerical_target(card, source, 750, 'mm', facts)['enabled'])

    def test_climate_missing_and_qualitative_cannot_be_numeric(self):
        source = {'fixture': {'edition':'test-1','status':'content_verified'}}
        card = self.card()
        for climate in ('hot-humid', None):
            facts = {'climate':{'value':climate,'status':'confirmed'}}
            self.assertFalse(g.numerical_target(card, source, 750, 'mm', facts)['enabled'])
        card.update(category='qualitative_principle', applies_when={})
        self.assertFalse(g.numerical_target(card, source, 750, 'mm')['enabled'])

    def test_each_stage_has_usable_evidence_and_methods(self):
        data = g.library(ROOT)
        for stage in range(8):
            context = g.stage_context(stage)
            for key in ('method','worked_example','failures','deliverables','approval','questions'):
                self.assertTrue(context['package'][key])
            self.assertTrue(any(c['applicability']['status']=='applicable' for c in context['knowledge']))
            self.assertFalse(g.review_stage(stage)['approved'])
        self.assertTrue(all(not r['enabled_for_approval'] for r in g.rule_audit()))
        for row in g.rule_audit():
            self.assertTrue(row['evidence_refs'])
            self.assertTrue(all(ref in data['evidence'] for ref in row['evidence_refs']))

    def test_area_arithmetic_and_negative_cases(self):
        schedule = self.project['area_schedule']
        self.assertEqual(g.area_check(schedule)['gross_m2'], 370)
        schedule['available_m2'] = 360
        self.assertEqual(g.area_check(schedule)['status'], 'fail')
        for value in (-1, float('nan'), True):
            schedule['walls_m2'] = value
            with self.assertRaises(ValueError):
                g.area_check(schedule)

    def test_pretty_pavilion_still_fails_privacy_structure_comfort(self):
        checks = g.concept_checks(self.project['concepts'][2])
        self.assertEqual(checks[0]['status'], 'fail')
        self.assertEqual(checks[1]['status'], 'unresolved')
        self.assertEqual(checks[2]['status'], 'unresolved')
        self.assertEqual(g.concept_checks(self.project['concepts'][0])[0]['status'], 'pass')

    def test_drawn_arrival_does_not_cross_private_block_before_hall(self):
        import xml.etree.ElementTree as ET
        from shapely.geometry import LineString, box
        diagram = ET.parse(ROOT/'docs/guidance/pilot-concepts.svg')
        private = diagram.find('.//*[@id="garden-bar-private"]').attrib
        x, y, width, height = (float(private[key]) for key in ('x','y','width','height'))
        room = box(x,y,x+width,y+height)
        route = diagram.find('.//*[@id="garden-bar-arrival"]').attrib['points']
        points = [tuple(map(float, pair.split(','))) for pair in route.split()]
        self.assertFalse(LineString(points[:2]).intersects(room))
        # Independent critic's actual original defect: entry crossed guest before hall.
        self.assertTrue(LineString([(210,460),(210,342)]).intersects(box(170,360,345,425)))

    def test_cache_reuse_and_edition_invalidation(self):
        first = self.review(1)
        self.assertTrue(self.review(1)['reused'])
        source = next(s for s in self.lib['sources'] if s['id']=='yourhome-orientation')
        source['edition'] = 'changed edition'
        self.save()
        changed = self.review(1)
        self.assertFalse(changed['reused'])
        self.assertNotEqual(first['dependency_key'], changed['dependency_key'])
        self.assertIn('Evidence: yourhome-orientation', changed['unresolved'])

    def test_project_isolation(self):
        first = self.review(0)
        self.project['id'] = 'another-client'
        self.project['brief']['taste'] = 'Bright and colourful'
        self.save()
        second = self.review(0)
        self.assertNotEqual(first['dependency_key'], second['dependency_key'])
        self.assertNotIn('Bright and colourful', json.dumps(g.library(self.root)))

    def complete_intent(self):
        self.project['example'] = False
        for record in self.project['facts'].values():
            record.update(status='confirmed',value='Client-confirmed test fact')
        artifact = self.root/'brief.md'
        artifact.write_text('Reviewed test brief', encoding='utf-8')
        record = dict(path='brief.md',sha256=hashlib.sha256(artifact.read_bytes()).hexdigest())
        stage = self.lib['stages'][0]
        self.project['stages']['0'] = dict(
            artifacts={key:record for key in stage['deliverables']},
            qualitative={key:dict(status='pass',reviewer='test reviewer',notes='Test review notes',
                         revision=self.project['revision']) for key in stage['approval']})
        self.save()

    def test_explicit_approval_and_changed_artifact(self):
        self.complete_intent()
        self.assertTrue(self.review(0)['ready_for_client_approval'])
        self.assertFalse(self.review(0)['approved'])
        self.project['stages']['0']['approval'] = dict(status='approved',by='test client',date='2026-09-24',revision=self.project['revision'],review_key=self.review(0)['dependency_key'])
        self.save()
        self.assertTrue(self.review(0)['approved'])
        (self.root/'brief.md').write_text('Changed brief',encoding='utf-8')
        changed = self.review(0)
        self.assertFalse(changed['approved'])
        self.assertFalse(changed['reused'])

    def test_changed_brief_cannot_reuse_approval_even_without_revision_bump(self):
        self.complete_intent()
        self.project['stages']['0']['approval'] = dict(status='approved',by='test client',date='2026-09-24',revision=self.project['revision'],review_key=self.review(0)['dependency_key'])
        self.save()
        self.assertTrue(self.review(0)['approved'])
        self.project['brief']['taste'] = 'Client has requested a different direction'
        self.save()
        self.assertFalse(self.review(0)['approved'])

    def test_missing_facts_and_assumptions_keep_gate_open(self):
        self.complete_intent()
        self.project['facts']['budget']['status'] = 'assumed'
        self.save()
        self.assertIn('Missing project fact: budget', self.review(0)['unresolved'])

    def test_late_gate_requires_earlier_approval(self):
        self.project['example'] = False
        self.save()
        self.assertIn('Earlier stage approval missing or stale: 0', self.review(1)['unresolved'])

    def test_render_staleness_is_exposed(self):
        self.assertIn('Presentation is not bound to the reviewed revision, model and rendering input', self.review(7)['unresolved'])
        record = dict(path='missing.png',sha256='invented')
        self.assertFalse(g.artifact_status(record, self.root))

    def test_cached_presentation_rechecks_image_and_requirement_content(self):
        def artifact(name, content):
            path = self.root/name
            path.write_bytes(content)
            return dict(path=name,sha256=hashlib.sha256(content).hexdigest())
        self.project['scope'] = 'room'
        self.project['model'] = artifact('model.json',(ROOT/'tests/fixtures/bedroom-from-revit.json').read_bytes())
        self.project['render_binding'] = dict(render=artifact('image.png',b'fixture image identity only'),
            input=artifact('input.json',b'{}'),model_sha256=self.project['model']['sha256'],revision=self.project['revision'])
        self.project['requirements'] = [dict(id='privacy',response='Test fixture',artifact=artifact('trace.md',b'reviewed trace'))]
        self.save()
        first = self.review(7)
        message = 'Presentation is not bound to the reviewed revision, model and rendering input'
        self.assertNotIn(message, first['unresolved'])
        self.assertTrue(self.review(7)['reused'])
        (self.root/'image.png').write_bytes(b'changed image')
        (self.root/'trace.md').write_bytes(b'changed trace')
        changed = self.review(7)
        self.assertFalse(changed['reused'])
        self.assertIn(message, changed['unresolved'])
        self.assertIn('Client requirement traceability incomplete', changed['unresolved'])

    def test_real_directional_source_rejects_pilot_climate(self):
        result = g.lookup_evidence('australian-heating-orientation',stage=1,facts=self.project['facts'])
        card = next(r for r in result['results'] if r['id']=='australian-heating-orientation')
        self.assertEqual(card['applicability']['status'],'unresolved')

    def test_bedroom_review_uses_actual_obstacles(self):
        from archpipe.review_extract import review_model
        data = json.loads((ROOT/'tests/fixtures/bedroom-from-revit.json').read_text())
        bed = next(f for f in data['furniture'] if f['mark']=='FN-BED')
        table = next(f for f in data['furniture'] if f['mark']=='FN-BST-L')
        table['bbox_center_mm'] = bed['at']
        result = review_model(data, scope='room')
        self.assertEqual(result['furniture_count'], 6)
        self.assertTrue(any(f['rule']=='FURN-03' for f in result['findings']))
        self.assertFalse(result['approval_ready'])

    def test_retrieval_no_match_and_path_escape(self):
        self.assertTrue(g.lookup_evidence('nonexistent-claim')['unresolved'])
        with self.assertRaises(ValueError):
            g.stage_context(0,'../outside.json',self.root)
        for bad in (-1,8,True):
            with self.assertRaises(ValueError):
                g.stage_context(bad,'project.json',self.root)


if __name__ == '__main__':
    unittest.main()
