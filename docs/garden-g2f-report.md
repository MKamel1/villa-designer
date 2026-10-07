# Garden G2 render-review fixes

2026-10-06. Resumed the uncommitted package after the usage limit; preserved G3,
shared-data symlinks. Identifiers now follow the recorded client convention. No presentation images or commits.
Client directions: model −x = **North**, +y = **East**, +x = **South**, −y = **West**.
Current IDs use North Garden for the street side, East Yard for the ramp/deck and open strip, and South Garden for the rear lawn. The exact historical aliases are recorded in `knowledge/site-orientation.json`. “GF balcony” is the client's name for the context
object still identified as `entrance-steps`. GF means ground floor.
All dimensions below are measured scene metres; areas are square metres.
QA means automated quality assurance. EXR is the linear high dynamic range
image format; HDRI means a high dynamic range environment image. UTC is
Coordinated Universal Time; UTC+02:00 is two hours ahead of it.
Review criteria are authored project criteria, not building or nursery standards.

## F1 — Strelitzia form

Cause: the shared clump builder put equal-height radial leaf rings above long
exposed stems. Its closed solid and species/envelope tests passed without
measuring actual foliage height or inspecting a neutral specimen. The real
frozen Strelitzia has a **0.660 m** bare gap above its root datum.

The Strelitzia builder now constructs 17 independent, overlapping upright
paddle blades with arching outer leaves and connected basal petioles, leathery
blue-green finish and the existing palette's young envelope. Actual blade
length divided by width is measured after normalization and must be 3–4.
The specimen remains an **ASSUMED young, non-flowering appearance**, not a
verified nursery product or manufacturer model. Flowering and photographic
likeness remain a lead/nursery judgement; no imported asset or route record changed.

The general `plant_form_findings` guard uses explicit leaf-face indices and
root-soil datum, so a stem reaching soil cannot hide a raised leaf mass.
Maximum authored foliage gap: **0.20 m**. The same measurement covers the
other basal procedural plants, G3 trough plants and deterministic climbers.
It fails on the frozen real Strelitzia, a translated/renamed sibling, a raised
leaf-only mutation and missing leaf metadata; current plants pass. The
Strelitzia paddle ratios are measured again from mesh vertices by the guard.

Inspected neutral previews: `out/garden-g2f/strelitzia-before.png` and
`out/garden-g2f/strelitzia-after.png` (1.8 m scale rod). The new silhouette reads
as upright blades rather than a cup; the front Aspidistra appearance remains
an unverified procedural likeness, distinct from the repaired Strelitzia.
Proof: `tests.test_landscape.LandscapeGuards.test_g2f_real_leaf_gap_clean_paddles_and_renamed_siblings`.

## F2 — GF balcony soffit

The offending mesh is the frozen **shell-039-paving**, source `entrance-steps`:
x −0.123…3.617, y −31.16032…−28.671, z −1.2…0. Its underside is 1.8 m above
the garden floor. The driveway ramp already had a white soffit; it was not
this defect. Semantic context assignment bypassed normal-based finish selection.

Every ground-only shell finish now passes the face-normal classifier, and
faces whose outward normal has vertical component below −0.7 receive
`ceiling-white`. A scene-wide guard checks every mesh and every material
slot, including buried faces, with no source-id exemption. The sibling audit
found **31 stepping/threshold stones and two top bench pads** with floor
finish on their downward faces. Those closed solids now use mineral stone
substrate on the underside through explicit per-face slots; Blender keeps
those assignments without splitting their physical solids. Geometry is unchanged.

The spec at `src/archpipe/villa_env.py`, `spec()`, describes this object as
“shared entrance steps from the street gate up to the core's GF entrance
(PDF)”. It builds a single GenericModel box, with no treads, risers, landing
assembly or balcony slab build-up. Consequently the **solid 1.2 m box is a
context placeholder**, not a detailed steps/landing construction. The client's
GF-balcony identification conflicts with the retained spec description;
construction/structural interpretation remains unresolved. This job corrects
its finish and does not invent a replacement structural design.

