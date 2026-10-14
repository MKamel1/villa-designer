"""Actual integrated input contracts, their mutations and clean siblings."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from archpipe.concept import garments as G
from archpipe.imported_appearance import bind_scene, require_scene, with_models
from tests.scene_migration import prior_reviewed_rows

FIXTURES = Path(__file__).parent/'fixtures'


def frozen(name):
    return json.loads(gzip.decompress((FIXTURES/name).read_bytes()))


class IntegrationContracts(unittest.TestCase):
    def test_real_rail_requires_both_end_brackets_and_renamed_sibling(self):
        before = frozen('integ6-rail-support-before.json.gz')
        for renamed in (False, True):
            case = deepcopy(before)
            if renamed:
                identifiers = {p['id']:'other-villa-'+p['id'] for p in case['parts']}
                case['missing_id'] = identifiers[case['missing_id']]
                for row in case['parts']:
                    row['id'] = identifiers[row['id']]
                    for key in ('contents_support', 'contents_joint', 'rail_id', 'associated_mounting_root'):
                        if row.get(key) in identifiers:row[key] = identifiers[row[key]]
                    for face in row['faces']:
                        for p in face:p[2] += 3
            broken = [p for p in case['parts'] if p['id'] != case['missing_id']]
            self.assertTrue(any('missing declared rail brackets' in f
                                for f in G.contents_findings(case['wardrobes'], broken)))
        from tests.test_garments import clean_package
        wardrobes, parts = clean_package()
        self.assertEqual(G.contents_findings(wardrobes, parts), [])
        rail = next(p for p in parts if p.get('contents_role') == 'rail')
        for identifier in rail['contents_support_parts']:
            broken = [p for p in parts if p['id'] != identifier]
            self.assertTrue(any('missing declared rail brackets' in f
                                for f in G.contents_findings(wardrobes, broken)))

    def test_exact_contents_retirement_requires_all_closed_replacements(self):
        policy = json.loads(Path('knowledge/garment-part-retirements.json').read_text())
        migration = frozen('integ6-scene-migration.json.gz')
        rows = migration['added']+[r['after'] for r in migration['changed']]
        scene = dict(garment_contents_version='closed/1', meshes=rows)
        for record in policy['rows']:
            old = record['before']
            self.assertEqual(len(G.historical_replacements(scene, old)), 3)
            changed = deepcopy(old);changed['faces'][0][0][0] += .001
            with self.assertRaisesRegex(ValueError, 'provenance drift'):
                G.historical_replacements(scene, changed)
            missing = dict(scene, meshes=[r for r in rows if r['id'] != record['replacement_ids'][0]])
            with self.assertRaisesRegex(ValueError, 'missing strict'):
                G.historical_replacements(missing, old)
        self.assertIsNone(G.historical_replacements(scene, dict(id='unrelated-new-part')))

    def test_real_scene_migration_keeps_full_inventory_and_exact_row_bindings(self):
        record = frozen('integ6-scene-migration.json.gz')
        old = {k:dict(id=k) for k in record['reviewed_ids']}
        for row in record['removed']:old.pop(row['id'])
        for change in record['changed']:old[change['after']['id']] = change['after']
        rows = list(old.values())+record['added']
        self.assertEqual(len(prior_reviewed_rows(rows)), len(record['reviewed_ids']))
        for mutation in ('geometry', 'renamed', 'unknown'):
            changed = deepcopy(rows)
            if mutation == 'geometry':changed[-1]['faces'][0][0][0] += .001
            elif mutation == 'renamed':changed[-1]['id'] = 'another-villa-contents'
            else:changed.append(dict(id='unexpected-source'))
            with self.assertRaises(ValueError):prior_reviewed_rows(changed)

    def test_real_orphan_bed_pair_refuses_and_atomic_selection_stays_clean(self):
        stale = frozen('integ6-bed-baseline-pair-before.json.gz')
        for renamed in (False, True):
            case = deepcopy(stale)
            if renamed:
                for key in ('imported_appearances', 'physical_model_meshes'):
                    for row in case[key]:row['id'] = 'other-villa-'+row['id']
            with self.assertRaisesRegex(ValueError, 'missing, stale'):require_scene(case)
            with self.assertRaisesRegex(ValueError, 'missing, stale'):with_models(case, [])
        source = bind_scene(dict(models=[], meshes=[]))
        self.assertEqual(require_scene(with_models(source, [])), [])
        real = frozen('parents-bed-activation.json.gz')
        source = bind_scene(dict(models=real['receipt']['models'], meshes=[]))
        expanded = dict(source, meshes=source['physical_model_meshes'])
        with self.assertRaisesRegex(ValueError, 'must stay outside'):
            with_models(expanded, [])
        selected = with_models(source, [])
        self.assertEqual(require_scene(selected), [])
        self.assertTrue(source['models'])
        self.assertTrue(source['physical_model_meshes'])
        # Validated identity reuse must neither alias pair records nor bless
        # a later source mutation. A new model object is constructed afresh.
        reused = with_models(source, source['models'])
        reused['physical_model_meshes'][0]['faces'][0][0][0] += .001
        require_scene(source)
        with self.assertRaisesRegex(ValueError, 'missing, stale'):require_scene(reused)
        moved = deepcopy(source['models'][0]);moved['position'][0] += 4
        translated = with_models(source, [moved])
        require_scene(translated)
        self.assertNotEqual(translated['physical_model_meshes'], source['physical_model_meshes'])
        source['models'][0]['position'][0] += .001
        with self.assertRaisesRegex(ValueError, 'missing, stale'):
            with_models(source, source['models'])

    def test_garment_cache_tracks_recipe_translation_and_caller_mutation(self):
        before = frozen('l0923-dressing-before.json.gz')
        wardrobes = before['wardrobes']
        G._cached_build.cache_clear()
        first, modules = G.build(wardrobes, .002)
        retained = deepcopy(first)
        first[0]['faces'][0][0][0] += 1
        second, _ = G.build(wardrobes, .002)
        self.assertEqual(second, retained)
        self.assertEqual(G._cached_build.cache_info().hits, 1)
        with patch.dict(G.DROP, dress=G.DROP['dress']+.001):
            changed, _ = G.build(wardrobes, .002)
        self.assertNotEqual(changed, retained)
        moved = deepcopy(wardrobes)
        for w in moved:w['cx'] += 4
        translated, _ = G.build(moved, 3.002)
        self.assertNotEqual(translated, retained)
        self.assertEqual(G.build(wardrobes, .002)[0], retained)
