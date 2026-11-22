# LDP lessons

- **Collecting is the bottleneck, not measuring.** Search tools return summaries, so most "published gardens" are large public projects or have no scale bar; of ~60 candidates opened, 12 south and 2–3 north were measurable. Guard: the loader reports n_usable per metric and writes GAP below 6 instead of a thin range (`test_too_few_gardens_is_gap`).
- **A house plan is not a landscape plan.** Plans read from ArchDaily house drawings give area, surface split and trees, but no plant symbols, paths or heights; fields with no data in either pass are GAP. Source landscape plans (HALS, designer portfolios) next time.
- **Independent passes still share the picture.** Both passes used the same hand-estimated scale bars, so agreement bounds reading noise, not truth. Spread limits (0.25 metric, 0.5 garden) are policy, stated as such.
- **Size mismatch hides in "similar size".** The sourced gardens had median ~157 m² against D1's 57 m²; size-dependent ranges would have been silently wrong. Guard: the size band in `derive` and `test_size_band_excludes_big_gardens`.
- **Freezing needs a guard, not a promise.** `freeze()` refuses to overwrite; `check_frozen` compares the content hash and the file hash recorded in docs/lanes/LDP.md.
- **Sourcing agents drift to whole-house plans again, and the scale bar is the scarce part.** Second pass: 16 gardens added, only 9 with a scale, 2 south with planting detail. Guard: build.py drops plan numerics from unscaled gardens (`test_unscaled_garden_has_no_plan_numerics`); ranges stay GAP at n<6. Do not retry with the same search tools: use a browser session for HALS/RHS.
- **A bot challenge is a stop sign, not a puzzle.** LOC/HALS and some design sites answer scripts with Cloudflare; those sources need a human-driven browser.
- **Calibration photos picked by script were 62 % wrong** (55 of 88 interior/facade/aerial/duplicate). Guard: `removed_photos` records the screen; any new photo list must be viewed before use.
