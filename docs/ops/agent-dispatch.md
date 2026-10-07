---
Document Outline:
  - [Document Outline](#document-outline)
  - [Executive Summary](#executive-summary)
  - [Agent Dispatch and Operational Disciplines](#agent-dispatch-and-operational-disciplines)
  - [1. Remote Monitor Connections (Bounded Polling)](#1-remote-monitor-connections-bounded-polling)
  - [2. Holistic Prompt Authoring (No Appended Addenda)](#2-holistic-prompt-authoring-no-appended-addenda)
  - [3. Visual Preview Gate (Look-Before-Integrate)](#3-visual-preview-gate-look-before-integrate)
  - [4. Environment and Runtime Preflight](#4-environment-and-runtime-preflight)
  - [Operational Dispatch Checklist](#operational-dispatch-checklist)
Executive Summary: >
  This document defines mandatory operational rules for dispatching, monitoring, and integrating work
  from autonomous coding agents and remote workstation processes. It establishes bounded polling protocols
  to prevent silent monitor disconnections, whole-prompt rewrite disciplines to eliminate contradictory
  preconditions, and a strict visual preview artifact requirement before referencing new scene elements.
---

# Agent Dispatch and Operational Disciplines

These operational procedures govern task delegation, remote workstation execution, and scene integration across all autonomous agents (e.g. Claude Code, Codex) and human operators.

## 1. Remote Monitor Connections (Bounded Polling)

- **Rule:** Poll remote state with bounded short connections (timeout per call), never one long-lived SSH wait.
- **Problem:** Single persistent `ssh ... until` connections drop silently over network blips or timeouts, causing local monitoring loops to stall indefinitely while background jobs finish unobserved.
- **Procedure:**
  - Execute remote checks via bounded commands: `timeout 30 ssh <host> '<status-check>'`.
  - Maintain the wait loop in the local shell or Python script with an explicit sleep interval (e.g. `sleep 10` or `time.sleep(10)`).
  - Explicitly handle per-iteration connection timeouts and retries with a maximum retry counter and timestamped logging.
  - Cross-reference: [docs/LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L1564) (`ssh-monitor-silent-drop`).

## 2. Holistic Prompt Authoring (No Appended Addenda)

- **Rule:** When a decision changes, rewrite the whole job prompt; before dispatch, check new text against every STOP and precondition line.
- **Problem:** Incrementally appending addenda, exceptions, and updates to the bottom of an existing task prompt creates contradictory instructions (such as "STOP if condition X" earlier vs "proceed with X" later), forcing agents to halt or waste entire execution turns.
- **Procedure:**
  - Never append postscripts or contradictory overrides to an active or template prompt.
  - When design parameters, constraints, or decisions evolve, re-author the complete task specification from scratch.
  - Prior to dispatch, perform a systematic line-by-line check comparing newly authored instructions against every `STOP`, gate, precondition, and waiver in the prompt.
  - Cross-reference: [docs/LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L1597) (`agent-prompt-appended-contradiction`).

## 3. Visual Preview Gate (Look-Before-Integrate)

- **Rule:** A new visible element needs a recorded neutral preview (path and content hash) before its builder can be referenced by the scene.
- **Problem:** Unverified procedural generators, plant proxies, and material assignments integrate directly into presentation scenes, escaping to late-stage render reviews with crude stand-ins (e.g. lollipop blobs for plants or paving on soffits).
- **Procedure:**
  - Before any newly authored mesh builder, procedural component, or material binding is imported into scene assembly (`villa_render.build` or `villa_landscape.build`), generate an isolated neutral preview image.
  - Record the absolute artifact file path (e.g. `out/previews/<component>-preview.png`) and its SHA-256 content hash in the component deliverable metadata.
  - Inspect the preview against photographic realism, botanical morphology, and surface orientation rules before wiring the builder into the villa scene.
  - Cross-reference: [docs/LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L1575) (`visible-element-unpreviewed-integration`) and [docs/LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L1586) (`procedural-plant-and-soffit-guards`).

## 4. Environment and Runtime Preflight

- **Rule:** Launch test suites and execution scripts strictly through the designated project virtual environment interpreter (`.venv/Scripts/python.exe` on Windows, `.venv/bin/python` on Linux), never system Python.
- **Procedure:**
  - Preflight checks verify required domain dependencies (e.g. `shapely`, `yaml`) using `importlib.util.find_spec` before running test discovery or domain modules.
  - Runners refuse execution immediately with exit code 2 and a single clear message naming missing dependencies and `sys.executable` if launched under an unconfigured interpreter.
  - Cross-reference: [docs/LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L1553) (`execution-context-wrong-interpreter`).

## Operational Dispatch Checklist

Before launching an agent task or remote process, verify:
1. **Prompt Consistency:** All preconditions and `STOP` directives align with the current design decision; no conflicting append addenda exist.
2. **Environment Specified:** Explicit invocation paths use the project `.venv` runtime.
3. **Preview Artifact Bound:** If the task creates or modifies visible scene elements, a neutral preview path and hash must be produced before scene referencing.
4. **Monitoring Bounded:** Any remote execution monitor uses bounded short connections with per-call timeouts (e.g. `timeout 30 ssh`).
5. **Output Freshness Checked:** Downstream consumption verifies fresh output hashes and non-zero exit codes.
