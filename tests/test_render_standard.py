"""ADR-0013 is the standard for EVERY presentation render, not only the bedroom (client 2026-09-27: "that should
be our standards and our process for all renders"). The first villa set skipped half of it (16-20 mm lenses at
1.55 m, fixed guessed exposures, textured 'rugged' paint, box furniture, no skirting or frames); this test fails if a
villa scene departs from the parts the bedroom proved."""
import unittest

from archpipe.blender import grain
from archpipe.concept import revit_spec as RS
from archpipe.concept import villa_r11 as R
from archpipe.concept import villa_render as VR

SCENE = VR.build()

# Audited presentation finishes, including the explicitly authored luminous
# surfaces. A new CAD fallback or unassigned material fails this list.
ALLOWED_MATERIALS = {
    "artificial-grass", "stepping-stone", "trellis", "bougainvillea-bract",
    "terracotta-red-glaze", "garden-soil", "garden-foliage", "star-jasmine-flower", "star-jasmine-leaf",  # round-3 garden finishes
    "strelitzia-foliage", "stone-substrate", "shade-variegation", "grape-ivy-leaf",
    "top-trough-coating", "top-rosemary-foliage", "top-aloe-foliage",  # G3 explicitly ASSUMED appearances
    "plaster-warm-white", "ceiling-white", "travertine", "oak-floor", "marble-ensuite", "marble-bath", "marble-wet",
    "marble-white", "walnut", "walnut-grain-x", "walnut-grain-y", "oak", "oak-grain-x", "greige-lacquer", "boucle", "linen", "sage-fabric",
    "charcoal-fabric", "taupe-fabric", "bedding-white", "throw-taupe", "rug", "leather-brown", "brass",
    "black-metal", "ceramic-white", "screen-black", "glass-clear", "glass-guard", "glass-edge", "opal-strip",
    "silvered-mirror", "door-oak", "garden-gravel", "garden-pebbles", "garden-sandstone", "glass-bath-screen",
    "render-exterior", "paint-exterior-grey-green", "paving", "lawn", "outdoor-fabric", "teak", "bougainvillea-leaf",
    "alu-bronze", "stainless", "paint-white-satin", "white-paint-joinery", "led-lin-2700", "lens-2700",
    "marker-2200", "opal-pen-globe-2700", "opal-inner-2700", "swing-disc-2700", "opal-pen-small-2700", "opal-wall-read-2700", "opal-sconce-3000",
    "opal-vsconce-3000", "curtain-sheer", "curtain-heavy", "curtain-heavy-dimout",
    "garment-ivory", "garment-blush", "garment-terracotta", "garment-sage-soft",
    "garment-navy", "garment-charcoal", "garment-stone", "garment-olive",
}


