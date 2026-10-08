---
outline:
  - title: Executive Summary
    link: "#executive-summary"
  - title: Reused Architecture and Components
    link: "#reused-architecture-and-components"
  - title: Ingest and Integrity Pipeline (Phase 1)
    link: "#ingest-and-integrity-pipeline-phase-1"
  - title: Phase 2 Call-Site Migration Inventory
    link: "#phase-2-call-site-migration-inventory"
  - title: Defect Reference Mapping
    link: "#defect-reference-mapping"
executive_summary: >
  This document details the external claims defense architecture implemented in
  src/archpipe/external_claims.py to prevent trusting unverified external data sources.
  It documents existing code reused from evidence, luminaire, asset, and search modules,
  and catalogues all call sites across the codebase targeted for migration in Phase 2.
---

# External Claims Defense: Architecture and Phase 2 Migration Inventory

## Executive Summary

External systems—remote servers, manufacturer catalogues, search engines, download archives, and third-party BIM files—frequently make assertions that are inaccurate or incomplete. In response to 13 historical defects where external claims were erroneously trusted, Phase 1 introduces [`src/archpipe/external_claims.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/external_claims.py) built upon [`src/archpipe/evidence.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py). This document outlines what code was reused and inventories all candidate call sites to be migrated in Phase 2.

---

## Reused Architecture and Components

Rather than inventing duplicate data models or sniffing logic, Phase 1 directly builds upon existing verified project modules:

