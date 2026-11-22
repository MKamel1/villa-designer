# LDS: landscape site analysis (2026-11-22)

Stage LD-S of `docs/quality/LANDSCAPE-METHOD.md`, for the approved garden brief (`docs/decisions/garden-brief-2026-11-22.md`).
Every layer is **computed from the model** (villa_env + the D1 revit_spec) with the project's own solar code. Nothing is assumed
except where a value is named ASSUMED below, and it is then listed as a GAP.

Rebuild: `PYTHONPATH=src python -m archpipe.landscape.site.build` (about 3 min; `--no-png` skips the plans).
Validate: `PYTHONPATH=src python -m archpipe.landscape.site.check`. Tests: `python -m pytest tests/landscape -q`.

## Frame and grid (shared by every layer)

* Frame: model metres (the villa scene frame; z = 0 is the GF FFL, the garden floor is z = **-3.0**).
* Client naming: street side = **NORTH = model -x**; east = +y; south = +x; west = -y (the sister plot). True north is used only for the sun
  (model +y bears 20 deg true; the street facade faces 290 deg).
* Grid: origin (-0.5, -30.0) m, cell **0.25 m**, nx 117, ny 40. `rows[j][i]`: j along y from -30.0, i along x from -0.5; the centre of
  cell (i, j) is (-0.5 + (i+.5)*0.25, -30.0 + (j+.5)*0.25). `null` = not analysed (building, fence, steps block, yard wall, outside, guard-rail cell).
* Plans (`knowledge/landscape/site/plan-*.png`) draw client north (street) at the top, client east to the right; the black arrow is client
  north, the dashed orange arrow is TRUE north (for the sun).

## Files in `knowledge/landscape/site/` (schema `lds-site/1`; every file carries `schema`, `layer`, `grid`, `gaps`)

| file | content |
|---|---|
| `inventory.json` | `cell_class` (codes in `classes`), `surface_z_m`, `zones{name: rect_m, polygon_area_m2, cell_area_by_class_m2, surface_z_m, openings[]}`, `levels`, `steps_and_changes_of_level`, `structure[]`, `services[]`, `connected_ground[]`, `not_ours`, `gaps` |
| `sun.json` | `layers{name: rows}` in hours of direct sun; `zone_stats`; `location` (with the placeholder status), `dates`, `windows`, `sensitivity_vs_yaml_placeholder`, `sanity` (vs earlier studies) |
| `privacy.json` | `viewers[]` (id, group, eye point, source), `layers{overlooking_eyes_<group>_<standing\|seated>, ..._any_*}` (count of eye points that see the cell), `eyes_any_standing_stats_by_zone`, `boundaries{east-fence, rear-fence, sister-line, street-fence}` with 0.5 m `segments[]` of the **screen top z needed** (all groups and `by_group`, by distance band), `eye_heights_m` |
| `views.json` | `per_opening{cells_seen, zone, eye_z_m}`, `layers{rooms_seeing_cell, seen_from_<room>}`, `focal_point_candidates{zone: [centre_m, patch_m, mean_rooms_seeing, rooms_seeing_half_or_more]}` |
| `wind.json` | station rose (16 sectors, share %, mean speed) for all-year, summer evening 17-20 and winter day 10-15; share by client side |
| `checklist.json` | coverage of the held site-analysis checklist and the full GAP list |

Layers in `sun.json`: `sun_hours_summer_solstice` (21 Jun), `sun_hours_equinox` (20 Mar), `sun_hours_winter_solstice` (21 Dec),
`summer_evening_17_20_standard_time` (out of 3 h; shade = 3 - value), `summer_evening_17_20_dst_clock` (the same clock hours on a UTC+3 clock = 16-19
standard; gap S7), `winter_day_10_15` (out of 5 h, 21 Dec).

## Method (and its limits)

* **Sun**: from each cell centre 0.05 m above its surface a ray toward the sun, 15-minute steps sampled at mid-interval (each sunlit sample = 0.25 h), local
  STANDARD time (UTC+2) as in `concept/garden_sun.py`, NOAA solar position (`archpipe.solar`). Obstructions: the triangles `garden_sun.default_study()` uses
  (our walls and slabs, fences 4.0 m from the basement floor, the 1.4 m NE yard wall, the 12 m neighbours, the sister villa, the apartment above, the
  steps block, ramp/deck/roof). **Glass is transparent; planting, pergola and furniture are absent** (they are what is being designed).
  `raycast.blocked` reproduces `SunStudy.clear` on 120 hourly cases with no difference (test).
