# D1 presentation render review — 2026-09-27

Role: `render_critic`, following `.claude/skills/photoreal-render/SKILL.md` and ADR-0013. Reviewed all fourteen original 1920 × 1280 images in `out/villa/render-d1`, their quality reports, `scene.json`, and the scene authoring and rendering code. No rendering implementation was changed by this review.

**Disposition: presentation set not accepted.** Nine of fourteen automated quality reports pass. Those passes do not establish photorealism, product fidelity, prop placement, or usable composition. The existing images contain conspicuous shape and placement defects, including defects in images that pass. Preserve them as diagnostic evidence rather than deliver them as approved finals.

The user's governing criterion is physical authenticity: a preview must withstand constructing the villa as shown. Attractiveness is secondary. No remedy below authorizes cosmetic light boosts, changed reflectances, hidden context, invented products, or changes to design geometry. A visually better image is still invalid if its inputs do not describe the intended construction.

## Fidelity blockers before construction-representative use

- **Products and photometry:** `villa_lighting` explicitly retains generic distributions for unbound kinds. Its wall-washer binding uses a symmetric iGuzzini flood product as a labelled substitute after the asymmetric wall-washer file pair failed validation. This is not evidence of the intended wall washer's appearance or distribution. Generic pendants, strips, fixture bodies, furniture, and sanitary blocks must remain visibly identified as unresolved products. A check reporting all files bound does not mean all fixtures are selected measured products.
- **Finish assumptions:** the scene module says the questionnaire had no finish answers and authors the palette from a taste profile. Photo textures, surface roughness, and numerical reflectances are assumptions, not measured chosen finishes. It even records replacing charcoal cinema fabric with taupe because the earlier room was unreadable. That is a design change affecting light transport, not a rendering correction; it requires an explicit design consequence and cannot be used to conceal an error in lighting.
- **Site and surroundings:** `villa-site.yaml` has client-provided city-level Sheikh Zayed coordinates, expressly not a plot survey. Its plot/envelope remain marked example data. Render context and neighbour materials must not be treated as surveyed physical obstructions. Evening sky images and their authored illuminance are scenarios, not a measured local sky. Day and evening comparisons also change light states and exposure presets, so they are not a controlled daylight test.
- **Glass:** the parent investigation verified that the villa uses a single glazing plane but reuses a shader intended for two slab faces. For nominal 70% transmission, applying the square root once gives approximately 83.7% instead. This overstates the intended transmission. A villa-specific correction and a one-plane transmission probe are required; a two-face bedroom slab must retain its separate treatment. The nominal 70% itself is a study assumption until tied to the selected glazing.
- **Native-model authority:** render shell geometry is regenerated through `villa_daylight.scene`, and furnishings through `villa_furnish3d.spec`; the authoring module does not consume a current complete native-model mesh extraction. Its own notes identify added coves, feature panels, and stair guarding not yet in the native model. Prior envelope checks do not prove every rendered surface equals the current constructed design. Close those gaps with saved-model read-back and explicit revision identity before calling this a faithful native-model render.

The parent is also checking a possible conflict between a kitchen requirement for 4000 kelvin without mixed light colours and authored warmer fixtures. This review has not established whether a later questionnaire answer supersedes that requirement; it remains an unresolved source-authority check, not a confirmed client-approved change.

## Priority 1: recover trustworthy indirect lighting before judging lighting design

The kitchen-to-garden, street lounge, and first children's room day images lose substantial portions of the design into black. Existing reports measure respectively 36.1%, 48.9%, and 19.5% near-black pixels. Their reported median luminances are 0.01, 0.01, and 0.02. These are output-image measurements, not measured room illuminance. The cinema also has 16.6% near-black pixels. A bright sun patch in the garden-living image establishes that sunlight does enter that opening; a global claim that glass blocks all daylight would be false.

The parent investigation identified an indirect-light clamp of 10 in `villa_scene.configure_cycles`, despite this renderer using calibrated luminous units. Such clipping is a structural suspect because it can suppress bounced light while retaining direct sun and lamp pools. The code correction must be followed by a controlled comparison with identical camera exposure, sky, materials, geometry, and fixture outputs. This review has not seen that comparison and does not claim the clamp accounts for all darkness. Context walls outside the openings visibly restrict views and may physically restrict sky access; their contribution should be measured after the renderer correction.

Next steps: render small unclamped comparisons of the kitchen, street lounge, children's room, and a lamp-lit interior; compare linear light measurements as well as images; validate the existing calibration probes. Keep the authored camera presets and source fixture outputs fixed. Only then decide whether remaining darkness is an actual design limitation. Do not brighten fixtures or change white balance to pass an image threshold.

## Priority 2: botanical assets are appearing as scattered specimens

In the evening living image, detached plant tufts appear across the coffee table, rug, and armchairs. The source requests the entire `anthurium_botany_01` asset as a single table plant at uniform scale 1.0. The render metadata records six imported mesh objects for it. Its combined projected bounds span most of the seating area and extend below the image. The terrace image also shows a plant fragment emerging from the upper exterior wall near the parents' room; the bedroom's `calathea_orbifolia_01` imports five mesh objects.

After workstation access recovered, direct inspection of the source glTF files confirmed that these are multi-specimen botanical packs. Anthurium has six independent scene roots arranged at metre-spaced offsets in two rows; calathea has five roots arranged in two rows, with horizontal offsets reaching one metre from the origin. The whole specimen sheet was imported as one plant. For the table plant, rotation is zero and scale is one: the common root translations did not create this separation. The importer does, however, lack an explicit common placement pivot for rotation and scaling of multi-root assets, which is a separate risk for other placements.

