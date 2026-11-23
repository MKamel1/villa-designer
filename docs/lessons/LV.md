# LV lessons (defect -> why it was missed -> guard)

| defect | why it was missed | guard now |
|---|---|---|
| V1's instance check compared each sample of the 8-point pendant with the whole fixture's lumens. | The check was written when every product was one placement per fixture; the L6c redesign sampled the pendant along its length. | `instance_problems` sums by parent; `test_sampled_pendant_is_summed_by_parent` (fails on the old code) and `test_wrong_parent_total_is_still_caught`. |
| Frozen Radiance baselines silently described the previous design. | Tests compared stored results with the live design, so a redesign only showed as a failing test, not as a stale baseline. | Baseline regenerated on the L6c design; `python -m archpipe.lightverify --regen-radiance --freeze` rebuilds it from the current design. |
| V10 only knew the iGuzzini products; the ERCO products were "V10 pass" by LP's say-so. | V10 trusted the lane that bound the product. | `v10_erco.py` parses the data-sheet PDFs itself and reproduces lumens, Imax, lux on axis and beam; negative tests change the data-sheet text. A 1 m cone row was first missed (row shares its line with other text): `test_datasheet_parser_reads_every_row_of_the_cone_table`. |
| A gate that was global (`V10` pass/fail for the whole design) could not express "one product is partial". | One failing point would have made every room unverified, or been hidden. | V10 is a per-room status; the partial ADJ makes only the lounge unverified, with the armchair sensitivity in numbers. |
| The wallwasher is thrown 90 deg off in Cycles versus the engine and Radiance; V5 only compared room averages. | Room averages mix many lights; the calibrated azimuth offset was proven on straight-down lights only. | V5 single-light orientation probe per product kind (`kind_orientation`), a negative test that the probe responds to spin, and a quiet test for the symmetric DL. |
| LA4 passes with a 90 000 cd/m2 downlight in the room. | The check only counts sources inside 45 deg of one chosen sightline. | Reported as a design finding with the numbers; add a "looking up" sightline (not mine to edit). |

## L6d verification (2026-11-22)
| defect | why missed | guard |
|---|---|---|
| V10 hard-wired product ids; a product change was reported as a failure | ids in a module constant | products read from `bind_products()`; test rebinds ADJ and expects the table to follow |
| `run_cycles` cache ignored the renderer | key = job JSON + probe | `renderer_sha()` over `blender/*.py` + probe; test edits a renderer file and expects a new jobq id |
| V6 n/e for three sub-planes | rooms without a room-* plane had no V6 row | `v6_handcalc.subplanes` judges `v6-subplanes.json` against this lane's Radiance (stale file fails) |
| QA03 CRI recorded 90, page says 92 | spec read from the product name | V10 `cri` row: overstated fails, understated flagged |
| A fresh clone at a reused path failed the v5 test (jobq returned the dead clone's job) | job id = hash of content that holds only paths; jobq submit is idempotent on id | id unique per submission; guard `test_run_cycles_job_id.py` with a fake jobq that behaves the same way |
| V10 had no CRI check for Libera pages | CRI parsed only from the QA layout (label and value on separate lines) | `_inline_cri` reads "CRI nn" under "Light colour quality"; `test_iguzzini_page_is_read_by_label...` covers both layouts |
