# L6 lighting engine

Package `src/archpipe/lightcalc/` (stdlib only; imports `archpipe.photometry` and `archpipe.radiance` helpers, edits neither).
Tests: `PYTHONPATH=src python -m pytest tests/lightcalc -q` (53 pass, 1 skipped: the live Radiance run needs `ARCHPIPE_L6_SSH` or a local Radiance).
Results: `out/checks/L6.json` (copy committed at `knowledge/lighting/checks/L6.json`), reference run `knowledge/lighting/L6-reference-results.json`, dining run `knowledge/lighting/L6-dining-result.json`.

## What it does

| module | role |
|---|---|
| `geometry` | non-convex polygon rooms: area, point-in-polygon, cell-centred grids inside any outline, EN 12464-1 cell size p = 0.2 * 5^log10(d), outward wall normals |
| `direct` | analytic direct light from IES photometry with aim/spin (same frame as the Radiance `xform` chain), luminance toward an observer, ULR |
| `radjob` | Radiance total-light job for any polygon: floor, ceiling, one wall per edge, per-class reflectance, boxes, one octree per control zone, `rtrace -I+ -ab N` at N and 2N (convergence). Writes `run.sh`; runs locally or over ssh on the workstation (Radiance 6.0.1) |
| `roomcalc` | task planes (Em, Emin, Emax, U0, max:avg, avg:min), scenes (dim level per zone, exact linear recombination of per-zone results, MF applied once), LA1-LA3 per scene |
| `checks` | `CheckResult` emitters: LA1, LA2, LA3, LA4 (UGR limit and luminance), LA9, LA12, LA13 |
| `ugr` | CIE 117 UGR formula, Guth position index, reference tables |
| `sources` | every threshold as a `SourceCard` (sourced / std / policy / unverified) |
| `refcases`, `dining`, `emit` | reference cases, D1 dining smoke run, `out/checks/L6.json` |

Scenes: dimming is assumed to scale photometric output linearly (stated; real drivers can differ at low levels).
Radiance parameters: `-ab 6` and `-ab 12` (cube cases `-ab 8/16` and `21/42`), `-ad 1024-2048`, `-lw 1e-6`, `-lr 12`; every report carries both bounce counts.

## Reference cases (expected vs achieved)

Source of the expected values: **CIE 171:2006** test cases 5.2 and 5.8, **as reproduced in** DAU Design and Consulting, "Validation of NVIDIA Iray against CIE 171:2006" (2016), Tables 7 and 15. The CIE report itself is paywalled and not held. DAU Table 19 (case 5.7) is flagged there as wrong in the original, so 5.7 is not used. The Iray program's own results are not used as expected values. Tolerance from the LA1 row: +/-5 %.

**Case 5.2, point source, diffuse photometry I = 1000 cos(theta) cd, 10 points 3 m below.** Expected E = 111.11, 105.21, 90.02, 71.11, 99.73, 85.64, 68.06, 74.36, 59.98, 49.39 lx.
Achieved: Radiance max error **0.039 %**, analytic engine max error 0.044 % (all 10 points). The published rows also satisfy E = I cos(i)/d^2 to 0.2 %, which is tested (guards the transcription). The point coordinates are derived from the published d and incidence columns (the text layer carries no coordinates); every derived d matches the published d to 0.002 m. The second photometry column of that table (T9 measured file) was not used: its intensity table is not held.

**Case 5.8, 4 x 4 x 4 m room, all surfaces diffuse, isotropic 10,000 lm source at the centre.** Expected = average indirect illuminance over the six surfaces (`Eav`), equal to the closed form Phi rho / (A (1 - rho)), A = 96 m2. Sensors: 6 x 6 cell-centred points per face, normals inward; indirect = total (ab N) minus direct (ab 0).

