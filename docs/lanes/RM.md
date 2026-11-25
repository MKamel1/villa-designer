# RM: reference-match proposals (living, media, parents' bedroom, dining)

The client asked whether the interior is being brought close to the photos they supplied. This lane read all
24 reference images that belong to these rooms (plus the cross-room ones that show a room's features), rendered each room as it is,
listed what the references share that the room lacks, and mocked the top gaps up on a COPY of the render-set scene.
Kitchen and ensuite are lane L4's and were not touched. The production scene and design model were not changed.

Data: `knowledge/refmatch/<room>/{gaps,proposals}.json`. Images: `cur_*.jpg` (the room today), `mock_*.jpg` (with the
proposals), `compare_*.jpg` (the two side by side). **No reference image is committed** (hash-checked by
`tests/refmatch`, 9 tests). For the client meeting, `python scripts/refmatch_sheet.py out/RM/cur out/RM/mockfinal`
writes `out/RM/sheets/<room>.jpg` locally: current | mock-up | the three closest references (not committed; it holds the client's images).

Read this first: **the mock-ups are draft look-alike renders (1280 x 853, 48 spp, 24 mm).** Stone is a CC0 marble texture colour-matched to
the maker's swatch, so it reads lighter and more contrasty than the real product. Glow is drawn with emissive strips; the real
lighting level is for the lighting lanes. The proposals are not a lighting design and not a finished specification.

## Living (lounge TV wall and garden living) :: `knowledge/refmatch/living/`

References used: 16, 17, 19, 21, 22, 36, 37 (the room's seven), plus 32 and 33 (media) for the stone-and-backlit-shelf TV wall.
What the references share that the rooms lack: **(1)** a full-height veined stone feature wall behind the TV or seating, flanked by timber
(21, 36, 22, 37, 32, 33); the lounge has walnut flutes only and the garden-living alcove (2.0 m wide) is a bare painted panel;
**(2)** light as a feature: halo, glow under the console, grazing wash (19, 22, 36, 37, 32, 33); the coves are designed but nothing lights the TV wall;
**(3)** glass or opal globes (19, 36); none in either room.

| proposal | where (design model) | product |
|---|---|---|
| L-P1 stone panel, 2.40 m wide, floor to ceiling, flutes kept either side | lounge north wall, x 4.80-7.20, z -3.0..-0.3 | Marazzi Grande Marble Look **Tafu Lux RT** 120 x 278 cm, code MEP6 |
| L-P2 same stone in the library alcove | x 18.70-20.64, z -2.45..-0.95 | same |
| L-P3 lighting ask: halo, toe glow, wash; alcove edge glow | as listed in `proposals.json` | lighting lanes |
| L-P4 clear-glass globe cluster over the coffee table | (20.55, -26.0), 0.9-1.5 m below ceiling | Bocci **28 Series**, Clear (cluster) |

Mock-up: `mock_v03-street-lounge.jpg`, `mock_v02-garden-living.jpg` (current: `cur_*`).
How close: the lounge now has the *structure* of references 36 and 21 (stone behind the TV, walnut either side, a floating console with a floor glow) and the
alcove reads as the stone-and-walnut pairing of 36. It falls short in four ways: the stone renders whiter and greyer than the taupe Tafu swatch; the TV
halo is drawn brighter than a designed halo should be; there is no walnut shelving with shelf LED (36, 22) because the lounge has no wall for it; the sofa, coffee table and cushions are unchanged. Honest estimate: about two-thirds of the way to 36 on the TV wall, far from 19 and 22.
Lead to approve: L-P3 needs a 25 mm reveal at the panel edge and a ceiling-line slot.

## Media (cinema) :: `knowledge/refmatch/media/`

References used: 18, 20, 32, 33, 34, 35 (all six media images). Shared: **(1)** marble or dark stone panel behind the screen (18, 32, 33, 34, 35); **(2)** glow on the wall: halo, toe glow, wash (18, 32, 34, 35);
**(3)** a floating console (18, 20, 32, 34, 35); **(4)** timber slats beside the stone (18, 32, 34); **(5)** backlit shelves either side (32-35). The cinema has taupe acoustic fabric walls and a bare screen, no console.

| proposal | where | product |
|---|---|---|
| M-P1 dark marble panel 2.25 x 1.8 m behind the screen | east wall x 9.18, y -22.90..-20.65, z -2.9..-1.1 | Marazzi Grande Marble Look **Frappuccino Lux** 120 x 120 cm, M0G3 (the client's chosen wet-room stone) |
| M-P2 walnut slat flank, 0.60 m | y -23.55..-22.95 | WoodUpp **Akupanel Natural Wood, Walnut, Black Felt**, 240 x 60 cm |
| M-P3 floating console, 2.33 m | x 8.74-9.18, z -2.8..-2.45 | EGGER **H3180 ST37 Brown Halifax Oak** (chosen joinery) |
| M-P4 lighting ask: halo, toe glow, wash | as listed | lighting lanes |
| M-P5 lighting ask: backlit shelf niches (NOT modelled) | needs about 0.25 m of wall depth in a 3.04 m wide room | lead to approve (changes room width) |

Mock-up: `mock_v08-cinema.jpg`. How close: **least close of the four.** It gets the panel, console, flute flank and halo, but not the backlit shelves, which are half of references 32-35. The stone
reads rose-bronze, not the dark Emperador of 35, and the halo is hot. The 4 m2 of acoustic fabric behind the panel is lost: the lead should confirm with the cinema's acoustic intent (the walnut slats and the existing fabric elsewhere partly compensate).

## Parents' bedroom :: `knowledge/refmatch/bedroom/`

References used: 5, 6, 7 (the room's three). Shared: **(1)** dark walnut slat tone (6, 7); **(2)** a slat wall full height and wider than the bed (5, 6, 7);
**(3)** a glow washing the slats (5, 6, 7); **(4)** under-bed glow (7). Present already: the slat wall itself (x 19.54-21.12, to 2.10 m) and opal wall-read globes (as 5).
**Finding for the lead, outside the proposals:** the scene renders the slats in *Natural* Halifax (light oak), but the client chose *Brown* Halifax for this room's joinery (decision 2026-11-23).
Proposal B-P1 is therefore partly a correction: slats in the chosen EGGER H3180 ST37, extended to the ceiling and 2.7 m wide. B-P2/B-P3 are lighting asks (ceiling-line wash; under-bed glow); B-P4 (Flos IC Lights S1 pendants) is an optional swap not drawn.
Not proposed: bouclé bed (no verified maker product), glass-door wardrobes (they live in the dressing room), floor-to-ceiling glazing (architecture).

Mock-up: `mock_n13-parents-day.jpg`, `mock_v05-parents-bedroom.jpg`. How close: **closest of the four** to its references: reads as 6 and 7 (dark slats to the ceiling with a wash). Gaps left: the grey channel-stitched headboard is not the bouclé platform bed of 7; the wash shows as a hot patch at the ceiling line; under-bed glow is out of frame; the Nile Clay feature wall (the client's own choice) replaces the stone panels of 6. The dusk mock (v05) is brighter than the production dusk view because the evening exposure group is re-metered on the new geometry.

## Dining :: `knowledge/refmatch/dining/`

References used: 28, 29, 30, 31 (the room's four). Shared: **(1)** a pendant cluster of glass or opal globes over the table (all four); the scene has one black linear bar;
**(2)** a stone or concrete-look feature wall behind the sideboard (28, 29, 30); the wall is plain Off White; **(3)** a cove or wash on that wall (28, 29, 30); **(4)** up/down sconces (28, 29);
**(5)** upholstered curved-back chairs with cognac or rust seats (all four) vs walnut slat-back chairs with bouclé seats (not proposed: no verified maker chair).

| proposal | where | product |
|---|---|---|
| D-P1 staggered globe cluster replaces the linear pendant | over the table (16.95, -25.9) | Bocci **28 Series**, Clear |
| D-P2 stone continued up the party-side wall, 1.9 m wide | y -28.47, x 15.50-17.40, z -3.0..-0.3 | Marazzi Mystone **Gris Fleury Taupe RT** 60 x 120 (the chosen floor) |
| D-P3 lighting ask: ceiling-line wash and two up/down sconces | as listed | lighting lanes |

Mock-up: `mock_n01-dining-day.jpg`, `mock_n20-dining-side-day.jpg`. How close: the globe cluster and stone wall bring it to references 29 and 30 in composition; the chairs, table and art are unchanged, so it is not yet 28 or 29 (rust seats, art, rug).
The linear pendant carries the L6 table task light (the L6 dining plane must be re-verified if it is replaced).

## Decisions taken without a human (all reversible)

1. The reference images were not at the stated path (`docs/brief/villa_01_guidelines_images` is absent in this clone); read from `/home/omar/archpipe/lead/docs/brief/villa_01_guidelines_images`. I viewed every image listed above myself and wrote the features down; `taste.json` was used for room pairing and cross-checked against what I saw.
2. "Living" covers the garden living **and** the street lounge/family TV wall (the only TV wall in a living space); "media" is the cinema.
3. Product choices are limited to makers whose own pages I read on 2026-11-24 (Marazzi, WoodUpp, Bocci, Flos, EGGER). Quotes are in `proposals.json` and no price is recorded (the pages show prices; they are deliberately not copied). Colour comes from the maker's swatch image or product name. WoodUpp's slat width and pitch are not on the page text, so the mock-up's 40 mm slats at 60 mm and 24 mm at 45 mm are assumptions, not maker data. Bocci's cluster is sold as 19 pendants (28.19) and via a configurator; the mock-up's five globes need confirming with Bocci.
4. Exposure: the frozen exposure-group record is bound to production geometry, so the mock-up keeps the production view-to-group assignment and re-binds only the transport hash (`scripts/refmatch_build.py`); the EV of each group is re-metered at render time. The "current" renders are the unedited production render-set scene, so the pair is comparable but the mock-ups are not exposure-identical to production.
5. Mock-ups added geometry to a copy of `out/RM/base/scene.json` built with `render_set.write_scene` from this tree; nothing under `src/archpipe/` other than the new `refmatch` package changed.
6. Render jobs: several attempts failed or waited (GPU shared with the walkthrough and L4 lanes; two attempts hit `System is out of GPU memory` when my own two jobs ran together). Final jobs: `RM-cur-6` (current), `RM-mock-7` and `RM-mock-8` (mock-ups), one at a time.
7. Not proposed, by design: anything in the kitchen and ensuite (L4), furniture with no verified maker product (bed, dining chairs), glazing (architecture).

## Needs the lead

Approve or reject: the 25 mm reveals and ceiling slots (L-P3, M-P4, D-P3); the cinema's width and acoustic-fabric trade-offs (M-P1, M-P5); the bedroom slat finish correction (B-P1, which contradicts what the production scene shows against the client's 2026-11-23 choice).
