"""Lane SC: the G1 guards, riser infill and understair cupboard that the scene builder draws from the spec.

Pure geometry (blender/g1_geometry.py) is tested on the real spec; the placement of the built meshes is checked
against the spec's own numbers, and every test has a negative twin (it must stay quiet when it should)."""
import unittest

import numpy as np

from archpipe.blender import g1_geometry as G1
from archpipe.concept import revit_spec as RS, villa_render as VR
from archpipe.parity import geom as PG


def box_faces(x0, y0, z0, x1, y1, z1):
    return VR.box_faces(x0, y0, z0, x1, y1, z1)


def bounds(faces):
    v = np.array([p for f in faces for p in f])
    return v.min(0), v.max(0)


def crossing_depth(a, b):
    ta = np.concatenate([PG.fan(f) for f in a]); tb = np.concatenate([PG.fan(f) for f in b])
    return PG.penetration(*PG.tri_cross_segments(ta, tb))[0]


class G1Geometry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sp = RS.build(VR.R.design("D1"))
        cls.g = {g["id"]: g for g in cls.sp["guards"]}

    def test_terrace_guard_height_path_and_no_overlap(self):
        g = self.g["guard-gf-terrace-edge"]
        part = G1.glass_guard(g, box_faces, "m", "rail-gf-terrace-edge")
        lo, hi = bounds(part.faces)
        self.assertAlmostEqual(hi[2] - lo[2], 1.1, places=6)                       # the model's 1100 mm
        self.assertAlmostEqual(lo[2], g["path"][0][2], places=6)
        self.assertAlmostEqual(lo[1], g["path"][0][1] - 0.0, places=6)             # starts at the path start
        self.assertAlmostEqual(hi[0], g["path"][-1][0], places=6)                  # ends at the path end
        self.assertEqual(part.element_ids, ["rail-gf-terrace-edge"])
        a, b = part.faces[:6], part.faces[6:]
        self.assertEqual(crossing_depth(a, b), 0.0)                                # panes meet face to face, not through
        self.assertEqual(len(part.faces), 12)

    def test_terrace_guard_negative_overlapping_corner_is_detected(self):
        # the same corner built without the face-to-face rule: the crossing test must see it
        t = 0.012
        a = box_faces(1.831, -28.671, 0, 1.843, -23.691, 1.1)
        b = box_faces(1.831, -23.697, 0, 3.617, -23.685, 1.1)
        self.assertGreater(crossing_depth(a, b), 0.0)

    def test_patio_bars_leave_no_opening_over_the_specified_clear(self):
        g = self.g["guard-entrance-steps-patio-edge"]
        part = G1.bar_guard(g, box_faces, "m", "rail-patio-steps-edge")
        boxes = [bounds(part.faces[i:i + 6]) for i in range(0, len(part.faces), 6)]
        *bars, rail = boxes
        xs = sorted((lo[0], hi[0]) for lo, hi in bars)
        clears = [b[0] - a[1] for a, b in zip(xs, xs[1:])]
        self.assertLessEqual(max(clears) * 1000, g["max_opening_mm"] + 1e-6)       # 75 mm clear at most
        self.assertGreater(min(clears), 0.05)                                      # and not a solid fence
        top = max(hi[2] for _, hi in boxes)
        self.assertAlmostEqual(top - g["path"][0][2], 1.1, places=6)               # rail top at 1100 mm
        self.assertAlmostEqual(rail[1][2] - rail[0][2], 0.020, places=6)
        self.assertAlmostEqual(xs[0][0], g["path"][0][0], places=6)
        self.assertAlmostEqual(xs[-1][1], g["path"][1][0], places=6)

    def test_bar_guard_rejects_a_path_that_is_not_one_segment_on_x(self):
        g = dict(self.g["guard-entrance-steps-patio-edge"], path=[[0, 0, 0], [1, 1, 0]])
        with self.assertRaises(ValueError):
            G1.bar_guard(g, box_faces, "m", "x")

    def test_riser_infill_one_bar_per_gap_between_the_steel(self):
        part = G1.riser_infill(self.sp, box_faces, -28.396, -27.536)
        self.assertEqual(len(part.faces) // 6, self.sp["stair_infill_spec"]["count"])
        lo, hi = bounds(part.faces)
        self.assertAlmostEqual(lo[1], -28.396); self.assertAlmostEqual(hi[1], -27.536)
        self.assertEqual(part.element_ids, ["stair-main"])
        # the slot left at the tread edge stays under the 100 mm sphere
        tread_edge = max(b[4] for b in self.sp["stair"]) / 1000
        self.assertLess(tread_edge - hi[1], 0.100)

    def test_riser_infill_none_without_spec_infill(self):
        self.assertIsNone(G1.riser_infill(dict(self.sp, stair_infill=[]), box_faces, -28.396, -27.536))

    def test_cupboard_steps_follow_treads_and_never_poke_into_one(self):
        parts = G1.understair_cupboard(self.sp, box_faces, -28.396, -27.536)
        by = {p.mesh_id.rsplit("-", 1)[-1]: p for p in parts}
        self.assertEqual(set(by), {"side", "toe", "end", "door", "pull"})
        self.assertTrue(all(p.element_ids == ["joinery-understair-cupboard"] for p in parts))
        side = by["side"].faces
        treads = [[v / 1000 for v in b] for b in self.sp["stair"] if b[5] - b[2] < 300 and b[2] + 3000 < 2000]
        tread_tris = [box_faces(*t) for t in treads]
        for t in tread_tris:                                      # the stepped top touches the treads, never crosses
            self.assertEqual(crossing_depth(side, t), 0.0)
        lo, hi = bounds(side)
        self.assertAlmostEqual(hi[2], -3.0 + 1.8812, places=3)    # model soffit_max
        self.assertAlmostEqual(lo[2], -3.0)

    def test_cupboard_door_opening_is_cut_and_the_leaf_fits_it(self):
        parts = G1.understair_cupboard(self.sp, box_faces, -28.396, -27.536)
        door = next(p for p in parts if p.mesh_id.endswith("door"))
        side = next(p for p in parts if p.mesh_id.endswith("side"))
        (dlo, dhi), d = bounds(door.faces), self.sp["understair_cupboard"]["door"]
        self.assertAlmostEqual(dhi[2] - dlo[2], d["height"] - 0.003, places=6)
        self.assertEqual(crossing_depth(side.faces, door.faces), 0.0)   # leaf sits in the opening, not through the wall
        # negative: a leaf taller than the opening (a wrong height) does cross the lintel
        tall = box_faces(dlo[0], dlo[1], -3.0, dhi[0], dhi[1], -3.0 + d["height"] + 0.2)
        self.assertGreater(crossing_depth(side.faces, tall), 0.0)

    def test_cupboard_absent_without_spec(self):
        self.assertEqual(G1.understair_cupboard(dict(self.sp, understair_cupboard=None), box_faces, -28.4, -27.5), [])

    def test_steel_clear_y_reads_the_members_it_must_avoid(self):
        m = [dict(id="detail-stair-wall-stringer-00", faces=[[[0, -28.6, 0], [0, -28.396, 0], [1, -28.396, 0]]]),
             dict(id="detail-stair-wall-plate", faces=[[[0, -28.43, 0], [0, -28.40, 0], [1, -28.40, 0]]]),
             dict(id="detail-stair-glass-shoe", faces=[[[0, -27.536, 0], [0, -27.496, 0], [1, -27.5, 0]]]),
             dict(id="detail-stair-open-stringer", faces=[[[0, -27.526, 0], [0, -27.496, 0], [1, -27.5, 0]]]),
             dict(id="furn-other", faces=[[[0, -1, 0], [0, -99, 0], [1, 5, 0]]])]
        self.assertEqual(G1.steel_clear_y(m), (-28.396, -27.536))


if __name__ == "__main__":
    unittest.main()


class ElementIdentity(unittest.TestCase):
    """The identity rules this lane added (blender/element_ids.py)."""

    def test_non_model_mesh_gets_an_explicit_class_id_not_an_empty_one(self):
        from archpipe.blender import element_ids as EID
        scene = dict(meshes=[dict(id="rug-lounge", group="furniture", faces=[1] * 6, element_ids=[], element_id_basis="unresolved"),
                             dict(id="landscape-g6-pergola-post-0", group="furniture", faces=[1] * 6, element_ids=[],
                                  element_id_basis="unresolved"),
                             dict(id="mystery-mesh", group="furniture", faces=[1] * 6, element_ids=[], element_id_basis="unresolved"),
                             dict(id="furn-k-run-0", group="furniture", faces=[1] * 6, element_ids=["furn-k-run"],
                                  element_id_basis="generator-name")])
        left = EID.tag_non_model(scene)
        m = {x["id"]: x for x in scene["meshes"]}
        self.assertEqual(m["rug-lounge"]["element_ids"], ["nonmodel-rug"])
        self.assertEqual(m["landscape-g6-pergola-post-0"]["element_ids"], ["nonmodel-garden-structure"])
        self.assertEqual(m["rug-lounge"]["element_id_basis"], "non-model")
        # negative: an unexplained mesh stays unresolved and is reported, a resolved one is left alone
        self.assertEqual(left, ["mystery-mesh"])
        self.assertEqual(m["mystery-mesh"]["element_ids"], [])
        self.assertEqual(m["furn-k-run-0"]["element_ids"], ["furn-k-run"])

    def test_every_no_model_prefix_has_a_class(self):
        from archpipe.blender import element_ids as EID
        for prefix, _ in EID.NO_MODEL_ELEMENT:
            self.assertIsNotNone(EID.no_model_class(prefix + "x"), prefix)

    def test_declared_shared_mesh_gives_every_id_every_face(self):
        from archpipe.blender import element_ids as EID
        face = [[0, 0, 0], [1, 0, 0], [1, 1, 0]]
        scene = dict(meshes=[dict(id="furn-gwc-shower-0", group="furniture", faces=[face] * 6)])
        EID.attach(scene, EID.Registry(), {"furn-gwc-shower", "wetzone-gwc-shower"},
                   {"furn-gwc-shower-0": dict(element_ids=["furn-gwc-shower", "wetzone-gwc-shower"])})
        m = scene["meshes"][0]
        self.assertEqual(m["faces_by_element"], {e: list(range(6)) for e in m["element_ids"]})
        self.assertEqual(EID.covered_faces(m), 6)                       # union, not 12

    def test_floor_slabs_are_the_model_slabs_and_context_slabs_are_not(self):
        from archpipe.blender import element_ids as EID
        self.assertEqual(EID.MODEL_SLABS["slab-GF-front"], "slab-gf-terrace")
        for ctx in ("slab-APT", "slab-ROOF", "yard-sister"):
            self.assertNotIn(ctx, EID.MODEL_SLABS)
