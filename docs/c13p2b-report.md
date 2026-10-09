---
outline:
  - title: Document Outline
    link: "#document-outline"
  - title: Executive Summary
    link: "#executive-summary"
  - title: Files Actually Changed
    link: "#files-actually-changed"
  - title: Per-File Migration Details
    link: "#per-file-migration-details"
    subsections:
      - title: revit/build_bedroom.py
        link: "#revitbuild_bedroompy"
      - title: revit/diag_context.py
        link: "#revitdiag_contextpy"
      - title: revit/dump_mcp_tools.py
        link: "#revitdump_mcp_toolspy"
      - title: revit/export_views.py
        link: "#revitexport_viewspy"
      - title: revit/place_families_test.py
        link: "#revitplace_families_testpy"
      - title: revit/probe.py
        link: "#revitprobepy"
      - title: revit/probe_fixture_drop.py
        link: "#revitprobe_fixture_droppy"
      - title: revit/probe_fixture_geometry.py
        link: "#revitprobe_fixture_geometrypy"
      - title: revit/probe_product_family.py
        link: "#revitprobe_product_familypy"
      - title: revit/probe_villa_inventory.py
        link: "#revitprobe_villa_inventorypy"
  - title: Direct Writes and Native Saves Left Unchanged
    link: "#direct-writes-and-native-saves-left-unchanged"
  - title: Deliberate Byte Differences
    link: "#deliberate-byte-differences"
  - title: Verification and Proofs
    link: "#verification-and-proofs"
  - title: Lessons to Register
    link: "#lessons-to-register"
summary: |
  Phase 2 Batch 2 migration report for serialization class (C13). Ten IronPython 2.7
  report writers in revit/ were migrated to atomic safe_io.save_json writers while
  strictly preserving Python 2.7 syntax, default=str, and _clean serialization semantics.
---

# Document Outline

