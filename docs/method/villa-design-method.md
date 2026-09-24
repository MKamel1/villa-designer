# The Villa Design Method (VDM)

**Version 1.0 · 2026-09-20**

A staged, looped, AI-led method for designing a private house.

---

## Scope and evidence authority

The original eight stages and thirteen backward loops remain the project method.
The [expert guidance packages](../guidance/README.md) strengthen each stage with
sources, methods, worked examples, failure cases, deliverables and approval criteria.
The [coverage matrix and acquisition manifest](../guidance/coverage-and-acquisition.md)
record the full scope and source needs.

This work covers private-villa design and visualization. Hotel references inform
residential aesthetics and comfort. Local-code research, permit documentation,
construction administration and engineering certification are excluded. Supplied
site restrictions are inputs with provenance, not a claim of legal verification.
“A+ luxury” means the client-approved quality brief, not a certification.

Earlier broad citations to Neufert, general practice, WELL and hospitality
practice did not verify the claimed numerical values or applicability. The
[rule audit](../guidance/rule-audit.md) now marks them unresolved. Readable citations
remain for compatibility; measured geometry does not establish a valid target.
The source registry distinguishes identified references from verified passages.

Structure, services, lighting, materials and landscape start during concept design
and develop together. Stage packages supersede historical claims of universal
minimum dimensions or design superiority in this document.

---

## Authority

**The AI leads. The client governs.**

| | Owns |
|---|---|
| **AI** | Proposing the design, running checks, explaining trade-offs, recommending one option, doing the work, flagging consequences |
| **Client** | The brief, aesthetic judgement, budget, gate approval, absolute veto |

1. The AI arrives with a **recommendation, not a menu**: what it
   recommends, why, the cost, and what it rejected and why.
2. A **veto is absolute** and becomes a logged waiver with a reason — not
   a silently suppressed warning.
3. Consequences of a veto are stated **at the moment of the veto**.
4. **Silence is not approval.** A gate needs an explicit yes.
5. Gate decisions are recorded in `docs/decisions/`.

---

## The eight stages

### Stage 0 — Intent

*Question:* who lives here, how, and what does "good" mean for them?

**Decisions owned:** occupants and how they actually live; daily and
seasonal rhythm; hosting patterns; ageing-in-place intent; storage
expectations; budget band; aesthetic direction.

**Method:** interview, not a form. The AI asks, the client answers, the
AI writes it back for correction. Reference images are read for concrete
attributes — palette, material, proportion, light quality — not adjectives.

**Artifact:** `brief.yaml`, taste board.

**Gate:** the brief is specific enough that a drawing could contradict it.
A brief that cannot be contradicted cannot be checked against.

### Stage 1 — Ground

*Question:* what does the site dictate before a line is drawn?

**Decisions owned:** orientation strategy.

**Inputs:** plot boundary and area; north angle; latitude and longitude;
topography and spot levels; access point; prevailing wind; views to keep
and to screen; noise sources; neighbouring masses and heights; trees;
services; statutory envelope (setbacks, height limit, plot ratio).

Sun path is computed from latitude and date — arithmetic, no service.
Orientation drives glazing, shading and outdoor space more than any other
single decision, which is why it is fixed here rather than discovered
later.

**Patterns:** 104 Site Repair · 105 South Facing Outdoors · 162 North Face

**Artifact:** `site.yaml`, orientation analysis.

**Gate:** orientation strategy fixed and justified against the sun path.

### Stage 2 — Fit

*Question:* does the programme fit the ground at all?

**Check:** sum of brief target areas, plus a circulation and wall
allowance, against permitted footprint × storeys. Plot ratio, height limit
and setbacks applied.

**Patterns:** 96 Number of Stories · 107 Wings of Light (plan depth must
let daylight reach every habitable room) · 109 Long Thin House

**Gate:** **the brief fits, or the brief changes.** This is the cheapest
place in the entire project to discover a mismatch, which is why it is a
stage of its own rather than a task inside concept design.

### Stage 3 — Order

*Question:* what are the big moves? Wrong here and nothing downstream
can rescue it.

**Decisions owned:** zoning (public / semi-private / private / service);
the intimacy gradient; the circulation spine — decided **before** rooms
are placed; response to orientation; level strategy and stair position;
wet-area stacking; massing within the envelope.

**Patterns:** 110 Main Entrance · 112 Entrance Transition · **127 Intimacy
Gradient** · 129 Common Areas at the Heart · 130 Entrance Room · 131 The
Flow Through Rooms · 133 Staircase as a Stage · 158 Open Stairs ·
205 Structure Follows Social Spaces

**Rules:** private rooms not reached through public ones; no room doubles
as a corridor; every habitable room has a daylight-capable aspect; living
spaces on the good aspect with service absorbing the poor one; wet areas
stack between levels; self-overshadowing; back-of-house circulation
separated from guest circulation.

**Gate:** concept coherent and approved. **Only now does the design enter
Revit.** Drawing walls before this settles is the expensive mistake.

### Stage 4 — Rooms

*Question:* does each room actually work?

**Patterns:** 128 Indoor Sunlight · 139 Farmhouse Kitchen · 144 Bathing
Room · 145 Bulk Storage · **159 Light on Two Sides of Every Room** ·
179 Alcoves · 180 Window Place · 184 Cooking Layout · 188 Bed Alcove ·
190 Ceiling Height Variety · 191 The Shape of Indoor Space · 196 Corner
Doors · 198 Closets Between Rooms

