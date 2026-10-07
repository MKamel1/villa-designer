---
Document Outline:
  - [Document Outline](#document-outline)
  - [Executive Summary](#executive-summary)
  - [Changed Files Inventory](#changed-files-inventory)
  - [Six Recorded Lessons and Class Mapping](#six-recorded-lessons-and-class-mapping)
  - [Summary Matrix: Class, Control Tier, and Current Status](#summary-matrix-class-control-tier-and-current-status)
  - [Tier 3 Review Steps Added](#tier-3-review-steps-added)
  - [Operational Rules Codified](#operational-rules-codified)
  - [Inbox Disposal](#inbox-disposal)
Executive Summary: >
  This report details the integration of six process lessons from 2026-10-06 into the archpipe lesson
  system. It covers four lead engineering incidents, the visual integration failure of procedural
  proxies, and the client-flagged site orientation conflation, establishing rigorous class mappings,
  honest control declarations, new Tier 3 review criteria, and operational dispatch rules.
---

# Process Lessons Report (2026-10-06)

This report documents the systematic recording of engineering and process lessons captured on 2026-10-06, including five lead findings and the client-raised site orientation correction.

## Changed Files Inventory

The following five files were modified or created in this workspace (`C:/Users/mmbka/arch-pipeline-agy`):

1. [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md): Appended section `## Process lessons (2026-10-06)` containing all six entries with full root-cause, reproduction, class, control tier, proof, and registry fields.
2. [`docs/ops/agent-dispatch.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/ops/agent-dispatch.md): Created dedicated operational procedures guide codifying bounded remote polling, holistic prompt rewrites, visual preview gates, and runtime preflight.
3. [`docs/review-steps.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/review-steps.md): Expanded Tier 3 review checklist with Item D.6 (procedural plant morphology and soffit finishes) and Item F.3 (neutral preview artifact gate), updating inventory and automatable signals.
4. [`docs/inbox/lead-lessons-2026-10-06.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/inbox/lead-lessons-2026-10-06.md): Replaced raw notes content with a single-line pointer to the permanent LEARNINGS entries.
5. [`docs/proc-lessons-report.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/proc-lessons-report.md): Authored this summary report.

*(Note: In accordance with project instructions, generated tables in [`docs/lessons-audit.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md) were not edited; class mappings and proposed names are documented below.)*

---

## Six Recorded Lessons and Class Mapping

### 1. `execution-context-wrong-interpreter`
- **One-line Summary:** Test runners and `verify.py` launched under unconfigured system Python 3.14 without project packages instead of `.venv`, causing 24 import failures.
- **Source:** Lead raw note (bullet 1).
- **Class Mapping:** **`execution context implicit`** (matches existing class in [`docs/lessons-audit.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md)).
- **Direct Cause:** Preflight validated Python release version (3.11–3.14) but did not check required packages. Third-party imports in `verify.py` occurred before preflight.
- **Current Control Status (Honest):** **Landed in commit `65218e3`**. `archpipe.execution_context.check_dependencies` checks module import names without import side effects; `scripts/run_tests.py` and `scripts/verify.py` fail closed with exit 2 on unconfigured environments before domain imports.

### 2. `ssh-monitor-silent-drop`
- **One-line Summary:** Monitor scripts holding single persistent `ssh ... until` connections dropped silently without event while remote batch jobs finished ~1.5 h earlier.
- **Source:** Lead raw note (bullet 2).
- **Class Mapping:** Proposed new class **`remote execution monitor fragile`** (or maps to existing `execution context implicit` / `pipeline result lacks atomic proof`).
- **Direct Cause:** Relied on a single long-lived remote SSH connection to wait for completion rather than client-side bounded polling loops.
- **Current Control Status (Honest):** **Process change only**. Monitor loops poll locally with short `timeout 30 ssh` calls per iteration. No automated watchdog guard exists yet. Codified in [`docs/ops/agent-dispatch.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/ops/agent-dispatch.md).

### 3. `visible-element-unpreviewed-integration`
- **One-line Summary:** Procedural Strelitzia and a ramp with paving on its soffit were integrated by an agent into presentation scenes without prior visual preview.
- **Source:** Lead raw note (bullet 3 process aspect).
- **Class Mapping:** Proposed new class **`visual preview gate omitted`** (or maps to existing `evidence or scope silently promoted` / `human judgement or intent`).
- **Direct Cause:** Look-before-integrate was documented only as a skill memory convention, lacking a mandatory gate requiring preview artifacts before scene referencing.
- **Current Control Status (Honest):** **Process rule only**. Documented in [`docs/ops/agent-dispatch.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/ops/agent-dispatch.md) and [`docs/review-steps.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/review-steps.md) (Item F.3). An automated fail-closed gate at scene reference time is pending / not yet implemented.

### 4. `procedural-plant-and-soffit-guards`
- **One-line Summary:** Procedural Strelitzia rendered as crude lollipop blobs on bare stalks, and a sloped ramp carried stone paving finish on its downward-facing soffit.
- **Source:** Lead raw note (bullet 3 physical defects).
- **Class Mapping:** **`proxy lacks physical geometry`** (for Strelitzia lollipop blobs) and **`appearance lacks verified basis`** (for ramp soffit paving); both are existing classes in [`docs/lessons-audit.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md).
- **Direct Cause:** Plant generator emitted primitive sphere-on-stalk solids rather than botanical morphology; ramp generator applied floor paving uniformly without testing face normals.
- **Current Control Status (Honest):** **QUEUED / planned (G2f)**. Construction-level plant-form morphology and downward-facing soffit-material checks are queued. Currently governed by human render review (Item D.6 in [`docs/review-steps.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/review-steps.md)).

### 5. `agent-prompt-appended-contradiction`
- **One-line Summary:** Incremental append addenda in task G4 created conflicting instructions ("STOP if no climber record" vs "add these lead-verified records"), causing the agent to halt.
- **Source:** Lead raw note (bullet 4).
- **Class Mapping:** Proposed new class **`dispatch instruction contradiction`** (or maps to existing `human judgement or intent`).
- **Direct Cause:** Appending amendments to existing text without holistic prompt reconciliation or checking against earlier preconditions.
- **Current Control Status (Honest):** **Process change only**. Operational rule in [`docs/ops/agent-dispatch.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/ops/agent-dispatch.md): rewrite prompt whole when decisions change; verify against every STOP line before dispatch. No automated prompt linter implemented.

### 6. `site-orientation-conflation`
- **One-line Summary:** Lead named street garden 'west court' and +y strip 'north court' using true north instead of client naming (street = north, +y = east, +x = south); landscape direct sun hours applied true azimuths to unrotated model axes with a 3 m proxy enclosure (reporting 4–5 h vs ~1 h real ray-cast).
- **Source:** Client review correction ("WHY ARE YOU GETTING DIRECTION WRONG!").
- **Class Mapping:** Proposed new class **`orientation naming implicit`** (or maps to existing `coordinate or unit conversion scattered` / `authored values overwritten`).
- **Direct Cause:** Conflation of true geographic north (solar azimuth calculation frame) with nominal client north (spatial brief and model axes); direct solar model omitted the 20 deg rotation matrix and used an unrepresentative 3 m wall box proxy.
- **Current Control Status (Honest):** **QUEUED, not done**. Codex job is queued to author `knowledge/site-orientation.json`, rename landscape zones to client naming, replace the proxy sun calculation with a scene ray-cast, and add a compass-word lint guard.

---

## Summary Matrix: Class, Control Tier, and Current Status

| Lesson ID | General Root Class | Class Status | Control Tier | Current Enforcement Status |
|---|---|---|:---:|---|
| `execution-context-wrong-interpreter` | `execution context implicit` | Existing | Tier 1 / 2 | **Landed in commit `65218e3`** (`execution_context.check_dependencies`, `verify.py` bootstrap) |
| `ssh-monitor-silent-drop` | `remote execution monitor fragile` | Proposed | Tier 3 | **Process change only** (bounded `timeout 30 ssh` polling in `docs/ops/agent-dispatch.md`) |
| `visible-element-unpreviewed-integration` | `visual preview gate omitted` | Proposed | Tier 3 | **Process rule only** (preview artifact path + hash required before scene reference; code gate pending) |
| `procedural-plant-and-soffit-guards` | `proxy lacks physical geometry` / `appearance lacks verified basis` | Existing | Tier 3 / Tier 2 | **QUEUED / planned (G2f)** (currently governed by Tier 3 render review Item D.6) |
| `agent-prompt-appended-contradiction` | `dispatch instruction contradiction` | Proposed | Tier 3 | **Process change only** (whole-prompt rewrite discipline in `docs/ops/agent-dispatch.md`) |
| `site-orientation-conflation` | `orientation naming implicit` | Proposed | Tier 1 / Tier 2 | **QUEUED, not done** (Codex job queued for `site-orientation.json`, ray-cast sun, compass guard) |

---

## Tier 3 Review Steps Added

In [`docs/review-steps.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/review-steps.md), two new human review moments were formalized:

1. **Item D.6: Procedural Plant-Form Morphology and Botanical Plausibility** (under Moment D: Render Realism and Aesthetics)
   - Evaluates whether procedural plant elements display authentic botanical morphology (leaf blades, petioles, fan habit) rather than crude symbolic blobs, and checks that downward soffits do not carry paving finishes.
   - Requires recorded render preview image ID and reviewer visual sign-off.
2. **Item F.3: Visual Preview Artifact Before Scene Integration (Look-Before-Integrate)** (under Moment F: Delegating Research and Debugging)
   - Validates that every newly authored procedural mesh builder or exterior surface feature has an inspected neutral preview artifact with recorded file path and SHA-256 hash before being referenced by scene assembly code.
   - Requires artifact path and SHA-256 checksum in dispatch logs.

In addition, both items were documented under Section 7 and 8 of *Automatable Lessons and Measurable Signals* with their respective future automated check specifications.

---

## Operational Rules Codified

In [`docs/ops/agent-dispatch.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/ops/agent-dispatch.md), four operational rules and a pre-dispatch checklist were established:

1. **Bounded Remote Polling:** Poll remote workstation state using short, bounded SSH calls with explicit timeouts (e.g. `timeout 30 ssh`), maintaining the wait loop locally with sleep intervals. Never hold an open SSH pipe across long waits.
2. **Holistic Prompt Rewriting:** When design parameters or instructions change, re-author the complete task prompt rather than appending incremental addenda. Compare all instructions against `STOP` lines and preconditions prior to dispatch.
3. **Look-Before-Integrate Gate:** Every newly authored procedural generator, material binding, or plant model must produce an isolated neutral preview image (with recorded disk path and SHA-256 hash) before scene assembly code can reference the builder.
4. **Environment Preflight:** Always execute via `.venv` Python; runners verify packages before importing domain code and fail closed with exit code 2 and a single clear error message.

---

## Inbox Disposal

In compliance with project instruction 5, [`docs/inbox/lead-lessons-2026-10-06.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/inbox/lead-lessons-2026-10-06.md) was replaced with a single-line pointer to the permanent LEARNINGS entries:

```markdown
Recorded into [LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L1551) entries: execution-context-wrong-interpreter, ssh-monitor-silent-drop, visible-element-unpreviewed-integration, procedural-plant-and-soffit-guards, agent-prompt-appended-contradiction, and site-orientation-conflation.
```
