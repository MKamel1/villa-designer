# Lessons, lane MK

- MK-01 (frame): RV2's panel offsets exist only while a sheet is drawn. Recorded by spying on `plans._draw_plan` during RV2's own render, and every ingest re-verifies the frame against the issued PDF (room tags inside their rooms, 30/30 on A-101/111/121/131). Guard: `test_mirrored_and_rotated_frames_are_caught`, `test_ingest_refuses_a_frame_that_no_longer_matches_the_sheet`.
- MK-02 (pick point): a PDF sticky note's anchor is its icon's top-left, not the rect centre; the centre was 175 mm off at 1:50 and missed the luminaire. Guard: round-trip test links a luminaire from a Text note.
- MK-03 (tolerance): 3 mm of paper (150 mm at 1:50) lists 4 luminaires round one pick; all are reported as ambiguous alternatives rather than one guessed.
- MK-04: 2-value railing profiles (site edge rails) are relative to the placement; 3-value ones are absolute.
