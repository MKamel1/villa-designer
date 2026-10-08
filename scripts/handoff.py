"""Consultant hand-off package from one L0 spec (method step W0.5).

    python scripts/handoff.py <spec.yaml> --name <package-id> [--thermal-label <concept id>]

Writes docs/handoff/<package-id>/: README (what is supplied, what is MISSING and needs a consultant),
schedules as CSV, quantities and relative cost (JSON), the IFC4 model, rule findings, and, when given,
the per-room TM59 screen of a concept (out/workstation/thermal-cases-latest.json).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from archpipe.execution_context import ContextError, project_context  # noqa: E402
from archpipe import deliverables as D, model, rules
from archpipe.safe_io import save_json, save_text

MISSING = [
    ("Glare (DGP) and detailed daylight compliance", "daylight consultant", "room window sizes and orientations (windows.csv); TM59 screen"),
    ("HVAC design and sizing", "MEP engineer", "room list and areas (rooms.csv); free-running TM59 screen per room; IFC"),
    ("Electrical design", "electrical engineer", "rooms.csv; IFC; lighting layout when authored"),
    ("Plumbing and drainage", "plumbing engineer", "wet rooms in rooms.csv; wet-stack status in the concept report; IFC"),
    ("Structural design and certification", "structural engineer", "IFC walls and openings; spans implied by rooms.csv"),
    ("Permits and local code compliance (Egypt)", "local architect of record", "every sheet here is best-practice guidance, not local compliance"),
    ("Acoustics end-check", "acoustician (at the end, per the method)", "room adjacencies; build-ups when specified"),
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("spec", type=Path)
    ap.add_argument("--name", required=True)
    ap.add_argument("--thermal-label", help="concept id prefix in out/workstation/thermal-cases-latest.json")
    a = ap.parse_args(argv)
    try:
        project_context(
            ROOT,
            Path(__file__).resolve(),
            "handoff",
            inputs=[a.spec],
            modules=["yaml", "shapely", "ifcopenshell", "numpy"],
        )
    except ContextError as exc:
        print("PREFLIGHT FAILED: " + str(exc), file=sys.stderr)
        return 2
    p = model.load(a.spec)
    out = ROOT / "docs" / "handoff" / a.name
    out.mkdir(parents=True, exist_ok=True)
    s = D.schedules(p)
    for k, rows in s.items():
        D.write_csv(rows, out / f"{k}.csv")
    q = D.quantities(p)
    gia = D.gross_area_m2(p)
    cost = D.relative_cost({a.name: gia})
    save_json(out / "quantities.json", {"quantities": q, "net_room_area_m2": gia, "relative_cost": cost}, indent=1)
    D.to_ifc(p, out / "model.ifc")
    findings = [{"level": lv.id, "rule": f.rule, "severity": f.severity, "where": f.where, "message": f.message}
                for lv in p.levels for f in rules.review(p, lv.id)]
    save_json(out / "findings.json", findings, indent=1)
    thermal_lines = []
    tfile = ROOT / "out" / "workstation" / "thermal-cases-latest.json"
    if a.thermal_label and tfile.is_file():
        for x in json.loads(tfile.read_text(encoding="utf-8"))["results"]:
            if (x.get("label") or "").startswith(a.thermal_label + "/"):
                t = x.get("tm59", {})
                thermal_lines.append(f"| {x['label'].split('/')[1]} | {x['case']['azimuth_deg']} | {x['case']['wwr']} | "
                                     f"{t.get('a', {}).get('hours')} / {t.get('limit_hours')} | "
                                     f"{t['b']['nights'] if t.get('b') else '-'} | {'yes' if t.get('pass') else 'no'} |")
    lines = [f"# Consultant hand-off: {a.name}", "",
             f"Generated from `{a.spec.as_posix()}` by `scripts/handoff.py`. Every file here is computed from that spec. "
             "This is design guidance, not local code compliance.", "",
             "## Supplied", "",
             "| File | Content |", "|---|---|",
             "| rooms.csv, doors.csv, windows.csv, furniture.csv | Schedules |",
             "| quantities.json | Floor and wall quantities per level; relative cost (AECOM MEH 2026 Gulf villa rates, relative only) |",
             "| model.ifc | IFC4: storeys, walls, openings with doors/windows, spaces (geometry checked against the spec by tests) |",
             f"| findings.json | Rule engine findings ({len(findings)}); every rule's source is in docs/guidance/rule-audit.md |", ""]
    if thermal_lines:
        lines += ["## Room thermal screen (free-running TM59:2026 criteria, not an assessment)", "",
                  "| Room | Azimuth | WWR | Criterion a (hours / limit) | Criterion b (nights) | Pass |",
                  "|---|---|---|---|---|---|"] + thermal_lines + [""]
    lines += ["## MISSING in-house: needs a consultant", "", "| Scope | Who | What we hand over |", "|---|---|---|"]
    lines += [f"| {s_} | {w} | {h} |" for s_, w, h in MISSING] + [""]
    save_text(out / "README.md", "\n".join(lines))
    print(f"  handoff: {out.relative_to(ROOT)} ({len(findings)} findings, {len(s['rooms'])} rooms)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
