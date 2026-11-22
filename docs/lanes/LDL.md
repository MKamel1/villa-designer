# LDL: landscape plant library (2026-11-22)

Lane output for the landscape method (`docs/quality/LANDSCAPE-METHOD.md`, stage LD-L) and the garden brief
(`docs/decisions/garden-brief-2026-11-22.md`). Data in `knowledge/landscape/plants/`, code in
`src/archpipe/landscape/plants/`, tests in `tests/landscape/plants/`.

## What is here

| file | content |
|---|---|
| `knowledge/landscape/plants/species/<slug>.json` | one source record per species (78): the editable truth |
| `knowledge/landscape/plants/plants.json` | **generated** (`python -m archpipe.landscape.plants.library`): all records + derived `site_viability` + `quote_check`; never hand-edit |
| `knowledge/landscape/plants/assets.json` | 37 graded 3D assets, a drawable table for every species, free candidates for the gaps |
| `knowledge/landscape/plants/asset-previews/<id>.jpg` | turntable sheets: top row camera at 5 m, bottom at 15 m, azimuth 0/90/180/270 |
| `knowledge/landscape/plants/quote-verification.json` | result of re-fetching every cited page and matching each quote |
| `library.py` / `assets.py` / `verify_quotes.py` / `asset_preview.py` | validator + viability, asset-table validator, quote re-check, Blender preview script |

## Schema (per species file)

`slug`, `layers` (subset of canopy_tree, small_fruit_tree, palm, screen_hedge, climber, flowering_shrub, perennial,
groundcover_lawn, grass, tropical_foliage, aquatic_marginal, herb; our classification), `pond_relevant` (bool) and
`attributes`. Required attributes (`library.REQUIRED`): accepted_name, height_m, spread_m, growth_rate, sun, water
(hydrozone), heat, drought, alkaline_soil, salt, frost, flowering, foliage, root_behaviour, toxicity_people,
toxicity_fish, litter, maintenance, egypt_availability.

Each attribute is one of:

* `SOURCED`: `value` (enum-checked) plus `source` {`source_id`, `url` (https, or `held:<book>`), `accessed` (ISO date), `locator` or `quote` (<= 400 chars, verbatim)}.
* `GAP`: `reason` plus `searched` (what was opened or tried). Valid, and never filled.
* `NA`: only `toxicity_fish` of a species that is not pond-relevant, with a reason.
* `POLICY`: only `egypt_availability` = "unknown — supplier check". No citable source for Egyptian nurseries was found, so every species carries this; the validator refuses any other availability text unless a non-book source is cited.

A species with a missing attribute, a SOURCED attribute without a complete source, a bad enum or a bare value fails (`load_species` raises). Extra
unvalidated keys are allowed (`notes`, `uses`, `invasive_flag`, `toxicity_pets`).

## Climate used (stated, not assumed)