| rho | published Eav (lx) | achieved (ab 2N) | error | ab N vs 2N |
|---|---|---|---|---|
| 0.2 | 26.00 | 26.31 | +1.2 % | -0.01 % |
| 0.5 | 104.00 | 105.08 | +1.0 % | -0.14 % |
| 0.8 | 417.00 | 407.63 | -2.3 % | -0.01 % |

All inside +/-5 %. Truncation after N bounces is about rho^N of the indirect term; N = 8, 8, 21 were chosen so that it is under 1 %, and N versus 2N agree to 0.14 % or better. The -2.3 % at rho 0.8 is Radiance's irradiance-cache accuracy (`-aa 0.1`) at high rho; it is not a bounce-count effect.

**Analytic versus Radiance on the real iGuzzini file** (aimed LSEVO-AAHENX spots in the dining run, 18 table points): max difference 0.06 %. This validates the aim/spin convention and the `ies2rad` scaling for a real photometry file. Both paths read the same IES, so it is a consistency check between two implementations, not an independent photometric proof.

**UGR.** No published worked example with its inputs could be obtained: CIE 190:2010's example is paywalled; the held SLL Code (chapter 12, Table 12.5) prints a UGR table without the luminaire's photometry; no manufacturer UGR table with its LDT was found. The LA4 acceptance ("CIE 190 example exact, one manufacturer table within +/-1") is therefore **not demonstrated** and `out/checks/L6.json` carries it as `not_evaluated`. What was validated instead, against held pages:
- Flux correction 8 log10(Phi/1000) against all 49 printed values of SLL Table 12.6 (printed p. 198): max difference 0.05 UGR.
- Position index: SLL eq. gives K = pi / (4 p^2 D^2) (printed p. 209); computing K from our Guth index at 27 transcribed cells of Table 12.10 gives max error 7.5 %, mean 4.8 % (K goes as p^-2, so p is within about 4 %). The IES HB10 eq. 10.36 print (p. 10.35) was rejected: it evaluates to 10.36 on the line of sight (the equation number is typeset into the formula) and has lost the alpha terms. The Guth coefficients used are the CIE 117 form, which no held page prints legibly, so the position index is **validated, not sourced**, and `check_la4_ugr` can only `warn` (never `fail`) until it is carded.
- Formula arithmetic by hand for a single source; doubling flux raises UGR by 8 log10 2 = 2.408 (Table 12.6: 2.4).

## Dining smoke run (D1 dining area, L-shaped, 6 vertices)

Inputs: L2 model (`archpipe.model.load("D1")`), frozen at `knowledge/lighting/d1-dining-input.json`; table plane = table top at z = -2.25 (1.8 x 0.9 m), card `ies-res-dining-informal-100` = 100 lx; reflectances from the render's own materials (wall 0.80, ceiling 0.85, floor 0.33, ASSUMED finishes); MF 0.8; walls closed on all sides (the real zone is open to the kitchen and entry, so inter-reflection is overstated). No furniture or doors in the Radiance scene.

The brief's 797 lx is not reproduced by any set. Two sets exist and both are reported:
- **model** (L2 model: 4 recessed adjustable spots, real iGuzzini LSEVO-AAHENX, + the linear pendant PEN-LIN, **generic** photometry 1200 lm / 90 deg, split into 8 point sources along 1.6 m): table Em **709 lx** (Emin 289, Emax 1334, U0 0.41) = **7.09 x target**.
- **built** (what `scene.json` lists as lights in the dining area: the 4 spots only; the pendant exists there only as an emissive mesh): table Em **390 lx** (Emin 73, Emax 875, U0 0.19) = **3.90 x target**.

**LA2 fails in both** (cap 150 lx = 1.5 x 100): 709 and 390 lx. LA1 also fails (allowed 90-110 lx). LA3 is reported (U0 0.41 / 0.19, max:avg 1.88 / 2.24, avg:min 2.46 / 5.36).
**Dimmed scene** (per-scene recompute): sideboard accent kept at 100 %, table-lighting zones at f = 0.13 (model) or 0.23 (built), solved from the linear model so that Em = 100 lx: LA1 pass, LA2 pass (1.00 x target), U0 0.45 / 0.25. f is derived from the target for the illustration, not a design decision.

