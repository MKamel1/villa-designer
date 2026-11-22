"""VLM composition criteria on the plan image, for critique(vlm=True). Only criteria that passed calibration gate;
the rest are advisory (calibrated false). Prompts come from rubric.json."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .common import Finding, KNOW
from . import plan


def vlm_findings(layout, host="http://localhost:11434", view=None):
    from ...critic import vlm as V
    from .run_vlm import jpg_b64
    rub = json.loads((KNOW / "critic/rubric.json").read_text())
    cal = json.loads((KNOW / "critic/calibration.json").read_text())["criteria"] if (KNOW / "critic/calibration.json").exists() else {}
    with tempfile.TemporaryDirectory() as d:
        p = str(Path(d) / "plan.png"); plan.plan_png(layout, p, view=view)
        img = jpg_b64(p); out = []
        for c, spec in rub["criteria"].items():
            try:
                r = V.clean_score(V.chat(host, rub["model"], rub["preamble"] + "\n\nCriterion: " + spec["prompt"], [img], rub["options"], V.SCORE_SCHEMA, False))
            except V.VlmUnavailable as e:
                out.append(Finding("landscape-architect", c, "not_evaluated", "info", f"VLM unavailable: {e}", spec["source"], kind="vlm")); continue
            s = r.get("score")
            st = "not_evaluated" if s is None else {2: "pass", 1: "warn", 0: "fail"}[s]
            gating = cal.get(c, {}).get("calibrated", False)
            out.append(Finding("landscape-architect", c, st, "major" if (gating and s == 0) else "minor", f"VLM score {s}: {r.get('evidence', '')}", spec["source"] + " (qualitative; no number)", kind="vlm"))
    return out
