# LDK lessons

1. **The index was empty, the PDFs were not.** `scripts/knowledge.py` returned `[]` because `~/archpipe-sources/_index` holds no books on this
   workstation. The licensed PDFs live in `~/ai-projects/archpipe-knowledge-data/drop_in/done/`. Guard: `tests/landscape/rules/test_source_quotes.py`
   reads those PDFs directly and fails if a card's quote or number is not on the cited page. Three of the books the brief names
   (A Pattern Language, Site Analysis, BR 209) are in no corpus here; they are GAPs, not guesses.
2. **A page can carry another page's passage.** I first cited the 1:4 enclosure sentence to 340-8 (the figure's page); the text is on 340-4. The quote
   guard failed on it. Cite the page where the sentence is printed, not where its figure is.
3. **Interleaved columns defeat exact-quote checks.** Time-Saver pages extract line-interleaved, so a contiguous match failed on a correct quote.
   The guard falls back to "every number and 85 % of the words". Prove it fails closed: `GuardFailsClosed` changes 115 to 125 and expects a miss.
4. **A near-by figure is not the figure.** Time-Saver's 300-450 mm pool depth looks like a koi depth. It is a US fountain-pool figure. The card is named `...-NOT-KOI`
   and a test asserts no rule uses it.
5. **Check the context of every number.** The 900/1 200 mm fire-ring space is accessible-camping ground space, the 1 500 mm seat distance is for a council ring of 1 800 mm or more, the
   600 mm pool margin is for splash. Each card's `note` says what the figure is and is not; severity drops to `warn` where the context is borrowed.
6. **The proof on the real garden needs honest gaps.** The garden data has no water need, slope, step or soil-depth fields. Rules report `not_evaluated` instead of
   guessing; the result (6 fail, 1 warn) names exactly which checks did not run. Guard: `test_what_cannot_be_judged_is_not_a_pass`, and a snapshot test that rebuilds the
   garden (26 s) and fails if the adapter and the committed snapshot drift.
7. **A borderline fail is a near miss, not a verdict.** The rosemary trough reads 245 mm against 250 mm; the 245 mm is soil top height, an upper bound. Reported as a 5 mm
   near miss with that caveat, not as a defect proven.
8. **An agent's quote is a claim until a guard reads it.** Research agents returned 71 web and 80 book passages; a test now reads each web card's snapshot (and each book card's
   PDF page) and fails closed on a changed figure or an invented sentence. Eight pages were also re-fetched live by hand. Not every web quote survives a JS-rendered page: `LDK_LIVE=1` reports the ones that do not.
9. **A source can contradict itself.** The International Fire Code extract prints "15 feet (3048 mm)" (15 ft is 4 572 mm). The card keeps the printed text and the card note says which figure the rule uses. Check the arithmetic in the source, not only the quote.
10. **Absence of a standing zone must not read as success.** A rule that only loops over zones is silent when the zone is missing. LS-STAND-AREA reports `not_evaluated` for the whole garden when no standing zone exists, so the 10-20 person brief cannot pass by omission.
11. **A figure about a different thing is a trap in both directions.** Metric Handbook's 0.3 m2 standing area is a crowd-safety maximum; Neufert's 355 mm is a lily pool; the 6 m safety shelf is a stormwater pond; EN 124 is a drainage standard. Each is a card marked NOT-USED or a warn-grade rule that says what it is; tests assert the NOT cards are wired to nothing.
12. **Withdraw, do not hedge.** Marking the memory-cited Pattern Language rules "unverified" still let critics cite them. They are moved to `withdrawn` (not Rule objects, source card removed); the loader refuses a withdrawn id that is also active.
13. **A scanned book is not a held book.** Unwin's PDF has no text layer, so "held" did not mean "readable". The agent that found it said so instead of inventing a passage.
