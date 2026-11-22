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
* 1482 required attribute slots (78 x 19): **892 SOURCED, 456 GAP** (31 %), 56 NA (fish toxicity of non-pond species), 78 POLICY (Egyptian availability).
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
For each undrawable species `assets.json` lists up to 3 **free candidates** (CC Attribution or CC0 per the public Sketchfab search API, downloadable, name contains the genus or common name): 36 of the 72 have at least one. They are ungraded and unpreviewed, and the licence label must be rechecked at download. The Sketchfab "Realistic HD ..." series by PlantCatalog (the author of the jacaranda, poinciana, frangipani and lemon assets that passed) has fan palm, date palm, fig, hibiscus, rosemary and rooibos models, so the next step is to preview those first. No species in the Japanese-garden set (Fatsia, Nandina, Acorus, Farfugium, Rhapis) or the aquatic set has a graded candidate beyond a few ungraded CC "Japanese plant" scans (heavy: 0.4-2.3 M tris). Nothing was bought or downloaded.

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


## Pass 2 (2026-11-22): hot-arid evidence, viability decisions, assets

Full tables: `docs/lanes/LDL-assets-shortfall.md` (free shortfall per species, paid options). Counts from `python src/archpipe/landscape/plants/tools/stats.py`.

### Gaps before -> after (required-attribute slots; 78 species -> 77 after Ixora was dropped)

| attribute | before | after |
|---|---|---|
| heat | 54 | **35** |
| litter | 70 | 46 |
| root behaviour | 65 | 45 |
| toxicity to people | 50 | 42 |
| salt | 43 | 32 |
| alkaline soil | 30 | 22 |
| drought | 27 | 25 |
| toxicity to fish | 22 | 22 (see below) |
| all others | unchanged | unchanged |
| total GAP slots | 456 | **364** |

Viability: 11 viable / 13 conditional / 2 not viable / 52 unverified -> **19 / 20 / 1 / 37** (the 1 is *Nassella tenuissima*, low heat tolerance; Ixora left the library). Sources opened this pass:
SelecTree (Cal Poly) JSON API (62 attributes, 25 trees), the Southern Nevada Regional Plant List June 2026 (12 heat), AMWUA *Landscape Plants for the Arizona Desert* (1 heat; 206 plant pages crawled, 13 of our species matched), Missouri Botanical Garden Plant Finder (6). Wikipedia attributes **33 -> 31** (the replaced ones were not in any new source; the remaining 31 are mostly height, sun, water, flowering, foliage; 4 frost, 1 heat, 1 alkaline, 1 human toxicity).
Quote re-check: 870 verified, 77 API-derived, 9 not matched (all older, stitched quotes), 14 page unreachable.

