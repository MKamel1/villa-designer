"""Lane SC3: a pendant's rendered body matches its product's published dimensions (+-5 mm).

The published size is read from the product's own LDT header (luminaire length/diameter, width, height, mm) in
knowledge/lighting-products, never from the renderer's constants."""
import unittest
from pathlib import Path

import numpy as np

from archpipe.concept import villa_render as VR
from archpipe.fixture_record import PRODUCT_CHOICE

PRODUCTS = Path(__file__).resolve().parents[1] / "knowledge/lighting-products"
TOL_MM = 5.0


def ldt_size_mm(maker, code):
    """(length or diameter, width, height) in mm from the LDT header; None when the product has no LDT."""
    f = PRODUCTS / maker.lower() / code / f"{code}.ldt"
    if not f.exists():
        return None
    v = [x.strip() for x in f.read_text(errors="replace").splitlines()]
    return float(v[12]), float(v[13]), float(v[14])        # LDT lines 13-15: length/diameter, width, height


def body_size_mm(mesh):
    p = np.array([q for f in mesh["faces"] for q in f]) * 1000
    return p.max(0) - p.min(0)


class PendantBodies(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scene = VR.build(views=[])
        cls.meshes = {m["id"]: m for m in cls.scene["meshes"]}

    def test_every_pendant_body_matches_its_products_published_size(self):
        checked = []
        for mid, body in self.meshes.items():
            if not mid.startswith("lamp-body-PEN-"):
                continue
            kind = "-".join(mid.removeprefix("lamp-body-").split("-")[:2])      # PEN-LIN
            maker, code, _ = PRODUCT_CHOICE[kind]
            size = ldt_size_mm(maker, code)
            self.assertIsNotNone(size, "%s: product %s has no LDT with a published size" % (mid, code))
            dx, dy, dz = body_size_mm(body)
            dia, wid, h = size
            want, got = sorted([dia, wid or dia]), sorted([dx, dy])
            self.assertTrue(all(abs(a - b) <= TOL_MM for a, b in zip(want, got)) and abs(dz - h) <= TOL_MM,
                            "%s %s: drawn %.0f x %.0f x %.0f mm, published %.0f x %.0f x %.0f mm"
                            % (mid, code, dx, dy, dz, dia, wid or dia, h))
            checked.append(mid)
        self.assertIn("lamp-body-PEN-LIN-dining-01", checked)           # the QA03 over the dining table is really read

    def test_negative_the_comparison_fails_on_the_pre_sc3_body(self):
        # the same check on a 59 x 59 x 60 mm body (what the scene drew before SC3) must fail
        size = ldt_size_mm("iguzzini", "QA03")
        self.assertEqual(size, (59.0, 0.0, 250.0))
        self.assertGreater(abs(60.0 - size[2]), TOL_MM)

    def test_the_suspension_reaches_the_ceiling_from_the_top_of_the_body(self):
        body = self.meshes["lamp-body-PEN-LIN-dining-01"]
        top = max(q[2] for f in body["faces"] for q in f)
        for s in (-1, 1):
            wire = self.meshes["wire-PEN-LIN-dining-01-%d" % s]
            lo = min(q[2] for f in wire["faces"] for q in f)
            self.assertAlmostEqual(lo, top, places=3)


if __name__ == "__main__":
    unittest.main()
