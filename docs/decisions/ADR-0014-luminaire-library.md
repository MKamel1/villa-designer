# ADR-0014: A manufacturer luminaire library. Specs come from the product's own files

- **Status:** accepted
- **Date:** 2026-09-24
- **Relates to:** ADR-0012 (spec photometry joined to the model), ADR-0013
  (faithful renders), the lamp-source fix (emitter, not insertion point)

## Context

The bedroom's fittings were generic Revit families with IES files that ship
with Revit. None of them described a real product, and the pairing was
often wrong: a 594 × 24 mm strip file lit a round drum. The client's photos
are the basis for real purchases, so lighting must be picked from real
products. Each pick must be installed with the product's exact
specification, tested against what the design needs, and replaceable by an
alternate. Europe and MENA are the markets that matter.

## Decision

1. **The EULUMDAT file is the specification.** Per lamp set, an LDT states:
   - flux, colour temperature, CRI and watts;
   - the luminaire's dimensions, luminous area, DFF, LORL and the full
     distribution.

   `archpipe.luminaires.eulumdat` reads it, and nothing is retyped. IES is
   produced from it for Revit, Blender and the lux engine.
2. **Every product is verified before it can be picked** (`library.verify_product`):
   - The distribution integrates to its stated LORL.
   - Where the manufacturer also ships IES, our conversion must agree with
     it in every direction. This caught a 90° axis difference between the
     two formats: IES horizontal h equals EULUMDAT C = h + 90. With that
     correction, Signify's three lamp sets agree within 0.02%.
   - Sanity checks on efficacy, size and colour data.

   A failed product stays out of search results and is never repaired
   silently.
3. **Two layers:**
   - **Catalogue** (`catalogue.sqlite`): everything a manufacturer lists, taken
     from pages its robots.txt allows. It includes market availability read
     from the per-country sites (EG, AE, SA, GB). It is unverified.
   - **Library** (`library.sqlite`): products whose files were imported and
     verified. One row per lamp set. Only these can be picked.
4. **Files arrive through an inbox.** Downloads of any shape go into
   `assets/user/luminaires/inbox/`: zips (nested), LDT, IES, RFA and TXT.
   - The importer identifies them by content, never by extension or server
     content type. Signify serves a zip labelled `application/json`, and
     Revit type catalogues are UTF-16.
   - Manufacturer files are never committed (`assets/user/` is git-ignored).
5. **Install is a spec entry, and it is the only source of truth.** An entry
   reads `product: {manufacturer, sku, lamp_set}`.
   - `install.resolve` derives lumens, watts, kelvin, CRI, the IES file and
     the Revit family from it.
   - A hand-typed value that disagrees is refused.
   - One loader (`install.load_spec`) serves the spec builder, the
     round-trip check and the render input. `photometry.find_ies` resolves
     product IES for every consumer, including the workstation package.
6. **Tested against the design's requirement.** `install.expectations`
   compares the product with what the design asked for: colour
   temperature, minimum CRI, flux range, computed beam, size and efficacy.
   It reports achieved versus required. `check_bedroom` measures the
   emitter from the manufacturer's own geometry.
7. **Unattended Revit.** Manufacturer type catalogues raise modal warnings
   ("The parameter Apparent Load doesn't exist in the Family"), which hung a
   headless run. `revit/unattended.py` answers every dialog, records its
   message and keeps it in the build report.

## Rejected

| Option | Why not |
|---|---|
| Bulk-download the Signify file server | Its `robots.txt` is `Disallow: /` for all agents. The user downloads files in a browser; the tool refuses that host (`verify.py` checks it). |
| ERCO complete archives, fetched by the tool | The download app gates archives behind an interactive content-access step. The user downloads them from the checklist. |
| ieslibrary.com | Paid, with registration. We never create accounts. |
| GLDF now | The format is open, but no manufacturer was found publishing GLDF files publicly. Deferred until one is. The sniffer already recognises the container. |
| A generic "nicer" housing for appearance | Not the specified product (ADR-0013, faithful before beautiful). |
| Trusting the Revit family's photometric parameters | Signify's CoreLine family says 3200 K and 3 W; its LDT says 3000 K and 23 W. The LDT governs, and the build writes its values onto the family. |

## Consequences

- **Picking a product needs its files.** The catalogue says what exists and
  where it's sold. `scripts/luminaires.py links` and `checklist` give the
  links to click, and `import` does the rest.
- **The emitter rule has to know luminous materials.** "Lens" alone missed
  Signify's "Glass, White, High Luminance". The rule is mirrored in
  IronPython scripts, and `verify.py` keeps every copy identical.
- **Recessed products sit in the ceiling void by design.** The check
  reports the recess depth they need as a coordination figure, not a clash.
- **Market availability is family-level.** An individual SKU can still vary
  by market.

## iGuzzini source extension (2026-09-27)

iGuzzini product pages expose LDT and IES links on the same permitted host.
The crawler checks live robots rules before each command, uses a single paced
request stream and caches responses on disk. Product-code inbox folders bind
the photometry to the public product code if an LDT uses an internal number.
The same library flux, paired-file and sanity checks decide whether each
import is pickable. The fetch stops if live robots rules cannot be read.
This extension has only fixture-based verification in the current execution
environment: its connection to `www.iguzzini.com` was refused before
`robots.txt` could be read. No real iGuzzini product was imported or approved.
