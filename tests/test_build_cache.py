"""Build-local derived data must follow values and remain independent for callers."""
import copy
import time
import unittest
from unittest.mock import patch

from archpipe.concept import revit_spec as RS, villa_furnish as F, villa_r11 as R
from archpipe.concept.build_cache import scope
from archpipe.concept import villa_render as VR


class BuildCache(unittest.TestCase):
    def test_full_villa_build_time_budget(self):
        # Set from the measured clean build after the cache correction. This
        # remains a real full view search, rather than an empty-view shortcut.
        start = time.perf_counter()
        counts = {"layout": 0, "spec": 0}
        original_layout, original_spec = F._layout, RS._build

        def layout(*args, **kwargs):
            counts["layout"] += 1
            return original_layout(*args, **kwargs)

        def spec(*args, **kwargs):
            counts["spec"] += 1
            return original_spec(*args, **kwargs)

        with patch.object(F, "_layout", layout), patch.object(RS, "_build", spec):
            scene = VR.build()
        elapsed = time.perf_counter() - start
        self.assertTrue(scene["views"])
        self.assertLessEqual(counts["layout"], 2, counts)
        self.assertEqual(counts["spec"], 1, counts)
        self.assertLess(elapsed, 120.0, "full villa build took %.1f s" % elapsed)

    def test_real_layout_and_spec_recompute_after_input_mutation(self):
        lay = R.design("D1")
        with scope():
            before = F.layout(lay, products=False)
            spec = RS.build(lay)
            before[0]["cx"] = -999
            spec["title"] = "changed by caller"
            self.assertNotEqual(F.layout(lay, products=False)[0]["cx"], -999)
            self.assertEqual(RS.build(lay)["title"], lay["title"])

            # The real lounge's north edge affects the TV wall location.
            old = lay["rooms"]["lounge"]["rect"]
            lay["rooms"]["lounge"]["rect"] = tuple(old[:3]) + (old[3] - 0.01,)
            changed = F.layout(lay, products=False)
            a = next(i for i in before if i["id"] == "lounge-tv")
            b = next(i for i in changed if i["id"] == "lounge-tv")
            self.assertNotEqual(a["cy"], b["cy"])

    def test_scope_does_not_survive_next_build(self):
        lay = R.design("D1")
        with scope():
            first = RS.build(lay)
        with scope():
            second = RS.build(copy.deepcopy(lay))
        self.assertEqual(first, second)
        self.assertIsNot(first, second)

    def test_changed_product_record_invalidates_layout(self):
        lay = R.design("D1")
        product = F.PRODUCT["living-chair-1"]
        original = copy.deepcopy(product)
        calls = 0
        real_layout = F._layout

        def counted(*args, **kwargs):
            nonlocal calls
            if len(args) > 1 and args[1]:
                calls += 1
            return real_layout(*args, **kwargs)

        try:
            with patch.object(F, "_layout", counted), scope():
                F.layout(lay, products=True)
                product["w"] += 0.05
                F.layout(lay, products=True)
            self.assertEqual(calls, 2)
        finally:
            product.clear()
            product.update(original)
