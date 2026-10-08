# G4d — brighten the north garden

2026-10-08 current-state note: [G4e](garden-g4e-report.md) renumbers the north
evening view to v42, records its v41 alias, rebuilds Rhapis/Aspidistra
appearance and corrects cameras. The G4d fixtures, aims, finishes and sky
remain unchanged. G4e reproduces the retained evening QA failure; the G4d
diagnostic evidence below remains historical.

Client approval 2026-10-07: pale gravel, light stepping stones and soft palm
uplighting. North means the street-side sunken garden, model negative x;
the corrected enclosure study records approximately 1.1 hours of direct June
sun there. This package changes finishes and adds fixtures/view only.
No bed, plant, swing, trellis, route or existing camera is moved.
Coordinates are in metres: x and y are the existing model's horizontal axes,
and z is vertical. Parenthesised coordinates list x, y, then z.

## Authored finishes

| Finish | Diffuse reflectance target | Basis | Pattern/scale |
|---|---:|---|---|
| Warm-white limestone-like gravel | 0.70 | ASSUMED dry pale mineral design target; no product or verified published value | ASSUMED 10–20 mm chips; metre-native nominal 15 mm procedural cells |
| Pale limestone/travertine-like stepping stone | 0.65 | ASSUMED dry pale stone design target; no product or verified published value | Subtle authored stone relief; pad geometry retained |

Reflectance means the fraction of incident diffuse visible light reflected.
Both materials record `basis_status`, `reflectance_basis` and appearance
status. Their linear red/green/blue colour is normalised to the stated
luminance target. The gravel pattern changes surface normals only. Its
neutral preview is an angular pattern proxy, not a photographed product or
a claim of realistic loose-chip geometry. Dirt, wetness and ageing may
reduce the eventual reflectance; supplier samples remain required.

The held-book search could not access the private source index in this
workstation environment. No limestone or marble reflectance citation is
invented. These are explicitly authorised design assumptions. Texture scale
is tied to the assumed physical chip range rather than the size of a mesh.

One retained gravel mesh covers north paths, balcony-understorey gravel and
gravel mulch between beds. All six north stepping pads receive the new
surface; every downward pad face retains `stone-substrate`. Other gardens'
gravel/pads and the natural feature stone remain unchanged. Both new names
are added to the independent audited finish list in `test_render_standard`.

## Evening fittings and direct-lamp screen

The imported project library searches at 2700 K and 50–300 lumens, and at
2700 K with outdoor mounting and no flux limit, both returned no verified
rows. No product is selected or claimed. Four ASSUMED generic
ground-bearing uplights illuminate the one Rhapis and three Fatsia clumps:

- 120 source lumens before each physical snoot, warm 2700 kelvin. An
  independent integral of the retained source distribution inside the
  actual 24-sided aperture's inner/outer cones bounds emitted fitting
  output at approximately 93 lumens each (approximately 373 total). These are
  ASSUMED point-source optical estimates before external foliage/ground
  obstruction, not measured product output. The record separates source
  flux from emitted flux; the shield cuts the source beam tail without
  changing the 30 degree half-maximum beam. Geometry/intensity stay fixed.
- 30 degree full beam width at half maximum; rotational cosine-power
  distribution generated as an ASSUMED LM-63 file, the Illuminating
  Engineering Society's photometric text format.
- Assumed colour rendering index 90 (metadata, not measured spectral data).
- Ground disc, short supporting stem, tilted solid head, glass lens and a
  physical black snoot. The lens is non-emissive, avoiding extra light outside
  the recorded 120 lumen source. The snoot is 120 mm deep with a 48 mm clear
  aperture radius and 12 mm lens radius.
- Each mount sits 220 mm streetward of its unchanged plant root in that
  plant's actual soil bed. The emitter is 65 mm above court grade and points
  toward foliage 800 mm above the same root. This is an assumed placement,
  not an installation clearance standard.

C4 denotes the project's finite mounting contract; each assembly is joined
to a live upward soil face through that API. C5 denotes the requested
fixture-record check: emitter, actual lens, photometry, shield dimensions,
plant target, light identity and C4 ground support agree. C7 denotes the
requested material-basis check. This checkout previously had no checks
under those names: this package supplies them for G4d; it does not claim an
audit of every legacy luminaire or material. No frozen baseline is widened.

