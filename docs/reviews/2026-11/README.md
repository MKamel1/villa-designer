# Project review — 2026-11-20

Critical review of arch-pipeline (villa-designer) after the work paused on 2026-10-16.
Scope: what was built and tried, project structure, operations, the quality of the D1
deliverables, and what it takes to reach A+ automated architecture, interior, lighting and
electrical design.

Method: read-only reviews by independent agents, each with a narrow brief and the evidence
named. Detailed reports sit beside this file:

| Report | Reviewer brief |
|---|---|
| [visual-audit.md](visual-audit.md) | All 38 final renders graded A–F against the bedroom benchmark; QA verdict compared |
| [panel-architecture-interior.md](panel-architecture-interior.md) | Egypt-practice architect + senior interior designer reviewing D1 as a consultant submission |
| [panel-lighting-electrical.md](panel-lighting-electrical.md) | Lighting designer + Egyptian residential electrical engineer |
| [workstation-ops.md](workstation-ops.md) | ai-workstation jobs, reliability, reproducibility, data inventory |

Code-structure, history and capability-gap findings came from three exploration passes and
are summarised below (no separate file).

## Verdict

The project built an unusually honest **checking and measuring** system: every rule cites a held
source, results are reported as achieved-versus-required, the render is photometrically
calibrated (render vs calculation within 0.4 %), and daylight is validated against closed-form
cases. That core is worth keeping.

What it does not yet do is **produce professional output**. The final renders grade a median
C−/D+, the plans are not issuable, there is no Egyptian code, no real products, no electrical
design, and the automated QA passes 77 % of views that a reviewer would reject. Since late
September most effort went into process machinery rather than into the output.

## Scorecard

| Discipline | Today | Main reason | Gap to A+ |
|---|---|---|---|
| Architecture | **D+** | UK/US rules only; basement living unflagged; open-riser stair with >100 mm gaps; single stair, dead-end hall; plans undimensioned | Egypt code pack, life-safety checker, planning envelope, issuable sheet set |
| Interior design | **C−** | Strong clearance/ergonomic planning, but no style identity, products are "assumed envelopes", no finish/FF&E schedule, boards or elevations | Style engine, Egyptian product library with EGP prices, schedules, elevations/joinery |
| Lighting | **C+** | Calculation tools B+; design package D: over-lighting (dining 797 lx vs 100), no glare (UGR/DGP), scattered downlights, no exterior, no controls | Whole-room Radiance calc report, glare, RCP setting-out, DALI scenes, exterior + emergency |
| Electrical | **F** | Does not exist | Placement → circuits → load → sizing → panel/SLD → Revit |
| Visualisation | **C−/D+** median | Crude assets, one exposure lock crushing/clipping 11 views, material scale, camera occluders, repeated styling | Vision critic gate, curated asset library, texel-density and camera standards |
| Engineering | **C** | Good verification habits; but scene build is ~14 in-place patch passes, 6,000-line guard registry, tests are mostly snapshot bookkeeping | One design data model; data-driven guards; quality tests |
| Operations | **C−** | No offsite backup of 213 GB; three job paths, two stuck jobs; auto-resume reports crashes as done; 4 lanes sharing one Codex quota | Backup, one job runner with a GPU lock, one lane |

## What was tried, and what it taught

