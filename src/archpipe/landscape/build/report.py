"""Schedule (what was drawn, what is a stand-in, element ids) and the CLI:

    python -m archpipe.landscape.build.report LAYOUT.json OUT_DIR [--render]
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

from . import build, checks, guard


def schedule(scene):
    guard.refuse(scene, "the schedule")
    rows = scene.schedule
    per = collections.OrderedDict()
    for r in rows:
        d = per.setdefault(r["species"], dict(species=r["species"], status=r["status"], individuals=0, reason=r.get("reason"), asset=r.get("asset"), grade=r.get("grade"),
                                              species_fit=r.get("species_fit"), mature_height_m=r.get("mature_height_m"), shown_height_m=r.get("shown_height_m"),
                                              size_basis=r.get("size_basis"), colour_basis=r.get("colour_basis")))
        d["individuals"] += 1
    counts = collections.Counter(r["status"] for r in rows)
    out = collections.Counter()
    for o in scene.objects:
        if o.kind in ("table", "chair", "koi") and o.state is None:
            out["%s:%s" % (o.kind, "asset" if o.asset else "simple geometry")] += 1
    return dict(age_years=scene.age, individuals=dict(counts), outdoor=dict(out), species=list(per.values()), rows=rows)


def element_table(scene):
    guard.refuse(scene, "the element table")
    return [dict(id=o.id, kind=o.kind, layout_id=o.layout_id or o.meta.get("layout_id"), state=o.state, standin=o.standin, label=o.label) for o in scene.objects]


def markdown(sch_age, sch_mature, elements, findings, warnings):
    L = ["# LDB build schedule", "", "Plant sizes: at %s years (policy, no growth curve is held) and at maturity." % sch_age["age_years"], "",
         "| species | status | individuals | asset / reason | mature height m | shown height m (age %s) | size basis |" % sch_age["age_years"], "|---|---|---|---|---|---|---|"]
    for s in sch_age["species"]:
        L.append("| %s | %s | %d | %s | %s | %s | %s |" % (s["species"], s["status"].upper() if s["status"] == "standin" else s["status"], s["individuals"],
                 ("%s grade %s (%s fit)" % (s["asset"], s["grade"], s["species_fit"])) if s["status"] == "asset" else (s["reason"] or ""), s.get("mature_height_m"), s.get("shown_height_m"), s.get("size_basis")))
    L += ["", "Individuals: %s" % json.dumps(sch_age["individuals"]), "Furniture and koi: %s" % json.dumps(sch_age.get("outdoor")), "", "## Checks (age %s, closed cover)" % sch_age["age_years"], "", "```", json.dumps(checks.summary(findings), indent=1), "```", ""]
    if warnings:
        L += ["## Build warnings", ""] + ["- " + w for w in warnings] + [""]
    L += ["## Element ids", "", "| id | kind | layout id | note |", "|---|---|---|---|"]
    for e in elements:
        L.append("| %s | %s | %s | %s |" % (e["id"], e["kind"], e["layout_id"] or "", (e["label"] or "")[:110].replace("|", "/")))
    return "\n".join(L)


def main(argv):
    layout = build.load_layout(argv[0])
    out = Path(argv[1]); out.mkdir(parents=True, exist_ok=True)
    s3 = build.build_scene(layout, age=3)
    sm = build.build_scene(layout, age=None)
    findings = checks.run_all(s3, "closed") + [f for f in checks.run_all(s3, "open") if f["check"] in ("support", "clip", "footprint")]
    mat_findings = checks.run_all(sm, "closed")
    (out / "schedule.json").write_text(json.dumps(dict(age3=schedule(s3), mature=schedule(sm), elements=element_table(s3), warnings=s3.warnings), indent=1))
    (out / "checks.json").write_text(json.dumps(dict(age3=findings, mature=mat_findings), indent=1))
    (out / "SCHEDULE.md").write_text(markdown(schedule(s3), schedule(sm), element_table(s3), findings, s3.warnings))
    print("age 3:", checks.summary(findings)); print("mature fails:", [(f["id"], f["achieved"]) for f in mat_findings if f["status"] == "fail"])
    if "--render" in argv:
        from . import preview
        for tag, sc in (("age3", s3), ("mature", sm)):
            rec = preview.render(sc, out / "previews", tag)
            print(tag, [(v["name"], v["file"]) for v in rec["views"]])


if __name__ == "__main__":
    main(sys.argv[1:])
