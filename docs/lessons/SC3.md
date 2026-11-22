# SC3 lessons (south B wall roof slot, dining pendant body, 2026-11-22)

* **A fix that "keeps the old measure" hides the next defect of the same class.** SC2 left `clearance_problems` measuring walls
  along the ramp against the deck soffit (a comment said so), so the south B wall's 150 mm slot under the roof was invisible to it
  and to every later check. The wall-top guard now reads every wall against what is above it (`revit_spec.wall_top_readings`), and
  `clearance_problems` measures along-ramp walls against the roof beyond the deck too. Guard: `tests/model/test_sc3_walltop.py`
  fails on the real pre-fix spec (the spec without its appended infill: wall #9, 150 mm open) and stays quiet on the other 35 walls.
* **Ids that are list indices make "split the wall" a migration, "append an element" free.** The slot was closed by appending an
  infill (`spec-ramp-wall-infill-3`, the mechanism the ramp soffit already uses) rather than splitting wall 9, which would renumber
  every later `wall-*` id and every approval keyed on them. Test: wall count, wall 9's extent and the three earlier infills are pinned.
* **An appended coplanar element widens an approved host face.** The new infill's face (y -20.801) is coplanar with the hood canopy's
  host face, so the face grew from x 15.212..15.412 to 12.777..15.412 and the lead-review guard refused the build. The approved
  13 mm movement and the face top did not change; the row was updated mechanically and flagged (same class as SC2's).
* **A constant in a record can disagree with the product it names for a whole lane without any test noticing.** The QA03 body was
  drawn 59 x 59 x 60 mm because its wire shape was the only one `c3-part-exemptions.json` admits; the 250 mm body was a comment, not
  a check. Guard: `tests/test_villa_render_pendant_dims.py` reads the published size from the product's own LDT header and compares
  every drawn pendant body (+-5 mm); it fails on the pre-SC3 body (59 x 59 x 60 vs 250). The exemption was extended with the product
  data as evidence (the shape is not shrunk to fit the exemption).
* **A preview scene with extra views must drop the frozen exposure record.** `require_record` demands the view inventory equal the
  measured one; build the preview copy without `exposure_groups`/`exposure_group_mode` (as SC2 did) rather than editing the record.
* **A job that waits for another by `pgrep -f <name>` matches its own shell.** The measure-exposure job spun forever because its
  own command line contained the name it polled for; submit dependent jobs after the first one ends instead.
