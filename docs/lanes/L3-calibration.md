# L3 render vision critic: method and calibration

Lane L3, branch `lane/L3`. Criteria R1-R13 are from `docs/quality/a-plus-interior-renders.md` section C; labels are the human grades in `docs/reviews/2026-11/visual-audit.md` (38 views of `out/villa/finals-2026-10-15`).

## Result in one paragraph

On the held-out half (18 views), frozen rubric, the critic failed **8 of 8** views graded D+, D or F (recall 100 %, target 90 %) and **12 of 13** of the audit's seeded QA false passes, but it also **failed 1 of the 2** views graded B- (false-fail 50 %, target 10 %: **missed**). Both numbers rest on tiny groups (8 and 2 views), so the recall figure is encouraging, not established, and the false-fail figure is a miss with a very wide interval. Over all 38 views the critic fails 32 and passes 6; it passes 3 of 5 views graded B- or better and fails 2 (v34 on tuning, v21 held-out). The current QA failed only 3 of 38.

## Pipeline

`python scripts/critic_run.py <png|dir> [--vlm ssh|off|CACHE_DIR]` prints a `contracts.RenderVerdict` per image and writes `contracts.CheckResult` records (one per criterion, lane `L3`) to `out/checks/L3.json`.

Deterministic (metadata json beside the png, plus pixels; `src/archpipe/critic/meta.py`, `pixels.py`), about 1 s per image, numpy and Pillow only (the project venv has no OpenCV):

| id | check | score 2 / 1 / 0 |
|---|---|---|
| R1 | `camera.lens_mm`, written reason from `camera.overrides` | 24-35 mm / 16-<24 mm with a reason / no reason or outside 16-35 |
| R2 | camera z above the floor datum (-3.0 m or 0.0 m, the highest at or below the camera; assumption, since z is absolute) | 1.1-1.6 m / within 0.2 m of that / else. Every view is 1.35 m. |
| R3 | camera pitch from position and target, plus lean of straight near-vertical edges (structure-tensor coherence > 0.9, bins with >= 3000 supporting pixels) | <= 0.5 deg / <= 1.5 / else |
| R4 | clipped (any channel >= 0.985) and crushed (luma <= 0.03) share on the subject mask | <= 1 % and <= 2 % / each within 3x / else |
| R10 | solid black or white band >= 1.5 % wide at a frame edge (pixel), min with the VLM score | none / - / band |
| R12 | mid-tone (luma 0.25-0.75) cool excess (b-r) <= 0.03, cyan <= 0.05, warm cast magnitude <= 0.09 | 2; up to 0.06 / 0.08 / 0.10 is 1; else 0 |

Subject mask approximation: union of the `subjects[].screen` boxes from the view json (conservative mesh bounds, so generous: they include background and sometimes windows), clipped to the frame and flipped from y-up. If the union is under 15 % of the frame or missing (v23 has no subjects), the central 60 % x 60 % rectangle is used. The mask basis is printed in every R4 message.

VLM (`src/archpipe/critic/vlm.py`, Ollama on the workstation, one criterion per call, JSON schema output with the evidence field first, temperature 0, seed 7, `think: false`), prompts in `knowledge/critic/rubric.json`:

- R5 context, R7 material scale, R8 asset fidelity, R9 contact, R10 composition and frame (seams, bands, haze, occluders, cropping), R11 truth and styling (given the view title). Each call shows the benchmark `bedroom-overcast-door.png` (cropped to 3:2) as image 1, "the reference, score 2", and the render as image 2, with severity and extent anchors for 0/1/2 and "score 2 if not sure".
- R13 benchmark parity: pairwise, both left/right orders. 2 only if both orders judge the render at least as photographic, 0 only if both say clearly less, else 1.
- R6 texel density is out of scope for an image critic (`not_evaluated`, excluded from the verdict).
- Images are sent as 1280 px JPEG (quality 90). Runtime on the RTX 3090 under `flock ~/archpipe/locks/graphics.lock`: **29 s per image** with all 7 calls (R13 is two) for qwen3.8:27b-mtp-q4_K_M; 17 s with gemma4:31b; about 20 s for six criteria.

