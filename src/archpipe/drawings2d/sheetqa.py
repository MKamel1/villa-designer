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


# ---- print legibility and composition (lead review 2026-11-21: drawings filled ~20 % of the sheet, text unreadable in print)
# House standard (policy, not a quoted clause): text height = cap height = 0.73 x font size (DejaVu Sans).
# Room names >= 2.5 mm, every other text on the sheet >= 1.8 mm (tags, dimensions, notes, title block).
CAP = 0.729
MIN_ROOM_NAME_MM = 2.5
MIN_TEXT_MM = 1.8
DRAWING_KINDS = {"site", "plan", "callout", "elevation", "section", "interior"}
MIN_FILL = 0.60                    # ink bounding box over the drawing area
FRAME_LEFT, FRAME_EDGE, TITLE_BAND_MM = 20.0, 10.0, 16.0
PT_MM = 25.4 / 72.0


def pdf_spans(pdf: Path | str) -> list[dict]:
    doc = _fitz().open(str(pdf))
    out = []
    for page in doc:
        for b in page.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                for sp in l["spans"]:
                    if sp["text"].strip():
                        out.append({"text": sp["text"].strip(), "cap_mm": sp["size"] * PT_MM * CAP, "bbox": sp["bbox"], "bold": bool(sp["flags"] & 16 or "Bold" in sp["font"])})
    doc.close()
    return out


def text_violations(pdf: Path | str, room_names: list[str] = ()) -> dict:
    """Printed text heights read from the PDF: spans under 1.8 mm cap height, room-name spans under 2.5 mm."""
    names = [n.lower() for n in room_names]
    small, small_rooms, n_room = [], [], 0
    for sp in pdf_spans(pdf):
        t = sp["text"].lower()
        is_room = sp["bold"] and len(t) >= 4 and any(t in n for n in names)      # room tags are bold; table cells are not
        n_room += is_room
        if is_room and sp["cap_mm"] < MIN_ROOM_NAME_MM - 0.02:
            small_rooms.append((sp["text"], round(sp["cap_mm"], 2)))
        elif sp["cap_mm"] < MIN_TEXT_MM - 0.02:
            small.append((sp["text"], round(sp["cap_mm"], 2)))
    sizes = [sp["cap_mm"] for sp in pdf_spans(pdf)]
    return {"text_below_min": len(small), "room_names_below_min": len(small_rooms), "room_name_spans": n_room,
            "min_cap_mm": round(min(sizes), 2) if sizes else None, "examples": (small + small_rooms)[:5]}


