# Reusable engineering lessons

## R3b-1: imported furniture front axis

- Observed: the garden-living Minotti sofa faced backwards in the round-3 render. The lead found it at presentation review; asset ingest and scene export should have caught it.
- Reproduction: the real Minotti has native front +Z, while the old scene exported the layout yaw unchanged. `test_real_minotti_old_yaw_fires_and_corrected_scene_is_quiet` freezes that transform.
- Cause and escape: the manifest recorded bounds and up axis but no front axis; the exporter and importer therefore treated every asset as if its front were already the layout front. Geometric footprint checks could pass a reversed model.
- Class and siblings: directional furniture imported from glTF. The Probber chair has native front -Z; the other placed sofa, dining chair, desk chairs and bed have native +Z. A round rug has no front.
- Tier 1 control: measure the tall back against the low open side at ingest, allow a lead-verified override, record the front axis in the manifest, and compute scene yaw from it. Tier 2 backup: scene validation checks that the resulting yaw maps the native front to the layout front within one degree; Blender import repeats the check.
- Proof: the historical Minotti yaw fails, the corrected scene stays quiet, a deliberately reversed Probber chair fails, and fixed vertex statistics from both real meshes return their measured fronts. The check uses the asset axis and layout yaw without design-specific coordinates.
- Registry: `furniture-front-axis` -> `model_yaw` and `check_model_orientation` -> `tests.test_furniture_models.GuardOnThePlacedScene` -> asset ingest and scene export.

This index records observed behavior and its consequence. It is not a
source of architectural standards. The cited rule catalogue and decision
records remain authoritative for design guidance.

| Area | Observed behavior | Required consequence / evidence |
|---|---|---|
| Revit runner | A relative script path can exit zero without executing; model argument can leave no open document | Absolute paths, explicit document resolution, fresh artifact checks. `extract_model.resolve_doc`, `run_bedroom.run` |
| Revit 2027 | Family symbols load inactive; inactive placement raises; Name property can be ambiguous in IronPython | Activate, regenerate, use `Element.Name.GetValue`. `place_families_test.py`, committed fixture |
| Content | Template contains doors/windows although Libraries count suggests none; third-party categories and declared sizes are unreliable | Verify actual placed dimensions and bind by intent. Never substitute catalogue size for a measured family |
| Geometry | DirectShape rotation is baked; world bounding box is already rotated; family insertion point need not be footprint centre | Carry proxy direction, measured box centre and size. Quarter-turn reversal is exact; arbitrary rotation needs a local footprint. `from_extract.py`, regression tests |
| Review coverage | Dropping unknown chairs/tables makes clearances pass falsely | Keep every measurable piece as an obstacle, even without a published access figure |
| Product furniture bounds (WP4b) | The real Minotti sofa and modern low sofa have native width/depth ratios that the old generic envelopes miss; testing only a swapped footprint rejects a sofa because its neighbours keep their old positions | Normalize each manifest model with one scale, rearrange neighbouring furniture around its measured footprint, then rerun all furnishing checks. The living sofa passes with a 1.10 × 0.45 m table and two measured cane chairs; `test_old_coffee_position_rejects_real_living_sofa_but_relayout_passes` proves the original 0.60 m table placement fails. The 3.29 × 1.62 m lounge sofa still closes the 914 mm route to the pantry after moving its table and armchair, so its procedural fallback records the route failure. Cinema and parents' bed retain explicit client arrangement reasons. Ambiguous chair and rug scales remain explicitly ASSUMED. |
| Furniture orientation (R3b-1) | A glTF asset's front can differ from the plan's front; Minotti native +Z becomes scene -Y and the uncorrected layout yaw faces it backwards | Ingest records a measured or lead-verified front axis; scene export computes and checks the model yaw; importer checks again. `tests.test_furniture_models` freezes measured Minotti and Probber half statistics and tests the historical yaw. |
| Windows verifier temporary directory | Python 3.14 `tempfile.mkdtemp` created a directory under `out/tmp` that the sandbox process could not write into, so `scripts/verify.py` failed before its first fixture | Create a unique directory with `Path.mkdir` under `tempfile.gettempdir()`; the same verifier then ran to `RESULT: ALL PASS`. Keep `TMP` and `TEMP` pointed at `out/tmp` for test runs. |
| Climber mass (WP4b) | A solid magenta box reads as a wall rather than vegetation even when its trellis envelope is correct | Keep the measured envelope, replace its render visibility with seeded leaf and bract polygons, and check count per square metre, 70/30 mix and every centre inside the original bounds in `test_climber_placement`. |
| Accessory relationships | A desk chair occupies its desk's use zone; bedside tables intentionally occupy the bed's head-end zone | Explicit `accessory_to` intent is stored in Revit comments and disclosed in review. Exemption applies only to parent access; physical overlap and unrelated access still fail. It is a design interpretation, not an invented standard |
| Metadata | Falling back to Comments as an identity collides when comments contain shared structured metadata | Reserve `archpipe:` comments for intent; preserve Mark/ApplicationDataId as identity |
| Serialization | Revit `Color` channels are .NET bytes that IronPython's JSON encoder rejects | Convert to Python integers and serialize before opening the output, so failure cannot truncate the last extract |
| Scope | An isolated room is not a dwelling | Report unassessed dwelling rules and preserve their findings separately. Never quietly waive a missing bathroom in a full-house review |
| Native output | PDF export uses `PageOrientationType` and `ZoomType`; displayed headings do not prove a view's actual type | Verify native view types, scale, page count, vector geometry, and markup read-back; inspect pages |
| Native sheet layout | A blank sheet's content was off-centre and its viewport title overlapped the synthetic review note; long titles wrapped over the scale, despite passing vector-count checks | Create a native paper frame, reserve title spacing, use short display titles, and visually inspect exported pages. `revit/export_views.py` |
| Elevation direction | Revit's `ViewDirection` points toward the viewer, as documented in its installed application interface reference; a northward direction shows the south wall | Name interior elevations by the opposite direction and record the actual vector in the view report. Confirm the wall's openings/furniture visually |
| Markup text | Revit TextNote stores carriage-return line breaks and a trailing newline | Compare logical lines, preserving content; verify cloud vertices against chosen coordinates |
| Lighting ownership | Third-party families may override photometry even when writes appear successful | Join explicit spec photometry by model Mark, keep geometry from Revit, report unmatched identities. Never call the join wholly Revit-authored |
| Photometry | Blender IES azimuth differs, finite sphere sizing can wash out a strip light, coarse angular interpolation biases narrow beams | Keep calibrated orientation/size/angle corrections; see [decision 0010](decisions/ADR-0010-photometric-render-calibration.md) |
| Lighting claims | Direct calculations omit shadows and inter-reflection; an empty-room probe is calibration | Label the probe's contents. Do not claim furnished-room uniformity or real-world precision from it. [Decision 0009](decisions/ADR-0009-no-uniformity-verdict-from-direct-light.md) |
| Materials | Revit paint hue can be read; shading colour is not measured reflectance | Carry actual finish names/hues and separately disclose assumed optical values |
| Gates | A script printing FAIL but returning zero cannot gate a pipeline | Assert failed, missing and stale cases as well as passing cases; inspect saved evidence, not shell exit alone |
| Door handling | The current extract lacks actual hinge/facing handedness; the adapter uses the default left hinge | Native views show the authored door. Automated swing checks are provisional until handedness is extracted; do not claim general door-swing certification |
| MCP process input | On Windows with Python 3.14.7 and MCP library 1.30.0, a cached child inherited the live protocol input pipe and hung before creating its run lock; the same command completed directly | Give noninteractive children `stdin=subprocess.DEVNULL`. The real transport regression in `scripts/test_mcp.py --cached-run` verifies matching evidence first and requires a response within 30 seconds. Measured complete test: under two seconds |

## Update procedure

Workstation lessons measured on 2026-09-23:

| Area | Observed behavior | Reusable consequence / evidence |
|---|---|---|
| Probe placement | Three isolated timing trials gave graphics speed ratios of 1.98 for direct light and 7.08 for sixteen bounces; mean illuminance differed by less than 0.001 percent | Use graphics acceleration by default, retain processor comparison. `workstation.py benchmark`, [worker evidence](ops/workstation-jobs.md) |
| Reuse | Three unchanged camera jobs were all reused after unrelated documentation/orchestration changes; a modified cached artifact fails the hash check | Fingerprint job dependencies and actual runtime; verify artifacts, preserve failed attempts. `worker.cached_job`, `tests/test_worker.py` |
| Candidate interpretation | Both negative bed shifts failed design review while the worker batch completed successfully | Report execution success separately from design acceptance; never apply candidate geometry to a saved extract. `worker_entry.py` sweep |
| Portable verification | Installed native Revit family corpus is unavailable on Ubuntu and its transfer was not authorized | Keep live corpus checks on Windows; explicitly report skipped coverage and run synthetic parser cases remotely. `verify.py --portable`, `tests/test_rfa_portable.py` |
| Headless Radiance build | The full CMake build attempted OpenGL targets even with headless mode enabled | Build the twelve required command-line targets from the checksum-pinned official source; record the installed subset. `ops/workstation/bootstrap.py` |
| Worker contention | Render and probe jobs share one graphics processor | Use an operating-system lock across worker processes and bounded processor jobs; benchmark in isolation. `worker.process_lock`, `worker_entry.py` |
| External implementation | Claude Code's actual session identified `claude-sonnet-5`; broad scientific work required substantial research before writing code | Pin and verify the model; provide narrow ownership, bounded effort and existing evidence. The lead retains actual integration checks. [Delegation workflow](ops/delegated-implementation.md) |
| Native fixture geometry | Fine extraction exposed a 1,828.8 mm housing across the west wall and 2,624-triangle light-source display webs below each cylinder pendant | Check actual housing bounds and rotate the long fitting along the wall. Preserve `Light Source` subcategory geometry with an explicit symbolic role and exclude those display webs from physical rendering. `probe_fixture_geometry.py`, extractor, round-trip gate |
| Procedural solids | A closed, consistently connected headboard mesh still had inward-facing triangles because its two-dimensional profile walked clockwise | Test positive signed volume independently of paired edges; reverse the profile before extrusion. `tests/test_furniture.py` caught the error before final acceptance |
| Radiance tool contracts | Portable mocks accepted the wrong output-directory flag and a split format flag; the actual toolchain exposed them | Use absolute per-job `ies2rad -o` prefixes, `RAYPATH` for support files, joined `rtrace -faa`, separate diagnostic output, and actual source/sky checks. `tests/test_radiance.py` |
| Window simulation | An extracted glass solid has front and back faces; giving both a whole-window transmittance applies it twice | Use one planar surface from the actual glazing mesh, keep actual opaque frames, and state the optical assumption. `radiance._glazing_surface` regression |

### Presentation rendering (2026-09-24)

Every row says why the defect was missed, not only what broke. A guard
listed as a check is automatic, and is proven against the real defect.

