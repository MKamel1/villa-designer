"""Score a calibration split and print the table.

    python scripts/critic_calibrate.py --split tuning --vlm-dir out/critic/vlm/tune_v0 [--gates auto|all|R5,R8]
    python scripts/critic_calibrate.py --split held_out --vlm-dir out/critic/vlm/held_frozen --gates <list from freeze>

Held-out scoring is refused unless knowledge/critic/rubric.json carries version 'frozen-*'.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from archpipe.critic import calibrate as C   # noqa: E402
from archpipe.critic import labels as L      # noqa: E402
from archpipe.critic import meta as M        # noqa: E402
from archpipe.critic import pixels as P      # noqa: E402
from archpipe.critic import verdict as V     # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["tuning", "held_out", "all"], default="tuning")
    ap.add_argument("--vlm-dir", default="")
    ap.add_argument("--gates", default="auto", help="auto (selection rule, tuning only) | all | comma list of VLM criteria")
    ap.add_argument("--rubric", default=str(V.RUBRIC_PATH))
    ap.add_argument("--finals", default=C.FINALS)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    rubric = V.load_rubric(a.rubric)
    if a.split != "tuning" and not str(rubric["version"]).startswith("frozen"):
        print("refusing: held-out scoring needs a frozen rubric (version 'frozen-*')")
        return 2
    split = json.loads((ROOT / "knowledge" / "critic" / "split.json").read_text(encoding="utf-8"))
    labels = split["labels"]
    views = split["tuning"] + split["held_out"] if a.split == "all" else split[a.split]
    vlm = C.load_vlm_dir(a.vlm_dir) if a.vlm_dir else {}
    rows = {}
    for v in views:
        png = C.png_for(v, a.finals)
        det = V.deterministic_scores(png)
        j = vlm.get(v)
        rows[v] = V.merge(det, j["scores"] if j and j.get("status") == "ok" else None, rubric)
    if a.gates == "auto":
        info = C.select_gates(rows, labels, split["tuning"] if a.split == "tuning" else split["tuning"])
        gating = set(V.ALWAYS_GATING) | {c for c, i in info.items() if i["gates"]}
        print("gate selection:", json.dumps(info, indent=1))
    elif a.gates == "all":
        gating = set(V.ALWAYS_GATING) | set(V.VLM_CRITERIA)
    else:
        gating = set(V.ALWAYS_GATING) | set(a.gates.split(","))
    verdicts, notes = {}, {}
    for v in views:
        verdicts[v], notes[v] = V.decide(rows[v], gating, True, vlm_ok=True)
    crit = ["R1", "R2", "R3", "R4", "R5", "R7", "R8", "R9", "R10", "R11", "R12", "R13"]
    print("view grade  " + " ".join(f"{c:>3}" for c in crit) + "  verdict  reasons")
    for v in sorted(views, key=lambda x: (L.GRADE_ORDER.index(labels[x]["grade"]), x)):
        s = " ".join(f"{('-' if rows[v][c]['score'] is None else rows[v][c]['score']):>3}" for c in crit)
        print(f"{v}  {labels[v]['grade']:3}   {s}  {verdicts[v]:7} {'; '.join(notes[v]['reasons'])}")
    cm = C.confusion(verdicts, labels, views)
    print(json.dumps(cm, indent=1))
    print("gating:", sorted(gating))
    if a.out:
        Path(a.out).write_text(json.dumps(dict(split=a.split, gating=sorted(gating), verdicts=verdicts, confusion=cm,
                                               scores={v: {c: rows[v][c]["score"] for c in rows[v]} for v in views},
                                               notes=notes), indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
