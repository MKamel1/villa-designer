# C2 asset intake: Phase 2a checkpoint

Historical checkpoint. Current phase 2d scope and workstation handoff:
[`asset-intake-phase2d-checkpoint.md`](asset-intake-phase2d-checkpoint.md).

## Phase 2c checkpoint (2026-09-30)

The validator now accepts an `ASSUMED` size range only for the ten lead-approved uncited roles, requires its reason, and lists each accepted assumption separately. `scripts/verify.py` prints **19 assumptions**. A sofa or other cited role with an `ASSUMED` range fails. Plant records require a named species and a cited species range. The source figures are mature-size ceilings, so a smaller nursery specimen is allowed; an uncited or deliberately maintained/clump spread is left untested and labelled `ASSUMED` in the reason. The figures are from the held [plant palette](../out/villa/round3/plant-palette.json) and the Missouri Botanical Garden cards already linked in `villa_landscape.py`. No layout, design or camera changed.

The 19 assumption entries are `book_encyclopedia_set_01`, `alarm_clock_01`, `brass_vase_03`, `throw_pillows_01`, `ceramic_vase_01`, `ceramic_vase_03`, `decorative_book_set_01`, `wooden_bowl_01`, `hanging_picture_frame_01`, `hanging_picture_frame_02`, `standing_picture_frame_01`, `planter_box_01`, `boulder_01`, `namaqualand_stones_01`, `sf_egg_chair`, `sf_rug_round_jute`, `sf_wooden_bench`, `outdoor_table_chair_set_01`, and `desk_lamp_arm_01`. Each has `min_m`, `max_m`, `basis: ASSUMED`, and a reason in the manifest; these are provisional intake envelopes, not published product dimensions.

