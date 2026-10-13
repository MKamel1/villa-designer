# Wardrobes and storage — Stage 2

2026-10-12, branch `codex/storage`. D1 means the current authored villa layout option; no real villa-design gate is approved. The initial worktree was clean and contained no prior storage evidence despite the resume note. No commit was made.

**No new loose storage appearance qualifies for activation.** All four storage fallbacks remain visible; the existing seven measured desks, eight task chairs and parents bed retain their prior activation. All wardrobes, dressing fit-out, kitchen and other built-in joinery remain procedural under the user instruction. The research inventory labels the two kids wardrobes loose; this task applies the user’s stricter wardrobe scope. A scope clarification was offered while work continued; no response was received.

## Inventory, sources and copy

The imported research documents are byte-identical to `origin/codex/search2:docs/storage-candidates.json` and `docs/search2-report.md`. All 32 parent records match the exact current builder context for footprint and authored height: 13 research-classified loose pieces and 19 built-in pieces. Existing desk replacements are preserved rather than reselected. No native Revit extract or specification was edited.

All 14 lead-downloaded `sf_store_*` folders were copied into **new** `/home/omar/archpipe/assets/library/props/` folders. Licence, author, original provenance, buffers and textures are preserved; `model.gltf` is a byte-identical alias of `scene.gltf`. Copy hashes and complete Creative Commons Attribution credits are in `out/storage/stage2/copy-receipt.json`; every intake row carries the full original credit. Jonah is stored for quarantine, not approved use. No credentials were read, printed or copied.

These are render appearances, not manufacturer-certified purchasable products. Timber names describe the listing/appearance; species, finish, hardware travel and structural suitability remain unverified. glTF means Graphics Library Transmission Format; its declared coordinate convention is metres. No target-derived unit conversion was applied.

## Measured candidates and appearance decisions

Dimensions below are **native X extent × native Z extent × vertical extent, in metres**, for the complete retained item. X and Z are the two native horizontal axes; front-facing width/depth are selected from the measured front axis in the intake. Every fit uses one whole-item transform. Width/depth factors must each be 0.5–2.0, with larger/smaller ratio at most 1.15; the independent vertical factor comes from the design height and retained height geometry. The vanity uses its actual desktop, with its mirror still retained.

| Asset suffix / name | Native X × Z × height, m | Decision |
|---|---|---|
| `0999a8a7` / Modern Closet / Wardrobe / Dresser Cabinet | 1.094314 × 0.637504 × 1.997443 | Closed wardrobe measured separately; six complete open-pose meshes omitted. Kids B fit passes (14.279% distortion); all wardrobes kept procedural by user scope. Kids A fails. |
| `20a54670` / Metal Desk | 3.971372 × 6.355819 × 3.035804 | Large metre-coordinate metal desk; all mapped plan factors below 0.5. Worn metal appearance also differs from the current timber desks. |
| `2402ee23` / Wood Desk-Rigged-Animated | 0.982305 × 1.690246 × 1.179421 | Importer bone-display helpers excluded by references. Actual integrated desk/hutch remains one retained item; unresolved desktop/storage-height contract refuses. Existing measured desks retained. |
| `3028ba44` / Mid Century Teak Sideboard Credenza | 393.644066 × 1349.999756 × 637.000206 | Mid-century teak appearance; source coordinates are very large. Declared glTF metres retained. Even a separate millimetre-unit confirmation would leave 28.606% plan distortion for dining. |
| `48bd85b3` / Sala 120ワードローブ OAK | 1.174000 × 0.607000 × 1.900001 | Kids B fit passes (1.425% distortion); kids A fails. Wardrobes kept procedural by user scope. |
| `5577bdb9` / Free Modular TV Cabinet – Mid Century | 1.640296 × 1.479921 × 0.596437 | Diagonal modular floor-standing cabinet; no verified single cardinal front, and source feet do not match floating media design. |
| `62227102` / W1A-Wardrobe (RH) | 255.000000 × 84.000015 × 250.000040 | Additional wardrobe/dressing scene with wall backdrop and oversized coordinates; outside loose-only scope. |
| `65c10ad6` / Mid Century Cabinet | 0.989949 × 0.643180 × 0.714711 | Mid-century timber appearance suits the dining style, but the dining fit requires 73.256% plan distortion, above 15%. |
| `79138881` / Dressing table | 1.500000 × 0.500000 × 1.275000 | Complete desktop sets 0.750 m; mirror retained at 1.275 m. Source plan requires 20.000% distortion for the vanity. Light timber also differs from the current walnut appearance. |
| `9ef2d891` / Walnut Console | 104.139999 × 53.340015 × 73.342515 | Walnut-labelled appearance suits study/lounging palette; oversized undeclared coordinates and floor-supported feet refuse both floating media targets. |
| `ba32c03d` / Bedside table | 19.685040 × 15.749484 × 23.622053 | Round/curved bedside with oversized metre coordinates; factors below 0.5 and 42.844% plan distortion. Does not preserve requested slim walnut/brass appearance. |
| `c5046eb6` / jonah_bedside_table_oak_and_brass | 0.591149 × 0.650168 × 0.697302 | Separate staging platform Object_7 omitted; item fits (3.911% distortion), but search2 flags uncertain re-upload rights. Quarantined, no activation. Oak/brass appearance is not verified walnut. |
| `c5105496` / Modern Wooden Desk with Drawer | 3D Model | 5.317378 × 9.970996 × 5.038239 | Oversized coordinates; source plan factors below 0.5 for every mapped desk. Existing measured desks retained. |
| `f5d363e1` / Columpio 70ワードローブ OAK | 0.800000 × 0.426838 × 1.599739 | Open garment stand rather than a closed wardrobe; extra wardrobe download, outside loose-only scope. |

