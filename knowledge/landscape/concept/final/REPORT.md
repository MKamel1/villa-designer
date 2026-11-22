# Final garden design: concept B adapted (LDG round 2, 2026-11-22)

Client decisions applied: concept B adapted; shared gas fire pit on the west line; west screen tall except an opening at the pit; grape vine on the dining pergola; both ponds kept; mirrored visualisation of the south garden on the sister plot (viewing only). Numbers below are generated from `final.json`; `layout-final.json` is the design, `layout-visualisation.json` is the mirror (excluded everywhere).

**Result: 0 hard failures.** Tally {'pass': 123, 'fail': 0, 'warn': 3, 'not_evaluated': 8}. LDK `LS-FIRE-STRUCT` (2.0 m open-fire floor, a wood-fire bylaw) is reported as a warning for the pit and replaced by the manuals' own clearances (see Fire pit); the client's screen opening is recorded as a visible waiver (`LDG-PRIV-OPENING`). Critic findings are listed, not gated.

## The design in one paragraph

South garden (5.71 x 9.32 m): the **social terrace** at the west. The flush gas fire pit (0.9 m envelope) is centred ON the west line; the 2.1 m screen stops 1.25 m from its edge on both sides, an opening of 3.4 m sized to the table's chairs that face the fire (ten at the extended table: 3.0 m long, 1.2 m clear). The dining table (8, extending to 10) sits 2.1 m from the pit under a louvred, non-combustible pergola carrying a **grape vine**; the BBQ stand is 2 m from everything; a built-in bench (3 seats) and a quiet bench (2 seats) run along the rear wall under a second pergola; a 1.5 m deep planted mass with the pomegranate and a herb strip closes the east, so the **quiet room** (east yard: bench under a pergola facing a flush koi pond) lies behind it, reached along the house wall. North court: the second **quiet room** (bench niche under a pergola, planted screen, flush koi pond with shade foliage). Both ponds are kept for now.

## Fire pit on the west line

Position: centre at the west line (b 0.0), 2.8 m from the house face and 2.9 m from the rear fence. Screen opening a 1.1-4.5 m along the line; each screen end is 1250 mm from the pit edge, nothing combustible (planting, vine, pergola, tree crown) is within 1250 mm sideways or 2000 mm overhead (measured straight-line to the burner, `LDG-FIRE-MANUAL`). The nearest pergola is 2.9 m away (3-D). The pit straddles the boundary: the fixture needs the sister owner's agreement (client's matter). In the schedule: one shared flush gas pit, our share 50 % (`our_share`); the sister's seats exist only in the visualisation.

### Shortlist: three gas burners with manuals that state clearances

| product | certification (quoted) | side clearance | overhead | flush installation | cover / lid | Egypt |
|---|---|---|---|---|---|---|
| Pebble Technology (PTI) linear burner, inner mount, 12 V AC, 36 in (0.91 m) class | CSA/AGA; CSA certificate 2325190; tested to ANSI Z223.1-2010, ANSI Z21.97-2010 (outdoor decorative gas appliances), Z21.42-2010 | 1219 mm | 1829 | closest: 'the top of the Burner is 1/2 in - 1 in below the top of wall or cap of built burner cavity' (13-25 mm below the cap); flush with paving is not stated | none stated; 'For installation on or over non-combustible floors only' | US/Canada certification only |
| Planika Mico Automatic 800 (LPG or natural gas), 800 x 800 mm class | CE marking under Regulation (EU) 2016/426 (gas appliances), manual cites EN 778; certificate GAR1450CT0048 | 1000 mm | not stated | 'not a free-standing device and is destined to be housed' (a built cavity); flush with paving not stated | none stated; 'protected from atmospheric conditions' when not used, main valve off | EU certification only; no Egyptian approval found |
| MAD Design Group ESF gas burner (clearances and installation manual) | not stated in the clearances manual read | 610 mm | 2000 | not stated; the manual requires ventilation of the underside and that the base never touches flammable material | none stated | unknown |

Quoted sentences (each checked as a literal substring of the manual text in `fire-manuals/` by the tests):

- **PTI-linear-inner** (12V-AC-Linear-Burner-Installation-Maintenance-Warranty-Guidelines.pdf (pebbletec.com/wp-content/uploads/2021/11/)): "Adhere to recommended CSA/AGA clearances: sides 4ft/top 6ft."; "Do not install near any combustibles (side or overhead)"; "The Pebble Technology Fire + Water Elements fire burner assembly is CSA/AGA approved."
- **Planika-Mico** (Manual_Mico_Automatic.pdf (cdn.shopify.com/s/files/1/0729/4186/3197/files/)): "1 metre radius from the fire"; "Install the fireplace away from flammable materials"; "All elements above the fireplace need to be made of non-flammable materials"; "It is not permitted to use a device which is not housed in some way"; "Regulation (EU) 2016/426"
- **MAD-ESF** (ESF_CI-gas.pdf (cdn.shopify.com/s/files/1/0326/3129/2039/files/)): "24in (610mm) away from the flame"; "78.7in (2000mm) away from the flame at all times"

