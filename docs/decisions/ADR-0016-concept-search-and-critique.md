# ADR-0016: Concept design by search and critique, with a calibration gate

Date: 2026-09-25. Status: accepted (generator v1 diagnostic).

## Context

The AI is strong as a critic and weak as an inventor (CLAUDE.md). The plan
(W2) asked for:
- a precedent corpus;
- a typology catalogue;
- a generator that proposes many variants per parti;
- a critic that scores them all the same way.

The critic may only be trusted after it ranks known-good plans above
seeded-bad ones.

## Decision

- **`archpipe.concept.critic`** is the single scoring path.
  - **Graph checks** (private access, WC access for guests, reachability) run on any room graph. That covers published precedents, the pilot concepts and generated layouts.
  - **Geometric checks** run on generated layouts:
    - links actually buildable as doors;
    - every habitable room has a window;
    - wet stack;
    - living with a north window;
    - within plot;
    - gross and circulation area;
    - elongation.
  - Every check names its basis: a pilot fact, an evidence card, or "project figure, not a standard". A check without a sourced threshold stays advisory and only orders variants.
- **`archpipe.concept.generator`** lays the pilot programme out per parti (bar, L, U) in banded rectangular wings.
  - Seeded random variation covers band depths, room order, block placement and an optional wet core next to the stair.
  - It critiques every variant and keeps the best per parti.
  - Output is the L0 spec format (`spec/concepts/pilot/*.yaml`), so the existing rule engine runs on it unchanged.
  - Generator settings are recorded as settings, not standards: corridor 1.3 m, stair allowance, minimum room run 1.8 m, a placeholder road offset.
- **Calibration gate: `tests/test_concept_calibration.py`.**
  - Graph half:
    - the critic is quiet on four room graphs read from Mitton & Nystuen (Figs. 2.7 and 3.5a–c);
    - every seeded defect fails its check (private rooms through a living space, WC only through a bedroom, a room with no door), with full separation;
    - the pilot's pavilion concept, authored before the critic, is the only pilot concept that fails.
  - Geometric half: **skipped with its reason**. No held book gives a labelled, dimensioned house plan: *Precedents in Architecture* plans are unlabelled at print scale, and *Floor Plan Manual* keys rooms by number. So generated concepts are diagnostic and are not shown to a client.
- **Precedent records** come in two levels:
  - parti-level (12 houses from *Precedents in Architecture*): organisation, circulation, section and diagram themes, with rooms null;
  - room-graph level (4 Mitton figures).

  Rooms are never reconstructed from memory.

## Rejected

- **Reconstructing room graphs of famous houses from memory or unlabelled drawings.** This breaks "record what the source shows".
- **Calling mutation tests on synthetic layouts "calibration".** They are unit tests (`tests/test_concept.py`) and are kept separate.
- **OR-Tools CP-SAT packing now.** The banded generator already meets every sourced check on the pilot for bar and L. A solver is worth adding when the geometric calibration can run and the checks get richer. Not pinned, not installed.
- **Treating the schedule's 40 m² circulation allowance as a hard fail.** Every variant needs 66 m² or more with a stair and 1.3 m halls. That is a finding about the schedule, reported as achieved-versus-allowance.

## Consequences

- `python scripts/concept.py generate` writes three concepts and `docs/guidance/concepts-pilot.md`:
  - bar and L pass every check;
  - U fails the 400 m² gross allowance at 436 m².
- The real villa (Sheikh Zayed) is untouched. Nothing here closes a design gate.
- **Next, to make the geometric critic trustworthy:** obtain a labelled, dimensioned plan set (e.g. *Floor Plan Manual* single-family chapter with its key, or Neufert house plans), encode 5–8 plans, and un-skip the geometric calibration.
