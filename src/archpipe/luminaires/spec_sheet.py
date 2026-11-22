"""L6c: write the supplier luminaire schedule (XLSX, Markdown, HTML -> PDF) and the cover note into docs/lighting-spec/.

    PYTHONPATH=src python -m archpipe.luminaires.spec_sheet

Everything is generated from the design (`schedule.build_schedule`); nothing is typed twice.
"""
from __future__ import annotations

import html
import shutil
import subprocess
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from . import schedule as SCH

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs" / "lighting-spec"
EQUIV = "or approved equivalent - submit IES/LDT + datasheet"
COLS = ["Tag", "Type", "Role / rooms", "Qty", "Reference product (maker, code, URL)", "Reference status",
        "Lumens (full output, per fitting) and tolerance", "Beam / distribution", "CCT", "CRI / R9", "Glare (UGR / cut-off / shielding)",
        "IP / IK", "Dimming protocol", "Flicker", "Cut-out / size", "Mounting", "Finish", "Commissioned output (zone drivers)", "Note"]


def _lumen_text(r: dict) -> str:
    sp = r["spec"]
    if r["lm_per_m"]:
        lm = r["lm_per_m"]
        return "%d lm per metre at full output, -10 / +25 %% (strip: sized to the design; supplier's strip may be rated higher and dimmed)" % lm
    rated = r["rated_lm"][-1] if r["rated_lm"] else 0
    if sp.get("lumens_text"):
        return sp["lumens_text"]
    if sp["ref"]:
        lo, hi = rated * (1 - SCH.LM_BAND), rated * (1 + SCH.LM_BAND)
        return "%d lm (%d-%d, +/-%d %%). A different output is accepted only if the substitution check keeps every zone at or under %d %% output" % (
            rated, lo, hi, 100 * SCH.LM_BAND, 100 * SCH.HEADROOM)
    lo = rated * 0.9
    return "%d lm rated (>= %d, <= %d). Sized so the design commissions it at about 70 %%; the zone must stay at or under %d %%" % (
        rated, lo, rated * 1.25, 100 * SCH.HEADROOM)


def rows_for_sheet(sched: list[dict]) -> list[list]:
    out = []
    for r in sched:
        sp = r["spec"]
        rooms = ", ".join("%s x%d" % (k, v) for k, v in r["rooms"].items())
        qty = "TBD (exterior design not yet counted)" if r.get("proposed") else "%d" % r["qty"] + (" (%.1f m total)" % r["length_m"] if r["length_m"] else "")
        ref = "\n".join("%s %s - %s\n%s" % (x["maker"], x["code"], x["name"], x["url"]) for x in sp["ref"]) or \
            "none held: specify by performance (supplier proposes a common product)"
        status = "; ".join("%s: V10 %s" % (x["code"], {"pass": "pass (maker's lab data reproduced)", "partial": "partial (see note)",
                                                       "lumens-only": "lumens only"}[x["v10"]]) for x in sp["ref"]) or "no reference"
        drv = ("%d-%d %% of rated output" % (round(100 * r["driver_min"]), round(100 * r["driver_max"]))) if r["driver_min"] is not None else "fixed scene levels (not tuned)"
        out.append([r["tag"], sp["name"], "%s. %s" % (sp["role"], rooms), qty, ref, status, _lumen_text(r),
                    sp["beam"][1] + ("" if not sp["beam"][0] else " (%g deg, +/-%g deg)" % (sp["beam"][0], max(SCH.BEAM_TOL * sp["beam"][0], 2))),
                    "%d K +/- %d K, <= 3 SDCM" % (sp["cct"], SCH.CCT_TOL_K), "CRI >= %d; R9 >= %d if stated" % (SCH.CRI_MIN, SCH.R9_MIN),
                    sp["ugr"], "%s / %s" % (sp["ip"], sp["ik"]), sp["dimming"], SCH.FLICKER, sp["size"], sp["mount"], sp["finish"], drv,
                    sp["note"]])
    return out


