"""Capture the real -PLOT prompt sequence for a NAMED LAYOUT, one prompt at a time.

Guessing the sequence from documentation is how you wedge accoreconsole
forever (trap 1 in acad.py). The safe protocol is the opposite: feed only
the answers you are sure of, let the script run out of lines -- which
aborts the command rather than wedging it -- and read the transcript to
see the next prompt verbatim. Then add exactly one line and repeat.

    python scripts/capture_plot_prompts.py out/sheet_test.dwg A3-1-50 "Y" "A3-1-50" ...

Answers are given on the command line, so extending the sequence is
editing one shell line rather than editing this file.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from archpipe import acad  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    dwg = Path(argv[0]).resolve()
    answers = argv[1:]

    workdir = Path(__file__).resolve().parents[1] / "out"
    scr = acad._script(workdir / "_capture.scr", ["FILEDIA", "0", "-PLOT", *answers])
    log = workdir / "_capture.log"
    print(f"script: {scr}\nanswers after -PLOT: {answers}\n")

    try:
        acad._run(dwg, scr, timeout=90, log=log)
        print("-- run completed without blocking --")
    except acad.AcadError as e:
        print(f"-- AcadError: {e}")

    text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
    print("\n================ transcript ================")
    print(text[-4000:])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