Treat the listed patterns as qualitative prompts until their actual passages
and applicability are verified. Do not interpret a count of window aspects as a
measured predictor of whether a household will use a room.

**Work:** dimensioned plans, sections and elevations; furniture and actual activity
tests; kitchens, bathrooms, dressing rooms, storage, doors, windows, ceilings,
shading and garden connections. Report actual measurements separately from
unverified catalogue targets. The [Rooms package](../guidance/stages/4-rooms.md)
defines the current deliverables and review.

**Gate:** activities and spatial relationships reviewed, evidence gaps resolved,
and explicit client decision recorded. A waiver does not verify a source.

### Stage 5 — Systems

*Question:* how do light, power, water, air, sound and temperature support life here?

Coordinate daylight, electric lighting, glare, scenes, controls, blackout,
acoustics, cooling, ventilation, power, plumbing and technology. Show equipment,
ducts, access panels and outlets in plans and sections. Use room-by-room comfort
targets and a coordinated ceiling plan.

Earlier lighting numbers and layer counts were not verified universal residential
requirements. Use [the Systems package](../guidance/stages/5-systems.md), scoped
evidence and project-specific targets. Direct-light calculations cannot establish
total-light uniformity or the absence of glare.

**Gate:** coordinated systems, appropriate measured studies, resolved evidence
and explicit client approval; no attractive rendering substitutes for these.

### Stage 6 — Substance

Materials, junctions, details, specification. Thermal and acoustic
build-ups; maintenance and cleaning access.

**Patterns:** 197 Thick Walls · 200 Open Shelves · 202 Built-in Seats

### Stage 7 — Proof

The drawing set out of Revit, and a check back against Stage 0 intent.

**Gate:** every Stage 0 intent is traceable to something in the design.
Compare plans, sections, landscape and day/night presentation together; expose unresolved issues and verify one reviewed revision.

---

## Inner loops

Design does not run forwards. These backward paths are named so they are
handled deliberately rather than as chaos.

| # | Trigger | Returns to | Typically changes |
|---|---|---|---|
| **L1** | Furniture won't fit; clearance or door swing fails | Rooms → Order | wall position, room size, bedroom location |
| **L2** | Rooms only work at sizes exceeding the footprint | Rooms → Fit | storey count, or the brief |
| **L3** | Can't hit lux or layering in this room shape; sockets clash; no wall for a unit | Systems → Rooms | room proportion, window position, furniture |
| **L4** | Wet areas don't stack; drainage or riser can't route | Systems → Order | which rooms sit where vertically |
| **L5** | Working massing exceeds setbacks, or overshadows itself | Order → Ground | orientation or massing strategy |
| **L6** | Circulation costs more area than the allowance assumed | Order → Fit | recompute feasibility |
| **L7** | Brief does not fit the plot | Fit → Intent | cut or restructure the brief |
| **L8** | Wall build-up eats internal dimension; a room that passed at nominal thickness now fails | Substance → Rooms | room size, or the build-up |
| **L9** | Material can't take the fixing or luminaire; acoustic build-up changes thickness | Substance → Systems | fixture or construction |
| **L10** | Render shows the feel is wrong although every number passes | Systems → Rooms/Order | aesthetic veto — the client's call |
| **L11** | Site reveals noise, overlooking or slope defeating a briefed requirement | Ground → Intent | the brief |
| **L12** | Documentation exposes an unresolved junction | Proof → Substance | detail |
| **L13** | Client changes their mind | any → Intent | anything — must stay cheap and recorded |

Furniture, wall build-ups and wet-area stacking can force costly rework. Review their dependencies early; no universal frequency or cost ranking is claimed.

### Thrash control

Loops without discipline are infinite churn. Four mechanisms:

1. **Cheapest-fix-first.** Every finding carries a fix ladder ordered by
   how far back each remedy forces the design. For a clearance failure:
   (a) move the furniture *[in-stage]*, (b) resize the room *[→ Order]*,
   (c) change the brief *[→ Intent]*. Most failures are fixable in-stage,
   and saying so prevents needless backtracking.
2. **Blast radius.** Before a change is made, compute what it
   invalidates — "moving this wall re-opens checks X, Y, Z and the
   lighting grid for two rooms" — so the decision is informed.
3. **Frozen decisions.** A passed gate freezes its decisions. Re-opening
   requires an explicit unfreeze with a recorded reason.
4. **Loop budget.** Count re-entries per stage. Three returns to the same
   stage means the problem is upstream — usually the brief — and the AI
   says so rather than iterating a fourth time.

---

## Rule classification

Every rule declares:

- **stage** — the earliest stage at which it is meaningful
- **severity** — `violation` (breaks a published minimum) / `warning`
  (recognised planning fault) / `advisory` (comfort, preference, taste)
- **kind** — `computed` (a measurable test) or `advisory` (a prompt the
  AI raises, never reported as a measurement)
- **source** — Alexander pattern number, Neufert figure, or code clause

The `computed` / `advisory` split matters. Many of Alexander's patterns
are qualitative by design; forcing them into pass/fail would produce
confident nonsense. The count of window-bearing aspects can be computed from geometry, but this does not verify the pattern’s qualitative claim. 134 Zen View is not, and must never be presented
as though it were measured.
