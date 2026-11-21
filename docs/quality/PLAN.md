# Plan to A+ — villa first, product second

Goal: take the villa (D1) to the A+ bar in [A-PLUS.md](A-PLUS.md). The general product grows out
of the tools built for it. Each milestone ends with a re-grade against the criteria IDs listed;
nothing moves on without an explicit pass.

Working rules (from the 2026-11 review): one implementer lane (Codex) at a time; research and
sourcing on a second worker that cannot collide (agy); Claude leads, writes briefs and reviews;
no new guard unless it covers a class of defect; one `STATUS.md` updated per milestone instead of
phase reports.

**Order matters:** legal and safety gates come before visuals. The new Egyptian rules may change
the plan (ceiling heights, basement light, courtyard sizes, stair), and there is no point
re-rendering a design that has to move.

| # | Milestone | Main work | Passes when | Needs from you | Size |
|---|---|---|---|---|---|
| M0 | Stabilise | Offsite data backup; remove the `out/` junctions; merge `review/2026-11`; laptop on `main`; prune ~45 branches and 4 worktrees; one lane; fix the 2 stuck render jobs; GPU lock on every job | Nothing at risk; one branch; workstation jobs restartable | Backup destination | 1–2 days |
| M1 | Inputs and sources | Brief interview (budget cap, each daughter's identity, style likes); plot facts: dimensions, street level, setbacks, the validity statement if issued; card ER Art.93–112 into an Egypt pack in `codes.py`; obtain fire, disability and electrical codes | `spec/villa-brief.yaml` and `villa-site.yaml` real; EG pack loads with positive/negative fixtures | ~1 h interview; plot documents; any code PDFs you can get | 1 week |
| M2 | Compliance baseline | Run EG1–EG9 and LS1–LS5 on D1; list every failure with achieved vs required; fix the design (stair to closed risers and solid guards; heights; basement openings; courtyard sizes; escape route) | All architecture gates pass on D1 (EG1–EG9, LS1–LS5) | Approve design changes | 1–2 weeks |
| M3 | One design model | Replace the ~14 scene patch passes with one placed-object record; guard registry becomes data; quality tests beside snapshot tests | Scene builds from the model with identical output; registry is data | — | 2 weeks (parallel with M4) |
| M4 | Vision critic | 12–13 item rubric (R1–R13) scored by a vision model; calibrate on the 38 graded views | Catches ≥90 % of the D/F views and falsely fails ≤10 % of B views, reported before it gates | — | 1–2 weeks |
| M5 | Interior identity and products | 2–3 concepts with mood boards; choose one; Egyptian product library (SKU, supplier, EGP, lead time, 3D); replace stand-ins; FF&E and finish schedules; styling | I1–I9, I11–I14, I17–I18 pass; budget within cap | Pick a concept; budget cap | 2–3 weeks |
| M6 | Render re-shoot | Camera and texture standards; exposure policy decided once; re-render the set; critic gate; blind test against studio photos | R1–R13 pass on hero views; blind test at chance | Exposure policy choice; final visual sign-off | 1–2 weeks |
| M7 | Documents | Revit sheet automation: dimensions, grids, tags, title block (Art.111), sections, elevations, schedules, bilingual; interior elevations and millwork; permit set (Art.112) | DS1–DS4, SC1, BM1, I15–I16 pass; sheet QA finds zero untagged/undimensioned items | — | 3 weeks |
| M8 | Lighting package | Whole-room Radiance calc report, glare, RCP setting-out, DALI scenes, exterior and obtrusive light, emergency, LM-83 daylight | LA1–LA15 pass; reference cases reproduce | Scene preferences | 3 weeks (parallel with M7) |
| M9 | Electrical | Device placement, circuits, maximum demand, cable and protection sizing, boards, single-line diagram, earthing, low-voltage systems, Revit read-back | EA1–EA15 pass; worked examples reproduce | Supply type from the utility (1- or 3-phase) | 4 weeks |
| M10 | Final review | Cross-discipline coherence (A-PLUS §5); re-grade all; optional review by a licensed Egyptian engineer | Overall grade A+ | Choose a licensed reviewer if wanted | 1 week |

Rough total: about 4–5 months at one implementer lane, shorter where M3/M4 and M7/M8 run in parallel.
The biggest uncertainty is M2: if the Egyptian gates force a re-plan of the basement or stair, M2 grows.

## What to start now

1. **M0** — needs only the backup destination.
2. **M1 sourcing** in parallel (agy): Arabic Gazette check of ER Art.93–112; the fire, disability and
   electrical code editions.
3. **M1 interview** — a short session with you, using the existing `villa-intent` stage method.
4. **M2 dry run** as soon as the Egypt pack exists: likely first failures to check are the 2.307 m
   cinema soffit (Art.93 asks 2.70 m), the open-riser stair (Art.103), the basement rooms' openings
   onto the sunken gardens (Art.96) and whether those gardens are large enough to count as courtyards (Art.98).
