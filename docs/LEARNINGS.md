# Reusable engineering lessons

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
