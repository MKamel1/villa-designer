# Final garden design: concept B adapted (LDG round 2, 2026-11-22)

Client decisions applied: concept B adapted; shared gas fire pit on the west line; west screen tall except an opening at the pit; **round 3 (client 2026-11-22): trimmed shade trees instead of pergolas, deciduous preferred (sun in Dec-Feb welcome), layered planting everywhere**; both ponds kept; mirrored visualisation of the south garden on the sister plot (viewing only). Numbers below are generated from `final.json`; `layout-final.json` is the design, `layout-visualisation.json` is the mirror (excluded everywhere).

**Result: 0 hard failures.** Tally {'pass': 140, 'fail': 0, 'warn': 4, 'not_evaluated': 8}. LDK `LS-FIRE-STRUCT` (2.0 m open-fire floor, a wood-fire bylaw) is reported as a warning for the pit and replaced by the manuals' own clearances (see Fire pit); the client's screen opening is recorded as a visible waiver (`LDG-PRIV-OPENING`). Critic findings are listed, not gated.

## The design in one paragraph

South garden (5.71 x 9.32 m): the **social terrace** at the west. The flush gas fire pit (0.9 m envelope) is centred ON the west line; the 2.1 m screen stops 1.25 m from its edge on both sides (grape on the north stub, sambac jasmine on the south stub, each in a 1.3 m deep bed). The BBQ stand place and a standing area sit between pit and table; the dining table (8, extending to 10) moved east to b 4.05-4.95 so that **one deciduous crape myrtle (pruned multi-stem head, 4.0 m, leaning toward the table) is its roof**; the floor under both crowns is permeable gravel (LS-ROOTZONE keeps paving out of every dripline). A built-in bench (2 seats) and a quiet bench (2 seats) run along the rear wall under a pruned **evergreen olive** (year-round overhead privacy where winter sun is small anyway); the pomegranate stays as the understorey fruit tree. A planted edge runs along the south wall (climbers on the wall face), a planted mass closes the east. East yard: the quiet room (bench, flush koi pond) under a smaller pruned olive. North court: the second quiet room (bench niche, planted screen, flush koi pond with shade foliage); no tree fits there (see Layers). Both ponds are kept for now.

## Fire pit on the west line

