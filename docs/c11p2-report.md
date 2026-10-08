---
outline:
  - title: Executive Summary
    link: "#executive-summary"
  - title: Changed Files Inventory
    link: "#changed-files-inventory"
  - title: Call-Site Migration Details
    link: "#call-site-migration-details"
  - title: Refactor Audit Removals and Justifications
    link: "#refactor-audit-removals-and-justifications"
  - title: Deferred Inventory Call Sites
    link: "#deferred-inventory-call-sites"
  - title: Lessons to Register
    link: "#lessons-to-register"
executive_summary: >
  This report documents the Class C11 (external-claims) Phase 2 Batch 1 migrations
  across four targeted call sites in fetch.py and iguzzini.py. All call sites fail
  closed against historical defects l0072, l0113, and l0122 while preserving public
  signatures, return types, and complete test isolation.
---

# External Claims Defense: Phase 2 Batch 1 Migration Report

## Executive Summary

Phase 2 Batch 1 routes four critical external intake call sites through the centralized guards in [`src/archpipe/external_claims.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/external_claims.py). The migrations eliminate silent ingestion of empty files ([`l0072`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L257)), content-type spoofing and HTML error pages disguised as assets ([`l0113`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L298)), and catalogue crawl completeness shortfalls ([`l0122`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L307)). Public function signatures and return types are strictly preserved, no arbitrary thresholds were introduced, and unit tests execute under complete network isolation via mocked HTTP layers.

---

## Changed Files Inventory

Only the following six files were modified or created for this batch:

1. [`src/archpipe/fetch.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/fetch.py): Added `external_claims` import; updated `get_text()` and `download()`.
2. [`src/archpipe/luminaires/iguzzini.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/luminaires/iguzzini.py): Added `external_claims` import; updated `crawl_products()` and `fetch_photometry()`.
3. [`tests/test_c11_phase2.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_c11_phase2.py): New unit test suite with 10 isolated tests verifying all four call sites against frozen historical defects, quiet clean inputs, and sibling mutations.
4. [`docs/external-claims.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/external-claims.md): Marked the four migrated rows in Sections 1 and 2 as migrated in Phase 2 Batch 1.
5. [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md): Appended the Phase 2 Batch 1 migration record under the `external-claims-phase1` section.
6. [`docs/c11p2-report.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/c11p2-report.md): This report document.

---

## Call-Site Migration Details

### 1. `src/archpipe/fetch.py:download()`
- **Old Behavior**: Streamed HTTP response bytes to a `.part` temporary file and directly replaced destination path `dest` with only a size upper-bound check (`MAX_BYTES`). An HTML error page (e.g. 404 Not Found) served with HTTP 200 would replace `.ies` or `.gltf` destination files undetected.
- **New Behavior**: Before `part.replace(dest)`, downloaded bytes are read and passed to `external_claims.ingest_bytes(data, declared_type=dest.suffix.lstrip(".") or None, url=url)`.
  - If `rec.status != external_claims.VERIFIED`:
    - The `.part` file is deleted (`part.unlink()`).
    - If `sniffed_type == "empty"`, raises `external_claims.EmptyContentError` ([`l0072`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L257)).
    - Otherwise raises `external_claims.ContentTypeMismatchError` ([`l0113`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L298)).
- **Return Type & Intake Receipt Rationale**: The inventory noted recording SHA-256 and retrieval time into an intake receipt. However, `download()` has an established public return type signature of `Path` (`return dest: Path`), consumed across the project (e.g., `src/archpipe/asset_intake.py`). Returning a tuple or dictionary receipt would alter this public return type and break existing callers. In accordance with the instruction, the public `Path` return type was kept strictly unchanged, and this limitation is recorded here.
- **Test Proofs in `tests/test_c11_phase2.py`**:
  - `test_fetch_download_real_html_error_page_fails_closed_l0113`: Frozen Signify HTML 404 error page payload fails closed with `ContentTypeMismatchError`; `dest` is not created.
  - `test_fetch_download_real_empty_payload_fails_closed_l0072`: Frozen 0-byte download payload fails closed with `EmptyContentError`; `dest` is not created.
  - `test_fetch_download_clean_ies_content_passes_quietly`: Clean IES photometry downloads quietly, returns `dest: Path`, and matches expected bytes.
  - `test_fetch_download_sibling_png_payload_to_ies_dest_fails`: Sibling disguised PNG payload fails closed with `ContentTypeMismatchError`.

