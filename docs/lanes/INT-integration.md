# INT: integration after the L6b/LV lighting redesign (2026-11-21)

**Re-run (after L6c or any lighting/model change):** `python -m archpipe.exchange.integrate` (add `--skip-snapshot` if the model snapshot is
already current; the snapshot step is ~6 min, everything else ~1 min plus the suite). Steps: model snapshot, electrical design on the
real zones (writes `docs/lanes/L7b-d1/` and `tests/electrical/d1/`), exchange (IFC/DXF/quantities + validation), drawing set and the committed sample
schedules, then the lane suite (plus, since INT2, `tests/test_mounting*.py tests/test_d1_*.py tests/test_exposure_groups.py tests/test_villa_lighting.py`: the scene-building tests; `integrate` runs them). Then `python -m archpipe.compliance.run_d1` (0 failing gates; `git checkout` the regenerated L1 report) and
`python scripts/lane_guard.py INT`.

## Broken tests, cause, fix

| test | cause | fix |
|---|---|---|
| `tests/electrical/test_villa.py::test_d1_no_failures` (EA3, EA13) | the committed model snapshot still held the old 142-luminaire design, so zones-d1.json ids did not match; after the snapshot was regenerated, two real defects remained: (a) circuits skipped `emergency`-layer zones, leaving 9 escape/night markers (4 zones) on no circuit; (b) L6b zone W is the commissioned (dimmed) output, below the rated luminaire W in 12 zones, so circuit W != sum of luminaire W | (a) one dedicated "Escape/night marker lighting" circuit per board (`DB-B/L3`, `DB-GF/L3`); (b) zones are sized on the higher of published and rated luminaire W (conservative; flagged in `h.flags`). Guard: EA3/EA13 plus `test_d1_uses_the_real_l6b_lighting_zones` |
| `..._lighting_zones_are_marked_provisional_when_l6b_is_absent` | asserted the provisional branch while `zones-d1.json` exists (the `else` branch was dead) | replaced by a real-zones test (69 zones, none provisional, escape circuit present) and a negative test that monkeypatches the file away and expects `Z-PROV-*` |
| `tests/exchange` 10 errors | the `out` fixture builds D1-LIGHT/ELEC from the committed electrical CSVs and the model: the CSVs listed old luminaire ids that were not in the model ("device_list luminaires not in the model"). Same stale-snapshot cause | regenerated model + electrical outputs (this lane); no exchange code change needed for the errors |
| `test_elec_counts_match_electrical_outputs` | hard-coded 59 systems; now 58 final circuits + 2 feeders = 60 | test reads `tests/electrical/d1/summary.json` and asserts 60 |
| exchange zones | `build` still labelled every zone "provisional" and ignored L6b layer/dimming | `exchange/disciplines.py` reads `zones-d1.json` (Layer, Dimming, Basis); new test `test_light_zones_are_the_published_l6b_zones` (69 groups, no `Z-PROV-*`) |
| `tests/drawings2d::test_schedules_cover_model` | hard-coded 142 luminaires | 136, and tied to the model's luminaire count; committed sample schedules refreshed |
| `tests/model::test_counts_by_kind` | 142 luminaires | 136 |
| `tests/model::test_luminaires_carry_photometry_ref` | `> 80` luminaires with an IES; the redesign has 73. **Not an export defect**: all 63 others are `generic: True` with no product (strips, pendants, task lamps, markers), by design of L6b | exact 73 plus a stricter check that every luminaire without an IES is explicitly generic with no code and no product id (63). **For L6c:** re-binding more luminaires to products should raise the 73; update the two numbers |

## Results

* Electrical: maximum demand **77.4 kVA** (352 A single-phase equivalent, 117.5 A worst phase, three-phase), 58 final circuits (6 lighting) + 2 feeders,
  MDB 8/10, DB-B 32/40, DB-GF 20/26 ways; EA: 0 fail. Detail in `L7b-villa-electrical.md`.
* Exchange: validation **59 checks, 0 failed** (ARCH 20, LIGHT 14, ELEC 6, shared origin 1, quantities 15, DXF 3). `RV3-exchange.md` (not an INT path) still quotes
  142 luminaires, 59 circuits and provisional zones; the figures are now 136 luminaires, 60 distribution systems (58 + 2) and 69 published zone groups.
* Not regenerated: the elevation and section previews (`A-201`, `A-301`) need a Blender scene (`--scene`); they do not show luminaires.
