# C2 asset intake: phase 1 checkpoint

## Record and validator

`src/archpipe/asset_intake.py` defines one 3D model record. Required fields are `id` (unique identifier), `role` (intended use), `source_url` (origin page), `licence` (reuse permission), `author`, `credit` (attribution), `units_normalised` (positive scale factor applied to native coordinates and its reason), `up_axis` (native vertical direction), `front_axis` (native facing direction), `bounds_m` (file-measured minimum and maximum coordinates in metres), `expected_size_range` (minimum and maximum width, height and depth in metres with a catalogue or held-book citation), `contents` (role-specific flags), and `preview_image` (review image path). The letters X, Y and Z name the model's three coordinate directions; glTF means Graphics Library Transmission Format. A directional role needs a measured or lead-verified front axis; `none` requires a reason for a nondirectional role. A bed needs bedding, and a plant needs a pot or root ball. Allowed licences are Creative Commons Zero (CC0), Creative Commons Attribution (CC-BY) with credit, and free tier. The validator checks all fields, scaled extents against the cited range, and local file bounds against the record within 0.005 m.

## Real manifest findings

The scope of this geometric record is the 62 `props` entries in `ops/workstation/library-manifest.json`. Texture sets (37) and environment maps (7) need medium-specific measurements and remain outside this 3D model schema. The manifest was not changed.

Every row below also lacks these six required fields: `source_url` (the old `url` alias is insufficient), `units_normalised` (scale factor and reason), `up_axis`, `expected_size_range` (three extents and a cited source), `contents`, and `preview_image`. The `Additional violations` column names all other missing fields and semantic violations.

| Asset ID | Additional violations |
|---|---|
| `book_encyclopedia_set_01` | licence, author, credit, front |
| `alarm_clock_01` | licence, author, credit, front |
| `brass_vase_03` | licence, author, credit, front |
| `potted_plant_04` | licence, author, credit, front |
| `potted_plant_01` | licence, author, credit, front |
| `throw_pillows_01` | licence, author, credit, front |
| `potted_plant_02` | licence, author, credit, front |
| `pachira_aquatica_01` | licence, author, credit, front |
| `calathea_orbifolia_01` | licence, author, credit, front |
| `anthurium_botany_01` | licence, author, credit, front |
| `ceramic_vase_01` | licence, author, credit, front |
| `ceramic_vase_03` | licence, author, credit, front |
| `decorative_book_set_01` | licence, author, credit, front, bounds |
| `wooden_bowl_01` | licence, author, credit, front |
| `hanging_picture_frame_01` | licence, author, credit, front |
| `hanging_picture_frame_02` | licence, author, credit, front |
| `standing_picture_frame_01` | licence, author, credit, front |
| `shrub_01` | licence, author, credit, front |
| `shrub_03` | licence, author, credit, front |
| `planter_box_01` | licence, author, credit, front |
| `jacaranda_tree` | licence, author, credit, front |
| `tree_small_02` | licence, author, credit, front |
| `searsia_lucida` | licence, author, credit, front |
| `grass_medium_01` | licence, author, credit, front |
| `grass_medium_02` | licence, author, credit, front |
| `flower_gazania` | licence, author, credit, front |
| `periwinkle_plant` | licence, author, credit, front |
| `wild_rooibos_bush` | licence, author, credit, front |
| `shrub_02` | licence, author, credit, front |
| `shrub_04` | licence, author, credit, front |
| `boulder_01` | licence, author, credit, front |
| `namaqualand_stones_01` | licence, author, credit, front |
| `sf_bauhinia` | front |
| `sf_bottlebrush` | front |
| `sf_bougainvillea` | front |
| `sf_chelsea_bed` | none beyond common fields |
| `sf_cinema_sofa_velvet` | none beyond common fields |
| `sf_dining_chair_boucle` | none beyond common fields |
| `sf_egg_chair` | front, direction |
| `sf_frangipani` | front |
| `sf_garden_flower_clump` | front |
| `sf_hibiscus` | front |
| `sf_ixora` | front |
| `sf_jacaranda` | front |
| `sf_kidschair_oak` | none beyond common fields |
| `sf_lavender_clump` | front |
| `sf_lemon_tree` | front |
| `sf_minotti_aston_armchair` | front, direction |
| `sf_minotti_sofa` | none beyond common fields |
| `sf_modern_low_sofa` | none beyond common fields |
| `sf_olive_old` | front |
| `sf_probber_cane_armchair` | none beyond common fields |
| `sf_royal_poinciana` | front |
| `sf_rug_round_jute` | none reason |
| `sf_wooden_bench` | front, direction |
| `outdoor_table_chair_set_01` | author, credit, front, direction |
| `flower_ursinia` | author, credit, front |
| `flower_heliophila` | author, credit, front |
| `didelta_spinosa` | author, credit, front |
| `modern_arm_chair_01` | author, credit |
| `mid_century_lounge_chair` | author, credit, front, direction |
| `desk_lamp_arm_01` | author, credit, front, direction |

## Re-measurement and observed anomalies

All 23 locally present Sketchfab glTF files under `out/villa/round3/stage-props` were re-measured from their node-transformed mesh bounds. None disagreed with the recorded bounds by more than 0.005 m. The other 39 model files are not locally available and require lead/workstation re-measurement before approval. `jacaranda_tree` is recorded at 19.4689 m vertical extent; `sf_minotti_sofa` is recorded at 295.8562 m horizontal extent, consistent with unnormalised centimetre coordinates. Neither can pass a cited size range until units and intended role limits are evidenced. No range was invented for the live manifest.

## Phase 2 proposal

Require the intake record as the sole output of `fetch_asset_library.py` and `fetch_sketchfab.py`; measure and normalise the downloaded file before any manifest or index write. Make the villa importer resolve only registered, passing records and refuse missing or failed ones. Add the validator and mutation tests to `scripts/verify.py`. Use a distinct medium-specific measurement record for texture sets and environment maps, then route them through the same intake gate. Preview each new model in neutral light beside a 1.8 m figure and obtain lead review before integration.

This is a checkpoint only; the fetchers, importer and verification gate were not changed.

