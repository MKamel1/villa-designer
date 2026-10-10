# Measured furniture fit

Client decision 2026-10-09 applies the beds scaling rule to desks and chairs.
`archpipe.furniture_fit` owns bounds, declared-unit conversion, symmetric
plan distortion and one whole-item fit transform. `archpipe.beds` keeps the
bed-specific mattress, headboard, berth and room checks. Its historical
empty unit-evidence dictionary still means the glTF metre default; new
furniture intake requires valid explicit evidence when any is supplied.
Ordinary and frozen read-only mappings must both work through shared APIs.

1. Inventory authored furniture with `scripts/inventory_desks.py`. It reads
   the existing D1 furnishing data and actual chair dispatch, writes only
   `docs/desks-inventory.json`, and returns JSON-compatible lists. Compare
   the written report with a fresh inventory; do not hand-edit native extracts.
2. Search public listings without a login or token; check robots policies,
   permit CC0 (public domain) or CC-BY (Creative Commons Attribution), and
   write full author/model/licence credit for every CC-BY appearance. Preserve
   search/listing receipts and inspect public thumbnails. Unknown source
   dimensions, mesh separability or physical timber species stay unknown.
   Never label an appearance as a verified buyable product.
3. After the lead downloads: measure actual indexed geometry, declared units
   and up/front axes using existing asset intake. Record a contents review
   with `status: item-only`, a review basis, `extras`, `fused_extras`, and
   `omitted_meshes`. Extras must be separate measured mesh names, all omitted;
   fused extras refuse. Existing bed-only contracts remain compatible.
4. Call `fit_furniture` with complete retained geometry, the fixed design
   footprint, and actual desktop or seat mesh names as `height_parts`.
   `height_basis` is `design` or `citation`; `height_source` names the design
   field or the read publication/edition/page. Authored assumptions remain
   labelled; they do not establish ergonomic verification. Pass every other
   required height through `height_constraints`, including a chair back.
   No part is individually stretched to hit a datum.
5. Width/depth factors after source-unit conversion must each lie in 0.5–2.0.
   Larger divided by smaller minus one must be at most 0.15 (15 percent).
   The vertical factor comes independently from measured height above the
   retained item bottom. A failed fit preserves the design and fallback.
6. Before later activation, verify the imported transform and placement,
   preview with a scale figure and in the unchanged room/camera, get the
   preview reviewed, and run C8 (geometry topology): support, routes, swings,
   overlaps and required access. Stage 1 supplies arithmetic and a shortlist;
   it integrates no replacement and approves no villa-design gate.

Focused regression command uses `scripts/run_tests.py` with
`tests.test_furniture_fit`, `tests.test_beds`, `tests.test_bed_models` and
`tests.test_bed_scaling`. Run `scripts/verify.py --portable` in normal and
empty HOME environments. HOME is the user's home-directory environment
variable; set it only for the requested empty-home verification, never as
a shell scratch variable. Use the supplied interpreter, `PYTHONPATH=src`
and `NO_COLOR=1`, and judge by exit status. Keep failed diagnostic logs.
