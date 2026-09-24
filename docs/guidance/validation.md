# Guidance implementation validation — 2026-09-24

The implementation retains stages 0 through 7 and the existing rendering input
contracts. It adds eight guidance packages, eight stage skills, two specialist
roles, three read-only server operations, a source registry, evidence cards,
precedent study, acquisition manifest, quality-brief template and existing-rule
audit. The fictional villa pilot compares three spatial organisations; the bedroom
exercise uses the committed measured model. All example approval gates stay closed.

Executed checks:

- Full regression discovery: **116 tests passed**, including 17 guidance tests.
  The worker-unavailable line is an expected negative-test output; suite result
  was successful.
- `scripts/verify.py`: **ALL PASS**, including existing geometry, photometry,
  rule declarations, native-model fixtures and learned guards.
- `scripts/test_mcp.py`: real standard-input/output client/server session passed
  with twelve tools. New operations returned missing facts, evidence provenance,
  the pavilion privacy failure, cached review and errors for invalid arguments.
- Nine villa skill files passed skill validation; all 27 generated agent/skill
  adapters matched canonical inputs.
- `scripts/demo_guidance.py`: all eight repeated villa-stage reviews reused
  their prior results; the report records index-cache hits and misses. Area
  arithmetic returned 370 square metres against a 400 square metre scenario
  allowance. This establishes arithmetic, not geometric or statutory feasibility.
- Original concept diagram rendered locally for visual inspection. Independent
  critique identified a route/room contradiction; correction was confirmed and a
  regression now checks the actual diagram geometry against the historical defect.

Negative tests cover wrong/missing edition context, wrong units, misread numerical
values, incompatible climate/hemisphere assumptions, qualitative advice promoted
to a numerical target, missing facts, unapproved gates, changed source editions,
changed project taste, changed artifacts, changed presentation images and changed
requirement traces. Tests also preserve all six measured bedroom furniture objects
and catch the known accessory-overlap failure class.

The [independent critique](pilot-independent-critique.md) remains part of the
record. Its initial drawing contradiction and vague fact-status reporting were
corrected. Its requests for scaled two-storey plans, stair/structure/service
overlays, comparable alternative quantities, comfort studies, landscape proof and
the two-worker study decision remain unresolved. The diagram is a spatial study,
not a dimensioned building design.

No new native Revit model or final rendered presentation was produced during this
guidance task. The transport test skipped its optional photoreal-image check
because that image was absent. Claude's rendering changes were preserved. Source
verification is limited to the scoped public passages in the registry; no licensed
numerical standard was obtained or silently enabled. See the
[acquisition manifest](coverage-and-acquisition.md) for the remaining originals.

Generated demonstration detail is at `out/guidance-demo.json`; rerun the demo to
refresh it after changes. This record establishes software and workflow capability,
not completed villa design or client acceptance.