* **Location**: `villa_env.LATITUDE/LONGITUDE` = 30.0403 / 30.9611 (client maps link, resolved 2026-09-25; plot-level but NOT surveyed).
  **`spec/villa-site.yaml` holds 30.050 / 31.000 EXAMPLE city-level PLACEHOLDERS: they are not used.** Sensitivity of every layer to them: mean |diff| <= 0.01 h, max 0.25 h (one step).
* **Privacy**: a straight sightline from each viewer eye point to a target point above each cell, blocked by the same enclosure. Eye heights **1.525 m standing, 1.125 m seated**
  (Time-Saver Standards for Landscape Architecture 2nd ed., p.340-4 note 3, fig. 340-8 on p.340-7; a US-average adult). Conservative: glass transparent, no
  field-of-view limit. Viewers (85): neighbour-east windows 20 and neighbour-rear windows 8 (4 storeys, ASSUMED windows like ours, villa_env), the apartment
  above 13 (the GF openings repeated +3.0 m, plus its north terrace edge), the sister villa's x-face openings 7 (mirror), a standing person in the sister's yard 28 (open line, no fence), walkers on the
  shared entrance steps 4 (solid block, top z 0.0: upper bound), street pedestrians 5 (negative control: the street fence is solid, they see nothing).
* **Screen height** at a boundary segment: the highest z at which any *visible* sightline crosses the boundary line, by how far behind the line its target is. A screen
  of top T blocks a band only if T >= the band's value.
* **Views**: three eye points 1.0 m inside each exterior opening of a garden-facing room, the sightline must pass the aperture and then be clear.
* **Wind**: the held TMYx for Cairo West AP (WMO 623680, nearest station, ADR-0017), hours local standard, hour-ending.

## Results

### Inventory (measured)

| zone (client name) | polygon m2 | open cells m2 | surface z | notes |
|---|---:|---:|---|---|
| north-garden (street-side court) | 23.65 | 17.50 (8.75 open + 8.75 under the GF terrace slab) | -3.0 | the rest is the entrance-steps block 4.38 m2 and the NE yard wall 0.88 m2 |
| east-ramp | 20.93 | 21.0 | -1.2..0.0 | car ramp: structure |
| east-deck | 17.64 | 17.25 | 0.0 | parking deck: structure |
| east-roof | 7.88 | 7.5 | 0.0 | extension roof (guard rail on its east edge) |
| east-yard (in front of the dirty kitchen and the dining/living doors) | 21.48 | 21.0 | -3.0 | sunken, open |
| south-garden | 53.19 | 54.6 | -3.0 | sunken |

* Zones run to the fences' inner faces (250 mm bands removed). **No fence on the line to the sister plot (y = -29.916): it is open.** The sister plot is not ours and is excluded.
* Connected garden-floor ground: **two separate pieces**: east-yard + south-garden (75.6 m2, one piece) and the north court (17.5 m2). The east strip (ramp, deck, roof over the basement
  rooms) separates them: **no ground route joins the north court to the rest; no step or ramp joins any sunken zone to deck, roof or street in the model.**
* 12 exterior openings onto the zones (doors: lounge to north; dining, living to east-yard; living to south; study sliding door to the deck; windows: dirty kitchen to east-yard, study/kids-a/kids-b/parents-bed to ramp, roof, east-yard, south).
  **There is no door from the dirty kitchen to the east yard** (a 2.59 m full-height window only).
* Services in the model: only two extract-fan discharges (guest WC at (10.1, -20.5), dirty kitchen at (13.83, -20.5), under the deck/roof edge). No AC units, drains, meters or bins (GAP S1).

### Sun, hours of direct sun per cell (zone mean / max)

| zone | 21 Jun | 20 Mar | 21 Dec | summer evening 17-20 std (of 3) | same hours on a DST clock (of 3) | winter day 10-15 (of 5) |
|---|---|---|---|---|---|---|
| north-garden | 1.3 / 2.0 | 0.7 / 1.75 | 0.1 / 1.25 | 0.0 / 0.0 | 0.0 / 0.0 | 0.1 / 1.25 |
| east-yard | 4.0 / 6.25 | 2.0 / 3.75 | 0.2 / 2.0 | 0.0 / 0.0 | 0.02 / 0.5 | 0.2 / 2.0 |
| south-garden | 4.2 / 7.0 | 3.0 / 3.75 | 2.7 / 3.75 | 0.02 / 0.5 | 0.1 / 1.5 | **2.7 / 3.75** |
| east-roof / deck / ramp | 6.5 / 7.2 / 7.0 (max 10.5) | 0.8 / 2.2 / 3.6 | 0.0 / 0.0 / 0.4 | 1.2 / 1.3 / 0.4 | 1.7 / 1.9 / 1.0 | 0.0 / 0.0 / 0.4 |

