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
    - upper rooms supported by ground rooms;
    - each room within 25 % of its scheduled area;
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
- **Treating the schedule's 40 m² circulation allowance as a hard fail.** Over all 1,500 variants per parti, the minimum circulation (halls, landings, stair) was 61.1 m² (bar), 98.9 m² (L) and 111.9 m² (U), with 1.3 m halls. That is a finding about the schedule, reported as achieved-versus-allowance.

## Consequences

- `python scripts/concept.py generate` writes three concepts and `docs/guidance/concepts-pilot.md`:
  - bar and L pass every check except area match: the 6 m² ground bath comes out at about 9 to 9.7 m², because the generator's 1.8 m minimum frontage stretches it;
  - U fails the 400 m² gross allowance at 436 m² and area match. Its ground bath stretches to 54 m², and its east arm is a stub (a 2 m² gallery plus the utility room). The U does not suit a 272 m² programme in this generator.
- The real villa (Sheikh Zayed) is untouched. Nothing here closes a design gate.
- **Next, to make the geometric critic trustworthy:** obtain a labelled, dimensioned plan set (e.g. *Floor Plan Manual* single-family chapter with its key, or Neufert house plans), encode 5–8 plans, and un-skip the geometric calibration.

## Update 2026-09-25: real-plan calibration (CubiCasa5k)

The client approved CubiCasa5k (CC BY-NC-SA 4.0; only aggregate results are stored in the repo).

**Procedure** (pre-registered in `scripts/cubicasa_calibrate.py`): 300 single-floor plans per run, 90 % quiet gate, seeded defects must be caught. Results are in `knowledge/precedents/cubicasa-calibration.json`.

**Window check: calibrated.** On fresh plans 601–900 it was quiet on 95.0 % and caught 277 of 300 seeded defects. One amendment was made: an open-plan room borrows daylight from a windowed room it is open to.

**Reachability check: NOT calibrated.**
- It was quiet on only 87.3 % of the final fresh sample, below the 90 % gate.
- The named cause is door-to-room matching across thick walls, a parser limit.
- Next step: fix the matching, then judge on plans 901–1200.

**Checks that need a scale** (area, width, wet stack): still not calibrated, because CubiCasa has no absolute scale.

Generated concepts therefore stay diagnostic.

**Update (run 4, plans 901–1200, fresh):** the run-3 reachability failures were not door matching. Reachability started from a plant-room door while the real front door opened onto a mapped porch.

Amendment 3 treats the outside as one node, joined to every mapped outdoor space and every external door. On fresh plans:
- **Reachability: now calibrated.** Quiet on 95.7 %, and caught 300 of 300 seeded defects.
- **Window:** quiet on 94.0 %, and caught 284 of 300.

Caveat: 40 plans with no detectable external door were excluded by the sampling rule.

The checks that need a scale remain uncalibrated, so generated concepts stay diagnostic for area, width and wet-stack.

**Update: dimensioned checks on Swiss Dwellings** (CC BY 4.0; metric geometry; `scripts/swiss_calibrate.py`, pre-registered).
- The room rules AREA-01 and DIM-01 were run as-is on real apartments. Pre-registered sample: 300 apartments, quiet 99 %, seeded defects 300 of 300. Replication: 1,000 fresh apartments, quiet 99.2 %, seeded defects 1,000 of 1,000.
- Flags came from genuinely small rooms, and from open-plan dining zones labelled as separate areas.
- The thresholds sit just below the 1st percentile of real rooms, so they bite without being vacuous.
- Not tested: the double-bedroom minimum (the data do not say which bedrooms are doubles), wet-stack, and area-schedule matching.
