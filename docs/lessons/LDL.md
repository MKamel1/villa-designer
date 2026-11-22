# LDL lessons

1. **A fetch tool that summarises is not a source.** Seven of nine research agents read pages through a summarising fetch and reported
   "verbatim" quotes. Re-fetching the pages and matching every quote (`verify_quotes`) found 6 wrong URLs (underscore instead of hyphen: the
   cited page does not exist), 9 stitched or paraphrased quotes and a page-normalising bug of my own (a quote containing `<6.0) ... (>8.0` was
   read as an HTML tag and stripped, which made 3 true quotes look false). Guard: the re-check is a script plus a test that caps unmatched quotes at 2 %; verify
   the checker against a quote that is known true before believing its failures.
2. **Silence is not a pass.** 54 of 78 species have no sourced heat tolerance. The first viability function returned `unknown` for 62 species
   whenever any factor was a GAP, which hid the real failures (frost-tender, heat-intolerant). Guard: per-factor results and a verdict order
   (fail > conditional > unverified > viable), tests `test_a_fail_outranks_a_gap` and `test_gap_gives_unverified_never_viable`.
3. **Pet toxicity is not human toxicity.** ASPCA and NC State pet tags were kept in `notes`, never in `toxicity_people`; 50 species stay GAP.
4. **A good-looking asset is not the species.** Poly Haven's "jacaranda_tree" has maple-like leaves; the bougainvillea model is a nursery pot on a
   plane; the banana palm has no textures; a lavender model is 3.9 m tall. Grades come from looking at 5 m and 15 m renders, with the species fit
   recorded separately (`species_fit`: a look-alike can never make a species drawable; test `test_look_alike_cannot_map_to_species`).
5. **The GPU queue can block a preview.** The first GPU job stayed queued behind other lanes; a CPU `jobq` job (`--cpu` flag in `asset_preview.py`)
   finished the 33 assets in 3 minutes. `jobq --cwd` did not apply to the Blender script path: give absolute script paths.
6. **The held dry-climate guide holds principles, not species data.** Do not promise per-species attributes from Time-Saver section 550 (the
   xeriscape pages, printed 333-335, and Tables 550-1, 550-3, 550-4, 550-7); the scan's printed page labels are flagged unreliable.
7. **Research agents write plausible enums.** Mappings such as "water need low" to `low` or `Resistance To Challenges: Drought` to `moderate` are judgment calls;
   each record keeps the source wording in `text` so a reviewer can disagree.
