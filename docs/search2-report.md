# Search 2: kids beds and storage — research only

Branch `codex/search2`; public searches checked 2026-10-12T05:50:41.424819+00:00. Local workstation date is 2026-10-11; receipts use UTC, which is already 2026-10-12.

No production code, shared assets or shared round-3 outputs were changed. No login, token access, model/archive download, integration or commit. Public listing thumbnails were inspected in temporary contact sheets; no dimensions were inferred from image pixels.

**Result: zero dimension-qualified bed replacements and zero verified exact storage matches.** Four new bunk leads and one new oak-bed lead are recorded in [kids-beds-candidates.json](kids-beds-candidates.json). The 32-record inventory and 12 conditional loose-furniture leads are in [storage-candidates.json](storage-candidates.json). Retain the procedural furniture pending actual intake.

D1 means the current authored villa layout option. UID means Sketchfab unique model identifier. CC-BY means Creative Commons Attribution; each candidate links its exact licence. CC0 means Creative Commons Zero public-domain dedication. Dimensions use metres (m), with millimetres (mm) where stated. This is storage research stage 1, not approval of Villa Method Stage 1 Ground.

## Bed inventory and acceptance

| ID / room | Mattress plan | Mattress tops above finished floor | Overall design height |
|---|---|---|---|
| `ka-bunk` / kids-a | two berths, each 0.900 × 2.000 m | lower 0.400; upper 1.400 m | 1.700 m |
| `kb-bed` / kids-b | 1.200 × 2.000 m | 0.475 m | 0.950 m |

Sources: `docs/beds-report.md` existing-bed table/round 5, `villa_furnish.layout` and the existing render mattress datums. The local report ends at round 5; rounds 6–7 cited in the job are absent from this branch. The requested 50 mm frame margin is therefore carried explicitly as the user requirement, without claiming a current production guard.

Width and length multipliers come from actual mattress bounds. Each must lie between 0.5 and 2.0. Plan distortion is the larger multiplier divided by the smaller, minus one; it must be no greater than 0.15, or 15 percent. “Within 15 percent” concerns their ratio, not each multiplier’s distance from one. The whole bunk uses one transform, which must preserve both required mattress tops. Every retained frame edge must be within 0.050 m outward of the mattress, as requested. Keep ladder, source bedding and real frame in room/support/route/front-access review. No listing supplies enough data to establish these conditions.

### New bed shortlist

