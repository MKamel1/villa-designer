"""Build knowledge/electrical/cards.json and tables.json from the source snapshots.

Run:  python knowledge/electrical/build_data.py

Big numeric tables (IEC 60364-5-52 B.52.4, simplified C.52.1, Fig G30 voltage drop) are parsed
from the committed snapshot text so no cell is typed by hand. Small tables are typed here and
verified cell-by-cell against the snapshots by tests/electrical/test_cards.py.
Cards whose status is "std"/"sourced" carry a verbatim quote that must occur in the snapshot.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SNAP = HERE / "source_snapshots"
WB = "https://web.archive.org/web/2023id_/https://www.electrical-installation.org/enwiki/"
TLC = "https://www.tlc-direct.co.uk/"


def _rows(name: str, start: str, stop: str | None = None) -> list[list[str]]:
    txt = (SNAP / name).read_text(encoding="utf-8").replace(chr(160), " ")
    i = txt.index(start)
    seg = txt[i:]
    if stop:
        seg = seg[: seg.index(stop)] if stop in seg else seg
    out = []
    for ln in seg.splitlines():
        if ln.startswith("ROW: "):
            out.append([c.strip() for c in ln[5:].split("|")])
    return out


def _num(x: str):
    x = x.strip()
    return None if x in ("", "-") else float(x)


def parse_g20() -> dict:
    rows = _rows("eig_general_method_cable_sizing.txt", "Fig. G20", "Note: In columns")
    cols = ["A1", "A2", "B1", "B2", "C", "D1", "D2"]
    out = {"Cu": {}, "Al": {}}
    mat = None
    for r in rows:
        if r[0] == "Copper":
            mat = "Cu"
        elif r[0] == "Aluminium":
            mat = "Al"
        elif mat and re.fullmatch(r"\d+(\.\d+)?", r[0]) and len(r) == 8:
            out[mat][r[0]] = dict(zip(cols, (_num(c) for c in r[1:])))
    return out


def parse_g21() -> dict:
    rows = _rows("eig_simplified_cable_sizing.txt", "Fig. G21", "Correction factors are given")
    out = {"Cu": {}, "Al": {}}
    mat = None
    for r in rows:
        if r[0] == "Copper":
            mat = "Cu"
        elif r[0] == "Aluminium":
            mat = "Al"
        elif mat and re.fullmatch(r"\d+(\.\d+)?", r[0]) and len(r) == 13:
            out[mat][r[0]] = [_num(c) for c in r[1:]]  # value columns 1..12 (source numbering 2..13)
    return out


def parse_g30() -> dict:
    rows = _rows("eig_voltage_drop_steady.txt", "Fig. G30", "Examples")
    names = ["sp_motor_08", "sp_motor_start_035", "sp_light_1", "tp_motor_08", "tp_motor_start_035", "tp_light_1"]
    out = {}
    for r in rows:
        if re.fullmatch(r"\d+(\.\d+)?", r[0]) and len(r) >= 7:
            out[r[0]] = dict(zip(names, (_num(c) for c in r[1:7])))
    return out


def card(id, document, edition, locator, quote, value, status, url):
    return dict(id=id, document=document, edition=edition, locator=locator, quote=quote,
                value=value, status=status, url_or_path=url)


EIG = "Schneider Electric, Electrical Installation Guide (electrical-installation.org wiki, Wayback 2023 snapshot)"
EIGED = "2016/2018 wiki edition"
WHIT = "J. Whitfield, The Electrician's Guide, 5th ed. (EPA Press), as hosted by TLC Electrical Supplies"
WHED = "5th ed.; tables from BS 7671:1992 (16th edition), superseded; reference only"
SEL = "SELECT (Scotland), Electrical Installations in Locations Containing a Bath or Shower, pocket guide TS 19-001 (summarises BS 7671:2018+A2:2022 s.701)"


def sp(name):  # snapshot path
    return f"knowledge/electrical/source_snapshots/{name}"


def cards() -> list[dict]:
    C = []
    # ---- ampacity and correction factors (IEC 60364-5-52, second-hand via Schneider) ----
    C.append(card("EL-IEC-B524", EIG + " reproducing IEC 60364-5-52 Table B.52.4", EIGED,
        "Fig. G20 (page General_method_for_cable_sizing)",
        "Fig. G20 – Current-carrying capacities in amperes for different methods of installation, PVC insulation, three loaded conductors, copper or aluminium, conductor temperature: 70 °C, ambient temperature: 30 °C in air, 20 °C in ground (table B.52.4 of IEC 60364-5-52)",
        "e.g. 1.5 mm2 Cu: A1 13.5, A2 13, B1 15.5, B2 15, C 17.5, D1 18, D2 19 A; 95 mm2 Cu: C 223 A",
        "std", sp("eig_general_method_cable_sizing.txt") + " ; " + WB + "General_method_for_cable_sizing"))
    C.append(card("EL-IEC-C521", EIG + " reproducing IEC 60364-5-52 simplified table", EIGED,
        "Fig. G21 (page Recommended_simplified_approach_for_cable_sizing)",
        "Fig. G21 – Current-carrying capacity in amperes (table C.52.1 of IEC 60364-5-52)",
        "Simplified ampacity table, 12 value columns. Only the column mapped to F/3 PVC is used (value column 7 as numbered here from 1; it also reproduces the source's worked-example sizes). A1/A2 header cells are inconsistent as scraped and are NOT used.",
        "std", sp("eig_simplified_cable_sizing.txt") + " ; " + WB + "Recommended_simplified_approach_for_cable_sizing"))
    C.append(card("EL-IEC-B5214-CA", EIG + " reproducing IEC 60364-5-52 Table B.52.14", EIGED,
        "Fig. G12",
        "Fig. G12 – Correction factors for ambient air temperatures other than 30 °C to be applied to the current-carrying capacities for cables in the air (from table B.52.14 of IEC 60364-5-52)",
        "PVC: 40 C 0.87, 45 C 0.79, 50 C 0.71, 55 C 0.61; XLPE/EPR: 45 C 0.87, 50 C 0.82",
        "std", sp("eig_general_method_cable_sizing.txt") + " ; " + WB + "General_method_for_cable_sizing"))
    C.append(card("EL-IEC-B5217-CG", EIG + " reproducing IEC 60364-5-52 Table B.52.17", EIGED,
        "Fig. G16",
        "Fig. G16 – Reduction factors for groups of more than one circuit or of more than one multi-core cable (table B.52.17 of IEC 60364-5-52)",
        "Bunched in air, on a surface, embedded or enclosed: 1 circuit 1.00, 2 0.80, 3 0.70, 4 0.65, 5 0.60, 6 0.57, 8 0.52, 9 0.50, 12 0.45, 16 0.41, 20 0.38",
        "std", sp("eig_general_method_cable_sizing.txt") + " ; " + WB + "General_method_for_cable_sizing"))
    C.append(card("EL-IEC-G521-VDLIM", EIG + " reproducing IEC 60364-5-52 Table G.52.1", EIGED,
        "Fig. G25 (page Maximum_voltage_drop)",
        "Fig. G25: Maximum voltage-drop between the service-connection point and the point of utilization (IEC60364-5-52 table G.52.1)",
        "LV service connection from a public LV network: lighting 3 %, other uses 5 %",
        "std", sp("eig_max_voltage_drop.txt") + " ; " + WB + "Maximum_voltage_drop"))
    C.append(card("EL-EIG-G30-VD", EIG, EIGED, "Fig. G30 (page Calculation_of_voltage_drop_in_steady_load_conditions)",
        "Fig. G30 – Phase-to-phase voltage drop ΔU for a circuit, in volts per ampere per km",
        "Copper 2.5 mm2 single-phase lighting 19 V/A/km; 70 mm2 balanced 3-phase lighting 0.59; 95 mm2 3-phase motor 0.43",
        "std", sp("eig_voltage_drop_steady.txt") + " ; " + WB + "Calculation_of_voltage_drop_in_steady_load_conditions"))
    C.append(card("EL-EIG-G29-RX", EIG, EIGED, "Fig. G29 formulas and notes (same page as G30)",
        "In the absence of any other information, take X as being equal to 0.08 Ω/km.",
        "R(copper) = 23.7 ohm.mm2/km / S; X = 0.08 ohm/km; LED lighting cos phi > 0.9",
        "std", sp("eig_voltage_drop_steady.txt") + " ; " + WB + "Calculation_of_voltage_drop_in_steady_load_conditions"))
    C.append(card("EL-WHIT-T47", WHIT, WHED, "Tables 4.6 and 4.7 (page Book/4.3.9)",
        "Table 4.7 - Current ratings and volt drops for sheathed multi-core p.v.c.-insulated cables",
        "6 mm2 twin in thermal insulation 32 A, 7.3 mV/A/m; 10 mm2 43 A; 4 mm2 11 mV/A/m",
        "std", sp("whitfield_Book_4_3_9_htm.txt") + " ; " + TLC + "Book/4.3.9.htm"))
    C.append(card("EL-WHIT-T43-CA", WHIT, WHED, "Table 4.3 (page Book/4.3.4)",
        "Correction factors to current rating for ambient temperature",
        "70 C PVC: 40 C 0.87, 45 C 0.79, 50 C 0.71, 55 C 0.61",
        "std", sp("whitfield_Book_4_3_4_htm.txt") + " ; " + TLC + "Book/4.3.4.htm"))
    C.append(card("EL-WHIT-T44-CG", WHIT, WHED, "Table 4.4 (page Book/4.3.5)",
        "Table 4.4 - Correction factors for groups of cables",
        "2 circuits 0.80, 3 0.70, 4 0.65, 5 0.60, 6 0.57, 7 0.54, 8 0.52, 9 0.50 (enclosed or clipped, touching)",
        "std", sp("whitfield_Book_4_3_5_htm.txt") + " ; " + TLC + "Book/4.3.5.htm"))
    C.append(card("EL-WHIT-T45-CI", WHIT, WHED, "Table 4.5 (page Book/4.3.6)",
        "Derating factors (CI) for cables up to 10mm² in cross-sectional",
        "50 mm in insulation 0.89, 100 mm 0.81, 200 mm 0.68, 400 mm 0.55, 500 mm or more 0.50",
        "std", sp("whitfield_Book_4_3_6_htm.txt") + " ; " + TLC + "Book/4.3.6.htm"))
    C.append(card("EL-WHIT-T62-DIV", WHIT + " (table originally BS 7671:1992 / IEE On-Site Guide diversity table)", WHED,
        "Table 6.2 (page Book/6.2.3)",
        "10 A + 30% balance + 5 A for socket",
        "Households: lighting 66 % total; heating and power 100 % to 10 A + 50 % balance; cookers 10 A + 30 % balance + 5 A for socket; instantaneous water heaters 100%X+100%Y+25%Z; thermostatic water heaters 100 %; standard circuits and sockets 100%X + 40%(Y+Z)",
        "std", sp("whitfield_Book_6_2_3_htm.txt") + " ; " + TLC + "Book/6.2.3.htm"))
    C.append(card("EL-EIG-A14-DIV", EIG, EIGED, "Fig. A14 (page Estimation_of_actual_maximum_kVA_demand)",
        "Fig. A14 – Diversity factor according to circuit function (see UTE C 15-105 table AC)",
        "Lighting 1; heating and air conditioning 1; socket-outlets 0.1 to 0.2",
        "std", sp("eig_diversity.txt") + " ; " + WB + "Estimation_of_actual_maximum_kVA_demand"))
    C.append(card("EL-EIG-A11-DIV", EIG, EIGED, "Fig. A11",
        "Fig. A11 – Example of diversity factors for an apartment block as defined in French standard NFC14-100, and applicable for apartments without electrical heating",
        "25 to 29 consumers: ks 0.46",
        "std", sp("eig_diversity.txt") + " ; " + WB + "Estimation_of_actual_maximum_kVA_demand"))
    # ---- protection ----
    C.append(card("EL-IEC-4-41-TT-F13", EIG + " reproducing IEC 60364-4-41", EIGED, "Fig. F13 (page TT_system_-_Practical_aspects)",
        "Fig. F13 – Maximum disconnecting times in TT system for final circuits not exceeding 63 A with one or more socket-outlets, and 32 A supplying only fixed connected current-using equipment",
        "120 V < Uo <= 230 V: 0.2 s (TT final circuits); other circuits 1 s",
        "std", sp("eig_tt_practical.txt") + " ; " + sp("eig_fig_F13_F19_raw.txt") + " ; " + WB + "TT_system_-_Practical_aspects"))
    C.append(card("EL-IEC-4-41-TN-F19", EIG + " reproducing IEC 60364-4-41", EIGED, "Fig. F19 (page Automatic_disconnection_for_TN_systems)",
        "the maximum disconnection time given in Fig. F19 is 0.4 s",
        "120 V < Uo <= 230 V: 0.4 s (TN final circuits); other circuits 5 s",
        "std", sp("eig_tn_disconnection.txt") + " ; " + sp("eig_fig_F13_F19_raw.txt") + " ; " + WB + "Automatic_disconnection_for_TN_systems"))
    C.append(card("EL-IEC-RCD-TIMES-F14", EIG, EIGED, "Fig. F14",
        "Fig. F14 – Maximum operating time of RCDs (in seconds)",
        "Domestic instantaneous RCD: 1xIdn 0.3 s, 2x 0.15 s, 5x 0.04 s",
        "std", sp("eig_tt_practical.txt") + " ; " + WB + "TT_system_-_Practical_aspects"))
    C.append(card("EL-IEC-TT-RA", EIG + " reproducing IEC 60364-4-41", EIGED, "TT system - Principle; Fig. F12",
        "Protection by automatic disconnection of the supply used in TT system is by RCD of sensitivity:",
        "Idn <= 50 / RA (50 V limit); 30 mA RCD permits RA up to 1666 ohm",
        "std", sp("eig_tt_principle.txt") + " ; " + WB + "TT_system_-_Principle"))
    C.append(card("EL-EIG-H28-CURVES", EIG + " reproducing IEC 60898", EIGED, "Fig. H28",
        "Fig. H28 – Tripping-current ranges of overload and short-circuit protective devices for LV circuit breakers",
        "Domestic IEC 60898: type B 3 In <= Im <= 5 In; type C 5 In <= Im <= 10 In; type D 10 In <= Im <= 20 In",
        "std", sp("eig_cb_characteristics.txt") + " ; " + WB + "Fundamental_characteristics_of_a_circuit-breaker"))
    C.append(card("EL-EIG-Q7-RCD", EIG + " reproducing IEC 60364 requirements", EIGED, "Residential electrical installation - Protection of people, Fig. Q7",
        "mandatory protection by 30 mA high sensitivity RCDs of socket outlet circuits, and circuits feeding bathroom.",
        "30 mA RCD mandatory on socket-outlet circuits and bathroom circuits (all earthing systems)",
        "std", sp("eig_residential_protection.txt") + " ; " + WB + "Residential_electrical_installation_-_Protection_of_people"))
    # ---- bathroom zones ----
    C.append(card("EL-701-ZONE0", SEL, "BS 7671:2018+A2:2022 s.701 (identical zones to IEC 60364-7-701)", "page 1",
        "Zone 0 is limited to the interior of the bath tub or shower basin.",
        "Zone 0: inside bath/shower basin; showers without a basin: height 0.10 m, same extent as zone 1",
        "std", sp("select_bs7671_701_pocket_guide.txt")))
    C.append(card("EL-701-ZONE1", SEL, "BS 7671:2018+A2:2022 s.701", "page 1",
        "Zone 1 is the area above the bath tub or shower basin to a height of 2.25 m from the floor or the highest fixed shower head, whichever is higher.",
        "Zone 1: above basin/bath to 2.25 m; showers without a basin: 1.20 m horizontally from the fixed outlet",
        "std", sp("select_bs7671_701_pocket_guide.txt")))
    C.append(card("EL-701-ZONE2", SEL, "BS 7671:2018+A2:2022 s.701", "page 4",
        "Zone 2 is the area external to zone 1 for a distance of 0.6 m horizontally and a height of 2.25 m from the floor",
        "Zone 2: 0.6 m beyond zone 1, 2.25 m high; no zone 2 for showers without a basin",
        "std", sp("select_bs7671_701_pocket_guide.txt")))
    C.append(card("EL-701-SOCKETS", SEL, "BS 7671:2018+A2:2022 s.701 (UK national distance)", "page 4",
        "Socket-outlets (other than those of SELV circuits noted above) are prohibited within a distance of 2.5 m horizontally from the boundary of zone 1.",
        "No socket-outlets in zones 0-2 except SELV; UK national rule: none within 2.5 m of zone 1 (reported as warn, not an IEC gate)",
        "std", sp("select_bs7671_701_pocket_guide.txt")))
    C.append(card("EL-701-RCD", SEL, "BS 7671:2018+A2:2022 s.701", "page 4",
        "Additional protection by use of one or more 30 mA RCDs must be provided for all low voltage circuits:",
        "30 mA RCD on all circuits serving the bath/shower location",
        "std", sp("select_bs7671_701_pocket_guide.txt")))
    # ---- worked examples (expected values) ----
    C.append(card("EL-EX-WHIT-6.1", WHIT, WHED, "Example 6.1 (page Book/6.2.3)",
        "Total single phase current",
        "Shop loads, 415 V 3-phase: total single-phase current demand 486.2 A; three-phase line current 162 A",
        "sourced", sp("whitfield_Book_6_2_3_htm.txt") + " ; " + TLC + "Book/6.2.3.htm"))
    C.append(card("EL-EX-WHIT-6.2", WHIT, WHED, "Example 6.2 (page Book/6.5.2)",
        "A 30 A protective device is likely to be chosen.",
        "Cooker 14 kW at 240 V with socket: demand 29.5 A",
        "sourced", sp("whitfield_Book_6_5_2_htm.txt") + " ; " + TLC + "Book/6.5.2.htm"))
    C.append(card("EL-EX-WHIT-4.1", WHIT, WHED, "Example 4.1 (page Book/4.3.9)",
        "is not quite large enough",
        "3 kW immersion heater 240 V, 15 A MCB, 50 C roof space, 8 bunched circuits through 50 mm insulation: 6 mm2 (32 A) too small, 10 mm2 (43 A); two bunches of four: 6 mm2",
        "sourced", sp("whitfield_Book_4_3_9_htm.txt") + " ; " + TLC + "Book/4.3.9.htm"))
    C.append(card("EL-EX-WHIT-4.5", WHIT, WHED, "Example 4.5 (page Book/4.3.11)",
        "Maximum permissible volt drop is 4% of 240 V",
        "Example 4.1 cable: 7.3 mV/A/m x 12.5 A x 14 m = 1.28 V; maximum length 105 m",
        "sourced", sp("whitfield_Book_4_3_11_htm.txt") + " ; " + TLC + "Book/4.3.11.htm"))
    C.append(card("EL-EX-EIG-A12", EIG, EIGED, "Example under Fig. A11/A12",
        "The apparent-power supply required for the building is: 150 x 0.46 = 69 kVA",
        "25 consumers x 6 kVA: 150 kVA x 0.46 = 69 kVA; rising main current 100 A at 400 V",
        "sourced", sp("eig_diversity.txt") + " ; " + WB + "Estimation_of_actual_maximum_kVA_demand"))
    C.append(card("EL-EX-EIG-WEX", EIG, EIGED, "Worked example of cable calculation (Figs G69-G72)",
        "The total voltage drop at the end of cable C7 is then: 0.73 %.",
        "Method F, 3 PVC copper, 400 V: C1 2x240 mm2 (909 A), C3 2x120 mm2 (526 A), C7 1x95 mm2 (238 A); voltage drop 0.12 / 0.47 / 0.13 %, total 0.73 %; Ecodial run gives same sizes",
        "sourced", sp("eig_worked_example_cable.txt") + " ; " + WB + "Worked_example_of_cable_calculation"))
    C.append(card("EL-EX-EIG-G32", EIG, EIGED, "Example 2 (Fig. G32)",
        "7.6 + 2.54 = 10.1 V",
        "70 mm2 3-ph feeder 50 m 150 A + 2.5 mm2 lighting circuit 20 m 20 A: 10.1 V = 4.4 % of 230 V",
        "sourced", sp("eig_voltage_drop_steady.txt") + " ; " + WB + "Calculation_of_voltage_drop_in_steady_load_conditions"))
    # ---- policy (ours, not sourced) ----
    pol = "ours; not from a standard"
    C.append(card("EL-POL-CIRCUITS", pol, "L7 v0", "EA3", "", "Lighting circuits <= 10 A design current, each control zone wholly on one circuit; socket radials 16 A (20 A kitchen); one dedicated circuit per AC, cooker, water heater, washer, pump", "policy", ""))
    C.append(card("EL-POL-PLACEMENT", pol, "L7 v0", "EA1", "", "Per room-type device minima (bedside sockets, TV cluster, worktop spacing 1.2 m, switch on latch side at 1.1-1.2 m, data/AC points); not yet recall-tested against an engineer's marked rooms", "policy", ""))
    C.append(card("EL-POL-PHASEBAL", pol, "L7 v0", "EA11", "", "Phase loads within 10 % of the mean", "policy", ""))
    C.append(card("EL-POL-SPARE", pol, "L7 v0", "EA12", "", ">= 20 % spare ways on every board", "policy", ""))
    C.append(card("EL-POL-RCD", pol, "L7 v0", "EA8", "", "Type A 30 mA RCBO on every final circuit; Type S 300 mA at the origin of a TT installation", "policy", ""))
    C.append(card("EL-POL-BREAKERS", pol, "L7 v0", "sizing", "", "Breaker ladder 6,10,16,20,25,32,40,50,63,80,100,125 A; curve B lighting/sockets, C motors and AC", "policy", ""))
    C.append(card("EL-POL-SIZES", pol, "L7 v0", "sizing", "", "Minimum csa 1.5 mm2 lighting, 2.5 mm2 sockets/dedicated; PF 0.9 LED lighting (see G29 cos phi > 0.9)", "policy", ""))
    # ---- unverified: needed, not obtained ----
    unv = "not obtained"
    C.append(card("EL-UNV-B522", "IEC 60364-5-52 Tables B.52.2, B.52.3, B.52.5", "-", "-", "", "Two-loaded-conductor PVC and all XLPE/EPR ampacity tables were not found as clean text. Engine uses B.52.4 (3 loaded, conservative for 2 loaded) and Whitfield Table 4.7 (2-core, BS 7671:1992) for single-phase finals.", "unverified", ""))
    C.append(card("EL-UNV-OSGA", "IET On-Site Guide Appendix A (max demand) worked example", "-", "-", "", "The IET OSG Appendix A table and worked example were not found; Whitfield Table 6.2 (the same household percentages, 16th ed. reprint) is used and reported as the reference.", "unverified", ""))
    C.append(card("EL-UNV-ROOF-EG", "Roof ambient 45-50 C and TT earthing at the site", "-", "-", "", "Site facts supplied by the client brief; earth-electrode resistance RA must be measured/confirmed with the utility.", "unverified", ""))
    return C


def tables() -> dict:
    T = {}
    T["ampacity_iec_b524_pvc_3loaded"] = {"card": "EL-IEC-B524", "unit": "A", "ref_ambient_c": 30, "conductor_c": 70,
                                         "methods": ["A1", "A2", "B1", "B2", "C", "D1", "D2"], "rows": parse_g20()}
    g21 = parse_g21()
    T["ampacity_iec_c521_simplified_cu_F_3pvc"] = {
        "card": "EL-IEC-C521", "unit": "A", "note": "value column 7 (1-based) mapped to F/3 PVC by the source header; A1/A2 not used",
        "column": 7, "rows": {k: v[6] for k, v in g21["Cu"].items()}}
    T["ampacity_iec_c521_simplified_cu_columns"] = {"card": "EL-IEC-C521", "unit": "A", "rows": g21["Cu"],
        "column_labels_by_header": {"B2:3PVC": 3, "B1:3PVC": 4, "C:3PVC": 5, "E:3PVC": 6, "F:3PVC": 7},
        "note": "labels as in the source header row; columns shared by several labels are merged values; use only for reproduction of the source worked example"}
    T["voltage_drop_g30_v_per_a_km_cu"] = {"card": "EL-EIG-G30-VD", "unit": "V/A/km", "rows": parse_g30()}
    # Whitfield Tables 4.6 / 4.7 (BS 7671:1992 4D1A/4D2A as reproduced); cols as in the source
    cols = ["in_insulation_2", "in_insulation_34", "conduit_wall_2", "conduit_wall_34", "clipped_2", "clipped_34", "vd_2_mv_a_m", "vd_34_mv_a_m"]
    t46 = {"1.0": [11.0, 10.5, 13.5, 12.0, 15.5, 14.0, 44.0, 38.0], "1.5": [14.5, 13.5, 17.5, 15.5, 20.0, 18.0, 29.0, 25.0],
           "2.5": [19.5, 18.0, 24.0, 21.0, 27.0, 25.0, 18.0, 15.0], "4.0": [26.0, 24.0, 32.0, 28.0, 37.0, 33.0, 11.0, 9.5],
           "6.0": [34.0, 31.0, 41.0, 36.0, 47.0, 43.0, 7.3, 6.4], "10.0": [46.0, 42.0, 57.0, 50.0, 65.0, 59.0, 4.4, 3.8],
           "16.0": [61.0, 56.0, 76.0, 68.0, 87.0, 79.0, 2.8, 2.4]}
    t47 = {"1.0": [11.0, 10.0, 13.0, 11.5, 15.0, 13.5, 44.0, 38.0], "1.5": [14.0, 13.0, 16.5, 15.0, 19.5, 17.5, 29.0, 25.0],
           "2.5": [18.5, 17.5, 23.0, 20.0, 27.0, 24.0, 18.0, 15.0], "4.0": [25.0, 23.0, 30.0, 27.0, 36.0, 32.0, 11.0, 9.5],
           "6.0": [32.0, 29.0, 38.0, 34.0, 46.0, 41.0, 7.3, 6.4], "10.0": [43.0, 39.0, 52.0, 46.0, 63.0, 57.0, 4.4, 3.8],
           "16.0": [57.0, 52.0, 69.0, 62.0, 85.0, 76.0, 2.8, 2.4]}
    T["bs7671_1992_whitfield_t46_single_core_pvc"] = {"card": "EL-WHIT-T47", "columns": cols,
        "note": "source prints 2.5 mm2 2-cable vd as '18..0' (typo); 18.0 used, agrees with Table 4.7", "rows": t46}
    T["bs7671_1992_whitfield_t47_multicore_pvc"] = {"card": "EL-WHIT-T47", "columns": cols, "rows": t47}
    T["ca_air_iec_b5214"] = {"card": "EL-IEC-B5214-CA", "unit": "factor", "rows": {
        "10": [1.22, 1.15], "15": [1.17, 1.12], "20": [1.12, 1.08], "25": [1.06, 1.04], "30": [1.0, 1.0], "35": [0.94, 0.96],
        "40": [0.87, 0.91], "45": [0.79, 0.87], "50": [0.71, 0.82], "55": [0.61, 0.76], "60": [0.50, 0.71]},
        "columns": ["PVC", "XLPE_EPR"]}
    T["cg_iec_b5217_bunched"] = {"card": "EL-IEC-B5217-CG", "rows": {
        "1": 1.00, "2": 0.80, "3": 0.70, "4": 0.65, "5": 0.60, "6": 0.57, "7": 0.54, "8": 0.52, "9": 0.50, "12": 0.45, "16": 0.41, "20": 0.38}}
    T["ci_whitfield_t45"] = {"card": "EL-WHIT-T45-CI", "rows": {"50": 0.89, "100": 0.81, "200": 0.68, "400": 0.55, "500": 0.50},
                              "note": "mm in insulation; 500 or more: 0.5; cables up to 10 mm2"}
    tot = lambda p: {"kind": "total_pct", "p": p}
    rk = lambda *w: {"kind": "ranked", "w": list(w)}
    T["diversity_whitfield_t62"] = {"card": "EL-WHIT-T62-DIV", "note": "ranked: weights for largest X, second Y, remainder Z; total_pct: share of summed current; ac/ev from EIG Fig A14 (ks 1)", "premises": {
        "household": {"lighting": tot(0.66), "heating_power": {"kind": "first_plus", "first": 10, "rest": 0.5},
                      "cooker": {"kind": "cooker", "first": 10, "rest": 0.3, "socket_a": 5}, "inst_wh": rk(1, 1, 0.25), "thermo_wh": tot(1.0),
                      "standard": rk(1, 0.4, 0.4), "sockets": rk(1, 0.4, 0.4), "ac": tot(1.0), "ev": tot(1.0)},
        "shop": {"lighting": tot(0.9), "heating_power": rk(1, 0.75, 0.75), "cooker": rk(1, 0.8, 0.6), "motors": rk(1, 0.8, 0.6),
                 "inst_wh": rk(1, 1, 0.25), "thermo_wh": tot(1.0), "standard": rk(1, 0.5, 0.5), "sockets": rk(1, 0.75, 0.75), "ac": tot(1.0), "ev": tot(1.0)},
        "hotel": {"lighting": tot(0.75), "heating_power": rk(1, 0.8, 0.6), "cooker": rk(1, 0.8, 0.6), "motors": rk(1, 0.5, 0.5),
                  "inst_wh": rk(1, 1, 0.25), "thermo_wh": tot(1.0), "standard": rk(1, 0.5, 0.5), "sockets": rk(1, 0.75, 0.4), "ac": tot(1.0), "ev": tot(1.0)}}}
    T["diversity_eig_a11_apartments"] = {"card": "EL-EIG-A11-DIV", "rows": [[2, 4, 1.0], [5, 9, 0.78], [10, 14, 0.63], [15, 19, 0.53], [20, 24, 0.49],
                                          [25, 29, 0.46], [30, 34, 0.44], [35, 39, 0.42], [40, 49, 0.41], [50, 1000000, 0.38]]}
    T["disconnection_s"] = {"card_tn": "EL-IEC-4-41-TN-F19", "card_tt": "EL-IEC-4-41-TT-F13",
        "rows": [{"uo_gt": 50, "uo_le": 120, "tn": 0.8, "tt": 0.3}, {"uo_gt": 120, "uo_le": 230, "tn": 0.4, "tt": 0.2},
                 {"uo_gt": 230, "uo_le": 400, "tn": 0.2, "tt": 0.07}, {"uo_gt": 400, "uo_le": 1e9, "tn": 0.1, "tt": 0.04}],
        "other_circuits_s": {"tn": 5.0, "tt": 1.0}}
    T["mcb_magnetic_multiple_iec60898"] = {"card": "EL-EIG-H28-CURVES", "rows": {"B": [3, 5], "C": [5, 10], "D": [10, 20]}}
    T["rcd_max_time_s_domestic_instantaneous"] = {"card": "EL-IEC-RCD-TIMES-F14", "rows": {"1": 0.3, "2": 0.15, "5": 0.04}}
    T["tt_ra_max_ohm"] = {"card": "EL-IEC-TT-RA", "rows": {"3000": 16, "1000": 50, "500": 100, "300": 166, "30": 1666}, "unit": "idn_ma -> RA ohm at 50 V"}
    T["voltage_drop_limits_pct"] = {"card": "EL-IEC-G521-VDLIM", "lighting": 3.0, "other": 5.0}
    T["breaker_ladder_a"] = {"card": "EL-POL-BREAKERS", "rows": [6, 10, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000]}
    T["csa_ladder_mm2"] = [1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300]
    return T


def main() -> None:
    (HERE / "cards.json").write_text(json.dumps(cards(), indent=1, ensure_ascii=False), encoding="utf-8")
    (HERE / "tables.json").write_text(json.dumps(tables(), indent=1, ensure_ascii=False), encoding="utf-8")
    print("cards", len(cards()), "tables", len(tables()))


if __name__ == "__main__":
    main()
