"""Frozen branch-start C3 collection, source controls and renamed siblings."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
import unittest

from archpipe.concept.construction_solids import backed_polygon, close_skin, complete_shell
from archpipe.concept.component_kinds import assembly_kind, component_kind
from archpipe.concept.part_exemptions import annotate, exemption_for, records
from archpipe.concept.physical_part import Part, PartError, PartMeshList, geometry_errors, SURFACE_EXEMPTIONS

FROZEN = json.loads(gzip.decompress((Path(__file__).parent/'fixtures/c3-phase2c-before.json.gz').read_bytes()))

# Exact admission vocabulary before phase 2c, retained by value. Re-running
# this historical screen must not borrow newly admitted physical kinds.
LEGACY_BOX_KINDS = frozenset(('trellis', 'cabinet-carcass', 'shelf', 'worktop',
    'wall-panel', 'plinth', 'door-leaf', 'stair-stringer', 'wall-plate',
    'rail-bracket', 'glass-pane', 'finish-layer', 'led-strip', 'tv-panel',
    'mirror-panel', 'appliance-front', 'stepping-stone', 'bench-slab', 'planter-soil'))


def legacy_findings(mesh):
    errors = geometry_errors(mesh['faces'], surface=mesh.get('surface', False),
                             occupied_side=mesh.get('occupied_side'))
    axes = [{round(p[i], 6) for f in mesh['faces'] for p in f} for i in range(3)]
    if not mesh.get('surface') and all(len(a)<=2 for a in axes) and mesh['part_kind'] not in LEGACY_BOX_KINDS:
        errors.insert(0, 'bare rectangular proxy for '+mesh['part_kind'])
    return '; '.join(errors)


class FrozenPhysicalGroups(unittest.TestCase):
    def test_real_collection_is_frozen_by_value_and_every_kind_fires(self):
        self.assertEqual(FROZEN['branch_start'], 'acee29d')
        self.assertEqual(FROZEN['collection_count'], 169)
        self.assertEqual(len(FROZEN['meshes']), 169)
        by_id = {m['id']:m for m in FROZEN['meshes']}
        for failure in FROZEN['failures']:
            with self.subTest(id=failure['id']):
                mesh = by_id[failure['id']]
                self.assertEqual(legacy_findings(mesh), failure['reason'])
                sibling = deepcopy(mesh)
                sibling['id'] = 'other-project-renamed-member'
                sibling['room'] = 'other-room'
                self.assertEqual(legacy_findings(sibling), failure['reason'])

    def test_camera_free_collection_is_also_frozen_by_value(self):
        self.assertEqual(len(FROZEN['camera_free_collection']), 178)
        by_id = {m['id']: m for m in FROZEN['camera_free_meshes']}
        self.assertEqual(len(by_id), 178)
        for failure in FROZEN['camera_free_collection']:
            with self.subTest(id=failure['id']):
                self.assertEqual(legacy_findings(by_id[failure['id']]), failure['reason'])

    def test_real_retyped_worktop_preserves_approved_support_and_renamed_sibling(self):
        from archpipe.concept.support_mounting import nearest
        data = json.loads(gzip.decompress((Path(__file__).parent/
            'fixtures/c3-phase2c-support-drift.json.gz').read_bytes()))
        bb = data['rows'][0]['old']
        anchor = [(bb[0]+bb[3])/2, (bb[1]+bb[4])/2, bb[2]]
        sources = data['sources']
        # The old selector hid the actual worktop and selected a lower fascia.
        old_sources = [m for m in sources if m['part_kind'] in ('desk', 'base_run')]
        old = nearest({'mounting_hosts':{}}, anchor, (0,0,1), old_sources,
                      'frozen-wrong-selector', 'joinery-panel')
        self.assertAlmostEqual(old.structural_point[2], data['rows'][0]['new'][2])
        self.assertNotAlmostEqual(old.structural_point[2], data['approved'][0]['new'][2])
        for renamed in (False, True):
            members = deepcopy(sources)
            if renamed:
                for m in members:
                    m['id'] = 'other-' + m['id']
                    m['room'] = 'another-room'
                    for face in m['faces']:
                        for p in face:
                            p[0] += 3
            selected = [m for m in members if assembly_kind(m) in ('desk','base_run')]
            probe = [anchor[0]+(3 if renamed else 0), *anchor[1:]]
            host = nearest({'mounting_hosts':{}}, probe, (0,0,1), selected,
                           'other-host', 'joinery-panel')
            self.assertAlmostEqual(host.structural_point[2], data['approved'][0]['new'][2])
        self.assertEqual(assembly_kind({'part_kind':'wardrobe'}), 'wardrobe')
        self.assertEqual(assembly_kind({'part_kind':'wall-panel','assembly_kind':'screen'}), 'screen')

    def test_all_real_shell_faces_close_without_moving_fronts(self):
        for mesh in FROZEN['meshes']:
            if mesh['part_kind'] not in ('finish-layer', 'door-leaf'):
                continue
            with self.subTest(id=mesh['id']):
                fixed = dict(mesh, faces=close_skin(mesh['faces']))
                fixed.pop('surface', None)
                fixed.pop('occupied_side', None)
                PartMeshList().append(fixed)
                fronts = fixed['faces']
                self.assertTrue(all(face in fronts for face in mesh['faces']))
                # A translated concave profile cannot rely on D1 coordinates.
                moved = [[[p[0]+4, p[1]-7, p[2]+9] for p in f] for f in mesh['faces']]
                self.assertEqual(geometry_errors(close_skin(moved)), [])

    def test_closure_keeps_opening_bridge_unbuilt(self):
        # The actual slab keyhole is frozen, not reconstructed from the
        # current daylight builder. Reverse bridge edges must not get walls.
        mesh = next(m for m in FROZEN['meshes'] if m['material']=='travertine' and any(len(f)>8 for f in m['faces']))
        face = next(f for f in mesh['faces'] if len(f)>8)
        fixed = backed_polygon(face)
        edges = Counter((tuple(a),tuple(b)) for a,b in zip(face,face[1:]+face[:1]))
        bridges = {e for e in edges if edges[e[::-1]]}
        self.assertTrue(bridges)
        for side in fixed[2:]:
            self.assertNotIn((tuple(side[1]),tuple(side[0])), bridges)
        self.assertEqual(geometry_errors(fixed), [])
        with self.assertRaisesRegex(ValueError, 'positive thickness'):
            backed_polygon(face, 0)

    def test_component_roles_generalise_without_identifiers(self):
        for assembly,names,kind in (
            ('desk',['pull'],'joinery-pull'), ('wc',['flush-plate'],'wall-plate'),
            ('desk',['cable-tray'],'joinery-cable-tray'),
            ('shower_walkin',['glass'],'glass-pane'),
            ('shower_walkin',['wet-floor'],'finish-layer'),
            ('tv_unit',['screen'],'tv-panel'), ('base_run',['oven-glass'],'appliance-front'),
            ('store_shelving',['seasonal-boxes-back'],'cabinet-carcass'),
            ('store_shelving',['luggage-base'],'cabinet-carcass'),
            ('under_stair_storage',['small-boxes-shelf'],'shelf'),
            ('joinery_end_panel',['joinery_end_panel'],'wall-panel'),
            ('joinery_end_panel',['block'],'wall-panel'),
            ('unknown',['block'],'unknown'),
            ('chair',['back'],'chair'), ('sofa_3seat',['base'],'sofa_3seat'),
            ('unknown',['new-proxy'],'unknown')):
            self.assertEqual(component_kind(assembly,names), kind)
        self.assertEqual(component_kind('under_stair_storage',['vacuum-body'],
                                        fallback='vacuum-body'), 'vacuum-body')

    def test_exemptions_are_explicit_bounded_and_never_skip_geometry(self):
        kinds = {r['kind'] for r in records()}
        covered = set()
        for mesh in FROZEN['meshes']:
            if mesh['part_kind'] not in kinds:
                continue
            fixed = annotate(deepcopy(mesh))
            self.assertIn('proxy_exemption', fixed)
            self.assertTrue(fixed['proxy_exemption']['reason'])
            fixed['id'] = 'renamed-retained-shape'
            PartMeshList().append(fixed)
            covered.add(fixed['part_kind'])
            opened = deepcopy(fixed)
            opened['faces'].pop()
            with self.assertRaises(PartError):
                PartMeshList().append(opened)
            resized = deepcopy(fixed)
            for face in resized['faces']:
                for point in face:
                    point[0] *= 1.1
            with self.assertRaisesRegex(PartError, 'changed proxy exemption'):
                PartMeshList().append(resized)
        self.assertEqual(covered, kinds)

    def test_surface_exemptions_are_registered_and_direction_checked(self):
        face = [[[0,0,0],[1,0,0],[1,1,0],[0,1,0]]]
        for kind,reason in SURFACE_EXEMPTIONS.items():
            self.assertTrue(reason)
            sink = PartMeshList()
            sink.append(dict(id='other-film',part_kind=kind,material='neutral',faces=face,
                             surface=True,occupied_side=(0,0,1)))
            self.assertEqual(sink[0]['surface_exemption_reason'],reason)
            with self.assertRaisesRegex(PartError,'away from occupied'):
                Part(kind,face,('x','y','z'),'neutral','authored',surface=True,occupied_side=(0,0,-1))
        with self.assertRaisesRegex(PartError,'unregistered surface'):
            Part('new-open-proxy',face,('x','y','z'),'neutral','authored',surface=True,occupied_side=(0,0,1))

    def test_clipped_source_closes_and_clean_solid_stays_unchanged(self):
        source = next(m for m in FROZEN['meshes'] if m['part_kind']=='door-leaf')
        scene = {'meshes':[deepcopy(source)]}
        complete_shell(scene)
        clean = deepcopy(scene)
        complete_shell(scene)
        self.assertEqual(scene,clean)
        scene['meshes'][0]['faces'] = [source['faces'][0]]
        complete_shell(scene)
        PartMeshList().extend(scene['meshes'])

    def test_real_material_slots_follow_closure_and_ground_siblings(self):
        from archpipe.concept.garden_render_review import downward_ground_findings
        data = json.loads(gzip.decompress((Path(__file__).parent/
            'fixtures/c3-phase2c-face-materials.json.gz').read_bytes()))
        self.assertEqual(len(data['failure_after']['faces']), 339)
        self.assertEqual(len(data['failure_after']['face_materials']), 63)
        with self.assertRaisesRegex(PartError, 'face material count'):
            PartMeshList().append(data['failure_after'])
        for renamed in (False, True):
            source = deepcopy(data['before'])
            if renamed:
                source['id'] = 'other-project-ground-shell'
                source['face_materials'] = ['another-ground' if m=='paving' else m
                                            for m in source['face_materials']]
                for face in source['faces']:
                    for p in face:
                        p[0] += 8
            scene = {'meshes':[source], 'materials':{'another-ground':{'surface_use':'ground-only'}}}
            original = deepcopy(source)
            complete_shell(scene)
            self.assertEqual(len(source['faces']), len(source['face_materials']))
            self.assertEqual(downward_ground_findings(scene), [])
            PartMeshList().append(source)
            pairs = list(zip(source['faces'],source['face_materials']))
            for pair in zip(original['faces'],original['face_materials']):
                self.assertIn(pair, pairs)
            # A malformed source must be rejected before any face mutation.
            bad = deepcopy(original)
            bad['face_materials'].pop()
            before = deepcopy(bad)
            with self.assertRaisesRegex(ValueError, 'source face material count'):
                complete_shell({'meshes':[bad]})
            self.assertEqual(bad, before)

    def test_real_stacked_bridge_front_follows_host_before_closure(self):
        from archpipe.concept.mounting import Host, Finish, stacked_finish_bridge
        from archpipe.concept.fitting_mounting import normal
        data = json.loads(gzip.decompress((Path(__file__).parent/
            'fixtures/c3-phase2c-bridge-winding.json.gz').read_bytes()))
        self.assertLess(normal(data['bridge']['faces'][0])[1], 0)
        for flipped in (False, True):
            record = data['host']
            outward = (0,-1,0) if flipped else (0,1,0)
            structural = list(record['structural_point'])
            if flipped:
                structural[1] = 2*data['bridge']['faces'][0][0][1]-structural[1]
            host = Host('unrelated-host', 'wall', tuple(structural),
                        outward, Finish(**record['finish']))
            faces = stacked_finish_bridge(host, host, data['lower_faces'],
                                         data['upper_faces'], data['slab_depth_m'])
            self.assertEqual(len(faces),1)
            face = faces[0]
            self.assertEqual({tuple(p) for p in face}, {tuple(p) for p in data['bridge']['faces'][0]})
            self.assertGreater(sum(a*b for a,b in zip(normal(face), outward)), .999999)
            skin = backed_polygon(face)
            self.assertEqual(geometry_errors(skin), [])
            # Every backing vertex belongs on the structural side of the
            # retained finished plane, for either host direction.
            self.assertTrue(all(sum((p[i]-face[0][i])*outward[i] for i in range(3)) <= 1e-9
                                for f in skin for p in f))


class FinalPhysicalScene(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from archpipe.concept.villa_render import build
        cls.scene = build()

    def test_real_collection_shrinks_to_zero_and_final_sink_is_strict(self):
        self.assertEqual(self.scene['part_failures'], [])
        self.assertIsInstance(self.scene['meshes'], PartMeshList)
        self.assertFalse(self.scene['meshes'].collect)
        PartMeshList().extend(self.scene['meshes'])
        # Historical side-pair fixtures are retired by the branch-start C5
        # decision. No phase 2c deletion is accepted as a geometric remedy.
        by_id = {m['id']:m for m in self.scene['meshes']}
        retired = {'lamp-VSCONCE-parents-ensuite-04','lamp-VSCONCE-parents-ensuite-05'}
        leaves = [m for m in self.scene['meshes'] if m['part_kind']=='door-leaf'
                  and m['group'] in ('shell','context')]
        face_key = lambda face: tuple(tuple(p) for p in face)
        door_faces = {face_key(f) for m in leaves for f in m['faces']}
        for mesh in FROZEN['meshes']:
            with self.subTest(id=mesh['id']):
                if mesh['part_kind']=='door-leaf' and mesh['group'] in ('shell','context'):
                    # Render bucket ids retire; every actual authored face
                    # remains in a complete physical door source.
                    self.assertTrue(all(face_key(f) in door_faces for f in mesh['faces']))
                else:
                    self.assertTrue(mesh['id'] in by_id or mesh['id'] in retired)
        # A real fixed member from every frozen kind must still be admitted
        # with unrelated identifiers. Neither room nor identifier is a waiver.
        covered = set()
        for mesh in FROZEN['meshes']:
            if mesh['part_kind'] in covered:
                continue
            current = by_id.get(mesh['id'])
            if current is None and mesh['part_kind']=='door-leaf':
                fronts = {face_key(f) for f in mesh['faces']}
                current = next((m for m in leaves if any(face_key(f) in fronts for f in m['faces'])),None)
            if current is None:
                continue
            sibling = deepcopy(current)
            sibling['id'] = 'another-project-fixed-member'
            sibling['room'] = 'another-room'
            PartMeshList().append(sibling)
            covered.add(mesh['part_kind'])
        self.assertEqual(covered, {m['part_kind'] for m in FROZEN['meshes']})

    def test_new_open_proxy_and_post_build_mutation_fail(self):
        fresh = deepcopy(next(m for m in self.scene['meshes'] if m['part_kind']=='glass-pane'))
        fresh['id'] = 'another-villa-new-open-pane'
        fresh['faces'] = fresh['faces'][:-1]
        with self.assertRaises(PartError):
            self.scene['meshes'].append(fresh)
        mutated = deepcopy(self.scene['meshes'])
        source = next(m for m in mutated if m.get('construction_backing_m'))
        source['faces'].pop()
        with self.assertRaises(PartError):
            PartMeshList().extend(mutated)
