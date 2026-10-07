---
Document Outline:
  - [Executive Summary](#executive-summary)
  - [Phase 2 Batch 1 Registration Overview](#phase-2-batch-1-registration-overview)
  - [Lesson-by-Lesson Guard Registration Details](#lesson-by-lesson-guard-registration-details)
    - [Subsystem 1: Safe IO and Serialization](#subsystem-1-safe-io-and-serialization)
    - [Subsystem 2: Render QA](#subsystem-2-render-qa)
  - [Uncovered Lessons and Justifications](#uncovered-lessons-and-justifications)
  - [Coverage Audit Metrics](#coverage-audit-metrics)
  - [Changed Files List](#changed-files-list)
  - [Verification and Next Steps](#verification-and-next-steps)
  - [Fix Round 1](#fix-round-1)
Executive Summary:
  This report documents Phase 2 Batch 1 of the defect guard registry migration covering the Safe I/O & serialization and Render QA subsystems, as well as Fix Round 1 resolving test suite failures across four Safe I/O guards. Registered clean case expectations were updated to match the actual typed records produced by safe_io.encode, and temporary file staging was introduced for guards reading UTF-16 byte streams from disk. All 11 guard registry tests pass with zero failures.
---

# Phase 2 Batch 1 Guard Registration Report

## Executive Summary

This report documents Phase 2 Batch 1 of the defect guard registry migration covering the Safe I/O & serialization and Render QA subsystems. Fourteen guards have been registered across fifteen audited lessons, with seven Safe I/O guards proven on frozen historical failure cases and seven Render QA guards tracked under `needs_real_case` awaiting physical pixel renders. Exactly one lesson ([`l0101`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/lessons-audit.md)) remains uncovered due to the absence of automated retry-promotion logic in current code, bringing total uncovered lessons down from 182 to 169.

---

## Phase 2 Batch 1 Registration Overview

Per [`docs/guard-registry.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/guard-registry.md) Section 8 (Step 1), Phase 2 migration registers defect guards for two prioritized subsystems:
1. **Safe I/O & Serialization**: Eight lessons ([`l0019`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/lessons-audit.md), [`l0024`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/lessons-audit.md), [`l0067`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/lessons-audit.md), [`l0101`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/lessons-audit.md), [`l0117`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/lessons-audit.md), [`l0131`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/lessons-audit.md), [`l0272`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/lessons-audit.md), [`l0466`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/lessons-audit.md)).
2. **Render QA**: Seven lessons ([`l0061`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/lessons-audit.md), [`l0078`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/lessons-audit.md), [`l0079`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/lessons-audit.md), [`l0081`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/lessons-audit.md), [`l0082`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/lessons-audit.md), [`l0100`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/lessons-audit.md), [`l0136`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/lessons-audit.md)).

In accordance with project integrity standards:
- All Safe I/O guards use frozen real failure inputs recovered by value from [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/LEARNINGS.md), [`tests/test_safe_io.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_safe_io.py), [`tests/test_jsonsafe.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_jsonsafe.py), and [`scripts/verify.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/verify.py).
- No synthetic image fixtures were fabricated for Render QA checks; all image-based guards awaiting real historical rendering assets are registered with `needs_real_case=True`.
- No new production logic was authored for lessons without an existing guard in code ([`l0101`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/lessons-audit.md)); [`l0101`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/lessons-audit.md) is faithfully tracked as uncovered.

---

## Lesson-by-Lesson Guard Registration Details

### Subsystem 1: Safe IO and Serialization

| Lesson ID | Guard Name | Guard Function | Real Failing Case & Source | Clean Quiet Case | needs_real_case | Status / Notes |
|---|---|---|---|---|---|---|
| `l0019` | `safe_io_color_channels` | [`safe_io.encode`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/safe_io.py#L48) | `safe_io.Color(256, 180, 0)`: out-of-range byte channel (256 > 255). Frozen by value from [`tests/test_safe_io.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_safe_io.py#L84) boundary test. | `safe_io.Color(0, 180, 255)`: valid byte channels. Frozen from [`tests/test_safe_io.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_safe_io.py#L20). | `False` | Real raises `ValueError`. Clean produces `{"type": "Color", "value": [{"type": "int", "value": 0}, {"type": "int", "value": 180}, {"type": "int", "value": 255}]}`. |
| `l0024` | `safe_io_textnote_normalization` | [`safe_io.encode`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/safe_io.py#L63) | `safe_io.Text("Review\rRegistered \u00ae\r\n\n", "Review\rRegistered \u00ae\r\n\n")`: un-normalized raw TextNote string with CR and trailing newlines. Frozen by value from [`tests/test_safe_io.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_safe_io.py#L53). | `safe_io.normalized_text("Review\rRegistered \u00ae\r\n\n")`: normalized TextNote record. | `False` | Real raises `ValueError`. Clean produces `{"type": "Text", "value": [{"type": "str", "value": "Review\rRegistered \u00ae\r\n\n"}, {"type": "str", "value": "Review\nRegistered \u00ae"}]}`. |
| `l0067` | `safe_io_falsy_zero_lint` | [`check_falsy_zero_lint`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/guard_registry.py) | `'energy = P * float(fx.get("output") or 1.0)'`: exact historical code line swallowing explicit zero. Frozen by value from [`scripts/verify.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/verify.py#L697) and [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/LEARNINGS.md#L210). | `'energy = P * (float(fx["output"]) if fx.get("output") is not None else 1.0)'`: explicit None check preserving zero. | `False` | Real raises `ValueError`. Clean returns `None`. |
| `l0101` | *None* | *None* | *No guard yet in code* (retry promotion convention pending implementation). | *N/A* | `N/A` | Left uncovered. Documented in [Uncovered Lessons](#uncovered-lessons-and-justifications). |
| `l0117` | `safe_io_utf16_bom_decode` | [`check_utf16_or_utf8_json`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/guard_registry.py) / [`safe_io.load_json`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/safe_io.py#L197) | `b""`: IronPython reading UTF-16 stream as empty bytes `''`, failing json decode. Frozen by value from [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/LEARNINGS.md#L261). | `b'\xff\xfe{\x00"\x00n\x00a\x00m\x00e\x00"\x00:\x00"\x00\xae\x00"\x00}\x00'`: UTF-16 LE with BOM containing registered sign `\u00ae`. Frozen from [`tests/test_safe_io.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_safe_io.py#L124). | `False` | Real raises `json.JSONDecodeError` / `ValueError`. Clean produces `{"name": "\u00ae"}` via temporary file staged in case setup. |
| `l0131` | `safe_io_raw_copy_lint` | [`check_raw_copy_lint`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/guard_registry.py) | `"shutil.copyfile(folder/'render.png',out/'bedroom.png')"`: exact historical raw copy line causing Windows file lock (`OSError 22`). Frozen from [`scripts/verify.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/verify.py#L752) and [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/LEARNINGS.md#L275). | `"copy_file(folder/'render.png', out/'bedroom.png')"`: atomic replacement via safe_io. | `False` | Real raises `ValueError`. Clean returns `None`. |
| `l0272` | `safe_io_measured_readback_agreement` | [`safe_io.assert_measured_readback`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/safe_io.py#L127) | `{"width": 1200}, {"width": 1000}, {"width": "model"}`: authored width 1200 echoed over measured stock width 1000. Frozen from [`tests/test_safe_io.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_safe_io.py#L130) and [`scripts/verify.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/verify.py#L737). | `{"width": 1000}, {"width": 1000}, {"width": "model"}`: measured read-back agreeing with model source. | `False` | Real raises `ValueError`. Clean returns `None`. |
| `l0466` | `safe_io_element_id_exact_integer` | [`check_element_id_exact_integer`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/guard_registry.py) / [`safe_io.encode`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/safe_io.py#L54) | `1.25`: float degradation of .NET Int64 integer bridge. Frozen by value from [`tests/test_jsonsafe.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_jsonsafe.py#L56). | `9223372036854775807`: exact Int64 boundary value. Frozen from [`tests/test_jsonsafe.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_jsonsafe.py#L27) and [`scripts/verify.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/verify.py#L730). | `False` | Real raises `ValueError`. Clean produces `{"type": "ElementId", "value": [{"type": "int", "value": 9223372036854775807}]}`. |

---

### Subsystem 2: Render QA

All Render QA checks inspect rendered pixel data or scene QA payloads. Per [`docs/guard-registry.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/guard-registry.md) Section 2 and [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/LEARNINGS.md) (rule: "prove every guard on a real reproduction; synthetic cases prove the logic, not the calibration"), guards awaiting frozen physical pixel assets are registered with `needs_real_case=True`:

| Lesson ID | Guard Name | Guard Function | Real Failing Case Missing | Clean Case | needs_real_case | Status / Notes |
|---|---|---|---|---|---|---|
| `l0061` | `render_qa_window_view_detail` | [`render_qa.check`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/render_qa.py#L86) | Frozen pixel render of void sky gradient (measured detail `0.0026`). | *None* | `True` | Pre-registered in Phase 1; retained with `needs_real_case=True`. |
| `l0078` | `render_qa_threshold_calibration` | [`render_qa.check`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/render_qa.py#L86) | Frozen renders for the three historical calibration defects: void window detail (`0.0026` vs `0.0365`), warm colour cast (`0.052-0.070` vs `0.06`), and highlight floor. | *None* | `True` | Calibrates thresholds against real measured render data rather than synthetic tests ([`l0078`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/lessons-audit.md)). |
| `l0079` | `render_qa_cool_lamplit_cast` | [`render_qa.check`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/render_qa.py#L86) | Frozen pixel render of cool lamp-lit night view (measured `0.036` cool cast). | *None* | `True` | Direction-aware colour cast guard failing cool cast above 0.02 on lamp-lit night views ([`l0079`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/lessons-audit.md)). |
| `l0081` | `render_qa_highlight_clipping` | [`render_qa.check`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/render_qa.py#L86) | Frozen pixel render of view clipping 4.1% under highlight-priority metering. | *None* | `True` | Fails closed when highlight clipping exceeds 3% under highlight-priority metering ([`l0081`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/lessons-audit.md)). |
| `l0082` | `render_qa_exposure_midtones` | [`render_qa.check`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/render_qa.py#L86) | Frozen pixel render of underexposed view (measured `0.18` and `0.23` median luminance). | *None* | `True` | Enforces midtone floor of at least 0.30 median luminance to prevent gloomy underexposure ([`l0082`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/lessons-audit.md)). |
| `l0100` | `render_qa_view_subject_framing` | [`render_qa.check`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/render_qa.py#L86) | Frozen scene render where pendant LT-03 sat at screen height `2.59` outside `[0, 1]` frame. | *None* | `True` | Fails closed when declared view subject is out of frame in rendered camera view ([`l0100`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/lessons-audit.md)). |
| `l0136` | `render_qa_overcast_highlights` | [`render_qa.check`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/render_qa.py#L86) | Frozen pixel render of soft overcast scene reaching `0.86` without direct light sources. | *None* | `True` | Treats highlight floor as advisory WARN on soft overcast scenes lacking direct light sources ([`l0136`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/lessons-audit.md)). |

---

## Uncovered Lessons and Justifications

### `l0101` (`l0101-look-retry-overwrote`)
- **Audit Row**: Current enforcement: `NONE`. Proposed control: `Revit read-back: round-trip bridge types and interrupted writes`.
- **Learnings Entry**: "A look retry overwrote the first render; when the retry also failed, the files on disk disagreed with the report and the exposure lock. Retries render under -retry and are promoted only if they pass; the records are renamed with them." ([`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/LEARNINGS.md#L245)).
- **Codebase Status**: In [`docs/serialization-boundary.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/serialization-boundary.md#L84), retry promotion lifecycle controls are explicitly acknowledged as pending Phase 2 implementation. No automated pipeline guard currently enforces `-retry` naming promotion in [`src/archpipe/safe_io.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/safe_io.py), [`src/archpipe/stage_result.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/stage_result.py), or [`scripts/`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts).
- **Disposition**: In accordance with the prompt instruction ("Find the EXISTING guard in the code that prevents or catches it (do not write new production logic unless no guard exists; if none exists, record the lesson as 'no guard yet' in the report and do NOT fake one)"), [`l0101`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/lessons-audit.md) is registered as **no guard yet** and left uncovered.

---

## Coverage Audit Metrics

Audit evaluation against [`docs/lessons-audit.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/lessons-audit.md) using [`audit_lesson_coverage`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/guard_registry.py#L509):

| Metric | Before Batch 1 | After Batch 1 | Net Change |
|---|---|---|---|
| **Total Lessons Tracked** | 217 | 217 | 0 |
| **Covered by Guard** | 13 | **20** | +7 (`l0019`, `l0024`, `l0067`, `l0117`, `l0131`, `l0272`, `l0466`) |
| **Covered by Review Step** | 21 | **21** | 0 |
| **Needs Real Case** | 1 | **7** | +6 (`l0078`, `l0079`, `l0081`, `l0082`, `l0100`, `l0136`) |
| **Uncovered Lessons** | 182 | **169** | -13 (-7 guard, -6 needs real case) |
| **Coverage Percentage** | 15.7% | **18.9%** | +3.2% (excluding needs_real_case) |

The new uncovered count reported by [`report_uncovered_lessons`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/guard_registry.py#L617) is **169**.

---

## Changed Files List

Only the following files were modified or created in this batch:

1. [`src/archpipe/guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/guard_registry.py): Added imports (`json`, `render_qa`, `safe_io`), helper check functions (`check_falsy_zero_lint`, `check_utf16_or_utf8_json`, `check_raw_copy_lint`, `check_element_id_exact_integer`), exported helpers in `__all__`, registered 7 Safe I/O guards with frozen historical defect cases, and registered 6 new Render QA guards with `needs_real_case=True`.
2. [`tests/test_guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_guard_registry.py): Extended coverage audit assertions to assert 20 covered by guard, 7 needs real case, and 169 uncovered; added batch 1 expected guard lessons and needs real case lessons; added `test_phase2_batch1_guards_execution` asserting all new guards fire on real case and stay quiet on clean case.
3. [`docs/reg1-report.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/reg1-report.md): Authored this report detailing lesson mappings, guard functions, real and clean fixtures, and coverage metrics.

---

## Verification and Next Steps

1. **Test Verification**:
   - Every registered guard with `needs_real_case=False` (`safe_io_color_channels`, `safe_io_textnote_normalization`, `safe_io_falsy_zero_lint`, `safe_io_utf16_bom_decode`, `safe_io_raw_copy_lint`, `safe_io_measured_readback_agreement`, `safe_io_element_id_exact_integer`) runs on its real failing case (fires) and clean case (quiet).
   - Every Render QA guard tracked under `needs_real_case=True` verifies that `run_case("real")` fails closed with `"needs real case"`.
   - All static lints in [`scripts/verify.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/verify.py) (falsy-zero lint, raw-copy lint, invented-dimension lint) remain quiet.
2. **Next Steps (Phase 2, Step 2)**:
   - Extract and freeze real historical pixel renders for `l0061`, `l0078`, `l0079`, `l0081`, `l0082`, `l0100`, and `l0136` into `tests/data/frozen_defects/`.
   - Update registrations to bind `real_case` and remove `needs_real_case=True`.
   - Implement automated retry-promotion lifecycle guard for [`l0101`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/lessons-audit.md).

---

## Fix Round 1

Fix Round 1 addresses the 6 test failures reported in `docs/reg1-lead-test-failures.log` from running `tests.test_guard_registry` (11 tests, 6 failures).

### Detailed Defect Diagnosis and Fixes

1. **`safe_io_color_channels` (`l0019`)**:
   - **Diagnosis**: The lead test reported `Key 'type': expected 'color', got 'Color'`. Inspection of [`safe_io.encode`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/safe_io.py#L48) reveals that typed record values preserve the PascalCase record name (`type(value).__name__ == "Color"`), and inner tuple values are recursively encoded as typed records (`{"type": "int", "value": ...}`). The registered clean expectation mistakenly anticipated a lowercase type `"color"` and un-tagged integers `[0, 180, 255]`.
   - **Resolution**: Corrected `expected_clean` in [`src/archpipe/guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/guard_registry.py) to `{"type": "Color", "value": [{"type": "int", "value": 0}, {"type": "int", "value": 180}, {"type": "int", "value": 255}]}`. The real failing case (`Color(256, 180, 0)`) continues to raise `ValueError("invalid byte channel")`.

2. **`safe_io_textnote_normalization` (`l0024`)**:
   - **Diagnosis**: The lead test reported `Key 'type': expected 'text', got 'Text'`. Inspection of [`safe_io.encode`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/safe_io.py#L48) and `safe_io.normalized_text` shows that `Text` namedtuples are serialized with `type: "Text"` and a two-element value tuple `[encode(original), encode(normalized)]`, where each string is tagged as `{"type": "str", "value": ...}`. The registered expectation mistakenly had `"type": "text"` and a flat dictionary schema.
   - **Resolution**: Corrected `expected_clean` in [`src/archpipe/guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/guard_registry.py) to `{"type": "Text", "value": [{"type": "str", "value": "Review\rRegistered \u00ae\r\n\n"}, {"type": "str", "value": "Review\nRegistered \u00ae"}]}`. The real failing case (`Text` where normalization disagrees with original) continues to raise `ValueError("text normalization disagrees with original")`.

3. **`safe_io_element_id_exact_integer` (`l0466`)**:
   - **Diagnosis**: The lead test reported `Key 'type': expected 'element_id', got 'ElementId'`. Inspection of [`check_element_id_exact_integer`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/guard_registry.py) and [`safe_io.encode`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/safe_io.py#L48) indicates that `ElementId` namedtuples are encoded with `type: "ElementId"` and `value: [encode(v)]` (`[{"type": "int", "value": 9223372036854775807}]`). The registered expectation had specified lowercase `"type": "element_id"` and a bare integer value.
   - **Resolution**: Corrected `expected_clean` in [`src/archpipe/guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/guard_registry.py) to `{"type": "ElementId", "value": [{"type": "int", "value": 9223372036854775807}]}`. The real failing case (`1.25` float) continues to raise `ValueError("identifier must be an exact integer")`.

4. **`safe_io_utf16_bom_decode` (`l0117`)**:
   - **Diagnosis**: The lead test reported on real case: `FileNotFoundError: No such file or directory: "b''"`, and on clean case: `OSError: [Errno 22] Invalid argument: 'b\'\xff\xfe{...'`. Inspection reveals that [`safe_io.load_json`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/safe_io.py#L197) expects a file path parameter and opens the file via `open(str(path), "rb")`. Passing raw bytes (`b""` or `b'\xff\xfe...'`) resulted in `open()` treating the byte repr as a file path string.
   - **Resolution**: Updated `RegisteredGuard.run_case` in [`src/archpipe/guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/guard_registry.py) to perform case setup for file-reading guards: if the case fixture provides raw bytes to a guard function expecting a file path, the runner stages the bytes into a temporary file (`Path(tempfile.gettempdir()) / ...`), supplies the temporary file path to the guard, and deterministically unlinks the file in a `finally` block. A matching safety fallback was also added to [`check_utf16_or_utf8_json`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/guard_registry.py). On the real case (`b""`), `safe_io.load_json` reads the empty file, attempts `utf-8-sig` decode, and raises `json.JSONDecodeError` / `ValueError` (historical bug reproduction verified). On the clean case (`b'\xff\xfe...'`), `safe_io.load_json` detects the UTF-16 BOM and returns `{"name": "\u00ae"}` (clean case quiet verified).

### Files Changed in Fix Round 1

Only the following files were actually changed in Fix Round 1:
- [`src/archpipe/guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/guard_registry.py)
- [`docs/reg1-report.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/reg1-report.md)
