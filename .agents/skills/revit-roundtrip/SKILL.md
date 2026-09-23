---
name: revit-roundtrip
description: Author, extract, inspect, or debug this project's Revit models and native drawings, including measured furniture, finishes, and review markup. Use for Revit automation and round-trip verification.
---

Read [Revit lessons](../../../docs/LEARNINGS.md) and the relevant
[working agreement](../../../CLAUDE.md) constraints. Current target is
Revit 2027; its files cannot be reopened in older versions.

For the bedroom capability test use
`scripts/run_bedroom.py --resume`. Reuse only matching recorded evidence;
do not delete a lock until its owning process has been checked. Inspect every failed stage's log and expected
artifact. The runner checks freshness because pyRevit can exit zero after
a script error. Do not launch concurrent Revit writers against one model.

For other models, identify the authorized authored input and target copy
before adapting the workflow. Pass absolute script paths. Resolve/open
the document explicitly, activate symbols, convert length units at the
boundary, save, re-extract, and verify against dimensions chosen before
the model existed.

Keep all measured furniture as obstacles. Catalogue figures describe
requirements, not replacement geometry. Preserve insertion-point versus
bounding-box-centre distinctions and world versus local rotations.
Unknown sizes or arbitrary-angle boxes without local footprints are
limitations, not clean passes.

Native drawing tests require native view types and exported geometry.
Read back authored finishes and labelled synthetic text/clouds from the
saved model. A synthetic annotation is never client approval. Review in
the authoring tool; the legacy drawing converter is a separate workflow.

Persist new facts in the learning index and owning tests. The optional
[MCP tools](../../../docs/MCP.md) expose these same operations; they do
not bypass model validation or grant new authority.

When maintaining the MCP wrapper, keep its protocol input separate from
noninteractive children. After refreshing the example evidence, run
`scripts/test_mcp.py --cached-run` to verify the real transport and reuse path.