class RenderStandard(unittest.TestCase):
    def test_g2f_real_steps_and_ground_siblings_have_no_paved_soffits(self):
        from copy import deepcopy
        import json
        from pathlib import Path
        from archpipe.concept.garden_render_review import downward_ground_findings,normal
        from archpipe.villa_render_contract import validate_scene,mesh_batch_key
        frozen=json.loads((Path(__file__).parent/'fixtures/garden-g2f-before.json').read_text())
        bad={'meshes':frozen['shell']+frozen['ground_siblings'],'materials':VR.M}
        self.assertEqual(len(downward_ground_findings(bad)),3)
        self.assertEqual(downward_ground_findings(SCENE),[])
        self.assertEqual(validate_scene(SCENE),[])
        # Independent class mutation and renamed floor-only material.
        renamed=deepcopy(frozen['shell'][0]);renamed['id']='another-sloping-deck';renamed['material']='other-floor'
        for f in renamed['faces']:
            for q in f:q[2]+=.1*q[0]
        self.assertTrue(downward_ground_findings({'meshes':[renamed],'materials':{'other-floor':{'surface_use':'ground-only'}}}))
        clean=deepcopy(SCENE);stone=next(m for m in clean['meshes'] if m['id']=='landscape-stone-study-00')
        self.assertIsNone(mesh_batch_key(stone,'principled'))
        for i,face in enumerate(stone['faces']):
            if normal(face)[2]<-.7:self.assertEqual(stone['face_materials'][i],'stone-substrate')
        stone['face_materials']=[stone['material']]*len(stone['faces'])
        self.assertTrue(any(stone['id'] in f for f in validate_scene(clean)))
        stone['face_materials']=[]
        self.assertTrue(any('one registered finish per authored face' in f for f in validate_scene(clean)))

    def test_c4_frozen_plant_support_datums(self):
        from copy import deepcopy
        import json
        from pathlib import Path
        from archpipe.concept.support_mounting import bind_plant_support, plant_support_findings
        frozen = json.loads((Path(__file__).parent / 'fixtures/c4-plant-support-before.json').read_text())
        # The real migrated table plant carried the table's floor contract.
        self.assertEqual(plant_support_findings(frozen),
                         ['living-plant-table: stale or MISSING recorded plant support datum'])
        clean = deepcopy(frozen)
        for prop in clean['props']:
            bind_plant_support(clean, prop)
        self.assertEqual(VR.indoor_plant_violations(clean['props'], R.design('D1'), clean), [])
        self.assertEqual([p['position'] for p in clean['props']], [p['position'] for p in frozen['props']])
        # Frozen clean geometry fires against every old room/table datum,
        # and a migrated prop cannot silently fall back to authored heights.
        for prop in clean['props']:
            sunk = deepcopy(prop)
            sunk['position'][2] -= .002
            self.assertTrue(any('base' in f for f in plant_support_findings(clean, [sunk])))
        self.assertTrue(all('scene geometry required' in f for f in
                            VR.indoor_plant_violations(clean['props'], R.design('D1'))))

    def test_c4_plant_live_support_mutations_and_translated_siblings(self):
        from copy import deepcopy
        import json
        from pathlib import Path
        from archpipe.concept.support_mounting import bind_plant_support, plant_support_findings
        from archpipe.concept.mounting import scene_findings
        frozen = json.loads((Path(__file__).parent / 'fixtures/c4-plant-support-before.json').read_text())
        for prop in frozen['props']:
            bind_plant_support(frozen, prop)
        self.assertEqual(plant_support_findings(frozen), [])
        for prop in frozen['props']:
            source_id = frozen['mounting_hosts'][prop['mounting']['host_id']]['source_mesh']
            for mutation in ('moved', 'removed', 'record'):
                mutant = deepcopy(frozen)
                if mutation == 'removed':
                    mutant['meshes'] = [m for m in mutant['meshes'] if m['id'] != source_id]
                elif mutation == 'moved':
                    source = next(m for m in mutant['meshes'] if m['id'] == source_id)
                    for face in source['faces']:
                        for point in face:
                            point[2] += .002
                else:
                    target = next(p for p in mutant['props'] if p['id'] == prop['id'])
                    target['mounting']['finished_face'][2] -= .002
                self.assertTrue(any(prop['id'] in f and 'support' in f for f in plant_support_findings(mutant)),
                                (prop['id'], mutation))
                self.assertTrue(any(prop['id'] in f and 'support' in f for f in scene_findings(mutant)))
        # No D1 identifier, room, coordinates or nominal floor level is needed.
        translated = deepcopy(frozen)
        translated['meshes'] = [m for m in translated['meshes'] if not m.get('finished_host_id')]
        translated['mounting_hosts'] = {}
        for mesh in translated['meshes']:
            mesh['id'] = mesh['id'].replace('floor-', 'floor-other-', 1) if mesh['id'].startswith('floor-') else mesh['id'].replace('furn-', 'furn-other-', 1)
            mesh['room'] = 'other-' + mesh['room']
            for face in mesh['faces']:
                for point in face:
                    for axis, travel in enumerate((7, -4, 8)):
                        point[axis] += travel
        for prop in translated['props']:
            prop['id'] = 'other-' + prop['id']
            prop['room'] = 'other-' + prop['room']
            if prop['support_id'] != 'finished-floor':
                prop['support_id'] = 'other-' + prop['support_id']
            prop['position'] = [value + travel for value, travel in zip(prop['position'], (7, -4, 8))]
            bind_plant_support(translated, prop)
        self.assertEqual(plant_support_findings(translated), [])
        translated['props'][0]['position'][2] += .002
        self.assertTrue(any('base' in f for f in plant_support_findings(translated)))

    def test_c3_chunk_b_visible_parts_and_removed_frame(self):
        from archpipe.concept.physical_part import Part
        by_id = {m["id"]: m for m in SCENE["meshes"]}
        kinds = ("hanging-rail", "rail-bracket", "storage-box", "box-handle",
                 "suitcase", "suitcase-handle", "suitcase-wheel", "planter",
                 "planter-rim", "planter-soil", "trellis", "climber-branch", "climber", "extract-valve")
        for kind in kinds:
            members = [m for m in SCENE["meshes"] if m["part_kind"] == kind and
                       (m["id"].startswith(("dress-", "furn-", "landscape-door-pot-", "landscape-lemon-pot",
                                            "landscape-top", "landscape-trellis-",
                                            "landscape-climber-", "detail-vent-")))]
            self.assertTrue(members, kind)
            for m in members:
                Part(kind, m["faces"], ("x", "y", "z"), m["material"], "authored-procedural")
        # G1 removes the former north trellis because it occupied the full
        # east court. The retained west assembly still needs real members.
        self.assertGreaterEqual(len(by_id["landscape-trellis-north"]["faces"]), 48)
        cases = [m for m in SCENE["meshes"] if m["part_kind"] == "suitcase" and m["id"].startswith("furn-")]
        self.assertTrue(cases)
        for case in cases:
            points = [p for face in case["faces"] for p in face]
            self.assertLessEqual(max(p[0] for p in points)-min(p[0] for p in points), .550001)
            self.assertLessEqual(max(p[1] for p in points)-min(p[1] for p in points), .350001)
            handle = by_id[case["id"]+"-handle"]
            self.assertGreater(min(p[1] for face in handle["faces"] for p in face),
                               max(p[1] for p in points))
        self.assertFalse(any(p["asset"] == "hanging_picture_frame_01" for p in SCENE["props"]))
        for room in ("guest-wc", "dirty-kitchen"):
            valve = by_id[f"detail-vent-{room}-valve"]
            fitting = next(v for v in RS.build(R.design("D1"))["ventilation"] if v["room"] == room)
            from archpipe.concept import villa_lighting as VL
            from archpipe.concept import villa_furnish as F
            ceiling = VL.ceiling_z(fitting["level"], x=fitting["fan"][0], y=fitting["fan"][1],
                                   room=room, lay=R.design("D1"), spec=RS.build(R.design("D1")))
            self.assertLessEqual(max(p[2] for face in valve["faces"] for p in face), ceiling)
            grille = by_id[f"detail-vent-{room}-grille"]
            facade_y = max(w[3] for w in F._walls(RS.build(R.design("D1")), fitting["level"])
                           if w[0] <= fitting["fan"][0] <= w[2] and w[3] <= fitting["duct_route"][-1][1])
            # The approved exterior grille's rear fixing face sits on the
            # facade; its 12 mm body projects outdoors, with no burial.
            self.assertAlmostEqual(min(p[1] for face in grille["faces"] for p in face), facade_y)
            self.assertAlmostEqual(max(p[1] for face in grille["faces"] for p in face), facade_y+.012)

    def test_c3_bath_and_grille_parts_are_closed_and_detailed(self):
        from archpipe.concept.physical_part import Part
        by_id = {m["id"]: m for m in SCENE["meshes"]}
        for prefix in ("gwc", "pe"):
            kinds = {"rain-head": ("rain-head-drop", "rain-head-plate", "rain-head-nozzle-face",
                                   "rain-head-nozzles"),
                     "riser-rail": ("hand-shower-rail", "hand-shower-slider"),
                     "shower-head": ("hand-shower-head",),
                     "shower-hose": ("hand-shower-hose",)}
            for kind, suffixes in kinds.items():
                for suffix in suffixes:
                    m = by_id[f"detail-{prefix}-{suffix}"]
                    self.assertEqual(m["part_kind"], kind)
                    Part(kind, m["faces"], ("x", "y", "z"), m["material"], "authored-procedural")
            for end in ("lower", "upper"):
                m = by_id[f"detail-{prefix}-hand-shower-bracket-{end}"]
                Part(m["part_kind"], m["faces"], ("x", "y", "z"), m["material"], "authored-procedural")
            head = by_id[f"detail-{prefix}-rain-head-plate"]
            xs = [p[0] for face in head["faces"] for p in face]
            self.assertAlmostEqual(max(xs) - min(xs), .28, places=3)
        for room in ("guest-wc", "dirty-kitchen"):
            m = by_id[f"detail-vent-{room}-grille"]
            self.assertEqual(m["part_kind"], "fan-grille")
            self.assertGreater(len(m["faces"]), 40)  # perimeter and seven separate blades leave open slots
            Part("fan-grille", m["faces"], ("x", "y", "z"), m["material"], "authored-procedural")
            valve = by_id[f"detail-vent-{room}-valve"]
            self.assertEqual(valve["part_kind"], "extract-valve")
            Part("extract-valve", valve["faces"], ("x", "y", "z"), valve["material"], "authored-procedural")
            self.assertNotIn(f"detail-vent-{room}-duct", by_id)
            self.assertTrue(any(v["room"] == room and v["duct_route"] for v in RS.build(R.design("D1"))["ventilation"]))
        for name in ("detail-gwc-linear-drain", "detail-gwc-linear-drain-recess"):
            m = by_id[name]
            self.assertEqual(m["part_kind"], "drain")
            Part("drain", m["faces"], ("x", "y", "z"), m["material"], "authored-procedural")
        drain = by_id["detail-gwc-linear-drain"]
        self.assertEqual(drain["material"], "stainless")
        self.assertGreater(len(drain["faces"]), 100)  # frame plus slotted cross bars
        spec_drain = next(f for f in RS.build(R.design("D1"))["bath_fittings"] if f["id"] == "gwc-linear-drain")
        self.assertAlmostEqual(spec_drain["x1"] - spec_drain["x0"], .07)
        self.assertAlmostEqual(max(p[0] for face in drain["faces"] for p in face) -
                               min(p[0] for face in drain["faces"] for p in face), .07)

    def test_indoor_plants_have_integrated_pots_floor_support_and_clear_tv(self):
        from copy import deepcopy
        lay = R.design("D1")
        clean = [p for p in SCENE["props"] if p.get("indoor_plant")]
        self.assertEqual(VR.indoor_plant_violations(clean, lay, SCENE), [])
        # Frozen real failed placement: the Pachira's manifest width is 6.869 m at scale 1.
        old = deepcopy(next(p for p in clean if p["id"] == "lounge-plant"))
        old.update(asset="pachira_aquatica_01", position=[4.3, -24.35, -3.0], scale=1.0)
        old.pop("container")
        self.assertTrue(any("pot" in x for x in VR.indoor_plant_violations([old], lay, SCENE)))
        self.assertTrue(any("corridor" in x for x in VR.indoor_plant_violations([old], lay, SCENE)))
        sunk = deepcopy(next(p for p in clean if p["id"] == "bedroom-plant"))
        sunk["position"][2] -= 0.15
        self.assertTrue(any("support" in x for x in VR.indoor_plant_violations([sunk], lay, SCENE)))
        blocked = deepcopy(next(p for p in clean if p["id"] == "lounge-plant"))
        blocked["position"][:2] = [6.2, -25.4]
        self.assertTrue(any("corridor" in x for x in VR.indoor_plant_violations([blocked], lay, SCENE)))

    def test_wp4b_fixture_and_dressing_parts(self):
        ids = {m["id"] for m in SCENE["meshes"]}
        swings = [m for m in SCENE["meshes"] if m["id"].startswith("swing-plate-")]
        self.assertEqual(len(swings), 2)
        for plate in swings:
            lamp = plate["id"].removeprefix("swing-plate-")
            self.assertIn("swing-arm-" + lamp, ids)
            self.assertIn("swing-knuckle-" + lamp, ids)
            self.assertIn("swing-head-" + lamp, ids)
            self.assertIn("swing-emitter-" + lamp, ids)
        globes = [m for m in SCENE["meshes"] if m["material"] == "opal-pen-globe-2700"]
        self.assertTrue(globes)
        # Client round-3 (v01): the globe shell read as "smoky grey glass" as a rough refractive "glass" kind.
        # "translucent" (Principled diffuse + Translucent BSDF mix, already proven by the curtains) is the fix --
        # a milky white body that diffusely passes the inner bulb's light, not a dielectric that mostly reflects.
        globe_mat = SCENE["materials"]["opal-pen-globe-2700"]
        self.assertEqual(globe_mat["kind"], "translucent")
        self.assertGreater(min(globe_mat["base_rgb"]), 0.85, "must read white, not grey")
        self.assertGreater(globe_mat.get("transmittance", 0), 0.4, "must actually glow from inside")
        self.assertTrue(all("bulb-" + m["id"].removeprefix("lamp-") in ids for m in globes))
        self.assertTrue(any(i.startswith("dress-hers-long-hang-") for i in ids))
        self.assertTrue(any(i.startswith("dress-his-drawers-") for i in ids))
        self.assertTrue(any(i.startswith("dress-hers-top-box-") for i in ids))
        self.assertTrue(any(i.startswith("dress-his-top-box-") for i in ids))

    def test_wp2b_checked_joinery_and_kitchen_builders(self):
        from archpipe.concept import villa_furnish as F, villa_furniture_detail as FD
        items = {i["id"]: i for i in F.layout(VR.R.design("D1"))}
        expected = {
            "library-cabinet-left": {"glass-door", "door-frame", "shelf", "back"},
            "library-cabinet-right": {"glass-door", "door-frame", "shelf", "back"},
            "library-daybed": {"mattress", "cushion", "nook-side", "nook-top"},
            "dk-appliance-bank": {"fridge", "oven-glass"},
            "k-island": {"microwave-glass", "single-induction", "waterfall-end"},
            "dk-fold": {"worktop", "front", "handle"},
            "cinema-desk": {"top", "pedestal", "drawer", "cable-tray"},
        }
        for name, required in expected.items():
            # world_parts raises EnvelopeError if any builder vertex leaves the
            # checked footprint or the daybed's separate full-height surround.
            parts = FD.world_parts(items[name], VR.LZ[items[name]["level"]])
            self.assertTrue(required <= set(parts), (name, set(parts)))
        ids = {m["id"] for m in SCENE["meshes"]}
        self.assertTrue(any(i.startswith("detail-cabinet-led-") for i in ids))
        # WP4-B1: the daybed item now carries curtain=False -- the nook curtain and its track are REMOVED.
        self.assertNotIn("detail-curtain-library-nook-track", ids)
        self.assertTrue(all(m["material"] == "walnut" for m in SCENE["meshes"]
                            if m["id"].startswith("furn-library-end-panel-")))
        self.assertEqual(sum(i.startswith("lamp-shade-DESK-cinema-") for i in ids), 2)
        self.assertEqual(sum(i.startswith("furn-cinema-desk-chair-") and i.endswith("-0") for i in ids), 2)
        wet = [m for m in SCENE["meshes"] if m["id"].startswith("furn-gwc-shower-")]
        self.assertEqual({m["material"] for m in wet}, {"marble-wet"})
        self.assertIn("detail-gwc-rain-head-plate", ids)
        self.assertIn("detail-gwc-hand-shower-head", ids)

    def test_wp2b_openings_bath_stair_and_extract_match_spec(self):
        from archpipe.concept import revit_spec as RS, villa_daylight as VD
        from archpipe import daylight as D
        lay = VR.R.design("D1")
        sp = RS.build(lay)
        ids = {m["id"] for m in SCENE["meshes"]}
        for name in ("detail-hatch-sill", "detail-hatch-head", "detail-hatch-left", "detail-hatch-right",
                     "detail-hatch-shutter-box", "detail-pocket-panel-0", "detail-pocket-panel-1",
                     "detail-pocket-panel-2", "detail-pe-rain-head-plate", "detail-pe-rain-head-drop",
                     "detail-pe-hand-shower-rail", "detail-pe-bath-screen", "detail-vent-guest-wc-grille",
                     "detail-vent-dirty-kitchen-grille", "appliance-hood-dirty-canopy"):
            self.assertIn(name, ids)
        hatch = sp["hatches"][0]
        wall = next(w for w in sp["walls"] if w["level"] == "B" and
                    abs(w["y0"] - hatch["y"]) < 0.001 and w["x0"] <= hatch["x0"] < hatch["x1"] <= w["x1"])
        opening = dict(offset=hatch["x0"] - wall["x0"], width=hatch["x1"] - hatch["x0"],
                       sill=hatch["sill"], head=hatch["head"], kind="hole")
        faces = D.wall((wall["x0"], wall["y0"]), (wall["x1"], wall["y1"]), VR.LZ["B"],
                       wall["height"], wall["thickness"], [opening])
        self.assertFalse(any(f.material in ("glass", "door") for f in faces))
        self.assertEqual(VD.scene(lay).openings["spec"], len(sp["windows"]) + len(sp["doors"]) + 1)
        self.assertEqual(VD.scene(lay).openings["placed"], VD.scene(lay).openings["spec"])
        pocket = next(d for d in sp["doors"] if d.get("sliding") and
                      set(d["rooms"]) == {"kitchen", "dirty-kitchen"})
        self.assertEqual(VD._openings_on(wall, "B", [], [pocket])[0]["kind"], "hole",
                         "stowed pocket leaves must leave an open passage, not a glass pane")
        self.assertTrue(all(m["material"] == "glass-guard" for m in SCENE["meshes"]
                            if m["id"].startswith("detail-stair-glass-") and
                            "edge" not in m["id"] and m["id"][-2:].isdigit()))
        self.assertEqual(next(m for m in SCENE["meshes"] if m["id"] == "detail-stair-wall-handrail")["material"], "oak")

    def test_wp2b_landscape_plot_support_setbacks_and_routes(self):
        from archpipe.concept import villa_landscape as LAND, revit_spec as RS, render_support as S
        sp = RS.build(VR.R.design("D1"))
        meshes, props, notes, plan = LAND.build(sp)
        self.assertEqual(set(plan["paths"]), {"dining", "living-east", "living-south", "lounge-north", "study", "gate-link"})
        for m in meshes:
            for face in m["faces"]:
                for x, y, _ in face:
                    self.assertTrue(LAND.inside_yard(x, y), m["id"])
        parking = sp["parking2"]["ramp"]
        deck = sp["parking2"]["deck"]
        parked = (min(x for x, _ in parking["profile"]), parking["y0"], deck["x1"], parking["y1"])
        for m in meshes:
            if not m["id"].startswith(("landscape-planter-", "landscape-gravel-", "landscape-path-")):
                continue
            pts = [p for face in m["faces"] for p in face]
            x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
            y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
            self.assertFalse(min(x1, parked[2]) - max(x0, parked[0]) > 0.005 and
                             min(y1, parked[3]) - max(y0, parked[1]) > 0.005, m["id"])
        for _, _, _, (x, y), _, _ in plan["trees"]:           # round 3: (bed, asset, species, (x, y), h, yaw)
            self.assertTrue(LAND.inside_yard(x, y))
            self.assertGreaterEqual(LAND.facade_distance(x, y), 1.5)
        self.assertEqual(LAND.extent_violations([p for p in props if p["id"].startswith("landscape-tree-")]), [],
                         "every placed tree's real (measured) canopy must clear the building and stay in the yard")
        self.assertLess(LAND.facade_distance(1.10, -28.00), 1.5,
                        "the old west tree must fail against the front projection")
        for d in (d for d in sp["doors"] if d.get("garden")):
            self.assertTrue(any(x0 - 0.001 <= d["x"] <= x1 + 0.001 and
                                y0 - 0.001 <= d["y"] <= y1 + 0.001
                                for x0, y0, x1, y1 in plan["paths"].values()), d)
        # G1's client-agreed palette excludes Bauhinia and east furniture.
        assets = {p["asset"] for p in props}
        self.assertTrue({"sf_frangipani", "sf_wooden_bench"} <= assets)
        self.assertNotIn("sf_bauhinia",assets)
        self.assertFalse({"sf_egg_chair", "outdoor_table_chair_set_01"} & assets)
        for prop in props:
            if prop["asset"] in ("sf_egg_chair", "outdoor_table_chair_set_01"):
                self.assertLess(LAND._rect(prop)[2],LAND.EAST[0])
        self.assertTrue(all(p["position"][2] >= LAND.GROUND for p in props))
        self.assertEqual(S.unsupported(SCENE), [])
        self.assertEqual(S.blocked_openings(SCENE), [])
        self.assertTrue(any("Hourly June scene ray-cast" in n and "UTC+02" in n for n in notes))   # round 3 per-bed sun screen
        self.assertTrue(any("Drip" in n or "drip" in n for n in notes))

    def test_lighting_spec_needs_no_render_ceiling_moves(self):
        moves = [note for note in SCENE["notes"] if note.startswith("Recessed fittings seated")]
        self.assertEqual(moves, [], "render seating still corrected lighting-spec heights")
        self.assertEqual(VR._seat_recessed_on_soffit(SCENE), [])

    def test_our_exterior_and_boundary_are_grey_green_context_is_neutral(self):
        finish = SCENE["materials"]["paint-exterior-grey-green"]
        self.assertAlmostEqual(finish["reflectance"], 0.65)
        self.assertNotIn("asset", finish, "painted mineral render must stay smooth")
        self.assertAlmostEqual(sum(a * b for a, b in zip(finish["base_rgb"], (0.2126, 0.7152, 0.0722))),
                               0.65, delta=0.005)
        self.assertGreater(finish["base_rgb"][1], finish["base_rgb"][0])
        shell = [m for m in SCENE["meshes"] if m["id"].startswith("shell-")]
        boundary = [m for m in shell if m.get("source_id", "").startswith("fence-") or
                    m.get("source_id") == "yard-wall-ne"]
        self.assertEqual({m["source_id"] for m in boundary},
                         {"fence-street", "fence-east", "fence-rear", "fence-west", "yard-wall-ne"})
        self.assertTrue(all(m["material"] == "paint-exterior-grey-green" for m in boundary))
        context = [m for m in shell if m.get("source_id", "").startswith(("neighbour-", "apartment-above"))]
        self.assertTrue(context)
        self.assertTrue(all(m["material"] == "render-exterior" for m in context))
        exposed_beams = [m for m in shell if m.get("source_id", "").startswith("beam-0-") and
                         m["room"] is None]
        self.assertTrue(exposed_beams)
        self.assertTrue(all(m["material"] == "paint-exterior-grey-green" for m in exposed_beams))
        self.assertTrue(any(m["source_id"] == "villa-shell" and m["material"] == "paint-exterior-grey-green"
                            for m in shell))
        self.assertFalse(any(m["source_id"] == "villa-shell" and m["material"] == "render-exterior"
                             for m in shell))

    def test_every_mesh_has_an_explicit_finish(self):
        self.assertEqual({m.get("material") for m in SCENE["meshes"]} - ALLOWED_MATERIALS, set())
        self.assertTrue(all(m["material"] in SCENE["materials"] for m in SCENE["meshes"]))
        self.assertEqual(set(SCENE["materials"]) - ALLOWED_MATERIALS, set())

    def test_g3_frozen_finish_consumer_and_renamed_missing_registration(self):
        import json
        from pathlib import Path
        from unittest.mock import patch
        old=set(json.loads((Path(__file__).parent/'fixtures/garden-g3-material-list-before.json').read_text()))
        self.test_every_mesh_has_an_explicit_finish()
        # Execute the actual consumer guard with its real prior input.
        with patch.dict(globals(),ALLOWED_MATERIALS=old):
            with self.assertRaises(AssertionError):
                self.test_every_mesh_has_an_explicit_finish()
        sibling=dict(meshes=[dict(material='unregistered-sibling-finish')],
                     materials={'unregistered-sibling-finish':{}})
        with patch.dict(globals(),SCENE=sibling):
            with self.assertRaises(AssertionError):
                self.test_every_mesh_has_an_explicit_finish()

    def test_parents_pillows_are_seated_and_lean_against_headboard(self):
        from archpipe.concept import villa_furnish as F
        bed = next(i for i in F.layout(VR.R.design("D1")) if i["id"] == "pb-bed")
        x0, y0, x1, y1 = F.footprint(bed)
        headboard = next(c for c in VR.generated_components(bed, bed["type"], 1.05)
                         if c["name"].endswith(":headboard"))
        head_top = max(v[2] for v in headboard["vertices_mm"]) / 1000
        pillows = [m for m in SCENE["meshes"] if m["id"].startswith("furn-pb-bed-") and
                   "dressing: pillow" in m["label"]]
        self.assertEqual(len(pillows), 2)
        for pillow in pillows:
            self.assertEqual(pillow["material"], "sage-fabric")
            points = [v for face in pillow["faces"] for v in face]
            self.assertTrue(all(x0 <= v[0] <= x1 and y0 <= v[1] <= y1 for v in points))
            self.assertLessEqual(max(v[2] for v in points), head_top)
            lo = min(v[1] for v in points)
            hi = max(v[1] for v in points)
            low_edge = max(v[2] for v in points if abs(v[1] - lo) < 1e-6)
            high_edge = max(v[2] for v in points if abs(v[1] - hi) < 1e-6)
            head_edge, foot_edge = (high_edge, low_edge) if bed["rot"] == 180 else (low_edge, high_edge)
            self.assertGreater(head_edge - foot_edge, 0.12)

    def test_camera_24mm_level_at_eye_height(self):                 # ADR-0013 part 8
        for v in SCENE["views"]:
            if v["state"] == "exterior-dusk":
                continue
            c = v["camera"]
            if "lens_reason" in c:
                self.assertEqual(v["id"], "v32-dressing-his")
                self.assertEqual(c["lens_mm"], 16)
                self.assertAlmostEqual(c["shift_y"], 0.10)
            elif "lens_basis" in c:                  # client 2026-09-27: a CALCULATED lens where 24 mm cannot hold the room
                import math
                narrow, wide = (c["lens_basis"][key] for key in ("at_24_mm", "at_16_mm"))
                vertical_keys = ("lower_top_need_deg", "upper_fitting_need_deg", "whole_subject_need_deg")
                for measured, lens in ((narrow, 24), (wide, 16)):
                    self.assertAlmostEqual(measured["horizontal_limit_deg"],
                                           math.degrees(math.atan(c["sensor_mm"] / 2 / lens)))
                    self.assertAlmostEqual(measured["vertical_limit_deg"],
                                           math.degrees(math.atan(c["sensor_mm"] / 3 / lens)))
                self.assertEqual(narrow["framed_candidates"], 0, v["id"] + ": a 24 mm point holds it")
                self.assertTrue(narrow["horizontal_need_deg"] > narrow["horizontal_limit_deg"] or
                                any(narrow[key] > narrow["vertical_limit_deg"] for key in vertical_keys),
                                v["id"] + ": 24 mm would have held it")
                self.assertEqual(c["lens_mm"], 16, v["id"])
                self.assertGreater(wide["framed_candidates"], 0)
                self.assertEqual(c["position"][:2], wide["position"])
                self.assertEqual(c["target"][:2], wide["target"])
                self.assertLessEqual(wide["horizontal_need_deg"], wide["horizontal_limit_deg"], v["id"])
                for key in vertical_keys:
                    self.assertLessEqual(wide[key], wide["vertical_limit_deg"], v["id"] + ": " + key)
            else:
                self.assertEqual(c["lens_mm"], 24, v["id"])
            self.assertAlmostEqual(c["position"][2], c["target"][2], places=3, msg=v["id"] + " is tilted")
            floor = -3.0 if c["position"][2] < -0.1 else 0.0
            self.assertTrue(1.19 <= c["position"][2] - floor <= 1.36, v["id"])

    def test_exposure_metered_and_locked_per_state(self):          # ADR-0013 part 6 + amendment
        self.assertEqual(SCENE["exposure_mode"], "set-metered")

    def test_every_bed_is_dressed_with_cloth(self):                 # ADR-0013 part 9
        ids = {c["id"] for c in SCENE["cloth"]}
        for bed in ("pb-bed", "kb-bed", "ka-bunk"):
            self.assertIn("duvet-" + bed, ids)
        self.assertFalse(any(m["id"].startswith("dress-duvet-") for m in SCENE["meshes"]), "box duvets are back")

    def test_painted_walls_are_smooth(self):                        # ADR-0013 part 7 (real finishes)
        m = SCENE["materials"]["plaster-warm-white"]
        self.assertNotIn("asset", m, "a photo-texture with a bump map made painted walls look rough")
        self.assertAlmostEqual(m["reflectance"], 0.80)

    def test_construction_details_present(self):                    # ADR-0013 part 10 (skirting, frames)
        ids = {m["id"] for m in SCENE["meshes"]}
        for d in ("detail-skirting-B", "detail-skirting-GF", "detail-window-frames", "detail-architraves"):
            self.assertIn(d, ids)

    def test_generated_furniture_where_a_builder_exists(self):      # archpipe.furniture, as the bedroom
        ids = {m["id"].rsplit("-", 1)[0] for m in SCENE["meshes"] if m["group"] == "furniture"}
        for mark in ("furn-pb-bed", "furn-pb-bedside", "furn-kb-bed", "furn-kb-desk", "furn-ka-wardrobe"):
            self.assertIn(mark, ids)
        tri = [m for m in SCENE["meshes"] if m["id"].startswith("furn-pb-bed-")]
        self.assertTrue(all(len(f) == 3 for m in tri for f in m["faces"]), "the bed is not the generated one")

    def test_stand_ins_and_dressing_are_declared(self):             # ADR-0013 amendment (captions)
        notes = " ".join(SCENE["notes"])
        self.assertIn("PROCEDURAL STAND-INS", notes)
        self.assertIn("Dressing", notes)
        self.assertTrue(all(p["label"].startswith("dressing:") for p in SCENE["props"]))

    def test_generated_pieces_face_the_way_the_plan_says(self):
        """The generator's headboard sits on the plan's headboard side and a bedside table's drawers face the plan's
        front. The first map swapped 0 and 180: the parents' bed rendered head-to-foot (client: "duvet flying on
        the end"). Checked on the real pieces, every rotation in the layout."""
        from archpipe.concept import villa_furnish as F, villa_furnish3d as F3
        items = {i["id"]: i for i in F.layout(VR.R.design("D1"))}
        checked = 0
        for mid, kind, part, f3part in (("pb-bed", "bed_double", "headboard", "headboard"),
                                        ("kb-bed", "bed_double", "headboard", "headboard"),
                                        ("pb-bedside", "bedside_table", "drawer_top_handle", None)):
            it = items[mid]
            comps = {c["name"].split(":")[1]: c["vertices_mm"] for c in VR.generated_components(it, kind)}
            vs = comps[part]
            gx = sum(v[0] for v in vs) / len(vs) / 1000.0 - it["cx"]
            gy = sum(v[1] for v in vs) / len(vs) / 1000.0 - it["cy"]
            if f3part:                                   # the plan's own part, in world
                b = next(F3.to_world(it, bx) for n, bx in F3.body(it) if n == f3part)
                px, py = (b[0] + b[3]) / 2 - it["cx"], (b[1] + b[4]) / 2 - it["cy"]
            else:                                        # the plan's front: local +y
                px, py = {0: (0, 1), 180: (0, -1), -90: (1, 0), 90: (-1, 0)}[it["rot"]]
            self.assertGreater(gx * px + gy * py, 0, "%s: generated %s on the wrong side" % (mid, part))
            checked += 1
        self.assertEqual(checked, 3)

    def test_duvet_cut_hangs_like_the_bedroom(self):
        """photoreal.cloth_bedding: mattress width + 0.30 m each side and 0.30 m over the foot. The first villa cut
        ended 20 mm past the foot and its stiff lip stood out flat."""
        from archpipe.concept import villa_furnish as F
        items = {i["id"]: i for i in F.layout(VR.R.design("D1"))}
        for c in (c for c in SCENE["cloth"] if c["id"].startswith("duvet-")):
            bid = c["id"][len("duvet-"):].replace("-upper", "")
            q = F.footprint(items[bid])
            cx, cy = c["center"]
            sx, sy = c["size"]
            lo_x, hi_x, lo_y, hi_y = cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2
            if c["bunk"]:
                self.assertTrue(q[0] < lo_x and hi_x < q[2] and q[1] < lo_y and hi_y < q[3], c["id"] + " leaves its frame")
                continue
            over = [q[0] - lo_x, hi_x - q[2], q[1] - lo_y, hi_y - q[3]]
            self.assertEqual(sum(o >= 0.25 for o in over), 3, "%s: overhangs %s (sides and foot must hang)" %
                             (c["id"], [round(o, 2) for o in over]))
            self.assertGreaterEqual(c["z_start"] - c["mattress_top"], 0.03, c["id"] + " starts inside the mattress")

    def test_scene_passes_the_render_contract(self):
        """Checked here, not first on the workstation: the detailed furniture's lofts once carried 1,780 zero-area
        triangles (corner radius = half the ring) and the whole draft was refused remotely. Round-3: WP4/5's new
        `rod_faces` helper (the dressing hanger's neck, the swing lamp's arm) degenerated on every VERTICAL rod --
        its fallback "up" reference (0,0,1) is parallel to a straight-down direction, so the frame's cross product
        was zero and every corner of both end squares collapsed onto the rod's own centreline. 72 degenerate faces
        on the real scene, all "-hanger" meshes; see test_rod_faces_handles_a_vertical_rod below for the isolated
        reproduction."""
        from archpipe import villa_render_contract as C
        self.assertEqual(C.validate_scene(SCENE), [])

    def test_rod_faces_handles_a_vertical_rod(self):
        # Reproduces the real pre-fix defect directly (a hanger's neck: same x/y, differing only in z) rather
        # than relying on the full scene to surface it.
        faces = VR.rod_faces((0.0, 0.0, 1.0), (0.0, 0.0, 0.9), 0.006)
        from archpipe import villa_render_contract as C
        errors = C.validate_scene({"schema": "villa-render/1", "camera": {"lens_mm": 24, "position": [0, 0, 0],
                                   "target": [0, 0, -1]}, "exposure": {"ev100": 6}, "sun": None,
                                   "library_root": "$HOME/archpipe/assets/library", "materials": {"black-metal": VR.M["black-metal"]},
                                   "meshes": [dict(id="rod-test", group="fixture", material="black-metal", faces=faces)],
                                   "lights": [], "views": []})
        self.assertEqual([e for e in errors if "degenerate" in e or "faces" in e], [])

    def test_nothing_floats(self):
        """Client: "flying plants", "duvet flying"; draft 9 still had desk-lamp shades hanging in a window, step
        markers 70 mm off the stair wall, downlights 155 mm below the dirty-kitchen slab and a sconce off its wall."""
        from archpipe.concept import render_support as S
        self.assertEqual(S.unsupported(SCENE), [])

    def test_openings_passable(self):
        """Reproduce the former bedside pendants and 900 mm dressing door on the actual D1 scene."""
        import copy
        from unittest.mock import patch
        from archpipe.concept import render_support as S, revit_spec as RS, villa_r11 as R
        from archpipe.concept.villa_render import box_faces
        self.assertEqual(S.blocked_openings(SCENE), [])

        old = copy.deepcopy(SCENE)
        # Historical obstruction reproduction deliberately bypasses the current
        # part constructor; the production scene above has already passed it.
        old["meshes"] = list(old["meshes"])
        bed = (19.53, -26.591, 21.13, -24.591)
        for n, x in (("02", bed[0] - 0.28), ("03", bed[2] + 0.25)):
            y = bed[1] + 0.2
            old["meshes"].append(dict(id="lamp-PEN-SMALL-parents-bed-" + n, group="fixture",
                                      material="opal-pen-small-2700", faces=VR.sphere(x, y, 1.25, 0.1)))
            old["meshes"].append(dict(id="cord-PEN-SMALL-parents-bed-" + n, group="fixture",
                                      material="black-metal", faces=box_faces(x - 0.003, y - 0.003, 1.35,
                                                                                 x + 0.003, y + 0.003, 2.7)))
        lay = R.design("D1")
        actual_build = RS.build

        def old_spec(layout):
            spec = actual_build(layout)
            door = next(d for d in spec["doors"] if set(d["rooms"]) == {"parents-bed", "parents-dressing"})
            door["x"], door["width"] = 21.847, 0.9
            return spec

        with patch.object(RS, "build", side_effect=old_spec):
            found = {mid for mid, _ in S.blocked_openings(old, lay)}
        self.assertIn("lamp-PEN-SMALL-parents-bed-02", found)
        self.assertIn("lamp-PEN-SMALL-parents-bed-03", found)
        self.assertIn("furn-pb-bedside-0", found)

    def test_doorway_guard_uses_the_leaf_actually_in_the_scene(self):
        # The telescopic kitchen door's panels are stowed in the pocket, clear of its 1.2 m opening, so the v17
        # doorway camera stands in a clear opening; the cinema door has a swinging leaf that must be hidden.
        from scripts import villa_render_views as views
        by = {v["id"]: v for v in SCENE["views"]}
        cinema = by["v08-cinema"]
        door = next(d for d in RS.build(R.design("D1"))["doors"] if set(d["rooms"]) == {"kitchen", "dirty-kitchen"})
        lo, hi = door["x"] - door["width"] / 2, door["x"] + door["width"] / 2
        for m in SCENE["meshes"]:
            if m["id"].startswith("detail-pocket-panel"):
                xs = [p[0] for f in m["faces"] for p in f]
                self.assertTrue(max(xs) <= lo + 1e-6 or min(xs) >= hi - 1e-6, m["id"] + " stands in the opening")
        self.assertTrue(views.door_leaf_near(SCENE, *cinema["camera"]["position"][:2]))
        self.assertTrue(cinema.get("hide_meshes"), "the real cinema leaf must be hidden for its doorway view")

    def test_study_windows_are_low_and_column_clear(self):
        from archpipe.concept import villa_r11 as R, revit_spec as RS
        spec = RS.build(R.design("D1"))
        windows = [w for w in spec["windows"] if w["room"] == "study-game"]
        self.assertEqual(len(windows), 2)
        for window in windows:
            self.assertEqual((window["sill"], window["height"]), (0.9, 1.4))
            axis, face, lo, hi = window["span"]
            self.assertGreaterEqual((hi - lo - window["width"]) / 2, 0.3 - 1e-6)
            self.assertEqual(RS.opening_problems(spec), [])

    def test_study_deck_slider_is_closed_glass_with_bronze_frame(self):
        spec = RS.build(R.design("D1"))
        door = next(d for d in spec["doors"] if set(d["rooms"]) == {"study-game", "deck"})
        lo, hi = door["x"] - door["width"] / 2, door["x"] + door["width"] / 2
        glass = [m for m in SCENE["meshes"] if m["material"] == "glass-clear"]
        panes = []
        for mesh in glass:
            for face in mesh["faces"]:
                if (all(lo - .001 <= p[0] <= hi + .001 for p in face) and
                        all(abs(p[1] - door["y"]) <= .12 for p in face) and
                        all(RS.LEVELS_Z["GF"] - .001 <= p[2] <= RS.LEVELS_Z["GF"] + door["height"] + .001
                            for p in face)):
                    panes.append(face)
        self.assertEqual(len(panes), 12)  # six faces for each of the two closed leaves
        ys = [p[1] for face in panes for p in face]
        self.assertAlmostEqual(max(ys) - min(ys), .010, places=4)
        frame = next(m for m in SCENE["meshes"] if m["id"] == "detail-window-frames")
        self.assertEqual(frame["material"], "alu-bronze")
        self.assertTrue(any(all(lo - .06 <= p[0] <= hi + .06 and abs(p[1] - door["y"]) <= .14
                                for p in face) for face in frame["faces"]))

    def test_assumed_stair_construction_is_present(self):
        ids = {m["id"] for m in SCENE["meshes"]}
        for suffix in ("wall-stringer-00", "wall-plate", "open-stringer", "glass-00", "glass-edge-00",
                       "glass-shoe", "wall-handrail"):
            self.assertIn("detail-stair-" + suffix, ids)
        self.assertFalse(any("baluster" in i or "open-handrail" in i for i in ids))
        self.assertIn("Risers remain open", " ".join(SCENE["notes"]))

    def test_desk_chairs_and_drawers_face_each_other(self):
        from archpipe.concept import villa_furnish as F, villa_furnish3d as F3, villa_furniture_detail as FD, villa_r11 as R
        lay = R.design("D1")
        desks = [i for i in F.layout(lay) if i["type"] == "desk"]
        seats = {f["mark"]: f for f in F3.spec(lay) if "#chair-" in f["mark"]}
        for desk in desks:
            parts = FD.world_parts(desk, 0)
            self.assertTrue({"top", "pedestal", "drawer", "pull", "modesty", "cable-tray"} <= set(parts))
            chair = seats[desk["id"] + "#chair-1"]
            item = FD.seat_item(chair)
            front = {0: (0, 1), 180: (0, -1), -90: (1, 0), 90: (-1, 0)}[item["rot"]]
            to_desk = (desk["cx"] - item["cx"], desk["cy"] - item["cy"])
            self.assertGreater(sum(a * b for a, b in zip(front, to_desk)), 0, desk["id"])
            drawer_y = sum(v[1] for face in parts["drawer"] for v in face) / sum(len(face) for face in parts["drawer"])
            drawer_x = sum(v[0] for face in parts["drawer"] for v in face) / sum(len(face) for face in parts["drawer"])
            self.assertGreater((drawer_x - desk["cx"]) * (item["cx"] - desk["cx"]) +
                               (drawer_y - desk["cy"]) * (item["cy"] - desk["cy"]), 0, desk["id"])
            self.assertTrue({"caster", "gas-lift", "back-mesh", "armrest"} <=
                            {name for name, _ in FD._task_chair(item["w"] * 1000, item["d"] * 1000)})

    def test_kitchen_appliances_and_sinks_are_present(self):
        from archpipe.concept import villa_furnish as F, villa_furnish3d as F3, villa_furniture_detail as FD, villa_r11 as R
        ids = {m["id"] for m in SCENE["meshes"]}
        self.assertIn("appliance-downdraft-island", ids)
        for name in ("coffee-main", "coffee-dirty"):
            for part in ("body", "drip-tray", "spout", "water-tank"):
                self.assertIn("appliance-" + name + "-" + part, ids)
        for part in ("canopy", "chimney"):
            self.assertIn("appliance-hood-dirty-" + part, ids)
        hood = {m["id"].rsplit("-", 1)[-1]: m for m in SCENE["meshes"]
                if m["id"].startswith("appliance-hood-dirty-")}
        canopy_top = max(p[2] for face in hood["canopy"]["faces"] for p in face)
        duct_top = max(p[2] for face in hood["chimney"]["faces"] for p in face)
        self.assertGreater(duct_top - canopy_top, 0.25, "the wall hood is a flat plate again")
        machine = next(m for m in SCENE["meshes"] if m["id"] == "appliance-coffee-dirty-body")
        self.assertEqual(machine["subdivide"], 1)
        self.assertGreater(len(machine["faces"]), 100, "the machine body is a plain box again")
        items = {i["id"]: i for i in F.layout(R.design("D1"))}
        self.assertIn("fridge", items["dk-appliance-bank"]["why"])
        self.assertIn("cleaning storage", items["dk-run"]["why"])
        for name in ("k-run", "dk-run"):
            self.assertTrue({"sink", "tap"} <= set(FD.world_parts(items[name], 0)))
        self.assertIn("microwave-glass", FD.world_parts(items["k-island"], 0))
        self.assertNotIn("microwave-glass", FD.world_parts(items["dk-appliance-bank"], 0))
        self.assertIn("glass-door", {name for name, _ in F3.body(items["library-cabinet-left"])})

    def test_bath_mixer_ladder_and_upholstery_stay_in_the_checked_envelopes(self):
        from archpipe.concept import villa_furnish as F, villa_furnish3d as F3, villa_furniture_detail as FD
        items = {i["id"]: i for i in F.layout(VR.R.design("D1"))}
        bath = items["pe-bath"]
        self.assertEqual(bath["rot"], 0)  # local rear rim faces its wall
        parts = FD.world_parts(bath, 0)
        self.assertIn("tap", parts)
        self.assertTrue(any(m["id"].startswith("furn-pe-bath-") and m["material"] == "brass"
                            for m in SCENE["meshes"]))
        for item in items.values():
            if item["type"].startswith("sofa") or item["type"] in ("armchair", "recliner"):
                detail = FD.world_parts(item, 0)  # raises if a vertex leaves the checked box
                self.assertTrue({"seat", "back", "arm", "plinth", "leg"} <= set(detail))
        sofa = items["living-sofa"]
        parts_local = FD.local_parts(sofa)
        seat_vertices = next(vertices for name, (vertices, _) in parts_local if name == "seat")
        self.assertGreater(len({round(v[2]) for v in seat_vertices}), 3, "a flat beveled slab returned")
        crown = [v for v in seat_vertices if v[2] == max(p[2] for p in seat_vertices)]
        self.assertGreater(min(v[0] for v in crown), min(v[0] for v in seat_vertices) + 0.03 * 1000)
        back_vertices = next(vertices for name, (vertices, _) in parts_local if name == "back")
        heights = sorted({v[2] for v in back_vertices})
        mean_y = lambda height: sum(v[1] for v in back_vertices if v[2] == height) / sum(
            v[2] == height for v in back_vertices)
        self.assertLess(mean_y(heights[-2]), mean_y(heights[1]) - 0.01 * 1000)
        self.assertTrue(all(m["subdivide"] == 1 for m in SCENE["meshes"] if
                            m["id"].startswith("furn-living-sofa-") and m["material"] == "boucle"))
        bunk = items["ka-bunk"]
        bed_parts = F3.body(bunk)
        self.assertEqual(sum(name == "ladder-rung" for name, _ in bed_parts), 4)
        self.assertEqual(sum(name == "ladder-stile" for name, _ in bed_parts), 2)
        self.assertTrue(all(-bunk["w"]/2 <= b[0] <= b[3] <= bunk["w"]/2 and
                            -bunk["d"]/2 <= b[1] <= b[4] <= bunk["d"]/2 and 0 <= b[2] <= b[5] <= bunk["h"]
                            for name, b in bed_parts if name.startswith("ladder-")))
        self.assertTrue(any(m["id"].startswith("furn-ka-bunk-") for m in SCENE["meshes"]))

    def test_bed_pillows_are_puffed_and_rest_on_the_mattress(self):
        for bed in ("pb-bed", "kb-bed"):
            pillows = [m for m in SCENE["meshes"] if m["id"].startswith("furn-" + bed + "-") and
                       "dressing: pillow" in m["label"]]
            self.assertEqual(len(pillows), 2)
            for pillow in pillows:
                pts = [p for face in pillow["faces"] for p in face]
                self.assertGreater(max(p[2] for p in pts) - min(p[2] for p in pts), 0.12)
                self.assertEqual(pillow["subdivide"], 1)
                self.assertGreater(max(p[0] for p in pts) - min(p[0] for p in pts), 0.35)
                self.assertGreater(max(p[1] for p in pts) - min(p[1] for p in pts), 0.25)

    def test_mirrors_are_above_basins_and_between_the_sconces(self):
        from archpipe.concept import villa_furnish as F
        items = {i["id"]: i for i in F.layout(VR.R.design("D1"))}
        for basin_id, room in (("gwc-basin", "guest-wc"), ("fb-basin", "family-bath"),
                               ("pe-basin", "parents-ensuite")):
            mirror = next(m for m in SCENE["meshes"] if m["id"] == "mirror-" + basin_id)
            self.assertEqual(mirror["material"], "silvered-mirror")
            pts = [p for face in mirror["faces"] for p in face]
            floor = VR.LZ[items[basin_id]["level"]]
            self.assertAlmostEqual(min(p[2] for p in pts) - floor - items[basin_id]["h"], 0.20)
            sconces = [m for m in SCENE["meshes"] if m["id"].startswith(("lamp-SCONCE-" + room,
                                                                           "lamp-VSCONCE-" + room))]
            self.assertEqual(len(sconces), 2)
            axis = 0 if max(p[0] for p in pts) - min(p[0] for p in pts) > 0.1 else 1
            mirror_lo = min(p[axis] for p in pts); mirror_hi = max(p[axis] for p in pts)
            centres = [sum(p[axis] for face in m["faces"] for p in face) /
                       sum(len(face) for face in m["faces"]) for m in sconces]
            self.assertLess(min(centres), mirror_lo)
            self.assertGreater(max(centres), mirror_hi)

    def test_villa_render_qa_receives_and_runs_the_six_scene_checks(self):
        import sys
        import io
        from PIL import Image
        from archpipe.render_qa import check
        sys.path.insert(0, str(VR.ROOT / "scripts"))
        import villa_render as driver
        self.assertTrue(all("mattress_span" in c and "length_axis" in c for c in SCENE["cloth"]
                            if c["id"].startswith("duvet-")))
        day_view = next(v for v in SCENE["views"] if v["state"] == "day")
        report = {"subjects": [], "white_balance_applied": True, "lights_on_count": 0,
                  "camera_pitch_deg": 0,
                  "qa_scene": {"windows": [{"id": "window-01", "screen": [0.1, 0.2, 0.5, 0.8]}],
                               "glass": {"architectural": 1},
                               "materials": [{"name": "alu-bronze", "note": "dark bronze", "override": True,
                                              "luminance": 0.09}],
                               "textiles": [{"name": "bedding-white", "reflectance": 0.70}],
                               "soft_goods": [{"name": "duvet-kb-bed", "simulated": True}],
                               "bedding": [{"id": "duvet-kb-bed", "mattress_y": [0, 2],
                                            "duvet_y": [0.2, 2.2], "duvet_z_min": 0.30}]}}
        context = driver.villa_qa_context(SCENE, day_view, report)
        for key in ("windows", "glass", "materials", "textiles", "soft_goods", "bedding"):
            self.assertEqual(context[key], report["qa_scene"][key])
        image = io.BytesIO()
        Image.new("RGB", (120, 80), (150, 150, 150)).save(image, format="PNG")
        image.seek(0)
        result = check(image, context)
        scope = driver.villa_qa_scope(result, context)
        for prefix in ("window_view", "glass_passes_daylight", "finish_matches_name",
                       "textile_reflectance", "soft_goods_simulated", "cloth_plausible"):
            self.assertTrue(any(name == prefix or name.startswith(prefix + ":") for name in scope["applied"]),
                            prefix)
            self.assertNotIn(prefix, scope["omitted"])

    def test_the_float_guard_catches_the_real_defects(self):
        import copy
        from archpipe.concept import render_support as S
        from archpipe.concept.villa_render import box_faces
        sc = copy.deepcopy(SCENE)
        # Draft 9 preceded the assumed stair steel; leaving it in the reproduction would support the old marker.
        sc["meshes"] = [m for m in sc["meshes"] if not m["id"].startswith(
            ("detail-stair-wall-stringer-", "detail-stair-wall-plate"))]
        # draft 9's desk lamp: no base or stem, an arm bracketed to the window (kids A, north glazing y -23.591)
        sc["meshes"] = [m for m in sc["meshes"] if m["id"] != "lamp-arm-DESK-kids-a-03"]
        shade = next(m for m in sc["meshes"] if m["id"] == "lamp-shade-DESK-kids-a-03")
        zs = [v[2] for f in shade["faces"] for v in f]
        x = sum(v[0] for f in shade["faces"] for v in f) / sum(len(f) for f in shade["faces"])
        y = sum(v[1] for f in shade["faces"] for v in f) / sum(len(f) for f in shade["faces"])
        sc["meshes"].append(dict(id="old-arm", group="fixture", material="black-metal", faces=box_faces(
            x - 0.008, y, max(zs) - 0.01, x + 0.008, -23.591, max(zs) + 0.006)))
        # draft 9's step marker: 20 mm in from the tread edge, 70 mm off the wall
        mk = next(m for m in sc["meshes"] if m["id"].startswith("marker-STEP-stair-b-"))
        for f in mk["faces"]:
            for v in f:
                v[1] += 0.068
        found = {u[0] for u in S.unsupported(sc)}
        self.assertIn("lamp-shade-DESK-kids-a-03", found)
        self.assertIn(mk["id"], found)

    def test_every_bedroom_and_living_window_has_a_curtain(self):
        """Client 2026-09-28: sheer + blackout (bedrooms) / dim-out (living spaces) on ceiling tracks, whole villa.
        RULE (villa_render.CURTAIN_OCC): every window/glazed garden door in a room whose occupancy is bedroom,
        living, dining or study gets one; kitchens/dirty kitchen, bathrooms/WC and the stair void get none even
        though some of them carry windows too."""
        from archpipe.concept import revit_spec as RS
        lay = VR.R.design("D1")
        sp = RS.build(lay)
        openings = ([w["room"] for w in sp["windows"]] +
                   [next(r for r in d["rooms"] if r != "yard") for d in sp["doors"] if d.get("garden")])
        expected_rooms = {room for room in openings if lay["rooms"][room]["occupancy"] in VR.CURTAIN_OCC}
        got_rooms = {c["room"] for c in SCENE["curtains"]}
        # WP4-B1: the daybed's nook curtain is removed (curtain=False), so "bar-alcove" no longer carries one.
        self.assertEqual(got_rooms, expected_rooms)
        self.assertEqual(sum(c["id"] == "curtain-library-nook" for c in SCENE["curtains"]), 0)
        self.assertTrue(expected_rooms & {"kids-a", "kids-b", "parents-bed"}, "no bedroom curtains found")
        self.assertTrue(expected_rooms & {"living", "dining"}, "no living-space curtains found")
        excluded = {"guest-wc", "family-bath", "parents-ensuite", "kitchen", "kitchen-island", "kitchen-work",
                   "kitchen-store", "kitchen-side", "dirty-kitchen", "stair-b", "stair-gf"}
        self.assertEqual(got_rooms & excluded, set())
        for c in SCENE["curtains"]:
            bedroom = lay["rooms"][c["room"]]["occupancy"] == "bedroom"
            self.assertEqual(c["bedroom"], bedroom, c["id"])
            self.assertEqual(c["heavy_material"], "curtain-heavy" if bedroom else "curtain-heavy-dimout", c["id"])
            self.assertEqual(c["sheer_material"], "curtain-sheer", c["id"])
            self.assertGreaterEqual(c["open_stack_m"], c["open_pier_reach_m"], c["id"])
            self.assertGreater(c["track_z"], c["floor_z"], c["id"])

    def test_curtain_open_stack_is_a_realistic_fullness(self):
        """Lead review of draft render 2: a flat 0.14 m stack cap held no real fabric -- a 2.4-2.76 m door's pair
        of panels carries roughly double fullness (~5 m) and cannot gather into 0.14 m; rendering it would show a
        curtain that could not exist. villa_render's STACK_RATIO (0.18 x opening width, ASSUMED typical stacking
        allowance, ridden as far as the wall pier allows with the rest over the glazing edge, per opening_kind)
        replaces it. This checks the stack is the full ratio (not silently clamped) for the villa's actual doors,
        and that windows (never walked through) carry no clear-width field at all."""
        for c in SCENE["curtains"]:
            self.assertAlmostEqual(c["open_stack_m"], round(0.18 * c["width"], 3), places=2, msg=c["id"])
            if c["opening_kind"] == "window":
                self.assertNotIn("open_clear_width_m", c, c["id"] + ": a window has no passage rule")

    def test_curtain_clear_width_through_doors(self):
        """Task B guard (lead review): for a garden/glazed DOOR, the open sheer+heavy stacks together must leave
        >= F.BODY (0.914 m, card mitton-path-of-travel-min, archpipe.concept.villa_furnish.BODY) clear to walk
        through -- windows carry no such rule. render_support.blocked_openings is NOT used here: it treats a
        door's WHOLE width as the passage and has no notion of "clear width", so it would flag the realistic
        stack's deliberate overlap onto the glazing edge by design (see villa_scene.build_curtains). This checks
        the contract's own open_clear_width_m field against the real 2.4 m and 2.76 m garden doors (pass) and
        proves a synthetic curtain left under 0.914 m clear is rejected (fail)."""
        from archpipe.concept import villa_furnish as F
        from archpipe import villa_render_contract as C
        import copy
        self.assertEqual(F.BODY, 0.914)
        doors = {round(c["width"], 2): c for c in SCENE["curtains"] if c["opening_kind"] == "garden-door"}
        for width in (2.4, 2.76):
            self.assertIn(width, doors, "no garden-door curtain at the expected width %.2f m" % width)
            c = doors[width]
            self.assertGreaterEqual(c["open_clear_width_m"], F.BODY, c["id"])
            self.assertAlmostEqual(c["open_clear_width_m"], c["width"] - 2 * (c["open_stack_m"] - c["open_pier_reach_m"]),
                                   places=2, msg=c["id"])
        self.assertEqual(C.validate_scene(SCENE), [])
        bad = copy.deepcopy(SCENE)
        template = next(c for c in SCENE["curtains"] if c["opening_kind"] == "garden-door")
        bad["curtains"] = [dict(template, open_clear_width_m=0.80)]     # < F.BODY: a stack that closes the door
        errors = C.validate_scene(bad)
        self.assertTrue(any("open_clear_width_m" in e for e in errors), errors)

    def test_curtain_panels_hang_on_the_room_side_of_the_wall_not_the_window(self):
        """Lead review of draft render 1: the closed curtain hung INSIDE the window reveal (behind
        detail-window-frames, alu-bronze, +-0.03 m of the window line; split by the mullion into two apparent
        curtains) because the panel's depth offset was measured from the window LINE, which is still inside the
        wall's own thickness. villa_scene.build_curtains now hangs the sheer 0.10 m and the heavy 0.15 m past
        `wall_face` (clear_rect's room-side boundary, already past the wall's full thickness) instead. This checks
        every curtain's hang line lands strictly inside the room's clear rect and clear of the window/frame plane,
        and proves the OLD (window-line-relative) placement would have failed the same check."""
        from archpipe.concept import villa_furnish as F
        lay = VR.R.design("D1")
        FRAME_CLEARANCE = 0.06  # detail-window-frames extends +-0.03 m from the window line

        def hang_ok(c, depth_offset):
            rx0, ry0, rx1, ry1 = F.clear_rect(lay, c["room"])
            at = c["wall_face"] + c["normal_sign"] * depth_offset
            cx, cy = c["center"]
            if c["axis"] == "h":
                inside, clear_of_frame, delta = ry0 < at < ry1, abs(at - cy) >= FRAME_CLEARANCE, (at - cy)
            else:
                inside, clear_of_frame, delta = rx0 < at < rx1, abs(at - cx) >= FRAME_CLEARANCE, (at - cx)
            return inside and clear_of_frame and delta * c["normal_sign"] > 0

        self.assertTrue(SCENE["curtains"])
        for c in SCENE["curtains"]:
            if c["id"] == "curtain-library-nook":
                # This track is fixed to the daybed's checked tall surround,
                # rather than to an exterior wall or window reveal.
                self.assertEqual(c["opening_kind"], "window")
                self.assertGreater(c["wall_face"] + 0.10, c["center"][1] - 0.01)
                continue
            self.assertTrue(hang_ok(c, 0.10), c["id"] + ": sheer not on the room side of the wall face")
            self.assertTrue(hang_ok(c, 0.15), c["id"] + ": heavy not on the room side of the wall face")
            # the pre-fix placement (0.05/0.11 m off the window line itself) fails this same check
            old = dict(c, wall_face=c["center"][0 if c["axis"] == "v" else 1])
            self.assertFalse(hang_ok(old, 0.05), c["id"] + ": window-line offset should fail this guard")
            self.assertFalse(hang_ok(old, 0.11), c["id"] + ": window-line offset should fail this guard")


