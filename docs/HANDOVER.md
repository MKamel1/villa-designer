# Handover — for the agent picking this up on the VM

> Historical bootstrap handover (2026-09-20). For current work read
> [ROADMAP.md](ROADMAP.md), [LEARNINGS.md](LEARNINGS.md), and
> [MCP.md](MCP.md). Revit 2027 is now local; Blender renders run on the
> Ubuntu workstation. The old "not built" lists below are not current status.
> The [bedroom validation record](bedroom-validation.md) contains the
> completed capability test and its remaining limitations.

You are taking over an AI-led villa design system. Read this once, then
work from `CLAUDE.md` (auto-loaded) and the documents it points at.

**Nothing in this repository has ever run on the VM.** Everything was
built and verified on a bare-metal Windows machine. Section 5 is the test
plan; run it before trusting anything, and report what breaks rather than
working around it silently.

---

## 1. What this is

Not a CAD tool. A **method with checks attached**: eight decision-led
stages, thirteen named backward loops, and a rule engine where every
finding cites a published source and reports *achieved versus required*
rather than an adjective.

The whole thing rests on one idea: **the AI is strong as a critic and
weak as an inventor.** It does not generate good layouts from nothing. It
checks a layout against figures that have a source, explains the
consequence, and orders the remedies by how far back each forces the
design. Keep that framing — it is why the advice is defensible.

Read in this order:
1. `docs/method/villa-design-method.md` — the method itself
2. `docs/PRD.md` — goals, roles, architecture, glossary
3. `docs/decisions/` — eight ADRs, each with what was *rejected* and why
4. `docs/discussions/2026-09-20-kickoff.md` — how it got here, including
   the client's corrections and the mistakes that caused them

## 2. Authority — this matters more than it sounds

**The AI leads. The client governs.**

- Arrive with a **recommendation, not a menu**: what you recommend, why,
  the cost, what you rejected.
- A client **veto is absolute** and becomes a recorded waiver with its
  reason — never a silently suppressed warning.
- State downstream consequences **at the moment of the veto**, not later.
- **Silence is not approval.** A gate needs an explicit yes.

The client has corrected the previous agent four times. The corrections
are in the discussion log; they are worth reading because each one was a
real failure of judgement, not a misunderstanding.

## 3. Disciplines you must not relax

These are the project's whole value. Breaking one quietly is worse than
not doing the work.

- **Every rule cites a source.** Neufert figure, Alexander pattern
  number, or named published practice. The framework is ours; the
  standards never are. `rules.Rule` *raises* if a rule has no reference.
- **No invented standards, figures or clause numbers.** With no
  jurisdiction pack loaded, output says plainly that findings are
  guidance, not code compliance. Keep it that way — the client chose
  best practice over a specific code.
- **Advisory findings never carry a measurement.** Alexander's patterns
  are qualitative by design; forcing one into pass/fail produces
  confident nonsense. That is what `kind="advisory"` is for.
- **Verify, do not assume.** Every hard number in this repo was checked
  against something independent. Solar position against published almanac
  times. The Revit extract against a model whose dimensions were chosen,
  not measured. Follow that pattern.
- **Negative tests, always.** `scripts/verify.py` has 53 checks and
  deliberately includes cases that *must* fire. Two false positives in
  this project — a bed clearance rule and a door-swing arc — both passed
  their positive tests and were caught only by asking "does it stay quiet
  when it should?"

## 4. State of play

**Working and verified (on bare metal):**
- Stages 0–2: brief, site, feasibility. No Autodesk needed.
- Solar position — NOAA algorithm, 14 checks including London
  sunrise/sunset within 2 minutes of published times.
- Rule engine — stage-aware, `--stage N` filtering, fix ladders citing
  loop ids, required references.
- Revit extract — verified against known geometry, in millimetres.
- AutoCAD pipeline — spec → DXF → DWG → true 1:50 A3 sheet, headless.
- Web review sheet — platform-independent storage, JSON export.

**Not built:**
- Lighting (the largest remaining piece): lux grids from IES photometry,
  layered-lighting rules, Radiance, Blender renders. See ADR-0004 — the
  key insight is that lighting *compliance* is arithmetic, not rendering.
- Stage 3 concept tooling: zoning, adjacency, intimacy gradient, massing.
- Viewer markup tools (ink, highlight, arrow, measure) and in-page AI chat.
- Dirty DWG/PDF ingest — blocked on the client's real files.

**Blocked on the client, not on you:**
- Real plot, setbacks, and location. `spec/villa-site.yaml` is invented.
  **Latitude drives every orientation figure** — the current sun study is
  Cairo as a stand-in and means nothing for the real site.
- The Stage 0 brief interview. `spec/villa-brief.yaml` is a placeholder
  and is meant to be replaced by interview, not by editing the file.

**Known unfixed:**
- Dashed linetypes plot **solid** through the AutoCAD layout viewport.
  Narrowed to the plot path — the same geometry renders dashed in the web
  sheet. Root cause not isolated.
