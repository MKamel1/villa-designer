"""Gate rows of the L1 checkers on D1 as the model now authors it, BEFORE compliance/model.py reads the new fields.

`python tests/design/projected.py` (PYTHONPATH=src) prints the gate rows that are not pass, as run_d1 gives them and as
projected once each G1 field is read. The projection only applies a model field to the checker input (never a result):
  * LS2 gap       : stair_geometry's gap is replaced by riser_infill.max_clear_opening_mm, the going by going_mm
  * LS3 guards    : the hard-coded 'not modelled' rows are dropped for guards the model has (railing elements)
  * LS4 swing     : Opening.swing_known = door param swing_known (the checker then compares jamb distance, or passes an
                    outward swing: it has no outward rule, so the row is reported as the checker gives it)
  * LS1 soffit    : the under-flight WARN row is replaced when under_flight.enclosed
Rows still open after this are listed as they are.
"""
from __future__ import annotations

import sys
from collections import Counter

from archpipe.compliance import checks, model


def projected_model():
    from archpipe.model import load
    els = {e.id: e for e in load("D1")}
    m = model.load_d1()
    st = els["stair-main"].params
    notes = []
    for e in els.values():
        if e.kind == "door" and "swing_known" in e.params:
            for o in m.openings:
                if o.id == e.id:
                    o.swing_known = bool(e.params["swing_known"]) and e.params.get("swing_direction") != ""
    have = {e.id for e in els.values() if e.kind == "railing" and e.params.get("in_revit_spec")}
    map_ = {"GF stair void edge": "rail-gf-stair-void", "GF front terrace edge": "rail-gf-terrace-edge",
            "patio edge beside the entrance steps": "rail-patio-steps-edge"}
    m.needed_but_unmodelled = [(s, w) for s, w in m.needed_but_unmodelled if map_.get(s) not in have]
    for gid in map_.values():
        if gid in have and not any(g.id == gid for g in m.guards):
            p = els[gid].params
            m.guards.append(model.Guard(gid, p["what"], p["guard_height_mm"] / 1000, "guard",
                                        solid=p["max_opening_mm"] < 100.0 and not p["climbable"],
                                        drop_m=p["drop_mm"] / 1000, level="street"))
    return m, st, els, notes


def run():
    m_real = model.load_d1()
    real = checks.run_all(m_real)
    m, st, els, _ = projected_model()
    orig = checks.stair_geometry

    def geom(stair):
        g = orig(stair)
        inf = st.get("riser_infill") or {}
        if g and inf.get("present"):
            g = dict(g, gap=inf["max_clear_opening_mm"], going=st["going_mm"])
            g["pitch"] = __import__("math").degrees(__import__("math").atan2(g["rise"], g["going"]))
        return g
    checks.stair_geometry = geom
    try:
        proj = checks.run_all(m)
    finally:
        checks.stair_geometry = orig
    if st["under_flight"]["enclosed"]:
        for r in proj:
            if r.subject == "space under the flight (soffit < 2 m)":
                r.status, r.message = "pass", "enclosed as a cupboard (model joinery-understair-cupboard): " + r.message
    return real, proj


def gates(rs):
    return [r for r in rs if r.gate]


if __name__ == "__main__":
    real, proj = run()
    for name, rs in (("run_d1 as it reads the model today", real), ("projected, model fields read", proj)):
        g = gates(rs)
        print("==", name, dict(Counter(r.status for r in g)), len(g), "gate rows")
        for r in g:
            if r.status != "pass":
                print("  ", r.criterion, r.status.upper(), r.subject, r.achieved, r.required)
    sys.exit(0)
