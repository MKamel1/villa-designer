# Existing-rule audit

The legacy engine remains available for diagnostic comparisons, preserving its tools and rendering inputs. No existing numerical target currently has the required verified passage, edition and applicability. None is enabled as a published requirement in stage approval. Geometry clash calculations remain useful observations.

| Rule | Stage | Existing readable citation | Status |
|---|---|---|---|
| SAN-01 | 3 | UK AD G para 4.8 with M4(1) and para 5.6 | Verified 2026-09-25 (see below) |
| CIRC-01 | 3 | Alexander, A Pattern Language -- 127 Intimacy Gradient; Neufert, Architects' Data -- circulation: 900 mm minimum clear width in a dwelling | Unresolved; diagnostic only |
| CIRC-02 | 3 | Alexander, A Pattern Language -- 110 Main Entrance, 112 Entrance Transition, 130 Entrance Room; Neufert, Architects' Data -- entrances: a draught lobby or threshold zone | Unresolved; diagnostic only |
| AREA-01 | 4 | Neufert, Architects' Data -- minimum floor areas by room type | Unresolved; diagnostic only |
| DIM-01 | 4 | General practice: below ~2.4 m a room will not take a bed plus circulation | Unresolved; diagnostic only |
| DOOR-01 | 4 | UK AD M Vol 1 para 2.20 and Table 2.1 | Verified 2026-09-25 (see below) |
| FURN-01 | 4 | Geometric clash against the wall solid; footprints from Neufert, Architects' Data | Unresolved; diagnostic only |
| FURN-02 | 4 | Neufert, Architects' Data -- clearances by furniture type | Unresolved; diagnostic only |
| FURN-03 | 4 | Geometric clash between footprints; footprints from Neufert, Architects' Data | Unresolved; diagnostic only |
| DOOR-02 | 4 | Neufert, Architects' Data -- doors: the leaf must open through 90 degrees | Unresolved; diagnostic only |
| LIGHT-01 | 4 | IRC R303.1 via Mitton & Nystuen 4th ed. p. 92 -- glazing at least 8 % of floor area | Verified 2026-09-25 (see below) |
| CIRC-03 | 4 | Neufert, Architects' Data -- circulation: 900 mm minimum clear width in a dwelling | Verified 2026-09-25 (see below) |
| VIEW-01 | 4 | Alexander, A Pattern Language -- 134 Zen View | Unresolved; diagnostic only |

Also audit every catalogue dimension/access target, feasibility efficiency, lighting target and physical-model heuristic. See [machine-readable audit](../../knowledge/rule-audit.json). Page verification must check dimension arrows, clear versus nominal sizes, units, diagram context, exceptions and footnotes. A checked calculation does not verify its benchmark.

## First verified numerical evidence (2026-09-24)

Twelve cards are now verified from held originals: AD K 2013 (private stair
rise/going/pitch, 2R+G, headroom 2 m) and AD M Vol 1 2015+2016 (M4(2) hall
900 mm, door-to-corridor Table 2.1, entrance door 775 mm). Each carries the
printed page, unit and value. `tests/test_evidence_values.py` re-reads the
value from the original page when it is held.

They corroborate part of CIRC-01 and DOOR-01. CIRC-01 is the 900 mm hall
width, for halls and landings. DOOR-01 covers door widths, where AD M ties
the width to how the corridor approaches the door, not to room type. The
legacy rules still cite Neufert and remain diagnostic. They get restructured
to reference verified cards, and their applicability, in the rule-verification
step (W1b). CIRC-03 checks routes between furniture inside a room, and AD M's
hall width does not apply to that.

## Rules mapped to verified evidence (2026-09-25)

`knowledge/rule-evidence.json` maps each rule's numerical parameters to
evidence cards. `guidance.rule_audit()` marks a parameter verified only when
the value the engine uses equals a verified card's value, in the card's unit.

