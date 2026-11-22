# Pass 2 concepts: typology first (LDG, 2026-11-22)

West line screened (2.1 m) in all six packages; each concept has both pond options. Numbers come from `packages.json` (generated). LDC critics are NOT calibrated: counts are reported, not a gate.

## Comparison (pond in the east yard; the north option differs only in the two courts)

| | A Tree court | B Two rooms | C Axial terrace |
|---|---|---|---|
| hard failures (LDK + ours) | 0 | 0 | 0 |
| south hard share (range 0.52-0.82) | 0.818 | 0.856 (above) | 0.826 (above) |
| canopy trees per 100 m2, south (range 1.56-3.26) | 1.88 | 1.88 | 1.88 |
| same, south + east yard (74.7 m2) | 1.34 | 1.34 | 1.34 |
| seats: dining + built-in/lounge + quiet (south) | 8 + 6 + 2 | 8 + 13 + 2 | 8 + 5 + 2 |
| standing at an event, furniture in place (free floor / 1.3 m2) | 21 | 18 | 19 |
| dining 10 (3.0 m table) / 12 (3.6 m): clear mm vs 1200 | 1000 / 700 | 900 / 600 | 900 / 600 |
| LDC critics, fails (architect / horticulturist / user / climate) | 3/1/1/2 | 5/0/1/2 | 4/0/0/1 |
| rooms that see the focal cell (LDS views) | 3.0 | 3.0 | 1.0 |

Pond options (client chooses): A north court: critic fails 7, east yard: 7; B north court: critic fails 9, east yard: 8; C north court: critic fails 6, east yard: 5. The north court pond fails C-POND-SUN in every concept (1.3-1.5 h of direct sun against 2.0 h policy).

## Concept A: Tree court

Tree court. A courtyard room around one focal tree: a pomegranate stands at the south-west on a permeable gravel floor that is also the dining court (so no paving lies in its dripline, LS-ROOTZONE), the table sits under a louvred pergola beside it, a built-in bench runs along the rear wall under a second pergola (two quiet seats under the tree, the rest face the hearth), the flush fire pit and BBQ are the paved hearth court to the east, and a 1.2 m layered border wraps the screened west line. North court: a gravel room (tsubo-niwa) around a fatsia and Phoenix mass with the bench in an alcove under a pergola. East yard: a layered border on the fence; with the pond, a bench under a pergola at the north end faces it.

**Sources:** Ching, Form, Space and Order (centralised organisation; a focal element with lesser accents, pp. 234, 402-403; a shade tree as the roof of a gathering place, pp. 144, 159, 175); Clark & Pause, Precedents in Architecture, p. 256 (focal); Time-Saver Landscape p. 210-2 Fig. 210-1 (floor, wall, canopy make the room); LDP frozen ranges (hard share, trees per 100 m2).

**Focal point seen from the doors:** pond in the east yard + the pomegranate (LDS: 3.0 rooms see the cell).

Plans: `plans/A-pond-east-south.png` (south garden + east yard), `plans/A-pond-north-south.png`, `plans/A-pond-east-north.png` / `A-pond-north-north.png` (north court), massing `plans/A-pond-east-massing.png` (south garden, camera from the south-south-east) and `A-pond-east-north-massing.png` (north court, camera from the north-north-west).

### Programme: achieved vs required (pond east)

