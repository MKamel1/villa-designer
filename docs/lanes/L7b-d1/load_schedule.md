# Load schedule and maximum demand, D1 villa

Supply 220/380 V 50 Hz, TT. Diversity: Whitfield Table 6.2 household column (EL-WHIT-T62-DIV); socket radials are counted at their breaker rating.

- Connected load (sum of Ib, single-phase equivalent at 220 V): 153.6 kVA
- Maximum demand after diversity: **85.0 kVA** = 386.4 A single-phase equivalent
- Worst-phase line current on three phases: 128.9 A; incomer 160 A
- Supply recommendation: **three-phase**. single-phase equivalent demand 386 A is above the 63 A policy limit for one phase; three phases give a worst-phase line current of 129 A. policy threshold (ours): above a 63 A single-phase service the villa is recommended on three phases; the utility's actual single-phase limit is not verified

## By board (own diversified demand)

| board | circuits | demand kVA | worst-phase line A |
|---|---|---|---|
| MDB | 6 | 12.1 | - |
| DB-B | 34 | 48.2 | 81.7 |
| DB-GF | 20 | 29.3 | 44.8 |

## By category (installation)

| category | circuits | connected A | demand A | demand kVA |
|---|---|---|---|---|
| ac | 8 | 68.2 | 68.2 | 15.0 |
| cooker | 2 | 40.9 | 26.3 | 5.8 |
| ev | 1 | 33.6 | 33.6 | 7.4 |
| lighting | 6 | 8.7 | 5.7 | 1.3 |
| sockets | 29 | 472.0 | 200.8 | 44.2 |
| standard | 11 | 50.0 | 26.8 | 5.9 |
| thermo_wh | 3 | 25.0 | 25.0 | 5.5 |

## Sensitivity to the socket-circuit assumption (the headline above is the upper bound; sizing uses it)

The carded rule (100 % of the largest circuit + 40 % of every other) is applied to the breaker rating of each socket radial. With many radials it dominates, so the headline is an upper bound. The table shows the demand if the radials carried a fraction of their rating; the reduced factors are policy, not sourced. The three-phase recommendation holds in every row (each is above the 63 A single-phase limit).

| socket current factor | demand kVA | 1-ph equivalent A | worst-phase 3-ph line A |
|---|---|---|---|
| 1.0 | 85.0 | 386.4 | 128.8 |
| 0.5 | 62.9 | 286.0 | 95.3 |
| 0.25 | 51.9 | 235.8 | 78.6 |

## Phases (sum of Ib)

L1 232.7 A, L2 232.9 A, L3 232.7 A
