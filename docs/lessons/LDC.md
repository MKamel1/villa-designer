# Lessons, lane LDC (landscape critics)

Each defect or near-miss: why it was missed, and the guard now in place.

1. **Seeded defects tuned until they trip are not evidence.** The first versions of `seat-in-summer-sun` (seats at 4.5 h, not 6 h) and `evergreen-over-lounge` (a 15 m tree whose
   shadow in a 33 degree December sun lands 14 m away) did not trip their criteria; I changed the defects, not the checks, which is legitimate but makes set 1 a sensitivity test only.
   Guard: PREREG.md discloses it; set 2 (`seeds_heldout.py`) was written and committed before it was run, and its one miss (A-ENCLOSURE at exactly 50 %) is reported.
2. **A coordinate-frame slip in intuition, not code: the sun and wind come from the west here.** I first put the shading tree east of the seats; model +y bears 20 degrees true, so the low
   winter sun and the prevailing north wind both act along -y. Guard: `test_evergreen_crown_reduces_winter_sun` and the fire-wind check use the LDS frame; `docs/lanes/LDC.md` lists the site facts.
3. **A criterion that cannot fail on this site is not a check.** C-SUMMER-EVENING cannot fail in a 3 m sunken garden (0.07 h mean); it would have passed everything. Guard: it is reported but
   no defect claims it, and C-SUMMER-SHADE uses the full-day 6 h sun definition instead.
4. **Precedents drawn for a different job cannot calibrate site critics.** A precedent has no brief, species or site layers, so false-fail is unmeasurable for three of four critics.
   Guard: `calibrated` requires evaluated professional-good items; the table says `recall-only`, never "calibrated".
5. **My own drawing is a confound.** The first precedent layouts carried paths I had guessed; A-PATH-TERMINUS then "failed" professional gardens. I removed the guesses (disclosed in PREREG.md) rather than loosening the check.
6. **Plan-image VLM scored a bad garden 2 on six of seven criteria.** The model reads symbol-level layers as present; D1's real defects are brief-level. Guard: gate rule (separation >= 0.30 and no good scored 0) demoted all seven without a prompt tweak; photo-level criteria are confounded by medium and never gate.
7. **Seats as walking obstacles disconnected the lounge.** Treating 0.6 m chairs as obstacles with a 0.3 m person-radius erosion cut the garden into islands; every use looked unreachable. Guard: reachability test on the reference scheme (`BaseIsQuiet`), seats are destinations not obstacles.
