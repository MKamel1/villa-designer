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
    "black-metal", "ceramic-white", "screen-black", "glass-clear", "glass-guard", "door-oak",
    "render-exterior", "paint-exterior-grey-green", "paving", "lawn", "outdoor-fabric", "teak",
    "alu-bronze", "paint-white-satin", "white-paint-joinery", "led-lin-2700", "lens-2700",
    "marker-2200", "opal-pen-globe-2700", "opal-pen-small-2700", "opal-wall-read-2700", "opal-sconce-3000",
    "opal-vsconce-3000",
}


class RenderStandard(unittest.TestCase):
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
        for suffix in ("wall-stringer-00", "wall-plate", "open-stringer", "baluster-00", "open-handrail",
                       "wall-handrail"):
            self.assertIn("detail-stair-" + suffix, ids)
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
        from archpipe.concept import villa_furnish as F, villa_furniture_detail as FD, villa_r11 as R
        ids = {m["id"] for m in SCENE["meshes"]}
        for name in ("coffee-main", "coffee-dirty", "microwave-dirty", "fridge-dirty", "downdraft-island", "hood-dirty"):
            self.assertIn("appliance-" + name, ids)
        items = {i["id"]: i for i in F.layout(R.design("D1"))}
        self.assertIn("fridge", items["dk-fridge"]["why"])
        self.assertIn("cleaning storage", items["dk-fold"]["why"])
        for name in ("k-run", "dk-run"):
            self.assertTrue({"sink", "tap"} <= set(FD.world_parts(items[name], 0)))
        self.assertIn("microwave-glass", FD.world_parts(items["k-tall"], 0))

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


if __name__ == "__main__":
    unittest.main()
