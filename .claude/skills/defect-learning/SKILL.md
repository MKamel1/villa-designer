---
name: defect-learning
description: Turn any found error, bug, defect, wrong assumption or process mistake into a lasting improvement - record it, find why it happened (not just what), generalise it to its whole class, change the building process so it cannot recur, add a fail-closed check where prevention is impractical, and prove the fix generalises. Use whenever a client, reviewer, test, render, read-back or agent finds something wrong, whenever the same kind of mistake appears twice, and before closing any defect.
---

A defect is evidence about the *process* that produced it. Fixing the
instance is the smallest part of the work; the goal is that neither this
defect nor any member of its class can be built again. This extends
CLAUDE.md discipline 7 ("every defect leaves a guard") to its full form.

Blameless: describe what the system (code, data, prompts, agents,
reviewers) allowed, never who erred. "The builder accepted a zero-thickness
glass plane", not "the agent forgot thickness".

## The loop (do every step; stop and report at the two checkpoints)

1. **Capture, immediately.** One record per defect in
   `docs/LEARNINGS.md` using [the template](record-template.md): what was
   observed, where, who found it, at which stage, and at which stage it
   *should* have been caught. Capture before fixing, while the evidence
   exists. Keep the evidence (image, read-back, log line, failing input).
2. **Reproduce on the real case.** Freeze the actual failing input
   (by value, not by importing the current code) as a test that fails now.
   A guard written against a synthetic case has missed the real defect here
   twice. Diagnose the cause on data before touching anything
   (see `photoreal-render` for render causes, `evidence-before-claims`).
3. **Find why, not just what.** Ask "why" until the answer is a property of
   the *process*, not of this instance (usually 3-5 steps). Separate:
   - the **direct cause** (the wrong value, shape, call);
   - the **escape**: why no existing check caught it, and why it reached
     the stage it did (e.g. "checks were geometric; nobody looked at the
     image until the full draft");
   - **contributing factors** (unclear brief, trusted input, batch size,
     missing reference).
4. **Generalise to the class.** Name the root in general terms ("an item
   mounted on a wall was positioned from the room outline, not the finished
   face"). Then **search for siblings**: grep the codebase and past
   LEARNINGS for the same pattern and list every other place it can occur.
   Several past records usually share one root; link them.
   **CHECKPOINT 1:** report cause, escape, class and siblings to the lead
   before building anything.
5. **Choose the control, strongest first** (hierarchy of controls):
   1. **Eliminate / prevent by construction** (mistake-proofing): change
      the builder, API, data model or default so the error cannot be
      expressed - e.g. the glass builder only makes closed panes of stated
      thickness; model import requires recorded units and axes; one
      `finished_face()` replaces raw room rectangles for wall-mounted items;
      the camera placer only searches positions with line of sight. Migrate
      every sibling call site. Prefer this whenever practical.
   2. **Detect early and fail closed**: a check at the *earliest* pipeline
      stage that has the information (spec build, layout, lighting, scene
      export, asset ingest, render driver, Revit read-back, `verify.py`),
      run unconditionally with no skip flag.
   3. **Process step** only when judgement is irreducible (aesthetics,
      client intent): a named review step with the reason it cannot be
      scripted. Never write a fake numeric check for a judgement.
   Layers can combine (defence in depth) but a check never substitutes for
   an available construction fix.
6. **Fix and prove.** Apply the control; the step-2 test must now pass.
   Prove the control:
   - **fires** on the real reproduction and on at least one sibling;
   - **stays quiet** on the clean case (negative test: two false positives
     here passed their positive tests);
   - **generalises**: runs on other options/villas/examples without
     D1-specific ids or coordinates, and on an injected defect of the same
     class (mutation test).
   **CHECKPOINT 2:** report the change, its tier, the three proofs and, for
   anything visible, a preview image.
7. **Register and document.** Add the record's control to the guard
   registry (lesson id -> check or construction change -> proving test ->
   stage) so `verify.py` knows it; the "Enforced rules" in AGENTS.md are
   generated from that registry. Complete the LEARNINGS record (tier,
   control, proofs, siblings retired). Update the affected skill if the
   operating procedure changed.
8. **Review the pattern.** When a class recurs, or at the end of each
   delivery round, re-read the round's records together: repeated escapes
   through the same stage mean that stage's process is the defect. Record
   the process change (e.g. "preview before integrate", "small checkpointed
   agent jobs") and enforce it in scripts, not memory.

## Rules

- Never close a defect with only a fix to the instance.
- Never tune a check, threshold or tolerance until a failing case passes;
  never move design content to satisfy a check or camera.
- A record without a reproduction test, a class, and a control tier is
  incomplete.
- Prose in AGENTS.md or memory documents what the scripts enforce; it is
  never the enforcement.
- Keep records short and factual; measurements, not adjectives.

See [worked example](example.md) for a complete record.
