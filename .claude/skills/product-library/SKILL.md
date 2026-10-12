---
name: product-library
description: Find, verify and pick finishes, fabrics, furniture, decor, plants (and later sanitary, kitchen, glazing) from the product library; keep buyable products apart from render look-alikes. Use whenever a material or object is chosen, rendered or scheduled.
---

Read [the decision](../../../docs/decisions/ADR-0015-product-library.md).
For luminaires use the `lighting-library` skill; `products/lighting.py`
only presents those rows here.

**Two kinds of record.** A *product* can be bought (manufacturer, range or
SKU, dimensions, performance). An *appearance* can be rendered (PBR
material or 3D model with real size). A render that uses an appearance for a
product says which claim applies: `manufacturer-supplied`,
`scan-of-product` or `look-alike-proxy`. A free texture is a look-alike
unless a link says otherwise. Never present it as the named product.

**Workflow**
1. State the requirement: use, finish, colour and LRV if known, size, slip
   and water exposure, maintenance. Oversample the project's
   `taste.json` styles; don't exclude others.
2. Search the verified layer:
   `python scripts/products.py search --text walnut --category surface`
   (MCP: `search_products`). Add `--all` to see unverified catalogue rows.
3. To verify more items, add them to the pilot list or the next batch and
   run `python scripts/products.py pilot` (workstation). A check is
   `passed`, `failed` or `not_checkable`. Report all three; a
   `not_checkable` is never counted as a pass.
4. Record the product (primary and alternate from different ranges) and the
   appearance used to render it, with the claim.

**Traps already met**
- Map roles come from the source's file API, not file names. Poly Haven's
  leather base map is `_albedo_`, not `_diff_`.
- A published number with an unknown definition verifies nothing. Poly
  Haven's polycount can describe the base mesh or the subdivided export.
- An asset can disagree with its own metadata (desk_lamp_arm_01). Report it;
  never repair it.
- Colour space is checked by physics: under a uniform white environment a
  diffuse swatch renders at its albedo. The Non-Color negative control must
  keep failing.


**Measured furniture fitting and replacement (2026-10-09).** Follow
[the fit workflow](../../../docs/ops/furniture-fit.md). Copy downloaded
appearances into new shared-library folders with complete licence/credits;
measure declared units, actual mesh bounds, facing and complete item contents.
Plan factors must each be 0.5–2.0 with a larger/smaller factor ratio no greater
than 1.15. Fit the whole item; identify a complete desktop or seat datum and
check every independently required height under the same vertical factor.
A plan pass cannot approve an unresolved seat/back or a fused extra. For
separable platforms or bundles, record exact retained/omitted identities and
measure each complete retained item independently; a prose omission is not
a measurement receipt.

Use the scene builder's deep-copied `authoring_room_context`, not inputs
reconstructed under another revision. Compare the current procedural item
and model through identical room/card checks using `baseline_relative_review`:
access loss at most five millimetres per side; no bigger boundary overrun or
new route, swing, storage-front or fixed-element body conflict. Preserve
inherited layout findings. Review both individual and combined replacements,
then isolated and unchanged-camera neutral images before integration. Bind
accepted geometry, contents, transforms, physical inputs and reviewed camera
identities. Actual changes refuse; omitted numerical view selections remain
valid subsets. Bind architectural faces/materials and stable physical host
fields independently of generated shell buckets and doorway captions. Test
actual full/empty-view exports; geometry, material, visibility and finish-host
mutations must still refuse. Replace exact body identifiers, preserving derived chairs and
physical procedural fallbacks. Missing source geometry restores those bodies.