The direct-lamp screen samples the actual lounge garden opening across its
3.810 m authored span at nine positions and two eye heights (1.20/1.35 m),
the two retained lounge camera points, and a 3 × 3 seated-eye envelope
around the swing (1.20 m above court grade). For each fixture/eye pair,
seventeen centre/perimeter lens rays cross the circular aperture plane.
A ray is blocked when it lies outside the opening, or behind the opaque
head. This measures direct lens visibility; it is not a human glare index.
The screen and physical shield record run during build, contract validation
and portable verification. On-axis and shortened-shield negative controls
prove that the screen can detect visible lamps.
The final result is **0 visible lens samples in 116 fixture/eye pairs**
(1,972 rays). The smallest radial clearance beyond the aperture at its
plane is **18.110 mm**. This is the measured geometric margin, not a glare
comfort threshold.

All four sources use the new `evening-garden` layer. No existing view
activates it; no new light source is active in a day scene. The day finishes
are intentionally lighter, as approved. Outdoor product ingress protection,
electrical supply, drainage and installation specification remain unresolved.
IP in fixture/caption metadata means ingress protection against dust/water;
no rating has been specified or verified.

## Camera and preview review

`v41-north-garden-evening` is a final-only exterior evening view at
(0.000, −26.400, −1.650) metres: inside the actual open-sky yard, 1.35 m
above its unchanged ground. Its 24 mm lens is level; downward lens shift
is −0.1618526878 in sensor-width units. It shows Rhapis, Fatsia, the swing
basket/cushions and a portion of pale gravel. The upper suspension/anchor
and full court are outside this detail. Only the evening garden layer is on.
The ordinary fixed exterior-dusk exposure/sky preset is retained.

Independent render-critic review accepted all refreshed isolated previews
and the neutral context view before integration. Exact plant vertices, rather
than empty bounding-box corners, establish complete framing. First-hit rays
reach Rhapis in 10/13 samples, Fatsia in 13/13 and the basket in 7/13;
partial foliage screening is disclosed. The shared Blender consumer now
reports actual vertices and a separate complete-frame result for views
declaring that requirement; an intersection-only flag cannot prove it.

Evidence under local `out/garden-g4d/`:

- `previews-reviewed/north-pale-gravel-detail.png` and
  `north-light-stone-detail.png`: neutral swatches, with companion 1.8 m
  scale-reference previews.
- `previews-reviewed/rhapis-uplight.png`: neutral warm-uplight close-up.
- `previews-reviewed/isolated-preview-evidence.json`: matching actual
  geometry, used-material and light hashes plus safe staging floor datum.
- `context-final/v41-north-garden-evening-neutral.png`: neutral camera
  diagnosis, not an evening presentation render.
- `acceptance.json`, `fixed-design-comparison.json`, `glare-evidence.json`,
  focused-test and portable-verification logs: measured final results.
- `preview-authority-comparison.json`: preview fixture faces, light records
  and materials match the authoritative export; source provenance is current.
- `foliage-beam-evidence.json`: each axis/cone intersects actual leaf vertices
  (3,141 vertices for each Fatsia and 5,301 for Rhapis); this checks direction,
  not achieved lux or illuminated projected area.
- `independent-preview-review.md`: final review scope and acceptance.

No presentation image was rendered. The new evening view is declared for
later rendering; these neutral diagnostics do not certify evening brightness,
photographic likeness, procurement or real-world glare compliance. Neither
protected shared symlink was modified. No package installation or commit.

## Validation

`scripts/garden_g4d_evidence.py` exits **0**. Plant-form, soffit-material,
garden-camera, unsupported, blocked openings, C4 mounting, C5 fixture record,
C7 material basis and G4d findings are all empty. Decoded existing geometry,
props, views and lights compare exactly. New-view physical proximity and
complete-frame checks are empty, alongside the recorded first-hit results.
No frozen known-findings list was expanded.

The final new/consumer/adapter batch runs **18 tests**, exit **0**; all changed
Python files compile. `scripts/sync_agent_assets.py` generated the adapters
after the skill update, and `--check` verifies all 38. Both normal and freshly
empty-HOME `NO_COLOR=1 scripts/verify.py --portable` runs exit **0** with
`ALL PASS`; the home directory is asserted empty before launch.

The broader affected render, mounting and provenance batch passes **135
tests**; the retained garden/view batch passes **36 tests**, both exit **0**.
The final flux-metadata correction is covered by the new focused regression
and refreshed portable runs; fixture geometry and source intensity are
unchanged. The lead runs the full suite.
