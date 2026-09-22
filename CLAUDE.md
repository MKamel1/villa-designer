# archpipe — working agreement

An AI-led villa design system: a staged method with checks attached.
**New to this repo? Read `docs/HANDOVER.md` first.**

## The framing

The AI is **strong as a critic, weak as an inventor**. It does not
generate good layouts from nothing. It checks a layout against figures
that have a source, names the consequence, and orders remedies by how far
back each one forces the design. Everything here follows from that.

## Authority

**The AI leads. The client governs.**

- Arrive with a **recommendation, not a menu** — what you recommend, why,
  the cost, and what you rejected.
- A client **veto is absolute**, and is recorded as a waiver with its
  reason. Never silently suppress a warning.
- State downstream consequences **at the moment of the veto**.
- **Silence is not approval.** A gate needs an explicit yes.

## Non-negotiable disciplines

1. **Every rule cites a source** — Neufert figure, Alexander pattern
   number, or named published practice. `rules.Rule` raises without one.
   The framework is ours; the standards never are.
2. **Never invent a standard, a figure, or a clause number.** With no
   jurisdiction pack loaded, output states it is guidance, not code
   compliance. The client chose best practice over a specific code.
3. **Report achieved-versus-required, never an adjective.**
   "350 mm clear where 450 is needed", not "a bit tight".
4. **Advisory findings carry no measurement.** Alexander's patterns are
   qualitative; forcing one into pass/fail produces confident nonsense.
5. **Verify against something independent.** Solar position was checked
   against published almanac times; the Revit extract against a model
   whose dimensions were chosen rather than measured. Do the same.
6. **Negative tests always.** Two false positives here passed their
   positive tests and were caught only by asking "does it stay quiet when
   it should?"

## Before you claim something works

```bash
PYTHONPATH=src python scripts/verify.py     # expect: ALL PASS, 53 checks
```

Every stage command exits non-zero when its gate is closed — that is by
design, not a failure: `fit` exits 1 when the brief does not fit the
plot, `design` exits 1 on a violation.

## Environment

- **Revit 2025, not 2026** — 2026 could not be licensed for automated
  launch (ADR-0008). Root cause never isolated.
- **`pyrevit run <model>` does not open the model** — it hands you a
  `UIApplication` with zero documents. `extract_model.py` opens it itself.
- **`revit.doc` returns `None`** in the runner rather than raising.
- **Revit internal units are decimal feet.** A units bug does not raise;
  it silently yields a model 304.8× wrong. All conversion goes through
  one `mm()` boundary.
- Full AutoCAD only — LT has no `accoreconsole.exe`. Three traps that
  wedge it are documented in `src/archpipe/acad.py`; read them before
  debugging a hang.

## Source of truth

Revit is the only authored artifact; the text extract is **generated and
never hand-edited** (ADR-0001, ADR-0002). Drift is structurally
impossible because only one thing is authored.

`spec/villa-brief.yaml` and `spec/villa-site.yaml` are **placeholders**.
Latitude drives every orientation figure — the current sun study is a
stand-in and means nothing for the real site.

## Layout

    docs/method/     the Villa Design Method: 8 stages, 13 loops
    docs/decisions/  ADRs, each recording what was rejected and why
    docs/HANDOVER.md context transfer + the VM test plan
    docs/SETUP.md    rebuilding the environment on a new machine
    src/archpipe/    rule engine, stages 0-2, drawing pipeline
    revit/           extractor, pyRevit extension, probe, test-model builder
    scripts/verify.py 53 checks, positive and negative
