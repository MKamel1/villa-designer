# LDL pass 4 (2026-11-22): free sources, procedural proposal, rescales

Client finds Botaniq too expensive. Licences were read from the vendors' own pages on 2026-11-22 (quotes below). Nothing needing an account was downloaded and no account was created.

## 1. Sources: licence verdict and what each covers

| source | licence verdict | covers our 13 gap species? | state |
|---|---|---|---|
| **Fab / Quixel Megascans** | **PASS, engine-agnostic.** Fab EULA summary: "Use the assets commercially or privately"; "Use the assets with any compatible tools (usage is not limited to Unreal Engine)"; "Commercially distribute your Projects with the Fab assets incorporated into it"; may not "Resell or redistribute the asset for free on a standalone basis". Both Personal and Professional tiers "grant you the same scope of rights". Some listings are CC-BY instead (read per listing). Megascans became free again in Nov 2026 (CG Channel 2026-11, Digital Production 2026-11-13). | **Yes, 4 of 13 and 5 more genus-level**: Rosemary (Rosmarinus), Oregano (title only; the species is presumably Origanum vulgare, not stated), Red Fountain Grass (Pennisetum), Cast-Iron Plant (= Aspidistra elatior); plus lawn grass, clover, periwinkle, ivy, taro, water lilies, fan/lady palms, aloe, canna. 26 free 3D listings with FBX+glTF in `knowledge/landscape/plants/free-candidates-fab.json`. Preview images of Rosemary, Oregano and Red Fountain Grass were looked at: real scanned plants, several variants each, not stylised. | **BLOCKED on an Epic Games account** (see client actions). Not graded: our rubric needs our own 5 m/15 m renders of the file. |
| **BlenderKit / Blendkit** | PASS: "Everything you download is available for commercial use"; Royalty Free "allows commercial use without mentioning the author, but doesn't allow for re-sale of the asset in the same form"; CC0 also offered. Engine-agnostic. | **No.** Anonymous search API: jasmine 10 results, 0 free; rosemary/oregano/salvia 0 free; Petrea, Acorus, Fatsia, Pittosporum, Bougainvillea 0 results at all. Free items are generic "Shrub", "Grass", "Hedge". | Download needs a (free) account and API key: STOP. Not worth creating for our species. |
| **CGTrader free** | CONDITIONAL: licence is per listing; free items can carry editorial or restrictive terms; T&C 19.2 forbids crawling free items. | **No** free listing for any gap species found (Pittosporum, Fatsia, Jasminum, Bougainvillea exist only paid, $5-$49). | Needs login. Skipped. |
| **TurboSquid free** | PASS for royalty-free listings ("3D Models are royalty free unless otherwise noted"), **REJECT any listing labelled Editorial Use** ("may not be used for any commercial, promotional, advertising or merchandising use"). | **No** free listing for a gap species found (Pittosporum $5-$10). | Needs login. Skipped. |
| **Smithsonian 3D (Open Access, CC0)** | PASS (CC0). | **No.** 1,937 3D models via the Open Access API; plant hits are fossil leaves (e.g. *Aralia kellingtoniana*), none of our species. | Nothing to download. |
| **Poly Haven (again)** | PASS (CC0). | **No.** 57 plant models; the newest (Nov 2024) are Namaqualand succulents and pine-forest items; none of our species. Useful: CC0 bark textures (used by the prototype). | nothing new to take. |
| **GrabCAD** | REJECT for plants: CAD/mechanical library, site returns 403 to automated clients and has no botanical content; licences are per model. | No. | skipped |
| **Graswald (free since 2024)** | licensed for commercial use (CG Channel) | No: temperate European ground cover. Site unreachable from this machine (connection fails). | skipped |
| **BD3D The Plant Library (free)** | Royalty Free, usable only with Geo-Scatter/Biome-Reader for the biome files; plants "licensed for use in commercial projects" | No: temperate lawns, forest floor, ferns. Needs a Blender Market account. | skipped |
| **Blender add-ons: BagaPie free modifier; Sapling Tree Gen** | BagaPie *modifier* is free (GPL/MIT) but its plant *assets* are a paid Royalty Free pack ($39/$93). Sapling Tree Gen is a GPL add-on that grows trees from parameters; its output geometry is ours. | No species; Sapling makes tree skeletons, not herbs or shrubs with sourced leaves. | not used |

Rejected outright: anything NC/ND, Editorial-only, or engine-locked (none of the passing sources is engine-locked; the old Megascans/UEFN "Reference only" licence appears on some listings, read the licence list on each listing before use; the Personal/Professional tiers are what the Rosemary, Oregano and Red Fountain Grass listings showed).

## 2. Procedural route: feasibility proposal (not a build)

Prototype: *Pittosporum tobira*, `src/archpipe/landscape/plants/proto_shrub.py` (Blender 4.5, seeded Python mesh generation; ~277k tris, 7.7k obovate leaf meshes, 700 shoot tips, 3 stems). Sheet: `knowledge/landscape/plants/asset-previews/proto_pittosporum_tobira.jpg` (jobq `ldl-p4-proto1` v1, `ldl-p4-proto2` v2; 5 m top row, 15 m bottom row, azimuths 0/90/180/270).

