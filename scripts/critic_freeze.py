"""Freeze the rubric after tuning: record the chosen model and gating set, bump the version to 'frozen-v1'.
Run once, then commit and push BEFORE scoring the held-out half.
"""
import json
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "knowledge" / "critic" / "rubric.json"
r = json.loads(p.read_text(encoding="utf-8"))
r["version"] = "frozen-v1"
r["preregistration"]["model"] = "qwen3.8:27b-mtp-q4_K_M"
r["preregistration"]["model_note"] = (
    "chosen on the tuning half by the summed gate-selection separation over R5,R7,R8,R9,R10,R11 "
    "(scripts/critic_model_compare.py): qwen3.8:27b-mtp-q4_K_M 1.43, gemma4:31b 1.17, qwen3.6:35b-a3b 1.10. "
    "The selection rule was written while the first 7 qwen3.8 rows had been read.")
r["gating"] = {
    "vlm": ["R8", "R10", "R11"],
    "selection": "rubric.scoring.gate_selection on the tuning half with qwen3.8 scores: R8 0.47, R10 0.47, R11 0.47 gate; "
                 "R5 0.07, R7 -0.23, R9 0.20, R13 0.00 do not (they are still scored and reported)"}
r["amendments"].append({
    "id": "A6", "scope": "model and gating freeze",
    "why": "model chosen by summed separation on the tuning half; gating set by the pre-registered rule",
    "evidence": "tuning half, qwen3.8: recall on must_fail 10/10, false-fail on should_pass 1/3 "
                "(v34 B: R4 warn from window glare inside the subject box, plus an R10 warn)"})
p.write_text(json.dumps(r, indent=2), encoding="utf-8")
print(r["version"], r["preregistration"]["model"], r["gating"]["vlm"])
