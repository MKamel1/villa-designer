"""Regression for the 2026-10-01 stale D1 render scene."""
import json
import os
import shutil
import subprocess
import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from archpipe.concept import villa_render as scene_builder
from archpipe.concept.villa_render import source_provenance


class VillaSceneProvenance(unittest.TestCase):
    def setUp(self):
        self.root = ROOT / "out/tmp" / ("scene-provenance-" + uuid.uuid4().hex)
        self.root.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.root)
        paths = [
            "src/archpipe/concept/villa_render.py", "src/archpipe/blender/villa_scene.py",
            "src/archpipe/blender/photoreal.py", "src/archpipe/blender/build_scene.py",
            "src/archpipe/blender/presentation.py", "src/archpipe/villa_render_contract.py",
            "src/archpipe/furniture_orientation.py", "ops/workstation/library-manifest.json",
            "knowledge/garden-palette.json", "knowledge/site-orientation.json", "knowledge/c4-final-approvals.json", "spec/villa-site.yaml",
            "knowledge/library.json", "knowledge/projects/villa-01/brief-requirements.json",
            "knowledge/projects/villa-01/taste.json"]
        for relative in paths:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        self.scene = self.root / "scene.json"
        self._write_scene()

    def _write_scene(self):
        self.scene.write_text(json.dumps({"schema": "villa-render/1", "library_root": "/library",
                                          "views": [{"id": "v1"}],
                                          "lights": [], "provenance": source_provenance(self.root)}),
                              encoding="utf-8")

    def _driver(self, *args):
        # Keep the actual driver and hash algorithm; stub only the costly scene builder,
        # render contract and workstation. A separate process proves the CLI exit status.
        code = '''
import json, sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(sys.argv[1]) / "scripts"))
sys.path.insert(0, str(Path(sys.argv[1]) / "src"))
import villa_render as driver
from archpipe.concept.villa_render import source_provenance
root, scene = Path(sys.argv[2]), Path(sys.argv[3])
def write():
    data = json.loads(scene.read_text(encoding="utf-8"))
    data["provenance"] = source_provenance(root)
    scene.write_text(json.dumps(data), encoding="utf-8")
    return scene, data
# Keep the launch root real; only provenance inputs use the isolated copy.
sys.argv = ["villa_render.py", *sys.argv[4:]]
with patch.object(driver, "source_provenance", lambda: source_provenance(root)), \\
     patch.object(driver, "write_scene", write), \\
     patch.object(driver, "validate_scene", lambda scene: []):
    driver.main()
'''
        env = os.environ.copy()
        env["NO_COLOR"] = "1"
        return subprocess.run([sys.executable, "-c", code, str(ROOT), str(self.root),
                               str(self.scene), *args], cwd=ROOT, env=env,
                              capture_output=True, text=True)

    def test_real_stale_scene_refused_default_rebuilds_and_hash_is_reported(self):
        clean = self._driver("--scene", str(self.scene), "--dry-run")
        self.assertEqual(clean.returncode, 0, clean.stderr)
        source = self.root / "src/archpipe/concept/villa_render.py"
        source.write_bytes(source.read_bytes() + b"\n# changed after scene export\n")
        stale = self._driver("--scene", str(self.scene), "--dry-run")
        self.assertNotEqual(stale.returncode, 0)
        self.assertIn("Scene provenance mismatch", stale.stderr)
        fresh = self._driver("--dry-run")
        self.assertEqual(fresh.returncode, 0, fresh.stderr)
        result = json.loads(fresh.stdout)
        self.assertEqual(result["scene_source_hash"], source_provenance(self.root)["source_hash"])
        self.assertFalse(result["stale_scene"])
        self.assertEqual(json.loads(self.scene.read_text())["provenance"]["source_hash"],
                         result["scene_source_hash"])

    def test_orientation_record_change_makes_scene_stale(self):
        authority=self.root/'knowledge/site-orientation.json'
        authority.write_bytes(authority.read_bytes()+b' ')
        result=self._driver('--scene',str(self.scene),'--dry-run')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Scene provenance mismatch',result.stderr)

    def test_data_change_is_stale_and_override_is_labelled(self):
        palette = self.root / "knowledge/garden-palette.json"
        palette.write_bytes(palette.read_bytes() + b" ")
        result = self._driver("--scene", str(self.scene), "--allow-stale-scene", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertTrue(data["stale_scene"])
        self.assertEqual(data["label"], "STALE-SCENE")
        self.assertNotEqual(data["scene_source_hash"], source_provenance(self.root)["source_hash"])

    def test_changed_garden_approval_retirement_makes_scene_stale(self):
        authority = self.root / "knowledge/c4-final-approvals.json"
        authority.write_bytes(authority.read_bytes() + b" ")
        result = self._driver("--scene", str(self.scene), "--dry-run")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Scene provenance mismatch", result.stderr)

    def test_historical_unstamped_scene_refuses_before_render(self):
        # Frozen by value from the lead's 2026-10-01 D1 evidence: villa-render/1,
        # id D1, 34 views, 915 meshes, and no provenance field. The gate runs
        # before contract validation, so the large face lists are immaterial.
        self.scene.write_text(json.dumps({"schema": "villa-render/1", "id": "D1",
                                          "views": [{"id": "v1"}], "lights": []}), encoding="utf-8")
        result = self._driver("--scene", str(self.scene), "--dry-run")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Scene provenance mismatch", result.stderr)

    def test_write_stamps_scene_and_refuses_source_change_during_build(self):
        target = self.root / "export.json"
        with patch.object(scene_builder, "build", lambda views=None: {"schema": "villa-render/1", "lights": []}), \
             patch("archpipe.villa_render_contract.validate_scene", lambda scene: []), \
             patch.object(scene_builder, "source_provenance", lambda: source_provenance(self.root)):
            scene_builder.write(target)
        stamped = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(stamped["provenance"]["source_hash"], source_provenance(self.root)["source_hash"])
        old_bytes = target.read_bytes()
        hashes = iter(({"source_hash": "before"}, {"source_hash": "after"}))
        with patch.object(scene_builder, "build", lambda views=None: {"schema": "villa-render/1", "lights": []}), \
             patch("archpipe.villa_render_contract.validate_scene", lambda scene: []), \
             patch.object(scene_builder, "source_provenance", lambda: next(hashes)):
            with self.assertRaisesRegex(RuntimeError, "changed during build"):
                scene_builder.write(target)
        self.assertEqual(target.read_bytes(), old_bytes)

    def test_stale_override_marks_each_qa_record_and_result(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import villa_render as driver
        source = self.root / "src/archpipe/concept/villa_render.py"
        source.write_bytes(source.read_bytes() + b"\n# another source revision\n")

        class RemoteResult:
            returncode = 0
            stderr = b""
            def __init__(self, stdout=b""):
                self.stdout = stdout

        def ssh(host, command, **kwargs):
            if command.startswith("cat "):
                if command.endswith("/execution-context.json"):
                    return RemoteResult(json.dumps({
                        "schema": "execution-context/1", "working_directory": "/release",
                        "scripts": ["/release/src/archpipe/blender/villa_scene.py"],
                        "environment": {"NO_COLOR": "1"},
                        "tools": {"blender": {"path": "/remote/opt/blender-4.5.14/blender",
                                              "requested_path": "/remote/opt/blender/blender", "version": "4.5.14"}}
                    }).encode())
                if command.endswith("/status"):
                    return RemoteResult(b"0\n")
                if command.endswith(".png"):
                    return RemoteResult(b"fake png")
                if command.endswith(".json"):
                    return RemoteResult(b"{}")
            return RemoteResult()

        with patch.object(driver, "source_provenance", lambda: source_provenance(self.root)), \
             patch.object(driver, "validate_scene", lambda scene: []), \
             patch.object(driver, "deploy", lambda host: ("/remote/archpipe", "/release", "release")), \
             patch.object(driver, "_ssh", ssh), patch.object(driver, "_push"), \
             patch.object(driver, "check", lambda path, context: {"passed": True, "checks": []}), \
             patch.object(driver, "villa_qa_context", lambda *args: {}), \
             patch.object(driver, "villa_caption", lambda *args: {}):
            result = driver.run(self.scene, "v1", None, None, "fake-host", self.root,
                                allow_stale_scene=True)
        qa = json.loads((self.root / "v1.qa.json").read_text(encoding="utf-8"))
        self.assertEqual(qa["label"], "STALE-SCENE")
        self.assertEqual(result["label"], "STALE-SCENE")
        self.assertEqual(result["views"][0]["label"], "STALE-SCENE")
        self.assertEqual(qa["scene_source_hash"], result["scene_source_hash"])
        self.assertEqual(qa["scene_provenance"], result["scene_provenance"])


if __name__ == "__main__":
    unittest.main()
