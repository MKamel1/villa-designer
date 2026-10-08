# G4d reproduction and promotion

Read [the report](../garden-g4d-report.md). The client-approved scope is
northern mineral finishes, low-output uplights and one open-sky evening
camera. Geometry and existing views remain fixed. Do not modify the shared
`out/villa/round3` or `assets/user` symlinks.

1. Export the committed pre-change producer to local
   `out/garden-g4d/before-scene.json`; keep it as the fixed-design comparator.
   Do not overwrite it with the changed scene when rerunning this package.
2. Run `scripts/garden_g4d_evidence.py --specimens` with `PYTHONPATH=src`.
   Fixtures pass physical-part and early renderer metadata checks before
   preview generation. Use actual exported material definitions, including
   runtime materials, rather than the static material dictionary alone.
   Record source flux separately from the fitting's shielded output. Integrate
   the source photometric distribution against the actual aperture geometry;
   never label pre-shield source lumens as final emitted luminaire lumens.
3. Run Blender with `scripts/garden_g6_preview.py -- --input
   out/garden-g4d/specimens.json --output out/garden-g4d/previews-reviewed`.
   The shared driver rejects missing materials before rendering, keeps the
   staging floor below authored ground, supplies close swatches alongside
   the 1.8 m reference, and records geometry/material/light hashes.
4. Review all new appearances independently. Promotion requires current
   receipt hashes; changing a shield, aim, finish or light after preview
   invalidates that preview. Never increase fixture output or move plants
   for a neutral preview. The neutral fill cannot establish evening lux.
5. Review the camera against actual enclosure, physical clearance, every
   actual subject vertex and first-hit rays. A bounding-box crop allegation
   requires actual-vertex confirmation before changing a camera. Neutral
   context remains diagnostic, with partial screening disclosed.
6. Run `scripts/garden_g4d_evidence.py` for authoritative export, C4/C5/C7,
   plant/soffit/camera/support/opening results and exact retained geometry,
   props, existing lights and view comparisons through decoded JSON delivery
   values (native tuples serialize as lists). Preview receipt checks run
   before export. No known-findings baseline exemption is needed.
7. Run focused tests and `NO_COLOR=1 scripts/verify.py --portable` using the
   specified Python, then repeat portable verification with a newly empty
   HOME. Judge exit status. Keep logs and the report current; the lead runs
   the full suite and commits. Native-model or presentation approval remains
   separate.

The repeatable optical/fixture data live in `garden_g4d`, not generated
extracts. `fixture_record` and `material_basis` are G4d's C5/C7 checks;
their generic/assumed scope is explicit. New finishes must also join the
independent audited material register. Unregistered fitting parts, missing
identity/colour-rendering data, stale lenses/shields/soil supports and day
activation of the evening layer are refused.
