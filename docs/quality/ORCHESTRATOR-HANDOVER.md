# Orchestrator handover — villa A+ programme (from the laptop session, 2026-11-21)

You are the lead (orchestrator) of a parallel multi-agent build that takes the client's villa (design D1)
to the A+ bar. You plan, brief, verify and merge; Sonnet 5.5 lanes implement. Everything runs on this
workstation (client decision 2026-11-21).

## Read first (in this order)
1. `docs/quality/A-PLUS.md` — what "done" means; overall grade = lowest discipline.
2. `docs/quality/PLAN.md` — waves, lane ownership, **§9 scope decisions log** (client decisions; obey them).
3. `docs/quality/LANES.md` — the protocol every lane follows; `ops/lanes.yaml` — file ownership.
4. `docs/quality/REVIT-REPLACEMENT-PLAN.md` (approved) and `docs/quality/LIGHTING-VERIFICATION.md` (V1–V12).
5. `docs/reviews/2026-11/README.md` — the critical review that started this; `STATUS.md`.
6. Your memory directory (copied from the laptop session) — client preferences and standing rules.

## Standing rules (from the client; also in memory)
- International best practice is the bar; Egyptian code is informative only.
- No pricing or budget yet; quantities and specifications only.
- Propose any NEW capability to the client before building it (multi-select question).
- Revit-free, with no loss of functionality; scenes build only on Linux (this machine).
- Lighting results must pass independent verification (lane LV, which may not edit the engine) before
  merge; every task met at ≤ 80 % dimmer (V12); no physical lux check (too late after purchase).
- Prefer luminaires with public photometric datasheets; "common products" + a performance spec sheet for an
  Egyptian supplier, with a substitution loop (`python -m archpipe.luminaires.substitute`, lane L6c).
- Renders must be faithful (no invented content), 24 mm lens default, client naming: street side = NORTH.
- Lead does not implement; decide close choices yourself; escalate only what blocks.

## Where things are
- Repo: `~/archpipe/lead` (GitHub `MKamel1/villa-designer`), branch **`integ/aplus`** = integration line.
  Never push to `main`; it reaches main later by PR. Background-job rule: no force-push.
- Lanes run as unattended Claude Code services:
  `systemd-run --user --unit=lane-<ID> --collect ~/archpipe/ops/run_claude_lane.sh <ID> ~/archpipe/lanes/briefs/<brief>.md`
  - clone `~/archpipe/lanes/<ID>`, branch `lane/<ID>` (resumes `origin/lane/<ID>` if it exists)
  - status `~/archpipe/lanes/<ID>.status` (running|done|failed), log `<ID>.log`, hand-back `<ID>.report.md`
  - permissions: full bypass (client decision). Add each new lane's paths to `ops/lanes.yaml` first.
  - wait for completion with a background until-loop on the status files, never by sleeping.
- Python: `~/archpipe/envs/laneP-venv/bin/python` (pytest, shapely, ifcopenshell 0.9, ezdxf, openpyxl);
  browser for public manufacturer pages: `xvfb-run -a ~/archpipe/envs/browser-venv/bin/python …` (real
  Chrome via Playwright; public pages only, no logins, skip sites that challenge).
