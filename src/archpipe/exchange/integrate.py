"""Re-run the whole integration after a lighting (or other model) change. Lane INT.

    python -m archpipe.exchange.integrate [--skip-snapshot]

1. model snapshot (~6 min, skipped with --skip-snapshot)   2. electrical design on the real L6b zones, committed outputs
3. exchange (IFC/DXF/quantities, validation)               4. drawing set + committed sample schedules
5. the lane suite.  Stops at the first failing step; the exit status is the first non-zero one.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SUITE = "tests/luminaires tests/compliance tests/design tests/model tests/electrical tests/lightcalc tests/lightverify tests/critic tests/ops tests/documents tests/drawings2d tests/pipeline tests/exchange tests/approvals".split()


def run(*cmd: str) -> None:
    print("+", " ".join(cmd), flush=True)
    r = subprocess.run([sys.executable, *cmd], cwd=ROOT, env={**__import__("os").environ, "PYTHONPATH": str(ROOT / "src"), "NO_COLOR": "1"})
    if r.returncode:
        sys.exit(r.returncode)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-snapshot", action="store_true")
    a = ap.parse_args()
    if not a.skip_snapshot:
        run("-m", "archpipe.model.export", "--snapshot")
    run("-m", "archpipe.electrical.d1_run", "--docs", "docs/lanes/L7b-d1", "--data", "tests/electrical/d1")
    run("-m", "archpipe.exchange", "--out", "out/exchange/D1")
    run("-m", "archpipe.documents", "--out", "out/documents/D1")
    samples = ROOT / "src/archpipe/documents/samples"
    for f in [*Path(ROOT, "out/documents/D1").glob("schedule-*.csv"), ROOT / "out/documents/D1/schedules.md"]:
        shutil.copy(f, samples / f.name)
    run("-m", "pytest", *SUITE, "-q")


if __name__ == "__main__":
    main()