* Weather file: `EGY_QH_Cairo.West.AP.623680_TMYx.epw` (the project's weather station; ADR-0017). It is a *typical* year, not extremes: minimum dry bulb **5.1 C**, maximum **43.9 C**, **154 days** with daily maximum above 30 C, 17 hours at or above 40 C, **15 mm** rain a year (everything is irrigated), no hour at or below 0 C. Computed from the file in this lane.
* **Coordinates are placeholders.** `villa_env` holds 30.040 N, 30.961 E from the BRIEF maps link; the station is at 30.117 N, 30.917 E, 151 m. Results are labelled accordingly in `plants.json` (`site_climate.coordinates_status`).
* Soil pH and irrigation-water salinity are **not measured**. Alkaline-soil and salt tolerance are therefore reported but cannot pass or fail a species.

## Site viability (derived; our policy thresholds, not a published standard)

`site_viability(record)` per factor (frost, heat, alkaline soil): pass / conditional / fail / unknown.
Frost: hardy to 0 C or lower passes (the 0 C floor is our policy margin below the 5.1 C typical-year minimum, because a typical year hides cold nights); hardy only to 0 .. 5.1 C is conditional; needs warmer than 5.1 C fails. USDA zone letters convert at 5 F per half zone from 10a = -1.1 C. Heat: class low fails, moderate is conditional. Alkaline soil: intolerant is conditional. Verdict: any fail = not_viable; else any conditional = viable_with_conditions; else any unknown = **unverified** (a GAP is never read as a pass); else viable.

Result: **11 viable, 13 viable with conditions, 2 not viable, 52 unverified**. The 52 are not rejected; their *heat tolerance is a GAP* (see below).

## Counts and sources

* 78 species, 12 layers all covered (the brief's layers: canopy 6, small/fruit trees 9, palms 3, screens 9, climbers 7, flowering shrubs 8, perennials 5, grasses 3, groundcover/lawn 8, tropical/Japanese foliage 13, aquatic/marginal 8, herbs 9; a species may carry two layers).
* 1485 attribute slots: **1029 SOURCED, 456 GAP** (31 %), plus NA/POLICY slots.
* Sources actually opened: NC State Extension Plant Toolbox (593 attributes), GBIF API for accepted names (78), PFAF (64), UF/IFAS (39), Wikipedia (33; used only where nothing better opened, and always visible as `source_id` Wikipedia), Tropical Plants Database (31), RHS (24), UC-ANR (14), ASU, Clemson, NParks, ASPCA, UNF (few). **Held book:** Time-Saver Standards (Harris & Dines, 2nd ed. 1997) section 550. It names none of the species' size, water or sun data; it was checked for Table 550-3 (poisonous plants), 550-4 (invasives), 550-7 (salt-tolerant plants) and 550-1 (crown density), and its findings are cited in `notes` where a species is named (lantana, bamboo, Cynodon). The held "dry-climate planting guide" is the xeriscape guidance on printed pp. 333-335 of that section and carries principles (match plant to site, irrigate deep and rarely, no turf in narrow areas, saline soils) and no per-species data, so it supplied no attribute values. The page labels of this scan are unreliable (basis: "UNRELIABLE... verify printed page from the image"); the printed pages quoted here were read off the extracted headers and should be confirmed from the page image before any quantitative use.
* Not usable from this machine: POWO/Kew (HTTP 403), Missouri Botanical Garden (certificate error), RHS plant pages without an ID, EDIS (redirect loops). Accepted names come from the GBIF API instead of POWO; where GBIF treats the listed name as a synonym the accepted name is recorded and the slug kept: Citrus x sinensis -> *Citrus x aurantium*, Eriobotrya japonica -> *Rhaphiolepis bibas*, Rosmarinus officinalis -> *Salvia rosmarinus*, Nymphaea caerulea -> *Nymphaea nouchali*, Cyperus involucratus -> *Cyperus alternifolius* subsp. *flabelliformis*, Pennisetum alopecuroides -> *Cenchrus alopecuroides*.
* Quote re-check (`verify_quotes`): the pages were fetched again and every SOURCED quote matched as a substring: **794 verified, 78 API-derived (GBIF fields, not page text), 9 not matched, 14 page unreachable (UF/IFAS FP181 PDF redirect loop)**. The 9 not matched are stitched or paraphrased quotes (for example Murraya frost joins two sentences); they stay flagged `quote_check: quote_not_found` in `plants.json` and a test caps them at 2 %. Subagent note: seven of nine research agents read pages through a summarising fetch tool, so the re-check above is the real verification.

## GAPS (listed, never filled)

Count of GAP slots across the 78 species: litter 70, root behaviour 65, **heat tolerance 54**, toxicity to people 50, salt 43, alkaline soil 30, drought 27, maintenance 23, **toxicity to fish 22 (every pond-relevant species)**, spread 15, growth rate 13, water 12, frost 8, flowering 8, height 7, foliage 5, sun 4. Egyptian availability: unknown for all 78 (supplier check).
Nothing states fish toxicity for any pond plant; a koi-keeper or pond-supplier source is needed. Heat tolerance is rarely stated by the extension sources; Missouri Botanical Garden's AHS heat zones would close most of this but MBG could not be opened. Pet toxicity (ASPCA, NC State tags) was not accepted as human toxicity.

## Brief items put at risk by the findings

1. **Ixora coccinea (existing garden palette) is frost-tender for this site**: NC State gives a 10 C minimum against a 5.1 C typical-year minimum, so it computes as not viable; Plumeria rubra (frangipani, client standing decision) is conditional (hardy only to 1.7 C per UF/IFAS) and Petrea volubilis (existing palette) is conditional (1.7 C). Frangipani needs the client's explicit waiver and a note of winter protection.
2. **Privacy screening**: only *Cupressus sempervirens*, *Dodonaea viscosa* and *Pittosporum tobira* compute fully viable. Oleander (the strongest hot-dry screen) is **highly toxic** and sits beside a children's/gathering garden; *Murraya* needs frost care (conditional) and is flagged invasive by two sources; bamboo (*Bambusa multiplex*) has no heat or alkaline data.
3. **Alkaline soil** (untested): sources call these intolerant: *Bougainvillea glabra*, *Callistemon citrinus*, *Delonix regia*, *Ficus carica*, *Ixora coccinea*, *Tipuana tipu*. Both client-favoured shade trees (poinciana, tipu) are in this list. A soil test comes before specifying them.
4. **Toxic to people** per the sources opened: oleander (highly), lantana, nandina, plumbago, Strelitzia nicolai, star jasmine, calla lily. 50 species have no stated human toxicity at all, which is not evidence of safety (Time-Saver 550-3 is explicit that brightly coloured poisonous plants stay out of reach of children).
5. **Pond planting**: no fish-toxicity statement exists for any of the 22 pond-relevant species, and the lush tropical layer leans on species whose heat/alkaline data are GAPs. Leaf litter into the pond is stated for few species.
6. **Drawability**: only 5 of 78 species have a grade A/B asset of the right species or genus, plus 1 genus stand-in (below). The Japanese/tropical pond garden, the screens and all drift plants cannot be drawn faithfully yet.

## 3D asset grading (what was looked at)

Rubric (our policy): A real modelled leaves, no card planes at 5 m, recognisable silhouette at 5 and 15 m; B reads as the plant at 5 and 15 m, cards allowed only if no fishbone or flat planes show, no faceting; C fails at 5 m (faceted, sparse, flat, wrong scale or foliage) or too small to read at 15 m; D broken, mis-scaled, untextured, a nursery pot on a plane. Candidates: every plant-like asset in `~/archpipe/assets/library/props` (33) and four Sketchfab plants from `~/archpipe/library/sketchfab` (37 in all). Each was rendered (Cycles, 35 mm lens, eye 1.6 m, camera at 5 m and 15 m, 4 azimuths; `jobq` job ids `ldl-prev-cpu2`, `ldl-prev-cpu3`; the first GPU job sat queued behind other lanes so these two ran on CPU) and viewed. Result: 4 A, 10 B, 19 C, 4 D.

Drawable: `jacaranda_mimosifolia` (sf_jacaranda, A), `delonix_regia` (sf_royal_poinciana, A), `plumeria_rubra` (sf_frangipani, A, genus level), `citrus_limon` (sf_lemon_tree, A), `ixora_coccinea` (sf_ixora, B; but not viable on site), and `citrus_x_sinensis` only as a *genus stand-in* (lemon for orange, fruit colour wrong; lead decision needed). **Not drawable yet: 72 species**, including those whose only asset failed: olive (faceted trunk base), bougainvillea (a nursery pot on a plane), hibiscus (sparse), bottlebrush (small, sparse), lavender (illustrated, 3.9 m tall), gazania (correct species but a 0.3 m scatter asset; may reach B when instanced in drifts, to be tested not assumed), Monstera (on a mid-century stand). The Poly Haven "jacaranda_tree" is *not* a jacaranda (broad lobed leaves, 3.86 M triangles). The banana-palm Sketchfab model renders solid white (no textures).
For each undrawable species `assets.json` lists up to 3 **free candidates** (CC Attribution or CC0 per the public Sketchfab search API, downloadable, name contains the genus or common name): 38 of the 72 have at least one. They are ungraded and unpreviewed, and the licence label must be rechecked at download. The Sketchfab "Realistic HD ..." series by PlantCatalog (the author of the jacaranda, poinciana, frangipani and lemon assets that passed) has fan palm, date palm, fig, hibiscus, rosemary and rooibos models, so the next step is to preview those first. No species in the Japanese-garden set (Fatsia, Nandina, Acorus, Farfugium, Rhapis) or the aquatic set has a graded candidate beyond a few ungraded CC "Japanese plant" scans (heavy: 0.4-2.3 M tris). Nothing was bought or downloaded.

## Decisions taken (no human available)

1. Species list: 78 chosen from the brief's layers, Egypt-common and heat-viable plants, the existing palette and client standing decisions (frangipani, terracotta-pot plants). Brief-adjacent species dropped for time: Bauhinia, mango, Washingtonia, Vitex, Duranta, Quisqualis, Tecomaria, Leucophyllum, Cycas, Musa, Miscanthus, Pelargonium, Salvia officinalis, Ligustrum. They are not "rejected", just not researched.
2. Sources: extension services and the open botanical sites that opened, over a perfect-source list; Wikipedia and PFAF were allowed when nothing better opened and are visible per attribute.
3. Viability thresholds, hydrozone mapping and the asset rubric are labelled as our policy.
4. `egypt_availability` is POLICY "unknown — supplier check" everywhere: no citable Egyptian nursery source was found.
5. Quote re-check is automatic and published, not hidden: failing quotes are flagged and not silently dropped.

## Open items

* Close the heat-tolerance GAP (54) with MBG AHS heat zones or a Gulf/Arizona extension page; close fish toxicity with a pond-supplier source; get the Egyptian supplier list.
* Soil pH and irrigation-water salinity measurements (site analysis lane / soil test) to turn the alkaline and salt columns into pass/fail.
* Preview and grade the free candidates (a short jobq batch), starting with the Japanese-garden, screen and palm species; then re-run `assets.json`.
* Confirm Time-Saver printed page numbers from the page image.
* Decide the Citrus stand-in and the frangipani/ixora waivers with the client.
* The research subagents used pages as they read them; a second, independent re-fetch of all `quote_check: verified` quotes after a month would catch silent page changes (`python -m archpipe.landscape.plants.verify_quotes --write`).

## Commands

```
PYTHONPATH=src python -m archpipe.landscape.plants.library            # validate all species, rebuild plants.json
PYTHONPATH=src python -m archpipe.landscape.plants.library f.json     # validate one record
PYTHONPATH=src python -m archpipe.landscape.plants.verify_quotes --write
PYTHONPATH=src python -m pytest tests/landscape -q
```