def write_xlsx(sched: list[dict], path: Path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Schedule"
    ws.append(["Luminaire schedule - Villa D1 - first issue for supplier confirmation"])
    ws.append(["Every row: %s. Reference products are examples that define the performance; they are not mandatory." % EQUIV])
    ws.append([])
    ws.append(COLS)
    for c in ws[4]:
        c.font, c.fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="334455")
        c.alignment = Alignment(wrap_text=True, vertical="top")
    for row in rows_for_sheet(sched):
        ws.append(row)
    for i, w in enumerate([11, 24, 44, 14, 46, 22, 44, 30, 18, 18, 34, 12, 28, 30, 40, 30, 22, 24, 44], 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for row in ws.iter_rows(min_row=5):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "C5"
    ws["A1"].font = Font(bold=True, size=14)
    rooms = wb.create_sheet("Quantities by room")
    rooms.append(["Room", "Tag", "Qty"])
    for r in sched:
        for room, n in r["rooms"].items():
            rooms.append([room, r["tag"], n])
    notes = wb.create_sheet("How to answer")
    for line in ANSWER_STEPS:
        notes.append([line])
    notes.column_dimensions["A"].width = 120
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


ANSWER_STEPS = [
    "For each tag, answer one of: AVAILABLE (as the reference), EQUIVALENT (name the product), NOT FOUND.",
    "For an EQUIVALENT, send the product's IES or LDT file and its datasheet (PDF). We check it against the performance columns.",
    "If the supplier cannot send an IES/LDT, send the datasheet and the maker's name: we will fetch it, and the answer stays 'unconfirmed'.",
    "Please state for every product: lumens, CCT, CRI (R9 if known), beam angle, IP, dimming protocol, cut-out size, finish. No prices or lead times at this stage.",
    "Return the same workbook with the answer columns filled, or a list of tags with the product code. Names you cannot find: leave blank.",
    "We reply with ACCEPT, ACCEPT WITH DIMMING CHANGE (the commissioning level of the zone changes; nothing else), or REJECT with the reasons.",
]


def write_md(sched: list[dict], path: Path):
    L = ["# Luminaire schedule - Villa D1 (first issue for supplier confirmation)", "",
         "Every row: **%s**. Reference products are examples that define the performance, not mandatory choices." % EQUIV, ""]
    L += ["| Tag | Type | Qty | Reference | Lumens | Beam | IP | Dimming |", "|---|---|---|---|---|---|---|---|"]
    for r, row in zip(sched, rows_for_sheet(sched)):
        sp = r["spec"]
        ref = "; ".join("%s %s" % (x["maker"], x["code"]) for x in sp["ref"]) or "none held"
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (row[0], row[1], row[3], ref, row[6].split(".")[0], row[7], row[11], row[12]))
    L += ["", "## Full performance specification per tag", ""]
    for r, row in zip(sched, rows_for_sheet(sched)):
        L += ["### %s - %s" % (row[0], row[1]), ""]
        for name, val in zip(COLS[2:], row[2:]):
            L.append("- **%s:** %s" % (name, str(val).replace("\n", " | ")))
        L.append("")
    path.write_text("\n".join(L), encoding="utf-8")


def write_html(sched: list[dict], path: Path):
    """Portrait A4: a one-page summary, then one block per type with every performance field (a 19-column table does not print)."""
    rows = rows_for_sheet(sched)
    e = lambda t: html.escape(str(t)).replace("\n", "<br>")
    h = ["<html><head><meta charset='utf-8'><style>body{font-family:sans-serif;font-size:8.5pt}table{border-collapse:collapse;width:100%}"
         "td,th{border:1px solid #888;padding:2px 4px;vertical-align:top}th{background:#334455;color:#fff;text-align:left}"
         "h1{font-size:14pt}h2{font-size:10.5pt;margin:12px 0 3px}td.k{width:24%;background:#eef;font-weight:bold}</style></head><body>",
         "<h1>Luminaire schedule - Villa D1 - first issue for supplier confirmation</h1>",
         "<p>Every row: <b>%s</b>. Reference products are examples that define the performance; they are not mandatory. "
         "The same data, in one row per tag, is in luminaire-schedule.xlsx.</p>" % EQUIV,
         "<table><tr><th>Tag</th><th>Type</th><th>Qty</th><th>Reference</th><th>Beam / distribution</th><th>CCT</th><th>IP</th><th>Dimming</th></tr>"]
    for r, row in zip(sched, rows):
        ref = "; ".join("%s %s" % (x["maker"], x["code"]) for x in r["spec"]["ref"]) or "none held"
        h.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" %
                 tuple(e(x) for x in (row[0], row[1], row[3], ref, row[7], row[8].split(",")[0], row[11], row[12])))
    h.append("</table>")
    for row in rows:
        h.append("<h2 style='page-break-before:auto'>%s - %s</h2><table>" % (e(row[0]), e(row[1])))
        for name, val in zip(COLS[2:], row[2:]):
            h.append("<tr><td class='k'>%s</td><td>%s</td></tr>" % (e(name), e(val)))
        h.append("</table>")
    h.append("</body></html>")
    path.write_text("\n".join(h), encoding="utf-8")


def to_pdf(src: Path) -> Path | None:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return None
    subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(src.parent), str(src)], check=True, capture_output=True,
                   timeout=180)
    return src.with_suffix(".pdf")


def main():
    sched = SCH.build_schedule()
    OUT.mkdir(parents=True, exist_ok=True)
    write_xlsx(sched, OUT / "luminaire-schedule.xlsx")
    write_md(sched, OUT / "luminaire-schedule.md")
    h = OUT / "luminaire-schedule.html"
    write_html(sched, h)
    pdf = to_pdf(h)
    h.unlink()
    print("wrote", OUT, "tags:", ", ".join(r["tag"] for r in sched), "pdf:", pdf)


if __name__ == "__main__":
    main()
