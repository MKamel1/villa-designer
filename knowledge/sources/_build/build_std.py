"""Lane R: cards for the 'STD' thresholds of the lighting/electrical doc, NKBA and tip-over.

Source files are local copies of public downloads (kept in DL, outside the repo); every quote is checked
against the extracted text before a card is written. Status meaning:
  sourced    - the primary text (held book, or a public preview that contains the clause) was read
  std        - the standard itself was not read; the quote is from a named secondary that cites it
  unverified - nothing readable found; the card records what was tried
"""
import sys
from cardlib import held_quote, pdf_quote, text_quote, write
from archpipe.contracts import SourceCard

DL = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\mmbka\r_dl\std"
SC = SourceCard


from ovr import OVR  # noqa: E402

FAILS = []


def _o(cid, quote, value, loc):
    o = OVR.get(cid, {})
    return o.get("quote", quote), o.get("value", value), o.get("loc", loc)


def held(book, doc, ed, url, rows, status="sourced"):
    out = []
    for cid, loc, quote, value, *lab in rows:
        quote, value, loc = _o(cid, quote, value, loc)
        try:
            label, pdf, q = held_quote(book, quote, lab[0] if lab else None)
        except ValueError as e:
            FAILS.append((cid, str(e)[:230])); continue
        where = f"pdf index {pdf}; printed page label unreliable in this book" if book == "nkba-guidelines" else f"printed p. {label} (pdf index {pdf})"
        out.append(SC(cid, doc, ed, f"{loc}; {where}", q, value, status, url))
    return out


def pdfs(fname, doc, ed, url, rows, status):
    out = []
    for cid, loc, quote, value, *hint in rows:
        quote, value, loc = _o(cid, quote, value, loc)
        try:
            label, pdf, q = pdf_quote(f"{DL}\\{fname}", quote, hint[0] if hint else None)
        except ValueError as e:
            FAILS.append((cid, str(e)[:230])); continue
        out.append(SC(cid, doc, ed, f"{loc}; printed p. {label} (pdf page {pdf} of the preview file)", q, value, status, url))
    return out


def html(fname, doc, ed, url, rows, status):
    out = []
    for cid, loc, quote, value in rows:
        quote, value, loc = _o(cid, quote, value, loc)
        try:
            q = text_quote(f"{DL}\\{fname}.txt", quote)
        except ValueError as e:
            FAILS.append((cid, str(e)[:230])); continue
        out.append(SC(cid, doc, ed, loc, q, value, status, url))
    return out


def unverified(cid, doc, ed, loc, value, tried):
    return SC(cid, doc, ed, loc, "", value, "unverified", f"not read; tried: {tried}")


# ------------------------------------------------------------------ SLL Code for Lighting 2012 (EN 12464-1:2011 values)
SLL = "sll-code"
SLL_DOC = "SLL Code for Lighting (chapter 2 reproduces BS EN 12464-1:2011 indoor workplace requirements)"
SLL_ED = "2012 (held: knowledge/library.json sll-code); EN 12464-1:2011 text, superseded by EN 12464-1:2021, not read"
SLL_URL = "held: sll-code/SLL - Code for Lighting (2012).pdf"
sll = held(SLL, SLL_DOC, SLL_ED, SLL_URL, [
    ("EN12464-1-2011-basis", "section 2 intro",
     "This chapter of the Code is based on BS EN 12464-1: 2011: Light and lighting - Lighting of work places - Part 1: Indoor work places",
     "SLL chapter 2 tables are the EN 12464-1:2011 requirements"),
    ("EN12464-1-2011-T2.30.2-writing", "Table 2.30 row 2.30.2 'Writing, typing, reading, data processing'",
     "2.30.2 Writing, typing, reading, data processing 500 19 0.60 80",
     "writing/reading task: Em 500 lx, UGRL 19, Uo 0.60, Ra 80"),
    ("EN12464-1-2011-T2.30.4-CAD", "Table 2.30 row 2.30.4",
     "2.30.4 CAD work stations 500 19 0.60 80", "CAD workstation: 500 lx, UGRL 19, Uo 0.60"),
    ("EN12464-1-2011-2.1.6.3-modelling", "section 2.1.6.3 Note 2",
     "For uniform arrangement of luminaires or roof lights a value between 0.30 and 0.60 is an indicator of good modelling.",
     "cylindrical:horizontal illuminance 0.30-0.60 indicates good modelling (faces)"),
    ("EN12464-1-2011-2.1.6.2-cylindrical", "section 2.1.6.2",
     "The maintained mean cylindrical illuminance (average vertical plane illuminance) in the activity and interior areas shall be not less than 50 lx with Uo",
     "mean cylindrical illuminance >= 50 lx (>= 150 lx where visual communication matters: offices, meeting rooms), Uo >= 0.10, at 1.2 m seated / 1.6 m standing"),
    ("EN12464-1-2011-2.1.6.2-cylindrical-150", "section 2.1.6.2 Note",
     "should be not less than 150 lx with Uo ≥ 0.10.",
     "mean cylindrical illuminance not less than 150 lx with Uo >= 0.10 where good visual communication matters (offices, meeting and teaching areas)"),
    ("EN12464-1-2011-T2.2-shielding", "Table 2.2",
     "Minimum shielding angle a 20 to < 50 15° 50 to < 500 20° ≥500 30°",
     "minimum shielding angle 15 deg (20-<50 kcd/m2), 20 deg (50-<500), 30 deg (>=500)"),
    ("EN12464-1-2011-2.1.5-UGR-note", "section 2.1.5.2 Note 2",
     "If the maximum UGR value in the room is higher than the UGR limit given in section 2",
     "UGR limits are the section 2.2 table values (UGRL); CIE 117 tabular method is the calculation route"),
    ("SLL-12.2.10-escape-centreline", "section 12.2.10 (spacing tables, emergency lighting)",
     "ensure that the illuminance on the centre line of the escape route does not fall below the required illuminance and that the edges of the strip have at least half that illuminance.",
     "escape routes: centre-line illuminance >= required value and strip edges >= half of it (the numeric 1 lx is EN 1838, see EN1838 cards)"),
])

