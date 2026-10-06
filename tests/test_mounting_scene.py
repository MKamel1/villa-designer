"""C4 first package: actual frozen failures, clean geometry and mutations."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from archpipe.concept.mounting import (
    BUILD_UP_RECORD, FACE_TOLERANCE_M, Finish, Host, MountItem,
    binding, check_mesh, finish_from_record, scene_findings,
    stacked_finish_bridge,
)
from archpipe.concept import revit_spec as RS, villa_r11 as R, villa_render as VR
from archpipe.concept import stair_mounting as SM


def bounds_for_test(mesh):
    from archpipe.concept.fitting_mounting import bounds
    return bounds(mesh)


def plane(mid, y):
    return dict(id=mid, part_kind="wall-plate",
                faces=[[[0, y, 0], [1, y, 0], [1, y, 1], [0, y, 1]]])


class SceneMountingGuard(unittest.TestCase):
    def test_frozen_actual_core_return_and_clean_sibling(self):
        frozen = json.loads((Path(__file__).parent / "fixtures/c4-stair-host-coverage.json").read_text(encoding="utf-8"))
        findings = scene_findings(frozen)
        self.assertEqual(len(findings), 1)
        self.assertIn("stringer-04: MISSING finite host coverage", findings[0])
        frozen["meshes"] = [m for m in frozen["meshes"] if not m["id"].endswith("stringer-04")]
        self.assertEqual(scene_findings(frozen), [])
        tolerated = deepcopy(frozen)
        for member in tolerated["meshes"]:
            if "mounting" in member:
                for face in member["faces"]:
                    for point in face:
                        point[1] += FACE_TOLERANCE_M
        self.assertEqual(scene_findings(tolerated), [])
        # Removing the actual finite surface also makes the supported sibling
        # fail, despite its mathematically correct infinite-plane placement.
        frozen["meshes"] = [m for m in frozen["meshes"] if not m.get("finished_host_id")]
        self.assertIn("finite host coverage", scene_findings(frozen)[0])

    def test_frozen_l0856_not_current_export(self):
        # Actual l0856 coordinates from LEARNINGS: nearest surface 140 mm
        # behind the then-rendered wall. No current builder is imported here.
        host = Host("historic-wall", "wall", (0, -28.471, 0), (0, 1, 0), Finish("historic-modeled-face", 0))
        rail = dict(id="frozen-l0856", part_kind="handrail", faces=[
            [[5.317, -28.611, .70], [9.517, -28.611, -1.95],
             [9.517, -28.581, -1.95], [5.317, -28.581, .70]]])
        rail["mounting"] = binding(MountItem(rail["id"]), host, .085, "wall-hung")
        self.assertIn("-225.000 mm", check_mesh(rail, {host.id: host})[0])

    def test_frozen_l0119_reports_unknown_void_and_depth(self):
        # Actual body top 2732 mm, ceiling 2700 mm. Historic clear void was
        # never established: the 25 mm void in the phase-1 API test is a
        # chosen witness, not a measured property of this failing model.
        ceiling = Host("historic-ceiling", "ceiling", (0, 0, 2.7), (0, 0, -1), Finish("existing-ceiling", 0))
        body = dict(id="frozen-l0119", part_kind="lamp-housing",
                    faces=[[[0, 0, 2.700], [1, 0, 2.700], [1, 0, 2.732], [0, 0, 2.732]]],
                    mounting=dict(host_id=ceiling.id, kind="recessed", offset_m=0,
                                  housing_depth_m=.032, finished_face=[0, 0, 2.7]))
        self.assertIn("MISSING", check_mesh(body, {ceiling.id: ceiling})[0])
        body["mounting"]["housing_depth_m"] = None
        known_void = Host("historic-ceiling", "ceiling", (0, 0, 2.7), (0, 0, -1), Finish("existing-ceiling", 0), .050)
        self.assertIn("MISSING", check_mesh(body, {known_void.id: known_void})[0])
        body["mounting"]["housing_depth_m"] = .032
        short_void = Host("historic-ceiling", "ceiling", (0, 0, 2.7), (0, 0, -1), Finish("existing-ceiling", 0), .025)
        self.assertIn("exceeds the clear void", check_mesh(body, {short_void.id: short_void})[0])
        self.assertEqual(check_mesh(body, {known_void.id: known_void}), [])
        # A 10 mm discrepancy between stated housing and real vertices fails.
        body["faces"][0][2][2] += .010
        self.assertIn("finished-face error", check_mesh(body, {known_void.id: known_void})[0])

    def test_missing_host_and_geometry_mutations_fail(self):
        host = Host("other-project", "wall", (0, 2, 0), (0, 1, 0), finish_from_record("interior-plaster"))
        good = plane("unrelated-id", 2.013)
        self.assertIn("MISSING mounting host", check_mesh(good, {host.id: host})[0])
        good["mounting"] = binding(MountItem(good["id"]), host, 0, "surface-mounted")
        self.assertEqual(check_mesh(good, {host.id: host}), [])
        for delta in (-.006, .006):
            bad = deepcopy(good)
            for point in bad["faces"][0]:
                point[1] += delta
            self.assertIn("finished-face error", check_mesh(bad, {host.id: host})[0])
        at_tolerance = deepcopy(good)
        for point in at_tolerance["faces"][0]:
            point[1] += FACE_TOLERANCE_M
        self.assertEqual(check_mesh(at_tolerance, {host.id: host}), [])
        good["mounting"]["finished_face"][1] -= .013
        self.assertIn("stale", check_mesh(good, {host.id: host})[0])

    def test_reverse_normal_and_floor_are_not_d1_specific(self):
        wall = Host("reverse", "wall", (0, 4, 0), (0, -1, 0), finish_from_record("interior-plaster"))
        mesh = plane("sibling", 3.987)
        mesh["mounting"] = binding(MountItem(mesh["id"]), wall, 0, "surface-mounted")
        self.assertEqual(check_mesh(mesh, {wall.id: wall}), [])
        floor = Host("floor", "floor", (0, 0, 0), (0, 0, 1), Finish("bare-model-datum", 0))
        mesh = dict(id="floor-item", faces=[[[0, 0, 0], [1, 0, 0], [1, 1, .5]]])
        mesh["mounting"] = binding(MountItem(mesh["id"]), floor, 0, "floor-standing")
        self.assertEqual(check_mesh(mesh, {floor.id: floor}), [])

    def test_whole_scene_missing_host_is_unconditional(self):
        self.assertIn("MISSING mounting host", scene_findings({"meshes": [plane("unknown", 0)]})[0])


class StairFirstPackage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scene = VR.build(views=[])
        # Historical a-d proofs retain their pre-e clearance case. Current
        # authorized slides are independently exercised by support tests.
        for identifier,record in cls.scene.get('wc_slides',{}).items():
            delta=record['delta']
            for mesh in cls.scene['meshes']:
                if mesh['id'].startswith('furn-'+identifier+'-'):
                    mesh['faces']=[[[p[i]-delta[i] for i in range(3)] for p in f] for f in mesh['faces']]
        cls.scene['wc_slides']={}
        cls.scene['mounting_movements']=[r for r in cls.scene['mounting_movements'] if r['package']!='wc-same-wall-slide']
        cls.members = [m for m in cls.scene["meshes"] if "mounting" in m and m["id"].startswith("detail-stair-wall")]

    def test_migrated_plane_contracts_quiet_but_core_coverage_fails(self):
        self.assertEqual(len(self.members), 22)
        surfaces = [m for m in self.scene.get("diagnostic_meshes", []) + self.scene["meshes"] if m.get("finished_host_id")]
        subset = dict(meshes=self.members + surfaces, mounting_hosts=self.scene["mounting_hosts"])
        failures = scene_findings(subset)
        self.assertEqual(failures, [])
        # The actually covered components stay quiet with their real surfaces.
        failed_ids = {f.split(":", 1)[0] for f in failures}
        clean = dict(meshes=[m for m in subset["meshes"] if m["id"] not in failed_ids],
                     mounting_hosts=subset["mounting_hosts"])
        self.assertEqual(scene_findings(clean), [])
        subset = clean
        mutant = deepcopy(subset)
        for face in mutant["meshes"][0]["faces"]:
            for point in face:
                point[1] -= .013
        self.assertTrue(scene_findings(mutant))
        mutant = deepcopy(subset)
        del next(m for m in mutant["meshes"] if m.get("part_kind") == "handrail")["mounting"]
        self.assertTrue(scene_findings(mutant))
        # Final C4 authority now resolves the retained non-stair findings too.
        # Frozen core/edge reproductions above still prove the guard fires.
        self.assertEqual(scene_findings(self.scene), [])

    def test_common_datum_in_d1_d2_d3(self):
        for option in ("D1", "D2", "D3"):
            spec = RS.build(R.design(option))
            datum = spec["stair_wall_datum"]
            self.assertTrue(all(abs(b[1] - datum["outer_face_mm"] - datum["tread_setback_mm"]) < 1e-8
                                for b in spec["stair"] if b[5] - b[2] < 300))
            host = SM.wall_host(spec)
            self.assertAlmostEqual(host.finish.thickness_m, .013)
            self.assertAlmostEqual(SM.finished_y(host), -28.458)

    def test_bc_pending_geometry_unchanged_small_moves_applied(self):
        # Historical function name retained for registry continuity. The
        # explicit frozen 58-row approval now applies; d stays bounded.
        self.assertEqual(self.scene['lead_approved_count'],64)
        fixes={'detail-gwc-hand-shower-head','detail-gwc-hand-shower-hose','lamp-SCONCE-guest-wc-03'}
        render_meshes={m['id']:m for m in self.scene['meshes']}
        diag_meshes={m['id']:m for m in self.scene.get('diagnostic_meshes',[])}
        for row in self.scene['mounting_movements']:
            if row['package']=='e-support': continue
            if row['id'] in fixes:
                continue
            rid=row['id']
            self.assertTrue((rid in render_meshes) ^ (rid in diag_meshes),
                            f"{rid}: row must be in exactly one channel")
            mesh=render_meshes[rid] if rid in render_meshes else diag_meshes[rid]
            if row['approval']=='PENDING':
                self.assertGreater(row['mm'],5)
                self.assertEqual(bounds_for_test(mesh),row['old'])
            else:
                self.assertEqual(mesh['faces'],row['proposed_faces'])
        self.assertEqual(len([m for m in render_meshes.values() if m.get('mounting_package') in ('b-bathroom','c-wall-lights')]),62)

    def test_bc_frozen_handset_and_wall_edge_are_not_silenced(self):
        frozen=json.loads((Path(__file__).parent/'fixtures/c4-guest-before-fixes.json').read_text())
        failures=scene_findings(frozen)
        self.assertEqual(len(failures),5)
        self.assertTrue(any('head: finished-face error -8.000' in f for f in failures))
        self.assertTrue(any('hose: finished-face error -65.961' in f for f in failures))
        ids={'detail-gwc-hand-shower-head','detail-gwc-hand-shower-hose','lamp-SCONCE-guest-wc-03'}
        subset=dict(self.scene,props=[],meshes=[m for m in self.scene["meshes"] if m["id"] in ids or m.get("finished_host_id")])
        self.assertEqual(scene_findings(subset),[])
        original=json.loads((Path(__file__).parent/'fixtures/c4-bc-before.json').read_text())
        old=next(m for m in original['meshes'] if m['id']=='detail-gwc-hand-shower-head')
        head=next(m for m in subset['meshes'] if m['id']==old['id'])
        for before_face,after_face in zip(old['faces'],head['faces']):
            for before,after in zip(before_face,after_face):
                self.assertAlmostEqual(after[0]-before[0],-.046)
                self.assertEqual(after[1:],before[1:])
        evidence=self.scene['guest_fix_evidence']
        self.assertAlmostEqual(evidence['sconce_slide_mm'],99)
        self.assertGreaterEqual(evidence['hose_min_surface_clearance_mm'],2)
        mutant=deepcopy(subset)
        hose=next(m for m in mutant['meshes'] if m['id'].endswith('-hose'))
        hose['hose_path']['points'][2][0]+=1
        self.assertTrue(any('hose violates' in f for f in scene_findings(mutant)))
        mutant=deepcopy(subset)
        hose=next(m for m in mutant['meshes'] if m['id'].endswith('-hose'))
        hose['hose_path']['retained_endpoints'][0][0]+=.01
        self.assertTrue(any('endpoints changed' in f for f in scene_findings(mutant)))
        mutant=deepcopy(subset)
        sconce=next(m for m in mutant['meshes'] if m['id'].endswith('SCONCE-guest-wc-03'))
        sconce['mounting']['fixing_footprint'][0][1]-=.1
        self.assertTrue(any('finite host coverage' in f for f in scene_findings(mutant)))

    def test_ceiling_unknowns_are_unresolved_and_small_moves_only(self):
        from archpipe import villa_render_contract as contract
        # The structural test builds no views. Supply the existing authored
        # view records for schema validation; no camera/design change.
        schema_scene=dict(self.scene,views=VR.VIEWS(R.design('D1')))
        self.assertEqual(contract.validate_scene(schema_scene),[])
        frozen=json.loads((Path(__file__).parent/'fixtures/c4-ceiling-label-before.json').read_text())
        reproduced=deepcopy(schema_scene)
        # Reproduce the historical render-channel defect explicitly: this
        # datum now lives only in diagnostics, so replacement was a no-op.
        self.assertIn(frozen['id'], {m['id'] for m in reproduced['diagnostic_meshes']})
        reproduced['meshes'].append(frozen)
        self.assertTrue(any('.label: string required' in f for f in contract.validate_scene(reproduced)))
        sibling=deepcopy(schema_scene)
        del next(m for m in sibling['meshes'] if m['material']=='ceiling-white')['label']
        self.assertTrue(any('.label: string required' in f for f in contract.validate_scene(sibling)))
        self.assertEqual(len(self.scene['ceiling_existing_bc']),10)
        self.assertEqual(self.scene['ceiling_unresolved'],[])
        for row in self.scene['ceiling_unresolved']:
            self.assertIsNone(row['housing_depth_m'])
            self.assertIsNone(row['void_depth_m'])
        findings=scene_findings(self.scene)
        self.assertEqual(sum('MISSING recessed housing depth' in f for f in findings),len(self.scene['ceiling_unresolved']))
        ceiling=[m for m in self.scene['meshes'] if m.get('mounting_package')=='d-ceiling']
        surfaces=[m for m in self.scene['meshes'] if m.get('finished_host_id')]
        proposal=deepcopy(dict(self.scene,props=[],meshes=ceiling+surfaces))
        by={m['id']:m for m in proposal['meshes']}
        for row in self.scene['mounting_movements']:
            if row['package']=='d-ceiling': by[row['id']]['faces']=row['proposed_faces']
        self.assertFalse([f for f in scene_findings(proposal) if 'MISSING recessed housing depth' not in f])
        self.assertEqual(self.scene['ceiling_deferred_joinery'],[])

    def test_real_clearance_failures_retained_and_movement_is_measured(self):
        from archpipe.concept.mounting_clearances import review, measured_items
        report=review(self.scene)
        failures={r['check']:r for r in report['failures']}
        rows={r['check']:r for r in report['rows']}
        self.assertEqual(rows['open wet-zone depth']['achieved_mm'],800)
        self.assertEqual(rows['drain within finished wet floor']['status'],'PASS')
        self.assertEqual(rows['gwc-wc separation from wet floor']['achieved_mm'],109.869)
        self.assertEqual(rows['gwc-wc horizontal wet-floor separation']['achieved_mm'],27)
        self.assertIn('fb-basin front approach',failures)
        self.assertFalse(report['unresolved'])
        self.assertEqual(report['requirements'][0]['status'],'CONSTRUCTION REQUIREMENT')
        before=deepcopy(self.scene)
        frozen=json.loads((Path(__file__).parent/'fixtures/c4-lead-before.json').read_text())
        old={m['id']:m for m in frozen['meshes']}
        current={m['id']:m for m in self.scene['meshes']}
        for mid,original_mesh in old.items():
            for old_face,new_face in zip(original_mesh['faces'],current[mid]['faces']):
                for before_point,after_point in zip(old_face,new_face):
                    self.assertAlmostEqual(after_point[0]-before_point[0],-.023)
                    self.assertEqual(after_point[1:],before_point[1:])
        before['meshes']=[old.get(m['id'],m) for m in before['meshes']]
        reproduced={r['check']:r for r in review(before)['failures']}
        self.assertEqual(reproduced['open wet-zone depth']['achieved_mm'],777)
        self.assertEqual(reproduced['drain within finished wet floor']['achieved_mm'],-23)
        original={i['id']:i for i in __import__('archpipe.concept.villa_furnish',fromlist=['layout']).layout(R.design('D1'))}
        measured={i['id']:i for i in measured_items(self.scene,R.design('D1'))}
        self.assertNotEqual(original['gwc-wc']['cy'],measured['gwc-wc']['cy'])
        self.assertTrue(all(r['status']=='PASS' for r in report['rows'] if 'route' in r['check'] or 'door swing' in r['check']))

    def test_lead_ceiling_requirements_and_authority_fail_closed(self):
        from archpipe.concept.ceiling_requirements import product_depth, requirements
        from archpipe.concept.mounting_resume import apply_approvals, APPROVALS
        from archpipe.concept import villa_lighting as VL
        for kind,depth in [('DL',95),('DLN',95),('ADJ',98),('WW',95)]:
            self.assertEqual(product_depth(kind)['housing_depth_mm'],depth)
        recorded=product_depth('DL',{'installation_clearance_mm':40,'installation_depth_mm':110})
        self.assertEqual(recorded['clearance_mm'],40)
        self.assertNotIn('ASSUMED',recorded['clearance_source'])
        self.assertEqual(recorded['housing_depth_mm'],110)
        with self.assertRaisesRegex(ValueError,'invalid stored manufacturer'):
            product_depth('DL',{'installation_clearance_mm':-1})
        for zone in self.scene['ceiling_requirements']:
            self.assertEqual(zone['status'],'requirement')
            self.assertEqual(zone['required_void_mm'],zone['max_housing_depth_mm']+25)
        meshes=[m for m in self.scene['meshes'] if m.get('mounting',{}).get('geometry_role')=='recessed-trim'
                and m.get('mounting_package')=='d-ceiling']
        self.assertEqual(len(meshes),80)
        for root in (meshes[0],next(m for m in meshes if 'cinema' in m['id'])):
            mutant=deepcopy(self.scene)
            host=mutant['mounting_hosts'][root['mounting']['host_id']]
            host['void_depth_m']-=.03
            self.assertTrue(any('void' in f for f in scene_findings(mutant) if f.startswith(root['id']+':')))
        with __import__('unittest.mock',fromlist=['patch']).patch.dict(VL.PRODUCT_CHOICE,{'DL':('iguzzini','NO-DEPTH-RECORD','missing')}):
            req=requirements([VL.Fixture('custom','DL','new-room','GF',1,1,2.7)])
            self.assertEqual(req[0]['status'],'UNRESOLVED')
            self.assertIsNone(req[0]['required_void_mm'])
        mutant=deepcopy(self.scene)
        row=next(r for r in mutant['mounting_movements'] if r['id']=='lens-WW-cinema-03')
        row['new'][0]+=.001
        with self.assertRaisesRegex(ValueError,'schedule drift'):
            apply_approvals(mutant,APPROVALS.with_name('c4-d-lead-approvals.json'))
        mutant_neither=deepcopy(self.scene)
        mutant_neither['meshes']=[m for m in mutant_neither['meshes'] if m['id']!='lens-WW-cinema-03']
        mutant_neither['diagnostic_meshes']=[m for m in mutant_neither.get('diagnostic_meshes',[]) if m['id']!='lens-WW-cinema-03']
        with self.assertRaisesRegex(KeyError,'lens-WW-cinema-03'):
            apply_approvals(mutant_neither,APPROVALS.with_name('c4-d-lead-approvals.json'))
        mutant_both=deepcopy(self.scene)
        mutant_both.setdefault('diagnostic_meshes',[]).append(dict(id='lens-WW-cinema-03',faces=[]))
        with self.assertRaisesRegex(ValueError,'lens-WW-cinema-03'):
            apply_approvals(mutant_both,APPROVALS.with_name('c4-d-lead-approvals.json'))
        original_packages={m['id'] for m in self.scene['meshes'] if m.get('mounting_package') in ('b-bathroom','c-wall-lights','d-ceiling')}
        self.assertFalse([f for f in scene_findings(self.scene) if 'finished-face error' in f and f.split(':')[0] in original_packages])

    def test_full_side_clearance_blocks_partial_slide_and_generalises(self):
        from archpipe.concept.mounting_clearances import review, measured_items, same_wall_slide_feasibility, wc_side_clearances
        from archpipe.concept import villa_furnish as F
        items={i['id']:i for i in measured_items(self.scene,R.design('D1'))}
        wc,basin,shower=(items[k] for k in ('fb-wc','fb-basin','fb-shower'))
        report=review(self.scene)
        feasibility=report['family_slide_feasibility']
        self.assertEqual(feasibility['status'],'NO FEASIBLE SLIDE')
        self.assertEqual(feasibility['required_centre_separation_mm'],550)
        self.assertEqual(feasibility['max_separation_wc_below_basin_mm'],280)
        self.assertEqual(feasibility['max_separation_basin_below_wc_mm'],295)
        self.assertEqual(feasibility['wc_old_centre'],feasibility['wc_new_centre'])
        self.assertEqual(feasibility['basin_old_centre'],feasibility['basin_new_centre'])
        # Generalised names, room, position: continuous interval proof is invariant.
        moved=deepcopy([wc,basin,shower])
        for i in moved: i.update(id='other-'+i['type'],room='other',cx=i['cx']+4,cy=i['cy']+6)
        rect=F.clear_rect(R.design('D1'),'family-bath')
        finished=[rect[0]+.023,rect[1]+.023,rect[2]-.023,rect[3]-.023]
        translated=[finished[0]+4,finished[1]+6,finished[2]+4,finished[3]+6]
        self.assertEqual(same_wall_slide_feasibility(*moved,translated)['status'],'NO FEASIBLE SLIDE')
        enlarged=list(finished);enlarged[1]-=2
        self.assertEqual(same_wall_slide_feasibility(wc,basin,shower,enlarged)['status'],'NEEDS FULL SOLVER')
        clean=dict(wc,cx=1,cy=2,id='unrelated')
        self.assertTrue(all(g>=r for g,r,_ in wc_side_clearances(clean,[],[0,0,4,4])))
        blocked=[('sibling wall',(0,2.1,3,2.2),'wall')]
        self.assertTrue(any(g<r for g,r,_ in wc_side_clearances(clean,blocked,[0,0,4,4])))

    def test_stair_return_step_and_floor_trim_use_real_datums(self):
        members = {m["id"]: m for m in self.members}
        for index in range(7):
            self.assertEqual(members["detail-stair-wall-stringer-%02d" % index]["mounting"]["host_id"], "stair-core-return")
        floor = members["detail-stair-wall-stringer-15"]
        self.assertEqual(floor["mounting"]["host_id"], "stair-basement-floor")
        self.assertEqual(min(p[2] for face in floor["faces"] for p in face), -3)

    def test_visible_wall_face_agrees_with_mounts_and_stays_in_package(self):
        spec = RS.build(R.design("D1"))
        treads = [b for b in spec["stair"] if b[5] - b[2] < 300]
        start, end = min(b[0] for b in treads) / 1000, max(b[3] for b in treads) / 1000
        walls = [m for m in self.scene["meshes"] if m.get("finished_host_id") == "stair-party-wall"]
        self.assertTrue(walls)
        for wall in walls:
            for face in wall["faces"]:
                for point in face:
                    self.assertAlmostEqual(point[1], -28.458)
                    self.assertLessEqual(start - 1e-9, point[0])
                    self.assertLessEqual(point[0], end + 1e-9)

    def test_design_elevations_and_tread_ends_remain_frozen(self):
        frozen = json.loads((Path(__file__).parent / "fixtures/c4-stair-phase1.json").read_text(encoding="utf-8"))
        old = {m["id"]: m for m in frozen["meshes"]}
        for mesh in self.members:
            before = old[mesh["id"]]
            for axis in (0, 2):
                if mesh["id"].endswith("stringer-06") or (axis == 2 and mesh["id"].endswith("stringer-15")):
                    continue  # stepped return contact and approved floor bearing trim
                self.assertEqual([p[axis] for f in mesh["faces"] for p in f],
                                  [p[axis] for f in before["faces"] for p in f])
        for mesh in self.members:
            if mesh["part_kind"] == "stair-stringer":
                self.assertEqual(max(p[1] for f in mesh["faces"] for p in f),
                                 max(p[1] for f in old[mesh["id"]]["faces"] for p in f))

    def test_render_meshes_contain_no_diagnostic_or_host_face_meshes(self):
        from archpipe.villa_render_contract import validate_scene
        render_mesh_ids = [m["id"] for m in self.scene["meshes"]]
        for mid in render_mesh_ids:
            self.assertFalse(mid.startswith("host-face-"), f"render mesh {mid} starts with host-face-")
            self.assertFalse(mid.startswith("support-"), f"render mesh {mid} starts with support-")
            self.assertFalse(mid.startswith("yard-boundary-edge-"), f"render mesh {mid} starts with yard-boundary-edge-")
            self.assertFalse(mid.startswith("hood-support-patch-"), f"render mesh {mid} starts with hood-support-patch-")
            self.assertFalse("-patch-" in mid, f"render mesh {mid} contains -patch-")
            self.assertNotEqual(mid, "finish-stair-basement-floor-host")

        for m in self.scene["meshes"]:
            self.assertFalse(m.get("diagnostic", False), f"render mesh {m['id']} is marked diagnostic")

        errors = validate_scene(self.scene)
        self.assertFalse(any("bookkeeping" in e or "host-face" in e for e in errors), errors)

        diagnostic_ids = [m["id"] for m in self.scene.get("diagnostic_meshes", [])]
        self.assertTrue(any(mid.startswith("host-face-") for mid in diagnostic_ids))
        self.assertTrue(any("stair-basement-floor" in mid for mid in diagnostic_ids))
        self.assertIn("stair-basement-floor", self.scene.get("mounting_hosts", {}))

        mutant = deepcopy(self.scene)
        mutant["meshes"].append(dict(
            id="host-face-bath-gwc-wc", group="shell", material="marble-bath",
            room="guest-wc", label="Measured finished fixing face",
            faces=[[[0, 0, 0], [1, 0, 0], [1, 1, 0]]], part_kind="finish-layer"
        ))
        mutant_errors = validate_scene(mutant)
        self.assertTrue(any("host-face-bath-gwc-wc" in e and "bookkeeping" in e for e in mutant_errors))

        mutant2 = deepcopy(self.scene)
        mutant2["meshes"].append(dict(
            id="support-detail-test-patch", group="shell", material="ceiling-white",
            room="guest-wc", label="Support patch",
            faces=[[[0, 0, 0], [1, 0, 0], [1, 1, 0]]], part_kind="finish-layer"
        ))
        mutant2_errors = validate_scene(mutant2)
        self.assertTrue(any("support-detail-test-patch" in e and "bookkeeping" in e for e in mutant2_errors))

    def test_real_full_scene_passes_write_contract(self):
        """(1) The real full scene passes villa_render's write-time contract."""
        from archpipe.villa_render_contract import validate_scene
        scene = VR.build()
        errors = validate_scene(scene)
        self.assertEqual(errors, [], f"Real full scene failed write-time contract: {errors}")

    def test_host_face_mesh_in_render_list_fails(self):
        """(2) A host-face mesh in the render list fails the write-time contract."""
        from archpipe.villa_render_contract import validate_scene
        scene = VR.build()
        mutant = deepcopy(scene)
        mutant["meshes"].append(dict(
            id="host-face-test-wall", group="shell", material="plaster-warm-white",
            room="lounge", label="Bookkeeping host face",
            faces=[[[0, 0, 0], [1, 0, 0], [1, 1, 0]]], part_kind="finish-layer"
        ))
        errors = validate_scene(mutant)
        self.assertEqual(len(errors), 1)
        self.assertIn("host-face-test-wall", errors[0])
        self.assertIn("must not be a diagnostic or host/support bookkeeping mesh", errors[0])

    def test_real_furniture_mesh_with_finished_host_id_passes(self):
        """(3) A real furniture mesh legitimately carrying finished_host_id passes."""
        from archpipe.villa_render_contract import validate_scene
        scene = VR.build()
        mutant = deepcopy(scene)
        furn = next(m for m in mutant["meshes"] if m["id"] == "furn-lounge-armchair-0")
        furn["finished_host_id"] = "support-lounge-armchair"
        furn["mounting"] = {"host_id": "support-lounge-armchair", "kind": "floor-standing"}
        errors = validate_scene(mutant)
        self.assertEqual(errors, [], f"Real furniture with finished_host_id failed write-time contract: {errors}")

    def test_real_scene_build_approvals_applied_to_single_channel(self):
        """Build real scene; prove no host-face/support in render meshes, all approvals applied to 1 channel."""
        scene = VR.build(views=[])
        self.assertIsNotNone(scene)

        render_mesh_ids = {m['id'] for m in scene['meshes']}
        diag_mesh_ids = {m['id'] for m in scene.get('diagnostic_meshes', [])}

        # Assert no host-face or support id is in the render meshes
        for mid in render_mesh_ids:
            self.assertFalse(mid.startswith('host-face-'), f"host-face ID found in render meshes: {mid}")
            self.assertFalse(mid.startswith('support-'), f"support ID found in render meshes: {mid}")

        # Assert every approved row was applied to exactly one channel
        from archpipe.concept.mounting_resume import APPROVALS
        knowledge_dir = APPROVALS.parent
        authority_files = [
            knowledge_dir / 'c4-bc-approvals.json',
            knowledge_dir / 'c4-d-lead-approvals.json',
            knowledge_dir / 'c4-e-lead-approvals.json',
            knowledge_dir / 'c4-final-approvals.json',
        ]
        retired = {'host-face-support-detail-vent-' + room + '-grille' for room in ('guest-wc', 'dirty-kitchen')}

        render_meshes = {m['id']: m for m in scene['meshes']}
        diag_meshes = {m['id']: m for m in scene.get('diagnostic_meshes', [])}
        all_movements = {r['id']: r for r in scene['mounting_movements']}

        approved_count = 0
        for auth_file in authority_files:
            auth_data = json.loads(auth_file.read_text(encoding='utf-8'))
            for row in auth_data['rows']:
                mid = row['id']
                if mid in retired:
                    continue
                approved_count += 1
                in_render = mid in render_mesh_ids
                in_diag = mid in diag_mesh_ids
                self.assertTrue(
                    in_render ^ in_diag,
                    f"Approved row {mid} must be applied to exactly one channel (render={in_render}, diag={in_diag})"
                )
                target = render_meshes[mid] if in_render else diag_meshes[mid]
                self.assertEqual(
                    target.get('faces'),
                    all_movements[mid]['proposed_faces'],
                    f"Faces for {mid} do not match proposed faces in movement record"
                )
                # Later explicit design fixes supersede a pose, but the
                # approved host and bounds must survive in the history.
                scheduled = [r for r in scene['mounting_movements'] if r['id']==mid
                             and r['host_id']==row['host_id'] and
                             all(abs(a-b)<1e-8 for key in ('old','new')
                                 for a,b in zip(r[key],row[key]))]
                self.assertTrue(scheduled, f"Frozen approval for {mid} absent from movement history")
                self.assertTrue(all('APPLIED' in r['approval'] for r in scheduled))

        self.assertGreater(approved_count, 0)