| Defect | Why it was missed | Guard now in place |
|---|---|---|
| Five render rounds changed samples, textures and HDRI strength, and the images still read as CG | No diagnosis step: symptoms were tuned because nothing asked "what physical cause?" first | Diagnosis order in the `photoreal-render` skill; `render_critic` agent must rule out structural causes before tuning. [ADR-0013](decisions/ADR-0013-presentation-renders.md) |
| No sunlight entered: a refractive glass slab blocks Cycles shadow rays, so sun/sky arrived only as caustics | Nobody checked whether daylight physically reached the floor; brightening the sky hid it | `render_qa` check `glass_passes_daylight`; `photoreal.architectural_glass`; proven with `--qa-break glass` |
| The window looked like a mirror, then showed a void, then a white band | Assumed `Is Camera Ray` stays true through glass (it becomes a transmission ray), and helper ground was hidden from camera rays only | `render_qa` check `window_view` (local detail inside the window's projected rectangle); proven with `--qa-break view` |
| The first `window_view` check passed the void | It used global standard deviation, and a smooth gradient has spread but no content. It had only been tested on synthetic images | Measured metric (void 0.0026 vs garden 0.0365); rule: **prove every guard on a real reproduction** |
| The whole room rendered orange | Blender 4.2 had no display white balance; nothing measured colour cast | Blender 4.5 LTS; `render_qa` check `colour_cast`; `SCENE QA` reports white balance |
| Walls leaned | The camera was pitched down, with no lens shift; nobody inspected verticals | Level camera with `shift_y` (`photoreal.photographic_camera`); `render_qa` check `verticals_level` |
| Pure-red lamp shade and orange door frame | Revit shading colours were treated as finishes and rescaled to 0.35, saturating a channel | `photoreal.FINISHES`; `render_qa` check `cad_colour` for un-overridden saturated materials |
| Ivory bedding rendered grey | One 0.35 "furniture" reflectance was reused for textiles | Per-textile presentation reflectance; `render_qa` check `textile_reflectance` |
| Lights could not be switched off | `float(x or 1.0)` turned an explicit 0 into 1; the same line was repeated in `compare_lux.py` | Explicit `None` checks; `verify.py` falsy-zero lint (`# falsy-ok: reason` where 0 is invalid anyway) |
| The first falsy-zero lint found nothing | Its regex could not match the real line (inner parentheses) | The lint now asserts it matches the historical line before scanning |
| Fixtures rendered as isotropic points | An ad-hoc driver did not remap IES paths, and the fallback only printed a note | `render_qa` check `photometry_bound`; the driver remaps like `worker_entry.py` |
| The duvet slid 0.6 m and hung onto the floor | Cloth was too elastic and unpinned, and a simulation's output was trusted without numbers | Pinned head edge, stiffer cloth, floor collider; `render_qa` check `cloth_plausible` |
| Oak lost its colour after reducing grain contrast | The contrast blend pulled toward a grey of equal luminance, not the photo's mean colour | Blend to the mean linear RGB (reflectance is still exact) |
| Blender 4.5 installed unverified | The checksum file name was wrong, and a missing checksum only warned | Per-release `blender-<ver>.sha256`; a missing checksum refuses unless `BLENDER_ALLOW_UNVERIFIED=1`; `verify.py` asserts it |
| All six props were recorded as downloaded while their folders were empty | The API shape was one level deeper than assumed, and there was no post-condition on files | Raise when a package has no URL; confirm files on disk |
| The glTF viewer showed nothing ("loadfailure") | Exporting lights marked `KHR_lights_punctual` as *required* | Export without lights; the reason is commented in `build_scene.py` |
| Nishita sky units and sun direction were unknown | They were never measured | `calibrate_sky.py`: rotation equals azimuth; x800 scale to lux, measured at three elevations |
| "Free modern bed" candidates were AI-generated meshes with no bedding and no licence | Provenance was not checked before proposing | Check the licence, the generator and the contents before shortlisting an asset |
| The project's agents (`render_critic`, `lighting_reviewer`, and the rest) were unavailable in the working session | Claude Code discovers `.claude/agents` only in the directory it was launched from; this session started in the parent folder | Launch Claude Code from `arch-pipeline/`; otherwise point a general agent at the generated role file. Noted in `docs/HANDOVER.md` |
| The render critic found five defects that every QA check passed | Guards covered only defects already seen, and two pushed the wrong way: a clipping ceiling rewarded flat, milky images | The critic (`render_critic`) reviews every set before the user sees it; tonal checks bound all four sides (`highlight_clipping`, `highlights_present`, `shadows_present`, `exposure_midtones`) |
| Thresholds set on synthetic images were wrong on real renders three times (window detail, colour cast, highlight floor) | Synthetic cases prove the logic, not the calibration | Every threshold records the real measurements it was set from: `render_qa.py` constants |
| A blue lamp-lit night passed `colour_cast` at 0.036 | The check was direction-blind and calibrated only on warm failures | Direction-aware: a lamp-lit night fails any cool cast above 0.02; daylight allows up to 0.05 |
| Lamps rendered far cooler than their 2700 K spec; the night came out blue and was nearly "fixed" by tuning white balance to 4200 K | `kelvin_to_rgb` used Tanner Helland's display-sRGB fit as linear light (2700 K came out as (1, 0.65, 0.34), not (1, 0.39, 0.10)); correcting with the camera hid the spec error | CIE 1931 blackbody in linear Rec.709, unit luminance; `verify.py` checks it against the published Planckian locus (dxy < 0.003). **Rule: fix a lighting spec at its source; never compensate in camera, exposure or look settings.** The camera uses a standard tungsten preset |
| Highlight-priority metering still clipped 4.1% | It assumed every AgX look reaches white at +5 stops | Measured through Blender's own view transform: None +6.5, Medium High Contrast +5.5, High Contrast +4.75 (`AGX_WHITE_STOPS`) |
| Highlight priority then underexposed two views (median 0.18 and 0.23) | There was no floor on overall exposure | `exposure_midtones` (median at least 0.30); protection capped at 0.7 stop; the tonal look falls back automatically instead of being tuned per view |
| Oak grain ran horizontally on wardrobe doors and across the gap between doors | World-space box projection has no notion of a member's length | Per-object grain axis from each piece's longest extent (`presentation._grain_triplanar`) |
| "Dark bronze" rendered pale tan | A stated finish was never checked against its own description | `render_qa` check `finish_matches_name` |
| The garden view was scaled by an HDRI mean dominated by its photographed sun | The mean included the sun | Anchor on the sky mean with the sun excluded (`_sky_luminance`); for overcast and night, one HDRI serves as light and view, scaled to stated lux by integrating the image |
| Curtains looked corrugated, and then still machine-made after cloth simulation | Pleats pinned uniformly survived the simulation; `soft_goods_simulated` proves the process, not the outcome | Irregular gathered heading that relaxes toward the hem. Shape realism is judged by the critic, not by a process flag |
| Light fixtures look like CAD blocks (flat opal disc, crude shades) | Downloaded low-detail Revit families; materials cannot fix geometry | **Open.** Swap the visual housings for detailed models, keeping Revit's position and the IES photometry (as proposed for the bed) |
| The critic claimed a garden darker than sunlit bedding was a defect | Sunlit white bedding (0.70) really is brighter than sunlit foliage (0.15) | Check reviewer claims against physics before turning them into guards |
| Another session edited the same repo concurrently | Broad `git add` would have committed its unfinished work | Stage only your own hunks; confirm with `git diff --cached` before committing |
| Window glass passed 100% of sunlight; the model says 85% | The fix for glass blocking shadow rays over-corrected to "perfectly transparent" with no data | Tv from the model's own material (transparency 85), sqrt(Tv) per face of the slab (the two-face trap already recorded for Radiance). Shown in each image's `caption.json` |
| Every view was metered separately, so a dark corner and a sunlit bed looked equally bright | Per-image auto-exposure optimises each picture and destroys comparability between them | Exposure and look locked across a set, absolute EV recorded; tonal checks become WARN under a lock. Principle: faithful before beautiful (ADR-0013 amendment) |
| Invented dressing and stand-ins were indistinguishable from design content | Nothing labelled what an image's contents were based on | `*.caption.json` per image: from the design, invented, stand-ins, assumptions; `--no-dress` shows the design only |
| `verticals_level` reported a 0 deg pitch for level cameras | The check read `matrix_world` before any scene evaluation; only the metered first view had one | `view_layer.update()` before reading scene state. A check that reads state must force evaluation first |
| "Detailed fixture swap" would have used generic nicer models | Appearance was treated as decoration, not design evidence | Swap only to the specified product (manufacturer family plus its own IES file); a design decision for the client |
| Lamp sources sat 57-466 mm from the fittings' emitters (a drum's light below the drum, a cone's above its shade) | Build, check, lux engine and render all read the family INSERTION height, so they agreed with each other. `check_bedroom` compared the insertion to the spec: circular. The host offset it set was inert for these pendants (offsets -700/-400 both emitted at 2243 mm) | `archpipe.fixture_source` measures the emitter (Light Source symbol apex, else lens). `check_bedroom` compares it to the spec within 25 mm and checks the housing stays below the ceiling; it failed 5/5 on the old model. `build_bedroom` finds the lever by measurement (`Ceiling To B.O. Fixture`) and refuses a placement that would push a fitting through the ceiling. Rule: a check must measure the thing the spec names, not the value the builder wrote |
| Two spec heights were physically impossible for their fittings: LT-01 at 2400 put the cone's shade at 2717 mm through a 2700 ceiling; LT-04 is surface-mounted and emits at 2600 by construction | The spec never said what `mounting_height` measured, and nothing checked a fitting's body against the room | The spec now defines it as emitter height. The builder refuses an impossible placement instead of forcing it. `check_bedroom` checks the housing is below the ceiling, proven in `tests/test_check_bedroom.py` on the real meshes. Resolved as a client decision (LT-01 2233, LT-04 2600) |
| The lamp-source regression test broke when the model was rebuilt correctly | It read the live `out/` extract, so fixing the defect deleted its own reproduction | Reproductions are frozen data: `tests/data/bedroom-fixture-meshes-pre-fix.json`. Live outputs are for checks, never for the regression that proves a guard |
| A photometric file described a different product from its fitting (a 594 x 24 mm strip file on a round drum; a 2-ft strip on a 6-ft linear) | The lux engine reads only the file; nothing compared the file's luminous opening with the modelled lens | `fixture_source.photometry_matches_fitting` (x2 size, x3 shape), reported by `make_render_input`, the MCP tool `check_fixture_sources` and every render caption. Tested on the real meshes, including negative cases. **Open**: LT-02 to LT-05 await the specified products |
| Design dimensions were silently invented when missing (`mounting_height or 2400`, `ceiling_height or 2700`, wall `thickness or 100`, proxy `height or 800`, `default_h`) | The falsy-zero lint asked "does 0 survive?", not "is this value specified?"; its scan also skipped `revit/`, where the 2400 lived | `verify.py` invented-dimension lint over `src/`, `scripts/` and `revit/`, proven on both historical forms (literal and named default). Dimensions are now required; a genuine fallback needs `# default-ok: reason` on the line (two remain, both justified) |
| The detail view was named for "bedside, pendant and pillows" but never framed the pendant (it sat at screen height 2.59, where the frame spans 0 to 1) | A view is a fixed camera over a design that moves, and nothing checked what it showed. I then misreported the cause as the height fix, without checking | `photoreal.VIEW_SUBJECTS` declares each view's design ids; `render_qa` `view_subject:<id>` fails when one is out of frame, proven on the real old framing. Framings are chosen with the projection model, which matched Blender exactly (0.075, 2.591). Claims are checked by projection before they are reported |
| A look retry overwrote the first render; when the retry also failed, the files on disk disagreed with the report and the exposure lock | The retry reused the output name | Retries render under `-retry` and are promoted only if they pass; the records are renamed with them. Proven on the real night door view |
| `colour_cast` could fail a warm lamp-lit night that is physically correct under the tungsten preset | Its only remedy would have been retuning white balance: a guard that pushes toward cheating | A warm lamp-lit cast is advisory (WARN); a daylight cast still fails. Rule: a guard must never have in-camera compensation as its only remedy |
| **Open**: the night door view fails `highlights_present` (p99.5 0.84 against 0.90) after the lamps were moved inside their fittings | The floor was calibrated on renders where lamps outside their shades blasted the ceiling: a guard inherits the defects it was calibrated on | Not lowered and not exposed up. Lamps are not modelled as visible luminous surfaces; the fix is the specified products. The skill now requires re-reading thresholds after an upstream fix |
| Captions did not say the sun came from a placeholder site | The site file's EXAMPLE status was never carried into the image record | Captions record the sun altitude and azimuth, plus the site's latitude, longitude, north angle and `placeholder: true` |

### Luminaire library (2026-09-24)

See [ADR-0014](decisions/ADR-0014-luminaire-library.md) and the `lighting-library` skill.

| Defect or finding | Why it was missed | Guard now in place |
|---|---|---|
| Signify's photometry and Revit file server is `Disallow: /` in robots.txt; bulk download was the obvious plan | The pages and the file server are different hosts with different rules | Read robots.txt and terms for every host before fetching. The catalogue reads only allowed pages; the person downloads files. `signify.fetch` refuses the host; `verify.py` checks the refusal and that no code calls it |
| Signify served a zip labelled `application/json`; Revit type catalogues are UTF-16 with a BOM | Extensions and content types were assumed truthful | `library.sniff` identifies by content (zip, OLE, UTF-16 `##` header, IES, LDT); tested |
| Converted LDT agreed with the manufacturer's IES in flux and peak but differed by up to 34% in single directions | EULUMDAT C0 and IES 0 degrees are different axes; totals cannot show a rotation | IES h = EULUMDAT C + 90, proven on all three Signify lamp sets (within 0.02%). Every imported product with both formats is compared direction by direction; a 90-degree-rotated pair fails the unit test |
| The emitter rule found nothing on a Signify family | Its luminous face is "Glass, White, High Luminance"; the rule looked only for "lens" | `fixture_source.LUMINOUS_WORDS`; the IronPython copies are checked identical by `verify.py`, proven by reverting one copy |
| A headless Revit probe hung on "The parameter Apparent Load doesn't exist in the Family" | Type catalogues raise modal warnings; nothing answered them. The first handler then read a script global after pyRevit tore the scope down | `revit/unattended.py`: dialogs answered and recorded, the store bound at registration; probes run in `try/finally` with a watchdog. The user spotted the dialog |
| IronPython read UTF-16 as '' and died writing a registered sign (0xAE) mid-JSON | IronPython 2.7 text I/O is not Python 3's | Read bytes then decode; escape non-ASCII and serialise before opening the file (the trap `extract_model.py` already recorded) |
| Signify's Revit family says 3200 K and 3 W; its LDT says 3000 K and 23 W | Manufacturer BIM metadata is not checked by anyone | The LDT governs; the build writes its figures onto the family; `install.resolve` refuses a spec that contradicts the product |
| `housing below the ceiling` failed a recessed luminaire (body top 2732 over a 2700 ceiling) | The guard was written for pendants only | Mount-aware: recessed reports the recess depth needed as a coordination NOTE; test uses the measured geometry |
| A unit test exported a synthetic IES into the real product folder, which is deployed to the render worker | The export folder was a global default | `install.resolve(ies_dir=...)` in tests; `verify.py` rejects any product IES not in the library, proven with the real stray file |
| `git check-ignore` showed downloaded manufacturer files would have been committed | `assets/user/` was not ignored | Ignored; manifests carry source and hash instead of the files |
| The catalogue crawl lost 158 of 381 families (41%) and still looked finished | My URL builder dropped `prof/`, so every family listed only on the global site got a real 404; families also listed on a market site were rescued by the fallback, so the failure looked random. I first diagnosed throttling from a curl test that used the *correct* URL, and slowed the crawl for nothing | Key keeps the full path, tested. Coverage (families listed vs read) is stored with the catalogue and `luminaires.py crawl` exits 1 below 95%. Rules: **a scraper reports its coverage, never just its output**; **reproduce with the exact request the program made, not a hand-built equivalent** |
| Swapping to the 4300 lm lamp set over-lit the pillow: 501 lx against a 300-500 lx band | Not a defect: a swap changes results | Every swap re-runs the same requirement and lux gates (`scripts/luminaire_demo.py`, `out/demo/compare.json`) |

### Working practice (2026-09-24)

| Defect | Why it was missed | Guard now in place |
|---|---|---|
| A failing check was read as `exit=0` | The exit status came from `grep` at the end of a pipe | Read a command's own status (`$?` straight after it, or `PIPESTATUS`); never judge a gate through a pipe |
| A scripted edit "applied" but changed nothing after the indentation shifted | A string replacement that matches nothing is silent | Scripted edits assert exactly one match (`assert s.count(old) == 1`), then the changed behaviour is run |
| Windows file lock (`OSError 22`) when replacing an image being viewed, twice: in the render driver, then at the end of a 20-minute pipeline run | The first fix was local to the render driver, so the same error recurred in `run_bedroom.py`'s raw `shutil.copyfile` | Shared `archpipe.safe_io` (temp file plus retried replace) used by every writer of pipeline output; a `verify.py` lint rejects raw `shutil.copy*`, proven on the historical line. Rule: **fix a defect class where it lives, not where it was first seen** |
| A stopped pipeline run left `bedroom-run.lock`, and every later run refused to start | A killed process never runs its `finally`, and the lock recorded a PID that nothing checked | `run_bedroom.py` removes a lock only when its recorded owner is provably not running (`pid_alive`, which never signals: on Windows `os.kill(pid, 0)` would kill the process). A live or unreadable owner still stops the run |
| **Open**: right after a passing run, `run_bedroom --resume` once re-ran the downstream stages (6 s, worker jobs reused) where full reuse was expected; the next call reused fully | Not yet known. The test's pre-check (inputs and artifacts) agreed, so the likely differing key is `worker_runtime`, possibly captured before the run's own asset deployment. **Hypothesis, unverified** | None yet. Next step: record the runtime fingerprint before and after `worker_bedroom` and compare. `test_mcp.py --cached-run` catches the symptom |
| Tests "could not import archpipe" | Windows `PYTHONPATH` separates entries with `;`, not `:` | Use `PYTHONPATH="src;."` on Windows |
| `python` was not found from bash on Windows | The venv is not on the bash PATH | Call `.venv/Scripts/python.exe` explicitly |
| `highlights_present` failed soft overcast light | The rule "a photo has near-white somewhere" is true only with a direct source | Advisory without a sun or lamps (`test_overcast_without_direct_source_may_lack_white`) |

For a new failure, capture the input and expected versus measured result;
separate hypotheses from facts. Add a regression where it can catch the
same failure. Record the version/environment and link the owning code or
fixture here. Change a skill only when the lesson changes how the workflow
should be run. Change an agent role only when its responsibility changes.
Change an MCP tool when the reusable operation or its contract changes.

This is an explicit maintenance loop, not autonomous model training:
observed failure, regression, reusable fix, shared lesson, affected workflow.

For every defect, answer three questions before closing it:
1. **Why was it missed?** Which check did not exist, or which assumption
   went unverified?
2. **Which guard stops it recurring?** Prefer an automatic one: a
   `render_qa` or `verify.py` check, a script post-condition, or a
   regression test. Otherwise use a skill step, an agent instruction or an
   MCP tool.
3. **Does the guard catch the real defect?** Reproduce the defect and watch
   the guard fail. Checks that had only seen synthetic data missed the
   real case twice.

Do not copy bedroom coordinates, permissive example scope, or proxy
fallbacks into universal villa rules. A later real-site result must not
inherit the example's assumptions unnoticed.

## Evidence-aware design gates

Observed: existing rule records name books or general practice without edition-specific passages. Calculation tests validate arithmetic, not the target or its applicability. The new guidance boundary keeps those checks diagnostic and rejects wrong editions, unverified numerical transcriptions, incompatible climate assumptions and qualitative-to-numerical promotion. `tests/test_guidance.py` exercises these failures, the real bedroom obstacle case, source/artifact cache invalidation, project isolation and explicit approval bound to a reviewed content fingerprint. Missing facts and incomplete comfort/structure evidence remain unresolved even for attractive concepts.

Independent pilot critique caught a diagram route crossing a guest block although
the abstract connectivity graph passed. The diagram now reserves an entrance
strip; graph checks alone cannot establish plan geometry. Keep an explicit
diagram/graph comparison in the Order review, and mark incomplete narrative
facts missing or assumed rather than calling a generic pointer a known input.

## Product library and thermal (2026-09-24)

| Observed | Why it was missed | Guard now |
|---|---|---|
| A good texture (Poly Haven brown_leather) failed `maps_complete` | Map roles were guessed from file names (`_diff_`); this asset names its base map `_albedo_` | The source's role label wins (`find_maps(files=...)`); `tests/test_products.py` |
| A good model failed `polycount_match` (10 296 vs 2 548) | The published count's definition (base vs exported, subdivided mesh) is unstated | polycount is `not_checkable` with both numbers; size stays the gate |
| A model genuinely disagrees with its metadata (desk_lamp_arm_01 depth 202 vs 408 mm) | Nothing: the check caught it | Reported as failed, never repaired |
| The thermal hand check failed north by 16 % | It compared TOTAL solar with an isotropic sky; EnergyPlus uses Perez (north sky diffuse −17 %, south +34 %) | The check asserts beam only (within 0.7 %); totals are information; `tests/test_thermal.py` stops the change being reverted |
| EnergyPlus fatal errors returned zeros | A fatal run still leaves an empty SQLite file | `run_case` reads the `.err` log and raises on Fatal |
| Thermal results were 3.6 million times too small | Ladybug already converts joules to kWh | Units are asserted per collection (`kWh`) |

## Knowledge index (2026-09-24)

| Observed | Why it was missed | Guard now |
|---|---|---|
| A file named "Neufert 6th ed. 2023" is the 1980 2nd English edition; "Lighting Design Basics 3rd" is the 1st (2004) | Editions were taken from download filenames | Editions confirmed from each copyright page before citing; `edition_note` records the mismatch |
| Building Construction Illustrated's PDF page labels are sequence numbers (191 where the page prints 5.45) | PDF labels were trusted | Labels chosen from three candidates by agreement with printed edge numbers; < 70 % marked UNRELIABLE; `tests/test_knowledge_index.py` |
| "overheating criteria operative temperature" returned nothing although Lechner covers it | Every word was required on one page | Partial-match fallback |
| The fallback then returned a page for nonsense words | One matching word counted as a hit | At least half the words (min 2); the negative test caught it |
| A book sent to the workstation arrived as 0 bytes, and the RAG system quarantined it as "unreadable PDF" | A piped ssh transfer failed silently | Copies are checked by sha256 on both ends before ingest |
| Every scp copy failed with "No such file" | Shell-quoting the remote path: modern scp (SFTP) takes the path literally, so the quotes became part of the name | Pass the remote path unquoted to scp and quoted to ssh; verify sha256 on both ends |

## Concept generator: the critic caught one defect, the drawing caught two (2026-09-25)

**Defect 1: a room too narrow for a door.**
- Generator v1 sized rooms at area ÷ band depth. A 6 m² bath in a 5 m band came out 1.2 m wide, and no door fits on 1.2 m of corridor wall.
- It was missed because the generator placed no door-width constraint.
- **Guard:** the critic caught it through `reachability` and `links_built`. The bath had no door and could not be reached. The generator now has a minimum run (`MIN_RUN` 1.8 m).

**Defect 2: circulation area and stretched rooms were invisible to the checks.**
- Only a look at the plan PNGs showed them:
  - the L and U corridors were long;
  - one U room was stretched to 54 m² against 6 m²;
  - the U's east arm was a stub;
  - an L upper floor overhung the ground floor.
- Every check reported pass or advisory.
- **Guards:**
  - `circulation_area` reports achieved against the schedule allowance;
  - `area_match` now fails a room more than 25 % off its schedule;
  - `upper_supported` fails upper rooms with no ground room beneath.
- Tests: `tests/test_concept.py`, with positive and negative cases.

**Lesson:** read the generated drawings before trusting a clean check table.


## Real-plan calibration: seeded-defect recall exposed extraction bugs (2026-09-25)

**Calibration runs** (critic checks against CubiCasa5k, `scripts/cubicasa_calibrate.py`, pre-registered):
- **Run 1** failed the 90 % gate (75.7 %). The images showed flaws in the check definitions:
  - open-plan kitchen alcoves borrow the living room's daylight;
  - garages and plant rooms have their own outside doors.
- **Run 2** used amended checks on fresh plans. It passed, but seeded-defect recall fell, which exposed two parser bugs:
  - a doorway is a gap in the wall, so it was read as an open-plan connection;
  - balcony doors were read as entrances.

**Guard:** recall on seeded defects is reported next to the quiet rate. A rising quiet rate with falling recall means the checks got more lenient, not more accurate.

**Final run** (fresh plans 601–900):
- window passed;
- reachability failed (87.3 %), because doors inside thick walls are not matched to rooms. It stays not calibrated.

**Lesson:** never re-score the sample used to design a fix. Every amendment is judged on untouched plans.

## Adding documents to the workstation corpus (2026-09-25)

`app.ingest_local` stages files and then runs `app.ingest`, which runs `app.parse_phase` from a temporary folder holding a per-run `config.yaml`.
- Setting `RAG_CONFIG` overrides that per-run config. The parse phase then loses the document IDs and falls back to an arXiv query, which currently returns HTTP 406.
- A relative `PYTHONPATH=.` also breaks in that temporary folder.

**Working command:**
```
cd ~/ai-projects/archpipe-knowledge-data && PYTHONPATH=$HOME/ai-projects/research-system-rag \
  ~/miniconda3/envs/agent-rag-research/bin/python -m app.ingest --paper-ids-file drop_in/<manifest>.txt
```
Use `app.ingest_local` for new drops, run the same way. The run on 2026-09-25 added TM59, AD G and AECOM: 35 documents, 20,345 points.

## Test fixtures with hand arithmetic fail like wrong rules (2026-09-25)

**What happened.** Twice in one session a new test failed because its fixture was wrong, not the rule:
- SAN-01: the fixture put a bedroom on the entrance storey, which made the expected WC mandatory;
- FURN-02: the bed position was hand-computed, and the "failing" case actually left 850 mm on one side.

Both were caught only because the failure was diagnosed before any code changed. The risk is "fixing" a correct rule, or loosening a test, to match a wrong fixture.

**Guard** (`tests/test_bed_clearance.py` is the pattern):
- build fixtures from the quantities under test (left gap, right gap, foot gap), not from coordinates;
- take sizes from the object the rule reads (`catalogue.CATALOGUE[...]`);
- assert the fixture's own geometry before calling the rule;
- test exactly at the threshold (750 passes, 740 fails).

**Practice:** when a new test fails, check the fixture's arithmetic first, then the rule.

**Third instance** (DOOR-02 test, same day): I expected contact where the leaf tip reaches the obstacle edge (83.6°). The leaf actually meets the obstacle's near corner first (71.6°), and the rule was right. The practice caught it before any code changed. The fixture docstring now states the geometry it relies on.

## IFC export: a 1000x unit error, and a wrong diagnosis of the checker (2026-09-25)

**The unit error.**
- IfcOpenShell's `geometry.add_*_representation` helpers take SI metres and convert them to project units. Passing millimetres made every wall and space 1,000 times too large.
- The counts (walls, openings, spaces) were all correct, so a count check could not see it.
- **Guard:** `tests/test_deliverables.py` reads the written file back through the geometry engine and compares every space and wall with the spec, to within 0.5 mm. It was proven to fail with the bug reinstated (a 10,004,499 mm wall against 10,004 mm).

**The wrong diagnosis.**
- The first read-back returned no vertices, and I concluded the Windows Python 3.14 geometry build was broken.
- The real cause: `create_shape(...).geometry.verts` read inline frees the shape before the buffer is copied, so it returned nothing or garbage.
- Keeping the shape in a variable fixed it. A second environment (the workstation) exposed the cause.
- **Lesson:** a "broken library" diagnosis needs a minimal reproduction that does not share my own code's pattern.

## Reading a real Revit 2021 model in 2027: two serialisation failures after a 17-minute upgrade (2026-09-25)

- Opening `omar.rvt` (Revit 2021) in 2027 upgrades it for ~17 minutes on every run. Both first runs then died at the very end, writing JSON:
  1. Arabic text in names broke IronPython's `json.dumps` (UnicodeDecodeError);
  2. in 2027, `ElementId.Value` is a .NET Int64, which the IronPython json encoder rejects (`1586207L is not JSON serializable`).
- Why missed: the extractor had only ever read models we authored ourselves, with ASCII names and in 2027-native files.
- **Guards:** `revit/probe_villa_inventory.py` saves the upgraded copy (`ARCHPIPE_SAVE_UPGRADED`, new file only) BEFORE any serialisation, so a late failure no longer costs another upgrade; `_clean()` coerces strings to unicode and any non-Python number through float/int before writing.
- **Lesson:** in a slow session, persist the expensive result first, then do the fragile work.
- The original's SHA-256 is recorded in `out/villa/original-sha256-before.txt` and re-checked after each run.

## Building the villa environment in Revit 2027: two API traps (2026-09-25)

1. **`ElementId(int)` is ambiguous in 2027 under IronPython.** It fails with "Multiple targets could match:
   ElementId(BuiltInParameter), ElementId(BuiltInCategory), ElementId(Int64)".
   - **Guard:** `build_villa_env._eid()` passes `System.Int64`.
2. **Mass-category DirectShapes are hidden in views by default.** The first 3D export showed the neighbours' windows
   floating in the air with no buildings. The read-back check still passed, because bounding boxes exist whether or
   not a view shows them.
   - **Guard:** context volumes use Generic Models.
   - **Lesson:** a geometric read-back proves the model, not the picture, so look at every exported view before
     showing it.

The checker `scripts/villa_env.py check` has its own negative tests in `tests/test_villa_env.py`. They cover
azimuth, a fence height, a missing slab, a column span and a level elevation.

## A stair modelled as one room hid a blocked foot (2026-09-25, found by the client)

- **What happened.** In villa concept A (round 2) the straight flight along the party wall had its basement foot at
  the street end. Only the flex room and the laundry touched that end, so the bottom step could be reached only
  through a room.
- **Why every check passed.** The critic treated the stair as a single room linked to the hall along its long side.
  The graph said "reachable", and nothing asked where a person actually steps on and off.
- **Guard.** The `stair_access` check in `src/archpipe/concept/villa.py`:
  - every stair room declares its `ends` (the foot on the lower storey, the arrival on the upper);
  - each end must open onto a circulation room;
  - a stair without declared ends fails.
  - `tests/test_villa_concepts.py::StairAccess.test_round2_defect_is_caught` rebuilds the real round-2 geometry and
    proves the graph alone passes it while the new check fails it.
- **Also:** the plans now draw UP/DN arrows at the stair ends, so a reviewer sees the route.
- **Lesson.** Check a stair by its two ends, not as a room. And read the client's own sketches before choosing a
  direction: the villa_01 docx sketch had the flight rising from the basement hall toward the street end.

## The stair was never built in 3D, and the model already said where it belonged (2026-09-25, client review r3)

**What was wrong** (Revit ids from `out/villa/omar-2027.rvt`; CAD `01-GROUND_FLOOR_PLAN.dwg`):
1. **Stairs existed only as 2D rectangles**, so nothing was ever checked against the structure we must keep.
2. **The round-3 straight flight ran into column 1590377.** Its top treads and headroom (x 3.82-3.98, y -28.47 to
   -28.16) hit the GF column and its basement copy 1614989, and the assumed front and party-wall beams. Revit's
   intersection filter confirmed all four.
3. **The street strip is an outdoor terrace**, not floor:
   - its street and east walls are 900 mm parapets;
   - it is reached through the 68"x80" sliding door in the living room's front wall.
   Rounds 1-3 put a study, then the GF stair landing, on it.
4. **The old stair bay was ignored.** The DWG marks the built stair opening (layer A-DETL, x 7.377-9.387,
   y -26.721 to -23.771), and the old PDF has a U-stair there with 280 mm goings. Revit's floors carry no opening,
   and the environment build deleted those floors, so the checked model no longer showed it.
5. **The dog-leg variant assumed a clear 2.2 m bay.** The facade columns project 0.51 m, leaving 1.85 m between
   their faces.

**Guards:**
- `src/archpipe/concept/stairs.py` models each stair as treads, landings and a 2.0 m headroom envelope, and
  clash-checks them against the columns on all storeys and the beams.
- The critic's `stair_structure` check fails a layout whose stair clashes.
  `tests/test_villa_concepts.py::StairStructure::test_round3_flight_hits_column_1590377` rebuilds the real round-3
  geometry.
- `revit/build_villa_stairs.py` builds the same solids in a copy of the environment model and runs Revit's
  `ElementIntersectsSolidFilter`. `scripts/villa_stairs.py compare` shows the two checks agree.
- The critic no longer allows rooms on the terrace (the GF envelope excludes it), and a test asserts it.

**Lesson.** A plan rectangle is not a stair. Before showing a stair, build it in 3D against the kept structure and
read the existing model's marks (openings, parapet heights) before the old sheets.

## Revit image exports: dark canvas, missing tag text, far-off level lines (2026-09-26)

- **Dark canvas.** Revit 2027 exports plan and 3D images on the dark UI canvas, and setting
  `Application.BackgroundColor` did not change it.
- **Tag text.** Room tags were created but did not show in the exports.
- **Level lines.** The surroundings 3D view carried level lines far outside the model, shrinking the model to a
  corner.

**Guards (in `scripts/villa_option_pdfs.py` and `revit/build_villa_option.py`):**
- Plan images: the background turns white and the white linework turns dark.
- 3D images: only the background changes. Recolouring bright pixels in 3D blackened the white wall surfaces; the
  first composed page showed it and was redone.
- Room names are placed from the known crop box (109.5 px/m), with Revit's own room areas from the read-back.
- Levels are hidden in 3D views, and the images are cropped to their drawn content.

**Independent check.** Revit's room areas agree with the concept tool's net areas (flex room 12.17 m² against 12.4;
kitchen 16.66 against 16.6).

## Extension blocks built against each other counted their joints as windows (2026-09-26, round 7)

The round-7 rooms under the ramp and deck are contiguous blocks from the street gate to the deck end.
`villa.window_faces` added each block's two end faces as external window faces, so the joint between the store
and the laundry (x 5.377), the laundry and the WC, and so on counted as windows. A closed habitable room placed
there would have passed `window` with no daylight at all. It was missed because every earlier extension block
(S5) stood alone in the yard, so no end face ever touched another block. Guard: faces shared by two blocks are
dropped; `test_villa_parking.Negative.test_a_closed_windowless_room_still_fails_window` failed on the real P1
layout before the fix and passes after it. The same pass removed the store's side on the client's kept 1.40 m
NE yard wall as a window face (`YardWall.test_store_side_on_the_wall_is_not_a_window`).

## Walls came through the ramp, and a 2.1 m door opened under a 1.9 m soffit (2026-09-26, client review r7)

Two model errors the client found in the round-7 PDFs; I had reviewed the same 3D pages and missed both.

1. **Walls through the ramp and deck.** `revit_spec` clipped wall heights under the ramp with a guard meant to spare
   the villa's east face (`min(y) < YE + 0.05: skip`). Every cross wall of the rooms under the ramp *starts* on
   that face, so every one was skipped and built 2.8 m tall, 0.5-1.35 m through the ramp and deck. The wall along
   the fence took the lowest clear height (1.45 m) over its whole length, leaving 850 mm open under the deck.
2. **A door taller than the room it opens into.** Doors were put at the middle of the shared wall with whatever
   leaf the template had; nothing compared a door head with the clear height where it stands. The lounge door to
   the store under the ramp sat where the clear height is 1.91 m.

Why it was missed: new element types (a sloping ramp, a deck) were added without a geometric post-condition
against what they touch, and my check of the built model was a look at the images. A look is not a check.

Guards: `revit_spec.clearance_problems` (walls above the soffit, gaps under it, door leaf + frame vs clear
height), run on the spec (elevation-check row, `tests/test_villa_parking.UnderRampFit`) **and on Revit's read-back**
(the builder now reads back every wall top and every door's type size; the checks page has a BUILT row). Proven
on the real as-built specs: 8 problems in P1/P3, 9 in P2/P4, before the fix; 0 after. Doors under the ramp are
placed by `villa_parking.door_fit` (slid to the high end, leaf sized: full 2.10, reduced to >= 2.0 for rooms,
cupboard height for stores, else the check fails), and the builder makes exact-size door types instead of the
nearest stock type.

Rule going forward: any new element that bounds a space (slab, ramp, deck, beam, infill) gets a clearance
post-condition against its neighbours, checked on the Revit read-back, before a PDF goes out.

## Smaller catches in the same session (2026-09-26)

- **A section drawn mirrored.** My drawn section across the NE yard wall put east on the right while looking
  from the street toward the villa; facing +x, east (+y) is on the LEFT, as Revit's own export showed. I had
  labelled Revit's (correct) image as mirrored. Guard: the drawn section and Revit's export sit side by side in
  the PDF, same direction; derive left/right from the view direction, never assume.
- **A locked model crashed the batch build.** `os.remove` on an option model the client had open in Revit killed
  the run after P2 and left an old read-back. The builder now saves beside a locked file (`-v2`) and says so.
- **A wall position assumed as fact.** The NE yard wall's thickness and side were labelled ASSUMED and sent for
  confirmation before building on them; the client corrected the side (flush with the villa face, not the
  column face). Keep asking before an assumption drives geometry.

## Round 8 catches: guards that disagreed with each other (2026-09-26)

Five defects in one round; each was caught by a second, independent check disagreeing with the first.

1. **A stair touching a column that Python passed.** The lengthwise U's half landing started at x 3977, the CAD
   face of column 1590377. Revit holds that column face at 3977.2; the Python clash test counts an overlap only
   above 1 mm, so it passed, and Revit's intersection filter (`scripts/villa_stairs.py compare`) flagged it.
   Landing moved 20 mm clear. Guard: `tests/test_villa_parking.RevitStairCompare` requires every stair an option
   uses to be in the Revit comparison and the comparison to agree; the checks page no longer claims "Revit
   agrees" for a stair that was never compared (`villa.REVIT_STAIR_COMPARED`).
2. **Doors and windows through columns.** Openings were centred on the shared wall with no knowledge of the kept
   columns: the S4/P3/P4 GF entrance and basement pantry doors ran into column 1590377, a ramp door into the
   column at x 7.0, and a window on a column would have passed too. Present since S4. Guard:
   `revit_spec.opening_problems` on the spec and on Revit's read-back (checks page BUILT row); openings are placed
   in column-free runs (`_clear_columns`), doors under the ramp in the highest column-free run.
3. **A window credited but not built.** The critic took the kitchen's 1.5 m east face as a window; a column split it
   into two 0.5 m pieces and the spec dropped the window, so the checks said lit and the model had no window.
   Guard: the critic's window faces now subtract the columns (`villa._minus_columns`), and
   `revit_spec.window_credit_problems` compares the critic's credit with the windows Revit built (read-back);
   `WindowCredit.test_the_real_false_credit_is_caught` reproduces the real case. Dropped openings are listed on
   the checks page. A seeded test had assumed the hall's 1.30 m street face could hold a window; the column
   leaves 0.69 m, so the fixture was wrong, not the rule.
4. **Checks rows hard-wired to one stair.** The stair rows always measured the old U (`u_in_old_bay`), so the new
   stairs' pages showed the old U's slab opening. Guard: rows use `villa.stair_model(lay['stair'])`.
5. **Rounding under a threshold, and an id collision.** `X_LOW` rounded to x 3.124 where the clear height is
   1.999 m (the laundry "at 2.0 m" was 1 mm short): now rounded up to the mm and verified. A new GF room reused the
   id `landing-gf` and silently replaced the straight stair's landing, breaking three checks at once: layout
   builders must not reuse ids (caught by the critic's entrances/stair_access/suite checks).

## The daylight study found the generator under-glazing every room (2026-09-26)

The first whole-building daylight run put kids bedroom A at 0.47 % ADF even in S1, with no deck in front of it.
Cause: the spec sized a window as its facade run minus 0.4 m each side (`L - 0.8`), a margin meant for the room's
corners; after round 8 the runs were already cut clear of the columns with their own 0.1 m margin, so the margin
counted twice. The bedroom got a 0.63 m window and its second run's window (0.39 m) was dropped. Every option was
under-glazed, which would have blamed the architecture for the generator's default. Now `revit_spec.REVEAL = 0.2`
m each side; S1's kids bedroom A reads 1.24 % (two windows, 1.03 + 0.79 m).
Why missed: no check tied window size to anything but a plausible default; nothing read daylight until now.
Guard: the whole-building daylight study (archpipe.daylight, validated) now runs on every option, and its results
table sits next to the SLL cards; a window rule that starves rooms shows as a column of red.
Also caught while building it: a glazed opening drawn as two coincident panes would square the transmittance
(`test_window_is_one_glass_pane_and_leaves_a_hole`); an opening that lands on no wall would silently become wall
(`VillaScene.test_every_opening_lands_on_exactly_one_wall`); `villa_env.py check` ignored the read-back path it
was given (now `--readback`); a PDF open in the viewer crashed the writer (now `safe_io.writable_path`).

## Climate daylight, and a JSON fix that only a real model could test (2026-09-26)

- **The JSON fix passed its unit test and failed on the client's model.** Cleaning values (Arabic text, .NET
  Int64) was not enough: the model holds text in U+0080-U+00FF (Arabic stored as mis-decoded bytes, e.g. 0xD8), and
  IronPython's own json string escaper tries to re-decode that as UTF-8 and throws. The unit test only exercised
  CPython. Guard: `revit/jsonsafe.py` now writes JSON itself (ASCII, every non-ASCII char escaped; byte-identical
  to json.dumps for ASCII data, tested), the extractor prints a full traceback on failure (the runner showed only
  the message), and the proof is running the extractor on `omar-2027.rvt` itself. Lesson: a serialisation fix for
  IronPython is proven only under IronPython, on the data that failed.
- **`solar.sun_position` takes UTC and ignores tzinfo.** Passing Cairo local time with a tzinfo gave the sun at 81 deg
  at 09:30. The docstring says UTC; the parameter accepts an aware datetime silently. Caught by plausibility.
- **Two pieces of the build tree were macOS binaries.** The Radiance source tarball ships prebuilt Mach-O tools in
  `ray/src/*`; copying them gave "Exec format error". The Linux build is `cmake-build/bin` (built the daylight-
  coefficient tools there: gendaymtx, rcontrib, rfluxmtx, dctimestep, rmtxop, all 6.0.1).
- **Climate-based daylight validated before use:** sky orientation (a vertical sensor facing the sun gets > 2x the one
  facing away, pre-registered; measured 3.7-7x) and daylight coefficients vs direct rtrace under the same gendaylit
  sky (pre-registered 20 %; measured 11.6 % and 2.1 %).
- **A camera that sees a wall.** One render spot (S1 view 1) faced a partition 1 m away because S1's rooms sit
  differently; comparable views need a spot open in every layout (view 5, down the basement's length).

## Windows chosen by the room behind them, not by the face (client r8 review, 2026-09-26)

- **The extension's end had a 0.8 m high-sill window (P1/P3) or none (P2/P4); the street door was capped at 2.4 m.**
  The generator decided a window by the room's occupancy: a utility got 0.8 x 0.8 at sill 1.5, a store got nothing,
  living rooms a garden door capped at 2.4 m. The client reads the facade, not the room list: the basement's street
  face is floor to beam today, and the extension's end is the only face it has onto the garden.
  Why missed: every check asked "does the room have a window" (window_credit_problems), none asked "is this face
  glazed as intended". Guard: `revit_spec.full_height_faces` (street face + every extension end) and
  `glazing_problems`, a post-condition on the spec and on Revit's read-back (PDF row "BUILT: street face and
  extension end glazed floor to beam"); proven on the real round-7 read-back (P1, P2, P3 all caught; quiet on P1's
  street door, which already fills its run). The dirty kitchen now always sits at the end
  (`test_the_dirty_kitchen_is_the_last_room_of_the_extension`).
- **The Revit window read-back echoed the spec.** Windows were placed as the nearest stock type by width only, at
  the family's stock height, and the read-back copied the spec's width and sill, so a guard on the read-back could
  never see a wrong window. Now `build_villa_option.sized_door(..., what="window")` duplicates an exact-size type and
  the read-back reports the type's width/height and the instance's sill as built. Lesson: a read-back that copies
  its input is not a read-back; check each field's source.

## Stair headroom from the tread tops, and a pinch round the void (client r9, 2026-09-26)

- **Headroom was measured from the wrong line, under the wrong soffit.** AD K Diagram 1.3 (card
  ukadk-stair-headroom-min) measures 2.0 m above the PITCH line; our envelope started at each tread top, which is
  up to one rise lower at the back of the tread. And the GF slab zone was taken as -200..0 (slab only), ignoring the
  0.10 floor build-up: the soffit is at -300. Together they sized the slab opening to x 8.537, which leaves 1.82 m.
  Why missed: the envelope boxes WERE the check, so the generator and the check shared the error. Guards:
  `stairs.straight` slices the envelope to the pitch line, `stairs.SLAB_SOFFIT` (tested equal to FLOOR_BUILDUP +
  SLAB), and `stairs.pitch_headroom`, an independent sampled check shown as an elevation row; proven on the
  round-8 opening (1824 mm, `test_the_round8_opening_is_caught`). The opening now runs to x 8.887 (2045 mm).
- **The way from the stair top to the bedrooms was 0.69 m where it turned round the void.** Every room passed its
  own width check; nothing measured the route between rooms. Guard: `villa.gf_route_width` rasterises the open
  floor (void + balustrade and half partitions removed) and finds the widest body that gets from the landing to the
  corridor's end; row "GF route from the stair top to the bedrooms" against card ukadm-hall-min-m42. Round-8 plan:
  0.59 m (0.25 m once the void was right); now 0.91 m, kids A's wall moved to void + 1.0 m and the kids rooms kept
  at 11.5 m2 by narrowing the family bath (1.82 m). The old S4 plan reads 0.21 m (superseded, not rebuilt).
- **r9 follow-ups.** A door beside a corner landed on both walls of the corner in the daylight scene (the parking
  pass rebuilds doors without their `span`, so the direction test could not see it): each opening now goes to its
  nearest wall only (`villa_daylight._owners`); `scene().openings` spec == placed for every case. An alcove of a room
  (`part_of`, the lounge under the stair's top landing) is sized, lit and glazed with its room, so the street window
  runs column to column (3.41 m) instead of stopping at a utility wall. Occupied rooms under the ramp (the cinema)
  get a ceiling row: 2.3 m over 75 % of the floor (card mh-dwelling-ceiling-min), proven failing when the room is
  pushed toward the gate.

## Furnishing D1: three checker gaps found by their own negative tests (2026-09-27)

- **A 20 mm grid lost every shared room edge.** The furnished-route raster filled rooms with strict inequalities;
  on a 20 mm grid the cell centres fell exactly on the edges between rooms, so every open-plan join became a wall
  and nothing was reachable (a 0.5 m body failed). Guard: half-open fills; `test_the_route_check_really_examines_rooms`.
- **The body was rounded down.** 914 mm on a 50 mm grid became a 900 mm body, so a 909 mm gap between two beds
  passed. Guard: 20 mm grid, body rounded UP (never kinder than the card); the same test reproduces the first
  draft's 0.909 m gap.
- **A corner is not a side.** A body grazing the last centimetre of a bed's foot counted as reaching the bedside;
  nodes are now the middle of the side (`_middle`). Seats facing a table are reached from the front or a side.
- **The seating card assumed no traffic.** The island's seated side first faced the cook's aisle and passed on
  the 813 mm no-traffic card. NKBA 2nd ed. (held) gives 1118 mm where people walk past behind the diners; the
  stools now face the tall wall with 1.31 m behind them (cards nkba-seating-walk-past-1118 / -edge-past-914;
  `test_stools_need_room_to_walk_past`).
- Also carded from the held originals: NKBA landing areas (sink, hob, fridge), seating width, and AD M Diagram 2.4
  zone 'a' (bedside furniture within 600 mm of the bed head).
- **Stair flight counted as floor; slivers counted as reached.** Adding stair ends and the principal bedroom's
  window (AD M Diagram 2.4 note 1) as route nodes, the negative test (a console at the stair foot) still passed:
  the raster let the body stand on the flight, and a 9 mm overlap counted as reaching a node. Guards: the
  basement flight, the GF opening and voids are not floor; a node needs up to 0.1 m of real overlap
  (`test_stair_foot_must_stay_reachable`, `test_principal_bedroom_window_must_stay_reachable`). The dining table
  is also checked extended to 2.8 m (`extended_table`).

## Re-furnishing D1 for the questionnaire and the bigger dressing (2026-09-27)

- **Furniture was placed against room outlines, i.e. inside the walls.** Room rects run to wall centre lines (or
  the outer face on the envelope), so pieces "against a wall" sat 50-200 mm inside it and every check passed.
  Guards: `clear_rect` for authoring; the checks take the spec's real walls (`_walls`, cut at doors) as obstacles
  (inside_room fails a piece overlapping a wall).
- **Pinned doors were re-centred.** `_clear_columns` moved a door placed with `door_at`; pinned doors now move only
  if they hit a column. The critic's `min_area` fix overwrote `w`/`d` (min_width read 1.0); now `a_net`.
- **A door can run into the wall across it.** The bedroom->dressing door at x 22.10 ran 153 mm into the 0.2 m
  south wall (clear 0.75 m), and `_walls` cut *every* wall at a door gap, perpendicular ones too, so the clash was
  also invisible to the route raster. The new guard then found three more: the ensuite door 26 mm into its wall,
  the deck slider 25 mm into the study partition (centred between column faces, but the partition stands 50 mm
  proud), and a false one, because a door with no `span` defaulted to "h" (the cinema door was never cut from its
  wall). Guards: the doors check measures each opening against the walls (`test_a_door_running_into_a_wall_is_caught`,
  proven at 153 mm on the real position); `_door_axis`; walls cut only parallel to a door
  (`test_a_door_without_a_span_is_cut_from_its_own_wall`). Fixed: DRESSING_DOOR_X 21.847, ENSUITE_DOOR_X 21.65,
  STUDY_DOOR to the partition face.
- **The principal-bedroom window guard switched itself off.** It keyed on `bed_king`; the client's queen bed is
  `bed_double`, so no window node existed and the check passed silently. Now keyed on the room (PRINCIPAL_BEDROOM);
  `test_the_window_guard_follows_the_room_not_the_bed_type`. Its strip also started on the wall's line: a 0.2 m
  external wall swallowed it; it now starts at the inner face.
- **A pocket door gave no route node.** Route nodes came from swing zones, and a pocket door has none, so the
  parents' cluster started its route at a piece of furniture and never checked the way in. Nodes now come from
  approach strips at every door (`_door_approaches`); `test_the_parents_entry_must_stay_passable`. This exposed
  real pinches, fixed in the design: the queen bed's foot had exactly 0.750 m (PARENTS_BED_DEPTH 3.00 -> 3.05:
  0.80 m), kids B's bed corner to wardrobe corner 0.75 m (bed 0.1 m north), the ensuite approach 0.82 m (rail
  0.1 m shorter), the lounge sofa end to the pantry (sofa 0.12 m east: 1.10 m).
- **The square body failed corners the path turns.** Supersedes "body rounded UP" above: the body is now a DISC of
  the path width with exact distances to obstacles (no grid rounding at all). A path's width is measured across
  the direction of travel; a square of the same side sweeps outside that width at a turn (the dressing: rail end
  and column 1.24 m apart on the diagonal, legs 1.05/0.94 m, refused). Negative kept:
  `test_the_body_turns_a_corner_the_path_turns` refuses a straight 0.90 m aisle; all earlier negatives still fail.
- Messages now state the width checked (750 in bedrooms, card ukadm-bedroom-route-750; 914 elsewhere).

## D1 furniture in Revit (Phase 2, 2026-09-27)

### D1 round-2 native detail payload (2026-09-28)

- **The option spec listed approved details that the Revit builder ignored.** Doors, windows and furniture had a build path, while `hatches`, `pocket_buildouts`, `balustrades`, `bath_fittings` and `ventilation` did not. `villa_furnish_build.py spec` now includes `round2_elements`, derived from those fields; `build_villa_option.py` creates a Walls-category pocket buildout, a native wall Opening and tagged detail solids. `villa_furnish3d.round2_postcondition` checks measured world boxes, categories, the host wall, the 1.2 m door, suite door, study windows and structural columns. `tests/test_d1_wp5.py` moves the real-spec hatch, shortens the door, removes a grille, moves a glass panel and raises a study sill to prove the guard fails.
- **A placeholder size is not structural design.** The stair spec leaves laminated-glass thickness `null`. The native detail payload uses a 20 mm representation and writes `ASSUMED` in Comments; the lead must replace it after structural sizing. Fitting and ventilation proxy sizes are likewise labelled. The option spec still has no lighting fixture records, so corrected fitting heights in `villa_lighting` cannot be reconciled by this Revit option build.
- **The first open-side glass extrusion projected outside the stair room.** Its nosing line is the room edge; adding thickness toward positive y put the entire 20 mm panel into the adjacent room. The payload now puts that thickness inside `stair-b`; the room check and `test_glass_panel_outside_stair_room_fails` catch the old direction.

- **A run's modules overran the run.** Building the dirty kitchen in 3D, its modules added up to 3.64 m on a 3.60 m
  run; the 2D plan drew them and the landing check measured them without noticing. Guard: the kitchen check
  requires modules to fill their run to 1 mm (`test_modules_must_fill_their_run`, proven on the real 3.64 m).
- Post-condition PRE-REGISTERED before the first build (`villa_furnish3d.TOL`): each Mark built once, every face of
  its box within 5 mm, category exact (bound by intent), and every furniture check re-run on the as-built
  footprints. First build: 65/65 elements, PASS. Negatives: 10 mm off, missing/doubled, wrong category, a
  wardrobe built 0.5 m out (`tests/test_villa_furnish3d.py`).

## D1 lighting, products and the villa renderer (Phases 3-4, 2026-09-27)

- **Function and beauty, both carded.** Function: 24 IES HB10 Table 33.2 rows (maintained lux, 25-65 column) read
  on the held original, each a card with its row as the regression needle. Beauty: pendant 762 mm over a table
  (Residential Interior Design Fig. 4.9), vanity sconces 914-1016 mm apart, accent aimed ~30 deg (Lighting Design
  Basics p. 62). The client's rule (flush downlights for ambient; pendants/spots only for task and centrepieces) is
  a test (`tests/test_villa_lighting.py`).
- **First drafts failed their own checks, and that was the point.** Sconces alone gave 87-142 lx on the basin
  counters (300 needed): sconces light faces (Ev), not counters (Eh); a task downlight in front of each mirror was
  added (`test_basins_lit_only_by_sconces_fail_grooming` reproduces the draft). The island middle, tall-wall
  counters, dirty kitchen run and kids' desks were also short and fixed in the design, not the check.
- **A fitting was labelled with the wrong room.** A dining fill placed across an open-plan join kept the room it was
  authored for; fittings are now labelled by the room that contains them (`test_recessed_fittings_sit_in_their_room_clear_of_columns`).
- **Manufacturer data: parse, never repair.** iGuzzini LDTs write 'ww/3000' for the CCT: the parser now reads one
  Kelvin value beside a label (two values stay None). The number regex matched a bare '.'. Underscore ST49 and the
  Laser Evo wall washer fail our LDT/IES pair check (59.8 %, 100 %) and are not pickable; their positions use generic
  or a stated substitute, named in every caption. Product pages are fetched within robots.txt (iguzzini.com Allow /;
  the asset API host has no robots.txt); the configurator's LDT buttons were used in the browser as a person would.
- **Git Bash rewrote '/en/...' CLI arguments into 'C:/Program Files/Git/en/...'.** Set MSYS_NO_PATHCONV=1 for any
  URL-path argument.
- **A render job resumed a stale result.** The driver's job id hashed the scene and IES files but not the renderer,
  so a calibration after a renderer change returned the previous run's files. The renderer's code is now part of
  the identity.
- **Blender exited 0 after a Python exception**, so a crashed render reported success with no images: the driver
  now runs Blender with `--python-exit-code 1`. The crash: the shell's walls-with-openings are keyhole polygons that
  revisit a vertex; faces are now built with a fresh vertex for a repeat.
- Calibrations measured on the workstation: IES downlight 167.25 lx vs 172.75 analytic (3.2 %); an 800 lm emissive
  opal sphere 9.71 lx vs 9.79 analytic (0.8 %). Exposure presets were pre-registered before the first render.

## D1 continuation audit (2026-09-27)

- The final render driver stopped on a 30-second SSH polling timeout. Its surrounding shell
  still returned success because its last command appended `EXIT 1` to a log. The workstation
  finished all fourteen 1024-sample images. Re-running the identical content-addressed command
  retrieved them without rendering again. Five images fail image checks; execution is not acceptance.
- The villa renderer reintroduced indirect-light clamping at 10 in calibrated lumen units,
  despite `build_scene.configure_render` documenting why this discards interior reflected light.
  It also left diffuse bounce limits at Blender defaults. The villa configuration now disables
  direct and indirect clamping and explicitly sets the bounce limits. Regression:
  `test_calibrated_transport_does_not_discard_bounced_light`. The real old configuration fails
  this test. This is a configuration fix, not yet a measured improvement: the planned three-view
  comparison was blocked by SSH connection permission failures. Exposure and fixture powers
  have not been changed. Do not claim corrected renders until that comparison and review run.

## D1 authenticity pass (client: "authentic to the daylight and lighting ... what the villa would look like after construction", 2026-09-27)

- **A document was taken as the client's brief without the client owning it.** villa_01_guidelines.docx set
  4000 K for the kitchen and dressing; the client: "I have never specified that specifically". It is now ADVISORY
  (client decision): sound targets adopted, all 47 measured and reported by `villa_brief.check`, none enforced;
  withdrawn targets carry the client's words; `test_no_4000k_source_anywhere`. Why missed: the lighting design
  consulted the published cards but not the project brief file at all; now the brief check runs with the design.
- **An in-scene lux measurement read 0 lx on every surface.** Its sensor camera sat 25 mm above the sensor with
  Blender's default 100 mm near clip, so it saw the inside of the worktop. Once fixed, the measurement agrees with the
  analytic direct calculation (island 1473 vs 1419 lx) and found three real design faults the analytic check cannot
  see: reading spots tilted off the pillows (135 lx, now 1141), a desk lamp enclosed by its own shade, and a reading
  spot INSIDE a perimeter beam (1 lx). Guards: `beam_clashes` + `test_no_fitting_in_a_beam` (proven on the real
  position), step markers only below the beam soffit.
- **Glass verified:** a single-sheet window transmits 0.700 (stated 0.70), a closed slab 0.850 (stated 0.85); the
  probe is part of --calibrate.
- **Unclamped transport brightens the images, physically.** Removing the indirect clamp made every room brighter;
  the measurement's total/direct ratios (1.07-1.3 in lit rooms) are ordinary inter-reflection, so the earlier dark
  images were the defect, not the new ones. Exposure stays pre-registered.
- **The render and the daylight analysis now describe one building:** `scripts/villa_daylight_finished.py` puts the
  render's faces and reflectances into the validated Radiance method (living ADF 4.1 -> 5.0 with the chosen finishes;
  grid points under furniture read the shade beneath it).
