# LDC calibration pre-registration (written before the VLM, the held-out seeded set and the final scoring were run)

Date 2026-11-22. Lane LDC. Targets (A3, docs/quality/LANDSCAPE-METHOD.md): **recall >= 90 % on known-bad, false-fail <= 10 % on known-good.**
Nothing below is tuned after scoring; a criterion that misses is demoted to advisory (`calibrated: false`), never adjusted.

## Disclosures (what was already seen before this file)
1. The 19 *seeded defects* in `seeds.py` (set 1) were written and **iterated until each tripped its target criterion** (e.g. the evergreen
   tree was moved from the east to the west boundary and shortened after the first version did not shade anything; the summer-sun seats were moved
   to the 6 h strip). Their recall is therefore a **sensitivity test of the code, not independent evidence**, and is reported as such.
2. The reference scheme (`base`) and the policy thresholds in `computed.py` (PRIV_MAX 8, ENCL_SHARE 0.5, full-sun-misfit 3 h, ...) were set while
   looking at the base scheme's results, so that the base is the clean baseline; PRIV_MAX in particular was relaxed from LDS's 5 to 8 for that reason.
3. The 10 precedent layouts were drawn before scoring. After a first run showed A-PATH-TERMINUS failing on them I removed the paths I had invented for
   the plans that do not draw paths (kept: SAU-02 ramps, SAU-04 entry). That changed the *input*, not the critic. Their architect-critic results were seen.
4. **Independent evidence** is therefore: (a) set 2 (`seeds_heldout.py`, 9 defects, written below before being run, not iterated); (b) D1, the real
   known-bad; (c) the precedent false-fail rate; (d) the VLM held-out half.

## Critics and verdict
A critic's **verdict is FAIL** if any of its findings has status `fail` and severity `blocking` or `major`; `warn` findings are advisory.
A seeded defect is **caught** by criterion C when C is `fail` or `warn` on the defect and `pass` (or absent) on the base. A defect whose target
criterion is already non-pass on the base is excluded and listed. Recall per criterion = caught / defects that target it.
**False-fail** per criterion = known-good layouts on which it is `fail` / known-good layouts on which it was evaluated (not `not_evaluated`).

## `calibrated` flag per criterion (frozen rule)
`calibrated = true` only if (recall >= 0.9 over >= 2 targeting known-bad items) AND (false-fail <= 0.10 over >= 5 evaluated known-good items). A criterion
with no evaluated known-good item is `calibrated: false` with status `recall-only`. VLM criteria additionally need the pre-registered gate rule below.

## Known-bad / known-good sets
* Known-bad: D1 as drawn (`d1-layout.json`); set 1 (19) and set 2 (9) seeded defects. VLM subset (plan-visible): D1, lone-specimens, no-enclosure,
  path-to-nowhere, single-layer, privacy-exposed, oversize-tree, capacity-4.
* Known-good: the 10 re-drawn precedent plans (P-SME-01/02/05/08, P-SAU-01/02/04/05, P-S2-04/20); `base` is an extra control, not a professional garden.
  Only the site-independent architect criteria can be evaluated on them. **Horticulture, user and climate criteria need the brief, the plant species or the
  villa site layers, none of which a precedent has: their false-fail on professional gardens cannot be measured here.** Stand-in species are used for planting.
* 33 precedent photos (calibration.json) vs the 9 D1 render views (v19, v25-28, v36, v37, v39, v40 in `~/archpipe/shared/laptop-out/villa/finals-2026-10-15`):
  photo criteria P-ENCLOSURE, P-LAYERS, P-FOCAL. **Confounded by medium** (photograph vs CG render; the D1 grades are for asset defects): reported, never gating.

## VLM (plan image)
Model qwen3.8:27b-mtp-q4_K_M via Ollama, temperature 0, seed 7, one criterion per call, evidence field first, prompts v0 in `rubric.json` (frozen
when this file is committed except for anchors edited on the TUNING half, logged). Split: sha256(`LDC-2026-11-landscape-critic-v1:<id>`) order, alternate:
stored in `rubric.json` `split`. Gate rule: a VLM criterion gates iff on the tuning half separation (share of bad < 2 minus share of good < 2) >= 0.30 and no good
item scores 0. Image verdict: FAIL if a gating criterion scores 0 or two gating criteria score 1. The held-out half is scored once after `rubric.version` is set to `frozen-*`.
A VLM criterion reaches `calibrated: true` only by the frozen rule above on the HELD-OUT half (n is tiny: held-out bad 4, good 5; one-sided 95 % bounds are reported).
