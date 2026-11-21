"""python -m archpipe.documents [--design D1] [--out out/documents/D1]: write the sheet set, schedules and QA."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from archpipe import model

from archpipe.drawings2d import callouts, scene_slim, siteplan, variants, viewsheets

from . import crosscheck, plans, schedules, sheetset, tables


PREVIEWS = ("A-100-site", "A-112-plan", "A-301-section")


def combine(out: Path, spec: dict) -> Path:
    """One PDF of every produced sheet in sheet-number order, with bookmarks (print set)."""
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    doc = fitz.open()
    toc = []
    for s in spec["sheets"]:
        f = out / ("%s-%s.pdf" % (s["no"], s["kind"]))
        if f.exists():
            toc.append([1, "%s  %s" % (s["no"], s["title_en"]), doc.page_count + 1])
            doc.insert_pdf(fitz.open(str(f)))
    doc.set_toc(toc)
    dest = out / "D1-set.pdf"
    doc.save(str(dest))
    return dest


def previews(out: Path, dest: Path) -> list[str]:
    import shutil
    dest.mkdir(parents=True, exist_ok=True)
    for old in dest.glob("*.png"):
        old.unlink()
    got = []
    for stem in PREVIEWS:
        f = out / (stem + ".png")
        if f.exists():
            shutil.copy(f, dest / f.name)
            got.append(f.name)
    return got


def run(design: str, out: Path, formats=("pdf", "svg", "png"), slim: dict | None = None) -> dict:
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
    for name, rows in (("finish", schedules.finish_schedule(els)), ("furniture", schedules.furniture_schedule(els)),
                       ("luminaire", schedules.luminaire_schedule(els))):
        (out / ("schedule-%s.csv" % name)).write_text(schedules.to_csv(rows), encoding="utf-8")
    pages = len(spec["sheets"])
    reports, qa_rows, produced, all_reps = [], [], [], {}
    stems = {}
    for i, s in enumerate(spec["sheets"], 1):
        if s["generator"] == "lineart" and slim is not None:
            stem = out / ("%s-%s" % (s["no"], s["kind"]))
            rep = viewsheets.render_view_sheet(slim, els, spec, s, stem, page=i, pages=pages, formats=formats)
            all_reps[s["no"]] = rep
            produced.append({"sheet": s["no"], "files": rep["files"], "scene_sha256": rep["scene_sha256"]})
            continue
        if s["generator"] != "model":
            continue
        stem = out / ("%s-%s" % (s["no"], s["kind"]))
        stems[s["no"]] = stem
        k = s["kind"]
        if k == "plan":
            rep = plans.render_plan(els, spec, s, stem, page=i, pages=pages, formats=formats, layers=variants.LAYERS[s["variant"]],
                                    extras=variants.extras_for(s["variant"], s["level"]))
            if s["variant"] == "ga":
                reports.append(rep)
                qa_rows.append(plans.qa(els, rep, stem.with_suffix(".pdf") if "pdf" in formats else None))
        elif k == "site":
            rep = siteplan.render_site(els, spec, s, stem, page=i, pages=pages, formats=formats)
        elif k == "callout":
            rep = callouts.render_callouts(els, spec, s, stem, page=i, pages=pages, formats=formats)
        elif k == "schedule":
            rep = tables.render_schedules(els, spec, s, stem, page=i, pages=pages, formats=formats)
        elif k == "schedule2":
            rep = tables.render_table_sheet(els, spec, s, stem, page=i, pages=pages, formats=formats)
        else:
            rep = tables.render_cover(spec, s, stem, page=i, pages=pages, formats=formats)
        all_reps[s["no"]] = rep
        produced.append({"sheet": s["no"], "files": rep["files"]})
    from archpipe.drawings2d import sheetqa
    from archpipe import contracts
    qa = sheetqa.run(els, all_reps, out, spec["levels"])
    (out / "sheet-qa.json").write_text(json.dumps({"totals": qa["totals"], "opening_axis_findings": qa["opening_axis_findings"], "sheets": qa["sheets"]}, indent=1), encoding="utf-8")
    contracts.write_results("RV2", qa.pop("results"), root=out / "checks")
    xc = crosscheck.sc1(els, reports)
    summary = {"design": design, "produced": produced,
               "not_produced": [s["no"] for s in spec["sheets"] if s["generator"] != "model" and (slim is None)],
               "sheet_reports": all_reps,
               "plan_qa": qa_rows, "sheet_qa": qa["totals"], "sc1": xc, "spec": spec}
    (out / "sheetset.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "plan-reports.json").write_text(json.dumps(reports, indent=1), encoding="utf-8")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--design", default="D1")
    ap.add_argument("--out", default="out/documents/D1")
    ap.add_argument("--previews", help="copy 3 PNG previews of the set to this directory (committed samples)")
    ap.add_argument("--scene", help="built scene.json: enables the Line Art sections and elevations (needs Blender)")
    a = ap.parse_args()
    slim = None
    if a.scene:
        Path(a.out).mkdir(parents=True, exist_ok=True)
        sp = Path(a.out) / "slim-scene.json"
        scene_slim.slim(a.scene, sp)
        slim = json.loads(sp.read_text(encoding="utf-8"))
    s = run(a.design, Path(a.out), slim=slim)
    spec_ = s["spec"]
    print("combined:", combine(Path(a.out), spec_))
    if a.previews:
        print("previews:", previews(Path(a.out), Path(a.previews)))
    print(json.dumps({k: s[k] for k in ("produced", "not_produced", "plan_qa")}, indent=1))
    print("SC1 ok=%s evaluated=%s" % (s["sc1"]["ok"], s["sc1"]["evaluated"]))
    for c in s["sc1"]["checks"]:
        print("  ", c["ok"], c["name"], c["expected"], c["got"])
    return 0 if s["sc1"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
