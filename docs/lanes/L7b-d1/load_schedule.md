# Load schedule and maximum demand, D1 villa

Supply 220/380 V 50 Hz, TT. Diversity: Whitfield Table 6.2 household column (EL-WHIT-T62-DIV); socket radials are counted at their breaker rating.

- Connected load (sum of Ib, single-phase equivalent at 220 V): 143.1 kVA
- Maximum demand after diversity: **80.8 kVA** = 367.2 A single-phase equivalent
- Worst-phase line current on three phases: 122.5 A; incomer 125 A
- Supply recommendation: **three-phase**. single-phase equivalent demand 367 A is above the 63 A policy limit for one phase; three phases give a worst-phase line current of 122 A. policy threshold (ours): above a 63 A single-phase service the villa is recommended on three phases; the utility's actual single-phase limit is not verified

## By board (own diversified demand)

| board | circuits | demand kVA | worst-phase line A |
|---|---|---|---|
| MDB | 6 | 12.1 | - |
| DB-B | 32 | 45.4 | 77.1 |
| DB-GF | 19 | 27.9 | 45.7 |

## By category (installation)

| category | circuits | connected A | demand A | demand kVA |
|---|---|---|---|---|
| ac | 8 | 68.2 | 68.2 | 15.0 |
| cooker | 2 | 40.9 | 26.3 | 5.8 |
| ev | 1 | 33.6 | 33.6 | 7.4 |
| lighting | 6 | 8.7 | 5.7 | 1.3 |
| sockets | 26 | 424.0 | 181.6 | 40.0 |
| standard | 11 | 50.0 | 26.8 | 5.9 |
| thermo_wh | 3 | 25.0 | 25.0 | 5.5 |

## Sensitivity to the socket-circuit assumption (the headline above is the upper bound; sizing uses it)

The carded rule (100 % of the largest circuit + 40 % of every other) is applied to the breaker rating of each socket radial. With many radials it dominates, so the headline is an upper bound. The table shows the demand if the radials carried a fraction of their rating; the reduced factors are policy, not sourced. The three-phase recommendation holds in every row (each is above the 63 A single-phase limit).

| socket current factor | demand kVA | 1-ph equivalent A | worst-phase 3-ph line A |
|---|---|---|---|
| 1.0 | 80.8 | 367.2 | 122.4 |
| 0.5 | 60.8 | 276.4 | 92.1 |
| 0.25 | 50.8 | 231.0 | 77.0 |

## Phases (sum of Ib)

L1 216.7 A, L2 216.9 A, L3 216.7 A
