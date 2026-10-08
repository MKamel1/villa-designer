# Serialization boundary: Phase 1 checkpoint

Scope: the thirteen records in the `serialization or file replacement fragile`
class in `docs/lessons-audit.md`. Partial migration; no native acceptance claimed.

## API and operating procedure

`archpipe.safe_io` is the boundary module; its core uses IronPython 2.7 compatible
syntax. `Byte`, `Color`, `ElementId`, `XYZ`, `Quantity` and `Text` are portable
records, not Autodesk objects. XYZ stores three Cartesian coordinates and a
length unit; Quantity stores a length and unit. Units: `ft` (feet), `mm`
(millimetres), `m` (metres). `convert_length` converts an explicit Quantity.

`encode` creates explicit type/value tags; `decode` reconstructs portable records.
Native Byte, Color, ElementId and XYZ wrappers are projected deliberately;
native XYZ is in feet. Unknown objects, invalid byte channels and non-finite
numbers raise. `assert_round_trip` compares tags after serialization and decoding,
preserving integer zero, floating zero, False and None separately. CPython bytes
have a bytes tag; Python 2 byte strings remain legacy text, so individual native
byte channels must use Byte explicitly.

`normalized_text` changes carriage returns and CR/LF pairs to logical LF lines,
removes terminal line endings and records the exact original. Interior blank
lines survive. CR means carriage return; LF means line feed.

`atomic_path` stages at a unique path beside the destination, flushes the file
to disk with `fsync`, then uses `os.replace`. Python 2 uses .NET `File.Replace`
for existing files and `File.Move` for new files, never delete-then-move.
Writers must close the staged file before leaving the context. Failure removes
staging and preserves the old destination; replacement retries remain available.
`save_bytes`, `save_text`, `save_json` and `copy_file` share this implementation.
JSON serialization finishes before staging. Revit supplies the existing ASCII-only
`jsonsafe.dumps` serializer. `load_json` reads bytes before decoding UTF-8 with
an optional byte-order mark or byte-order-marked UTF-16. Atomicity is per file,
not an entire package. Both extract entry points must use `write_extract`.

`assert_measured_readback(actual, measured, sources)` requires matching fields,
an independent measurement witness and a declared `model` source for each field.
A specification echo disagreeing with measurement raises; authored values that
match measurement legitimately pass. The helper cannot establish whether callers
truly measured their witnesses. Native adapters/wiring remain Phase 2; copies of
actual or specification values are not independent measurement evidence.

## Inventory and migrations

| Boundary | Before | Phase 1 |
|---|---|---|
| `safe_io.save_bytes`, `copy_file` | Shared fixed `.part`, retries, no disk flush | Unique staging, disk flush, atomic replace, failure cleanup |
| CLI `revit/extract_model.py` | ASCII serializer before opening; in-place overwrite; manual Color casts | Shared `write_extract`; typed Color/TextNote adapter wiring is not present in this worktree and remains pending |
| Extract Model ribbon | Raw JSON/truncating writes | Same `write_extract` as CLI |
| `from_extract.convert`, `review_extract.review_model` | Dict input, explicit mm and measured footprint requirements | Dict behavior retained; file inputs use `load_json` through convert |
| `deliverables.write_csv`, `to_ifc`; `scripts/handoff.py` | Direct CSV/IFC/JSON/README writes | Atomic publication; independent IFC geometry tests retained |
| `concept/villa_render.write` | Already `safe_io.save_bytes`, scene validation/source fingerprint | No call-site edit; strengthened shared writer applies |
| `execution_context.write_record` | Direct JSON overwrite | Atomic shared JSON writer |
| `revit/jsonsafe.clean` | Integral wrappers passed through float | Exact integer conversion before numeric fallback |
| `daylight.write_job`, `read_case` | Direct `write_text`/`write_bytes`, direct `json.loads` | Atomic `save_text`, `save_json`, `save_bytes`, and `load_json` via `safe_io` |
| `daylight_climate.write_job` | Direct `write_text`/`write_bytes` | Atomic `save_text`, `save_json`, and `save_bytes` via `safe_io` |
| `radiance._write` | Direct `Path.write_text` in helper | Atomic `save_text` via `safe_io` covers all scenes, points, grids, and reports |
| `cli._design` | Direct `Path.write_text(json.dumps(...))` for markup notes | Atomic `save_json` via `safe_io` |
| `thermal.py` | Direct `write_text`/`open` | Audited: process log redirection requires append mode; scratch IDF and scene files immediately consumed by child processes are listed exceptions |

