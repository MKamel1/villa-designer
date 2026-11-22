# LDP: landscape precedent statistics (2026-11-22)

Lane output: `knowledge/landscape/precedents/` (JSON) and `src/archpipe/landscape/precedents/` (loader, validator, derivation, freeze). Tests: `tests/landscape/precedents/` (18).

## FROZEN TARGETS
`knowledge/landscape/precedents/targets.json`, frozen **2026-11-22**, file **sha256 = 3f8caec278dc4a1ada0c21a99a22f8a7b1f10bd0503803ed1298143aee9fd118**.
Frozen before any concept generation exists. The generator must not tune it. `precedents.freeze()` refuses to overwrite it and `check_frozen(expected_file_sha256=...)` fails on any edit (guard test reads the hash from this file).

## Result in one paragraph
The precedent collection is **too thin to freeze most ranges**. Only two metrics have a usable range, both for the south set: **hard share of surface 0.44–0.87** (median 0.69, n=6) and **trees per 100 m² 1.56–3.26** (median 2.23, n=6). Every other metric, and the whole north set, is a **GAP**. Reasons are below; none is filled with a guess.

## Sources and counts
- South: 12 gardens (7 hot-dry Mediterranean/Middle East via ArchDaily house plans: Cyprus, Malta, Dubai, Amman; 5 Australia). 48 photos + 12 plans cached in `~/archpipe/shared/landscape-precedents/south/`. Only 5 gardens fall in the 30–150 m² size band; 9 in 30–250 m².
- North: 12 candidates (Kyoto machiya/tsubo-niwa, Singapore/Jakarta/Chiang Rai/Bandung koi-pond houses). 40 photos + plans cached in `.../north/`. Only **N14** has a legible scale with a pond, N02 and N09 are low-confidence tiny courts; 2 pairs total.
- Every record carries its page URL (and plan URL where known). Images are publisher copyright: cached outside the repo for analysis, never committed or rendered. No gardens are copied.
- The sourcing agents' web access was weak (WebSearch returns summaries; Houzz/Landezine/ASLA are JS-heavy or large public projects; **no California garden with a scale bar was found**). Plans are mostly **house plans in which the courtyard is read**, not landscape plans, so planting metrics were not readable.

## Method
Two independent measurement passes (A, B) by separate agents; each saw only the plan image, the page URL and shared definitions (`DEFINITIONS.md` in the cache): not the sourcing notes, not the other pass; pass B ran in reverse order. Areas are hand-estimated from the scale bar (a hand-estimated polygon, not CAD): confidence is low to medium. Per garden the value is the mean of the passes, **excluded if A and B differ by more than 50 %** (policy). A metric is **dropped if the median A/B relative disagreement exceeds 25 %** (policy), or if fewer than 6 usable gardens remain (policy). Range = interquartile (Q1–Q3) of garden means. Size-dependent metrics use the strict band (south 30–150 m², north 8–60 m²); density metrics (hard/soft/water share, trees per 100 m²) use the wide band (south 30–250 m², north 8–100 m²) and carry `size_matched: false`. All thresholds are our policy, not published standards.

Spread achieved (south, median relative A/B): area 0.12, hard share 0.17, trees/100 m² 0.20, rooms 0.0, room area 0.21. Dropped for **no data in either pass**: path widths, drift size, layer shares, species per 100 m², enclosure ratio (no plan shows plant symbols, a legend, path dimensions or a section). Dropped for spread or n: north (all), south soft share, water share (n<6), n_rooms, room area, area (n<6 inside the strict band).

## D1 garden against the frozen ranges (read-only, `d1.json`)
| metric | D1 south (57.0 m²) | south range | position |
|---|---|---|---|
| hard share | 0.265 | 0.44–0.87 | **below** (D1 is softer than every quartile of precedents) |
| trees per 100 m² | 1.75 | 1.56–3.26 | inside (one frangipani) |
| n_rooms | 2 | GAP | no range |
| path primary | 0.914 m | GAP | no range |
| layers canopy/shrub/ground (symbols) | 0.03/0.60/0.38 | GAP | no range; canopy share is very low |
| species per 100 m² | 14.0 (8 species) | GAP | no range |
| drift size | 3 | GAP | no range |
D1 north (25.2 m²): hard 0.69, soft 0.31, 0 trees, no water, 5 species: no north ranges exist. Definitions for D1 are in `d1_measure.py` (gravel and stone are hard; artificial turf is soft and flagged).

## Brief risks the findings expose
- The south set's hard share (median ~0.7) suggests a 10–20 person gathering garden is mostly paving; D1's 0.265 would not hold a dining + lounge group plus standing room. The brief's capacity needs a **terrace-area-per-person rule from LDK** that this lane cannot supply.
- Precedent gardens were mostly 60–240 m²; the 57 m² south garden is at or below the small end, so a 10–20 person group with a quiet corner, fire pit, BBQ, herbs and screening will be tight. Not a measured fact: a size mismatch of the evidence.
- **North pond**: no usable precedent for a 25 m² pond court with a flush pond; the only measured pond court (N14, ~63–100 m², pond 36 m²) is a koi-farm office and not comparable. The pond/garden ratio is a GAP.
- Enclosure and privacy statistics are GAP; privacy (critical in the brief) has no precedent number.