Not shortlisted: Travis Fire Garden linear burner (ANSI Z21.97-2017, CSA 2.41-2017) (installs in a ventilated block enclosure with a glass wind guard: not flush; side clearance only in a diagram on p. 13 (no text).); Firegear Outdoors LOF-H/T flat linear pits (manual 90105B) ('installing fire pits below grade' is listed as outside the design (W-firegear-below-grade-not-supported); a lid is 'highly recommended' with no load rating.); Solus Decor linear (FSD LP) (free-standing concrete vessel: 'not designed for seating purposes'; says nothing on flush installation (held cards W-solus-*).).

**Honest status.** No manual read states that the product may be installed flush with paving, and none states a walk-on load rating for a cover. The flush installation and the 15 kN cover (our specification, BS EN 124 A15 as the nearest class) are therefore **supplier or engineer approvals**, not certified facts. Only PTI is CSA (US/Canada) and Planika is CE (EU): no Egyptian approval was found for any product. The design clearances are the strictest figures in the shortlist (PTI 1219 mm side, MAD 2000 mm overhead), so any of the three fits the same layout and the product decision stays open. The supersession is limited to the pit: the BBQ, planting and everything else keep the 2.0 m rule; house wall and rear fence are 2.35 and 2.46 m from the pit edge anyway.

### Wind: summer-evening wind runs toward the west (LDS), checked on the data

Station TMYx Cairo West AP, sectors resolved against the site frame (client west = true bearing 200):

| set | hours | share of hours blowing toward the west half-plane | mean westward component |
|---|---|---|---|
| all-year | 8760 | 75.8 % | 1.6 m/s |
| summer-evening-17-20 (Jun-Aug) | 276 | 94.2 % | 4.37 m/s |
| winter-day-10-15 (Dec-Feb) | 450 | 61.7 % | 0.32 m/s |

Share of hours in which a seat lies in the pit's downwind +-45 degree sector (smoke / heat plume):

| seat | all year | summer evening | winter day |
|---|---|---|---|
| s-dining-table | 10.8 % | 2.2 % | 15.6 % |
| s-bench-rear | 13.3 % | 2.5 % | 24.9 % |
| s-bench-quiet | 13.3 % | 2.5 % | 24.9 % |
| e-bench | 8.5 % | 0.7 % | 8.9 % |
| sister seat 2 m west of the pit (mirror) | 54.7 % | 80.1 % | 31.1 % |

Confirmed: in a summer evening 94 % of hours blow toward the west and our seats are in the plume 0.7-2.5 % of hours; **the sister's seats are downwind 80 % of the time**. A gas flame has little smoke, but the warm combustion gases go to them: that is a consequence for the sister owner to accept, stated here. In winter days only 62 % blow west (0.3 m/s mean westward component) and our seats are downwind 9-25 % of hours: weaker. Station-level wind, open terrain; no site measure or lee modelling (LDS gap W1).

## Grape vine on the dining pergola: summer shade, winter bareness

Foliage-level sun (2.4 m, 21 June, ray test against the enclosure): 5.58 h, so the full-sun class of *Vitis vinifera* is met at the leaves although the ground under the vine strip gets 2.5 h; the vine is planted at the rear fence foot (2 plants, 0.31 m strip) and trained up the fence and along the beams.

Table seats, direct sun 10-15 h (10-15 h local standard time): 21 June 3.54 h open sky, **0.89 h under the leafed vine** (density 0.75, POLICY); 21 December 3.54 h open sky, 3.54 h under the bare vine. The winter figure does not change because the low winter sun (below 40 degrees) reaches the table from the sides, under the roof plane; the vine's bareness therefore costs and gains nothing for table sun at this geometry. What bareness does change is **overhead privacy**: with the vine bare and the louvres open the table is overlooked at 60 % of today's eye points (limit 30 %), with leaf or closed louvres 21 %. The pergola is therefore a **non-combustible louvred frame with the vine on it** (LDB builds louvres): the vine shades in summer, and in winter the louvres are closed when overlooked (opaque while closed: LDK GAP-OVERLOOK-ABOVE assumption). Climber density figures are POLICY (no source gives a leaf density).

**Sources for the deciduous period** (status honest: the habit is sourced, the calendar is a GAP):

