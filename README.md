# villa-designer (`archpipe`)

An AI-led villa design system: a **staged method with checks attached**. It
takes a house from client intent to a furnished, lit, rendered and
documented design, and every piece of advice it gives cites a published
source and reports *achieved versus required* rather than an adjective
("350 mm clear where 450 is needed", never "a bit tight").

It is not a CAD tool and not a layout generator. Its premise is that an AI is
**strong as a critic and weak as an inventor**: it does not produce good plans
from nothing, but it can check a plan against sourced figures, name the
consequence, and order the remedies by how far back each one forces the
design to go.

> **Status: working research system, not a construction package.** Outputs
> are design guidance, not code compliance (no jurisdiction pack is loaded),
> and nothing here replaces a structural, MEP or permit consultant. The
> bedroom is a capability example; the real villa (a Sheikh Zayed, Egypt
> project) is in furnished-layout and render-review stage. Several
> inputs are placeholders until the client supplies a survey and brief. See
> [docs/ROADMAP.md](docs/ROADMAP.md) for exactly what is and is not done.

## Authority model

**The AI leads. The client governs.**

- Every recommendation arrives with the reason, the cost and what was
  rejected; not a menu.
- A client **veto is absolute** and is recorded as a waiver with its reason.
  Warnings are never silently suppressed, and downstream consequences are
  stated at the moment of the veto.
- **Silence is not approval.** A gate needs an explicit yes.

## What it can do

| Capability | What it does | Where |
|---|---|---|
| **Eight-stage method** | Intent, Ground, Fit, Order, Rooms, Systems, Substance, Proof, with quality gates and thirteen named backward loops ordering remedies cheapest-first | [method](docs/method/villa-design-method.md), [PRD](docs/PRD.md) |
| **Stages 0-2 (no CAD needed)** | Machine-readable brief and site; NOAA solar-position engine verified against almanac times; feasibility arithmetic that returns a *cut ladder* | `brief.py`, `site.py`, `solar.py`, `feasibility.py` |
| **Rule engine (the critic)** | Rules that cannot be created without a source citation; violation / warning / advisory severities; advisory findings never carry a fake measurement. Values are re-read from held books and free standards by tests | `rules.py`, `catalogue.py`, [rule audit](docs/guidance/rule-audit.md) |
| **Evidence library** | Full-text and semantic search over held books and standards (printed page to cite); a passage counts as verified only when read and applicable | `knowledge_index.py`, [guidance](docs/guidance/README.md) |
| **Concept generation and critique** | Typology catalogue and constraint-solver variants, judged by a critic calibrated on published plan datasets (CubiCasa5k, Swiss Dwellings) | `concept/`, [ADR-0016](docs/decisions/ADR-0016-concept-search-and-critique.md) |
| **Climate, thermal and daylight** | Window studies with shading fins, TM59 overheating screen per room, Radiance daylight on Cairo-region weather | `thermal.py`, `daylight.py`, [ADR-0017](docs/decisions/ADR-0017-thermal-window-study.md) |
| **Lighting** | IES/LDT photometry reader, lux grids and heat maps, layered-lighting checks, and a real-manufacturer luminaire library with exact specifications and alternates | `photometry.py`, `lighting.py`, `luminaires/` |
| **Product library** | About 3,550 indexed and 469 verified surfaces, fabrics, furniture, plants and decor; buyable products kept apart from render look-alikes | `products/`, [ADR-0015](docs/decisions/ADR-0015-product-library.md) |
| **Revit 2027 round-trip** | Text spec authors a native model; the saved model is re-extracted and compared with the input; native plans, ceiling plans, elevations, sections and sheets; markup survives save/extract | `revit/`, [validation record](docs/bedroom-validation.md) |
| **Photoreal rendering** | Blender Cycles on a GPU workstation, calibrated against independent photometric probes, with automatic render QA (window view, daylight through glass, colour cast, clipping, cloth, level camera and more) | `blender/`, `render_qa.py`, [ADR-0013](docs/decisions/ADR-0013-presentation-renders.md) |
| **Hand-off** | Schedules, quantities, relative cost, specification book and an IFC4 export checked against the spec, plus an explicit list of consultant scope that is *missing in-house* (glare, HVAC, electrical, plumbing, structure, permits) | `deliverables.py`, `scripts/handoff.py` |
| **Assistant tools (MCP)** | Typed, mostly read-only operations so an AI assistant calls tools instead of reconstructing shell sequences | [docs/MCP.md](docs/MCP.md) |

The legacy 2D pipeline (spec to DXF to DWG to plotted A3 sheet, plus a
web review sheet with millimetre-accurate pinned notes) still works and is
documented in [docs/pipeline-reference.md](docs/pipeline-reference.md).

## The bedroom capability example

One room exercises the whole chain end to end, so each link can be tested
independently of the real villa:

1. Text specification builds a native Revit 2027 model.
2. The saved model is re-extracted and compared with the input (57 checks).
3. The rule engine reviews the *measured* geometry.
4. Native floor plan, reflected ceiling plan, elevations, section and 3D view go onto A3 sheets.
5. A lighting report is computed from real fixture positions and joined photometry.
6. The scene is rebuilt on the render workstation; rendered direct-light values agree with the analytical calculation (median ratio about 0.97 over 10,944 points).
7. Synthetic markup (text and a revision cloud) survives save and extraction.

```bash
.venv/Scripts/python scripts/run_bedroom.py --resume
```