Inspected neutral underside preview: `out/garden-g2f/steps-soffit-neutral.png`;
actual Blender polygon/material read-back: `soffit-preview-evidence.json`.
Proof: `tests.test_render_standard.RenderStandard.test_g2f_real_steps_and_ground_siblings_have_no_paved_soffits`.

## F3 — North Garden enclosure, furniture and cameras

The active North Garden excludes the roofed basement strip. Its measured
rectangle is x −0.373…3.617, y −29.91566…−23.591: **25.235 m²**.
The excluded strip y −23.591…−20.351 is not treated as open garden.

The GF balcony covers **4.655 m²** of that active rectangle; the client's
plan interpretation therefore leaves **20.580 m²** before fence/wall areas.
The actual exported scene also contains a downward slab at z −0.2 and the
upper-storey `apartment-above-front` projection over x 1.787…3.617,
y −28.671…−23.591. Including those and low wall undersides, the exact
architectural union covers **14.429 m²**, leaving **10.806 m²** uncovered.
The polygon includes boundary wall/fence land, so this is an enclosure screen,
not a usable-floor-area schedule. The client's statement that the rest is
open sky conflicts with those explicit modeled surfaces. No geometry was
removed to manufacture an open garden. See `court-corrected-domain.json`.

| Retained item | Measured footprint | Cover / total footprint | GF balcony portion |
|---|---|---:|---:|
| Swing | x 1.867…3.333; y −29.063…−27.637 | 2.090 / 2.090 m² | 0.575 m² |
| Bistro | x 1.662…2.438; y −25.566…−23.734 | 1.205 / 1.421 m² | 0 m² |
| Planting bed | x −0.05…1.50; y −29.80…−26.90 | 1.750 / 4.495 m² | 1.750 m² |

The bistro's authored centre remains **(2.05, −24.65)**. The swing's authored
centre remains **(2.60, −28.35)**. Asset anchor coordinates differ from these
centres because their native bounds are asymmetric; report JSON retains both.
Both labels retain **“relocated from the south garden; client to confirm”**,
as explicitly requested even though the client now calls that side South.

Sun/sky screen from real opaque architectural triangles, at each footprint
centre 0.75 m above garden floor:

| Item | June 21 direct sun | October 15 | December 21 | Unweighted sky visibility |
|---|---:|---:|---:|---:|
| Swing | 0.00 h | 0.00 h | 0.00 h | 5.08% |
| Bistro | 2.00 h | 1.33 h | 0.67 h | 9.18% |

`garden_g2f_diagnose.py` uses 10-minute midpoint sun samples and 512
uniform-solid-angle hemisphere rays. Inputs are latitude 30.05°, longitude
31.0°, model +y true bearing 20°, UTC+02:00, dates in 2026. Sky visibility is
a fraction of unobstructed rays, not illuminance or a weather-weighted
sky-view factor. Glass, movable furniture and planting are excluded from
architectural obstruction. These city-level geometry screens do not verify
actual site weather, nursery suitability or the presentation's exact sky.

A 0.05 m grid tested 9,672 swing translations with its existing orientation
and 0.25 m motion allowance. Cover is tested on the actual stand footprint;
the motion envelope still clears all structural and furniture obstacles. Eleven initially passed the existing guards,
but their envelopes entered the **actual street fence thickness**, which
those guards omitted because the yard polygon follows the outer fence face.
The builder now supplies measured boundary solids as obstacles to the swing
envelope guard. All eleven are rejected by the current guard; zero candidates pass. The retained swing stays clean. `scripts/garden_g2f_placement_proof.py` reproduces this measured search.
This is a measured missing-obstacle defect, not an excuse to relax a clearance.
The record `open-placement-proof.json` preserves the search and a real rejected
candidate. A rigid bed move out from under the GF balcony needs at least
1.129 m toward model +y; the tested 1.149 m move overlaps the fixed door route
by 0.431 m². Retain the bed and swing and report the covered portions; a larger
planting/furniture redesign is unresolved. Bistro relocation is explicitly
excluded by addendum 3.