Next steps: select a complete named specimen, give it a suitable authored container where needed, and author its intended dimensions and support surface. For example, the unshifted `anthurium_botany_01_b` root is approximately 0.757 m wide and 0.472 m high before any scale change; `calathea_orbifolia_01_b` is approximately 0.347 m wide and 0.303 m high. These source dimensions must be checked against the intended location, not arbitrarily shrunk for appearance. Preserve all component relationships under one placement transform. Report resulting world bounds and support height, and reject asset spreads that cannot fit their stated table or floor location. Prove any guard on these actual botanical assets, not only a synthetic single-mesh prop.

## Priority 3: soft goods are explicitly authored as boxes

This is a confirmed source cause. `villa_render.build` makes duvets and pillows with `box_faces`. The parents' duvet is a six-face box measuring 1.66 m by 1.47 m by 0.07 m. Each parents' pillow is a six-face box measuring 0.71 m by 0.40 m by 0.14 m. A 0.02 m bevel and one subdivision level round edges but produce neither drape nor fabric fullness. The parents' and second children's images therefore show bedding like rigid slabs. The first children's room has similarly rigid mattresses and inadequate visible bedding.

Sofas and armchairs inherit five cuboid parts from `villa_furnish3d.body`; the living sofa is thirty source faces. Those are explicitly documented as footprint placeholders for massing renders. The terrace chairs are single cuboids rather than chairs with backs, legs, and cushions. Dressing clothes are thin rectangular boxes and read as hanging boards in the dressing view.

Next steps: use the existing cloth workflow for bedding while preserving the checked bed frame and footprint. Give pillows physically plausible volume and contact with the bed. Replace furniture appearance only with the specified product, or explicitly retain and label a procedural stand-in; do not silently select prettier products. A presentation gate must distinguish box placeholders from cloth or chosen products. The current quality reports omit soft-goods checks because villa simulation metadata is absent, which is why these obvious defects pass.

## Priority 4: plumbing and architectural detail are still massing representations

The ensuite bath is visibly an angular open box, with hard dark interior faces. The source confirms five rectangular solids form its floor and rim. The washbasin source is a solid 50 mm thick slab over a vanity: it has no bowl, drain, or faucet geometry. The image cannot communicate a selected sanitary product. Broad window openings and flush featureless door planes elsewhere also read as unfinished shell geometry. These observations do not establish a clash or construction defect in the native model; they establish limits of the presentation geometry.

Next steps: bind actual specified sanitary products and required opening details, or label this output as massing. Preserve checked envelopes. Do not invent products or imply construction completeness. The stair view shows bare floating treads and does not provide enough visible detail to assess support or protection; resolve those through the design/model workflow rather than treating a render as a safety check.

## Priority 5: projected bounds do not establish useful visibility

The dressing image is dominated by the near cabinet side, obscuring much of the room. The ensuite cuts off the basin, while the cinema shows seating and a blank wall without the screen. The stair pendant cluster is cut at the top. These framings limit the views' stated review purposes even where an object's projected bounding rectangle passes. A large bounding rectangle can include an object hidden behind a nearer object, and imported-prop bounds can straddle the camera plane.

Next steps: add occlusion-aware subject visibility where practical, or explicitly review subject visibility manually. Compose the dressing and ensuite from available clear space and verify the named subjects' meaningful parts are visible. If the cinema is a seating-only view, name it accordingly and add a screen relationship view. Avoid changing geometry merely to make a camera work.

## View-by-view disposition

| View | Existing automated result | Principal visible limitation |
|---|---|---|
| 01 Kitchen to garden | Fail | Most near kitchen and ceiling unreadable; direct pools dominate |
| 02 Garden living | Pass | Cuboid seating and scattered plant specimens; sun entry visible |
| 03 Street lounge | Fail | Large black regions; television wall difficult to assess |
| 04 Study to deck | Pass | Cuboid seat; sparse joinery; window view dominated by context wall |
| 05 Parents' bedroom | Pass | Rigid slab duvet and block pillows |
| 06 Children's room A | Fail | Bed largely dark; rigid mattresses |
| 07 Terrace | Fail | Cuboid outdoor chairs; plant fragment intersects upper exterior wall |
| 08 Cinema | Fail | Dark room, block seating, screen absent from composition |
| 09 Dining evening | Pass | Clearer lighting, but cuboid furniture and sparse cabinetry details |
| 10 Living evening | Pass | Detached plant tufts across seating; cuboid upholstery |
| 11 Stair void | Pass | Pendant cluster cropped; massing-level tread detail |
| 12 Ensuite | Pass | Box bath and slab basin; basin cropped |
| 13 Children's room B | Pass | Rigid bedding; minimally represented desk and bed |
| 14 Dressing | Pass | Foreground obstruction and board-like clothes |

## Closure evidence required

1. A measured and visually inspected unclamped-light comparison with fixed exposure and source lighting.
2. Source-asset inspection and corrected placement of the actual botanical props, including dimension/support checks.
3. Cloth or faithful product geometry for the prominent soft goods, with provenance and assumption captions.
4. Explicit distinction between massing placeholders and chosen products for plumbing, furniture, openings, and joinery.
5. Revised useful framings, followed by all image-quality checks and another full-image critic review.

Texture appearance also warrants a close review after light and geometry corrections: wood surfaces show conspicuous repeated straight striping, and interior plaster looks strongly textured. Those are visible observations; this review did not verify the source texture scale or finish specification sufficiently to prescribe a mapping or roughness change. Do not infer optical correctness from aesthetic preference.
