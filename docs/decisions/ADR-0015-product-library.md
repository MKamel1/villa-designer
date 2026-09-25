# ADR-0015: Product library for every category

**Status:** accepted, 2026-09-24. Extends [ADR-0014](ADR-0014-luminaire-library.md).

## Context

The client wants a large library to design from: finishes, fabrics,
furniture, decor, plants, sanitary, kitchens and glazing, not only
luminaires. The client's references are to be **oversampled**, not treated
as rules. Egypt lacks product data, so the design states intent and the
closest local match is found at procurement. Paid 3D and texture libraries
are out; free ones with accounts are in, with the user doing any downloads
that need an account.

## Decision

1. **Two kinds of record, kept apart** (`archpipe.products`):
   - A *product* is something that can be bought, with a manufacturer, SKU
     or range, dimensions and performance.
   - An *appearance* is something that can be rendered: a PBR material or a
     3D model with its real-world size.

   A link between them carries a claim: `manufacturer-supplied`,
   `scan-of-product` or `look-alike-proxy`. A free marble texture never
   passes silently as "Brand X Calacatta"; the render states the claim.
2. **Two layers, as for luminaires.** The *catalogue* holds everything a
   source lists and is unverified. *Verified* items have files that passed
   every computable check. Each check is recorded as `passed`, `failed` or
   `not_checkable`:
   - an item is verified only with at least one pass and no failure;
   - `not_checkable` is never a pass;
   - a refresh never demotes a verified or failed item.
3. **Sources first where they are open.** Poly Haven (API, CC0, md5 per
   file, real size in mm) and ambientCG (API, CC0, size per file, real size
   in cm) are indexed in full. Manufacturer catalogues come next. A
   reachability probe (2026-09-24) recorded:
   - pages that allow tools: Caesarstone, Florim, Duravit, Grohe, Hansgrohe,
     Schüco, Reynaers, ERCO, iGuzzini, Louis Poulsen, Delta Light, Flos,
     HAY, &Tradition;
   - refused: Vitra (403), Little Greene (403); rate-limited: Atlas Concorde
     (429); tool access disallowed in robots.txt: Klus;
   - these become click-lists.
4. **Files live on the workstation** (`~/archpipe/library/`). The index
   lives on the laptop (`assets/user/products/index.sqlite`, git-ignored).
5. **The luminaire library is unchanged.** `products/lighting.py` is a
   read-only adapter. Its tests, the verify guards and the MCP tools pass
   unchanged.

## Checks (pilot, `scripts/products.py pilot`)

| Check | Computed how | Independent of |
|---|---|---|
| download_integrity | md5 (Poly Haven) or size (ambientCG) published by the source | our download |
| maps_complete | base, roughness and normal present; role taken from the source's file API | file names |
| albedo_physical_range | mean linear luminance of the base map, Pillow sRGB decode, in 0.02–0.90 | Blender |
| swatch_albedo_match | Cycles render of a 1 m plane under a uniform white environment (a diffuse surface returns its albedo). Must fall in [0.90·a, 1.10·a + 0.08] | the Pillow decode |
| dimensions_match | glTF bounding box vs published dimensions, sorted, 3 % | the published figure |
| textures_resolved, units_scale_sane | import in Blender 4.5 | none |
| real_size_declared | tile size published? If not, not_checkable | none |
| polycount | not_checkable: Poly Haven does not say whether its count is the base or the exported mesh | none |
| product_link | not_checkable for free appearances: a look-alike-proxy until linked | none |

## Pilot result (2026-09-24)

- **Verified: 19 of 20.** They cover walnut and oak veneer, marble ×2,
  travertine, onyx, grey stone, clay plaster, microcement-like concrete,
  bouclé, linen, leather, velvet, terrazzo, two vases, a plant, a sofa and a
  bar chair. Albedo against rendered values, for example: walnut 0.159 →
  0.190, bouclé 0.208 → 0.227, Marble004 0.741 → 0.749.
- **Failed: desk_lamp_arm_01.** Its bounding box is 202 × 614 × 893 mm
  against a published 408 × 617 × 879. The asset does not match its
  metadata, probably because the arm is posed differently. It is reported,
  not repaired.
- **Negative control caught.** marble_01 with its base colour read as
  Non-Color renders at 0.637, against an expected window of
  [0.315, 0.465], and fails.
- **Two defects found in my own checks and fixed, not waved through.**
  - brown_leather "failed" because its base map is named `_albedo_`. The
    source's role label now wins over file names.
  - ceramic_vase_01 "failed" polycount, 10 296 triangles against 2 548
    published: the imported mesh is subdivided and its size matches. A
    count with an unknown definition verifies nothing, so polycount is
    `not_checkable`, with both numbers recorded.

## Next

- Manufacturer product indexes, starting with what the brief needs most:
  - lighting: LED profiles and strips in diffuser channels; matte-black and
    brushed-brass pendants and sconces; wall-grazing;
  - surfaces: large-format stone and quartz, travertine, walnut veneer;
  - sanitary: wall-hung WC, basins, brushed-brass fittings.
- Paint LRV/LAB where the brand publishes it.
- Glazing U/g/VT from IGDB, which needs a free account.
- Deep verified core of 300–500 items.

## Fab / Quixel Megascans (2026-09-24)

- **Claimed (client-approved):** 111 free Megascans items were added to the
  client's Fab library under the **$0 Professional licence**, which suits
  commercial client work. Twelve models whose Professional licence costs
  $28–42 were skipped; only a $0 offer is ever claimed.
- **Downloaded:** 96 materials, 2K and 4K, 191 files, 9.2 GB, in
  `~/archpipe/library/fab/<material>/`.
  - Each file's size was checked against Fab's own listing.
  - Signed links expire after 5 minutes, and the CDN sometimes stalls a
    connection. The helper therefore runs at most 3 downloads at once and
    abandons any transfer slower than 20 kB/s for 60 s.
  - The 35 failed files were retried with fresh links, and all arrived.
- **Chrome blocks scripted multi-file downloads** (its automatic-download
  protection). Browser settings were not changed. The browser only
  requested the signed links; the workstation downloaded the files.
- **Verified: 94 of 96.** Each zip carries Megascans' own JSON, with the
  scan area (real-world size) and the colour calibration (GretagMacbeth
  ColorChecker).
  - Black suede and studded leather fail `albedo_physical_range`, with
    means of 0.010 and 0.006.
  - That range's lower bound (0.02) is a generic PBR rule of thumb, not a
    verified source. The two stay failed and flagged; the threshold is not
    loosened to pass them.
- **Search:** `python scripts/products.py search --text marble` (MCP
  `search_products`).

## Sketchfab and 3D Warehouse

- **Sketchfab:** 173 furniture, lighting, bath, decor and plant models were
  shortlisted, CC0 or CC-BY only (NonCommercial and NoDerivatives are
  excluded). The browser tool refuses to return signed links, so downloads
  use the official Data API with the client's own API token. The client
  stores the token in `~/.config/archpipe/sketchfab.env` on the workstation,
  and it is never seen or logged. `library/sketchfab/get.py` re-checks each
  licence before downloading and writes the CC-BY attribution to
  `meta.json`.
- **3D Warehouse:** the browser tool blocks its data responses because they
  carry session cookies, so there is no automated route. Use a click-list
  with manual downloads, or rely on BIMobject, whose manufacturers publish
  official Revit families.
