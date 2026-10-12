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
   required height through `height_constraints`, for other exact design heights. Lead decision 2026-10-11 changes task-chair back height: derive the vertical factor from the design seat height, label it ASSUMED where applicable, and use a cited `back_height_range` measured above the seat. Back height follows the source under that factor. Report overall top and above-seat rise; do not force the old assumed back top. No part is individually stretched to hit a datum.
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

Stage 2 (2026-10-09): `scripts/prepare_desks_stage2.py` measures the seventeen
lead-downloaded assets from immutable indexed geometry and source hashes.
`furniture_fitting` stores one whole-item transform; `height_parts` must
identify complete desktop or seat geometry. Every separately required back
height still uses that same vertical factor. A footprint pass never admits
an unresolved seat or fused extra. Source credits accompany the library copy
and `out/desks/stage2/credits.md`; the accepted geometries are appearance
proxies, not verified buyable products.

Use `villa_render.build`'s deep-copied `authoring_room_context` for the exact
layout, specification and furniture reviewed; do not reconstruct them under
different revision/default contexts. Compare the same procedural versus model
room scope with `bed_room_review(..., target_marks=..., absolute=True)` and
`baseline_relative_review`. Retain all inherited layout findings. Each access
side must achieve at least its baseline minus 0.005 m (five millimetres,
client decision); no new route, swing, storage-front failure or fixed-element
body conflict is permitted. Boundary overrun may not exceed baseline. Check
both individual replacements and their combined scene.

The active Stage-2 receipt is `knowledge/furniture-stage2.json.gz`, generated
only after isolated and unchanged-room neutral images have been inspected.
It carries exact source faces, three source geometries shared by seven desk
instances, complete credits, reviewed image hashes, actual import error and
selection-bound fit/room records. `furniture_stage2.apply` validates the live
physical context and each supplied reviewed camera before activation. Cold
and cached override **explanations** are not physical inputs; all actual
furniture values remain bound. A numerical build requesting no views is a
valid view subset, not an edited camera. Architectural binding compares each
physical face/material and stable host fields, independent of numbered export
buckets and doorway captions. Exact geometry, winding, materials, visibility
and finish-host data still invalidate a receipt; generated bucket renaming
does not. Test actual full/empty-view exports, not only an edited view list.

Record exact `replacement_mesh_ids`: a desk prefix also contains its derived
chair names. Only the desk's own body may hide/delete. Derived task chairs
remain independent physical fallbacks. Missing source files restore the
exact procedural body at runtime. Normal imports require accepted review;
pending review is admitted only for explicit neutral diagnostics. Never add
a production bypass to make a pending receipt load.

2026-10-11 source-cover/chair package: `prepare_furniture_oct11.py`, `review_furniture_oct11.py`, `preview_chairs_supplemental.py` and `accept_furniture_oct11.py`. Review against the current measured desks, not merely the former procedural desk geometry. Resolve derived chair identifiers and exact fallback floor from their authored bodies; keep parent desk access cards, with the chair planning body excluded only from its own intended use zone. Retain all physical faces in support/routes/overlap/boundary checks. Namespace every imported glTF hierarchy object, including empty nodes. Supplemental diagnostic angles bind actual full-frame chair vertices and preserve original named cameras. Source geometry and CC-BY credits remain in portable receipts; other candidates and the vanity retain fallbacks.

Every Blender diagnostic command must set `--python-exit-code 1`; inspect the final evidence and image bindings as well as process status. Independent fitted models are audited through their active `scale_xyz`, with a manifest `placement_scale_source`; dormant candidate metadata must be completed before activation.
