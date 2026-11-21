# LP: luminaire products with public photometric data

Client decision 2026-11-21: nothing bought yet; prefer makers that publish photometry openly so every product can be
checked against the manufacturer's lab data. Data: `knowledge/lighting-products/candidates.json`
(files, sha256 and source per product; code `src/archpipe/luminaires/v10.py`, `lp_candidates.py`; tests `tests/luminaires/`).

## Bottom line (2nd run, 2026-11-21, real Chrome)

ERCO opened to a normal Chrome visit (the scripted fetch had hit a Vercel checkpoint, which was not circumvented). Each article
has a datasheet PDF, an LDT and an IES at `download-service.erco.com`, the endpoint the page buttons call; one request at a time,
3 s apart. **Nine ERCO articles are stored** under `knowledge/lighting-products/erco/<code>/` (PDF, LDT, IES byte-for-byte,
`source.json` with URL, date, sha256). Every published point is transcribed from datasheet page 1 with its quote
(`src/archpipe/luminaires/lp_erco.py`) and reproduced by **both** routes (archpipe `lightcalc.direct` and the independent reader).

**Full V10 pass (lumens within 2 %, every published point within 5 %)** for DL, DLN, both WW, PEN-LIN, DESK and the two exterior
products. The two ADJ spots are **partial**: Imax, lux on axis at 1-5 m and lumens pass, but the published beam diameter / beam
angle fail (published 4.7 deg / 5.0 deg; the file's 50 % angle is 5.7 / 6.0 deg, diameters 16-24 % off). The LDT is sampled at 1 deg
so a 5 deg beam is poorly resolved (axis 56 067 cd, 3 deg 27 597 cd); that is a cause, not a proven one. The datasheet axis
values are 3.1-3.5 % above the file's, inside tolerance. Not edited, not tuned.

## Per kind (recommended = V10 result on the manufacturer's own datasheet; all ERCO 2700 K, Ra/CRI 92, dimmable)

| kind | recommended | V10 | published vs computed (engine / independent) | worst error | caveat |
|---|---|---|---|---|---|
| DL | ERCO 41321.000 Quintessence downlight, wide flood 56 deg | **pass** | Imax 1147 vs 1147.6/1147.6 cd; beam 56 vs 57.0/57.0 deg; 1065 lm vs 1065.9/1066.0 | 1.8 % (beam) | 1065 lm vs the kind's 650: dim or pick size 3 lower flux; IP20, DALI-2; cut-off 40 deg; UGR not printed for size 3 |
| DLN | ERCO 41369.000 Quintessence extra wide flood 89 deg | **pass** | Imax 535 vs 535.2 cd; beam 89 vs 91.8/91.7; 904 vs 904.7/905.0 lm | 3.2 % (beam) | 2700 K, the kind wants 3000 K (ERCO also lists 3000 K Ra 97 for this family; not fetched) |
| ADJ | ERCO A9001547 Optec New spot L (855 lm) or A9000028 (304 lm) | **partial** | lux 1 m 57 848 vs 56 066.9 (3.1 %); 5 m 2314 vs 2242.7; beam diameter 0.09 vs 0.1048 m (16.5 %) | 3.5 % pass / 24 % fail | beam diameter fails; 304 lm is below 500, 855 above; track, on-board dim, IP20 |
| WW | ERCO 26141.000 Pantrac Lens wallwasher (777 lm, track) or 41374.000 Quintessence Lens wallwasher (recessed, 399 lm) | **pass** | 26141: Imax 1036 vs 1045.7 cd (0.9 %), 777 vs 777.3/777.1 lm; 41374: Imax 471 vs 478.6 (1.6 %), 399 vs 399.0/399.1 | 1.6 % | wall-wash mean illuminance table (wall height, offset, spacing) is printed but not reproduced: it is a room calculation, not a file figure |
| PEN-LIN | ERCO 50674.000 Jilly pendant downlight 1500 mm (UGR 19) | **pass** | Imax 1055 vs 1053.8 cd; beam 86 vs 89.0/89.0 deg; 1779 lm per file (2 files) vs 3558/2 | 3.5 % (beam) | 3558 lm total, far above the kind's 1200 lm; two identical emission files |
| DESK | ERCO 31327.000 Lucy task light (234 lm) | **pass** | Imax 454 vs 461.4 cd (1.6 %); 234 vs 233.9/233.8 lm | 1.6 % | 2700 K vs the kind's 3000 K; 234 lm vs 450; IP20 |
| exterior terrace/step downlight | ERCO B0000184 Iku surface downlight IP65 | **pass** | Imax 815 vs 816.1 cd; lumens 676 vs 676.4; cone table 815/204/91/51/33 lx and D 1.03-5.15 m reproduced | 1.7 % (worst point, beam) | **3000 K** as listed ("2700 K or 3500 K on request"); IK07; not a design kind in `fixture_record.KINDS` |
| exterior bollard | ERCO 35720.000 Castor | **pass** (photometry) | Imax 135 vs 136.4 cd; 198 lm | 1.0 % | **3000 K, not dimmable** (datasheet "Dimming range --"); disqualified on the brief's dimming rule |
| COVE, BACK, NL, TOE | iGuzzini ST49 Underscore15 | lumens-only | 680 lm/m vs 680.0 | 0 % | as run 1 |
| (iGuzzini LSEVO) | DL/DLN/ADJ/WW substitutes | lumens-only | see run 1 | 0.4 % | superseded by the ERCO entries above for DL, DLN, WW; ADJ stays partial |

Kinds still **without a V10 pass**: PEN-GLOBE, PEN-SMALL, WALL-READ, SWING, SCONCE, VSCONCE, VANITY-LIN (IP44), UC, RAIL,
VSTRIP, STORE-BATTEN, MIRROR, STEP, PATH, and COVE/BACK/NL/TOE (lumens-only). Reason: ERCO has no decorative pendants, sconces,
vanity or tape products in the families checked (indoor recessed/track/pendant/wall/task, outdoor), and the outdoor families
list 3000/4000 K only (Site, Tesis give no CCT in the finder). Delta Light, Zumtobel, Flos and Signify were not completed (below).
ERCO article search: 3 321 articles in 36 families were listed from the product-finder backend the page itself calls, filtered
2700 K and CRI >= 90 (`/tmp` working files, not stored).

Not found in the obtained set: R9, IP44 vanity, Egypt distributor (left empty); datasheets print CE/UKCA/RCM marks only.

## Sites

ERCO: working (above). Delta Light: pages load in Chrome (HTTP 200); files are generated per variant by api.deltalight.com after
JavaScript variant selection, not completed in this run. Zumtobel, Flos, Signify: not retried (time box spent on ERCO).
Thorn 403 earlier; no bot challenge was bypassed anywhere. Flos home loads 200.

## Run-1 files

Run 1 committed the iGuzzini LDT/IES through the old `text=auto` rule (LF-converted blobs). They were re-added under the binary
rule; the committed blobs now hash to the `source.json` sha256 (test `test_stored_files_match_source_sha`).

## Decisions

* A figure typed from memory is not published data: only the 451G page values I read today are entered as points.
* LSEVO file names: product URL was not recorded at import (2026-09-27); sidecar says so.
* "pass" requires a non-lumen published point; lumen agreement with the product name alone is `lumens-only`.
* Redistribution: files are public iGuzzini downloads for design use; their terms were not separately read.
