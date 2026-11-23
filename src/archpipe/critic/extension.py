"""Score the L9P extension set with the frozen rubric and print the pre-registered table.

    python -m archpipe.critic.extension --images out/l9p/final-drafts --vlm-dir out/l9p/critic/vlm \\
        [--out knowledge/critic/extension-L9P-results.json]

Nothing here tunes anything: gating criteria are the frozen ones (R8, R10, R11 plus the deterministic six).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import calibrate as C
from . import labels as L
from . import verdict as V

ROOT = Path(__file__).resolve().parents[3]
FROZEN_GATES = {"R8", "R10", "R11"}
# From docs/lanes/L3-calibration.md (audit views, frozen-v1): (k, n). Tuning figures carry the tuning caveat.
AUDIT = {
    "held_out": dict(recall_must_fail=(8, 8), false_fail_should_pass=(1, 2), recall_c_or_worse=(14, 16), middle_fail=(6, 8)),
    "tuning": dict(recall_must_fail=(10, 10), false_fail_should_pass=(1, 3), recall_c_or_worse=(16, 17), middle_fail=(6, 7)),
}


def score_set(labels: dict, images: Path, vlm_dir: Path | None, rubric: dict, gates=FROZEN_GATES):
    """-> (verdicts, rows, notes). A view whose VLM result is missing fails closed, as in the frozen rule."""
    vlm = C.load_vlm_dir(vlm_dir) if vlm_dir else {}
    gating = set(V.ALWAYS_GATING) | set(gates)
    verdicts, rows, notes = {}, {}, {}
    for v in labels:
        det = V.deterministic_scores(images / f"{v}.png")
        j = vlm.get(v)
        ok = bool(j and j.get("status") == "ok")
        rows[v] = V.merge(det, j["scores"] if ok else None, rubric)
        verdicts[v], notes[v] = V.decide(rows[v], gating, True, vlm_ok=ok)
    return verdicts, rows, notes


def table(labels: dict, verdicts: dict) -> dict:
    """New-set confusion, and pooled with the audit halves (all 'held-out' except the tuning half caveat)."""
    cm = C.confusion(verdicts, labels, list(labels))
    return dict(new=cm,
                new_wilson={k: tuple(round(x, 3) for x in C.wilson(*cm[k]))
                            for k in ("recall_must_fail", "false_fail_should_pass", "recall_c_or_worse", "middle_fail")},
                pooled_with_audit_held_out=C.pooled(cm, AUDIT["held_out"]),
                pooled_with_all_38=C.pooled(cm, AUDIT["held_out"], AUDIT["tuning"]))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", default=str(ROOT / "out/l9p/final-drafts"))
    ap.add_argument("--vlm-dir", default=str(ROOT / "out/l9p/critic/vlm"))
    ap.add_argument("--labels", default=str(ROOT / "knowledge/critic/extension-L9P-labels.json"))
    ap.add_argument("--out", default="")
    a = ap.parse_args(argv)
    rubric = V.load_rubric()
    if not str(rubric["version"]).startswith("frozen"):
        print("refusing: rubric is not frozen")
        return 2
    labels = json.loads(Path(a.labels).read_text(encoding="utf-8"))["labels"]
    verdicts, rows, notes = score_set(labels, Path(a.images), Path(a.vlm_dir), rubric)
    crit = ["R1", "R2", "R3", "R4", "R5", "R7", "R8", "R9", "R10", "R11", "R12", "R13"]
    print("view grade " + " ".join(f"{c:>3}" for c in crit) + "  verdict reasons")
    for v in sorted(labels, key=lambda x: (L.GRADE_ORDER.index(labels[x]["grade"]), x)):
        s = " ".join(f"{('-' if rows[v][c]['score'] is None else rows[v][c]['score']):>3}" for c in crit)
        print(f"{v:30} {labels[v]['grade']:3} {s}  {verdicts[v]:5} {'; '.join(notes[v]['reasons'])}")
    t = table(labels, verdicts)
    print(json.dumps(t, indent=1))
    if a.out:
        Path(a.out).write_text(json.dumps(dict(verdicts=verdicts, table=t, notes=notes,
                                               scores={v: {c: rows[v][c]["score"] for c in rows[v]} for v in labels}),
                                          indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
