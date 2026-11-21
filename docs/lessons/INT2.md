# INT2 lessons

* **Lanes that branch from different bases hide each other's failures.** RA2 (scene build, mounting guard) branched before the L6b
  lighting redesign; L6b's lane suite never built the full scene. Each was green alone; merged, `support-marker-PATH-landing-gf-02`
  stopped the build. The lane suite named in `INT-integration.md` had no mounting/scene tests, so INT and L6c could not see it.
  **Guard:** `archpipe.exchange.integrate` now also runs `tests/test_mounting*.py tests/test_d1_*.py tests/test_exposure_groups.py`
  and `tests/test_villa_lighting.py`; `docs/lanes/INT-integration.md` lists the same command.
* **A host guard that passes by accident is worse than one that fails.** Wall markers are +y-only (the marker mesh is built in an
  xz plane and `support_mounting` hosts them on a +y shell face). L6b authored landing markers on the west wall (aim +x). Marker 01
  "passed" by hosting on a wall end-cap 0.19 m behind it; marker 02 had nothing within 250 mm. Fix: both on the landing's real
  +y face (south-wall stub x 3.817..4.102). Open: a wall marker whose aim is not +y should be rejected up front, not by luck.
* **Module/package shadowing:** `archpipe/model.py` (spec loader) was shadowed by the `archpipe/model/` package from L2 on, so
  `cli`, `rules`, `verify.py` and ~15 legacy tests were un-importable for weeks. Legacy module renamed `spec_model.py`.
* **Frozen derived tables follow the product binding**: `model/data/derived-sizes.json` listed the old iGuzzini products, so the
  snapshot could not be regenerated after L6c until the table was refreshed (needs the ERCO IES files in `erco/<code>/<code>.ies`).
* **Idempotent job ids hide a changed command**: resubmitting a failed jobq id (even with `--retry`) re-ran the old spec.
  Use a new id when the command changes.
* **Old evaluators outlive their scheme**: `villa_lighting.check` (direct-only, no driver dimming) and 3000 K/LSEVO assertions
  were obsolete after L6b/L6c; the Radiance-verified rows are the gate.
