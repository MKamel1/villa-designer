---
document_outline:
  - title: Executive Summary
    link: "#executive-summary"
  - title: Files Changed
    link: "#files-changed"
  - title: Call Site Migrations and Invariants
    link: "#call-site-migrations-and-invariants"
    subsections:
      - title: "Site 1: knowledge_index.py page_label_findings() and build()"
        link: "#site-1-knowledge_indexpy-page_label_findings-and-build"
      - title: "Site 2: guidance.py review_stage()"
        link: "#site-2-guidancepy-review_stage"
  - title: Caller Audit for review_stage
    link: "#caller-audit-for-review_stage"
  - title: Non-Migrated Sites and Scope Boundaries
    link: "#non-migrated-sites-and-scope-boundaries"
  - title: Lessons to Register
    link: "#lessons-to-register"
executive_summary: >
  This report documents Phase 2 Batch 2 of the C12 evidence-status migration.
  Two authoritative check call sites from docs/evidence-status.md were wired into
  src/archpipe/evidence.py: PDF sequence page label checking in knowledge_index.py (l0189)
  and model review scope enforcement in guidance.py (l0020).
  All existing signatures, return shapes, and SQLite database schemas were strictly preserved.
---

# Phase 2 Batch 2 Migration Report: Evidence Status Class (C12)

## Executive Summary
Phase 2 Batch 2 connects two authoritative call sites to the single authority of [`src/archpipe/evidence.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/evidence.py):
- `knowledge_index.py`: PDF sequence labels disagreeing with printed page numbers are detected using `check_page_locator` via a new sibling function `page_label_findings()` without storing state on function or document objects and without mutating the public return type of `page_labels()`. Disagreements are recorded in the index report dictionary in `build()` without altering the SQLite schema.
- `guidance.py`: Model review scope is routed through `EvidenceRecord.apply_to` so room-scoped model results cannot silently widen to dwelling scope (lesson l0020). Existing public signature and return shapes are preserved.

All existing public signatures, return types, and schemas were preserved.

---

## Files Changed

Only the following files were modified or created in this worktree:
1. [`src/archpipe/knowledge_index.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/knowledge_index.py)
2. [`src/archpipe/guidance.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/guidance.py)
3. [`tests/test_c12_phase2b.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_c12_phase2b.py)
4. [`docs/evidence-status.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/evidence-status.md)
5. [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/LEARNINGS.md)
6. [`docs/c12p2b-report.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/c12p2b-report.md)

---

## Call Site Migrations and Invariants

### Site 1: [`src/archpipe/knowledge_index.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/knowledge_index.py) `page_label_findings()` and `build()`
- **Context & Defect**: In lesson `l0189`, Building Construction Illustrated's PDF page labels were plain sequence numbers (`191` where the page prints `5.45`). Trusting PDF labels caused citation errors. A prior attempt in Batch 1 was rejected because it stored hidden state on `page_labels.flags` and `doc.page_label_flags` and re-implemented page-number detection.
- **Implementation**:
  - Maintained `page_labels(doc, texts)` return signature completely untouched (`tuple[list[str], str]`).
  - Added new sibling function `page_label_findings(doc, texts: list[str]) -> list[dict]`. It reuses the candidate page labels extracted by `page_labels()` and falls back to existing `_running_head()` and `_edge_numbers()` helpers from `knowledge_index.py`. It calls `archpipe.evidence.check_page_locator(pdf_label, printed)` for each page and returns all flagged mismatches.
  - Zero state is attached to the function object or document objects.
  - In `build()`, invoked `label_findings = page_label_findings(doc, texts)` for non-EPUB documents, and recorded `report[key]["label_findings"] = len(label_findings)`.
- **Schema Preservation Rationale**:
  - The SQLite database table `books` has a fixed DDL schema: `(id, title, edition, file, kind, pages, label_basis, sha256)`. Adding a column would mutate database schema.
  - Failing closed (raising an exception) during `build()` would completely block indexing of books like Building Construction Illustrated where sequence-number PDF labels exist but candidate agreement successfully resolves printed chapter-page numbers.
  - Therefore, recording `label_findings` count in the index build report dictionary (`report[key]["label_findings"]`) was selected: it preserves schema integrity, keeps indexing functional for disambiguated books, and records finding counts transparently.
- **Tests**: [`tests/test_c12_phase2b.py::TestKnowledgeIndexPageLabelFindings`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_c12_phase2b.py)
  - `test_l0189_real_recorded_failure_flagged`: Frozen sequence number `191` vs printed `5.45` from Building Construction Illustrated is flagged with `check_page_locator` result citing `l0189`, while `page_labels` returns `(labels, basis)` unchanged and stores no state on function or document objects.
  - `test_clean_input_stays_quiet`: Document where PDF labels match printed pages (`17`) returns 0 findings.
  - `test_sibling_failure_flagged`: Sibling sequence label `42` vs printed `3.10` is flagged.
  - `test_schema_preservation_and_record_findings`: Proves `books` SQLite schema is unmodified.

