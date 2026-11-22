"""Positive and negative tests for the landscape critics. Negative = the check stays quiet on the clean reference scheme."""
import json
import unittest
from pathlib import Path

from archpipe.landscape import critic as K
from archpipe.landscape.critic import computed as C, seeds, seeds_heldout as H, site as S
from archpipe.landscape.critic.common import KNOW


def st(findings):
    rank = {"fail": 3, "warn": 2, "not_evaluated": 1, "pass": 0}
    t = {}
    for f in findings:
        if f.criterion not in t or rank[f.status] > rank[t[f.criterion]]: t[f.criterion] = f.status
    return t


BASE = seeds.base()
BASE_T = st(K.critique(BASE))


class BaseIsQuiet(unittest.TestCase):          # negative tests: the reference scheme must not trip the defect-targeted criteria
    def test_no_target_criterion_fails_on_base(self):
        targets = {e for _, (_, ex) in seeds.DEFECTS.items() for e in ex} | {e for _, (_, ex) in H.HELD.items() for e in ex}
        bad = {c: BASE_T.get(c) for c in targets if BASE_T.get(c) in ("fail", "warn")}
        self.assertEqual(bad, {})


class Seeded(unittest.TestCase):               # positive tests: every seeded defect trips its named criterion
    def test_set1(self):
        for k, (_, expect) in seeds.DEFECTS.items():
            t = st(K.critique(seeds.make(k)))
            for e in expect: self.assertIn(t.get(e), ("fail", "warn"), f"{k}: {e}")

    def test_not_viable_seed_fails_loudly_without_species(self):
        from unittest import mock
        with mock.patch.object(seeds, "plants_db", return_value={"a": {"site_viability": {"verdict": "viable"}}}):
            with self.assertRaises(RuntimeError): seeds._not_viable_species()

    def test_set2_report_only(self):                # held-out set: misses are reported in calibration.json, not asserted
        for k in H.HELD: self.assertTrue(H.make(k)["seeded_defect"]["expect"])


class D1(unittest.TestCase):
    def test_d1_fails_blocking_critics(self):
        d1 = json.loads((KNOW / "critic/d1-layout.json").read_text())
        v = K.verdict(K.critique(d1))
        self.assertEqual(v["user"], "fail"); self.assertEqual(v["horticulturist"], "fail"); self.assertEqual(v["climate"], "fail")


class Site(unittest.TestCase):
    def test_sunken_garden_has_no_summer_evening_sun(self):     # LDS fact the critics rely on
        self.assertLess(S.sample("sun.json", "summer_evening_17_20_dst_clock", (24.5, -26.0)), 0.5)

    def test_screen_blocks_sightline(self):
        pt = (24.0, -28.0)
        raw = S.overlook({"screens": []}, pt)[0]
        lay = {"screens": [{"id": "s", "kind": "hedge", "rect": [22.6, -29.9, 28.3, -29.5], "height_m": 2.4, "opacity": 0.9}], "walls": []}
        self.assertLess(S.overlook(lay, pt)[0], raw)

    def test_evergreen_crown_reduces_winter_sun(self):
        lay = seeds.make("evergreen-over-lounge")
        a = S.sun_hours(lay, (24.55, -27.0), "winter"); self.assertLess(a[0], a[1])


class Findings(unittest.TestCase):
    def test_fields_and_not_evaluated(self):
        for f in K.critique(BASE):
            self.assertIn(f.status, ("pass", "fail", "warn", "not_evaluated")); self.assertTrue(f.source); self.assertTrue(f.evidence)
        # no fire pit -> wind check is not_evaluated, never pass
        lay = seeds.make("no-quiet"); lay["features"] = [f for f in lay["features"] if f["kind"] != "firepit"]
        self.assertEqual(st(K.critique(lay))["C-FIRE-WIND"], "not_evaluated")

    def test_calibrated_flag_comes_from_the_table(self):
        cal = json.loads((KNOW / "critic/calibration.json").read_text())["criteria"]
        for f in K.critique(BASE): self.assertEqual(f.calibrated, bool(cal.get(f.criterion, {}).get("calibrated", False)))


class Plan(unittest.TestCase):
    def test_renders_fixed_width(self):
        import tempfile
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            for lay, view in ((BASE, [14, -31, 29.5, -19.5]), (json.loads((KNOW / "critic/precedent-layouts/P-SME-08.json").read_text()), None)):
                p = K.plan_png(lay, str(Path(d) / "p.png"), view=view)
                w, h = Image.open(p).size
                self.assertGreater(w, 1000); self.assertGreater(h, 400)


if __name__ == "__main__":
    unittest.main()


class PlanStandard(unittest.TestCase):
    def test_sheet_width_and_style(self):
        import struct, tempfile
        self.assertEqual(K.STYLE_VERSION, "ldc-plan-style/2")
        for lay in (seeds.make("capacity-4"), json.loads((KNOW / "critic/d1-layout.json").read_text())):
            with tempfile.TemporaryDirectory() as d:
                p = K.plan_png(lay, str(Path(d) / "p.png"))
                w = struct.unpack(">I", Path(p).read_bytes()[16:20])[0]
                self.assertEqual(w, 1600)

    def test_empty_layout_draws_without_planting_key(self):      # negative: nothing to key, nothing invented
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(Path(K.plan_png({"schema": "landscape-layout/1", "zones": []}, str(Path(d) / "e.png"))).exists())


class Massing(unittest.TestCase):          # the spec builder is pure; the Blender run is exercised by hand through jobq
    def test_tree_at_mature_size_and_pergola(self):
        from archpipe.landscape.critic.massing import build_spec
        lay = {"zones": [], "trees": [{"id": "t", "species": "Punica granatum", "center": [5, 5], "form": "small_tree", "mature_spread_m": 3.0, "mature_height_m": 3.7}],
               "canopies": [{"id": "p", "kind": "pergola", "rect": [0, 0, 4, 2], "height_m": 3.0}], "buildings": [[10, 0, 14, 4]]}
        sp = build_spec(lay)
        e = [s for s in sp["solids"] if s["kind"] == "ellipsoid"]
        self.assertEqual(len(e), 1); self.assertAlmostEqual(e[0]["rx"], 1.5)
        self.assertEqual(sum(1 for s in sp["solids"] if s["kind"] == "box" and s["z1"] == 3.0), 4)       # 4 pergola posts
        self.assertTrue(any(s["mat"] == "house" for s in sp["solids"]))

    def test_no_planting_no_volumes(self):                      # negative: nothing to model, nothing invented
        from archpipe.landscape.critic.massing import build_spec
        sp = build_spec({"zones": [{"id": "z", "rect": [0, 0, 5, 5], "use": "lounge"}]})
        self.assertFalse([s for s in sp["solids"] if s["kind"] in ("ellipsoid", "cylinder")])