# ------------------------------------------------------------------ IES Handbook 10th ed. (held) - sDA / sunlight
IES = "ies-handbook"
ies = held(IES, "IES Lighting Handbook, 10th edition, section 14.16.1 (annual daylight metrics)",
           "10th ed., 2011 (held: knowledge/library.json ies-handbook); predates IES LM-83-12",
           "held: ies-handbook/IES - The Lighting Handbook (10th ed, 2011).pdf", [
    ("IES-HB10-14.47-sDA", "section 14.16.1.5",
     "Research has suggested that for a given room, occupants find the daylight levels nominally acceptable when sDA300 > 50%, and are progressively more satisfied as the area increases above 75% to an upper feasible limit of approximately 95%.",
     "sDA300 > 50% nominally acceptable; satisfaction rises above 75% (NOTE: LM-83-12 slides below say 55%, see R-sources discrepancy D5)"),
    ("IES-HB10-14.47-sDA-def", "section 14.16.1.5",
     "It is recommended that the percent time component be locked-in at 50% of the time.",
     "sDA: 300 lux for at least 50% of the analysis year"),
    ("IES-HB10-14.47-sunlight-1000", "section 14.16.1.8",
     "exceeds 1000 lux based on Perez sky distributions based on site weather data.",
     "direct-sunlight hours metric: direct sun alone > 1000 lux (the handbook gives no 250 h or 10 % limit)"),
])

# ------------------------------------------------------------------ IES LM-83-12 via a conference presentation
lm83 = pdfs("radlm83.pdf", "IES LM-83-12 Approved Method: sDA and ASE, as summarised in 'Challenges and opportunities of incorporating LM-83 into building simulations' (Mahic, Nezamdoost; 2017 International Radiance Workshop)",
            "LM-83-12 itself NOT read (paywalled); slide deck 2017",
            "https://www.radiance-online.org/community/workshops/2017-portland-or/presentations/08_AMAN_LM83SimulationChallenges.pdf", [
    ("IES-LM83-12-sDA-55-75", "slide 3 (secondary)",
     "Exceed 55% of the floor area for “nominally acceptable daylight” • Exceed 75% of the floor area for “preferred daylight”",
     "sDA300/50%: >=55% nominally acceptable, >=75% preferred (analysis hours 8am-6pm)"),
    ("IES-LM83-12-ASE-10", "slide 3 (secondary)",
     "Below 10% of the floor area for less discomfort",
     "ASE1000,250 < 10% of floor area; > 20% suggests automated blinds or extra fixed shading"),
    ("IES-LM83-12-ASE-def", "slide 3 (secondary)",
     "What % of the floor area exceeds 1000 lux",
     "ASE1000,250: share of floor area above 1000 lux of computational direct sun"),
    ("IES-LM83-12-ASE-250h", "slide 3 (secondary)",
     "for more than 250 annual analysis hours?",
     "ASE duration criterion: more than 250 annual analysis hours (8am-6pm)"),
], "std")

