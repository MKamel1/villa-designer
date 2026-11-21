"""villa_render must launch through jobq (GPU lock, dead-job relaunch), not the old pid-file guard."""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
import villa_render  # noqa: E402


class LaunchTest(unittest.TestCase):
    def test_old_wedging_guard_is_gone_and_job_takes_the_gpu_lock(self):
        text = (ROOT / "scripts/villa_render.py").read_text(encoding="utf-8")
        self.assertNotIn('"/pid"', text)
        self.assertNotIn("echo $! >", text)
        self.assertIn('"--gpu"', text)
        self.assertIn('"/bin/jobq"', text)

    def test_missing_runner_fails_with_the_install_command(self):
        original = villa_render._ssh
        villa_render._ssh = lambda host, cmd, **kw: subprocess.CompletedProcess([], 1, b"", b"")
        try:
            with self.assertRaisesRegex(RuntimeError, "install-runner"):
                villa_render.ensure_runner("h", "/r")
        finally:
            villa_render._ssh = original

    def test_installed_runner_passes(self):
        original = villa_render._ssh
        villa_render._ssh = lambda host, cmd, **kw: subprocess.CompletedProcess([], 0, b"", b"")
        try:
            villa_render.ensure_runner("h", "/r")
        finally:
            villa_render._ssh = original


if __name__ == "__main__":
    unittest.main()