| rule | subject | achieved | required | status |
|---|---|---|---|---|
| LS-PATH-MAIN | path-door | 1200.0 mm | 1200 | pass |
| LS-PATH-MAIN | path-n-0 | 1200.0 mm | 1200 | pass |
| LS-PATH-SERVICE | path-e-0 | 1200.0 mm | 900 | pass |
| LS-SEATWALL | seat-wall/height | 450 mm | 450 | pass |
| LS-SEATWALL | seat-wall/width | 450 mm | 450 | pass |
| LS-DINE-AREA | dining | 4.19 m2 | 3.46 | pass |
| LS-DINE-CLEAR | dining-table | 1200 mm | 1200 | pass |
| LS-CAPACITY | south garden | 14 seats | 10 | pass |
| LS-LOUNGE-AREA | lounge | 5.02 m2 | 1.8 | pass |
| LS-LOUNGE-CLUSTER | lounge | 3710 mm | 3658 | pass |
| LS-STAND-AREA | standing | 1.38 m2 | 1.3 | pass |
| LS-FIRE-CLEAR | firepit | 900 mm | 1200 | warn |
| LS-FIRE-SEAT | firepit | 1550 mm | 1500 | pass |
| LS-FIRE-COVER | firepit | 15.0 kN | 15.0 | pass |
| LS-FIRE-OVERHEAD | firepit | 99000 mm | 2000 | pass |
| LS-FIRE-CLEAR | bbq | 900 mm | 1200 | warn |
| LS-FIRE-STRUCT | firepit | 2050 mm | 2000 | pass |
| LS-FIRE-STRUCT | bbq | 2010 mm | 2000 | pass |
| LS-POND-FLUSH-MARGIN | pond-e | 600 mm | 600 | pass |
| LS-POND-DEPTH | pond-e | 1000 mm | 900 | pass |
| LS-POND-STOCK | pond-e | 23.6 in/m2 | 28.7 | pass |
| LS-POND-GUARD | pond-e | 1 count | 1 | pass |
| LS-HYDROZONE | bed-west | 1 classes | 1 | pass |
| LS-HYDROZONE | bed-se | 1 classes | 1 | pass |
| LS-HYDROZONE | bed-herb | 1 classes | 1 | pass |
| LS-HYDROZONE | n-street | 1 classes | 1 | pass |
| LS-HYDROZONE | e-edge | 1 classes | 1 | pass |
| LS-HYDROZONE | e-pondmass | 1 classes | 1 | pass |
| LS-SCREEN | fence-east | 4.0 m | 1.8 | pass |
| LS-SCREEN | fence-rear | 4.0 m | 1.8 | pass |
| LS-SCREEN | sister-screen | 2.1 m | 1.8 | pass |
| LS-ROOTZONE | tree-0-punica | 0.0 m2 | 0.0 | pass |
| LS-TREE-BUILDING | tree-0-punica | 4.8 m | 2.78 | pass |
| LS-HERB-SUN | herb-bed | 6.12 h | 6 | pass |
| LDG-PRIV | table | 0.239 share | 0.3 | pass |
| LDG-SHADE | table/evening | 1.0 share | 0.9 | pass |
| LDG-PRIV | bench-quiet | 0.057 share | 0.25 | pass |
| LDG-SHADE | bench-quiet/evening | 1.0 share | 0.9 | pass |
| LDG-PRIV | bench-rear | 0.033 share | 0.3 | pass |
| LDG-SHADE | bench-rear/evening | 1.0 share | 0.9 | pass |
| LDG-PRIV | bench-n | 0.3 share | 0.75 | pass |
| LDG-SHADE | bench-n/evening | 1.0 share | 0.9 | pass |
| LDG-PRIV | bench-e | 0.0 share | 0.75 | pass |
| LDG-SHADE | bench-e/evening | 1.0 share | 0.9 | pass |
| LDG-BEDDEPTH | bed-west | 1.2 m | 1.2 | pass |
| LDG-BEDDEPTH | bed-se | 1.2 m | 1.2 | pass |
| LDG-BEDDEPTH | n-street | 1.24 m | 1.2 | pass |
| LDG-BEDDEPTH | e-pondmass | 1.79 m | 1.2 | pass |
| LDG-SUNFIT | site | 0 bed-species | 0 | pass |
| LDG-SPREAD | tree-0-punica | 0.0 m2 | 0 | pass |

Tally {'pass': 84, 'fail': 0, 'warn': 2, 'not_evaluated': 5}. Warnings and not-evaluated items are in `packages.json` (`checks`).

### Planting schedule (pond east)

