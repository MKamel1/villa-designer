# Phase coverage and acquisition

This framework covers design and visualization for private villas. Hotel
references inform comfort and appearance. Permits, construction
administration and engineering certification are outside scope, and so is
tailoring to one jurisdiction. The basis is published **UK and US practice,
with several sources cross-checked**. Where they disagree, both values are
recorded and the choice is explained by applicability. “A+ luxury” is the
client's agreed quality brief, not a certification.

Every expert judgement must rest on a source that has been obtained and
read. A title in this list is only *identified*. A rule becomes usable for
approval only when the passage was read from the held edition and a
regression test exists (see the [rule audit](rule-audit.md)).

| Stage | Package | Deliverables | Usable evidence now | Sources that unlock numbers |
|---|---|---|---|---|
| 0 Intent | [Method](stages/0-intent.md) | quality_brief, design_direction, taste_profile | yourhome-brief, yourhome-cost, norm-copenhagen | problem-seeking |
| 1 Ground | [Method](stages/1-ground.md) | site_constraints, climate_summary, landscape_strategy | yourhome-orientation, yourhome-shading | cairo-epw, br209, lechner-hcl, site-analysis |
| 2 Fit | [Method](stages/2-fit.md) | area_schedule, cost_assumptions, tradeoffs | aia-phases, yourhome-cost | metric-handbook, neufert, spons |
| 3 Order | [Method](stages/3-order.md) | three_concepts, facade_strategy, recommendation, independent_critique | aia-phases, yourhome-orientation, yourhome-noise | precedents-in-architecture, floor-plan-manual, form-space-order, studio-companion, msd-dataset |
| 4 Rooms | [Method](stages/4-rooms.md) | dimensioned_rooms, furniture_access, opening_schedule | aia-phases, yourhome-light, yourhome-noise | neufert, metric-handbook, human-dimension, residential-interior-design, nkba-guidelines, uk-ad-m, uk-ad-k |
| 5 Systems | [Method](stages/5-systems.md) | comfort_schedule, window_study, lighting_schedule, coordinated_ceiling, consultant_handoff | yourhome-light, yourhome-shading | ies-rp11, en17037, cibse-tm59, uk-ad-o, lbnl-igdb |
| 6 Substance | [Method](stages/6-substance.md) | material_board, finish_schedule, ffe_schedule, junction_details, planting_schedule | yourhome-noise, yourhome-cost | materials, construction-illustrated, id-reference-spec, landscape-timesaver |
| 7 Proof | [Method](stages/7-proof.md) | coordinated_presentation, requirements_trace, acoustic_check, open_issue_log | aia-phases, norm-copenhagen | bs8233, acoustics |

## How to obtain