# ------------------------------------------------------------------ IEC 60364-4-41:2005 (+AMD1:2017) previews
IEC41 = "IEC 60364-4-41 Low-voltage electrical installations, Part 4-41: Protection against electric shock"
iec41 = pdfs("iec41_b.pdf", IEC41, "Edition 5.0, 2005-12 (the iTeh preview file contains clauses 411.3-411.5 in full)",
             "https://cdn.standards.iteh.ai/samples/10887/b410f7c10853465e9e7f293d9e18fd98/IEC-60364-4-41-2005.pdf", [
    ("IEC60364-4-41-2005-411.3.2.2-scope", "clause 411.3.2.2",
     "The maximum disconnection time stated in Table 41.1 shall be applied to final circuits not exceeding 32A.",
     "2005 text: Table 41.1 applies to final circuits <= 32 A (replaced by AMD1:2017, see the AMD1 card for 411.3.2.2)"),
    ("IEC60364-4-41-2005-T41.1", "Table 41.1 (printed p.10; columns 50-120 V a.c./d.c., 120-230 V a.c./d.c., 230-400 V, >400 V)",
     "TN 0,8 Note 1 0,4 5 0,2 0,4 0,1 0,1 TT 0,3 Note 1 0,2 0,4 0,07 0,2 0,04 0,1",
     "2005 Table 41.1, a.c.: 120 V < Uo <= 230 V: TN 0.4 s, TT 0.2 s; 230 V < Uo <= 400 V: TN 0.2 s, TT 0.07 s (the d.c. TN value 5 s became 1 s in AMD1:2017)"),
    ("IEC60364-4-41-2005-411.3.2.3-5s", "clause 411.3.2.3-4",
     "In TN systems, a disconnection time not exceeding 5 s is permitted for distribution circuits",
     "TN distribution circuits <= 5 s; TT distribution circuits <= 1 s"),
    ("IEC60364-4-41-2005-411.3.3-20A", "clause 411.3.3 (2005 base text; superseded by AMD1:2017 below)",
     "socket-outlets with a rated current not exceeding 20 A that are for use by ordinary persons and are intended for general use",
     "2005 base text: 30 mA RCD on general-use socket-outlets <= 20 A and outdoor mobile equipment <= 32 A (Note 2: Spain and Ireland use 32 A)"),
    ("IEC60364-4-41-2005-411.4.4-Zs", "clause 411.4.4",
     "Zs × Ia ≤ Uo", "TN: Zs x Ia <= Uo, with Ia the current giving disconnection within the Table 41.1 time"),
    ("IEC60364-4-41-2005-411.5.3-RA", "clause 411.5.3",
     "ii) RA x IΔn ≤ 50 V", "TT with RCD: RA x I_delta_n <= 50 V, plus the disconnection time of 411.3.2.2/411.3.2.4"),
], "sourced")
iec41 += pdfs("amd1.pdf", IEC41 + ", Amendment 1", "Amendment 1, 2017-03 (iTeh preview contains the replaced 411.3.3 and new 411.3.4)",
              "https://cdn.standards.iteh.ai/samples/22593/faab23b5c332418984d5b3c627cbd1b0/IEC-60364-4-41-2005-AMD1-2017.pdf", [
    ("IEC60364-4-41-AMD1-2017-411.3.2.2-scope", "clause 411.3.2.2 (replaced)",
     "The maximum disconnection times stated in Table 41.1 shall be applied to final circuits with a rated current not exceeding • 63 A with one or more socket-outlets, and • 32 A supplying only fixed connected current-using equipment.",
     "Table 41.1 applies to final circuits <= 63 A with socket-outlets and <= 32 A fixed equipment (the 2005 text said <= 32 A)"),
    ("IEC60364-4-41-AMD1-2017-T41.1", "Table 41.1 (replaced)",
     "TN 0,8 a 0,4 1 0,2 0,4 0,1 0,1 TT 0,3 a 0,2 0,4 0,07 0,2 0,04 0,1",
     "AMD1:2017 Table 41.1, a.c. 120 V < Uo <= 230 V: TN 0.4 s, TT 0.2 s (d.c. TN now 1 s); 230 V < Uo <= 400 V a.c.: TN 0.2 s, TT 0.07 s"),
    ("IEC60364-4-41-AMD1-2017-411.3.3-32A", "clause 411.3.3 (replaced)",
     "a.c. socket-outlets with a rated current not exceeding 32 A that are liable to be used by ordinary persons and are intended for general use",
     "30 mA RCD on general-use a.c. socket-outlets <= 32 A and outdoor mobile equipment <= 32 A (replaces the 20 A of the 2005 text)"),
    ("IEC60364-4-41-AMD1-2017-411.3.4-luminaires", "clause 411.3.4 (new)",
     "In premises designed to accommodate a single household, additional protection by a residual current protective device (RCD) with a rated residual operating current not exceeding 30 mA shall be provided for a.c. final circuits supplying luminaires.",
     "single-household premises: 30 mA RCD on a.c. final circuits supplying luminaires"),
], "sourced")

