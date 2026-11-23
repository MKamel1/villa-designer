"""Generated foliage (lane FG): determinism, sourced habit, no dead leaves, honest labels, negative cases."""
import copy
import functools
import json
import unittest

import numpy as np

from archpipe.landscape.foliage import generate as G
from archpipe.landscape.foliage import library as L
from archpipe.landscape.foliage.species import SPECS, sourced_ranges

SIZE = {s: L.DEMO.get(s) or G.default_size(s) for s in SPECS}


@functools.lru_cache(maxsize=None)
def _gen(slug, seed, h, s, state, lod):
    return G.generate(slug, seed, h, s, state, lod)


def _plant(slug, seed=1, state="leaf-on", lod=0):
    h, s = SIZE[slug]
    return _gen(slug, seed, h, s, state, lod)


class Determinism(unittest.TestCase):
    def test_same_seed_identical_other_seed_differs(self):
        for slug in ("justicia_brandegeeana", "acorus_gramineus", "lagerstroemia_indica", "vitis_vinifera"):
            a, b, c = _plant(slug, 5), _plant(slug, 5), _plant(slug, 6)
            self.assertEqual(a.digest(), b.digest(), slug)
            self.assertNotEqual(a.digest(), c.digest(), slug)

    def test_library_seed_is_stable_by_element_id(self):
        self.assertEqual(L.seed_of("s-bed-mass#3"), L.seed_of("s-bed-mass#3"))
        self.assertNotEqual(L.seed_of("a"), L.seed_of("b"))


class Habit(unittest.TestCase):
    def test_size_within_sourced_ranges_and_matches_target(self):
        """Target sizes sit in the sourced range (a GAP is skipped) and the built bounding box matches the target."""
        for slug in SPECS:
            p = _plant(slug)
            lo, hi = p.bbox()
            ext = hi - lo
            h_t, s_t = SIZE[slug]
            self.assertAlmostEqual(ext[2], h_t, delta=0.12 * h_t, msg=slug + " height")
            spread = ext[0] if SPECS[slug]["form"] == "climber" else max(ext[0], ext[1])
            self.assertAlmostEqual(spread, s_t, delta=0.18 * s_t, msg=slug + " spread")
            r = sourced_ranges(slug)
            for key, val in (("height", ext[2]), ("spread", spread)):
                if r[key] and slug not in ("jasminum_sambac", "petrea_volubilis", "vitis_vinifera", "trachelospermum_jasminoides"):   # climbers are sized to the trellis, not to the free-standing range
                    self.assertGreaterEqual(val, r[key][0] * 0.88, "%s %s below sourced" % (slug, key))
                    self.assertLessEqual(val, r[key][1] * 1.12, "%s %s above sourced" % (slug, key))

    def test_plant_stands_on_the_ground(self):
        for slug in SPECS:
            lo, _ = _plant(slug).bbox()
            self.assertAlmostEqual(lo[2], 0.0, delta=0.02, msg=slug)

    def test_branches_are_not_straight_radial_twigs(self):
        """The LDL prototype's defect: straight twigs. Every grown axis must curve, taper and vary in direction."""
        for slug in ("justicia_brandegeeana", "salvia_leucantha", "lagerstroemia_indica"):
            p = _plant(slug)
            tort, taper, dirs = [], [], []
            for b in p.branches:
                pts = b["pts"]
                if len(pts) < 5:
                    continue
                path = np.linalg.norm(np.diff(pts, axis=0), axis=1).sum()
                tort.append(path / np.linalg.norm(pts[-1] - pts[0]))
                taper.append(b["radii"][0] / b["radii"][-1])
                d = pts[-1] - pts[0]; dirs.append(d / np.linalg.norm(d))
            self.assertGreater(np.mean(tort), 1.02, slug + " twigs are straight")
            self.assertGreater(np.mean(taper), 1.5, slug + " no taper")
            self.assertGreater(np.std(np.array(dirs), axis=0).sum(), 0.4, slug + " all branches point the same way")

    def test_tree_leaf_states_share_one_skeleton(self):
        on, off = _plant("lagerstroemia_indica", state="leaf-on"), _plant("lagerstroemia_indica", state="leaf-off")
        self.assertGreater(len(on.leaves["length"]), 8000)
        self.assertEqual(len(off.leaves["length"]), 0)
        self.assertEqual(len(on.branches), len(off.branches))
        self.assertTrue(np.allclose(on.branches[3]["pts"], off.branches[3]["pts"], atol=0.05))

    def test_lod_thins_leaves(self):
        self.assertLess(len(_plant("justicia_brandegeeana", lod=2).leaves["length"]), len(_plant("justicia_brandegeeana").leaves["length"]) * 0.5)