- Soft goods: duvets are cloth draped onto the beds' own parts (photoreal._simulate, unchanged); furniture and
  sanitaryware are declared procedural stand-ins in every caption.

### D1 renders, client review of draft 8 (2026-09-27)

- **The parents' bed rendered head-to-foot.** The generator rotation map swapped 0 and 180 against the generator's
  own docstring; its tall headboard stood at the foot and the duvet draped over it ("duvet flying on the end").
  Missed because nothing compared the generated piece with the plan's orientation. Guard:
  `test_generated_pieces_face_the_way_the_plan_says` (headboard and bedside drawers vs the plan's own parts; fails on
  the old map with the real pb-bed).
- **Duvets stood out stiffly past the foot in every bedroom.** The villa cut stopped 20 mm past the foot, where the
  bedroom standard hangs 0.30 m over the foot and sides, and the sheet started from the plan's h, not the generated
  mattress top. Guard: `test_duvet_cut_hangs_like_the_bedroom` (fails on the old cut: foot overhang 0.02).
- **Stone and wood read pink.** Textures were mean-matched in luminance only, so each photo kept its own chroma
  (Marble014 G/R 0.87, B/R 0.69 against the stated cream 0.95 / 0.86); the floor tinted every bounce. Measured on the
  linear EXR before changing anything: the wall in v13 was redder than a 2700 K source on 0.80 plaster, so the cast
  was in the scene, not the camera. Fix: per-channel mean-matching to the stated base colour at the stated
  reflectance (ADR-0013 part 7). No white-balance change: that would have hidden a real cause.
