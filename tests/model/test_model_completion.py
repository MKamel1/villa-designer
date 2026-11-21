"""Lane M: model completion (slabs, build-ups, ceilings, floors, types, door handing, sizes, net areas, existing data,
validation rules). Positive and negative cases; the negatives use the real pre-fix spec where there is one."""
import copy
import json
import os
import shutil
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from archpipe import model, villa_env as E
from archpipe.concept import revit_spec as RS
from archpipe.concept import villa_r11 as R
from archpipe.model import api, geometry_doors as GD, geometry_existing as GX, geometry_net as GN, geometry_sizes as GS
from archpipe.model import validate_rules as VR


class Completed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.els = model.load_json(api.snapshot_path("D1"))
        cls.by = {e.id: e for e in cls.els}
        cls.k = Counter(e.kind for e in cls.els)
        cls.lay = R.design("D1")
        cls.sp = RS.build(cls.lay)

    def test_validates_and_rules_clean(self):
        self.assertEqual(model.validate(self.els), [])
        self.assertEqual([f for f in VR.check(self.els, self.lay, self.sp, E.COLUMNS) if f["severity"] == "error"], [])

    def test_new_kinds_counts(self):
        self.assertEqual((self.k["floor"], self.k["ceiling"], self.k["storey"]), (30, 30, 5))
        self.assertGreaterEqual(self.k["slab"], 6)                       # + B and GF floor slabs
        self.assertIn("slab-B-floor", self.by)
        self.assertIn("slab-GF-floor", self.by)

    def test_floor_slabs(self):
        gf = self.by["slab-GF-floor"]
        self.assertEqual(gf.params["thickness_mm"], 200.0)
        self.assertEqual(len(gf.params["holes_mm"]), 1)                  # the stair opening
        self.assertEqual(gf.params["layers"][0]["function"], "structure")

    def test_walls_have_layers_with_stated_status(self):
        for w in (e for e in self.els if e.kind == "wall"):
            fn = [l["function"] for l in w.params["layers"]]
            self.assertIn("structure", fn, w.id)
            core = next(l for l in w.params["layers"] if l["side"] == "core")
            self.assertEqual(core["thickness_mm"], w.params["thickness_mm"])
            for l in w.params["layers"]:
                self.assertTrue(l["source"], w.id)
                if l["thickness_mm"] is None:                            # never invented: unauthored stays None
                    self.assertIn(l["status"], ("UNVERIFIED", "ASSUMED"))
        # a marble bathroom wall gets the recorded marble + bed layers (20 + 3 mm), a plastered one 13 mm
        bath = [w for w in self.els if w.kind == "wall" and any(s["finish_code"] == "marble-bath" for s in w.params["sides"].values())]
        self.assertTrue(bath)
        self.assertEqual(sorted(l["thickness_mm"] for l in bath[0].params["layers"] if l["function"] != "structure" and "marble" in l["material"] or l["material"] == "wall-tile-bed"), [3, 20])

    def test_ceilings_include_bulkheads_and_soffits(self):
        c = self.by["ceiling-lounge"].params
        self.assertEqual((c["ceiling_kind"], c["height_min_mm"], c["height_max_mm"]), ("cove", 2700.0, 2800.0))
        s = self.by["ceiling-cinema"].params
        self.assertEqual(s["ceiling_kind"], "soffit-lining")
        self.assertLess(s["height_min_mm"], 2300)                        # under the ramp
        self.assertEqual(self.by["ceiling-corridor"].params["height_mm"], 2700.0)
        self.assertEqual(self.by["floor-lounge"].params["area_m2"], self.by["room-lounge"].params["net_area_m2"])

    def test_every_typed_element_references_an_existing_type(self):
        types = {e.id for e in self.els if e.kind == "type"}
        for e in self.els:
            if e.kind in ("door", "window", "furniture", "luminaire"):
                self.assertIn(e.params["type_id"], types, e.id)
        t = self.by[self.by["door-GF-corridor-kids-a"].params["type_id"]]
        self.assertEqual(t.params["occurrences"], 3)                     # kids-a, kids-b and lounge/cinema: one 900 x 2100 hinged leaf
        self.assertEqual(sum(e.params["occurrences"] for e in self.els if e.kind == "type"),
                         sum(self.k[x] for x in ("door", "window", "furniture", "luminaire")))

    def test_every_door_decided_and_never_across_a_stair_landing(self):
        for d in (e for e in self.els if e.kind == "door"):
            p = d.params
            self.assertIn("handing", p, d.id)
            self.assertIn("judgement", p, d.id)
            if p["operation"] == "hinged":
                self.assertIn(p["hinge_side"], ("west", "east", "south", "north"), d.id)
                self.assertIn(p["handing"], ("LH", "RH"), d.id)
                self.assertNotIn(p["swing_into"], GD.STAIR_ZONE, d.id)
                self.assertTrue(p["swing_stair_clear"], d.id)
                self.assertEqual(len(p["hinge_xy_mm"]), 2)
        core = self.by["door-GF-landing-gf-core"].params
        self.assertEqual((core["swing_into"], core["hinge_side"]), ("core", "west"))      # authored G1 swing kept
        self.assertEqual(self.by["door-B-lounge-nook-pantry"].params["swing_into"], "lounge-nook")
        self.assertTrue(self.by["door-GF-corridor-parents-entry"].params["judgement"])    # pocket side not authored

    def test_sizes_have_a_basis_and_are_not_invented(self):
        for e in self.els:
            if e.kind in ("luminaire", "furniture", "plant"):
                self.assertTrue(e.params.get("size_basis"), e.id)
        self.assertEqual(self.by["lum-DL-lounge-01"].size[:2], (76.0, 76.0))
        self.assertIn("IES", self.by["lum-DL-lounge-01"].params["size_basis"])
        books = self.by["prop-lounge-books"]
        self.assertGreater(books.size[0], 100)
        self.assertIn("glTF", books.params["size_basis"])
        self.assertTrue(all(any(e.size) for e in self.els if e.kind == "luminaire" and e.product_id))
        gen = [e for e in self.els if e.kind == "luminaire" and not e.product_id and not any(e.size)]
        for e in gen:
            self.assertTrue(e.params["size_basis"].startswith("not derivable"), e.id)

    def test_guard_return_edge_has_a_position(self):
        g = self.by["rail-gf-stair-void"].params
        self.assertEqual(g["return_edge"]["start_mm"], [8887.0, -27471.0])
        self.assertEqual(g["return_edge"]["end_mm"], [8887.0, -28421.0])
        self.assertEqual(g["return_edge"]["along"], "y")
        self.assertEqual([p["guarded"] for p in g["void_perimeter"]], [True, True, False, False])

    def test_storeys_and_existing_columns(self):
        st = {e.id: e for e in self.els if e.kind == "storey"}
        self.assertEqual(set(st), {"storey-B", "storey-GF", "storey-L1", "storey-ROOF", "storey-roof-garden"})
        self.assertTrue(st["storey-L1"].params["context"])
        self.assertFalse(st["storey-GF"].params["context"])
        for c in (e for e in self.els if e.kind == "column"):
            self.assertIsInstance(c.params["existing_id"], int, c.id)

    def test_net_areas_from_walls_within_tolerance_of_frozen_revit(self):
        rows = {e.room: e.params for e in self.els if e.kind == "room"}
        dev = [abs(p["net_area_deviation_m2"]) for p in rows.values() if p["net_area_deviation_m2"] is not None]
        self.assertEqual(len(dev), 27)                                   # Revit read 27 of 30 rooms
        self.assertLessEqual(max(dev), GN.TOLERANCE_M2)
        for rid in ("store-ramp", "cinema", "parents-dressing-ext"):
            self.assertIsNone(rows[rid]["revit_net_area_m2"])
            self.assertGreater(rows[rid]["net_area_m2"], 0)

    def test_no_untracked_input_needed(self):
        old = os.environ.get("ARCHPIPE_REVIT_READBACK")
        os.environ["ARCHPIPE_REVIT_READBACK"] = "/nonexistent/readback.json"
        try:
            net = GN.net_areas(self.lay, self.sp, E.COLUMNS)
        finally:
            os.environ.pop("ARCHPIPE_REVIT_READBACK") if old is None else os.environ.update(ARCHPIPE_REVIT_READBACK=old)
        self.assertEqual(net["lounge"]["net_m2"], self.by["room-lounge"].params["net_area_m2"])