Legacy extract fields remain compatible. The current extractor still casts Color
channels manually and exports legacy TextNote fields; native typed adapter wiring
remains pending. The complete extract is not changed to a typed envelope. Native lengths retain
Autodesk UnitUtils and the existing millimetre declaration. Generic typed units
and identifiers are tested but complete field adoption is pending. Legacy
`jsonsafe` still stringifies unknown objects; strict `encode` rejects them.

## Phase 2 list

Direct report writers in `revit/`: `build_bedroom.py`, `diag_context.py`,
`dump_mcp_tools.py`, `export_views.py`, `place_families_test.py`, `probe.py`,
`probe_fixture_drop.py`, `probe_fixture_geometry.py`, `probe_product_family.py`,
`probe_villa_inventory.py`. The last two use local cleaning, not atomic writes.
Product-family output still uses `default=str`; its UTF-16 catalogue reader
already decodes bytes explicitly.

Local JSON input readers: `build_bedroom.py`, `build_villa_env.py`,
`build_villa_stairs.py`, `build_villa_option.py`. Raw parameter JSON metadata:
`build_bedroom.py`. Native model/PDF saves in builders, inventory upgrades and
`export_views` need staged native publication and independent acceptance.

Other siblings: generated photometry in `concept/villa_render.py`; Blender reports
in `blender/measure_lux.py`, `blender/villa_scene.py`. (`daylight.py`, `daylight_climate.py`,
`thermal.py`, `radiance.py`, and `cli.py` markup notes migrated in Phase 2 Batch 1).
Dict review callers still own decoding. Audit command/Model Context Protocol loaders
and deploy the shared module with remote workers before expanding.

The retry, stale cache, status-read race, fatal EnergyPlus and untaggable Opening
lessons also require lifecycle/provenance controls. Existing retry promotion,
renderer fingerprints, final status re-read, fatal-log checking and spec_id
matching remain; this phase does not replace or retire them. Integrate per-field
independent model witnesses before closing spec-echo defects. Native IronPython
replacement and read-back must be proven before claiming runtime acceptance.

Canonical `.agents/skills/revit-roundtrip/SKILL.md` could be read but its update
was blocked by the session's read-only `.agents` permission. The intended workflow
update is the operating procedure above; the lead must carry it into that skill.

## Proof and registry

Registry key `serialization-file-boundary-phase1`: shared construction/publication
-> `tests.test_safe_io` -> bridge/file-output stage. `scripts/verify.py` executes
typed round trips, stock-width echo rejection and ribbon shared-publication checks.

Current-source correction (2026-10-05): the first Linux verification found that
the earlier documented CLI/ribbon publication migration was absent. The missing
`write_extract` helper is now implemented with `safe_io.save_json` and the native
serializer, and both actual entry points use it. `tests.test_extract_publication`
executes them with native APIs stubbed, checks exact large identifiers/Unicode,
and preserves the old extract under serialization and flush failures. The three
new regressions failed before correction; the focused publication/boundary/
serializer run passed 24 tests, exit 0. See `extract-publication-migration-missing`
in `docs/LEARNINGS.md` for current full-suite and verification evidence. Historical
ALL PASS records below are not proof of current integration or native acceptance.

50 focused tests passed, exit 0: `tests.test_safe_io`, `tests.test_jsonsafe`,
`tests.test_extract_review`, `tests.test_deliverables`, `tests.test_execution_context`,
`tests.test_villa_scene_provenance`. Frozen data covers byte channels, TextNote
line endings, mis-decoded Arabic/registered-sign text, large identifiers,
zero/off/missing values, interrupted writes, locks and measurement mismatches.
Injected invalid units/types, disk-flush failure and nested writers generalise;
clean records/text and matching measurement stay quiet. `scripts/verify.py`:
ALL PASS, exit 0. No full suite, native authoring, visible output or design approval.

Execution-record integration also passed: `tests.test_pipeline_contracts`, four
tests, exit 0 (54 focused tests total). The expected worker-unavailable negative
case prints `FAIL worker unavailable` while the test process correctly exits 0.
Evidence: `out/serialization-phase1-tests.json` (50-test run),
`out/tests-result.json` (four integration tests), `out/verify-result.json` and
`out/serialization-phase1-verify.log` (final verification).