- **Forcing 24 mm on cameras framed for 16-20 mm cut the rooms.** The views guard checked only subject centres.
  Guard: every footprint corner must be in frame. Cameras now stand where a photographer would (`frame`: same room
  or its door opening, 0.30 m off walls, door leaf hidden for that view only); where 24 mm still cannot hold the
  subjects, 16 mm by client decision, with the measured angle recorded and checked.
- **1,780 zero-area triangles refused the whole draft on the workstation.** Corner radius equal to half a loft ring
  made neighbouring arcs share end points. Guards: radii clamped below half; `test_scene_passes_the_render_contract`
  runs the contract locally.
- **A lighting negative test depended on test order.** `villa_render.build()` binds the real products into
  `villa_lighting` for the process; with them the ensuite basin reaches 526 lx from its sconces alone. The first-draft
  reproductions now pin the generic photometry per test.
- **Open item, not fixed in the render:** the basement stair treads stand 50 mm (east) to 200 mm (west) off the party
  wall in the spec, with no stringer; the render shows the model as it is. To be resolved in the Revit
  reconciliation (a design question, not a render one).
- **Floating objects, found by a new guard, not by eye** (`archpipe.concept.render_support.unsupported`,
  `test_nothing_floats`, proven by `test_the_float_guard_catches_the_real_defects` on the real draft-9 lamp and
  marker): desk-lamp shades bracketed to the window glass (now table lamps on their desks); stair step markers 70 mm
  off the party wall (set from the tread edge; the treads stop short of the wall); 11 downlights 100 mm below the
  cove rooms' slab field and 3 under the ramp 155 mm below the slab (the lighting design assumes one ceiling height
  per room, and the parking model's ramp differs from the rendered ramp); 3 stair-void pendant cords ending at 2.70 m
  in a double-height void; corridor path markers 21 mm proud; a vertical sconce 30 mm off its wall. All now seat on
  the surface actually rendered (`_seat_recessed_on_soffit`, wall-marker snap, sconce bracket), recorded in the scene
  notes for the Revit reconciliation. Lux must be re-measured in the scene after these moves.