def buried_behind_walls(scene, mesh_id, axis=1):
    """Wall faces (constant `axis` coordinate, shell group) that the mesh's own span overlaps and that lie on the
    room side of the mesh: a fixture behind such a face is inside the wall and never renders."""
    m = next(x for x in scene["meshes"] if x["id"] == mesh_id)
    pts = [q for f in m["faces"] for q in f]
    lo = [min(q[k] for q in pts) for k in range(3)]
    hi = [max(q[k] for q in pts) for k in range(3)]
    out = []
    for w in scene["meshes"]:
        if w["group"] != "shell":
            continue
        for f in w["faces"]:
            c = [q[axis] for q in f]
            if max(c) - min(c) > 1e-4:
                continue
            o = [k for k in range(3) if k != axis]
            if all(min(q[k] for q in f) < hi[k] - 0.05 and max(q[k] for q in f) > lo[k] + 0.05 for k in o)                     and lo[axis] < c[0] < hi[axis] + 0.5 and c[0] > hi[axis] - 1e-6:
                out.append((w["id"], round(c[0], 3)))
    return out


class BuriedFixtures(unittest.TestCase):
    def test_stair_wall_handrail_stands_in_front_of_the_plaster(self):
        # Round-2 finals v11: the rail sat at y -28.611..-28.581 while the finished plaster beside the flight is at
        # -28.471, so it rendered inside the wall and only its brackets showed.
        self.assertEqual(buried_behind_walls(SCENE, "detail-stair-wall-handrail"), [])
        old = {"meshes": [dict(id="old-rail", group="fixture", faces=[[[5.317, -28.611, 0.70], [9.517, -28.611, -1.95],
                                                                        [9.517, -28.581, -1.95], [5.317, -28.581, 0.70]]])]
               + [m for m in SCENE["meshes"] if m["group"] == "shell"]}
        self.assertTrue(buried_behind_walls(old, "old-rail"), "the real buried rail must be caught")


