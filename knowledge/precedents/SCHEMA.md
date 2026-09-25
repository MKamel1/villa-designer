# Precedent records

One JSON file per analysed house, in `knowledge/precedents/<id>.json`. This
corpus lets concept design work by search and critique rather than
invention. It supplies:
- typologies with real examples;
- priors for room adjacency and proportion;
- a calibration set, because the critic must rank these good precedents
  above deliberately broken variants.

`candidates.json` lists the 96 houses in *Precedents in Architecture*
(4th ed.) still to be encoded. A candidate becomes a record only after its
pages have been read, including the analytic diagrams as page images
(`knowledge.py image`).

```json
{
  "id": "<slug>",
  "name": "<house name as printed>",
  "architect": "<as printed>",
  "year": null,                              // only if the pages state it
  "climate": null,                           // from a cited source, else null
  "sources": [{"source_id": "precedents-in-architecture", "locator": "<architect>, printed pages <n-m>"}],
  "typology": "<id from knowledge/typologies.json, or null>",
  "organization": "<centralized|linear|radial|clustered|grid, as the diagrams show>",
  "storeys": null,
  "rooms": [{"id": "<room>", "use": "<use>", "area_m2": null}],   // null = not published; never guessed
  "adjacency": [["<room>", "<room>"]],
  "zoning": {"public": [], "private": [], "service": []},
  "circulation": null,
  "orientation": null,
  "section": null,
  "outdoor_relation": null,
  "diagram_themes": [],                      // only themes whose diagrams were read (book vocabulary below)
  "notes": null,
  "verified": "<date> by <reader>: pages and diagrams read"
}
```

The book's diagram vocabulary: structure, natural light, massing, plan to
section, circulation to use-space, unit to whole, repetitive to unique,
symmetry and balance, geometry, additive and subtractive, hierarchy.

**Rules**
- Record what the source shows. An unknown value is `null`, never a guess.
- `diagram_themes` uses the book's own analysis vocabulary. Record only the
  themes whose diagrams were read.
- Climate is recorded so a precedent is not transplanted blindly. A
  southern-hemisphere house faces the sun to the north.
- The calibration test (`tests/test_concept_calibration.py`, planned) runs
  the critic on every record against seeded-bad mutations: rooms without
  windows, private rooms reached through the living room, split wet stacks.
