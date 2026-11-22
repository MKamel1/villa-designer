# RA2 lessons

* **A receipt digest hashes what exists at its stage.** `room_context_inputs` runs mid-build, before P2 attaches element
  ids; a diff against a finished (id-carrying) scene shows ~940 phantom changes. Guard: `section_diff.py` and
  `refresh_receipts.py` strip ids first; the old tree reproducing all eight stored digests is the sanity gate.
* **Fixture numbering is per room, across kinds.** Removing one `BACK` strip bay renumbered approved
  `marker-STEP-stair-b-04..06` and tripped the approval guard. Keep module counts when trimming a store, or expect re-keyed approvals.
* **Same class as B4 recurred** (`test_mounting_finish_layers` compared a mesh to a pre-P2 fixture). Any consumer that compares or hashes whole mesh dicts must go through `without_ids`/`strip`.
* **A one-axis change can fail a check in another lane's builder**: G1's 16 mm tread overlap broke the under-stair soffit check on the base (`test_d1_round3`); only a full run of the furniture tests showed it.
* **FIX1's candidate check did not run the scene-level swing guard** (RA); B1 only passes because the lead chose RA's position.