- SHX text gives PDFs no selectable text (one-line fix in `layers.py`).
- Revit 2026 could not be licensed for automated launch; 2025 works.
  Root cause not isolated — see ADR-0008.

## 5. Test plan for the VM

Run in order. Each tier assumes the one above passed; a failure in tier N
makes tier N+1 meaningless, so stop and report rather than pressing on.

### Tier 0 — the repo itself (no Autodesk, no VM specifics)

```bash
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt
PYTHONPATH=src python scripts/verify.py
```

**Expect:** `RESULT: ALL PASS`, 53 checks.
If this fails, it is the Python environment, not the VM. Check Python
version — built on 3.14.7.

### Tier 1 — Revit reachable from the command line

Install Revit **2025** (ADR-0008), sign in interactively **once**, close
it. Install pyRevit, attach, register the extension (`docs/SETUP.md` §2).

```powershell
$env:ARCHPIPE_PROBE_OUT="$PWD\probe.json"
& $pr run revit\probe.py --revit=2025
```

**Expect:** `api_ok: true`, `raw_revitapi_import: true`, a non-empty
`revit_username`, in roughly 15–20 s.

**If it hangs ~300 s then fails** with `Adlsdk Error:(20)`: that is the
licensing failure that made 2026 unusable. In a VM it is more likely to
be Autodesk activation refusing the virtual hardware — a live risk named
in ADR-0006. Report it; do not try to work around licensing.

### Tier 2 — extract correctness (the one that matters)

```powershell
$env:ARCHPIPE_TEST_MODEL="$PWD\test.rvt"
& $pr run revit\build_test_model.py --revit=2025
$env:ARCHPIPE_MODEL="$PWD\test.rvt"
$env:ARCHPIPE_EXTRACT_OUT="$PWD\test.model.json"
& $pr run revit\extract_model.py --revit=2025
```

**Expect exactly:**
- wall lengths `[4000.0, 4000.0, 6000.0, 6000.0]`
- room area `(6000 − t) × (4000 − t) / 1e6` for the template thickness
  `t` (was 200 mm → **22.040 m²**)
- `units: "mm"`

**Why this and not "did it run":** Revit's internal units are decimal
feet. A units bug does not raise. It silently yields a model 304.8×
wrong that looks entirely healthy. If the numbers are off by that factor,
the `mm()` conversion in `extract_model.py` is the place to look.

### Tier 3 — AutoCAD pipeline (skip if AutoCAD is not on the VM)

```bash
PYTHONPATH=src python -m archpipe build spec/apartment.yaml --pdf
```

**Expect:** DXF, PNG, DWG, PDF, and a PNG of the plotted PDF.
Needs **full** AutoCAD — LT has no `accoreconsole.exe`.
If it hangs, read the three traps in `src/archpipe/acad.py` before
touching anything; all three were hit for real.

### Tier 4 — Linux host compute

Radiance and Blender are **not installed** on `ai-workstation`. Neither
is needed until lighting work starts. When it does: Radiance is CPU-only
(use the 32 cores), Blender Cycles wants the GPU — which the VM may be
holding.

### Tier 5 — VM specifics, all unverified

| Question | Why it matters |
|---|---|
| Does the 3090 isolate cleanly in its own IOMMU group? | Passthrough fails outright if not |
| Does Autodesk activation work inside a VM? | Named in ADR-0006 as an unverified risk |
| Does Revit 2026 behave differently here than on bare metal? | Try it *after* 2025 works, so there is a known-good baseline |
| GPU contention between guest and host | Blender on the host cannot use a GPU bound to the guest |
| Does `pyrevit run` still take ~15 s? | Slower startup changes whether CLI or the ribbon button is the primary path |

## 6. Two Revit behaviours that will waste your time

**`pyrevit run <model.rvt>` does not open the model.** It accepts a model
path and still hands the script a `UIApplication` with
`Documents.Count == 0`. Measured, not assumed. `extract_model.py` opens
the document itself.

**`revit.doc` is `None` in the runner** and *returns* None rather than
raising, so a `try/except` around it catches nothing and the next line
dies on `None.Title`. `resolve_doc()` handles all three contexts.

## 7. Where to start

**Launch your assistant from `arch-pipeline/`.** Claude Code discovers
the project's agents and skills (`render_critic`, `lighting_reviewer`,
`photoreal-render` and the rest) only in the directory it starts in. A
session started in the parent folder silently has none of them. That
happened once, and nobody noticed until an agent call failed.

If the client has supplied plot and brief data: **run the Stage 0
interview**, then Stage 1 and 2. That is the highest-value work and needs
no Revit.

If not: **lighting** is the largest unbuilt piece and is mostly
arithmetic — it needs neither Revit nor the client's data to begin. Start
with the lux engine and validate it against a hand-calculable single
fixture before trusting any heat map.

Do not start Stage 3 concept tooling before the brief and site are real.
It would be built against invented constraints.
