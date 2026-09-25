# Existing-rule audit

The legacy engine remains available for diagnostic comparisons, preserving its tools and rendering inputs. No existing numerical target currently has the required verified passage, edition and applicability. None is enabled as a published requirement in stage approval. Geometry clash calculations remain useful observations.

| Rule | Stage | Existing readable citation | Status |
|---|---|---|---|
| SAN-01 | 3 | Neufert, Architects' Data -- dwelling schedule: every dwelling requires sanitary accommodation; near-universal code requirement | Unresolved; diagnostic only |
| CIRC-01 | 3 | Alexander, A Pattern Language -- 127 Intimacy Gradient; Neufert, Architects' Data -- circulation: 900 mm minimum clear width in a dwelling | Unresolved; diagnostic only |
| CIRC-02 | 3 | Alexander, A Pattern Language -- 110 Main Entrance, 112 Entrance Transition, 130 Entrance Room; Neufert, Architects' Data -- entrances: a draught lobby or threshold zone | Unresolved; diagnostic only |
| AREA-01 | 4 | Neufert, Architects' Data -- minimum floor areas by room type | Unresolved; diagnostic only |
| DIM-01 | 4 | General practice: below ~2.4 m a room will not take a bed plus circulation | Unresolved; diagnostic only |
| DOOR-01 | 4 | Neufert, Architects' Data -- doors: clear opening widths by room type | Unresolved; diagnostic only |
| FURN-01 | 4 | Geometric clash against the wall solid; footprints from Neufert, Architects' Data | Unresolved; diagnostic only |
| FURN-02 | 4 | Neufert, Architects' Data -- clearances by furniture type | Unresolved; diagnostic only |
| FURN-03 | 4 | Geometric clash between footprints; footprints from Neufert, Architects' Data | Unresolved; diagnostic only |
| DOOR-02 | 4 | Neufert, Architects' Data -- doors: the leaf must open through 90 degrees | Unresolved; diagnostic only |
| LIGHT-01 | 4 | Neufert, Architects' Data -- daylight: glazing area at least 1/8 of floor area in habitable rooms | Unresolved; diagnostic only |
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
| CIRC-03 | verified | Client decision 2026-09-25: 900 mm (AD M M4(2) para 2.22a card). Mitton p. 68 gives 914 mm (36 in); the 1.6 % difference is within the close-values policy. Using the hall width for routes inside rooms is this decision, not AD M's own scope. |
| DIM-01 | unresolved | The generic 2.4 m has no source. NDSS gives widths by room type (2.15, 2.75 and 2.55 m). Split the rule by room type. |
| DOOR-01 | unresolved | AD M ties door width to how the corridor approaches it (Table 2.1), not to room type. The AD M entrance minimum is 775 mm; the legacy value is 900 mm. |

**Kitchen planning evidence** (NKBA, free edition): work aisle 1067 mm for one
cook and 1219 mm for several; walkway 914 mm; one of two perpendicular
walkways 1067 mm; seating with no traffic behind 813 mm; dishwasher within
914 mm of the sink; 533 mm standing space beside the dishwasher. These are
ready for a kitchen checker; no rule uses them yet.

No rule is enabled for approval yet: that needs every parameter verified and
the mapping marked complete.