- GPU/CPU jobs: `~/archpipe/bin/jobq submit [--gpu] --timeout S --id X -- cmd` (docs/lanes/L8-runner.md).
- Shared data: `~/archpipe/shared/assets/user` (symlink into clones as `assets/user`),
  `~/archpipe/shared/laptop-out/{villa,photoreal}` (copied laptop `out/`: final renders, read-backs, PDFs,
  Revit models), `~/archpipe/shared/client/omar.rvt` (client's original model), `~/archpipe/shared/revit-readback/`.
- Review page for the client: https://claude.ai/artifact/9SWRx9rTgXYAbcskN9C7yc (update it at milestones).

## Merge procedure (do not skip — a lighting merge once broke 14 downstream tests)
1. `git fetch origin lane/<ID> && git merge --no-ff origin/lane/<ID>` in `~/archpipe/lead`.
2. Run the FULL lane suite, not just the lane's tests:
   `PYTHONPATH=src python -m pytest tests/luminaires tests/compliance tests/design tests/model tests/electrical tests/lightcalc tests/lightverify tests/critic tests/ops tests/documents tests/drawings2d tests/pipeline tests/exchange tests/approvals -q`
3. `PYTHONPATH=src python -m archpipe.compliance.run_d1` → 0 failing gates (revert the regenerated report).
4. Look at any visual output yourself (Read the PNGs) — sheet QA once passed sheets with reversed Arabic.
5. Push `HEAD:integ/aplus`; update `STATUS.md` / PLAN §9 when a decision was made.

## State at handover (2026-11-21 ~12:30 MST)
Merged on `integ/aplus`: review + A+ definition + plan; contracts; L1 safety (0 failing gates) + D (G1
fixes) + FIX1; L2 model + M completion (696 elements, net areas from walls, door handing, existing structure
frozen) + P2 element ids; L3 render critic; L5/RV2 drawing set (20 sheets, north-up, Arabic fixed); RV3
IFC/DXF/quantities (59/59 round-trip); L6/L6b lighting (bugs fixed, V12 ≤ 0.772) + LV verification; LP
(ERCO products V10-verified); L7/L7b electrical (77.6 kVA, 3-phase); L8 job queue; RA approvals review; R sources.

**Known broken on integ:** after the lighting merge, ~14 downstream tests fail (electrical, exchange,
schedules, model snapshot). Lane **INT** is fixing this.

Running lanes (check `~/archpipe/lanes/*.status`):
| Lane | Brief | On completion |
|---|---|---|
| INT | integration after lighting: snapshot, electrical with real zones, exchange, schedules | merge; integ must be fully green |
| L6c | re-bind lighting to V10-verified products (ERCO), supplier spec sheet, substitution loop | merge, then re-run INT (one command in docs/lanes/INT-integration.md), then LV final verification |
| RA2 | make the production scene build (B1–B5: planting, furniture receipts incl. store/cupboard clash, contract ignores ids, stair test, exposure re-measure) | merge; then launch RV1 checks |

## Next, in order
1. After RA2: **RV1** independent Revit-replacement checks on the built scene (parity contract
   `knowledge/parity/revit-uses.json`; must FAIL on the 13 historic Revit-caught defects + seeded mutations).
2. After L6c + INT: **LV final verification** (V10 with ERCO lab data; V11 DIALux needs Windows → laptop, one-off).
3. Re-render the set (L9) on the workstation with the L3 critic as a gate (calibrate further on good views),
   then the blind photo test.
4. **MK** markup loop (client wants it): sheet/review-page comments → change requests linked to element ids.
5. Electrical: EA7/EA9/EA10 need the utility's earthing type and RA; Revit read-back no longer applies.
6. Later (approved): automatic layout generation, mood and material boards (needs a style concept —
   lane L4 products/style is PAUSED by the client; ask before resuming).

## Open items needing the client
- Confirm the 8 door-handing judgement calls (marked "?" on the plans).
- Title-block owner / engineer / Syndicate number (currently "NOT SUPPLIED").
- Brief interview still open: daughters' ages/identities, style references; plot survey/setbacks.
- Send the luminaire spec sheet (L6c output) to an Egyptian supplier; feed back alternatives.
- Data backup destination for non-git data (deferred by the client).
- V11 DIALux cross-check must run on the Windows laptop.

## Gotchas
- Line endings: `.gitattributes` forces LF; IES/LDT/PDF are binary (hash provenance).
- Never read silently from untracked `out/`; inputs must be tracked or fail loudly.
- The scene build takes ~90–170 s here; the laptop cannot build it (libm drift).
- `claude -p` lanes cannot receive messages; to redirect, stop the unit and relaunch with an updated brief
  (work is preserved on `origin/lane/<ID>`).
