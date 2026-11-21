"""Writes docs/lanes/R-sources.md from knowledge/sources/*.json. Every card id in the table is checked against the JSON;
the status column is computed from the cards, so the document cannot drift from the files. Run after the builders."""
import collections
import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
cards = {}
for f in sorted(glob.glob(str(ROOT / "knowledge" / "sources" / "*.json"))):
    for c in json.loads(Path(f).read_text(encoding="utf-8")):
        cards[c["id"]] = c

K = "UK-ADK-2013-"
M = "UK-ADM1-2015-"
B = "UK-ADB1-2019-"
E41 = "IEC60364-4-41-2005-"
A41 = "IEC60364-4-41-AMD1-2017-"
Z = "IEC60364-7-701-2019-"
ROWS = [
    ("LS1 stair geometry", [K + x for x in ("1.3-T1.1-private-stair", "1.3-T1.1-note1-pitch", "1.3-2R+G", "1.5-uniform-steps", "1.11-headroom", "1.16-entrance-storey-width", "1.17-36-risers", "1.20-landings", "1.34-handrail")], "UK ADK; ADK sets no dwelling stair width except para 1.16"),
    ("LS2 open risers / gaps", [K + "1.9-open-risers", K + "3.3-sphere-climb", K + "1.8-soffit"], ""),
    ("LS3 guards", [K + x for x in ("D3.1-guard-900", "D3.1-guard-1100", "3.1-guard-siting", "K2-performance-600", "3.3-sphere-climb")], "see D2"),
    ("LS6 smoke detection / EA15", [B + x for x in ("1.1-alarm-grade", "1.2-1.4-alarm-power", "1.5-large-definition", "1.6-large-two-storeys", "1.7-large-three-storeys")] + ["BS5839-6-grade-D1", "BS5839-6-grade-D2", "BS5839-6-LD1", "BS5839-6-LD2", "BS5839-6-LD3", "BS5839-6-no-alarm-in-baths"], "ADB read in full text; BS 5839-6 via manufacturer summary; see D1"),
    ("LS7 / escape (UK analogue of fire separation)", [B + x for x in ("2.1-habitable-rooms-ground", "2.5-protected-stairway", "2.10-escape-window", "2.10-escape-window-area", "2.10-escape-window-1100", "2.16-basement")], "the Egyptian separation rule itself is not carded"),
    ("AC1 accessibility", [M + x for x in ("M4(1)-performance", "1.6-approach-900", "1.7-ramp", "1.14-entrance", "1.15-corridor", "1.17-WC", "2.27-WC-M4(2)")], "UK M4(1)/M4(2), not the Egyptian code"),
    ("EA1 device heights", [M + "1.18-controls"], "heights only; socket counts per room not carded"),
    ("EA2 bathroom zones", [Z + x for x in ("701.30.102-zone0", "701.30.103-zone1", "701.30.104-zone2", "701.30.104-no-zone2-shower", "701.415.1.101-RCD", "701.512.2.4.101.3-zone1-sockets", "701.512.2.4.101.4-zone2-equipment")], "ed. 3.0; see D6"),
    ("EA6 voltage drop", ["IEC60364-5-52-G52.1-A", "IEC60364-5-52-G52.1-B", "IEC60364-5-52-annexG-exists"], "see D10"),
    ("EA7 fault protection", [E41 + x for x in ("411.3.2.2-scope", "T41.1", "411.3.2.3-5s", "411.4.4-Zs", "411.5.3-RA")] + [A41 + "411.3.2.2-scope", A41 + "T41.1"], "2005 edition and AMD1:2017; see D4"),
    ("EA8 RCD", [A41 + "411.3.3-32A", A41 + "411.3.4-luminaires", E41 + "411.3.3-20A", Z + "701.415.1.101-RCD"], "IEC 60364-7-714 (outdoor) was not searched; see D4"),
    ("LA3 uniformity, LA4 UGR", ["EN12464-1-2011-T2.30.2-writing", "EN12464-1-2011-T2.30.4-CAD", "EN12464-1-2011-2.1.5-UGR-note", "EN12464-1-2011-T2.2-shielding", "EN12464-1-2011-basis"], "EN 12464-1:2011 text as printed in SLL 2012; see D9"),
    ("LA5 modelling", ["EN12464-1-2011-2.1.6.3-modelling", "EN12464-1-2011-2.1.6.2-cylindrical", "EN12464-1-2011-2.1.6.2-cylindrical-150"], ""),
    ("LA7 flicker", ["IEEE1789-2015-low-risk-0.08f", "IEEE1789-2015-min-freq-100", "IEEE1789-2015-unknown-freq-10", "IEEE1789-2015-1250Hz", "IEEE1789-2015-0.0333f-special", "SVM-0.4-regulatory", "IEEE1789-2015-low-freq-0.025f", "IEC-TR-61547-1-PstLM-1"], "see D7"),
    ("LA13 emergency / night safety", ["EN1838-escape-1lx-centreline", "EN1838-escape-duration-1h", "EN1838-escape-uniformity-40", "EN1838-escape-response-5s-60s", "EN1838-vendor-escape-1lx-1m-band", "EN1838-vendor-duration", "SLL-12.2.10-escape-centreline", "MH7-11-27-escape-lighting"], "see D8"),
    ("LA14 daylight", ["IES-LM83-12-sDA-55-75", "IES-LM83-12-ASE-10", "IES-LM83-12-ASE-def", "IES-LM83-12-ASE-250h", "IES-HB10-14.47-sDA", "IES-HB10-14.47-sDA-def", "IES-HB10-14.47-sunlight-1000"], "LM-83 via a 2017 slide deck; see D5"),
    ("I10 bath planning", ["NKBA-DC-1.5-clear-floor-space", "NKBA-DC-1.5-no-door", "NKBA-DC-1.5e-turning-circle-label", "NKBA-BG4-clear-space-30in", "NKBA-BG20-toilet-centreline-18in", "NKBA-BG20-toilet-centreline-code-15in", "NKBA-BG21-toilet-front-21in", "NKBA-BG21-compartment-recommended", "NKBA-BG21-compartment-code", "NKBA-BG5-lav-centreline-20in", "NKBA-BG9-shower-36in", "NKBA-BG9-shower-code-30in", "NKBA-BG3-ceiling-80in"], "US practice; see D11"),
    ("I14 tall storage anchored", ["US-16CFR1261.2-ASTM-F2057-23", "US-F2057-23-three-stability-tests", "US-F2057-23-9.2.2-pull", "US-F2057-23-9.2.3-carpet", "EN14749-2005-6.2.1-stability-applicability", "ASTM-F2057-anchoring"], "the anchoring rule is unverified; see D13"),
]

