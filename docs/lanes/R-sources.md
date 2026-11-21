# Lane R: source cards (2026-11-20)

Cards live in `knowledge/sources/*.json` (one file per document; each file is a list of `SourceCard` records, written by
`knowledge/sources/_build/*.py`, which refuses to write a card whose quote is not found in the page text it names).
`.gitignore` line 46 ignores `sources/`, so the files were added with `git add -f`; the lead should add `!knowledge/sources/` to `.gitignore`.

**Status meaning.** `sourced` = the primary text was read (held book page, or a public preview file that contains the clause).
`std` = the standard itself is paywalled and not read; the card quotes a named secondary that cites it, so it can inform but not gate.
`unverified` = nothing readable found; the card has an empty quote and says what was tried.
Quotes are normalised for whitespace, ligatures, en-dashes and curly quotes only.

**Scope change.** The client dropped Egyptian law/code sourcing mid-run. No Egyptian card was written. What had been read before the stop
(not carded, so unverified for gating): the Andersen English text of ER Art. 93-112 (read in full) and Gazette issue 82 bis (a), 8 Apr 2009, pp. 79-81
(Arabic scan, read by eye: Art. 95-100 agree with the English figures). The English text differs from a-plus-architecture.md in two places the
architecture lane should know: Art. 100 gives step width 110 cm only up to four units per floor and 130 cm for the main stair above four; Art. 98 bis has
a separate, smaller courtyard table for plots with a ground-floor footprint up to 100 m2 and height up to 19 m. The ER is "as amended"; amendments after 2009 were not checked.
The three Egyptian code identifiers (fire, accessibility, electrical) were not found.

## Criterion to card

| Criterion | Card ids | Status |
|---|---|---|
| LS1 stair geometry | UK-ADK-2013-1.3-T1.1-private-stair, -1.3-T1.1-note1-pitch, -1.3-2R+G, -1.5-uniform-steps, -1.11-headroom, -1.16-entrance-storey-width, -1.17-36-risers, -1.20-landings, -1.34-handrail | sourced |
| LS2 open risers / gaps | UK-ADK-2013-1.9-open-risers, -3.3-sphere-climb | sourced |
| LS3 guards | UK-ADK-2013-D3.1-guard-900, -D3.1-guard-1100, -3.1-guard-siting, -K2-performance-600, -3.3-sphere-climb | sourced |
| LS6 smoke detection | UK-ADB1-2019-1.1-alarm-grade, -1.2-1.4-alarm-power, -1.5-large-definition, -1.5-1.7-large-dwellinghouse; BS5839-6-grade-D1/-D2/-LD1/-LD2/-LD3/-no-alarm-in-baths | ADB sourced; BS 5839-6 std |
| LS7 fire separation basement/GF | UK-ADB1-2019-2.5-protected-stairway, -2.16-basement (escape only; separation rule is Egyptian code, not carded) | sourced (UK analogue) |
| LS fire escape windows | UK-ADB1-2019-2.1-habitable-rooms-ground, -2.10-escape-window, -2.10-escape-window-area, -2.10-escape-window-1100 | sourced |
| AC1 accessibility | UK-ADM1-2015-M4(1)-performance, -1.6-approach-900, -1.7-ramp, -1.14-entrance, -1.15-corridor, -1.17-WC, -2.27-WC-M4(2) | sourced |
| EA1 device heights | UK-ADM1-2015-1.18-controls (450-1200 mm); Egyptian code and Metric Handbook socket counts not carded | sourced (heights only) |
| EA2 bathroom zones | IEC60364-7-701-2019-701.30.102-zone0, -701.30.103-zone1, -701.30.104-zone2, -701.30.104-no-zone2-shower, -701.415.1.101-RCD, -701.512.2.4.101.3-zone1-sockets, -701.512.2.4.101.4-zone2-equipment | sourced (ed. 3.0, 2019) |
| EA6 voltage drop | IEC60364-5-52-G52.1-A, -G52.1-B, -annexG-exists | std |
| EA7 fault protection | IEC60364-4-41-2005-411.3.2.2-scope, -T41.1, -411.3.2.3-5s, -411.4.4-Zs, -411.5.3-RA | sourced (ed. 5.0, 2005) |
| EA8 RCD | IEC60364-4-41-AMD1-2017-411.3.3-32A, -411.3.4-luminaires, IEC60364-4-41-2005-411.3.3-20A, IEC60364-7-701-2019-701.415.1.101-RCD; IEC 60364-7-714 (outdoor) not found | sourced |
| EA15 ELV and fire | UK-ADB1-2019-1.1-alarm-grade and the BS5839-6 cards above | see D1 |
| LA3 uniformity, LA4 UGR | EN12464-1-2011-T2.30.2-writing, -T2.30.4-CAD, -2.1.5-UGR-note, -T2.2-shielding | sourced via SLL Code 2012 (EN 12464-1:2011 text) |
| LA5 modelling | EN12464-1-2011-2.1.6.3-modelling, -2.1.6.2-cylindrical | sourced via SLL |
| LA7 flicker | IEEE1789-2015-low-risk-0.08f, -min-freq-100, -unknown-freq-10, -1250Hz, -0.0333f-special, SVM-0.4-regulatory; IEEE1789-2015-low-freq-0.025f, IEC-TR-61547-1-PstLM-1 | std; the last two unverified |
| LA13 emergency | EN1838-escape-1lx-centreline, -duration-1h, -uniformity-40, -response-5s-60s, EN1838-vendor-escape-1lx-1m-band, -vendor-duration, SLL-12.2.10-escape-centreline, MH7-11-27-escape-lighting | EN 1838 std; SLL, MH sourced (principle) |
| LA14 daylight | IES-LM83-12-sDA-55-75, -ASE-10, -ASE-def, -ASE-250h; IES-HB10-14.47-sDA, -sDA-def, -sunlight-1000 | LM-83 std (slide deck); IES Handbook sourced |
| I10 bath planning | NKBA-DC-1.5-clear-floor-space, -1.5-no-door, NKBA-BG4-clear-space-30in, -BG20-toilet-centreline-18in, -BG21-toilet-front-21in, -BG5-lav-centreline-20in, -BG9-shower-36in, -BG3-ceiling-80in | sourced (US) |
| I14 tall storage anchored | US-16CFR1261.2-ASTM-F2057-23, US-STURDY-tests-60lb, EN14749-2005-6.2.1-stability-applicability, ASTM-F2057-anchoring | std; anchoring rule unverified |

