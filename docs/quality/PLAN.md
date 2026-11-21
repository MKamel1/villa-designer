# Plan to A+ — parallel execution

Goal: the villa (D1) reaches the A+ bar in [A-PLUS.md](A-PLUS.md) as fast as possible, with many
agents implementing at once. The general product grows out of the tools built for it.

## 1. Why the last parallel attempt stalled, and what changes

The October lanes (A/B/M/R) did not speed anything up. The 2026-11 review found three causes:
- All four lanes drew on one Codex quota. All 43 lane stops were quota stops.
- Lanes edited the same files (`villa_render.py`, `LEARNINGS.md`, `knowledge/*.json`, `verify.py`). That took 42 merges and needed custom merge tools.
- Most lanes worked on a single shared villa scene, so each one waited on the others.

This plan fixes all three:

| Cause | Fix |
|---|---|
| One quota | **Mixed worker pool.** Claude subagents work in their own isolated copies of the repo (git worktrees); Codex takes up to 2 heavy implementation lanes; agy (Gemini) does sourcing and research. Each pool has its own limit, so they add up. |
| Shared files | **Each lane owns its files** (§4), enforced by a check in CI. Shared registries become per-lane files that are discovered automatically: no central edits, no merge conflicts. |
| Waiting on the villa | **Engines first, villa second.** Each lane builds and proves its engine against published reference cases and small test rooms, so it does not wait for the villa. It applies the engine to the villa only once the design is frozen at G1. |

Concurrency: 5–6 lanes at once. More than that and the lead's review becomes the bottleneck.
The lead (Claude Opus) writes briefs, reviews every hand-back with an independent verifier agent,
and merges. The lead does not implement.

## 2. Waves at a glance

```
Wave 0  (2–3 days)  W0-A stabilise ─┐   W0-B contracts ─┐   H1 interview + plot docs (you)
                                    └──────────┬────────┘
Wave 1  (≈3 weeks)  L1 compliance │ L2 design model │ L3 vision critic │ L4 products+style
                    L6 lighting engine │ L7 electrical engine │ L8 ops │ R research (agy)
                                    │
        G1 — compliance report → you approve design fixes; concept chosen (H2) → DESIGN FREEZE
                                    │
Wave 2  (≈3 weeks)  L2 apply fixes to D1 │ L4 FF&E into model │ L5 Revit sheets
                    L6 villa lighting design │ L7 villa electrical │ L3 critic as gate
                                    │
        G2 — model complete, all discipline checks green
                                    │
Wave 3  (≈2 weeks)  L9 re-render + blind test │ L5 permit set │ L6/L7 packages │ X cross-checks
                                    │
        G3 — final regrade (overall = lowest discipline)
```

Rough total: **about 8–9 weeks**, against 4–5 months with one lane in series. The critical path runs
L1 (compliance) → G1 (your approval) → L2 (fixes) → L9 (re-render). Everything else is off it.

## 3. Work packages

Worker key: **C** = Claude subagent in its own worktree · **X** = Codex · **G** = agy/Gemini (research, docs) · **H** = you.

### Wave 0 — foundation (blocks everything; short)
| WP | Worker | Output | Done when |
|---|---|---|---|
| W0-A Stabilise | C | Remove the `out/` junctions; merge `review/2026-11`; laptop on `main`; prune merged branches and worktrees; fix the 2 stuck render jobs; one GPU lock for every workstation job | `main` is the only live line; workstation jobs restart cleanly |
| W0-B Contracts | Lead | The interfaces in §5; lane ownership map `ops/lanes.yaml`; check script `scripts/lane_guard.py`; per-lane registration folders; brief and hand-back templates | Each lane can start with no further questions to the lead |
| H1 Inputs | H + C (interview) | Budget cap, each daughter's identity, style likes; plot facts and documents → `spec/villa-brief.yaml`, `spec/villa-site.yaml` | Placeholders gone |

