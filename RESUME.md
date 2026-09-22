# Resume this session

## The command

```
cd C:\Users\mmbka
claude --resume 02db61f0-bee7-4f37-bea3-95928d4943d2
```

**The `cd` matters.** The session is registered under the directory it
started in (`C:\Users\mmbka`), not under `arch-pipeline` where the work
ended up. Resuming from the wrong directory will not find it.

| | |
|---|---|
| **Session ID** | `02db61f0-bee7-4f37-bea3-95928d4943d2` |
| **Transcript** | `C:\Users\mmbka\.claude\projects\C--Users-mmbka\02db61f0-bee7-4f37-bea3-95928d4943d2.jsonl` |
| **Web link** | <https://claude.ai/code/session_016cMtz6h5ESSdNk7YhYy6rB> |
| **Project** | `C:\Users\mmbka\arch-pipeline` |
| **Date** | 2026-09-20 · Claude Code 2.1.278 |

Other useful forms:

```
claude --resume                 # interactive picker of recent sessions
claude -c                       # continue the most recent in this directory
claude --resume <id> --fork-session   # branch off without altering the original
```

Subagent transcripts (SheetAgent, ViewerAgent) are kept alongside, under
`...\02db61f0-bee7-4f37-bea3-95928d4943d2\subagents\`.

---

## Where things stand

Full reasoning lives in [`docs/PRD.md`](docs/PRD.md); the approved plan is
at `C:\Users\mmbka\.claude\plans\witty-cooking-sundae.md`.

### Done and verified

- **Method defined** — the Villa Design Method: 8 stages, 13 backward
  loops, 4 thrash controls. `docs/method/villa-design-method.md`.
- **Docs** — PRD, 7 ADRs, discussion log with rejected options.
- **Stages 0–2 working** — `brief`, `site`, `fit` commands. No Revit or
  AutoCAD needed.
- **Solar position** — NOAA algorithm, 14 checks including London
  sunrise/sunset within 2 minutes of published almanac times.
- **AutoCAD pipeline** — spec → DXF → DWG → A3 sheet at a verified
  1:50.0000, headless.
- **Rule engine** — 12 Neufert-cited rules, achieved-vs-required.
- **Web review sheet** — platform-independent storage, JSON export.
- `scripts/verify.py` — 16 checks, positive **and negative**.

### Next up (M5)

**Stage-aware rules and the fix ladder.** The method doc currently
promises more than the code delivers: cheapest-fix-first and blast radius
exist only in `feasibility.py`. The 12 rules in `rules.py` still emit bare
findings with no stage tag.

Close first: `brief.py` uses occupancy names (`hall`, `utility`, `store`,
`dressing`, `garage`) that `rules.py` does not know, so brief-compliance
checking would silently see no circulation rooms.

### Blocked on you

1. **Real plot and statutory envelope.** `spec/villa-site.yaml` is
   invented — dimensions, setbacks, plot ratio, location. **Latitude
   changes every orientation number**; the current study is Cairo as a
   stand-in.
2. **The brief interview.** `spec/villa-brief.yaml` is a placeholder meant
   to be replaced by interview, not by editing the file.
3. **Your DWG / sketch / PDF files** — dirty-drawing ingest cannot be
   built against imagined input.
4. **Revit + pyRevit install** (~30 GB). Unverified risk: whether
   `pyrevit run` supports command-line automation. The Revit story leans
   on it and it is untested.

### Known unfixed

- Dashed linetypes plot **solid** through the AutoCAD layout viewport.
  Narrowed to the plot path — the same geometry renders dashed in the web
  sheet. Cause not isolated.
- SHX text gives PDFs no selectable text (one-line fix to a TrueType font
  in `layers.py`).
- The published review sheet is still **version 1** — pre-furniture,
  Claude-only storage, no markup tools. The rebuilt page sits on disk at
  `out/web/index.html` and was never republished.
  <https://claude.ai/artifact/8NomCjZgCA2e6ruv8RnHyi>

---

## Fast restart

```
cd C:\Users\mmbka\arch-pipeline
PYTHONPATH=src .venv/Scripts/python scripts/verify.py    # expect: ALL PASS (16)
PYTHONPATH=src .venv/Scripts/python -m archpipe fit spec/villa-brief.yaml spec/villa-site.yaml
```