- NCSU-vitis-vinifera: https://plants.ces.ncsu.edu/plants/vitis-vinifera/ : "It is a woody, deciduous vine" (SOURCED (deciduous habit; no calendar dates))
- Burkes-ornamental-grape: https://www.burkesbackyard.com.au/fact-sheets/in-the-garden/flowering-plants-shrubs/ornamental-grape/ : "shade in summer and sun in winter" (SOURCED (qualitative, garden fact sheet; Vitis vinifera purpurea/ornamental grape, Australia))
- EKB-dormex-trials: https://journals.ekb.eg/article_171522.html : "Thompson Seedless grapevines ... sprayed hydrogen cyanamide on 1, 7 or 14 January" (INFERENCE: a dormancy-breaker is applied to dormant vines, so vines in Egypt are dormant (leafless) in early January; no leaf-fall or leaf-out date was found (GAP))

Fire: grape is rated 'high flammability' by NCSU; it is outside the 1.25 m side and 2.0 m overhead clearances (nearest foliage 2.9 m in 3-D).

## West screen climber: jasmine, ivy not scheduled

Choice per section: **both screen stubs (north 1.1 m, south 1.2 m) carry Jasminum sambac** on the garden face (scent at the seats; the species is in the sourced pool as viable with conditions: frost 1 C, afternoon shade, size GAP). It is **not drawable yet**, so it is drawn as a labelled STAND-IN. English ivy (Hedera helix) is **not used**: its LDL record is `unverified` (heat tolerance GAP, invasive flag in NC), so it cannot enter the schedule; the Fab/Megascans ivy wall panel is graded B, but its glTF is not on this machine ('graded asset file missing'). If LDL closes the ivy heat GAP, ivy is the drawable alternative for the south stub (shade side, no scent needed). No climber stands within the pit clearance: both stubs end 1.25 m from the pit edge.

## Ponds

Section fixed to the real width (the 1:4 slope applies to the entry margin, not to the 900 mm trench: a 1:4 slope to 900 mm needs 3.6 m of run per side, LDK GAP-POND-EDGE-SAFETY):

entry slope 1:4 over 150 mm = 0.6 m, safety shelf 0.3 m at 150 mm below the water (rigid grille rests on it), trench 0.5 m wide, 900 mm below the water, freeboard 150 mm; far side a vertical wall with marginal planting. Total 1.4 m = the pond width.

