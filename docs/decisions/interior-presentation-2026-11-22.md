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
- **2026-11-25 refinement (client):** option (a). Both drawers take their depth from the built-out headboard wall only (about 150–200 mm), identical on both sides. The dressing-room wardrobe (furn-pd-hang-1) stays UNTOUCHED and loses no hanging length.
- **2026-11-25 revision (client, after measurement):** the built-out wall left 0.60–0.65 m at the bed foot, where 0.75 m is required (UK AD M 2.25a, card ukadm-bedroom-route-750) on the only route from the entry to the dressing room. It is replaced by a SLIM bed-mounted headboard panel (about 50 mm) carrying:
  - a matched pair of floating side ledges with slim push-to-open drawers (about 80 mm);
  - the cove and the reading lights.
  Both bedside tables are still removed, and the wardrobe is untouched. The bed moves at most 50 mm, and the foot route must stay ≥ 0.75 m.
- **Lead decision (staging):** park the curtain stacks clear of the bed-foot corners, and shorten the duvet's foot drop so the cloth does not narrow that route (DF measured 0.45 m with cloth as obstacles).
- **2026-11-26 revision (client): pull-out trays replace the floating ledges.** The ledges (furn-pb-ledge-w and -e, 280 × 300 mm, top at 0.525 m) sat beside doorways:
  - the west ledge projected 0.30 m where you step in from the entry lobby, narrowing the 1.05 m opening to about 0.77 m;
  - the east ledge stood 0.09 m from the dressing door frame.

  The client: "night stand blocking the room door". Decision: remove both ledges. The parents' bed becomes a custom joinery bed with:
  - a slim walnut-and-fabric headboard of our own design (replacing the imported grey headboard, so frame, headboard and cove read as one piece);
  - a hidden tray-drawer in each side rail at mattress height that slides out when used and sits flush when closed.

  Nothing may project at the entry or the dressing door. The bed position and the 0.75 m foot route are unchanged.
- **2026-11-26 applied (lane DF round 4):** both ledges removed; the imported bed is retired and replaced by a custom joinery queen bed (mattress 1600 x 2000, bed unmoved; 50 mm walnut-and-upholstery headboard; a push-to-open tray in each side rail, Blum MOVENTO 760H NL 270 with TIP-ON as the runner basis). Closed: nothing beyond the bed footprint. Trays out 0.25 m: route entry -> dressing door 0.766 m (0.75 required), west passage 0.803 m, dressing approach 1.000 m. One honest shortfall: the tray rim is the deck, 0.19 m below the mattress top, because the runner lives under the mattress. Detail and measurements: `docs/lanes/DF.md` round 4.
