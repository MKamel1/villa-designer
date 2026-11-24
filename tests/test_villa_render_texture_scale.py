"""RF defect 1 guard: stone/veneer textures are mapped at a bounded real-world size and keep a minimum texel density."""
import os
import unittest
from pathlib import Path

from archpipe.concept import villa_render as VR

LIB = Path(os.environ.get("ARCHPIPE_LIBRARY", Path.home() / "archpipe/assets/library")) / "materials"
STONE = ("travertine", "marble-")
VENEER = ("walnut", "oak", "door-oak")      # teak is the garden lounge (lane GI)
MIN_TEXELS_PER_M = 1000       # 1 mm texel; ASSUMED policy
PRODUCT_MIN_TEXELS_PER_M = 400   # 2.5 mm texel: a large-format product (2.35 m plank, 3.27 m slab) maps ONE scan per format unit


def product_derived(spec):
    """Finishes from the client's chosen schedule: their scale is the PRODUCT's format, not RF's assumed 0.6-0.7 m policy."""
    return str(spec.get("note", "")).startswith("LOOK-ALIKE")


def _klass(name):
    if name == "oak-floor" or "outdoor" in name:
        return None
    if name.startswith(STONE):
        return "stone"
    if name.startswith(VENEER):
        return "veneer"
    return None


def over_scaled(materials):
    """(name, tile_m, limit) for every stone/veneer material mapped wider than its class limit."""
    out = []
    for name, spec in materials.items():
        k = _klass(name)
        if k and spec.get("asset") and not product_derived(spec) and spec["tile_m"] > VR.TEXTURE_FIGURE_MAX_M[k]:
            out.append((name, spec["tile_m"], VR.TEXTURE_FIGURE_MAX_M[k]))
    return out


class TextureScale(unittest.TestCase):
    def test_materials_within_limit(self):
        self.assertEqual(over_scaled(VR.M), [])

    def test_product_scale_is_not_held_to_the_assumed_limit_but_must_equal_the_product_format(self):
        from archpipe.interior import chosen as CH, finishes
        ch = CH.load()
        for sid, slot in ch["slots"].items():
            if not slot.get("render") or not slot["render"].get("asset"):
                continue
            want = finishes.texture_scale_m(slot["item"])[0]
            for name in slot["scene_materials"]:
                self.assertTrue(product_derived(VR.M[name]), name)
                self.assertAlmostEqual(VR.M[name]["tile_m"], round(want, 4), msg=name)
        # negative: an over-wide ASSUMED material (no product behind it) is still flagged
        self.assertEqual([n for n, *_ in over_scaled({"marble-x": dict(asset="Marble014", tile_m=1.2, note="ASSUMED")})], ["marble-x"])

    def test_the_draft_values_are_caught(self):          # negative: the L9P draft's real values
        draft = {"marble-bath": dict(asset="Marble014", tile_m=1.2), "door-oak": dict(asset="oak_veneer_01", tile_m=1.83)}
        self.assertEqual([n for n, *_ in over_scaled(draft)], ["marble-bath", "door-oak"])

    def test_floor_planks_not_flagged(self):              # stays quiet when it should
        self.assertEqual(over_scaled({"oak-floor": dict(asset="oak_wood_planks", tile_m=1.2)}), [])

    @unittest.skipUnless(LIB.is_dir(), "render library not on this host")
    def test_texel_density(self):
        from PIL import Image
        low = []
        for name, spec in VR.M.items():
            if spec.get("asset") and spec.get("tile_m") and (LIB / spec["asset"]).is_dir():
                col = next((f for f in (LIB / spec["asset"]).iterdir() if "_Color" in f.name), None)
                if col:
                    px = Image.open(col).size[0] / spec["tile_m"]
                    if px < (PRODUCT_MIN_TEXELS_PER_M if product_derived(spec) else MIN_TEXELS_PER_M):
                        low.append((name, round(px)))
        self.assertEqual(low, [])


if __name__ == "__main__":
    unittest.main()