- **How the guard itself was wrong four times before it was right** (each caught by proving it on a real defect):
  a merged mesh (every door handle in one object) had a house-sized bounding box that "touched" everything -> split
  meshes into connected parts; bounding boxes of wall triangles around a window span the glass, and a fan over a
  KEYHOLE polygon covers the opening -> ear-clipping and an exact triangle-box (separating-axis) test; sampled
  points straddled a door leaf at exactly the tolerance -> exact overlap, not samples; a lamp arm "rested" on its own
  shade while the shade hung from the arm -> only building surfaces ground a group, pieces only join groups.

### D1 renders, client punch list (2026-09-28)

- **The parents' entrance was closed by a render-only detail.** The slatted headboard panel ran 0.6 m past the bed
  each way, across the doorless entry opening and the dressing door. The furnished-plan route check could not see
  it (it checks layout pieces, not render details). Guard: `render_support.blocked_openings` (doors: any piece;
  doorless passages 0.6-1.6 m: render details and hanging fixtures, which the route check cannot see);
  `test_openings_passable` reproduces the old pendant and door. It also found a real LAYOUT defect the Gate A checks
  missed: the parents' bedside table stood 0.23 m into the dressing door (clear 0.67 of 0.90 m), and a bedside
  pendant hung at 1.15 m in the entry passage.
