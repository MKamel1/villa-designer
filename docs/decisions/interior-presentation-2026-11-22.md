# Interior presentation decisions (client, 2026-11-22)

- **Windows by day: option (b).** In day views where the design has curtains or sheers, show the sheers half-drawn (their real design position and modelled fabric, never a fake overlay). Where there are no curtains, the window stays as the camera sees it (bright). No exposure blending.
- **Finishes and styling: RESUME product selection (L4) for finishes and styling ONLY**, still with NO pricing. The lead brings 2–3 finish palettes for the client to pick from: floor stone, worktops, timber, kitchen backsplash, wall paint, plus soft furnishings (cushions, throws), open-shelf contents and wardrobe garments. Each item is a real buyable product, with render look-alikes labelled as such.
- **Lead decisions (technical):** the ramp store (v30) gets its own exposure group under a pre-registered rule. The GF hall (n10) blue cast is resolved by a view-state rule (door and daylight state) for that view.

## Client palette choice (2026-11-23): a mix
- **Kitchen: palette B.**
  - Worktop and backsplash: Cosentino Dekton Nacre.
  - Kitchen fronts: FENIX 0719 Beige Luxor.
  - Kitchen joinery: EGGER Natural Halifax Oak.
- **Basement open plan (north–south living): palette C, the marble look.**
  - Floor: Marazzi Gris Fleury Taupe RT 60x120.
  - Living soft furnishings (cushions, throws, rug): C.
- **Parents' bedroom: palette C.**
  - Floor: Havwoods Cantal Smoked Cocoa oak.
  - Joinery: EGGER Brown Halifax Oak.
  - Cushions, throw and rug: C.
- **Lead proposals, CONFIRMED by the client 2026-11-23:**
  - **Walls:**
    - Basement open plan: B's Dulux Off White (LRV 89). The kitchen and living share the space, and C's Nile Clay (LRV 27) would darken the lower-ground level.
    - Parents' bedroom: Nile Clay as a feature wall behind the bed only.
  - **Rest of the house follows C:**
    - GF floors: Smoked Cocoa oak, for continuity with the bedroom.
    - Doors: Durian Smoke Oak.
    - Wet rooms: Marazzi Limestone20 Taupe floor and Grande Marble Look Frappuccino wall.
    - Other soft furnishings: C.

## Applied to the production scene (L4, 2026-11-23)

The chosen mix is scheduled in `knowledge/products/finishes/chosen.json` and drawn in the production scene; decisions the lead took on the way, the renders, the critic and the open items are in `docs/lanes/L4-finishes.md` ("Round 2"). Needing a client yes: GF walls other than the parents' feature wall are B Off White; the en-suite and bathrooms read dark copper-brown; the rug sizes keep the design footprints.

## Client decisions (2026-11-24), after reviewing their own style references (docs/brief/villa_01_guidelines_images, taste.json)
1. **Kitchen, toward reference image 23:**
   - walnut fronts (EGGER Dijon Walnut, palette A);
   - a WHITE marble-look worktop and WATERFALL island with gold-brown veining (a real Calacatta Gold-look porcelain or quartz product), with a matching backsplash.
   - This replaces palette B's kitchen.
2. **Ensuite, toward reference image 12:**
   - keep the dark Frappuccino marble walls;
   - ADD a light veined-marble feature panel behind the bath with an LED cove;
   - a light veined marble-look floor;
   - brass taps and fittings.
3. **Lead decisions applied (the client was told and did not object):**
   - tree uplights: John Cullen Kew 25 spike, pending the maker confirming DALI-2 and supplying the 2027 article's photometry;
   - ground-floor walls: Off White.

### Applied (lane L4 round 5, 2026-11-24)
Kitchen and ensuite decisions 1 and 2 are applied in `chosen.json` and the scene; products, model changes, cove verification and the honest likeness to the references are in `docs/lanes/L4-finishes.md` ("Round 5"). Decision 3's tree uplights belong to lane LG.

## 2026-11-25: parents' bedroom headboard wall with hidden nightstands (client approved)
- **Removed:** both floor-standing nightstands. The east one stood 17 mm from the dressing-door opening, and its books blocked the way at 6:21 of the v3 walkthrough.
- **Replaced by:** one full-width headboard wall across the bed and both sides. It carries:
  - a matched pair of flush ledges at mattress height with push-to-open drawers, no handles;
  - the existing 2700 K headboard cove along the top;
  - the existing swing-arm reading lights.
- **Where the depth comes from:**
  - The east side borrows depth from the end of the wardrobe behind it (furn-pd-hang-1).
  - The west side, with the entry behind it, gets its depth from building the wall out about 150–200 mm into the bedroom.
- **Accepted trade-off:** the bed moves about 150–200 mm toward the window, and the foot clearance falls from about 0.8 m toward 0.6 m.
- **Condition:** if the measured foot clearance or any passage falls below its sourced minimum, the lane reports back rather than applying.
- **Reason:** a clean, minimal look and more room to move on both sides of the bed.
