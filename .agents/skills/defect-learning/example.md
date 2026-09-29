# Worked example (D1 round 2-3, handrail / chimney / duct)

```
### wall-mount-from-room-outline — wall-mounted items placed inside the wall
- Observed: stair handrail rendered inside the plaster (only brackets visible, v11);
  dirty-kitchen hood chimney and duct inside the wall thickness (v17).
- Found by / stage: lead review of finals / critic of drafts; should have been
  caught at scene export (the finished faces were known there).
- Reproduction: tests/test_render_standard.py::BuriedFixtures (old rail frozen by value);
  tests/test_d1_wp1.py::test_dirty_kitchen_duct_rises_from_the_hood_chimney
- Direct cause: offsets taken from the party-wall line / room rectangle (wall centre)
  instead of the finished plaster face.
- Escape: float guard passed (items touched the wall); no check that a fixture is in
  front of the face it mounts on; nobody looked at the element before the full draft.
- Contributing factors: two coordinate notions (room rect vs clear rect) both available,
  no single accessor for "the face I mount on".
- Class: an item mounted on a surface was positioned from a structural/reference line,
  not the finished surface.
- Siblings: handrail, hood chimney, extract duct, grilles, sconces, mirrors, trellises,
  curtain tracks (curtains had the same defect in round 2).
- Control tier: 1 (planned) — one finished_face(room, side) accessor used by every
  wall-mounted builder; raw room rects banned for mounting (lint test). Tier 2 meanwhile:
  BuriedFixtures check at scene export.
- Proofs: fires on the old rail and the old chimney; quiet on the current scene;
  generalises to D2/D3 and to an injected sconce 50 mm behind a face.
- Registry: wall-mount-finished-face
```
