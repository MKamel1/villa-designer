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
  "id": "magney-house",
  "name": "Magney House, Bingie Point",
  "architect": "Glenn Murcutt",
  "year": 1984,
  "climate": "temperate coastal (for reference only; not a hot-dry analogue)",
  "sources": [{"source_id": "precedents-in-architecture", "locator": "Glenn Murcutt, printed pages 156-159"}],
  "typology": "bar",                         // an id from knowledge/typologies.json
  "organization": "linear",                  // Ching: centralized|linear|radial|clustered|grid
  "storeys": 1,
  "rooms": [{"id": "living", "use": "living", "area_m2": null}],   // null = not published; never guessed
  "adjacency": [["entry", "living"], ["living", "kitchen"]],
  "zoning": {"public": ["living", "kitchen"], "private": ["bed1", "bed2"]},
  "circulation": "single-loaded spine along the south side",
  "orientation": "long axis east-west; glazing north (southern hemisphere sun side)",
  "section": "single volume, curved roof, clerestory",
  "outdoor_relation": "verandah along the sun side",
  "diagram_themes": ["structure", "natural light", "massing", "plan to section", "circulation to use-space",
                     "unit to whole", "repetitive to unique", "symmetry and balance", "geometry",
                     "additive and subtractive", "hierarchy"],
  "notes": "what this precedent teaches for a villa, in one or two sentences",
  "verified": "2026-09-25 by <reader>: pages and diagrams read"
}
```

**Rules**
- Record what the source shows. An unknown value is `null`, never a guess.
- `diagram_themes` uses the book's own analysis vocabulary. Record only the
  themes whose diagrams were read.
- Climate is recorded so a precedent is not transplanted blindly. A
  southern-hemisphere house faces the sun to the north.
- The calibration test (`tests/test_concept_calibration.py`, planned) runs
  the critic on every record against seeded-bad mutations: rooms without
  windows, private rooms reached through the living room, split wet stacks.
