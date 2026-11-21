# L5 drawing set (D1)

## Revit probe (step 1): Revit 2027 could not be driven from this shell

What was run: a copy of `out/villa/furnish-d1/revit/omar-option-D1F.rvt` in this worktree's `out/l5/`, and
`pyrevit.exe run <absolute path>\revit\sheets\probe_headless.py --revit=2027` (script opens the copy with
`app.OpenDocumentFile`, counts levels/rooms/doors/windows/grids/sheets/title blocks, closes without saving).

What happened:

- `pyrevit.exe` started and launched `Revit.exe` (2027.3) in desktop session 1. The process stayed `Responding`
  with ~3 s of CPU in 12 minutes; the probe's output JSON was never written, so the script never ran.
- The only other windows were a Chrome tab titled "Sign in - Autodesk" and Revit's own frame. The most likely cause
  is that Revit 2027 is waiting for an Autodesk sign-in that this non-interactive shell cannot complete. A screenshot
  from this shell showed only the wallpaper (my shell does not see the user's real desktop), so the dialog was not
  visible to me. This is an inference, not a confirmed cause.
- Both processes were started by this probe (nothing was running before) and were killed afterwards. No model was
  saved, nothing was written to `out/villa`.

Therefore: step 2 (native Revit sheets, tags, dimensions, sections, PDF export, Revit read-back) is **not done and
not tested**. `revit/sheets/probe_headless.py` is the only Revit script; it is untested beyond the failed launch.
To retry: sign in to Autodesk in the user's session once (or run from the user's own terminal), then re-run the probe.

## What was produced (step 3, model-driven, "model-generated, not Revit")

`python -m archpipe.documents --out out/documents/D1` (PYTHONPATH=src) reads `archpipe.model.load("D1")`
(517 elements: 30 rooms, 18 doors, 8 windows, 36 walls) and writes:

| file | content |
|---|---|
| `sheetset.json` | sheet-set spec (8 sheets, views, expected counts, missing title-block fields), plan QA, SC1 result |
| `schedule-door.csv`, `schedule-window.csv`, `schedule-room.csv`, `schedules.md` | schedules from the model (copies and the two sample PNGs in `src/archpipe/documents/samples/`; the brief asked for docs/lanes/L5-samples/ but lane_guard only allows .md there) |
| `A-001-cover`, `A-101-plan`, `A-102-plan`, `A-601-schedule` (`.pdf` vector, `.svg`, `.png`) | A3 sheets |

Every sheet is banner-labelled "MODEL-GENERATED, NOT REVIT" (English and Arabic). The plans are drawn from the
L2 model's wall segments, openings, room polygons, columns and stair treads, not from a Revit view, so they are **no
evidence for BM1** (Revit as the source).

Sheet content: white background; title block with project, owner, address, engineer, Syndicate no., scale, date, drawing
title (EN and AR), sheet no., revision table with location, issue sequence; GA plans for B (-1.80) and GF (+1.20) at
1:100 with a structural grid derived from the column centres (A-G, 1-2), level mark, north point, graphic scale, room
tags (name, Arabic name, tag, net area), door tags (D01..) and window tags (W01..), and per-exterior-wall opening
dimension chains plus grid and overall chains on all four sides. Arabic is shaped by `archpipe/documents/arabic.py`
(no external dependency).

Not produced: A-201/A-202 elevations and A-301/A-302 sections (need Revit geometry; the sheet index says so), the
roof/site sheet, a finish schedule, a GF/L1 sheet for the apartment (not ours).

## QA counts (run 2026-11-20)

| check | A-101 (B) | A-102 (GF) | target |
|---|---|---|---|
| untagged doors / windows / rooms (draw lists) | 0 / 0 / 0 | 0 / 0 / 0 | 0 |
| untagged doors / windows / rooms (read back from the exported PDF text) | 0 / 0 / 0 | 0 / 0 / 0 | 0 |
| exterior walls without a full chain set (opening + grid + overall) | 0 of 14 | 0 of 8 | 0 |

SC1 (`crosscheck.sc1`): door 18 = 18, window 8 = 8, room 30 = 30 schedule rows vs model; ids equal; tags unique (56);
tags on the plans equal the schedule rows. Revit schedule counts: **not_evaluated** (Revit not run), so SC1 is
`ok` but `evaluated = false`; it must not be read as a pass of the Revit half.

Tests: `PYTHONPATH=src python -m pytest tests/documents -q`, 8 passed (positive and negative cases for the tag QA,
chain QA and SC1). `python scripts/lane_guard.py L5` prints `lane L5: clean`.

## Gaps and caveats

- No Revit output at all (see probe). DS2 elevation/section callouts, ST1 structure clash, BM1 are not evaluated.
- Owner, engineer, Syndicate number are **not supplied** anywhere in the repo; the title block prints "NOT SUPPLIED"
  in red. The address is the city-level value from `spec/villa-site.yaml` (plot not surveyed). DS1 therefore stays
  open until those are provided.
- Arabic names and titles are written by the pipeline and unreviewed. DS4 for drawings is UNVERIFIED as a legal rule.
- "Issue sequence" is the sheet's position in the index, a placeholder for a real issue register.
- The D1 model snapshot excludes the ~14 later build patch passes (see `L2-model.md` gaps), so the plans may differ
  from the built Revit model in small positions. Door swing sides follow `swing_into` or the first room, not a
  surveyed hinge side. Tags are placed by rule and may overlap small rooms (0.4 to 3 m2 rooms get a compact tag).
- Wall dimension chains on inner exterior walls pass through the plan; no automatic de-cluttering.
- `plans.qa` draw-list counts are partly self-referential; the PDF-text read-back is the independent count.
