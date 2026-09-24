# Expert-guided villa design

Start with [coverage and acquisition](coverage-and-acquisition.md), the
[rule audit](rule-audit.md), and the [pilot](villa-pilot.md). The eight original
stages and thirteen backward loops remain in place. Design proposals include
feasibility, landscape, structure, services, comfort, junctions and integrated
review from concept onward. The system supports design and visualization, not
local-code research, permit documents, construction administration or engineering
certification.

The [validation record](validation.md) lists executed checks and remaining design
and source-acquisition work.

The initial library contains scoped, verified public-source paraphrases and
identified licensed references. It is not a complete technical reference library.
No legacy numerical design threshold is currently enabled as a verified published
requirement. The existing calculation tools retain their diagnostic behavior;
their passing results cannot close design gates.

## Use

The Model Context Protocol server connects assistants to project tools. It now
offers `stage_context`, `lookup_evidence`, and `review_stage`. Pass the stage
number, from 0 through 7, and a project-relative manifest path. Defaults exercise
the fictional villa in `knowledge/projects/villa-pilot.json`. For room development
use `knowledge/projects/bedroom.json`. All three operations are read-only.

`stage_context` returns a brief, scoped facts and decisions, missing inputs,
applicable evidence and required deliverables. `lookup_evidence` searches focused
paraphrases and precedent studies rather than dumping books. `review_stage`
combines area/graph/geometry checks with explicit qualitative reviews and missing
evidence. It distinguishes readiness from recorded client approval.

Read the returned unresolved items. Do not ask a non-expert client for duct sizes,
lux values or span tables: ask about routines, sleep, reading, entertaining,
privacy and maintenance, then explain the technical implications. Present:
recommendation, household reason, diagram, evidence, cost/space/maintenance
consequences, and the decision needed.

## Records and provenance

The shared [library](../../knowledge/library.json) contains sources, evidence,
precedents and stage packages. Four evidence categories remain separate:
published technical requirements, professional recommendations, qualitative
principles, and client/project targets. A source being identified does not mean
its contents have been obtained. A public webpage being readable does not grant
image reproduction or full-text redistribution rights.

An evidence card identifies the source, exact edition, page/figure/table/clause or
dated web section, conditions, exceptions, units and verification method. Before
enabling a numerical rule, verify the original value and unit against the original
page, including dimension arrows and footnotes, and attach a meaningful regression
test. Resolve conflicting recommendations by applicability and explain the choice;
do not simply choose the largest dimension.

The [templates](templates.md) describe project and source intake. Licensed
originals stay outside the repository in controlled storage. Project taste stays
inside project manifests. Promote a lesson to shared knowledge only after source
verification; reproduced failures receive regression tests.

## Freshness and integration

Content-based library indexing avoids re-parsing unchanged source content.
In-process review caching includes source editions, project revision, relevant
facts, decisions, rule declarations and artifact hashes. Every cache hit rechecks
artifact content; it does not certify a remote renderer or authoring application.
Cache statistics report reuse, and `scripts/demo_guidance.py` demonstrates it.
Changing a decision's `affects` stages identifies which contexts to revisit;
revision changes conservatively invalidate reviews. No persistent hidden taste or
assistant conclusions are written into shared evidence.

Existing rendering inputs are preserved. For presentation review, record the
current model, rendering input and image hashes plus project revision in a
`render_binding`. This proves file identity, not visual correctness or physical
performance. Claude's existing rendering workflow still performs native read-back,
image inspection and rendering checks. See the [bedroom exercise](bedroom-worked-example.md).

## Acceptance status

All stages have a usable workflow, public evidence, a worked example, failure
cases, deliverables and approval criteria. The villa exercises early design and
whole-building coordination as a labelled scenario. The bedroom exercises the
existing measured model. These are design-guidance demonstrations, not a completed
villa or a freshly rebuilt bedroom. Licensed numerical verification, measured
comfort studies, actual design documents, independently reviewed final proposals
and explicit client decisions remain open and are reported as unresolved.

Run `.venv/Scripts/python scripts/demo_guidance.py` to regenerate the local pilot
report. Run `.venv/Scripts/python -m unittest discover -s tests -p test_guidance.py`,
`.venv/Scripts/python scripts/test_mcp.py`, and
`.venv/Scripts/python scripts/verify.py` for verification.