Measured arithmetic-only exceptions do not authorize integration. The closed AlyStation wardrobe and Sala wardrobe pass the kids B plan/height arithmetic but are excluded by the wardrobe scope. The Jonah bedside passes at width/depth/vertical factors 0.592067, 0.615225 and 0.788754 after its separately measured platform is omitted, but its provenance quarantine remains. Every other complete loose candidate fails fit or mounting. Exact omissions and source hashes are in `intake.json`; fused/uncertain extras never become a fitted stand-in.

## Fixed-room evidence

The exact `authoring_room_context` snapshot supplies layout, specification and furniture; no reconstructed default context is used. `room-review.json` reviews sideboard, both media units, bedside and vanity in their current physical room scopes. The dining sideboard achieves **914 mm where 914 mm is required**. The vanity chair zone achieves **864 mm where 864 mm is required**. Media units and bedside have no standalone access strip in the current catalogue; this does not waive physical body, route, boundary or neighbouring storage checks.

The storage-front card is Time-Saver Standards for Interior Design and Space Planning, second edition, printed page 87: 36 inches, recorded in the existing verified card as 914 mm. This is guidance, not local code compliance. Held originals and the knowledge index are absent on this Linux workstation; the initial book-search command failed at the historical default source path. The existing verified evidence card and source-value regression provide portable evidence; no new original-page verification is claimed.

The baseline preserves **15 inherited body-overlap findings**: lounge cabinet/fluting, bedside/rug, and the procedural vanity chair against the already accepted vanity desk source parts. They are disclosed in full in `room-review.json`, not silently suppressed or repaired by moving design content. No candidate enters the room, so an individual/combined replacement comparison is **not applicable**, not passed. No new Stage-2 activation receipt is published. `activation-readback.json` verifies all 32 inventory sizes and visible storage fallbacks, with no `sf_store_*` model active.

## Previews and diagnosed defects

All fourteen sources received opposing neutral isolated views with a 1.8 m scale figure; true native size is retained. The animated desk was regenerated after excluding importer bone helpers. Neutral previews are diagnostics, not presentation renders, lighting proof, hardware-motion proof or real design approval. The fixed-room images use unchanged existing cameras and recorded neutral fill, with design emission disabled. Storage replacements with closed numerical/provenance gates are never imported through a diagnostic bypass.

Three defects were captured and generalised in `docs/LEARNINGS.md`, registered in `knowledge/furniture-fit-guards.json`, and covered by `tests/test_storage_stage2.py`:

- Importer custom-shape spheres leaked through selection cleanup. Both extraction and preview now remove all object datablocks and exclude actual bone custom-shape references from measured source geometry. The real Blender reproduction shows the old two-sphere leak, seven clean animated-desk meshes and two clean cabinet meshes; renamed helpers and real source meshes with similar names are tested.
- Sideboard review selected a bed clearance card. The additive room-review dispatch now includes sideboards, bookcases and pantry shelving in the existing storage-front card. Real sideboard, renamed storage siblings, clean bed/no-own-clearance cases and a six-millimetre worsening mutation are tested. No dimension or tolerance changed.
- The diagnostic request used the camera room `dining`, but the sideboard belongs to `dining-side`. Requests now derive from exact authored ownership; preview scope validates before rendering and retains the full authored room cluster. The failed image is superseded and excluded from review.

The new workflow is documented in `docs/ops/furniture-fit.md`. The product-library skill was updated and all 38 adapters synchronized. Shared fit arithmetic itself was not edited. The `archpipe.beds` change is limited to one additive storage-type set and its two dispatch uses; parallel kids-bed authoring was not altered.

## Validation

Final execution evidence follows. Portable verification passed with normal and initially empty HOME (the user home-directory environment variable), 186 checks in each run. Source copies and fallback read-back also passed. The supplied interpreter, `PYTHONPATH=src` and `NO_COLOR=1` were used; no package was installed. `assets/user` and `out/villa/round3` were not modified. Full-suite testing and any commit remain with the lead.

Final numerical validation:

- Focused furniture and bed regressions: **109 tests, exit 0**, 544.659 seconds; `out/storage/stage2/focused-tests.log`.
- Latest storage, evidence-card and adapter checks: **18 tests, exit 0**, 5.626 seconds; one original-page reread test skipped because licensed originals are absent. `out/storage/stage2/storage-final-acceptance.log`. The new real-source extremal-face fixture proves the loose sideboard/vanity/bedside refusals and the scope/quarantine arithmetic exceptions.
- Portable verifier, final normal run: **186 PASS checks, exit 0**; `verify-normal-final.log`.
- Portable verifier, final initially empty HOME run: **186 PASS checks, exit 0**; `verify-empty-home-final.log`.
- Actual Blender measurement, leak reproduction and corrected room-preview driver: **exit 0**, with `--python-exit-code 1`. All 28 final source views and twelve corrected room/isolated views were visually inspected and hashed in `preview-review.json`.
- `sync_agent_assets.py --check` and `git diff --check`: **exit 0**.

[Final source contact sheet](../out/storage/stage2/source-contact-sheet-final.jpg) and
[retained-room contact sheet](../out/storage/stage2/retained-room-contact-sheet.jpg)
show the measured/rejected sources and retained furniture. The original fixed
parents day view frames the vanity and excludes the bedside; the supplemental
unchanged existing parents evening view shows the bedside top, with its lower
body screened by the bed. Both limitations are retained in the review receipt.
Room diagnostics omit decorative props, curtains and generated bed cloth;
these images do not replace the full presentation set. Isolated media-unit
images include their authored screen, which is excluded from the storage
height measurement. The procedural models are retained as the existing
fallback, not newly approved for procurement or construction.