- **A Codex fix cut an exterior wall; rejected.** Centring the 0.8 m dressing door at 22.05 put its leaf 53 mm into
  the 0.2 m east wall and Codex added a recessed jamb reveal. The lead's arithmetic had used the room edge, not the
  wall's inner face. Final: door centred 21.897 (100 mm return), bedside 0.35 m. Also corrected: the code comment
  and ADR attributed the lead's door decision to the client; the route waiver it implies is pending, not accepted.
- **A Codex pass removed every photographed normal map**, reasoning that tangent normals have no UV basis on
  box-projected meshes; the renderer already had `triplanar_normal` for exactly that. Restored for stone, paving and
  wood; fabrics keep the subtle weave bump. Reduced wood grain contrast is a finish CHOICE (a calm, low-figure
  veneer) and is now labelled as such in the material notes, not presented as physics.
- **Study windows: an inherited privacy rule overridden by the client.** The 1.7 m sill came from the ramp/deck
  privacy adjustment in `revit_spec._parking`; ADR-0014 records the client's big low-sill windows. Daylight, glare
  and privacy must be re-evaluated.
- **Hand-typed cameras went stale and some looked the wrong way.** Interior views are now declared by intent (room +
  subjects) and placed by `render_views.choose` (standing points 0.30 m off walls, 0.15 m off furniture or in a
  door opening; score = subjects wholly in frame, then how much of the room's design shows, depth, windows).
  Two slips found on the way: a point ON a room's edge was classed "inside" (its door stayed shut with the camera in
  the leaf) -> strictly-inside test; a basement camera "opened" the ground-floor door above it -> same-storey match.
  Where no point holds the subjects even at 16 mm, the build stops (the dirty-kitchen run and fridge face each
  other: the view's subject became the run).
- **Stair**: open risers kept; steel stringers, bearings, open-side balustrade and handrails added as ASSUMED
  construction details (for the Revit model). **Kitchens**: microwave, coffee machine, hoods and a dirty-kitchen
  fridge as ASSUMED appliances; the fridge replaced a cleaning column whose storage moved under the folding counter.
- **Plants were placed without asking where a person would put one**: the bedroom plant stood in the vanity chair's
  way, the study plant in front of the new low window. Moved to corners; no guard yet beyond float/openings.
- **The view chooser's first scoring picked uninformative frames** (render critic on draft 11, checked by the lead):
  the parents' view stood at the entry facing the windows (headboard out of frame); the dressing view was 60 % a
  wardrobe end panel 0.68 m from the lens. Terms added to `render_views.choose`: stand on the main subject's front
  side, penalise a piece within 0.8 m of the lens and in view, penalise subjects behind a wall in plan; the frame
  constraint weighted so no bonus can outvote it. Guards: `tests/test_render_views.py` -- facing and looming FAIL on
  the old scoring (proven); the wall-occlusion test did NOT fail on the old scoring (the family-bath camera had plan
  line of sight to the WC), so it is not yet proven on a real case, and the critic's "WC not visible" has another
  cause, still to be found on the next render.
- **An automated critic's claims are leads, not findings.** The Sonnet render critic was right about the bath
  tap, ladder, pillows, hood, coffee machine, mirrors, boxy sofas, framing and the six omitted QA checks (each
  confirmed in code); it recommended brightening the cinema and lounge, which would contradict the locked-exposure,
  no-enhancement rule; not done.
- **Final renders, first pass (2026-09-28).** The driver reported a finished 24-view job as "stopped without status":
  it read the status file just before the shell wrote it, then saw the process gone. Fix: re-read status before
  declaring the job dead (the identical re-run resumed and fetched the results, as designed). The first final pass
  also showed what drafts had skipped: exteriors by day on the interiors' exposure lock were blown out (own locked
  state `exterior-day` now); a windowless corridor by day with lights off was black (lamps on, lamp white
  balance); a street camera at garden level looked at the underside of the ground; from the street and the front
  yard only the boundary wall and the ramp enclosure showed, so the street elevation is deferred until the site
  frontage is modelled. Final-only views need at least one draft before the final set.
- **A render-side fix is not a design fix.** The fixture seating moved 14 fittings in the render only; the lighting
  spec (and so Revit) still put them 100-155 mm below the ceiling. Source fix: `villa_lighting` reads the finished
  ceiling (cove field, extension roof); the render's seating is now a check that must move nothing (test proven
  on the old heights). Root cause of the ramp gap: the parking model's deck clearance was extended under the
  extension roof, which the spec builds at ground-floor level.
- **A specified tint must be checked in the image.** The grey-green exterior (G/R 1.06) read warm grey under the
  sun in the finals; at 1.14 the sunlit facade samples G > R > B. **A published explanation must be measured**: the
  v04 window flag was first explained as "a plain neighbouring wall"; a ray-cast showed the villa's own boundary
  wall, then open sky (no context modelled there).
