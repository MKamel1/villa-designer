"""Second precedent target file (targets-2.json, 2026-11-22): adds south2/north2 gardens (planted small gardens and
courtyards) to the first-pass sets. The first file (targets.json) stays frozen and untouched; this one is separately
hashed and refuses overwrite. Groups: <set>_combined (first pass + new) and <set>2_only (new gardens, tagged by climate).
Policy numbers are those of __init__ (ours, not published standards)."""
from __future__ import annotations

import hashlib
import json
from collections import Counter

from . import (DATA, GARDEN_LIMIT, MIN_N, PLAN_METRICS, SIZE_BAND, SIZE_FREE, SPREAD_LIMIT, WIDE_BAND, content_sha,
               derive, load)

NAME = "targets-2.json"


def _tally(gs: list[dict], key: str) -> dict:
    """Qualitative metric (counts, no range): value per garden if both passes agree, else 'disagree'."""
    c = Counter()
    for g in gs:
        a, b = g["passes"]["A"].get(key), g["passes"]["B"].get(key)
        if a is None and b is None:
            continue
        c[a if a == b else "disagree"] += 1
    return {"n": sum(c.values()), "counts": dict(c)}


def build_targets_2(date: str) -> dict:
    out = {"date": date, "supersedes": None, "note": "targets.json remains frozen and in force; this file only ADDS ranges",
           "policy": {"spread_limit": SPREAD_LIMIT, "garden_limit": GARDEN_LIMIT, "min_n": MIN_N,
                      "size_band_m2": SIZE_BAND, "wide_band_m2_density_only": WIDE_BAND}, "groups": {}}
    for s in ("south", "north"):
        old, new = load(s), load(f"{s}2")
        for gname, gs in ((f"{s}_combined", old + new), (f"{s}2_only", new)):
            strict, wide = derive(gs, SIZE_BAND[s]), derive(gs, WIDE_BAND[s])
            out["groups"][gname] = {
                "n_gardens": len(gs),
                "metrics": {m: ({**wide[m], "size_matched": False} if m in SIZE_FREE else {**strict[m], "size_matched": True})
                            for m in PLAN_METRICS},
                "privacy_approach": _tally(gs, "privacy_approach"),
                "water_edge": _tally(gs, "water_edge"),
                "climate_counts": dict(Counter(g.get("climate") or "first-pass-unspecified" for g in gs)),
            }
    return out


def freeze2(date: str) -> str:
    path = DATA / NAME
    if path.exists():
        raise FileExistsError(f"{NAME} is frozen; it must not be regenerated or tuned")
    t = build_targets_2(date)
    t["content_sha256"] = content_sha(t)
    path.write_text(json.dumps(t, indent=1, sort_keys=True) + "\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()
