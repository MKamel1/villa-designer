"""Precedent statistics for the landscape method (lane LDP): load, validate, derive and freeze target ranges.

Data lives in knowledge/landscape/precedents/{south,north}.json (one record per garden, two independent
measurement passes A and B), d1.json (current D1 garden) and targets.json (frozen ranges). Schema: docs/lanes/LDP.md.
Policy numbers here (spread limits, minimum n) are ours, not published standards.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from statistics import median

DATA = Path(__file__).resolve().parents[4] / "knowledge/landscape/precedents"
SETS = ("south", "north")

# Metrics read off a SCALED PLAN (numeric). A garden without a scaled plan may not carry these.
PLAN_METRICS = (
    "area_m2", "hard_share", "soft_share", "water_share", "n_rooms", "room_area_mean_m2",
    "path_primary_m", "path_secondary_m", "trees_per_100m2", "drift_size_median",
    "layer_canopy", "layer_shrub", "layer_ground", "species_per_100m2", "enclosure_ratio",
)
# Counted/classified from photographs or text; allowed on photo-only gardens (flagged as such).
QUALITATIVE = ("privacy_approach",)
# Shares that must sum to 1 within tolerance when all are given.
SURFACE = ("hard_share", "soft_share", "water_share")
LAYERS = ("layer_canopy", "layer_shrub", "layer_ground")
SUM_TOL = 0.06          # policy: two independent readings of a plan never sum exactly
SPREAD_LIMIT = 0.25     # policy: metric dropped if median relative A/B disagreement exceeds this
GARDEN_LIMIT = 0.50     # policy: a garden's value for a metric is excluded if A/B disagree by more than this
MIN_N = 6               # policy: fewer usable gardens than this gives no range (GAP)


def load(name: str) -> list[dict]:
    return json.loads((DATA / f"{name}.json").read_text())["gardens"]


def validate_garden(g: dict) -> list[str]:
    """Return problems (empty = valid). Fail closed: unknown metric names, plan metrics on photo-only gardens,
    missing source URL, share sums, negative numbers."""
    p = []
    for k in ("id", "name", "page_url", "scaled_plan", "passes"):
        if k not in g:
            p.append(f"{g.get('id','?')}: missing {k}")
    if p:
        return p
    if not str(g["page_url"]).startswith("http"):
        p.append(f"{g['id']}: page_url is not a URL")
    if set(g["passes"]) != {"A", "B"}:
        p.append(f"{g['id']}: needs exactly passes A and B")
        return p
    known = set(PLAN_METRICS) | set(QUALITATIVE)
    for ps, vals in g["passes"].items():
        for m, v in vals.items():
            if m not in known:
                p.append(f"{g['id']}/{ps}: unknown metric {m}")
            elif v is None:
                continue
            elif m in PLAN_METRICS:
                if not g["scaled_plan"]:
                    p.append(f"{g['id']}/{ps}: {m} given but the garden has no scaled plan")
                if not isinstance(v, (int, float)) or v < 0:
                    p.append(f"{g['id']}/{ps}: {m}={v!r} is not a non-negative number")
        for grp in (SURFACE, LAYERS):
            vs = [vals.get(m) for m in grp]
            if all(isinstance(v, (int, float)) for v in vs) and abs(sum(vs) - 1) > SUM_TOL:
                p.append(f"{g['id']}/{ps}: {'+'.join(grp)} sums to {sum(vs):.2f}, not 1")
    return p


def validate_set(gardens: list[dict]) -> list[str]:
    ids = [g.get("id") for g in gardens]
    p = [f"duplicate id {i}" for i in set(ids) if ids.count(i) > 1]
    for g in gardens:
        p += validate_garden(g)
    return p


def garden_value(g: dict, metric: str):
    """Mean of the two passes, or None when either is missing or they disagree by more than GARDEN_LIMIT."""
    a, b = g["passes"]["A"].get(metric), g["passes"]["B"].get(metric)
    if not all(isinstance(v, (int, float)) for v in (a, b)):
        return None
    m = (a + b) / 2
    if m == 0:
        return 0.0 if a == b else None
    return m if abs(a - b) / m <= GARDEN_LIMIT else None


def spread(gardens: list[dict], metric: str) -> dict:
    """Median relative A/B disagreement over gardens that have both readings, and n."""
    rel = []
    for g in gardens:
        a, b = g["passes"]["A"].get(metric), g["passes"]["B"].get(metric)
        if all(isinstance(v, (int, float)) for v in (a, b)):
            m = (a + b) / 2
            rel.append(0.0 if m == 0 and a == b else (abs(a - b) / m if m else 1.0))
    return {"n_pairs": len(rel), "median_rel_spread": round(median(rel), 3) if rel else None}


def quantile(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    i = (len(xs) - 1) * q
    lo = int(i)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (i - lo)


def derive(gardens: list[dict]) -> dict:
    """Per metric: interquartile range of garden means, or a GAP with the reason (spread too large / too few)."""
    out = {}
    for m in PLAN_METRICS:
        sp = spread(gardens, m)
        vals = [v for g in gardens if (v := garden_value(g, m)) is not None]
        rec = {**sp, "n_usable": len(vals)}
        if sp["median_rel_spread"] is not None and sp["median_rel_spread"] > SPREAD_LIMIT:
            rec.update(status="GAP", reason=f"A/B spread {sp['median_rel_spread']} > {SPREAD_LIMIT}")
        elif len(vals) < MIN_N:
            rec.update(status="GAP", reason=f"fewer than {MIN_N} usable gardens")
        else:
            rec.update(status="range", q1=round(quantile(vals, .25), 3), median=round(quantile(vals, .5), 3),
                       q3=round(quantile(vals, .75), 3), min=round(min(vals), 3), max=round(max(vals), 3))
        out[m] = rec
    return out


def content_sha(t: dict) -> str:
    body = {k: v for k, v in t.items() if k != "content_sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def check_frozen(path: Path | None = None, expected_file_sha256: str | None = None) -> list[str]:
    """Problems with the frozen targets file: content hash mismatch, or file hash differs from the one recorded
    in docs/lanes/LDP.md (pass it in). Any edit after freezing is a problem; there is no re-freeze path."""
    path = path or DATA / "targets.json"
    raw = path.read_bytes()
    t = json.loads(raw)
    p = []
    if t.get("content_sha256") != content_sha(t):
        p.append("targets.json content hash does not match its body (edited after freezing)")
    if expected_file_sha256 and hashlib.sha256(raw).hexdigest() != expected_file_sha256:
        p.append("targets.json file sha256 differs from the one recorded in docs/lanes/LDP.md")
    return p


def position(value: float, rec: dict) -> str:
    """Where a measured value sits against a derived range: below / inside / above, or 'no range' for a GAP."""
    if rec.get("status") != "range":
        return "no range"
    if value < rec["q1"]:
        return "below"
    return "above" if value > rec["q3"] else "inside"
