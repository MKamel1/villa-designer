"""python -m archpipe.documents [--design D1] [--out out/documents/D1]: write the sheet set, schedules and QA."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from archpipe import model

from . import crosscheck, plans, schedules, sheetset, tables


def run(design: str, out: Path, formats=("pdf", "svg", "png")) -> dict:
    els = model.load(design)
    spec = sheetset.build(design, elements=els)
    spec["levels"] = json.loads(Path(model.api.snapshot_path(design)).read_text(encoding="utf-8")).get("levels", {})
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in (("door", schedules.door_schedule(els)), ("window", schedules.window_schedule(els)),
                       ("room", schedules.room_schedule(els))):
        (out / ("schedule-%s.csv" % name)).write_text(schedules.to_csv(rows), encoding="utf-8")
    md = "".join(schedules.to_md(r, t) + "\n" for r, t in (
        (schedules.door_schedule(els), "Door schedule"), (schedules.window_schedule(els), "Window schedule"),
        (schedules.room_schedule(els), "Room schedule")))
    (out / "schedules.md").write_text("# Schedules, %s (generated from the design model)\n\n%s" % (design, md), encoding="utf-8")
    pages = len(spec["sheets"])
    reports, qa_rows, produced = [], [], []
    for i, s in enumerate(spec["sheets"], 1):
        if s["generator"] != "model":
            continue
        stem = out / ("%s-%s" % (s["no"], s["kind"]))
        if s["kind"] == "plan":
            rep = plans.render_plan(els, spec, s, stem, page=i, pages=pages, formats=formats)
            reports.append(rep)
            qa_rows.append(plans.qa(els, rep, stem.with_suffix(".pdf") if "pdf" in formats else None))
        elif s["kind"] == "schedule":
            rep = tables.render_schedules(els, spec, s, stem, page=i, pages=pages, formats=formats)
        else:
            rep = tables.render_cover(spec, s, stem, page=i, pages=pages, formats=formats)
        produced.append({"sheet": s["no"], "files": rep["files"]})
    xc = crosscheck.sc1(els, reports)
    summary = {"design": design, "produced": produced,
               "not_produced": [s["no"] for s in spec["sheets"] if s["generator"] != "model"],
               "plan_qa": qa_rows, "sc1": xc, "spec": spec}
    (out / "sheetset.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "plan-reports.json").write_text(json.dumps(reports, indent=1), encoding="utf-8")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--design", default="D1")
    ap.add_argument("--out", default="out/documents/D1")
    a = ap.parse_args()
    s = run(a.design, Path(a.out))
    print(json.dumps({k: s[k] for k in ("produced", "not_produced", "plan_qa")}, indent=1))
    print("SC1 ok=%s evaluated=%s" % (s["sc1"]["ok"], s["sc1"]["evaluated"]))
    for c in s["sc1"]["checks"]:
        print("  ", c["ok"], c["name"], c["expected"], c["got"])
    return 0 if s["sc1"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