1. **[`archpipe.evidence`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py)**:
   - Reused [`EvidenceRecord`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py#L236-L483), [`EvidenceStatus`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py#L54-L61), [`SourceRef`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py#L135-L194), and [`EvidenceError`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py#L114-L116).
   - All external ingest decisions produce typed `EvidenceRecord` structures. Discrepancies stay `UNVERIFIED` with both contradictory values retained for audit.

2. **[`archpipe.luminaires.library`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/luminaires/library.py)**:
   - Reused the `OLE_MAGIC` compound binary signature (`b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"`) for Revit `.rfa` and `.rvt` identification.
   - Reused zip inspection patterns for GLDF container detection (`product.xml` presence) and Eulumdat parser invocation.

3. **[`archpipe.fixture_source`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/fixture_source.py)**:
   - Reused the geometric aspect ratio (3:1 max drift) and dimension ratio (2:1 max size factor) logic from [`photometry_matches_fitting`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/fixture_source.py#L67-L89) to prevent attaching linear strip photometry to round drum fittings ([`l0098`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L201)).

4. **[`archpipe.knowledge_index`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/knowledge_index.py)**:
   - Reused the standard stop-word corpus and the minimum term requirement ratio (`need = max(2, (len + 1) // 2)`) to eliminate nonsense queries returning spurious fallback hits ([`l0191`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L294)).

---

## Ingest and Integrity Pipeline (Phase 1)

[`src/archpipe/external_claims.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/external_claims.py) provides seven centralized functions:

- `sniff_content(data: bytes) -> tuple[str, str | None]`: Pure byte-level identification (magic numbers, UTF-16/UTF-8 BOMs, IES/LDT headers).
- `ingest_bytes(...) -> EvidenceRecord`: Provenance tracking (URL, timestamp, SHA-256 hash, byte count) and declared vs sniffed type validation ([`l0113`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L216)).
- `check_manifest_completeness(...) -> EvidenceRecord`: Coverage verification refusing to report complete when crawl or ingest falls short ([`l0122`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L225)).
- `check_found_content(...) -> EvidenceRecord`: Ensures 'found' or 'downloaded' claims have non-empty on-disk content ([`l0072`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L175)).
- `check_cct_and_watts_agreement(...) -> EvidenceRecord`: Product cross-source agreement maintaining both values and remaining `UNVERIFIED` on divergence ([`l0118`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L221)).
- `check_photometry_fitting_agreement(...) -> EvidenceRecord`: Detects mismatched photometry files vs physical fittings ([`l0098`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L201)).
- `check_search_relevance(...)` and `filter_search_results(...)`: Eliminates spurious search hits from multi-word nonsense queries ([`l0190`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L293), [`l0191`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L294)).
- `check_safe_destination(...)`: Enforces destination isolation to prevent test output writing into deployed repositories ([`l0120`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L223)).

---

## Phase 2 Call-Site Migration Inventory

The following call sites currently ingest external data or assert claims without the centralized external claims guards. They are scheduled for migration in Phase 2:

### 1. HTTP Fetch & Download Pipeline
- **[`src/archpipe/fetch.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/fetch.py#L88-L106)** (`download`) **[MIGRATED Phase 2 Batch 1]**:
  - *Current*: Ingests downloaded bytes via `external_claims.ingest_bytes` before staging `.part` file replaces `dest`; fails closed on content-type mismatch or empty payload.
  - *Target*: Ingest via `external_claims.ingest_bytes`; verify sniffed type matches expected extension before replacing `.part` file; record SHA-256 and retrieval timestamp into an intake receipt (public Path return type preserved).
- **[`src/archpipe/fetch.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/fetch.py#L73-L86)** (`get_text`) **[MIGRATED Phase 2 Batch 1]**:
  - *Current*: Reads UTF-8 text from cache or network; validates response bytes through `external_claims.ingest_bytes`, rejecting empty payloads and non-HTML content before writing cache.
  - *Target*: Pass through `external_claims.ingest_bytes` to verify non-empty, non-HTML error payload.

### 2. Luminaire Ingestion & Catalogue Crawl
- **[`src/archpipe/luminaires/library.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/luminaires/library.py#L107-L136)** (`sniff`):
  - *Current*: Local luminaire-only sniffing function.
  - *Target*: Replace implementation with delegation to `external_claims.sniff_content`.
- **[`src/archpipe/luminaires/library.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/luminaires/library.py#L201-L278)** (`import_inbox`):
  - *Current*: Loops through inbox and writes product folders and `product.json` records without verifying declared vs sniffed type or cross-source parameter agreement.
  - *Target*: Ingest incoming assets using `external_claims.ingest_bytes`; record provenance records into `product.json`; run `check_cct_and_watts_agreement` before marking product verified.
- **[`src/archpipe/luminaires/iguzzini.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/luminaires/iguzzini.py#L172-L198)** (`crawl_products`) **[MIGRATED Phase 2 Batch 1]**:
  - *Current*: Crawls product pages, writes catalogue and coverage statistics, and gates completion via `external_claims.assert_manifest_complete` against requested family count (l0122).
  - *Target*: Gate crawl completion with `external_claims.assert_manifest_complete` against requested family count ([`l0122`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L225)).
- **[`src/archpipe/luminaires/iguzzini.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/luminaires/iguzzini.py#L200-L220)** (`fetch_photometry`) **[MIGRATED Phase 2 Batch 1]**:
  - *Current*: Verifies downloaded photometry bytes via `external_claims.ingest_bytes(data, declared_type=kind, url=...)` before saving to inbox, preserving `ValueError` contract.
  - *Target*: Replace with `external_claims.ingest_bytes(data, declared_type=kind, url=...)`.

### 3. Asset Intake & 3D Prop Manifest
- **[`src/archpipe/asset_intake.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/asset_intake.py#L93-L213)** (`validate_entry`):
  - *Current*: Evaluates bounds and metadata when local model file exists, but missing local files are reported as warnings or ignored for candidates.
  - *Target*: Enforce `external_claims.check_found_content` for every downloaded asset folder to catch 0-byte or empty directories ([`l0072`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L175)).
  - *Target*: Integrate `check_photometry_fitting_agreement` during lighting asset intake ([`l0098`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L201)).

### 4. Knowledge Base & Literature Search
- **[`src/archpipe/knowledge_index.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/knowledge_index.py#L320-L370)** (`search`):
  - *Current*: Contains inline BM25 fallback term counting logic (lines 345–351).
  - *Target*: Replace inline term matching with `external_claims.check_search_relevance` and `external_claims.filter_search_results` ([`l0191`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L294)).

### 5. Revit Extraction and Family Parameter Cross-Checking
- **[`revit/install_family.py`](file:///C:/Users/mmbka/arch-pipeline-agy/revit/install_family.py)** & **[`revit/extract_model.py`](file:///C:/Users/mmbka/arch-pipeline-agy/revit/extract_model.py)**:
  - *Current*: Extracts Revit family type parameters (e.g. Apparent Load, Initial Color Temperature) and applies them directly.
  - *Target*: Run `external_claims.check_cct_and_watts_agreement` comparing extracted Revit parameters with the LDT file. When they conflict (e.g. 3200 K/3 W vs 3000 K/23 W), refuse silent overwrite and keep `status: UNVERIFIED` ([`l0118`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L221)).

---

## Defect Reference Mapping

| Lesson ID | Observed Defect | Defense in `external_claims.py` | Phase 2 Action |
|---|---|---|---|
| [`l0070`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L173) | Oak lost colour after reducing contrast | Provenance and content hash tracking | Texture processing ingest |
| [`l0072`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L175) | Props recorded as downloaded with empty folders | `check_found_content` | `asset_intake.py` manifest check |
| [`l0098`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L201) | Strip photometry attached to round drum | `check_photometry_fitting_agreement` | `fixture_source.py` / lighting intake |
| [`l0113`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L216) | Zip labelled application/json; UTF-16 BOM | `sniff_content`, `ingest_bytes` | `fetch.py`, `library.py` inbox import |
| [`l0118`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L221) | Revit family 3200K/3W vs LDT 3000K/23W | `check_cct_and_watts_agreement` | Revit family installation / spec build |
| [`l0120`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L223) | Test exported synthetic IES to deployed store | `check_safe_destination` | Test suite destination assertions |
| [`l0122`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L225) | Crawl lost 158 of 381 families (41%) | `check_manifest_completeness` | `iguzzini.crawl_products` gate |
| [`l0177`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L280) | Good texture failed map role | Provenance mapping | Texture manifest validator |
| [`l0178`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L281) | Polycount mismatch across definitions | Unstated definition preserved as UNVERIFIED | Asset intake polycount audit |
| [`l0190`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L293) | Partial match required for literature search | `check_search_relevance` fallback | `knowledge_index.search` |
| [`l0191`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L294) | Search fallback returned nonsense query hits | `filter_search_results` min term gate | `knowledge_index.search` |
| [`l0612`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L715) | Manufacturer data parsed, never repaired | Non-repaired `UNVERIFIED` retention | Eulumdat parser integration |
| [`l0846`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L949) | Asset stand-in native size is claim, not default | Intake claim bounds audit | Scene asset intake gate |