- **Landscape trees were placed at their CC0 asset's native size, checked only against a trunk setback.**
  `villa_landscape.TREES` placed a jacaranda (measured on ai-workstation from the glTF POSITION accessors,
  ops/workstation/library-manifest.json `bounds_m`: 19.3 m tall, ~24 x 19 m canopy) at scale 1.0, 18.30 m from the
  north facade -- inside the 1.5 m trunk-setback rule, since the RULE only ever checked the trunk POINT.
  The canopy, never measured, put jacaranda foliage through the parents' bedroom and the garden-living ceiling
  (draft renders v01/v02/v05/v07/v17). Missed because: (1) no prop-size data existed anywhere in the repo -- Codex
  had no workstation access to measure a glTF, and the lead's own figures were hand-copied from an ssh session, not
  checked in; (2) `villa_landscape.facade_distance`/`inside_yard` operated on the TRUNK coordinate only, with no
  concept of a prop's world-space extent. Fix: `ops/workstation/library-manifest.json` now carries a `bounds_m`
  (native glTF Y-up world AABB, node-hierarchy-aware -- naively unioning every accessor's own min/max silently
  missed that some Poly Haven packs, e.g. `shrub_02` and `searsia_lucida`, hold several complete plant variants as
  separate offset root nodes; the union must walk the node TRS chain) for every landscape (and, cheaply, every
  other) prop; `ops/workstation/fetch_asset_library.py` measures and drift-checks it going forward.
  `villa_landscape.prop_world_box` reproduces `villa_scene.import_props`' glTF-Yup-to-Blender-Zup convention
  (scene xyz = gltf x, -z, y; verified against a real headless Blender 4.2.9 `import_scene.gltf` of `tree_small_02`
  and `shrub_02`, matching to < 1e-4 m) and `extent_violations` checks the FULL scaled/rotated/translated box, not
  a point, against the building footprint (a) and the yard polygon by perimeter sampling, not just 4 corners (b) --
  the yard is L-shaped, and a corner-only test can miss a bite its re-entrant corner takes from a wide canopy.
  Height is now an explicitly labelled ASSUMPTION (3.5-4.5 m per tree; no cited mature-height figure for the
  requested olive, Olea europaea, is held in knowledge/library.json) rather than the CC0 stand-in's raw mesh size.
  Guard: `tests/test_landscape.py` freezes the real D1 draft placement and proves `extent_violations` fails on it
  and passes on the corrected `TREES`/planting tables; four planting props (searsia, one grass, the rooibos, one
  shrub) also needed a smaller scale once their true multi-variant bounds were known, not a moved point.
