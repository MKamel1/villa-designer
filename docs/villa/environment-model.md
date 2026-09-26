# Villa environment model (2026-09-25, revised with the client's answers)

**The model** is `out/villa/omar-env.rvt` (Revit 2027; not in git). It was built from a copy of `omar.rvt` by
`revit/build_villa_env.py`, using the spec that `src/archpipe/villa_env.py` generates.

**How it was checked:** `scripts/villa_env.py check` reads the geometry back from the built model and compares it
with the spec: levels, site, true north, every element, every slab and all 27 columns. Result: **PASS**.
`tests/test_villa_env.py` (16 tests) checks the spec against independent evidence, and proves the checker catches
drift.

**For review:**
- the site plan, drawn from the read-back geometry: `out/villa/env-site-plan.pdf`;
- the Revit views: `out/villa/env-view - *.jpg`.

## Sources and their authority (client, 2026-09-25)

| Source | Authority | What it gave |
|---|---|---|
| CAD `01-GROUND_FLOOR_PLAN.dwg` and Revit `omar.rvt` | **Structure and building geometry** | Outline 18.98 × 5.08 m, our GF bathroom (19.60–22.32), 9 columns, the twin's mirror axis |
| Old PDFs `2- Basement…` and `4- Ground floor… furniture plan` | **Fence offsets and the shared core only.** They MUST NOT inform the space layout. | Fence 0.25 thick; face to fence inner face: street 3.74 (the 4.02 dimension is to the outer face), east 2.99, rear 5.71; the core's contents and positions (±0.15 m) |
| Brief and client answers | Programme, levels, heights | Street 0; basement −1.80; GF +1.20; fence 4 m from basement; neighbours 12 m; the apartment above |
| Maps link | Site | 30.04026 N, 30.96110 E; street facade azimuth 290° |

**How the PDF was measured:** the sheet was scaled on the CAD building length, 124.5 px/m at zoom 3, and
cross-checked against the core's printed clear width (2.51 m printed, 2.48–2.54 m measured).

## The shared core (not ours)

The 2.49 m strip between the two villas is the building's shared core. The apartments are reached from it by the
main stair. From the street end to the rear, on the GF:

| Segment | x (m) |
|---|---|
| Entrance (the steps from the street gate cross the sunken front yard) | 3.62–8.51 |
| Main stair | 8.51–12.78 |
| Landing and **air shaft** (1.5 m wide, beside our party wall, all floors) | 12.78–14.13 |
| Lobby with doors to both villas | 14.13–15.93 |
| **Lift**, read from an X box with a 0.80 m door on both floors (OPEN) | 15.93–17.41 |
| The sister's bathroom | 17.41–19.60 |
| **Our bathroom** | 19.60–22.32 |

**Basement.** The core's two ends are split on the axis between the villas: the front up to x ≈ 6.94, and the rear
from x ≈ 17.27. Our basement is therefore the bar plus those two halves. The middle stays shared: lobby, stair, shaft
and lift.

**The apartment storey** repeats the GF (assumed).

## Consequences for the concepts

- The party wall faces the core. Its only daylight or ventilation opportunity is the shared air shaft
  (x 12.8–14.1).
- Daylight and views come from three facades:
  - the street (WNW, 290°);
  - the plot-east facade (20°, facing a 12 m neighbour 6.2 m away);
  - the rear (110°, 5.7 m of yard).
- The apartment's weight and wet stacks sit on our GF. The columns and perimeter beams are fixed.
- The street-side strip (CAD 1.83 × 5.08 m) is ours, at GF, with no use yet. Opening it to the living room is a
  concept decision.

## Confirmed assumptions

- The apartment's floor-to-floor height is 3.0 m.
- The neighbours are 12 m tall measured from their basement level, with windows like ours on every storey.
- Beams are 250 × 600.
- The street is 10 m wide (context only), and there is no fence between the two yards.

## Rebuild

```powershell
$env:PYTHONPATH="src"; .\.venv\Scripts\python.exe scripts\villa_env.py spec
$env:ARCHPIPE_MODEL="$PWD\out\villa\omar-2027.rvt"; $env:ARCHPIPE_ENV_SPEC="$PWD\out\villa\env-spec.json"
$env:ARCHPIPE_ENV_OUT="$PWD\out\villa\omar-env.rvt"; $env:ARCHPIPE_ENV_READBACK="$PWD\out\villa\env-readback.json"
& "$env:APPDATA\pyRevit-Master\bin\pyrevit.exe" run "$PWD\revit\build_villa_env.py" --revit=2027
.\.venv\Scripts\python.exe scripts\villa_env.py check; .\.venv\Scripts\python.exe scripts\villa_env.py plan
```

The builder refuses to overwrite `omar-env.rvt`; delete or rename it first.
