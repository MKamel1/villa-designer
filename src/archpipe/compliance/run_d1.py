"""Run every L1 checker on design D1, write out/checks/L1.json and docs/lanes/L1-safety-report-D1.md.

    PYTHONPATH=src python -m archpipe.compliance.run_d1 [--out-dir C:\\...\\out] [--no-report]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .. import contracts
from . import checks, model, report, sources


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--checks-dir", default="out/checks")
    ap.add_argument("--report", default="docs/lanes/L1-safety-report-D1.md")
    ap.add_argument("--no-report", action="store_true")
    a = ap.parse_args(argv)
    m = model.load_d1(a.out_dir)
    results = checks.run_all(m)
    cards = sources.load_cards()
    bad = sources.missing_sources(results, cards)
    if bad:
        print("missing source cards: %s" % bad, file=sys.stderr)
        return 2
    path = contracts.write_results("L1", results, a.checks_dir)
    print("wrote", path, len(results), "results")
    if not a.no_report:
        Path(a.report).parent.mkdir(parents=True, exist_ok=True)
        Path(a.report).write_text(report.render(m, results, cards), encoding="utf-8")
        print("wrote", a.report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