class FailLoudly(unittest.TestCase):
    def test_missing_frozen_reference_raises(self):
        old = GN.FROZEN
        GN.FROZEN = Path("/nonexistent/d1f-readback.json")
        try:
            with self.assertRaises(GN.NetAreaError):
                GN.frozen_reference()
        finally:
            GN.FROZEN = old

    def test_spec_without_walls_raises(self):
        with self.assertRaises(GN.NetAreaError):
            GN.net_areas(R.design("D1"), dict(walls=[]), E.COLUMNS)

    def test_existing_data_checked_against_manifest(self):
        self.assertEqual(GX.summary()["columns"], 15)
        d = Path(tempfile.mkdtemp())
        try:
            shutil.copytree(GX.DIR, d / "existing")
            (d / "existing" / "omar-wet.json").write_text('{"tampered": true}')
            old, GX.DIR = GX.DIR, d / "existing"
            GX._load.cache_clear(); GX.manifest.cache_clear()
            try:
                with self.assertRaises(GX.ExistingDataError):
                    GX.wet_probe()
                (d / "existing" / "omar-wet.json").unlink()
                GX._load.cache_clear()
                with self.assertRaises(GX.ExistingDataError):
                    GX.wet_probe()
            finally:
                GX.DIR = old
                GX._load.cache_clear(); GX.manifest.cache_clear()
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_missing_size_table_raises(self):
        old = GS.TABLE
        GS.TABLE = Path("/nonexistent/derived-sizes.json")
        try:
            with self.assertRaises(GS.SizeDataError):
                GS.table()
        finally:
            GS.TABLE = old

    def test_unmatched_kept_column_raises(self):
        from archpipe.contracts import DesignElement
        from archpipe.model import geometry_complete as GC
        bad = DesignElement(id="column-xx", kind="column", level="B", params=dict(x0_mm=0, y0_mm=0, x1_mm=360, y1_mm=510))
        with self.assertRaises(GX.ExistingDataError):
            GC.link_existing([bad])


