# Frozen bed geometry fixture attribution

These unchanged imported faces are retained for deterministic regression tests,
not as selected villa products. The geometry receipts record source-file hashes.

- `bed-scandi-geometry.json.gz`: based on “Stained Bare Scandinavian Bed” by
  JudeNavarre, https://sketchfab.com/3d-models/3af9fc8452ca4c1180ce9ae7a9600b79,
  licensed under CC-BY-4.0, https://creativecommons.org/licenses/by/4.0/.
  All imported faces are retained in Blender-converted metre coordinates.
- `bed-forssa-mattress.json.gz`: based on “Bed FORSSA” by leonardgraylar,
  https://sketchfab.com/3d-models/0e4ec2bb5aff42d8a324b3f8ab9ac9de,
  licensed under CC-BY-4.0, https://creativecommons.org/licenses/by/4.0/.
  The actual mattress part is isolated from the complete imported receipt;
  its faces are unchanged.

`bed-round2-measurements.json` additionally records measurements of
“Upholstered Bed / Free model” by cyberfox3d
(https://sketchfab.com/3d-models/7602267cc32e4caf8c92c60b677539be),
“Home Series – Bunk Bed” by spazio_silvestre
(https://sketchfab.com/3d-models/2ba8ccae518d4dc1be00dcdff0d4ac01), and
“Simple wooden bunk bed” by 3DWorkbench
(https://sketchfab.com/3d-models/a7685bd7b2354157b4c1a8264892acf0).
All were downloaded under CC Attribution, re-read by the lead at download;
full source credits are preserved in the asset manifest and library license files.

Round-5 regression data:

- `bed-round5-measurements.json`: unchanged actual extremal triangles (plus
  Cyberfox source-bedding face 5922 for initialization) from “Upholstered Bed /
  Free model” by cyberfox3d, https://sketchfab.com/3d-models/7602267cc32e4caf8c92c60b677539be,
  and “Simple Bunk Bed 3D Model” by sparshgupta,
  https://sketchfab.com/3d-models/2cabd354ef2e4293ae817b01a8fdbf10.
  Both CC-BY-4.0, https://creativecommons.org/licenses/by/4.0/.
  These are bounded regression inputs, not production geometry receipts.
- `bed-round5-upper-containment.json.gz`: the actual scaled 28,224-triangle
  upper source duvet shell from sparshgupta's model, same CC-BY attribution.
  Its outside/inside test points and the previous nearest-plane diagnostic
  are recorded beside source hashes. No source face was edited.

- `bed-round5-heading-support.json.gz`: actual source triangles near the measured duvet headings from the two same CC-BY-4.0 models above, preserving author credits and source hashes in each record.
- `bed-round5-heading-refusal.json`: evaluated diagnostic receipts from those models, recording the prior suspended heading and failed point-anchor correction.
