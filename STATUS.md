# STATUS — current state of arch-pipeline

Single current-state page. Supersedes `docs/ROADMAP.md`, `RESUME.md` and `docs/HANDOVER.md`
for "where are we" (those are kept for history; they describe 2026-09-20 → 09-24).

**As of 2026-11-20.** Work paused 2026-10-16 (`main` = e24189c, integ-10).

## Where things are
- **Code:** GitHub `origin/main`. All branches from laptop and workstation are on GitHub;
  uncommitted lane work is on `backup/*` branches (walk2 walkthrough, TRELLIS-2 trial, Revit extract fix).
- **Design:** D1 (client-accepted direction), round 12, rendered set `out/villa/finals-2026-10-15/`
  (laptop, not in git). Revit source: `C:\Users\mmbka\omar.rvt` (client model, copy-only).
- **Heavy compute:** `ai-workstation:~/archpipe` (Blender/Cycles, Radiance, lanes in `work/`).
- **Inputs still placeholders:** `spec/villa-brief.yaml`, `spec/villa-site.yaml`.

## Open items
- Walkthrough: no accepted clip; walk2 WIP on `backup/walk2-wip-2026-11-20`.
- Kids' beds and vanity seat: candidate research only (`agy/cands8`).
- Exposure policy for crushed/clipped views needs a client decision.
- Offsite backup of non-git data (see review).

## Review and next steps
Full review and roadmap: [docs/reviews/2026-11/README.md](docs/reviews/2026-11/README.md).
Next stage: **A — Stabilise** (backup data, prune branches/worktrees, one lane, one job runner).
