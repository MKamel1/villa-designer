"""Calibrate the wet-stack check and the principal-double-bedroom minimum on Swiss Dwellings (CC BY 4.0).

    python scripts/swiss_stack_calibrate.py <swiss-dwellings-v3.0.0 dir> stack  [-n 300] [--skip 0]
    python scripts/swiss_stack_calibrate.py <swiss-dwellings-v3.0.0 dir> double [-n 300] [--skip 0]

Pre-registered 2026-09-25, before any outcome was looked at (only floor alignment was checked:
consecutive floors of a building share coordinates, and repeated typical floors reuse one plan_id).

stack:
- unit: a pair of consecutive residential floors (by elevation) of one building whose plan_id
  DIFFERS (a repeated typical floor stacks trivially and says nothing), first N pairs in
  (building_id, elevation) order;
- check = the concept critic's wet_stack definition unchanged: every upper-floor BATHROOM lies at
  least 50 % over lower-floor wet rooms (BATHROOM, WASH_AND_DRY_ROOM); kitchens do NOT count;
- diagnostic only: the same with lower-floor KITCHENs counted as wet;
- gate: >= 90 % of pairs quiet; seeded defect per pair: one upper bathroom moved (translated) so
  its centroid sits on the centroid of the largest lower-floor dry habitable room -> must fail.

double:
- apartments with >= 2 BEDROOM/ROOM areas; the largest is the principal double (occupancy
  "bedroom": NDSS 11.5 m2 and the dwelling-wide 2.75 m first-double width), the rest single;
- checks = rules.r_room_min_area and rules.r_room_min_width, as in swiss_calibrate.py;
- gate: >= 90 % quiet; seeded defects: principal scaled to 11.0 m2, or compressed to 2.6 m across.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

from shapely import affinity, wkt
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from archpipe.execution_context import ContextError, project_context  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import swiss_calibrate as S                      # noqa: E402

from archpipe import rules                       # noqa: E402

GATE = 0.90
WET = {"BATHROOM", "WASH_AND_DRY_ROOM"}
DRY = {"LIVING_ROOM", "LIVING_DINING", "BEDROOM", "ROOM", "DINING", "OFFICE"}
csv.field_size_limit(10 ** 9)


def floors(path: Path):
    by = defaultdict(lambda: defaultdict(list))
    meta = {}
    with open(path / "geometries.csv", newline="") as f:
        for r in csv.DictReader(f):
            if r["entity_type"] == "area" and r["unit_usage"] == "RESIDENTIAL":
                key = (r["building_id"], r["floor_id"])
                by[key][r["entity_subtype"]].append(wkt.loads(r["geometry"]))
                meta[key] = (float(r["elevation"] or 0.0), r["plan_id"])
    buildings = defaultdict(list)
    for (b, fl), rooms in by.items():
        buildings[b].append((meta[(b, fl)][0], meta[(b, fl)][1], fl, rooms))
    return buildings


def stack_ok(upper, lower, wet):
    below = unary_union([p for t in wet for p in lower.get(t, [])])
    baths = upper.get("BATHROOM", [])
    return all(b.intersection(below).area >= 0.5 * b.area for b in baths) if baths else None


def run_stack(path, n, skip):
    rows = []
    for b in sorted(floors(path).items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else kv[0]):
        fls = sorted(b[1])
        for lo, up in zip(fls, fls[1:]):
            if lo[1] == up[1] or not up[3].get("BATHROOM"):
                continue
            if skip:
                skip -= 1
                continue
            lower, upper = lo[3], up[3]
            ok = stack_ok(upper, lower, WET)
            ok_k = stack_ok(upper, lower, WET | {"KITCHEN"})
            dry = [p for t in DRY for p in lower.get(t, [])]
            caught = None
            if dry:
                target = max(dry, key=lambda p: p.area).centroid
                bath = upper["BATHROOM"][0]
                moved = affinity.translate(bath, target.x - bath.centroid.x, target.y - bath.centroid.y)
                mut = dict(upper, BATHROOM=[moved] + upper["BATHROOM"][1:])
                caught = stack_ok(mut, lower, WET) is False
            rows.append({"building": b[0], "lower": lo[2], "upper": up[2], "stacked": ok, "stacked_with_kitchen": ok_k,
                         "seeded_caught": caught})
            if len(rows) >= n:
                return rows
    return rows


def run_double(path, n, skip):
    rows = []
    gen = S.apartments(path, 10 ** 9, 0)
    for aid, rooms in gen:
        beds = [i for i, (s, _) in enumerate(rooms) if s in ("BEDROOM", "ROOM")]
        if len(beds) < 2:
            continue
        if skip:
            skip -= 1
            continue
        ang = S.dominant_angle([p for _, p in rooms])
        rooms = [(s, affinity.rotate(p, -ang, origin=(0, 0))) for s, p in rooms]
        k = max(beds, key=lambda i: rooms[i][1].area)
        occ = {i: ("bedroom" if i == k else "bedroom_single") for i in beds}

        def check(rs):
            p = S.project(rs)
            p.rooms = tuple(r if int(r.id[1:]) not in occ else r.__class__(r.id, r.level, r.name, r.boundary, occ[int(r.id[1:])])
                            for r in p.rooms)
            return ([f.message for f in rules.r_room_min_area(p, "L00")], [f.message for f in rules.r_room_min_width(p, "L00")])

        a, w = check(rooms)
        s, poly = rooms[k]
        small = affinity.scale(poly, math.sqrt(11.0 / poly.area), math.sqrt(11.0 / poly.area), origin="centroid")
        x0, y0, x1, y1 = poly.bounds
        fx, fy = (2.6 / (x1 - x0), 1.0) if (x1 - x0) <= (y1 - y0) else (1.0, 2.6 / (y1 - y0))
        narrow = affinity.scale(poly, fx, fy, origin="centroid")
        sa = bool(check(rooms[:k] + [(s, small)] + rooms[k + 1:])[0])
        sw = bool(check(rooms[:k] + [(s, narrow)] + rooms[k + 1:])[1])
        rows.append({"apartment": aid, "area_findings": a, "width_findings": w, "seeded_area_caught": sa, "seeded_width_caught": sw})
        if len(rows) >= n:
            break
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root", type=Path)
    ap.add_argument("mode", choices=["stack", "double"])
    ap.add_argument("-n", type=int, default=300)
    ap.add_argument("--skip", type=int, default=0)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    try:
        project_context(
            ROOT,
            Path(__file__).resolve(),
            "swiss-stack-calibrate",
            inputs=[a.root / "geometries.csv"],
            output=a.out.parent,
            modules=["shapely"],
        )
    except ContextError as exc:
        print("PREFLIGHT FAILED: " + str(exc), file=sys.stderr)
        return 2
    if a.mode == "stack":
        rows = run_stack(a.root, a.n, a.skip)
        n = len(rows)
        seeded = [r["seeded_caught"] for r in rows if r["seeded_caught"] is not None]
        s = {"sample": n, "gate": GATE, "quiet_rate": {"wet_stack": round(sum(bool(r["stacked"]) for r in rows) / n, 3)},
             "diagnostic_quiet_rate_kitchen_counts_as_wet": round(sum(bool(r["stacked_with_kitchen"]) for r in rows) / n, 3),
             "seeded_caught": {"wet_stack": sum(seeded), "of": len(seeded)}}
        s["gate_pass"] = s["quiet_rate"]["wet_stack"] >= GATE
    else:
        rows = run_double(a.root, a.n, a.skip)
        n = len(rows)
        s = {"sample": n, "gate": GATE,
             "quiet_rate": {"area": round(sum(not r["area_findings"] for r in rows) / n, 3),
                            "width": round(sum(not r["width_findings"] for r in rows) / n, 3)},
             "seeded_caught": {"area": sum(r["seeded_area_caught"] for r in rows),
                               "width": sum(r["seeded_width_caught"] for r in rows)}}
        s["gate_pass"] = min(s["quiet_rate"].values()) >= GATE
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps({"summary": s, "rows": rows}, indent=1), encoding="utf-8")
    print(json.dumps(s, indent=1))
    return 0 if s["gate_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
