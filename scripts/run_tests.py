"""Run the unittest suite with writable temporary directories on Windows.

Python 3.14's mkdtemp creates directories that the managed Windows sandbox
cannot write or remove. This runner changes only its own test process.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))


def _accessible_mkdtemp(suffix=None, prefix=None, dir=None):
    root = Path(os.fsdecode(dir) if dir is not None else tempfile.gettempdir())
    stem = os.fsdecode(prefix) if prefix is not None else "tmp"
    end = os.fsdecode(suffix) if suffix is not None else ""
    for _ in range(10):
        target = root / (stem + uuid.uuid4().hex + end)
        try:
            target.mkdir()
        except FileExistsError:
            continue
        return os.fsencode(target) if any(isinstance(x, bytes) for x in (suffix, prefix, dir)) else str(target)
    raise FileExistsError("could not create unique test directory")


def main():
    if os.name == "nt":
        # Path.mkdir uses an accessible ACL here; tempfile.mkdtemp does not.
        test_temp = ROOT / "out" / "tmp"
        test_temp.mkdir(parents=True, exist_ok=True)
        tempfile.tempdir = str(test_temp)
        tempfile.mkdtemp = _accessible_mkdtemp
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    return 0 if unittest.TextTestRunner().run(suite).wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