### Site 2: [`src/archpipe/guidance.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/guidance.py) `review_stage()`
- **Context & Defect**: In lesson `l0020`, an isolated room is not a dwelling. A pass in one room (e.g. bedroom layout) cannot be silently applied at dwelling scope. In `guidance.py` lines 320-327, `review_model` was called with `scope=project.get('scope', 'dwelling')` as a plain string, allowing room-scoped models to be evaluated at dwelling scope without enforcement.
- **Implementation**:
  - Derived `model_scope` from `model_record.get('scope') or model_data.get('scope') or ('room' if len(model_data.get('rooms', [])) <= 1 else 'dwelling')`.
  - Evaluated `result = review_model(model_data, scope=model_scope)`.
  - Constructed `EvidenceRecord(value=result, scope=result.get('scope', model_scope), status=EvidenceStatus.UNVERIFIED)`.
  - Routed target scope via `rec.apply_to(project.get('scope', 'dwelling'))`.
  - When a room-scoped model is evaluated under dwelling scope, `apply_to()` raises `ScopeWideningError` citing `l0020`.
  - When evaluated under matching room scope (or when dwelling evidence is narrowed to room), `apply_to()` succeeds quietly.
- **Invariants Preserved**:
  - Function signature `review_stage(stage, project_path, root)` is unchanged.
  - Return structure of `review_stage()` is identical.
  - Shape of diagnostic check `checks.append({'check': 'legacy_geometry', 'status': 'diagnostic', 'result': result})` is preserved.
- **Tests**: [`tests/test_c12_phase2b.py::TestGuidanceReviewStageScopeEvidence`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_c12_phase2b.py)
  - `test_l0020_real_recorded_failure_raises_scope_widening`: Real bedroom model extract ([`tests/fixtures/bedroom-from-revit.json`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/fixtures/bedroom-from-revit.json)) evaluated under `project['scope'] = 'dwelling'` fails closed with `ScopeWideningError` citing `l0020`.
  - `test_clean_room_scope_stays_quiet`: Real bedroom model extract evaluated under `project['scope'] = 'room'` succeeds quietly with diagnostic legacy geometry check intact.
  - `test_sibling_scope_widening_fails_closed`: Sibling explicit `scope: room:bedroom` applied to dwelling fails closed with `ScopeWideningError`.

---

## Caller Audit for `review_stage`

An audit of all callers of `review_stage` across the repository was conducted:
1. `tests/test_guidance.py::test_each_stage_has_usable_evidence_and_methods`:
   - Runs `review_stage(stage)` for stages 0-7 against [`knowledge/projects/villa-pilot.json`](file:///C:/Users/mmbka/arch-pipeline-agy2/knowledge/projects/villa-pilot.json).
   - In `villa-pilot.json`, `project.get('model')` is empty (`{}`).
   - Line 268 sets `model_fresh = False`, so the model review block (`if model_fresh:`) is skipped. Does not raise.
2. `tests/test_guidance.py::test_cached_presentation_rechecks_image_and_requirement_content`:
   - Sets `self.project['scope'] = 'room'` and sets `self.project['model']` to `bedroom-from-revit.json`.
   - Because `scope` is explicitly `'room'`, `rec.apply_to('room')` matches and succeeds cleanly. Does not raise.
3. Other calls in `test_guidance.py` (`test_cache_reuse_and_edition_invalidation`, `test_project_isolation`, etc.):
   - Target stages 0 or 1, skipping the model review block entirely.
4. Summary: No current caller in the repository test suite raises unexpectedly. Any future caller attempting to pass a room model under dwelling scope will now raise `ScopeWideningError` fail-closed as intended.

---

## Non-Migrated Sites and Scope Boundaries

The following call sites from [`docs/evidence-status.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/evidence-status.md) remain unmigrated or excluded per instructions:
1. `src/archpipe/rules.py` `Rule` dataclass: Changes public dataclass types.
2. `src/archpipe/guidance.py` `evidence_status()` and `numerical_target()`: Changes public dictionary shapes.
3. `src/archpipe/concept/*`: Reserved for concept generator migrations.
4. `src/archpipe/guard_registry.py`: Registry integration.

---

## Lessons to Register

| Lesson ID | Module / Call Site | Defect Behavior | Enforcement Mechanism |
|---|---|---|---|
| `l0189` | [`src/archpipe/knowledge_index.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/knowledge_index.py) `page_label_findings()` | PDF page labels were plain sequence numbers (`191` where page prints `5.45`), causing false citations | Sibling `page_label_findings()` flags sequence mismatches with `check_page_locator`, keeping `page_labels` return type unchanged and recording counts in `build()` report |
| `l0020` | [`src/archpipe/guidance.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/guidance.py) `review_stage()` | Room-scoped capability examples silently applied at dwelling scope, bypassing whole-dwelling checks | Model review scope is routed through `EvidenceRecord.apply_to()`, raising `ScopeWideningError` fail-closed on un-rescoped dwelling application |

## Lead review (2026-10-09)

- ACCEPTED: knowledge_index.page_label_findings (new sibling function; page_labels unchanged; reuses its candidate labels and edge numbers; the build report records a label_findings count). l0189 covered.
- REVERTED: the guidance.review_stage change. It invented a scope rule (one room = room scope, more = dwelling) with no source, changed the scope passed to review_model from the project's to the model's, and would raise for a single-room model under a dwelling project. Its tests were removed. l0020 stays covered by batch 9's evidence guard, not by this call site.
