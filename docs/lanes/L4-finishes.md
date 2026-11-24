# L4: finishes and styling palettes (client resume 2026-11-22, no pricing)

Three palettes, each coherent across the villa. Every item is a real product with a maker page quote; the render look-alike is a CC0 ambientCG / Poly Haven material, labelled as such, with the texture scale derived from the product format (or, where the format is small or absent, the look-alike's own published scan size). **No prices anywhere.** Data: `knowledge/products/finishes/{A,B,C}.json` (generated tables below). Sample boards: `knowledge/products/finishes/boards/`. Production scene untouched.

## What I inferred (character)

- The design is *warm contemporary* (taste weights 42 %, then glam/luxury 23 %, warm transitional 9 %), with the client's 2700 K / CRI 90 lighting, walnut and oak, large-format stone, boucle and fluted timber (`knowledge/projects/villa-01/taste.json`, brief concepts 'Warm Luxury Minimalism', 'The Organic Statement'). Cairo's heat favours stone/porcelain floors and light, low-maintenance surfaces.
- **A Travertine & Walnut** is the closest to the existing design (the production stand-ins are cream stone + walnut). **B Pale Oak & Limestone** is the Japandi/Scandinavian reading: lighter, saves light in the basement. **C Taupe Stone & Smoked Timber** is the richer warm-transitional/quiet-luxury reading.

## Method and honest limits

- Texture scale (`finishes.texture_scale_m`): format long side for stone/tile/worktop/paving; the look-alike's published scan size (ambientCG `dimensionX`, Poly Haven `dimensions`) for timber, fabric and small formats. It replaces RF's assumed 0.6 m. Painted and lacquered surfaces are flat colour at the maker's LRV (no image).
- **LRV** is published for the paint colours only (Dulux Australia colour pages; no Egypt-sold paint publishes LRV on the pages read). Every other LRV is `n/a`, not guessed.
- **Colours of look-alikes** come from `render-colours.json` (our ESTIMATES from the maker's colour name) or, for fabrics, a name-to-hex table; the maker supplies no sRGB. Boards and renders show the look-alike, never the product.
- **Egypt availability is thin**: confirmed only for Ceramica Cleopatra (an Egyptian maker, palette B floor) and IKEA Egypt (cushions, throws, rugs, objects). Marazzi, Kahrs, Caesarstone, Cosentino, EGGER, FENIX, Havwoods, Durian, Dulux (Australian colour data), Phaidon, Ferm Living and Uniqlo have no Egypt page I could cite: they are marked `GAP` (international). Weak Egyptian leads are in `egypt_alternatives` in A.json (Galala / Sunny Menia limestone, Marmonil, Al Motaheda Wood, Jotun Egypt): unverified, no product pages.
- Marazzi pages often give only the product name for finish and R-rating; where the page does not state a slip rating, none is claimed (C floor-wet: wet-room compliance NOT claimed).
- Look-alike weaknesses seen on the boards: ambientCG concrete stands in for cement-look porcelain and sintered stone (speckled, rougher than the product); Marble015/025 are plain stand-ins for quartz; rust-pink veins in some marbles. Fabrics give weave only.

## Palette A: Travertine & Walnut

Warm contemporary: cream travertine-effect stone underfoot, mid-to-dark walnut joinery and warm-white walls, softened by ivory and natural-fibre textiles with brushed brass accents. It is the closest palette to the existing design and the easiest to render with on-disk look-alike materials.

Boards: `boards/A-hard.png`, `boards/A-soft.png` (in `knowledge/products/finishes/`).

### Hard finishes

| id | use | maker, range | colour | format / finish | LRV | Egypt | maker page | look-alike (not the product) | scale |
|---|---|---|---|---|---|---|---|---|---|
| A-floor-living | Lower-ground living, lounge, hall, kitchen floor | Marazzi Mystone Travertino | Navona M9EL | 600 x 1200 x 10 mm | n/a | GAP: No Egypt distributor/showroom/dealer page found for Marazzi (searches | [page](https://www.marazzitile.co.uk/collections/mystone-travertino-collections/) | ambientCG [Travertine009](https://ambientcg.com/view?id=Travertine009) CC0 | 1.20 m (format-long-side) |
| A-floor-gf | Ground-floor bedrooms and corridors | Kährs Kährs engineered wood (brown floors) | American Walnut, stained LTCLRW3010-150 | 150 x 1810 x 7 mm Matt Lacquer | n/a | GAP: No Kahrs Egypt agent found; Nordic Homeworx is Kahrs agent for UAE/Mid | [page](https://a.storyblok.com/f/336347/x/c9fed18ea4/kahrs-engineered-wood-guide-consumer-srp-august-2026-full-digital.pdf) | ambientCG [WoodFloor051](https://ambientcg.com/view?id=WoodFloor051) CC0 | 1.81 m (format-long-side) |
| A-floor-wet | Wet rooms floor (slip-rated) | Marazzi Mystone Tivoli (listed in Mystone Travertino collection page) | Beige MQAY | 600 x 1200 x 9 mm | n/a | GAP: No Egypt distributor/showroom/dealer page found for Marazzi (searches | [page](https://www.marazzitile.co.uk/collections/mystone-travertino-collections/) | ambientCG [Travertine001](https://ambientcg.com/view?id=Travertine001) CC0 | 1.20 m (format-long-side) |
| A-bath-tile | Bathroom wall (fluted 3D), shower walls | Marazzi Mystone Travertino | Navona M9PA | 300 x 600 x 10 mm Struttura 3D Righe (fluted relief) | n/a | GAP: No Egypt distributor/showroom/dealer page found for Marazzi (searches | [page](https://www.marazzitile.co.uk/collections/mystone-travertino-collections/) | ambientCG [Travertine001](https://ambientcg.com/view?id=Travertine001) CC0 | 0.60 m (format-long-side) |
| A-worktop | Kitchen worktop and island (island in 3 cm) | Caesarstone Quartz (Premium group) | Nougat 6600 | 1440 x 3050 mm Polished (P in catalogue) | n/a | GAP: No Caesarstone Egypt distributor found; caesarstone.com where-to-buy p | [page](https://studio.caesarstoneus.com/wp-content/uploads/2025/03/Caesarstone-Catalog-April-2025-US-1.pdf) | ambientCG [Marble015](https://ambientcg.com/view?id=Marble015) CC0 | 3.05 m (format-long-side) |
| A-backsplash | Kitchen backsplash | Marazzi Lume | Caramel MQ7Z | 100 x 100 mm Lux (glossy) | n/a | GAP: No Egypt distributor/showroom/dealer page found for Marazzi (searches | [page](https://www.marazzitile.co.uk/collections/lume-collections/) | Poly Haven [marble_tiles](https://polyhaven.com/a/marble_tiles) CC0 | 2.00 m (lookalike-scan-size) |
| A-joinery-timber | Walnut joinery, TV wall | EGGER Decorative boards (EGGER Decorative Collection) | Natural Dijon Walnut H3734 ST9 | ST9 Smoothtouch Matt | n/a | GAP: No EGGER-published Egypt dealer page read | [page](https://www.egger.com/en/furniture-interior-design/decors/H3734_9?country=GB) | Poly Haven [natural_walnut_veneer](https://polyhaven.com/a/natural_walnut_veneer) CC0 | 1.00 m (lookalike-scan-size) |
| A-joinery-light | Light timber slats, headboard | EGGER Decorative boards (EGGER Decorative Collection) | Natural Hamilton Oak H3303 ST10 | ST10 Deepskin Rough (per search summary of EGGER page) | n/a | GAP: No EGGER-published Egypt dealer page read | [page](https://www.egger.com/en/furniture-interior-design/decors/H3303_10?country=GB) | ambientCG [Wood049](https://ambientcg.com/view?id=Wood049) CC0 | 0.80 m (lookalike-scan-size) |
| A-door | Interior door leaf finish (laminate/HPL on door skin) | EGGER Decorative boards (EGGER Decorative Collection) | Natural Carini Walnut H3710 ST9 | ST9 Smoothtouch Matt | n/a | GAP: No EGGER-published Egypt dealer page read | [page](https://www.egger.com/en/furniture-interior-design/decors/H3710_9?country=GB) | Poly Haven [american_walnut_veneer](https://polyhaven.com/a/american_walnut_veneer) CC0 | 1.00 m (lookalike-scan-size) |
| A-kitchen-front | Kitchen cabinet fronts | EGGER Decorative boards (EGGER Decorative Collection) | Cotton Beige U113 ST9 | ST9 Smoothtouch Matt | n/a | GAP: No EGGER-published Egypt dealer page read | [page](https://www.egger.com/en/furniture-interior-design/decors/U113_9?country=GB) | flat colour / chip | |
| A-wall-paint | Walls and ceilings, warm white | Dulux (AkzoNobel) - Australian colour data Dulux colour collection (whites and neutrals) | Antique White U.S.A. Atlas SW1H7 |  | 84 (https://www.dulux.com.au/colour/whites-a) | GAP: Items specify Dulux Australia colours; no Dulux (Australia) colour is | [page](https://www.dulux.com.au/colour/whites-and-neutrals/antique-white-usa/) | flat colour / chip | |
| A-garden-paving | Terrace and garden paving tying to interior floor | Marazzi Mystone Travertino20 (outdoor) | Navona MN3U | 600 x 1200 x 20 mm Strutturato | n/a | GAP: No Egypt distributor/showroom/dealer page found for Marazzi (searches | [page](https://www.marazzitile.co.uk/collections/mystone-travertino20-collections/) | ambientCG [Travertine009](https://ambientcg.com/view?id=Travertine009) CC0 | 1.20 m (format-long-side) |

### Soft furnishings, cushion schedule, rugs, shelf contents, garments

| id | use | maker, range | colour | format / finish | LRV | Egypt | maker page | look-alike (not the product) | scale |
|---|---|---|---|---|---|---|---|---|---|
| A-living-sofa | Living room 3-seat sofa | IKEA NÄTNÄVA | beige (fuzzy texture per image alt text) 706.175.89 |  | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/naetnaeva-cushion-cover-beige-70617589/) | [page](https://www.ikea.com/eg/en/p/naetnaeva-cushion-cover-beige-70617589/) | Poly Haven [curly_teddy_natural](https://polyhaven.com/a/curly_teddy_natural) CC0 | 0.34 m (lookalike-scan-size) |
| A-lounge-sofa | Lounge 4-seat sofa | IKEA ÅSVEIG | grey-brown (corduroy per image alt text) 806.264.18 |  | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/asveig-cushion-cover-grey-brown-80626418/) | [page](https://www.ikea.com/eg/en/p/asveig-cushion-cover-grey-brown-80626418/) | Poly Haven [ribbed_corduroy](https://polyhaven.com/a/ribbed_corduroy) CC0 | 0.27 m (lookalike-scan-size) |
| A-study-sofa | Study 2-seat sofa | IKEA DYTÅG | dark beige 805.176.88 |  | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/dytag-cushion-cover-dark-beige-80517688/) | [page](https://www.ikea.com/eg/en/p/dytag-cushion-cover-dark-beige-80517688/) | Poly Haven [rough_linen](https://polyhaven.com/a/rough_linen) CC0 | 0.27 m (lookalike-scan-size) |
| A-cinema-sofa | Cinema room 2-seat sofa | IKEA NÄTNÄVA | brown (fuzzy texture per image alt text) 206.397.01 |  | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/naetnaeva-cushion-cover-brown-20639701/) | [page](https://www.ikea.com/eg/en/p/naetnaeva-cushion-cover-brown-20639701/) | Poly Haven [curly_teddy_natural](https://polyhaven.com/a/curly_teddy_natural) CC0 | 0.34 m (lookalike-scan-size) |
| A-library-daybed | Library daybed | IKEA ÅSVEIG | light beige 906.132.60 |  | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/asveig-cushion-cover-light-beige-90613260/) | [page](https://www.ikea.com/eg/en/p/asveig-cushion-cover-light-beige-90613260/) | Poly Haven [rough_linen](https://polyhaven.com/a/rough_linen) CC0 | 0.27 m (lookalike-scan-size) |
| A-parents-bed | Parents' bed: bed cushions plus throw | IKEA JÄTTEGRAN | off-white (jacquard-woven per image alt text) 805.722.41 |  | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/jaettegran-cushion-cover-off-white-80572241/) | [page](https://www.ikea.com/eg/en/p/jaettegran-cushion-cover-off-white-80572241/) | Poly Haven [rough_linen](https://polyhaven.com/a/rough_linen) CC0 | 0.27 m (lookalike-scan-size) |
| A-rug-living | Living room rug | IKEA LOHALS | natural | 2000 x 3000 mm | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/lohals-rug-flatwoven-natural-00277395/) | [page](https://www.ikea.com/eg/en/p/lohals-rug-flatwoven-natural-00277395/) | Poly Haven [hessian_230](https://polyhaven.com/a/hessian_230) CC0 | 0.27 m (lookalike-scan-size) |
| A-rug-lounge | Lounge rug | IKEA LOKALTÅG | beige/grey | 2000 x 3000 mm | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/lokaltag-rug-low-pile-beige-grey-00623230/) | [page](https://www.ikea.com/eg/en/p/lokaltag-rug-low-pile-beige-grey-00623230/) | ambientCG [Carpet016](https://ambientcg.com/view?id=Carpet016) CC0 | 1.70 m (lookalike-scan-size) |
| A-rug-parents | Parents' bedroom rug | IKEA KANARIEPALM | off-white | 2000 x 3000 mm | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/kanariepalm-rug-low-pile-off-white-20635958/) | [page](https://www.ikea.com/eg/en/p/kanariepalm-rug-low-pile-off-white-20635958/) | ambientCG [Carpet016](https://ambientcg.com/view?id=Carpet016) CC0 | 1.70 m (lookalike-scan-size) |
| A-shelf-book-atlas-interior-design | Open shelf (sparse, 3-5 books) | Phaidon Press Phaidon | 9781838663063 | Standard Edition (hardback per Phaidon listing - not read; treat as unverified) | n/a | GAP: Phaidon Egypt availability not checked in this pass. | [page](https://www.phaidon.com/store/home-and-garden/atlas-of-interior-design-9781838663063/) | flat colour / chip | |
| A-shelf-book-atlas-21c-houses | Open shelf (sparse, 3-5 books) | Phaidon Press Phaidon | 9781838667658 | Standard Edition (hardback per Phaidon listing - not read; treat as unverified) | n/a | GAP: Phaidon Egypt availability not checked in this pass. | [page](https://www.phaidon.com/en-us/products/atlas-of-twenty-first-century-houses) | flat colour / chip | |
| A-shelf-book-shizen | Open shelf (sparse, 3-5 books) | Phaidon Press Phaidon | 9781837293667 | Standard Edition (hardback per Phaidon listing - not read; treat as unverified) | n/a | GAP: Phaidon Egypt availability not checked in this pass. | [page](https://www.phaidon.com/en-us/products/shizen-spaces-shaped-by-nature-in-japan) | flat colour / chip | |
| A-shelf-book-japanese-garden | Open shelf (sparse, 3-5 books) | Phaidon Press Phaidon | 9780714874777 | Standard Edition (hardback per Phaidon listing - not read; treat as unverified) | n/a | GAP: Phaidon Egypt availability not checked in this pass. | [page](https://www.phaidon.com/store/design/the-japanese-garden-9780714874777/) | flat colour / chip | |
| A-shelf-decor-fountain-vase | Open shelf decor | Ferm Living Ferm Living collection | Off-White |  | n/a | GAP: Ferm Living Egypt availability not checked in this pass. | [page](https://fermliving.com/products/fountain-vase-off-white) | flat colour / chip | |
| A-shelf-decor-block-candle | Open shelf decor | Ferm Living Ferm Living collection | Brass |  | n/a | GAP: Ferm Living Egypt availability not checked in this pass. | [page](https://fermliving.com/products/block-candle-holder-brass) | flat colour / chip | |
| A-shelf-decor-balance-candle | Open shelf decor | Ferm Living Ferm Living collection | Brass |  | n/a | GAP: Ferm Living Egypt availability not checked in this pass. | [page](https://fermliving.com/products/balance-candle-holder-brass) | flat colour / chip | |
| A-garment-supima-tee | Dressing room wardrobe | Uniqlo SUPIMA Cotton | BEIGE 31 |  | n/a | GAP: Uniqlo Egypt availability not checked in this pass. | [page](https://www.uniqlo.com/us/en/products/E455365-000/00?colorDisplayCode=31) | flat colour / chip | |
| A-garment-slim-chino | Dressing room wardrobe | Uniqlo Chino | BEIGE 32 |  | n/a | GAP: Uniqlo Egypt availability not checked in this pass. | [page](https://www.uniqlo.com/us/en/products/E450251-000/00?colorDisplayCode=32) | flat colour / chip | |
| A-garment-linen-shirt | Dressing room wardrobe | Uniqlo Premium Linen | OLIVE 57 |  | n/a | GAP: Uniqlo Egypt availability not checked in this pass. | [page](https://www.uniqlo.com/us/en/products/E444641-000/00?colorDisplayCode=57) | flat colour / chip | |
| A-garment-merino | Dressing room wardrobe | Uniqlo Merino | GREY 07 |  | n/a | GAP: Uniqlo Egypt availability not checked in this pass. | [page](https://www.uniqlo.com/se/en/products/E450535-000/00) | flat colour / chip | |

### Cushion and throw schedule (per sofa)

| sofa / bed | item | maker, range | colour | size | composition | Egypt |
|---|---|---|---|---|---|---|
| Living room 3-seat sofa | A-living-sofa | IKEA NÄTNÄVA | beige (fuzzy texture per image alt text) 706.175.89 |  | 100 % polyester (100% recycled) | yes |
| Lounge 4-seat sofa | A-lounge-sofa | IKEA ÅSVEIG | grey-brown (corduroy per image alt text) 806.264.18 |  | 100% cotton | yes |
| Study 2-seat sofa | A-study-sofa | IKEA DYTÅG | dark beige 805.176.88 |  | 100% linen | yes |
| Cinema room 2-seat sofa | A-cinema-sofa | IKEA NÄTNÄVA | brown (fuzzy texture per image alt text) 206.397.01 |  | 100 % polyester (100% recycled) | yes |
| Library daybed | A-library-daybed | IKEA ÅSVEIG | light beige 906.132.60 |  | 100% cotton | yes |
| Parents' bed: bed cushions plus throw | A-parents-bed | IKEA JÄTTEGRAN | off-white (jacquard-woven per image alt text) 805.722.41 |  | 100% cotton | yes |

### Maintenance and durability (cited)

- **A-floor-living**: Maker technical characteristics for this tile ([source](https://www.marazzitile.co.uk/collections/mystone-travertino-collections/)): "Technical characteristics: Frost proof Resistance deep abrasion"
- **A-floor-gf**: Maker note on matt finishes (collection text) ([source](https://a.storyblok.com/f/336347/x/c9fed18ea4/kahrs-engineered-wood-guide-consumer-srp-august-2026-full-digital.pdf)): "Low maintenance scuff free & soft to the touch."
- **A-floor-wet**: Maker technical characteristics for this tile ([source](https://www.marazzitile.co.uk/collections/mystone-travertino-collections/)): "Technical characteristics: Frost proof Resistance deep abrasion"
- **A-bath-tile**: Collection-level durability statement ([source](https://www.marazzitile.co.uk/collections/mystone-travertino-collections/)): "StepWise, Tecnico and Sublime Sync enhance depth, durability and continuity between indoors and out."
- **A-worktop**: Maker design/spec page ([source](https://www.caesarstone.com/design-and-specification/)): "Caesarstone retains its beauty without sealants or waxes."
- **A-backsplash**: Maker technical characteristics ([source](https://www.marazzitile.co.uk/collections/lume-collections/)): "Frost proof Resistance deep abrasion"
- **A-joinery-timber**: Maker cleaning guidance for melamine-faced boards (Cleaf data sheet hosted on egger.com downloads) ([source](https://downloads.egger.com/static/decorative/Cleaf_Technical_data_sheet_MFC_EN.pdf)): "For cleaning, use only soft cloths and normal household hygiene products."
- **A-joinery-light**: Maker cleaning guidance for melamine-faced boards (Cleaf data sheet hosted on egger.com downloads) ([source](https://downloads.egger.com/static/decorative/Cleaf_Technical_data_sheet_MFC_EN.pdf)): "For cleaning, use only soft cloths and normal household hygiene products."
- **A-door**: Maker cleaning guidance for melamine-faced boards (Cleaf data sheet hosted on egger.com downloads) ([source](https://downloads.egger.com/static/decorative/Cleaf_Technical_data_sheet_MFC_EN.pdf)): "For cleaning, use only soft cloths and normal household hygiene products."
- **A-kitchen-front**: Maker cleaning guidance for melamine-faced boards (Cleaf data sheet hosted on egger.com downloads) ([source](https://downloads.egger.com/static/decorative/Cleaf_Technical_data_sheet_MFC_EN.pdf)): "For cleaning, use only soft cloths and normal household hygiene products."
- **A-garden-paving**: Maker technical characteristics ([source](https://www.marazzitile.co.uk/collections/mystone-travertino20-collections/)): "Technical characteristics: Frost proof Resistance deep abrasion"

## Palette B: Pale Oak & Limestone

A lighter, calmer Japandi-warm palette of sand limestone-look porcelain, pale oak and warm off-white walls that stretches light in a hot-climate villa. Undyed linen, jute and wool with matt black metal accents keep it soft and tactile.

Boards: `boards/B-hard.png`, `boards/B-soft.png` (in `knowledge/products/finishes/`).

### Hard finishes

| id | use | maker, range | colour | format / finish | LRV | Egypt | maker page | look-alike (not the product) | scale |
|---|---|---|---|---|---|---|---|---|---|
| B-floor-living | Lower-ground living, lounge, hall, kitchen floor | Ceramica Cleopatra Rock (Cemento) | Beige | 1200 x 1200 x 8 mm Matt, rectified porcelain | n/a | [Ceramica Cleopatra Group (Egyptian manufacturer)](https://www.cleopatraceramics.com/en/ceramic-tiles-collections/Rock/) | [page](https://www.cleopatraceramics.com/en/ceramic-tiles-collections/Rock/) | ambientCG [Concrete012](https://ambientcg.com/view?id=Concrete012) CC0 | 1.20 m (format-long-side) |
| B-floor-gf | Ground-floor bedrooms and corridors, engineered oak | Kahrs Harmony | Oak Pale 153N5BEKP1KW240 | 200 x 2423 x 15 mm Matt lacquer, brushed | n/a | GAP: No Kahrs Egypt agent found; Nordic Homeworx is Kahrs agent for UAE/Mid | [page](https://www.kahrs.com/uk/product/oak-pale-2975) | ambientCG [WoodFloor051](https://ambientcg.com/view?id=WoodFloor051) CC0 | 2.42 m (format-long-side) |
| B-floor-wet | Wet-room floors (slip-rated) | Marazzi Mystone Limestone | Sand | 1600 x 1600 x 9 mm Matt (Naturale/Matt filter), rectified | n/a | GAP: No Egypt distributor/showroom/dealer page found for Marazzi (searches | [page](https://www.marazzigroup.com/collections/mystone-limestone-collection/) | ambientCG [Concrete012](https://ambientcg.com/view?id=Concrete012) CC0 | 1.60 m (format-long-side) |
| B-bath-tile | Bathroom wall tile | Marazzi Limestone Wall | Sand MFCE | 400 x 1200 x 6 mm Matt (only finish filter shown; not stated for this product) | n/a | GAP: No Egypt distributor/showroom/dealer page found for Marazzi (searches | [page](https://www.marazzigroup.com/collections/limestone-wall-collection/) | ambientCG [Travertine009](https://ambientcg.com/view?id=Travertine009) CC0 | 1.20 m (format-long-side) |
| B-worktop | Kitchen worktop and island | Cosentino Dekton Kraftizen | Nacre | 1470 x 3270 mm Grip+ or Velvet (both listed) | n/a | GAP: No Cosentino Egypt page found; cosentino.com/en-eg redirects (307); Mi | [page](https://www.cosentino.com/usa/colors/dekton/nacre/) | ambientCG [Marble025](https://ambientcg.com/view?id=Marble025) CC0 | 3.27 m (format-long-side) |
| B-backsplash | Kitchen backsplash (continuous slab) | Cosentino Dekton Kraftizen | Nacre | 1470 x 3270 mm Grip+ or Velvet (both listed) | n/a | GAP: No Cosentino Egypt page found; cosentino.com/en-eg redirects (307); Mi | [page](https://www.cosentino.com/usa/colors/dekton/nacre/) | ambientCG [Marble025](https://ambientcg.com/view?id=Marble025) CC0 | 3.27 m (format-long-side) |
| B-joinery-timber | TV wall, bookcases (oak-look decor) | EGGER Feelwood | Natural Halifax Oak H1180 ST37 | ST37 Feelwood Rift embossed-in-register (from search summary) | n/a | GAP: No EGGER-published Egypt dealer page read | [page](https://www.egger.com/en/furniture-interior-design/decors/Q1180_RO?lci=Y29sbD0xNjU1Jm5jPW5hdzEg) | Poly Haven [oak_veneer_01](https://polyhaven.com/a/oak_veneer_01) CC0 | 1.83 m (lookalike-scan-size) |
| B-joinery-light | Slats, headboard (light timber) | EGGER Feelwood | Natural Halifax Oak H1180 ST37 |  | n/a | GAP: No EGGER-published Egypt dealer page read | [page](https://www.egger.com/en/furniture-interior-design/decors/Q1180_RO?lci=Y29sbD0xNjU1Jm5jPW5hdzEg) | Poly Haven [white_oak_veneer](https://polyhaven.com/a/white_oak_veneer) CC0 | 0.50 m (lookalike-scan-size) |
| B-door | Interior doors | LPD Doors Blonde Oak | Blonde Oak SOHOAKSOL30 | 762 x 1981 x 35 mm Pre-finished, light blonde oak finish | n/a | GAP: to be checked | [page](https://lpddoors.co.uk/products/blonde-oak-soho/) | Poly Haven [white_oak_veneer](https://polyhaven.com/a/white_oak_veneer) CC0 | 0.50 m (lookalike-scan-size) |
| B-kitchen-front | Kitchen cabinet fronts | FENIX FENIX NTM | Beige Luxor 0719 | 1300 x 3050 mm | n/a | GAP: to be checked | [page](https://www.fenixforinteriors.com/en/fenix/beige-luxor) | flat colour / chip | |
| B-wall-paint | Walls and ceilings, warm off-white | Dulux (Australia) Atlas colour system | Off White SW1E7 | Matt (not stated on page) | 89 (Dulux Australia colour page: (Light Refl) | GAP: Items specify Dulux Australia colours; no Dulux (Australia) colour is | [page](https://www.dulux.com.au/specifier/colour/whites-sw1/off-white) | flat colour / chip | |
| B-garden-paving | Terrace and garden paving tying to interior stone | Marazzi Mystone Limestone20 | Sand MFH4 | 1200 x 1200 x 20 mm Strutturato (textured), rectified | n/a | GAP: No Egypt distributor/showroom/dealer page found for Marazzi (searches | [page](https://www.marazzigroup.com/collections/mystone-limestone20-collection/) | ambientCG [Travertine009](https://ambientcg.com/view?id=Travertine009) CC0 | 1.20 m (format-long-side) |

### Soft furnishings, cushion schedule, rugs, shelf contents, garments

| id | use | maker, range | colour | format / finish | LRV | Egypt | maker page | look-alike (not the product) | scale |
|---|---|---|---|---|---|---|---|---|---|
| B-cushions-living-sofa | Cushions and throw for living-sofa | IKEA DYTAG | dark beige | 650 x 650 mm | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/cat/cushions-cushion-covers-10659/) | [page](https://www.ikea.com/eg/en/cat/cushions-cushion-covers-10659/) | Poly Haven [rough_linen](https://polyhaven.com/a/rough_linen) CC0 | 0.27 m (lookalike-scan-size) |
| B-cushions-lounge-sofa | Cushions and throw for lounge-sofa | IKEA DYTAG | dark beige | 650 x 650 mm | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/cat/cushions-cushion-covers-10659/) | [page](https://www.ikea.com/eg/en/cat/cushions-cushion-covers-10659/) | Poly Haven [rough_linen](https://polyhaven.com/a/rough_linen) CC0 | 0.27 m (lookalike-scan-size) |
| B-cushions-study-sofa | Cushions and throw for study-sofa | IKEA DYTAG | unbleached | 500 x 500 mm | n/a | GAP: DYTAG unbleached not seen on IKEA Egypt page. | [page](https://www.ikea.com/gb/en/p/dytag-cushion-cover-unbleached-20625445/) | Poly Haven [rough_linen](https://polyhaven.com/a/rough_linen) CC0 | 0.27 m (lookalike-scan-size) |
| B-cushions-cinema-sofa | Cushions and throw for cinema-sofa | IKEA VALLKRASSING | light grey-brown | 500 x 500 mm | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/cat/cushions-cushion-covers-10659/) | [page](https://www.ikea.com/eg/en/cat/cushions-cushion-covers-10659/) | Poly Haven [rough_linen](https://polyhaven.com/a/rough_linen) CC0 | 0.27 m (lookalike-scan-size) |
| B-cushions-library-daybed | Cushions and throw for library-daybed | IKEA DYTAG | unbleached | 500 x 500 mm | n/a | GAP: DYTAG unbleached not seen on IKEA Egypt page. | [page](https://www.ikea.com/gb/en/p/dytag-cushion-cover-unbleached-20625445/) | Poly Haven [rough_linen](https://polyhaven.com/a/rough_linen) CC0 | 0.27 m (lookalike-scan-size) |
| B-cushions-parents-bed | Cushions and throw for parents-bed | IKEA DYTAG | unbleached | 500 x 500 mm | n/a | GAP: DYTAG unbleached not seen on IKEA Egypt page. | [page](https://www.ikea.com/gb/en/p/dytag-cushion-cover-unbleached-20625445/) | Poly Haven [rough_linen](https://polyhaven.com/a/rough_linen) CC0 | 0.27 m (lookalike-scan-size) |
| B-rug-living | Living room rug | IKEA LOHALS | natural | 2000 x 3000 mm flatwoven | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/lohals-rug-flatwoven-natural-00277395/) | [page](https://www.ikea.com/eg/en/p/lohals-rug-flatwoven-natural-00277395/) | Poly Haven [hessian_230](https://polyhaven.com/a/hessian_230) CC0 | 0.27 m (lookalike-scan-size) |
| B-rug-lounge | lounge rug | IKEA TIDTABELL | beige | 2000 x 3000 x 6 mm flatwoven | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/tidtabell-rug-flatwoven-beige-50561852/) | [page](https://www.ikea.com/eg/en/p/tidtabell-rug-flatwoven-beige-50561852/) | ambientCG [Carpet016](https://ambientcg.com/view?id=Carpet016) CC0 | 1.70 m (lookalike-scan-size) |
| B-rug-parents-bedroom | parents-bedroom rug | IKEA TIDTABELL | beige | 1700 x 2400 mm flatwoven | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/tidtabell-rug-flatwoven-beige-30555282/) | [page](https://www.ikea.com/eg/en/p/tidtabell-rug-flatwoven-beige-30555282/) | ambientCG [Carpet016](https://ambientcg.com/view?id=Carpet016) CC0 | 1.70 m (lookalike-scan-size) |
| B-book-1 | Open shelf, library/living | Phaidon Japanese Interiors |  |  | n/a | GAP: Phaidon Egypt availability not checked in this pass. | [page](https://www.phaidon.com/store/home-and-garden/japanese-interiors-9781838663995/) | flat colour / chip | |
| B-book-2 | Open shelf, library/living | Phaidon WA: The Essence of Japanese Design |  |  | n/a | GAP: Phaidon Egypt availability not checked in this pass. | [page](https://www.phaidon.com/store/design/wa-the-essence-of-japanese-design-9780714866963/) | flat colour / chip | |
| B-book-3 | Open shelf, library/living | Thames & Hudson Japanese Style at Home |  | 160 x 210 mm Flexibound | n/a | GAP: to be checked | [page](https://www.thamesandhudson.com/products/japanese-style-at-home) | flat colour / chip | |
| B-book-4 | Open shelf, library/living | Thames & Hudson The Japanese House Since 1945 |  | 230 x 280 mm Hardback | n/a | GAP: to be checked | [page](https://thamesandhudson.com/the-japanese-house-since-1945-9780500343739) | flat colour / chip | |
| B-object-1 | Open shelf decor | Ferm Living Shell Vase - Off-white |  |  | n/a | GAP: Ferm Living Egypt availability not checked in this pass. | [page](https://fermliving.com/products/shell-vase-off-white) | flat colour / chip | |
| B-object-2 | Open shelf decor | Ferm Living Spun Alu Vase - Blackened Aluminium |  |  | n/a | GAP: Ferm Living Egypt availability not checked in this pass. | [page](https://fermliving.com/products/spun-alu-vase-blackened-aluminium) | flat colour / chip | |
| B-object-3 | Open shelf decor | Ferm Living Moire Vase - H30 - Off-white |  |  | n/a | GAP: Ferm Living Egypt availability not checked in this pass. | [page](https://fermliving.com/products/moire-vase-off-white) | flat colour / chip | |
| B-garment-1 | Dressing room basics | Uniqlo Premium Linen | OFF WHITE 01 |  | n/a | GAP: Uniqlo Egypt availability not checked in this pass. | [page](https://www.uniqlo.com/in/en/products/E482434-000/01) | flat colour / chip | |
| B-garment-2 | Dressing room basics | Marks & Spencer M&S Sartorial | Neutral (M&S colour group; swatch name not read; page also lists a BLUE option) |  | n/a | GAP: to be checked | [page](https://www.marksandspencer.com/regular-fit-egyptian-cotton-dobby-shirt/p/clp60916527) | flat colour / chip | |

### Cushion and throw schedule (per sofa)

| sofa / bed | item | maker, range | colour | size | composition | Egypt |
|---|---|---|---|---|---|---|
| Cushions and throw for living-sofa | B-cushions-living-sofa | IKEA DYTAG | dark beige  | 650 x 650 mm | linen (per Egypt category listing) | yes |
| Cushions and throw for lounge-sofa | B-cushions-lounge-sofa | IKEA DYTAG | dark beige  | 650 x 650 mm | linen (per Egypt category listing) | yes |
| Cushions and throw for study-sofa | B-cushions-study-sofa | IKEA DYTAG | unbleached  | 500 x 500 mm | 100% linen | GAP |
| Cushions and throw for cinema-sofa | B-cushions-cinema-sofa | IKEA VALLKRASSING | light grey-brown  | 500 x 500 mm | cotton (per Egypt category listing) | yes |
| Cushions and throw for library-daybed | B-cushions-library-daybed | IKEA DYTAG | unbleached  | 500 x 500 mm | 100% linen | GAP |
| Cushions and throw for parents-bed | B-cushions-parents-bed | IKEA DYTAG | unbleached  | 500 x 500 mm | 100% linen | GAP |
| parents-bedroom rug | B-rug-parents-bedroom | IKEA TIDTABELL | beige  | 1700 x 2400 mm | User surface 100% wool; warp 100% cotton | yes |

### Maintenance and durability (cited)

- **B-floor-wet**: Maker states grip/cleaning performance ([source](https://www.marazzigroup.com/collections/mystone-limestone-collection/)): "StepWise and Tecnico improve grip, cleaning and performance from indoor areas to outdoor spaces."
- **B-garden-paving**: Maker on grip ([source](https://www.marazzigroup.com/collections/mystone-limestone20-collection/)): "Tecnico technology improves reliability, grip and slip resistance."

## Palette C: Taupe Stone & Smoked Timber

A quiet-luxury warm-transitional scheme: taupe limestone-look porcelain, smoked oak and deep clay walls with a dark veined stone worktop. Soft layers in olive, clay, camel and charcoal velvet and wool keep the deeper palette warm for a lower-ground living level.

Boards: `boards/C-hard.png`, `boards/C-soft.png` (in `knowledge/products/finishes/`).

### Hard finishes

| id | use | maker, range | colour | format / finish | LRV | Egypt | maker page | look-alike (not the product) | scale |
|---|---|---|---|---|---|---|---|---|---|
| C-floor-living | Lower-ground living, lounge, hall, kitchen floor | Marazzi Mystone Gris Fleury | Taupe MLGY | 600 x 1200 x 10 mm Naturale/Matt, rectified, through-body coloured porcelain | n/a | GAP: No Egypt distributor/showroom/dealer page found for Marazzi (searches | [page](https://www.marazzi.it/en/mystone-gris-fleury) | ambientCG [Marble007](https://ambientcg.com/view?id=Marble007) CC0 | 1.20 m (format-long-side) |
| C-floor-gf | Ground-floor bedrooms and corridors, smoked oak | Havwoods Venture Plank | Smoked Cocoa (colour group Cocoa) HW7470 | 242 x 1750-2350 x 15 mm Brushed & Smoked, lacquered, 4mm wear layer | n/a | GAP: No Havwoods Egypt dealer found. | [page](https://www.havwoods.com/uk/products/hw7470/) | ambientCG [WoodFloor041](https://ambientcg.com/view?id=WoodFloor041) CC0 | 2.35 m (format-long-side) |
| C-floor-wet | Wet rooms floor, slip-resistant 20 mm porcelain | Marazzi Mystone Limestone20 | Taupe M7SQ | 600 x 1200 x 20 mm Strutturato (structured), rectified | n/a | GAP: No Egypt distributor/showroom/dealer page found for Marazzi (searches | [page](https://www.marazzigroup.com/collections/mystone-limestone20-collection/) | ambientCG [Concrete012](https://ambientcg.com/view?id=Concrete012) CC0 | 1.20 m (format-long-side) |
| C-bath-tile | Bathroom walls and floors, large-format slab | Marazzi Grande Marble Look | Frappuccino M0G3 | 1200 x 1200 mm Lux (per product name), rectified | n/a | GAP: No Egypt distributor/showroom/dealer page found for Marazzi (searches | [page](https://www.marazzigroup.com/collections/grande-marble-look-collection/) | ambientCG [Marble015](https://ambientcg.com/view?id=Marble015) CC0 | 1.20 m (format-long-side) |
| C-worktop | Kitchen worktop and island, dark veined quartz | Silestone (Cosentino) Eternal | Eternal Marquina | 1590 x 3250 mm Polished or Suede | n/a | GAP: No Cosentino Egypt page found; cosentino.com/en-eg redirects (307); Mi | [page](https://www.specifiedby.com/ivett-reed/eternal-marquina) | ambientCG [Marble017](https://ambientcg.com/view?id=Marble017) CC0 | 3.25 m (format-long-side) |
| C-backsplash | Kitchen backsplash, dark veined large-format porcelain | Marazzi Grande Marble Look | Onice Nero MEP5 | 1200 x 2780 mm Lux (per product name), rectified | n/a | GAP: No Egypt distributor/showroom/dealer page found for Marazzi (searches | [page](https://www.marazzigroup.com/collections/grande-marble-look-collection/) | ambientCG [Marble006](https://ambientcg.com/view?id=Marble006) CC0 | 2.78 m (format-long-side) |
| C-joinery-timber | TV wall, bookcases, smoked/dark timber decor | EGGER Feelwood | Brown Halifax Oak H3180 ST37 | ST37 Feelwood Rift synchronised pore | n/a | GAP: No EGGER-published Egypt dealer page read | [page](https://www.egger.com/en/furniture-interior-design/decors/H3180_37?country=GB) | ambientCG [Wood051](https://ambientcg.com/view?id=Wood051) CC0 | 0.80 m (lookalike-scan-size) |
| C-joinery-light | Slats / headboard, lighter contrast timber | EGGER Feelwood | Natural Halifax Oak H1180 ST37 | 1300 x 2311 mm ST37 Feelwood Rift synchronised surface texture | n/a | GAP: No EGGER-published Egypt dealer page read | [page](https://www.egger.com/en/furniture-interior-design/decors/H1180_37?country=GB) | Poly Haven [white_oak_veneer](https://polyhaven.com/a/white_oak_veneer) CC0 | 0.50 m (lookalike-scan-size) |
| C-door | Interior doors, smoke oak veneer | Durian Craftsman Series | Smoke Oak | PU Matt / PU Gloss | n/a | GAP: No Durian Egypt dealer found; Durian is an Indian maker. | [page](https://www.durian.in/product/trace) | ambientCG [Wood049](https://ambientcg.com/view?id=Wood049) CC0 | 0.80 m (lookalike-scan-size) |
| C-kitchen-front | Kitchen cabinet fronts, matt taupe-brown laminate | FENIX FENIX NTM | Castoro Ottawa 0717 | 1300 x 3050 mm | n/a | GAP: No FENIX Egypt distributor found. | [page](https://www.fenixforinteriors.com/en/fenix/castoro-ottawa) | flat colour / chip | |
| C-wall-paint | Deep warm taupe-clay feature walls (pale ceiling separate) | Dulux Australia Dulux colour specifier | Nile Clay S13B5 (Atlas) |  | 27 (https://www.dulux.com.au/specifier/colou) | GAP: Items specify Dulux Australia colours; no Dulux (Australia) colour is | [page](https://www.dulux.com.au/specifier/colour/s13/nile-clay/) | flat colour / chip | |
| C-garden-paving | Garden paving tying to interior floor, 20 mm outdoor porcelain | Marazzi Mystone Gris Fleury20 | Grigio | 600 x 600 x 20 mm Outdoor | n/a | GAP: No Egypt distributor/showroom/dealer page found for Marazzi (searches | [page](https://www.marazzi.it/en/mystone-gris-fleury) | ambientCG [Travertine009](https://ambientcg.com/view?id=Travertine009) CC0 | 0.60 m (format-long-side) |

### Soft furnishings, cushion schedule, rugs, shelf contents, garments

| id | use | maker, range | colour | format / finish | LRV | Egypt | maker page | look-alike (not the product) | scale |
|---|---|---|---|---|---|---|---|---|---|
| C-cushion-living-sofa-1 | Living 3-seat sofa | IKEA SANELA | dark brown 906.360.25 | 500 x 500 mm | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/sanela-cushion-cover-dark-brown-90636025/) | [page](https://www.ikea.com/eg/en/p/sanela-cushion-cover-dark-brown-90636025/) | Poly Haven [rough_linen](https://polyhaven.com/a/rough_linen) CC0 | 0.27 m (lookalike-scan-size) |
| C-cushion-living-sofa-2 | Living 3-seat sofa | IKEA SANELA | dark green 406.360.04 | 500 x 500 mm | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/sanela-cushion-cover-dark-green-40636004/) | [page](https://www.ikea.com/eg/en/p/sanela-cushion-cover-dark-green-40636004/) | ambientCG [Fabric066](https://ambientcg.com/view?id=Fabric066) CC0 | 0.40 m (lookalike-scan-size) |
| C-cushion-living-sofa-3 | Living 3-seat sofa | IKEA LAGERPOPPEL | light brown 905.618.07 | 400 x 580 mm | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/lagerpoppel-cushion-cover-light-brown-90561807/) | [page](https://www.ikea.com/eg/en/p/lagerpoppel-cushion-cover-light-brown-90561807/) | ambientCG [Fabric066](https://ambientcg.com/view?id=Fabric066) CC0 | 0.40 m (lookalike-scan-size) |
| C-cushion-lounge-sofa-1 | Lounge 4-seat sofa | IKEA SANELA | dark green 406.360.04 | 500 x 500 mm | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/sanela-cushion-cover-dark-green-40636004/) | [page](https://www.ikea.com/eg/en/p/sanela-cushion-cover-dark-green-40636004/) | ambientCG [Fabric066](https://ambientcg.com/view?id=Fabric066) CC0 | 0.40 m (lookalike-scan-size) |
| C-cushion-lounge-sofa-2 | Lounge 4-seat sofa | IKEA SANELA | dark grey 305.911.24 | 500 x 500 mm | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/sanela-cushion-cover-dark-grey-30591124/) | [page](https://www.ikea.com/eg/en/p/sanela-cushion-cover-dark-grey-30591124/) | Poly Haven [rough_linen](https://polyhaven.com/a/rough_linen) CC0 | 0.27 m (lookalike-scan-size) |
| C-cushion-lounge-sofa-3 | Lounge 4-seat sofa | IKEA SANELA | yellow-brown 506.359.90 | 500 x 500 mm | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/sanela-cushion-cover-yellow-brown-50635990/) | [page](https://www.ikea.com/eg/en/p/sanela-cushion-cover-yellow-brown-50635990/) | ambientCG [Leather035A](https://ambientcg.com/view?id=Leather035A) CC0 | 0.30 m (lookalike-scan-size) |
| C-cushion-study-sofa-1 | Study 2-seat sofa | IKEA SANELA | dark brown 906.360.25 | 500 x 500 mm | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/sanela-cushion-cover-dark-brown-90636025/) | [page](https://www.ikea.com/eg/en/p/sanela-cushion-cover-dark-brown-90636025/) | Poly Haven [rough_linen](https://polyhaven.com/a/rough_linen) CC0 | 0.27 m (lookalike-scan-size) |
| C-cushion-study-sofa-2 | Study 2-seat sofa | IKEA SANELA | light beige 505.908.97 | 500 x 500 mm | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/sanela-cushion-cover-light-beige-50590897/) | [page](https://www.ikea.com/eg/en/p/sanela-cushion-cover-light-beige-50590897/) | ambientCG [Carpet016](https://ambientcg.com/view?id=Carpet016) CC0 | 1.70 m (lookalike-scan-size) |
| C-cushion-cinema-sofa-1 | Cinema 2-seat sofa | IKEA SANELA | dark grey 305.911.24 | 500 x 500 mm | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/sanela-cushion-cover-dark-grey-30591124/) | [page](https://www.ikea.com/eg/en/p/sanela-cushion-cover-dark-grey-30591124/) | Poly Haven [rough_linen](https://polyhaven.com/a/rough_linen) CC0 | 0.27 m (lookalike-scan-size) |
| C-cushion-cinema-sofa-2 | Cinema 2-seat sofa | IKEA SANELA | dark brown 906.360.25 | 500 x 500 mm | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/sanela-cushion-cover-dark-brown-90636025/) | [page](https://www.ikea.com/eg/en/p/sanela-cushion-cover-dark-brown-90636025/) | Poly Haven [rough_linen](https://polyhaven.com/a/rough_linen) CC0 | 0.27 m (lookalike-scan-size) |
| C-cushion-library-daybed-1 | Library daybed | IKEA SANELA | yellow-brown 506.359.90 | 500 x 500 mm | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/sanela-cushion-cover-yellow-brown-50635990/) | [page](https://www.ikea.com/eg/en/p/sanela-cushion-cover-yellow-brown-50635990/) | ambientCG [Leather035A](https://ambientcg.com/view?id=Leather035A) CC0 | 0.30 m (lookalike-scan-size) |
| C-cushion-library-daybed-2 | Library daybed | IKEA LAGERPOPPEL | light brown 905.618.07 | 400 x 580 mm | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/lagerpoppel-cushion-cover-light-brown-90561807/) | [page](https://www.ikea.com/eg/en/p/lagerpoppel-cushion-cover-light-brown-90561807/) | ambientCG [Fabric066](https://ambientcg.com/view?id=Fabric066) CC0 | 0.40 m (lookalike-scan-size) |
| C-cushion-parents-bed-1 | Parents bed | IKEA SANELA | light beige 505.908.97 | 500 x 500 mm | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/sanela-cushion-cover-light-beige-50590897/) | [page](https://www.ikea.com/eg/en/p/sanela-cushion-cover-light-beige-50590897/) | ambientCG [Carpet016](https://ambientcg.com/view?id=Carpet016) CC0 | 1.70 m (lookalike-scan-size) |
| C-cushion-parents-bed-2 | Parents bed | IKEA SANELA | dark brown 906.360.25 | 500 x 500 mm | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/sanela-cushion-cover-dark-brown-90636025/) | [page](https://www.ikea.com/eg/en/p/sanela-cushion-cover-dark-brown-90636025/) | Poly Haven [rough_linen](https://polyhaven.com/a/rough_linen) CC0 | 0.27 m (lookalike-scan-size) |
| C-cushion-parents-bed-3 | Parents bed | IKEA LAGERPOPPEL | light brown 905.618.07 | 400 x 580 mm | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/lagerpoppel-cushion-cover-light-brown-90561807/) | [page](https://www.ikea.com/eg/en/p/lagerpoppel-cushion-cover-light-brown-90561807/) | ambientCG [Fabric066](https://ambientcg.com/view?id=Fabric066) CC0 | 0.40 m (lookalike-scan-size) |
| C-throw-living-sofa | Living 3-seat sofa | IKEA MYRULL | light grey 905.634.82 | 1300 x 1700 mm | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/myrull-throw-light-grey-90563482) | [page](https://www.ikea.com/eg/en/p/myrull-throw-light-grey-90563482) | Poly Haven [rough_linen](https://polyhaven.com/a/rough_linen) CC0 | 0.27 m (lookalike-scan-size) |
| C-throw-lounge-sofa | Lounge 4-seat sofa | IKEA MYRULL | light grey 905.634.82 | 1300 x 1700 mm | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/myrull-throw-light-grey-90563482) | [page](https://www.ikea.com/eg/en/p/myrull-throw-light-grey-90563482) | Poly Haven [rough_linen](https://polyhaven.com/a/rough_linen) CC0 | 0.27 m (lookalike-scan-size) |
| C-throw-study-sofa | Study 2-seat sofa | IKEA HOLMVI | grey 305.135.98 | 1200 x 1600 mm | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/holmvi-throw-grey-30513598/) | [page](https://www.ikea.com/eg/en/p/holmvi-throw-grey-30513598/) | Poly Haven [rough_linen](https://polyhaven.com/a/rough_linen) CC0 | 0.27 m (lookalike-scan-size) |
| C-throw-cinema-sofa | Cinema 2-seat sofa | IKEA HOLMVI | grey 305.135.98 | 1200 x 1600 mm | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/holmvi-throw-grey-30513598/) | [page](https://www.ikea.com/eg/en/p/holmvi-throw-grey-30513598/) | Poly Haven [rough_linen](https://polyhaven.com/a/rough_linen) CC0 | 0.27 m (lookalike-scan-size) |
| C-throw-library-daybed | Library daybed | IKEA MYRULL | light grey 905.634.82 | 1300 x 1700 mm | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/myrull-throw-light-grey-90563482) | [page](https://www.ikea.com/eg/en/p/myrull-throw-light-grey-90563482) | Poly Haven [rough_linen](https://polyhaven.com/a/rough_linen) CC0 | 0.27 m (lookalike-scan-size) |
| C-throw-parents-bed | Parents bed | IKEA MYRULL | light grey 905.634.82 | 1300 x 1700 mm | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/myrull-throw-light-grey-90563482) | [page](https://www.ikea.com/eg/en/p/myrull-throw-light-grey-90563482) | Poly Haven [rough_linen](https://polyhaven.com/a/rough_linen) CC0 | 0.27 m (lookalike-scan-size) |
| C-rug-living | Living room rug | IKEA BRÖNDEN | beige 705.329.72 | 2000 x 3000 mm | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/broenden-rug-low-pile-handmade-beige-70532972/) | [page](https://www.ikea.com/eg/en/p/broenden-rug-low-pile-handmade-beige-70532972/) | ambientCG [Carpet016](https://ambientcg.com/view?id=Carpet016) CC0 | 1.70 m (lookalike-scan-size) |
| C-rug-lounge | Lounge rug | IKEA BRÖNDEN | beige 705.329.72 | 1700 x 2400 mm | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/broenden-rug-low-pile-handmade-beige-70532972/) | [page](https://www.ikea.com/eg/en/p/broenden-rug-low-pile-handmade-beige-70532972/) | ambientCG [Carpet016](https://ambientcg.com/view?id=Carpet016) CC0 | 1.70 m (lookalike-scan-size) |
| C-rug-parents-bedroom | Parents bedroom rug (bedside runners; larger sizes not seen) | IKEA TIDTABELL | beige 605.618.75 | 800 x 2000 mm | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/tidtabell-rug-flatwoven-beige-60561875/) | [page](https://www.ikea.com/eg/en/p/tidtabell-rug-flatwoven-beige-60561875/) | ambientCG [Carpet016](https://ambientcg.com/view?id=Carpet016) CC0 | 1.70 m (lookalike-scan-size) |
| C-object-vase | Open shelf vase | IKEA STILREN | dark grey-beige 406.232.66 | Stoneware, coloured glaze | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/stilren-vase-dark-grey-beige-40623266) | [page](https://www.ikea.com/eg/en/p/stilren-vase-dark-grey-beige-40623266) | flat colour / chip | |
| C-object-bowl-brown | Open shelf bowl | IKEA STOCKHOLM 2025 | brown 305.924.25 | Stoneware, coloured glaze | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/stockholm-2025-bowl-brown-30592425) | [page](https://www.ikea.com/eg/en/p/stockholm-2025-bowl-brown-30592425) | flat colour / chip | |
| C-object-bowl-beige | Open shelf centrepiece bowl | IKEA STOCKHOLM 2025 | beige 505.924.29 | Stoneware, coloured glaze | n/a | [IKEA Egypt](https://www.ikea.com/eg/en/p/stockholm-2025-serving-bowl-beige-50592429/) | [page](https://www.ikea.com/eg/en/p/stockholm-2025-serving-bowl-beige-50592429/) | flat colour / chip | |
| C-book-wearstler-evocative | Open shelf book | Rizzoli Kelly Wearstler: Evocative Style |  |  | n/a | GAP: No Egypt bookseller page checked; international title | [page](https://www.rizzoliusa.com/book/9780847866038) | flat colour / chip | |
| C-book-wearstler-synchronicity | Open shelf book | Rizzoli Kelly Wearstler: Synchronicity |  |  | n/a | GAP: No Egypt bookseller page checked; international title | [page](https://www.rizzolibookstore.com/product/kelly-wearstler-synchronicity) | flat colour / chip | |
| C-book-van-duysen-private | Open shelf book | Rizzoli Vincent Van Duysen: Private |  |  | n/a | GAP: No Egypt bookseller page checked; international title | [page](https://www.rizzoliusa.com/book/9780847899555) | flat colour / chip | |
| C-book-loyzaga | Open shelf book | Rizzoli Jorge Loyzaga: Classical and Harmonic Proportions |  |  | n/a | GAP: No Egypt bookseller page checked; international title | [page](https://www.rizzoliusa.com/book/9780847873678) | flat colour / chip | |
| C-garment-merino-olive | Dressing room garment | UNIQLO Merino | Olive E469426-000 / 56 |  | n/a | GAP: Uniqlo Egypt availability not checked in this pass. | [page](https://www.uniqlo.com/de/en/products/E469426-000/00) | flat colour / chip | |
| C-garment-merino-grey | Dressing room garment | UNIQLO Merino | Grey E450514-001 / 06 |  | n/a | GAP: Uniqlo Egypt availability not checked in this pass. | [page](https://www.uniqlo.com/be/en/products/E450514-001/00) | flat colour / chip | |
| C-garment-linen-trouser | Dressing room garment | UNIQLO Linen Blend | OLIVE 57 |  | n/a | GAP: to be checked | [page](https://www.uniqlo.com/uk/en/products/E463857-000/00) | flat colour / chip | |
| C-garment-merino-crew | Dressing room garment | UNIQLO Extra Fine Merino | GRAY 03 |  | n/a | GAP: to be checked | [page](https://www.uniqlo.com/us/en/products/E429066-000/00) | flat colour / chip | |

### Cushion and throw schedule (per sofa)

| sofa / bed | item | maker, range | colour | size | composition | Egypt |
|---|---|---|---|---|---|---|
| Living 3-seat sofa | C-cushion-living-sofa-1 | IKEA SANELA | dark brown 906.360.25 | 500 x 500 mm | 100% cotton (min. 20% recycled), cotton velvet | yes |
| Living 3-seat sofa | C-cushion-living-sofa-2 | IKEA SANELA | dark green 406.360.04 | 500 x 500 mm | cotton velvet (composition line not captured) | yes |
| Living 3-seat sofa | C-cushion-living-sofa-3 | IKEA LAGERPOPPEL | light brown 905.618.07 | 400 x 580 mm | 100 % polyester (100% recycled) | yes |
| Lounge 4-seat sofa | C-cushion-lounge-sofa-1 | IKEA SANELA | dark green 406.360.04 | 500 x 500 mm | cotton velvet (composition line not captured) | yes |
| Lounge 4-seat sofa | C-cushion-lounge-sofa-2 | IKEA SANELA | dark grey 305.911.24 | 500 x 500 mm | 100% cotton, cotton velvet | yes |
| Lounge 4-seat sofa | C-cushion-lounge-sofa-3 | IKEA SANELA | yellow-brown 506.359.90 | 500 x 500 mm | 100% cotton (min. 20% recycled), cotton velvet | yes |
| Study 2-seat sofa | C-cushion-study-sofa-1 | IKEA SANELA | dark brown 906.360.25 | 500 x 500 mm | 100% cotton (min. 20% recycled), cotton velvet | yes |
| Study 2-seat sofa | C-cushion-study-sofa-2 | IKEA SANELA | light beige 505.908.97 | 500 x 500 mm | 100% cotton, cotton velvet | yes |
| Cinema 2-seat sofa | C-cushion-cinema-sofa-1 | IKEA SANELA | dark grey 305.911.24 | 500 x 500 mm | 100% cotton, cotton velvet | yes |
| Cinema 2-seat sofa | C-cushion-cinema-sofa-2 | IKEA SANELA | dark brown 906.360.25 | 500 x 500 mm | 100% cotton (min. 20% recycled), cotton velvet | yes |
| Library daybed | C-cushion-library-daybed-1 | IKEA SANELA | yellow-brown 506.359.90 | 500 x 500 mm | 100% cotton (min. 20% recycled), cotton velvet | yes |
| Library daybed | C-cushion-library-daybed-2 | IKEA LAGERPOPPEL | light brown 905.618.07 | 400 x 580 mm | 100 % polyester (100% recycled) | yes |
| Parents bed | C-cushion-parents-bed-1 | IKEA SANELA | light beige 505.908.97 | 500 x 500 mm | 100% cotton, cotton velvet | yes |
| Parents bed | C-cushion-parents-bed-2 | IKEA SANELA | dark brown 906.360.25 | 500 x 500 mm | 100% cotton (min. 20% recycled), cotton velvet | yes |
| Parents bed | C-cushion-parents-bed-3 | IKEA LAGERPOPPEL | light brown 905.618.07 | 400 x 580 mm | 100 % polyester (100% recycled) | yes |
| Living 3-seat sofa | C-throw-living-sofa | IKEA MYRULL | light grey 905.634.82 | 1300 x 1700 mm | 100% wool | yes |
| Lounge 4-seat sofa | C-throw-lounge-sofa | IKEA MYRULL | light grey 905.634.82 | 1300 x 1700 mm | 100% wool | yes |
| Study 2-seat sofa | C-throw-study-sofa | IKEA HOLMVI | grey 305.135.98 | 1200 x 1600 mm | 100% polyester (min. 90% recycled) | yes |
| Cinema 2-seat sofa | C-throw-cinema-sofa | IKEA HOLMVI | grey 305.135.98 | 1200 x 1600 mm | 100% polyester (min. 90% recycled) | yes |
| Library daybed | C-throw-library-daybed | IKEA MYRULL | light grey 905.634.82 | 1300 x 1700 mm | 100% wool | yes |
| Parents bed | C-throw-parents-bed | IKEA MYRULL | light grey 905.634.82 | 1300 x 1700 mm | 100% wool | yes |
| Parents bedroom rug (bedside runners; larger sizes not seen) | C-rug-parents-bedroom | IKEA TIDTABELL | beige 605.618.75 | 800 x 2000 mm | User surface 100% wool, warp 100% cotton | yes |

### Maintenance and durability (cited)

- **C-floor-living**: Durability claim from maker ([source](https://www.marazzi.it/en/mystone-gris-fleury)): "la tecnologia Tecnico garantisce la resistenza nel tempo"
- **C-floor-gf**: Underfloor heating suitability ([source](https://www.havwoods.com/uk/products/hw7470/)): "Suitable for floating over underlay Suitable for underfloor heating"
- **C-floor-wet**: Maker page states Tecnico improves grip and slip resistance; no numeric rating ([source](https://www.marazzigroup.com/collections/mystone-limestone20-collection/)): "Tecnico technology improves reliability, grip and slip resistance."
- **C-worktop**: Stain resistance ([source](https://www.specifiedby.com/ivett-reed/eternal-marquina)): "Silestone is non-porous and highly resistant to stains from coffee, wine, lemon juice, olive oil, vinegar and many other products."
- **C-garden-paving**: 20 mm outdoor version ([source](https://www.marazzi.it/en/mystone-gris-fleury)): "La collezione è disponibile anche in 20mm per gli esterni."

## Draft views (living from the north v33, kitchen island n02, parents' bedroom n13)

**NOT YET RENDERED.** The GPU graphics locks were held by an external `HOLD-RAG` process (`~/archpipe/locks/HOLD-RAG.txt`, held since 2026-11-22 23:23, a `sleep` loop outside the queue), so jobs `L4-pipe-A-3`, `L4-pipe-B-3`, `L4-pipe-C-3` sit in `waiting_lock`. They are submitted and will run unattended once the lock is released (each: palette scene -> re-measure exposure groups, because materials are transport inputs -> render the 3 views at 96 spp, 1920x1280; output `out/L4/<P>/views/`). Nothing below describes a view I have seen. The earlier attempts failed on a wrong IES directory and then on CUDA out-of-memory with the GPU shared.

## Recommendation (provisional, from boards and sources, not from the views)

**Palette A, Travertine & Walnut.** Reasons: (1) it is the closest to the client's stated taste (warm contemporary 42 %, large-format stone 22 mentions, walnut 12) and to the existing design, so integration changes the least; (2) the floor is porcelain in a travertine look (Marazzi Mystone Travertino), which keeps the look and avoids natural travertine's sealing and etching upkeep in a hot, wet-room-heavy house; (3) the light cream floor (look-alike reflectance about 0.6) and warm white walls (Dulux Antique White, LRV 84) keep the lower-ground level bright, where C's taupe walls (LRV 27) would not; (4) walnut at 2700 K / CRI 90 is the client's own choice. Costs: Egypt availability of A's hard finishes is unconfirmed (only IKEA soft goods are); B has the one Egyptian-made floor (Ceramica Cleopatra) and a lighter feel, so if local supply decides, B's floor tile can be swapped into A. Rejected: C (dark walls cut the lighting; wet-room tile has no stated slip rating); B (calmer but furthest from the stated glam/warm-contemporary taste).

## Open items
1. Render and look at the 9 draft views (queued), then revise this section if they disagree.
2. Egypt supply for hard finishes (a distributor call for Marazzi, Egger, Kahrs, Caesarstone/Cosentino, FENIX; or Egyptian equivalents).
3. LRV for non-paint finishes (maker data sheets), slip ratings (DIN 51130 / BS 7976) for wet-room tiles, Martindale for cushion fabrics (IKEA does not state).
4. Kitchen backsplash geometry does not exist in the scene (RF open item); the backsplash appears on the boards only.
5. Cushion props are the shared `throw_pillows_01` model: the palette renders swap the pillow, throw and rug materials, not per-sofa cushion models; sofa upholstery materials are unchanged.
6. Integration of the chosen palette into the production scene is a later lane.


---

# Round 2 (2026-11-23): the client's finish mix applied to the production scene

Client choice and lead-confirmed proposals: `docs/decisions/interior-presentation-2026-11-22.md`, "Client palette choice (2026-11-23)". Schedule: `knowledge/products/finishes/chosen.json` (generated by `scripts/build_chosen.py` from palettes B and C; never hand-edited; no prices).
Loader and consistency checks: `src/archpipe/interior/chosen.py`. Scene wiring: `villa_render.py` (`CHOSEN`, `FINISH`, `part_material`, `RUG_MATERIAL`, `SOFA_SCHEDULE`), `src/archpipe/interior/soft_dressing.py`.

## Chosen schedule (48 slots, 30 rooms)

| slot | product (look-alike, labelled; texture scale from the product format) | drives (scene material) | rooms |
|---|---|---|---|
| floor-basement | C Marazzi Mystone Gris Fleury Taupe RT 60x120 (ambientCG Marble007, 1.2 m) | `travertine` | all basement rooms except the cinema |
| floor-gf | C Havwoods Venture Cantal Smoked Cocoa oak (WoodFloor041, 2.35 m) | `oak-floor` | GF circulation, study, kids A/B, parents' bedroom, entry, dressing |
| floor-wet / wall-tile-wet | C Marazzi Mystone Limestone20 Taupe 60x120 (Concrete012, 1.2 m) / Grande Marble Look Frappuccino 120x120 (Marble015, 1.2 m) | `marble-wet` / `marble-bath`, `marble-ensuite` | guest bathroom, family bathroom, en-suite (and the shower) |
| wall-paint-main | B Dulux Off White, LRV 89 (flat colour) | `plaster-warm-white` | all basement and GF rooms except the wet rooms and the cinema |
| wall-feature-parents | C Dulux Nile Clay, LRV 27 (flat) | `fin-wall-feature` | parents' bedroom head wall, behind the bed only |
| worktop | B Cosentino Dekton Nacre (Marble025, 3.27 m slab) | `marble-white` | kitchen island, run, laundry counter |
| backsplash | B Cosentino Dekton Nacre | none | **no backsplash zone in the design model: not built** |
| kitchen-front | B FENIX 0719 Beige Luxor (flat) | `greige-lacquer` | kitchen zone only |
| kitchen-joinery | B EGGER H1180 Natural Halifax Oak (white_oak_veneer, 0.5 m) | `fin-kitchen-joinery(-x)` | island carcass |
| joinery-timber | C EGGER H3180 Brown Halifax Oak (Wood051, 0.8 m) | `walnut`, `-grain-x`, `-grain-y` | TV wall, sideboards, bookcases, vanities, parents' wardrobes, stair |
| joinery-light | C EGGER H1180 Natural Halifax Oak (white_oak_veneer, 0.5 m) | `oak`, `oak-grain-x` | wardrobes, desks, bed frames, headboard slats |
| door | C Durian Trace Smoke Oak (Wood049, 0.8 m) | `door-oak` | every door leaf |
| cushions, throws, rugs | C IKEA SANELA / LAGERPOPPEL / MYRULL / HOLMVI / BRÖNDEN / TIDTABELL (colours from the maker's colour names, ESTIMATES) | `fin-cushion-<sofa>-<n>`, `fin-throw-<sofa>`, `fin-rug-*` | living, lounge, study, cinema sofas, library daybed, parents' bed; living, lounge, parents' rugs (kids A rug = the living rug) |
| open-shelf objects, books, garments | C | none | chosen, **not applied**: the scene has no such assets to colour |

## Decisions I took (listed, all reversible)

1. **GF walls other than the feature wall are B Off White.** The client's "rest of the house follows C" has no whole-wall C paint: C's only paint is Nile Clay (LRV 27), which its own item says is for feature walls. Off White keeps the GF light and matches the basement. Needs a client yes.
2. **Cinema and the stair void keep their design finishes** (acoustic fabric walls and carpet; the stair void has no finish layer): recorded as `retained` with a reason, not assigned a palette slot.
3. **The basement service rooms** (pantry, store under the ramp, dirty kitchen) take the basement floor and wall as before (they shared the open plan's stone).
4. **Kitchen joinery uses the light-oak look-alike.** B's joinery-timber slot names the same EGGER product but its look-alike (oak_veneer_01) rendered salmon in the first draft; the product is identical, the proxy is the better match.
5. **Backsplash not built.** `grep` of the model and the furnish layer finds only the brief's K-SPLASH 600 mm clearance target, no zone or element. Reported, not invented.
6. **Garden paving (C) not applied**: outside the client's list, and lanes GI and LG own the garden.
7. **Product format replaces RF's assumed 0.6 m texture policy for the chosen finishes** (`tests/test_villa_render_texture_scale.py`: product-derived materials must equal `finishes.texture_scale_m`, density floor 400 px/m for large formats; the assumed policy still guards everything else).
8. **Mounting finish tables accept `fin-wall-feature`** (`fitting_mounting.py`, `exterior_mounting.py`): it is paint on the same interior-plaster build-up, so the lead-approved mounting schedule is unchanged.
9. The dressing room's drawer fronts (garments.py) were `greige-lacquer` (the kitchen front's name): now `walnut-grain-x`, the parents' joinery.

## Defect found in the first draft and its guard (defect-learning)

* `chosen-stone-grain-axis`: the first `chosen.json` forced `grain_axis: "z"` on every textured slot, and a floor quad is thin in z, so the Box projection sampled one texel row: the Gris Fleury floor rendered as horizontal stripes in v33, v34, n01, n03 (draft `L4-draft-1`). I looked at the images before any change; the cause is the documented `grain.mapping_rotated_span` class (stair treads, 2026-09-28), and it was missed because the schedule's own tests checked the file, not the geometry it ends up on. Guard: `tests/interior/test_scene_finishes.py::FinishLayers` builds the scene and fails any finish layer whose grain rotation collapses a coordinate (compared with the identity mapping so narrow strips are not flagged); its negative control is the REAL lounge floor with the grain axis the first file used.
* The first feature wall was a 3 mm overlay at the structural face and sat inside the plaster finish layers (invisible in n13). The wall colour is now set on the shell face, so `finish_layers.py` inherits it; guard `test_scene_finishes.py::FeatureWall`.
* The first sofa cushions sat behind the library sofa's tall back cushions (v33). The model's seat top, back-cushion face and arm width are now measured from its mesh and used when a model replaced the procedural sofa.

## Production scene: receipts, exposure, hashes (no bypass)

* Merged `origin/integ/aplus` (`60ed0fe`: GI, RF, HY, LG). Took theirs for `knowledge/furniture-stage2.json.gz`, `parents-bed.json.gz` and both exposure records, then regenerated on top (RA method, baseline-relative): old tree = `origin/integ/aplus` in a git worktree, **reproduces all 8 stored section digests**; section diff (`knowledge/approvals-review/evidence-l4/section-diff.json`): layout, specification, furniture, models, props unchanged; **materials** 14 changed ids (the finishes' look-alikes) + 27 `fin-*` added, 0 removed; **meshes** 9 added (the scheduled cushions and throws in the cinema, the study and on the parents' bed) and 2 changed (`rug-kids-a`, `rug-parents-bed`, material); **architecture** 48 finish-layer faces removed / 48 added, **0 unexplained** (wet-room floor layers 18 + 18; the parents' head-wall plaster layers 30 + 30 now carrying the feature colour). `refresh_receipts.py` writes `refresh_2026_11_23_L4` beside the earlier records. `review-current`: **16 individual + joint reviews, all ok, 0 findings** (receipts regenerated four times as fixes landed; the last for the final cushion geometry). The parents' bed cloth spec changed (the scheduled throw): disclosed in the note; the cloth is re-simulated at render.
* Exposure re-measured on the final tree through the documented procedure (`write(measure_exposure_groups=True)` / `render_set.write_scene(measure=True)`, ERCO IES assembled from `knowledge/lighting-products`, Blender `villa_scene.py --measure-exposure-groups`), jobq **`L4-measure-prod-6`** and **`L4-measure-set-6`**, each with a NEW id because the materials and geometry changed (ids `-prod-1..5` and `-set-1..5` were superseded by tree changes; `-set-1` and `-prod-5` died, one of GPU out-of-memory when two jobs ran together, one OOM-killed by host RAM while my parallel test chunks ran: do not run big test batches beside measurement). Copied byte for byte. **No membership change** against the integ records (production: evening 15, exterior-day 11, day 9, exterior-shade 5, lamp-dominant 3, lamp-low-key 1, exterior-dusk 1, exterior-dusk-dim 1; render set: evening 19, day 13, exterior-day 5, lamp-dominant 4, exterior-shade 2, lamp-low-key 1, dusk 1, dusk-dim 1).
* Scene hashes (built clean at `60718a1`, `git_dirty` false, receipts and records active; full record `knowledge/render-set/l4/scene-hashes.json`):

| scene | bytes | sha256 | content sha256 (ids and provenance stripped) | meshes / views |
|---|---|---|---|---|
| production (`villa_render.write`) | 260,973,574 | `c55c9eff5d721bdad03f81e4b2677e241a5aa81344574bfc6bc73510c25a8eba` | `cb2d2a984a45d3da5761dfed17827d4d09998af7d5797f668c8e1429924edb1f` | 1,226 / 46 |
| render set (`render_set.write_scene`) | 261,014,022 | `a43e993a31bea4ea0f002485abcfc6d560457476348eeecc2160bf83275f3931` | `602dc5ff914a7e2d97dda4c8b5ca66c78a2e133b1820d90a5686b2f53ae49f61` | 1,226 / 46 |

`source_hash` `6354e121...`; receipts `furniture-stage2` room_context `6e8be36d53359c59`, `parents-bed` `3d71d6c05e41d8fe`; exposure measurement hashes production `54d22795...`, set `3026a0a2...`. The file hash includes provenance (the checkout); the content hash does not. The images were rendered from a render-set scene whose content hash equals the final build's.

## Renders (draft, 96 spp, 1920 x 1280, GPU through jobq `L4-draft-4` with the scene cache `a7918642...`; JPEGs at 1500 px in `knowledge/render-set/l4/draft/`, PNGs in `out/L4/draft/`)

I looked at every image (v33, v34, n13, v05, n03 in the final pass; n01, n02, n15, n16, v06 in the previous pass, their finishes and scene content unchanged since, only the cushion geometry differs). What each shows, honestly:

* **v33 basement north-south**: the Gris Fleury floor reads as a veined taupe stone at tile scale (no stripes); walls Off White (grey-beige in shade); dark Brown Halifax bookcases and TV wall; the library sofa carries three scheduled cushions (a landscape lumbar in peach-tan at the left arm, dark green, dark brown) and a white-grey folded throw. **Seen face-on the cushions still read as flat rounded boards, and the throw as a flat white block**; the critic still says "flat, rigid rectangles" here (R8 1).
* **v34 basement south-north**: same floor and sofa from behind. The dark backs of the cushions still peek a few centimetres above the sofa back (much less than the first pass's 10-15 cm). The right 10 % of the frame is the dark TV-wall/door edge (critic R10 0, a camera item, not a finish). Off White walls and curtains read well.
* **n02 kitchen island**: Dekton Nacre worktop reads as a pale veined slab; island fronts are Natural Halifax Oak (blond, wavy grain); the day group's blue cast is pre-existing, not changed here.
* **n03 kitchen run**: marble-look floor, blond oak island, white Dekton worktops, beige FENIX front on the run; the far sofa shows cushions. The best of the set (critic pass).
* **n13 parents' bedroom by day**: **the Nile Clay feature wall is visible behind the bed** (a light taupe in daylight) with the oak slats over it, Durian smoke-oak door, Brown Halifax desk. The three scheduled cushions (dark brown, tan SANELA, cream bouclé-like lumbar) now read as plump rounded cushions (critic: "soft, rounded forms"). Bed pillows white (the library bed's own). Headboard and desk are unchanged models.
* **v05 parents' bedroom (evening)**: Nile Clay reads as a deep taupe-brown, the smoke-oak door nearly black, cushions soft and believable, a plain taupe throw at the foot (critic pass).
* **n15 and n16 en-suite**: **the Frappuccino taupe walls read as a deep copper-brown** in 2700 K light (stated colour `#b8a58e`, reflectance 0.39, an ESTIMATE from the colour name; the room's warm bounce saturates it). Both rooms are dark, far darker than the old cream marble. A client decision about the colour or the room lighting belongs here.
* **n01 dining (day)**: Gris Fleury floor, Brown Halifax table, chairs and sideboard (dark, heavy), the living sofa's cushions behind. The dining end is much darker than the old walnut-on-cream scheme.
* **v06 kids room A (GF bedroom)**: Smoked Cocoa floor (very dark, reflectance 0.064), Natural Halifax Oak bunk and desks, Off White walls, the living rug product. The window is blown (physical; RF item 7).

## Critic (frozen-v1 rubric, VLM `L4-critic-vlm-3`, gates R8/R10/R11 plus the deterministic six; `knowledge/render-set/l4/critic-results.json`)

**2 pass (n03, v05), 8 fail** on the final renders (first pass with the slab cushions: 1 pass, 9 fail; before the merge also 1 / 9). n01 fail (R4 0: crushed shadows in the dark dining end); n02 fail (R12 0, the day group's blue cast); n13 fail (R4 0: window clipped 3.7 %, no VLM warning left); n15 fail (3 WARNs: bare room, flat shower head); n16 fail (4 WARNs); v06 fail (R4 0: window); v33 fail (R3 lean, R8 cushions "flat rigid rectangles"); v34 fail (R10 0: the dark right edge). None of the failures is a finish-colour finding; the cushion-shape finding was real and the inflated profile cleared it in the bedroom views. The critic is a noisy high-recall filter (RF, L9P).

## Open items
1. Render and look at the 9 draft views (queued), then revise this section if they disagree.
2. Egypt supply for hard finishes (a distributor call for Marazzi, Egger, Kahrs, Caesarstone/Cosentino, FENIX; or Egyptian equivalents).
3. LRV for non-paint finishes (maker data sheets), slip ratings (DIN 51130 / BS 7976) for wet-room tiles, Martindale for cushion fabrics (IKEA does not state).
4. Kitchen backsplash geometry does not exist in the scene (RF open item); the backsplash appears on the boards only.
5. Cushion props are the shared `throw_pillows_01` model: the palette renders swap the pillow, throw and rug materials, not per-sofa cushion models; sofa upholstery materials are unchanged.
6. Integration of the chosen palette into the production scene is a later lane.


---

# Round 2 (2026-11-23): the client's finish mix applied to the production scene

Client choice and lead-confirmed proposals: `docs/decisions/interior-presentation-2026-11-22.md`, "Client palette choice (2026-11-23)". Schedule: `knowledge/products/finishes/chosen.json` (generated by `scripts/build_chosen.py` from palettes B and C; never hand-edited; no prices).
Loader and consistency checks: `src/archpipe/interior/chosen.py`. Scene wiring: `villa_render.py` (`CHOSEN`, `FINISH`, `part_material`, `RUG_MATERIAL`, `SOFA_SCHEDULE`), `src/archpipe/interior/soft_dressing.py`.

## Chosen schedule (48 slots, 30 rooms)

| slot | product (look-alike, labelled; texture scale from the product format) | drives (scene material) | rooms |
|---|---|---|---|
| floor-basement | C Marazzi Mystone Gris Fleury Taupe RT 60x120 (ambientCG Marble007, 1.2 m) | `travertine` | all basement rooms except the cinema |
| floor-gf | C Havwoods Venture Cantal Smoked Cocoa oak (WoodFloor041, 2.35 m) | `oak-floor` | GF circulation, study, kids A/B, parents' bedroom, entry, dressing |
| floor-wet / wall-tile-wet | C Marazzi Mystone Limestone20 Taupe 60x120 (Concrete012, 1.2 m) / Grande Marble Look Frappuccino 120x120 (Marble015, 1.2 m) | `marble-wet` / `marble-bath`, `marble-ensuite` | guest bathroom, family bathroom, en-suite (and the shower) |
| wall-paint-main | B Dulux Off White, LRV 89 (flat colour) | `plaster-warm-white` | all basement and GF rooms except the wet rooms and the cinema |
| wall-feature-parents | C Dulux Nile Clay, LRV 27 (flat) | `fin-wall-feature` | parents' bedroom head wall, behind the bed only |
| worktop | B Cosentino Dekton Nacre (Marble025, 3.27 m slab) | `marble-white` | kitchen island, run, laundry counter |
| backsplash | B Cosentino Dekton Nacre | none | **no backsplash zone in the design model: not built** |
| kitchen-front | B FENIX 0719 Beige Luxor (flat) | `greige-lacquer` | kitchen zone only |
| kitchen-joinery | B EGGER H1180 Natural Halifax Oak (white_oak_veneer, 0.5 m) | `fin-kitchen-joinery(-x)` | island carcass |
| joinery-timber | C EGGER H3180 Brown Halifax Oak (Wood051, 0.8 m) | `walnut`, `-grain-x`, `-grain-y` | TV wall, sideboards, bookcases, vanities, parents' wardrobes, stair |
| joinery-light | C EGGER H1180 Natural Halifax Oak (white_oak_veneer, 0.5 m) | `oak`, `oak-grain-x` | wardrobes, desks, bed frames, headboard slats |
| door | C Durian Trace Smoke Oak (Wood049, 0.8 m) | `door-oak` | every door leaf |
| cushions, throws, rugs | C IKEA SANELA / LAGERPOPPEL / MYRULL / HOLMVI / BRÖNDEN / TIDTABELL (colours from the maker's colour names, ESTIMATES) | `fin-cushion-<sofa>-<n>`, `fin-throw-<sofa>`, `fin-rug-*` | living, lounge, study, cinema sofas, library daybed, parents' bed; living, lounge, parents' rugs (kids A rug = the living rug) |
| open-shelf objects, books, garments | C | none | chosen, **not applied**: the scene has no such assets to colour |

## Decisions I took (listed, all reversible)

1. **GF walls other than the feature wall are B Off White.** The client's "rest of the house follows C" has no whole-wall C paint: C's only paint is Nile Clay (LRV 27), which its own item says is for feature walls. Off White keeps the GF light and matches the basement. Needs a client yes.
2. **Cinema and the stair void keep their design finishes** (acoustic fabric walls and carpet; the stair void has no finish layer): recorded as `retained` with a reason, not assigned a palette slot.
3. **The basement service rooms** (pantry, store under the ramp, dirty kitchen) take the basement floor and wall as before (they shared the open plan's stone).
4. **Kitchen joinery uses the light-oak look-alike.** B's joinery-timber slot names the same EGGER product but its look-alike (oak_veneer_01) rendered salmon in the first draft; the product is identical, the proxy is the better match.
5. **Backsplash not built.** `grep` of the model and the furnish layer finds only the brief's K-SPLASH 600 mm clearance target, no zone or element. Reported, not invented.
6. **Garden paving (C) not applied**: outside the client's list, and lanes GI and LG own the garden.
7. **Product format replaces RF's assumed 0.6 m texture policy for the chosen finishes** (`tests/test_villa_render_texture_scale.py`: product-derived materials must equal `finishes.texture_scale_m`, density floor 400 px/m for large formats; the assumed policy still guards everything else).
8. **Mounting finish tables accept `fin-wall-feature`** (`fitting_mounting.py`, `exterior_mounting.py`): it is paint on the same interior-plaster build-up, so the lead-approved mounting schedule is unchanged.
9. The dressing room's drawer fronts (garments.py) were `greige-lacquer` (the kitchen front's name): now `walnut-grain-x`, the parents' joinery.

## Defect found in the first draft and its guard (defect-learning)

* `chosen-stone-grain-axis`: the first `chosen.json` forced `grain_axis: "z"` on every textured slot, and a floor quad is thin in z, so the Box projection sampled one texel row: the Gris Fleury floor rendered as horizontal stripes in v33, v34, n01, n03 (draft `L4-draft-1`). I looked at the images before any change; the cause is the documented `grain.mapping_rotated_span` class (stair treads, 2026-09-28), and it was missed because the schedule's own tests checked the file, not the geometry it ends up on. Guard: `tests/interior/test_scene_finishes.py::FinishLayers` builds the scene and fails any finish layer whose grain rotation collapses a coordinate (compared with the identity mapping so narrow strips are not flagged); its negative control is the REAL lounge floor with the grain axis the first file used.
* The first feature wall was a 3 mm overlay at the structural face and sat inside the plaster finish layers (invisible in n13). The wall colour is now set on the shell face, so `finish_layers.py` inherits it; guard `test_scene_finishes.py::FeatureWall`.
* The first sofa cushions sat behind the library sofa's tall back cushions (v33). The model's seat top, back-cushion face and arm width are now measured from its mesh and used when a model replaced the procedural sofa.

## Production scene: receipts, exposure, hashes (no bypass)

* Merged `origin/integ/aplus` (`60ed0fe`: GI, RF, HY, LG). Took theirs for `knowledge/furniture-stage2.json.gz`, `parents-bed.json.gz` and both exposure records, then regenerated on top (RA method, baseline-relative): old tree = `origin/integ/aplus` in a git worktree, **reproduces all 8 stored section digests**; section diff (`knowledge/approvals-review/evidence-l4/section-diff.json`): layout, specification, furniture, models, props unchanged; **materials** 14 changed ids (the finishes' look-alikes) + 27 `fin-*` added, 0 removed; **meshes** 9 added (the scheduled cushions and throws in the cinema, the study and on the parents' bed) and 4 changed (`furn-pb-bed-4/5` pillow material, `rug-kids-a`, `rug-parents-bed`); **architecture** 48 finish-layer faces removed / 48 added, **0 unexplained** (wet-room floor layers 18 + 18; the parents' head-wall plaster layers 30 + 30 now carrying the feature colour). `refresh_receipts.py` writes `refresh_2026_11_23_L4` beside the earlier records. `review-current`: **16 individual + joint reviews, all ok, 0 findings**. The parents' bed cloth spec changed (the scheduled throw): disclosed in the note; the cloth is re-simulated at render.
* Exposure re-measured on the final tree through the documented procedure (`write(measure_exposure_groups=True)` / `render_set.write_scene(measure=True)`, ERCO IES assembled from `knowledge/lighting-products`, Blender `villa_scene.py --measure-exposure-groups`, jobq **`L4-measure-prod-3`** and **`L4-measure-set-4`**, each with a NEW id because materials changed; earlier ids `-prod-1/-2`, `-set-1..3` were superseded by tree changes, and `-set-1` failed with GPU out-of-memory when two jobs ran together: later jobs ask `--vram-mb 16000`). Copied byte for byte. **No membership change** against the integ records (production: evening 15, exterior-day 11, day 9, exterior-shade 5, lamp-dominant 3, lamp-low-key 1, exterior-dusk 1, exterior-dusk-dim 1; render set: evening 19, day 13, exterior-day 5, lamp-dominant 4, exterior-shade 2, lamp-low-key 1, dusk 1, dusk-dim 1). The records' measurement hashes: production `d0da444a...`, set `99d02f57...`.

| scene (built clean at `5f5b962`, `git_dirty` false) | bytes | sha256 | content sha256 (ids and provenance stripped) | meshes / views |
|---|---|---|---|---|
| production (`villa_render.write`) | 260,442,031 | `ad5d9b07a4301b80278a6fc10118688e7074136f168214d093d074681a78c214` | `63c25fa037cd96ac3844b4062e448b739989dd1d788c791a88a151632d9d0aa0` | 1,226 / 46 |
| render set (`render_set.write_scene`) | 260,482,476 | `ea8cc13019bc44a5ee96289ba8f870ddf55f7d3e8aa759a5c36a56c66af2b135` | `153a67fca89b52ad020f002bad7ff7c9c2a8cd53666dfc7d384c05561d58e16c` | 1,226 / 46 |

`source_hash` `97b6cdba...`; receipts `furniture-stage2` room_context `26a7e26bf5423c9c`, `parents-bed` `b731cd03c52615c4`. The file hash includes provenance (the checkout); the content hash does not. The images were rendered from a render-set scene built one commit earlier; its content hash equals the final build's. Full record: `knowledge/render-set/l4/scene-hashes.json`.

## Renders (draft, 96 spp, 1920 x 1280, GPU through jobq `L4-draft-3` with the scene cache; JPEGs at 1500 px in `knowledge/render-set/l4/draft/`, PNGs in `out/L4/draft/`)

I looked at every image. What each shows, honestly:

* **v33 basement north-south** (`v33-basement-north-south`): the Gris Fleury floor now reads as a veined taupe stone at tile scale (no stripes); walls Off White (grey-beige in the shade); dark Brown Halifax bookcases and TV wall; the library sofa carries three scheduled cushions (peach-tan tall one at the left arm, dark green, dark brown) and a white-grey folded throw at the left arm. **The cushions read as stiff, chamfered slabs and the throw as a flat white block**; the critic says the same (R8). The cushions sit on the seat and against the back cushions as intended.
* **v34 basement south-north**: same floor and sofa seen from behind. **The cushions stand about 10-15 cm proud of the sofa back and show as dark flat panels over the back edge**; the right 10 % of the frame is the dark TV-wall/door edge (critic R10 0, a camera item, not a finish). The Dulux Off White walls and curtains read well.
* **n02 kitchen island**: Dekton Nacre worktop reads as a pale veined slab; the island fronts are Natural Halifax Oak (blond, wavy grain); the whole image has the day group's blue cast (a pre-existing exposure-group behaviour, not changed by this lane).
* **n03 kitchen run**: marble-look floor, blond oak island, white Dekton worktops, beige FENIX front on the run; the far sofa shows the cushions; the best of the set (critic pass).
* **n13 parents' bedroom by day**: **the Nile Clay feature wall is visible behind the bed** (a light taupe in daylight), oak slats over it, Durian smoke-oak door, Brown Halifax desk. Three scheduled cushions on the bed: dark brown, tan SANELA, cream bouclé-like LAGERPOPPEL stand-in. **They read as thick rigid blocks, large against the bed.** The bed pillows are white (the library bed's own). The headboard and desk are unchanged models.
* **v05 parents' bedroom (evening)**: Nile Clay reads as a deep taupe-brown at night, the smoke-oak door nearly black, cushions as above (slab-like), throw flat at the foot.
* **n15 and n16 en-suite**: **the Frappuccino taupe walls read as a deep copper-brown** in 2700 K light (stated colour `#b8a58e`, reflectance 0.39, an ESTIMATE from the colour name; the room's warm bounce saturates it). Both rooms are dark; the earlier cream marble was far lighter. A client decision about the colour or the room lighting belongs here.
* **n01 dining (day)**: Gris Fleury floor, Brown Halifax dining table, chairs and sideboard (dark, heavy), the living sofa's cushions behind. The dining end is now much darker than the old walnut-on-cream scheme.
* **v06 kids room A (GF bedroom)**: Smoked Cocoa floor (very dark, reflectance 0.064), Natural Halifax Oak bunk and desks, Off White walls, the living rug product. The window is blown (physical; RF item 7).

## Critic (frozen-v1 rubric, VLM `L4-critic-vlm-2`, gates R8/R10/R11 plus the deterministic six; `knowledge/render-set/l4/critic-results.json`)

**1 pass (n03), 9 fail.** Before the merge, on the same ten views, also 1 / 9 (n03 pass). n01 fail (R4 0: crushed 6.5 % in the dark dining end); n02 fail (R12 0 blue cast; 3 WARNs); n13 fail (R4 0: clipped 3.7 % at the window; 2 WARNs); n15 fail (3 WARNs: bare room, flat shower head); n16 fail; v05 fail (2 WARNs: R8 "pillows as flat, rigid, rectangular slabs", R11 sparse); v06 fail (R4 0 window); v33 fail (R3 lean 1.27 deg, R8 "green and brown pillows rigid flat blocks"); v34 fail (R10 0 right edge band). **The critic independently flags the cushions as rigid slabs in v33, v05 and n13: that is a real defect of mine, not noise.** The critic is a noisy high-recall filter (RF, L9P); nothing here is a finish-colour finding.

## Open items

1. **Cushion and throw shape (mine, visible):** after the inflated-profile fix the bed cushions read soft, but the sofa cushions still read as flat rounded boards face-on (v33) and the folded throws as flat blocks; a draped cloth throw (as the bed's) and a true inflated cushion mesh are the fix; any change re-opens receipts and exposure (the cushions are in receipt rooms), so it is a separate pass. In v34 the cushions' dark backs still stand a few cm above the library sofa back.
2. **Rug product sizes are not applied.** The rugs keep the design footprints (living 2.6 x 2.4, lounge 3.1 x 2.0, parents 2.2 x 2.6 m); the schedule products are BRÖNDEN 2.0 x 3.0 (living), 1.7 x 2.4 (lounge) and TIDTABELL 0.8 x 2.0 bedside runners. Material and colour are the product's; the size is a layout decision for the client. Kids A takes the living rug product.
3. **En-suite and bathrooms read dark copper-brown** under 2700 K light (n15, n16). Colour is an ESTIMATE from the maker's colour name (`render-colours.json`); a client colour sample, a lighter wall, or cooler bathroom light is the decision.
4. **GF walls = B Off White** is my decision (decision 1 above); needs a client yes.
5. **No backsplash zone in the design model**: the slot is chosen (B Dekton Nacre) but nothing is built; adding the zone is a design change (K-SPLASH 600 mm clearance, wall units only on tall runs).
6. **Chosen but not applied (no scene asset):** open-shelf objects, books, wardrobe garments (C), the sofas' own upholstery (not a palette slot), garden paving (not in the client's list).
7. **Products with no Egypt supplier found (`egypt.available: unknown`, no price):** Marazzi (floor-basement, floor-wet, wall-tile-wet: only a Dubai showroom reported), Havwoods Cantal (floor-gf), Dulux Australia Off White and Nile Clay (not Egypt products; Jotun Egypt colour matches would be needed), Cosentino Dekton (worktop, backsplash: Dubai hub), FENIX 0719 ("to be checked"), EGGER (kitchen joinery, joinery-timber, joinery-light: a third-party list shows an Egyptian EGGER agent, unverified), Durian door (an Indian maker). Books (Rizzoli) and garments (UNIQLO) not checked. The 27 IKEA soft items are available through IKEA Egypt.
8. **Texture scale is the product format** (Marazzi 120 cm, Dekton slab 3.27 m, Havwoods plank 2.35 m): one look-alike image per format unit, so the worktop and the plank read soft at close range (400-630 px/m). A measured sample would replace the look-alike.
9. n02 keeps the day group's blue cast and the windows stay blown by day (RF items, not finishes).


---

# Round 3 (2026-11-23): render-fidelity fixes (lead findings on the applied drafts)

## 1. Colours now come from the makers' own images (cause, fix, evidence)

* **Cause.** Every finish colour in `render-colours.json` (and the soft-goods `NAME_HEX` table) was an estimate from the maker's colour NAME. The lead read the en-suite as a "flat dark copper-brown" and expected a light beige marble. **The maker's own image says the premise was wrong: Marazzi Grande Marble Look Frappuccino (M0G3) is a dark brown marble** (the maker's alt text on the page: "gres porcellanato marrone scuro"; sampled mean `#514238`, luma 0.060). The flatness had a different cause: the look-alike was `Marble015`, a near-uniform cream (luma spread cv 0.02) against the maker's strongly veined slab (cv 0.78), so a dark tint on it gave a flat panel. The product stays (client's choice); the colour and the look-alike change.
* **Fix.** `scripts/source_maker_colours.py` downloads the maker's swatch (or product photo, backdrop masked) and samples the mean colour in linear space (`src/archpipe/interior/maker_colour.py`), recording the URL, sha256, mode and luma spread in `render-colours.json` (images are the makers' and are cached, not committed). Dulux publishes the hex on the colour page ("Hex" row), used as published. `scripts/build_chosen.py` writes the source into every slot (`colour_source`). **Guard:** `interior/chosen.py::colour_problems` (run by `problems()` and `tests/interior/test_chosen.py::MakerColour`) fails any chosen product without a maker-sourced colour; the one documented gap is `UNSOURCED` (below). The look-alike pattern guard fails a look-alike whose luma spread is outside 0.25 to 4 times the maker image's; its negative control is the real defect (Marble015 vs M0G3 is 39 times off).
* **Items whose colour was a name-based estimate, all now sampled (48 chosen products; before and after):**

| item | product | before (name-based estimate) | now (maker image, mean linear) | method | maker image / page |
|---|---|---|---|---|---|
| C-floor-living | Marazzi Taupe | #a39786 | #aca29b | swatch | https://www.marazzi.it/app/uploads/collezioni/mystone-gris-fleury-mlgy/marazzi_mystone_gris_fleury_mlgy-800x400.jpg |
| C-floor-gf | Havwoods Smoked Cocoa (colour group Cocoa) | #5a4332 | #3f3326 | swatch | https://res.cloudinary.com/havwoods-global/image/upload/ar_1.4429824561403508,c_fill,g_center,w_1479/f_auto/q_auto/v1721144786/image_%7C_hw7470_%7C_panel_%7C_photo.jpg |
| C-floor-wet | Marazzi Taupe | #a09484 | #aa9e8e | swatch | https://www.marazzigroup.com/app/uploads/collezioni/mystone-limestone20-m7sq/marazzi_mystone_limestone20_m7sq.jpg |
| C-bath-tile | Marazzi Frappuccino | #b8a58e | #514238 | swatch | https://www.marazzigroup.com/app/uploads/collezioni/grande-marble-look-m0g3/marazzi_grande_marble_look_m0g3-800x800.jpg |
| B-wall-paint | Dulux (Australia) Off White | #efebe3 | #f9f1e1 | published-hex | https://www.dulux.com.au/specifier/colour/whites-sw1/off-white |
| C-wall-paint | Dulux Australia Nile Clay | #8b8074 | #8b8074 | published-hex | https://www.dulux.com.au/specifier/colour/s13/nile-clay/ |
| B-worktop | Cosentino Nacre | #e2d9cb | #ded4c0 | swatch | https://assetstools.cosentino.com/api/v1/bynder/color/CKC/detalle/CKC-thumb.jpg?w=700&h=700&auto=compress%2Cformat |
| B-backsplash | Cosentino Nacre | #e2d9cb | #ded4c0 | swatch | https://assetstools.cosentino.com/api/v1/bynder/color/CKC/detalle/CKC-thumb.jpg?w=700&h=700&auto=compress%2Cformat |
| B-kitchen-front | FENIX Beige Luxor | #cdc0a8 | #b0a187 | swatch | https://res.cloudinary.com/dozlb75sf/image/upload/v1679331548/FENIX%20Colours/Thumb/FENIX_0719_BEIGE_LUXOR_thumb_eloyrz.jpg |
| B-joinery-light | EGGER Natural Halifax Oak | #c0a27a | #ba9c77 | swatch | https://cdn.egger.com/img/pim/8854365372446/8854523117598/original.png |
| C-joinery-timber | EGGER Brown Halifax Oak | #4b3626 | #735a42 | swatch | https://cdn.egger.com/img/pim/8860203974686/8860204007454/original.png |
| C-joinery-light | EGGER Natural Halifax Oak | #b08e62 | #ba9c77 | swatch | https://cdn.egger.com/img/pim/8854365372446/8854523117598/original.png |
| C-door | Durian Smoke Oak | #4a3c32 | #4a3c32 | - | - |
| C-cushion-living-sofa-1 | IKEA dark brown | #4a3426 | #362b24 | product | https://www.ikea.com/eg/en/images/products/sanela-cushion-cover-dark-brown__1502335_pe1007600_s5.jpg |
| C-cushion-living-sofa-2 | IKEA dark green | #3d4a36 | #2a3328 | product | https://www.ikea.com/eg/en/images/products/sanela-cushion-cover-dark-green__1502326_pe1007596_s5.jpg |
| C-cushion-living-sofa-3 | IKEA light brown | #b8987a | #a9795a | product | https://www.ikea.com/eg/en/images/products/lagerpoppel-cushion-cover-light-brown__1259129_pe926539_s5.jpg |
| C-cushion-lounge-sofa-1 | IKEA dark green | #3d4a36 | #2a3328 | product | https://www.ikea.com/eg/en/images/products/sanela-cushion-cover-dark-green__1502326_pe1007596_s5.jpg |
| C-cushion-lounge-sofa-2 | IKEA dark grey | #4a4a48 | #4f4f51 | product | https://www.ikea.com/eg/en/images/products/sanela-cushion-cover-dark-grey__1284674_pe933082_s5.jpg |
| C-cushion-lounge-sofa-3 | IKEA yellow-brown | #b88a4a | #a3763b | product | https://www.ikea.com/eg/en/images/products/sanela-cushion-cover-yellow-brown__1502327_pe1007597_s5.jpg |
| C-cushion-study-sofa-1 | IKEA dark brown | #4a3426 | #362b24 | product | https://www.ikea.com/eg/en/images/products/sanela-cushion-cover-dark-brown__1502335_pe1007600_s5.jpg |
| C-cushion-study-sofa-2 | IKEA light beige | #d9ccb4 | #d5cab8 | product | https://www.ikea.com/eg/en/images/products/sanela-cushion-cover-light-beige__1284678_pe933086_s5.jpg |
| C-cushion-cinema-sofa-1 | IKEA dark grey | #4a4a48 | #4f4f51 | product | https://www.ikea.com/eg/en/images/products/sanela-cushion-cover-dark-grey__1284674_pe933082_s5.jpg |
| C-cushion-cinema-sofa-2 | IKEA dark brown | #4a3426 | #362b24 | product | https://www.ikea.com/eg/en/images/products/sanela-cushion-cover-dark-brown__1502335_pe1007600_s5.jpg |
| C-cushion-library-daybed-1 | IKEA yellow-brown | #b88a4a | #a3763b | product | https://www.ikea.com/eg/en/images/products/sanela-cushion-cover-yellow-brown__1502327_pe1007597_s5.jpg |
| C-cushion-library-daybed-2 | IKEA light brown | #b8987a | #a9795a | product | https://www.ikea.com/eg/en/images/products/lagerpoppel-cushion-cover-light-brown__1259129_pe926539_s5.jpg |
| C-cushion-parents-bed-1 | IKEA light beige | #d8ccb6 | #d5cab8 | product | https://www.ikea.com/eg/en/images/products/sanela-cushion-cover-light-beige__1284678_pe933086_s5.jpg |
| C-cushion-parents-bed-2 | IKEA dark brown | #4a3426 | #362b24 | product | https://www.ikea.com/eg/en/images/products/sanela-cushion-cover-dark-brown__1502335_pe1007600_s5.jpg |
| C-cushion-parents-bed-3 | IKEA light brown | #b8987a | #a9795a | product | https://www.ikea.com/eg/en/images/products/lagerpoppel-cushion-cover-light-brown__1259129_pe926539_s5.jpg |
| C-throw-living-sofa | IKEA light grey | #c4c1ba | #b2ada2 | product | https://www.ikea.com/eg/en/images/products/myrull-throw-light-grey__1187183_pe899082_s5.jpg |
| C-throw-lounge-sofa | IKEA light grey | #c4c1ba | #b2ada2 | product | https://www.ikea.com/eg/en/images/products/myrull-throw-light-grey__1187183_pe899082_s5.jpg |
| C-throw-study-sofa | IKEA grey | #8a8a88 | #9f9f9e | product | https://www.ikea.com/eg/en/images/products/holmvi-throw-grey__1022849_pe832952_s5.jpg |
| C-throw-cinema-sofa | IKEA grey | #8a8a88 | #9f9f9e | product | https://www.ikea.com/eg/en/images/products/holmvi-throw-grey__1022849_pe832952_s5.jpg |
| C-throw-library-daybed | IKEA light grey | #c4c1ba | #b2ada2 | product | https://www.ikea.com/eg/en/images/products/myrull-throw-light-grey__1187183_pe899082_s5.jpg |
| C-throw-parents-bed | IKEA light grey | #bdbab3 | #b2ada2 | product | https://www.ikea.com/eg/en/images/products/myrull-throw-light-grey__1187183_pe899082_s5.jpg |
| C-rug-living | IKEA beige | #cdbd9f | #dccfc5 | product | https://www.ikea.com/eg/en/images/products/broenden-rug-low-pile-handmade-beige__0804523_pe769465_s5.jpg |
| C-rug-lounge | IKEA beige | #c9b89a | #dccfc5 | product | https://www.ikea.com/eg/en/images/products/broenden-rug-low-pile-handmade-beige__0804523_pe769465_s5.jpg |
| C-rug-parents-bedroom | IKEA beige | #c9b89a | #e1d8c3 | product | https://www.ikea.com/eg/en/images/products/tidtabell-rug-flatwoven-beige__1185186_pe898305_s5.jpg |
| C-object-vase | IKEA dark grey-beige | #4a4a48 | #867974 | product | https://www.ikea.com/eg/en/images/products/stilren-vase-dark-grey-beige__1450873_pe990482_s5.jpg |
| C-object-bowl-brown | IKEA brown | #6b4a35 | #5f4e48 | product | https://www.ikea.com/eg/en/images/products/stockholm-2025-bowl-brown__1387524_pe964281_s5.jpg |
| C-object-bowl-beige | IKEA beige | #c9b89a | #b0a38f | product | https://www.ikea.com/eg/en/images/products/stockholm-2025-serving-bowl-beige__1387533_pe964285_s5.jpg |
| C-book-wearstler-evocative | Rizzoli Kelly Wearstler: Evocative | none (look-alike own mean) | #a29372 | product | https://images.penguinrandomhouse.com/cover/9780847866038 |
| C-book-wearstler-synchronicity | Rizzoli Kelly Wearstler: Synchroni | none (look-alike own mean) | #c6c3bd | product | https://images.penguinrandomhouse.com/cover/9780847873425 |
| C-book-van-duysen-private | Rizzoli Vincent Van Duysen: Privat | none (look-alike own mean) | #a79073 | product | https://images.penguinrandomhouse.com/cover/9780847899555 |
| C-book-loyzaga | Rizzoli Jorge Loyzaga: Classical a | none (look-alike own mean) | #8b7f6d | product | https://images.penguinrandomhouse.com/cover/9780847873678 |
| C-garment-merino-olive | UNIQLO Olive | #6b6a3f | #948153 | swatch | https://image.uniqlo.com/UQ/ST3/WesternCommon/imagesgoods/469426/chip/goods_56_469426_chip.jpg |
| C-garment-merino-grey | UNIQLO Grey | #8a8a88 | #737376 | product | https://image.uniqlo.com/UQ/ST3/WesternCommon/imagesgoods/450514001/item/goods_06_450514001_3x4.jpg |
| C-garment-linen-trouser | UNIQLO OLIVE | #6b6a3f | #6f7663 | swatch | https://image.uniqlo.com/UQ/ST3/WesternCommon/imagesgoods/463857/chip/goods_57_463857_chip.jpg |
| C-garment-merino-crew | UNIQLO GRAY | none (look-alike own mean) | #99999e | product | https://image.uniqlo.com/UQ/ST3/WesternCommon/imagesgoods/429066/item/goods_03_429066_3x4.jpg |

* **`C-door` (Durian Trace, Smoke Oak) is the one product still on its name-based estimate**: `durian.in` returns Cloudflare 522 to curl and to the browser tool, the Wayback Machine would not connect, and the brochure PDFs do not list Trace. It is a lead-confirmed slot, recorded in `chosen.UNSOURCED` with the reason; `tests/interior/test_chosen.py::MakerColour` pins that set to exactly this one id so it cannot grow silently. Run `scripts/source_maker_colours.py` when the site answers (add its image to `SWATCH`) and empty `UNSOURCED`.
* **The sourced colours moved some finishes noticeably:** Smoked Cocoa is much darker than estimated (`#3f3326`, luma 0.036 against the old 0.062); the Natural Halifax Oak joinery is lighter and yellower; the Dekton Nacre worktop is lighter. The IKEA/UNIQLO fabrics are sampled from the product photo's foreground.

## 2. Look-alikes checked against the makers' images

| slot | maker image shows | look-alike | verdict |
|---|---|---|---|
| wall-tile-wet (Frappuccino) | dark brown marble, broad flowing bands, cream veins, cv 0.78 | was `Marble015` (cream, cv 0.02) | **swapped to `Marble011`** (grey-brown, white veins, cv 0.36, colour ratio 1:0.79:0.62 against the maker's 1:0.67:0.48). A first swap to `Marble008` had the right pattern but is orange (1:0.55:0.25) and per-channel matching turned its cream veins lilac in the render |
| floor-gf (Smoked Cocoa oak) | clean wide plank, fine grain, bevelled seams, very dark | was `WoodFloor041` (knotty rustic boards in mixed light and dark tones) | **swapped to Poly Haven `laminate_floor_02`** (clean oak planks with seams, CC0, 1.7 m scan; colour 1:1:1.01 of the maker's). Plank tone comes from the maker's swatch, not the look-alike |
| floor-basement (Gris Fleury) | fine speckled grey-taupe aggregate, cv 0.19 | `Marble007` (cloudy brown with dark blotches, cv 0.16) | kept; pattern scale and contrast agree, not an aggregate. The terrazzo candidates (`Terrazzo019*`) have chips that are too big |
| floor-wet (Limestone20 taupe) | speckled stone, cv 0.12 | `Concrete012` (cv 0.09) | kept |
| worktop (Dekton Nacre), kitchen joinery (Halifax oak) | near-uniform cream (cv 0.03); blond oak with wavy grain (cv 0.26) | `Marble025`; `white_oak_veneer` | kept; per-material pattern contrast now stretches the look-alike to the maker's spread (clamped 0.5 to 2) |

## 3. Throws and cushions

* **Cause.** `soft_dressing.py` lofted every cushion from seven rounded-rectangle rings (a flat plateau) and every throw as a three-layer slab.
* **Fix.** Cushions are now an inflated closed shell (rounded-rectangle thickness profile, corner pinch, centre dimple, bowed cover, small wrinkles; 3,600 triangles); throws are a closed cloth shell (rolled rim, soft ridges, seeded wrinkle field) from the same module. The products, formats, schedule and placement are unchanged. The bed throw stays the existing Blender cloth simulation (`drape_cloth`), the same pipeline as the duvet. `src/archpipe/drape*.py` are garment cloth (wardrobe hangers) and do not apply to a throw on a sofa, so I did not force them.
* **Guard.** `tests/interior/test_scene_finishes.py::SoftGeometry`: closed (every edge shared by two faces), outward normals, real volume, not a few planes.
* **Evidence (looked at).** n13 and v05: cushions read as plump pillows (critic R8 2 in v05; in n13 the critic's R8 1 is about the bed's own pillows and the wall lamps). v33: critic R8 now **2** (it was 1, "flat rigid rectangles"). **The sofa throw still reads as a flat pale folded slab with a wavy top edge seen face-on from v33** (honest limit: no real cloth simulation on the sofas; a simulated throw over the library model needs invisible seat colliders and is the next step).

## 4. Dark rooms (n01 dining, v06 kids' room): not a finish defect

Mean relative luminance of the render (linear, Rec. 709 weights, `scripts/mean_luminance.py`, 96 spp, 1920 x 1280):

| view | before the finishes (`60ed0fe`, old cream stone + walnut) | first finishes draft (name-based estimates) | final (maker colours, `L4-r4-draft-1`) |
|---|---|---|---|
| n01 dining, day | 0.1744 | 0.1834 | **0.1842** |
| v06 kids' room A | 0.2237 | 0.2499 | **0.2452** |

The mean is not lower with the finishes (n01 +6 %, v06 +10 %), because the exposure groups compensate and the walls stay Off White. What the eye reads as darker is the large dark masses (the Brown Halifax table, chairs and sideboard in n01; the Smoked Cocoa floor, whose sourced luma is 0.036, in v06): this is the true look of the chosen finishes, not a defect. The exposure groups **were** re-measured on the final tree (new jobq ids below). Membership changes against the previous record: render set n15 evening -> lamp-low-key and n16 lamp-dominant -> lamp-low-key (the dark marble absorbs the lamp light, so those rooms are exposed longer; they are now properly lit), production v01 lamp-dominant -> day. n01 and v06 do not change group.

## Production scene, receipts, exposure, hashes (no bypass)

* Merged `origin/integ/aplus` (nothing new since the last merge). Receipts regenerated baseline-relative twice (once for the colours and geometry, once after the Marble011 swap): old tree `e348c08` reproduces all 8 stored digests; section diff (`knowledge/approvals-review/evidence-l4/section-diff.json`): layout, specification, furniture, architecture, models and props unchanged; materials 40 changed ids, 0 added, 0 removed; meshes 9 changed ids (the cushions and throws on the cinema and study sofas and the parents' bed), 0 added, 0 removed; the parents' bed cloth specs unchanged. `review-current`: 16 individual + joint reviews, 0 findings. The second refresh's section diff against `e348c08` reports "RECEIPT-DIFFERS-FROM-OLD-TREE" only because the stored receipt is by then the first refresh.
* Exposure: jobq `L4-r4-measure-prod-1` and `L4-r4-measure-set-1` (new ids; the earlier `L4-r3-measure-*` pair was superseded by the Marble011 swap), copied byte for byte.
* Renders: jobq `L4-r4-draft-1` (96 spp, scene cache), JPEGs at 1500 px in `knowledge/render-set/l4/draft/`; critic VLM jobq `L4-r4-critic-vlm-2`, `knowledge/render-set/l4/critic-results.json`: **3 pass (n01, n03, v05), 7 fail** (R4 clipped window in n13, n16, v06; n02 blue cast R12; n15 and v34 framing and bare-room WARNs; v33 R12/R3 WARNs). None is a finish-colour finding.
* Scene hashes (built clean at the commit in `knowledge/render-set/l4/scene-hashes.json`, `git_dirty` false, receipts and records active, no bypass): production `39a8174d84a1202e...` (272,995,744 bytes, content `d00d565b...`), render set `3d19c10687e463e8...` (273,036,203 bytes, content `2c46884b...`), 1,226 meshes, 46 views; receipts `furniture-stage2` room_context `e9532d04871c53e5`, `parents-bed` `3ad6955d132b45d9`; exposure measurement hashes production `eb49f806...`, set `eb0b9fbb...`. The images were rendered from a scene whose provenance-stripped content hash equals the final build's.