# ------------------------------------------------------------------ IEC 60364-7-701:2019
IEC701 = "IEC 60364-7-701 Low-voltage electrical installations, Part 7-701: Locations containing a bath or shower"
iec701 = pdfs("iec701.pdf", IEC701, "Edition 3.0, 2019-10 (iTeh preview contains the zone and equipment clauses; figures 2-10 not checked)",
              "https://cdn.standards.iteh.ai/samples/23637/b686a82d669541109302676be8ecd23b/IEC-60364-7-701-2019.pdf", [
    ("IEC60364-7-701-2019-701.30.102-zone0", "clause 701.30.102",
     "by a vertical circumscribing virtual surface at a distance of 120 cm from the centre of the fixed shower head(s)",
     "zone 0: inside a bath tub; for showers 0-10 cm above the floor within 120 cm of the fixed shower head/outlet"),
    ("IEC60364-7-701-2019-701.30.103-zone1", "clause 701.30.103",
     "a horizontal plane lying 225 cm above the floor level below the bath tub or a horizontal plane corresponding to the highest fixed shower head",
     "zone 1: bath tub footprint up to 225 cm (or the highest fixed shower head/outlet); showers: within 120 cm of the fixed head"),
    ("IEC60364-7-701-2019-701.30.104-zone2", "clause 701.30.104",
     "the parallel vertical virtual surface at a distance of 60 cm from the zone 1 border",
     "zone 2 (bath tub only): 60 cm beyond zone 1, up to 225 cm; for showers there is no zone 2"),
    ("IEC60364-7-701-2019-701.30.104-no-zone2-shower", "clause 701.30.104 b)",
     "for showers, there is no zone 2.", "ed.3.0 (2019): showers have no zone 2"),
    ("IEC60364-7-701-2019-701.415.1.101-RCD", "clause 701.415.1.101",
     "additional protection by the use of one or more RCDs having a rated residual operating current not exceeding 30 mA shall be provided for: – circuits serving the location containing a bath tub and/or a shower;",
     "30 mA RCD for circuits serving the bath/shower location and circuits passing through zones 1/2 (SELV/PELV and electrical separation excepted)"),
    ("IEC60364-7-701-2019-701.512.2.4.101.4-zone2-equipment", "clause 701.512.2.4.101.4",
     "socket-outlets, having a degree of protection of at least IPX4, of circuits protected by SELV or PELV with the source of supply installed outside zones 0 and 1;",
     "zone 2 sockets only SELV/PELV with the source outside zones 0-1, IPX4; shaver supply units per IEC 61558-2-5 allowed"),
    ("IEC60364-7-701-2019-701.512.2.4.101.3-zone1-sockets", "clause 701.512.2.4.101.3 b)",
     "socket-outlets of circuits protected by SELV or PELV with a rated voltage not exceeding 25 V AC or 60 V DC, with the source of supply installed outside zones 0 and 1;",
     "zone 1 sockets only SELV/PELV <= 25 V a.c./60 V d.c., source outside zones 0-1"),
], "sourced")

# ------------------------------------------------------------------ IEC 60364-5-52 (voltage drop)
vd = html("etb.html", "IEC 60364-5-52 Table G.52.1 (Annex G, informative) as reproduced by 'eToolboX' (secondary)",
          "IEC 60364-5-52:2009; Annex G text itself NOT read", "https://sites.google.com/view/etoolsbox/electrical/voltage-drop-iec", [
    ("IEC60364-5-52-G52.1-A", "Table G.52.1 type A (secondary)",
     "A – Low voltage installations supplied directly from a public low voltage distribution system: Lighting is 3% and other use is 5%.",
     "public LV supply: lighting 3 %, other uses 5 %"),
    ("IEC60364-5-52-G52.1-B", "Table G.52.1 type B (secondary)",
     "B – Low voltage installation supplied from private LV supply* : Lighting is 6% and other use is 8%.",
     "private LV supply: lighting 6 %, other 8 %; +0.005 %/m beyond 100 m, max +0.5 %"),
], "std")
vd += pdfs("vde552.pdf", "IEC 60364-5-52 Wiring systems (VDE-Verlag preview, contents and foreword)",
           "Edition 3.1, 2024-11 consolidated (2009+AMD1:2024); preview shows contents and foreword only",
           "https://www.vde-verlag.de/iec-normen/preview-pdf/info_iec60364-5-52{ed3.1}en.pdf", [
    ("IEC60364-5-52-annexG-exists", "contents and foreword",
     "Clause 525 introduces changes in the maximum value of voltage drop permitted between the origin of the consumer's installation and the equipment which should not be greater than that given in the relevant annex.",
     "Clause 525 sets the voltage-drop limit by reference to Annex G (informative); the numbers are in Annex G, which the preview omits", 7),
], "std")

