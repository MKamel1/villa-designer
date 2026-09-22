# Product Requirements — AI-led villa design system

**Status:** active · **Owner:** mmbka (client/governance) + Claude (design lead)
**Last updated:** 2026-09-20

---

## 1. Problem

Designing a house well is not a drawing problem. The expensive mistakes
are made early — a brief that never fitted the plot, a plan whose
circulation was an afterthought, a room that cannot take the furniture it
exists for — and they are discovered late, when changing them is costly.

Existing tools do not help with this. CAD and BIM software will faithfully
draw a bad plan. Generic "AI architects" generate plausible-looking
layouts with no accountability for whether they are habitable.

**What is missing is a method with checks attached**: an ordered process
where, at each step, the design is tested against published standards and
the results are explained with their source, so the advice can be argued
with rather than taken on trust.

## 2. Goals

1. **Lead the design, not just document it.** Propose layouts, lighting
   and detail; check them; recommend one option with reasons.
2. **Every finding cites a source.** Alexander pattern number, Neufert
   figure, or code clause. No invented standards.
3. **Report achieved versus required**, never an adjective. "350 mm clear
   where 450 is needed", not "a bit tight".
4. **Fire at the right moment.** Rules apply at the stage where the
   decision is being made.
5. **Support backtracking deliberately.** Design loops; the system names
   the loop, computes its blast radius, and records it.
6. **Keep the whole design reviewable as text**, so both client and agent
   can read, diff and argue about it.
7. **Produce real deliverables** — a coordinated BIM model and a drawing
   set, not just analysis.

## 3. Non-goals

- Not a substitute for a licensed architect or engineer where one is
  legally required.
- Not a code-compliance certification tool. Guidance is Neufert-based and
  jurisdiction-neutral; a local code always wins.
- Not generative "design from nothing". The system is strongest as a
  critic and executor, weakest as an inventor, and the method reflects
  that.
- Not multi-project practice management.

## 4. Users and authority

| Role | Who | Owns |
|---|---|---|
| **Design lead** | Claude | Proposing design, running checks, explaining trade-offs, recommending one option, doing the work, flagging consequences |
| **Client / governance** | mmbka | The brief, aesthetic judgement, budget, gate approval, and an absolute veto |

Operating rules:

- The AI arrives with a **recommendation, not a menu** — stating what it
  recommends, why, the cost, and what it rejected.
- A client **veto is absolute and recorded** as a logged waiver with a
  reason, never a silently suppressed warning.
- Downstream consequences of a veto are stated **at the moment of the
  veto**.
- **Silence is not approval.** A gate needs an explicit yes.

## 5. Method

Eight stages with quality gates and explicit backward loops. Defined in
[`method/villa-design-method.md`](method/villa-design-method.md).

    0 Intent -> 1 Ground -> 2 Fit -> 3 Order -> 4 Rooms
      -> 5 Systems -> 6 Substance -> 7 Proof

Thirteen named backward loops (L1–L13) with four thrash-control
mechanisms: cheapest-fix-first, blast radius, frozen decisions, loop
budget.

## 6. Architecture

    Revit (.rvt)  <- the only artifact a human authors      [Windows]
        | pyRevit export
        v
    model extract (text)  <- generated, never hand-edited   [git-tracked]
        |
        +--> rule engine: geometry, livability, lighting    [Linux]
        +--> web review sheet: markup + in-page AI          [Linux build]
        +--> lighting: lux grids -> Radiance                [Linux, 32 cores]
        +--> renders: Blender Cycles                        [Linux, RTX 3090]

    Revit -> 2D sheets -> PDF / DWG

**Single source of truth.** Only the Revit model is authored. The text
extract is generated, so drift is structurally impossible while
readability, diffing and review are preserved.

**Platform split.** Revit and AutoCAD on the Windows PC (Revit is
Windows-only); everything else on `ai-workstation`; git as the contract
between them. See [ADR-0006](decisions/ADR-0006-windows-pc-for-revit.md).

## 7. Standards used

| Source | Used for |
|---|---|
| Alexander, *A Pattern Language* | Qualitative design intelligence; cited by pattern number |
| Neufert, *Architects' Data* | Dimensions, clearances, minimum areas |
| Bioclimatic method | Climate analysis, orientation, shading |
| WELL / hospitality practice | Light quality, acoustics, arrival, back-of-house |

The **framework is this project's own**; the **standards never are**.
That separation is what keeps the advice accountable.

## 8. Scope

**In:** brief and site capture; feasibility; concept order; room
resolution; lighting design and verification; BIM authoring in Revit; 2D
output; the web review surface; dirty-DWG ingest.

**Out:** structural calculation; MEP sizing; energy modelling for
certification; cost estimation beyond order-of-magnitude; construction
administration.

## 9. Milestones

| # | Milestone | Needs Revit? |
|---|---|---|
| M1 | Docs, method, decision log | no |
| M2 | `brief.yaml` + `site.yaml` schemas and interview | no |
| M3 | Sun path and orientation analysis | no |
| M4 | Stage 2 feasibility check | no |
| M5 | Stage-aware rules + fix ladder | no |
| M6 | Concept tooling: zoning, adjacency, massing | no |
| M7 | Revit + pyRevit, model extract | **yes** |
| M8 | Lighting: lux grids, layered rules, Radiance, Blender | partial |
| M9 | Viewer rebuild: markup + in-page AI chat | no |

M1–M6 deliver value before Revit is installed.

## 10. Risks

| Risk | Mitigation |
|---|---|
| Bespoke framework becomes unaccountable | Every rule cites an external source |
| Patterns forced into pass/fail produce confident nonsense | Each classified computable or advisory; advisory never reported as measured |
| Loops thrash | Cheapest-fix-first, blast radius, frozen decisions, loop budget |
| `pyrevit run` may not support CLI automation | Tested before M7 is committed to |
| Revit education output is watermarked | Acceptable for personal use; disqualifying for client/authority work |
| Invented IES photometry would make heat maps confident and wrong | Manufacturer IES files only |
| Brief and site data are the client's to supply | System cannot proceed past M4 without them |

## 11. Open questions

- Jurisdiction for code-level rules (currently Neufert-only, neutral).
- Whether the villa has a fixed plot yet — blocks M3/M4.
- Whether to consolidate onto a single machine via a Windows VM later
  (hardware is capable; deferred).

## 12. Glossary

**Stage** — one of the eight method steps, each with a gate.
**Gate** — a design-quality test that must pass before proceeding.
**Loop** — a named backward path from a later stage to an earlier one.
**Blast radius** — the set of checks a proposed change invalidates.
**Waiver** — a client override of a finding, recorded with its reason.
**Extract** — the generated text model derived from Revit.
**Fix ladder** — remedies for a finding, ordered by how far back they
force the design.
