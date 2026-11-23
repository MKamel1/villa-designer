# Schedules, D1 (generated from the design model)

## Door schedule (18)

| tag | id | level | from | to | width_mm | height_mm | operation | handing | hinge_side | swing_into | to_confirm | glazed_garden_door | host_wall |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D01 | door-B-cinema-store-ramp | B | cinema (under the ramp; 2.0-2.65 m ceiling) | store under the ramp (1.45-2.0 m clear) | 800 | 1880 | hinged | LH | west | store under the ramp (1.45-2.0 m clear) | YES | False | wall-B-int-11 |
| D02 | door-B-dining-yard | B | dining (column bay 5-6, east window) | yard | 2350 | 2200 | sliding | n/a |  |  |  | True | wall-B-ext-04 |
| D03 | door-B-entry-b-core | B | entrance (second core lobby) | core | 1000 | 2100 | hinged | LH | north | entrance (second core lobby) | YES | False | wall-B-ext-02 |
| D04 | door-B-family-guest-wc | B | family / TV corner (open to the lounge) | guest bathroom (under the deck) | 800 | 2100 | hinged | RH | south | guest bathroom (under the deck) |  | False | wall-B-int-05 |
| D05 | door-B-kitchen-dirty-kitchen | B | open kitchen (column bay 4-5) | dirty kitchen + laundry (full-height window at the end) | 1200 | 2100 | sliding | n/a |  |  |  | False | wall-B-int-05 |
| D06 | door-B-living-yard | B | garden living | yard | 2760 | 2200 | sliding | n/a |  |  |  | True | wall-B-ext-04 |
| D07 | door-B-living-yard-2 | B | garden living | yard | 2400 | 2200 | sliding | n/a |  |  |  | True | wall-B-ext-18 |
| D08 | door-B-lounge-cinema | B | lounge (street window floor to beam) | cinema (under the ramp; 2.0-2.65 m ceiling) | 900 | 2100 | hinged | RH | south | cinema (under the ramp; 2.0-2.65 m ceiling) | YES | False | wall-B-int-05 |
| D09 | door-B-lounge-nook-pantry | B | lounge (under the stair's top landing) | pantry / store | 800 | 2100 | hinged | RH | south | lounge (under the stair's top landing) |  | False | wall-B-int-03 |
| D10 | door-B-lounge-yard | B | lounge (street window floor to beam) | yard | 3710 | 2200 | sliding | n/a |  |  |  | True | wall-B-ext-12 |
| D11 | door-GF-corridor-kids-a | GF | hall | kids bedroom A | 900 | 2100 | hinged | RH | south | kids bedroom A | YES | False | wall-GF-int-23 |
| D12 | door-GF-corridor-kids-b | GF | hall | kids bedroom B | 900 | 2100 | hinged | LH | north | kids bedroom B | YES | False | wall-GF-int-23 |
| D13 | door-GF-corridor-parents-entry | GF | hall | parents' bedroom (entry) | 900 | 2100 | pocket | n/a |  |  | YES | False | wall-GF-int-23 |
| D14 | door-GF-gallery-end-family-bath | GF | gallery (round the stair void to the bedrooms) | family bathroom | 800 | 2100 | hinged | LH | north | family bathroom | YES | False | wall-GF-int-25 |
| D15 | door-GF-landing-gf-core | GF | stair landing (core door) | core | 1000 | 2100 | hinged | RH | north | core |  | False | wall-GF-ext-21 |
| D16 | door-GF-parents-bed-parents-dressing | GF | parents' bedroom | dressing (hanging both sides) | 800 | 2100 | hinged | LH | south | dressing (hanging both sides) |  | False | wall-GF-int-24 |
| D17 | door-GF-parents-dressing-ext-parents-ensuite | GF | dressing (taken from the ensuite) | en-suite | 800 | 2100 | hinged | LH | south | en-suite | YES | False | wall-GF-int-20 |
| D18 | door-GF-study-game-deck | GF | study / game room (open to the stair; sliding door to the deck) | deck | 1800 | 2100 | sliding | n/a |  |  |  | False | wall-GF-ext-26 |

## Window schedule (8)