Position: centre at the west line (b 0.0), 2.8 m from the house face and 2.9 m from the rear fence. Screen opening a 1.1-4.5 m along the line; each screen end is 1250 mm from the pit edge, nothing combustible (planting, tree crown) is within 1250 mm sideways or 2000 mm overhead (measured straight-line to the burner, `LDG-FIRE-MANUAL`). The nearest crown is the crape's, more than 3 m from the burner in plan and above 2.2 m. The pit straddles the boundary: the fixture needs the sister owner's agreement (client's matter). In the schedule: one shared flush gas pit, our share 50 % (`our_share`); the sister's seats exist only in the visualisation.

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

**Honest status.** No manual read states that the product may be installed flush with paving, and none states a walk-on load rating for a cover. The flush installation and the 15 kN cover (our specification, BS EN 124 A15 as the nearest class) are therefore **supplier or engineer approvals**, not certified facts. Only PTI is CSA (US/Canada) and Planika is CE (EU): no Egyptian approval was found for any product. The design clearances are the strictest figures in the shortlist (PTI 1219 mm side, MAD 2000 mm overhead), so any of the three fits the same layout and the product decision stays open. The supersession applies to the pit and the BBQ stand only (the BBQ by its own manual, see Trade: BBQ); house wall and rear fence are 2.35 and 2.46 m from the pit edge anyway.

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

## Shade trees instead of pergolas

Client 2026-11-22: remove the pergolas, use trimmed shade trees, evergreen NOT required ("we don't mind the sun in Dec to Feb"): deciduous or semi-deciduous trees that are bare from about December to February and in leaf March to November are preferred; olive only where year-round screening matters more.

### Candidates compared on data (LDL plants.json figures; NHBC distance = 0.5 / 0.75 / 1.25 x height for low / moderate / high water demand, LS-TREE-BUILDING)

| tree | habit | height; spread | roots; soil | NHBC distance needed | best asset grade | draw | decision and reason |
|---|---|---|---|---|---|---|---|
| Lagerstroemia indica L. | deciduous | 9.1 m; 1.8-9.1 m | benign; alkaline tolerant | 6.82 m (pruned 4.5 m: 3.38 m) | B | drawable | PICKED over the dining: deciduous, graded B asset, benign roots, high heat, tolerates alkaline soil, non-toxic, summer flowers (Jul-Sep: the summer evenings), pruning regime sourced (UF/IFAS EP399, excerpt). NHBC fits only at the pruned height. |
| Jacaranda mimosifolia D.Don | deciduous | 15.2 m; 4.6-7.6 m | benign; alkaline moderate | 7.6 m | A | drawable | REJECTED for these gardens: graded A and deciduous, but 15.2 m mature height needs 7.6 m from the house (low water) and the sourced minimum spread 4.6 m will not fit; no source on holding it at 4.5 m; messy (leaf and flower litter). Fits a larger plot. |
| Delonix regia (Bojer ex Hook.) Raf. | semi_evergreen | 18 m; None-None m | aggressive; alkaline intolerant | 9.0 m | A | drawable | REJECTED: graded A, but alkaline soil intolerant (LDL), aggressive shallow roots that lift walls, 18 m. |
| Punica granatum L. | deciduous | 3.7 m; 2.4-3.0 m | benign; alkaline tolerant | 2.78 m | B | drawable | KEPT as the understorey fruit tree (graded B, deciduous, benign roots); too small to roof a seat (spread 2.4-3.0 m) and NHBC moderate x 3.7 m = 2.8 m cannot fit the east yard (2.3 m to the house wall). |
| Ficus carica L. | deciduous | 9.1 m; 3.0-9.1 m | benign; alkaline intolerant | 6.82 m | - | stand-in | REJECTED: deciduous and fruiting but not drawable, alkaline soil intolerant (LDL) in a site of unknown soil pH, suckers; wet-fruit litter. |
| Tipuana tipu (Benth.) Kuntze | semi_evergreen | 30 m; None-None m | benign; alkaline intolerant | 22.5 m | - | stand-in | REJECTED: its leaf-drop window (midwinter to spring) is sourced but leaves the hot early spring bare; large (30 m), invasive flag, alkaline intolerant. |
| Olea europaea L. | evergreen | 9.1 m; 4.6-7.6 m | moderate; alkaline moderate | 4.55 m (pruned 4.5 m: 2.25 m) | C | stand-in | PICKED where year-round screening matters (quiet bench, east yard bench) and winter sun is already small: evergreen, low water (NHBC 0.5), roots moderate; stand-in asset only (grade C); NO source on umbrella pruning (GAP, stated). |
| Ficus microcarpa L.fil. | evergreen | 15.2 m; 0.6-12.2 m | aggressive; alkaline tolerant | 11.4 m | - | stand-in | REJECTED: densest shade but aggressive roots (LDL): needs 6 m (policy) from a pond or building: no position in the 5.7 m x 9.3 m garden or the courts; invasive flag; ('Nitida' clipping tolerance is well attested in trade sources, not used). |
| Citrus × limon (L.) Osbeck | evergreen | 6.1 m; 3.0-4.6 m | benign; alkaline moderate | 7.62 m | A | drawable | REJECTED as a shade tree: light shade, 6.1 m, hydrozone high (needs its own bed), thorny; graded A, fine as a fruit tree elsewhere. |
| melia azedarach | not in the LDL pool | - | - | - | - | - | no LDL record, no graded asset; no Cairo leaf-month source found (street-tree surveys of Greater Cairo exist but the excerpts read give no phenology); not evaluated |
| bauhinia variegata | not in the LDL pool | - | - | - | - | - | no LDL record, no graded asset; no leaf-month source found; not evaluated |
| morus alba | not in the LDL pool | - | - | - | - | - | no LDL record, no graded asset; fruit stains paving (not tested); no leaf-month source found; not evaluated |
| ceratonia siliqua | not in the LDL pool | - | - | - | - | - | no LDL record (large evergreen, brief names it); not evaluated |

**Leaf-drop and leaf-out months for a Cairo-like climate: a GAP for every species.** The searches of 2026-11-22 found habit statements (deciduous, semi-deciduous, evergreen) and one southern-hemisphere calendar that does not transfer, no Egypt or Cairo calendar. The design therefore uses the client's own months (bare December-February, in leaf March-November) as a stated ASSUMPTION; before purchase a Cairo nursery should confirm the crape myrtle's leaf-out month. Evidence per species:

- Lagerstroemia indica L.: deciduous (LDL: UF/IFAS ST342 'deciduous', autumn colour yellow/orange/red); Cairo leaf-drop and leaf-out months: GAP (no Egypt source found)
- Jacaranda mimosifolia D.Don: deciduous or semi-deciduous (LDL, NCSU: flowers while leafless); UF/IFAS ST317 excerpt: blooms April-August, sometimes before the new leaves; a Zambian guide gives leaf fall July-August (southern hemisphere: NOT used); Cairo months: GAP
- Delonix regia (Bojer ex Hook.) Raf.: semi-evergreen (LDL); Cairo months: GAP
- Punica granatum L.: deciduous (LDL: NCSU, SelecTree); Cairo months: GAP
- Ficus carica L.: deciduous (LDL); Cairo months: GAP
- Tipuana tipu (Benth.) Kuntze: semi-evergreen, 'largely deciduous midwinter to spring depending on site' (LDL, Wikipedia excerpt): the only sourced drop window, and it runs into the hot months
- Olea europaea L.: evergreen (LDL, NCSU)
- Ficus microcarpa L.fil.: evergreen (LDL, NCSU)
- Citrus × limon (L.) Osbeck: evergreen (LDL)

### Where each pick stands, and why (per location)

- **Dining (south): crape myrtle** (Lagerstroemia indica), deciduous, graded B asset. 4.0 m pruned head, 4.5 m high, trunk 3.45 m from the house (needs 3.38 m at the pruned height: the NHBC pass depends on the pruning being kept; at its species height of 9.1 m it would need 6.8 m). Dripline kept free of paving (gravel). Roots benign.
- **Quiet bench and rear bench (south): olive** (evergreen, stand-in asset grade C). Chosen over a second deciduous tree because winter sun is already 1.6-1.8 h there (the sun-poor corner of the garden) and the quiet corner is where privacy matters year-round: with the olive it is overlooked at 4 % of today's in winter; with no tree 56 %.
- **East yard bench: olive**, smaller head (2.6 m). Only an olive fits: NHBC low water 0.5 x 4.5 m = 2.25 m against 2.3 m available from the house wall; a pomegranate (2.8 m) or a crape (3.4 m) would need more.
- **North court: no tree.** 3.74 m deep, 1.3 h of June sun, a pond in the middle, house wall on one side; the clipped Ficus (aggressive roots, needs 6 m from pond and building) and every other candidate fail one of these. Overhead privacy at its bench is inside the 75 % limit for that room without a canopy.

### Pruning is a maintenance specification

Species figures stay in LDL; the layout carries the pruned size. Regimes (`TREE_PRUNING` in final.py; each tree carries its regime as `pruning`):

- Crape myrtle: multi-stem (3-5 stems), clear trunk to 2.2 m, head 4.0 m trained to lean up to 1.3 m toward the table, structural thinning every January-February while bare, cut back to previous heads (never flat topping), base suckers removed twice a year. **Source:** UF/IFAS EP399 "What is a crape murder?" (hard pruning and pollarding make vigorous sprouts and, once started, need annual pruning; blooms fall with the size of branch removed). Status: read as a search excerpt, the page itself was not fetched; tolerance of a held 4.0 m head is INFERENCE from "pollarding keeps a plant at a set height".
- Olive (south 3.6 m, east yard 2.6 m): pruned multi-stem umbrella, thinned each late winter. **Source: GAP** (no source on olive tolerance of a held umbrella head was found); the olive picks are conditional on a nursery or arborist confirming it. `LDG-PRUNE` fails any pruned tree with no declared regime.
- Clipped Ficus microcarpa 'Nitida': trade sources attest tolerance of shearing; not used, so not relied on.

### Summer shade and winter sun at the seats (leaf-on and leaf-off; ray test against the enclosure; crown density from the LDC CROWN assumption: evergreen 0.8, leaf-on 0.7, bare 0.15; no held source gives a leaf density)

| seat | 21 Jun 10-15 h: open sky | leafed crown | 21 Dec 10-15 h: open sky | bare crown | if the crown kept its leaves |
|---|---|---|---|---|---|
| table | 3.62 | 1.17 | 3.12 | 3.12 | 3.12 |
| s-bench-rear | 3.0 | 1.09 | 1.75 | 1.75 | 1.75 |
| s-bench-quiet | 3.0 | 0.6 | 1.75 | 1.64 | 1.22 |
| e-bench | 4.75 | 1.35 | 0.25 | 0.25 | 0.25 |

Reading: the table is the **winter-sun sitting place**, with 3.1 h of the 5 h window outside every crown, and the place where the crape halves the summer sun (3.6 to 1.2 h). Evening 17-20 h on the DST clock is sun-free at every seat from the structure alone (0 h in the LDS layer), so the leaf-on state costs nothing there. The crape sits to the east and above the table, so its leaves make no difference to the table's December sun (3.1 h either way): at this geometry deciduous versus evergreen only matters at the quiet bench (1.6 h bare against 1.2 h leafed). The east yard bench has 0.25 h of December sun whatever the tree does.

### Overhead privacy from the apartment above, at each seat (share of today's overlooking that remains)

| seat | no tree | summer, leafed | winter, bare crowns | limit |
|---|---|---|---|---|
| table | 65 % | 18 % | 65 % | 30 % |
| s-bench-rear | 62 % | 21 % | 21 % | 30 % |
| s-bench-quiet | 56 % | 4 % | 4 % | 25 % |
| n-bench | 50 % | 50 % | 50 % | 75 % |
| e-bench | 82 % | 5 % | 5 % | 30 % |

The canopy counts as cover only where a crown stands over the seat (crown disc as 0.25 m cells; leafed in summer, evergreen only in winter). **Summer** is hard (every seat inside its limit). **Winter** is the cost of deciduous: the table goes back to the 'no tree' figure (65 %, limit 30 %) while the crape is bare; the rear bench stays covered by the olive, reported as `LDG-PRIV-WINTER` warnings with the figures; the client accepted winter sun, but a winter lunch is overlooked more than a summer one. The olives keep the quiet bench and the east yard bench covered all year. Fire pit: no crown within 2.0 m overhead (`LDG-FIRE-MANUAL`).

### Trade: the BBQ stand place

With two shade trees, the beds and the seating, no position in the garden keeps the LDK 2.0 m open-fire floor from planting, crowns and the house. The BBQ is a small portable gas grill (brief), so its clearance follows a manual: **Weber Q1200 owner's manual** (ManualsLib page 2; the Weber PDF is an image without text): "Keep the grill a minimum of 24 inches away from recreational vehicles and combustible materials like wood, paper, cloth and plastic." and "Do not use in a garage, building, breezeway, tent, any other enclosed area or beneath overhead combustible construction." Design: 650 mm to any combustible, structure or planting and 300 mm outside every crown projection (`LDG-BBQ-MANUAL`; the LDK floor is still reported). The product is NOT chosen: the figure stands in for any small gas grill and is re-checked at product choice. **Cost: the BBQ moved to the west terrace between the pit and the table and the table moved 1.4 m east; seated bench places fell from 5 to 4 in the lounge/rear bench count (3 to 2).**

## Climbers, layers and drifts

Climbers on every screen and wall face (a climber within 0.9 m of the face; the house facade stays clear for the fire items):

| face | climbers |
|---|---|
| screen N stub | vitis_vinifera |
| screen S stub | jasminum_sambac |
| south garden rear wall | jasminum_sambac, petrea_volubilis |
| south garden east fence | jasminum_sambac, petrea_volubilis |
| north court street fence | jasminum_sambac |

**East yard: no climber.** Its south boundary is not a declared wall in the layout (the site fragment has `fence-east` from x 22.6 only), so a climber there would be drawn as a free mound (LDB warns) and is not claimed; the yard has a tree, shrubs, perennials and groundcover. Declare the fence, then add climbers (open item).

Grape (Vitis vinifera, deciduous) stands on the north screen stub: it moved from the pergola to the screen as a climber (the client keeps the fruit); NCSU rates it high flammability, and it stays outside the 1.25 m side clearance of the pit. Sambac jasmine and Petrea cover the south stub, the rear wall and the south garden's east fence (Jasminum grandiflorum is not in the layout). English ivy is still **not used** (heat tolerance GAP in LDL); creeping fig, star jasmine and bougainvillea climber panels were not yet graded on this branch, so every climber is a labelled stand-in or a genus mass.

### Layer table per garden room (plants counted from the layout; classification by LDL layer and height)

| room | canopy | understorey | shrub | perennial | groundcover | climber | missing |
|---|---|---|---|---|---|---|---|
| south garden | 2 (2 sp) | 5 (4 sp) | 8 (2 sp) | 6 (2 sp) | 20 (2 sp) | 14 (3 sp) | none |
| east yard | 1 (1 sp) | 2 (1 sp) | 2 (1 sp) | 6 (1 sp) | 9 (1 sp) | 0 (0 sp) | climber |
| north court | 0 (0 sp) | 1 (1 sp) | 1 (1 sp) | 2 (1 sp) | 14 (2 sp) | 3 (1 sp) | canopy |

North court has no canopy tree for the reasons above. **Precedent comparison (LDP frozen ranges, south garden):** layer shares are a GAP in LDP (fewer than 6 usable gardens), so there is no layer range to compare against; hard share and trees per 100 m2 have ranges (below). **Advisory pattern rules (qualitative, no score):** AD-COMP-TREE-CANOPY (a shade tree as the roof of a gathering place with a seat beneath: crape over the table, olive over the quiet bench); AD-COMP-LAYERING (foreground, middle, background in layers: the beds above); AD-APL-246 Climbing Plants (climbers on sunny walls and trellises: rear wall, east fence, screen stubs); AD-APL-170 Fruit Trees (a group, not a single tree: only a pomegranate and a grape, a thin answer); AD-EXT-OVERLOOK (canopy does the work a hedge cannot against the apartment above: summer figures above); AD-EXT-SHADE-PLACEMENT (deciduous trees to the east of the use area: the crape stands east of the table); AD-EXT-POND-SITING (no trees over ponds: the east olive's crown reaches the pond end, evergreen with small leaf fall; flagged); AD-EXT-TREE-BARRIER (no root barrier is relied on, only distance); AD-LECH-SHADE (trees chosen by compass side: the sun-path result above).

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
| tree inside a pergola footprint | pergolas removed (round 3); the check stays and is quiet | `LDG-TREE-PERGOLA` (+negative test) |
| plant inside the pot | pot moved to the path-side corner; no plant row crosses it | `LDG-PLANT-SOLID` (+negative) |
| pot 0.31 m from the fence | pot centre 1.37 m from the nearest wall (policy 1.3 m) | `LDG-POT` (+negative) |
| 1:4 pond edge cannot fit 1.0 m | section split: 1:4 entry margin + shelf + trench, 1.4 m wide ponds | `LDG-POND-SECTION` (+negative) |
| ids repeated across gardens | every id prefixed s-/n-/e-; walls renamed wall-* | `LDG-IDS` (+negative) |
| 6.2 m2 north court and 8.7 m2 gravel zone with no surface | every garden room fully covered; a gravel zone is exactly the gravel | `LDG-SURFACE`, `LDG-GRAVEL-ZONE` (+negatives) and the LDB build: 0 `ld-ground` objects |
| polyline paths not built | all paths are rectangles (LDB builds rects only) | LDB build: 0 warnings |
| chairs clip at pergola corner posts | no pergola posts remain | LDB `clip` check: 0 fails, closed and open pit |

LDB build of this layout (age 3): {'climber-coverage:pass': 5, 'footprint:pass': 62, 'id:pass': 180, 'pit-half:pass': 2, 'plant-footprint:info': 7, 'plant-footprint:pass': 66, 'pond-section:pass': 18, 'standin:pass': 96, 'support:pass': 178} (closed pit); warnings [].

## Programme: achieved versus required

| item | achieved | required | status | source |
|---|---|---|---|---|
| seats, whole design (table + built-in benches) | 16 | >= 10 (brief 10-20 people) | pass | client brief; LS-CAPACITY |
| people at an event: seated + standing in the free floor of the south garden | 8 + 2 seated south, 19 standing at 1.3 m2 | 10-20 | pass | client brief; LS-STAND-AREA (Neufert p.211) |
| dining table, 8 seats | 8 | 8 (brief: dining 8 extending to 10) | pass | client decision 2026-11-22 |
| dining table extended to 10 (3.0 m), clear to nearest obstruction | 1200 mm | 1200 mm | pass | LS-DINE-CLEAR (Time-Saver Fig. 210-3) |
| dining table extended to 12 (3.6 m), clear | 900 mm | 1200 mm | fail (not offered) | LS-DINE-CLEAR |
| dining zone area per seat [s-dining] | 3.52 m2 | 3.46 m2 | pass | LS-DINE-AREA |
| table to obstruction [s-dining-table] | 1200 mm | 1200 mm | pass | LS-DINE-CLEAR |
| lounge area per seat [s-lounge] | 7.14 m2 | 1.8 m2 | pass | LS-LOUNGE-AREA |
| lounge across [s-lounge] | 3710 mm | 3658 mm | pass | LS-LOUNGE-CLUSTER |
| standing area per person [s-standing] | 1.63 m2 | 1.3 m2 | pass | LS-STAND-AREA |
| fire pit clear ground [s-firepit] | 1250 mm | 1200 mm | pass | LS-FIRE-CLEAR |
| fire pit clear ground [s-bbq] | 1238 mm | 1200 mm | pass | LS-FIRE-CLEAR |
| fire pit to nearest seat or table [s-firepit] | 3600 mm | 1500 mm | pass | LS-FIRE-SEAT |
| flush cover load rating (declared, to be certified) [s-firepit] | 15.0 kN | 15.0 kN | pass | LS-FIRE-COVER |
| clear above the fire [s-firepit] | 99000 mm | 2000 mm | pass | LS-FIRE-OVERHEAD |
| herb bed midsummer sun [s-herb-bed] | 6.5 h | 6 h | pass | LS-HERB-SUN |
| tree trunk to building [s-tree-crape] | 3.45 m | 3.38 m | pass | LS-TREE-BUILDING |
| tree trunk to building [s-tree-olive] | 4.34 m | 2.25 m | pass | LS-TREE-BUILDING |
| tree trunk to building [s-tree-punica] | 3.77 m | 2.78 m | pass | LS-TREE-BUILDING |
| tree trunk to building [e-tree-olive] | 2.3 m | 2.25 m | pass | LS-TREE-BUILDING |
| paving in the tree dripline [s-tree-crape] | 0.0 m2 | 0.0 m2 | pass | LS-ROOTZONE |
| paving in the tree dripline [s-tree-olive] | 0.0 m2 | 0.0 m2 | pass | LS-ROOTZONE |
| paving in the tree dripline [s-tree-punica] | 0.0 m2 | 0.0 m2 | pass | LS-ROOTZONE |
| paving in the tree dripline [e-tree-olive] | 0.0 m2 | 0.0 m2 | pass | LS-ROOTZONE |
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
| one water class per bed [s-bed-mass] | 1 classes | 1 classes | pass | LS-HYDROZONE |
| one water class per bed [s-bed-mass-corner] | 1 classes | 1 classes | pass | LS-HYDROZONE |
| one water class per bed [s-bed-herb] | 1 classes | 1 classes | pass | LS-HYDROZONE |
| one water class per bed [s-bed-screen-n] | None  | None  | not_evaluated | LS-HYDROZONE |
| one water class per bed [s-bed-screen-s] | 1 classes | 1 classes | pass | LS-HYDROZONE |
| one water class per bed [s-bed-wall] | 1 classes | 1 classes | pass | LS-HYDROZONE |
| one water class per bed [s-bed-wall-b] | 1 classes | 1 classes | pass | LS-HYDROZONE |
| one water class per bed [s-bed-wall-c] | 1 classes | 1 classes | pass | LS-HYDROZONE |
| one water class per bed [s-bed-pocket] | 1 classes | 1 classes | pass | LS-HYDROZONE |
| one water class per bed [n-screen] | 1 classes | 1 classes | pass | LS-HYDROZONE |
| one water class per bed [n-edge-far] | 1 classes | 1 classes | pass | LS-HYDROZONE |
| one water class per bed [n-edge-back] | 1 classes | 1 classes | pass | LS-HYDROZONE |
| one water class per bed [e-divider] | 1 classes | 1 classes | pass | LS-HYDROZONE |
| one water class per bed [e-far] | 1 classes | 1 classes | pass | LS-HYDROZONE |
| one water class per bed [e-edge] | 1 classes | 1 classes | pass | LS-HYDROZONE |
| LDG-SHADE [table/evening] | 1.0 share | 0.9 share | pass | POLICY / decision (ours) |
| LDG-SHADE [s-bench-rear/evening] | 1.0 share | 0.9 share | pass | POLICY / decision (ours) |
| LDG-SHADE [s-bench-quiet/evening] | 0.9 share | 0.9 share | pass | POLICY / decision (ours) |
| LDG-SHADE [n-bench/evening] | 1.0 share | 0.9 share | pass | POLICY / decision (ours) |
| LDG-SHADE [e-bench/evening] | 1.0 share | 0.9 share | pass | POLICY / decision (ours) |
| LDG-BEDDEPTH [s-bed-mass] | 1.52 m | 1.2 m | pass | POLICY / decision (ours) |
| LDG-BEDDEPTH [n-screen] | 1.2 m | 1.2 m | pass | POLICY / decision (ours) |
| LDG-BEDDEPTH [e-divider] | 1.24 m | 1.2 m | pass | POLICY / decision (ours) |
| LDG-BEDDEPTH [e-far] | 1.2 m | 1.2 m | pass | POLICY / decision (ours) |
| LDG-PRIV [table/summer] | 0.183 share | 0.3 share | pass | POLICY / decision (ours) |
| LDG-PRIV-WINTER [table/winter] | 0.652 share | 0.3 share | warn | POLICY / decision (ours) |
| LDG-PRIV-OPENING [table/summer] | 0.508 share | 0.3 share | warn | POLICY / decision (ours) |
| LDG-PRIV [s-bench-rear/summer] | 0.211 share | 0.3 share | pass | POLICY / decision (ours) |
| LDG-PRIV [s-bench-quiet/summer] | 0.039 share | 0.25 share | pass | POLICY / decision (ours) |
| LDG-PRIV [n-bench/summer] | 0.496 share | 0.75 share | pass | POLICY / decision (ours) |
| LDG-PRIV [e-bench/summer] | 0.051 share | 0.3 share | pass | POLICY / decision (ours) |
| LDG-SUNFIT [site] | 0 bed-species | 0 bed-species | pass | POLICY / decision (ours) |
| LDG-SPREAD [s-tree-crape] | 0.0 m2 | 0 m2 | pass | POLICY / decision (ours) |
| LDG-SPREAD [s-tree-olive] | 0.0 m2 | 0 m2 | pass | POLICY / decision (ours) |
| LDG-SPREAD [s-tree-punica] | 0.0 m2 | 0 m2 | pass | POLICY / decision (ours) |
| LDG-SPREAD [e-tree-olive] | 0.0 m2 | 0 m2 | pass | POLICY / decision (ours) |
| LDG-IDS [layout] | 0 duplicates | 0 duplicates | pass | POLICY / decision (ours) |
| LDG-ZONE-CLASS [zones] | 0 items | 0 items | pass | POLICY / decision (ours) |
| LDG-SURFACE [gardens] | 0.0 m2 | 0.02 m2 | pass | POLICY / decision (ours) |
| LDG-GRAVEL-ZONE [zones] | 0 zones | 0 zones | pass | POLICY / decision (ours) |
| LDG-TREE-PERGOLA [trees] | 0 trees | 0 trees | pass | POLICY / decision (ours) |
| LDG-PLANT-SOLID [planting] | 0 plants | 0 plants | pass | POLICY / decision (ours) |
| LDG-POT [pot] | 1.37 m | 1.3 m | pass | POLICY / decision (ours) |
| LDG-FIRE-MANUAL [s-firepit/side] | 1250 mm | 1250 mm | pass | POLICY / decision (ours) |
| LDG-FIRE-MANUAL [s-firepit/overhead] | 2193 mm | 2000 mm | pass | POLICY / decision (ours) |
| LDG-BBQ-MANUAL [s-bbq] | 670 mm | 650 mm | pass | POLICY / decision (ours) |
| LDG-POND-SECTION [n-pond] | 1.4 m | 1.4 m | pass | POLICY / decision (ours) |
| LDG-POND-SECTION [e-pond] | 1.4 m | 1.4 m | pass | POLICY / decision (ours) |
| LDG-PRUNE [s-tree-crape] | 4.0 m | None m | pass | POLICY / decision (ours) |
| LDG-PRUNE [s-tree-olive] | 3.6 m | None m | pass | POLICY / decision (ours) |
| LDG-ROOTS [s-tree-olive] | 6.69 m | 1.5 m | pass | POLICY / decision (ours) |
| LDG-PRUNE [e-tree-olive] | 2.6 m | None m | pass | POLICY / decision (ours) |
| LDG-ROOTS [e-tree-olive] | 1.55 m | 1.5 m | pass | POLICY / decision (ours) |
| LDG-TREE-SUN [s-tree-crape] | 6.0 h | None h | pass | POLICY / decision (ours) |
| LDG-TREE-SUN [s-tree-olive] | 7.25 h | None h | pass | POLICY / decision (ours) |
| LDG-TREE-SUN [s-tree-punica] | 9.5 h | None h | pass | POLICY / decision (ours) |
| LDG-TREE-SUN [e-tree-olive] | 10.0 h | None h | pass | POLICY / decision (ours) |
| LDG-SHADE-SUMMER [table] | 1.17 h | 2.17 h | pass | POLICY / decision (ours) |
| LDG-SHADE-WINTER [table] | 3.12 h | 2.5 h | pass | POLICY / decision (ours) |
| LDG-WINTER-SEAT [table] | 3.12 h | 2.5 h | pass | POLICY / decision (ours) |

Precedent ranges (LDP frozen): south hard share **0.849 before -> 0.756 after** against 0.52-0.82 (inside; gravel counts as hard); trees 5.64 per 100 m2 in the south garden (range 1.56-3.26: **above**: the three trees are two crowns and the small pomegranate in 53 m2, the cost of replacing two pergolas by trees; the east yard olive is not counted); standing at an event 19 (was 22).

## Waivers and warnings carried (nothing is silently suppressed)

- **LS-FIRE-STRUCT** s-firepit: distance to house, fence, structure or planting (Calgary Fire Department): 1250 mm achieved, 2000 mm required (the product instructions govern; this is the published floor)
- **LS-FIRE-STRUCT** s-bbq: distance to house, fence, structure or planting (Calgary Fire Department): 1238 mm achieved, 2000 mm required (the product instructions govern; this is the published floor)
- **LDG-PRIV-WINTER** table/winter: table, winter (deciduous crowns bare): 65% of today's overlooking remains (limit 30%); accepted with the winter sun (client 2026-11-22), shown not hidden
- **LDG-PRIV-OPENING** table/summer: WAIVED by the client's decision (screen opening at the shared fire pit): table summer would be overlooked at 51% of today's through the opening (limit 30%); a closable screen leaf would restore 18%

## Critic findings (LDC, uncalibrated: not a gate)

Counts {'landscape-architect': {'pass': 14, 'fail': 3, 'warn': 1, 'not_evaluated': 0}, 'horticulturist': {'pass': 23, 'fail': 2, 'warn': 2, 'not_evaluated': 3}, 'user': {'pass': 17, 'fail': 2, 'warn': 0, 'not_evaluated': 0}, 'climate': {'pass': 6, 'fail': 1, 'warn': 0, 'not_evaluated': 2}}; trees carry their habit, so the critics use the leafed density in summer windows and the bare density in the winter window.

- landscape-architect A-ENCLOSURE (fail, major): room 'n-quiet': 29% of its perimeter enclosed by walls/buildings/screens/planting >= 1.8 m (required >= 50%)
- landscape-architect A-ENCLOSURE (fail, major): room 'e-quiet': 0% of its perimeter enclosed by walls/buildings/screens/planting >= 1.8 m (required >= 50%)
- landscape-architect A-ENCLOSURE (fail, major): room 's-dining': 43% of its perimeter enclosed by walls/buildings/screens/planting >= 1.8 m (required >= 50%)
- landscape-architect A-ROOMS (warn, minor): 5 outdoor rooms with uses/surfaces ["('dining', 'paving')", "('lounge', 'paving')", "('quiet', 'paving')"]; a change of floor marks a room
- horticulturist H-SIZE-VS-SPACE (fail, major): lagerstroemia_indica: mature spread 4.0 m in a space 4.7 m across (limit 0.8 x = 3.8 m)
- horticulturist H-SIZE-VS-SPACE (fail, major): olea_europaea: mature spread 3.6 m in a space 1.4 m across (limit 0.8 x = 1.1 m)
- horticulturist H-BED-CROWDING (warn, minor): bed s-bed-wall-b: mature crowns 3.0 m2 on 1.1 m2 of bed (limit 1.5 x)
- horticulturist H-BED-CROWDING (warn, minor): bed n-screen: mature crowns 4.7 m2 on 2.7 m2 of bed (limit 1.5 x)
- user U-GATHER-GROUPS (fail, major): gathering 10-20: dining seats 8 (>= 4), lounge seats 2 (>= 3): a dining group and a lounge group
- user U-FIRE (fail, major): fire pit: 3 seats 1.5-4.0 m from the fire (required >= 4; 1.5 m is LS-FIRE-SEAT); reachable: True
- climate C-POND-SUN (fail, major): pond cell gets 1.75 h direct sun on 21 Jun (required >= 2.0 h, policy: deep shade drops the planting and the water goes green); LS-POND-SHADE covers the opposite excess

Reading them: C-PRIVACY (6 of 15 seats) is the screen opening again (the critic cuts sight lines with the two stubs only); A-ENCLOSURE on the dining room (37 %: the west side is the opening) and the two quiet rooms (the critic counts a room's perimeter against walls, buildings, screens and planting of 1.8 m; the quiet benches are backed by a 4 m fence the critic did not credit, as in pass 2) and A-FOCAL (focal elements counted: pit, two ponds, trees) are conventions of the uncalibrated architect critic; C-POND-SUN reads the first pond (north court, 1.69 h) only: the east pond gets 4.45 h.

## Planting schedule (drawable versus stand-in)

| zone | bed | species | count | layer | verdict | status | conditions |
|---|---|---|---|---|---|---|---|
| east yard | e-edge | Acorus gramineus Aiton | 9 | ground | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | heat: moderate tolerance; plant in afternoon shade or verify locally |
| east yard | e-divider | Farfugium japonicum (L.) Kitam. | 3 | shrub/perennial | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | heat: moderate tolerance; plant in afternoon shade or verify locally; alkaline-soil tolerance is a GAP (site soil unmeas |
| east yard | e-far | Farfugium japonicum (L.) Kitam. | 3 | shrub/perennial | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | heat: moderate tolerance; plant in afternoon shade or verify locally; alkaline-soil tolerance is a GAP (site soil unmeas |
| east yard | e-divider | Fatsia japonica (Thunb.) Decne. & Planch. | 1 | shrub/perennial | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | heat: moderate tolerance; plant in afternoon shade or verify locally |
| east yard | e-far | Fatsia japonica (Thunb.) Decne. & Planch. | 1 | shrub/perennial | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | heat: moderate tolerance; plant in afternoon shade or verify locally |
| east yard | e-divider | Phoenix roebelenii O'Brien | 1 | shrub/perennial | viable_with_conditions | DRAWABLE: graded A asset skf3_a05b5ef5 | alkaline soil: intolerant; conditional on soil test (a professional item; site pH not tested) |
| east yard | e-far | Phoenix roebelenii O'Brien | 1 | shrub/perennial | viable_with_conditions | DRAWABLE: graded A asset skf3_a05b5ef5 | alkaline soil: intolerant; conditional on soil test (a professional item; site pH not tested) |
| north court | n-screen | Jasminum sambac (L.) Aiton | 3 | climber | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | frost: hardy only to 1 C; typical-year minimum is 5.1 C, floor policy 0.0 C; heat: moderate tolerance; plant in afternoo |
| north court | n-edge-far | Acorus gramineus Aiton | 6 | ground | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | heat: moderate tolerance; plant in afternoon shade or verify locally; sun conditional at 1.7 h (21 Jun) |
| north court | n-edge-back | Acorus gramineus Aiton | 5 | ground | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | heat: moderate tolerance; plant in afternoon shade or verify locally; sun conditional at 1.6 h (21 Jun) |
| north court | n-screen | Aspidistra elatior Blume | 3 | shrub/perennial | viable_with_conditions | STAND-IN (generic mass, labelled): graded asset file missing on this machine | heat: moderate tolerance; plant in afternoon shade or verify locally |
| north court | n-screen | Farfugium japonicum (L.) Kitam. | 2 | shrub/perennial | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | heat: moderate tolerance; plant in afternoon shade or verify locally; alkaline-soil tolerance is a GAP (site soil unmeas |
| north court | n-screen | Fatsia japonica (Thunb.) Decne. & Planch. | 1 | shrub/perennial | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | heat: moderate tolerance; plant in afternoon shade or verify locally; sun conditional at 1.7 h (21 Jun) |
| north court | n-screen | Rhapis excelsa (Thunb.) A.Henry | 1 | shrub/perennial | viable_with_conditions | DRAWABLE: graded B asset skf3_86982789 | heat: moderate tolerance; plant in afternoon shade or verify locally |
| other | - | Olea europaea L. | 1 | canopy/understorey (tree) | viable | STAND-IN (generic mass, labelled): not drawable yet | canopy checked at the sourced minimum spread 2.6 m (LDL range 4.6-7.6 m): keep pruned |
| south | - | Lagerstroemia indica L. | 1 | canopy/understorey (tree) | viable | DRAWABLE: graded B asset skf3_a9cb68fd | canopy checked at the sourced minimum spread 4.0 m (LDL range 1.8-9.1 m): keep pruned |
| south | - | Olea europaea L. | 1 | canopy/understorey (tree) | viable | STAND-IN (generic mass, labelled): not drawable yet | canopy checked at the sourced minimum spread 3.6 m (LDL range 4.6-7.6 m): keep pruned |
| south | - | Punica granatum L. | 1 | canopy/understorey (tree) | viable | DRAWABLE: graded B asset skf3_86de7dea; skf3_f697f7da | canopy checked at the sourced minimum spread 2.4 m (LDL range 2.4-3.0 m): keep pruned |
| south | s-bed-mass | Jasminum sambac (L.) Aiton | 2 | climber | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | frost: hardy only to 1 C; typical-year minimum is 5.1 C, floor policy 0.0 C; heat: moderate tolerance; plant in afternoo |
| south | s-bed-mass-corner | Jasminum sambac (L.) Aiton | 2 | climber | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | frost: hardy only to 1 C; typical-year minimum is 5.1 C, floor policy 0.0 C; heat: moderate tolerance; plant in afternoo |
| south | s-bed-screen-s | Jasminum sambac (L.) Aiton | 2 | climber | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | frost: hardy only to 1 C; typical-year minimum is 5.1 C, floor policy 0.0 C; heat: moderate tolerance; plant in afternoo |
| south | s-bed-wall-c | Jasminum sambac (L.) Aiton | 2 | climber | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | frost: hardy only to 1 C; typical-year minimum is 5.1 C, floor policy 0.0 C; heat: moderate tolerance; plant in afternoo |
| south | s-bed-mass-corner | Petrea volubilis L. | 1 | climber | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | frost: hardy only to 1.7 C; typical-year minimum is 5.1 C, floor policy 0.0 C; heat tolerance is a GAP; alkaline-soil to |
| south | s-bed-wall | Petrea volubilis L. | 2 | climber | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | frost: hardy only to 1.7 C; typical-year minimum is 5.1 C, floor policy 0.0 C; heat tolerance is a GAP; alkaline-soil to |
| south | s-bed-wall-c | Petrea volubilis L. | 3 | climber | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | frost: hardy only to 1.7 C; typical-year minimum is 5.1 C, floor policy 0.0 C; heat tolerance is a GAP; alkaline-soil to |
| south | pot | Plumeria rubra L. (terracotta pot) | 1 | container tree | viable | STAND-IN (frangipani asset exists as a genus fit; pot size is a LDL GAP) | frost: hardy only to 1.7 C; typical-year minimum is 5.1 C, floor policy 0.0 C; frost: accepted by lead decision (client  |
| south | s-bed-herb | Origanum majorana L. | 2 | ground | viable | STAND-IN (generic mass, labelled): graded asset file missing on this machine | sun conditional at 5.1 h (21 Jun) |
| south | s-bed-mass | Aspidistra elatior Blume | 4 | shrub/perennial | viable_with_conditions | STAND-IN (generic mass, labelled): graded asset file missing on this machine | heat: moderate tolerance; plant in afternoon shade or verify locally |
| south | s-bed-screen-n | Aspidistra elatior Blume | 2 | shrub/perennial | viable_with_conditions | STAND-IN (generic mass, labelled): graded asset file missing on this machine | heat: moderate tolerance; plant in afternoon shade or verify locally |
| south | s-bed-screen-s | Aspidistra elatior Blume | 3 | shrub/perennial | viable_with_conditions | STAND-IN (generic mass, labelled): graded asset file missing on this machine | heat: moderate tolerance; plant in afternoon shade or verify locally |
| south | s-bed-wall | Aspidistra elatior Blume | 4 | shrub/perennial | viable_with_conditions | STAND-IN (generic mass, labelled): graded asset file missing on this machine | heat: moderate tolerance; plant in afternoon shade or verify locally |
| south | s-bed-wall-b | Aspidistra elatior Blume | 3 | shrub/perennial | viable_with_conditions | STAND-IN (generic mass, labelled): graded asset file missing on this machine | heat: moderate tolerance; plant in afternoon shade or verify locally |
| south | s-bed-pocket | Aspidistra elatior Blume | 2 | shrub/perennial | viable_with_conditions | STAND-IN (generic mass, labelled): graded asset file missing on this machine | heat: moderate tolerance; plant in afternoon shade or verify locally |
| south | s-bed-mass | Justicia brandegeeana Wassh. & L.B.Sm. | 3 | shrub/perennial | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | frost tolerance is a GAP; heat: moderate tolerance; plant in afternoon shade or verify locally; sun conditional at 1.6 h |
| south | s-bed-screen-s | Justicia brandegeeana Wassh. & L.B.Sm. | 2 | shrub/perennial | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | frost tolerance is a GAP; heat: moderate tolerance; plant in afternoon shade or verify locally |
| south | s-bed-wall-b | Justicia brandegeeana Wassh. & L.B.Sm. | 1 | shrub/perennial | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | frost tolerance is a GAP; heat: moderate tolerance; plant in afternoon shade or verify locally |
| south | s-bed-mass | Cenchrus alopecuroides (L.) Thunb. | 3 | shrub/perennial | viable | STAND-IN (generic mass, labelled): graded asset file missing on this machine | sun conditional at 1.6 h (21 Jun) |
| south | s-bed-mass | Phoenix roebelenii O'Brien | 2 | shrub/perennial | viable_with_conditions | DRAWABLE: graded A asset skf3_a05b5ef5 | alkaline soil: intolerant; conditional on soil test (a professional item; site pH not tested); sun conditional at 1.6 h  |
| south | s-bed-wall-b | Rhapis excelsa (Thunb.) A.Henry | 1 | shrub/perennial | viable_with_conditions | DRAWABLE: graded B asset skf3_86982789 | heat: moderate tolerance; plant in afternoon shade or verify locally |
| south | s-bed-mass | Salvia leucantha Cav. | 1 | shrub/perennial | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | heat: moderate tolerance; plant in afternoon shade or verify locally; sun conditional at 1.6 h (21 Jun) |
| south | s-bed-screen-n | Salvia leucantha Cav. | 2 | shrub/perennial | viable_with_conditions | STAND-IN (generic mass, labelled): not drawable yet | heat: moderate tolerance; plant in afternoon shade or verify locally |
| south | s-bed-screen-n | Vitis vinifera L. | 2 | shrub/perennial | viable | STAND-IN (generic mass, labelled): not drawable yet | sun conditional at 4.5 h (21 Jun) |

Drawable on this machine means a graded A/B glTF file is present; the Fab/Megascans species graded by LDL are not present here as files ("graded asset file missing on this machine"), so only the species counted below draw as plants. Everything else is a labelled generic stand-in.

Plants drawable versus stand-in, before -> after: drawable 8 -> 9, stand-in 57 -> 87; species drawable 4 of 13 -> 5 of 17.
The olives are stand-ins (grade C asset); the crape myrtle draws when its glTF is present.

## Images (looked at)

Images of round 3 (shade trees; looked at 2026-11-22, described as seen; plans are CPU drawings, massing views are clay Cycles renders through jobq, trees drawn as translucent green ellipsoids at the PRUNED crown size, not as models).

- `plans/final-south.png` (plan, client north up, house top left): the south garden and the east yard. The west line is at the left with the flush pit (orange disc) between two short screen stubs; each stub has a small planted bed against it (grape and salvia at the top, jasmine, justicia and aspidistra at the bottom). Right of the pit are the BBQ square and the table (white rectangle) with its chairs, now under a large pale-green circle (the crape myrtle's 4.0 m head, trunk dot to its right). A second, darker circle at lower right is the olive over the rear and quiet benches, overlapping a third (pomegranate) at the garden's east end. Paving is only the west third; the floor under the crowns is cream gravel. A thin planted strip with climbers runs along the south wall, a mass of palms, jasmine and perennials fills the south-east corner. At the top right the east yard shows the blue pond, a bench, and a fourth round crown (the small olive) over the bench; gravel under it. The plan reads as a planted garden, not a paved terrace; the labels at the right are dense. The plan key calls the crape 'understorey' (its LDL form is shrub): a labelling quirk of the plan style, not a design fact.
- `plans/final-north.png`: the north court. Pond (blue, grille dashed) in the middle, a ring of acorus on the east and north edges, fatsia, palms and aspidistra massed behind it, a bench outline (white rectangle) at the west edge. No tree: the lower third of the court is plain paving and a path patch, the dullest part of the design. The rhapis crown drawn at 1.8 m spread is the largest plant.
- `plans/final-massing-south.png` (clay massing, oblique from the south-east): the two big crowns, crape and olive, merge into one green mass over the table and rear benches and hide them; the pomegranate sphere sits behind them at the east. West of them the fire pit area is paved and open, the two screen stubs are thin glass-like slabs with small beds. The massing therefore shows the canopy but not the furniture below it (use the plan for that).
- `plans/final-massing-east.png` (azimuth 90): the east yard seen along the house wall: the pond (blue) with its acorus edge, the bench box beside it and the olive crown, a dense shrub clump in the yard's corner. The crape/olive masses of the south garden fill the left edge of the frame.
- `plans/final-massing-north.png` (azimuth 250, high): the north court looks like a small pit between tall blocks; the pond, an L of small acorus spheres and one bulky clump of palms/rhapis are visible, the bench box at the bottom. Dark and low-contrast, as before.
- `plans/final-visualisation-plan.png` and `plans/final-visualisation-massing.png`: the south garden mirrored onto the sister plot (left half, tinted red), each with a red band 'VISUALISATION ONLY' above and below and a labelled zone. The mirror repeats the crowns, so the sister side reads as a second identical grove; it is not our land, not checked, not scheduled. The plan's label leaders are the worst clutter of all the images (long crossing lines at the left and the right).

