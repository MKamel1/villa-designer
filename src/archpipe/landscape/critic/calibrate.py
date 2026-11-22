"""Calibration arithmetic for the landscape critics: computed criteria (seeded set 1, held-out set 2, D1, precedents)
and the VLM runs. Writes knowledge/landscape/critic/calibration.json. Rules are in PREREG.md; nothing here tunes a check."""
from __future__ import annotations

import json
import math
from collections import defaultdict

from . import computed as C, seeds, seeds_heldout as H, precedents as P
from .common import KNOW, Finding

OWNER = {}      # criterion -> critic, filled while scoring


def run_all(layout):
    out = []
    for fn in (C.architect, C.horticulturist, C.user, C.climate): out += fn(layout)
    return out


def table(findings):
    """criterion -> worst status (fail > warn > not_evaluated > pass), plus owner critic."""
    rank = {"fail": 3, "warn": 2, "not_evaluated": 1, "pass": 0}
    t = {}
    for f in findings:
        OWNER[f.criterion] = f.critic
        if f.criterion not in t or rank[f.status] > rank[t[f.criterion]]: t[f.criterion] = f.status
    return t


def wilson_lower(k, n, z=1.645):
    """One-sided 95 % lower confidence bound of a proportion k/n."""
    if n == 0: return None
    p = k / n; d = 1 + z * z / n
    return round((p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d, 3)


def seeded(defects, make, base_t):
    rows, caught = [], defaultdict(list)
    for k, (fn, expect) in defects.items():
        t = table(run_all(make(k)))
        for e in expect:
            clean = base_t.get(e) in (None, "pass")
            ok = t.get(e) in ("fail", "warn")
            rows.append({"defect": k, "criterion": e, "critic": OWNER.get(e), "base_status": base_t.get(e), "status": t.get(e), "excluded_base_not_clean": not clean, "caught": bool(ok and clean)})
            if clean: caught[e].append(ok)
    return rows


def main():
    base_t = table(run_all(seeds.base()))
    s1 = seeded(seeds.DEFECTS, seeds.make, base_t)
    s2 = seeded(H.HELD, H.make, base_t)
    d1 = json.loads((KNOW / "critic/d1-layout.json").read_text())
    d1f = run_all(d1)
    d1_t = table(d1f)
    good = {}
    for k in P.ALL:
        lay = json.loads((KNOW / f"critic/precedent-layouts/{k}.json").read_text())
        good[k] = table(C.architect(lay))
    crit = {}
    names = set(OWNER)
    for c in sorted(names):
        r1 = [r for r in s1 if r["criterion"] == c and not r["excluded_base_not_clean"]]
        r2 = [r for r in s2 if r["criterion"] == c and not r["excluded_base_not_clean"]]
        ev = [t[c] for t in good.values() if c in t and t[c] != "not_evaluated"]
        ff = sum(1 for s in ev if s == "fail")
        rec_all = [r["caught"] for r in r1 + r2]
        rec2 = [r["caught"] for r in r2]
        n_bad = len(rec_all)
        recall = sum(rec_all) / n_bad if n_bad else None
        calibrated = bool(n_bad >= 2 and recall is not None and recall >= 0.9 and len(ev) >= 5 and ff / len(ev) <= 0.10)
        status = "calibrated" if calibrated else ("recall-only (no evaluable professional known-good)" if len(ev) == 0 and n_bad else ("no seeded defect targets it" if not n_bad else "missed A3"))
        crit[c] = {"critic": OWNER[c], "seeded_set1": {"n": len(r1), "caught": sum(r["caught"] for r in r1)}, "seeded_heldout": {"n": len(r2), "caught": sum(rec2)},
                   "recall": None if recall is None else round(recall, 3), "recall_lower95": wilson_lower(sum(rec_all), n_bad),
                   "known_good": {"evaluated": len(ev), "false_fail": ff, "false_fail_rate": None if not ev else round(ff / len(ev), 3), "false_fail_items": [k for k, t in good.items() if t.get(c) == "fail"]},
                   "d1_status": d1_t.get(c), "calibrated": calibrated, "status": status}
    vf = KNOW / "critic/vlm-calibration.json"
    if vf.exists():
        v = json.loads(vf.read_text())
        for c, info in v["gate_selection_tuning"].items():
            ho = v.get("held_out", {}).get("per_criterion", {}).get(c, {})
            crit[c] = {"critic": "landscape-architect", "kind": "vlm", "tuning": info, "held_out": ho, "calibrated": False,
                       "status": "demoted to advisory: failed the pre-registered gate rule on the tuning half (no gating criterion)" if not info["gates"] else "gated on tuning; see held-out"}
    per_critic = {}
    for who in ("landscape-architect", "horticulturist", "user", "climate"):
        rows = [r for r in s1 + s2 if r["critic"] == who and not r["excluded_base_not_clean"]]
        by_def = defaultdict(list)
        for r in rows: by_def[r["defect"]].append(r["caught"])
        n = len(by_def); k = sum(any(v) for v in by_def.values())
        h_rows = [r for r in s2 if r["critic"] == who and not r["excluded_base_not_clean"]]
        hd = defaultdict(list)
        for r in h_rows: hd[r["defect"]].append(r["caught"])
        verd_bad_d1 = any(f.status == "fail" and f.severity in ("blocking", "major") for f in d1f if f.critic == who)
        gverd = [any(f.status == "fail" and f.severity in ("blocking", "major") for f in C.architect(json.loads((KNOW / f"critic/precedent-layouts/{k2}.json").read_text()))) for k2 in P.ALL] if who == "landscape-architect" else []
        per_critic[who] = {"seeded_defects_targeting": n, "caught_any_target": k, "recall": None if not n else round(k / n, 3), "recall_lower95": wilson_lower(k, n),
                           "heldout": {"n": len(hd), "caught": sum(any(v) for v in hd.values())}, "d1_verdict_fail": verd_bad_d1,
                           "known_good_verdict_fail": sum(gverd) if gverd else None, "known_good_n": len(gverd) or 0,
                           "false_fail": None if not gverd else round(sum(gverd) / len(gverd), 3)}
    out = {"schema": "ldc-calibration/1", "prereg": "knowledge/landscape/critic/PREREG.md", "criteria": crit, "critics": per_critic,
           "seeded_set1": s1, "seeded_set2": s2, "base_status": base_t, "precedent_statuses": good,
           "d1": [{"criterion": f.criterion, "status": f.status, "critic": f.critic, "evidence": f.evidence} for f in d1f if f.status in ("fail", "warn")]}
    (KNOW / "critic/calibration.json").write_text(json.dumps(out, indent=1) + "\n")
    return out


if __name__ == "__main__":
    o = main()
    print(json.dumps(o["critics"], indent=1))