### 2. `src/archpipe/fetch.py:get_text()`
- **Old Behavior**: Read UTF-8 decoded text directly from network and wrote to disk cache `f` without byte sniffing.
- **New Behavior**: Network response bytes are passed to `external_claims.ingest_bytes(data, declared_type="html", url=url)`.
  - If `rec.status != external_claims.VERIFIED`:
    - If `sniffed_type == "empty"`, raises `external_claims.EmptyContentError`.
    - Otherwise raises `external_claims.ContentTypeMismatchError`.
  - Decoded text is only written to cache `f` upon verification. Disk caching behavior is otherwise unchanged (cached files are returned directly without network access).
- **Test Proofs in `tests/test_c11_phase2.py`**:
  - `test_fetch_get_text_real_empty_payload_fails_closed_l0072`: 0-byte page fails closed with `EmptyContentError`; cache file is not created.
  - `test_fetch_get_text_real_binary_zip_payload_fails_closed_l0113`: Binary zip payload served where HTML was expected fails closed with `ContentTypeMismatchError`; cache file is not created.
  - `test_fetch_get_text_clean_html_passes_and_preserves_cache`: Valid HTML page passes, caches to disk, and subsequent call reads from disk cache without network requests.
  - `test_fetch_get_text_sibling_gltf_payload_fails`: Sibling binary glTF payload fails closed with `ContentTypeMismatchError`.

### 3. `src/archpipe/luminaires/iguzzini.py:fetch_photometry()`
- **Old Behavior**: Evaluated `if library.sniff(data) != kind:` on downloaded raw bytes and raised `ValueError(f"{code} {kind}: downloaded content is not {kind}")`.
- **New Behavior**: Replaced `library.sniff(data) != kind` with `rec = external_claims.ingest_bytes(data, declared_type=kind, url=row["files"][kind])`.
  - If `rec.status != external_claims.VERIFIED`: raises the exact same `ValueError(f"{code} {kind}: downloaded content is not {kind}")`, preserving caller error contracts.
- **Test Proofs in `tests/test_c11_phase2.py`**:
  - `test_iguzzini_fetch_photometry_real_html_error_fails_closed_l0113`: HTML error page served for `.ldt` file fails closed with `ValueError("451G ldt: downloaded content is not ldt")`.
  - `test_iguzzini_fetch_photometry_clean_eulumdat_passes_quietly`: Clean valid Eulumdat LDT and IES payloads succeed, write catalogue and inbox files, and return inbox import result.
  - `test_iguzzini_fetch_photometry_sibling_format_swap_fails`: Format translation mutation (IES payload served when LDT requested) fails closed with `ValueError`.

### 4. `src/archpipe/luminaires/iguzzini.py:crawl_products()`
- **Old Behavior**: Crawled product pages and wrote coverage statistics via `write_coverage`, returning parsed rows even when substantial families were unread.
- **New Behavior**: Immediately after `write_coverage("iguzzini", ...)`, calls `external_claims.assert_manifest_complete(len(requested), len(rows), label="iGuzzini product crawl", min_coverage_ratio=1.0, missing_items=unread)`.
- **Threshold Policy**: In accordance with the instructions ("do not invent a threshold: if assert_manifest_complete needs a minimum ratio that the repo does not already define, require completeness (all requested families) and state that in the report"), the ratio is set to strict 100% completeness (`min_coverage_ratio=1.0`). If any requested family fails to parse, the crawl fails closed with `CompletenessShortfallError` ([`l0122`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L307)).
- **Test Proofs in `tests/test_c11_phase2.py`**:
  - `test_iguzzini_crawl_products_real_shortfall_fails_closed_l0122`: Frozen historical defect of 381 requested families with 158 unread/lost (223 received, 41% loss) fails closed with `CompletenessShortfallError`.
  - `test_iguzzini_crawl_products_clean_completeness_passes_quietly`: 5 requested families all parsed successfully passes quietly and returns all 5 rows.
  - `test_iguzzini_crawl_products_sibling_single_missing_item_fails`: Sibling mutation of 10 requested items with 1 unread fails closed under the 100% completeness gate.

