# A villa design method — staged, looped, AI-led

## Context

RIBA was the wrong backbone and this replaces it. RIBA 2020 is a
**procurement framework**: it defines when information passes between
client, design team, contractor and statutory bodies, and who carries
liability. For a private villa with one client and no tender, most of that
is dead weight — and it is deliberately silent on *how* to design, which
is the part we need. Its own wording proves the mismatch: Stage 3 "is not
about adjusting the Architectural Concept." Correct for a large commercial
job; wrong for a house, where cheap iteration before commitment is the
entire value.

**Kept:** staged gates, decisions locked at the stage that owns them.
**Dropped:** information exchanges, procurement, liability machinery,
and the no-iteration rule.
**Added:** explicit backward loops, and a defined split of authority
between the AI and the client.

### Built from four citable sources

The *framework* is ours; every *rule* cites an external authority.

1. **Alexander, *A Pattern Language*** — the design intelligence RIBA
   omits. Numbering verified against the published contents, not recalled.
2. **Neufert, *Architects' Data*** — dimensions and clearances (already
   in `catalogue.py`).
3. **Bioclimatic method** — climate first; orientation as the primary move.
4. **WELL / hospitality practice** — light quality, acoustics, arrival
   sequence, back-of-house separation. Where "hotel-like" becomes
   checkable rather than aspirational.

### Platform decisions (unchanged)

Revit is the single source of truth; the text extract is generated, never
hand-edited; Revit and AutoCAD on the Windows PC; everything else on
`ai-workstation` (32 cores, RTX 3090); git between them.

---

## Who decides what

**The AI leads. The client governs.**

| | Owns |
|---|---|
| **AI** | Proposing the design, running every check, explaining trade-offs, **recommending one option**, doing the work, flagging consequences. |
| **Client** | The brief, aesthetic judgement, budget, approval at gates, and an **absolute veto**. |

Working rules that make this real rather than decorative:

- **I arrive with a recommendation, not a menu.** Every proposal states:
  what I recommend, why, what it costs, and what I rejected and why.
- **A veto is absolute and is recorded, not argued twice.** If you
  override a finding, it becomes a **logged waiver** with your reason —
  not a silently suppressed warning. That is how a practice handles it,
  and it keeps the record honest.
- **I state downstream consequences at the moment of the veto**, not
  later. If overriding a rule now makes a Stage 5 rule unachievable, you
  hear it now.
- **Silence is not approval.** A gate needs an explicit yes.
- Every gate decision lands in `docs/decisions/` with the date, the
  choice, the reason, and the options rejected.

---

## The eight stages

Each owns decisions, applies rules, produces an artifact, and passes a
gate that is a **design-quality test**, not a document handover.

**0 — Intent.** Who lives here and how; rhythm; hosting; ageing in place;
budget; what "good" means. `brief.yaml` + taste board, filled by
**interview, not a form**. Reference images read for concrete attributes,
not adjectives.
*Gate:* the brief is specific enough that a drawing could contradict it.

**1 — Ground.** `site.yaml`: plot boundary and area, **north angle**,
latitude, topography, access, prevailing wind, views to keep and screen,
noise, neighbouring masses, trees, services, and the statutory envelope
(setbacks, height, plot ratio). Sun path is pure maths from latitude and
date. *Patterns 104, 105, 162.*
*Gate:* orientation strategy fixed and justified.

**2 — Fit.** Brief target areas + circulation and wall allowance versus
permitted footprint × storeys. *Patterns 96, 107, 109.*
*Gate:* **the brief fits, or the brief changes.** The cheapest place in
the whole project to find a mismatch.

**3 — Order.** The big moves: zoning; **intimacy gradient**; circulation
spine decided *before* rooms are placed; orientation response; level
strategy and stair position; wet-area stacking; massing.
*Patterns 110, 112, 127, 129, 130, 131, 133, 158, 205.*
*Rules:* private not reached through public; no room doubles as a
corridor; every habitable room has a daylight-capable aspect; wet areas
stack; self-overshadowing; back-of-house circulation separated from guest
circulation.
*Gate:* concept coherent and approved. **Only now does it go into Revit.**

**4 — Rooms.** Each room resolved. *Patterns 128, 139, 144, 145, 159,
179, 180, 184, 188, 190, 191, 196, 198.* This is where the existing engine
lands almost entirely — areas, proportion, furniture fit, clearance
achieved-vs-required, overlap, door swings, circulation width, glazing
ratio, storage, kitchen triangle, stairs (riser 150–180, going ≥ 250,
Blondel `2R+G = 600–650`, ≤ ~16 risers/flight, headroom ≥ 2000,
width ≥ 900).

**5 — Systems.** Light, power, water, air, sound, heat.
*Pattern 135 Tapestry of Light and Dark* is Alexander's 1977 statement of
exactly the layered-lighting principle that reads as "hotel".
*Rules:* ≥ 3 lighting layers in key rooms; **fail a lone central fixture
as the only source**; lux targets and uniformity ≥ 0.4; glare sightlines;
colour-temperature consistency; CRI ≥ 90; vertical surfaces lit; mirror
lit at the face; under-cabinet task light; night circulation. Plus
sockets against furniture, extract rates, acoustic adjacency, hot-water
dead-legs.

**6 — Substance.** Materials, junctions, details, specification.
*Patterns 197, 200, 202.* Thermal and acoustic build-ups; maintenance
access.

**7 — Proof.** Drawing set out of Revit, and a check back against Stage 0
intent — the loop RIBA has no equivalent of.

---

## Inner loops

Design does not run forwards. These are the backward paths, named so they
can be handled deliberately instead of as chaos. Each is a **trigger →
return-to → what changes**.