missing = [i for _, ids, _ in ROWS for i in ids if i not in cards]
assert not missing, missing
used = {i for _, ids, _ in ROWS for i in ids}
unlisted = sorted(set(cards) - used)
assert not unlisted, unlisted

tot = collections.Counter(c["status"] for c in cards.values())
table = ["| Criterion | Cards (full ids) | Status of those cards | Note |", "|---|---|---|---|"]
for name, ids, note in ROWS:
    st = collections.Counter(cards[i]["status"] for i in ids)
    stx = ", ".join(f"{n} {k}" for k, n in sorted(st.items()))
    table.append(f"| {name} | " + "; ".join(f"`{i}`" for i in ids) + f" | {stx} | {note} |")

doc = f"""# Lane R: source cards (2026-11-20)

{len(cards)} cards in `knowledge/sources/*.json` (one file per document; each file is a JSON list of `SourceCard` records): **{tot['sourced']} sourced, {tot['std']} std, {tot['unverified']} unverified**.
They are written by `knowledge/sources/_build/*.py` (`cardlib.py` refuses a card whose quote is not found in exactly one page of the named source, and lists any number in a card's `value` that is not in its quote, id, locator, document or edition string); this table is written by `make_doc.py`, which fails if a card id is missing or unlisted.
`.gitignore` line 46 ignores `sources/`, so the files were added with `git add -f`; the lead should add `!knowledge/sources/` to `.gitignore`.
The web sources (ADB vol. 1 PDF, IEC preview files, decks, vendor notes) were downloaded to `C:\\Users\\mmbka\\r_dl`, outside the repo; each card carries its URL. ADB vol. 1 is not in the held index.

**Status meaning** (A-PLUS.md section 2: sourced = page read; STD = standard known but its page not carded; UNVERIFIED = cannot gate).
`sourced`: the primary text was read: a held book page, or a public preview file that contains the clause (the IEC iTeh previews contain the clauses carded).
`std`: the standard itself is paywalled and not read; the quote is from a named secondary that cites it (manufacturer note, committee-chair deck, CPSC preamble, conference slide). These inform but must not gate.
`unverified`: nothing readable found; the card has an empty quote and says what was tried.
**Quotes** are the source span: whitespace collapsed, line-end hyphenation joined and ligature code points expanded (fi, fl); nothing else changed. Matching ignores dash and curly-quote differences, so a stored quote can differ from a typed one only in those characters.

## Scope change and the Egyptian material

The client dropped Egyptian law/code sourcing mid-run, so **no Egyptian card was written**. Read before the stop (uncarded, so unverified for gating):
- The Andersen English text (unofficial) of ER Art. 93-112, in full. Its Art. 106, 108 and 108 bis name the *Egyptian Code for Design Principles and Execution Requirements for the Protection of Structures from Fire Hazards*, the *Egyptian Code for Safety Requirements for Multi-Purpose Structures* (parking) and the *Egyptian Code for the Design of External Spaces and Buildings for Use by Persons with Disabilities*. Code numbers and editions were not looked up, the Egyptian electrical-installations code was not searched for, and IEC 60364-7-714 was not searched for.
- Gazette issue 82 bis (a), 8 April 2009 (Arabic scan, manshurat.org file), pp. 79-81 only, by eye: Art. 96 (8% / 10%, 0.5 m2 / 0.25 m2), Art. 97 (80/70/100/280 cm), the window-sill 0.9 m and door-to-stair 1 m clauses, Art. 98 table rows, Art. 99, and Art. 100 agree with the English figures **except Art. 100**: the Gazette table gives step length 110 cm if the units per floor do not exceed four and 130 cm if they exceed four, with no main/secondary-stair split; the English text says 130 cm for the main staircase and 110 cm for the secondary staircase above four units. The 2009 Gazette has no Art. 98 bis (the English text, which is an amended version, has one: a smaller courtyard table for plots with a ground-floor footprint up to 100 m2 and height up to 19 m). Art. 93, 94, 103, 106, 110-112 were not compared with the Arabic. Amendments after 2009 were not checked.
- a-plus-architecture.md rows that cite ER Art. 93-112 therefore stay at their existing status; nothing here upgrades them.

## Criterion to card

{chr(10).join(table)}

Not attempted (outside the revised list): LA6 R9/SDCM, LA10, LA11, LA15, EA3-EA5, EA9-EA14, DGP/EN 17037, I11 dining clearances, I14 bunk guard and bed-base gap, all EG* and DS* rows.

## Discrepancies and cautions

- **D1 alarm grade (EA15, LS6).** a-plus-lighting-electrical.md cites "BS 5839-6 grade D LD2". ADB vol. 1 para 1.1 reads "minimum Grade D2 Category LD3". Paras 1.5-1.7 add that a large dwellinghouse (more than one storey, at least one storey over 200 m2) takes Grade A LD3 (two storeys) or Grade A LD2 (three or more storeys, basements excluded). If any villa storey is over 200 m2 the Grade A rule applies: check the plan areas. Grade D1/LD2 or better is a design choice above the ADB minimum.
- **D2 sunken-garden guard (LS3).** ADK 3.1a requires guarding at a "light well, basement or similar sunken area" but Diagram 3.1 gives 1100 mm only for external balconies and roof edges and 900 mm for stairs, landings, ramps and internal floor edges. 1100 mm at a sunken-garden edge is our policy, not an ADK value.
- **D3 stair width (LS1).** ADK sets no minimum stair width for a dwelling except 900 mm in the exceptional entrance-storey case (para 1.16). The 1100 mm in LS1 comes from ER Art. 100 (110 cm for up to four units per floor in both the English and Arabic texts read), not from ADK.
- **D4 RCD and disconnection (EA7, EA8).** IEC 60364-4-41:2005 411.3.3 covers socket-outlets up to 20 A (its Note 2: Spain and Ireland use 32 A). Amendment 1 (2017) raises it to 32 A, adds outdoor mobile equipment up to 32 A, and adds 411.3.4: a 30 mA RCD on a.c. final circuits supplying luminaires in single-household premises. EA8 matches AMD1:2017, not the base edition. AMD1 also replaces 411.3.2.2 and Table 41.1: the scope becomes final circuits up to 63 A with socket-outlets and up to 32 A with only fixed equipment (the 2005 text said up to 32 A), and the d.c. TN time for 120-230 V falls from 5 s to 1 s. The a.c. times in the 120-230 V and 230-400 V columns are unchanged (TN 0.4 s / 0.2 s, TT 0.2 s / 0.07 s). Which Uo column applies to a 230/400 V supply (line-to-earth 230 V, so the 120-230 V column) is our reading, not a quoted sentence. Which edition Egypt's code adopts was not checked.
- **D5 sDA (LA14).** The IES Handbook 10th ed. (held, p. 14.47) says sDA300 "> 50%" is nominally acceptable and satisfaction grows above 75%. A 2017 summary of LM-83-12 says "exceed 55%" nominally acceptable and 75% preferred, and ASE below 10% "for less discomfort" (a guideline). LM-83-12 itself was not read; both are recorded and LA14 should keep the 55/75/10 numbers as std. The Handbook's direct-sun measure has no 250 h or 10% limit.
- **D6 shower zones (EA2).** IEC 60364-7-701 ed. 3.0 (2019) gives showers no zone 2 and a zone 1 within 120 cm of the fixed outlet (circumscribing surface, limited by fixed partitions); zone 2 (60 cm beyond zone 1) exists only for bath tubs. Figures 2-10 were not seen, only the clauses. Other editions were not read, so a zone test written from older drawings must be compared with this text.
- **D7 flicker (LA7).** The IEEE 1789 multiplication shortcut read (committee chair's deck) is for products flickering at 100 Hz or more; LA7 says 90 Hz, which this deck does not support. The 0.025 x f low-frequency rule and Pst LM <= 1 are unverified. SVM <= 0.4 is described only as a value regulatory groups use for sensitive populations; the regulation is not named.
- **D8 EN 1838 (LA13).** Two vendor notes agree on 1 lx on the centre line and a one-hour minimum, but word the width differently (Glamox: routes up to 2 m wide with a central band of at least half the width; the other: one metre of path width within a 2 m route). Metric Handbook Table XIX concerns common escape routes of flats, not the inside of a single-family house, so LA13 is advisory for the villa. EN 1838 itself was not read.
- **D9 EN 12464-1 edition.** The UGR 19 / U0 0.60 / modelling 0.30-0.60 values are the 2011 edition as printed in SLL 2012. EN 12464-1:2021 was not read.
- **D10 voltage drop (EA6).** 3% lighting / 5% other use (public LV supply) and 6% / 8% (private supply) are IEC 60364-5-52 Table G.52.1 (informative annex), read from a secondary; the VDE preview shows that clause 525 refers to Annex G but omits its text. No 4% figure was found.
- **D11 NKBA is US practice.** The 30 x 48 in clear floor space and the code minima are 2015 IRC/IPC values; the guideline pages' printed labels are unreliable in the index, so those cards cite guideline number and pdf index. Figure 1.5.d-e of the Design Concepts summary (page image read) shows overlapping clear floor spaces and a 60-67 in turning circle; the turning-circle label is carded by eye, not machine-checked.
- **D12 ADB edition.** The ADB PDF is the 2019 edition collated with the 2025, 2026 (in force 2026-09-30) and 2029 amendments. The amendment summaries cover Regulation 38 and fire safety information, reaction-to-fire classes, sprinklers in care homes, blocks of flats, evacuation lifts and fire-resistance classes. The carded paragraphs were not compared against the 2019 base text.
- **D13 tip-over.** ASTM F2057-23 itself and EN 14749:2016+A1:2022 were not read. What is carded: the US mandatory adoption of F2057-23, CPSC's description of its three stability tests (loaded drawers open; 10 lb horizontal pull; 60 lb on an open drawer with a 0.43 in carpet block), and the applicability test of EN 14749:2005 clause 6.2.1 from a preview (height above 600 mm and centre-of-gravity height in m times mass in kg above 6). These test products; the rule that tall storage in a villa be wall-anchored is unverified.

## Regenerating

`cd knowledge/sources/_build && python build_uk_adk_adm.py && python build_uk_adb.py && python build_std.py && python make_doc.py` (needs `PYTHONIOENCODING=utf-8`). A card whose source text changed fails to rebuild rather than keeping an unchecked quote.
"""
out = ROOT / "docs" / "lanes" / "R-sources.md"
out.write_text(doc, encoding="utf-8")
print(out, len(cards), dict(tot))
