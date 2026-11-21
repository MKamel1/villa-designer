# Load schedule and maximum demand, D1 villa

Supply 220/380 V 50 Hz, TT. Diversity: Whitfield Table 6.2 household column (EL-WHIT-T62-DIV); socket radials are counted at their breaker rating.

- Connected load (sum of Ib, single-phase equivalent at 220 V): 137.3 kVA
- Maximum demand after diversity: **77.5 kVA** = 352.2 A single-phase equivalent
- Worst-phase line current on three phases: 117.6 A; incomer 125 A
- Supply recommendation: **three-phase**. single-phase equivalent demand 352 A is above the 63 A policy limit for one phase; three phases give a worst-phase line current of 118 A. policy threshold (ours): above a 63 A single-phase service the villa is recommended on three phases; the utility's actual single-phase limit is not verified

## By board (own diversified demand)

| board | circuits | demand kVA | worst-phase line A |
|---|---|---|---|
| MDB | 6 | 12.1 | - |
| DB-B | 32 | 42.1 | 72.0 |
| DB-GF | 20 | 27.9 | 48.3 |

## By category (installation)

| category | circuits | connected A | demand A | demand kVA |
|---|---|---|---|---|
| ac | 8 | 68.2 | 68.2 | 15.0 |
| cooker | 1 | 13.6 | 11.1 | 2.4 |
| ev | 1 | 33.6 | 33.6 | 7.4 |
| lighting | 7 | 8.0 | 5.3 | 1.2 |
| sockets | 26 | 424.0 | 181.6 | 40.0 |
| standard | 12 | 51.5 | 27.4 | 6.0 |
| thermo_wh | 3 | 25.0 | 25.0 | 5.5 |

## Sensitivity to the socket-circuit assumption (the headline above is the upper bound; sizing uses it)

The carded rule (100 % of the largest circuit + 40 % of every other) is applied to the breaker rating of each socket radial. With many radials it dominates, so the headline is an upper bound. The table shows the demand if the radials carried a fraction of their rating; the reduced factors are policy, not sourced. The three-phase recommendation holds in every row (each is above the 63 A single-phase limit).

| socket current factor | demand kVA | 1-ph equivalent A | worst-phase 3-ph line A |
|---|---|---|---|
| 1.0 | 77.5 | 352.2 | 117.4 |
| 0.5 | 57.5 | 261.4 | 87.1 |
| 0.25 | 47.5 | 216.0 | 72.0 |

## Phases (sum of Ib)

L1 208.3 A, L2 207.9 A, L3 207.7 A