| # | Trigger | Returns to | Typically changes |
|---|---|---|---|
| L1 | Furniture won't fit; clearance or door swing fails | **Rooms → Order** | wall position, room size, bedroom location *(your example — the most common loop)* |
| L2 | Rooms only work at sizes that exceed the footprint | **Rooms → Fit** | storey count, or the brief |
| L3 | Can't hit lux targets or layering in this room shape; sockets clash; no wall for a unit | **Systems → Rooms** | room proportion, window position, furniture layout |
| L4 | Wet areas don't stack; drainage or riser can't route | **Systems → Order** | which rooms sit where, between levels — expensive, which is why Order carries a stacking rule |
| L5 | Working massing needs more footprint than setbacks allow, or overshadows itself | **Order → Ground** | orientation or massing strategy |
| L6 | Circulation spine costs more area than the allowance assumed | **Order → Fit** | recompute feasibility |
| L7 | Brief does not fit the plot | **Fit → Intent** | cut or restructure the brief |
| L8 | Wall build-up (insulation, services zone) eats internal dimension; a room that passed at nominal thickness now fails | **Substance → Rooms** | room size, or the build-up *(classic, and usually caught too late)* |
| L9 | Chosen material can't take the fixing or luminaire; acoustic build-up changes thickness | **Substance → Systems** | fixture choice or construction |
| L10 | Render shows the *feel* is wrong although every number passes | **Systems → Rooms/Order** | aesthetic veto — legitimate, and the client's call |
| L11 | Site analysis reveals noise, overlooking or slope that defeats a briefed requirement | **Ground → Intent** | the brief |
| L12 | Documentation exposes an unresolved junction | **Proof → Substance** | detail |
| L13 | Client changes their mind | **any → Intent** | anything — must stay cheap and recorded |

### Stopping loops from becoming thrash

Loops without discipline are infinite churn. Four mechanisms:

1. **Cheapest-fix-first.** When a check fails, I present fixes ordered by
   how far back they force us. For a clearance failure: *(a)* move the
   furniture [in-stage], *(b)* resize the room [Order], *(c)* change the
   brief [Intent] — with the cost of each stated. Most failures are
   fixable in-stage, and naming that prevents needless backtracking.
2. **Blast radius before backtracking.** Before a change is made, I
   compute what it invalidates — "moving this wall re-opens checks X, Y, Z
   and the lighting grid for two rooms" — so the decision is informed.
3. **Frozen decisions.** A passed gate freezes its decisions. Re-opening
   requires an explicit unfreeze with a reason, recorded. This is the
   piece RIBA gets right and it is worth keeping.
4. **Loop budget.** Count re-entries per stage. Three returns to the same
   stage means the problem is upstream — usually the brief — and I say so
   rather than iterating a fourth time.

---

## What this changes in the tooling

- **Rules become stage-aware.** Each declares the earliest stage at which
  it is meaningful; `archpipe design --stage N` reports only what is
  actionable now. Clearance checks during massing are noise; plot ratio
  during detailing is too late.
- **Findings carry a fix ladder** — the cheapest-fix-first list above,
  generated per finding, which is what turns a complaint into advice.
- **Patterns become a second rule family** cited by number. Some compute
  directly (159 Light on Two Sides is a geometric test on a room's
  exterior wall segments; 127 Intimacy Gradient is a graph test on the
  circulation network). Others are advisory prompts — **labelled
  advisory, never dressed up as measurements.**
- **Brief-compliance checking**, which no generic checker does: "you asked
  for four bedrooms, the plan has three." Only possible because the brief
  is data.
- **A decision and waiver log** under `docs/decisions/`, including
  overrides and their stated consequences.

## Build order

1. `docs/` — `PRD.md`, `method/` (this framework), `decisions/`,
   `discussions/`.
2. `brief.yaml` and `site.yaml` schemas, and the interview that fills them.
3. Sun path + Stage 1 orientation analysis.
4. Stage 2 feasibility check.
5. Stage tagging across existing rules, `--stage N`, and the fix ladder.
6. Stage 3 concept tooling — zoning, adjacency, intimacy gradient, massing.
7. Revit + pyRevit, and the extract.
8. Lighting — lux grids, layered rules, then Radiance and Blender.
9. Viewer rebuild — markup and in-page AI chat.

**Steps 1–6 need no Revit, no AutoCAD and no install**, so they start now
and are useful on their own — which matters, because your files and the
Revit licence are not here yet.

## Verification

- Sun path checked against a published solar-position calculator for a
  known latitude and date; a wrong azimuth silently corrupts every
  orientation rule.
- Feasibility arithmetic hand-checked on a worked example.
- Every rule gets a deliberately-bad case proving it fires and a good case
  proving it does not fire falsely — the bed-clearance and door-swing
  false positives already caught are why this is not optional.
- Advisory patterns are labelled advisory and never reported as measured.
- Extract fidelity: room areas and wall lengths must match Revit's own
  schedules.

## Risks

1. **A bespoke framework can drift into being unaccountable.** Guard:
   every rule cites Alexander by number, Neufert by figure, or a code
   clause. The method is ours; the standards never are.
2. **Alexander's patterns are qualitative by design** — forcing them all
   into pass/fail would produce confident nonsense. Each is classified
   computable or advisory.
3. **Loops can thrash.** The four mechanisms above are the guard; the loop
   budget is the backstop.
4. **Brief and site data are yours.** I cannot invent your plot dimensions
   or setbacks.
5. `pyrevit run` command-line automation is unverified.
6. Revit not installed (~30 GB); education output is watermarked.
7. IES photometric files must come from real manufacturers.

## Carried forward

- Dashed linetypes plot solid through the AutoCAD layout viewport.
- SHX text gives PDFs no selectable text.
- The live review sheet is still v1, pending the viewer rebuild.
- Dirty DWG/PDF ingest waits on your files.
