"""Views chosen by intent (archpipe.concept.render_views): each rule is here because a draft broke it.
Client 2026-09-27: "Some of the cameras are looking at the wrong direction and uninformative"."""
import math
import unittest

from archpipe.concept import render_views as RV
from archpipe.concept import revit_spec as RS
from archpipe.concept import villa_furnish as F
from archpipe.concept import villa_r11 as R

LAY = R.design("D1")
SP = RS.build(LAY)
ITEMS = {i["id"]: i for i in F.layout(LAY)}


class ChosenViews(unittest.TestCase):
    def test_exterior_lounge_subject_uses_built_sofa_bounds(self):
        from scripts import villa_render_views as views
        scene = {"meshes": [{"id": "landscape-sofa-00",
                             "faces": [[[24.0, -28.0, -3.0], [26.1, -28.0, -3.0],
                                        [26.1, -27.15, -3.0], [24.0, -27.15, -3.0]]]}]}
        self.assertEqual(views.subject_footprint("landscape-sofa", ITEMS, LAY["rooms"], scene),
                         (24.0, -28.0, 26.1, -27.15))
        with self.assertRaisesRegex(ValueError, "unresolved view subject"):
            views.subject_footprint("landscape-sofa", ITEMS, LAY["rooms"], {"meshes": []})

    def test_every_view_subject_matches_scene_content(self):
        """Round-2 draft: v07 still named "terrace lounge set" after the landscape replaced that set, so the
        renderer matched nothing and QA reported the subject out of frame. Mirror villa_scene.subjects' matching."""
        from archpipe.concept import villa_render as V
        scene = V.build(LAY)
        meshes = scene["meshes"]

        def matched(s):
            return [m for m in meshes if m["id"] == s or m["id"].startswith(s) or m.get("room") == s
                    or m.get("label") == s]
        orphans = [(v["id"], s) for v in scene["views"] for s in v["subjects"] if not matched(s)]
        self.assertEqual(orphans, [])
        self.assertFalse(matched("terrace lounge set"), "the stale v07 subject must stay unmatched (the real defect)")
        additions = scene["views"][24:]
        self.assertEqual([v["id"].split("-")[0] for v in additions],
                         ["v%02d" % n for n in range(25, 35)])
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

    def test_a_point_in_a_door_band_is_a_doorway_point(self):
        """A camera 30 mm inside the ensuite stood in its closed door leaf (a black band in draft 10)."""
        d = next(d for d in SP["doors"] if set(d["rooms"]) == {"parents-dressing-ext", "parents-ensuite"})
        h = F._door_axis(d) == "h"
        # right beside the jamb, inside the wall band: never a standing point
        jx, jy = (d["x"] + d["width"] / 2 - 0.05, d["y"] - 0.03) if h else (d["x"] - 0.03, d["y"] + d["width"] / 2 - 0.05)
        self.assertFalse(RV._in_opening(SP, "GF", jx, jy, "parents-ensuite"))


if __name__ == "__main__":
    unittest.main()