The sunken garden is shaded by the 12 m neighbours and our own apartment: in summer evenings the three garden floors get almost no sun (the south garden stays in shade for the use the client wants);
in a winter day only the south garden gets sun (about 2.7 of 5 h; the west half, nearest the sister line, gets the most: up to 3.75 h). The north court and the east yard get nearly none.

**Sanity against the earlier studies** (`sun.json -> sanity`):

* G4 trellis wall point (x -0.06, y -24.0, z -2.90), quoted 1.50 / 1.00 / 1.17 h: ours **1.50 / 1.00 / 1.25**.
* G6 south-garden east boundary (5 points on y -20.65, x 24.55-26.85), quoted mean 6.4 / 3.0 / 2.4 h (actual loquat root 7 / 3 / 2): ours, project hourly code **7.0 / 3.2 / 2.2**, 15-min **6.4 / 3.2 / 2.5**.
* G2 (legacy names: its "north" is today's east yard) "four/five hours" in June: ours east-yard bed mean 4.3, max 5.5. OK.
* G2's "nine hours throughout the east [= today's south] bed": **not reproduced**: ours 3.0 mean, 4.0 max on the south rear beds. G2 says its screen was a "bare-court" screen (no neighbours); G6, which uses the full enclosure as we do, agrees with us. Treat G2's nine hours as superseded.
* The frangipani stands near the middle of the south garden (aim point (25.6, -25.15), from the render cameras): ours **4.25 h on 21 Jun, 3.25 h in March, 3.0 h on 21 Dec** (zero in summer evenings): partly sunny in summer, the sunniest place we have in winter. G6 left its light quote UNVERIFIED, so there is no earlier number to compare; G6's loquat points, in the same garden, agree (above).

### Privacy (conservative: every cell is overlooked)

* **No garden cell is unseen.** Fewest / median / most eye points that see a standing person: north 5 / 8.5 / 18; east-yard 4 / 10 / 21; south 11 / 15 / 29; east roof 21 / 21 / 24; deck 21 / 21 / 25.
* Per group: the apartment above sees the whole east strip, east yard and south garden (100 %); the sister villa's rear-face openings see **all** of the south garden and the sister's yard sees all of it
  across the open line; the east neighbour sees 100 % of the deck and roof, 58 % of the east yard, 74 % of the south garden; the rear neighbour sees 80 % of the east yard and 65 % of the south garden; the north court is seen by the sister (100 %),
  the entrance steps (67 %), the apartment (50 %) and the east neighbour (22 %). Street pedestrians see nothing (the fence is solid; **the gate is not modelled**, gap S4).
* **Screen needed at the boundary** (top z, garden floor -3.0, existing fences top +1.0). Standing target. Bands = distance of the protected target behind the line (0-1, 1-2, 2-3, 3+ m):
  * east fence (east neighbour, up to 4 storeys): **2.75 / 3.75 / 4.40 / 5.31** (= 5.75 to 8.3 m above the floor; the fence gives 4.0): further bands need taller screens.
  * rear fence (rear neighbour): none / none / 1.57 / 6.23; the fence already hides the first two metres.
  * sister line, ground-level person: **-1.475 for every band = 1.525 m above the floor** (any screen taller than a standing eye blocks them); sister villa openings: -0.58 / 0.23 / 0.82 / 3.3.
* So a boundary screen can shield seats from the sister's ground and from a GF opening at modest height, but **cannot shield seats set back from the east and rear fences from the upper storeys**: a downward sightline from an
  upper window grazes any realistic fence. For the apartment above and the neighbours' upper storeys the answer must be overhead or near-seat cover (pergola, canopy, shade tree over the seating).

### Views out (seated eye 1.125 m; 1.525 m in the kitchens)

* Cells seen per opening: lounge door to north 280; dining door 258; living door east 420; living door south 744; dirty-kitchen window 966; study door to deck 293; kids-a 289; kids-b 112; parents-bed (east) 9; parents-bed (south) 0.
  The study's north window sees **0** cells: the GF terrace slab hides the court. The family-bath window (sill 1.7) is excluded as a privacy window.
* Best focal-point candidates (1.5 m patches, most rooms seeing them): east-yard (18.5, -22.25), (17.0, -21.5), (20.0, -21.5): seen by **dining, dirty kitchen and living (3 rooms)**; south garden (23.25, -21.25): dirty kitchen and living, and its west
  end (27.0, -29.25), (25.5, -28.25); north garden: only the lounge sees it (1 room): (0.75, -28.0), (2.25, -28.0); east roof: kids-a and kids-b.
