"""The render release must carry every tracked file the source reads by a fixed path.

Real case (2026-10-14): the first GPU draft batch on integration 7 failed inside
Blender with FileNotFoundError for knowledge/imported-legacy-components.json.gz,
because scripts/workstation.package() shipped no knowledge/ files and no .gz data.
"""
import io
import re
import subprocess
import sys
import tarfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import workstation  # noqa: E402

LITERAL = re.compile(r"ROOT\s*/\s*['\"]([^'\"]+)['\"]")


def packaged_names():
    _, archive = workstation.package()
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tf:
        return set(tf.getnames())


def tracked():
    out = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode()
    return {name for name in out.split("\0") if name}


class ReleasePackage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.names = packaged_names()
        cls.tracked = tracked()

    def test_real_imported_appearance_inputs_are_packaged(self):
        for name in ("knowledge/imported-legacy-components.json.gz",
                     "knowledge/imported-component-policy.json"):
            self.assertIn(name, self.tracked)
            self.assertTrue(name in self.names, name + " missing from the render release")

    def test_every_tracked_file_read_by_fixed_path_in_src_is_packaged(self):
        missing = []
        for path in sorted((ROOT / "src").rglob("*.py")):
            for name in LITERAL.findall(path.read_text(encoding="utf-8")):
                if name in self.tracked and name not in self.names:
                    missing.append("%s reads %s" % (path.relative_to(ROOT), name))
        self.assertEqual(missing, [])

    def test_tests_fixtures_and_unrelated_binaries_stay_out(self):
        self.assertFalse([n for n in self.names if n.startswith("tests/fixtures/") and n.endswith(".gz")])


if __name__ == "__main__":
    unittest.main()
