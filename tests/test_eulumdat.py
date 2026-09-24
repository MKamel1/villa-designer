"""EULUMDAT reader: every symmetry form of one known distribution must agree,
flux must integrate to LORL, and the IES written from it must be read back
identically. The real manufacturer pair (LDT + the manufacturer's own IES)
runs when the local library holds it; manufacturer files are not committed.
"""
import glob
import math
import os
import unittest
from pathlib import Path

from archpipe import photometry as ph
from archpipe.luminaires import eulumdat as eu

ROOT = Path(__file__).resolve().parents[1]
REAL = ROOT / "assets/user/luminaires/_reference/signify-911401840687"


def dist(c, g):
    """cd/klm: cosine lobe, stronger toward C0 (mirror-symmetric about C0-C180 only)."""
    if g > 90:
        return 0.0
    return 1000.0 / math.pi * math.cos(math.radians(g)) * (1.0 + 0.3 * math.cos(math.radians(c)))


def ldt_text(isym, mc=24, ng=19, lamp_sets=((1, "LED", 2000.0, "3000", "90", 20.0),),
             lum=(600.0, 100.0), fn=dist):
    dc, dg = 360.0 / mc, 180.0 / (ng - 1)
    cs = [i * dc for i in range(mc)]
    gs = [i * dg for i in range(ng)]
    first, count = eu._planes_stored(isym, mc)
    stored = [cs[(first + k) % mc] for k in range(count)]
    head = ["test/archpipe", "1", str(isym), str(mc), f"{dc}", str(ng), f"{dg}", "R1", "Test lum",
            "T-001", "t.ldt", "2026-09-24", "620", "120", "40", f"{lum[0]}", f"{lum[1]}", "0", "0", "0", "0",
            "100", "100", "1.0", "0", str(len(lamp_sets))]
    for n, t, f, k, r, w in lamp_sets:
        head += [str(n), t, f"{f}", k, r, f"{w}"]
    head += ["0.5"] * 10 + [f"{c}" for c in cs] + [f"{g}" for g in gs]
    for c in stored:
        head += [f"{fn(c, g):.4f}" for g in gs]
    return "\n".join(head) + "\n"


class EulumdatTests(unittest.TestCase):
    def test_every_symmetry_form_agrees_and_integrates_to_lorl(self):
        full = eu.parse(ldt_text(0))
        self.assertAlmostEqual(full.integrated_rel_flux(), 1000.0, delta=15)   # cosine lobe, mean(1+0.3cosC)=1
        for isym in (2,):   # the only other form this distribution is valid in
            other = eu.parse(ldt_text(isym))
            for c in range(0, 360, 15):
                for g in (0, 30, 60, 85):
                    self.assertAlmostEqual(other.intensity_rel(c, g), full.intensity_rel(c, g), places=6)

    def test_round_and_quadrant_forms(self):
        rnd = lambda c, g: dist(0, g) / 1.3                   # no C dependence
        for isym in (1, 3, 4):
            f = eu.parse(ldt_text(isym, fn=rnd))
            self.assertAlmostEqual(f.intensity_rel(123, 40), rnd(0, 40), places=4)
            self.assertAlmostEqual(f.integrated_rel_flux(), 1000.0, delta=15)   # dist(0,g)/1.3 is the plain cosine lobe

    def test_absolute_candela_scales_with_each_lamp_set(self):
        f = eu.parse(ldt_text(0, lamp_sets=((1, "A", 1000.0, "2700", "90", 10.0),
                                             (1, "B", 3000.0, "3000", "80", 25.0))))
        a, b = f.to_photometry(0), f.to_photometry(1)
        self.assertAlmostEqual(b.intensity(0, 0) / a.intensity(0, 0), 3.0, places=6)
        self.assertEqual((f.lamp_sets[1].cct_k, f.lamp_sets[1].cri_ra, f.lamp_sets[1].watts), (3000.0, 80.0, 25.0))

    def test_ies_axis_is_c_plus_90_and_survives_round_trip(self):
        f = eu.parse(ldt_text(0))
        p = ph.parse(f.to_ies_text(0))
        for h in (0, 45, 90, 180, 270):
            self.assertAlmostEqual(p.intensity(30, h), f.intensity_rel(h + 90, 30) * 2.0, delta=0.05)
        self.assertEqual(p.luminous_dimensions_m()[:2], (0.1, 0.6))

    def test_round_opening_is_negative_in_ies(self):
        f = eu.parse(ldt_text(1, fn=lambda c, g: dist(0, g), lum=(150.0, 0.0)))
        self.assertEqual(f.to_photometry(0).width, -0.15)

    def test_corrupt_files_fail_with_a_reason(self):
        good = ldt_text(0).split("\n")
        with self.assertRaisesRegex(eu.LDTError, "symmetry"):
            eu.parse("\n".join(good[:2] + ["7"] + good[3:]))
        with self.assertRaisesRegex(eu.LDTError, "needs"):
            eu.parse("\n".join(good[:-40]))                 # truncated table
        with self.assertRaisesRegex(eu.LDTError, "lines"):
            eu.parse("IESNA:LM-63-2002\nTILT=NONE\n")

    @unittest.skipUnless(REAL.is_dir(), "manufacturer reference pair not in the local library")
    def test_real_manufacturer_pair_agrees(self):
        """Signify 911401840687: LDT converted here vs Signify's own IES, all lamp sets."""
        ldt = eu.load(next(REAL.glob("*.ldt")))
        self.assertAlmostEqual(ldt.integrated_rel_flux(), ldt.lorl * 10, delta=5)
        for k, ies_path in enumerate(sorted(REAL.glob("*_[0-9].ies"))):
            ies, conv = ph.load(ies_path), ph.parse(ldt.to_ies_text(k))
            worst = max(abs(ies.intensity(g, h) - conv.intensity(g, h)) / max(ies.intensity(g, h), conv.intensity(g, h))
                        for g in range(0, 91, 2) for h in range(0, 360, 10)
                        if max(ies.intensity(g, h), conv.intensity(g, h)) > 0.02 * ies.peak_candela)
            self.assertLess(worst, 0.001, ies_path.name)


if __name__ == "__main__":
    unittest.main()