Verdict rule (policy, fixed): a 0 on any gating criterion is a hard fail (all finals are hero views); two or more gating 1s escalate to FAIL; a gating criterion that did not run, or an unreachable VLM, makes the verdict `fail` (fail closed). Gating criteria: R1, R2, R3, R4, R10, R12 always; VLM R8 and R11 chosen on the tuning half (R10 has a pixel part and always gates). R5, R7, R9, R13 are scored and reported but do not gate.

## Calibration protocol and what was actually done

1. **Pre-registration** (commit `c656192`, before any image was scored by any model): label tiers, split seed and rule, thresholds, VLM prompts v0, escalation rule, gate-selection rule, targets. Tiers: must_fail = D+, D, D-, F (18 views); should_pass = B- or better (A, A-, B+, B, B-; 5 views; only v34 is a full B); middle = C+, C, C- (15 views, reported, not scored against a target). Split: per grade, order by sha256(seed:view), deal alternately; v27 forced into tuning because it was shown to three models in a probe. Tuning 20 views (10 must_fail, 3 should_pass, 7 middle), held-out 18 (8, 2, 8). The held-out list was `v02 v03 v04 v09 v13 v15 v17 v20 v21 v23 v25 v26 v30 v32 v33 v35 v39 v40`; no held-out image was scored or read until the freeze.
2. **Tuning** on the 20 tuning views only (amendments A1-A6 in `rubric.json`, evidence in each):
   - A1 R12: v0 used red-minus-blue for warm limits and failed 11 of 20 tuning views including B and B- (a unit error against render_qa's cast-magnitude limit). Warm now uses cast magnitude; green is informational because gardens are green.
   - A2 R10 seams: the pixel seam detector missed the known v27 seam and flagged 7 of 20 views on real wall edges, so seams are left to the VLM; the band detector still gates (v19).
   - A3 R3: the first lean estimator followed foliage (2-4 deg on garden views); replaced by the coherent-edge version.
   - A4 VLM prompts: gemma4:31b with single-image anchors scored 0 on R7/R8/R9 for 20 of 20 tuning views (`knowledge/critic/runs/tuning/gemma4_31b_v0`), failing every good view. Reference-relative prompts (v1) fixed that.
   - Model: gemma4:31b, qwen3.6:35b-a3b and qwen3.8:27b-mtp-q4_K_M, all accept images. Selected by the summed gate-selection separation on the tuning half (`scripts/critic_model_compare.py`): qwen3.8 1.43, gemma4 1.17, qwen3.6 1.10. The selection rule was written down when 7 qwen3.8 rows had already been read.
   - Gating by the pre-registered rule (separation >= 0.30 and no should_pass view scoring 0): R8 0.47, R10 0.47, R11 0.47 gate; R5 0.07, R7 -0.23, R9 0.20, R13 0.00 do not.
   - Tuning result with the frozen rubric: recall on must_fail 10/10, false-fail on should_pass 1/3 (v34, B), C-or-worse 16/17, seeded false passes 14/14. This already missed the false-fail target and no further prompt tuning was done to fix it.
3. **Freeze** (commit `6c07dde`, rubric `frozen-v1`), then the held-out half was scored once (`knowledge/critic/runs/held_out/`, `scripts/critic_calibrate.py --split held_out --gates R8,R10,R11`; the script refuses held-out scoring unless the rubric version starts with `frozen`).
4. **After the freeze** one code change: a gating criterion that is not evaluated now makes the verdict fail (the rule was already pre-registered as fail closed, but `decide()` only recorded it). No held-out verdict changed. One slip to disclose: before the freeze I ran the CLI over the whole finals directory with the VLM off; I printed only the fail count and two clone lists, not per-view scores.

## Held-out results (18 views, frozen-v1, qwen3.8:27b-mtp-q4_K_M)

| human grade | verdict | views |
|---|---|---|
| B- (should pass) | pass 1, **fail 1** | v33 pass; v21 fail |
| C+ | pass 1, fail 1 | v09 pass; v02 fail |
| C | fail 3 | v17, v20, v23 |
| C- | pass 1, fail 2 | v25 pass; v04, v32 fail |
| D+ | fail 4 | v13, v35, v39, v40 |
| D | fail 3 | v03, v15, v26 |
| F | fail 1 | v30 |

| measure | held-out | target | tuning | all 38 |
|---|---|---|---|---|
| recall on D+/D/F | 8/8 = 100 % | >= 90 % | 10/10 | 18/18 |
| false-fail on B- or better | 1/2 = 50 % | <= 10 % | 1/3 | 2/5 |
| fails of C-or-worse views | 14/16 | not set | 16/17 | 30/33 |
| fails of the audit's seeded QA false passes | 12/13 | seeded recall reported before gating | 14/14 | 26/27 |
| fails of C+/C/C- | 6/8 | none | 6/7 | 12/15 |

Targets: recall met, false-fail **missed**. With 8 must_fail views the one-sided 95 % lower bound on 8/8 is about 69 %; with 2 good views a 0/2 result would also carry no weight. Treat the recall as promising and the false-fail rate as unresolved: five good views are too few to estimate a 10 % rate.

Ablation, post hoc and not used for any decision: deterministic checks plus the VLM R10 alone (no R8/R11 gating) on all 38 views give recall 16/18 and false-fail 2/5; adding R8 and R11 gating raises recall to 18/18 with the same two false fails.

## Failure examples

- **False fail, v21 (B-, held-out).** R3 = 0: the left column bin shows a 1.93 deg lean while the other four bins show 0.0-0.1 deg; the audit notes the stair "still slices the left edge", so the measured lean is most likely a slanted stair element, not camera tilt (cause not verified beyond the bin location). R11 = 0: the model called the room daytime against the title "Street lounge at night"; the render is lit as evening. One deterministic false positive and one VLM misreading made a hard fail.
- **False fail, v34 (B, tuning).** R4 = 1 from 2 % clipping inside the subject box (window glare, which the audit also notes) plus an R10 = 1 from the VLM.
- **Pass despite defects, v09 (C+).** The model, like gemma, saw the over-scaled wood grain (R7 = 1) and the sparse styling (R11 = 1), but R7 does not gate and one gating warn is not enough. v25 (C-, a seeded false pass: clay neighbours, faceted pots) passes with R5 = 1 (non-gating) and R8 = 1 (one gating warn).
- **Deterministic catches.** R4 alone scores 0 on v03, v04, v20, v23, v30 and v32 in the held-out half (crushed or clipped subject), R12 fails v15 (blue cast) and v39 (cyan cast), R1 contributes the 16 mm warn that pushes v17, v20, v35 and v15 over the escalation line.
- **Weak VLM criteria.** R13 (benchmark parity) says "both are renders" for almost everything, including the good views (qwen3.8 gives 0 to v05, a B-): no separation, so it does not gate. R5 (context) and R9 (contact) do not separate the groups either; gemma4 separated R7 (material scale) while qwen3.8 did not, and no single model was best on every criterion.

## Known weaknesses

- Five should-pass views in total (three in tuning), so gate selection and the false-fail rate are noisy; the held-out false-fail target was missed.
- Prompts and gating were tuned once on 20 views and the model was chosen on them; some optimism is built into the tuning numbers.
- R3 pixel lean flags slanted architecture (stairs, sloped panels: v21, v31). Bent wall and ceiling lines (v08, v30) are not detected by any deterministic check; only the VLM R10 prompt mentions them.
- The seam detector is informational only: it could not separate the v27 seam from wall edges. Seams rely on the VLM.
- R4 uses generous boxes; a window inside the subject box counts against exposure.
- R12 implements the mid-tone cast only; the wood/stone hue limit named in the criterion is not implemented. R6 is out of scope.
- The cross-view clone report (`meta.clone_report`, shown as `notes.cloned_assets` in directory mode) projects model bounds without occlusion, so it over-counts (12 views for the sofa against the audit's 7). It is informational and not part of the verdict.
- R2 uses an assumed floor datum (-3.0 / 0.0 m); all views are at 1.35 m by construction, so R2 never discriminates.
- VLM outputs are not perfectly repeatable across Ollama versions; one batch of R13 calls had a JSON truncation (fixed with a retry at triple `num_predict`; unparsable replies become `not_evaluated`).

## Files

`src/archpipe/critic/` (labels, meta, pixels, vlm, verdict, calibrate), `knowledge/critic/` (rubric.json, split.json, runs/tuning, runs/held_out), `scripts/critic_run.py` (CLI), `critic_vlm_batch.py` (workstation batch), `critic_calibrate.py`, `critic_model_compare.py`, `critic_show.py`, `critic_report.py`, `critic_make_v1.py`, `critic_freeze.py`, `tests/critic/` (40 tests, VLM mocked).