* **MBG certificate**: the server omits its GeoTrust intermediate. Verification stays ON: bundle = system roots + the intermediate fetched from the certificate's own AIA URL (`~/archpipe/shared/assets/user/landscape/ca-bundle-mbg.pem`; `verify_quotes` uses it for mobot.org hosts). MBG yields zone, "Tolerate" lists and prose; it does **not** publish AHS heat zones, so it closed only 6 heat attributes.
* **Heat inference, flagged**: 12 of the 19 new heat values are **inferences from inclusion** in a hot-desert list (Las Vegas / Phoenix) when the source states no heat tolerance in words; they carry `inferred: true` and an `INFERENCE` text, class high only if our own sun attribute includes full sun, otherwise moderate. A tree rated 3+ stars in the Las Vegas list is the one case where the source says in words that it is well adapted to desert heat. Test `test_inferred_heat_is_always_flagged_as_inference`.
* **Not reachable / no species data**: Earth-Kind plant selector (JavaScript app, no data URL found), Abu Dhabi Public Realm Design Manual and Dubai Municipality Greenery and Plantation Manual 2026 (no species list found by search; the Abu Dhabi 2009 guideline is on SlideShare, headings only), ADWR Phoenix list and Tucson plants book (HTTP 403), Arizona Extension az1153/az1876/az1673/az1100a (downloaded; they name 5 of our species and give no per-species heat data), Cal Poly SelecTree (done), `wucol` (no response).
* **Fish toxicity**: no fish-toxicity statement exists for any of the 22 pond species. The Midwest Pond and Koi Society list (`mpks.org/poisonous-plants`, read) names none of them; it names **Plumeria** and **Lantana** (placement-carefully), recorded as `koi_pond_note` on those two. Absence from a koi-society list is not evidence of safety, so the 22 stay GAP and `placement_constraints` says "not beside the koi pond until sourced". Garden Gate (a magazine) and retail pages were not accepted as sources.
* **Placement constraints (derived, `plants.json`)**: toxic to people (oleander, lantana, nandina, plumbago, Strelitzia nicolai, star jasmine, calla): "away from seating and edibles"; no children or pets in the brief.
* **Decisions applied**: frangipani VIABLE via `lead_decisions` (frost accepted, winter-cold note with the 1.7 C figure; only a *conditional* factor can be accepted, a fail never is); Ixora removed from the species set and recorded in `rejected.json`; **`knowledge/garden-palette.json`, `site-orientation.json`, `src/archpipe/concept/villa_landscape.py` and others still name Ixora: not my files, lead to align**; alkaline-intolerant species read "conditional on soil test (a professional item)".

### Assets

* **Blocker**: no Sketchfab API token on this machine (`sketchfab-api.txt` absent; the download endpoint returns 401), so none of the Sketchfab candidates could be downloaded. `sketchfab-candidates.json` lists downloadable CC0/CC-BY models for **44 of 77 species** (21 name the species) by public search; ungraded. **Unblock: create a free Sketchfab account token and save it as `sketchfab-api.txt` at the repo root of the lead checkout** (`ops/workstation/fetch_sketchfab.py` already does licence re-reading, front-axis checks and provenance).
* Downloaded instead: 21 Poly Haven (CC0) 1k glTF models into `~/archpipe/shared/assets/user/landscape/polyhaven/` (not in git); `asset-manifest.json` pins every file by sha256 and URL. All 20 new sheets were rendered through `jobq` (CPU) and looked at; plus a **drift test** (`drift_preview.py`: instanced scatter at 5 m and 15 m) for gazania, bermuda grass and periwinkle.
* Result: of 20, 0 A, 4 B (two olive-like island trees, a Burkea tree, a Searsia shrub, all **look-alikes with no palette species**), 1 B-by-drift (Gazania), 12 C, 1 D. **Drawable species 5 -> 5** (+1 genus stand-in): Ixora left (dropped), Gazania joined (drift use, patches 6 m and wider). The shortfall is real and is the Sketchfab token plus paid libraries.
* **Misnamed jacaranda**: the library prop `jacaranda_tree` (Poly Haven) is a broad-lobed-leaf tree; it now carries `misnamed_as` and the validator forces look-alike/none with no mapping. The real jacaranda is `sf_jacaranda`. The prop name itself lives in the shared library and was not renamed (other lanes may reference it).
* **White banana**: cause measured, not guessed: the glTF has **no images or textures and no baseColorFactor**, so every material falls back to default white; it is also not a banana (Ravenala and banana-leaf in pots). Not fixable from this file. Guard: `gltf_untextured_share` plus validator rule (untextured share > 0.5 caps the grade at D) and tests against the real file.
* Licence rule: only CC0 / CC Attribution count as free; validated.

### Tests

`tests/landscape`: 136 passed (pass 2 added lead-decision, placement, decision and asset-guard tests); lane suite (landscape, luminaires, compliance, design, model, electrical, lightcalc, lightverify, critic, ops, documents, drawings2d, pipeline, exchange, approvals, parity, markup, villa_render*): 825 passed, 6 skipped. New: lead decisions (positive, never rescues a fail, needs reason), placement constraints, Ixora dropped, frangipani accepted, inferred-heat flag, misnamed asset, untextured asset (positive on the real banana file, negative on a textured one), licence, manifest sha256 (and live hash check when the store exists).

