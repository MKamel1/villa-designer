"""The concept critic: one scoring path for precedents, pilot concepts and generated layouts.

Graph checks run on any room graph ({"rooms": {id: kind}, "connections", "entrance",
"sanitary"}). Geometric checks run on a layout (see layout.py). Every check names
its basis; checks with no source-backed threshold report a value and stay advisory.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .. import guidance
from .. import vocabulary as vocab
from . import layout as L

ROOT = Path(__file__).resolve().parents[3]
SANITARY_WORDS = re.compile(r"bath|powder|\bwc\b|toilet|ensuite|shower", re.I)

BASIS = {
    "private_access": "Pilot fact 'privacy': private bedroom access must bypass public entertaining rooms "
                      "(knowledge/projects/villa-pilot.json); same test as guidance.concept_checks.",
    "wc_access": "Pilot fact 'hosting' (weekly guests): a WC on the entrance level reached without entering a "
                 "private room.",
    "reachability": "Every room must be reachable from the entrance.",
    "links_built": "The layout must realise the doors its own graph intends.",
    "window": "Bedrooms, living rooms, kitchens: SLL Code for Lighting minimum average daylight factors (cards "
              "sll-min-adf-bedroom/-living/-kitchen); a room with no window cannot meet them. Study and dining are "
              "included by extension (project judgement: rooms occupied by day), not by those cards.",
    "wet_stack": "Pilot fact 'adjacencies': wet rooms proposed to stack.",
    "living_north": "Pilot fact 'views': the northern garden view is the scenario priority.",
    "within_plot": "Pilot fact 'boundary': 30 m east-west by 40 m north-south. Setbacks are not supplied.",
    "circulation_area": "Pilot area schedule circulation_m2 allowance (project figure, not a standard); halls, "
                        "landings and stairs, not the scheduled entry.",
    "upper_supported": "Project judgement: an upper room with no ground room under it needs a cantilever or "
                       "transfer, which is structural (consultant) scope; the concept must not rely on it silently.",
    "area_match": "Pilot area schedule: each room within 25 % of its scheduled area (project tolerance, not a standard).",
    "gross_area": "Pilot area schedule: available_m2 is a scenario allowance, not a legal envelope.",
    "elongation": "Card lechner-east-west-axis (qualitative): prefer a plan elongated east-west.",
}


def _check(name, status, **kw):
    return dict({"check": name, "status": status, "basis": BASIS.get(name, "")}, **kw)


def _reach(rooms, edges, start, blocked=lambda r: False):
    seen, todo = set(), [start]
    while todo:
        n = todo.pop()
        if n in seen:
            continue
        seen.add(n)
        if n != start and blocked(n):
            continue
        todo.extend(b if a == n else a for a, b in edges if n in (a, b))
    return seen


def graph_checks(g) -> list[dict]:
    rooms, edges, start = g["rooms"], g["connections"], g["entrance"]
    out = [dict(guidance.concept_checks(g)[0], basis=BASIS["private_access"])]
    san = [r for r in g.get("sanitary", []) if r in rooms and (not g.get("level") or g["level"].get(r) == g["level"].get(start))]
    if not san:
        out.append(_check("wc_access", "not_checkable", rooms=[], note="no sanitary room on the entrance level"))
    else:
        reached = _reach(rooms, edges, start, blocked=lambda r: rooms[r] == "private")
        ok = [r for r in san if r in reached]
        out.append(_check("wc_access", "pass" if ok else "fail", rooms=ok or san))
    unreached = sorted(set(rooms) - _reach(rooms, edges, start))
    out.append(_check("reachability", "fail" if unreached else "pass", rooms=unreached))
    return out


def precedent_graph(record) -> dict:
    """A precedent record with a room graph, in the critic's graph form."""
    rooms = {r["id"]: r["kind"] for r in record["rooms"]}
    san = [r["id"] for r in record["rooms"] if SANITARY_WORDS.search(r["use"] or "")]
    return {"rooms": rooms, "connections": [list(e) for e in record["adjacency"]], "entrance": record["entrance"],
            "sanitary": san}


def room_graph_precedents(root=ROOT) -> list[dict]:
    out = []
    for p in sorted((root / "knowledge" / "precedents").glob("*.json")):
        rec = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(rec, dict) and rec.get("rooms") and rec.get("adjacency") and rec.get("entrance"):
            out.append(rec)
    return out


def _kind(occ):
    if occ in vocab.CIRCULATION:
        return "circulation"
    if occ in vocab.PRIVATE:
        return "private"
    if occ in vocab.HABITABLE:
        return "public"
    return "service"


def layout_graph(layout) -> dict:
    """The graph a layout actually builds: doors that fit, plus stair links across levels."""
    edges = []
    for lid in layout["levels"]:
        doors, _, _ = L.openings(layout, lid)
        edges += [list(d["rooms"]) for d in doors if None not in d["rooms"]]
    edges += [list(v) for v in layout.get("vertical", [])]
    rooms = {rid: _kind(r["occupancy"]) for rid, r in layout["rooms"].items()}
    return {"rooms": rooms, "connections": edges, "entrance": layout["entrance"],
            "sanitary": [rid for rid, r in layout["rooms"].items() if r["occupancy"] in vocab.SANITARY],
            "level": {rid: r["level"] for rid, r in layout["rooms"].items()}}


