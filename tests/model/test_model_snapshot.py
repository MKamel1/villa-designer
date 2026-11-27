"""The committed model snapshot (src/archpipe/model/data/d1-elements.json) against live source data.

Fast checks only. Regenerating the slow sources (lighting, garden plan: minutes) is `python -m archpipe.model.export
--snapshot`; set ARCHPIPE_SLOW=1 to have this file re-derive luminaires and compare them with the snapshot.
"""
import copy
import os
import unittest
from collections import Counter
from dataclasses import asdict

from archpipe import model
from archpipe.concept import revit_spec as RS
from archpipe.concept import villa_furnish as F
from archpipe.concept import villa_r11 as R
from archpipe.model import api, spec_source as S


class Snapshot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.els = model.load_json(api.snapshot_path("D1"))
        cls.kinds = Counter(e.kind for e in cls.els)
        cls.lay = R.design("D1")
        cls.sp = RS.build(cls.lay)

    def test_validates(self):
        self.assertEqual(model.validate(self.els), [])

    def test_counts_by_kind(self):
        k = self.kinds
        self.assertEqual((k["room"], k["wall"], k["door"], k["window"], k["stair"]), (31, 37, 19, 8, 1))  # +1: suite-vestibule, client FINAL 2026-11-26: +1 room, +1 wall (x=17.45), +1 door
        self.assertEqual((k["column"], k["beam"], k["slab"], k["railing"]), (9, 24, 6, 8))     # slab: + B and GF floor slabs (lane M)
        self.assertEqual(k["luminaire"], 137)        # +3 PCOVE (ST39 cove round the ensuite bath feature panel, L4 round 5)
        self.assertEqual(k["plant"], 80)
        self.assertEqual(k["furniture"], 79)       # +1 sv-store (and +1 FX kids loft) flat cabinet in the suite vestibule (client FINAL 2026-11-26); was 77 = 79 less the two floating ledges (DF 2026-11-26: the joinery bed carries its own trays); includes the G1 under-stair cupboard; the two throw-pillow props were replaced by the L4 cushion schedule (2026-11-23)

    def test_spec_kinds_equal_a_fresh_derivation(self):
        from archpipe.model import geometry_complete as GC
        spec = S.all_from_spec(self.lay, self.sp, finish=_finish())
        ids = {e.id for e in spec}
        slow = [e for e in self.els if e.kind in ("furniture", "luminaire", "plant", "garden") and e.id not in ids]
        done = GC.complete(spec + [copy.deepcopy(e) for e in slow], self.lay, self.sp, _finish())
        fresh = {e.id: asdict(e) for e in done if e.id in ids or e.kind in ("floor", "ceiling", "storey", "type")
                 or e.id in ("slab-B-floor", "slab-GF-floor")}
        snap = {e.id: asdict(e) for e in self.els if e.id in fresh}
        self.assertEqual(set(snap), set(fresh))
        for i, f in fresh.items():
            self.assertEqual(_norm(snap[i]), _norm(f), i)

    def test_furniture_equals_layout(self):
        items = {f"furn-{i['id']}": i for i in F.layout(self.lay)}
        got = {e.id: e for e in self.els if e.kind == "furniture" and e.id in items}
        self.assertEqual(set(got), set(items))
        for i, it in items.items():
            self.assertEqual(got[i].size[0], round(it["w"] * 1000.0, 1))
            self.assertEqual(got[i].room, it["room"])

    def test_luminaires_carry_photometry_ref(self):
        lums = [e for e in self.els if e.kind == "luminaire"]
        with_ies = [e for e in lums if e.params["photometry"]["ies"]]
        self.assertEqual(len(with_ies), 75)   # FX 2026-11-25: kids A desk downlights (2 ERCO) replaced by generic UC strips: 77 -> 75;      # +3 PCOVE carry the ST39 IES (74 -> 77; generic stays 58). L6d: the entry-lobby DL became a generic cove (75 -> 74). L6c design: the ERCO-bound kinds (DL, DLN, ADJ, WW, DESK, PEN-LIN) and their substitutes carry an IES
        # every luminaire without an IES must say so: generic, no product, no manufacturer code (never a silent gap)
        for e in lums:
            ph = e.params["photometry"]
            if not ph["ies"]:
                self.assertTrue(ph["generic"] and not ph["code"] and not e.product_id, e.id)
        self.assertEqual(len(lums) - len(with_ies), 62)   # FX 2026-11-25: 58 -> 62 generic (3 UC strips: sink run + 2 under lofts; +1 kids night light)
        for e in with_ies:
            self.assertFalse(e.params["photometry"]["ies"].startswith(("C:", "/", "\\")), e.id)
            self.assertTrue(e.params["photometry"]["ies"].endswith(".ies"))
            self.assertIn("/", e.product_id)
        for e in lums:
            self.assertGreater(e.params["flux_lm"], 0, e.id)

    def test_net_area_and_openings_for_l1(self):
        by = {e.id: e for e in self.els}
        lounge = by["room-lounge"].params
        self.assertEqual(lounge["gross_area_m2"], lounge["area_m2"])
        self.assertLess(lounge["net_area_m2"], lounge["gross_area_m2"])
        self.assertEqual(lounge["revit_net_area_m2"], 21.87)            # Revit read-back, furnish-d1 option 0
        for e in self.els:
            if e.kind == "room":
                self.assertGreater(e.params["net_area_m2"], 0, e.id)
                self.assertLessEqual(e.params["net_area_m2"], e.params["gross_area_m2"], e.id)
            if e.kind == "door":
                for k in ("operation", "swing_basis", "clear_width_mm", "clear_width_basis", "leaf_width_mm"):
                    self.assertIn(k, e.params, e.id)
                self.assertIn(e.params["operation"], ("hinged", "pocket", "sliding"))
                self.assertLessEqual(e.params["clear_width_mm"], e.params["leaf_width_mm"] + 1e-6)
            if e.kind == "window":
                self.assertIn("openable_area_m2", e.params)
                self.assertIsNone(e.params["openable_area_m2"])         # not authored: explicit, not invented
                self.assertGreater(e.params["gross_area_m2"], 0)
        pocket = by["door-B-kitchen-dirty-kitchen"].params
        self.assertEqual(pocket["operation"], "sliding")                # the client-approved 1.2 m sliding link
        self.assertEqual(by["door-GF-parents-bed-parents-dressing"].params["swing_into"], "parents-dressing")

    def test_guards_and_unguarded_edges(self):
        by = {e.id: e for e in self.els}
        g = by["rail-gf-stair-void"]
        self.assertEqual(g.params["guard_height_mm"], 1100.0)
        self.assertEqual(g.params["edge_lengths_mm"][0], 3710.0)         # the 3.71 m open edge
        self.assertTrue(g.params["in_revit_spec"])                       # G1: guards are in the Revit spec
        self.assertTrue(g.params["in_scene"])
        for rid in ("rail-gf-terrace-edge", "rail-patio-steps-edge"):
            self.assertTrue(by[rid].params["in_revit_spec"], rid)
            self.assertFalse(by[rid].params["in_scene"], rid)
        for sid, gid in (("slab-gf-terrace", "rail-gf-terrace-edge"), ("ctx-entrance-steps", "rail-patio-steps-edge")):
            self.assertTrue(by[sid].params["guard_present"], sid)
            self.assertEqual(by[sid].params["guard_id"], gid)
        self.assertEqual(by["slab-gf-terrace"].params["drop_to_patio_mm"], 3000.0)
        self.assertEqual(by["garden-north-patio"].params["floor_below_street_mm"], 1800.0)

    def test_every_room_element_refers_to_a_room(self):
        rooms = {e.room for e in self.els if e.kind == "room"} | {e.id[5:] for e in self.els if e.kind == "room"}
        for e in self.els:
            if e.kind in ("luminaire", "furniture", "door") and e.room:
                self.assertIn(e.room, rooms, e.id)

    @unittest.skipUnless(os.environ.get("ARCHPIPE_SLOW"), "set ARCHPIPE_SLOW=1 (about a minute)")
    def test_luminaires_equal_lighting_design(self):
        from archpipe.concept import villa_lighting as VL
        from archpipe.model import fit_source as FS
        fresh = {e.id: asdict(e) for e in FS.luminaires(VL.design(self.lay))}
        snap = {e.id: asdict(e) for e in self.els if e.kind == "luminaire"}
        self.assertEqual(set(snap), set(fresh))
        for i in fresh:
            self.assertEqual(_norm(snap[i]), _norm(fresh[i]), i)


def _finish():
    from archpipe.concept import villa_render as VR
    return VR.FINISH


_REVIT_ONLY = ()                       # net areas now come from the built walls: nothing machine-dependent


def _norm(d):
    import json
    d = json.loads(json.dumps(d, default=list))
    for k in _REVIT_ONLY:
        d.get("params", {}).pop(k, None)
    return d


if __name__ == "__main__":
    unittest.main()
