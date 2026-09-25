"""Calibrate the dimensioned room checks (AREA-01, DIM-01) on real apartments with metric geometry.

    python scripts/swiss_calibrate.py <swiss-dwellings-v3.0.0 dir> [-n 300] [--skip 0] [--out FILE]

Data: Swiss Dwellings v3.0.0 (Archilyse AG), https://zenodo.org/records/7788422, CC BY 4.0.
Only aggregate results are stored in the repository.

Pre-registered 2026-09-25, before any apartment was looked at:
- sample: the first N residential apartments in apartment_id order that have at least one
  BEDROOM or ROOM and at least one LIVING_ROOM / LIVING_DINING / DINING;
- occupancy mapping: BEDROOM and ROOM (the Swiss "Zimmer") -> bedroom_single (the dataset does
  not say which bedrooms are doubles, so the least strict bedroom minimum is used);
  LIVING_ROOM, LIVING_DINING, DINING -> living/dining; OFFICE -> study; KITCHEN -> kitchen
  (excepted by IRC R304); everything else is not a habitable room and is ignored;
- each apartment is rotated to its dominant wall direction before the rules run (the width rule
  measures along the drawing axes, as our own models are drawn);
- the checks are the real rule functions rules.r_room_min_area and rules.r_room_min_width;
- gate: both quiet on >= 90 % of apartments;
- seeded defects on every apartment must be caught: one bedroom scaled to 7.0 m2 (area) and one
  living room compressed to 2.0 m across (width).
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

from archpipe import model, rules

MAP = {"BEDROOM": "bedroom_single", "ROOM": "bedroom_single", "LIVING_ROOM": "living", "LIVING_DINING": "living",
       "DINING": "dining", "OFFICE": "study", "KITCHEN": "kitchen"}
LIVING = {"LIVING_ROOM", "LIVING_DINING", "DINING"}
GATE = 0.90
csv.field_size_limit(10 ** 9)


def apartments(path: Path, n: int, skip: int):
    """Yield (apartment_id, [(subtype, polygon)]) for eligible apartments in id order."""
    rows = defaultdict(list)
    with open(path / "geometries.csv", newline="") as f:
        for r in csv.DictReader(f):
            if r["entity_type"] == "area" and r["unit_usage"] == "RESIDENTIAL" and r["entity_subtype"] in MAP:
                rows[r["apartment_id"]].append((r["entity_subtype"], r["geometry"]))
    taken = 0
    for aid in sorted(rows):
        subs = {s for s, _ in rows[aid]}
        if not subs & {"BEDROOM", "ROOM"} or not subs & LIVING:
            continue
        if skip:
            skip -= 1
            continue
        yield aid, [(s, wkt.loads(g)) for s, g in rows[aid]]
        taken += 1
        if taken >= n:
            return


def dominant_angle(polys) -> float:
    """Length-weighted wall direction modulo 90 degrees, in degrees."""
    acc = defaultdict(float)
    for p in polys:
        c = list(p.exterior.coords)
        for (x0, y0), (x1, y1) in zip(c, c[1:]):
            L = math.hypot(x1 - x0, y1 - y0)
            acc[round(math.degrees(math.atan2(y1 - y0, x1 - x0)) % 90.0)] += L
    return max(acc, key=acc.get) if acc else 0.0


def project(rooms):
    lv = model.Level("L00", "L00", 0, 3000)
    rs = []
    for i, (sub, poly) in enumerate(rooms):
        pts = tuple((x * 1000.0, y * 1000.0) for x, y in list(poly.exterior.coords)[:-1])
        rs.append(model.Room(f"R{i}", "L00", f"{sub} {i}", pts, MAP[sub]))
    return model.Project("swiss", levels=(lv,), rooms=tuple(rs))


def check(rooms):
    p = project(rooms)
    return ([f.message for f in rules.r_room_min_area(p, "L00")],
            [f.message for f in rules.r_room_min_width(p, "L00")])


def seeded(rooms):
    """(area defect caught, width defect caught)"""
    i = next(i for i, (s, _) in enumerate(rooms) if s in ("BEDROOM", "ROOM"))
    s, poly = rooms[i]
    small = affinity.scale(poly, math.sqrt(7.0 / poly.area), math.sqrt(7.0 / poly.area), origin="centroid")
    a = rooms[:i] + [(s, small)] + rooms[i + 1:]
    j = next(j for j, (s, _) in enumerate(rooms) if s in LIVING)
    s2, lp = rooms[j]
    x0, y0, x1, y1 = lp.bounds
    fx, fy = (2.0 / (x1 - x0), 1.0) if (x1 - x0) <= (y1 - y0) else (1.0, 2.0 / (y1 - y0))
    w = rooms[:j] + [(s2, affinity.scale(lp, fx, fy, origin="centroid"))] + rooms[j + 1:]
    return bool(check(a)[0]), bool(check(w)[1])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root", type=Path)
    ap.add_argument("-n", type=int, default=300)
    ap.add_argument("--skip", type=int, default=0)
    ap.add_argument("--out", type=Path, default=Path("out/swiss-calibration.json"))
    a = ap.parse_args(argv)
    plans = []
    for aid, rooms in apartments(a.root, a.n, a.skip):
        ang = dominant_angle([p for _, p in rooms])
        rooms = [(s, affinity.rotate(p, -ang, origin=(0, 0))) for s, p in rooms]
        area_f, width_f = check(rooms)
        sa, sw = seeded(rooms)
        plans.append({"apartment": aid, "rooms": len(rooms), "area_findings": area_f, "width_findings": width_f,
                      "seeded_area_caught": sa, "seeded_width_caught": sw})
    n = len(plans)
    s = {"sample": n, "gate": GATE,
         "quiet_rate": {"area": round(sum(not p["area_findings"] for p in plans) / n, 3),
                        "width": round(sum(not p["width_findings"] for p in plans) / n, 3)},
         "seeded_caught": {"area": sum(p["seeded_area_caught"] for p in plans),
                           "width": sum(p["seeded_width_caught"] for p in plans)}}
    s["gate_pass"] = s["quiet_rate"]["area"] >= GATE and s["quiet_rate"]["width"] >= GATE
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps({"summary": s, "plans": plans}, indent=1), encoding="utf-8")
    print(json.dumps(s, indent=1))
    return 0 if s["gate_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
