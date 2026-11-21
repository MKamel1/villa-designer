"""Human grade labels (docs/reviews/2026-11/visual-audit.md) and the pre-registered split."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

GRADE_ORDER = ["A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "F"]
SPLIT_SEED = "L3-2026-11-critic-v1"
# A view already shown to a model while choosing the model is not held out.
FORCED_TUNING = ("v27",)


def parse_audit(path: str | Path) -> dict[str, dict]:
    """view prefix ("v27") -> {name, grade, qa_passed, false_pass}."""
    out: dict[str, dict] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*(v\d\d)\s+([^|]*?)\s*\|\s*([A-F][+-]?)\s*\|(.*)\|(.*)\|(.*)\|\s*$", line)
        if not m:
            continue
        view, name, grade, defects, qa, fp = m.groups()
        out[view] = dict(name=name.strip(), grade=grade, defects=defects.strip(),
                         qa_passed=qa.strip().upper().startswith("PASS"),
                         false_pass=fp.strip().upper().startswith("YES"))
    return out


def _h(view: str) -> str:
    return hashlib.sha256(f"{SPLIT_SEED}:{view}".encode()).hexdigest()


def stratified_split(labels: dict[str, dict]) -> dict[str, list[str]]:
    """Per grade, order by seeded hash and deal alternately; the odd extra view alternates
    between halves so the halves stay balanced. FORCED_TUNING views always go to tuning."""
    tuning: list[str] = []
    held: list[str] = []
    flip = 0
    for g in GRADE_ORDER:
        views = sorted((v for v, d in labels.items() if d["grade"] == g), key=_h)
        for v in [x for x in views if x in FORCED_TUNING]:
            tuning.append(v)
            views.remove(v)
        half = len(views) // 2
        tuning += views[:half]
        held += views[half:half * 2]
        if len(views) % 2:
            (tuning if flip % 2 == 0 else held).append(views[-1])
            flip += 1
    return {"tuning": sorted(tuning), "held_out": sorted(held)}


def tier(grade: str) -> str:
    """Pre-registered mapping of human grades to the expected verdict."""
    if grade in ("D+", "D", "D-", "F"):
        return "must_fail"      # recall target >= 90 %
    if grade in ("A", "A-", "B+", "B", "B-"):
        return "should_pass"    # false-fail target <= 10 %
    return "middle"             # C+, C, C-: reported, not scored against a target
