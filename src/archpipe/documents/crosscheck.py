"""SC1 cross-check: schedule counts equal model counts, and the tags drawn on the sheets equal the schedules."""
from __future__ import annotations

from archpipe.contracts import DesignElement

from . import schedules


def sc1(els: list[DesignElement], plan_reports: list[dict] | None = None, revit_counts: dict | None = None) -> dict:
    """Return {checks: [...], ok: bool}. Each check: name, expected, got, ok.

    plan_reports: reports from plans.render_plan (tags drawn per level). revit_counts: optional
    {"door":n,"window":n,"room":n} read back from Revit schedules; absent means not evaluated.
    """
    model = {k: sum(1 for e in els if e.kind == k) for k in ("door", "window", "room")}
    rows = {"door": len(schedules.door_schedule(els)), "window": len(schedules.window_schedule(els)),
            "room": len(schedules.room_schedule(els))}
    checks = []
    for k in model:
        checks.append({"name": "%s schedule rows == model %ss" % (k, k), "expected": model[k], "got": rows[k],
                       "ok": rows[k] == model[k]})
    sched_ids = {"door": {r["id"] for r in schedules.door_schedule(els)},
                 "window": {r["id"] for r in schedules.window_schedule(els)}}
    for k in ("door", "window"):
        ids = {e.id for e in els if e.kind == k}
        checks.append({"name": "%s schedule ids == model ids" % k, "expected": len(ids), "got": len(sched_ids[k]),
                       "ok": ids == sched_ids[k]})
    tags = schedules.tag_numbers(els)
    checks.append({"name": "tags unique", "expected": len(tags), "got": len(set(tags.values())),
                   "ok": len(set(tags.values())) == len(tags)})
    if plan_reports is not None:
        for k, key in (("door", "door_tags"), ("window", "window_tags"), ("room", "room_tags")):
            drawn = sum(len(r[key]) for r in plan_reports)
            ids = [t["id"] for r in plan_reports for t in r[key]]
            checks.append({"name": "%s tags drawn on plans == schedule rows" % k, "expected": rows[k], "got": drawn,
                           "ok": drawn == rows[k] and len(set(ids)) == drawn})
    if revit_counts is None:
        checks.append({"name": "Revit schedule counts == model counts", "expected": model, "got": None, "ok": None,
                       "note": "not_evaluated: Revit not run"})
    else:
        for k in model:
            checks.append({"name": "Revit %s schedule == model" % k, "expected": model[k], "got": revit_counts.get(k),
                           "ok": revit_counts.get(k) == model[k]})
    return {"checks": checks, "ok": all(c["ok"] is not False for c in checks),
            "evaluated": all(c["ok"] is not None for c in checks)}