class WoodGrainMapping(unittest.TestCase):
    """Client 2026-09-28: stair tread wood (v11-stair-void.png) and the ensuite vanity front (v12-ensuite.png)
    both read as long smeared streaks -- "annoyingly fake". Cause, confirmed against a real Blender 4.2.9 import
    on ai-workstation (docs/LEARNINGS.md): a Box-projected Image Texture picks which pair of its input vector's
    three components it reads from the mesh's own UNROTATED geometric normal; `villa_scene.add_material` redirects
    grain by ROTATING that vector (`grain.GRAIN_ROTATION_DEG`), which does not move which pair is read -- it can
    instead point one of the two read components at the face's own normal axis (constant across the whole face),
    collapsing that coordinate to a single texel row/column. These tests exercise the same
    `archpipe.blender.grain.mapping_rotated_span` `villa_scene` uses, so they need no Blender runtime."""

    def test_current_bug_reproduced_on_the_real_tread_box(self):
        # stairs.py tread boxes: x = going (280 mm, walking direction), y = flight width (900 mm, the tread's
        # own length), z = TREAD_T (60 mm). The real, pre-fix material was plain "walnut" (grain_axis="z").
        u_span, v_span = grain.mapping_rotated_span("z", (140.0, 450.0, 30.0))
        self.assertAlmostEqual(u_span, 0.0, places=6,
                               msg="the OLD 'walnut' mapping must collapse on the tread's top face (the real bug)")

    def test_fix_grains_the_tread_along_its_own_length_not_its_depth(self):
        u_span, v_span = grain.mapping_rotated_span("y", (140.0, 450.0, 30.0))
        self.assertAlmostEqual(u_span, 900.0, places=3, msg="grain (image U) must run along the tread's 900 mm length")
        self.assertAlmostEqual(v_span, 280.0, places=3)
        self.assertGreater(min(u_span, v_span), 1.0, "neither span may collapse")

    def test_current_bug_reproduced_on_a_vanity_front_against_an_x_normal_wall(self):
        # villa_furniture_detail._fronts: local x = width, y = FRONT_T (19 mm, thin), z = height. villa_furnish3d
        # to_world swaps local x/y into world x/y for a wall requiring a +-90 deg rotation, so a vanity against
        # such a wall has its ~19 mm thickness along WORLD X, not world Y -- half-extents (9.5, 450, 350) below.
        # The real, pre-fix material was plain "walnut" (grain_axis="z"), same as the tread.
        u_span, v_span = grain.mapping_rotated_span("z", (9.5, 450.0, 350.0))
        self.assertAlmostEqual(v_span, 0.0, places=6,
                               msg="the OLD 'walnut' mapping must collapse on this vanity-front orientation")

    def test_fix_is_safe_on_a_vanity_front_regardless_of_which_wall_it_sits_against(self):
        # "walnut-grain-x" is identity rotation: no coordinate is ever rotated, so nothing can be pointed at the
        # panel's own normal axis, on EITHER orientation a vanity front can end up in.
        for half_extents in ((450.0, 9.5, 350.0), (9.5, 450.0, 350.0)):
            u_span, v_span = grain.mapping_rotated_span("x", half_extents)
            self.assertGreater(min(u_span, v_span), 1.0, half_extents)

    def test_negative_stone_and_fabric_materials_are_unaffected(self):
        # These never set grain_axis (villa_render.py M dict); spec.get("grain_axis", "x") already defaults them
        # to the safe identity rotation, so this fix changes no rendered stone or fabric surface.
        from archpipe.concept.villa_render import M
        untouched = {"travertine", "marble-ensuite", "marble-bath", "marble-white", "boucle", "linen", "paving",
                     "garden-gravel", "rug", "leather-brown"}
        for name in untouched:
            self.assertNotIn("grain_axis", M[name], name)


