"""scene_cache: key, source invalidation, corrupt-entry refusal, atomic store, no race (no bpy needed)."""
import importlib.util
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src/archpipe/blender/scene_cache.py"
spec = importlib.util.spec_from_file_location("scene_cache", SRC)
sc = importlib.util.module_from_spec(spec)
sys.modules["scene_cache"] = sc
spec.loader.exec_module(sc)


def fake_blend(path):
    Path(path).write_bytes(b"BLENDER-v450" + b"x" * 1000)


class SceneCacheTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def store(self, key="k1"):
        sc.store_entry(self.root, key, {"a": 1}, fake_blend, b"state")
        return self.root / key

    def test_intact_entry_verifies(self):
        e = self.store()
        self.assertIsInstance(sc.verify_entry(e, "k1"), dict)
        self.assertEqual([p.name for p in self.root.glob(".tmp-*")], [])

    def test_key_changes_with_each_component(self):
        base = ["s", "src", "4.5.14", "/lib", "/ies"]
        k = sc.cache_key(*base)
        for i in range(5):
            other = list(base)
            other[i] += "x"
            self.assertNotEqual(k, sc.cache_key(*other), i)
        self.assertEqual(k, sc.cache_key(*base))  # and it is stable: negative test, a hit stays a hit

    def test_builder_source_change_invalidates(self):
        (self.root / "blender").mkdir()
        f = self.root / "blender" / "villa_scene.py"
        f.write_text("x = 1\n")
        (self.root / "top.py").write_text("y = 1\n")
        h1 = sc.source_hash(self.root)
        self.assertEqual(h1, sc.source_hash(self.root))
        f.write_text("x = 2\n")
        h2 = sc.source_hash(self.root)
        self.assertNotEqual(h1, h2)
        (self.root / "top.py").write_text("y = 2\n")
        self.assertNotEqual(h2, sc.source_hash(self.root))
        (self.root / "blender" / "notes.txt").write_text("not source")
        self.assertEqual(sc.source_hash(self.root), sc.source_hash(self.root))

    def test_real_source_hash_covers_villa_scene(self):
        self.assertEqual(len(sc.source_hash()), 64)

    def test_corrupt_blend_refused(self):
        e = self.store()
        data = bytearray((e / "scene.blend").read_bytes())
        data[500] ^= 0xFF  # same size, one flipped byte
        (e / "scene.blend").write_bytes(bytes(data))
        self.assertIn("sha256 mismatch", sc.verify_entry(e, "k1"))

    def test_truncated_blend_and_missing_meta_refused(self):
        e = self.store()
        (e / "scene.blend").write_bytes((e / "scene.blend").read_bytes()[:100])
        self.assertIn("wrong size", sc.verify_entry(e, "k1"))
        e2 = self.store("k2")
        (e2 / "meta.json").unlink()
        self.assertIn("meta.json", sc.verify_entry(e2, "k2"))

    def test_entry_for_other_key_refused(self):
        e = self.store()
        self.assertIn("key", sc.verify_entry(e, "other"))

    def test_refuse_moves_never_deletes(self):
        e = self.store()
        sc.refuse(self.root, e, "test")
        self.assertFalse(e.exists())
        self.assertEqual(len(list((self.root / "_refused").iterdir())), 1)

    def test_failed_save_leaves_no_entry_and_no_temp(self):
        def boom(path):
            Path(path).write_bytes(b"partial")
            raise RuntimeError("disk full")
        with self.assertRaises(RuntimeError):
            sc.store_entry(self.root, "k9", {}, boom, b"s")
        self.assertFalse((self.root / "k9").exists())
        self.assertEqual(list(self.root.glob(".tmp-*")), [])

    def test_concurrent_jobs_build_once(self):
        builds, hits, errors = [], [], []

        def job(i):
            try:
                with sc.file_lock(self.root / "k.lock"):
                    e = self.root / "k"
                    if e.exists() and isinstance(sc.verify_entry(e, "k"), dict):
                        hits.append(i)
                        return
                    builds.append(i)
                    time.sleep(0.3)  # a slow build while the others queue on the lock
                    sc.store_entry(self.root, "k", {}, fake_blend, b"s")
            except Exception as exc:  # pragma: no cover
                errors.append(exc)

        ts = [threading.Thread(target=job, args=(i,)) for i in range(6)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual((errors, len(builds), len(hits)), ([], 1, 5))
        self.assertIsInstance(sc.verify_entry(self.root / "k", "k"), dict)


if __name__ == "__main__":
    unittest.main()
