# C2 asset intake: phase 2d checkpoint

The verifier derives placement from `archpipe.concept.villa_render.build()`'s
returned `props` and `models`: 28 of 62 manifest entries are placed and 34
are candidates. All placed records must pass intake. Every candidate is
reported as `status: candidate` with its gaps, and candidate gaps do not
close the verifier. The unchanged `villa_scene.import_props` and
`import_models` paths still call `require_registered_asset`, so any candidate
chosen later must pass full intake before import.

## Evidence and decisions

- *Bauhinia variegata*: UF/IFAS ENH251/ST092, height 20–40 ft and spread
  25–35 ft, [source](https://ask.ifas.ufl.edu/st092), accessed 2026-09-30.
  The manifest's nursery-size screen uses the published upper bounds.
- *Ursinia anthemoides*: RHS maximum height 0.1–0.5 m and maximum spread
  0.1–0.5 m, [source](https://www.rhs.org.uk/plants/161741/ursinia-anthemoides/details),
  accessed 2026-09-30. Its model is a multi-plant clump, so the 0.1718 m
  height is checked against the species range and its 2.19 m width against
  measured clump spacing.
- Heliophila has no verifiable size card. The one west accent at its original
  centre remains one clump, now specified as blue-flowered *Plumbago
  auriculata*, already in the palette with a [Missouri Botanical Garden
  card](https://plantfinder.mobot.org/PlantFinderDetails.aspx?kempercode=a542).
  The available Heliophila mesh is labelled a look-alike appearance proxy
  pending preview review. Plumbago was chosen for its explicitly pale-blue
  flowers; Duranta's palette role is a violet shrub with thorns near paths.
- *Gazania rigens*: the native model bounds measure 0.3987 m high, but the
  actual landscape placement uniformly scales it to 0.25 m, below the
  [Missouri Botanical Garden 0.3048 m ceiling](https://plantfinder.mobot.org/PlantFinderDetails.aspx?taxonid=277558).
  The manifest records that scale and the scene audit checks every instance.
  The local glTF is absent: the workstation must inspect its nodes for soil,
  pot or label geometry and measure the plant alone if any such geometry
  inflated the native height. The 0.25 m placement is retained unless that
  inspection justifies a different truthful scale.
- The Sketchfab `Sofa-minotti` mesh is an unidentified model and now reads
  “Minotti-style sofa (unidentified model).” The lead's dated size override
  accepts its measured 2.9586 m width in the large garden living layout,
  whose real-footprint clearances already pass. Every override prints in
  `verify.py`; unrecorded out-of-range sizes fail.
- The three placed numbered indoor Poly Haven plants have explicit design
  species and RHS size cards: *Ficus lyrata*, *Syngonium podophyllum*, and
  *Haworthiopsis attenuata*. The first two are labelled look-alike proxies;
  the source pages support their integrated pot records. Workstation previews
  must assess visual fidelity.

## Workstation intake handoff

The final `verify.py` output has exactly these placed-entry schema gaps:

| Field | Count | Placed assets |
|---|---:|---|
| Preview image | 28 | Every placed asset; render neutral previews and have the lead inspect them before integration. |
| Bounds | 0 | All 28 have recorded bounds; remeasure downloaded local files and reject drift. |
| Author | 13 | `book_encyclopedia_set_01`, `ceramic_vase_01`, `ceramic_vase_03`, `flower_gazania`, `flower_heliophila`, `flower_ursinia`, `hanging_picture_frame_01`, `outdoor_table_chair_set_01`, `potted_plant_01`, `potted_plant_02`, `potted_plant_04`, `throw_pillows_01`, `wooden_bowl_01`. |
| Normalised units | 14 | `sf_bauhinia`, `sf_bottlebrush`, `sf_bougainvillea`, `sf_egg_chair`, `sf_frangipani`, `sf_garden_flower_clump`, `sf_hibiscus`, `sf_ixora`, `sf_lavender_clump`, `sf_lemon_tree`, `sf_olive_old`, `sf_probber_cane_armchair`, `sf_rug_round_jute`, `sf_wooden_bench`. |
| Front axis | 4 | `hanging_picture_frame_01`, `outdoor_table_chair_set_01`, `sf_egg_chair`, `sf_wooden_bench`. |

No other placed entry has a schema or size violation. The workstation must
also inspect Gazania nodes and review the Plumbago and indoor plant proxy
previews. The verifier reports all 34 candidate gaps separately.

With `NO_COLOR=1`, the affected asset, landscape, scene and furnishing suite
passed 88 tests (exit 0); the new landscape test passed in a 14-test rerun
(exit 0). `scripts/verify.py` exited 1 solely at the placed intake gate; all
other checks passed. The gate is expected to remain closed until the above
workstation evidence is filled.

No commit was made. A failed `verify.py` intake check remains expected until
the placed asset evidence above is filled and preview review is complete.
