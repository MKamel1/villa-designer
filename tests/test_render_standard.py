"""ADR-0013 is the standard for EVERY presentation render, not only the bedroom (client 2026-09-27: "that should
be our standards and our process for all renders"). The first villa set skipped half of it (16-20 mm lenses at
1.55 m, fixed guessed exposures, textured 'rugged' paint, box furniture, no skirting or frames); this test fails if a
villa scene departs from the parts the bedroom proved."""
import unittest

from archpipe.concept import villa_render as VR

SCENE = VR.build()

# Audited presentation finishes, including the explicitly authored luminous
# surfaces. A new CAD fallback or unassigned material fails this list.
ALLOWED_MATERIALS = {
    "plaster-warm-white", "ceiling-white", "travertine", "oak-floor", "marble-ensuite", "marble-bath",
    "marble-white", "walnut", "walnut-grain-x", "oak", "oak-grain-x", "greige-lacquer", "boucle", "linen", "sage-fabric",
    "charcoal-fabric", "taupe-fabric", "bedding-white", "throw-taupe", "rug", "leather-brown", "brass",
    "black-metal", "ceramic-white", "screen-black", "glass-clear", "glass-guard", "glass-edge", "opal-strip",
    "silvered-mirror", "door-oak", "garden-gravel", "garden-pebbles", "garden-sandstone",
    "render-exterior", "paint-exterior-grey-green", "paving", "lawn", "outdoor-fabric", "teak",
    "alu-bronze", "paint-white-satin", "white-paint-joinery", "led-lin-2700", "lens-2700",
    "marker-2200", "opal-pen-globe-2700", "opal-pen-small-2700", "opal-wall-read-2700", "opal-sconce-3000",
    "opal-vsconce-3000", "curtain-sheer", "curtain-heavy", "curtain-heavy-dimout",
}


class RenderStandard(unittest.TestCase):
    def test_wp2b_checked_joinery_and_kitchen_builders(self):
        from archpipe.concept import villa_furnish as F, villa_furniture_detail as FD
        items = {i["id"]: i for i in F.layout(VR.R.design("D1"))}
        expected = {
            "library-cabinet-left": {"glass-door", "door-frame", "shelf", "back"},
            "library-cabinet-right": {"glass-door", "door-frame", "shelf", "back"},
            "library-daybed": {"mattress", "cushion", "nook-side", "nook-top"},
            "dk-appliance-bank": {"fridge", "oven-glass"},
            "k-island": {"microwave-glass", "hob"},
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
        self.assertIn("detail-curtain-library-nook-track", ids)
        self.assertTrue(all(m["material"] == "walnut" for m in SCENE["meshes"]
                            if m["id"].startswith("furn-library-end-panel-")))
        self.assertEqual(sum(i.startswith("lamp-shade-DESK-cinema-") for i in ids), 2)
        self.assertEqual(sum(i.startswith("furn-cinema-desk-chair-") and i.endswith("-0") for i in ids), 2)

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
        self.assertEqual(set(plan["paths"]), {"dining", "living-north", "living-east", "lounge-west"})
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
        for _, _, x, y, _ in plan["trees"]:
            self.assertTrue(LAND.inside_yard(x, y))
            self.assertGreaterEqual(LAND.facade_distance(x, y), 1.5)
        self.assertLess(LAND.facade_distance(1.10, -28.00), 1.5,
                        "the old west tree must fail against the front projection")
        for d in (d for d in sp["doors"] if d.get("garden")):
            self.assertTrue(any(x0 - 0.001 <= d["x"] <= x1 + 0.001 and
                                y0 - 0.001 <= d["y"] <= y1 + 0.001
                                for x0, y0, x1, y1 in plan["paths"].values()), d)
        self.assertTrue({"jacaranda_tree", "tree_small_02", "searsia_lucida", "grass_medium_01",
                         "grass_medium_02", "flower_gazania", "periwinkle_plant", "wild_rooibos_bush",
                         "boulder_01", "namaqualand_stones_01"} <= {p["asset"] for p in props})
        self.assertTrue(all(p["position"][2] >= LAND.GROUND for p in props))
        self.assertEqual(S.unsupported(SCENE), [])
        self.assertEqual(S.blocked_openings(SCENE), [])
        self.assertTrue(any("14:00" in n and "17:00" in n for n in notes))
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
            if "lens_basis" in c:                  # client 2026-09-27: a CALCULATED lens where 24 mm cannot hold the room
                import math
                need = float(c["lens_basis"].split(" deg off axis")[0].split()[-1])
                self.assertGreater(need, 36.87, v["id"] + ": 24 mm would have held it")
                self.assertEqual(c["lens_mm"], 16, v["id"])
                # the 16 mm camera is re-placed by render_views.choose; the check is at that camera
                at16 = float(c["lens_basis"].split("at 16 mm widest ")[1].split()[0])
                self.assertLessEqual(at16, math.degrees(math.atan(18 / 16)), v["id"] + ": 16 mm does not hold it")
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
        triangles (corner radius = half the ring) and the whole draft was refused remotely."""
        from archpipe import villa_render_contract as C
        self.assertEqual(C.validate_scene(SCENE), [])

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
        # The real D1 scene has no leaf at the new telescopic kitchen door, while the cinema door has one.
        from scripts import villa_render_views as views
        by = {v["id"]: v for v in SCENE["views"]}
        kitchen = by["v17-dirty-kitchen"]
        cinema = by["v08-cinema"]
        self.assertFalse(views.door_leaf_near(SCENE, *kitchen["camera"]["position"][:2]))
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
        mk = next(m for m in sc["meshes"] if m["id"] == "marker-STEP-stair-b-02")
        for f in mk["faces"]:
            for v in f:
                v[1] += 0.068
        found = {u[0] for u in S.unsupported(sc)}
        self.assertIn("lamp-shade-DESK-kids-a-03", found)
        self.assertIn("marker-STEP-stair-b-02", found)

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
        self.assertEqual(got_rooms, expected_rooms | {"bar-alcove"})
        self.assertEqual(sum(c["id"] == "curtain-library-nook" for c in SCENE["curtains"]), 1)
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


if __name__ == "__main__":
    unittest.main()
