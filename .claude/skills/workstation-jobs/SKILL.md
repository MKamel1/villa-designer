---
name: workstation-jobs
description: Run cached Blender views, lighting probes, Radiance studies, portable verification and bounded design sweeps on the configured Ubuntu workstation.
---

Use `run_workstation_job` or `scripts/workstation.py`; do not reconstruct
deployment and rendering shell commands. Read [worker operations](../../../docs/ops/workstation-jobs.md)
for the specific operation, setup or failure under investigation.

Start with the compact result. Read the referenced report and failed job
logs only when needed. Job success reports completed execution; candidate
`design_passed` and physical validation remain separate gates.

Use saved-model text extracts for actual design evidence. Candidate sweeps
are unbuilt alternatives and never overwrite extracted geometry. Native
Revit files and live installed-family tests stay on Windows; Ubuntu
verification declares that coverage unavailable and uses synthetic cases.

Retain the worker's bounded concurrency and graphics lock. Run timing
benchmarks in isolation. Reuse requires matching input/runtime hashes and
intact output artifacts; retry a failed attempt through the same operation
after fixing its cause. Do not remove process locks or hand-edit manifests
to force reuse. A changed dependency lock requires `workstation.py setup`.

Record a demonstrated worker failure in its owning regression and
`docs/LEARNINGS.md`. Rendering and lighting interpretation also follow the
existing lighting-proof workflow; a completed image alone is insufficient.