- **Wood grain rotated into a Box-projected texture reads as a smeared streak, not a rotated grain.** Client:
  stair tread wood (v11-stair-void.png) and the ensuite vanity front (v12-ensuite.png) both showed long streaks,
  "annoyingly fake". Cause, confirmed against a real Blender 4.2.9 import on ai-workstation: `villa_scene
  .add_material` redirects a material's `grain_axis` by ROTATING the Object coordinate fed into a Box-projected
  `ShaderNodeTexImage`, but Blender's Box projection reads which PAIR of that vector's three components a face
  samples from the face's own UNROTATED geometric normal -- rotating the coordinate does not rotate that pairing,
  so a rotation can point one of the two sampled components at the face's own normal axis (which never varies
  across that face), collapsing it to a single texel row/column. Missed because no guard checked a material's
  `grain_axis` against the actual shape of the mesh it was assigned to, and the codebase's own existing workaround
  (`"walnut-grain-x"`/`"oak-grain-x"`, identity rotation, already used for "horizontal tops and shelves") was never
  applied to the stair treads (`villa_render.py` hardcoded plain `"walnut"`) or the washbasin/vanity front
  (`part_material`, same). New bpy-free module `archpipe/blender/grain.py` (`mapping_rotated_span`) reproduces the
  rotation and the per-face-normal axis pairing (matching `villa_scene.triplanar_normal`'s own convention) in pure
  Python, so it is unit-tested without a Blender runtime. Fix: stair treads now use a new `"walnut-grain-y"`
  (proven non-degenerate on the tread's Z-normal top face, and grains along its own 900 mm length, not its 280 mm
  depth); the vanity front now uses the existing `"walnut-grain-x"` (identity rotation -- proven non-degenerate
  regardless of which wall, and so which world axis, the panel's thin dimension ends up on, unlike `"walnut"`
  itself, which only degenerates for SOME wall orientations, which is why only some walnut surfaces show the
  defect). Guard: `tests/test_render_standard.py::WoodGrainMapping` reproduces the real collapse on the tread and
  on a vanity-front orientation, and proves the fix is non-degenerate. Not fully closed: an attempted visual
  (rendered-pixel) confirmation on ai-workstation was inconclusive -- real wood grain photos are intrinsically
  anisotropic, so a simple per-axis variance comparison cannot distinguish "correctly oriented grain" from "a
  collapsed axis" by itself; the geometric proof above does not depend on that measurement. Visually confirm on
  the next real render.
  Visually confirmed 2026-09-28 by the lead (second D1 round-2 draft, v11-stair-void.png): tread grain now runs along the tread.
- **The prop-extent guard only knew the GF storey, so the north planting bed stood inside the dirty kitchen.**
  Second round-2 draft, v17-dirty-kitchen.png: shrubs filled the basement dirty kitchen and showed through the new
  kitchen hatch (v01). Cause: the garden is at basement level, and the yard polygon's north strip runs over the
  basement store-ramp, cinema, guest WC and dirty kitchen; `extent_violations` checked only the GF rectangles
  (FRONT/BAR/BUMP), so a bed at x 13.0-14.05 inside the dirty kitchen (x 11.2-15.41) passed both tests. Missed
  because the first guard was proven only on the tree defect it was written for. Guard: `garden_level_rooms(lay)`
  feeds every level-B room to `extent_violations` and to the bed check in `build`;
  `tests/test_landscape.py::test_guard_fails_on_the_real_north_bed_inside_the_dirty_kitchen` shows the GF-only
  guard passing the real draft searsia and the room-aware guard failing it. The bed moved to the open strip
  east of the dirty kitchen.
- **A view subject can outlive the thing it names.** v07 kept the subject "terrace lounge set" after the
  landscape replaced that set, so the renderer matched no object and QA reported the subject out of frame.
  Guard: `tests/test_render_views.py::test_every_view_subject_matches_scene_content` mirrors
  `villa_scene.subjects`' matching over every view of the real scene.
- **A landscape change must close the route, roof edge and planting checks together.** The D1
  2026-09-29 artificial-grass rebuild removed the teak lounge, but the first scene export still
  failed `scripts/villa_render_views.py`: its terrace subject resolver required the old
  `landscape-sofa-` mesh prefix. The new bistro table retains that identifier as a documented
  view alias while its label and geometry identify the bistro. `tests/test_landscape.py` now
  freezes the old oversized tree and dirty-kitchen shrub, a sofa footprint across the garden
  approach, a plant at 0.3 times its maintained spread, a chair in the egg swing envelope,
  and a planter on the deck rail line; each violation has a passing placed-layout control.
  Run `villa_render.write()`, `scripts/villa_render_views.py`, both render-support guards,
  unittest discovery and `scripts/verify.py` after changing a garden prop. The Poly Haven
  `outdoor_table_chair_set_01` is absent from the checked manifest, so the bistro is a
  dimensioned assumed proxy until that asset is indexed and measured.
- **An asset stand-in's native size is a claim to check, not a default.** Codex placed CC0 trees without a
  workstation to see them; the first render showed the error. The lead must render or measure every new asset
  before trusting a guard that reasons about it.
- **The dirty-kitchen duct floated beside its hood.** Round-2 critic pass on the drafts (v17): the extract duct hung
  at x 13.30 while the hood chimney (over dk-run's hob) stands at x 13.827. The spec's fan position was typed in
  rather than derived from the hob, and the float guard passed it because the duct touches the external wall.
  Guard: `tests/test_d1_wp1.py::test_dirty_kitchen_duct_rises_from_the_hood_chimney` (the old x fails it). The
  same critic pass showed the fridge/oven bank in no view; v17 now names it as a subject. Critic claims were
  checked against scene data first: the hatch, pocket door, wall handrail, hand shower and library glass all
  exist, and those "missing" findings were misreadings of the drafts.
- **The stair's wall handrail was buried in the plaster.** Round-2 finals (v11): only the rail's brackets showed.
  The stair details take `wall_y` = -28.671 (the party-wall line), but the finished plaster beside the flight is
  at -28.471; the rail was offset 60-90 mm from the party-wall line, so it sat 0.11-0.14 m inside the wall. This is
  the same class as the dirty-kitchen chimney (room rect or structural line taken for the finished face). Guard:
  `tests/test_render_standard.py::BuriedFixtures` finds shell faces on the room side of a fixture within its span,
  and fails on the real old rail. The critic had called the rail missing; the scene data showed it existed and
  was hidden, so the fix is placement, not a new mesh.
- **A Revit wall Opening has no Mark or Comments, and the tag writer skipped them silently.** D1F round-2 build:
  the hatch Opening was built exactly (x 11.80-13.10, sill 1.0, head 2.1, correct host wall) but the
  post-condition reported "opening built 0 times", because `stamp()` finds no Mark parameter and writes nothing,
  and Revit 2027 names the category "Rectangular Straight Wall Opening". The synthetic read-back fixture had
  assumed a Mark. Now the builder records `spec_id` and logs the missing tag, and the check accepts the real
  category. Guard: `tests/test_d1_wp5.py::test_real_revit_opening_has_no_mark_and_is_matched_by_spec_id`, built
  from the real read-back shape.
- **A Codex job dispatched from the wrong directory could not write the repo.** Round-3 WP2 ran with the session
  sitting in the plans folder, so its only writable root was that folder; it worked on a copy and returned a
  patch. Guard: dispatch Codex only from the repo directory, and every Codex prompt now starts "verify you can
  write inside the repo; if not, stop and report".
- **A per-point recomputation made the lighting check 110x slower and the suite 4.2 hours long.** Round-3
  `villa_lighting.check` rebuilt the open-plan cluster (`villa_furnish._cluster`) for every fixture at every grid
  point (334k calls, 171 of 180 s). Fixed by computing each room's cluster once (1.6 s). Missed because no test
  bounds a check's run time; the suite's own duration (483 s vs 15,018 s) was the only signal.
- **A climbing plant was drawn as an 80 mm magenta box floating 0.30 m above the ground** (round-3 WP3); the float
  guard caught the lift, and the box itself is replaced by a realistic climber in the renderer (WP4).
- **The bougainvillea climbers were replaced by scattered leaf/bract polygons (WP4) but stayed sparse enough to
  read as "almost invisible"** (round-3 lead review, v01/v02/v24). `build_climbers` hardcoded `density=120`
  with no coverage target; nobody had checked what fraction of the trellis face that density actually covered.
  Missed because `test_climber_placement.py` only checked point counts and envelope containment, never coverage.
  Fixed by giving `climber_placement.py` an explicit 2D-Poisson coverage model (`coverage_estimate`,
  `density_for_coverage`) and having `villa_scene.build_climbers` call `density_for_coverage(target=0.80)`
  instead of a bare number. Guard: `test_old_density_fails_80_percent_coverage_on_real_envelope` reproduces the
  old default failing 80% on the REAL east-trellis envelope from `villa_landscape.py` (not a synthetic box), and
  `test_render_density_covers_the_real_east_trellis_envelope` proves the fix clears it on that same envelope.
  The four wall-trellis mass boxes were widened from 3-8 cm to 12 cm deep; the renderer clips each instance
  to that envelope. The regression also checks the east mass depth.
- **`artificial-grass` rendered as a flat, untextured mint-green plane** (round-3 lead review). Cause: the
  MATERIALS dict entry had no `asset` key, so `villa_scene.add_material`'s photo-texture branch
  (`if asset and kind in ("principled", "translucent")`) never ran and the court got a bare Principled BSDF
  colour. Every other "flat" finish in the file (paving, gravel, lawn) already carries an `asset`; grass alone
  did not, and nothing checked for that. Fixed by adding a real CC0 texture (ambientCG Grass002, verified to
  exist via `ambientcg.com/view?id=Grass002` before adding it -- distinct from the Grass004 set already used
  for the garden lawn) to the manifest and the MATERIALS entry, mapped at a 1.0 m tile.
  Guard: `ArtificialGrassGuard` asserts the material has an `asset` key that is a real manifest entry, and
  reproduces the old flat dict to show it fails that check.
- **The island/stair-void pendant globes read as "smoky grey glass", not glowing white opal** (round-3 lead
  review, v01-stair-void.png). Cause: the shell used `kind="glass"` (a rough, roughness=0.35, refractive
  Principled-BSDF dielectric). A rough glass BSDF has no bulk scattering: at most viewing angles it mostly
  REFLECTS the room (grey) and only shows the interior bulb through narrow refraction cones, and it also picked
  up `photoreal.architectural_glass()`'s shadow/diffuse-ray transparent mix, written for window panes, not a
  lamp shade. Fixed by switching to `kind="translucent"` (Principled diffuse + Translucent BSDF mix, already
  implemented in `add_material` for the curtains) -- a milky white diffuse body that also passes the inner
  bulb's light through DIFFUSELY, giving the glow-from-inside, no-hard-shadow look asked for, without inventing
  a new shader graph. Guard: `test_wp4b_fixture_and_dressing_parts` now asserts `kind == "translucent"`, a
  near-white `base_rgb`, and `transmittance > 0.4`.
- **The ensuite bath screen (`detail-pe-bath-screen`) read as a mirror, not glass** (round-3 lead review,
  v12-ensuite.png). Lead's diagnosis, confirmed by inspection: the mesh was a ZERO-THICKNESS quad carrying a
  refractive `kind="glass"` material (`glass-bath-screen`, interfaces=1). A ray entering the front face of a
  plane with no back face has nowhere to exit, so Cycles' glass BSDF effectively total-internally-reflects it
  back at the camera. The same defect class existed in two more places nobody had flagged: `detail-stair-guard`
  (two zero-thickness "glass-guard" quads) and `detail-stair-glass-*` (two PARALLEL faces with no side edges --
  closer, but still open on all four sides). Fixed by giving each a real closed volume: `box_faces` (axis-
  aligned: bath screen, stair guard) or the new `pane_faces` helper (non-axis-aligned: the stair glass follows
  the sloped tread-nosing profile), plus `interfaces=2` where it had defaulted to 1. The shell's `glass-clear`
  windows were the same zero-thickness class, so their quads are now closed 10 mm panes. The shader divides its
  stated total transmittance across the two interfaces. Guard: `GlassClosedSolidGuard` checks every `kind="glass"`
  mesh, including windows, for watertightness and positive volume, reproduces the old zero-thickness screen,
  and checks the architectural glass has two interfaces.
- **Dressing-room clothes were flat 25 mm vertical slabs from one shared, colour-agnostic fabric list, and the
  dressing shelves used plain "walnut" (grain_axis="z")** (round-3 lead review, v31/v32). The shelf defect is
  the same class already fixed once for the stair treads and vanity front (`archpipe.blender.grain`,
  2026-09-28): a horizontal top face's Box-projected texture reads one axis from its own thin dimension when
  that axis is rotated onto the face's constant normal direction. It was missed here because that fix was only
  ever applied to the pieces the client had actually complained about, not audited across every other
  horizontal "walnut" surface in the file. Fixed by using `walnut-grain-x` (identity rotation, the established
  safe pattern) for the dressing shelves and the wardrobe shell's thin side/back panels. Garments: rebuilt as
  a hanger (brass neck + shoulder bar, touching the rail) plus a tapered body. The first two-ring body still
  rendered as a broad flat slab in v31; six closed cross-sections now shape the neckline, shoulders, waist and
  hem, with shallow pleat relief on the front and back. They use an 8-colour per-partner
  palette (`garment-*` in MATERIALS) instead of the old shared 6-fabric list, with lengths tied to garment type
  (shirts 0.90-1.00 m, jackets 0.82-0.88 m, dresses/abayas 1.45-1.60 m per card neufert-longhang-drop-1600,
  trousers folded over the hanger 0.68-0.72 m). Guard: `DressingGarmentGuard` checks each partner's garments use
  more than one colour, that no garment mesh is degenerate-thin along either the rail or the front-to-back axis,
  that long-hang garments (hers only -- villa_furnish.py gives "his" no long-hang module) fall in the dress
  length range, that each body has at least five distinct height rings (the old two-ring slab fails), and that
  every garment mesh stays inside its own wardrobe module's x-extent (the same
  boundary-clamp idiom `climber_placement.placements` already uses). Both wardrobes now also have distinct
  lidded top boxes and paired heeled shoes under a hanging module; a scene guard requires their meshes.
- **The swing-arm reading lamp in the library nook was three flat brass boxes** (round-3 lead review, v02/v24):
  no round wall plate, no articulated joint, no shade -- it read as "tiny brass boxes", not a recognisable
  fitting. Rebuilt as a round D100 wall plate, two knuckle-jointed 0.30 m arm segments (matching
  `villa_lighting`'s own SWING spec, "articulated 0.6 m reach" -- exactly 2 x 0.30 m; the two library-nook
  fixtures both have a 0.48 m reach, which the new code solves as a two-link arm with a sideways knuckle
  offset, not a stretched straight rod), and a D120 conical shade angled down over the existing emissive disc.
  New helper `rod_faces` closes an arbitrary (non-axis-aligned) square-section rod between two 3D points, since
  the knuckle-jointed segments are not axis-aligned and `box_faces` cannot describe them; it is a small
  orthonormal-frame construction reused from `pane_faces`. Guard: `test_wp4b_fixture_and_dressing_parts` now
  also asserts a `swing-knuckle-*` mesh exists for every SWING fixture. If a future SWING placement's reach
  exceeds two 0.30 m segments (0.60 m), the code now flags it in the render notes and shows a stretched arm
  rather than silently rendering an impossible bend.
- **The first v32 dressing draft showed an empty shelf instead of his hanging clothes.** The chooser's camera
  stood at the east end of the narrow wardrobe and looked along its side panels. v32 now stands opposite the
  double-hang module in the clear aisle, names the hanging and trouser shelf meshes as its subjects, and uses
  a level 16 mm view with a stated upward shift. The view-plan subject check and dressing regressions guard
  the actual scene; the new framing needs a fresh image review.
- **The top-garden bench read as a huge dark block** (v25). Its native long axis is glTF Z, which becomes
  scene -Y; scaling all three scene axes by its 0.48 m native height made its 3.58 m length dominate the deck.
  The first correction gave it 1.80 m length but yawed the long axis toward the gate camera, so the next draft
  still showed a dark end block. The importer and world-box calculator now accept a three-axis scale for this
  prop: 1.80 m scene-Y length and 0.40 m seat height. The bench is oriented across the gate view.
  `bench_violations` checks both achieved dimensions and the long-axis orientation; its regression fails the
  old scale and an end-on placement.
- **The top garden looked bare** (v25/v26). The edge had only three plants on each side and no planted south
  perimeter. It now has four on each side plus low south-edge clumps from the held palette. The first updated
  draft still showed an almost bare north rail because the lavender prop was only 0.21 m across at its authored
  height. Two shallow northern containers now carry 0.55 m Ixora shrubs from the same palette. The existing
  extent, spacing, route and rail guards run on the resulting world boxes; `test_landscape` checks the planted
  north containers as well as the whole build.
- **The v26 camera stood in the potted olive canopy and v28 made the lemon pot fill the foreground.** Their
  authored positions were moved to the deck edge and farther west in the sunken north strip respectively, and
  the north bed gained a back and front plant. `camera_proximity_violations` uses actual prop world boxes and
  furniture footprints and fails the historical v26 position. The old v28 lens was 1.98 m from the lemon box,
  so a one-metre check could not catch it; `dominant_foreground_props` catches its measured 41.5-degree angular
  span in the 74-degree frame. The first eastward replacement cleared the pot but cut the garden doors out of
  the image; the final westward view uses 24 mm to include the strip and facade. Both checks pass the new positions.
  The one-metre clearance applies to exterior
  garden views; compact interior views retain their own standing-clearance rule. `villa_render_views.py` checks
  subject framing and emits `views-plan.png` for visual inspection. The final 64-sample v28 draft was visually
  checked: the doors line the right side, the beds and trellis are ahead, and the lemon no longer dominates.
- **v29 missed the under-stair storage joinery** because its former lounge camera faced away from the storage
  modules. A first correction put both storage footprints inside the view wedge, but its stair-room camera at
  x=9.577 looked through the stair treads: the draft showed only steps. The camera now stands northwest of
  the flight in the lounge and uses a stated 16 mm lens to hold both storage fronts. `under_stair_occlusion_violation`
  rejects the historical stair-room point; subject-framing checks still run on both joinery footprints.
- **v30 read black** because a windowless store used the day exposure. It now uses the evening exposure,
  turns its ambient layer to full output and states the missing window in the caption. The view regression
  checks the scene fields; a 64-sample workstation draft was visually reviewed and its shelving is legible.
- **The v25 exterior draft failed `window_brightness` although the glass was physically plausible.** The
  outside camera saw an interior window at median luminance 0.66 while the sunlit exterior reached 0.85;
  the QA check assumed every daylight camera was indoors and demanded a brighter view through the window.
  `villa_qa_context` now passes the view's exterior-camera state and `render_qa` applies that comparison only
  indoors. The v25 measured relation is the reproduction; `test_exterior_camera_does_not_require_a_bright_interior_window`
  checks that a dim textured window passes from outside while `test_dim_window_fails` still catches the indoor
  defect. Image detail and clipping checks continue to run for exterior windows.
- **The v01 interior draft failed window brightness by a 0.01 luminance difference** (view median 0.80,
  room 90th percentile 0.81). The strict comparison treated a one-percent sampling difference as a dark garden.
  The indoor check now allows 0.02 luminance difference; `test_near_equal_window_brightness_is_within_sampling_tolerance`
  uses the measured v01 numbers and keeps a materially dark view failing.

### authored-value-silent-override — a later pass silently overwrote authored camera values
- Observed: v29 authored at 16 mm (its own lens_basis needs 43.7 deg; 24 mm holds 36.9) rendered at 24 mm, cutting the
  storage out of frame; every authored lens shift was zeroed except v11's; v11 authored 14 mm / shift 0.30 / tilted
  target had always been rendered at 24 mm / 0.12 / level.
- Found by / stage: test_camera_24mm_level_at_eye_height during the lead's verification of the round-3 fix batch;
  should have been caught at scene export (the authored value and the written value were both known there).
- Reproduction: tests/test_render_standard.py::test_camera_24mm_level_at_eye_height (v29 lens_basis vs lens_mm).
- Direct cause: the authored-camera branch of villa_render's view pass assigned `c["lens_mm"] = 24` and a hard-coded
  shift instead of keeping the view's own values.
- Escape: the test stopped at the first failing view, so v32's overwritten shift stayed hidden behind v29's lens;
  no check compared the declared view with the camera written to scene.json.
- Contributing factors: two sources of truth for one camera (the `v(...)` declaration and the pass that "normalises"
  it); defaults written as assignments rather than fallbacks.
- Class: a normalisation pass overwrote an explicit, authored value instead of filling only what was missing.
- Siblings: any post-pass that sets fields on authored records (exposure groups, dimmers, captions, material fields).
- Control tier: 1 — the pass now only fills missing values (`c.get(...) or default`); v11's declaration corrected to
  what was rendered and approved (24 mm, level, 0.12). Tier 2 (planned, render gate R3b-0): assert every declared
  camera field equals the exported one unless the pass records why it changed.
- Proofs: fires on the real v29 (fails before, passes after); v32's authored 0.10 shift now kept; 87 render tests OK.
- Registry: authored-value-preserved (to register in L2).
- Also: a 0.02 pass tolerance proposed for window_brightness to pass the real v01 draft (0.80 vs 0.81) was reverted;
  the check stays as pre-registered and the flag is explained on the page (calibration rule: never tune a failing
  check to pass).
- **2026-09-29, library nook reading lamps mounted on the wrong face.** Client found both SWING plates low on the rear wall in R3b-2; Stage 5 lighting authoring should have caught it. The design positioned plates from the nook back edge; the reach guard checked only emitter distance and a longitudinal sweep, so the render and Revit detail payload repeated the placement. Class: wall fittings located from an outline instead of the finished mounting face. Siblings checked: nook recessed lamps remain ceiling mounted; other wall sconces use their own wall-face logic. Control tier 1: `villa_lighting.design` derives plates from the 25 mm side-panel inner faces in `villa_furnish3d.body`; render and native details consume `wall_plate`. Tier 2: `swing_envelope_problems` rejects a rear-wall plate or panel centreline. The 1.00 m plate/emitter height is **ASSUMED**: 0.55 m above the authored 0.45 m mattress, chosen for seated arm reach; the held `ies-res-chair-reading-200` card supplies 200 lux but no mounting height. Proof: `tests/test_d1_round3.py::D1Round3.test_swing_envelope_and_lighting_targets` tests the real old back-wall coordinates, a wrong-face mutation, the clean two-side case, and the maintained reading point. Registry: `nook-side-swing-mount` -> `swing_envelope_problems` -> that test -> Stage 5.
- **2026-09-29, study-to-deck slider lacked glazing intent.** Client found the R3b-6 1.80 m bypass slider opaque; Stage 4 opening specification should have caught it. The deck door was tagged `sliding` only, while the scene built glass only for `garden` doors, so the same omission reached the daylight scene, render, and Revit input. Class: an exterior sliding door expressed only by its operation, without its leaf material. Sibling checked: kitchen pocket slider remains open, while garden doors retain glazing. Control tier 1: the deck door now carries explicit clear-glass, 10 mm, two-leaf and bronze aluminium frame fields; the daylight scene consumes `glazed`; the Revit builder prefers a glass sliding family and labels a proxy when unavailable. Tier 2: `deck_glazing_problems` rejects lost intent before spec export. Proof: `tests/test_villa_parking.py::ParkingOptions.test_study_opens_onto_the_deck_between_the_columns` checks both real parking layouts and a removed-glazing mutation; `tests/test_render_standard.py::RenderStandard.test_study_deck_slider_is_closed_glass_with_bronze_frame` checks the closed 10 mm scene pane and frame. Registry: `deck-slider-glazing` -> `deck_glazing_problems` and daylight scene -> those tests -> Stage 4 / scene export.
- The nook correction exposed a lighting test-order trap: the generic lamp file gave 202 lux while the chosen measured file gave 154 lux at the first side-mounted position. `test_d1_round3` now binds the chosen product explicitly. Moving the two existing recessed nook lights on the same top panel to 0.47 m in from the sides and 0.11 m from the back achieves 255 lux at the held 200 lux reading point with the measured file, without beam obstruction. Registry: `nook-measured-product-task` -> explicit `bind_products()` and `villa_lighting.check` -> `test_swing_envelope_and_lighting_targets` -> Stage 5.
- The two rendered deck-door glass leaves are exported as separate closed meshes. Combining touching closed leaves in one mesh failed the existing watertight glass guard at their shared seam. The render regression checks twelve pane faces in the real opening; `GlassClosedSolidGuard` checks each exported mesh is watertight.
