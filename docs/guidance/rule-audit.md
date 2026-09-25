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
| CIRC-03 | 4 | Neufert, Architects' Data -- circulation: 900 mm minimum clear width in a dwelling | Unresolved; diagnostic only |
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
