# INT2: RA2 (production scene) + L6b/L6c (lighting) integration (2026-11-21)

Merge of `origin/lane/RA2` onto `origin/integ/aplus` (1cf511a): no textual conflicts. Every failure was a semantic interaction.

| # | failure | cause | fix |
|---|---|---|---|
| 1 | `support-marker-PATH-landing-gf-02: no real host` | wall markers are +y-facing only (marker mesh built in an xz plane, hosted on a +y shell face). L6b put the landing markers on the west wall (aim +x). 01 passed only by hosting on a wall end-cap 0.19 m behind it; 02 had nothing within 250 mm | both on the landing's real +y face, the 0.285 m south-wall stub (x 3.817..4.102), aimed along the landing. Host guard untouched. Markers are in the *switched* night zone, so V12 is unaffected; `tests/lightcalc` 95 pass. **Open:** the 12 mm plaster move needs lead approval rows (see below) |
| 2 | wp6 67 != 69 | the two `DLN-bar-alcove-11/12` details: L6b removed the nook downlights | pins 69 -> 67, DLN 2 -> 0 |
| 3 | snapshot 1800 != 1200 | stale snapshot | integration re-run (+ derived size table refreshed for ERCO, ies refs repo-relative) |
| 4 | `ImportError SpecError` | `archpipe/model.py` shadowed by the `archpipe/model/` package since L2 | legacy module renamed `spec_model.py`, importers repointed (also `verify.py` line 47) |
| 5 | electrical/exchange/test_villa_lighting | stale zones (68 now), 132 luminaires, ERCO products; `VL.check` is a direct-only evaluator that ignores drivers | pins to L6c; gate = Radiance rows (`villa-after-rows.json`); EA13: zone W above the luminaire sum (generic strips) is carried by the luminaires |
| 6 | (found here) every recessed fitting UNRESOLVED | `ceiling_requirements.product_depth` read LDTs from the git-ignored `assets/user`, which has no ERCO | falls back to the repo's ERCO LDTs (DL 95, DLN 92, ADJ 169, WW 92 mm) |

Receipts and exposure record redone by RA2's baseline-relative procedure, twice (after the lighting merge: fixtures/markers only,
`evidence-int2/section-diff.json`; after the housing-depth fix: 26 `fix-*` meshes, `section-diff-housing-depth.json`). 17 reviews, 0 findings each time.

**Approval rows needed (lead):** `marker-PATH-landing-gf-01/02` finished-face move of -12 mm (plaster 13 mm; same physical case as the approved
`marker-PATH-corridor-07/08/09` rows in `knowledge/c4-e-lead-approvals.json`). Not added by this lane. Until then
`test_migrated_plane_contracts_quiet_but_core_coverage_fails` and verify.py's finished-surface check report exactly these 4 findings.