def fill_ratio(pdf: Path | str, strip_mm: float = 88.0, cell_mm: float = 40.0) -> dict:
    """Share of the drawing area that carries ink, read from the rendered PDF: the page is rasterised and the area
    (frame minus the title-block strip and the title band) is cut into `cell_mm` squares; fill = squares with any ink.
    A bounding box would count a stray legend in a far corner as 'filled', so occupancy is used (lead review: 20 %)."""
    import numpy as np
    fitz = _fitz()
    doc = fitz.open(str(pdf))
    page = doc[0]
    W, H = page.rect.width * PT_MM, page.rect.height * PT_MM
    dpi = max(10, round(25.4 / (cell_mm / 6)))                  # 6 px per cell
    pix = page.get_pixmap(dpi=dpi, colorspace=fitz.csGRAY)
    img = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w) < 235
    doc.close()
    ppm = pix.w / W
    x0, x1 = (FRAME_LEFT + 2) * ppm, (W - FRAME_EDGE - strip_mm - 2) * ppm
    y0, y1 = (FRAME_EDGE + TITLE_BAND_MM) * ppm, (H - FRAME_EDGE - 2) * ppm
    cs = cell_mm * ppm
    nx, ny = int((x1 - x0) // cs), int((y1 - y0) // cs)
    hit = 0
    for i in range(nx):
        for j in range(ny):
            hit += bool(img[int(y0 + j * cs):int(y0 + (j + 1) * cs), int(x0 + i * cs):int(x0 + (i + 1) * cs)].any())
    return {"fill": round(hit / (nx * ny), 3), "cells": [nx, ny]}


def _fills(pdf: Path | str) -> list[tuple[str, tuple[float, float, float, float]]]:
    """(hex fill colour, bbox in mm) of every filled vector shape on page 1."""
    doc = _fitz().open(str(pdf))
    out = []
    for d in doc[0].get_drawings():
        if d.get("fill") is not None:
            c = d["fill"]
            r = d["rect"]
            out.append(("#%02x%02x%02x" % tuple(round(v * 255) for v in c[:3]),
                        (r.x0 * PT_MM, r.y0 * PT_MM, r.x1 * PT_MM, r.y1 * PT_MM)))
    doc.close()
    return out


def stair_detail_violations(els: list[DesignElement], pdf: Path | str, scale: float = 20.0) -> dict:
    """A-301 must show what the model has: every riser infill bar, the glazed stair guards and the understair cupboard.
    Counted in the PDF by the detail's fixed fill colours (and, for the bars, by their printed size: bar_h x bar_t at scale)."""
    from .stairdetail import BAR_FC, CUPBOARD_FC, GLASS_FC
    st = next(e for e in els if e.kind == "stair")
    inf = st.params.get("riser_infill") or {}
    want_bars = inf.get("count", 0) if inf.get("present") else 0
    want_guards = sum(1 for e in els if e.id in ("rail-stair-open-glass", "rail-gf-stair-void") and e.params.get("glazed"))
    cb = next((e for e in els if e.id == "joinery-understair-cupboard"), None)
    want_cb = len(cb.params["walls"]) if cb else 0
    fills = _fills(pdf)
    bars = [b for c, b in fills if c == BAR_FC and abs((b[2] - b[0]) - inf.get("bar_t_mm", 0) / scale) < 0.2
            and abs((b[3] - b[1]) - inf.get("bar_h_mm", 0) / scale) < 0.2]
    guards = sum(1 for c, _ in fills if c == GLASS_FC)
    cupboard = sum(1 for c, _ in fills if c == CUPBOARD_FC)
    return {"bars_missing": max(0, want_bars - len(bars)), "guards_missing": max(0, want_guards - guards),
            "cupboard_walls_missing": max(0, want_cb - cupboard), "bars_found": len(bars), "bars_expected": want_bars}


def interior_violations(els: list[DesignElement], rep: dict, pdf: Path | str) -> dict:
    """Every door and window of the elevated rooms has its tag on the interior-elevation sheet."""
    from .interior import ROOMS
    tags = schedules.tag_numbers(els)
    found = {t for _, _, t in pdf_words(pdf)}
    want = [e for e in els if e.kind in ("door", "window") and any(e.room == r or r in e.params.get("rooms", []) for r, _ in ROOMS)
            and e.level == "GF"]
    return {"openings_untagged": sum(1 for e in want if tags[e.id] not in found), "openings_expected": len(want),
            "elevations": len(rep.get("elevations", [])), "elevations_expected": 4 * len(ROOMS)}


def yardwall_violations(els: list[DesignElement], pdf: Path | str) -> dict:
    """The NE yard wall sheet prints the model's own length, thickness and height."""
    w = next(e for e in els if e.id == "ctx-yard-wall-ne")
    words = {t for _, _, t in pdf_words(pdf)}
    want = {str(int(max(w.size[0], w.size[1]))), str(int(min(w.size[0], w.size[1]))), str(int(w.params["z1_scene_mm"] - w.params["z0_scene_mm"]))}
    return {"dimensions_missing": len(want - words)}


def _flatten(by_level: dict) -> dict:
    """Merge per-level check rows of one sheet into one row (counts add up; orientation keeps pairs and violations)."""
    out: dict = {}
    for lv, r in by_level.items():
        for k, v in r.items():
            if isinstance(v, dict):
                for kk, vv in v.items():
                    out.setdefault(k, {})[kk] = out.get(k, {}).get(kk, 0) + vv
            else:
                out[k] = out.get(k, 0) + v
    return out


def run(els: list[DesignElement], reports: dict, out: Path, levels: dict) -> dict:
    """QA over every produced sheet. `reports`: sheet no -> render report. Returns counts and CheckResults."""
    res: dict = {"sheets": {}, "totals": {}}
    results: list[CheckResult] = []
    total = {"orientation": 0, "tags": 0, "levels": 0, "chains": 0, "handing": 0, "views": 0, "text": 0, "fill": 0, "stair_detail": 0, "interior": 0, "yardwall": 0}
    for no, rep in sorted(reports.items()):
        pdf = out / (rep["files"][0].rsplit(".", 1)[0] + ".pdf")
        if not pdf.exists():
            continue
        row = {}
        subs = rep["plans"] if "plans" in rep else ([rep] if "room_tags" in rep and "panels" not in rep else [])
        for sub in (x for x in subs if x.get("level") in ("B", "GF")):
            lvl = sub["level"]
            o = orientation_violations(els, lvl, pdf)
            t = tag_violations(els, sub, pdf)
            lv = level_line_violations(levels, pdf, ["%+.2f" % (levels[lvl]["ffl_revit_mm"] / 1000.0)])
            row.setdefault(lvl, {}).update({"orientation": o, "tags_missing": t, "level_line_missing": lv})
            total["orientation"] += o["violations"]
            total["tags"] += sum(t.values())
            total["levels"] += lv
            if "dims" in sub.get("layers", []):
                c = chain_violations(els, sub)
                h = handing_violations(els, sub)
                row[lvl].update({"chains": c, "handing": h})
                total["chains"] += sum(c.values())
                total["handing"] += sum(h.values())
        if subs:
            row = _flatten(row)
        elif rep.get("generator") == "lineart":
            vv = view_violations(els, rep)
            exp = ["%+.2f" % (levels[k]["ffl_revit_mm"] / 1000.0) for k in ("B", "GF", "L1", "ROOF")]
            lv = level_line_violations(levels, pdf, exp)
            row.update({"views": vv, "level_line_missing": lv})
            total["views"] += vv["views_wrong"]
            total["levels"] += lv
        if not pdf.name.endswith("-cover.pdf"):
            names_ = [n for e in els if e.kind == "room" for n in {e.params["name"], e.params["name"].split(" (")[0]}]
            tv = text_violations(pdf, names_)
            fr = fill_ratio(pdf) if pdf.stem.split("-", 2)[2] in DRAWING_KINDS else {"fill": None}      # tables are not drawings
            row.update({"text": tv, "fill": fr})
            total["text"] += tv["text_below_min"] + tv["room_names_below_min"]
            total["fill"] += 0 if fr["fill"] is None or fr["fill"] >= MIN_FILL else 1
            results.append(CheckResult("DS2", "RV2", "pass" if tv["text_below_min"] + tv["room_names_below_min"] == 0 else "fail",
                                       "print text height " + no, float(tv["min_cap_mm"] or 0), MIN_TEXT_MM, "mm cap height (smallest on sheet)",
                                       "smallest text %.2f mm cap height, %.1f mm required (%d spans below; room names %.1f mm); house policy"
                                       % (tv["min_cap_mm"] or 0, MIN_TEXT_MM, tv["text_below_min"] + tv["room_names_below_min"], MIN_ROOM_NAME_MM),
                                       source_ids=(POLICY,)))
            if fr["fill"] is not None:
              results.append(CheckResult("DS2", "RV2", "pass" if fr["fill"] >= MIN_FILL else "fail", "drawing-area fill " + no,
                                         fr["fill"], MIN_FILL, "share of area with ink", "%.0f %% of the drawing area carries ink, %.0f %% required; house policy"
                                         % (fr["fill"] * 100, MIN_FILL * 100), source_ids=(POLICY,)))
        if rep.get("generator") == "lineart" and rep["views"] and rep["views"][0]["name"].startswith("Section 1"):
            sd = stair_detail_violations(els, pdf, rep["views"][0]["scale"])
            row["stair_detail"] = sd
            total["stair_detail"] += sd["bars_missing"] + sd["guards_missing"] + sd["cupboard_walls_missing"]
        if "elevations" in rep:
            iv = interior_violations(els, rep, pdf)
            row["interior"] = iv
            total["interior"] += iv["openings_untagged"] + abs(iv["elevations"] - iv["elevations_expected"])
        if rep.get("wall"):
            yv = yardwall_violations(els, pdf)
            row["yardwall"] = yv
            total["yardwall"] += yv["dimensions_missing"]
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