class LeafBanks(unittest.TestCase):
    def test_no_dead_or_white_leaf_cards(self):
        """Dead leaves (brown: G/R < 1) and petals are filtered; the star jasmine atlas holds 5 dead leaves (the LDL defect)."""
        for name, bank in G.BANKS.items():
            for lf in bank["leaves"]:
                self.assertGreaterEqual(lf["g_over_r"], 1.0, "%s has a dead-leaf card" % name)
        self.assertEqual(G.BANKS["star_jasmine"]["dropped"]["dead_or_white"], 5)
        self.assertEqual(len(G.BANKS["star_jasmine"]["leaves"]), 15)

    def test_every_leaf_card_references_a_real_bank_leaf(self):
        for slug in SPECS:
            p = _plant(slug)
            for bank, idx in zip(p.leaves["bank"], p.leaves["leaf"]):
                self.assertLess(idx, len(G.BANKS[bank]["leaves"]))

    def test_cards_are_not_degenerate(self):
        for slug in SPECS:
            p = _plant(slug)
            self.assertTrue((p.leaves["length"] > 0).all() and (p.leaves["width"] > 0).all(), slug)
            self.assertTrue(np.isfinite(p.leaves["base"]).all(), slug)


class Labels(unittest.TestCase):
    def test_every_species_has_complete_valid_label(self):
        for slug in SPECS:
            lab = _plant(slug).label
            self.assertTrue(L.validate_label(lab), slug)
            self.assertEqual(lab["generator_version"], G.VERSION)
            self.assertIn(lab["fidelity"], ("species", "form-class"))
            self.assertEqual(lab["construction"], "generated")

    def test_only_the_species_whose_scan_it_is_is_species_fidelity(self):
        fid = {s: _plant(s).label["fidelity"] for s in SPECS}
        self.assertEqual(fid["trachelospermum_jasminoides"], "species")        # star jasmine scan
        for s in SPECS:
            if s != "trachelospermum_jasminoides":
                self.assertEqual(fid[s], "form-class", s)                      # no scan of that species is held

    def test_form_class_plant_claiming_species_fails(self):
        """NEGATIVE: a form-class plant relabelled 'species' must be refused (the honesty guard)."""
        lab = copy.deepcopy(_plant("jasminum_sambac").label)
        lab["fidelity"] = "species"
        with self.assertRaises(L.LabelError):
            L.validate_label(lab)

    def test_generated_outline_is_never_species_fidelity(self):
        """NEGATIVE: Fatsia/grape leaf outlines are ours; even a label naming the right species must not pass as species."""
        lab = copy.deepcopy(_plant("fatsia_japonica").label)
        lab["fidelity"] = "species"
        with self.assertRaises(L.LabelError):
            L.validate_label(lab)

    def test_missing_field_fails_and_caption_is_honest(self):
        lab = copy.deepcopy(_plant("acorus_gramineus").label); del lab["seed"]
        with self.assertRaises(L.LabelError):
            L.validate_label(lab)
        c = L.caption(_plant("acorus_gramineus").label, close_up=True)
        self.assertIn("form-class", c); self.assertIn("not the species", c)
        self.assertNotIn("generated from a leaf scan of the species", c)

    def test_species_plant_passes_quietly(self):
        """POSITIVE counterpart: the genuinely species-faithful plant is not refused."""
        self.assertIn("leaf scan of the species", L.caption(_plant("trachelospermum_jasminoides").label))

    def test_schedule_lists_fidelity_for_every_generated_species_in_layout(self):
        rows = {r["species"]: r for r in L.schedule(grades={})}
        for s in ("jasminum_sambac", "justicia_brandegeeana", "salvia_leucantha", "petrea_volubilis", "vitis_vinifera", "fatsia_japonica", "farfugium_japonicum", "acorus_gramineus", "lagerstroemia_indica"):
            self.assertIn(s, rows)
            self.assertTrue(rows[s]["in_layout"] and rows[s]["count"] >= 1)
            self.assertIn(rows[s]["fidelity"], ("species", "form-class"))
            self.assertTrue(rows[s]["caption"])


if __name__ == "__main__":
    unittest.main()