The Chelsea bed now cites [BertO's Chelsea dimensions](https://www.bertosalotti.it/letto_moderno/letto-matrimoniale-imbottito-con-contenitore-chelsea.html). The Søborg chair now cites [Fredericia's product dimensions](https://www.fredericia.com/product/soborg-wood-base-3050-3050224856). Dining chairs use the held Mitton and Nystuen, *Residential Interior Design*, 4th edition, Figure 4.3, printed page 82, preliminary chair plan dimensions. Figure 4.5 on printed page 83 was also checked: it gives dining-table dimensions and chair positions, not individual chair sizes. Figure 8.1 on printed page 224 gives adult task-chair planning footprints, unsuitable for the Søborg child's desk-chair use. The product-specific sheet is retained for that model.

All **62** prop records remain blocked. Remaining failures measured by the validator: 62 previews, 39 authors, 22 native-unit factors, eight front axes, seven contents flags, one file-bound record, 23 plant species ranges, and three out-of-range models. The workstation script can address previews, bounds, authors, units, facing and mesh-name contents, but **the remaining work is not solely workstation-fillable**:

- Twenty unplaced plant assets have no species assignment: `potted_plant_04`, `potted_plant_01`, `potted_plant_02`, `pachira_aquatica_01`, `calathea_orbifolia_01`, `anthurium_botany_01`, `shrub_01`, `shrub_03`, `jacaranda_tree`, `tree_small_02`, `searsia_lucida`, `grass_medium_01`, `grass_medium_02`, `periwinkle_plant`, `wild_rooibos_bush`, `shrub_02`, `shrub_04`, `sf_jacaranda`, `sf_royal_poinciana`, `didelta_spinosa`. Their model names or use labels do not establish the species each stands in for in the live design. They require placement or an explicit species decision before a species citation can be attached.
- `flower_ursinia` and `flower_heliophila` are placed as *Ursinia anthemoides* and *Heliophila coronopifolia*. Their held supplementary care links do not provide mature height/spread. The landscape's `CLUMP_SPREAD` is explicitly `ASSUMED` from model width; it was not promoted to a species citation. `sf_bauhinia` is placed as *Bauhinia variegata*, but its palette card cites Gardenia rather than the required Missouri Botanical Garden or Royal Horticultural Society numerical card. Its species field is recorded and its range remains missing.
- `flower_gazania` measures 0.3987 m high while [Missouri Botanical Garden's Gazania rigens card](https://plantfinder.mobot.org/PlantFinderDetails.aspx?taxonid=277558) gives a 0.3048 m mature-height ceiling. This may be a multi-plant proxy or include geometry beyond the plant. The preview and node inspection must resolve it; the species range was not widened.
- `sf_minotti_sofa` measures 2.9586 m wide after its recorded 0.01 scale, above the held generic sofa maximum of 2.49 m. The [Sketchfab asset page](https://sketchfab.com/3d-models/sofa-minotti-e1422bbf699246b386f0ae6e37d9c635) identifies it only as “Sofa-minotti”; it supplies no Minotti collection or variant. Manufacturer sheets for similar-width models do not prove which model this mesh represents. It still needs an exact model identification and matching technical sheet before the generic range can be replaced.
- `mid_century_lounge_chair` measures 1.1903 m deep against the held chair maximum of 1.07 m. Its glTF model is unavailable in this checkout, so local node names and geometry cannot establish whether the depth includes an ottoman. The workstation must inspect the package and report that evidence. Its range was not changed.

The range gaps and model-identity questions above prevent the requested “only workstation fields remain” confirmation. This checkpoint reports them rather than citing a different product or treating an assumed clump width as a species fact.

Phase 2c checks: with `NO_COLOR=1`, `tests.test_asset_intake` passes 17 tests, and the affected asset, landscape, scene and furnishing group passes 85 tests (process exit 0). `scripts/verify.py` prints 19 assumptions and exits 1 only at the intentionally closed manifest intake gate. The named tests cover a rejected sofa assumption, an accepted and listed decor assumption, a cited plant in range, and that plant beyond its cited range. No commit was made.

All 62 prop records remain blocked after phase 2b. The validator is wired into both fetch paths, all three scene import paths, and `scripts/verify.py`. Preview review and workstation measurement are pending. No design, layout, or camera was changed.

## Backfill provenance

- Poly Haven `source_url`: existing manifest `url`, or the asset page formed from its published asset identifier. `licence=CC0` and optional `credit=Poly Haven`: https://polyhaven.com/license. Individual `author` is taken only from `https://api.polyhaven.com/info/{id}` when `--api` is used and a name is returned. The local network refused that request, so authors remain missing.
- Sketchfab `source_url`, `author`, `licence`, and `credit`: the manifest fields recorded by `fetch_sketchfab.py` from its model API metadata; absent fields stay absent.
- `up_axis=+Y`: glTF 2.0 specification section 3.4, https://github.com/KhronosGroup/glTF/blob/main/specification/2.0/Specification.adoc#34-coordinate-system-and-units. Blender import conversion `(x,y,z)` to `(x,-z,y)` is recorded in `villa_landscape.py`.
- Poly Haven `units_normalised=1`: glTF metre coordinates imported without a unit conversion. The Minotti sofa has `0.01` from the actual `villa_furnish.product` scale calculation, tied to its recorded native extent. Other Sketchfab factors are not yet asserted.
- `front_axis=none`: nondirectional vases, bowls, plants, and pillows, with a role reason. Other missing fronts stay missing. `contents` is added only when local glTF node, mesh or material names explicitly identify a supported flag.
- `expected_size_range`: role ranges for sofa and armchair use the plan dimensions in Mitton & Nystuen Fig. 4.3, printed p. 82; the uncited height axis is left untested. All other roles lack a defensible generic held range. Product-specific dimensions require the actual published URL.
- `sf_minotti_aston_armchair` cites Minotti's [Aston technical sheet](https://www.minotti.com/downloads/540/1358/ASTON_TECHNICAL_SHEET.pdf), which states 74 cm width, 75 cm height and 84 cm depth for the armchair. Its native unit factor remains unverified, so the downloaded mesh has not passed the dimensions check.

## Phase 2b validator results on the real manifest

The role vocabulary has 24 terms. All 62 entries have a controlled `role` and retain the old description as `use`; 23 roles are currently used. Mitton and Nystuen, *Residential Interior Design*, 4th edition (2022), Figure 4.3, printed page 82, provides cited plan width and depth ranges for `sofa` and `armchair`. It does not give height. These preliminary planning sizes are a screen; a real product's published dimensions can supersede them. The sofa and armchair figure was read from the held page image. The sources checked in this pass did not establish a generic model range for the other roles: the catalogue's later villa furniture envelopes are marked assumed, and the WP0 plant spread figures apply to named species or planting clumps, not every model in a role. These roles remain without a range and fail closed.

| Remaining issue | Entries | Why it remains |
|---|---:|---|
| Preview image | 62 | Workstation neutral previews have not been generated and reviewed. |
| Cited size range | 55 | The role has no defensible held generic range or verified product dimension page. The two cited role ranges cover seven entries, one of which uses the Aston product sheet instead. |
| Author | 39 | Individual Poly Haven authors require publisher API metadata; local request was refused. |
| Unit normalization | 22 | Sketchfab native units need model and product measurement; no factor was inferred from the file name. |
| Front axis | 8 | Directional assets need measured or lead-verified facing. |
| Contents | 7 | Six indoor plants need a verified integrated pot; the bed needs verified bedding. Garden plants need no pot flag. |
| Bounds | 1 | `decorative_book_set_01` needs model measurement. |
| Outside cited role range | 2 | `sf_minotti_sofa` is 2.9586 m wide against the preliminary sofa maximum 2.49 m; `mid_century_lounge_chair` is 1.1903 m deep against the chair maximum 1.07 m. These remain visible findings; a matching published product sheet can supply its own cited range. |

All 62 entries still fail. Empty `contents` is now accepted for all roles except bed and indoor plants. The workstation can fill previews, file bounds, facing, units and publisher metadata. Range gaps need source review or actual published product dimensions; the workstation script cannot invent them.

### Role size evidence

| Role | Entries | Held range status |
|---|---:|---|
| `armchair` | 4 | Mitton & Nystuen Fig. 4.3, plan axes only |
| `bed` | 1 | No held generic range |
| `bedding` | 1 | No held generic range |
| `bedside-table` | 0 | No held generic range |
| `bench-outdoor` | 1 | No held generic range |
| `bistro-set` | 1 | No held generic range |
| `boulder` | 2 | No held generic range |
| `climber` | 1 | No held generic range |
| `decor-small` | 8 | No held generic range |
| `dining-chair` | 1 | No held generic range |
| `egg-swing` | 1 | No held generic range |
| `groundcover` | 5 | No held generic range |
| `indoor-floor-plant` | 1 | No held generic range |
| `indoor-table-plant` | 5 | No held generic range |
| `ornamental-grass` | 2 | No held generic range |
| `planter` | 1 | No held generic range |
| `rug` | 1 | No held generic range |
| `shade-tree` | 5 | No held generic range |
| `shrub` | 11 | No held generic range |
| `small-tree` | 3 | No held generic range |
| `sofa` | 3 | Mitton & Nystuen Fig. 4.3, plan axes only |
| `task-chair` | 1 | No held generic range |
| `task-lamp` | 1 | No held generic range |
| `wall-art` | 2 | No held generic range |

## Workstation command

After deploying this working tree to the workstation, run the following from the repository root. The command selects the newest deployed release, asks the Poly Haven API for individual authors, inspects available mesh names, then runs `measure_assets.py` and records previews under the persistent library. Inspect its output and bring the updated release manifest back for review; it is not automatically integrated.

```powershell
ssh ai-workstation 'cd "$HOME/archpipe" && release=$(find releases -mindepth 1 -maxdepth 1 -type d -printf "%T@ %p\n" | sort -nr | head -1 | cut -d" " -f2) && PYTHONPATH="$release/src" python3 "$release/ops/workstation/backfill_asset_intake.py" --api "$HOME/archpipe/assets/library" && PYTHONPATH="$release/src" "$HOME/opt/blender/blender" -b --python-exit-code 1 --python "$release/ops/workstation/measure_assets.py" -- "$release/ops/workstation/library-manifest.json" "$HOME/archpipe/assets/library"'
```

## Test status

- `NO_COLOR=1 .venv/Scripts/python -m unittest tests.test_asset_intake`: 15 tests, exit 0.
- `NO_COLOR=1 python -m unittest tests.test_asset_intake tests.test_landscape tests.test_villa_render_scene tests.test_villa_furnish`: 83 tests, exit 0.
- `NO_COLOR=1 .venv/Scripts/python scripts/verify.py`: exit 1 only because the manifest intake gate remains red on all 62 prop records. System Python lacks Shapely, so the project virtual environment is required.
- No design, layout or camera changed. No commit made.
