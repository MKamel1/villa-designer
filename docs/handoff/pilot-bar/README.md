# Consultant hand-off: pilot-bar

Generated from `spec/concepts/pilot/bar.yaml` by `scripts/handoff.py`. Every file here is computed from that spec. This is design guidance, not local code compliance.

## Supplied

| File | Content |
|---|---|
| rooms.csv, doors.csv, windows.csv, furniture.csv | Schedules |
| quantities.json | Floor and wall quantities per level; relative cost (AECOM MEH 2026 Gulf villa rates, relative only) |
| model.ifc | IFC4: storeys, walls, openings with doors/windows, spaces (geometry checked against the spec by tests) |
| findings.json | Rule engine findings (2); every rule's source is in docs/guidance/rule-audit.md |

## Room thermal screen (free-running TM59:2026 criteria, not an assessment)

| Room | Azimuth | WWR | Criterion a (hours / limit) | Criterion b (nights) | Pass |
|---|---|---|---|---|---|
| study | 180.0 | 0.283 | 78 / 59 | - | no |
| guest | 180.0 | 0.268 | 131 / 110 | 36 | no |
| living | 0.0 | 0.15 | 32 / 59 | - | yes |
| dining | 0.0 | 0.242 | 42 / 59 | - | yes |
| kitchen | 0.0 | 0.24 | 42 / 59 | - | yes |
| main-bedroom | 180.0 | 0.258 | 133 / 110 | 36 | no |
| family | 0.0 | 0.24 | 42 / 59 | - | yes |
| bed-2 | 0.0 | 0.25 | 65 / 110 | 28 | no |
| bed-3 | 0.0 | 0.245 | 65 / 110 | 28 | no |

## MISSING in-house: needs a consultant

| Scope | Who | What we hand over |
|---|---|---|
| Glare (DGP) and detailed daylight compliance | daylight consultant | room window sizes and orientations (windows.csv); TM59 screen |
| HVAC design and sizing | MEP engineer | room list and areas (rooms.csv); free-running TM59 screen per room; IFC |
| Electrical design | electrical engineer | rooms.csv; IFC; lighting layout when authored |
| Plumbing and drainage | plumbing engineer | wet rooms in rooms.csv; wet-stack status in the concept report; IFC |
| Structural design and certification | structural engineer | IFC walls and openings; spans implied by rooms.csv |
| Permits and local code compliance (Egypt) | local architect of record | every sheet here is best-practice guidance, not local compliance |
| Acoustics end-check | acoustician (at the end, per the method) | room adjacencies; build-ups when specified |