# ------------------------------------------------------------------ IEEE 1789-2015 (via DOE/PNNL presentation by the committee chair)
f1789 = pdfs("doe1789.pdf", "IEEE 1789-2015 Recommended Practice for Modulating Current in High-Brightness LEDs, as summarised in 'Flicker: Understanding the New IEEE Recommended Practice' (N. Miller PNNL, B. Lehman, chair IEEE PAR1789; LightFair 2015, DOE SSL)",
             "IEEE 1789-2015 itself NOT read (paywalled); presentation May 2015",
             "https://www.energy.gov/sites/prod/files/2015/05/f22/miller+lehman_flicker_lightfair2015.pdf", [
    ("IEEE1789-2015-low-risk-0.08f", "slides 8 and 23 (secondary)",
     "Multiply the frequency by 0.08 and round up to the nearest whole number to get the max Allowable % Flicker",
     "low-risk: max %Flicker = 0.08 x frequency (Hz), rounded up; 120 Hz -> 10 %"),
    ("IEEE1789-2015-min-freq-100", "slide 23 (secondary)",
     "Test to determine the flicker frequency in Hz of the SSL product (it must be ≥100 Hz)",
     "the recommended-practice shortcut applies to products flickering at >= 100 Hz (the 90 Hz boundary in a-plus-lighting LA7 is not in this source)"),
    ("IEEE1789-2015-unknown-freq-10", "slide 23 (secondary)",
     "If frequency is difficult to determine, % Flicker shall not exceed 10%.", "unknown frequency: %Flicker <= 10 %"),
    ("IEEE1789-2015-1250Hz", "slide 23 (secondary)",
     "At 1250 Hz or higher, 100% flicker is allowed.", "f >= 1250 Hz: no flicker limit"),
    ("IEEE1789-2015-0.0333f-special", "slide 24 (secondary)",
     "% Flicker ≤ Flicker Freq x 0.0333 (special populations)", "special (sensitive) populations: %Flicker <= 0.0333 x f"),
], "std")
svm = pdfs("doetlm.pdf", "Temporal Light Modulation: A Phantom Array Visibility Measure (Tan, Miller, Royer, Irvin; PNNL, DOE 2024), remark on SVM",
           "2024 paper (secondary for SVM)", "https://www.energy.gov/sites/default/files/2024-05/ssl-tan-etal-2024-lrt_tlm.pdf", [
    ("SVM-0.4-regulatory", "discussion of PAVM limits (secondary)",
     "Just as regulatory groups are using lower values of SVM (0.4) to protect highly sensitive populations",
     "SVM <= 0.4 is used by regulatory groups to protect highly sensitive populations (the paper does not name the regulation)"),
], "std")
unv_flicker = [
    unverified("IEEE1789-2015-low-freq-0.025f", "IEEE 1789-2015 Recommended Practice for Modulating Current in High-Brightness LEDs", "2015", "recommendations below 90-100 Hz", "%Flicker coefficient 0.025 x f for f < 90 Hz and the 90 Hz boundary",
               "WebSearch (DOE LightFair deck covers only 0.08f / 0.0333f at >=100 Hz); IEEE standards page is paywalled; no readable copy found"),
    unverified("IEC-TR-61547-1-PstLM-1", "IEC TR 61547-1 / IEC 61000-4-15 (Pst LM)", "not identified", "Pst LM <= 1 limit used in LA7", "Pst LM <= 1.0",
               "WebSearch for IEC TR 61547-1 and a PstLM limit: no readable text; DOE TLM paper only names PstLM as a measure for < 80 Hz"),
]

