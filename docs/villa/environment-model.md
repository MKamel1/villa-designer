# Villa environment model (2026-09-25)

**The model** is `out/villa/omar-env.rvt` (Revit 2027; not in git). It was built from a copy of `omar.rvt` by
`revit/build_villa_env.py`, using the spec that `src/archpipe/villa_env.py` generates.

**How it was checked:** `scripts/villa_env.py check` reads the geometry back from the built model and compares it
with the spec: levels, site, true north, every context element, every slab and all 27 columns. Result: **PASS**.
`tests/test_villa_env.py` checks the spec itself against independent evidence, and proves the checker catches
drift.

**For review:**
- the site plan, drawn from the read-back geometry: `out/villa/env-site-plan.pdf`;
- the Revit views: `out/villa/env-view - *.jpg`.

Your original file is unchanged: the pre-upgrade backup `omar.0001.rvt` has the SHA-256 recorded before any run.

## Sources

| Source | What it gave |
|---|---|
| CAD `omar - Floor Plan - 01-GROUND_FLOOR_PLAN.dwg` (m, same coordinates as Revit) | Building outline 18.98 × 5.08 m plus the bathroom projection; the street-side terrace; the 9 column positions (they match the Revit GF columns to < 1 mm); current window positions |
| Revit `omar.rvt` (read in 2027) | One level, GF at 0; columns 0–3000; the sister's columns, which fix the twin's mirror axis at y = −29 915.66 (tested); the yard floor edge exactly 2.5 m past the plot-east face |
| Brief (`brief-2026-09.md`) | Levels (street 0, basement −1.80, GF +1.20); yard offsets 2.5 / 2.5 / 5.0; sunken yard; 4 m fence from basement; neighbours 12 m; the apartment above; keep columns and beams |
| Maps link | 30.04026 N, 30.96110 E (Sheikh Zayed); street facade azimuth 290° |

## What the model contains

- **Orientation.** Model −x is plot-north (the street), +y is plot-east, and +x is the rear. True north is set so
  that the street facade reads back at 290.00°.
- **Levels:**

  | Level | Height against street |
  |---|---|
  | Street | ±0.00 |
  | Basement (B) | −1.80 |
  | Ground floor (GF) | +1.20 |
  | Apartment (not ours) | +4.20 |
  | Apartment roof | +7.20 |

- **Structure to keep:**
  - the 9 existing GF columns, repeated on the basement and apartment storeys (27 in total);
  - perimeter beams 250 × 600 under the GF, apartment and roof slabs;
  - our slabs follow the CAD outline.
- **Plot and yard:**
  - the plot is 26.48 × 17.65 m (ours plus the sister's);
  - our yard is sunken at −1.80 (133.9 m²), made up of the east strip, our halves of the street and rear strips, and our half of the gap to the sister;
  - the sister's yard is mirrored.
- **Fence:** concrete, 200 mm thick, around the whole plot, from −1.80 to +2.20. That is 2.20 m above the street.
- **Neighbours:**
  - east, rear and rear-east blocks, each 12 m tall;
  - their facades facing us carry windows on every storey;
  - the street is drawn in front.
- **Our block:**
  - the apartment above (the same outline, +4.20 to +7.00);
  - the sister villa with its own apartment, mirrored.
- **Removed from the copy:** three floors that covered the whole plot at GF and at +2.9–3.1. They contradicted the
  sunken yard, and 22 dependent elements went with them. The existing walls, doors, furniture and interior are left
  in place and are ignored, as you instructed.

## Assumptions to confirm

1. The apartment's floor-to-floor height is 3.00 m, the same as ours. The old Revit slab sat 100 mm higher, which is
   within the close-value band.
2. The 2.5 m street-side offset is measured from the building face, which puts the plot edge at x = 1117. The old
   Revit yard floor stopped 2.74 m out, a 10 % difference.
3. The street-side enclosure (1.83 m deep, walls on the CAD's I-WALL layer) is a ground-floor terrace or entrance
   landing over the sunken yard. The apartment repeats it.
4. The neighbours are 12 m tall measured from their basement level, i.e. four 3 m storeys. Their windows are at our
   current window positions (sill 0.9 m, height 1.5 m).
5. The neighbour plots mirror ours: the east building is 2.5 m from the shared fence and the rear building 5.0 m.
6. The beam section is 250 × 600, with the outer face flush to the building face.
7. The sister mirrors our bar and terrace. The bathroom projection is ours only.
8. There is no fence between our yard and the sister's yard.
9. The street is 10 m wide. It is drawn for context only.

## Questions (they affect the concepts)

1. The party-side facade (the one facing the sister) has columns only at its two ends, an **18.98 m span**. Are
   there columns or bearing walls along it that the model is missing?
2. Is the bathroom projection (2.72 × 2.64 m) ours, and does it reach the sister's facade? It extends 0.15 m past
   the sister's face line.
3. **How is the apartment above reached** (stair, lift, entrance), and does that route cross our plot or our floor?
4. How do people get from the street (±0.00) down to the yard (−1.80) and up to the ground floor (+1.20)?
5. Is the 2.49 m gap between the two buildings ours up to the mirror line, and is there a divider?
6. Revit has a column at x 22.4, y −31.4, on the sister side at the projection's corner, that the CAD does not show.
   I kept it as it is and did not repeat it on other floors.

## Rebuild

```powershell
$env:PYTHONPATH="src"; python scripts\villa_env.py spec
$env:ARCHPIPE_MODEL="$PWD\out\villa\omar-2027.rvt"; $env:ARCHPIPE_ENV_SPEC="$PWD\out\villa\env-spec.json"
$env:ARCHPIPE_ENV_OUT="$PWD\out\villa\omar-env.rvt"; $env:ARCHPIPE_ENV_READBACK="$PWD\out\villa\env-readback.json"
& "$env:APPDATA\pyRevit-Master\bin\pyrevit.exe" run "$PWD\revit\build_villa_env.py" --revit=2027
python scripts\villa_env.py check; python scripts\villa_env.py plan
```

The builder refuses to overwrite `omar-env.rvt`; delete or rename it first.