## Schema (knowledge/landscape/precedents/*.json)
- `south.json`, `north.json`: `{"set", "gardens":[{id, name, designer, location, year, page_url, plan_url, scaled_plan, cache_dir, passes:{A:{...},B:{...}}}]}`. A pass holds metrics (null/omitted if unmeasured): area_m2, hard_share, soft_share, water_share, n_rooms, room_area_mean_m2, path_primary_m, path_secondary_m, trees_per_100m2, drift_size_median, layer_canopy/shrub/ground, species_per_100m2, enclosure_ratio, privacy_approach; plus annotations scope, scale_note, confidence, rooms_note, privacy_note, has_pond, pond_area_m2. A garden with no scaled plan may carry no plan metric (validator rejects).
- `d1.json`: current garden, same metrics. `targets.json`: per set per metric `{status: range|GAP, q1, median, q3, min, max, n_pairs, n_usable, median_rel_spread, size_matched, reason}` + policy + date + content_sha256.
- `calibration.json`: known-good photo lists (south 12 gardens/48 images; north 12/40, cached outside the repo, **not yet visually curated**) and known-bad D1 views from `docs/reviews/2026-11/visual-audit.md`: v19 C, v25 C-, v26 D, v27 D, v28 D+, v36 F, v37 D, v39 D+, v40 D+; v41 (B-) is kept out as the best exterior.
- Regenerate nothing: `build.py` imported the passes; `d1_measure.py` re-measures D1 (output not frozen).

## GAPS (not sourced, not guessed)
Path hierarchy, drift sizes, layer proportions, species-versus-area, enclosure ratio, privacy approach (south and north); every north metric; south soft share, water share, rooms, room area (n<6 in band). Also: no California / arid-Chile scaled plan; no Bawa court plan; no pond-court plan with a scale at 12–60 m².

## Open items
1. Source landscape-plan-grade precedents (HALS/LOC measured drawings, APLD/AILA small-garden portfolios, Bawa/Kyoto surveys, books) and re-run; ranges can only be **added** under a new, dated, separately hashed file, never by editing this one.
2. Visual curation of the calibration photo lists (some may be interior or aerial).
3. A human check of the hand-estimated areas for the 5 in-band south gardens.

## SECOND PASS — targets-2.json (2026-11-22)
`knowledge/landscape/precedents/targets-2.json`, frozen **2026-11-22**, file **sha256 = b08542f0d9fd3be889fe1b48092abf78cc851b98b2e57764dd42565691edb677** (separate from targets.json above, which is unchanged: 3f8caec2...). Recorded before any concept exists. `targets2.freeze2()` refuses to overwrite; the guard test reads this hash.

**Added gardens** (`south2.json` 9, `north2.json` 7; pages and plan images cached in `~/archpipe/shared/landscape-precedents/{south2,north2}`, never committed):
- south2: 2 show-garden (MIFGS 2013/2015), 3 award entries (MIFGS 2015, Parkside, Al Barsha 37 Dubai), 4 designer portfolio (Perth, Sydney, London x2). Climate tagged per garden (6 temperate, 2 mediterranean, 1 hot-dry). Only **2 have a usable scale** (S2-04 scale bar, S2-11 printed dimensions); S2-20 states 1:75@A3 but the raster has no scale bar, so no numerics.
- north2: 7 portfolio (ArchDaily, mooool) tsubo-niwa / tropical courtyards, all with a scale bar except N2-06 (unlabelled bar: all null). **No survey, paper, award or HALS entries**.
- Where the numbers sit: groups are `<set>_combined` (first pass + new) and `<set>2_only`; climate tag per garden in the JSON. With 1 hot-dry new garden, a hot-dry-only set cannot be derived.
- Numerics are only kept for gardens with a scale (build.py drops plan metrics from unscaled gardens; the first import let unscaled `n_rooms` through).

**Metrics with a range now** (interquartile, n_usable of gardens, median A/B spread; all low-confidence hand estimates):
| group | metric | range | n | spread |
|---|---|---|---|---|
| south_combined | area_m2 (30-150 band) | 46.0-87.8 m² | 6 | 0.07 |
| south_combined | hard_share (wide band) | 0.52-0.82 | 7 | 0.17 |
| south_combined | trees/100 m² (wide band) | 1.56-3.26 | 6 | 0.19 |
| north_combined | area_m2 (8-60 band) | 12.3-23.2 m² | 6 | 0.03 |
| north_combined | n_rooms | 1-1 (all one court) | 6 | 0.0 |
| north_combined | room_area_mean_m2 | 12.3-23.2 | 6 | 0.03 |
The north "range" is the area of whichever tiny courts were scaled, not a design target. The south hard-share range moved from 0.44-0.87 (n=6) to 0.52-0.82 (n=7).
Qualitative tallies (counts, no range): privacy approach and water edge are in the file. Privacy: most gardens disagree between passes (13 of 18 north, 7 of 21 south), so no approach is a target. Water edge (flush vs raised): n=4 south, 0 north; one "flush", three disagree. **No north water-edge precedent.**

**Still GAP** (both sets): path widths, drift size, layer shares, species per 100 m², enclosure ratio, soft share, water share, south n_rooms/room area, north hard/soft/water share, north trees (n=2). **Hot-dry planted small gardens: effectively none** (one scaled, Al Barsha 37).
Why: web access offered mostly whole-house plans or planting plans without a scale bar; LOC/HALS answers scripted requests with a Cloudflare challenge (not bypassed); Landezine refused connections; MDPI/ResearchGate/archnet blocked; J-STAGE reachable but plan figures were not extracted; no Bawa plan. The south2 sourcing agent stalled after 9 gardens.
**To close the gaps** a human (or a browser session) needs to fetch HALS drawings, RHS/Chelsea planting plans with scale bars and J-STAGE/Heritage Science PDFs; ranges can again only be added in a targets-3.json.

**Calibration photos (visual curation)**: all 88 photos viewed on contact sheets; 55 removed (interior, street facade, aerial, construction, duplicate), 33 kept (south 11 gardens/20, north 8/13); list in `calibration.json` `removed_photos`.
