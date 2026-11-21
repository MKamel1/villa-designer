# MK hand-back: markup loop (plan row U29, stage 3)

CLI: `python -m archpipe.markup ingest <pdf|csv|json>` | `list` | `decide <id> accept|reject --reason R` | `close <id> --commit SHA [--element ID]` | `revise <sheet.pdf> [--out]` | `frames` (re-record sheet frames). Exit 2 on missing/invalid input or a refused transition. Requests: `knowledge/markup/requests/MK-nnn.json`.

Supported sheets: the plan sheets A-101, A-111, A-121, A-131 (frames in `knowledge/markup/frames-D1.json`). Site, section, elevation, callout and schedule sheets: a mark is recorded with `link_status: unsupported-sheet` (honest, not guessed).

## Design
- Frame: recorded from RV2's own `render_plan` (spy on `_draw_plan`), mapping `orient.pt` + panel offsets/scale; verified against every issued PDF (room tags inside their rooms) or ingest refuses (mirrored/rotated/re-laid-out).
- Link: hit test on plan footprints within 3 mm of paper (150 mm at 1:50), limited to what the sheet draws; tiers object > wall > room; one containing footprint wins, 2+ in tolerance = `ambiguous` with all alternatives, none = `miss` with reason (title block / empty space / unsupported sheet). Area marks (Square/Circle/Ink/Polygon) use the objects they enclose.
- Status: open -> accepted | rejected(reason) ; accepted -> closed(commit). Ambiguous/miss requests close only with `--element` (recorded `resolved-by-lead`). Ingest is idempotent (source hash).
- Revise: copy of the sheet PDF, scalloped cloud round each changed element at its CURRENT model position, "REV A" label, revision-table row (rev, date, request, text, commit) bottom right.

## Proof (real D1 sheets; samples in `knowledge/markup/proof/`)
- "door too narrow" on A-111 -> `door-GF-corridor-kids-a` (0 mm, inside) + context `room-kids-a`.
- "move this light" between two luminaires on A-121 -> ambiguous, 4 candidates listed (`lum-WALL-READ-parents-bed-02`, `lum-VSTRIP-parents-dressing-03`, ...); close refused until `--element lum-WALL-READ-parents-bed-02`.
- mark east of the building -> miss ("outside the drawn plan"); in-extent empty corner -> miss "empty space"; title-block mark -> miss.
- Revised A-111 PNG (viewed): red scalloped cloud round the door D11 at kids bedroom A's corridor wall, "REV A" label, table row `A 2026-11-21 MK-001 door too narrow 1c3017e`. Revised A-121 (viewed): cloud round the wall-read light in the parents' bedroom, row MK-002.
- North: a mark on the street (top) side maps to lower model x; right = +y (test).

## Tests: `python -m pytest tests/markup` = 11 pass (~6 s). Negative: title block, mirrored (-y,-x), rotated 180, old north-up(+y), stale frame, rotated page, rejected/undecided/no-reason closes, unknown element.

## Open items
- Review page export: columns `sheet,text,author,date` + either `element` or `x_mm,y_mm` (paper mm, lower-left origin, y up); CSV or JSON (`{"comments":[...]}`). The page needs to emit these.
- Frames for site/section/elevation/callout sheets (elevations need a view->model map from RV2's line-art views).
- Decisions: tolerance 3 mm paper (policy); a Text note's anchor is its icon top-left; frames file must be re-recorded (`frames`) when RV2 changes layout (ingest fails loudly otherwise).
- The sheet PDF PyMuPDF annotations by phone viewers were not tried; only PyMuPDF-written annotations.