* Placed against the brief: the east yard in front of the dirty kitchen is the place seen from three rooms, which suits a koi pond as a feature seen from the dining and living rooms; the pond cells get ~0 h of winter sun and 0 h on summer evenings, and are overlooked by 4-21 eye points.

### Wind (TMYx Cairo West AP, station level)

* All year: 8760 h, mean 3.7 m/s, calm 2.4 %; from client east (+-45 deg of true 20 deg) 52 %, from client north 27 %.
* **Summer evening 17-20 (Jun-Aug)**: mean 5.6 m/s, calm 0.4 %; **75 % from the client east side (NNE true)**, 21 % from client north.
* Winter day 10-15 (Dec-Feb): mean 3.9 m/s; 37 % from client north, 35 % from east, 20 % from the sister side (west).
* Station-level and open-terrain only: no site measure, no lee zones (gap W1).

## Checklist (Time-Saver sec. 220, pp. 220-3 to 220-4; the held *Site Analysis* book itself was not reachable, gap C1)

Covered: solar access, adjacent land uses, topography (levels), views out/overlooking, fixed structure. Partial: climate (wind rose only), circulation, utility infrastructure. **Not covered: soil, groundwater/runoff, existing vegetation** (reasons in `checklist.json`).

## GAPS (nothing here is guessed)

S1 services (AC, meters, bins, hose bibs, drains); S2 drainage and falls; S3 ground levels inside the yard; S4 the street gate/route and the steps' true profile; S5 neighbours, the apartment's and the sister's openings are ASSUMED (villa_env);
S6 the site coordinates are plot-level but not surveyed (yaml placeholders unused); S7 Egypt's summer clock (DST) not held: both readings given; S8 no door from the dirty kitchen to the east yard; W1 on-site wind and lee zones;
C1 the *Site Analysis* book, *A Pattern Language* and BR 209 are not reachable on this machine (the knowledge index is empty, no copy on disk): not cited; C2 plants, pergola, furniture and the current garden's beds/paths are excluded.

## Findings that put the brief at risk

1. **Privacy is critical, and nothing is private.** Every cell is overlooked by at least 4 eye points. The east neighbour's upper storeys and the apartment above look down into the east yard and the south garden at angles
   no boundary screen can cut; the sister villa's openings and yard see the whole south garden across a line with **no fence**. Strong screening needs overhead/near-seat cover, plus a screen on the sister line taller than standing eye height.
2. **South garden for 10-20 people on summer nights**: it is in shade 17-20 (good), but the wind is 75 % from the client east (NNE true) at 5.6 m/s mean: the east fence and the neighbour are upwind; a fire pit or lightweight furniture needs a windbreak plan.
3. **South garden for winter daytime**: it is the only zone with winter sun (2.7 of 5 h mean, max 3.75; least near the east fence). The design must not shade it further with evergreen cover on the south/west.
4. **Koi pond in the east yard or the north garden**: the east yard has ~0 winter sun and 4 h in June (mean), is seen by three rooms (a good focal point) but overlooked; the north court is isolated at ground level (reachable only through the lounge door), shaded (1.3 h in June) and seen only from the lounge. Both are shaded enough for a lush Japanese-style scheme and neither suits sun-loving planting.
5. The north garden is cut off from the rest at garden level, so the "relaxation" garden has no ground path to the south garden; and **no step or ramp links a sunken zone to the street, deck or roof in the model**.
6. The study window above the north court sees none of it (terrace slab), and no door opens from the dirty kitchen onto the east yard: a pond "in front of the dirty kitchen" is only a view unless a door is added.

## Decisions taken without a human

* Zone rectangles follow `villa_landscape.SOUTH` / `NORTH_COURT` and the east-strip structure; the east strip is split into ramp / deck / roof / open yard from `revit_spec`'s parking2 and `slab-roof-0`.
* Eye heights from Time-Saver p.340-4 (the only sourced figures found), not a guess; seated for living rooms, standing for the kitchens.
* The north court's steps block and the yard wall are treated as not-ground (cells `null`), the area under the GF terrace slab as `covered-ground` (it still gets sunlight that slips under the slab edge, as the independent project study confirms).
* A cell whose centre lies inside a 50 mm guard-rail solid is dropped (class 10) instead of reported as 0 h of sun (this was a real false-shade strip found in the first build).
* Candidate focal points are limited to garden floor and the roof; the car ramp and parking deck are structure.
* Added no dependency (numpy, shapely-free, matplotlib were already installed).
