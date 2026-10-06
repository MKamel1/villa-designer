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
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from archpipe.execution_context import ContextError, project_context, write_record


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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("modules", nargs="*", help="focused unittest modules; omitted means discovery")
    args = parser.parse_args()
    try:
        context = project_context(ROOT, Path(__file__).resolve(), "tests")
    except ContextError as exc:
        print("PREFLIGHT FAILED: " + str(exc), file=sys.stderr)
        return 2
    if os.name == "nt":
        # Path.mkdir uses an accessible ACL here; tempfile.mkdtemp does not.
        test_temp = ROOT / "out" / "tmp"
        test_temp.mkdir(parents=True, exist_ok=True)
        tempfile.tempdir = str(test_temp)
        tempfile.mkdtemp = _accessible_mkdtemp
    suite = (unittest.defaultTestLoader.loadTestsFromNames(args.modules) if args.modules else
             unittest.defaultTestLoader.discover(str(ROOT / "tests")))
    result = unittest.TextTestRunner().run(suite)
    code = 0 if result.wasSuccessful() else 1
    write_record({"execution_context": context, "modules": args.modules,
                  "tests_run": result.testsRun, "exit_code": code, "passed": code == 0},
                 ROOT / "out/tests-result.json")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