# ------------------------------------------------------------------ EN 1838 (via two manufacturer technical notes; they agree on the numbers)
en1838 = html("glamox.html", "EN 1838 Lighting applications - Emergency lighting, as stated in Glamox 'Escape routes - rules and luminaires' (secondary)",
              "EN 1838 itself NOT read (paywalled)",
              "https://glamox.com/en/pbs/application-guide/emergency-lighting/rules-and-regulations/escape-routes--rules-and-luminaires", [
    ("EN1838-escape-1lx-centreline", "Glamox application guide, escape routes (secondary)",
     "in width, the horizontal illuminances on the floor along the centre line of an escape route must not fall below 1 lx.",
     "escape route (width <= 2 m): >= 1 lx on the floor along the centre line"),
    ("EN1838-escape-duration-1h", "Glamox application guide (secondary)",
     "The required minimum emergency escape lighting duration allowed for escape purposes is 1 hour.",
     "minimum duration 1 h"),
    ("EN1838-escape-uniformity-40", "Glamox application guide (secondary)",
     "The minimum to maximum diversity ratio must not be less than 1:40 along the centre line of the escape route.",
     "max:min along the centre line <= 40:1"),
    ("EN1838-escape-response-5s-60s", "Glamox application guide (secondary)",
     "The emergency escape route lighting must reach 50% of the required illuminance within 5 seconds and 100% of the required illuminance within 60 seconds.",
     "50 % within 5 s, 100 % within 60 s"),
], "std")
en1838 += pdfs("en1838.pdf", "EN 1838 Emergency Lighting, Technical Information (LED solutions vendor note, 01-2020) (secondary)",
               "EN 1838 itself NOT read; vendor note dated 01-2020",
               "https://a.storyblok.com/f/158120/x/16e33dc9a6/en-1838-emergency-lighting-en.pdf", [
    ("EN1838-vendor-escape-1lx-1m-band", "section 2.4 (secondary; differs in wording from Glamox)",
     "an illuminance level of at least 1 lux along the center line for a path width of one metre must be guaranteed.",
     "1 lx along the centre line for a 1 m path width within a 2 m route: Glamox says the central band is half the route width at >= 50 % of the value; the two wordings are not identical"),
    ("EN1838-vendor-duration", "section 2.4 (secondary)",
     "The rated service time is at least one hour.", "rated service time >= 1 h"),
], "std")
mh = held("metric-handbook", "Metric Handbook: Planning and Design Data (Buxton)", "7th ed., 2022 (held)",
          "held: metric-handbook/Buxton - Metric Handbook Planning and Design Data (7th ed, 2022).pdf", [
    ("MH7-11-27-escape-lighting", "section on emergency lighting, Table XIX follows",
     "Emergency (escape) lighting should be provided in those areas necessary for escape purposes in case the artificial lighting fails.",
     "principle only; Table XIX (BS 5266-1) lists common escape routes of flats, not the inside of a single-family house: advisory for a villa"),
])

# ------------------------------------------------------------------ BS 5839-6 (via Aico summary of the 2019+A1:2020 edition)
bs = html("aico.html", "BS 5839-6 Fire detection and alarm systems for fire safety in buildings, Part 6 (domestic premises), as summarised by Aico (manufacturer) (secondary)",
          "BS 5839-6:2019+A1:2020 itself NOT read (paywalled); Aico web page read 2026-11-20",
          "https://www.aico.co.uk/technical-support/standards-regulations/fire-british-standard-bs-5839-62019/", [
    ("BS5839-6-grade-D1", "Aico summary, alarm grades (secondary)",
     "Grade D1 A system of one or more mains powered detectors, each with a tamper-proof standby supply consisting of a battery or batteries. Grade D2",
     "Grade D1: mains-powered detectors with tamper-proof standby battery"),
    ("BS5839-6-grade-D2", "Aico summary (secondary)",
     "Grade D2 A system of one or more mains powered detectors, each with an integral standby supply consisting of a user-replaceable battery or batteries. Grade F1",
     "Grade D2: mains-powered with user-replaceable standby battery"),
    ("BS5839-6-LD1", "Aico summary, categories (secondary)",
     "LD1 High Protection All areas where a fire could start", "LD1: all areas where a fire could start (hall, landings, living room, kitchen, bedrooms, cupboards)"),
    ("BS5839-6-LD2", "Aico summary (secondary)",
     "LD2 - Medium Protection Escape routes and high risk areas", "LD2: escape routes plus high-risk areas (kitchen, living room)"),
    ("BS5839-6-LD3", "Aico summary (secondary)",
     "LD3 - Minimum Protection Escape routes", "LD3: escape routes only (hall, landings)"),
    ("BS5839-6-no-alarm-in-baths", "Aico summary (secondary)",
     "Across all Categories, alarms should not be installed within toilets, bathrooms or shower rooms.",
     "no smoke alarms in toilets, bathrooms, shower rooms"),
], "std")