**Resolved by L6b (2026-11-20, docs/lanes/L6b-villa-lighting.md):** the 963 lx is total light (direct 939); the Cycles probe 405 lx is the vase-obstructed reading (a Cycles replay with the vase on the sensor gives 403 lx, the recorded file 405; the same scene without the vase gives 952 lx direct, equal to this engine at the rendered emitter height). The engine is right; `lighting-measurements.json` (Sep 28) is stale and its centre point sat under `dining-vase`.

## Checks and tests (positive and negative for each)

LA1 band edges and minimum-gauged; LA2 at 149/150/150.1 lx and the 797 lx case; LA3 reporting and limits; LA4 UGR limit (unverified position index warns, never fails; no luminance => `not_evaluated`), luminance cap with shielded, outside-cone and point-opening cases; LA9 axis tolerance 9 mm pass / 11 mm fail, grid mode, spacing over SHR, wall-wash setback (unverified card => `warn`); LA12 boundary Ev both curfew columns, intensity, ULR (uplight fails), facade Lb; LA13 route pass / too far / no luminaires; scene recombination and per-scene LA1/LA2 flips; polygon wall generation, `run.sh`, output parsing and truncated-output rejection.

## Sources and policy

Sourced (quote from held page): IES HB10 p. 33.25 (+/-10 %, minima/maxima), uniformity targets; SLL Table 3.2 E3 (printed p. 90); SLL eq. 12.16, Tables 12.6 and 12.10. Policy (ours): LA2 1.5 x, LA4 3,000 cd/m2, LA9 10 mm tolerance. `std` (standard not held): EN 12464-1 U0 0.6, UGR 19 (via the ZVEI paper's quotation of the DIN EN 12464-1 table), EN 1838 1 lx, CIE 171 values (via DAU). `unverified`: wall-wash setback 0.6-1.0 m.
**SLL Table 3.2 ULR:** the printed column header says `%` but the printed values are 0 / 0.05 / 0.15 / 0.25; the engine reads 0.15 as a fraction (15 %), as the criteria document does.

## Gaps

- LA4 UGR worked example and manufacturer table: not reproduced (above). The tabular method is not implemented (only the basic formula); UGR also needs `Lb` from a Radiance vertical-eye sensor (indirect = ab N minus ab 0), which is a few lines in `radjob` but was not run.
- LA13: the 1 h duration cannot be computed; only the 1 lx centre line (direct light, no edges check). LA12: boundary Ev and facade luminance take pre-computed values; no exterior Radiance grid.
- LA9: the RCP check validates a given layout; it does not solve a layout (task L3 in the panel review).
- No sDA/ASE/DGP (LA14), no Ez/vertical grids (LA5), no scene CSV export (LA10).
- Luminaires are point sources (flat luminous opening used only for luminance); a linear pendant is approximated by 8 points. The dining pendant photometry is generic.
- Radiance noise: Monte-Carlo, no fixed seed; repeat-run variance was not measured (ab N versus 2N agree to 0.14 % or better on the cube cases and 2 % on the dimmed dining scene).

## Model gaps reported to the coordinator

- `PEN-LIN` over the dining table has no product (generic photometry, `watts` None, `length_mm` 0.0 although the fixture is 1.6 m; the length comes from the kind spec) and the `emitter_z_scene_mm` field is the only absolute height.
- The model holds a dining pendant that the built `scene.json` lists only as an emissive mesh, not as a light: the two sets disagree.
- Room `open_to` lists neighbours but there are no wall openings or door/window records to close or open a polygon's edges for Radiance.
- `placement.z` for luminaires is height above level FFL (2700 for a recessed spot) while `emitter_z_scene_mm` is absolute; the engine uses FFL + z with B at -3.0 m.
- The table's dressing (the vase at the task point) is not in the model.
