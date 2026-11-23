# HY lessons

* **Legacy modules were never run one at a time.** The lead gates on the lane suite; 17 modules rotted behind it as lanes changed shared
  data (lighting, garden, requirements, approvals). Guard: run the sweep (`scripts/run_tests.py` per module) at each integration; the list is in `docs/lanes/HY.md`.
* **Hash-bound stages must exclude fields attached after the binding.** P2 attached element ids "last" but `drape_appearance` hashed the part
  after that, so the cached reference was stale for every consumer of a finished scene. Guard: `physical_digest` + `test_identity_fields_do_not_stale_the_binding_but_geometry_does` (fires when geometry moves, quiet for id fields).
* **AST fingerprints are Python-version dependent.** `ast.dump` changed in 3.13; 111 of 112 frozen digests were reproduced only with `show_empty=True`. Guard: `FP()` in `tests/test_c14_phase2b.py`; the reproduction count is in the lane doc.
* **A guard whose "real" case deletes something the design no longer has is vacuous** (`villa_lighting_prep_task_illuminance` removed DLN fixtures that L6b dropped; the clean case failed, and had the real case been the only one run it would have passed silently). Guard: the registry's real case now removes the current prep fittings and fires, the clean case is quiet.
* **A frozen inventory should be compared as an explicit reviewed delta**, not bitwise and not re-frozen: `test_support_mounting` lists the 9 added and 22 removed ids with their cause, so an unexplained id still fails.
* **Retired is not passing.** Old-garden checks in `verify.py` print `SKIP ... retired:` with the decision, and the 22 decided-garden props with no intake entry are printed, not filtered silently.
