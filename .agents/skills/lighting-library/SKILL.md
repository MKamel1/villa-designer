---
name: lighting-library
description: Pick real manufacturer luminaires (Signify/Philips, ERCO, Zumtobel, iGuzzini, ...) for a design, install them with their exact specification, test them against the design's requirement, and swap to alternates. Use whenever lighting is chosen, replaced or questioned.
---

Read [the decision](../../../docs/decisions/ADR-0014-luminaire-library.md)
and the luminaire rows in [lessons](../../../docs/LEARNINGS.md).

**The product's files are the specification.** Lumens, watts, colour
temperature, CRI, dimensions and distribution come from the manufacturer's
EULUMDAT (LDT) file. Never type them into a spec. A spec entry names the
product and the design's position and emitter height:

    - id: LT-01
      at: [2100, 1800]
      mounting_height: 2700          # emitter height, measured back by check_bedroom
      product: {manufacturer: signify, sku: "911401840687", lamp_set: 0}
      requirement: {kelvin: 3000, cri_min: 90, lumens: [600, 1000]}

**Workflow**
1. **State the requirement first:** colour temperature, CRI, flux range,
   beam, size, market. The requirement comes from the design, not from a
   product you already like.
2. **Search the verified library.** Only these rows can be picked:
   `python scripts/luminaires.py search --mount pendant --cct 2700 --cri 90 --lm 600-1000`
   (MCP tool: `search_luminaires`).
3. **If nothing fits, search the catalogue** (unverified; add `--market EG`
   for Egypt): `search --catalogue ...`. Then give the user the files to
   download, with `links <mfr> <sku>` or a `checklist` page. Manufacturer
   file servers that disallow automated access are downloaded by the
   person, never by a tool.
4. **Import:** `python scripts/luminaires.py import`. A product that fails a
   check (flux vs LORL, LDT vs the manufacturer's IES, sanity) is not
   pickable. Report the failure; never repair it.
5. **Install** by writing the `product:` entry, and **test**:
   `scripts/luminaire_demo.py` for a trial in a copy of the room, or the
   design's own pipeline. Report achieved versus required: expectations,
   measured emitter, lux task points.
6. **Swap:** `alternates <mfr> <sku>` lists replacements with the same mount
   and colour temperature, at least the same CRI, and flux within 15%.
   Re-run the same tests; compare in `out/demo/compare.json`.

**Traps already met**
- Content, not names, identifies files. Signify served a zip as
  `application/json`, and Revit type catalogues are UTF-16.
- IES horizontal angle h is EULUMDAT plane C = h + 90. Flux and peak agree
  even when the axis is wrong, so compare every direction.
- A manufacturer's Revit family can carry wrong photometric parameters
  (3200 K and 3 W against an LDT of 3000 K and 23 W). The LDT governs.
- Type catalogues raise modal warnings, and headless Revit hangs on them.
  Import `revit/unattended.py` in any script that loads families.
- A recessed body above the ceiling is the design. Report the recess depth
  it needs; don't fail it.
- Tests write to temporary libraries and IES folders. The product IES
  folder is deployed to the render worker, and `verify.py` rejects strays.