def geometry_checks(layout, available_m2=None, circulation_m2=None) -> list[dict]:
    out, rooms = [], layout["rooms"]
    unbuilt, windows = [], {}
    for lid in layout["levels"]:
        _, wins, miss = L.openings(layout, lid)
        unbuilt += miss
        for w in wins:
            windows.setdefault(w["room"], []).append(w)
    out.append(_check("links_built", "fail" if unbuilt else "pass", links=[list(u) for u in unbuilt]))
    dark = sorted(r for r, v in rooms.items() if v["occupancy"] in vocab.HABITABLE and r not in windows)
    out.append(_check("window", "fail" if dark else "pass", rooms=dark))
    # wet stack: each upper-level sanitary room should sit mostly over a ground-level wet room
    lv = sorted(layout["levels"], key=layout["levels"].get)
    if len(lv) < 2:
        out.append(_check("wet_stack", "not_checkable", note="single level"))
    else:
        wet = lambda r: r["occupancy"] in vocab.SANITARY or r["occupancy"] == "utility"
        below = [r["rect"] for r in rooms.values() if r["level"] == lv[0] and wet(r)]
        split = []
        for rid, r in rooms.items():
            if r["level"] != lv[0] and r["occupancy"] in vocab.SANITARY:
                cover = sum(_overlap(r["rect"], b) for b in below) / L.room_area(layout, rid)
                if cover < 0.5:
                    split.append({"room": rid, "over_wet_fraction": round(cover, 2)})
        out.append(_check("wet_stack", "fail" if split else "pass", rooms=split,
                          note="pass = at least half of each upper sanitary room lies over a ground wet room "
                               "(project threshold)"))
    living = [r for r, v in rooms.items() if v["occupancy"] == "living" and v["level"] == lv[0]]
    north = [r for r in living if any(w["facing"] == "north" for w in windows.get(r, []))]
    out.append(_check("living_north", "pass" if north else ("fail" if living else "not_checkable"), rooms=north or living))
    W, D = layout["plot"]["width_m"], layout["plot"]["depth_m"]
    h = L.EXT / 2
    outside = sorted(r for r, v in rooms.items()
                     if v["rect"][0] - h < 0 or v["rect"][1] - h < 0 or v["rect"][2] + h > W or v["rect"][3] + h > D)
    out.append(_check("within_plot", "fail" if outside else "pass", rooms=outside,
                      note="Setbacks unknown: not checked."))
    gross = sum(L.room_area(layout, r) for r in rooms)
    if available_m2:
        out.append(_check("gross_area", "pass" if gross <= available_m2 else "fail",
                          gross_m2=round(gross, 1), available_m2=available_m2,
                          note="Gross measured to wall centrelines."))
    circ = sum(L.room_area(layout, r) for r, v in rooms.items()
               if v["occupancy"] in vocab.CIRCULATION and v["occupancy"] != "entrance")
    if circulation_m2:
        out.append(_check("circulation_area", "advisory", achieved_m2=round(circ, 1), allowance_m2=circulation_m2,
                          excess_m2=round(max(0.0, circ - circulation_m2), 1)))
    fp = [v["rect"] for v in rooms.values() if v["level"] == lv[0]]
    bw = max(r[2] for r in fp) - min(r[0] for r in fp)
    bd = max(r[3] for r in fp) - min(r[1] for r in fp)
    out.append(_check("elongation", "advisory", east_west_m=round(bw, 1), north_south_m=round(bd, 1),
                      ratio=round(bw / bd, 2)))
    dev = {r: round(L.room_area(layout, r) - v["target_m2"], 1) for r, v in rooms.items() if v.get("target_m2")}
    off = sorted(r for r, d in dev.items() if abs(d) > 0.25 * rooms[r]["target_m2"])
    out.append(_check("area_match", "fail" if off else "pass", rooms=off, deviation_m2=dev,
                      note="Achieved minus scheduled area per room (centreline)."))
    if len(lv) > 1:
        ground = [v["rect"] for v in rooms.values() if v["level"] == lv[0]]
        loose = []
        for r, v in rooms.items():
            if v["level"] != lv[0]:
                bare = L.room_area(layout, r) - sum(_overlap(v["rect"], g) for g in ground)
                if bare > 0.05:
                    loose.append({"room": r, "unsupported_m2": round(bare, 1)})
        out.append(_check("upper_supported", "fail" if loose else "pass", rooms=loose))
    out.append(_check("structure", "not_certified", max_room_short_side_m=round(max(
        min(v["rect"][2] - v["rect"][0], v["rect"][3] - v["rect"][1]) for v in rooms.values()), 1),
        basis="Engineering sizing and certification excluded (consultant scope)."))
    out.append(_check("cooling", "not_measured",
                      basis="Run the thermal shoebox per facade (workstation.py thermal) before choosing."))
    return out


def _overlap(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0])
    d = min(a[3], b[3]) - max(a[1], b[1])
    return max(0.0, w) * max(0.0, d)


def critique(layout, available_m2=None, circulation_m2=None) -> dict:
    checks = graph_checks(layout_graph(layout)) + geometry_checks(layout, available_m2, circulation_m2)
    fails = [c["check"] for c in checks if c["status"] == "fail"]
    return {"id": layout["id"], "parti": layout["parti"], "checks": checks, "fails": fails}


def rule_findings(spec_path) -> list[dict]:
    """The existing rule engine on the emitted spec, level by level. Legacy rules are diagnostic (rule audit)."""
    from .. import model, rules
    p = model.load(spec_path)
    out = []
    for lv in p.levels:
        for f in rules.review(p, lv.id):
            out.append({"level": lv.id, "rule": f.rule, "severity": f.severity, "where": f.where,
                        "message": f.message})
    return out
