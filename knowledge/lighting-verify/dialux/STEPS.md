# DIALux evo cross-check (V11) - one sitting on the laptop

Pass bar (docs/quality/LIGHTING-VERIFICATION.md): average illuminance Em within +/-10 %, Emin and U0 within +/-15 % of the
engine, on every plane below, in each of the three spaces. Spaces: `B-open` (contains the dining and kitchen planes),
`GF-family-bath`, `GF-parents-bed`.

For each space folder (`B-open/`, `GF-family-bath/`, `GF-parents-bed/`):

1. New project -> new room by importing `room.dxf` (metres; FLOOR and CEILING outlines at their elevations). If the importer
   keeps only 2D, draw the floor outline from FLOOR and set room height = CEILING elevation - FLOOR elevation (given in the file's header
   of `planes.csv` z values: floor z is the lowest elevation). Walls straight, no windows, no doors, no furniture, no daylight.
2. Surfaces: ceiling 85 %, walls 80 %, floor 33 % (`reflectances.json`). Maintenance factor 0.80 on all luminaires.
3. Luminaires: import `ies/*.ies` as user photometry. Place one luminaire per row of `luminaires.csv` at (x, y, z) in the same
   coordinates (z absolute; the floor is `FLOOR` elevation). Aim with tilt `tilt_from_nadir_deg` toward azimuth `tilt_azimuth_deg`
   (0 deg = +x, counter-clockwise). Set the dimming of each luminaire to `flux_scale` x 100 % relative to the file's own lumens
   (the generic `generic-*.ies` files are already at their design flux: use `flux_scale` = 1 only if it is 1, else follow the column).
   Rows with `layer` = night or emergency are OFF.
4. Calculation surfaces: one per row of `planes.csv`: a horizontal plane at height `z` (absolute) over the polygon, grid about
   0.2-0.3 m, no border. Use the same names as `id`.
5. Run a full calculation (direct + indirect). Read Em, Emin and Emin/Em (U0) per plane into `results-dialux.json`
   as `{"<plane id>": {"Em": .., "Emin": .., "U0": ..}}` in the space folder.
6. Tell the lead; `python -m archpipe.lightverify.dialux_compare` (to be run on the workstation) reads these files against
   `expected-engine.json` and applies the pass bar.
