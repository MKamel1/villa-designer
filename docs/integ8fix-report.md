# Integration 8 repair

Base: `b6343c5`, branch `codex/integ8fix`. No commit created.
Read the lead's `~/archpipe/logs/lanes/laneM-suite.log`: 1506 tests,
one failure and two errors. Reproduced all three before editing:
`out/integ8fix/before-c14.log` and `out/integ8fix/before-subjects.log`.

- The package audit still expected the pre-`6be1230` implementation. Kept
  exact fingerprint enforcement and recorded the reviewed replacement,
  previous digest, commit, reason and `tests/test_release_package.py` proof
  in the audit fixture. The replacement was independently computed from
  `git show 6be1230:scripts/workstation.py` and matches current source.
  Earlier integration `d400cec` similarly updated a reviewed garden
  fingerprint with its rationale; this C14 fixture had no prior amendments.
  Added clean and injected-edit proofs for package and its digest sibling.
- Production loads `villa_render_contract` before calling `subjects`.
  `f2abe02` correctly introduced its shared mounted-assembly selector;
  two extracted-function test namespaces had absent/partial modules.
  Both now bind the real contract module. The garden test uses actual
  bounds and perspective projection, preserving the empty-corner refusal
  and actual-vertex acceptance. Added real render-call coverage for
  mounted descendants, removed ownership and missing subjects.

Production rendering and packaging code required no changes. Registered
both controls in `knowledge/darkviews-guards.json`, captured the causes in
`docs/LEARNINGS.md`, and updated the integration audit workflow in
`docs/ops/agent-dispatch.md`. No `.agents/` files changed.

Validation uses `/home/omar/archpipe/envs/b16842c6f2161c9d/venv/bin/python`,
`PYTHONPATH=src`, `NO_COLOR=1`, and process exit status.
Portable verification: normal and initially empty HOME both exit 0,
206 checks each, `RESULT: ALL PASS`. The empty HOME was created with
`tempfile.TemporaryDirectory` and checked empty before launching the child.
Focused command: `python -m unittest tests.test_c14_phase2b
tests.test_garden_g4d tests.test_garden_render_subjects tests.test_darkviews
tests.test_render_views tests.test_release_package`: **69 tests, exit 0**
(926.855 seconds).

Full discovery: `python -m unittest discover -s tests`: **1508 tests,
13 skips, exit 0** (7352.010 seconds in tests; 7669.520 seconds including
discovery and cleanup). Expected negative-test `FAIL` messages are
preserved in the log; the process exit status determines success.

Evidence: [exit receipts](../out/integ8fix/exit-status.json),
[full suite](../out/integ8fix/suite.log), [focused modules](../out/integ8fix/focused.log),
[normal verification](../out/integ8fix/verify-normal.log),
[empty-HOME verification](../out/integ8fix/verify-empty-home.log).
Pre-fix reproductions: `out/integ8fix/before-{c14,subjects}.log`.
Final `git diff --check` passes. No production source files changed.

Pre-existing documentation observation: `HEAD:docs/LEARNINGS.md` already
contains three trailing merge-marker lines (commits `038e476`, `f2abe02`,
`7556af2`). They remain unchanged; resolving that separate merge residue
is outside these two regression repairs.