| Period | Work | Outcome |
|---|---|---|
| 09-21 → 09-23 | Bedroom end-to-end (Revit → Blender → Radiance) | Worked; 0.4 % render/calc agreement. Best result of the project. |
| 09-24 → 09-25 | Knowledge base sprint: sourced rules, 469 products, thermal, hand-off package | Deep but premature: built for a pilot before the real brief and site existed; mostly unused on the villa. |
| 09-25 → 09-26 | Concept rounds 1–12 | Fast and useful; client drove stair/parking rework. Layout stayed hand-authored. |
| 09-26 | Whole-building daylight | Caught real under-glazing → full-height glazing. Analysis paying for itself. |
| 09-27 | First D1 render set | Critic rejected it; 9/14 had passed pixel QA. The QA blindness was known from here on. |
| 09-29 → 10-09 | 217 lessons → classes C1–C16, guard registry batches reg1–15 | ~72 % of commits in this window; exposure, floating fittings, crude geometry still recurred 2–4×. |
| 10-01 → 10-06 | C4 finished-surface mounting | Floating fittings fixed only at C4i, via patch passes and approval-row migrations. |
| 10-06 → 10-08 | Garden G1–G6b | Delivered; interrupted by the north-naming confusion. Procedural plants read as "lollipops". |
| 10-08 → 10-14 | Beds, desks, storage | 7 bed rounds, 14 storage candidates; mostly stand-ins retained. Asset hunting per round does not converge. |
| 10-15 → 10-22 | Exposure groups; walkthrough (walk2); TRELLIS-2 asset trial | No walkthrough accepted; walk2 and TRELLIS left uncommitted on the workstation (now on `backup/*` branches). |

Lessons that should shape what comes next:

1. **Guards written after the defect do not prevent the next defect.** The recurring failures were
   classes (asset crudeness, exposure policy, mounting), and the fixes were instance guards.
2. **Pixel statistics cannot judge a render.** A near-black view (v30) passed. Quality needs a
   critic that looks at geometry, materials and composition.
3. **Asset quality is the ceiling on render quality.** The frangipani and rattan chairs (real assets)
   are the best things in the images; procedural stand-ins are the worst.
4. **Parallel agent lanes did not add throughput.** The bottleneck was Codex quota (all 43
   non-zero lane exits), so four lanes split one quota and added 42 merges and custom merge tools.
5. **Depth before inputs is waste.** The brief and site are still placeholders; every orientation,
   code and planning figure depends on them.

## Structure: keep, fix, delete

**Keep:** `rules.py` + evidence cards + citation discipline; `photometry.py`, `lighting.py`,
`radiance.py`, `daylight*.py`, the photometric render calibration; `worker.py` content-addressed
jobs; the perf work; ADRs; the client-decision records.

**Fix:**
- `concept/villa_render.build()` runs ~14 in-place passes (migrate → approvals → guest_fixes →
  … → garden_g4d.integrate). Replace with one canonical placed-object record per item that every
  builder reads; dated modules (`garden_g6*.py`, C4 `*_mounting`) become data.
- `guard_registry.py` (6,002 lines) → one data record per guard; stop adding guards for single
  instances; keep only those proven on a real defect *and* covering a class.
- Tests: 66 snapshot fixtures (41 MB) prove "unchanged", not "correct". Add quality tests
  (vision-critic recall on the graded set; code-pack positive/negative fixtures).
- `render_qa.py`: escalate ≥2 WARNs; measure exposure on subject pixels; then put the vision critic in front.
- Workstation: one job path, `graphics.lock` for every GPU job, systemd user units instead of tmux,
  relaunch dead jobs; move root scripts into `ops/workstation/`.

**Delete / consolidate:** the two `out/perf-*/out` directory junctions (recursive loop on the
laptop); 31 phase checkpoint/report docs → one architecture doc + `STATUS.md`; stale ROADMAP,
RESUME, HANDOVER; ~45 merged lane branches and 4 stale worktrees; unreferenced one-off scripts
(`checkpoint_mounting_bc/_f/_final`, ~10 `garden_g*_proof/diagnose` scripts); `dispatch.sh`,
`patch_release.py` on the workstation.

## Roadmap to A+ automated output

A realistic aim: the system produces a **complete, checked design package that a licensed
Egyptian architect and electrical engineer review and stamp**. Permits legally require a
licensed signatory, so "replace" means doing the design and documentation work, not the signature.

The principle changes from *reactive guards on a hand-built model* to *generate options → score
with calibrated critics → human decides at gates*.

### Stage A — Stabilise (days)
- Offsite backup of irreplaceable data (see below). Remove the `out/` junctions.
- One branch (`main`) + at most one implementer lane. Prune branches/worktrees.
- `STATUS.md` replaces ROADMAP/RESUME/HANDOVER as the single current-state page.
- Workstation: one job runner, GPU lock, systemd units, dead-job relaunch.