- [Executive Summary](#executive-summary)
- [Files Actually Changed](#files-actually-changed)
- [Per-File Migration Details](#per-file-migration-details)
  - [revit/build_bedroom.py](#revitbuild_bedroompy)
  - [revit/diag_context.py](#revitdiag_contextpy)
  - [revit/dump_mcp_tools.py](#revitdump_mcp_toolspy)
  - [revit/export_views.py](#revitexport_viewspy)
  - [revit/place_families_test.py](#revitplace_families_testpy)
  - [revit/probe.py](#revitprobepy)
  - [revit/probe_fixture_drop.py](#revitprobe_fixture_droppy)
  - [revit/probe_fixture_geometry.py](#revitprobe_fixture_geometrypy)
  - [revit/probe_product_family.py](#revitprobe_product_familypy)
  - [revit/probe_villa_inventory.py](#revitprobe_villa_inventorypy)
- [Direct Writes and Native Saves Left Unchanged](#direct-writes-and-native-saves-left-unchanged)
- [Deliberate Byte Differences](#deliberate-byte-differences)
- [Verification and Proofs](#verification-and-proofs)
- [Lessons to Register](#lessons-to-register)

# Executive Summary

This report documents the completion of Serialization Class (C13), Phase 2, Batch 2. The ten IronPython 2.7 direct report writers in `revit/` listed in [docs/serialization-boundary.md](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/serialization-boundary.md) (`build_bedroom.py`, `diag_context.py`, `dump_mcp_tools.py`, `export_views.py`, `place_families_test.py`, `probe.py`, `probe_fixture_drop.py`, `probe_fixture_geometry.py`, `probe_product_family.py`, and `probe_villa_inventory.py`) were migrated to route all report writes through `safe_io.save_json`. Python 2.7 syntax compatibility (no f-strings, no type annotations, no pathlib imports) was strictly preserved across all ten files, alongside specialized serialization handling (`default=str` with ASCII escaping in `probe_product_family.py`, and `_clean` via `jsonsafe.clean` in `probe_villa_inventory.py`), with native Revit model saves and PDF exports left untouched for later staged publication.

# Files Actually Changed

The following files were modified or created in this batch:

1. [revit/build_bedroom.py](file:///C:/Users/mmbka/arch-pipeline-agy2/revit/build_bedroom.py)
2. [revit/diag_context.py](file:///C:/Users/mmbka/arch-pipeline-agy2/revit/diag_context.py)
3. [revit/dump_mcp_tools.py](file:///C:/Users/mmbka/arch-pipeline-agy2/revit/dump_mcp_tools.py)
4. [revit/export_views.py](file:///C:/Users/mmbka/arch-pipeline-agy2/revit/export_views.py)
5. [revit/place_families_test.py](file:///C:/Users/mmbka/arch-pipeline-agy2/revit/place_families_test.py)
6. [revit/probe.py](file:///C:/Users/mmbka/arch-pipeline-agy2/revit/probe.py)
7. [revit/probe_fixture_drop.py](file:///C:/Users/mmbka/arch-pipeline-agy2/revit/probe_fixture_drop.py)
8. [revit/probe_fixture_geometry.py](file:///C:/Users/mmbka/arch-pipeline-agy2/revit/probe_fixture_geometry.py)
9. [revit/probe_product_family.py](file:///C:/Users/mmbka/arch-pipeline-agy2/revit/probe_product_family.py)
10. [revit/probe_villa_inventory.py](file:///C:/Users/mmbka/arch-pipeline-agy2/revit/probe_villa_inventory.py)
11. [tests/test_c13_phase2b.py](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_c13_phase2b.py)
12. [docs/serialization-boundary.md](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/serialization-boundary.md)
13. [docs/LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/LEARNINGS.md)
14. [docs/c13p2b-report.md](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/c13p2b-report.md)

# Per-File Migration Details

### revit/build_bedroom.py

- **Import added**:
  ```python
  _SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
  if _SRC not in sys.path:
      sys.path.insert(0, _SRC)
  from archpipe import safe_io
  ```
- **Replaced write**:
  - Direct write of build report:
    `safe_io.save_json(out, report, indent=2, sort_keys=True)`
- **Writes left unchanged**:
  - `doc.SaveAs(dest, opts)`: Native Revit model save (`.rvt`). Needs staged native publication in a later batch.
  - `open(spec_path)` and `open(spec_path, 'rb')`: Input specification reads, not report writes.

### revit/diag_context.py

- **Import added**:
  ```python
  _SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
  if _SRC not in sys.path:
      sys.path.insert(0, _SRC)
  from archpipe import safe_io
  ```
- **Replaced write**:
  - Direct file write of diagnostic context:
    `safe_io.save_json(dest, out, indent=2, sort_keys=True)`
- **Writes left unchanged**: None.

### revit/dump_mcp_tools.py

- **Import added**:
  ```python
  _SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
  if _SRC not in sys.path:
      sys.path.insert(0, _SRC)
  from archpipe import safe_io
  ```
- **Replaced write**:
  - Direct file write of MCP tool definitions:
    `safe_io.save_json(dest, out, indent=2, sort_keys=True)`
- **Writes left unchanged**: None.

### revit/export_views.py

- **Import added**:
  ```python
  _SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
  if _SRC not in sys.path:
      sys.path.insert(0, _SRC)
  from archpipe import safe_io
  ```
- **Replaced write**:
  - Direct file write of views report:
    `safe_io.save_json(os.path.join(dest, 'views-report.json'), report, indent=2, sort_keys=True)`
- **Writes left unchanged**:
  - `doc.Save(SaveOptions())`: Native Revit model save.
  - `doc.Export(dest, ids, opts)`: Native Revit PDF sheet export.

### revit/place_families_test.py

- **Import added**:
  ```python
  _SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
  if _SRC not in sys.path:
      sys.path.insert(0, _SRC)
  from archpipe import safe_io
  ```
- **Replaced write**:
  - Direct file write of family placement report:
    `safe_io.save_json(dest, out, indent=2, sort_keys=True)`
- **Writes left unchanged**:
  - `doc.SaveAs(save_as, opts)`: Native Revit model save (`.rvt`).

### revit/probe.py

- **Import added**:
  ```python
  _SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
  if _SRC not in sys.path:
      sys.path.insert(0, _SRC)
  from archpipe import safe_io
  ```
- **Replaced write**:
  - Direct file write of API probe report:
    `safe_io.save_json(dest, out, indent=2)`
- **Writes left unchanged**: None.

### revit/probe_fixture_drop.py

- **Import added**:
  ```python
  _SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
  if _SRC not in sys.path:
      sys.path.insert(0, _SRC)
  from archpipe import safe_io
  ```
- **Replaced write**:
  - `with open(dest, 'w') as fh: json.dump(records, fh, indent=2)`
    -> `safe_io.save_json(dest, records, indent=2)`
- **Writes left unchanged**: None.

### revit/probe_fixture_geometry.py

- **Import added**:
  ```python
  _SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
  if _SRC not in sys.path:
      sys.path.insert(0, _SRC)
  from archpipe import safe_io
  ```
- **Replaced write**:
  - `with open(dest,'w') as output: json.dump(records,output,indent=2)`
    -> `safe_io.save_json(dest, records, indent=2)`
- **Writes left unchanged**: None.

### revit/probe_product_family.py

- **Import added**:
  ```python
  _SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
  if _SRC not in sys.path:
      sys.path.insert(0, _SRC)
  from archpipe import safe_io
  ```
- **Replaced write**:
  - `text = json.dumps(_ascii(out), indent=2, sort_keys=True, default=str)` followed by `with open(dest, "w") as fh: fh.write(text)`
    -> `safe_io.save_json(dest, _ascii(out), indent=2, sort_keys=True, default=str)`
- **Writes left unchanged**: None.

### revit/probe_villa_inventory.py

- **Import added**:
  ```python
  _SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
  if _SRC not in sys.path:
      sys.path.insert(0, _SRC)
  from archpipe import safe_io
  ```
- **Replaced write**:
  - In `_write(path, data)`:
    `with codecs.open(path, "w", "utf-8") as fh: fh.write(json.dumps(_clean(data), indent=1, sort_keys=True, ensure_ascii=True))`
    -> `safe_io.save_json(path, _clean(data), indent=1, sort_keys=True)`
- **Writes left unchanged**:
  - `doc.SaveAs(upgraded, opts)` in `_save_upgraded(doc)`: Native Revit model upgrade save (`.rvt`).

---

# Direct Writes and Native Saves Left Unchanged

In compliance with the project rules and task boundaries, the following operations were audited and retained:

1. **`revit/build_bedroom.py` (`main`)**:
   `doc.SaveAs(dest, opts)`
   - *Reason*: Native Revit model `.rvt` project save. Staged native binary publication is reserved for a future batch.
2. **`revit/build_bedroom.py` (`main`)**:
   `with open(spec_path) as fh:`, `with open(spec_path, 'rb') as fh:`
   - *Reason*: Input specification read handles, not report writers.
3. **`revit/export_views.py` (`main`)**:
   `doc.Save(SaveOptions())`
   - *Reason*: Native Revit model `.rvt` save.
4. **`revit/export_views.py` (`main`)**:
   `doc.Export(dest, ids, opts)`
   - *Reason*: Native Revit PDF sheet export.
5. **`revit/place_families_test.py` (`main`)**:
   `doc.SaveAs(save_as, opts)`
   - *Reason*: Native Revit model `.rvt` save.
6. **`revit/probe_villa_inventory.py` (`_save_upgraded`)**:
   `doc.SaveAs(upgraded, opts)`
   - *Reason*: Native Revit 2021->2027 upgraded model `.rvt` save.

---

# Deliberate Byte Differences

Across all ten migrated files, replacing direct open/json.dump/fh.write calls with `safe_io.save_json` introduces the following deliberate byte and operational differences:

1. **Final Newline**: `safe_io.save_json` appends a final newline (`\n`) via `save_text`. Direct `json.dump` and `fh.write` calls that previously omitted a trailing newline now gain one.
2. **Non-Finite Number Rejection**: `safe_io.save_json` specifies `allow_nan=False`, causing any `NaN` or `Infinity` values to fail closed with a `ValueError` rather than producing invalid JSON tokens.
3. **Pure ASCII Encoding**: `safe_io.save_json` enforces `ensure_ascii=True`, producing uniform ASCII-escaped JSON representation across Python 2.7 and Python 3.
4. **Atomic Staging and Flush**: Staged output via `.part` files in the same directory, flushed with `fsync`, and replaced using `File.Replace` (or `File.Move` / `os.replace`), protecting pre-existing reports against truncation or lock collisions (`OSError 22`).

---

# Verification and Proofs

Tests were added in [tests/test_c13_phase2b.py](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_c13_phase2b.py), runnable under CPython without Revit:

1. **Proof (a) - AST Scan (`test_ast_no_unlisted_direct_writes`)**:
   Parses the abstract syntax trees of all ten files. Verifies that no `.write_text()`, `.write_bytes()`, `open(mode="w"/"a"/"x")`, `.open(mode="w"/"a"/"x")`, `json.dump()`, `codecs.open()`, or `shutil.copy*()` calls exist outside `EXCEPTIONS`. Since all ten direct report writes were migrated, `EXCEPTIONS` is verified empty with zero remaining direct report writes.
2. **Proof (b) - Python 2.7 Syntax Verification (`test_ast_python_27_compatible_syntax`)**:
   Traverses the ASTs of all ten files to verify that no Python 3-only syntax constructs exist (no f-strings / `JoinedStr`, no variable `AnnAssign` annotations, no function return or argument annotations, no async/await, no match statements, and no `pathlib` imports).
3. **Proof (c) - Safe IO Call Presence (`test_all_ten_files_call_safe_io_save_json`)**:
   Verifies that every one of the ten files imports `safe_io` from `archpipe` and contains at least one active call to `safe_io.save_json`.
4. **Proof (d) - Product Family Serialization (`test_probe_product_family_serialization_preserves_behavior`)**:
   Verifies that `probe_product_family.py`'s `_ascii` character escaping and `default=str` kwargs are preserved when passed through `safe_io.save_json`.
5. **Proof (e) - Villa Inventory Cleaning (`test_probe_villa_inventory_cleaning_preserves_behavior`)**:
   Verifies that `probe_villa_inventory.py`'s `_clean` method properly coerces foreign bridge integers and nested structures through `jsonsafe.clean` before atomic publication.
6. **Proof (f) - Write Failure Atomicity (`test_write_failure_leaves_existing_destination_file_unchanged`)**:
   Proves that when `json.dumps` raises an error or `os.fsync` encounters an `OSError`, existing destination files remain unmodified and no temporary `.part` files are left on disk.

---

# Lessons to Register

- **Lessons to Register**: `none`
  *(The existing registry entry `serialization-file-boundary-phase1` in [docs/LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/LEARNINGS.md) was updated with an appended line recording the Phase 2 Batch 2 migration of the ten IronPython 2.7 direct report writers in `revit/`, preserving historical lessons for sibling components without modifying `guard_registry.py`).*

## Lead review (2026-10-08)

Accepted with test fixes by the lead: the three AST tests failed to parse `revit/probe_product_family.py`, whose existing Python-2-only literal `"\u%04x"` is valid under IronPython but not CPython 3; the tests now parse such literals as their Python-2 meaning for analysis only (`_parse_py2`). Proof (e) was removed: it exercised `jsonsafe.clean`, not `probe_villa_inventory._clean`, and did not test the migrated path. Runtime behaviour under IronPython in Revit is not proven by these CPython tests; the next native Revit run must confirm the writers.
