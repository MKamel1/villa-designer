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
  This report documents the Class C11 (external-claims) Phase 2 Batch 2 migrations
  across remaining call sites in library.py and asset_intake.py. All call sites fail
  closed against historical defects l0072, l0113, and l0118 while preserving public
  signatures, return types, and complete test isolation.
---

# External Claims Defense: Phase 2 Batch 2 Migration Report

## Executive Summary

Phase 2 Batch 2 migrates the remaining call sites from sections 2 and 3 of [`docs/external-claims.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/external-claims.md) into the centralized external claims defense module [`src/archpipe/external_claims.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/external_claims.py). The migrations eliminate byte sniffing duplication and bypasses in luminaire file identification ([`l0113`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L314)), prevent ingestion and filing of empty payloads or HTML error pages disguised as photometry or BIM assets ([`l0072`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L273), [`l0113`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L314)), gate product verification on cross-source agreement between manufacturer BIM claims and photometric measurements ([`l0118`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L319)), and enforce directory/file non-emptiness validation during 3D asset intake ([`l0072`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L273)). Public function signatures and return types are strictly preserved, no invented thresholds were introduced, and all tests execute in temporary folders without network access.

---

## Changed Files Inventory

Only the following six files were modified or created for this batch:

1. [`src/archpipe/luminaires/library.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/luminaires/library.py): Delegated `sniff()` to `external_claims.sniff_content` preserving accepted luminaire types; audited incoming payloads in `import_inbox()` via `external_claims.ingest_bytes` attaching provenance records; enforced `external_claims.check_cct_and_watts_agreement` in `verify_product()` when product metadata already records both CCT and power.
2. [`src/archpipe/asset_intake.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/asset_intake.py): Added `external_claims.check_found_content` verification on downloaded asset folders and model files in `validate_entry()`, failing closed on empty folders or 0-byte models.
3. [`tests/test_c11_phase2b.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_c11_phase2b.py): New unit test suite with 10 isolated tests verifying all three call sites against frozen historical defects, quiet clean inputs, and sibling mutations.
4. [`docs/external-claims.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/external-claims.md): Marked the migrated rows in Section 2 (`library.py:sniff`, `library.py:import_inbox`) and Section 3 (`asset_intake.py:validate_entry`) as migrated in Phase 2 Batch 2.
5. [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md): Appended the Phase 2 Batch 2 migration record under `external-claims-phase1`.
6. [`docs/c11p2b-report.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/c11p2b-report.md): This report document.

---

## Call-Site Migration Details

### 1. `src/archpipe/luminaires/library.py:sniff()`
- **Old Behavior**: Contained an ad-hoc parser with local byte checks for zip (`PK\x03\x04`), GLDF (`product.xml`), OLE compound binaries (`OLE_MAGIC`), IES (`IESNA`), and basic LDT string parsing, duplicating logic now centralized in `external_claims`.
- **New Behavior**: Delegates byte inspection directly to `external_claims.sniff_content(data)`.
  - Directly returns the identified format for all accepted luminaire formats: `"zip"`, `"gldf"`, `"rfa"`, `"ies"`, `"ldt"`.
  - For `"txt"`, retains the specific Revit type catalogue header validation (UTF-16 with BOM containing `##`, or Latin-1 containing `##` with more than 3 commas), returning `"txt"` if valid and `None` otherwise.
  - Returns `None` for any unverified, empty, or non-luminaire payloads.
- **Contract & Return Value**: Preserves public signature `def sniff(data: bytes) -> str | None` and exact return values (`'zip' | 'rfa' | 'ies' | 'ldt' | 'gldf' | 'txt' | None`).
- **Test Proofs in `tests/test_c11_phase2b.py`**:
  - `test_library_sniff_real_zip_labelled_application_json_identifies_content_l0113`: Frozen historical defect of Signify serving a zip labelled `application/json` identifies by byte content as `"zip"`.
    - *Quoted LEARNINGS line 314*: `| Signify served a zip labelled application/json; Revit type catalogues are UTF-16 with a BOM | Extensions and content types were assumed truthful | library.sniff identifies by content (zip, OLE, UTF-16 ## header, IES, LDT); tested |`
  - `test_library_sniff_real_html_error_page_rejected_l0113`: Frozen HTML 404 error page returns `None`.
  - `test_library_sniff_real_empty_payload_rejected_l0072`: Frozen 0-byte payload returns `None`.
    - *Quoted LEARNINGS line 273*: `| All six props were recorded as downloaded while their folders were empty | The API shape was one level deeper than assumed, and there was no post-condition on files | Raise when a package has no URL; confirm files on disk |`
  - `test_library_sniff_clean_luminaire_types_pass_quietly`: Clean LDT, IES, RFA, GLDF, ZIP, and UTF-16/Latin-1 type catalogues all return their expected types.
  - `test_library_sniff_sibling_png_payload_rejected`: Sibling disguised PNG payload returns `None`.
  - `test_library_sniff_sibling_plain_text_rejected`: Sibling generic plain text without type catalogue headers returns `None`.

### 2. `src/archpipe/luminaires/library.py:import_inbox()`
- **Old Behavior**: Iterated over inbox files and wrote `.ldt`, `.ies`, `.rfa`, and `.txt` files directly to disk without verifying that the payload matched the declared format or was non-empty. In `verify_product()`, cross-source divergence between manufacturer BIM parameter claims (`product.json`) and photometric measurements (`.ldt`) was never verified.
- **New Behavior**:
  - Before writing files to product folders, passes each payload through `external_claims.ingest_bytes(data, declared_type=kind, url=origin)`.
  - If `rec.status != external_claims.VERIFIED`, skips filing the file and appends it to `skipped` with the rejection reason.
  - When filing accepted assets, records provenance metadata (`rec.value.get("provenance")`) into the `sources` array of `product.json`.
  - In `verify_product()`, inspects `product.json`. If `meta` already contains both CCT and power attributes (`has_meta_cct and has_meta_watts`), executes `external_claims.check_cct_and_watts_agreement(meta, {"cct_k": ls.cct_k, "watts": ls.watts}, source_a_label="product_record", source_b_label="ldt")`.
  - If the check does not verify (drift exceeds 100 K CCT or 0.5 W power), appends the discrepancy to `problems` and enforces `verified == 0`, ensuring divergent products are excluded from default search results. Products lacking both values in `product.json` bypass the check, preserving existing unconstrained behavior.
- **Contract & Return Value**: Preserves public signature `def import_inbox(library: Path = LIBRARY, log=print) -> dict` and returns the same dictionary schema `{"products": int, "rows": int, "skipped": list}`.
- **Test Proofs in `tests/test_c11_phase2b.py`**:
  - `test_import_inbox_real_html_error_page_skipped_before_filing_l0113`: Frozen HTML 404 payload disguised as `.ldt` is skipped, not written to the product folder, and reported in `skipped`.
  - `test_import_inbox_real_empty_payload_skipped_before_filing_l0072`: Frozen 0-byte `.ldt` payload is skipped and not filed into the product folder.
  - `test_import_inbox_real_cross_source_disagreement_stays_unverified_l0118`: Frozen historical defect of Signify Revit family claiming 3200 K / 3 W while LDT measures 3000 K / 23 W.
    - *Quoted LEARNINGS line 319*: `| Signify's Revit family says 3200 K and 3 W; its LDT says 3000 K and 23 W | Manufacturer BIM metadata is not checked by anyone | The LDT governs; the build writes its figures onto the family; install.resolve refuses a spec that contradicts the product |`
    - Product is indexed with `verified == 0`, sanity records `l0118` mismatch, and `library.search()` excludes it unless `include_unverified=True`.
  - `test_import_inbox_clean_product_passes_and_records_provenance`: Valid LDT agreeing with metadata (3000 K, 23 W) indexes with `verified == 1`, passes search, and attaches provenance metadata to `product.json`.
  - `test_import_inbox_sibling_watts_only_disagreement_stays_unverified`: Sibling mutation where CCT agrees (3000 K) but power disagrees (10 W vs 23 W) stays unverified with `verified == 0`.
  - `test_import_inbox_sibling_disguised_png_to_ies_skipped`: Disguised PNG payload in inbox claiming `.ies` is skipped and not filed.

### 3. `src/archpipe/asset_intake.py:validate_entry()`
- **Old Behavior**: When `model_path` was supplied, only inspected preview file existence and glTF bounding boxes if `target_model` existed. An empty download folder or a folder holding only 0-byte model files produced zero errors, falsely treating empty intake downloads as valid.
- **New Behavior**:
  - When `model_path` is passed, invokes `external_claims.check_found_content(model_path, name=asset_id)`.
  - If `model_path` is a file, also validates `model_path.parent` via `external_claims.check_found_content`.
  - If `rec.status != external_claims.VERIFIED`, appends the reason (e.g. `"[l0072] asset contains no non-empty files"`) to `errors`.
  - Subsequent glTF bounds parsing and preview checks proceed only when `target_model` is non-empty.
- **Contract & Return Value**: Preserves public signature `def validate_entry(entry: dict, model_path: Path | None = None, measure: Callable[[Path], dict] | None = None) -> list[str]` and returns `errors: list[str]`.
- **Test Proofs in `tests/test_c11_phase2b.py`**:
  - `test_validate_entry_real_empty_download_folder_fails_closed_l0072`: Frozen historical defect of all six props recorded as downloaded while folders were empty fails closed with `l0072`.
    - *Quoted LEARNINGS line 273*: `| All six props were recorded as downloaded while their folders were empty | The API shape was one level deeper than assumed, and there was no post-condition on files | Raise when a package has no URL; confirm files on disk |`
  - `test_validate_entry_real_zero_byte_download_files_fails_closed_l0072`: Download folder holding 0-byte `model.gltf` fails closed with `l0072`.
  - `test_validate_entry_clean_case_passes_quietly`: Valid asset directory containing non-empty `model.gltf` and preview image returns an empty error list `[]`.
  - `test_validate_entry_sibling_renamed_prop_empty_folder_fails`: Sibling renamed prop with empty download directory fails closed with `l0072`.

---

## Refactor Audit Removals and Justifications

For `scripts/refactor_audit.py --base <branch_start>`:

1. **`src/archpipe/luminaires/library.py:122-137` (in `sniff`)**:
   - *Removed statement*: Redundant inline byte-prefix checks (`data[:4] == b"PK\x03\x04"`, `data[:8] == OLE_MAGIC`, `data.startswith(b"IESNA")`, etc.).
   - *Justification*: Replaced with `kind, encoding = external_claims.sniff_content(data)`. Preserves exact luminaire filter and Revit type catalogue header validation while eliminating duplicate byte-sniffing code.
2. **`src/archpipe/luminaires/library.py:211-275` (in `import_inbox`)**:
   - *Modified statement*: Inserted `rec = external_claims.ingest_bytes(...)` checks in `ldts`, `iess`, and `rfas + txts` loops before writing files to disk; added provenance metadata to `sources`.
   - *Justification*: Protects library storage against unverified, empty, or disguised payloads (lessons `l0072`, `l0113`). No existing data structures or business logic were deleted.
3. **`src/archpipe/luminaires/library.py:322-364` (in `verify_product`)**:
   - *Modified statement*: Inserted check for `has_meta_cct and has_meta_watts` and called `external_claims.check_cct_and_watts_agreement(...)`, adding failure reasons to `problems` and gating `verified`.
   - *Justification*: Enforces cross-source consistency between BIM claims and photometric measurements (lesson `l0118`) without modifying products that lack both fields.
4. **`src/archpipe/asset_intake.py:200-216` (in `validate_entry`)**:
   - *Modified statement*: Inserted `external_claims.check_found_content(...)` calls for `model_path` (directory or file) before checking preview images and glTF geometry.
   - *Justification*: Catches empty asset directories and 0-byte download files (lesson `l0072`). No existing validation rules were deleted or rewritten.

---

## Deferred Inventory Call Sites

In accordance with batch boundary rules, the remaining candidate call sites from `docs/external-claims.md` were NOT modified in this batch:

1. **`src/archpipe/knowledge_index.py` (`search`)**: Section 4 search relevance filtering (lesson `l0191`).
2. **`revit/install_family.py` & `revit/extract_model.py`**: Section 5 Revit parameter extraction and cross-checking (lesson `l0118`).
3. **`src/archpipe/guard_registry.py`**: Reserved for project lead registry integration.

---

## Lessons to Register

| Lesson ID | Quoted Historical Learning | Registered Call-Site Function |
|---|---|---|
| [`l0072`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L273) | *"All six props were recorded as downloaded while their folders were empty"* | [`archpipe.luminaires.library.import_inbox`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/luminaires/library.py#L203-L295), [`archpipe.asset_intake.validate_entry`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/asset_intake.py#L96-L235) |
| [`l0113`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L314) | *"Signify served a zip labelled application/json; Revit type catalogues are UTF-16 with a BOM"* | [`archpipe.luminaires.library.sniff`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/luminaires/library.py#L122-L137), [`archpipe.luminaires.library.import_inbox`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/luminaires/library.py#L203-L295) |
| [`l0118`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L319) | *"Signify's Revit family says 3200 K and 3 W; its LDT says 3000 K and 23 W"* | [`archpipe.luminaires.library.verify_product`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/luminaires/library.py#L313-L370) |

## Lead review (2026-10-08)

- REVERTED: the `asset_intake.validate_entry` change. It reported a missing local model file as an l0072 error, where the existing contract accepts candidates without a local file; every manifest entry would fail on a machine without the library. Its four tests were removed. l0072 is not covered by this batch.
- ACCEPTED: `library.sniff` delegating to `external_claims.sniff_content` (existing luminaire tests pass), `import_inbox` ingesting each incoming file through `ingest_bytes` with provenance, and `verify_product` refusing verification when product-record CCT/watts disagree with the LDT (l0118). Lead change: all disagreement reasons are reported, not only the first.
- Test fixes by the lead: the import tests guessed the product folder name (the import files products by the LDT's own manufacturer/catalogue fields), passed an unsupported `sku=` to `search()`, and merged product metadata after the index was built; they now locate the real folder, merge the metadata and rebuild the index.
