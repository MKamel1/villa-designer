---
Document Outline:
  - [Document Outline](#document-outline)
  - [Executive Summary](#executive-summary)
  - [Incident Background and Defect Analysis](#incident-background-and-defect-analysis)
  - [Implementation Architecture](#implementation-architecture)
  - [Verification Proofs and Frozen Fixtures](#verification-proofs-and-frozen-fixtures)
  - [Operational Rules and Learnings Updates](#operational-rules-and-learnings-updates)
  - [Files Changed](#files-changed)
  - [Verification Instructions for the Lead](#verification-instructions-for-the-lead)
Executive Summary: >
  This report documents the implementation of the behaviour-preserving refactor audit tool developed following
  the 2026-10-07 incident where code was silently deleted during script preflight migration. The system provides
  pure-Python AST scope comparison, a CLI checking git diffs, guard registry integration, and value-frozen test proofs.
---

# Behaviour-Preserving Refactor Audit Report

## Incident Background and Defect Analysis

On 2026-10-07, during a task to migrate 16 scripts to the shared launch preflight (`project_context` in commit `13726cc`), an agent inadvertently deleted the line:
```python
rendered = json.loads(a.rendered.read_text(encoding="utf-8"))
```
from `scripts/compare_lux.py`. Although the prompt strictly mandated that no script's computations be altered, this deletion escaped initial review and was only caught by downstream pipeline integration tests (subsequently corrected in commit `a2ae9f8`).

A subsequent manual audit across all 16 migrated files by the lead compared assigned names per scope between the base and refactored revisions:
1. `scripts/compare_lux.py` lost the assigned name `rendered` and its corresponding `json.loads` call (a real defect).
2. `scripts/demo_bedroom_lighting.py` lost module-level `IES = ph.revit_ies_dir()` which was moved into `main()` as `ies = ph.revit_ies_dir()` (a harmless rename and move).

The manual audit demonstrated the need for an automated, fail-closed AST tool to verify that refactorings declared behaviour-preserving preserve all assigned names, call targets, and function scopes.

## Implementation Architecture

### 1. Pure Python Engine: [src/archpipe/refactor_audit.py](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/refactor_audit.py)

The core analysis function `audit_source(old_src: str, new_src: str, path: str = "", allowed: Any = None, removals_only: bool = False) -> list[Finding]` operates purely in Python without invoking git or shell commands:
- **Scope Extraction:** Traverses AST definitions to identify lexical scopes (`<module>`, functions, methods, and nested functions).
- **Assigned Names Comparison:** Extracts all `ast.Store` targets (including standard assignments, augmented assignments `AugAssign`, annotated assignments `AnnAssign`, walrus operators `NamedExpr`, and loop/context targets `For`, `With`).
- **Call Targets Comparison:** Extracts call targets via `ast.unparse(node.func)`. Calls on assignment right-hand sides are linked with their target variable to avoid double-reporting.
- **Top-Level Code Movement:** When module-level code moves into a new function scope (such as `main()`), it is reported as `moved` (`is_removal=False`) rather than an unallowed removal.
- **Pure Rename Detection:** If an old variable disappears but a new variable is assigned with an identical right-hand side expression (`ast.unparse(old_rhs) == ast.unparse(new_rhs)`), it is classified as `renamed` (`is_removal=False`).
- **Allowlist Mechanism:** Allows intentional removals declared via `{path: [names]}` or `{path: {name: reason}}`. Every intentional removal strictly requires a non-empty reason; entries without a justification fail closed by raising `ValueError`.
- **Syntax Error Handling:** Invalid Python syntax raises `SyntaxError`.

### 2. CLI Tool: [scripts/refactor_audit.py](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/refactor_audit.py)

A thin CLI script that integrates with git and project execution preflight:
- Preflight enforcement using `project_context(ROOT, Path(__file__).resolve(), "refactor-audit")`.
- Identifies modified Python files using `git diff --name-only <base> -- '*.py'`.
- Retrieves base versions using `git show <base>:<path>`.
- Fails closed with exit code 1 if any un-allowed removal is detected.
- Fails closed with exit code 2 if inputs are unreadable, allowlists are invalid, or preflight checks fail.
- Exits with 0 when all changes are verified behaviour-preserving or legitimately allowed.

### 3. Guard Registry Integration: [src/archpipe/guard_registry.py](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py)

Registered `refactor_silent_deletion` under Tier 2 controls:
- Adapter function `check_refactor_silent_deletion` calls `refactor_audit.audit_source` directly, satisfying the meta-guard requiring calls to production modules.
- Real case reproduces the `compare_lux.py` deletion and fires closed (`ValueError`).
- Clean case verifies the `demo_bedroom_lighting.py` harmless rename/move and stays quiet.

## Verification Proofs and Frozen Fixtures

Test suite [tests/test_refactor_audit.py](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_refactor_audit.py) freezes the real incident cases by value and tests sibling classes:
1. `test_real_defect_compare_lux_finds_dropped_assignment_and_call`: Verifies that dropping `rendered = json.loads(...)` from `compare_lux.py` produces exactly one finding naming `rendered` and `json.loads`.
2. `test_real_harmless_case_demo_bedroom_lighting_is_quiet`: Verifies that moving and renaming `IES = ph.revit_ies_dir()` into `main()` as `ies = ph.revit_ies_dir()` produces 0 removal findings.
3. `test_sibling_translated_defect_fires`: Validates a translated defect where `processed = parser.parse(...)` was deleted.
4. `test_sibling_translated_harmless_rename_stays_quiet`: Validates a translated rename `CONFIG_PATH` to `cfg`.
5. `test_sibling_deleted_call_without_assignment_fires`: Validates a dropped standalone call (`write_stage_result(...)`) without an assignment.
6. `test_allowed_removal_with_reason_stays_quiet`: Proves intentional removals declared with a reason in allowlist stay quiet.
7. `test_allowed_removal_without_reason_raises`: Proves allow declarations without reasons fail closed.
8. `test_unparsable_source_raises`: Confirms unparsable syntax raises `SyntaxError`.
9. `test_scope_disappeared_reported`: Confirms deleted function scopes are flagged as removals.

In addition, [tests/test_guard_registry.py](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_guard_registry.py) includes `test_refactor_silent_deletion_guard_execution` verifying real firing and clean quietness.

## Operational Rules and Learnings Updates

1. **Operating Rule Added:** [docs/ops/agent-dispatch.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/ops/agent-dispatch.md) updated with Section 5 ("Behaviour-Preserving Refactor Audit") requiring:
   > "after any refactor declared behaviour-preserving, run `scripts/refactor_audit.py --base <base>`; every removal must be allowed with a reason"
2. **Learnings Entry Added:** [docs/LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md) updated with entry `refactor-silent-deletion` documenting the 2026-10-07 incident, root cause, escape mechanism, control tiers, proofs, and guard registration.

## Files Changed

The following list contains only the files created or modified during this task:
1. `src/archpipe/refactor_audit.py` (created)
2. `scripts/refactor_audit.py` (created)
3. `tests/test_refactor_audit.py` (created)
4. `src/archpipe/guard_registry.py` (modified)
5. `tests/test_guard_registry.py` (modified)
6. `docs/ops/agent-dispatch.md` (modified)
7. `docs/LEARNINGS.md` (modified)
8. `docs/refaudit-report.md` (created)

## Verification Instructions for the Lead

Because tool execution constraints prohibit autonomous agents from running shell or git commands, the lead may execute the following commands in the active virtual environment:

1. **Run the refactor audit unit test suite:**
   ```powershell
   python -m unittest tests/test_refactor_audit.py
   ```
2. **Run guard registry tests (including meta-guard and refactor guard):**
   ```powershell
   python -m unittest tests/test_guard_registry.py
   ```
3. **Execute the refactor audit CLI against the base branch:**
   ```powershell
   python scripts/refactor_audit.py --base HEAD
   ```
4. **Run general repository verification:**
   ```powershell
   python scripts/verify.py
   ```
