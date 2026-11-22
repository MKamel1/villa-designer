"""Calibration arithmetic: gate selection on the tuning half, verdicts, confusion vs human grades."""
from __future__ import annotations

import glob
import json
from collections import Counter, defaultdict
from pathlib import Path

from . import labels as L
from . import verdict as V

FINALS = "C:/Users/mmbka/arch-pipeline/out/villa/finals-2026-10-15"


def png_for(view: str, finals: str = FINALS) -> str:
    return sorted(glob.glob(f"{finals}/{view}-*.png"))[0]


def select_gates(rows: dict[str, dict], labels: dict, tuning: list[str], criteria=V.VLM_CRITERIA,
                 min_sep: float = 0.30) -> dict:
    """rows: view -> merged scores. A VLM criterion gates iff separation >= min_sep and no should_pass
    view scores 0 (rubric.scoring.gate_selection). R10 is always gating (it has a pixel part)."""
    info = {}
    bad = [v for v in tuning if L.tier(labels[v]["grade"]) == "must_fail"]
    good = [v for v in tuning if L.tier(labels[v]["grade"]) == "should_pass"]
    for c in criteria:
        def sc(v):
            return rows[v].get(c, {}).get("score")
        bad_lt2 = [sc(v) is not None and sc(v) < 2 for v in bad]
        good_lt2 = [sc(v) is not None and sc(v) < 2 for v in good]
        sep = (sum(bad_lt2) / max(1, len(bad))) - (sum(good_lt2) / max(1, len(good)))
        good0 = any(sc(v) == 0 for v in good)
        info[c] = dict(separation=round(sep, 3), bad_lt2=f"{sum(bad_lt2)}/{len(bad)}",
                       good_lt2=f"{sum(good_lt2)}/{len(good)}", good_zero=good0,
                       gates=(sep >= min_sep and not good0) or c == "R10")
    return info


def confusion(verdicts: dict[str, str], labels: dict, views: list[str]) -> dict:
    """Per-grade pass/fail counts, tier recall and false-fail."""
    by_grade: dict[str, Counter] = defaultdict(Counter)
    for v in views:
        by_grade[labels[v]["grade"]][verdicts[v]] += 1
    must = [v for v in views if L.tier(labels[v]["grade"]) == "must_fail"]
    good = [v for v in views if L.tier(labels[v]["grade"]) == "should_pass"]
    cm = [v for v in views if labels[v]["grade"][0] in "CDF"]
    seeded = [v for v in views if labels[v].get("false_pass")]

    def rate(group, want):
        return (sum(verdicts[v] == want for v in group), len(group))
    rec = rate(must, "fail")
    ff = rate(good, "fail")
    return dict(by_grade={g: dict(c) for g, c in sorted(by_grade.items(), key=lambda kv: L.GRADE_ORDER.index(kv[0]))},
                recall_must_fail=rec, false_fail_should_pass=ff,
                recall_c_or_worse=rate(cm, "fail"), recall_seeded_false_passes=rate(seeded, "fail"),
                middle_fail=rate([v for v in views if L.tier(labels[v]["grade"]) == "middle"], "fail"))


def load_vlm_dir(d: str | Path) -> dict[str, dict]:
    """Load cached VLM results. `d` may be several directories joined by ',' (scores are merged per view)."""
    out: dict[str, dict] = {}
    for one in str(d).split(","):
        for p in sorted(Path(one).glob("v*.json")):
            j = json.loads(p.read_text(encoding="utf-8"))
            if j["view"] in out:
                out[j["view"]]["scores"].update(j["scores"])
                if j.get("status") != "ok":
                    out[j["view"]]["status"] = j["status"]
            else:
                out[j["view"]] = j
    return out


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for k of n (two-sided 95 % by default); (0, 1) when n is 0.
    The L3 groups hold 2-8 views, so every rate is reported with this interval."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def pooled(*groups: dict) -> dict:
    """Add `confusion()` outputs' (k, n) pairs so the audit set and an extension set read as one table."""
    keys = ("recall_must_fail", "false_fail_should_pass", "recall_c_or_worse", "middle_fail")
    out = {}
    for key in keys:
        k = sum(g[key][0] for g in groups)
        n = sum(g[key][1] for g in groups)
        out[key] = dict(k=k, n=n, wilson95=tuple(round(x, 3) for x in wilson(k, n)))
    return out