The old v36 lens at (0.7, −33.4, −1.65) was outside the yard on the sister
side. General `garden_camera_findings` now requires garden cameras to
stand inside the measured yard and outside architectural cover on their
own garden storey, or inside a
named measured room for a through-door/window view. The sibling audit also
caught v19 outside the yard; it gets an in-yard replacement camera.

A bounded 24 mm search found no open-yard single frame containing the whole
bed, trellis, pot, swing and bistro. Two views preserve the design:

- **v36**: open-sky North Garden standing point (−0.02, −23.85, −1.65),
  looking toward the complete bed, west pot and swing. It records the real cover.
- **v37**: North Garden trellis, bistro and east pot through the lounge;
  declared standing room `lounge`, position (5.35, −25.45, −1.65).
- **v19**: South Garden and living room from an in-yard point
  (28.30, −20.95, −1.65), replacing the outside-yard sibling camera.

All remain level at 1.35 m eye height and 24 mm. Declared room cameras use the
existing 0.15 m interior clearance; open-yard cameras retain 1.0 m prop/furniture
clearance. Camera-domain and foreground-frame checks are independent of view
ids and are proved on frozen old views, covered and wrongly declared points,
translated scenes and clean current views.

Final neutral preview paths: `out/garden-g2f/v36-final-neutral.png`,
`v37-final-neutral.png`, `v19-final-neutral.png`. Initial resume previews with
existing emissive fixture meshes retained are diagnostic only; the final
neutral pass replaces those emissive shaders with neutral diffuse materials.
All seven full-size specimen/material/camera previews were inspected by the independent render-critic before final camera integration. It accepted the cameras with explicit limits: the v37 pot hides much of the left seat/legs, the bistro hides lower trellis, and v19 does not clearly show the living-room sofa through glazing. The v37 foliage/bistro projected rectangle overlap is 28.45%, and bistro/trellis rectangle overlap is 29.72%; these are bounding-rectangle overlap measurements, **not actual occlusion percentages**. No claim of wholly unobstructed subjects or presentation lighting approval is made.

## F4 — south garden foreground mullion

Frozen old v28 projects actual `detail-window-frames` faces **116–119** into
the central third. Existing checks framed subjects and measured props without
projecting foreground opening members; batched glazing bounds also combine
many distinct openings. The camera moves 0.9 m within the dirty kitchen,
from y −22.5 to −21.6; geometry remains fixed. It stays level at 24 mm.

The guard identifies individual closed panes between the lens and subjects,
clips actual frame faces to the camera frustum and rejects central-third
occupation. It does not reject a remote facade window behind the primary
subject. It catches the frozen real camera, renamed/translated siblings, and
stays quiet on the new camera and remote-opening negative case. The through-
room declaration also prevents a roofed basement strip from being mislabeled
as an exterior garden standing place.

Inspected preview before the resume: `out/garden-g2f/v28-neutral.png`.
Final authoritative neutral preview: `out/garden-g2f/v28-final-neutral.png`.
Proof: `tests.test_render_views.ChosenViews.test_g2f_foreground_mullion_real_camera_and_translated_sibling`.

## F5 — South Garden v07 dusk cool cast

The requested `diag/v15-cast` branch/report is absent from this checkout.
The retained production data allow the same data-first investigation:
`cast-qa.json`, `cast-readback.json`, the resumed exact-context reproduction
`cast-resume-reproduction.json`, and their recorded source recipes under
`out/garden-g2f`. The production job `02a37ed6afd55121a2835ab5` has exact commit
provenance **7ae430d6072dbaba2b7959336aac9ca0dab263cf**, clean source.

Exact production QA context reproduces **0.090 cool; limit 0.02 cool**.
Earlier retained lawn-only and teak-seating images score 0.078 and 0.074 under
that same context; their missing commit provenance makes them corroborating
historical evidence rather than isolated revision experiments. This cast
**predates the lawn-only change**. No garden light removal appears in the
compared scenes; the earlier count of active interior lights differs.