### Stage B — Foundations (weeks 1–3)
1. **Real inputs:** client brief interview and plot survey into `spec/` (replaces placeholders).
2. **Egypt code pack** through the existing `codes.py`: Law 119/2008 + executive regulations,
   fire code, held PDFs, clause cards with positive/negative fixtures.
3. **One design data model** (IFC-aligned building/room/element/finish/fixture graph) that the
   scene, Revit, schedules and lighting all read. Retire the patch passes.
4. **Process diet:** freeze guard registry growth; guards become data; one STATUS page per milestone.

### Stage C — Quality loop (weeks 3–6)
5. **Vision critic gate:** 12-item rubric from the visual audit, scored by a VLM; calibrated on the
   38 graded views (report seeded recall, target ≥ 90 % on D/F views, ≤ 10 % false fails on B views);
   blocks publish.
6. **Curated asset library + product catalogue:** real SKUs available in Egypt, dimensions, EGP price,
   supplier, lead time, 3D model; placement binds to the product. No per-round asset hunting.
7. **Style engine:** named concept, 5–7 colour palette with LRV, materials, banned items; renders
   and FF&E validated against it; mood and material boards generated.
8. **Render standards:** texel-density check, 24 mm default lens, occluder/crop rules, an exposure
   policy decided once with the client (set-wide lock vs per-view development).

### Stage D — Professional deliverables (weeks 6–10)
9. **Issuable Revit sheet set:** dimensions, grids, levels, tags, sections, elevations, door/window
   schedules, title block, bilingual labels; sheet-QA counts zero untagged/undimensioned items.
10. **Interior package:** FF&E and finish schedules, interior elevations, joinery details.
11. **Lighting package (L1–L6):** per-room Radiance calc report (Em, U0, UGR), RCP setting-out solver,
    DALI zones and scenes, exterior and emergency, LM-83 sDA/ASE; each tested against CIE/LM reference cases.
12. **Life safety + climate:** stair/guard/egress checker (must fail the v03 stair), façade shading design.

### Stage E — Electrical (weeks 10–14)
13. **`archpipe.electrical` (E1–E6):** device placement rules, circuits, maximum demand, cable and
    protection sizing with voltage drop (IEC 60364 tables at 45–50 °C), panel schedule and
    single-line diagram, Revit circuits read back. First step: confirm the exact Egyptian code edition.

### Stage F — Generation (after the critics are trusted)
14. **Layout and furniture solver** with the rules engine and critics as objective; **RCP solver**
    for luminaires. Only once the critics have measured recall, so generation is scored, not guessed.

## Backup status (done 2026-11-20)

- All code is on GitHub (`MKamel1/villa-designer`). Verified: no branch on the laptop, the
  workstation bare repo, or the workstation lanes has a commit missing from GitHub.
- Uncommitted work was snapshotted without touching the checkouts:
  `backup/walk2-wip-2026-11-20` (laneA, 64 files), `backup/trellis-wip-2026-11-20` (laneB, 8 files),
  `backup/process-revit-extract-wip-2026-11-20` (laptop `arch-pipeline-process`, 3 files).
- Also pushed: `agy/cands8`, `agy/reg14`, `codex/search2`, `diag/v15-cast`, `tmp/reg13-check`,
  `wip/c4`, `lessons/process`, `integ/lessons`.

**Not yet backed up (needs an owner decision on where):**
- Laptop: the client's original Revit model `C:\Users\mmbka\omar.rvt` (300 MB) and derived
  `out/villa/omar-*.rvt` (1.3 GB); final render set `out/villa/finals-2026-10-15/`.
- Workstation (~29 GB, ~15 GB without Sketchfab): `library/fab` 12 G, `library/sketchfab` 14 G,
  `assets/library` 2.5 G, user luminaires 0.23 G, prompts + root ops scripts, the Radiance tarball,
  compressed lane logs. Everything else is regenerable. `rclone` is installed on the workstation.
