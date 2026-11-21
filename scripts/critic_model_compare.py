"""Compare VLM runs on the TUNING half only: per-criterion separation and 0/1/2 counts.

    python scripts/critic_model_compare.py out/critic/vlm/tune_v1 out/critic/vlm/tune_v1_qwen3_8_27b_mtp_q4_K_M

Separation = fraction of must_fail views scoring < 2 minus fraction of should_pass views scoring < 2
(the rubric's gate_selection quantity). Selection rule (pre-registered in the lane doc): the model with
the largest summed separation over R5, R7, R8, R9, R10, R11 wins; ties go to gemma4:31b.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
split = json.loads((ROOT / "knowledge" / "critic" / "split.json").read_text(encoding="utf-8"))
labels, tuning = split["labels"], split["tuning"]
CRIT = ["R5", "R7", "R8", "R9", "R10", "R11"]
bad = [v for v in tuning if labels[v]["tier"] == "must_fail"]
good = [v for v in tuning if labels[v]["tier"] == "should_pass"]
for d in sys.argv[1:]:
    runs = {}
    for f in Path(d).glob("v*.json"):
        j = json.loads(f.read_text(encoding="utf-8"))
        runs[j["view"]] = j["scores"]
    total, row = 0.0, {}
    for c in CRIT:
        def lt2(v):
            s = runs.get(v, {}).get(c, {}).get("score")
            return s is not None and s < 2
        sep = sum(lt2(v) for v in bad) / len(bad) - sum(lt2(v) for v in good) / len(good)
        row[c] = round(sep, 2)
        total += sep
    print(Path(d).name, f"n={len(runs)}", row, "sum", round(total, 2))
