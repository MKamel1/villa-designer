# ADR-0017: Thermal and cooling model for window decisions

**Status:** accepted, 2026-09-24. **Deciders:** client (scope), AI (method).

## Context

The AI is the only design expert on these projects. Window size, orientation,
shading and glass drive cooling load and overheating in a hot-arid climate, so
they cannot be chosen from elevations alone. Glare, HVAC design, electrical and
plumbing go to consultants, and the method records them as missing.

## Decision

- **Engine:** EnergyPlus 25.2, bundled in OpenStudio 3.11.0, which is the
  version the Ladybug Tools `honeybee-energy` CI tests against. It is driven
  from Python by the Ladybug Tools SDK (`requirements-thermal.txt`). The
  bootstrap installs it on the workstation under the user's home, without
  administrator rights, with a pinned SHA-256. Command:
  `ops/workstation/bootstrap.py --thermal`, via `workstation.py setup`.
- **Model:** a single-zone shoebox (`archpipe.thermal.shoebox`). It has one
  exterior wall facing the studied azimuth, and every other surface is
  adiabatic. Levers are window-to-wall ratio, overhang depth, glass (U, SHGC,
  VT) and wall U. Mode is `cooled` (ideal loads at 24/20 °C) or `free`
  (openable windows, for overheating hours). Every assumption is a named
  default in `ASSUMPTIONS` and is echoed in each result. The defaults are
  typical design-stage inputs; **their sources are not yet verified.**
- **Weather:** the site file from climate.onebuilding.org, held in
  `archpipe-sources/cairo-epw`. Cairo West (623680) and Cairo International
  (623660) differ a lot, so the station must match the site. **The site is Sheikh
  Zayed City (client, 2026-09-24), so studies use Cairo West**, the nearest station
  on the western side:

  | Station | Annual mean | CDD18 | HDD18 | Hours > 32 °C | July mean |
  |---|---|---|---|---|---|
  | Cairo West AP | 21.1 °C | 1566 | 446 | 602 | 27.4 °C |
  | Cairo Intl AP | 23.3 °C | 2155 | 232 | 904 | 30.3 °C |

- **Runs:** `workstation.py thermal --job spec/thermal/<job>.json`. Job kinds
  are `climate`, `study` and `validate`. A 72-case study takes 44 s.
- **Comfort thresholds:** reported as diagnostic hour counts (hours above
  26/28/30 °C). They are not pass/fail until CIBSE TM59:2026 and ASHRAE 55
  are held and their criteria verified.

## Validation (Cairo West, 2026-09-24): all pass

| Check | Result |
|---|---|
| Monthly mean dry-bulb, our EPW parse vs the weather converter's `.stat` | max 0.10 °C |
| Direct (beam) solar on the facade, EnergyPlus vs hand geometry (NOAA sun position from `archpipe.solar` + EPW direct-normal) | N +0.68 %, E +0.19 %, S −0.37 %, W −0.37 % (tolerance 2 %) |
| North facade receives the least solar radiation | yes |
| Larger window raises cooling; overhang lowers it; lower SHGC lowers it | 145.7 → 203.4 / 118.4 / 117.1 kWh/m² |

**Diagnosed, not tuned:** the first check compared *total* incident solar
with a 10 % tolerance and failed on the north facade (−16 %). Splitting the
radiation showed that beam agreed within 0.7 %. The whole difference was sky
diffuse: EnergyPlus uses the anisotropic Perez sky, which gives the north
facade 17 % less sky diffuse than an isotropic sky and the south 34 % more.
The hand check can only be exact for beam, so it now asserts beam (2 %) and
reports totals for information. `tests/test_thermal.py` stops this being
quietly reverted.

## Demonstration, not a decision

This is a 4 × 5 × 3 m bedroom, cooled to 24 °C, on Cairo West weather
(`spec/thermal/window-study-demo.json`). Figures are annual cooling in
kWh/m², with peak in W/m² in brackets.

| Facade, WWR 0.5 | No overhang, SHGC 0.40 | 1.2 m overhang, SHGC 0.25 |
|---|---|---|
| North | 84.1 (29.6) | 72.6 (27.2) |
| East | 154.5 (53.1) | 100.8 (28.6) |
| South | 184.7 (42.2) | 110.5 (26.8) |
| West | 182.7 (70.9) | 115.6 (38.5) |

The west peak stays highest even when shaded: a horizontal overhang does
little against low western sun. So vertical fins or external blinds are the
next shading type to add.

## Daylight and fins (added 2026-09-25)

- **Vertical fins:** `fin_m` adds fins at both jambs of each window, full
  window height, as a new shading lever beside `overhang_m`.
- **Daylight factor:** `thermal.daylight_factor` computes it on a 0.5 m
  grid at 0.85 m work-plane height, using Radiance `rtrace` under the CIE
  overcast sky (`gensky -c`) normalised to 10 000 lux. The job kind is
  `daylight`, run with `workstation.py thermal`. Surface reflectances are
  stated assumptions (walls 0.5, ceiling 0.8, floor 0.2).
- **Targets now verified:** SLL Code for Lighting 2012, Table 5.2 (p. 120),
  gives the minimum average daylight factor for bedrooms (1.0 %), living
  rooms (1.5 %) and kitchens (2.0 %). These are cards `sll-min-adf-*`.
  EN 17037 is still not held.
- **Validation (`spec/thermal/daylight-validate.json`), all pass:**
  - an unobstructed upward probe reads a daylight factor of 99.8 %
    (sky normalisation);
  - the simulated average daylight factor of 3.04 % is within 27 % of the
    simplified Lynes formula's 4.14 % (Baker & Steemers p. 65, a
    first-approximation formula; tolerance 35 %);
  - a larger window raises daylight (5.06 %), halving visible
    transmittance gives 0.45×, and a 1.2 m overhang (1.58 %) or 0.6 m fins
    (2.66 %) lower it.

## Not yet covered (next)

- 2050s morphed weather for TM59:2026.
- Annual climate-based daylight (sDA/ASE) and glare, which is consultant
  scope.
- Glazing records from the LBNL IGDB, which needs a free account.

## Rejected

- **A whole-building model at concept stage.** Too slow to explore, and its
  inputs don't exist yet. The shoebox isolates the window decision; the
  whole-building model belongs to the HVAC consultant.
- **Asserting total incident solar against an isotropic hand calculation.**
  It is physically wrong for vertical surfaces (see Validation).
- **System-wide `.deb` install.** It needs administrator rights on a shared
  worker.