Evidence lands in `out/bedroom-acceptance.json`, initially *failed* and
marked passed only after every gate completes. Details and limitations:
[docs/bedroom-validation.md](docs/bedroom-validation.md).

## Quick start

Requires Python 3 (built on 3.14). Stages 0-2, the rule engine, and the
tests need **no Autodesk software**.

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # + requirements-mcp.txt for MCP
export PYTHONPATH=src                                      # Windows cmd: set PYTHONPATH=src

python scripts/verify.py          # expect: RESULT: ALL PASS (121 checks, positive and negative)

python -m archpipe brief spec/villa-brief.yaml                          # Stage 0
python -m archpipe site  spec/villa-site.yaml                           # Stage 1 + sun study
python -m archpipe fit   spec/villa-brief.yaml spec/villa-site.yaml     # Stage 2
python -m archpipe design spec/apartment.yaml                           # design review
```

Every stage command **exits non-zero when its gate is closed** (`fit` when
the brief does not fit the plot, `design` on a violation). That is
by design, so each command works as a gate in a script.

`spec/villa-brief.yaml` and `spec/villa-site.yaml` are **placeholders**.
Latitude drives every orientation figure, so the sun study on placeholder
data means nothing for a real site.

### Optional infrastructure

| Needs | For |
|---|---|
| Windows + licensed **Revit 2027** and pyRevit | Native model authoring, extraction, drawings ([SETUP](docs/SETUP.md), [ADR-0011](docs/decisions/ADR-0011-target-revit-2027.md)). Files authored in 2027 cannot open in 2025. |
| Full AutoCAD (not LT) | DWG and plotted PDF path only |
| Ubuntu workstation with NVIDIA GPU, Blender 4.2, Radiance | Cycles renders, independent lighting and daylight studies, candidate sweeps ([compute placement](docs/ops/compute-placement.md), [workstation jobs](docs/ops/workstation-jobs.md)) |
| Held books and standards (never committed) | Evidence search; `verify.py` fails if a PDF/EPUB is committed |

Third-party assets, manufacturer files, client documents and generated
`out/` content are deliberately not in the repository; manifests record
their source and hash.

## Working with AI assistants

- **MCP server:** `scripts/archpipe_mcp.py` exposes project status, model
  reading and review, evidence and book search, product and luminaire search,
  render checks, lighting probes, concept generation and critique, and
  bounded workstation jobs. There is deliberately no arbitrary-command
  tool. Rebuilds are marked as write operations. See [docs/MCP.md](docs/MCP.md).
- **Skills** (canonical in `.agents/skills/`): `villa-method`, one per stage
  (`villa-intent` to `villa-proof`), `revit-roundtrip`, `lighting-proof`,
  `lighting-library`, `product-library`, `knowledge-search`,
  `photoreal-render`, `villa-render`, `workstation-jobs` and
  `defect-learning`.
- **Agent roles** in `agents/roles.json` (design lead, architectural critic,
  render critic, lighting reviewer, thermal analyst, product and source
  curators, Revit and workstation executors). Claude and Codex adapters are
  generated by `scripts/sync_agent_assets.py`; run it with `--check` to
  detect drift.
- **Launch the assistant from the repository root.** Project agents and
  skills are only discovered in the directory the session starts in.

## Engineering disciplines

These are the project's value; breaking one quietly is worse than not doing
the work.

1. Every rule cites a source; `rules.Rule` raises without one.
2. No invented standards, figures or clause numbers. A readable citation is
   not verification.
3. Achieved-versus-required, never an adjective.
4. Advisory findings carry no measurement.
5. Verify against something independent (almanac times, hand-calculable
   fixtures, models whose dimensions were chosen rather than measured).
6. Negative tests always: does it stay quiet when it should?
7. Every defect leaves a guard behind, recorded in [docs/LEARNINGS.md](docs/LEARNINGS.md),
   preferably as an automatic check proven against a *real* reproduction.
   Presentation renders pass `render_qa` before anyone is shown them, and
   exposure is never tuned to hide a dark design.

## Repository layout

```
docs/            method, PRD, ADRs (each with what was rejected), guidance, ops, learnings
src/archpipe/    rule engine, stages 0-2, concept, thermal/daylight, lighting, luminaires,
                 products, rendering contract, Revit/AutoCAD adapters
src/archpipe/blender/   scene build, photometric calibration, lux measurement
revit/           pyRevit extractor, probes, test-model builder
scripts/         verify.py, run_bedroom.py, MCP server, workstation and villa tooling
knowledge/       precedents, library index, product manifests (no third-party sources)
.agents/ agents/ canonical skills and agent roles
tests/           regression tests, including reproduced defects
spec/            brief, site and example specifications
```

## Where to read next

- New here: [docs/ROADMAP.md](docs/ROADMAP.md), then [CLAUDE.md](CLAUDE.md) (the working agreement).
- Method: [docs/method/villa-design-method.md](docs/method/villa-design-method.md), [docs/PRD.md](docs/PRD.md), [docs/decisions/](docs/decisions/).
- Measured traps and fixes: [docs/LEARNINGS.md](docs/LEARNINGS.md).
- Current villa work: [docs/D1-CONTINUATION.md](docs/D1-CONTINUATION.md), [docs/villa-render-scene.md](docs/villa-render-scene.md).
- Environment rebuild: [docs/SETUP.md](docs/SETUP.md). Historical notes: [docs/HANDOVER.md](docs/HANDOVER.md).
