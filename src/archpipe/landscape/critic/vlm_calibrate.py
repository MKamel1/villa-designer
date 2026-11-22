"""Gate selection (tuning half) and scoring (held-out) for the VLM plan criteria, by the PREREG.md rules."""
from __future__ import annotations

import json
from .common import KNOW
from .calibrate import wilson_lower

RUNS = KNOW / "critic/runs"


def load(split):
    return [json.loads(f.read_text()) for f in sorted((RUNS / split).glob("*.json"))]


def sc(r, c): return r["scores"].get(c, {}).get("score")


def select_gates(rows, crits, min_sep=0.30):
    bad = [r for r in rows if r["label"] == "bad"]; good = [r for r in rows if r["label"] == "good"]
    info = {}
    for c in crits:
        b = [sc(r, c) is not None and sc(r, c) < 2 for r in bad]; g = [sc(r, c) is not None and sc(r, c) < 2 for r in good]
        sep = sum(b) / max(1, len(b)) - sum(g) / max(1, len(g))
        g0 = any(sc(r, c) == 0 for r in good)
        info[c] = {"bad_lt2": f"{sum(b)}/{len(b)}", "good_lt2": f"{sum(g)}/{len(g)}", "separation": round(sep, 3), "good_zero": g0, "gates": sep >= min_sep and not g0}
    return info


def verdict(r, gates):
    s = {c: sc(r, c) for c in gates}
    return "fail" if any(v == 0 for v in s.values()) or sum(v == 1 for v in s.values()) >= 2 else "pass"


def main():
    rub = json.loads((KNOW / "critic/rubric.json").read_text())
    crits = list(rub["criteria"])
    tun = load("tuning")
    info = select_gates(tun, crits)
    gates = [c for c, v in info.items() if v["gates"]]
    out = {"rubric": rub["version"], "gate_selection_tuning": info, "gating": gates, "tuning_verdicts": {r["item"]: (r["label"], verdict(r, gates) if gates else "n/a") for r in tun}}
    try:
        ho = load("held_out")
    except Exception:
        ho = []
    if ho:
        bad = [r for r in ho if r["label"] == "bad"]; good = [r for r in ho if r["label"] == "good"]
        vb = [verdict(r, gates) == "fail" for r in bad]; vg = [verdict(r, gates) == "fail" for r in good]
        per = {c: {"bad_lt2": sum(sc(r, c) is not None and sc(r, c) < 2 for r in bad), "good_lt2": sum(sc(r, c) is not None and sc(r, c) < 2 for r in good), "good_zero": sum(sc(r, c) == 0 for r in good)} for c in crits}
        out["held_out"] = {"n_bad": len(bad), "n_good": len(good), "recall": round(sum(vb) / max(1, len(bad)), 3), "recall_lower95": wilson_lower(sum(vb), len(bad)),
                           "false_fail": round(sum(vg) / max(1, len(good)), 3), "per_criterion": per, "verdicts": {r["item"]: (r["label"], verdict(r, gates) if gates else "n/a") for r in ho}}
    try:
        ph = load("photos")
    except Exception:
        ph = []
    if ph:
        bad = [r for r in ph if r["label"] == "bad"]; good = [r for r in ph if r["label"] == "good"]
        out["photos"] = {"n_bad_renders": len(bad), "n_good_photos": len(good), "confound": "photograph vs CG render; D1 grades are for asset defects",
                         "per_criterion": {c: {"bad_lt2": f"{sum(sc(r, c) is not None and sc(r, c) < 2 for r in bad)}/{len(bad)}", "good_lt2": f"{sum(sc(r, c) is not None and sc(r, c) < 2 for r in good)}/{len(good)}",
                                               "good_zero": sum(sc(r, c) == 0 for r in good)} for c in rub["photo_criteria"]}}
    return out


if __name__ == "__main__":
    print(json.dumps(main(), indent=1))
