# D1 continuation — 27 September 2026

## Objective and authority

Continue Claude session `bedroom-spec-to-render`, identifier
`cd6cb945-c852-483d-afe5-cf5432265188`. Its local transcript is under
`C:/Users/mmbka/.claude/projects/C--Users-mmbka/`. The session began with
the villa method and bedroom capability example, then progressed to the
client's actual villa. Historical HANDOVER/RESUME documents predate this work.

The current objective is to complete furnished D1, verify the model and
lighting, and provide realistic construction-faithful renders. D2 follows
only after the client accepts D1. D3 remains a viable layout alternative.
The approved phased plan is `C:/Users/mmbka/.claude/plans/adaptive-singing-coral.md`.
The client approved proceeding on 27 September at 06:50 and 07:03 UTC and
explicitly requested the whole D1 scope through realistic rendering at 07:42 UTC.

The client reiterated during this continuation: authenticity to daylight
and installed lighting is paramount. Do not enhance images to hide a dark
design. Correct renderer errors, retain fixed comparison exposures, label
all assumptions, and change the physical design when a physical improvement
is needed. A pleasing image or software test pass is not construction proof.

Never alter original `C:/Users/mmbka/omar.rvt`; use project copies. Preserve
existing columns and beams. Licensed sources stay outside the repository.

## Recovered design decisions

- Real site is Sheikh Zayed. The interview supplies approximate orientation,
  neighbours, levels and setbacks; site-file plot/statutory examples are not
  a survey. Street facade faces approximately 290 degrees; model positive
  Y direction is approximately 20 degrees clockwise from true north.
- Original P1/P2 stair schemes and P5 were rejected. Keep the revised straight
  stair and verified storey rise/headroom. Extension stops at column five.
- Preserve the open garden connection. Cinema is under the ramp; the open
  kitchen handles light cooking and the separate kitchen handles heavy cooking.
- Fence top is one metre above ground-floor level. The northeast yard wall
  is 1.4 metres above basement level, flush with the villa face, about 250 mm thick.
- Family: two adults, three children aged 10, 6 and 3; two girls and one boy.
  Shared children's room has a bunk and separate desks. The other child has
  a separate room. Study supports homework, adult work and games.
- Five island seats, integrated fridge/freezer, one dishwasher, oven plus
  combination microwave, heavy-cooking kitchen with 600 mm gas hob and oven.
- Parents: 1600 by 2000 mm bed, vanity, enlarged two-sided dressing; ensuite
  gives 210 mm to dressing. Toilet must be at the south wall. Bath with shower
  over and single basin were the fit solution; do not imply separate shower
  and double basin were achieved.
- Cinema: loveseat for two, floor cushions and 85-inch television. Outdoor
  lounge seating, no barbecue; parking deck stays available for the car.
- General-purpose spots must be flush. Feature pendants, indirect coves,
  shelf lights, wall washing and low night lights were requested.
- Questionnaire answers did not override the original kitchen requirement
  of uniform 4000 kelvin light. Existing 2700/3000 kelvin kitchen sources
  conflict with that requirement and need resolution at the specification.

## Existing deliverables and evidence

- Round-12 layouts: `src/archpipe/concept/villa_r11.py`, outputs in
  `out/villa/designs-r12/`; daylight comparisons in `out/villa/daylight/`.
- Furnished plans: `out/villa/furnish-d1/D1-furnished.pdf`.
- Native copy: `out/villa/furnish-d1/revit/omar-option-D1F.rvt`;
  `readback.json` and `options-spec.json` accompany it. Historical read-back
  reports 65 furniture elements checked within 5 mm. This is not verification
  of later render-only finishes, lighting, ceiling details or dressing.
- Lighting/finishes: `out/villa/render-d1/D1-lighting-finishes.pdf`.
- Render authoring: `src/archpipe/concept/villa_render.py`; rendering:
  `src/archpipe/blender/villa_scene.py`; driver: `scripts/villa_render.py`.
- Original final job: `57a58cb2b1797d5f15bf6e0d` on `ai-workstation`, under
  `/home/omar/archpipe/villa-render/`. Fourteen views at 1920 by 1280 pixels,
  1024 samples, retrieved successfully in this continuation. Originals remain
  in `out/villa/render-d1/` with their reports. Nine pass image checks;
  v01, v03, v06, v07 and v08 fail. They are NOT accepted construction previews.
- Claude's apparent successful final task was misleading: the driver had
  timed out on an SSH read; a later shell echo returned zero. The remote
  render completed normally and was recovered without rerendering.

## Continuation work and remaining gates

1. Removed indirect energy clipping and set explicit bounce limits in the
   villa renderer. Shared bedroom measurement code remains untouched.
2. Added bounded retries for interrupted render-status reads, preserving
   detached-job recovery. Regression tests cover timeout, missing status
   and persistent disconnection separately.
3. Three-view diagnostic is in `out/villa/render-d1/transport-review/`.
   Unchanged exposure/lamps; energy transport alone changes v01 near-black
   pixels from 36.1 percent to zero and v08 from 16.6 percent to zero.
   This also exposes bright-material/daylight questions; it is not accepted.
4. Found single-sheet window geometry being treated as a two-interface slab.
   Specified 70 percent transmission became 83.7 percent. A villa-specific
   correction distinguishes window sheets from closed glass guards.
5. Independent render critic inspected all fourteen original full-size images.
   Plant source files contain multiple specimens that were imported together;
   floating/displaced plants are genuine scene errors. See the review report.
6. Remaining: validate corrected glazing and material energy behavior; verify
   installed-light calculations including occlusion; resolve kitchen colour
   temperature and generic fixture substitutions; reconcile render-only
   ceiling/finish changes with model and daylight analysis; correct plant
   assemblies and furniture detail without changing checked footprints;
   rerender, review, and package only after physical and visual acceptance.

No exposure, white-balance or fixture-power tuning is authorized as a way
to conceal a physics or design defect. Generic fixtures, assumed reflectances,
approximate site data and illustrative skies must remain plainly disclosed.
