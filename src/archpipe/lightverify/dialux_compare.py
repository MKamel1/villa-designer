"""V11: read results-dialux.json from each package folder and apply the pass bar (Em +/-10 %, Emin and U0 +/-15 %)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .common import LayerResult, check
from .sources import CARDS, ids
from ..contracts import SourceCard

CARDS["LV-V11-DIALUX"] = SourceCard("LV-V11-DIALUX", "archpipe lighting verification plan", "2026-11-21", "V11", "",
                                    "DIALux evo vs engine: Em within 10 %, Emin and U0 within 15 %", "policy",
                                    "docs/quality/LIGHTING-VERIFICATION.md")
SRC = ids("LV-V11-DIALUX")
BARS = {"Em": 0.10, "Emin": 0.15, "U0": 0.15}


def run(root: Path) -> LayerResult:
    L = LayerResult("V11")
    for d in sorted(p for p in Path(root).iterdir() if p.is_dir()):
        exp = json.loads((d / "expected-engine.json").read_text())["planes"]
        got_f = d / "results-dialux.json"
        if not got_f.exists():
            L.results.append(check("LV11", "not_evaluated", d.name, (), message="results-dialux.json not provided (DIALux run pending)"))
            continue
        got = json.loads(got_f.read_text())
        for pid, e in exp.items():
            g = got.get(pid)
            if not g:
                L.results.append(check("LV11", "not_evaluated", "%s/%s" % (d.name, pid), (), message="plane missing in DIALux results"))
                continue
            bad = {k: g[k] / e[k] - 1 for k in BARS if e.get(k) and g.get(k) is not None and abs(g[k] / e[k] - 1) > BARS[k]}
            L.results.append(check("LV11", "fail" if bad else "pass", "%s/%s" % (d.name, pid), SRC, achieved=g["Em"], required=e["Em"], unit="lx",
                                   message="Em engine %.0f / DIALux %.0f lx; Emin %.0f / %.0f; U0 %.2f / %.2f%s" % (
                                       e["Em"], g["Em"], e["Emin"], g["Emin"], e["U0"], g["U0"],
                                       ("; outside the bar: " + ", ".join("%s %+.0f %%" % (k, 100 * v) for k, v in bad.items())) if bad else "")))
    return L


if __name__ == "__main__":
    from .dialux_pack import OUT
    for r in run(OUT).results:
        print(r.status, r.subject, r.message)
