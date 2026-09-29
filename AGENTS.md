# Project instructions

Never introduce notation without defining its symbols, indices,
abbreviations and operators in plain language.

Read `docs/ROADMAP.md` for current scope and `CLAUDE.md` for the shared
working agreement. The bedroom is an end-to-end capability example; it
does not replace the eight-stage villa method or approve real design gates.

Use `docs/LEARNINGS.md` for measured traps and the relevant project skill
for repeatable work. Keep deterministic review/lighting arithmetic in
Python; agent roles interpret results and choose bounded next steps.

Run `scripts/verify.py` and affected regression tests before claiming a
code change works. For native model work, use `scripts/run_bedroom.py` and
inspect `out/bedroom-acceptance.json`; CLI exit zero alone is insufficient.
Generated extracts are never hand-edited. The specification is authored
input for the example; Revit supplies the geometry actually reviewed.

Passing tests is not proof that a visible result is right. For anything a
client will see (renders, drawings, models): produce a preview and have it
reviewed before integration; measure external inputs (asset size, units,
facing, licences) instead of trusting them; fix the design's cause, never
bend the design to satisfy a camera, meter or check; and work in small
packages with a checkpoint after diagnosis and after the first fix.
Details: `.agents/skills/villa-render/SKILL.md`, "Integration discipline".

Whenever anything is found wrong (client, reviewer, test, render, read-back,
agent), follow `.agents/skills/defect-learning/SKILL.md`: capture, reproduce
on the real case, find why it escaped, generalise to its class and siblings,
prevent by construction before adding a fail-closed check, prove it fires,
stays quiet and generalises, then register it.

Update code/tests, the learning index, and affected workflows together
when a demonstrated failure changes the operating procedure. Do not
silently treat historical setup notes as current evidence.
