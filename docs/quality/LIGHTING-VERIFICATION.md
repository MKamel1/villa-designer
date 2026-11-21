# Lighting verification — how we know the lux numbers are right

Why: the lighting engine (src/archpipe/lightcalc, lanes L6/L6b) is the only source of lux numbers for the
villa. The October process passed its own checks while reading the dining table at 405 lx instead of
~950 lx (a vase on the sensor), and a spec said 750 lm where the bound product emits 1343 lm. Nothing
independent caught either. From now on a lighting result is accepted only if it survives the checks
below, run by a lane (LV) that does not own the engine and may not edit it.

## Layers of verification

| # | Layer | What it catches | Method | Pass bar |
|---|---|---|---|---|
| V1 | **Input integrity** | wrong lumens, wrong file, wrong units, spec≠product | For every bound luminaire: integrate the IES/LDT candela distribution → total lumens and compare to the file's stated lumens and the manufacturer datasheet; check watts, CCT, beam; spec values must equal the bound product or be flagged | Integrated vs stated lumens within 2 %; zero unexplained spec≠product rows |
| V2 | **Geometry and placement** | fittings in the wrong place, wrong height or datum, wrong aim, emitter inside the ceiling | Emitter positions vs the design model (ceiling height, host, room); aim vectors vs intent; datum consistency (B −1.80 / scene −3.00) | Every emitter inside its room, below its ceiling, within 10 mm of the model |
| V3 | **Measurement validity** | the vase class: sensors inside or under objects, wrong plane, wrong grid | Every sensor point tested against all scene geometry (not just the dressing list); task planes at the right height above the surface they sit on; grid spacing per EN 12464-1 rule | Zero sensors inside or occluded by an object within 50 mm; planes within 5 mm of the surface |
| V4 | **Published reference cases** | engine physics errors | CIE 171:2006 cases (point source, area source, inter-reflection cube, obstruction, ...) — as many as are published with values; extend beyond 5.2/5.8 | Each within the published tolerance (±5 % default) |
| V5 | **Three independent engines** | an engine-specific bug | Same rooms computed by (a) analytic direct, (b) Radiance total, (c) Cycles calibrated photometric render (different code base). Direct light must agree a↔b↔c; total light b↔c | Direct within 3 %; total within 10 %, on at least 6 villa rooms covering open plan, small wet room, stair |
| V6 | **Hand calculation** | gross errors, unit slips | Lumen method per room: E ≈ N·Φ·UF·MF / A with UF from room index and reflectances | Engine average within ±25 % of the lumen-method estimate, or the difference explained |
| V7 | **Convergence and settings** | under-sampled results | Re-run with doubled ambient bounces/divisions and grid density | Change < 3 % |
| V8 | **Mutation tests** | a verification that cannot fail | Seed known errors (double a lumen value, move a sensor into a vase, shift a fitting 300 mm into the ceiling, swap a datum, rotate an IES 90°) and confirm V1–V7 flag each | 100 % of seeded errors caught |
| V9 | **Physical measurement** (client option) | everything the models share | Measure a real room with a lux meter and compare to the engine model of that room | Within ±15 % (meter accuracy ±5–10 %) |

V1–V8 run automatically on every lighting change and gate the merge. V9 is the only check that does not
share assumptions with the software; it needs a lux meter and a real room (client decision).

## Acceptance

A lighting result (per room, per scene) is reported with its verification status: inputs verified,
placement verified, sensors valid, engines agree (with numbers), hand-calc agreement, convergence. A
room that fails any layer is shown as "unverified", never as a pass.