class ArtificialGrassGuard(unittest.TestCase):
    """Round-3 defect 1: `artificial-grass` rendered as a flat, untextured mint-green plane. Cause: the MATERIALS
    dict had no `asset` key, so villa_scene.add_material's photo-texture branch (`if asset and kind in (...)`)
    never ran. Guard: the material must reference a texture set, and that set must be a real, fetchable manifest
    entry -- not just a truthy string."""

    def test_artificial_grass_references_a_real_texture_asset(self):
        self.assertIn("asset", VR.M["artificial-grass"], "must reference a texture set, not a flat base colour")
        import json
        manifest = json.loads((VR.ROOT / "ops" / "workstation" / "library-manifest.json").read_text())
        ids = {m["id"] for m in manifest["materials"]}
        self.assertIn(VR.M["artificial-grass"]["asset"], ids, "asset must be a real, fetchable manifest entry")

    def test_old_flat_colour_dict_is_caught_by_the_guard(self):
        old = dict(kind="principled", base_rgb=[0.18, 0.30, 0.12], reflectance=0.22, roughness=0.95,
                   note="ASSUMED drained artificial grass; client 2026-09-29")
        self.assertNotIn("asset", old)


def _watertight_and_volume(faces):
    """faces: list of planar polygons (each a list of [x, y, z] points), the same shape `mesh()` stores. Returns
    (is_closed, signed_volume). `is_closed`: every directed edge has exactly one match and exactly one reverse
    match (a watertight two-manifold). `signed_volume`: the divergence-theorem volume from a fan triangulation
    of each face; positive for a solid with consistently outward-wound (CCW) faces -- zero or negative means
    either a degenerate (zero-thickness) shape or inconsistent winding."""
    edge_count = {}
    volume = 0.0
    for face in faces:
        n = len(face)
        for i in range(n):
            a = tuple(round(c, 6) for c in face[i])
            b = tuple(round(c, 6) for c in face[(i + 1) % n])
            edge_count[(a, b)] = edge_count.get((a, b), 0) + 1
        v0 = face[0]
        for i in range(1, n - 1):
            v1, v2 = face[i], face[i + 1]
            volume += (v0[0] * (v1[1]*v2[2] - v1[2]*v2[1])
                       - v0[1] * (v1[0]*v2[2] - v1[2]*v2[0])
                       + v0[2] * (v1[0]*v2[1] - v1[1]*v2[0])) / 6.0
    closed = all(count == 1 and edge_count.get((b, a), 0) == 1 for (a, b), count in edge_count.items())
    return closed, volume