# ------------------------------------------------------------------ NKBA
nk1 = held("nkba-dc-summary-4ed", "NKBA Design Concepts summary (Universal design)", "4th ed., (c) 2022 NKBA (held)",
           "held: nkba-dc-summary-4ed", [
    ("NKBA-DC-1.5-clear-floor-space", "section 1.5 Clear Floor Space at Activity Centers (figures 1.5.d-e: bath)",
     "A minimum clear floor space of 30″ (760 mm) to 32″ (815 mm) by 48″ (1 220 mm) to 52″ (1 320 mm) should be provided at all activity centers.",
     "clear floor space 760-815 mm x 1220-1320 mm at every activity centre, centre-lined on the fixture, overlap allowed, not obstructed by door swing"),
    ("NKBA-DC-1.5-no-door", "section 1.5",
     "The clear floor space should not be obstructed by door swings, cabinetry, casework, fixtures or equipment.",
     "clear floor space not obstructed by door swings or fixtures"),
])
nk1.append(SC("NKBA-DC-1.5e-turning-circle-label", "NKBA Design Concepts summary (Universal design)", "4th ed., (c) 2022 NKBA (held)",
              "figure 1.5.e (drawing label read by eye from the page image, nkba-dc-summary-4ed pdf index 15; no text layer, so not machine-checked); printed p. 16",
              '60" - 67" (1 525 mm - 1 700 mm) TURNING CIRCLE',
              "bath turning circle 60-67 in (1525-1700 mm) drawn overlapping the clear floor spaces; figure 1.5.d is labelled 'clear floor space with no door swing interference'",
              "sourced", "held: nkba-dc-summary-4ed"))
nk2 = held("nkba-guidelines", "NKBA Kitchen & Bath Planning Guidelines with Access Standards (bathroom guidelines; IRC 2015 / IPC code references)",
           "2nd ed., 2016 NKBA/Wiley (held); pdf labels unreliable, cite by guideline number",
           "held: nkba-guidelines", [
    ("NKBA-BG4-clear-space-30in", "Bathroom Planning Guideline 4 Clear Space",
     "Plan a clear floor space of at least 30″ (762 mm) from the front edge of all fixtures (e.g., lavatory, toilet, bidet, tub, and shower) to any opposite bath fixture, wall, or obstacle.",
     "762 mm clear in front of every fixture"),
    ("NKBA-BG20-toilet-centreline-18in", "Bathroom Planning Guideline 20 Toilet/Bidet Placement",
     "The distance from the centerline of toilet and/or bidet to any bath fixture, wall, or other obstacle should be at least 18″ (457 mm).",
     "toilet centreline >= 457 mm from any fixture/wall (recommended); code minimum 15 in = 381 mm"),
    ("NKBA-BG21-toilet-front-21in", "Bathroom Planning Guideline 21 Toilet Compartment (code requirement)",
     "There shall be at least a 21″ (533 mm) clearance In front of the toilet to any wall, fixture, or door.",
     "code minimum 533 mm in front of the toilet; separate compartment code minimum 762 x 1524 mm, recommended 914 x 1676 mm"),
    ("NKBA-BG5-lav-centreline-20in", "Bathroom Planning Guideline 5 Single-Lavatory Placement",
     "The distance from the centerline of the lavatory to the sidewall/tall obstacle should be at least 20″ (508 mm).",
     "lavatory centreline >= 508 mm from side wall"),
    ("NKBA-BG9-shower-36in", "Bathroom Planning Guideline 9 Shower Size",
     "The interior shower size is at least 36″ × 36″ (914 mm × 914 mm).", "interior shower >= 914 x 914 mm recommended (code minimum 30 x 30 in)"),
])
nk2 += held("nkba-guidelines", "NKBA Kitchen & Bath Planning Guidelines with Access Standards (bathroom guidelines)", "2nd ed., 2016 (held)",
            "held: nkba-guidelines", [
    ("NKBA-BG3-ceiling-80in", "Bathroom Planning Guideline 3 Ceiling Height (IRC R305.1)",
     "The minimum ceiling height in a bathroom should not be less than 80″ (2032 mm)", "bathroom ceiling >= 2032 mm (US code)"),
    ("NKBA-BG20-toilet-centreline-code-15in", "Bathroom Planning Guideline 20 Toilet/Bidet Placement (code requirement)",
     "A minimum distance of 15″ (381 mm) is required from the centerline of toilet and/or bidet to any bath fixture, wall, or other obstacle.",
     "code minimum: toilet or bidet centreline 15 in (381 mm) from any fixture, wall or obstacle"),
    ("NKBA-BG21-compartment-recommended", "Bathroom Planning Guideline 21 Toilet Compartment",
     "The size for a separate toilet compartment should be at least 36″ × 66″ (914 mm × 1676 mm)",
     "separate toilet compartment recommended at least 36 x 66 in (914 x 1676 mm)"),
    ("NKBA-BG21-compartment-code", "Bathroom Planning Guideline 21 Toilet Compartment (code requirement)",
     "The minimum size for a separate toilet compartment is 30″ × 60″ (762 mm × 1524 mm).",
     "code minimum separate toilet compartment 30 x 60 in (762 x 1524 mm)"),
    ("NKBA-BG9-shower-code-30in", "Bathroom Planning Guideline 3 Ceiling Height (IRC R305.1, shower head area)",
     "A shower, or tub equipped with a shower head, shall have a minimum floor-to-ceiling height of 80″ (2032 mm) above a minimum area 30″ × 30″ (762 mm × 762 mm) at the shower head.",
     "shower head: 80 in (2032 mm) floor-to-ceiling over a 30 x 30 in (762 x 762 mm) area"),
])