Not attempted (outside the revised list): LA6 R9/SDCM, LA10, LA11, LA15, EA3-EA5, EA9-EA14, DGP/EN 17037, I11 dining clearances, I14 bunk guard and bed-base gap, all EG* and DS* rows.

## Discrepancies and cautions found

- **D1 alarm grade (EA15, LS6).** a-plus-lighting-electrical.md cites "BS 5839-6 grade D LD2". ADB vol. 1 para 1.1 reads "minimum Grade D2 Category LD3". It adds (paras 1.5-1.7) that a large dwellinghouse (more than one storey with a storey over 200 m2) takes Grade A LD3 (two storeys) or Grade A LD2 (three or more storeys, basement excluded). A villa with a storey over 200 m2 is probably in that class: check the plan areas. Grade D1/LD2 or better is a design choice above the ADB minimum, not the minimum.
- **D2 sunken-garden guard (LS3).** ADK 3.1a requires guarding at a "light well, basement or similar sunken area" but Diagram 3.1 gives 1100 mm only for external balconies and roof edges, and 900 mm for stairs, landings, ramps and internal floor edges. 1100 mm at a sunken-garden edge is our policy, not an ADK value.
- **D3 stair width (LS1).** ADK sets no minimum stair width for a dwelling except 900 mm in the exceptional entrance-storey case (para 1.16); the 1100 mm in LS1 comes from ER Art. 100 (English text), not ADK.
- **D4 socket RCD threshold (EA8).** IEC 60364-4-41:2005 411.3.3 says socket-outlets up to 20 A (Note 2: Spain and Ireland 32 A). Amendment 1 (2017) raises it to 32 A and adds 411.3.4: a 30 mA RCD on a.c. final circuits supplying luminaires in single-household premises. EA8's "sockets <= 32 A, luminaires" matches AMD1:2017, not the base edition. Which edition Egypt's code adopts was not checked (scope dropped).
- **D5 sDA (LA14).** The IES Handbook 10th ed. (held, p. 14.47) says sDA300 "> 50%" is nominally acceptable and satisfaction grows above 75%. A 2017 summary of LM-83-12 says "exceed 55%" nominally acceptable and "75%" preferred, and ASE below 10% "for less discomfort" (a guideline, with 20% flagged as needing shading). LM-83-12 itself was not read; both values are recorded, LA14 uses the LM-83 numbers, and the Handbook's direct-sun measure carries no 250 h or 10% limit.
- **D6 shower zones (EA2).** IEC 60364-7-701 ed. 3.0 (2019) gives showers no zone 2 and a zone 1 of 120 cm radius from the fixed outlet; zone 2 (60 cm beyond zone 1) exists only for bath tubs. A zone test written from older editions or UK drawings will give different shapes. Figures 2-10 of the standard were not seen, only the clauses.
- **D7 flicker (LA7).** The IEEE 1789 shortcut read (committee chair's deck) applies at >= 100 Hz; LA7 says >= 90 Hz, which the deck does not support. The 0.025 x f low-frequency rule and Pst LM <= 1 are unverified. SVM <= 0.4 is described only as a value regulatory groups use for sensitive populations; the regulation is not named in the source.
- **D8 EN 1838 (LA13).** Two vendor notes agree on 1 lx on the centre line and 1 h, but word the width differently (Glamox: route up to 2 m wide, central band at least half the width at >= 50 % of the value; the other: 1 lx along a 1 m path within a 2 m route). Treat 1 lx / 1 h as std. Metric Handbook Table XIX lists escape lighting for common routes of flats, not inside a single-family house, so LA13 is advisory for the villa.
- **D9 EN 12464-1 edition.** The UGR 19 / U0 0.60 / modelling 0.30-0.60 values are the 2011 edition as reproduced by SLL 2012. EN 12464-1:2021 was not read.
- **D10 voltage drop (EA6).** 3 % lighting / 5 % other (public LV supply) and 6 % / 8 % (private supply) are IEC 60364-5-52 Table G.52.1, informative, from a secondary; the VDE preview confirms Annex G exists but omits its text. No 4 % figure was found.
- **D11 NKBA is US practice.** The 30 x 48 in clear floor space and the code minima are 2015 IRC / IPC values, with figure 1.5.d-e of the Design Concepts summary being drawings (text of the clear-space rule was read, the figures were not interpreted).
- **D12 ADB edition.** The ADB PDF is the 2019 edition collated with the 2025, 2026 (in force 2026-09-30) and 2029 amendments. Their summaries mention only sprinklers in care homes, blocks of flats, evacuation lifts and fire-resistance classes, so none of the carded paragraphs should change.

## Regenerating

`cd knowledge/sources/_build && python build_uk_adk_adm.py && python build_uk_adb.py && python build_std.py`. The web files (ADB PDF, IEC previews, decks) are read from
`C:\Users\mmbka\r_dl` (not in the repo); URLs are on each card. A card whose source text changes will fail to rebuild rather than keep an unchecked quote.
