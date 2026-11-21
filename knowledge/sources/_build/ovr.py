"""Review fixes for build_std.py: every number in a card's value must be supported by its quote.
A key here replaces the row's quote / value / locator ("loc") of the same card id (applied by build_std.held/pdfs/html)."""

OVR = {
    "EN12464-1-2011-2.1.6.2-cylindrical": dict(
        quote="The maintained mean cylindrical illuminance (average vertical plane illuminance) in the activity and interior areas shall be not less than 50 lx with Uo ≥ 0.10",
        value="maintained mean cylindrical illuminance >= 50 lx with Uo >= 0.10 in the activity and interior areas"),
    "EN12464-1-2011-2.1.5-UGR-note": dict(value="UGR limits are those given in section 2; the maximum UGR in the room is compared with that limit"),
    "SLL-12.2.10-escape-centreline": dict(value="escape routes: centre-line illuminance at least the required value, strip edges at least half of it"),
    "IES-HB10-14.47-sDA": dict(value="sDA300 > 50% nominally acceptable; satisfaction rises above 75%"),
    "IES-HB10-14.47-sDA-def": dict(
        quote="each sensor point that achieves at least 300 lux for at least 50% of the analysis year contributes to the area that meets the criteria.",
        value="sDA: a point counts if it reaches at least 300 lux for at least 50% of the analysis year"),
    "IES-HB10-14.47-sunlight-1000": dict(value="direct-sunlight metric: hours per year when direct sun alone exceeds 1000 lux"),
    "IES-LM83-12-sDA-55-75": dict(value="sDA: more than 55% of floor area nominally acceptable; more than 75% preferred"),
    "IES-LM83-12-ASE-10": dict(value="ASE: below 10% of the floor area for less discomfort"),
    "IES-LM83-12-ASE-def": dict(value="ASE: share of floor area above 1000 lux of computational direct sunlight"),
    "IES-LM83-12-ASE-250h": dict(value="ASE duration criterion: more than 250 annual analysis hours"),
    "IEC60364-4-41-2005-411.3.2.2-scope": dict(value="Table 41.1 applies to final circuits not exceeding 32 A"),
    "IEC60364-4-41-2005-T41.1": dict(value="a.c. 120 V < Uo <= 230 V: TN 0.4 s, TT 0.2 s; 230 V < Uo <= 400 V: TN 0.2 s, TT 0.07 s"),
    "IEC60364-4-41-2005-411.3.2.3-5s": dict(
        quote="In TN systems, a disconnection time not exceeding 5 s is permitted for distribution circuits, and for circuits not covered by 411.3.2.2. 411.3.2.4 In TT systems, a disconnection time not exceeding 1 s is permitted for distribution circuits",
        value="TN distribution circuits: 5 s; TT distribution circuits: 1 s"),
    "IEC60364-4-41-2005-411.3.3-20A": dict(
        quote="additional protection by means of a residual current protective device (RCD) in accordance with 415.1 shall be provided for – socket-outlets with a rated current not exceeding 20 A that are for use by ordinary persons and are intended for general use",
        value="2005 text: RCD additional protection on general-use socket-outlets with rated current not exceeding 20 A"),
    "IEC60364-4-41-2005-411.4.4-Zs": dict(value="TN: Zs x Ia <= Uo, with Ia the current causing disconnection within the specified time"),
    "IEC60364-4-41-2005-411.5.3-RA": dict(value="TT with an RCD: RA x I_delta_n <= 50 V in addition to the disconnection-time requirement"),
    "IEC60364-4-41-AMD1-2017-411.3.2.2-scope": dict(value="Table 41.1 applies to final circuits up to 63 A with socket-outlets and up to 32 A supplying only fixed equipment"),
    "IEC60364-4-41-AMD1-2017-T41.1": dict(
        loc="Table 41.1 (replaced; columns 50-120 V, 120-230 V, 230-400 V, above 400 V, each a.c. and d.c.)",
        value="a.c. 120 V < Uo <= 230 V: TN 0.4 s, TT 0.2 s; 230 V < Uo <= 400 V: TN 0.2 s, TT 0.07 s"),
    "IEC60364-4-41-AMD1-2017-411.3.3-32A": dict(
        quote="Additional protection by means of a residual current protective device (RCD) with a rated residual operating current not exceeding 30 mA shall be provided for - a.c. socket-outlets with a rated current not exceeding 32 A that are liable to be used by ordinary persons and are intended for general use, and - a.c. mobile equipment for use outdoors with a rated current not exceeding 32A.",
        value="30 mA RCD on general-use a.c. socket-outlets up to 32 A and on a.c. mobile equipment for outdoor use up to 32 A"),
    "IEC60364-7-701-2019-701.30.103-zone1": dict(value="bath tub: zone 1 reaches 225 cm above the floor below the tub, or the highest fixed shower head or outlet if higher"),
    "IEC60364-7-701-2019-701.30.104-zone2": dict(value="bath tub only: zone 2 extends 60 cm beyond zone 1"),
    "IEC60364-7-701-2019-701.415.1.101-RCD": dict(
        quote="additional protection by the use of one or more RCDs having a rated residual operating current not exceeding 30 mA shall be provided for: – circuits serving the location containing a bath tub and/or a shower; – circuits passing through zone 1 and/or zone 2 not serving this location.",
        value="30 mA RCD for circuits serving the bath/shower location and circuits passing through zone 1 and/or zone 2 (SELV/PELV and electrical separation excepted)"),
    "IEC60364-7-701-2019-701.512.2.4.101.4-zone2-equipment": dict(
        quote="socket-outlets, having a degree of protection of at least IPX4, of circuits protected by SELV or PELV with the source of supply installed outside zones 0 and 1; – electrical accessories, other than socket-outlets, having a degree of protection at least IPX4, that are permanently connected; – shaver supply units according to IEC 61558-2-5.",
        value="zone 2: sockets only on SELV/PELV with the source outside zones 0 and 1 (IPX4); shaver supply units to IEC 61558-2-5"),
    "IEC60364-5-52-G52.1-B": dict(value="private LV supply: lighting 6%, other use 8%"),
    "IEEE1789-2015-low-risk-0.08f": dict(value="low-risk: max %Flicker = frequency x 0.08, rounded up to the nearest whole number"),
    "IEEE1789-2015-min-freq-100": dict(value="the multiplication shortcut applies to products flickering at 100 Hz or more"),
    "EN1838-escape-1lx-centreline": dict(value="escape route: at least 1 lx on the floor along the centre line"),
    "EN1838-vendor-escape-1lx-1m-band": dict(value="at least 1 lux along the centre line for a path width of one metre"),
    "EN1838-vendor-duration": dict(value="rated service time is at least one hour"),
    "MH7-11-27-escape-lighting": dict(value="principle only; the table that follows covers common escape routes, not the inside of a single-family house (advisory for a villa)"),
    "NKBA-BG20-toilet-centreline-18in": dict(value="toilet or bidet centreline at least 18 in (457 mm) from any fixture, wall or obstacle (recommended)"),
    "NKBA-BG21-toilet-front-21in": dict(value="code minimum: 21 in (533 mm) clear in front of the toilet"),
    "NKBA-BG9-shower-36in": dict(value="interior shower at least 36 x 36 in (914 x 914 mm), recommended"),
    "US-16CFR1261.2-ASTM-F2057-23": dict(value="clothing storage units must comply with ASTM F2057-23"),
    "US-F2057-23-9.2.2-pull": dict(
        quote="applies a 10-pound horizontal force over a period of at least 5 seconds at a ``hand-hold'' not to exceed a 56-inch height",
        value="horizontal force of 10 lb for at least 5 s at a hand-hold no higher than 56 in"),
}