| Bed / priority | Listing, author, licence | Stated dimensions | Why inspect / remaining risk |
|---|---|---|---|
| ka-bunk / 1 | [Bunk Bed](https://sketchfab.com/3d-models/e81c12b73b44472cbcc262069c03fc45), Em3D; [CC-BY](http://creativecommons.org/licenses/by/4.0/); `e81c12b73b44472cbcc262069c03fc45` | Not published; mattress size unmeasured | Best style lead: pale timber, two exposed mattresses and compact upright ladder at the end; simple form offers identifiable mattress and frame surfaces. No dimensions support a numerical pass prediction. Separate mattresses only appear distinct in the thumbnail; node separation, units, berth-height ratio, frame margins and ladder route remain unknown. |
| ka-bunk / 2 | [Bunk Bed](https://sketchfab.com/3d-models/3ddab7a93381496eba3c36677e777912), neverfollow81; [CC-BY](http://creativecommons.org/licenses/by/4.0/); `3ddab7a93381496eba3c36677e777912` | Not published; mattress size unmeasured | Thin tubular frame, exposed two mattresses and upright ladder avoid the staircase/storage width of previous misses. Bed-only thumbnail; clean surfaces make mattress identification plausible. Metal rather than light oak; artist describes a game asset. Real dimensions, mattress separation, both top heights and margins unpublished. |
| ka-bunk / 3 | [bunk bed](https://sketchfab.com/3d-models/ea60847abaaf4662b5f7c75b44f3ce9d), filthycent; [CC-BY](http://creativecommons.org/licenses/by/4.0/); `ea60847abaaf4662b5f7c75b44f3ce9d` | Not published; mattress size unmeasured | Bed-only preview has exposed mattresses, narrow posts and a straight ladder; frame looks less bulky than rejected staircase bunks. Black metal style reserve; listing description empty. Source dimensions, ladder projection, separate mattress nodes and common height transform unknown. |
| ka-bunk / 4 | [Low Poly Bunk Bed #1](https://sketchfab.com/3d-models/560110ada0484449b5ab71594c4bb85d), JustBlender; [CC-BY](http://creativecommons.org/licenses/by/4.0/); `560110ada0484449b5ab71594c4bb85d` | 1.97m x 1.03m x 1.62m | Dimension-first reserve: listing overall extents are near a single-bunk size. Two purple mattress surfaces and vertical ladder are visible. Overall plan ratios suggest modest adjustment, but only actual mattress ratios can establish eligibility. Very simple low-poly appearance with tall end panels and flat colour; 1.03 m overall width is not a 0.90 m mattress. Overall extents used as a deliberately invalid mattress proxy give 16.1873 percent distortion, above 15 percent. Mattress can be narrower, so measure before rejecting or accepting. |
| kb-bed / 1 | [Nordi-bed](https://sketchfab.com/3d-models/d92ab9476b6c4223b9e942954aa58835), WOODPORT; [CC-BY](http://creativecommons.org/licenses/by/4.0/); `d92ab9476b6c4223b9e942954aa58835` | Not published; mattress size unmeasured | Strongest material lead: author identifies oak; bed-only thumbnail shows a pale timber frame with exposed mattress edge and light bedding. No sizes stated. Headboard projects sideways; frame edges may exceed 50 mm. Mattress is partly dressed and a separable full mattress is unconfirmed. A double-bed aspect ratio would fail the plan-distortion rule. |

These are conditional search leads, not statements that they should pass. Em3D has the best pale-timber/ladder prospect; Nordi has the strongest explicit oak claim. Both require actual measurement before the lead spends integration effort. Existing measured rejects are excluded from the new shortlist; the JSON preserves the library bed IDs/credits used for duplicate screening.

### Other screens

- [Bed Wood Oak PBR](https://sketchfab.com/3d-models/28a8b7050a5e4951abbfb588015abf41), `28a8b7050a5e4951abbfb588015abf41`: Already cached and measured as sf_bed3_28a8b705, round 4. Removed by final UID duplicate audit; do not download again or treat a fresh metadata response as new geometry evidence.
- [Bed Sweet](https://sketchfab.com/3d-models/8aeacdcd0de84070b2ea64296ddba474), `8aeacdcd0de84070b2ea64296ddba474`: Published sleeping place 1500 by 2000 (units implicit, interpreted as mm). If confirmed, Kids B factors are 0.8 and 1.0, giving 25 percent distortion; published side thickness 120 also conflicts with a 50 mm frame margin. Not shortlisted.
- [bed with headboard begie 120 * 190](https://sketchfab.com/3d-models/b5a75d2a3bb242989d4d05e3e449a7ec), `b5a75d2a3bb242989d4d05e3e449a7ec`: Title supplies 120 by 190 without units or a mattress definition; preview shows only a rounded panel/headboard, not an identifiable whole bed. If it meant a 1.20 by 1.90 m mattress, factors 1 and 1.052632 give 5.2632 percent distortion, but this cannot establish a bed-only oak candidate.
- [Children's Bunk Bed Lucia](https://sketchfab.com/3d-models/b8fb51200aae41c6a660e54c16c9b538), `b8fb51200aae41c6a660e54c16c9b538`: Published overall dimensions 0.839 by 1.717 by 2.526 m, axes unnamed. Large storage staircase shown; no ladder and no mattress sizes. Poor prospect for retained-frame margin.
- [Bunk Bed](https://sketchfab.com/3d-models/964acad2c4ab45ca97d8c8d5d57d6327), `964acad2c4ab45ca97d8c8d5d57d6327`: Broad staircase/storage unit rather than compact ladder. No dimensions.
- [Bunk Bed](https://sketchfab.com/3d-models/e3f81d29bf234b728a154b41f50bbb9b), `e3f81d29bf234b728a154b41f50bbb9b`: Listing preview carries assorted loose toys/props and stylized bedding; no dimensions. Prefer cleaner bed-only prospects.
- [Single wooden bed](https://sketchfab.com/3d-models/c7bea79b8c7a4b7c9ec5eadfa2529b9a), `c7bea79b8c7a4b7c9ec5eadfa2529b9a`: Author explicitly describes separable mattress/bedding, but distressed horror-game appearance and unspecified single-bed size are weak prospects for a light-oak 1.20 m small double.
- [Low Poly Bunk Bed #2](https://sketchfab.com/3d-models/7e5f290cf4474aba93979b6c7244f142), `7e5f290cf4474aba93979b6c7244f142`: Overall 1.99 by 1.03 by 1.59 m, not mattress dimensions. Metal flat-colour reserve superseded by the dimensioned wood bunk; no additional download priority.

## Complete storage and dressing inventory

Read directly from `villa_furnish.layout(R.design("D1"))` with the current product setting. All seven desks are included because `villa_furniture_detail._desk` adds a three-drawer pedestal; a type-name-only cabinet inventory would omit them. The inventory also covers three basin vanities, fixed library surround/return, open shelving and service-run fronts. These are authored quantities, not a fresh Revit read-back.

Width × depth below is local to the item’s front. Heights are above its storey’s finished floor. B means basement; GF means ground floor. Builder names refer to `archpipe.concept.villa_furniture_detail` unless another module is named. Every native model parent uses `villa_furnish3d.body/spec`. Built-in classification follows bespoke modules, soffits, walls and service dependencies; loose classification is inferred from use and the generic builder, not a procurement schedule.

| ID | Room / level | Planned width × depth × height (m) | Builder | Classification / fronts |
|---|---|---|---|---|
| `lounge-tv` | lounge / B | 2.000 × 0.450 × 0.500 | `_cabinet(floating=True)` | loose furniture; Wall-hung, cabinet bottom 0.100 m; screen excluded. |
| `stair-flight-store` | stair-b / B | 1.800 × 0.400 × 2.300 | `archpipe.concept.villa_furnish3d.body` | built in joinery; Named fronts in JSON; access side is local +Y. |
| `stair-landing-store` | lounge-nook / B | 0.200 × 0.200 × 2.300 | `archpipe.concept.villa_furnish3d.body` | built in joinery; Named fronts in JSON; access side is local +Y. |
| `k-run` | kitchen / B | 2.010 × 0.600 × 0.900 | `_runs` | built in joinery; Named fronts in JSON; access side is local +Y. |
| `k-island` | kitchen / B | 3.050 × 1.100 × 0.920 | `_runs` | built in joinery; Named fronts in JSON; access side is local +Y. |
| `dining-sideboard` | dining-side / B | 1.200 × 0.450 × 0.800 | `_cabinet` | loose furniture; Named fronts in JSON; access side is local +Y. |
| `library-cabinet-left` | bar-alcove / B | 1.200 × 0.400 × 2.100 | `_glass_bookcase` | built in joinery; Named fronts in JSON; access side is local +Y. |
| `library-daybed` | bar-alcove / B | 2.000 × 0.950 × 0.450 | `_daybed_nook` | built in joinery; No opening front; fixed surround included to avoid losing built-in joinery in inventory. |
| `library-cabinet-right` | bar-alcove / B | 1.532 × 0.400 × 2.100 | `_glass_bookcase` | built in joinery; Named fronts in JSON; access side is local +Y. |
| `library-end-panel` | bar-alcove / B | 0.197 × 0.400 × 2.100 | `archpipe.concept.villa_furnish3d.body` | built in joinery; Fixed return panel; no opening front. |
| `cinema-desk` | cinema / B | 1.240 × 0.550 × 0.750 | `_desk` | loose furniture; Three-drawer pedestal added by detailed render builder; native box builder represents only table top and legs. |
| `gwc-basin` | guest-wc / B | 0.600 × 0.500 × 0.850 | `_washbasin` | built in joinery; Basin vanity front in render builder; sanitary basin occupies top. Retain service locations. |
| `dk-run` | dirty-kitchen / B | 3.450 × 0.600 × 0.900 | `_runs` | built in joinery; Named fronts in JSON; access side is local +Y. |
| `dk-appliance-bank` | dirty-kitchen / B | 1.200 × 0.600 × 2.300 | `_runs` | built in joinery; Named fronts in JSON; access side is local +Y. |
| `dk-fold` | dirty-kitchen / B | 1.250 × 0.600 × 0.900 | `_folding_counter` | built in joinery; Named fronts in JSON; access side is local +Y. |
| `pantry-shelves-1` | pantry / B | 0.995 × 0.300 × 2.200 | `archpipe.concept.villa_furnish3d.body` | built in joinery; Open shelves; no door. Ramp store heights are cut per module. |
| `pantry-shelves-2` | pantry / B | 0.995 × 0.300 × 2.200 | `archpipe.concept.villa_furnish3d.body` | built in joinery; Open shelves; no door. Ramp store heights are cut per module. |
| `store-shelves` | store-ramp / B | 2.850 × 0.500 × 1.900 | `archpipe.concept.villa_furnish3d.body` | built in joinery; Open shelves; no door. Ramp store heights are cut per module. |
| `study-desk` | study-game / GF | 1.800 × 0.700 × 0.750 | `_desk` | loose furniture; Three-drawer pedestal added by detailed render builder; native box builder represents only table top and legs. |
| `study-adult-desk` | study-game / GF | 1.400 × 0.700 × 0.750 | `_desk` | loose furniture; Three-drawer pedestal added by detailed render builder; native box builder represents only table top and legs. |
| `study-tv` | study-game / GF | 1.600 × 0.450 × 0.500 | `_cabinet(floating=True)` | loose furniture; Wall-hung, cabinet bottom 0.100 m; screen excluded. |
| `fb-basin` | family-bath / GF | 0.430 × 0.450 × 0.850 | `_washbasin` | built in joinery; Basin vanity front in render builder; sanitary basin occupies top. Retain service locations. |
| `ka-desk-1` | kids-a / GF | 1.100 × 0.600 × 0.750 | `_desk` | loose furniture; Three-drawer pedestal added by detailed render builder; native box builder represents only table top and legs. |
| `ka-desk-2` | kids-a / GF | 1.100 × 0.600 × 0.750 | `_desk` | loose furniture; Three-drawer pedestal added by detailed render builder; native box builder represents only table top and legs. |
| `ka-wardrobe` | kids-a / GF | 1.500 × 0.600 × 2.200 | `archpipe.furniture._build_wardrobe` | loose furniture; Named fronts in JSON; access side is local +Y. |
| `kb-desk` | kids-b / GF | 1.200 × 0.600 × 0.750 | `_desk` | loose furniture; Three-drawer pedestal added by detailed render builder; native box builder represents only table top and legs. |
| `kb-wardrobe` | kids-b / GF | 1.177 × 0.600 × 2.200 | `archpipe.furniture._build_wardrobe` | loose furniture; Named fronts in JSON; access side is local +Y. |
| `pb-bedside` | parents-bed / GF | 0.350 × 0.400 × 0.550 | `archpipe.furniture._build_bedside_table` | loose furniture; Named fronts in JSON; access side is local +Y. |
| `pb-vanity` | parents-bed / GF | 1.000 × 0.400 × 0.750 | `_desk` | loose furniture; Three-drawer pedestal added by detailed render builder; native box builder represents only table top and legs. |
| `pd-hang-1` | parents-dressing / GF | 1.720 × 0.600 × 2.300 | `archpipe.concept.villa_furnish3d.body` | built in joinery; Open dressing run; 4 drawers, upper box storage from 2.100 m. |
| `pd-hang-2` | parents-dressing-ext / GF | 1.346 × 0.600 × 2.300 | `archpipe.concept.villa_furnish3d.body` | built in joinery; Open dressing run; 6 drawers, upper box storage from 2.100 m. |
| `pe-basin` | parents-ensuite / GF | 0.600 × 0.500 × 0.850 | `_washbasin` | built in joinery; Basin vanity front in render builder; sanitary basin occupies top. Retain service locations. |

Counts: 32 parent records; 13 loose furniture, 19 built in joinery.

Kids B wardrobe width resolves to **1.177 m**, not the historical 1.5 m comment. The library daybed has a 0.450 m mattress/top datum and 2.100 m fixed surround. Ramp store modules top out at 1.740, 1.550 and 1.430 m although the parent envelope allows 1.900 m. The stair-flight store is cut to its stair soffit. The JSON lists module widths, drawer names, procedural front bounds, rotations, room/level and source hashes. Kitchen appliance fronts remain inside their parent runs; they are not independent loose cabinets. The parents bedside wall shelf mentioned in an authored placement reason has no separate furnishing ID and is not counted as a fabricated unit.

Built-in joinery stays procedural unless a model matches the complete envelope, modules, opening fronts, soffit, mounting, finish and service relationships exactly. No such model was found or measured. Opening swept volumes still need measurement; a static preview or “animated drawer” claim does not prove usable clearance.

### Loose-unit shortlist

| Target IDs | Listing / author / licence | Stated dimensions and decision |
|---|---|---|
| `ka-wardrobe`, `kb-wardrobe` | [Modern Closet / Wardrobe / Dresser Cabinet](https://sketchfab.com/3d-models/0999a8a70ed040c6afa8388ee4ffe923), AlyStation; [CC-BY](http://creativecommons.org/licenses/by/4.0/); `0999a8a70ed040c6afa8388ee4ffe923` | No published dimensions. Primary kids lead: light timber appearance, two doors and two lower drawers; author describes separately grouped moving fronts. No stated dimensions. Open and closed versions appear together in thumbnail: verify they are alternate poses/meshes, not inseparable duplicate wardrobes. |
| `kb-wardrobe`, `ka-wardrobe` | [Sala 120ワードローブ OAK](https://sketchfab.com/3d-models/48bd85b39d2b4c03901d50ab7b65d571), classe-saga; [CC-BY](http://creativecommons.org/licenses/by/4.0/); `48bd85b39d2b4c03901d50ab7b65d571` | No published dimensions. Oak-labelled, simple sliding-front wardrobe; Kids B width is 1.177 m, making the Sala 120 name worth checking with the manufacturer. 120 in title has no declared unit or dimension meaning. No depth/height stated. Do not assume 1.20 m width, resize built-in joinery, or claim exact fit. |
| `pb-bedside` | [jonah_bedside_table_oak_and_brass](https://sketchfab.com/3d-models/c5046eb689a54bf0b899b054abc13dc6), Ha Van; [CC-BY](http://creativecommons.org/licenses/by/4.0/); `c5046eb689a54bf0b899b054abc13dc6` | No published dimensions. Oak/brass-labelled two-drawer nightstand with restrained straight fronts, closer to warm luxury minimalism than ornate alternatives. No dimensions; must fit 0.350 by 0.400 by 0.550 m. Re-upload author differs from MADE.COM originals, which are noncommercial: platform CC-BY label does not establish rights to the original; quarantine pending provenance confirmation. Oak rather than requested walnut. |
| `pb-bedside` | [Bedside table](https://sketchfab.com/3d-models/ba32c03d924943c982ece9043e9ae9cb), patriciu; [CC-BY](http://creativecommons.org/licenses/by/4.0/); `ba32c03d924943c982ece9043e9ae9cb` | No published dimensions. Round two-drawer timber bedside can serve as a shape alternate after exact-envelope screening. Walnut/brass not established; curved form is a style reserve. No dimensions and likely wider than the slim bedside; do not enlarge layout. |
| `pb-vanity` | [Dressing table](https://sketchfab.com/3d-models/79138881b94547a4b42bb242b0094308), kochut_wood; [CC-BY](http://creativecommons.org/licenses/by/4.0/); `79138881b94547a4b42bb242b0094308` | No published dimensions. Timber dressing table with drawer pedestal and mirror; manufacturer-like author and simpler form than historical vanity listings. Light timber rather than verified walnut/brass. No dimensions; mirror is additional geometry requiring visibility, mount and window checks; preserve 1.000 by 0.400 by 0.750 m table envelope. |
| `study-tv`, `lounge-tv` | [Free Modular TV Cabinet – Mid Century](https://sketchfab.com/3d-models/5577bdb9323f48458472742acab745d9), Viksell; [CC-BY](http://creativecommons.org/licenses/by/4.0/); `5577bdb9323f48458472742acab745d9` | No published dimensions. Primary media lead: explicitly mid-century, wooden, modular cabinet with separate visible door forms. No sizes. Both D1 cabinets are wall-hung; source appears foot-supported, so exact mounting and envelope must be resolved without automatic conversion. |
| `study-tv`, `lounge-tv` | [Walnut Console](https://sketchfab.com/3d-models/9ef2d89128e44bdaa018ee9fb058a118), neverstopbuilding; [CC-BY](http://creativecommons.org/licenses/by/4.0/); `9ef2d89128e44bdaa018ee9fb058a118` | No published dimensions. Walnut two-door console with slatted electronics fronts; mid-century study and warm lounge appearance. No sizes; floor-standing legs conflict with wall-hung design. Treat as appearance reserve, not a drop-in cabinet. |
| `dining-sideboard`, `study-tv` | [Mid Century Teak Sideboard Credenza](https://sketchfab.com/3d-models/3028ba44d1f245b886c12eadc934f722), calebkung; [CC-BY](http://creativecommons.org/licenses/by/4.0/); `3028ba44d1f245b886c12eadc934f722` | 1350mml x ~360mmw x ~635mmh Dimensioned mid-century teak sideboard; drawers and doors visible. Useful compact shape reserve for serving/media storage. Stated width 1.350 m exceeds dining width 1.200 m by 150 mm, so fails unchanged-size dining fit; depth/height also differ. Study wall-hung mounting differs. Do not scale or change the design without a separate decision. |
| `dining-sideboard` | [Mid Century Cabinet](https://sketchfab.com/3d-models/65c10ad6cc1d4e7fae698334ee32ea89), GreekmythTR; [CC-BY](http://creativecommons.org/licenses/by/4.0/); `65c10ad6cc1d4e7fae698334ee32ea89` | No published dimensions. Compact mid-century door/drawer cabinet is an alternate to the oversized dimensioned credenza. No dimensions; warm timber rather than confirmed walnut. Legs and drop-down door motion require actual support and front clearance measurements. |
| `ka-desk-1`, `ka-desk-2`, `kb-desk`, `pb-vanity`, `study-desk`, `study-adult-desk`, `cinema-desk` | [Modern Wooden Desk with Drawer | 3D Model](https://sketchfab.com/3d-models/c51054964ac04d958a90b75c81b86347), Hassan Arts; [CC-BY](http://creativecommons.org/licenses/by/4.0/); `c51054964ac04d958a90b75c81b86347` | No published dimensions. Oak top and one drawer, clean leg form; primary kids drawer-desk lead, style reserve elsewhere. No dimensions. One drawer does not preserve the existing three-drawer pedestal capacity; exact size and storage requirement must be reviewed before replacement. |
| `ka-desk-1`, `ka-desk-2`, `kb-desk` | [Wood Desk-Rigged-Animated](https://sketchfab.com/3d-models/2402ee2330014244943f2c14b8627eaf), AnonimArt; [CC-BY](http://creativecommons.org/licenses/by/4.0/); `2402ee2330014244943f2c14b8627eaf` | No published dimensions. Author describes oak maps and animated drawers; provides an alternate with storage geometry to inspect. No dimensions; green/grey cabinet details and upper shelf differ from simple light-oak room style. Animation does not prove clearance. |
| `study-desk`, `study-adult-desk`, `cinema-desk` | [Metal Desk](https://sketchfab.com/3d-models/20a54670d5eb401585ae5dda4510927c), Jaxim; [CC-BY](http://creativecommons.org/licenses/by/4.0/); `20a54670d5eb401585ae5dda4510927c` | No published dimensions. Explicitly mid-century drawer desk; style alternate for study storage fronts. Metal appearance is dark/worn rather than the current walnut desk. No sizes; no source evidence of meeting either 1.800 or 1.400 m study width. |

No exact walnut/brass parents vanity or slim 350 mm bedside was established. The Jonah re-upload is a provenance quarantine lead, not an approved CC-BY replacement of MADE.COM’s noncommercial original. The dimensioned teak sideboard already exceeds the dining width by 150 mm. Floor-standing media models cannot automatically replace D1’s floating cabinets. Every loose parent has a candidate mapping; mappings express search relevance, not compatibility.

## Search queries, permissions and receipts

Public Sketchfab API: `/v3/search?type=models&downloadable=true&count=24&q=<query>`; the last four storage queries used 12 results. Public detail records: `/v3/models/<UID>`. Each shortlisted candidate has HTTP 200, UTC timestamp and SHA-256 digest (a content fingerprint) of its fresh JSON metadata response. The JSON retains author, exact licence URL and downloadable flag. Model downloads were never requested. First-page sampling is bounded and cannot establish that no suitable model exists anywhere.

Queries: `bunk bed`; `bunk`; `single bed`; `bed 120`; `scandinavian bed`; `oak bed`; `wardrobe`; `oak wardrobe`; `walnut bedside`; `dressing table`; `mid century cabinet`; `tv cabinet`; `sideboard`; `bunk dimensions`; `wooden bed`; `bedside brass`; `walnut nightstand`; `wardrobe 150`; `dressing table walnut`; `bed dimensions`; `bed small double`; `bed 120cm`; `nordic bed`; `walnut brass cabinet`; `walnut dressing table`; `desk mid century`; `oak desk drawers`; `bed 120x200`; `bunk 90x200`; `bed 120 200`; `oak wardrobe 150`; `bed 4ft`.

Web-index queries: `site:sketchfab.com/3d-models bunk bed 90 200 downloadable`; `site:sketchfab.com/3d-models bed 120 200 oak`; `site:sketchfab.com "bunk" "90" "200"`; `site:sketchfab.com "bed" "120x200"`; `site:sketchfab.com "bunk bed" "Dimensions"`; `site:polyhaven.com/a bed`; `site:polyhaven.com/license account`; BlenderKit queries for `download without login`, `docs login`, `free plan register download`, and `download account free`. Search-engine results were screened; irrelevant furniture packs/scenes and disallowed licences were not promoted.

| Robots URL | Fresh result / UTC time | Decision |
|---|---|---|
| [https://sketchfab.com/robots.txt](https://sketchfab.com/robots.txt) | HTTP 200, 2026-10-12T05:36:42.993201+00:00 | Public /3d-models/, /v3/search and /v3/models/<UID> permitted for User-agent *; no login or downloads requested. |
| [https://api.sketchfab.com/robots.txt](https://api.sketchfab.com/robots.txt) | HTTP 200, 2026-10-12T05:36:43.542199+00:00 | Public /3d-models/, /v3/search and /v3/models/<UID> permitted for User-agent *; no login or downloads requested. |
| [https://polyhaven.com/robots.txt](https://polyhaven.com/robots.txt) | HTTP 403, 2026-10-12T05:36:43Z | Robots unavailable; stopped direct requests. Search-engine indexed text only; no permission inferred. |
| [https://api.polyhaven.com/robots.txt](https://api.polyhaven.com/robots.txt) | HTTP 403, 2026-10-12T05:36:43Z | Robots unavailable; stopped direct requests. Search-engine indexed text only; no permission inferred. |
| [https://www.blenderkit.com/robots.txt](https://www.blenderkit.com/robots.txt) | HTTP 403, 2026-10-12T05:36:43Z | Robots unavailable; stopped direct requests. Search-engine indexed text only; no permission inferred. |
| [https://media.sketchfab.com/robots.txt](https://media.sketchfab.com/robots.txt) | HTTP 200, 2026-10-12T05:39:10.266536+00:00 | Listing /models/<UID>/thumbnails/ permitted; archive/download paths not accessed. |

The full robots bodies and hashes are embedded in both JSON deliverables. Restricted-sandbox DNS failed initially; the subsequent public read-only network requests produced the receipts above. The web browser also could not open the robots files. No blocked direct path was worked around.

[Poly Haven’s licence](https://polyhaven.com/license) assigns CC0 to assets, but separately restricts website scraping. Direct site/API robots checks returned 403; only indexed text was used. Its [indexed furniture catalogue](https://polyhaven.com/af/models/furniture) still lists Gothic Bed 01, Old Bed Frame and Vintage Day Bed, which do not provide the requested kids-bed form/style. No direct catalogue scraping or download was attempted.

[BlenderKit’s official free download flow](https://www.blenderkit.com/get-blenderkit/659b5eb1-707c-45c6-bb52-8f7193d04e70/) directs users through its add-on and promotes account creation; its [troubleshooting documentation](https://www.blenderkit.com/docs/add-on-troubleshooting/) discusses login and API keys. This does not prove every free asset requires authentication, but no permitted anonymous model-download path was established. Combined with robots 403, it is excluded for this job’s no-login requirement.

## Validation and handoff

Using `/home/omar/archpipe/envs/b16842c6f2161c9d/venv/bin/python`, with `NO_COLOR=1` and `PYTHONPATH=src`:

- `scripts/run_tests.py tests.test_beds tests.test_villa_furnish tests.test_villa_furnish3d tests.test_products`: **exit 0; 68 tests**, 436.536 seconds. Log: `/tmp/search2-focused-tests.log`.
- `scripts/verify.py --portable`: **exit 0; 173 PASS checks; ALL PASS**. Log: `/tmp/search2-verify.log`. Portable mode omits the Windows-only installed Revit-family corpus; no native acceptance claim.
- Deliverable audit: **exit 0**; JSON parses, all 32 inventory parents match current D1 room/level/width/depth/height, every furnishing parent is either inventoried or explicitly excluded, every loose parent has a candidate mapping, all five final bed UIDs are absent from the existing manifest, and production-source hashes remain unchanged.
- `git diff --check`: **exit 0**. Only the three requested docs are untracked; no production change or commit. No agent assets changed, so no adapter sync was required.

The public search samples contain 341 rows across queries, including duplicates and irrelevant results; this is not 341 distinct eligible models. Production/native-model acceptance is outside this search package. The lead owns full-suite testing and any authorized downloads.

### Draft defect and control handoff

`search2-cached-asset-as-new-lead`: the final audit found that Bed Wood Oak PBR, UID `28a8b7050a5e4951abbfb588015abf41`, had been promoted as a new lead even though `sf_bed3_28a8b705` was a measured round-4 reject. Its public display author now reads AK STUDIO; the embedded historic credit reads AHMED KCHIKICH. New metadata and changed titles/authors do not establish a new asset. The escape was screening appearance before joining the UID against the authoritative manifest. The draft JSON/report are the real case; the exact UID and previous rejection are frozen in the bed JSON's defect record.

The temporary generator now refuses construction of any cached UID as a new lead before writing outputs, regardless of target room. Executed proofs: the actual Oak PBR UID is refused, cached sparshgupta bunk UID `2cabd354ef2e4293ae817b01a8fdbf10` is refused as a sibling, clean Em3D UID is permitted as a conditional lead, and renaming the target to another villa/room does not bypass the rejection. The final whitelist contains five new UIDs. The initial audit also wrongly required HTTPS in source licence URLs; Sketchfab returns HTTP CC-BY URLs. The corrected audit checks the licence host/path and preserves the exact source link.

Durable handoff control for the lead, in plain Python (the `manifest_text` argument is the existing library manifest serialized as text, and `uid` is the candidate identifier):

```python
import json
from pathlib import Path

def require_new_uid(uid, manifest_text):
    if uid in manifest_text:
        raise ValueError("Cached asset cannot be a new search lead: " + uid)

manifest_text = Path("ops/workstation/library-manifest.json").read_text()
beds = json.loads(Path("docs/kids-beds-candidates.json").read_text())
for bed in beds["beds"]:
    for candidate in bed["candidates"]:
        require_new_uid(candidate["uid"], manifest_text)
for frozen_uid in [
    "28a8b7050a5e4951abbfb588015abf41",  # actual Oak PBR draft defect
    "2cabd354ef2e4293ae817b01a8fdbf10",  # cached bunk sibling
]:
    try:
        require_new_uid(frozen_uid, manifest_text)
    except ValueError:
        pass
    else:
        raise AssertionError("Cached candidate escaped the guard")
require_new_uid("e81c12b73b44472cbcc262069c03fc45", manifest_text)
```

This control is scoped to the research package. The central `docs/LEARNINGS.md`, guard registry and affected search workflow were not edited because the job authorizes only these three deliverables. **Lead follow-up remains: register and enforce UID exclusion before future candidate construction.** This is not claimed as a closed repository-wide process defect.