Inputs, all sourced: height 2.4-4.0 m, spread 1.2-2.4 m, "dense, compact ... sympodial" and "Rounded" (NC State Plant Toolbox, https://plants.ces.ncsu.edu/plants/pittosporum-tobira/); leaves obovate, entire, leathery, darker and shinier above, to 10 cm (Wikipedia, *Pittosporum tobira*); CC0 textures: ambientCG Leaf001 (leaf surface), Poly Haven bark_brown_01 (bark). Reference photo looked at: Wikimedia Commons "Pittosporum tobira - Flickr - peganum.jpg" (CC BY-SA 2.0): leaves in whorls at shoot tips, glossy dark green, terminal flower clusters.

**Grade: C** (rubric: fails at 5 m). Looked at:
* v1 was a lollipop: bare stems to 2.3 m, hollow crown. Fixed by lowering the stems and sampling shoot tips through the whole ellipsoid.
* v2 reads as a dense rounded dark evergreen shrub of the right size at 15 m (would be B at that distance). At 5 m it fails: the straight radial twigs make a sea-urchin or umbrella-rib pattern, leaves foreshortened to thin spikes at the tips, no foliage mass hiding the structure, no flowers. A reviewer would call it a model of a shrub, not a Pittosporum.
* It is not a Poly-Haven-grade scan and was not made to look like one.

Findings that matter for the decision:
* **CC0 leaf textures are the weak link, not geometry.** ambientCG Leaf001/003 are toothed or pinnate single leaves; no CC0 texture for entire-margined glossy leaves (Pittosporum, Fatsia lobes, Aspidistra blades, Alpinia) exists. Outline must come from our own mesh and colour from a generic leaf. Species identity therefore rests on shape + habit alone.
* Poly Haven has bark and ground but no leaf textures; Smithsonian has none.

**Effort for the full list** (my estimate; one shrub family per day by one person after a shared branching/whorl kit exists):
* Shared kit: hierarchical branching with curvature and tapering, leaf-library with per-species outline masks (alpha cards or meshes), wind-free instancing, 5 m / 15 m QA hook: 3-4 days.
* Per species: Pittosporum, Jasminum sambac, Justicia, Petrea (climber needing a trellis-fitting rule), Bougainvillea (thorny climber with bracts), Fatsia (palmate leaves), Aspidistra and Acorus and Alpinia (basal blades/canes), Pennisetum (grass tuft), Salvia leucantha (spikes) , Origanum and Rosmarinus (small herbs): 0.5-2 days each, about 12-15 days; flowers add 0.5 day per flowering species.
* Lawn and groundcover drifts: scatter on ground with CC0 grass textures; 2 days. Total roughly 20-25 working days.

**Expected grade**: B for foliage-dominated shrubs and basal-leaf herbs (Fatsia, Aspidistra, Alpinia, Pittosporum, Acorus, Pennisetum); C-to-B for flowering climbers and spray shrubs (Petrea, Bougainvillea, Jasminum, Justicia, Salvia), A for none. At best a scan-quality A is not reachable by this route.

**Risks**: species fidelity judged by shape only (no CC0 leaf for entire-margin leaves); evergreens look plasticky without leaf variation and subsurface; flowering state is seasonal and unsourced for appearance; effort is large against free scans; the C at 5 m shows the first-pass failure mode (visible skeleton) will recur until the kit has real branching.

**Recommendation**: do not start the procedural build first. The Megascans route (once an Epic account exists) gives photoscanned Rosemary, Oregano, Red Fountain Grass and Cast-Iron Plant (4 of 13) at no cost and no build; procedural remains the fallback for the other 9 (Jasminum, Petrea, Justicia, Acorus, Alpinia, Fatsia, Pittosporum, Salvia leucantha, Bougainvillea) and for species-faithful flowers.

## 3. Rescales applied (lead-approved)

Placement scale = mid sourced height / authored height, recorded as `placement_scale` and `placed_height_m` in `assets.json`; rendered again at that scale and looked at (jobq `ldl-p4-scaled`):
* **Papyrus** `skf3_d0248242`: 18.545 m authored, sourced 1.5-2.4 m: scale **0.105** -> 1.95 m tall, 0.70 x 0.78 m. Looked at: real papyrus stalks with thread umbels, reads at 5 m; one clump is thin at 15 m, so place in groups of 3 or more. **C -> B, drawable.**
* **Alocasia macrorrhizos** `skf3_75882b72`: authored 2.8 m tall but 6.3 m wide (the earlier "9.5 m" note was not the height; the file's stats are 6.1 x 6.3 x 2.8 m). Sourced height 1.5-2.5 m: scale **0.7135** -> 2.0 m tall, 4.4 m wide, a clump of several plants. Already B and drawable; the scale is now recorded. The lead's quoted "0.3" would give 0.84 m, below the sourced minimum, so the sourced height was used instead.
* Guard: `assets.validate_assets` fails if `placed_height_m` is not `size_m[2] x placement_scale`; test `test_placed_assets_match_sourced_height_and_inconsistent_scale_fails` also checks the placed heights lie in the sourced range.

## Client actions

1. **Create a free Epic Games account** (epicgames.com) and sign in at fab.com. Then add the 26 listings in `free-candidates-fab.json` ("Add to My Library", price 0), starting with Rosemary, Oregano, Red Fountain Grass, Cast-Iron Plant. Download glTF (or FBX) for each into `~/archpipe/shared/assets/user/landscape/fab/<listing uid>/` on ai-workstation and tell the lead; the lane then grades them at 5 m / 15 m. The lane cannot do this: Fab downloads need a signed-in account and no account was created.
2. Nothing is needed for BlenderKit (not worth it for our species), CGTrader or TurboSquid.