### Open items (pass 2)

* Sketchfab token; then run `tools/sketchfab_candidates.py` output through `fetch_sketchfab.py` and the preview jobs (Japanese set, screens, palms, drifts first).
* 35 heat gaps remain: citrus, hibiscus, fig, delonix, camphor, ficus microcarpa, guava, jasmines, Strelitzia, papyrus, lotus, monstera, bamboo and others. A Gulf source with species tables (Abu Dhabi PRDM PDF, Dubai manual) would close most; the PDFs were not found by search.
* Fish toxicity needs a vet/aquaculture source per species.
* Bauhinia, mango, Washingtonia and the other dropped species: **not added** (time went to evidence and assets).

## Pass 3 (2026-11-22): Gulf and Cairo lists, shade and pond species

* **Heat gaps 35 -> 22** (species 77 -> 82). 17 filled by `tools/apply_gulf.py`, all `inferred: true`, each with a quote re-checked live (`verify_quotes`: 938 verified, 9 not matched as before, 14 unreachable as before; none of the new quotes failed). Sources opened: Abu Dhabi UPC *Public Realm Design Manual* (2011) Appendix B (PDF read from the cip-icu.ca copy; it gives an **Exposure Group** per species, so class follows our policy A/B high, C/D/E moderate: fig B; lemon D; hibiscus, guava, poinciana, Ficus microcarpa C; Murraya (listed as *M. exotica*) D; lady palm E; PRDM notes: hibiscus "use not advised" for insects, poinciana "use only in humid coastal areas"); Abdelnaby et al. 2021, Cairo Festival City woody-ornamental survey (Plant Archives 21(1)): Lagerstroemia indica, Jasminum sambac, J. grandiflorum; Emirates Natural History Group Bulletin 29 (1986): grape; USDA FAS Cairo Citrus Annual EG2025-0031: orange grown across Egypt, mostly on reclaimed desert; a Mitt. Bot. Staatssamml. München note: wild papyrus in Wadi Natroun (marsh water, so heat is inferred, not water).
* **Shade species added (5)**, from PRDM exposure groups D/E (partial to total shade, the Gulf's own shaded-court list) and the Cairo survey: *Ravenala madagascariensis* (E), *Alocasia macrorrhizos* (D, "full shade"), *Livistona chinensis* (D), *Dypsis lutescens* (Cairo survey; heat from NC State listing). Pond edge: *Colocasia esculenta* (heat GAP: Egyptian journals on ekb.eg did not respond from this machine). Attributes sourced from NC State, RHS and NParks only; GAPs listed. Ravenala's NC State sun rating is full sun only, so it needs the PRDM shelter note, not an assumption of shade tolerance.
* **Viability** (policy thresholds as before): **23 viable, 30 viable with conditions, 1 not viable, 28 unverified** (was 22 / 26 / 1 / 28 at 77 species before the five additions, 11 / 13 / 2 / 52 at pass 1). Viable plus conditional **53** (39 at the start of this pass).
* **Not found / not usable**: Dubai Municipality (only a 2026 press release, no plant tables), Qatar Ashghal/PEO, Riyadh (the *Manual of Arriyadh Plants* mirror opened but its readable part named none of our gap species), Saudi MEWA/KISR, Orman and Zohriya (no species lists online), Egyptian ekb.eg journal PDFs (timeouts). Open: bamboo, camphor, jasmine-like climbers (Petrea), Strelitzia x2, monstera, thaumatophyllum, papyrus-relatives, lotus, water lily, iris, herbs, Pentas, Agapanthus, loquat, Phyla and Chlorophytum.
* **Fish toxicity: still GAP for every pond species.** Searched: Merck Veterinary Manual and veterinary lists (no koi/pond-plant chapter names any of ours), koi/pond hobby sites (not accepted), FAO aquaculture review of emergent macrophytes (FAO i1141e07): it records lotus, water lily and taro as eaten or used in fish feed (taro leaf powder partly replacing fishmeal for carp, dried and processed), which is feeding evidence, not a toxicity statement for ornamental koi, so it is kept as a note only.
* **Assets**: `~/archpipe/lead/sketchfab-api.txt` still absent (no download or grading of the 44 candidates); `~/archpipe/shared/assets/user/landscape/botaniq/` absent (no Botaniq grading). Five new species added to the asset table as not drawable.
* Tests: `tests/landscape` 157 passed, 1 skipped; `lane_guard.py LDL` clean.

## Pass 3b (2026-11-22): Sketchfab token arrived, 83 candidates downloaded, graded and looked at

* `tools/fetch_plants.py` reads the token from `~/archpipe/lead/sketchfab-api.txt` (never printed), re-reads each model's licence from the API at download time and refuses anything but CC0 / CC Attribution (0 refused: the candidate list was already filtered, all 83 re-checked as CC0 or CC-BY). Binaries: `~/archpipe/shared/assets/user/landscape/sketchfab/<uid>/` (outside git). Repo records `sketchfab-manifest.json` (sha256 per file, licence, author, url) and `asset-manifest.json` (`sketchfab/<uid>` keys, hash-tested). CC-BY credit = `author` + `source` on every `skf3_*` row of `assets.json`.
* 7 targeted extra candidates were added for papyrus, lady palm, alocasia, livistona and salvia (public search); 83 models cover 45 species. jobq jobs `ldl-p3b-0/1` (CPU) rendered 83 sheets (5 m top row, 15 m bottom row, 4 azimuths); every sheet was looked at, grades are in `assets.json` (`skf3_<uid8>`), sheets in `asset-previews/`.
* Result: 6 A, 7 B, 16 C, 54 D. **Drawable species 5 -> 12** (+1 genus stand-in): new are Phoenix roebelenii (A), Punica granatum (B, two assets), Alocasia (B, genus), Rhapis (B, genus), Phoenix dactylifera (B, young palm), Lagerstroemia indica (B, sparse), Nerium oleander (B, a set of ~25 shrubs: extract one).
* No materials were repaired: the untextured lady palms, livistona and calla have no images or colour in the file, so nothing was invented. Not applied, needs a lead decision: papyrus (18.5 m authored, B if scaled 0.1) and Alocasia macrorrhizos (9.5 m, B if scaled 0.3).
* Still undrawable, and why: no free model exists under any name searched for Petrea, Justicia, Alpinia, Aspidistra, Origanum, Pennisetum, Pittosporum and Salvia leucantha; Jasminum sambac, Acorus, Rosmarinus, Bougainvillea, Fatsia, Ficus, Olea, Citrus-orange and the fruit trees have only fruit, scans or 1-5 cm cuttings. Paid libraries (Xfrog, Botaniq) remain the route (see `LDL-assets-shortfall.md`).

## Pass 4 (2026-11-22): free sources, procedural prototype, rescales

Full detail in `docs/lanes/LDL-free-sources.md`.
* Sources checked with licence quotes: Fab/Megascans (engine-agnostic Fab Standard License; **blocked on an Epic account**, 26 free candidates listed in `free-candidates-fab.json`, 4 of the 13 gap species covered: Rosemary, Oregano, Red Fountain Grass, Cast-Iron Plant), BlenderKit (no gap species; account needed), CGTrader, TurboSquid, Smithsonian, Poly Haven, GrabCAD, free add-ons: no other source covers a gap species.
* Procedural prototype Pittosporum tobira graded **C** (`asset-previews/proto_pittosporum_tobira.jpg`); proposal: about 20-25 working days for the shrub list, expected B for foliage shrubs, C-B for flowering climbers.
* Papyrus rescaled to 0.105 (1.95 m) and now **B, drawable**; Alocasia placement scale 0.7135 recorded. Drawable species 12 -> 13 (+1 genus stand-in). No new species were graded from new downloads: nothing was downloadable without an account.

