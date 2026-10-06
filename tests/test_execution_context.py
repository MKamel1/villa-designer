"""Frozen launch failures from lessons-audit, plus injected siblings."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from archpipe.execution_context import (ContextError, Tool, absolute, preflight,
                                        resolve_tool, run_checked)

ROOT = Path(__file__).resolve().parents[1]


class ExecutionContextTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.base = Path(self.directory.name).resolve()
        self.script = self.base / "script.py"
        self.script.write_text("pass", encoding="utf-8")

    def context(self, **changes):
        values = dict(root=ROOT, scripts=[self.script], output=self.base / "out",
                      temp=self.base / "tmp")
        values.update(changes)
        return preflight(**values)

    def test_relative_pyrevit_real_case_and_accoreconsole_sibling(self):
        # CLAUDE.md: journal could not find target; CLI nevertheless exited 0.
        for path in ("revit/build_bedroom.py", "out/plot.scr"):
            with self.subTest(path=path), self.assertRaisesRegex(ContextError, "must be absolute"):
                run_checked([sys.executable, path], context=self.context(),
                            scripts=[Path(path)], record=self.base / "bad.json")

    def test_child_temp_directory_unwritable_before_launch(self):
        # Frozen Python 3.14 failure: parent exists, child write denied.
        original = Path.write_bytes
        def denied(path, data):
            if path.name == "write-read-delete":
                raise PermissionError("[WinError 5] Access is denied")
            return original(path, data)
        with patch.object(Path, "write_bytes", denied):
            with self.assertRaisesRegex(ContextError, "not writable/readable/removable"):
                self.context(output=self.base)
        # Probe residue is intentionally not claimed cleaned on denied access.
        for probe in self.base.glob(".context-probe-*"):
            probe.rmdir()

    def test_temp_only_denied_and_output_only_denied(self):
        from archpipe import execution_context as module
        original = module.writable_directory
        for label in ("output directory", "temporary directory"):
            def denied(path, name):
                if name == label:
                    raise ContextError(name + " is not writable/readable/removable")
                return original(path, name)
            with patch.object(module, "writable_directory", denied):
                with self.assertRaisesRegex(ContextError, label):
                    self.context()

    def test_clean_context_records_absolute_paths_no_color_and_real_permissions(self):
        context = self.context(env={"NO_COLOR": "0", "PATH": os.environ.get("PATH", "")})
        self.assertEqual(context["environment"]["NO_COLOR"], "1")
        self.assertEqual(context["tools"]["python"]["path"], str(Path(sys.executable).resolve()))
        self.assertEqual(context["scripts"], [str(self.script)])
        self.assertTrue(Path(context["temporary_directory"]).is_dir())
        self.assertFalse(list(self.base.rglob(".context-probe-*")))

    def test_missing_root_and_roles_not_in_live_session(self):
        with self.assertRaisesRegex(ContextError, "missing directory"):
            self.context(root=self.base / "missing")
        with self.assertRaisesRegex(ContextError, "roles unavailable"):
            self.context(required_roles=["render_critic"])
        self.context(required_roles=["render_critic"], available_roles=["render_critic"])

    def test_launch_elsewhere_resolves_paths_and_sets_child_directory(self):
        # Like the pipeline reproduction: project root differs from caller cwd.
        elsewhere = self.base / "elsewhere"
        elsewhere.mkdir()
        (elsewhere / "script.py").write_text("raise RuntimeError('wrong script')")
        input_file = self.base / "input.txt"
        input_file.write_text("declared root")
        self.script.write_text("from pathlib import Path\nprint(Path.cwd())\n"
                               "assert Path('input.txt').read_text() == 'declared root'\n"
                               "Path('out/result.json').write_text('fresh')\n")
        with patch("archpipe.execution_context.Path.cwd", return_value=elsewhere):
            context = self.context(root=self.base, scripts=[Path("script.py")],
                                   inputs=[Path("input.txt")], output=Path("out"), temp=Path("tmp"))
            result = run_checked([sys.executable, context["scripts"][0]], context=context,
                                 scripts=context["scripts"], record=Path("out/run.json"),
                                 expected=Path("out/result.json"))
        self.assertEqual(result.stdout.strip(), str(self.base))
        record = json.loads((self.base / "out/run.json").read_text())
        self.assertTrue(record["passed"])
        self.assertEqual(record["execution_context"]["working_directory"], str(self.base))
        self.assertEqual(context["launch_directory"], str(elsewhere))
        self.assertEqual(context["scripts"], [str(self.script)])
        self.assertEqual(context["inputs"], [str(input_file)])
        for value in [context["output_directory"], context["temporary_directory"],
                      *context["environment"].values(), context["tools"]["python"]["path"]]:
            if value != "1":
                self.assertTrue(Path(value).is_absolute(), value)

    def test_relative_tool_is_resolved_from_root_and_version_probe_sets_directory(self):
        with patch("archpipe.execution_context.subprocess.run",
                   return_value=subprocess.CompletedProcess([], 0, "Tool 1.2.3", "")) as probe:
            context = self.context(root=self.base, tools=[Tool("tool", Path("script.py"), "1.2.3")])
        self.assertEqual(context["tools"]["tool"]["path"], str(self.script))
        self.assertEqual(context["tools"]["tool"]["requested_path"], str(self.script))
        self.assertEqual(probe.call_args.kwargs["cwd"], self.base)
        self.assertEqual(probe.call_args.args[0][0], str(self.script))

    def test_missing_wrong_and_unverified_blender_version(self):
        tool = Tool("blender", Path(sys.executable), "4.5.14")
        for output, code in (("Blender", 0), ("Blender 4.2.9", 0), ("Blender 4.5.14", 1),
                             ("Blender 4.2.9 dependency 4.5.14", 0)):
            with patch("archpipe.execution_context.subprocess.run",
                       return_value=subprocess.CompletedProcess([], code, output, "")):
                with self.assertRaisesRegex(ContextError, "expected version 4.5.14"):
                    resolve_tool(tool, os.environ.copy(), ROOT)
        with patch("archpipe.execution_context.subprocess.run",
                   return_value=subprocess.CompletedProcess([], 0, "Blender 4.5.14", "")):
            self.assertEqual(resolve_tool(tool, os.environ.copy(), ROOT)["version"], "4.5.14")

    def test_missing_and_relative_tools_scripts_and_unpinned_version(self):
        for tool in (Tool("codex", Path("codex.exe"), "1.0.0"),
                     Tool("accoreconsole", self.base / "missing.exe", "2027.0"),
                     Tool("blender", Path(sys.executable), "")):
            with self.subTest(tool=tool.name), self.assertRaises(ContextError):
                self.context(tools=[tool])
        with self.assertRaisesRegex(ContextError, "missing file"):
            absolute(self.base / "missing.py", "script", file=True)
        with self.assertRaisesRegex(ContextError, "unsupported Python"):
            self.context(python_version="3.0.0")

    def test_coloured_failure_uses_exit_status_not_text_filter(self):
        self.script.write_text("import sys\nprint('\\x1b[31mFA\\x1b[0mILED')\nsys.exit(1)\n", encoding="utf-8")
        context = self.context()
        record = self.base / "failure.json"
        with self.assertRaisesRegex(ContextError, "exited 1"):
            run_checked([sys.executable, self.script], context=context,
                        scripts=[self.script], record=record)
        result = json.loads(record.read_text())
        self.assertEqual(result["exit_code"], 1)
        self.assertFalse(result["passed"])
        self.assertNotIn("FAILED", result["stdout"])

    def test_clean_exit_with_failure_word_and_controlled_child_environment(self):
        self.script.write_text("import os\nassert os.environ['NO_COLOR'] == '1'\nprint('FAILED is test data')", encoding="utf-8")
        record = self.base / "clean.json"
        result = run_checked([sys.executable, self.script], context=self.context(),
                             scripts=[self.script], record=record)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(json.loads(record.read_text())["passed"])

    def test_exit_zero_without_artifact_and_fresh_artifact_clean(self):
        context = self.context()
        artifact = self.base / "native.json"
        with self.assertRaisesRegex(ContextError, "without fresh artifact"):
            run_checked([sys.executable, self.script], context=context, scripts=[self.script],
                        record=self.base / "native-context.json", expected=artifact)
        artifact.write_text("stale", encoding="utf-8")
        os.utime(artifact, (1, 1))
        with self.assertRaisesRegex(ContextError, "without fresh artifact"):
            run_checked([sys.executable, self.script], context=context, scripts=[self.script],
                        record=self.base / "native-context.json", expected=artifact)
        self.script.write_text("from pathlib import Path\nPath(" + repr(str(artifact)) + ").write_text('fresh')", encoding="utf-8")
        run_checked([sys.executable, self.script], context=context, scripts=[self.script],
                    record=self.base / "native-context.json", expected=artifact)

    def test_cli_returns_two_for_missing_script_and_resolves_relative_paths_from_elsewhere(self):
        command = [sys.executable, str(ROOT / "scripts/preflight.py"),
                   "--root", str(self.base), "--out", "out", "--temp", "tmp",
                   "--record", "out/cli.json", "--script"]
        bad = subprocess.run(command + ["missing.py"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)
        self.assertIn("missing file", bad.stderr)
        good = subprocess.run(command + ["script.py"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(good.returncode, 0, good.stderr)
        context = json.loads((self.base / "out/cli.json").read_text())
        self.assertEqual(context["environment"]["NO_COLOR"], "1")
        self.assertEqual(context["scripts"], [str(self.script)])
        self.assertEqual(context["working_directory"], str(self.base))
        self.assertEqual(context["launch_directory"], str(ROOT))

    def test_command_cannot_use_unverified_tool_or_different_script(self):
        context = self.context()
        with self.assertRaisesRegex(ContextError, "not been version-checked"):
            run_checked([self.script], context=context, scripts=[], record=self.base / "bad.json")
        with self.assertRaisesRegex(ContextError, "verbatim"):
            run_checked([sys.executable, "script.py"], context=context, scripts=[self.script],
                        record=self.base / "bad.json")

    def test_remote_render_preflight_stops_on_bad_version_and_records_clean(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        from villa_render import remote_preflight
        failure = subprocess.CompletedProcess([], 2, b"", b"expected version 4.5.14")
        with patch("villa_render._ssh", return_value=failure) as ssh:
            with self.assertRaisesRegex(ContextError, "remote preflight failed"):
                remote_preflight("test-host", "/project/release", "/project/job", "/opt/blender/blender")
            self.assertEqual(ssh.call_count, 1)
        context = self.context()
        context.update(working_directory="/project/release",
                       scripts=["/project/release/src/archpipe/blender/villa_scene.py"])
        context["tools"]["blender"] = {"path": "/opt/blender-4.5.14/blender",
                                       "requested_path": "/opt/blender/blender", "version": "4.5.14"}
        with patch("villa_render._ssh", side_effect=[
                subprocess.CompletedProcess([], 0, b"", b""),
                subprocess.CompletedProcess([], 0, json.dumps(context).encode(), b"")]) as ssh:
            self.assertEqual(remote_preflight("test-host", "/project/release", "/project/job",
                                              "/opt/blender/blender"), context)
            command = ssh.call_args_list[0].args[1]
            self.assertIn("cd /project/release", command)
            self.assertIn("--tool blender /opt/blender/blender 4.5.14", command)
            self.assertIn("--script /project/release/src/archpipe/blender/villa_scene.py", command)
        with patch("villa_render._ssh", side_effect=[
                subprocess.CompletedProcess([], 0, b"", b""),
                subprocess.CompletedProcess([], 0, b"{}", b"")]):
            with self.assertRaisesRegex(ContextError, "incomplete or mismatched"):
                remote_preflight("test-host", "/project/release", "/project/job", "/opt/blender/blender")

    def test_bedroom_stage_records_context_and_retains_failure_log(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import run_bedroom
        self.script.write_text("import sys\nprint('native failure evidence')\nsys.exit(1)", encoding="utf-8")
        # Keep integration evidence in this isolated test directory.
        with patch.object(run_bedroom, "ROOT", self.base), \
                patch.object(run_bedroom, "project_context", return_value=self.context()):
            with self.assertRaisesRegex(ContextError, "exited 1"):
                run_bedroom.run([sys.executable, self.script], "frozen-failure")
        logs = self.base / "out/run-logs"
        self.assertIn("native failure evidence", (logs / "frozen-failure.log").read_text())
        self.assertEqual(json.loads((logs / "frozen-failure.context.json").read_text())["exit_code"], 1)

    def test_missing_declared_module_fails_with_interpreter_and_hint(self):
        missing_name = "archpipe_nonexistent_mod_c9x"
        with self.assertRaises(ContextError) as ctx:
            self.context(modules=[missing_name])
        msg = str(ctx.exception)
        self.assertIn(missing_name, msg)
        self.assertTrue(sys.executable in msg or str(Path(sys.executable).resolve()) in msg)
        self.assertIn("use the project environment", msg)

    def test_all_present_modules_stay_quiet_and_recorded_in_context(self):
        context = self.context(modules=["json", "pathlib"])
        self.assertIn("modules", context)
        self.assertEqual(context["modules"]["json"], {"found": True})
        self.assertEqual(context["modules"]["pathlib"], {"found": True})

    def test_real_incident_reproduced_by_value_shapely_missing(self):
        # Real incident (2026-10-06): Windows suite launched with system interpreter
        # lacking shapely from requirements.txt. Frozen fixture of mapped requirements.
        from archpipe.execution_context import requirements_import_names
        import importlib.util

        frozen_req_imports = tuple(requirements_import_names(ROOT / "requirements.txt"))
        self.assertIn("shapely", frozen_req_imports)

        real_find_spec = importlib.util.find_spec

        def mock_find_spec(name, *args, **kwargs):
            if name == "shapely":
                return None
            return real_find_spec(name, *args, **kwargs)

        with patch("importlib.util.find_spec", side_effect=mock_find_spec):
            with self.assertRaises(ContextError) as ctx:
                self.context(modules=frozen_req_imports)
        msg = str(ctx.exception)
        self.assertIn("shapely", msg)
        self.assertTrue(sys.executable in msg or str(Path(sys.executable).resolve()) in msg)
        self.assertIn("use the project environment", msg)

    def test_run_tests_subprocess_exits_2_on_missing_dependency(self):
        env = dict(os.environ)
        env["ARCHPIPE_TEST_EXTRA_MODULES"] = "archpipe_nonexistent_mod_c9x"
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/run_tests.py")],
            env=env,
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("PREFLIGHT FAILED:", result.stderr)
        self.assertIn("archpipe_nonexistent_mod_c9x", result.stderr)
        self.assertTrue(sys.executable in result.stderr or str(Path(sys.executable).resolve()) in result.stderr)
        self.assertIn("use the project environment", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_verify_subprocess_exits_2_on_missing_dependency(self):
        env = dict(os.environ)
        env["ARCHPIPE_TEST_EXTRA_MODULES"] = "archpipe_nonexistent_mod_c9x"
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/verify.py")],
            env=env,
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("PREFLIGHT FAILED:", result.stderr)
        self.assertIn("archpipe_nonexistent_mod_c9x", result.stderr)
        self.assertTrue(sys.executable in result.stderr or str(Path(sys.executable).resolve()) in result.stderr)
        self.assertIn("use the project environment", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_requirements_import_names_mapping(self):
        from archpipe.execution_context import requirements_import_names
        mapped = requirements_import_names(ROOT / "requirements.txt")
        expected = ["ezdxf", "matplotlib", "PIL", "pymupdf", "yaml", "shapely", "ifcopenshell"]
        self.assertEqual(mapped, expected)


if __name__ == "__main__":
    unittest.main()
