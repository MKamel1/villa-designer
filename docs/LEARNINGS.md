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