class FinishEvidence(unittest.TestCase):
    def test_hose_construction_generalises_and_rejects_buried_connections(self):
        from archpipe.concept.mounting_resume import wall_safe_hose
        for normal,starts in (((1,0,0),((.02,0,1.7),(.025,.1,1.3))),
                              ((0,1,0),((0,.02,1.7),(.1,.025,1.3)))):
            h=Host('other-villa','wall',(0,0,0),normal,Finish('finished',0))
            curve=wall_safe_hose(*starts,h)
            self.assertEqual(curve[0],list(starts[0]))
            self.assertEqual(curve[-1],list(starts[1]))
            self.assertGreater(min(sum(p[i]*normal[i] for i in range(3)) for p in curve),.008)
            self.assertLess(min(p[2] for p in curve),min(p[2] for p in starts))
            with self.assertRaisesRegex(ValueError,'Hose connection'):
                wall_safe_hose((0,0,1.7),starts[1],h)
    def test_bounded_movement_threshold_generalises(self):
        from archpipe.concept.fitting_mounting import package
        for distance, applied in ((.005, True), (.005001, False)):
            host = Host("other-villa", "wall", (0, 0, 0), (0,1,0), Finish("test-finish", distance))
            member = plane("independent", 0)
            scene = {"mounting_movements": []}
            package(scene,[member],host,0,"test","independent")
            self.assertEqual(member["faces"][0][0][1], distance if applied else 0)
            self.assertEqual(scene["mounting_movements"][0]["approval"].startswith("APPLIED"),applied)
    def test_stacked_hosts_same_finish_merge_offset_and_different_finish_do_not(self):
        lower = Host("lower", "wall", (0, 0, -3), (0, 1, 0), Finish("plaster", .013))
        upper = Host("upper", "wall", (0, 0, 0), (0, 1, 0), Finish("plaster", .013))
        lo = [[[0,.013,-3],[2,.013,-3],[2,.013,-.2],[0,.013,-.2]]]
        hi = [[[0,.013,0],[2,.013,0],[2,.013,3],[0,.013,3]]]
        self.assertEqual(len(stacked_finish_bridge(lower, upper, lo, hi, .2)), 1)
        offset = Host("offset", "wall", (0, .001, 0), (0,1,0), upper.finish)
        different = Host("tile", "wall", upper.structural_point, upper.normal, Finish("tile", .013))
        self.assertEqual(stacked_finish_bridge(lower, offset, lo, hi, .2), [])
        self.assertEqual(stacked_finish_bridge(lower, different, lo, hi, .2), [])
        self.assertEqual(stacked_finish_bridge(lower, upper, lo, hi, .19), [])
    def test_duplicate_dressing_retired_without_losing_review_view(self):
        views = {v["id"]: v for v in VR.VIEWS(R.design("D1"), resolve=False)}
        self.assertNotIn("v14-dressing", views)
        self.assertIn("v32-dressing-his", views)
        self.assertFalse(views["v31-dressing-hers"].get("final_only", False))
        self.assertTrue(views["v31-dressing-hers"]["caption_notes"])

    def test_one_record_preserves_verified_assumed_and_missing(self):
        record = json.loads(BUILD_UP_RECORD.read_text(encoding="utf-8"))["records"]
        self.assertEqual(record["interior-plaster"]["page"], "10.05")
        self.assertEqual(record["interior-plaster"]["status"], "VERIFIED")
        self.assertEqual(record["porcelain-wall-tile"]["status"], "ASSUMED")
        self.assertEqual(record["interior-marble-slab"]["status"], "ASSUMED")
        self.assertEqual(record["suspended-gypsum-ceiling"]["void_status"], "MISSING")
        self.assertIsNone(record["exterior-render"]["selected_mm"])
        self.assertAlmostEqual(finish_from_record("interior-plaster").thickness_m, .013)
        self.assertAlmostEqual(finish_from_record("marble-wall-thinset").thickness_m, .023)
        self.assertAlmostEqual(finish_from_record("porcelain-wall-thinset").thickness_m, .013)
