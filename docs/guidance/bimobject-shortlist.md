# BIMobject shortlist: families to add through the BIMobject app

**Purpose:** to get real manufacturer Revit families (with dimensions,
connection points and often photometry) into the library. You add them in
the BIMobject desktop app, which puts them into Revit. Then:
1. `revit/unattended.py` loads each family headlessly, and
   `archpipe.rfa` screens it first.
2. The product library records it as a **product** with
   `manufacturer-supplied` geometry.
3. The same checks as the luminaires run: the family loads, its category is
   right, and its bounding box matches the datasheet.

Search these in the app, and add the families that fit each role. The
brands are well-known European and US makers that ship worldwide. Nothing is
tailored to Egypt: the design states intent, and the closest local
equivalent is sourced at procurement.

**Where to save the files:** BIMobject's default download folder is fine.
Tell me the path, or copy the `.rfa` files into
`C:\Users\mmbka\arch-pipeline\sources\bim\`. That folder is git-ignored, and
the import files them by manufacturer.

## Priority 1: bathroom (the brief's "Modern Sanctuary" ensuite)

| Role | Search | Brands to prefer |
|---|---|---|
| Wall-hung WC with concealed cistern | "wall hung WC" + "concealed cistern" / "installation frame" | Geberit (Duofix frames), Duravit, Villeroy & Boch, Laufen, TOTO |
| Flush plate, brushed brass or black | "flush plate" | Geberit, Grohe |
| Floating vanity / wide trough basin | "trough basin", "vanity unit" | Duravit, Villeroy & Boch, Laufen, Kohler |
| Freestanding or Japanese-style soaking tub | "freestanding bath", "soaking tub" | Duravit, Kaldewei, Villeroy & Boch, Victoria + Albert |
| Walk-in shower tray / linear drain | "linear drain", "shower channel" | Geberit (CleanLine), ACO, Kaldewei |
| Brassware in brushed brass (taps, shower, thermostat) | "basin mixer", "concealed thermostat", "rain shower" | Grohe (Essence/Atrio), Hansgrohe/AXOR, Gessi, Vola |

## Priority 2: kitchen (the brief's "Culinary Sanctuary")

| Role | Search | Brands |
|---|---|---|
| Undermount single-bowl sink | "undermount sink" | Blanco, Franke |
| Pull-down tap, matte black or brushed brass | "pull-down kitchen mixer" | Grohe, Blanco, Franke |
| Freestanding side-by-side fridge (niche sizing) | "side by side refrigerator" | Samsung, LG, Bosch, Siemens |
| Oven, hob, hood, dishwasher | "built-in oven", "induction hob", "dishwasher 60" | Bosch, Siemens, Miele, Gaggenau |

## Priority 3: lighting (fills the Signify gap: warm residential pendants and profiles)

| Role | Search | Brands |
|---|---|---|
| Matte-black pendants over nightstands and the island | "pendant", filtered to lighting | Louis Poulsen, Flos, &Tradition, Artemide, Delta Light |
| Glass globe pendant clusters (dining) | "globe pendant" | Flos, Bocci, &Tradition |
| LED profiles and strips (coves, shelves, toe-kicks, mirrors) | "LED profile", "linear" | Delta Light, Linea Light, iGuzzini |
| Recessed deep-baffle downlights, 2700–3000 K | "recessed downlight" | ERCO, iGuzzini, Delta Light, Flos (architectural) |
| Brushed-brass vertical sconces (vanity) | "wall light" | Astro, Flos, Louis Poulsen |

Where a family comes with an IES/LDT file, keep it next to the `.rfa`. The
luminaire import verifies the photometry the same way as for Signify.

## Priority 4: joinery, doors and furniture

| Role | Search | Brands |
|---|---|---|
| Pivot or flush doors, concealed hinges | "pivot door", "flush door" | Rimadesio, Häfele, FritsJurgens (pivots) |
| Wardrobe systems (mirrored doors, internal fittings) | "wardrobe" | Häfele, Poliform, Rimadesio |
| Sofas, dining and lounge chairs | "sofa", "dining chair" | Vitra, Fritz Hansen, HAY, Muuto, &Tradition, Carl Hansen |

## What I do with them

The families you add are imported and checked, and recorded as products with
alternates. The design then picks two products from different ranges for
each role, the same Stage 5 rule used for lighting. I keep BIMobject
geometry, not free look-alikes, for anything that gets scheduled.