The unchanged specified sky is Belfast sunset at 30 lux, camera white balance
4300 K. Its zenith-band linear blue/red ratio is **1.649**. The retained midtone
masks exactly match vertically flipped PNG luminance masks with values
strictly between 0.25 and 0.75, consistent with Blender's bottom-up pixel order. Production EXR
midtones have mean linear red/green/blue **1.663 / 1.742 / 1.833**, blue/red
**1.102**, already cool before display development. EXR means are rendered
linear pixel values, not lux measurements. The grass and paving texture-channel
normalization follows their specified material tints; it does not introduce an
unexpected blue tint. The locked production camera gain is −3.052 exposure
stops versus −3.706 / −2.413 in earlier sets. Metering applies a scalar, but
changing the developed midtone population affects the QA statistic, so score
differences cannot be assigned quantitatively to lawn removal alone.

The evidence is consistent with the specified directional dusk environment
and its current mix of reflected surfaces/interior light. No demonstrated
material or photometry conversion defect warrants changing the design.
**Report the faithful cast and retain its production QA failure.** No exposure,
white-balance preset, material tint, lighting or QA threshold was tuned. The
initial diagnostic-only neutral-card result is excluded: its near-zero values
came from a probe without an explicit scene reset, so it cannot substantiate
source attribution. This does not alter the measured production EXR evidence.

A first partial-run QA call omitted driver state and accidentally selected the
0.05 daylight tolerance. The retained corrected `villa_qa_context` call restores
`daylight=False`, `lights_on=True`, and reproduces the actual 0.02 limit.
This is reported evidence; it is not a pass or a presentation-render approval.

## Acceptance and handoff

Completed, judged by process exit status:

- **145 focused tests passed**, exit 0: landscape, render_standard,
  render_views, final_mounting, support_mounting, villa_scene_provenance,
  garden_render_subjects and asset_route_geometry.
- **3 additional affected regressions passed**, exit 0, after extending the
  camera domain check to upper garden views as well as lower views.
- **128 portable verification checks passed**, exit 0 with normal HOME and
  again with HOME set to an empty `/tmp/g2f-empty-home`; `NO_COLOR=1` throughout.
- Authoritative full scene: **`unsupported == []`, `blocked_openings == []`,
  `scene_contract == []`**, exit 0. Scene SHA-256 (content digest):
  `1ee61e28482e7e628d91368508546a268121bb6ff65ff889ae8bb738506daea8`.
- Complete view-plan checks passed, exit 0. Skill adapters synchronized;
  `scripts/sync_agent_assets.py --check` and `git diff --check` pass.

Evidence summary: `out/garden-g2f/acceptance.json`. Logs: `focused-tests.log`,
`upper-camera-regressions.log`,
`verify-normal.log`, `verify-empty-home.log`,
`current-validation/authoritative-acceptance.json` and
`current-validation/views-plan.png`. Registry:
`knowledge/garden-render-guards.json`; operating workflow and generated Claude
adapter updated with it. Neither shared symlink was modified. No package was
installed into the supplied Python environment. No commits or presentation
renders were made. Native-model and full-suite acceptance remain with the lead.

The first resumed focused run caught an obsolete negative test whose absolute
“wrong-way” target became a valid sightline after the camera moved sides. It
now reverses the current sightline. Another remote-window negative left part
of its bed beyond the glazing; it now places the opening behind all subjects.
These test corrections preserve adverse cases without changing production
thresholds. The independent render-critic accepted the final visible changes
before camera integration with the visibility limits stated above.

Rerender: **v28, v36, new v37, v19**, and other views exposing Strelitzia or the
corrected underside (including v27). **v07** retains an explained QA flag;
no corrective rerender is claimed necessary for its unchanged cast.

Current naming authority: [site orientation](../knowledge/site-orientation.json). Historical numeric sun-proxy results in this report are superseded by [the orientation and ray-cast report](orientation-naming-report.md).

<!-- garden-side: -x; name: north -->
<!-- garden-side: +y; name: east -->
<!-- garden-side: +x; name: south -->
<!-- garden-side: -y; name: west -->