---

## Refactor Audit Removals and Justifications

For `scripts/refactor_audit.py --base <branch_start>`:

1. **`src/archpipe/fetch.py:84` (in `get_text`)**:
   - *Removed statement*: `text = r.read().decode("utf-8", "replace")`
   - *Justification*: Replaced by reading raw `data = r.read()`, passing `data` through `external_claims.ingest_bytes(data, declared_type="html", url=url)` to fail closed on empty content or non-HTML payloads, and then decoding `text = data.decode("utf-8", "replace")`.
2. **`src/archpipe/fetch.py:104` (in `download`)**:
   - *Modified statement*: Inserted verification block immediately prior to `part.replace(dest)`.
   - *Justification*: Staged `.part` bytes are audited via `external_claims.ingest_bytes` against `dest.suffix` before replacing `dest`. No existing statements were deleted.
3. **`src/archpipe/luminaires/iguzzini.py:197` (in `crawl_products`)**:
   - *Modified statement*: Inserted `external_claims.assert_manifest_complete(...)` after `write_coverage(...)` and before `return rows`.
   - *Justification*: Gates completion against requested item count (lesson `l0122`). No existing statements were deleted.
4. **`src/archpipe/luminaires/iguzzini.py:215-216` (in `fetch_photometry`)**:
   - *Removed statement*: `if library.sniff(data) != kind:`
   - *Justification*: Replaced local `library.sniff` check with centralized `external_claims.ingest_bytes(data, declared_type=kind, url=row["files"][kind])` and asserted `rec.status == external_claims.VERIFIED`, preserving identical `ValueError` message and caller contract.

---

## Deferred Inventory Call Sites

In accordance with batch boundary rules, the remaining candidate call sites from `docs/external-claims.md` were NOT modified in this batch:

1. **`src/archpipe/luminaires/library.py` (`sniff`, `import_inbox`)**: Owned by concurrent luminaire library tasks.
2. **`src/archpipe/asset_intake.py` (`validate_entry`)**: Owned by 3D asset pipeline agent.
3. **`src/archpipe/knowledge_index.py` (`search`)**: Owned by literature search workstream.
4. **`revit/install_family.py` & `revit/extract_model.py`**: Owned by Revit integration workstream.
5. **`src/archpipe/guard_registry.py`**: Reserved for project lead integration.

---

## Lessons to Register

| Lesson ID | Quoted Historical Learning | Registered Call-Site Function |
|---|---|---|
| [`l0072`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L257) | *"All six props were recorded as downloaded while their folders were empty"* | [`archpipe.fetch.download`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/fetch.py#L97-L125), [`archpipe.fetch.get_text`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/fetch.py#L75-L94) |
| [`l0113`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L298) | *"Signify served a zip labelled application/json; Revit type catalogues are UTF-16 with a BOM"* | [`archpipe.fetch.download`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/fetch.py#L97-L125), [`archpipe.fetch.get_text`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/fetch.py#L75-L94), [`archpipe.luminaires.iguzzini.fetch_photometry`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/luminaires/iguzzini.py#L208-L229) |
| [`l0122`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L307) | *"The catalogue crawl lost 158 of 381 families (41%) and still looked finished"* | [`archpipe.luminaires.iguzzini.crawl_products`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/luminaires/iguzzini.py#L173-L206) |

## Lead review correction (2026-10-08)

The first version declared every `get_text` payload as HTML and every download as its file extension. The only `get_text` callers read Poly Haven JSON APIs (`products/sources.py`, `scripts/products.py`), and the product worker downloads `.exr`, `.bin` and `.gltf` files that `sniff_content` cannot identify by extension, so both would have refused valid content. `fetch._refuse_payload` now: refuses empty payloads (l0072) everywhere; checks the declared type only for extensions the sniffer identifies (`SNIFFABLE`); refuses an HTML error page in place of any non-HTML download (l0113); and refuses binary payloads in `get_text`. Regression tests cover JSON text, `.exr`/`.bin`/`.gltf` downloads, and an HTML 404 served for an `.exr`.