1. Buy the Tier 1 titles first. Save each file into
   `C:\Users\mmbka\archpipe-sources\inbox\`. This folder sits outside the
   repository and is never committed.
2. Buy **unlocked** PDF or EPUB. If checkout mentions Kindle, VitalSource,
   Adobe DRM, FileOpen or Locklizard, the tool cannot read the file: buy
   print and scan the pages requested. A watermark is fine.
3. Run `python scripts/sources.py intake`. It files each readable copy
   under its registry id and marks it *held*. It reports:
   - locked or unreadable files;
   - files it cannot match. Rename those to the id, for example `neufert.pdf`.
4. The curator then reads the title and copyright pages (making the source
   *content_verified*) and writes evidence cards with page locators.
5. Deferred, not bought: ventilation design (ASHRAE 62.2) and MEP
   coordination go to consultants, and the hospitality lighting RP is
   superseded by RP-11.

The list below is generated from [library.json](../../knowledge/library.json)
by `python scripts/sources.py list`. Edit the registry, not this table.

<!-- purchase-list:begin -->
### To buy

**Tier 1** (about $1,675)

| Id | Title | Edition | What it unlocks | ≈ USD |
|---|---|---|---|---|
| `br209` | Paul Littlefair et al.: BR 209 Site layout planning for daylight and sunlight: a guide to good practice | 3 (2022) | sunlight-to-garden and overshadowing checks at concept stage | 80 |
| `cibse-tm59` | CIBSE: [TM59: Overheating risk in dwellings - a design stage methodology](https://www.cibse.org/knowledge-research/knowledge-portal/tm59-overheating-risk-in-dwellings-a-design-stage-methodology-2026/) | 2026 | the overheating gate for window and shading decisions | 120 |
| `en17037` | BSI / CEN: BS EN 17037:2018+A1:2021 Daylight in buildings | 2018+A1:2021 | daylight targets for every habitable room | 350 |
| `floor-plan-manual` | Oliver Heckmann and Friederike Schneider (eds.): [Floor Plan Manual Housing](https://birkhauser.com/books/9783035611496) | 5 | precedent plans and typology catalogue for concept generation | 90 |
| `form-space-order` | Francis D. K. Ching: [Architecture: Form, Space, and Order](https://www.wiley-vch.de/en?isbn=9781119853374&option=com_eshop&view=product) | 5, ISBN 9781119853374 | spatial order, circulation, proportion and organizing principles | 60 |
| `human-dimension` | Julius Panero and Martin Zelnik: Human Dimension & Interior Space | 1979 | furniture clearance checks (FURN-02, walkways, seating) | 45 |
| `ies-rp11` | Illuminating Engineering Society / American Lighting Association: [ANSI/IES/ALA RP-11-26 Recommended Practice: Lighting for Interior and Exterior Residential Environments](https://webstore.ansi.org/standards/iesna/ansiiesalarp1126) | RP-11-26 | residential lighting targets for every room (replaces the hospitality RP) | 150 |
| `lechner-hcl` | Norbert M. Lechner and Patricia Andrasik: [Heating, Cooling, Lighting: Sustainable Design Strategies Towards Net Zero Architecture](https://www.wiley.com/en-us/Heating%2C+Cooling%2C+Lighting%3A+Sustainable+Design+Strategies+Towards+Net+Zero+Architecture%2C+5th+Edition-p-9781119585749) | 5, ISBN 9781119585749 | window, shading and passive-cooling design rules for the thermal study | 110 |
| `metric-handbook` | Pamela Buxton (ed.): [Metric Handbook: Planning and Design Data](https://www.routledge.com/Metric-Handbook-Planning-and-Design-Data/Buxton/p/book/9780367511395) | 7, ISBN 9780367511395 | UK cross-check for every room, door, stair and circulation dimension | 90 |
| `neufert` | Ernst Neufert: [Architects’ Data](https://www.wiley-vch.de/en?isbn=9781119873945&option=com_eshop&view=product) | 6, ISBN 9781119873945 | dwelling areas, doors, furniture dimensions, circulation and all associated notes | 120 |
| `nkba-guidelines` | National Kitchen & Bath Association: [Kitchen & Bath Planning Guidelines with Support Spaces and Accessibility](https://nkba.org/planning-guidelines/) | 5 (2023/24) | kitchen and bathroom layout checks (aisles, landing areas, clearances) | 100 |
| `pattern-language` | Christopher Alexander and collaborators: [A Pattern Language](https://www.patternlanguage.com/) | 1977 | actual pattern passages; contents numbering alone does not verify claims | 60 |
| `precedents-in-architecture` | Roger H. Clark and Michael Pause: Precedents in Architecture: Analytic Diagrams, Formative Ideas, and Partis | 4, ISBN 9780470946749 | method for encoding the precedent corpus behind concept design | 60 |
| `problem-seeking` | William M. Peña and Steven A. Parshall: [Problem Seeking](https://www.wiley-vch.de/en?isbn=9781118152935&option=com_eshop&view=product) | 5, ISBN 9781118152935 | programming process, goals, facts, needs and problem statements | 70 |
| `residential-interior-design` | Maureen Mitton and Courtney Nystuen: [Residential Interior Design: A Guide to Planning Spaces](https://www.wiley.com/en-us/Residential+Interior+Design%3A+A+Guide+to+Planning+Spaces%2C+4th+Edition-p-9781119653424) | 4, ISBN 9781119653424 | room-level interior planning rules for every villa room | 80 |
| `studio-companion` | Edward Allen and Joseph Iano: [The Architect’s Studio Companion](https://www.wiley-vch.de/en?isbn=9781119826798&option=com_eshop&view=product) | 7, ISBN 9781119826798 | preliminary structural systems and service-zone planning | 90 |

**Tier 2** (about $2,825)

| Id | Title | Edition | What it unlocks | ≈ USD |
|---|---|---|---|---|
| `analysing-architecture` | Simon Unwin: Analysing Architecture | latest | concept analysis vocabulary | 50 |
| `ashrae-fundamentals` | ASHRAE: ASHRAE Handbook - Fundamentals | latest | cooling-load method cross-check | 330 |
| `ashrae55` | American Society of Heating, Refrigerating and Air-Conditioning Engineers: [Standard 55: Thermal Environmental Conditions for Human Occupancy](https://www.ashrae.org/technical-resources/standards-and-guidelines/titles-purposes-and-scopes) | to verify | comfort scope, methods, assumptions and exceptions | 120 |
| `cibse-guide-a` | CIBSE: Guide A: Environmental design | latest | thermal model inputs (gains, comfort, U-values) | 300 |
| `construction-illustrated` | Francis D. K. Ching: [Building Construction Illustrated](https://www.wiley-vch.de/en?isbn=9781394279272&option=com_eshop&view=product) | 7, ISBN 9781394279272 | envelope transitions, openings and junctions | 60 |
| `daylighting-handbook` | Christoph Reinhart: Daylighting Handbook I and II | 2014 / 2018 | daylight simulation method and validation | 90 |
| `id-reference-spec` | Chris Grimley and Mimi Love: The Interior Design Reference & Specification Book | 2 | FF&E and finish specification data | 45 |
| `ies-handbook` | Illuminating Engineering Society: The Lighting Handbook | 10 | lighting depth and cross-check | 550 |
| `interior-illustrated` | Francis D. K. Ching and Corky Binggeli: [Interior Design Illustrated](https://www.wiley-vch.de/en?isbn=9781119377207&option=com_eshop&view=product) | 4, ISBN 9781119377207 | room planning, furnishings and dimensional context | 60 |
| `landscape-timesaver` | Charles W. Harris and Nicholas T. Dines: Time-Saver Standards for Landscape Architecture (+ a dry-climate planting guide) | 2 | landscape dimensions and plant selection | 170 |
| `lighting-design-basics` | Mark Karlen, Christina Spangler and James R. Benya: Lighting Design Basics | 3 | lighting layering method | 70 |
| `materials` | Corky Binggeli: [Materials for Interior Environments](https://www.wiley-vch.de/en?isbn=9781118306352&option=com_eshop&view=product) | 2, ISBN 9781118306352 | moisture exposure, durability, cleaning and finish selection | 90 |
| `site-analysis` | James A. LaGro Jr.: [Site Analysis](https://www.wiley-vch.de/en?isbn=9781118123676&option=com_eshop&view=product) | 3, ISBN 9781118123676 | site inventory, analysis and suitability | 90 |
| `sll-code` | Society of Light and Lighting: SLL Code for Lighting (2022) and SLL Lighting Handbook (2018) | 2022 / 2018 | UK lighting cross-check | 350 |
| `spons` | AECOM (ed.): Spon's Architects' and Builders' Price Book (or RSMeans Residential Cost Data) | latest | relative cost comparison at every gate | 250 |
| `sun-wind-light` | Mark DeKay and G. Z. Brown: [Sun, Wind, and Light](https://www.wiley-vch.de/en?isbn=9781118332887&option=com_eshop&view=product) | 3, ISBN 9781118332887 | climate-responsive strategies and limits | 90 |
| `time-saver-interior` | Joseph De Chiara, Julius Panero and Martin Zelnik: Time-Saver Standards for Interior Design and Space Planning | 2 | interior dimension cross-check | 110 |

**Tier 3** (about $505)

| Id | Title | Edition | What it unlocks | ≈ USD |
|---|---|---|---|---|
| `acoustics` | Marshall Long: [Architectural Acoustics](https://shop.elsevier.com/books/architectural-acoustics/long/978-0-12-398258-2) | 2, ISBN 9780123982582 | sound paths, isolation and room acoustic design | 120 |
| `bs8233` | BSI: BS 8233:2014 Guidance on sound insulation and noise reduction for buildings | 2014 | acoustics end-check targets | 330 |
| `japanese-house` | Heinrich Engel: The Japanese House: A Tradition for Contemporary Architecture | any | Japanese style profile basis | 40 |
| `praise-of-shadows` | Jun'ichirō Tanizaki: In Praise of Shadows | any | Japanese style profile basis | 15 |

### Free: fetched by the tool (or you, if the site blocks tools)

**Tier 1**

| Id | Title | Edition | What it unlocks | ≈ USD |
|---|---|---|---|---|
| `icc-irc-2024` | International Code Council: [International Residential Code](https://codes.iccsafe.org/content/IRC2024P1) | 2024 | US residential cross-check | free |
| `lbnl-igdb` | Lawrence Berkeley National Laboratory: [International Glazing Database + WINDOW](https://windows.lbl.gov/software-tools) | latest | real glazing properties for the thermal model and glazing library | free |
| `msd-dataset` | C. van Engelenburg et al.: [Modified Swiss Dwellings (MSD) floor-plan dataset](https://data.4tu.nl/datasets/e1d89cb5-6872-48fc-be63-aadd687ee6f9) | ECCV 2024 | statistical priors (adjacency, proportions) for the concept generator | free |

**Tier 2**

| Id | Title | Edition | What it unlocks | ≈ USD |
|---|---|---|---|---|
| `cubicasa5k` | CubiCasa: CubiCasa5k floor-plan dataset | 2019 | additional detached-house plan priors | free |

Paid total about **$5,005** (prices approximate; confirm at checkout).
<!-- purchase-list:end -->

## Also missing, and not solved by books

- Real site survey, statutory envelope and brief interview (client).
- Exterior and landscape style references (client). The interior images are
  an oversampling target, not rules.
- Glare, HVAC, electrical, plumbing, structure and permits. These go to
  consultants. See the method's hand-off package.
