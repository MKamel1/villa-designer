"""Write knowledge/refmatch/<room>/{gaps,proposals}.json. The data is authored here, from looking at the
references (taste.json plus my own reading of each image) and at the current renders; see docs/lanes/RM.md."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import refmatch_products as P  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "knowledge" / "refmatch"


def w(room, gaps, props):
    d = OUT / room
    d.mkdir(parents=True, exist_ok=True)
    (d / "gaps.json").write_text(json.dumps(gaps, indent=1, ensure_ascii=False) + "\n")
    (d / "proposals.json").write_text(json.dumps(props, indent=1, ensure_ascii=False) + "\n")


def living():
    refs = [
        {"id": "image16", "why": "walnut plank TV wall, tray ceiling, walnut credenza"},
        {"id": "image17", "why": "reclaimed plank wall with grazing downlights"},
        {"id": "image19", "why": "backlit console niche, perimeter cove, clear-glass globe cluster, dark slat strip beside glazing"},
        {"id": "image21", "why": "large-format beige-grey marble wall panels with grazing downlights, polished marble floor"},
        {"id": "image22", "why": "grey stone-look panels, walnut shelving with shelf LED, cove above"},
        {"id": "image36", "why": "beige stone wall behind TV, walnut shelving with shelf LED, opal globe lamps"},
        {"id": "image37", "why": "stacked slate wall, cove, linear floor strip"},
        {"id": "image32", "why": "cross-room (media): book-matched beige marble TV wall, backlit shelves, fluted walnut"},
        {"id": "image33", "why": "cross-room (media): grey marble TV wall flanked by backlit shelves"},
    ]
    gaps = [
        {"id": "L-G1", "rank": 1, "feature": "Full-height stone feature wall behind the TV / seating (large-format, veined, taupe-beige-grey), flanked by timber",
         "refs_showing_it": ["image21", "image36", "image22", "image37", "image32", "image33"],
         "present_in_scene": "no: lounge TV wall is walnut flutes only; the garden-living library alcove (2.0 m wide, z -2.45..-0.95) is a bare painted panel inside a walnut frame",
         "visual_weight": "high (largest single surface in each reference)"},
        {"id": "L-G2", "rank": 2, "feature": "Light used as a feature: lit halo or reveal around the TV panel, glow under the floating console, grazing wash down the stone",
         "refs_showing_it": ["image19", "image36", "image22", "image37", "image32", "image33"],
         "present_in_scene": "partly: ceiling coves COVE-lounge-05/06 and COVE-living-01/02 are designed (L6), but nothing lights the TV wall, console or alcove",
         "visual_weight": "high (sets the warm 2700 K evening mood in 6 of 9 references)"},
        {"id": "L-G3", "rank": 3, "feature": "Clear- or opal-glass globe luminaires (cluster over the coffee table, floor/shelf globes)",
         "refs_showing_it": ["image19", "image36"],
         "present_in_scene": "no decorative luminaire in either living space; only recessed downlights and coves",
         "visual_weight": "medium"},
        {"id": "L-G4", "rank": 4, "feature": "Dark, low, round or chamfered coffee table and cognac/rust accent cushions",
         "refs_showing_it": ["image19", "image21", "image22", "image17"],
         "present_in_scene": "partly: cushions follow the chosen palette C (dark brown, dark green, light brown); coffee tables are walnut rectangles",
         "visual_weight": "low; not proposed (cushions are the client's own palette C choice)"},
    ]
    props = [
        {"id": "L-P1", "gap": "L-G1", "title": "Book-matched Tafu stone panel on the lounge TV wall, walnut flutes kept either side",
         "location": {"room": "lounge", "wall_or_zone": "north wall behind the TV (y = -23.65)", "rect_m": [4.80, 7.20], "z_range_m": [-3.0, -0.3],
                      "basis": "design model: detail-tv-fluting spans x 4.40-7.56; TV screen x 5.17-6.83; slab 120 x 278 cm vs 2.70 m storey height, two slabs = 2.40 m wide"},
         "change": "Replace the central 2.40 m of the walnut fluted wall with two 120 x 278 cm Tafu Lux slabs; keep 0.40 m of fluting each side (the ceiling and floor lines do not move).",
         "effect": "Brings the stone-behind-TV of references 36, 21 and 33 into the room while keeping the walnut the client already has.",
         "product": P.STONE_TAFU, "architecture_change": {"flag": False, "note": "applied finish only; 6.5 mm porcelain on the existing wall"}},
        {"id": "L-P2", "gap": "L-G1", "title": "Tafu stone panel in the garden-living library alcove",
         "location": {"room": "living", "wall_or_zone": "back wall of the walnut-framed alcove (y = -29.72)", "rect_m": [18.70, 20.64], "z_range_m": [-2.45, -0.95],
                      "basis": "design model: furn-library-daybed-0 frame x 18.67-20.67, cabinets top at z -0.90"},
         "change": "Line the blank back wall of the alcove with the same stone, 1.94 m x 1.50 m.",
         "effect": "Replaces the blank grey-beige panel (current render) with the stone-plus-walnut pairing of reference 36.",
         "product": P.STONE_TAFU, "architecture_change": {"flag": False, "note": "applied finish only"}},
        {"id": "L-P3", "gap": "L-G2", "title": "Lighting ask: halo, toe glow and stone wash on the lounge TV wall; edge glow and wash in the alcove",
         "location": {"room": "lounge", "wall_or_zone": "TV wall: 25 mm reveal around the screen (x 5.10-6.90, z -2.46..-1.34), under the console (x 5.0-7.0, z -2.92), wash from the ceiling line (z -0.33); alcove: edge strips x 18.70 and 20.64, wash at z -0.97",
                      "basis": "design model: furn-lounge-tv screen x 5.17-6.83, console x 5.0-7.0, floor z -3.0"},
         "lighting_ask": {"effect": "2700 K, dimmable with the ambient layer: (a) a soft halo around the TV panel, no hot spot on the screen; (b) a continuous toe glow under the floating console; (c) a grazing wash down the stone from the ceiling line so the veining reads; (d) 20 mm edge glow either side of the alcove stone with a wash across it. Mock-up used about 250, 120 and 700 lm per metre-run as placeholders only.",
                          "cct_k": 2700, "to_be_designed_by": "lighting lanes (L6 family)", "not_a_finished_design": True},
         "change": "Lighting only; the stone is not translucent porcelain, so the glow is a reveal and wash, not light through the stone.",
         "effect": "The lit-edge look of references 19, 22, 36 and 37.",
         "architecture_change": {"flag": True, "note": "needs a 25 mm reveal at the TV panel edge and a ceiling-line slot; small joinery change, lead to approve"}},
        {"id": "L-P4", "gap": "L-G3", "title": "Clear blown-glass globe cluster over the garden-living coffee table",
         "location": {"room": "living", "wall_or_zone": "ceiling over the coffee table, centre (20.35, -26.0), globes 0.8-1.35 m below the ceiling",
                      "rect_m": [20.0, 20.7], "z_range_m": [-1.5, -0.27], "basis": "design model: furn-living-coffee x 19.8-20.9, y -26.23..-25.77; ceiling z -0.27"},
         "product": P.BOCCI_28,
         "lighting_ask": {"effect": "Five dimmable 2700 K globes at staggered heights, on the ambient circuit; the downlights DL-living-03/04 stay.", "cct_k": 2700,
                          "to_be_designed_by": "lighting lanes (L6 family)", "not_a_finished_design": True},
         "change": "Add a decorative pendant cluster; no structure needed beyond a canopy fixing in the slab.",
         "effect": "The globe cluster of reference 19.", "architecture_change": {"flag": False, "note": "ceiling fixing only"}},
    ]
    return refs, gaps, props


def media():
    refs = [
        {"id": "image18", "why": "dark stacked-stone TV wall between vertical wood slats, cove wash on the stone, floating black console"},
        {"id": "image20", "why": "dark reclaimed-plank TV wall with a floating wood ledge and recessed spots in the soffit"},
        {"id": "image32", "why": "book-matched beige marble, fluted walnut, backlit shelves, floor LED under console"},
        {"id": "image33", "why": "grey marble TV wall flanked by backlit shelves, stone and brass tables"},
        {"id": "image34", "why": "grey marble with gold veins, backlit niches, floor LED, cove (screenshot overlay; not buildable as shown)"},
        {"id": "image35", "why": "dark Emperador-style marble, backlit shelves, halo around the TV, floating black console"},
    ]
    gaps = [
        {"id": "M-G1", "rank": 1, "feature": "Book-matched marble or dark stone panel behind the screen", "refs_showing_it": ["image18", "image32", "image33", "image34", "image35"],
         "present_in_scene": "no: the cinema walls are taupe acoustic fabric (shell-157); the screen sits on it with no panel", "visual_weight": "high"},
        {"id": "M-G2", "rank": 2, "feature": "Light on the wall: halo around the screen, glow under the console, wash down the stone", "refs_showing_it": ["image18", "image32", "image34", "image35"],
         "present_in_scene": "no: cinema lighting is two downlights, three wall-washers on the west wall and a night line", "visual_weight": "high"},
        {"id": "M-G3", "rank": 3, "feature": "Floating console under the screen", "refs_showing_it": ["image18", "image20", "image32", "image34", "image35"],
         "present_in_scene": "no console in the model: screen only", "visual_weight": "medium"},
        {"id": "M-G4", "rank": 4, "feature": "Vertical timber slats or flutes flanking the stone", "refs_showing_it": ["image18", "image32", "image34"],
         "present_in_scene": "no", "visual_weight": "medium"},
        {"id": "M-G5", "rank": 5, "feature": "Backlit shelves or niches either side of the screen", "refs_showing_it": ["image32", "image33", "image34", "image35"],
         "present_in_scene": "no", "visual_weight": "high but needs wall depth; asked of the lighting lanes and flagged as an architecture change, not modelled"},
    ]
    props = [
        {"id": "M-P1", "gap": "M-G1", "title": "Frappuccino marble-look panel behind the screen",
         "location": {"room": "cinema", "wall_or_zone": "east wall behind the screen (x = 9.18)", "rect_m": [-22.90, -20.65], "z_range_m": [-2.9, -1.1],
                      "basis": "design model: furn-cinema-tv screen y -22.69..-20.81, z -2.56..-1.50; cinema ceiling slopes 2.0-2.65 m under the ramp"},
         "change": "A 2.25 m x 1.8 m panel of 120 x 120 cm tiles book-matched in a 2 x 2 grid... (tile grid shown in the mock-up as one surface).",
         "effect": "Dark Emperador-look wall of reference 35 using the stone the client already chose for the wet rooms.",
         "product": P.STONE_FRAPPUCCINO, "architecture_change": {"flag": False, "note": "applied finish over the fabric wall; acoustic fabric behind is lost on this panel (about 4 m2), lead to confirm with the cinema acoustics"}},
        {"id": "M-P2", "gap": "M-G4", "title": "Walnut slat flank on the north side of the screen wall",
         "location": {"room": "cinema", "wall_or_zone": "east wall, north of the stone", "rect_m": [-23.55, -22.95], "z_range_m": [-2.9, -1.1], "basis": "design model: cinema wall y -23.64..-20.60"},
         "change": "0.60 m of walnut slat panel beside the stone (mock-up slat 40 mm at 60 mm centres, assumed).", "effect": "Slat-and-stone pairing of references 18 and 32.",
         "product": P.SLATS_WALNUT, "architecture_change": {"flag": False, "note": "applied finish; the slat panel also absorbs sound"}},
        {"id": "M-P3", "gap": "M-G3", "title": "Floating walnut console under the screen",
         "location": {"room": "cinema", "wall_or_zone": "east wall", "rect_m": [-22.95, -20.62], "z_range_m": [-2.8, -2.45], "basis": "x 8.74-9.18 (0.44 m deep), 0.20 m off the floor"},
         "change": "A 2.33 m long, 0.35 m high wall-hung console in the chosen Brown Halifax Oak.", "effect": "References 18, 32, 35.",
         "product": P.BROWN_HALIFAX, "architecture_change": {"flag": False, "note": "furniture; needs a wall fixing through the fabric"}},
        {"id": "M-P4", "gap": "M-G2", "title": "Lighting ask: screen halo, console toe glow and stone wash",
         "location": {"room": "cinema", "wall_or_zone": "east wall: halo 20 mm around the screen (y -22.76..-20.74, z -2.58..-1.44), toe strip under the console (z -2.82), wash from z -1.12",
                      "basis": "design model coordinates above"},
         "lighting_ask": {"effect": "2700 K, own dimmer, down to near-off for film; halo no brighter than needed to separate the screen from the wall (reference 35); toe glow; grazing wash so the veining reads. Mock-up placeholders 220, 150, 500 lm per run.",
                          "cct_k": 2700, "to_be_designed_by": "lighting lanes (L6 family)", "not_a_finished_design": True},
         "change": "Lighting only.", "effect": "The glow of references 32, 34, 35.", "architecture_change": {"flag": False, "note": "none beyond a reveal in the console and panel"}},
        {"id": "M-P5", "gap": "M-G5", "title": "Lighting ask: backlit shelf niches either side of the screen (not modelled)",
         "location": {"room": "cinema", "wall_or_zone": "either side of the stone panel", "basis": "needs about 0.25 m of wall depth; the north side is only 0.60 m wide and the south side 0.05 m"},
         "lighting_ask": {"effect": "2700 K LED line under each shelf, as references 32-35.", "cct_k": 2700, "to_be_designed_by": "lighting lanes (L6 family)", "not_a_finished_design": True},
         "change": "Not in the mock-up: the room is 3.04 m wide and the screen wall cannot take shelves on both sides without narrowing the room.",
         "effect": "Shelf glow of references 32-35.", "architecture_change": {"flag": True, "note": "changes the room's usable width by about 0.25 m; lead must approve"}},
    ]
    return refs, gaps, props


def bedroom():
    refs = [
        {"id": "image5", "why": "oak vertical slats flanking a plaster niche with 2700 K cove, opal globe pendants over floating nightstands"},
        {"id": "image6", "why": "walnut slats and grey stone panels at the head wall, cove above the headboard, taupe upholstered bed"},
        {"id": "image7", "why": "walnut vertical slats behind a bouclé platform bed, under-bed LED glow, slat-wall uplight, tinted-glass wardrobes"},
    ]
    gaps = [
        {"id": "B-G1", "rank": 1, "feature": "Slat colour: dark walnut tone (refs 6, 7); the scene slats render light oak", "refs_showing_it": ["image6", "image7"],
         "present_in_scene": "the slat wall exists (x 19.54-21.12, z 0-2.1) but uses the light 'oak' material; the client chose EGGER Brown Halifax (dark) for this room's joinery",
         "visual_weight": "high (it is the room's focal surface)"},
        {"id": "B-G2", "rank": 2, "feature": "Slat wall full height and wider than the bed, to the ceiling", "refs_showing_it": ["image5", "image6", "image7"],
         "present_in_scene": "no: it stops at 2.10 m, 1.58 m wide, about the bed width", "visual_weight": "high"},
        {"id": "B-G3", "rank": 3, "feature": "Glow on the head wall: cove or uplight washing the slats", "refs_showing_it": ["image5", "image6", "image7"],
         "present_in_scene": "a cove light COVE-parents-bed-01 exists in the lighting design but nothing in the day or dusk views shows it grazing the slats", "visual_weight": "high"},
        {"id": "B-G4", "rank": 4, "feature": "LED glow under the bed base", "refs_showing_it": ["image7"], "present_in_scene": "no", "visual_weight": "medium"},
        {"id": "B-G5", "rank": 5, "feature": "Bouclé bed, floating nightstands, glass-door wardrobes, floor-to-ceiling glazing", "refs_showing_it": ["image6", "image7"],
         "present_in_scene": "grey channel-upholstered headboard; one window; wardrobes are in the dressing room",
         "visual_weight": "medium; NOT proposed: no verified maker product found for the bed, and glazing changes the architecture"},
    ]
    props = [
        {"id": "B-P1", "gap": "B-G1", "title": "Headboard slat wall in the client's chosen Brown Halifax Oak, to the ceiling and wider than the bed",
         "location": {"room": "parents-bed", "wall_or_zone": "south (head) wall, y = -26.59", "rect_m": [19.10, 21.80], "z_range_m": [0.0, 2.62], "basis": "design model: bed x 19.57-21.09, nightstand to 21.48, wall z 0-2.7; mock-up slat 24 mm at 45 mm centres (assumed)"},
         "change": "Change the slat finish from Natural Halifax to Brown Halifax and extend the panel to 2.70 m wide, 2.62 m high (it now stops at 2.10 m).",
         "effect": "Reads as the walnut slat wall of references 6 and 7, with the Nile Clay feature wall above and beside.",
         "product": P.BROWN_HALIFAX, "architecture_change": {"flag": False, "note": "joinery only"}},
        {"id": "B-P2", "gap": "B-G3", "title": "Lighting ask: wash down the slat wall from a ceiling-line cove",
         "location": {"room": "parents-bed", "wall_or_zone": "head wall at the ceiling line, x 19.10-21.80, z 2.60", "basis": "existing COVE-parents-bed-01 at (20.33, -26.47, 2.73)"},
         "lighting_ask": {"effect": "2700 K, dimmable, grazing the slats from above so each slat catches light (references 6, 7). Mock-up placeholder 600 lm per run.", "cct_k": 2700,
                          "to_be_designed_by": "lighting lanes (L6 family)", "not_a_finished_design": True},
         "change": "Lighting only; check COVE-parents-bed-01 already does this before adding a second run.", "effect": "Head-wall glow of references 5-7.",
         "architecture_change": {"flag": False, "note": "a 0.12 m plaster return at the ceiling"}},
        {"id": "B-P3", "gap": "B-G4", "title": "Lighting ask: LED glow under the bed base",
         "location": {"room": "parents-bed", "wall_or_zone": "under the bed base", "basis": "bed x 19.57-21.09, y -26.33..-24.63"},
         "lighting_ask": {"effect": "2200-2700 K, very low level, night path; the room has no night line near the bed.", "cct_k": 2700, "to_be_designed_by": "lighting lanes (L6 family)", "not_a_finished_design": True},
         "change": "Lighting only.", "effect": "Reference 7.", "architecture_change": {"flag": False, "note": "none"}},
        {"id": "B-P4", "gap": "B-G1", "title": "Opal globe pendants over the nightstands (alternative to the wall-read lamps)",
         "location": {"room": "parents-bed", "wall_or_zone": "above the nightstands, x 19.35 and 21.3, 1.1 m above the floor", "basis": "existing WALL-READ-parents-bed-02/03 are wall opal globes on brass brackets"},
         "product": P.FLOS_IC, "change": "Optional: swap the wall-read globes for two pendant globes; not in the mock-up because the wall-reads already read as opal globes.",
         "effect": "Reference 5.", "architecture_change": {"flag": False, "note": "ceiling fixing"}},
    ]
    return refs, gaps, props


def dining():
    refs = [
        {"id": "image28", "why": "grey marble wall panel framed in bronze, clear-glass pendant cluster, up/down sconces, cove, banquette"},
        {"id": "image29", "why": "textured concrete wall, opal globe pendants at staggered heights, up/down wall cubes, walnut slat flank"},
        {"id": "image30", "why": "concrete wall with backlit walnut shelving, black dome pendant cluster"},
        {"id": "image31", "why": "walnut panelling, clear bubble-glass chandelier, large art"},
    ]
    gaps = [
        {"id": "D-G1", "rank": 1, "feature": "Pendant cluster of glass or opal globes at staggered heights over the table", "refs_showing_it": ["image28", "image29", "image30", "image31"],
         "present_in_scene": "no: one black linear LED pendant (399 lm, 1.14 m long)", "visual_weight": "high (every reference has it)"},
        {"id": "D-G2", "rank": 2, "feature": "Stone or concrete-look feature wall behind the sideboard / party side", "refs_showing_it": ["image28", "image29", "image30"],
         "present_in_scene": "no: plaster-warm-white (Off White) wall behind the walnut sideboard", "visual_weight": "high"},
        {"id": "D-G3", "rank": 3, "feature": "Cove, backlit shelf or wall wash on the feature wall", "refs_showing_it": ["image28", "image29", "image30"],
         "present_in_scene": "two adjustable spots on the sideboard side (ADJ-dining-side-01/02); no wash or cove on the wall", "visual_weight": "medium"},
        {"id": "D-G4", "rank": 4, "feature": "Up/down wall sconces flanking the art zone", "refs_showing_it": ["image28", "image29"],
         "present_in_scene": "no", "visual_weight": "medium"},
        {"id": "D-G5", "rank": 5, "feature": "Upholstered, curved-back dining chairs with cognac or rust seats", "refs_showing_it": ["image28", "image29", "image30", "image31"],
         "present_in_scene": "walnut slat-back chairs with bouclé seats", "visual_weight": "medium; NOT proposed: no verified maker chair found in this pass"},
    ]
    props = [
        {"id": "D-P1", "gap": "D-G1", "title": "Staggered clear-glass globe cluster replacing the linear pendant",
         "location": {"room": "dining", "wall_or_zone": "over the table, centre (16.95, -25.9), globes 0.9-1.3 m below the ceiling", "rect_m": [16.35, 17.55], "z_range_m": [-1.45, -0.30],
                      "basis": "design model: furn-dining-table x 16.05-17.85, lamp-PEN-LIN-dining-01 x 16.38-17.52"},
         "product": P.BOCCI_28,
         "lighting_ask": {"effect": "Replace the 399 lm linear pendant circuit with a 2700 K dimmable globe cluster of at least the same task output on the table (the L6 dining task plane must still pass); the two crossed spots stay.", "cct_k": 2700,
                          "to_be_designed_by": "lighting lanes (L6 family)", "not_a_finished_design": True},
         "change": "Swap one luminaire for a cluster; the table task light must be re-verified.", "effect": "References 28-31.", "architecture_change": {"flag": False, "note": "canopy fixing"}},
        {"id": "D-P2", "gap": "D-G2", "title": "Gris Fleury taupe stone carried up the party-side wall",
         "location": {"room": "dining-side", "wall_or_zone": "south wall behind the sideboard (y = -28.47)", "rect_m": [15.50, 17.40], "z_range_m": [-3.0, -0.3], "basis": "design model: sideboard x 16.2-17.4, wall x 15.44-17.47"},
         "product": P.GRIS_FLEURY, "change": "Floor-to-ceiling stone panel 1.9 m wide in the same product as the floor.", "effect": "The concrete-look wall of references 29 and 30 using the client's own chosen stone.",
         "architecture_change": {"flag": False, "note": "applied finish"}},
        {"id": "D-P3", "gap": "D-G3", "title": "Lighting ask: ceiling-line wash on the stone and up/down sconces either side of the sideboard",
         "location": {"room": "dining-side", "wall_or_zone": "wall wash at z -0.34, x 15.50-17.40; sconces at x 15.66 and 17.24, z -1.75..-1.60", "basis": "design model coordinates above"},
         "lighting_ask": {"effect": "2700 K wall wash grazing the stone from a 40 mm ceiling-line slot, plus two up/down wall sconces on the dining circuit. Mock-up placeholders 600 lm and 120 lm per side.", "cct_k": 2700,
                          "to_be_designed_by": "lighting lanes (L6 family)", "not_a_finished_design": True},
         "change": "Lighting only.", "effect": "References 28 and 29.", "architecture_change": {"flag": False, "note": "a ceiling-line slot"}},
    ]
    return refs, gaps, props


MOCK = {
    "living": {"views": {"v03-street-lounge": "TV wall (lounge)", "v02-garden-living": "garden living alcove"}, "note": ""},
    "media": {"views": {"v08-cinema": "cinema"}, "note": ""},
    "bedroom": {"views": {"n13-parents-day": "parents' bedroom"}, "note": ""},
    "dining": {"views": {"n01-dining-day": "dining", "n20-dining-side-day": "dining party side"}, "note": ""},
}

if __name__ == "__main__":
    rooms = {"living": living, "media": media, "bedroom": bedroom, "dining": dining}
    todo = sys.argv[1:] or list(rooms)
    for r in todo:
        refs, gaps, props = rooms[r]()
        cur = [f"cur_{v}.jpg" for v in MOCK[r]["views"]]
        mock = [f"mock_{v}.jpg" for v in MOCK[r]["views"]]
        w(r, {"schema": 1, "room": r, "references": refs, "gaps": gaps,
              "method": "references read by eye for concrete features, then counted; gaps are features most of the room's references share that the scene lacks"},
          {"schema": 1, "room": r, "concept": "see docs/lanes/RM.md", "proposals": props,
           "mockup": {"scene": "COPY of the render-set scene.json built by scripts/refmatch_build.py; production scene and design model untouched",
                      "exposure": "frozen exposure groups dropped (stale for any geometry change); current and mock-up both use per-state set-metered exposure",
                      "renders": [f"{m}" for m in mock] + [f"{c}" for c in cur]}})
    print("written", todo)