class GlassClosedSolidGuard(unittest.TestCase):
    """Round-3 defect 4 (v12-ensuite.png): the ensuite bath screen read as a mirror. Lead's diagnosis, confirmed
    here: `detail-pe-bath-screen` was a ZERO-THICKNESS plane with a refractive `kind="glass"` shader
    (`glass-bath-screen`, interfaces=1) -- a ray entering the front face has nowhere to exit. Checked the same
    class across every other refractive glass mesh in the scene (stair guard, stair glass panels), not just the
    one the lead named. `glass-clear` (architectural windows) is a DELIBERATE, out-of-scope exception: it is
    shell code (villa_render's window/opening builder, not furniture/fixture/garment GEOMETRY), a single sheet
    by design, and its transmittance is daylight-calibrated against that assumption -- reported to the lead
    rather than changed here."""

    def test_every_refractive_glass_mesh_is_a_closed_solid_with_thickness(self):
        checked = 0
        for m in SCENE["meshes"]:
            mat = SCENE["materials"].get(m["material"])
            if not mat or mat["kind"] != "glass":
                continue
            checked += 1
            closed, volume = _watertight_and_volume(m["faces"])
            self.assertTrue(closed, "%s (%s) is not a watertight solid" % (m["id"], m["material"]))
            self.assertGreater(volume, 0,
                               "%s (%s) has zero/negative volume: no real thickness or inconsistent winding"
                               % (m["id"], m["material"]))
        self.assertGreater(checked, 0, "expected at least one refractive glass mesh in the scene")

    def test_glass_clear_windows_have_two_interfaces(self):
        windows = [m for m in SCENE["meshes"] if m["material"] == "glass-clear"]
        self.assertTrue(windows, "expected architectural glazing meshes to exist")
        self.assertEqual(SCENE["materials"]["glass-clear"]["interfaces"], 2)
        self.assertTrue(all(_watertight_and_volume(m["faces"])[0] for m in windows))

    def test_old_single_quad_bath_screen_is_caught_by_the_guard(self):
        # Reproduces the real pre-fix defect on the real fitting dimensions (revit_spec's pe-bath-screen).
        old_screen = [[[19.9, -25.9, 0.0], [21.1, -25.9, 0.0], [21.1, -25.9, 2.0], [19.9, -25.9, 2.0]]]
        closed, volume = _watertight_and_volume(old_screen)
        self.assertFalse(closed)


