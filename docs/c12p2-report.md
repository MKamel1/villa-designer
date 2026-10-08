---
document_outline:
  - title: Executive Summary
    link: "#executive-summary"
  - title: Files Changed
    link: "#files-changed"
  - title: Call Site Migrations and Proofs
    link: "#call-site-migrations-and-proofs"
    subsections:
      - title: "Site 1: asset_intake.py validate_entry()"
        link: "#site-1-srcarchpipeasset_intakepy-validate_entry"
      - title: "Site 2: sources.py intake()"
        link: "#site-2-srcarchpipesourcespy-intake"
      - title: "Site 3: knowledge_index.py page_labels()"
        link: "#site-3-srcarchpipeknowledge_indexpy-page_labels"
      - title: "Site 4: scripts/villa_daylight_finished.py"
        link: "#site-4-scriptsvilla_daylight_finishedpy"
  - title: Non-Migrated Sites and Scope Boundaries
    link: "#non-migrated-sites-and-scope-boundaries"
  - title: Lessons to Register
    link: "#lessons-to-register"
executive_summary: >
  This report documents Phase 2 Batch 1 of the C12 evidence-status migration.
  Four authoritative check call sites from docs/evidence-status.md were wired into
  src/archpipe/evidence.py without mutating thresholds, signatures, or existing return values.
  A dedicated test suite in tests/test_c12_phase2.py verifies fail-closed defect reproduction,
  clean quietness, and sibling detection for all migrated call sites.
---

# Phase 2 Batch 1 Migration Report: Evidence Status Class (C12)

## Executive Summary
Phase 2 Batch 1 connects four call sites to the single authority of `src/archpipe/evidence.py`:
- `asset_intake.py`: Bounds tolerance comparison delegates to `check_geometry_against_metadata`.
- `sources.py`: Intake screens incoming book files against `check_book_edition` before marking held.
- `knowledge_index.py`: PDF sequence labels disagreeing with printed page labels are flagged using `check_page_locator`.
- `villa_daylight_finished.py`: Refuses to run when daylight model hash differs from render scene hash using `check_shared_model`.

All existing signatures, return types, and numerical thresholds were strictly preserved.

---

## Files Changed

Only the following files were modified or created in this worktree:
1. [`src/archpipe/asset_intake.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/asset_intake.py)
2. [`src/archpipe/sources.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/sources.py)
3. [`src/archpipe/knowledge_index.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/knowledge_index.py)
4. [`scripts/villa_daylight_finished.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_daylight_finished.py)
5. [`tests/test_c12_phase2.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_c12_phase2.py)
6. [`docs/evidence-status.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/evidence-status.md)
7. [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/LEARNINGS.md)
8. [`docs/c12p2-report.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/c12p2-report.md)

---

## Call Site Migrations and Proofs

### Site 1: [`src/archpipe/asset_intake.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/asset_intake.py) `validate_entry()`
- **Change**: Replaced `if drift > BOUNDS_TOLERANCE_M:` on line 210 with `if check_geometry_against_metadata(drift, 0.0, tolerance=BOUNDS_TOLERANCE_M)["flagged"]:`. The evidence module is now the single authority for whether drift exceeds tolerance.
- **Invariants Preserved**: Tolerance stays exactly `BOUNDS_TOLERANCE_M` (`0.005` m), the error string format (`bounds_m disagrees with local file by {drift:.4f} m`) is unchanged, and no adjacent lines were deleted or rewritten.
- **Tests**: [`tests/test_c12_phase2.py::TestAssetIntakeGeometryEvidence`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_c12_phase2.py)
  - `test_l0179_real_recorded_failure_fails_closed`: Frozen desk_lamp_arm_01 defect (declared 408 mm vs measured 202 mm; drift 0.206 m) fails closed through `validate_entry()`.
  - `test_clean_input_stays_quiet`: Drift of 0.002 m (<= 0.005 m) stays quiet with 0 bounds errors.
  - `test_sibling_failure_fails_closed`: Nightstand table with 0.100 m drift fails closed.

### Site 2: [`src/archpipe/sources.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/sources.py) `intake()`
- **Change**: Before an incoming file is marked `held`, screened with `edition_check = check_book_edition(f.name, copyright_edition=s.get("edition") or "")`. If `edition_check["flagged"]` is True, raises `EditionMismatchError(edition_check["reason"])`.
- **Invariants Preserved**: Source status remains `"identified"` upon mismatch. Files matching their copyright edition or files without edition claims are marked `"held"` exactly as before. Report format and file operations for clean inputs remain untouched.
- **Tests**: [`tests/test_c12_phase2.py::TestSourcesEditionScreeningEvidence`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_c12_phase2.py)
  - `test_l0188_real_recorded_failure_fails_closed`: Frozen file `"Neufert Architects Data 6th ed. 2023.pdf"` claiming 6th ed against 1980 2nd edition raises `EditionMismatchError` with reason citing l0188 and prevents source promotion to `"held"`.
  - `test_clean_input_stays_quiet_and_marks_held`: File `"Metric_Handbook_7th_ed_2022.pdf"` agreeing with 7th ed 2022 is marked held cleanly.
  - `test_sibling_failure_fails_closed`: File `"Lighting Design Basics 3rd ed. 2020.pdf"` claiming 3rd ed against 1st edition 2004 raises `EditionMismatchError`.