| tag | id | level | room | width_mm | height_mm | sill_mm | glazed_area_m2 | host_wall |
|---|---|---|---|---|---|---|---|---|
| W01 | window-B-dirty-kitchen-0 | B | dirty kitchen + laundry (full-height window at the end) | 2590 | 2300 | 0 | 5.96 | wall-B-ext-16 |
| W02 | window-GF-family-bath-5 | GF | family bathroom | 800 | 600 | 1700 | 0.48 | wall-GF-ext-26 |
| W03 | window-GF-kids-a-3 | GF | kids bedroom A | 2400 | 1400 | 900 | 3.36 | wall-GF-ext-26 |
| W04 | window-GF-kids-b-4 | GF | kids bedroom B | 2350 | 1400 | 900 | 3.29 | wall-GF-ext-26 |
| W05 | window-GF-parents-bed-6 | GF | parents' bedroom | 2400 | 1400 | 900 | 3.36 | wall-GF-ext-26 |
| W06 | window-GF-parents-bed-7 | GF | parents' bedroom | 2040 | 1400 | 900 | 2.86 | wall-GF-ext-35 |
| W07 | window-GF-study-game-1 | GF | study / game room (open to the stair; sliding door to the deck) | 2240 | 1400 | 900 | 3.14 | wall-GF-ext-26 |
| W08 | window-GF-study-game-2 | GF | study / game room (open to the stair; sliding door to the deck) | 1520 | 1400 | 900 | 2.13 | wall-GF-ext-27 |

## Room schedule (30)

| tag | id | level | name | occupancy | gross_area_m2 | net_area_m2 | clear_height_mm |
|---|---|---|---|---|---|---|---|
| R01 | bar-alcove | B | bar / library alcove (floor-to-beam garden window) | living | 6.63 | 5.15 | 2700 |
| R02 | cinema | B | cinema (under the ramp; 2.0-2.65 m ceiling) | media | 18.25 | 16.47 | 2579 |
| R03 | dining | B | dining (column bay 5-6, east window) | dining | 10.67 | 9.9 | 2700 |
| R04 | dining-side | B | dining (party side) | dining | 5.24 | 4.9 | 2700 |
| R05 | dirty-kitchen | B | dirty kitchen + laundry (full-height window at the end) | utility | 12.59 | 10.82 | 2800 |
| R06 | entry-b | B | entrance (second core lobby) | entrance | 3.22 | 2.9 | 2700 |
| R07 | family | B | family / TV corner (open to the lounge) | living | 4.74 | 4.67 | 2700 |
| R08 | guest-wc | B | guest bathroom (under the deck) | bathroom | 5.9 | 5.13 | 2650 |
| R09 | hall-b | B | hall at the stair foot | hall | 3.08 | 2.77 | 2700 |
| R10 | kitchen | B | open kitchen (column bay 4-5) | kitchen | 11.41 | 11.02 | 2700 |
| R11 | kitchen-island | B | open kitchen (island) | kitchen | 5.87 | 5.29 | 2700 |
| R12 | living | B | garden living | living | 21.49 | 19.45 | 2800 |
| R13 | lounge | B | lounge (street window floor to beam) | living | 23.44 | 21.96 | 2800 |
| R14 | lounge-nook | B | lounge (under the stair's top landing) | living | 1.87 | 1.49 | 2700 |
| R15 | pantry | B | pantry / store | store | 4.14 | 2.91 | 2700 |
| R16 | stair-b | B | stair (straight, to the GF) | stair | 5.38 | 4.71 | 2700 |
| R17 | store-ramp | B | store under the ramp (1.45-2.0 m clear) | store | 9.71 | 8.36 | 1674 |
| R18 | corridor | GF | hall | corridor | 13.83 | 11.25 | 2700 |
| R19 | family-bath | GF | family bathroom | bathroom | 6.25 | 5.24 | 2700 |
| R20 | gallery-end | GF | gallery (round the stair void to the bedrooms) | corridor | 2.59 | 2.43 | 2700 |
| R21 | kids-a | GF | kids bedroom A | bedroom | 13.14 | 11.91 | 2700 |
| R22 | kids-b | GF | kids bedroom B | bedroom | 13.14 | 11.85 | 2700 |
| R23 | landing-gf | GF | stair landing (core door) | landing | 3.59 | 2.81 | 2700 |
| R24 | parents-bed | GF | parents' bedroom | bedroom | 12.72 | 10.91 | 2700 |
| R25 | parents-dressing | GF | dressing (hanging both sides) | dressing | 6.23 | 5.43 | 2700 |
| R26 | parents-dressing-ext | GF | dressing (taken from the ensuite) | dressing | 0.57 | 0.37 | 2700 |
| R27 | parents-ensuite | GF | en-suite | ensuite | 6.61 | 5.06 | 2700 |
| R28 | parents-entry | GF | parents' bedroom (entry) | bedroom | 0.8 | 0.68 | 2800 |
| R29 | stair-gf | GF | stair void + gallery | stair | 8.53 | 7.79 | 2800 |
| R30 | study-game | GF | study / game room (open to the stair; sliding door to the deck) | study | 15.6 | 13.66 | 2700 |

