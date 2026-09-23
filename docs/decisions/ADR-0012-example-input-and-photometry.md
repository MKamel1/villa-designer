# ADR-0012: Explicit example inputs and photometry ownership

Status: implemented for the capability example, 2026-09-22.

The bedroom specification is authored input to an automated Revit build.
The saved Revit model supplies the geometry actually reviewed. Extracts
are generated and never hand-edited. This makes the old blanket claim
"Revit is the only authored file" inaccurate for this particular build
workflow; it is not permission to keep independent authored geometry.

Third-party light families can override their photometric definition
after writes appear successful. `make_render_input.py` therefore joins
the explicit light specification by stable Mark identity to actual
positions/heights in the Revit extract. Orphans and missing identities
fail the join. The result labels both sources.

Actual painted finish hue now comes from Revit; reflectance remains an
explicit simulation assumption. Furniture remains measured box geometry
where exact mesh export is not available, and is labelled as such.

Rejected: treating a family parameter write as proof, silently inventing
photometry, replacing real family dimensions with catalogue assumptions,
or describing proxy output as a final furniture design.

For manually authored real projects, a rebuild from an example input is
not an edit operation. Continue to preserve the user's model, apply
bounded edits, save, and verify through extraction. Promoting the example
builder to a general villa authoring system is separate future work.
