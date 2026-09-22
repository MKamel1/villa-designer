# The Villa Design Method (VDM)

**Version 1.0 · 2026-09-20**

A staged, looped, AI-led method for designing a private house.

---

## Why not RIBA

The RIBA Plan of Work 2020 is the default framework in practice, and it is
the wrong backbone here. It is a **procurement framework**: its stages
define when information passes between client, design team, contractor and
statutory bodies, and who carries liability. For a private villa with one
client and no tender, most of that machinery is dead weight.

More importantly it is **deliberately silent on how to design**. Its Stage
2 outcome is "Architectural Concept approved by the client and aligned to
the Project Brief" — how one arrives at a good concept is left entirely to
the designer. That is precisely the part this project needs.

And one of its rules is actively wrong for a house. RIBA states Stage 3
"is not about adjusting the Architectural Concept". Correct for a large
commercial job with forty consultants and a change-control procedure.
Wrong for a villa, where cheap iteration *before* commitment is the whole
value.

| From RIBA | Verdict |
|---|---|
| Staged gates; decisions locked at the stage that owns them | **Kept** — the discipline is real |
| Information exchanges, procurement strategy, liability machinery | **Dropped** |
| "Do not adjust the concept downstream" | **Replaced** with explicit, budgeted loops |
| Silence on design quality | **Filled** from Alexander, Neufert, bioclimatic method, WELL |

## Sources

Nothing in this method's *content* is invented. The framework is ours;
the standards never are.

1. **Christopher Alexander, *A Pattern Language* (1977)** — cited by
   pattern number. Numbering verified against the published contents.
2. **Neufert, *Architects' Data*** — dimensions, clearances, minimum areas.
3. **Bioclimatic design method** — climate analysis first; orientation as
   the primary move.
4. **WELL / hospitality practice** — light quality, acoustics, arrival
   sequence, back-of-house separation.

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

Pattern 159 deserves its emphasis: Alexander's claim is that people
gravitate to rooms lit from two sides and leave single-aspect rooms
unused. It is the strongest single predictor of whether a room gets lived
in, and it is geometrically checkable.

**Rules:** minimum areas and proportion; furniture fit; clearance
achieved-versus-required; furniture overlap; door swing arcs; circulation
width by erosion; door clear widths; glazing ratio; storage volume;
kitchen work triangle; stairs — riser 150–180 mm, going ≥ 250 mm, Blondel
`2R + G = 600–650 mm`, ≤ ~16 risers per flight, headroom ≥ 2000 mm,
width ≥ 900 mm.

**Gate:** every room passes, or carries a recorded waiver.

### Stage 5 — Systems

*Question:* light, power, water, air, sound, heat.

**Pattern 135 Tapestry of Light and Dark** is Alexander's 1977 statement
of exactly the layered-lighting principle that reads as "hotel". Also
181 The Fire · 199 Sunny Counter.

**Lighting rules:** ≥ 3 layers (ambient / task / accent / decorative) in
key rooms; **a lone central ceiling fixture as the only source fails** —
the single biggest tell of domestic-versus-hospitality lighting; lux
targets (living 100–300, kitchen worktop 300–500, bathroom 200–300 with
500 at the mirror, bedroom 100–200, stairs 100–150, corridor 100);
uniformity `Emin/Eavg` ≥ 0.4; glare sightlines — no bare lamp directly
visible; colour-temperature consistency within a space; CRI ≥ 90;
vertical surfaces lit, because perceived brightness comes from walls not
floors; mirror lit at the face, not only overhead; under-cabinet task
lighting where an overhead would cast the user's own shadow; low-level
night circulation lighting.

**Other systems:** sockets and switches against furniture positions;
ventilation extract rates; acoustic adjacency; hot-water dead-legs.

**Gate:** lux grids meet target and uniformity; no unresolved glare.

### Stage 6 — Substance

Materials, junctions, details, specification. Thermal and acoustic
build-ups; maintenance and cleaning access.

**Patterns:** 197 Thick Walls · 200 Open Shelves · 202 Built-in Seats

### Stage 7 — Proof

The drawing set out of Revit, and a check back against Stage 0 intent.

**Gate:** every Stage 0 intent is traceable to something in the design.
This closing loop is what RIBA has no equivalent of.

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

L1 and L8 are the two most common in practice. L4 is the most expensive,
which is why Stage 3 carries a wet-area stacking rule specifically to
catch it early.

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
confident nonsense. 159 Light on Two Sides is computable from a room's
exterior wall segments. 134 Zen View is not, and must never be presented
as though it were measured.