| Rule | State | What changed |
|---|---|---|
| AREA-01 | partly verified | Bedroom minimums changed to 11.5 m² (double) and 7.5 m² (single), per Metric Handbook 7th ed. p. 22-4 quoting NDSS. The legacy values were 12.0 and 8.0 (unsourced Neufert). Living, kitchen, bathroom and WC areas are unresolved. |
| CIRC-01 | partly verified | Hall width 900 mm matches AD M M4(2) para 2.22a. Its privacy test stays qualitative (Alexander 127). |
| SAN-01 | verified | Re-sourced 2026-09-25 to UK AD G (free, held). A WC is required on the entrance storey (4.8 with M4(1)), and a bathroom with bath or shower and basin somewhere in the dwelling (5.6). An upper storey with no WC is no longer a finding, since AD G does not ask for one. Where the entrance storey has no habitable rooms, a WC on the principal storey also satisfies it (AD M para 1.17a, found through the workstation semantic search). |
| LIGHT-01 | verified | Re-sourced 2026-09-25. The legacy 1/8 (12.5 %) was attributed to Neufert but is not in the held 1980 edition. The US code minimum (IRC R303.1, 8 %, quoted by Mitton p. 92) is the minimum-glazing screen; daylight adequacy is judged by SLL minimum ADF. |
| CIRC-03 | verified | Client decision 2026-09-25: 900 mm (AD M M4(2) para 2.22a card). Mitton p. 68 gives 914 mm (36 in); the 1.6 % difference is within the close-values policy. Using the hall width for routes inside rooms is this decision, not AD M's own scope. |
| DIM-01 | partly verified | Split by room type 2026-09-25. Bedrooms use NDSS via the Metric Handbook p. 22-4: single 2.15 m, other doubles 2.55 m, and one double of at least 2.75 m. Living, kitchen, dining and study keep the unsourced generic 2.4 m. |
| DOOR-01 | verified | Restructured 2026-09-25 to UK AD M. The entrance needs 775 mm (para 2.20). Internal doors are set by the corridor serving them (Table 2.1): 750 mm head-on from 900 mm; side approach 750/775/800 mm from 1200/1050/900 mm. A door between two rooms is read as approached from the narrower room; that reading is ours. The unsourced 700 mm WC value is dropped. En-suites and cupboards are exempt (Note 1). |

**Kitchen planning evidence** (NKBA, free edition): work aisle 1067 mm for one
cook and 1219 mm for several; walkway 914 mm; one of two perpendicular
walkways 1067 mm; seating with no traffic behind 813 mm; dishwasher within
914 mm of the sink; 533 mm standing space beside the dishwasher. These are
ready for a kitchen checker; no rule uses them yet.

No rule is enabled for approval yet: that needs every parameter verified and
the mapping marked complete.

## Furniture rules (2026-09-25)

| Rule | State | What changed |
|---|---|---|
| FURN-02 | partly verified (23 of 31) | Clearances re-sourced. **Beds:** AD M 2.25 (750 mm: principal double both sides and foot; other doubles one side and foot; singles one side). **WC, basin, bath:** AD M Diagram 2.5 (1100 / 1100 / 700 mm zones). **Wardrobe front:** Time-Saver p. 87 (914 mm). **Dining:** Time-Saver p. 81 (813 mm), agreeing with NKBA. **Kitchens:** NKBA (1219 multi-cook aisle, 914 walkway). Unresolved: sofa to coffee table, TV distance, fridge, shower, desk. |
| FURN-01, FURN-03 | no number to verify | Physical clash checks (furniture against walls, furniture against furniture) on the model's actual sizes. Catalogue footprints are placeholders until a product is chosen; AD M Appendix D gives minimum sizes for compliance layouts. |

**Context choice for beds.** Time-Saver's bed clearances (22 in / 12 in) are convenience minimums; AD M's 750 mm zones are for accessible and adaptable homes. They are far apart. The villa brief records ageing in place, so AD M applies (close/far policy, docs/guidance/README.md).

**Effect on the bedroom example.** The measured bedroom's wardrobe has 750 mm in front; the sourced value is 914 mm. `scripts/test_mcp.py` now expects exactly that warning.