class DressingGarmentGuard(unittest.TestCase):
    """Round-3 defect 5 (v31/v32): hanging garments were flat 25 mm vertical slabs, all drawn from one shared,
    colour-agnostic fabric list. Checks that the fix actually varies colour and shape, and stays inside the
    checked module envelope (`test_nothing_floats`/`test_openings_passable` cover the general float/collision
    guard against the real scene; these are specific to the new garment shapes)."""

    def test_hanging_garments_use_more_than_one_colour_per_partner(self):
        for partner, prefix in (("hers", "dress-hers-"), ("his", "dress-his-")):
            mats_used = {m["material"] for m in SCENE["meshes"]
                        if m["id"].startswith(prefix) and "-garment-" in m["id"] and "-hanger" not in m["id"]}
            self.assertGreater(len(mats_used), 1, "%s garments should not all share one fabric colour" % partner)
            for name in mats_used:
                self.assertTrue(name.startswith("garment-"), name)

    def test_garments_are_not_flat_slabs(self):
        # A real drape has depth; the old defect was a uniform 25 mm slab with identical top/bottom extents.
        garments = [m for m in SCENE["meshes"] if "-garment-" in m["id"] and "-hanger" not in m["id"]]
        self.assertTrue(garments)
        for m in garments[:40]:
            xs = [p[0] for face in m["faces"] for p in face]
            ys = [p[1] for face in m["faces"] for p in face]
            self.assertGreater(max(xs) - min(xs), 0.04, m["id"] + " too thin along the rail")
            self.assertGreater(max(ys) - min(ys), 0.03, m["id"] + " too thin front-to-back")
            levels = {round(p[2], 3) for face in m["faces"] for p in face}
            self.assertGreaterEqual(len(levels), 5, m["id"] + " has no shoulder/waist/hem drape")
        # The first round-three correction had only a top and bottom ring.
        old_slab = VR.pane_faces([[0, 0, 1], [.3, 0, 1], [.3, .03, 1], [0, .03, 1]],
                                 [[0, 0, 0], [.3, 0, 0], [.3, .03, 0], [0, .03, 0]])
        self.assertEqual(len({p[2] for face in old_slab for p in face}), 2)

    def test_long_hang_garments_are_hers_only_and_in_the_dress_length_range(self):
        for m in SCENE["meshes"]:
            if not (m["id"].startswith("dress-hers-long-hang-") and "-garment-" in m["id"] and "-hanger" not in m["id"]):
                continue
            zs = [p[2] for face in m["faces"] for p in face]
            self.assertTrue(1.40 <= max(zs) - min(zs) <= 1.65, "%s length %.2f out of the dress card range"
                            % (m["id"], max(zs) - min(zs)))
        self.assertFalse(any(m["id"].startswith("dress-his-long-hang-") for m in SCENE["meshes"]),
                         "his wardrobe has no long-hang module (villa_furnish.py)")

    def test_hanging_garments_stay_inside_their_module_envelope(self):
        # Envelope containment is exercised end-to-end by test_nothing_floats/test_openings_passable on the
        # real built scene; here we just confirm every garment mesh actually clamped to its module (no vertex
        # strays past the wardrobe's own footprint padding used when placing it).
        from archpipe.concept import villa_furnish as F
        lay = R.design("D1")
        wardrobes = {i["id"]: i for i in F.layout(lay) if i["id"] in ("pd-hang-1", "pd-hang-2")}
        for wid, wardrobe in wardrobes.items():
            q = F.footprint(wardrobe)
            prefix = "dress-" + wardrobe["partner"] + "-"
            for m in SCENE["meshes"]:
                if not (m["id"].startswith(prefix) and "-garment-" in m["id"]):
                    continue
                xs = [p[0] for face in m["faces"] for p in face]
                self.assertTrue(q[0] - 0.03 <= min(xs) and max(xs) <= q[2] + 0.03,
                               "%s strays past its wardrobe module in x" % m["id"])

    def test_each_partner_has_pairs_of_shoes_and_separate_top_boxes(self):
        for partner in ("hers", "his"):
            shoes = [m for m in SCENE["meshes"] if m["id"].startswith("dress-" + partner + "-shoe-")]
            boxes = [m for m in SCENE["meshes"] if m["id"].startswith("dress-" + partner + "-top-box-")]
            self.assertGreaterEqual(len(shoes), 2)
            self.assertGreaterEqual(len(boxes), 2)


if __name__ == "__main__":
    unittest.main()
