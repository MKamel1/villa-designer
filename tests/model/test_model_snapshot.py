"""The committed model snapshot (src/archpipe/model/data/d1-elements.json) against live source data.

Fast checks only. Regenerating the slow sources (lighting, garden plan: minutes) is `python -m archpipe.model.export
--snapshot`; set ARCHPIPE_SLOW=1 to have this file re-derive luminaires and compare them with the snapshot.
"""
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
        self.assertEqual((k["room"], k["wall"], k["door"], k["window"], k["stair"]), (30, 36, 18, 8, 1))
        self.assertEqual((k["column"], k["beam"], k["slab"], k["railing"]), (9, 24, 3, 5))
        self.assertEqual(k["luminaire"], 142)
        self.assertEqual(k["plant"], 80)
        self.assertGreaterEqual(k["furniture"], 52)

    def test_spec_kinds_equal_a_fresh_derivation(self):
        fresh = {e.id: asdict(e) for e in S.all_from_spec(self.lay, self.sp, finish=_finish())}
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
        self.assertGreater(len(with_ies), 80)
        for e in with_ies:
            self.assertFalse(e.params["photometry"]["ies"].startswith(("C:", "/", "\\")), e.id)
            self.assertTrue(e.params["photometry"]["ies"].endswith(".ies"))
            self.assertIn("/", e.product_id)
        for e in lums:
            self.assertGreater(e.params["flux_lm"], 0, e.id)

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


def _norm(d):
    import json
    return json.loads(json.dumps(d, default=list))


if __name__ == "__main__":
    unittest.main()
