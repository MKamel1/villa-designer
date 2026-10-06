---
Document Outline:
  - [Document Outline](#document-outline)
  - [Executive Summary](#executive-summary)
  - [Inventory of Tier 3 Lessons](#inventory-of-tier-3-lessons)
  - [Review Moments and Checklists](#review-moments-and-checklists)
  - [Moment A: Fact-Finding and Client Intent](#moment-a-fact-finding-and-client-intent)
  - [Moment B: Layout and Design Option Acceptance](#moment-b-layout-and-design-option-acceptance)
  - [Moment C: Camera and Composition Choice](#moment-c-camera-and-composition-choice)
  - [Moment D: Render Realism and Aesthetics](#moment-d-render-realism-and-aesthetics)
  - [Moment E: Evaluating Automated Checks and Critics](#moment-e-evaluating-automated-checks-and-critics)
  - [Moment F: Delegating Research and Debugging](#moment-f-delegating-research-and-debugging)
  - [Automatable Lessons and Measurable Signals](#automatable-lessons-and-measurable-signals)
Executive Summary: >
  This document establishes concrete human review moments and rigorous checklists for all 21 Tier 3
  engineering lessons from the architectural pipeline lessons audit. Each item is structured as a
  concrete question with an observable answer, grounded in verbatim citations from LEARNINGS.md, and
  details the verifiable evidence the reviewer must record. It also identifies candidate lessons
  amenable to future automated controls along with their measurable physical signals.
---

# Tier 3 Review Moments and Checklists

Tier 3 controls govern design aspects that depend on human judgement, client intent, or aesthetic
perception where no reliable numeric or geometric surrogate exists.

## Inventory of Tier 3 Lessons

The 21 Tier 3 lessons from [docs/lessons-audit.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md) are:

1. **l0027-direct-calculations-omit**: Direct calculations omit shadows and inter-reflection; an empty-room probe is calibration
2. **l0041-both-negative-bed**: Both negative bed shifts failed design review while the worker batch completed successfully
3. **l0045-claude-code-s**: Claude Code's actual session identified `claude-sonnet-5`; broad scientific work required substantial research before writing code
4. **l0058-five-render-rounds**: Five render rounds changed samples, textures and HDRI strength, and the images still read as CG
5. **l0086-curtains-looked-corrugat**: Curtains looked corrugated, and then still machine-made after cloth simulation
6. **l0088-critic-claimed-garden**: The critic claimed a garden darker than sunlit bedding was a defect
7. **l0102-colour-cast-could**: `colour_cast` could fail a warm lamp-lit night that is physically correct under the tungsten preset
8. **l0103-open-night-door**: the night door view fails highlights_present (p99.5 0.84 against 0.90) after the lamps were moved inside their fittings
9. **l0278-broken-library-diagnosis**: a "broken library" diagnosis needs a minimal reproduction that does not share my own code's pattern.
10. **l0415-wall-position-assumed**: A wall position assumed as fact.
11. **l0486-extension-s-end**: The extension's end had a 0.8 m high-sill window (P1/P3) or none (P2/P4); the street door was capped at 2.4 m. The client reads the facade, not the room list
12. **l0588-placeholder-size-not**: A placeholder size is not structural design.
13. **l0601-function-beauty-both**: Function and beauty, both carded.
14. **l0645-document-taken-as**: A document was taken as the client's brief without the client owning it.
15. **l0728-study-windows-inherited**: Study windows: an inherited privacy rule overridden by the client.
16. **l0738-stair**: Stair: open risers kept; steel stringers, bearings, open-side balustrade and handrails added as ASSUMED construction details (for the Revit model).
17. **l0743-view-chooser-s**: The view chooser's first scoring picked uninformative frames
18. **l0751-automated-critic-s**: An automated critic's claims are leads, not findings.
19. **l0768-specified-tint-must**: A specified tint must be checked in the image.
20. **l0880-bougainvillea-climbers-r**: The bougainvillea climbers were replaced by scattered leaf/bract polygons (WP4) but stayed sparse enough to read as "almost invisible"
21. **l0967-top-garden-looked**: The top garden looked bare

## Review Moments and Checklists

---

## Moment A: Fact-Finding and Client Intent

Conducted before generating candidate layout options or authoring primary envelopes.

### Item A.1: Client Brief Ownership
- **Lesson ID:** `l0645-document-taken-as` (`l0645`)
- **Source Quote (Verbatim):** "A document was taken as the client's brief without the client owning it." ([docs/LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L748))
- **Concrete Question:** Has the client explicitly confirmed and owned the project brief and its performance targets rather than accepting unverified external defaults?
- **Observable Answer:** Yes / No. (Must be Yes).
- **Evidence to Record:** Filename, timestamp, and message ID of the client's written sign-off message or document containing explicit approval of project brief targets.

### Item A.2: Existing Dimension and Wall Position Verification
- **Lesson ID:** `l0415-wall-position-assumed` (`l0415`)
- **Source Quote (Verbatim):** "A wall position assumed as fact." ([docs/LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L518))
- **Concrete Question:** Are boundary, party wall, and structural dimensions verified against measured survey drawings or client sign-off rather than treated as assumed facts?
- **Observable Answer:** Yes / No. (Must be Yes).
- **Evidence to Record:** Reference to the measured survey drawing file (DWG/RVT sheet ID, coordinate point) or signed client confirmation note with explicit wall alignment and thickness.

### Item A.3: Explicit Client Overrides of Standard Rules
- **Lesson ID:** `l0728-study-windows-inherited` (`l0728`)
- **Source Quote (Verbatim):** "Study windows: an inherited privacy rule overridden by the client." ([docs/LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L831))
- **Concrete Question:** Where standard privacy, setback, or sill rules are departed from, is an explicit client instruction recorded overriding the inherited constraint?
- **Observable Answer:** Yes / No. (Must be Yes).
- **Evidence to Record:** Link to the client's decision record (ADR reference or signed instruction note) approving low sills or rule overrides.

### Item A.4: Facade Composition and Glazing Intent
- **Lesson ID:** `l0486-extension-s-end` (`l0486`)
- **Source Quote (Verbatim):** "The extension's end had a 0.8 m high-sill window (P1/P3) or none (P2/P4); the street door was capped at 2.4 m." and "The client reads the facade, not the room list" ([docs/LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L589-L592))
- **Concrete Question:** Does the exterior elevation exhibit intentional floor-to-beam glazing on key street and garden faces rather than piecemeal per-room utility windows?
- **Observable Answer:** Yes / No. (Must be Yes).
- **Evidence to Record:** Signed elevation drawing sheet ID (PDF/RVT) confirming full-height glazing on the street face and extension garden end.

---

## Moment B: Layout and Design Option Acceptance

Conducted during spatial planning and option acceptance gating.

### Item B.1: Structural Placeholder Sizing
- **Lesson ID:** `l0588-placeholder-size-not` (`l0588`)
- **Source Quote (Verbatim):** "A placeholder size is not structural design." ([docs/LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L691))
- **Concrete Question:** Are all unengineered structural members, balustrades, glass extrusions, and transfer slabs explicitly labelled `ASSUMED` in specifications pending certified structural design?
- **Observable Answer:** Yes / No. (Must be Yes).
- **Evidence to Record:** Specification schedule or model parameters showing the `ASSUMED` comment annotation and structural review action item ID.

### Item B.2: Layout Visual Design Acceptance
- **Lesson ID:** `l0041-both-negative-bed` (`l0041`)
- **Source Quote (Verbatim):** "Both negative bed shifts failed design review while the worker batch completed successfully" ([docs/LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L144))
- **Concrete Question:** Does the proposed layout pass human architectural design review by the lead architect rather than relying solely on automated clearance and batch execution success?
- **Observable Answer:** Yes / No. (Must be Yes).
- **Evidence to Record:** Name of reviewer, review date, and approved layout PDF drawing reference in `out/acceptance.json`.

### Item B.3: Explicit Assumed Construction Details
- **Lesson ID:** `l0738-stair` (`l0738`)
- **Source Quote (Verbatim):** "Stair: open risers kept; steel stringers, bearings, open-side balustrade and handrails added as ASSUMED construction details (for the Revit model)." ([docs/LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L841))
- **Concrete Question:** Are tectonic and construction assumptions (open risers, steel stringers, bearings, balustrade fixings) explicitly recorded in the model notes as assumed construction details?
- **Observable Answer:** Yes / No. (Must be Yes).
- **Evidence to Record:** Notes section in the element specification detailing assumed structural stringers, bearings, and fixings.

### Item B.4: Lighting Function and Beauty Balance
- **Lesson ID:** `l0601-function-beauty-both` (`l0601`)
- **Source Quote (Verbatim):** "Function and beauty, both carded." ([docs/LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L704))
- **Concrete Question:** Does the lighting scheme satisfy both numerical maintained illuminance cards and aesthetic composition cards (pendant drops, sconce spacing, aiming angles)?
- **Observable Answer:** Yes / No. (Must be Yes).
- **Evidence to Record:** Recorded maintained lux values alongside specific aesthetic card citations (e.g., table pendant height 762 mm, vanity sconce separation 914-1016 mm).

### Item B.5: Final Lighting Evaluation with Inter-Reflection
- **Lesson ID:** `l0027-direct-calculations-omit` (`l0027`)
- **Source Quote (Verbatim):** "Direct calculations omit shadows and inter-reflection; an empty-room probe is calibration" ([docs/LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L130))
- **Concrete Question:** Is final lighting adequacy evaluated in a rendered scene with full multi-bounce inter-reflection and furniture occlusion rather than direct-light empty-room probes?
- **Observable Answer:** Yes / No. (Must be Yes).
- **Evidence to Record:** Multi-bounce render image ID and surface sensor lux log demonstrating indirect daylight and bounced luminaire transport.

---

## Moment C: Camera and Composition Choice

Conducted during view selection and render camera definition.

### Item C.1: Camera Subject Framing and Spatial Depth
- **Lesson ID:** `l0743-view-chooser-s` (`l0743`)
- **Source Quote (Verbatim):** "The view chooser's first scoring picked uninformative frames" ([docs/LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L846))
- **Concrete Question:** Does each camera view stand on the main subject's front/approach side, keep foreground elements clear of near-lens looming (<0.8 m), and frame the intended spatial depth?
- **Observable Answer:** Yes / No. (Must be Yes).
- **Evidence to Record:** Generated `views-plan.png` showing camera standing points, field of view wedges, and contact sheet of framed subjects.

---

## Moment D: Render Realism and Aesthetics

Conducted during visual inspection of presentation renders.

### Item D.1: Physical Cause Diagnosis Over Parameter Tuning
- **Lesson ID:** `l0058-five-render-rounds` (`l0058`)
- **Source Quote (Verbatim):** "Five render rounds changed samples, textures and HDRI strength, and the images still read as CG" ([docs/LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L161))
- **Concrete Question:** Were visible image realism defects diagnosed and resolved at their underlying physical cause (geometry, surface reflectance, light paths) before adjusting render samples or tuning sliders?
- **Observable Answer:** Yes / No. (Must be Yes).
- **Evidence to Record:** Diagnosis log entry confirming physical causes were ruled out or corrected prior to render parameter changes.

### Item D.2: Simulated Soft Goods Realism
- **Lesson ID:** `l0086-curtains-looked-corrugat` (`l0086`)
- **Source Quote (Verbatim):** "Curtains looked corrugated, and then still machine-made after cloth simulation" ([docs/LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L189))
- **Concrete Question:** Do simulated curtains, bedding, and textiles display natural gathering, irregular folds, and realistic relaxation toward edges rather than stiff machine corrugations?
- **Observable Answer:** Yes / No. (Must be Yes).
- **Evidence to Record:** Approved render preview image ID showing realistic textile drape and lead reviewer visual confirmation.

### Item D.3: Specified Material Tint Verification in Rendered Image
- **Lesson ID:** `l0768-specified-tint-must` (`l0768`)
- **Source Quote (Verbatim):** "A specified tint must be checked in the image." ([docs/LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L871))
- **Concrete Question:** Does the specified material tint (e.g. exterior facade plaster) sample with the intended chromaticity in the rendered image under realistic sun/sky illumination?
- **Observable Answer:** Yes / No. (Must be Yes).
- **Evidence to Record:** Image identifier and measured linear RGB pixel sample ratios (e.g., confirming G > R > B in sunlit areas for grey-green).

### Item D.4: Trellis Climber Visual Density
- **Lesson ID:** `l0880-bougainvillea-climbers-r` (`l0880`)
- **Source Quote (Verbatim):** "The bougainvillea climbers were replaced by scattered leaf/bract polygons (WP4) but stayed sparse enough to read as \"almost invisible\"" ([docs/LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L983))
- **Concrete Question:** Do climbing plants on wall trellises provide visible, balanced foliage coverage across the support lattice without reading as an empty or almost invisible scatter?
- **Observable Answer:** Yes / No. (Must be Yes).
- **Evidence to Record:** Render preview image ID showing visible leaf/bract foliage across the trellis frame.

### Item D.5: Terrace and Roof Garden Planting Fullness
- **Lesson ID:** `l0967-top-garden-looked` (`l0967`)
- **Source Quote (Verbatim):** "The top garden looked bare" ([docs/LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L1071))
- **Concrete Question:** Does the roof terrace or upper garden feature adequate container planting, perimeter shrubs, and ground clumps to avoid appearing barren?
- **Observable Answer:** Yes / No. (Must be Yes).
- **Evidence to Record:** Render preview image ID showing mature container planting and perimeter bed coverage.

---

## Moment E: Evaluating Automated Checks and Critics

Conducted when triaging diagnostic flags and automated critic reports.

### Item E.1: Automated Critic Claims Treated as Leads
- **Lesson ID:** `l0751-automated-critic-s` (`l0751`)
- **Source Quote (Verbatim):** "An automated critic's claims are leads, not findings." ([docs/LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L854))
- **Concrete Question:** Are automated critic warnings and suggestions investigated against underlying 3D scene data and photometric records before any modifications are implemented?
- **Observable Answer:** Yes / No. (Must be Yes).
- **Evidence to Record:** Written critic triage log distinguishing verified physical defects from invalid critic recommendations.

### Item E.2: Optical and Physical Validity of Critic Claims
- **Lesson ID:** `l0088-critic-claimed-garden` (`l0088`)
- **Source Quote (Verbatim):** "The critic claimed a garden darker than sunlit bedding was a defect" ([docs/LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L191))
- **Concrete Question:** When a critic flags relative brightness discrepancies between elements, is the finding checked against physical surface reflectance and lighting physics before action?
- **Observable Answer:** Yes / No. (Must be Yes).
- **Evidence to Record:** Physical surface reflectance and illuminance calculation demonstrating physical correctness (e.g., white bedding albedo 0.70 vs sunlit foliage 0.15).

### Item E.3: Physical Validity of Warm Tungsten Night Cast
- **Lesson ID:** `l0102-colour-cast-could` (`l0102`)
- **Source Quote (Verbatim):** "`colour_cast` could fail a warm lamp-lit night that is physically correct under the tungsten preset" ([docs/LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L205))
- **Concrete Question:** Does an advisory warm color cast warning on an interior night scene represent physically correct 2700 K emission under a tungsten preset rather than an unintended color error?
- **Observable Answer:** Yes / No. (Must be Yes).
- **Evidence to Record:** Camera preset metadata (tungsten) and luminaire CCT records confirming the cast is physically intentional without in-camera white balance tampering.

### Item E.4: Physical Shielding of Luminaire Highlights
- **Lesson ID:** `l0103-open-night-door` (`l0103`)
- **Source Quote (Verbatim):** "the night door view fails highlights_present (p99.5 0.84 against 0.90) after the lamps were moved inside their fittings" ([docs/LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L206))
- **Concrete Question:** When an interior night view fails peak highlight percentile thresholds, does the lower peak brightness reflect physical luminaire shielding rather than an underexposed scene?
- **Observable Answer:** Yes / No. (Must be Yes).
- **Evidence to Record:** Luminaire fitting inspection record and peak luminance histogram confirming lamps are correctly shielded within their housings.

---

## Moment F: Delegating Research and Debugging

Conducted during delegation of scientific research and troubleshooting tasks.

### Item F.1: Prior Research for Scientific Simulation Work
- **Lesson ID:** `l0045-claude-code-s` (`l0045`)
- **Source Quote (Verbatim):** "Claude Code's actual session identified `claude-sonnet-5`; broad scientific work required substantial research before writing code" ([docs/LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L148))
- **Concrete Question:** Was complex daylight, thermal, or scientific simulation work preceded by formal literature research, model verification, and formula confirmation before coding?
- **Observable Answer:** Yes / No. (Must be Yes).
- **Evidence to Record:** Committed ADR, literature citations, or research notes reference documenting the physical formulas and boundaries.

### Item F.2: Minimal Isolated Reproduction for Library Diagnoses
- **Lesson ID:** `l0278-broken-library-diagnosis` (`l0278`)
- **Source Quote (Verbatim):** "a \"broken library\" diagnosis needs a minimal reproduction that does not share my own code's pattern." ([docs/LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L381))
- **Concrete Question:** Before concluding that an external or third-party library is broken, has an isolated reproduction script been demonstrated that is completely decoupled from project codebase patterns?
- **Observable Answer:** Yes / No. (Must be Yes).
- **Evidence to Record:** Absolute path to the isolated standalone reproduction script and its terminal execution log.

---

## Automatable Lessons and Measurable Signals

While all 21 lessons are registered as human review steps, 6 lessons possess concrete physical signals
that could allow promotion to automated Tier 2 fail-closed guards in future iterations:

1. **l0768-specified-tint-must**:
   - *Automatable Control:* Isolate the diffuse albedo render pass under neutral D65 lighting; sample linear RGB on the target material faces; compute $\Delta E_{00}$ against specified linear RGB swatch.
   - *Measurable Signal:* $\Delta E_{00} \le 3.0$ between rendered albedo and specified product swatch.

2. **l0880-bougainvillea-climbers-r**:
   - *Automatable Control:* Calculate 2D projected polygon face area of leaf/bract geometry over the supporting trellis frame envelope.
   - *Measurable Signal:* Achieved coverage fraction $\ge 0.35$ (35% coverage target for young planting) across trellis boundary.

3. **l0967-top-garden-looked**:
   - *Automatable Control:* Audit container volume and planting counts along designated roof terrace perimeter bounding zones.
   - *Measurable Signal:* Placed container count $\ge 4$ on each terrace side and total shrub volume $\ge 0.50\text{ m}^3$.

4. **l0486-extension-s-end**:
   - *Automatable Control:* Group exterior wall segments by facade plane orientation and calculate glazed aperture area against total wall area.
   - *Measurable Signal:* Primary garden/street facade glazing ratio $\ge 0.60$ (floor to beam).

5. **l0743-view-chooser-s**:
   - *Automatable Control:* Project subject bounding boxes into camera viewport screen coordinates and perform z-buffer occlusion check.
   - *Measurable Signal:* Primary subject occupies $\ge 15\%$ of frame pixels and foreground occlusion within 0.8 m is $\le 5\%$.

6. **l0588-placeholder-size-not**:
   - *Automatable Control:* Lint schema on Revit parameters and specification dictionaries at the final delivery stage gate.
   - *Measurable Signal:* Count of components with `"ASSUMED"` comment flag equals zero at final stage gate.
