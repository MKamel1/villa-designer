"""Sheet QA (plan rows D15, D17, D18): orientation / mirroring against the MODEL, tags, level lines, chains, handing.

Every check reads the PRODUCED PDF (text positions) or the report of what was drawn and compares it to the design model;
a check never reuses the drawing code's own arithmetic. Result: violation counts (target 0) per check.
Defects these guard: D15 (plan north), D17 (mirrored/rotated view), D18 (missing level lines / tags), all seen only by
looking at exported sheets in the Revit era.
"""
from __future__ import annotations

import math
import re
from pathlib import Path

from archpipe.contracts import CheckResult, DesignElement

from . import orient, viewdraw
from archpipe.documents import schedules

POLICY = "ARCHPIPE-RV2-sheet-qa-policy"      # house policy, not a published figure


def _fitz():
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    return fitz


def pdf_words(pdf: Path | str) -> list[tuple[float, float, str]]:
    doc = _fitz().open(str(pdf))
    out = [((w[0] + w[2]) / 2, (w[1] + w[3]) / 2, w[4]) for page in doc for w in page.get_text("words")]
    doc.close()
    return out


def pdf_tag_positions(pdf: Path | str) -> dict[str, tuple[float, float]]:
    pos = {}
    for x, y, t in pdf_words(pdf):
        if re.fullmatch(r"[DWR]\d\d", t):
            pos.setdefault(t, (x, y))
    return pos


def orientation_violations(els: list[DesignElement], level: str, pdf: Path | str, min_sep_mm: float = 2500.0) -> dict:
    """Pairs of rooms (or doors) whose order on the PDF contradicts the model: street (model -x) must be higher on the
    sheet, east (model +y) further right. A mirrored or rotated plan makes many pairs wrong; correct ones make none."""
    tags = schedules.tag_numbers(els)
    pos = pdf_tag_positions(pdf)
    items = [(e, pos[tags[e.id]]) for e in els if e.kind in ("room", "door") and e.level == level and tags[e.id] in pos]
    bad = checked = 0
    for i, (a, pa) in enumerate(items):
        for b, pb in items[i + 1:]:
            if abs(a.placement[0] - b.placement[0]) > min_sep_mm:
                checked += 1
                if (a.placement[0] < b.placement[0]) != (pa[1] < pb[1]):        # PDF y grows downward
                    bad += 1
            if abs(a.placement[1] - b.placement[1]) > min_sep_mm:
                checked += 1
                if (a.placement[1] < b.placement[1]) != (pa[0] < pb[0]):
                    bad += 1
    return {"pairs_checked": checked, "violations": bad}


def tag_violations(els: list[DesignElement], rep: dict, pdf: Path | str) -> dict:
    tags = schedules.tag_numbers(els)
    found = set(pdf_tag_positions(pdf))
    level = rep["level"]
    want = {"R": {e.id for e in els if e.kind == "room" and e.level == level}}
    if "dims" in rep.get("layers", []):               # door and window tags only where the sheet carries them (GA plans)
        want["D"] = {e.id for e in els if e.kind == "door" and e.level == level}
        want["W"] = {e.id for e in els if e.kind == "window" and e.level == level}
    return {k: len({tags[i] for i in ids} - found) for k, ids in want.items()}


def level_line_violations(levels: dict, pdf: Path | str, expect: list[str]) -> int:
    """Each expected level elevation text (e.g. '+1.20') must be present in the PDF at least once."""
    txt = " ".join(t for _, _, t in pdf_words(pdf))
    return sum(1 for v in expect if v not in txt)


def chain_violations(els: list[DesignElement], rep: dict) -> dict:
    walls = {e.id: e for e in els if e.kind == "wall"}
    bad_sum, bad_len = 0, 0
    for d in rep["dimensions"]:
        if abs(sum(d["segments_mm"]) - d["total_mm"]) > len(d["segments_mm"]):
            bad_sum += 1
        if d["kind"] == "opening":
            p = walls[d["owner"]].params
            L = math.hypot(p["x1_mm"] - p["x0_mm"], p["y1_mm"] - p["y0_mm"])
            if abs(d["total_mm"] - L) > 3:
                bad_len += 1
    by_side: dict[str, set] = {}
    for d in rep["dimensions"]:
        if d["kind"] == "overall":
            by_side.setdefault(d["owner"], set()).add(d["total_mm"])
    grid_mismatch = sum(1 for d in rep["dimensions"] if d["kind"] == "grid" and d["total_mm"] not in by_side.get(d["owner"], {d["total_mm"]}))
    return {"sum_mismatch": bad_sum, "opening_chain_vs_wall_length": bad_len, "grid_vs_overall": grid_mismatch}


def handing_violations(els: list[DesignElement], rep: dict) -> dict:
    level = rep["level"]
    doors = {e.id: e for e in els if e.kind == "door" and e.level == level}
    cel = {e.id: e for e in orient.to_client(els)}
    want = {i for i, e in doors.items() if e.params.get("judgement")}
    unflagged = want - set(rep.get("handing_flags", []))
    wrong_hinge = 0
    for s in rep.get("swings", []):
        hx = cel[s["id"]].params.get("hinge_xy_mm")
        if hx and math.dist(s["hinge_xy"], hx[:2]) > 150:
            wrong_hinge += 1
    hinged = {i for i, e in doors.items() if e.params.get("operation") == "hinged"}
    undrawn = hinged - {s["id"] for s in rep.get("swings", [])}
    return {"judgement_doors_unflagged": len(unflagged), "hinge_off_authored": wrong_hinge, "hinged_doors_without_swing": len(undrawn)}