# ------------------------------------------------------------------ furniture tip-over
tip = html("fr1261.html", "16 CFR Part 1261 Safety Standard for Clothing Storage Units (88 FR 28403, 2023-05-04), adopting ASTM F2057-23",
           "Direct final rule published 2023-05-04; ASTM F2057-23 itself NOT read (paywalled)",
           "https://www.govinfo.gov/content/pkg/FR-2023-05-04/html/2023-08997.htm", [
    ("US-16CFR1261.2-ASTM-F2057-23", "section 1261.2",
     "Each clothing storage unit that is subject to ASTM F2057-23, Standard Safety Specification for Clothing Storage Units, approved on February 1, 2023, shall comply with ASTM F2057-23.",
     "US mandatory: clothing storage units comply with ASTM F2057-23 (units manufactured after 2023-09-01)"),
    ("US-F2057-23-three-stability-tests", "preamble, CPSC staff description of ASTM F2057-23 (secondary)",
     "ASTM F2057-23 has a set of three stability tests to simulate the capability of a child weighing up to 60 pounds interacting with a CSU.",
     "F2057-23 has three stability tests simulating a child up to 60 lb (loaded drawers open; horizontal pull; carpet reaction)"),
    ("US-F2057-23-9.2.2-pull", "preamble, CPSC staff description of section 9.2.2 (secondary)",
     "applies a 10-pound horizontal force over a period of at least 5 seconds",
     "9.2.2 horizontal dynamic force: 10 lb for at least 5 s, held 10 s, hand-hold height at most 56 in"),
    ("US-F2057-23-9.2.3-carpet", "preamble, CPSC staff description of section 9.2.3 (secondary)",
     "uses 60 pounds of weight placed on the edge of an open drawer or pull-out shelf, while the CSU is tilted forward using a 0.43 inch test block",
     "9.2.3: 60 lb on the edge of an open drawer or shelf, unit tilted forward on a 0.43 in block (carpet simulation)"),
], "std")
tip += pdfs("en14749.pdf", "EN 14749:2005 Domestic and kitchen storage units and worktops - Safety requirements and test methods (iTeh/SIST preview)",
            "EN 14749:2005 (current EN 14749:2016+A1:2022 NOT read); preview contains up to clause 6.2.3",
            "https://cdn.standards.iteh.ai/samples/23024/67f85dc0faf64d24b4493bf9160c07b1/SIST-EN-14749-2006.pdf", [
    ("EN14749-2005-6.2.1-stability-applicability", "clause 6.2.1",
     "The requirements and test methods for the stability (6.6) apply only to storage units, where the height to the top of the unit exceeds 600 mm, and when the multiplication of the height of the centre of gravity in m (6.2.2) and the total mass in kg (6.2.3) exceeds the value 6.",
     "stability clause 6.6 applies to units > 600 mm high with (centre-of-gravity height in m x total mass in kg) > 6; the 6.6 tilt/load values are NOT in the preview"),
], "std")
tip.append(unverified("ASTM-F2057-anchoring", "ASTM F2057-23 / EN 14749:2016+A1:2022", "2023 / 2022", "requirement that tall storage be wall-anchored",
                      "tip restraint hardware and the anchoring rule itself (I14 'tall storage is anchored')",
                      "WebSearch + govinfo FR rule (cites the standard, does not reproduce it); CPSC pages 403; ASTM and BSI texts paywalled; EN 14749 preview ends before clause 6.6"))

# ------------------------------------------------------------------ write
FILES = {
    "sll-code-2012-en12464-1.json": sll,
    "ies-handbook-10th-daylight.json": ies,
    "ies-lm83-12-secondary.json": lm83,
    "iec-60364-4-41.json": iec41,
    "iec-60364-7-701-2019.json": iec701,
    "iec-60364-5-52-voltage-drop.json": vd,
    "ieee-1789-2015-flicker.json": f1789 + svm + unv_flicker,
    "en-1838-escape-lighting.json": en1838 + mh,
    "bs-5839-6-domestic-detection.json": bs,
    "nkba-bath-clear-floor.json": nk1 + nk2,
    "furniture-tip-over.json": tip,
}
if __name__ == "__main__":
    if FAILS:
        for f in FAILS:
            print("FAIL", f)
        sys.exit(1)
    n = 0
    for fn, cards in FILES.items():
        write(fn, cards)
        n += len(cards)
        print(fn, len(cards))
    print("total", n)