class Rules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lay = R.design("D1")
        cls.sp = RS.build(cls.lay)
        cls.pre = RS._build(cls.lay)                                     # the spec before the join cleanup: a real reproduction

    def test_real_pre_fix_spec_has_five_corner_gaps_post_fix_has_none(self):
        pre = VR.joins(self.pre, E.COLUMNS)
        self.assertEqual(len(pre), 5)
        self.assertTrue(all("corner-only" in f["message"] for f in pre))
        self.assertEqual(VR.joins(self.sp, E.COLUMNS), [])
        self.assertEqual(len(self.sp["wall_joins_fixed"]), 4)

    def test_column_filled_corner_is_not_a_gap(self):
        # B-4 / B-16 meet inside the column at 14.9-15.4 m: stays unextended and unflagged
        ends = [(f["level"], f["end"]) for f in self.sp["wall_joins_fixed"]]
        self.assertNotIn(("B", [15.412, -23.691]), ends)
        self.assertEqual(VR.joins(self.sp, E.COLUMNS), [])

    def test_closure_flags_a_removed_wall(self):
        m = copy.deepcopy(self.sp)
        del m["walls"][12]                                               # B west wall of the lounge/pantry run
        f = VR.closure(self.lay, m, E.COLUMNS)
        self.assertTrue(f)
        self.assertTrue(all(x["rule"] == "closure" for x in f))
        self.assertEqual(VR.closure(self.lay, self.sp, E.COLUMNS), [])

    def test_overlap_flags_duplicate_wall(self):
        m = copy.deepcopy(self.sp)
        m["walls"].append(dict(m["walls"][5]))
        self.assertTrue(VR.overlaps(m))
        self.assertEqual(VR.overlaps(self.sp), [])

    def test_host_rules(self):
        els = model.load_json(api.snapshot_path("D1"))
        self.assertEqual(VR.hosts(els), [])
        door = next(e for e in els if e.id == "door-B-lounge-cinema")
        door.params["width_mm"] = 99999.0
        self.assertTrue(any("outside its host" in f["message"] for f in VR.hosts(els)))
        door.params["width_mm"] = 900.0
        door.host = ""
        self.assertTrue(any("no host" in f["message"] for f in VR.hosts(els)))
        win = next(e for e in els if e.kind == "window")
        win.params["height_mm"] = 99999.0
        self.assertTrue(any("above the host wall top" in f["message"] for f in VR.hosts(els)))

    def test_duplicate_ids_and_bad_type_ref(self):
        els = model.load_json(api.snapshot_path("D1"))
        els.append(copy.deepcopy(els[0]))
        self.assertTrue(any("duplicate id" in f["message"] for f in VR.ids(els)))
        next(e for e in els if e.kind == "door").params["type_id"] = "type-nope"
        self.assertTrue(any("type-nope" in f["message"] for f in VR.ids(els)))


class DoorRules(unittest.TestCase):
    def test_furniture_in_the_swing_flips_the_hinge_or_flags(self):
        from archpipe.contracts import DesignElement
        lay = R.design("D1")
        sp = RS.build(lay)
        base = GD.decide(sp, lay, [], E.COLUMNS)
        i = next(i for i, d in enumerate(sp["doors"]) if d["rooms"] == ["family", "guest-wc"])
        b = base[i]
        d = sp["doors"][i]
        # a cabinet exactly where that sector lies (in the swing room, beside the hinge)
        hx, hy = (v / 1000 for v in b["hinge_xy_mm"])
        n = b["swing_normal"]
        blocker = DesignElement(id="furn-test", kind="furniture", level="B",
                                placement=((hx + n[0] * 0.4) * 1000, (hy + n[1] * 0.4) * 1000, 0.0), size=(300.0, 300.0, 900.0))
        got = GD.decide(sp, lay, [blocker], E.COLUMNS)[i]
        self.assertTrue(got["hinge_side"] != b["hinge_side"] or got["swing_into"] != b["swing_into"] or got["judgement"])

    def test_stair_zone_is_never_a_swing_room(self):
        lay = R.design("D1")
        sp = RS.build(lay)
        for i, d in enumerate(sp["doors"]):
            r = GD.decide(sp, lay, [], E.COLUMNS)[i]
            if r["operation"] == "hinged":
                self.assertNotIn(r["swing_into"], GD.STAIR_ZONE)