def opening_axis_findings(els: list[DesignElement]) -> list[str]:
    """MODEL data check (not a drawing check): doors/windows whose `rotation_deg` disagrees with their host wall's axis.
    The drawing follows the host wall; these ids are reported to the model lane."""
    walls = {e.id: e for e in els if e.kind == "wall"}
    out = []
    for e in els:
        if e.kind in ("door", "window") and e.host in walls:
            p = walls[e.host].params
            wall_along_x = abs(p["y1_mm"] - p["y0_mm"]) < abs(p["x1_mm"] - p["x0_mm"])
            rot_along_x = abs(math.sin(math.radians(e.rotation_deg))) < 0.5
            if wall_along_x != rot_along_x:
                out.append(e.id)
    return out


def view_violations(els: list[DesignElement], rep: dict) -> dict:
    """Stroke extent in u against the MODEL's footprint projected on the same axis: a mirrored view fails this."""
    pts = []
    for e in els:
        if e.kind == "wall":
            p = e.params
            pts += [(p["x0_mm"], p["y0_mm"]), (p["x1_mm"], p["y1_mm"])]
        elif e.kind == "context" and e.id == "ctx-apartment-above":
            pts += [(e.placement[0] + sx * e.size[0] / 2, e.placement[1] + sy * e.size[1] / 2) for sx in (-1, 1) for sy in (-1, 1)]
    bad = 0
    detail = []
    for v in rep["views"]:
        ux, uy = v["u_axis"]
        us = [(x * ux + y * uy) / 1000.0 for x, y in pts]
        rng = v["stroke_u_range_m"]
        if v["kind"] == "elevation" and rng:
            ok = abs(rng[0] - min(us)) < 0.6 and abs(rng[1] - max(us)) < 0.6
            detail.append({"view": v["name"], "model_u": [round(min(us), 2), round(max(us), 2)], "strokes_u": [round(rng[0], 2), round(rng[1], 2)], "ok": ok})
            bad += 0 if ok else 1
        if v["kind"] == "section":
            bad += 0 if v["structure_polys"] > 0 else 1
    return {"views_wrong": bad, "detail": detail}


def run(els: list[DesignElement], reports: dict, out: Path, levels: dict) -> dict:
    """QA over every produced sheet. `reports`: sheet no -> render report. Returns counts and CheckResults."""
    res: dict = {"sheets": {}, "totals": {}}
    results: list[CheckResult] = []
    total = {"orientation": 0, "tags": 0, "levels": 0, "chains": 0, "handing": 0, "views": 0}
    for no, rep in sorted(reports.items()):
        pdf = out / (rep["files"][0].rsplit(".", 1)[0] + ".pdf")
        if not pdf.exists():
            continue
        row = {}
        if "room_tags" in rep and rep.get("level") in ("B", "GF") and "panels" not in rep:
            o = orientation_violations(els, rep["level"], pdf)
            t = tag_violations(els, rep, pdf)
            lv = level_line_violations(levels, pdf, ["%+.2f" % (levels[rep["level"]]["ffl_revit_mm"] / 1000.0)])
            row.update({"orientation": o, "tags_missing": t, "level_line_missing": lv})
            total["orientation"] += o["violations"]
            total["tags"] += sum(t.values())
            total["levels"] += lv
            if "dims" in rep.get("layers", []):
                c = chain_violations(els, rep)
                h = handing_violations(els, rep)
                row.update({"chains": c, "handing": h})
                total["chains"] += sum(c.values())
                total["handing"] += sum(h.values())
        elif rep.get("generator") == "lineart":
            vv = view_violations(els, rep)
            exp = ["%+.2f" % (levels[k]["ffl_revit_mm"] / 1000.0) for k in ("B", "GF", "L1", "ROOF")]
            lv = level_line_violations(levels, pdf, exp)
            row.update({"views": vv, "level_line_missing": lv})
            total["views"] += vv["views_wrong"]
            total["levels"] += lv
        res["sheets"][no] = row
        for crit, subject, n in (("DS2", "orientation " + no, sum([row.get("orientation", {}).get("violations", 0)])),
                                 ("DS2", "tags/levels " + no, sum(row.get("tags_missing", {}).values()) + row.get("level_line_missing", 0)),
                                 ("DS3", "chains " + no, sum(row.get("chains", {}).values()))):
            if row:
                results.append(CheckResult(crit, "RV2", "pass" if n == 0 else "fail", subject, float(n), 0.0, "violations",
                                           "%d violations, 0 allowed (read from the produced PDF against the design model; house policy)" % n,
                                           source_ids=(POLICY,)))
    total["opening_axis_vs_host_model_findings"] = len(opening_axis_findings(els))
    res["opening_axis_findings"] = opening_axis_findings(els)
    res["totals"] = total
    res["results"] = results
    return res