### Wave 1 — engines in parallel (no lane waits for another)
| WP | Worker | Builds | Proven against (before touching the villa) | Criteria |
|---|---|---|---|---|
| L1 Safety & quality | C | Best-practice checkers (ADK, Metric Handbook, Neufert) for heights, room sizes, doors, basement daylight, stairs, guards (100 mm sphere), escape; **safety report on D1**; Egyptian values informative only | A positive and a negative fixture per rule; the current stair must fail | EG1–EG9, LS1–LS5 |
| L2 Design model | X | One placed-object record per element (IFC-aligned); scene, Revit spec and schedules read it; retire the ~14 patch passes; guard registry as data | Byte-identical scene output from the new model | BM1, X1 |
| L3 Vision critic | C | Rubric R1–R13 scored by a vision model; metadata checks (lens, height, verticals, subject exposure, texel density, faceting) | ≥90 % recall on the 27 known bad views; ≤10 % false fails on B views | R1–R13 |
| ~~L4 Products + style~~ (PAUSED by client 2026-11-21; revisit after G1) | G (sourcing) + C (code) | Egyptian supplier catalogue (SKU, dimensions, 3D, finish; quantities per room; pricing deferred); style engine (palette with LRV, material limits, clone check); 2–3 concept boards for you | 30 real products per category verified; boards rendered | I1–I6, I16 |
| L6 Lighting engine | X | Whole-room Radiance calc report; UGR (CIE 117/190); over-lighting cap; ceiling-plan setting-out solver; scene and DALI table; exterior and obtrusive light; emergency path; LM-83 metrics | CIE 171 cases ±5 %; CIE 190 UGR exact; LM-83 reference ±3 points | LA1–LA15 engine |
| L7 Electrical engine | C | Device placement rules; circuits; maximum demand; cable/protection sizing; voltage drop; Zs; boards; single-line diagram (SVG/DXF) | IET OSG demand example ±2 %; IEC 60364-5-52 worked example within ±1 size; bathroom zone negative tests | EA1–EA12 engine |
| L8 Ops | C | One workstation job runner (systemd user units, dead-job relaunch, GPU queue); root scripts into `ops/workstation/` | Kill a job mid-run and it resumes; two GPU jobs never overlap | — |
| R Research | C | Card the international STD values (ADK, Metric Handbook pages, (IEC 60364, EN 12464, EN 1838, LM-83); NKBA bath figure | Each card has page and quote; UNVERIFIED rows drop | sourcing |

**Gate G1 (needs you):** L1's compliance report lists every failure with achieved against required,
plus a recommended fix. You approve the fixes (H3) and choose a concept (H2). The design freezes.

### Wave 2 — apply engines to the frozen villa
| WP | Worker | Work | Criteria |
|---|---|---|---|
| L2b Design fixes | X | Apply the approved G1 fixes in the model; re-run L1 until all gates pass | EG, LS green |
| L4b Interior | C | FF&E and finish schedules from the model; replace stand-ins with real products; styling | I7–I15, I17–I18 |
| L5 Documents | C (Windows laptop, Revit) | Revit sheet automation: dimensions, grids, levels, tags, Art.111 title block, sections, elevations, schedules, bilingual labels; interior elevations and millwork | DS1–DS4, SC1, I15 |
| L6b Villa lighting | C | Run the lighting engine on D1: RCP, scenes, exterior, emergency; fix over-lighting and glare | LA1–LA15 |
| L7b Villa electrical | C | Run the electrical engine on D1 using L6b's zones; Revit circuits read back | EA1–EA15 |
| L3b Critic gate | C | The critic gates every render job; the Revit view exports are checked too | R-gate live |

**Gate G2:** all discipline checks green on the model.

### Wave 3 — outputs and coherence
| WP | Worker | Work | Criteria |
|---|---|---|---|
| L9 Re-render | X (workstation GPU) | Full set to the R1–R13 standard, day and dusk; blind test against studio photographs | R1–R13, blind test |
| L5b Permit set | C | Art.112 permit set, bilingual, three-copy PDF | DS, permit |
| L6c / L7c Packages | C | Lighting L-01…L-10 and electrical E-01…E-12 issue sets | package lists |
| X Cross-checks | C (verifier) | Counts and positions agree across model, sheets, schedules and renders; circuits = luminaires = ceiling plan | A-PLUS §5 |

**Gate G3:** final regrade. Optional: an external review by a licensed Egyptian engineer.

## 4. Lane ownership (no two lanes write the same file)

| Lane | Owns (write) | Reads only |
|---|---|---|
| L1 | `src/archpipe/codes/eg/**`, `src/archpipe/compliance/**`, `knowledge/eg/**`, `tests/compliance/**` | design model, `rules.py` |
| L2 | `src/archpipe/model/**`, `src/archpipe/concept/villa_render.py`, `src/archpipe/blender/villa_scene.py`, `src/archpipe/guard_registry.py` | everything |
| L3 | `src/archpipe/critic/**`, `knowledge/critic/**`, `tests/critic/**` | renders in `out/` |
| L4 | `src/archpipe/products/**`, `src/archpipe/interior/**`, `knowledge/products/**` | design model |
| L5 | `revit/sheets/**`, `src/archpipe/documents/**` | design model, products |
| L6 | `src/archpipe/lighting/**` (new), extensions to `lighting.py`, `radiance.py`, `luminaires/**` | design model |
| L7 | `src/archpipe/electrical/**`, `knowledge/electrical/**`, `tests/electrical/**` | design model, L6 zone IDs |
| L8 | `ops/workstation/**`, `scripts/workstation.py` | — |
| R | `knowledge/sources/**` (cards only) | — |

Shared files are no longer hand-edited centrally:
- `verify.py` discovers checks from each lane's `checks/` folder.
- Lessons go to `docs/lessons/<lane>.md` instead of one `LEARNINGS.md`.
- Knowledge indexes are rebuilt by a script.

`scripts/lane_guard.py` fails any lane branch that writes outside its lane.

## 5. Contracts written in Wave 0 (lanes build against these)

1. **Design model record:** element id, type, level, placement, footprint and solid, product id, finish codes, host. Owned by L2; the first version is frozen in W0-B, so other lanes code against it from day one.
2. **Check result:** criterion id (e.g. `EG4`), status, achieved, required, source card, element ids. Every engine emits this, so the regrade is one script.
3. **Source card:** document, edition, page, quote, value, status (sourced / STD / POLICY / UNVERIFIED).
4. **Product record:** extends `products/schema.py` with SKU, supplier, dimensions, 3D asset, LRV (price fields optional, deferred).
5. **Lighting zone / circuit IDs:** L6 publishes zones; L7 consumes them.
6. **Render job and critic verdict:** view id, camera metadata, image, R-scores, verdict.

## 6. How a lane runs

1. **Brief.** The lead writes it: goal, owned paths, contracts, reference cases, criteria IDs, and what is out of scope.
2. **Isolated copy.** The agent works in its own worktree on branch `lane/<id>`. It commits small steps and pushes daily, so nothing is lost.
3. **Hand-back.** The agent returns: criteria passed, with check output; reference cases reproduced; open items.
4. **Independent verification.** A verifier agent re-runs the checks from a clean checkout and looks at any visual output. It is not given the implementer's conclusions.
5. **Merge.** The lead merges to `main` (fast-forward or a small merge; conflicts should be impossible by ownership). It then updates `STATUS.md` and a one-line row in the regrade table.

## 7. Human gates (yours) — they never stall engine work

| Gate | When | What you decide | Time |
|---|---|---|---|
| H1 | Wave 0 | Interview: daughters, style (no budget yet); plot documents | about 1 h, plus documents |
| H2 | End of Wave 1 | Pick one of 2–3 concepts | 15 min |
| H3 | G1 | Approve the compliance fixes, e.g. a closed stair or changed ceiling heights | 30 min |
| H4 | Wave 3 | Exposure policy, then final visual sign-off | 30 min |

## 8. Risks

- **G1 grows** if the Egyptian gates force a re-plan of the basement or stair. Mitigation: L1 runs first in Wave 1 and reports early failures by day 3.
- **The review load is on the lead.** Six lanes report back. Mitigation: verifier agents do the first pass; the lead reviews only verified hand-backs.
- **Contract drift.** If L2 changes the model record, lanes break. Mitigation: versioned record; changes only at wave boundaries.
- **Single GPU.** L3 calibration, L6 and L9 compete for the workstation. Mitigation: the L8 queue; Radiance runs on CPU; L9 is the only Wave 3 GPU-heavy job.

## 9. Scope decisions log

- 2026-11-21: International best practice is the gate; Egyptian code is informative only.
- 2026-11-21: No pricing or budget for now; quantities and specifications only.
- 2026-11-21: Client confirmed scope. Kept: L1 safety, L2 design model, L3 render critic, L6 lighting,
  L7 electrical, L8 workstation runner, R sourcing; later: Revit drawing set, blind photo test,
  automatic layout generation, mood and material boards. Paused: L4 products, style and quantities.
- Rule: any new capability is proposed to the client for confirmation before it is built.
- 2026-11-21: Revit-free, with no loss of functionality (client). Revit's two roles are replaced:
  background checks → RV1 (independent checks on the built scene, proven on the real defects Revit
  caught); 2D communication → RV2 (sections and elevations from Blender line art, furnished,
  lighting and site plans, sheet set) and RV3 (IFC + DXF/DWG hand-over). RV1's inventory of every
  Revit use is the parity contract. Revit stays optional as a second check if the sign-in is restored.
- 2026-11-21: Client equipment answers: gas hob, 7.4 kW EV charger, split AC in all habitable rooms.
- 2026-11-21: Scene builds run on the workstation (Windows maths libraries differ in the last bit).
- 2026-11-21: Lighting is verified independently (docs/quality/LIGHTING-VERIFICATION.md); a physical
  check after purchase is too late (client), so V10 manufacturer lab data + V12 80 % dimmer headroom
  carry the independent evidence. Client prefers luminaires from makers that publish full photometric
  datasheets openly (lane LP), so every specified product is checked against lab data before purchase.