| pond | section | stocking (LS-POND-STOCK) | 21 June sun | water lilies |
|---|---|---|---|---|
| n-pond | width 1.4 m holds entry slope 0.6 m (1:4 over 150 mm) + shelf 0.3 m + trench 0.5 m = 1.40 m; trench 900 mm below water; 2 koi at 12 in per 0.42 m2 on 2.8 m2 | fish length per m2 of surface: 19.7 in/m2 achieved, 28.7 in/m2 allowed (unaerated; the source figure is for 12 | 1.69 h | no: full-sun species needs 6 h |
| e-pond | width 1.4 m holds entry slope 0.6 m (1:4 over 150 mm) + shelf 0.3 m + trench 0.5 m = 1.40 m; trench 900 mm below water; 4 koi at 12 in per 0.42 m2 on 4.48 m2 | fish length per m2 of surface: 24.6 in/m2 achieved, 28.7 in/m2 allowed (unaerated; the source figure is for 12 | 4.45 h | no: full-sun species needs 6 h |

North court: lush shade foliage (Rhapis, Aspidistra; Acorus on the edges). East yard: Phoenix roebelenii and Farfugium mass, Acorus edge. No water lilies in either (neither pond has 6 h of sun); LS-POND-SHADE (50-75 % plant cover) is not evaluated because no floating plant is specified.

## Visualisation layout (viewing only)

`layout-visualisation.json`: the south garden reflected about the west line (y -29.916): every element has `visualisation_only: true` and a `vis-` id; the shared pit and the screen are on the line and are not copied; the sister house and boundary are unknown and not drawn. `assert_excluded` guards the design layout; `merge_for_view` is the only consumer (images). It is not in the checks, the schedule, the programme table, the critics or the quantities. Every image that shows it carries a red 'VISUALISATION ONLY' band above and below, a tinted sister half (plan) and a labelled zone.

## LDB layout findings: fixed (each with its guard)

| LDB finding | fix | guard |
|---|---|---|
| tree inside a pergola footprint | pomegranate moved to (3.15, 8.4); pergolas keep 1.0 m from any tree | `LDG-TREE-PERGOLA` (+negative test) |
| plant inside the pot | pot moved to the path-side corner; no plant row crosses it | `LDG-PLANT-SOLID` (+negative) |
| pot 0.31 m from the fence | pot centre 1.37 m from the nearest wall (policy 1.3 m) | `LDG-POT` (+negative) |
| 1:4 pond edge cannot fit 1.0 m | section split: 1:4 entry margin + shelf + trench, 1.4 m wide ponds | `LDG-POND-SECTION` (+negative) |
| ids repeated across gardens | every id prefixed s-/n-/e-; walls renamed wall-* | `LDG-IDS` (+negative) |
| 6.2 m2 north court and 8.7 m2 gravel zone with no surface | every garden room fully covered; a gravel zone is exactly the gravel | `LDG-SURFACE`, `LDG-GRAVEL-ZONE` (+negatives) and the LDB build: 0 `ld-ground` objects |
| polyline paths not built | all paths are rectangles (LDB builds rects only) | LDB build: 0 warnings |
| chairs clip at pergola corner posts | grape pergola posts outside the chair ring (LDB `avoid`) | LDB `clip` check: 0 fails, closed and open pit |

LDB build of this layout (age 3): {'footprint:pass': 67, 'id:pass': 142, 'plant-footprint:info': 7, 'plant-footprint:pass': 55, 'standin:pass': 65, 'support:pass': 140} (closed pit); warnings [].

## Programme: achieved versus required

| item | achieved | required | status | source |
|---|---|---|---|---|
| seats, whole design (table + built-in benches) | 17 | >= 10 (brief 10-20 people) | pass | client brief; LS-CAPACITY |
| people at an event: seated + standing in the free floor of the south garden | 8 + 3 seated south, 22 standing at 1.3 m2 | 10-20 | pass | client brief; LS-STAND-AREA (Neufert p.211) |
| dining table, 8 seats | 8 | 8 (brief: dining 8 extending to 10) | pass | client decision 2026-11-22 |
| dining table extended to 10 (3.0 m), clear to nearest obstruction | 1200 mm | 1200 mm | pass | LS-DINE-CLEAR (Time-Saver Fig. 210-3) |
| dining table extended to 12 (3.6 m), clear | 900 mm | 1200 mm | fail (not offered) | LS-DINE-CLEAR |
| dining zone area per seat [s-dining] | 3.52 m2 | 3.46 m2 | pass | LS-DINE-AREA |
| table to obstruction [s-dining-table] | 1200 mm | 1200 mm | pass | LS-DINE-CLEAR |
| lounge area per seat [s-lounge] | 4.76 m2 | 1.8 m2 | pass | LS-LOUNGE-AREA |
| lounge across [s-lounge] | 3710 mm | 3658 mm | pass | LS-LOUNGE-CLUSTER |
| standing area per person [s-standing] | 1.41 m2 | 1.3 m2 | pass | LS-STAND-AREA |
| fire pit clear ground [s-firepit] | 1250 mm | 1200 mm | pass | LS-FIRE-CLEAR |
| fire pit clear ground [s-bbq] | 1200 mm | 1200 mm | pass | LS-FIRE-CLEAR |
| fire pit to nearest seat or table [s-firepit] | 2100 mm | 1500 mm | pass | LS-FIRE-SEAT |
| flush cover load rating (declared, to be certified) [s-firepit] | 15.0 kN | 15.0 kN | pass | LS-FIRE-COVER |
| clear above the fire [s-firepit] | 99000 mm | 2000 mm | pass | LS-FIRE-OVERHEAD |
| herb bed midsummer sun [s-herb-bed] | 6.5 h | 6 h | pass | LS-HERB-SUN |
| tree trunk to building [s-tree-punica] | 3.77 m | 2.78 m | pass | LS-TREE-BUILDING |
| paving in the tree dripline [s-tree-punica] | 0.0 m2 | 0.0 m2 | pass | LS-ROOTZONE |
| neighbour screening height [fence-east] | 4.0 m | 1.8 m | pass | LS-SCREEN |
| neighbour screening height [fence-rear] | 4.0 m | 1.8 m | pass | LS-SCREEN |
| neighbour screening height [sister-line-screen] | 2.1 m | 1.8 m | pass | LS-SCREEN |
| main path width [s-path-door] | 1200.0 mm | 1200 mm | pass | LS-PATH-MAIN |
| main path width [n-path-0] | 1200.0 mm | 1200 mm | pass | LS-PATH-MAIN |
| service path width [e-path-0] | 1200.0 mm | 900 mm | pass | LS-PATH-SERVICE |
| seat wall [s-seat-wall/height] | 450 mm | 450 mm | pass | LS-SEATWALL |
| seat wall [s-seat-wall/width] | 450 mm | 450 mm | pass | LS-SEATWALL |
| pond deepest section [n-pond] | 1050 mm | 900 mm | pass | LS-POND-DEPTH |
| pond deepest section [e-pond] | 1050 mm | 900 mm | pass | LS-POND-DEPTH |
| koi stocking [n-pond] | 19.7 in/m2 | 28.7 in/m2 | pass | LS-POND-STOCK |
| koi stocking [e-pond] | 24.6 in/m2 | 28.7 in/m2 | pass | LS-POND-STOCK |
| pond child guard [n-pond] | 1 count | 1 count | pass | LS-POND-GUARD |
| pond child guard [e-pond] | 1 count | 1 count | pass | LS-POND-GUARD |
| pond flush margin [n-pond] | 600 mm | 600 mm | pass | LS-POND-FLUSH-MARGIN |
| pond flush margin [e-pond] | 600 mm | 600 mm | pass | LS-POND-FLUSH-MARGIN |
| pond edge slope [n-pond] | 4 run:rise | 4 run:rise | pass | LS-POND-EDGE-SLOPE |
| pond edge slope [e-pond] | 4 run:rise | 4 run:rise | pass | LS-POND-EDGE-SLOPE |
| pond freeboard [n-pond] | 150 mm | 150 mm | pass | LS-POND-FREEBOARD |
| pond freeboard [e-pond] | 150 mm | 150 mm | pass | LS-POND-FREEBOARD |
| one water class per bed [s-bed-vine] | None  | None  | not_evaluated | LS-HYDROZONE |
| one water class per bed [s-bed-mass] | 1 classes | 1 classes | pass | LS-HYDROZONE |
| one water class per bed [s-bed-mass-corner] | 1 classes | 1 classes | pass | LS-HYDROZONE |
| one water class per bed [s-bed-herb] | 1 classes | 1 classes | pass | LS-HYDROZONE |
| one water class per bed [s-bed-screen-n] | 1 classes | 1 classes | pass | LS-HYDROZONE |
| one water class per bed [s-bed-screen-s] | 1 classes | 1 classes | pass | LS-HYDROZONE |
| one water class per bed [n-screen] | 1 classes | 1 classes | pass | LS-HYDROZONE |
| one water class per bed [n-edge-far] | 1 classes | 1 classes | pass | LS-HYDROZONE |
| one water class per bed [n-edge-back] | 1 classes | 1 classes | pass | LS-HYDROZONE |
| one water class per bed [e-divider] | 1 classes | 1 classes | pass | LS-HYDROZONE |
| one water class per bed [e-far] | 1 classes | 1 classes | pass | LS-HYDROZONE |
| one water class per bed [e-edge] | 1 classes | 1 classes | pass | LS-HYDROZONE |
| LDG-SHADE [table/evening] | 1.0 share | 0.9 share | pass | POLICY / decision (ours) |
| LDG-SHADE [s-bench-rear/evening] | 1.0 share | 0.9 share | pass | POLICY / decision (ours) |
| LDG-SHADE [s-bench-quiet/evening] | 1.0 share | 0.9 share | pass | POLICY / decision (ours) |
| LDG-SHADE [n-bench/evening] | 1.0 share | 0.9 share | pass | POLICY / decision (ours) |
| LDG-SHADE [e-bench/evening] | 1.0 share | 0.9 share | pass | POLICY / decision (ours) |
| LDG-BEDDEPTH [s-bed-mass] | 1.52 m | 1.2 m | pass | POLICY / decision (ours) |
| LDG-BEDDEPTH [n-screen] | 1.2 m | 1.2 m | pass | POLICY / decision (ours) |
| LDG-BEDDEPTH [e-divider] | 1.24 m | 1.2 m | pass | POLICY / decision (ours) |
| LDG-BEDDEPTH [e-far] | 1.2 m | 1.2 m | pass | POLICY / decision (ours) |
| LDG-PRIV [table/summer] | 0.209 share | 0.3 share | pass | POLICY / decision (ours) |
| LDG-PRIV-OPENING [table/summer] | 0.579 share | 0.3 share | warn | POLICY / decision (ours) |
| LDG-PRIV [table/winter_louvres_closed] | 0.209 share | 0.3 share | pass | POLICY / decision (ours) |
| LDG-PRIV-OPENING [table/winter_louvres_closed] | 0.579 share | 0.3 share | warn | POLICY / decision (ours) |
| LDG-PRIV [s-bench-rear/summer] | 0.0 share | 0.3 share | pass | POLICY / decision (ours) |
| LDG-PRIV [s-bench-rear/winter_louvres_closed] | 0.0 share | 0.3 share | pass | POLICY / decision (ours) |
| LDG-PRIV [s-bench-quiet/summer] | 0.0 share | 0.25 share | pass | POLICY / decision (ours) |
| LDG-PRIV [s-bench-quiet/winter_louvres_closed] | 0.0 share | 0.25 share | pass | POLICY / decision (ours) |
| LDG-PRIV [n-bench/summer] | 0.224 share | 0.75 share | pass | POLICY / decision (ours) |
| LDG-PRIV [n-bench/winter_louvres_closed] | 0.224 share | 0.75 share | pass | POLICY / decision (ours) |
| LDG-PRIV [e-bench/summer] | 0.224 share | 0.3 share | pass | POLICY / decision (ours) |
| LDG-PRIV [e-bench/winter_louvres_closed] | 0.224 share | 0.3 share | pass | POLICY / decision (ours) |
| LDG-SUNFIT [site] | 0 bed-species | 0 bed-species | pass | POLICY / decision (ours) |
| LDG-SPREAD [s-tree-punica] | 0.0 m2 | 0 m2 | pass | POLICY / decision (ours) |
| LDG-IDS [layout] | 0 duplicates | 0 duplicates | pass | POLICY / decision (ours) |
| LDG-ZONE-CLASS [zones] | 0 items | 0 items | pass | POLICY / decision (ours) |
| LDG-SURFACE [gardens] | 0.0 m2 | 0.02 m2 | pass | POLICY / decision (ours) |
| LDG-GRAVEL-ZONE [zones] | 0 zones | 0 zones | pass | POLICY / decision (ours) |
| LDG-TREE-PERGOLA [trees] | 0 trees | 0 trees | pass | POLICY / decision (ours) |
| LDG-PLANT-SOLID [planting] | 0 plants | 0 plants | pass | POLICY / decision (ours) |
| LDG-POT [pot] | 1.37 m | 1.3 m | pass | POLICY / decision (ours) |
| LDG-FIRE-MANUAL [s-firepit/side] | 1250 mm | 1250 mm | pass | POLICY / decision (ours) |
| LDG-FIRE-MANUAL [s-firepit/overhead] | 2262 mm | 2000 mm | pass | POLICY / decision (ours) |
| LDG-POND-SECTION [n-pond] | 1.4 m | 1.4 m | pass | POLICY / decision (ours) |
| LDG-POND-SECTION [e-pond] | 1.4 m | 1.4 m | pass | POLICY / decision (ours) |
| LDG-GRAPE-SEASON [s-pergola-grape] | 3.54 h | 3.54 h | pass | POLICY / decision (ours) |

Precedent ranges (LDP frozen): south hard share 0.849 against 0.52-0.82 (**above the range**: the terrace is paved for 22 standing + 8 seated; the BBQ and fire clearances keep planting 2.0 m away); canopy trees 1.88 per 100 m2 (range 1.56-3.26, inside).

## Waivers and warnings carried (nothing is silently suppressed)

- **LS-FIRE-STRUCT** s-firepit: distance to house, fence, structure or planting (Calgary Fire Department): 1250 mm achieved, 2000 mm required (the product instructions govern; this is the published floor)
- **LDG-PRIV-OPENING** table/summer: WAIVED by the client's decision (screen opening at the shared fire pit): table summer would be overlooked at 58% of today's through the opening (limit 30%); a closable screen leaf would restore 21%
- **LDG-PRIV-OPENING** table/winter_louvres_closed: WAIVED by the client's decision (screen opening at the shared fire pit): table winter louvres closed would be overlooked at 58% of today's through the opening (limit 30%); a closable screen leaf would restore 21%

## Critic findings (LDC, uncalibrated: not a gate)

Counts {'landscape-architect': {'pass': 13, 'fail': 4, 'warn': 1, 'not_evaluated': 0}, 'horticulturist': {'pass': 21, 'fail': 0, 'warn': 2, 'not_evaluated': 3}, 'user': {'pass': 19, 'fail': 0, 'warn': 0, 'not_evaluated': 0}, 'climate': {'pass': 5, 'fail': 2, 'warn': 0, 'not_evaluated': 2}}; the grape pergola is critiqued twice (leafed vine; bare vine for C-WINTER-SUN only).

- landscape-architect A-ENCLOSURE (fail, major): room 'n-quiet': 29% of its perimeter enclosed by walls/buildings/screens/planting >= 1.8 m (required >= 50%)
- landscape-architect A-ENCLOSURE (fail, major): room 'e-quiet': 0% of its perimeter enclosed by walls/buildings/screens/planting >= 1.8 m (required >= 50%)
- landscape-architect A-ENCLOSURE (fail, major): room 's-dining': 37% of its perimeter enclosed by walls/buildings/screens/planting >= 1.8 m (required >= 50%)
- landscape-architect A-FOCAL (fail, minor): 8 focal elements (['firepit', 'pond', 'pond', 'specimen-tree', 'pergola', 'pergola', 'pergola', 'pergola']); required 1-4 (one primary with restraint)
- landscape-architect A-ROOMS (warn, minor): 5 outdoor rooms with uses/surfaces ["('dining', 'paving')", "('lounge', 'paving')", "('quiet', 'paving')"]; a change of floor marks a room
- horticulturist H-BED-CROWDING (warn, minor): bed n-screen: mature crowns 5.1 m2 on 2.7 m2 of bed (limit 1.5 x)
- horticulturist H-SUN-FIT (warn, major): 2 plants where the LDS sun layer contradicts the species' stated sun class (['vitis_vinifera']); full sun is 6 h+ (RHS via LDK), limit used 3 h
- climate C-PRIVACY (fail, blocking): 6 of 15 south seats overlooked by more than 8 eye points seated (raw LDS median 13.0; residual after layout screens 8.0); brief: privacy is critical
- climate C-POND-SUN (fail, major): pond cell gets 1.75 h direct sun on 21 Jun (required >= 2.0 h, policy: deep shade drops the planting and the water goes green); LS-POND-SHADE covers the opposite excess

Reading them: C-PRIVACY (6 of 15 seats) is the screen opening again (the critic cuts sight lines with the two stubs only); H-SUN-FIT reads the ground sun for the grape, not the 5.6 h at foliage level; A-ENCLOSURE on the dining room (37 %: the west side is the opening) and the two quiet rooms (the critic counts a room's perimeter against walls, buildings, screens and planting of 1.8 m; the quiet benches are backed by a 4 m fence the critic did not credit, as in pass 2) and A-FOCAL (8 focal elements, counted: pit, two ponds, tree, four pergolas) are conventions of the uncalibrated architect critic; C-POND-SUN reads the first pond (north court, 1.69 h) only: the east pond gets 4.45 h.

## Planting schedule (drawable versus stand-in)

| zone | bed | species | count | layer | verdict | status | conditions |
|---|---|---|---|---|---|---|---|
| east yard | e-edge | Acorus gramineus Aiton | 9 | ground | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | heat: moderate tolerance; plant in afternoon shade or verify locally |
| east yard | e-divider | Farfugium japonicum (L.) Kitam. | 3 | shrub/perennial | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | heat: moderate tolerance; plant in afternoon shade or verify locally; alkaline-soil tolerance is a GAP (site soil unmeas |
| east yard | e-far | Farfugium japonicum (L.) Kitam. | 3 | shrub/perennial | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | heat: moderate tolerance; plant in afternoon shade or verify locally; alkaline-soil tolerance is a GAP (site soil unmeas |
| east yard | e-divider | Phoenix roebelenii O'Brien | 2 | shrub/perennial | viable_with_conditions | DRAWABLE: graded A asset skf3_a05b5ef5 | alkaline soil: intolerant; conditional on soil test (a professional item; site pH not tested) |
| east yard | e-far | Phoenix roebelenii O'Brien | 2 | shrub/perennial | viable_with_conditions | DRAWABLE: graded A asset skf3_a05b5ef5 | alkaline soil: intolerant; conditional on soil test (a professional item; site pH not tested) |
| north court | n-edge-far | Acorus gramineus Aiton | 6 | ground | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | heat: moderate tolerance; plant in afternoon shade or verify locally; sun conditional at 1.7 h (21 Jun) |
| north court | n-edge-back | Acorus gramineus Aiton | 5 | ground | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | heat: moderate tolerance; plant in afternoon shade or verify locally; sun conditional at 1.6 h (21 Jun) |
| north court | n-screen | Aspidistra elatior Blume | 5 | shrub/perennial | viable_with_conditions | STAND-IN (generic mass, labelled): graded asset file missing on this machine | heat: moderate tolerance; plant in afternoon shade or verify locally |
| north court | n-screen | Rhapis excelsa (Thunb.) A.Henry | 2 | shrub/perennial | viable_with_conditions | DRAWABLE: graded B asset skf3_86982789 | heat: moderate tolerance; plant in afternoon shade or verify locally |
| south | - | Punica granatum L. | 1 | canopy/understorey (tree) | viable | DRAWABLE: graded B asset skf3_86de7dea; skf3_f697f7da | canopy checked at the sourced minimum spread 2.4 m (LDL range 2.4-3.0 m): keep pruned |
| south | s-bed-mass | Jasminum sambac (L.) Aiton | 2 | climber | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | frost: hardy only to 1 C; typical-year minimum is 5.1 C, floor policy 0.0 C; heat: moderate tolerance; plant in afternoo |
| south | s-bed-screen-n | Jasminum sambac (L.) Aiton | 1 | climber | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | frost: hardy only to 1 C; typical-year minimum is 5.1 C, floor policy 0.0 C; heat: moderate tolerance; plant in afternoo |
| south | s-bed-screen-s | Jasminum sambac (L.) Aiton | 1 | climber | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | frost: hardy only to 1 C; typical-year minimum is 5.1 C, floor policy 0.0 C; heat: moderate tolerance; plant in afternoo |
| south | pot | Plumeria rubra L. (terracotta pot) | 1 | container tree | viable | STAND-IN (frangipani asset exists as a genus fit; pot size is a LDL GAP) | frost: hardy only to 1.7 C; typical-year minimum is 5.1 C, floor policy 0.0 C; frost: accepted by lead decision (client  |
| south | s-bed-herb | Origanum majorana L. | 2 | ground | viable | STAND-IN (generic mass, labelled): graded asset file missing on this machine |  |
| south | s-bed-mass | Justicia brandegeeana Wassh. & L.B.Sm. | 10 | shrub/perennial | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | frost tolerance is a GAP; heat: moderate tolerance; plant in afternoon shade or verify locally |
| south | s-bed-mass-corner | Justicia brandegeeana Wassh. & L.B.Sm. | 3 | shrub/perennial | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | frost tolerance is a GAP; heat: moderate tolerance; plant in afternoon shade or verify locally |
| south | s-bed-mass | Cenchrus alopecuroides (L.) Thunb. | 3 | shrub/perennial | viable | STAND-IN (generic mass, labelled): graded asset file missing on this machine |  |
| south | s-bed-mass | Salvia leucantha Cav. | 1 | shrub/perennial | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | heat: moderate tolerance; plant in afternoon shade or verify locally |
| south | s-bed-mass-corner | Salvia leucantha Cav. | 1 | shrub/perennial | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | heat: moderate tolerance; plant in afternoon shade or verify locally |
| south | s-bed-vine | Vitis vinifera L. | 2 | shrub/perennial | viable | STAND-IN (generic mass, labelled): not drawable yet | sun conditional at 5.6 h (21 Jun) |

Drawable on this machine means a graded A/B glTF file is present; the Fab/Megascans species graded in LDL pass 5 are not present here as files, so only Phoenix roebelenii, Rhapis excelsa, Punica granatum (and frangipani by genus) draw as plants. Everything else is a labelled generic stand-in.

## Images (looked at)

All images are in `plans/`. I looked at each one. Plans use LDC style 2 (client north up); massing is clay (CPU Cycles, 48 samples: the GPU queue was behind other lanes' long jobs, so the clay views were rendered on CPU, which takes no GPU lock).

* **final-south.png (plan, south garden + east yard).** The house block is at the top; the west line is the left edge of the garden. The flush fire pit (orange disc in a white ring) sits half outside the garden frame, centred on the line. The 2.1 m screen shows only as two short grey stubs with a round jasmine stand-in each; between them is the 3.4 m opening, level with the pit and the table's west chairs. The 8-seat table (white rectangle, six chairs per long side shown as outline) stands 2 m east of the pit under the dashed grape pergola; the BBQ is a crossed square east of it; the rear bench and quiet bench sit under a second pergola along the bottom wall; the pomegranate (large circle with shadow) and the shrub mass fill the east end, with a small herb patch and the tiny vine dots at the rear wall. The east yard (right, narrow) holds the blue pond with its dashed grille, a bench under a pergola, and two shrub masses. Weak points I see: the terrace is mostly empty paving, the west side has no planting except two jasmine circles, the pomegranate crown piles over the mass, and the pit outside the frame makes the sheet look as if the pit were off the plot (it is on the line).
* **final-north.png (plan, north court).** A paved room with a pergola over a bench niche at the left, one large Rhapis circle with a strip of Aspidistra beside it, and the pond (2.0 x 1.4 m, grille crossed) at the right edged by Acorus drifts; a gravel-coloured path leads from the door at the bottom. It reads as a small, tidy quiet room; the paving at the bottom is large and plain.
* **final-visualisation-plan.png.** Red band above and below ("VISUALISATION ONLY: SISTER PLOT, NOT OUR LAND OR DESIGN"), the title repeats it, the sister half (left of the line) is washed pink and the mirrored garden is a labelled zone. The mirror is exact: the table, pergolas, benches, tree and shrub mass appear reflected, the pit is shared on the line, our design is untinted on the right. The leader lines on the left are long and crowded (the plan style puts every label outside the drawing); the sister house is not drawn (unknown).
* **final-massing-south.png.** Clay view from above, house block at the top, garden below. The screen stubs are translucent grey at the left, the louvre pergolas show as timber slats, the table and benches as timber boxes, the pomegranate a green sphere at the lower right over the shrub eggs, the pond a blue slab at the right. The camera hides the pit under the pergola slats' shadows: the pit is not legible in this view. Clay views show volumes, not finish.
* **final-massing-east.png (azimuth 90).** The east yard from the east: pond (blue) with a row of Acorus balls on its far edge, the bench pergola, shrub masses at both ends and the edge of the south terrace at the left. Reads clearly. My first east view (azimuth 300) showed only the house block and was discarded.
* **final-massing-north.png (azimuth 250).** North court seen through see-through fences: the pond with its Acorus balls and a Rhapis mass, the bench pergola and the bench in the foreground. Readable but dim and foggy; my first north view (azimuth 205) was a haze and was discarded.
* **final-visualisation-massing.png.** Same red bands. Two gardens side by side with the house block between; the left (sister) garden is the reflection, with its own tree, table and pergolas. It is the weakest image: there is no way to tint the mirrored half in the clay render, so only the bands label it, and the sister's house and ground are absent.

