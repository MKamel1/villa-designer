"""The pass registry: every record resolves, knowledge files exist, order is the one build() has always used."""
import importlib
import unittest
from pathlib import Path

from archpipe.model import passes as P


class PassRegistry(unittest.TestCase):
    def test_every_call_resolves_to_a_function(self):
        for p in P.PASSES:
            mod, fn = p.call.split(":")
            self.assertTrue(callable(getattr(importlib.import_module("archpipe." + mod), fn)), p.id)

    def test_knowledge_files_exist(self):
        for p in P.PASSES:
            for k in p.knowledge:
                self.assertTrue((P.ROOT / "knowledge" / k).is_file(), f"{p.id}: {k}")

    def test_ids_unique_and_stages(self):
        ids = [p.id for p in P.PASSES]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual({p.stage for p in P.PASSES}, {"mounting", "assembly", "furniture"})

    def test_mounting_order_is_the_historic_one(self):
        self.assertEqual([p.id for p in P.stage("mounting")], [
            "c4-fitting-migrate", "c4-bc-approvals", "c4-guest-fixes", "c4-vanity-emitters", "c4-ceiling-migrate",
            "c4-d-lead-approvals", "garden-g6-mount", "c4-support-migrate", "c4-e-lead-review", "c4-final-mounting",
            "wc-slides", "sanitary-family", "vanity-decision"])

    def test_run_stage_threads_scene_and_context(self):
        calls = []
        import types, sys
        mod = types.ModuleType("archpipe.fake_pass_mod")
        mod.a = lambda scene, lay: calls.append(("a", scene["n"], lay)) or None
        mod.b = lambda scene: dict(scene, n=scene["n"] + 1)
        sys.modules["archpipe.fake_pass_mod"] = mod
        orig = P.PASSES
        try:
            P.PASSES = (P.Pass("a", "t", "fake_pass_mod:a", ("scene", "lay")),
                        P.Pass("b", "t", "fake_pass_mod:b", ("scene",), returns_scene=True))
            out = P.run_stage("t", {"n": 1}, {"lay": "L"})
        finally:
            P.PASSES = orig
            del sys.modules["archpipe.fake_pass_mod"]
        self.assertEqual(calls, [("a", 1, "L")])
        self.assertEqual(out["n"], 2)


if __name__ == "__main__":
    unittest.main()