| zone | bed | species | count | layer | conditions |
|---|---|---|---|---|---|
| east yard | e-edge | Acorus gramineus Aiton | 9 | ground | heat: moderate tolerance; plant in afternoon shade or verify locally |
| east yard | e-pondmass | Acorus gramineus Aiton | 6 | ground | heat: moderate tolerance; plant in afternoon shade or verify locally |
| east yard | e-pondmass | Alpinia zerumbet (Pers.) B.L.Burtt & R.M.Sm. | 2 | shrub/perennial | frost tolerance is a GAP; heat: moderate tolerance; plant in afternoon shade or verify locally; alkaline-soil tolerance is a GAP (site soil unmeasured |
| north court | n-street | Aspidistra elatior Blume | 11 | shrub/perennial | heat: moderate tolerance; plant in afternoon shade or verify locally |
| south | - | Punica granatum L. | 1 | canopy/understorey (tree) | canopy checked at the sourced minimum spread 2.4 m (LDL range 2.4-3.0 m): keep pruned |
| south | bed-west | Jasminum sambac (L.) Aiton | 3 | climber | frost: hardy only to 1 C; typical-year minimum is 5.1 C, floor policy 0.0 C; heat tolerance is a GAP; alkaline-soil tolerance is a GAP (site soil unme |
| south | bed-se | Jasminum sambac (L.) Aiton | 1 | climber | frost: hardy only to 1 C; typical-year minimum is 5.1 C, floor policy 0.0 C; heat tolerance is a GAP; alkaline-soil tolerance is a GAP (site soil unme |
| south | bed-west | Petrea volubilis L. | 2 | climber | frost: hardy only to 1.7 C; typical-year minimum is 5.1 C, floor policy 0.0 C; heat tolerance is a GAP; alkaline-soil tolerance is a GAP (site soil un |
| south | pot | Plumeria rubra L. (terracotta pot) | 1 | container tree | frost: hardy only to 1.7 C; typical-year minimum is 5.1 C, floor policy 0.0 C; frost: accepted by lead decision (client standing choice; Cairo grows f |
| south | bed-herb | Origanum majorana L. | 2 | ground |  |
| south | bed-west | Justicia brandegeeana Wassh. & L.B.Sm. | 4 | shrub/perennial | frost tolerance is a GAP; heat: moderate tolerance; plant in afternoon shade or verify locally |
| south | bed-se | Justicia brandegeeana Wassh. & L.B.Sm. | 3 | shrub/perennial | frost tolerance is a GAP; heat: moderate tolerance; plant in afternoon shade or verify locally |
| south | bed-west | Cenchrus alopecuroides (L.) Thunb. | 4 | shrub/perennial |  |
| south | bed-west | Salvia leucantha Cav. | 7 | shrub/perennial | heat: moderate tolerance; plant in afternoon shade or verify locally |

### Trade-offs

- Inside both precedent ranges (hard share 0.818, 1.88 trees per 100 m2) and the strongest single image (tree, gravel court, pergola), but the east half is still a paved hearth court: the fire pit and BBQ keep planting 2.0 m away (LS-FIRE-STRUCT), so it reads empty.
- One 1.2 m border is the only deep planting; the pomegranate is judged tight (H-SIZE-VS-SPACE: 2.4 m crown, 1.4 m space) and the quiet seat is 1.9 m from the gathering seats' centre (policy 3.0 m).
- Dining at the base size only: 10 seats with end chairs, 12 do not clear 1.2 m (measured 700 mm).

## Concept B: Two rooms

Two rooms divided by a planted screen, one sociable and one quiet. The south garden is the sociable terrace; the east yard, seen from the dining and living doors, is the quiet garden room (pond, bench under a pergola), divided from the terrace by a deep planted mass at the garden mouth. The prevailing wind decides the terrace: the fire pit sits at the west end with a built-in bench along the screened line behind it, then a cooking line (BBQ, then the dining table), then a 2 m deep layered east mass that carries the pomegranate and the herbs, and a rear bench under a pergola. North court: a quiet room entered over a threshold, the bench niche closed by a planted screen.

**Sources:** Ching pp. 224, 230, 280 (layered depth, a space within a space) and pp. 232, 304 (a graded public-to-private sequence); Clark & Pause pp. 257-258; Ching pp. 290-291 and Clark & Pause p. 313 (thresholds); Time-Saver p. 210-2.

**Focal point seen from the doors:** pond, focal of the quiet east-yard room (LDS: 3.0 rooms see the cell).

Plans: `plans/B-pond-east-south.png` (south garden + east yard), `plans/B-pond-north-south.png`, `plans/B-pond-east-north.png` / `B-pond-north-north.png` (north court), massing `plans/B-pond-east-massing.png` (south garden, camera from the south-south-east) and `B-pond-east-north-massing.png` (north court, camera from the north-north-west).

### Programme: achieved vs required (pond east)

| rule | subject | achieved | required | status |
|---|---|---|---|---|
| LS-PATH-MAIN | path-door | 1200.0 mm | 1200 | pass |
| LS-PATH-MAIN | path-n-0 | 1200.0 mm | 1200 | pass |
| LS-PATH-SERVICE | path-e-0 | 1200.0 mm | 900 | pass |
| LS-SEATWALL | seat-wall/height | 450 mm | 450 | pass |
| LS-SEATWALL | seat-wall/width | 450 mm | 450 | pass |
| LS-DINE-AREA | dining | 4.65 m2 | 3.46 | pass |
| LS-DINE-CLEAR | dining-table | 1200 mm | 1200 | pass |
| LS-CAPACITY | south garden | 21 seats | 10 | pass |
| LS-LOUNGE-AREA | lounge | 3.1 m2 | 1.8 | pass |
| LS-LOUNGE-CLUSTER | lounge | 5710 mm | 3658 | pass |
| LS-STAND-AREA | standing | 1.88 m2 | 1.3 | pass |
| LS-FIRE-CLEAR | firepit | 901 mm | 1200 | warn |
| LS-FIRE-SEAT | firepit | 1650 mm | 1500 | pass |
| LS-FIRE-COVER | firepit | 15.0 kN | 15.0 | pass |
| LS-FIRE-OVERHEAD | firepit | 99000 mm | 2000 | pass |
| LS-FIRE-CLEAR | bbq | 901 mm | 1200 | warn |
| LS-FIRE-STRUCT | firepit | 2100 mm | 2000 | pass |
| LS-FIRE-STRUCT | bbq | 2050 mm | 2000 | pass |
| LS-POND-FLUSH-MARGIN | pond-e | 600 mm | 600 | pass |
| LS-POND-DEPTH | pond-e | 1000 mm | 900 | pass |
| LS-POND-STOCK | pond-e | 23.6 in/m2 | 28.7 | pass |
| LS-POND-GUARD | pond-e | 1 count | 1 | pass |
| LS-HYDROZONE | bed-east-north | 1 classes | 1 | pass |
| LS-HYDROZONE | bed-east | 1 classes | 1 | pass |
| LS-HYDROZONE | bed-herb | 1 classes | 1 | pass |
| LS-HYDROZONE | n-screen | 1 classes | 1 | pass |
| LS-HYDROZONE | n-back | 1 classes | 1 | pass |
| LS-HYDROZONE | e-divider | 1 classes | 1 | pass |
| LS-HYDROZONE | e-far | 1 classes | 1 | pass |
| LS-SCREEN | fence-east | 4.0 m | 1.8 | pass |
| LS-SCREEN | fence-rear | 4.0 m | 1.8 | pass |
| LS-SCREEN | sister-screen | 2.1 m | 1.8 | pass |
| LS-ROOTZONE | tree-0-punica | 0.0 m2 | 0.0 | pass |
| LS-TREE-BUILDING | tree-0-punica | 4.86 m | 2.78 | pass |
| LS-HERB-SUN | herb-bed | 6.43 h | 6 | pass |
| LDG-PRIV | table | 0.185 share | 0.3 | pass |
| LDG-SHADE | table/evening | 1.0 share | 0.9 | pass |
| LDG-PRIV | bench-west | 0.137 share | 0.3 | pass |
| LDG-SHADE | bench-west/evening | 1.0 share | 0.9 | pass |
| LDG-PRIV | bench-quiet | 0.039 share | 0.25 | pass |
| LDG-SHADE | bench-quiet/evening | 1.0 share | 0.9 | pass |
| LDG-PRIV | bench-rear | 0.064 share | 0.3 | pass |
| LDG-SHADE | bench-rear/evening | 1.0 share | 0.9 | pass |
| LDG-PRIV | bench-n | 0.224 share | 0.75 | pass |
| LDG-SHADE | bench-n/evening | 1.0 share | 0.9 | pass |
| LDG-PRIV | bench-e | 0.0 share | 0.75 | pass |
| LDG-SHADE | bench-e/evening | 1.0 share | 0.9 | pass |
| LDG-BEDDEPTH | bed-east | 1.46 m | 1.2 | pass |
| LDG-BEDDEPTH | n-screen | 1.2 m | 1.2 | pass |
| LDG-BEDDEPTH | n-back | 1.73 m | 1.2 | pass |
| LDG-BEDDEPTH | e-divider | 1.49 m | 1.2 | pass |
| LDG-BEDDEPTH | e-far | 1.2 m | 1.2 | pass |
| LDG-SUNFIT | site | 0 bed-species | 0 | pass |
| LDG-SPREAD | tree-0-punica | 0.0 m2 | 0 | pass |

Tally {'pass': 90, 'fail': 0, 'warn': 2, 'not_evaluated': 5}. Warnings and not-evaluated items are in `packages.json` (`checks`).

### Planting schedule (pond east)

| zone | bed | species | count | layer | conditions |
|---|---|---|---|---|---|
| east yard | e-divider | Acorus gramineus Aiton | 4 | ground | heat: moderate tolerance; plant in afternoon shade or verify locally |
| east yard | e-far | Acorus gramineus Aiton | 4 | ground | heat: moderate tolerance; plant in afternoon shade or verify locally |
| east yard | e-divider | Alpinia zerumbet (Pers.) B.L.Burtt & R.M.Sm. | 2 | shrub/perennial | frost tolerance is a GAP; heat: moderate tolerance; plant in afternoon shade or verify locally; alkaline-soil tolerance is a GAP (site soil unmeasured |
| east yard | e-far | Alpinia zerumbet (Pers.) B.L.Burtt & R.M.Sm. | 1 | shrub/perennial | frost tolerance is a GAP; heat: moderate tolerance; plant in afternoon shade or verify locally; alkaline-soil tolerance is a GAP (site soil unmeasured |
| north court | n-screen | Jasminum sambac (L.) Aiton | 2 | climber | frost: hardy only to 1 C; typical-year minimum is 5.1 C, floor policy 0.0 C; heat tolerance is a GAP; alkaline-soil tolerance is a GAP (site soil unme |
| north court | n-screen | Aspidistra elatior Blume | 5 | shrub/perennial | heat: moderate tolerance; plant in afternoon shade or verify locally |
| north court | n-back | Aspidistra elatior Blume | 4 | shrub/perennial | heat: moderate tolerance; plant in afternoon shade or verify locally |
| north court | n-back | Farfugium japonicum (L.) Kitam. | 1 | shrub/perennial | heat: moderate tolerance; plant in afternoon shade or verify locally; alkaline-soil tolerance is a GAP (site soil unmeasured) |
| north court | n-screen | Fatsia japonica (Thunb.) Decne. & Planch. | 2 | shrub/perennial | heat: moderate tolerance; plant in afternoon shade or verify locally; sun conditional at 1.7 h (21 Jun) |
| south | - | Punica granatum L. | 1 | canopy/understorey (tree) | canopy checked at the sourced minimum spread 2.4 m (LDL range 2.4-3.0 m): keep pruned |
| south | bed-east | Jasminum sambac (L.) Aiton | 2 | climber | frost: hardy only to 1 C; typical-year minimum is 5.1 C, floor policy 0.0 C; heat tolerance is a GAP; alkaline-soil tolerance is a GAP (site soil unme |
| south | pot | Plumeria rubra L. (terracotta pot) | 1 | container tree | frost: hardy only to 1.7 C; typical-year minimum is 5.1 C, floor policy 0.0 C; frost: accepted by lead decision (client standing choice; Cairo grows f |
| south | bed-herb | Origanum majorana L. | 3 | ground |  |
| south | bed-east | Aspidistra elatior Blume | 6 | shrub/perennial | heat: moderate tolerance; plant in afternoon shade or verify locally |
| south | bed-east-north | Justicia brandegeeana Wassh. & L.B.Sm. | 3 | shrub/perennial | frost tolerance is a GAP; heat: moderate tolerance; plant in afternoon shade or verify locally |
| south | bed-east | Justicia brandegeeana Wassh. & L.B.Sm. | 4 | shrub/perennial | frost tolerance is a GAP; heat: moderate tolerance; plant in afternoon shade or verify locally |
| south | bed-east | Cenchrus alopecuroides (L.) Thunb. | 3 | shrub/perennial |  |
| south | bed-herb | Salvia rosmarinus Spenn. | 2 | shrub/perennial |  |
| south | bed-east-north | Salvia leucantha Cav. | 2 | shrub/perennial | heat: moderate tolerance; plant in afternoon shade or verify locally |
| south | bed-east | Salvia leucantha Cav. | 1 | shrub/perennial | heat: moderate tolerance; plant in afternoon shade or verify locally |

### Trade-offs

- The most seats (8 + 13 built-in + 2, event standing 18) and the deepest planting mass (2 m east), but the hard share is 0.856 (above the range, the bench and cooking line take the floor) and the long west seat wall reads as a blank box on the plan.
- Two rooms is clearer in the yard than in the south garden: no room fits between the pit and the table, so the divider sits at the garden mouth, not inside the south garden.
- Most critic findings (landscape architect 5 fails: enclosure of four rooms, focal count); C-FIRE-WIND still flags 11 of 17 seats near the fire for the wind the critics assume (gas fuel, so little smoke; the critic does not know the fuel).

## Concept C: Axial terrace

Terrace wrapped by deep layered borders, with a main axis from the living door to a focal point. The axis leaves the door under a gate pergola (the threshold), crosses the flush concealed fire pit and ends at a sculpture place lit in the rear wall. BBQ west and the dining table east of the pit; a 1.2 m border on the screened west line with a bench along its edge, a rear-west mass, and a deep east border carrying the pomegranate and the herbs wrap the terrace. North court: the same axis from the lounge door to a sculpture place (no pond) or the pond (pond option) between two borders. East yard: the service path along the house runs to a sculpture place (no pond) or beside a long straight pond.

**Sources:** Ching p. 384-385 (an axis ends in something worth reaching) and pp. 282, 290-291 (threshold), pp. 122, 144, 165 (walls and planes that enclose); Clark & Pause p. 313; Time-Saver p. 210-2.

**Focal point seen from the doors:** fire pit on the axis, then the lit sculpture place (LDS: 1.0 rooms see the cell).

Plans: `plans/C-pond-east-south.png` (south garden + east yard), `plans/C-pond-north-south.png`, `plans/C-pond-east-north.png` / `C-pond-north-north.png` (north court), massing `plans/C-pond-east-massing.png` (south garden, camera from the south-south-east) and `C-pond-east-north-massing.png` (north court, camera from the north-north-west).

### Programme: achieved vs required (pond east)

| rule | subject | achieved | required | status |
|---|---|---|---|---|
| LS-PATH-MAIN | axis-1 | 1200.0 mm | 1200 | pass |
| LS-PATH-MAIN | axis-2 | 1200.0 mm | 1200 | pass |
| LS-PATH-MAIN | path-n-0 | 1200.0 mm | 1200 | pass |
| LS-PATH-SERVICE | path-e-0 | 1200.0 mm | 900 | pass |
| LS-SEATWALL | seat-wall/height | 450 mm | 450 | pass |
| LS-SEATWALL | seat-wall/width | 450 mm | 450 | pass |
| LS-DINE-AREA | dining | 4.78 m2 | 3.46 | pass |
| LS-DINE-CLEAR | dining-table | 1200 mm | 1200 | pass |
| LS-CAPACITY | south garden | 13 seats | 10 | pass |
| LS-LOUNGE-AREA | lounge | 9.02 m2 | 1.8 | pass |
| LS-LOUNGE-CLUSTER | lounge | 5710 mm | 3658 | pass |
| LS-STAND-AREA | standing | 1.83 m2 | 1.3 | pass |
| LS-FIRE-CLEAR | firepit | 900 mm | 1200 | warn |
| LS-FIRE-SEAT | firepit | 1500 mm | 1500 | pass |
| LS-FIRE-COVER | firepit | 15.0 kN | 15.0 | pass |
| LS-FIRE-OVERHEAD | firepit | 99000 mm | 2000 | pass |
| LS-FIRE-CLEAR | bbq | 900 mm | 1200 | warn |
| LS-FIRE-STRUCT | firepit | 2000 mm | 2000 | pass |
| LS-FIRE-STRUCT | bbq | 2000 mm | 2000 | pass |
| LS-POND-FLUSH-MARGIN | pond-e | 600 mm | 600 | pass |
| LS-POND-DEPTH | pond-e | 1000 mm | 900 | pass |
| LS-POND-STOCK | pond-e | 22.3 in/m2 | 28.7 | pass |
| LS-POND-GUARD | pond-e | 1 count | 1 | pass |
| LS-HYDROZONE | bed-east | 1 classes | 1 | pass |
| LS-HYDROZONE | bed-rear-west | 1 classes | 1 | pass |
| LS-HYDROZONE | bed-east-north | 1 classes | 1 | pass |
| LS-HYDROZONE | bed-herb | 1 classes | 1 | pass |
| LS-HYDROZONE | n-left | 1 classes | 1 | pass |
| LS-HYDROZONE | n-right | 1 classes | 1 | pass |
| LS-HYDROZONE | e-border | 1 classes | 1 | pass |
| LS-HYDROZONE | e-edge | 1 classes | 1 | pass |
| LS-SCREEN | fence-east | 4.0 m | 1.8 | pass |
| LS-SCREEN | fence-rear | 4.0 m | 1.8 | pass |
| LS-SCREEN | sister-screen | 2.1 m | 1.8 | pass |
| LS-ROOTZONE | tree-0-punica | 0.0 m2 | 0.0 | pass |
| LS-TREE-BUILDING | tree-0-punica | 3.98 m | 2.78 | pass |
| LS-HERB-SUN | herb-bed | 6.48 h | 6 | pass |
| LDG-PRIV | table | 0.263 share | 0.3 | pass |
| LDG-SHADE | table/evening | 1.0 share | 0.9 | pass |
| LDG-PRIV | bench-west | 0.145 share | 0.3 | pass |
| LDG-SHADE | bench-west/evening | 1.0 share | 0.9 | pass |
| LDG-PRIV | bench-quiet | 0.185 share | 0.25 | pass |
| LDG-SHADE | bench-quiet/evening | 1.0 share | 0.9 | pass |
| LDG-PRIV | bench-n | 0.492 share | 0.75 | pass |
| LDG-SHADE | bench-n/evening | 1.0 share | 0.9 | pass |
| LDG-PRIV | bench-e | 0.0 share | 0.75 | pass |
| LDG-SHADE | bench-e/evening | 1.0 share | 0.9 | pass |
| LDG-BEDDEPTH | bed-east | 1.27 m | 1.2 | pass |
| LDG-BEDDEPTH | bed-rear-west | 1.2 m | 1.2 | pass |
| LDG-BEDDEPTH | n-left | 1.2 m | 1.2 | pass |
| LDG-BEDDEPTH | n-right | 1.2 m | 1.2 | pass |
| LDG-BEDDEPTH | e-border | 1.79 m | 1.2 | pass |
| LDG-SUNFIT | site | 0 bed-species | 0 | pass |
| LDG-SPREAD | tree-0-punica | 0.0 m2 | 0 | pass |

Tally {'pass': 102, 'fail': 0, 'warn': 2, 'not_evaluated': 5}. Warnings and not-evaluated items are in `packages.json` (`checks`).

### Planting schedule (pond east)

| zone | bed | species | count | layer | conditions |
|---|---|---|---|---|---|
| east yard | e-border | Acorus gramineus Aiton | 6 | ground | heat: moderate tolerance; plant in afternoon shade or verify locally |
| east yard | e-edge | Acorus gramineus Aiton | 9 | ground | heat: moderate tolerance; plant in afternoon shade or verify locally |
| east yard | e-border | Alpinia zerumbet (Pers.) B.L.Burtt & R.M.Sm. | 2 | shrub/perennial | frost tolerance is a GAP; heat: moderate tolerance; plant in afternoon shade or verify locally; alkaline-soil tolerance is a GAP (site soil unmeasured |
| north court | n-right | Jasminum sambac (L.) Aiton | 2 | climber | frost: hardy only to 1 C; typical-year minimum is 5.1 C, floor policy 0.0 C; heat tolerance is a GAP; alkaline-soil tolerance is a GAP (site soil unme |
| north court | n-left | Aspidistra elatior Blume | 5 | shrub/perennial | heat: moderate tolerance; plant in afternoon shade or verify locally |
| north court | n-right | Aspidistra elatior Blume | 5 | shrub/perennial | heat: moderate tolerance; plant in afternoon shade or verify locally |
| north court | n-right | Fatsia japonica (Thunb.) Decne. & Planch. | 2 | shrub/perennial | heat: moderate tolerance; plant in afternoon shade or verify locally; sun conditional at 1.7 h (21 Jun) |
| north court | n-right | Phoenix roebelenii O'Brien | 1 | shrub/perennial | alkaline soil: intolerant; conditional on soil test (a professional item; site pH not tested); sun conditional at 1.7 h (21 Jun) |
| south | - | Punica granatum L. | 1 | canopy/understorey (tree) | canopy checked at the sourced minimum spread 2.4 m (LDL range 2.4-3.0 m): keep pruned |
| south | bed-east | Jasminum sambac (L.) Aiton | 2 | climber | frost: hardy only to 1 C; typical-year minimum is 5.1 C, floor policy 0.0 C; heat tolerance is a GAP; alkaline-soil tolerance is a GAP (site soil unme |
| south | bed-rear-west | Jasminum sambac (L.) Aiton | 1 | climber | frost: hardy only to 1 C; typical-year minimum is 5.1 C, floor policy 0.0 C; heat tolerance is a GAP; alkaline-soil tolerance is a GAP (site soil unme |
| south | bed-rear-west | Petrea volubilis L. | 1 | climber | frost: hardy only to 1.7 C; typical-year minimum is 5.1 C, floor policy 0.0 C; heat tolerance is a GAP; alkaline-soil tolerance is a GAP (site soil un |
| south | pot | Plumeria rubra L. (terracotta pot) | 1 | container tree | frost: hardy only to 1.7 C; typical-year minimum is 5.1 C, floor policy 0.0 C; frost: accepted by lead decision (client standing choice; Cairo grows f |
| south | bed-herb | Origanum majorana L. | 3 | ground |  |
| south | bed-rear-west | Aspidistra elatior Blume | 5 | shrub/perennial | heat: moderate tolerance; plant in afternoon shade or verify locally |
| south | bed-east | Justicia brandegeeana Wassh. & L.B.Sm. | 3 | shrub/perennial | frost tolerance is a GAP; heat: moderate tolerance; plant in afternoon shade or verify locally |
| south | bed-rear-west | Justicia brandegeeana Wassh. & L.B.Sm. | 1 | shrub/perennial | frost tolerance is a GAP; heat: moderate tolerance; plant in afternoon shade or verify locally |
| south | bed-east-north | Justicia brandegeeana Wassh. & L.B.Sm. | 3 | shrub/perennial | frost tolerance is a GAP; heat: moderate tolerance; plant in afternoon shade or verify locally |
| south | bed-east | Cenchrus alopecuroides (L.) Thunb. | 4 | shrub/perennial |  |
| south | bed-herb | Salvia rosmarinus Spenn. | 2 | shrub/perennial |  |
| south | bed-rear-west | Salvia leucantha Cav. | 3 | shrub/perennial | heat: moderate tolerance; plant in afternoon shade or verify locally |
| south | bed-east-north | Salvia leucantha Cav. | 2 | shrub/perennial | heat: moderate tolerance; plant in afternoon shade or verify locally |

### Trade-offs

- Fewest critic findings and the only one with no user-critic failure; the axis gives the door, the pit and the sculpture place one line, and each court has its own axis end. Hard share 0.826 is 0.006 above the range.
- The focal point on the axis is a concealed flush pit (the lid, not a fire, when not in use) and a sculpture place with no sculpture chosen; the lit wall is a client item.
- Fewest fixed seats (8 + 5 + 2): the capacity relies on standing room (19) and the table's end chairs; built-in bench only on the west edge.

## What the LDC critics said (pond east; uncalibrated, see docs/lanes/LDC.md)

**A:** A-ENCLOSURE (fail) room 'quiet-n': 31% of its perimeter enclosed by walls/buildings/screens/planting >= 1.8 m (required >= 50%); A-ENCLOSURE (fail) room 'quiet-e': 40% of its perimeter enclosed by walls/buildings/screens/planting >= 1.8 m (required >= 50%); A-FOCAL (fail) 7 focal elements (['firepit', 'pond', 'specimen-tree', 'pergola', 'pergola', 'pergola', 'pergola']); required ; H-SIZE-VS-SPACE (fail) punica_granatum: mature spread 2.4 m in a space 1.4 m across (limit 0.8 x = 1.1 m); U-QUIET-SOUTH (fail) quiet corner (south): quiet seat 1.9 m from the gathering seats' centre (required >= 3.0 m, policy) and reacha; C-WINTER-SUN (fail) 6 of 13 dining/lounge seats get under 2 of 5 h sun on 21 Dec 10-15 (allowed <= 30%); best seat 3.50 h; C-FIRE-WIND (fail) 10 of 14 seats within 4 m of the fire sit in its downwind +-45 deg sector for more than 35% of hours (max shar

**B:** A-ENCLOSURE (fail) room 'quiet': 33% of its perimeter enclosed by walls/buildings/screens/planting >= 1.8 m (required >= 50%); A-ENCLOSURE (fail) room 'quiet-n': 29% of its perimeter enclosed by walls/buildings/screens/planting >= 1.8 m (required >= 50%); A-ENCLOSURE (fail) room 'quiet-e': 0% of its perimeter enclosed by walls/buildings/screens/planting >= 1.8 m (required >= 50%); A-ENCLOSURE (fail) room 'dining': 38% of its perimeter enclosed by walls/buildings/screens/planting >= 1.8 m (required >= 50%); A-FOCAL (fail) 8 focal elements (['firepit', 'pond', 'specimen-tree', 'pergola', 'pergola', 'pergola', 'pergola', 'pergola']); A-ROOMS (warn) 5 outdoor rooms with uses/surfaces ["('dining', 'paving')", "('lounge', 'paving')", "('quiet', 'paving')"]; a ; H-BED-CROWDING (warn) bed bed-herb: mature crowns 3.5 m2 on 1.6 m2 of bed (limit 1.5 x); H-BED-CROWDING (warn) bed n-screen: mature crowns 4.5 m2 on 2.7 m2 of bed (limit 1.5 x); U-QUIET-SOUTH (fail) quiet corner (south): quiet seat 2.1 m from the gathering seats' centre (required >= 3.0 m, policy) and reacha; C-WINTER-SUN (fail) 9 of 21 dining/lounge seats get under 2 of 5 h sun on 21 Dec 10-15 (allowed <= 30%); best seat 3.75 h; C-FIRE-WIND (fail) 11 of 17 seats within 4 m of the fire sit in its downwind +-45 deg sector for more than 35% of hours (max shar

**C:** A-ENCLOSURE (fail) room 'quiet': 40% of its perimeter enclosed by walls/buildings/screens/planting >= 1.8 m (required >= 50%); A-ENCLOSURE (fail) room 'quiet-n': 38% of its perimeter enclosed by walls/buildings/screens/planting >= 1.8 m (required >= 50%); A-ENCLOSURE (fail) room 'quiet-e': 44% of its perimeter enclosed by walls/buildings/screens/planting >= 1.8 m (required >= 50%); A-FOCAL (fail) 10 focal elements (['firepit', 'sculpture', 'sculpture', 'pond', 'specimen-tree', 'pergola', 'pergola', 'pergo; H-BED-CROWDING (warn) bed bed-herb: mature crowns 3.5 m2 on 1.6 m2 of bed (limit 1.5 x); H-BED-CROWDING (warn) bed n-right: mature crowns 5.3 m2 on 2.9 m2 of bed (limit 1.5 x); C-FIRE-WIND (fail) 7 of 14 seats within 4 m of the fire sit in its downwind +-45 deg sector for more than 35% of hours (max share

Reading them: A-ENCLOSURE counts a quiet bench with an open side as under-enclosed; A-FOCAL counts every pergola as a focal element (it caps at 4: a convention, not a defect); C-WINTER-SUN is a real site fact (the rear and east seats get under 2 h on 21 December, the west and north parts 3-3.6 h); H-BED-CROWDING is the herb strip (rosemary at its 1.5 m minimum spread).

## Recommendation

**Concept C (axial terrace), pond in the east yard.** Reasons: no hard fail, the fewest LDC critic findings (5 fails against 7 and 8; uncalibrated, so a tiebreak, not proof), the only concept with a clean user critic (gathering groups, quiet corner 3 m from the gathering centre, pond view, service path), and its axis gives the living door, the pit and the sculpture place one line while the north court and east yard each carry their own axis end. The pond belongs in the east yard: three rooms (dining, living, dirty kitchen) see it and it gets 3.8-5.5 h of sun, against 1.3 h in the north court. **Runner-up A (tree court):** inside both precedent ranges and the strongest image; choose it if the client prefers a tree to an axis. Its cost is the empty hearth court and the 1.9 m quiet seat. **B** has the most seats and the deepest planting but the most findings and a hard share above the range.

## Rejected in this pass

- The pass-1 random packing as the generator (it fits furniture first; the bones came out as a perimeter strip). Kept only as a filter idea: the LDK rules decide what survives.
- Dining at 4 seats (pass 1): the brief needs 10-20 people; base is now 8 with end chairs to 10; 12 does not clear 1.2 m in any concept (measured 600-700 mm).
- A banquette-table unit on the rear wall (concept C first draft): LS-DINE-CLEAR measures the wall (0 mm). The rule penalises a built-in banquette; recorded, not worked around.
- Fire pit with the table inside its 1.5 m ring, a herb bed within 2 m of the BBQ, olive/jacaranda/tipu as the tree (spread or NHBC distance fails), cupressus as the tree (0.5 x 12.2 m = 6.1 m from the building, the garden is 5.7 m deep).
- Lawn in the hearth court (2.6-4.8 h of sun and 20-40 people on it); lush Fatsia/alpinia pond planting is kept but conditional (frost, heat GAP, alkaline soil) and thin where the sun is below 1.5 h.

## Decisions and policies (ours, no held source)

- Bench length per person 0.6 m (no held source; Time-Saver 340-11 gives seat-wall width 400-450 mm only). Border depth at least 1.2 m for layered borders (no held source; Neufert p. 105 gives soil depth, not width); strips (herb, pond margin, climber) are named and may be narrower.
- LS-DINE-AREA scales a 4-seat figure linearly (3.46 m2 per seat): 8 seats need 27.7 m2. The dining zone is declared as the shared central court (it also holds the hearth); the Time-Saver construction (table + 1.2 m all round) needs about 15.8 m2 for 8 seats.
- Privacy and evening shade are judged where people sit (table + 0.6 m, each bench + 0.6 m), not on the larger room rectangles; the louvred pergola is assumed closed (opaque) for privacy and shade credit (LDK GAP-OVERLOOK-ABOVE), which conflicts with the open pergola the winter sun needs.
- The pomegranate crown is checked at the sourced minimum spread (2.4 m, LDL range 2.4-3.0); at 3.0 m it would not fit with the fire clearance. Climbers are drawn at a trained width of 1.2 m. Plants are drawn at their planting spacing when that exceeds the mature spread so drifts merge.
- Trees per 100 m2 use the south garden (53.19 m2) as pass 1 did: one canopy tree gives 1.88, two would give 3.76 (above the 3.26 range). South + yard (74.7 m2) is reported next to it.
- North-court bench privacy limit 75 % remaining (as pass 1; the exposure comes across the entrance-steps block and the street), south 30 % (quiet 25 %).
- The sun class of every plant is checked against its bed's 21-June sun (policy: part shade needs 2 h, 1.5 h conditional): in the north court only shade species (Aspidistra, Farfugium) survive the check, so the lush pond planting there is thin.
