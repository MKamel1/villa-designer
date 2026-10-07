from archpipe.orientation import historical_aliases
"""Views chosen by intent (archpipe.concept.render_views): each rule is here because a draft broke it.
Client 2026-09-27: "Some of the cameras are looking at the wrong direction and uninformative"."""
import math
import unittest
import json
import gzip
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch

from archpipe.concept import render_views as RV
from archpipe.concept import revit_spec as RS
from archpipe.concept import villa_furnish as F
from archpipe.concept import villa_r11 as R

LAY = R.design("D1")
SP = RS.build(LAY)
ITEMS = {i["id"]: i for i in F.layout(LAY)}


class ChosenViews(unittest.TestCase):
    def test_g2f_real_outside_yard_cameras_cover_and_room_generalise(self):
        from archpipe.concept.garden_render_review import garden_camera_findings
        from archpipe.concept import villa_render as V
        frozen = historical_aliases(json.loads((Path(__file__).parent/'fixtures/garden-g2f-before.json').read_text()))
        scene = frozen['scene_for_camera']
        for view in frozen['outside_yard_views']:
            self.assertIn('outside yard', garden_camera_findings(view, scene)[0])
        upper = deepcopy(frozen['outside_yard_views'][1])
        upper['camera']['position'][2] = 1.35
        self.assertIn('outside yard', garden_camera_findings(upper, scene)[0])
        covered = deepcopy(frozen['outside_yard_views'][1])
        covered['id'] = 'another-garden-view'
        covered['camera']['position'] = [2.6, -28.35, -1.65]
        self.assertIn('under architectural cover', garden_camera_findings(covered, scene)[0])
        # This historical enclosure fixture has only two cover meshes;
        # it cannot prove a new upper camera's actual standing support.
        # Preserve that fail-closed result, then supply the frozen native
        # floor geometry for the clean current camera case.
        floor = json.loads(gzip.decompress((Path(__file__).parent/
            'fixtures/garden-g6-v27-occluded-before.json.gz').read_bytes()))
        supported = deepcopy(scene)
        supported['meshes'].extend(floor['floor_meshes'])
        supported['materials'].update(floor['materials'])
        for view in V.VIEWS(LAY, resolve=False):
            if 'standing_ground_m' in view:
                self.assertIn('no actual standing floor', str(garden_camera_findings(view, scene)))
                self.assertEqual(garden_camera_findings(view, supported), [], view['id'])
            else:
                self.assertEqual(garden_camera_findings(view, scene), [], view['id'])
        through = deepcopy(covered)
        through['camera']['position'] = [14.2, -21.6, -1.65]
        through['standing_room'] = 'dirty-kitchen'
        self.assertEqual(garden_camera_findings(through, scene), [])
        through['standing_room'] = 'lounge'
        self.assertTrue(garden_camera_findings(through, scene))
        translated = deepcopy(scene)
        domain = translated['garden_camera_domain']
        domain['yard_polygon_m'] = [[x+11, y-5] for x, y in domain['yard_polygon_m']]
        domain['ground_m'] += 7
        domain['upper_datum_m'] += 7
        for mesh in translated['meshes']:
            for face in mesh['faces']:
                for point in face:
                    point[0] += 11; point[1] -= 5; point[2] += 7
        old = deepcopy(frozen['outside_yard_views'][1]); old['id'] = 'renamed-view'
        old['camera']['position'] = [old['camera']['position'][0]+11, old['camera']['position'][1]-5, old['camera']['position'][2]+7]
        self.assertTrue(garden_camera_findings(old, translated))
        self.assertTrue(garden_camera_findings(covered, {}))
        self.assertEqual(garden_camera_findings({'subjects': []}, {}), [])

    def test_g2f_foreground_mullion_real_camera_and_translated_sibling(self):
        from archpipe.concept.garden_render_review import opening_frame_findings
        from archpipe.concept import villa_render as V
        frozen=historical_aliases(json.loads((Path(__file__).parent/'fixtures/garden-g2f-before.json').read_text()))
        old=frozen['views'][0];scene=frozen['scene_for_frames']
        self.assertEqual(opening_frame_findings(old,scene)[0]['face_indices'],[116,117,118,119])
        new=next(v for v in V.VIEWS(resolve=False) if v['id'].startswith('v28'))
        self.assertNotEqual(new['camera']['position'],old['camera']['position'])
        self.assertEqual(opening_frame_findings(new,scene),[])
        translated=deepcopy(scene);view=deepcopy(old);view['id']='another-through-opening-view'
        for m in translated['meshes']:
            for f in m['faces']:
                for q in f:q[0]+=10;q[1]-=4;q[2]+=7
        for key in ('position','target'):
            view['camera'][key]=[view['camera'][key][0]+10,view['camera'][key][1]-4,view['camera'][key][2]+7]
        self.assertTrue(opening_frame_findings(view,translated))
        # A window behind the main subject is a facade in the image, not
        # an opening through which this photograph is taken.
        remote=deepcopy(scene)
        for m in remote['meshes']:
            if m.get('part_kind') in ('window-frame', 'glass-pane'):
                for f in m['faces']:
                    for q in f:q[0]+=10
        self.assertEqual(opening_frame_findings(old,remote),[])

    def test_frozen_east_wc_vertical_lens_need_and_whole_mesh(self):
        from scripts.villa_render_views import subject_mesh_frame_violations
        frozen = historical_aliases(json.loads((Path(__file__).parent / "fixtures/c4-family-wc-lens-before.json").read_text()))
        meshes = {"meshes": [{"id": "furn-fb-wc-0", "label": "fb-wc",
                               "faces": [frozen["wc_vertices"]]}]}
        old = {"resolution": [1920, 1280], "camera": {"position": [9.727, -24.971, 1.35],
               "target": [12.025, -26.899, 1.35], "lens_mm": 16, "sensor_mm": 36}}
        self.assertEqual(subject_mesh_frame_violations(old, meshes, "fb-wc"), ["bottom edge"])
        original_items = deepcopy(frozen["items"])
        with patch.object(F, "layout", return_value=frozen["items"]), \
             patch.object(F, "_walls", return_value=frozen["walls"]), \
             patch.object(F, "_columns", return_value=frozen["columns"]):
            narrow = RV.choose(frozen["layout"], frozen["room"], frozen["subjects"], lens_mm=24, sp=frozen["spec"])
            wide = RV.choose(frozen["layout"], frozen["room"], frozen["subjects"], lens_mm=16, sp=frozen["spec"])
        self.assertFalse(narrow["subjects_in_frame"])
        self.assertEqual(narrow["framed_candidates"], 0)
        self.assertLess(narrow["framing"]["horizontal_need_deg"], narrow["framing"]["horizontal_limit_deg"])
        self.assertGreater(narrow["framing"]["lower_top_need_deg"], narrow["framing"]["vertical_limit_deg"])
        self.assertGreater(narrow["framing"]["whole_subject_need_deg"], narrow["framing"]["vertical_limit_deg"])
        self.assertTrue(wide["subjects_in_frame"])
        self.assertGreater(wide["framed_candidates"], 0)
        self.assertEqual(wide["search_step_m"], RV.STEP/4)
        new = {**old, "camera": {**old["camera"], "position": wide["position"]+[1.35],
                                "target": wide["target"]+[1.35]}}
        self.assertEqual(subject_mesh_frame_violations(new, meshes, "fb-wc"), [])
        self.assertEqual(frozen["items"], original_items, "camera placement must leave the fixtures fixed")
        # Independent injected clipping must still fail: neither height nor
        # horizontal coverage may be excused by the corrected lens diagnostics.
        mutant = deepcopy(new)
        mutant["camera"]["lens_mm"] = 24
        self.assertIn("bottom edge", subject_mesh_frame_violations(mutant, meshes, "fb-wc"))
        mutant = deepcopy(new)
        mutant["camera"]["target"] = [new["camera"]["position"][0]-3, new["camera"]["position"][1], 1.35]
        self.assertTrue(subject_mesh_frame_violations(mutant, meshes, "fb-wc"))
        self.assertTrue(subject_mesh_frame_violations(new, {"meshes": []}, "fb-wc"))

    def test_whole_wc_search_generalises_to_renamed_translated_room(self):
        frozen = historical_aliases(json.loads((Path(__file__).parent / "fixtures/c4-family-wc-lens-before.json").read_text()))
        room = frozen["layout"]["rooms"]["family-bath"]
        room["rect"] = [v+7 if k % 2 == 0 else v-4 for k, v in enumerate(room["rect"])]
        lay = {"rooms": {"compact-room": room}}
        for item in frozen["items"]:
            item["cx"] += 7
            item["cy"] -= 4
            if item["id"] == "fb-wc":
                item["id"] = "other-pan"
            if item["room"] == "family-bath":
                item["room"] = "compact-room"
        for collection in ("doors", "windows", "bath_fittings"):
            for record in frozen["spec"][collection]:
                # The spec also carries line/zone fitting records. Only the
                # point records are consumed by this camera search.
                if "x" in record and "y" in record:
                    record["x"] += 7
                    record["y"] -= 4
                if record.get("room") == "family-bath":
                    record["room"] = "compact-room"
                if "rooms" in record:
                    record["rooms"] = ["compact-room" if r == "family-bath" else r for r in record["rooms"]]
        translated = lambda boxes: [[v+7 if k % 2 == 0 else v-4 for k, v in enumerate(q)] for q in boxes]
        with patch.object(F, "layout", return_value=frozen["items"]), \
             patch.object(F, "_walls", return_value=translated(frozen["walls"])), \
             patch.object(F, "_columns", return_value=translated(frozen["columns"])):
            c = RV.choose(lay, "compact-room", ["other-pan"], lens_mm=16, sp=frozen["spec"])
            narrow = RV.choose(lay, "compact-room", ["other-pan"], lens_mm=24, sp=frozen["spec"])
        self.assertTrue(c["subjects_in_frame"])
        self.assertGreater(c["framed_candidates"], 0)
        self.assertFalse(narrow["subjects_in_frame"])
        self.assertAlmostEqual(c["position"][0]-7, 9.602, places=3)
        self.assertAlmostEqual(c["position"][1]+4, -24.846, places=3)

    def test_live_east_wc_is_wholly_in_frame(self):
        from scripts.villa_render_views import subject_mesh_frame_violations
        from archpipe.concept import villa_render as V
        scene = V.build(LAY)
        view = next(v for v in scene["views"] if v["id"] == "v35-family-bath-wc")
        self.assertEqual(subject_mesh_frame_violations(view, scene, "fb-wc"), [])
        self.assertEqual(view["camera"]["lens_mm"], 16)

    def test_exterior_camera_clearance_catches_old_v26_and_v28(self):
        from scripts import villa_render_views as views
        from archpipe.concept import villa_render as V
        scene = V.build(LAY)
        items = {i["id"]: i for i in F.layout(LAY)}
        by_id = {v["id"]: v for v in scene["views"]}
        for name in ("v26-top-garden-east", "v28-east-yard-below"):
            self.assertEqual(views.camera_proximity_violations(by_id[name], scene, items), [], name)
        old26 = {**by_id["v26-top-garden-east"], "camera": {**by_id["v26-top-garden-east"]["camera"],
                                                              "position": [14.5, -22.0, 1.35]}}
        old28 = {**by_id["v28-east-yard-below"], "camera": {**by_id["v28-east-yard-below"]["camera"],
                                                                "position": [16.1, -21.0, -1.65],
                                                                "target": [20.5, -22.1, -1.65], "lens_mm": 24}}
        # Retired specimens remain a frozen historical camera proof, not
        # restored objects or invisible aliases in the current garden.
        import json
        from pathlib import Path
        frozen=historical_aliases(json.loads((Path(__file__).parent/'fixtures/garden-g1-before.json').read_text()))
        historic={**scene,"props":frozen["props"]}
        self.assertTrue(any("olive" in name for name, _ in views.camera_proximity_violations(old26, historic, items)))
        self.assertTrue(any("lemon" in name for name, _ in views.dominant_foreground_props(old28, historic)))
        self.assertEqual(views.dominant_foreground_props(by_id["v28-east-yard-below"], scene), [])

    def test_storage_views_show_joinery_and_windowless_room_lighting(self):
        from archpipe.concept import villa_render as V
        scene = V.build(LAY)
        views = {v["id"]: v for v in scene["views"]}
        under_stair = views["v29-under-stair-store"]
        self.assertEqual(set(under_stair["subjects"]), {"stair-flight-store", "stair-landing-store"})
        # The old chosen camera at x=9.577 looked THROUGH the stair treads at
        # the stores. The northwest standing point sees their fronts first.
        from scripts import villa_render_views as render_plan
        self.assertFalse(render_plan.under_stair_occlusion_violation(under_stair))
        self.assertEqual(render_plan.storage_front_occlusions(under_stair, ITEMS), [])
        self.assertEqual(under_stair["camera"]["position"][:2], [5.2, -25.9])
        self.assertEqual(under_stair["camera"]["lens_mm"], 24)
        from archpipe.concept import villa_furnish3d as F3
        old_parts = {}
        for item_id in under_stair["subjects"]:
            item = ITEMS[item_id]
            parts = [(name, box) for name, box in F3.body(item) if name != "sliding-door-pocketed"]
            for name, box in F3.body(item):
                if name.endswith("-back"):
                    xa, _, _, xb, _, top = box
                    parts.append(("sliding-door-open", (xb - (xb - xa) * .28, item["d"] / 2 - .045,
                                                        .1, xb - .006, item["d"] / 2 - .025, top)))
            old_parts[item_id] = parts
        self.assertTrue(render_plan.storage_front_occlusions(under_stair, ITEMS, old_parts),
                        "the actual former 28-percent fronts must fail")
        flight = ITEMS["stair-flight-store"]
        closed = {flight["id"]: F3.body(flight) + [("sliding-door-closed", (-flight["w"] / 2,
                    flight["d"] / 2 - .04, .1, flight["w"] / 2, flight["d"] / 2 - .02, 1.5))]}
        self.assertTrue(render_plan.storage_front_occlusions(under_stair, ITEMS, closed))
        old = {**under_stair, "camera": {**under_stair["camera"], "position": [9.577, -27.871, -1.65]}}
        self.assertTrue(render_plan.under_stair_occlusion_violation(old))
        under_ramp = views["v30-under-ramp-store"]
        self.assertEqual(under_ramp["exposure"], "evening")
        self.assertEqual(under_ramp["dimmers"]["task"], 1.0)
        self.assertIn("task", under_ramp["layers_on"])
        self.assertTrue(any("no window" in note.lower() for note in under_ramp["caption_notes"]))

    def test_exterior_lounge_subject_uses_built_sofa_bounds(self):
        from scripts import villa_render_views as views
        scene = {"meshes": [{"id": "landscape-sofa-00",
                             "faces": [[[24.0, -28.0, -3.0], [26.1, -28.0, -3.0],
                                        [26.1, -27.15, -3.0], [24.0, -27.15, -3.0]]]}]}
        self.assertEqual(views.subject_footprint("landscape-sofa", ITEMS, LAY["rooms"], scene),
                         (24.0, -28.0, 26.1, -27.15))
        with self.assertRaisesRegex(ValueError, "unresolved view subject"):
            views.subject_footprint("landscape-sofa", ITEMS, LAY["rooms"], {"meshes": []})

    def test_imported_garden_subjects_resolve_from_measured_props_without_markers(self):
        from scripts import villa_render_views as views
        from archpipe.concept import villa_landscape as L, revit_spec as RS
        _,props,_,_=L.review_candidate(RS.build(LAY),LAY)
        tree=next(p for p in props if p["asset"]=="sf_frangipani")
        scene={"meshes":[],"props":[tree]}
        expected=L._rect(tree)
        for got,need in zip(views.subject_footprint(tree["id"],ITEMS,LAY["rooms"],scene),expected):
            self.assertAlmostEqual(got,need,places=4)
        renamed=dict(tree,id="another-imported-specimen")
        for got,need in zip(views.subject_footprint(renamed["id"],ITEMS,LAY["rooms"],{"meshes":[],"props":[renamed]}),expected):
            self.assertAlmostEqual(got,need,places=4)
        with self.assertRaisesRegex(ValueError,"unresolved view subject"):
            views.subject_footprint(tree["id"],ITEMS,LAY["rooms"],{"meshes":[],"props":[]})

    def test_v07_reframed_tree_and_living_sofa_without_design_movement(self):
        from scripts import villa_render_views as views
        from archpipe.concept import villa_render as V
        scene=V.build(LAY)
        view=next(v for v in scene["views"] if v["id"]=="v07-terrace-dusk")
        self.assertNotIn("landscape-sofa",view["subjects"])
        for subject in view["subjects"]:
            self.assertEqual(views.subject_mesh_frame_violations(view,scene,subject),[])
        old={**view,"camera":{**view["camera"],"position":[28.2,-21.2,-1.65],
                            "target":[21.0,-26.4,-1.65],"shift_y":.10}}
        self.assertIn("horizontal edge",views.subject_mesh_frame_violations(old,scene,"landscape-tree-south"))

    def test_d4_garden_handoff_and_west_view_hold_actual_geometry(self):
        from scripts import villa_render_views as views
        from archpipe.concept import villa_render as V
        scene=V.build(LAY)
        by={v['id']:v for v in scene['views']}
        west=by['v36-north-garden']
        self.assertEqual(west['camera']['lens_mm'],24)
        self.assertEqual(west['camera']['position'][2],-1.65)
        self.assertEqual(west['camera']['target'][2],-1.65)
        self.assertEqual(views.camera_proximity_violations(west,scene,ITEMS),[])
        for vid in ('v36-north-garden','v37-north-garden-lounge','v38-north-garden-floor-bed'):
            for prefix in by[vid]['subjects']:
                self.assertEqual(views.subject_mesh_frame_violations(by[vid],scene,prefix),[])
        self.assertEqual(set(by['v38-north-garden-floor-bed']['subjects']),
                         {'landscape-bed-north','landscape-north-back-00','landscape-north-back-01','landscape-north-mid-00','landscape-north-mid-01','landscape-north-front','landscape-north-edge'})
        self.assertFalse(any(p['asset'] in ('outdoor_table_chair_set_01','sf_egg_chair') for p in scene['props']))
        bad=deepcopy(west)
        # Reverse the current sightline. The former absolute target points
        # toward the swing once the lens moves from the sister side to the
        # required open-yard side, so it is no longer an adverse case.
        position, target = bad['camera']['position'], bad['camera']['target']
        bad['camera']['target']=[2*position[0]-target[0], 2*position[1]-target[1], position[2]]
        self.assertTrue(views.subject_mesh_frame_violations(bad,scene,west['subjects'][0]))
        for vid in ('v07-terrace-dusk','v19-garden-facade','v25-top-garden-gate',
                    'v26-top-garden-east','v27-east-yard-above','v28-east-yard-below'):
            for subject in by[vid]['subjects']:
                self.assertEqual(views.subject_mesh_frame_violations(by[vid],scene,subject),[],(vid,subject))
        for vid in ('v02-garden-living','v10-living-evening','v07-terrace-dusk','v19-garden-facade'):
            self.assertIn('offset from centre for a clear door route',' '.join(by[vid]['caption_notes']))

    def test_g3_top_views_name_physical_troughs_drifts_benches_and_open_colour(self):
        from scripts import villa_render_views as views
        from archpipe.concept import villa_render as V
        scene=V.build(LAY)
        by={v['id']:v for v in scene['views']}
        for vid in ('v25-top-garden-gate','v26-top-garden-east'):
            view=by[vid]
            self.assertEqual(set(view['subjects']),{'landscape-top-bench','landscape-top-trough',
                                                  'landscape-top-deck-east','landscape-top-roof'})
            self.assertIn('trough colour: dark bronze, pending client confirmation',' '.join(view['caption_notes']))
            self.assertTrue(view['final_only'])
            self.assertEqual(views.camera_proximity_violations(view,scene,ITEMS),[])
            for subject in view['subjects']:
                self.assertTrue(views.subject_points(subject,scene))
                self.assertEqual(views.subject_mesh_frame_violations(view,scene,subject),[])
        self.assertEqual(by['v25-top-garden-gate']['camera']['position'],[4.4,-21.7,1.35])
        self.assertEqual(by['v26-top-garden-east']['camera']['position'],[6.95,-23.2,1.35])
        import json
        from pathlib import Path
        before=historical_aliases(json.loads((Path(__file__).parent/'fixtures/garden-g3-v27-before.json').read_text()))
        self.assertTrue(any(pid=='landscape-top-pot-ixora-1' for pid,_ in
                            views.camera_proximity_violations(before,scene,ITEMS)))
        current=by['v27-east-yard-above']
        self.assertEqual(views.camera_proximity_violations(current,scene,ITEMS),[])
        self.assertEqual(set(current['subjects']),{'landscape-east-back','landscape-east-mid',
                                                  'landscape-east-front'})
        self.assertEqual(current['standing_ground_m'],0.)
        self.assertEqual(set(current['visibility_targets']),{'landscape-east-back-01','landscape-east-mid-01','landscape-east-front-01'})
        self.assertIn('complete trellis',' '.join(current['caption_notes']))
        self.assertIn('Full soil-bed extent is outside the frame',' '.join(current['caption_notes']))
        for subject in current['subjects']:
            self.assertEqual(views.subject_mesh_frame_violations(current,scene,subject),[])
        # Procedural appearances cannot bypass a guard that once checked
        # only imported props. A renamed real aloe leaf mesh still fires.
        source=next(m for m in scene['meshes'] if m.get('species')=='Aloe vera')
        points=[p for f in source['faces'] for p in f]
        close=deepcopy(current)
        close['camera']['position']=[sum(p[0] for p in points)/len(points),
                                     sum(p[1] for p in points)/len(points),1.35]
        renamed=dict(source,id='unrelated-procedural-rosette')
        self.assertTrue(views.camera_proximity_violations(close,dict(meshes=[renamed],props=[]),{}))

    def test_every_view_subject_matches_scene_content(self):
        """Round-2 draft: v07 still named "terrace lounge set" after the landscape replaced that set, so the
        renderer matched nothing and QA reported the subject out of frame. Mirror villa_scene.subjects' matching."""
        from archpipe.concept import villa_render as V
        scene = V.build(LAY)
        meshes = scene["meshes"] + scene["props"]

        def matched(s):
            return [m for m in meshes if m["id"] == s or m["id"].startswith(s) or m.get("room") == s
                    or m.get("label") == s]
        orphans = [(v["id"], s) for v in scene["views"] for s in v["subjects"] if not matched(s)]
        self.assertEqual(orphans, [])
        self.assertFalse(matched("terrace lounge set"), "the stale v07 subject must stay unmatched (the real defect)")
        # Retiring v14 shifted v25 to position 23. View identity must survive
        # retirement/reordering; selecting a list tail silently lost v25.
        expected_prefixes = ["v%02d" % n for n in range(25, 35)]
        by_prefix = {v["id"].split("-")[0]: v for v in scene["views"]}
        old_notes=historical_aliases(json.loads((Path(__file__).parent/'fixtures/garden-g4-captions-before.json').read_text()))
        self.assertNotIn('photographic',str(old_notes[1]['caption_notes']))
        self.assertIn('whole ground-level bed',str(old_notes[2]['caption_notes']))
        for prefix in ('v36','v37','v38'):
            notes=' '.join(by_prefix[prefix]['caption_notes'])
            self.assertIn('Authored botanical appearances ASSUMED',notes)
            self.assertIn('photographic likeness, procurement and Egypt nursery performance UNVERIFIED',notes)
        self.assertIn('near corner is partly screened',str(by_prefix['v38']['caption_notes']))
        self.assertNotIn('complete',by_prefix['v38']['title'])
        self.assertTrue(set(expected_prefixes).issubset(by_prefix))
        additions = [by_prefix[prefix] for prefix in expected_prefixes]
        self.assertEqual([v["id"].split("-")[0] for v in additions],
                         expected_prefixes)
        self.assertTrue(all(v["subjects"] for v in additions))
        self.assertTrue(all(v["camera"]["position"][2] == v["camera"]["target"][2]
                            for v in additions), "the added cameras must stay level")
        self.assertTrue(all(v["camera"]["lens_mm"] in (16, 24) for v in additions))
        self.assertEqual([v["exposure"] for v in additions[:4]], ["exterior-day"] * 4)

    def test_bed_is_seen_from_its_front(self):
        """Draft 11's parents' view stood at the entry and faced the windows; the headboard was out of frame."""
        c = RV.choose(LAY, "parents-bed", ["pb-bed"], lens_mm=24, sp=SP)
        q = F.footprint(ITEMS["pb-bed"])
        fx, fy = {0: (0, 1), 180: (0, -1), -90: (1, 0), 90: (-1, 0)}[ITEMS["pb-bed"]["rot"]]
        x, y = c["position"]
        self.assertTrue(c["subjects_in_frame"])
        self.assertGreater((x - (q[0] + q[2]) / 2) * fx + (y - (q[1] + q[3]) / 2) * fy, 0)

    def test_no_piece_looms_in_front_of_the_lens(self):
        """Draft 11's dressing view was 60 % wardrobe end panel, 0.68 m from the lens."""
        c = RV.choose(LAY, "parents-dressing", ["pd-hang-1"], lens_mm=24, sp=SP)
        x, y = c["position"]
        yaw = math.radians(c["yaw_deg"])
        half = math.atan(18 / 24)
        for i in F.layout(LAY):
            if i["level"] != "GF":
                continue
            q = F.footprint(i)
            qx, qy = min(max(x, q[0]), q[2]), min(max(y, q[1]), q[3])
            ang = RV._angle(x, y, (q[0] + q[2]) / 2, (q[1] + q[3]) / 2, yaw)
            self.assertFalse(math.hypot(qx - x, qy - y) < 0.8 and abs(ang) < half, i["id"] + " looms")

    def test_subjects_are_not_behind_a_wall(self):
        """Draft 11's family-bath WC passed the frame test but stood behind the shower wall."""
        c = RV.choose(LAY, "family-bath", ["fb-basin", "fb-wc", "fb-shower"], lens_mm=16, sp=SP)
        x, y = c["position"]
        walls = F._walls(SP, "GF") + F._columns()
        for s in ("fb-basin", "fb-wc", "fb-shower"):
            q = F.footprint(ITEMS[s])
            cx, cy = (q[0] + q[2]) / 2, (q[1] + q[3]) / 2
            k = max(2, int(math.hypot(cx - x, cy - y) / 0.05))
            for n in range(1, k):
                px, py = x + (cx - x) * n / k, y + (cy - y) * n / k
                if math.hypot(px - x, py - y) > 0.05:
                    self.assertFalse(any(RV._near(w, px, py, -0.01) for w in walls), s + " is behind a wall")

    def test_a_low_subject_is_not_below_the_frame(self):
        """Draft 13's family-bath view 'held' the WC in plan while its 0.4 m top sat 42 deg below the eye, out of the
        bottom of a 16 mm frame (37 deg). Basin + shower + WC fit no standing point once height is checked."""
        c = RV.choose(LAY, "family-bath", ["fb-basin", "fb-wc", "fb-shower"], lens_mm=16, sp=SP)
        self.assertFalse(c["subjects_in_frame"])
        c = RV.choose(LAY, "family-bath", ["fb-basin", "fb-shower"], lens_mm=16, sp=SP)
        self.assertTrue(c["subjects_in_frame"])

    def test_guest_rain_head_requires_wider_vertical_frame(self):
        subjects = ["gwc-shower", "detail-gwc-rain-head", "detail-gwc-hand-shower"]
        narrow = RV.choose(LAY, "guest-wc", subjects, lens_mm=24, sp=SP)
        wide = RV.choose(LAY, "guest-wc", subjects, lens_mm=16, sp=SP)
        self.assertFalse(narrow["subjects_in_frame"])
        self.assertTrue(wide["subjects_in_frame"])
        x, y = wide["position"]
        walls = F._walls(SP, "B") + F._columns()
        for fitting in (f for f in SP["bath_fittings"] if f["id"] in ("gwc-rain-head", "gwc-hand-shower")):
            for step in range(1, 100):
                px = x + (fitting["x"] - x) * step / 100
                py = y + (fitting["y"] - y) * step / 100
                self.assertFalse(any(RV._near(wall, px, py, -.01) for wall in walls),
                                 fitting["id"] + " is blocked by a wall")

    def test_a_point_in_a_door_band_is_a_doorway_point(self):
        """A camera 30 mm inside the ensuite stood in its closed door leaf (a black band in draft 10)."""
        d = next(d for d in SP["doors"] if set(d["rooms"]) == {"parents-dressing-ext", "parents-ensuite"})
        h = F._door_axis(d) == "h"
        # right beside the jamb, inside the wall band: never a standing point
        jx, jy = (d["x"] + d["width"] / 2 - 0.05, d["y"] - 0.03) if h else (d["x"] - 0.03, d["y"] + d["width"] / 2 - 0.05)
        self.assertFalse(RV._in_opening(SP, "GF", jx, jy, "parents-ensuite"))


if __name__ == "__main__":
    unittest.main()


class G4CameraPhysicalContents(unittest.TestCase):
    def test_g4_ground_plants_cannot_bypass_lens_clearance(self):
        from scripts.villa_render_views import camera_proximity_violations
        from archpipe.concept import villa_render as V
        scene=V.build(views=[])
        source=deepcopy(next(m for m in scene['meshes'] if m.get('species')=='Rhapis excelsa'))
        source['id']='another-ground-fan'
        view=deepcopy(next(v for v in V.VIEWS(resolve=False) if v['id'].startswith('v36')))
        view['camera']['position']=[source['center'][0],source['center'][1],source['root_z_m']+1.35]
        self.assertTrue(camera_proximity_violations(view,dict(meshes=[source],props=[]),{}))
        view['camera']['position'][0]+=5
        self.assertEqual(camera_proximity_violations(view,dict(meshes=[source],props=[]),{}),[])
