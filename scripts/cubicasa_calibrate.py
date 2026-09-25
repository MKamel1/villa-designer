"""Calibrate the critic's scale-free checks on real plans (CubiCasa5k, CC BY-NC-SA 4.0).

    python scripts/cubicasa_calibrate.py <dir-with-plan-folders> [-n 300] [--out out/cubicasa-calibration.json]

Pre-registered 2026-09-25, before any plan was looked at:
- sample: the first N plans (sorted by path) with one floor, at least one
  Bedroom and one LivingRoom, and a detectable entrance door;
- gate: the `window` and `reachability` checks stay quiet on >= 90 % of the
  sample, and every flagged plan in a reviewed subset has a named cause;
- seeded defects on each quiet plan must fail: a bedroom's windows removed
  (window), a bedroom's connections cut (reachability);
- privacy (bedroom not through a living space) and WC access are reported as
  base rates only: ordinary apartments are not bound by the pilot's brief.

Result of the first run (plans 1-300): gate FAILED, window 75.7 %, reachability
75.7 % quiet. Causes named from the images: open-plan kitchen alcoves that
borrow the living room's daylight, and garages or plant rooms with their own
external door (plus unlabelled "Undefined" spaces).

Amendment 1 (2026-09-25, written before the second sample was looked at):
- window: an open (wall-less) connection to a windowed habitable room counts;
- reachability: from every external door, with outdoor and no-stated-use rooms exempt.

The amended checks are judged on a FRESH sample (--skip 300: the next 300
eligible plans), with the same 90 % gate. Re-scoring the first sample would
be fitting to it.

Second run (plans 301-600, all "high_quality"): gate passed (window 95.7 %,
reachability 98.0 %), but seeded-defect recall fell to 283 and 278 of 300,
exposing two extraction bugs: doorways (gaps in walls) counted as open-plan
connections, and balcony doors counted as entrances. Fix 2: door openings
are masked out of open-plan detection; an entrance is a door with nothing
mapped outside it (else a hall door onto a mapped porch). The final gate is
judged on plans 601-900 (--skip 600).

Third run (plans 601-900): window PASSED (95.0 %), reachability FAILED
(87.3 %). The cause, found on plan high_quality/9480, was not door matching
(11 of 12 doors reach two rooms): reachability started from a plant-room door
while the real front door opens onto a mapped porch. Amendment 3: the outside
is one node, joined to every mapped outdoor space and every external door;
reachability runs from it. Judged on plans 901-1200 (--skip 900); the window
check is unchanged and is re-reported there too.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

from archpipe.concept import critic, cubicasa as C

GATE = 0.90


def evaluate(folders, n, skip=0):
    rows, skipped = [], {"floors": 0, "no_bed_or_living": 0, "no_entrance": 0, "parse_error": 0}
    for f in folders:
        if len(rows) >= n:
            break
        try:
            floors = C.parse(f / "model.svg")
        except Exception:
            skipped["parse_error"] += 1
            continue
        if len(floors) != 1:
            skipped["floors"] += 1
            continue
        g = C.graph(floors[0])
        types = set(g["types"].values())
        if "Bedroom" not in types or not types & {"LivingRoom", "Lounge"}:
            skipped["no_bed_or_living"] += 1
            continue
        if not g["entrance"]:
            skipped["no_entrance"] += 1
            continue
        if skip:
            skip -= 1
            continue
        checks = {c["check"]: c for c in critic.graph_checks(g)}
        checks["window"] = C.window_check(g)
        bed = next(r for r, t in g["types"].items() if t == "Bedroom")
        m1 = copy.deepcopy(g)
        m1["windows"][bed] = 0
        m2 = copy.deepcopy(g)
        m2["connections"] = [e for e in m2["connections"] if bed not in e]
        rows.append({"plan": f"{f.parent.name}/{f.name}", "subset": f.parent.name, "rooms": len(g["rooms"]),
                     "status": {k: c["status"] for k, c in checks.items()},
                     "flagged": {k: c.get("rooms") for k, c in checks.items() if c["status"] == "fail"},
                     "mutation_window_fails": C.window_check(m1)["status"] == "fail",
                     "mutation_reach_fails": any(c["check"] == "reachability" and c["status"] == "fail"
                                                 for c in critic.graph_checks(m2))})
    return rows, skipped


def summarise(rows, skipped):
    n = len(rows)
    rate = lambda k: sum(r["status"][k] != "fail" for r in rows) / n if n else 0.0
    s = {"sample": n, "skipped": skipped,
         "quiet_rate": {k: round(rate(k), 3) for k in ("window", "reachability", "private_access", "wc_access")},
         "mutation_detected": {"window": sum(r["mutation_window_fails"] for r in rows),
                               "reachability": sum(r["mutation_reach_fails"] for r in rows)},
         "gate": GATE,
         "by_subset": {s: {k: round(sum(r["status"][k] != "fail" for r in rows if r["subset"] == s) /
                                    max(1, sum(r["subset"] == s for r in rows)), 3) for k in ("window", "reachability")}
                       | {"n": sum(r["subset"] == s for r in rows)} for s in sorted({r["subset"] for r in rows})}}
    s["gate_pass"] = n > 0 and s["quiet_rate"]["window"] >= GATE and s["quiet_rate"]["reachability"] >= GATE
    return s


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root", type=Path)
    ap.add_argument("-n", type=int, default=300)
    ap.add_argument("--skip", type=int, default=0, help="eligible plans to skip (held-out sample)")
    ap.add_argument("--out", type=Path, default=Path("out/cubicasa-calibration.json"))
    a = ap.parse_args(argv)
    folders = sorted({p.parent for p in a.root.rglob("model.svg")})
    rows, skipped = evaluate(folders, a.n, a.skip)
    s = summarise(rows, skipped)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps({"summary": s, "plans": rows}, indent=1), encoding="utf-8")
    print(json.dumps(s, indent=1))
    return 0 if s["gate_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