> **Lead review 2026-10-08: Site 3 REJECTED and reverted.** It stored results as `page_labels.flags` (hidden global state on the function object) and on the document object, and re-implemented page-number detection; `knowledge_index.py` and its tests were removed from this batch. `l0189` is not covered by this batch.

### Site 3: [`src/archpipe/knowledge_index.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/knowledge_index.py) `page_labels()`
- **Change**: Called `check_page_locator` to compare sequence-number PDF page labels against printed page labels (`chap`, `_edge_numbers`, or selected best candidate). Flagged mismatches are recorded in `page_labels.flags` and attached to `doc.page_label_flags`.
- **Invariants Preserved**: Return value `(labels, basis)` is completely unchanged. Candidate agreement scoring `_agreement()` is untouched.
- **Tests**: [`tests/test_c12_phase2.py::TestKnowledgeIndexPageLocatorEvidence`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_c12_phase2.py)
  - `test_l0189_real_recorded_failure_flagged`: Frozen sequence label `"191"` vs printed page `"5.45"` from Building Construction Illustrated is flagged with `check_page_locator`'s result (`flagged=True`, `reliable=False`, `detail` citing l0189).
  - `test_clean_input_stays_quiet`: Document where PDF labels match printed pages (`"17"`) has zero flagged mismatches.
  - `test_sibling_failure_flagged`: Sequence label `"42"` vs printed page `"3.10"` is flagged.

### Site 4: [`scripts/villa_daylight_finished.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_daylight_finished.py)
- **Change**: Added `verify_shared_model(render_scene_hash=None) -> dict` and invoked it at the start of `run()`. Uses `concept/villa_render.source_provenance()["source_hash"]` as the authoritative daylight model hash. Compares against the render scene hash from `VR.OUT / "scene.json"` or explicit argument. Refuses to run with `RuntimeError` if hashes disagree.
- **Invariants Preserved**: Does not invent a new hash scheme; uses `source_provenance` exactly as defined. If no render scene hash is available, reports that to stderr and does not fake one. Existing signature `run(host=DEFAULT_HOST)` retains full backwards compatibility.
- **Tests**: [`tests/test_c12_phase2.py::TestVillaDaylightSharedModelEvidence`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_c12_phase2.py)
  - `test_l0661_real_recorded_failure_refuses_to_run`: Divergent render hash raises `RuntimeError` citing l0661 ("Render and analysis model hashes disagree: they must describe one building (l0661)").
  - `test_clean_input_stays_quiet`: Matching hash returns clean verification dictionary and permits run.
  - `test_sibling_failure_refuses_to_run`: Another divergent hash fails closed.
  - `test_missing_render_hash_reported_not_faked`: Verifies missing hash is reported without faking.

---

## Non-Migrated Sites and Scope Boundaries

The following call sites from [`docs/evidence-status.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/evidence-status.md) were explicitly excluded from Phase 2 Batch 1 per instruction:
1. `src/archpipe/guidance.py`: Owned by separate agent; changes public types.
2. `src/archpipe/rules.py`: Owned by separate agent; changes public types.
3. `src/archpipe/concept/villa_lighting.py`: Owned by separate agent; deferred to lighting batch.
4. `src/archpipe/concept/villa_render.py`: Owned by separate agent; deferred to render batch.
5. `src/archpipe/guard_registry.py`: Owned by separate agent.
6. `src/archpipe/asset_intake.py` line 133 (`_valid_size_override`): Part of client decision governance package, not Batch 1.

---

## Lessons to Register

The following defect lessons are now wired into production call sites and ready for registration in `guard_registry.py` by the registry agent:

| Lesson ID | Lesson Title | Owning Call-Site Function | File |
|---|---|---|---|
| `l0179` | Model metadata disagrees with measured mesh geometry | `validate_entry` | [`src/archpipe/asset_intake.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/asset_intake.py) |
| `l0188` | Book filename edition claims disagree with copyright page | `intake` | [`src/archpipe/sources.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/sources.py) |
| ~~`l0189`~~ (rejected, not covered) | PDF sequence-number page labels disagree with printed numbers | `page_labels` | [`src/archpipe/knowledge_index.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/knowledge_index.py) |
| `l0661` | Daylight analysis and render describe different models | `run` / `verify_shared_model` | [`scripts/villa_daylight_finished.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_daylight_finished.py) |
