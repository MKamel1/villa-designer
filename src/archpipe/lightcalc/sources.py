"""SourceCards for every threshold the lighting engine uses (LANES.md rule 3).

Status discipline: `sourced` = value read on a held page this session and the
quote is verbatim from the held text layer; `std` = standard not held (value from
the criteria document, needs the page); `policy` = ours, stated as ours;
`unverified` = cannot gate.
"""
from __future__ import annotations

from ..contracts import SourceCard

IES_PATH = "knowledge index book 'ies-handbook'"
SLL_PATH = "knowledge index book 'sll-code'"

CARDS: dict[str, SourceCard] = {c.id: c for c in [
    SourceCard(
        id="IES-HB10-p33.25-avg-allowance",
        document="IES Lighting Handbook, 10th ed. (2011), 33.3.3",
        edition="10th ed., 2011", locator="printed p. 33.25 (pdf_page 1135)",
        quote=("Standard engineering allowance of ±10% might be acceptable for targets gauged as average "
               "unless contractual or code obligations demand otherwise. Minima and maxima must be achieved "
               "as intended."),
        value="±10 % on average-gauged targets", status="sourced", url_or_path=IES_PATH),
    SourceCard(
        id="IES-HB10-p33.25-uniformity-targets",
        document="IES Lighting Handbook, 10th ed. (2011), 33.3.4 Uniformity Targets",
        edition="10th ed., 2011", locator="printed p. 33.25 (pdf_page 1135)",
        quote=("Illuminance uniformity targets work in conjunction with luminance uniformities and surface "
               "reflectances all of which must be addressed as part of the design to avoid visual discomfort, "
               "glare, and strain."),
        value="report U0, max:avg, avg:min; ratios per Table 33.2 where cited", status="sourced",
        url_or_path=IES_PATH),
    SourceCard(
        id="EN12464-1-task-U0-0.6",
        document="EN 12464-1 (not held)", edition="", locator="task area uniformity, study/office",
        quote="", value="U0 >= 0.6 (task area)", status="std",
        url_or_path="docs/quality/a-plus-lighting-electrical.md LA3"),
    SourceCard(
        id="L6-POLICY-LA2-over-lighting-1.5x",
        document="L6 lighting engine policy", edition="2026-11", locator="LA2",
        quote="", value="task Eavg <= 1.5 x target in the design scene",
        status="policy",
        url_or_path=("The IES p.33.25 allowance covers +/-10 % only; the 1.5x factor is OUR policy cap "
                     "(docs/quality/a-plus-lighting-electrical.md LA2: 'proposed and needs a carded basis')")),
    SourceCard(
        id="SLL-p207-UGR-basic-equation",
        document="SLL Code for Lighting (2012), 12.3.5", edition="2012", locator="printed pp. 206-207, eq. 12.16",
        quote=("p is the Guth Position Index for each individual luminaire, which relates to its displacement "
               "from the line of sight."),
        value="UGR = 8 log10[(0.25/Lb) * sum(L^2 * omega / p^2)], Lb = Eind/pi",
        status="sourced", url_or_path=SLL_PATH),
    SourceCard(
        id="UGR-limit-19-reading-writing",
        document="ZVEI position paper on the UGR method (quoting DIN EN 12464-1 Table 1)", edition="2110",
        locator="section 2, Table 1",
        quote="Reading, writing, classrooms, computer work, control work ≤19",
        value="UGR <= 19 (study)", status="std",
        url_or_path="https://www.licht.de/fileadmin/Publications/ZVEI_Publications/2110_E_ZVEI_UGR_method.pdf"),
    SourceCard(
        id="L6-POLICY-LA4-luminance-3000",
        document="L6 lighting engine policy", edition="2026-11", locator="LA4",
        quote="", value="no source > 3,000 cd/m2 visible within 45 deg of a given sightline unless shielded",
        status="policy",
        url_or_path="panel figure (docs/reviews/2026-11/panel-lighting-electrical.md); UNVERIFIED as a standard value"),
    SourceCard(
        id="L6-POLICY-LA9-axis-tolerance-10mm",
        document="L6 lighting engine policy", edition="2026-11", locator="LA9",
        quote="", value="luminaire on a declared axis within 10 mm", status="policy"),
    SourceCard(
        id="L6-LA9-spacing-SHR",
        document="Luminaire datasheet SHR (method: SLL Code 12.2 spacing/UGR tables)", edition="2012",
        locator="chapter 12", quote="", value="centre spacing <= SHR_max x mounting height above the work plane",
        status="policy",
        url_or_path="SHR_max is carried per luminaire from its data; no generic number is assumed"),
    SourceCard(
        id="L6-LA9-washer-setback-0.6-1.0",
        document="docs/quality/a-plus-lighting-electrical.md LA9", edition="2026-11", locator="LA9",
        quote="", value="wall-wash setback 0.6-1.0 m", status="unverified"),
    SourceCard(
        id="SLL-T3.2-E3",
        document="SLL Code for Lighting (2012), Table 3.2 Maximum obtrusive light permitted for exterior lighting installations",
        edition="2012", locator="printed p. 90 (pdf_page 97), zone E3",
        quote=("Environmental zone | Light on properties Ev lx pre curfew (a) / post curfew | Luminaire intensity I cd "
               "pre / post | Upward light ULR % | Luminance Lb, Ls cd/m2 ... E3 10 2 10 000 1000 0.15 10 800 ... "
               "E3 represents medium district brightness areas, such as industrial or residential suburbs"),
        value="E3: Ev 10 lx pre / 2 lx post curfew; I 10,000 cd pre / 1,000 cd post; ULR 0.15; Lb 10 cd/m2",
        status="sourced",
        url_or_path=(SLL_PATH + ". The printed column header for ULR says '%' but the printed values are "
                     "0 / 0.05 / 0.15 / 0.25; the engine reads 0.15 as a FRACTION (15 %), matching "
                     "docs/quality/a-plus-lighting-electrical.md LA12 'ULR <= 0.15'.")),
    SourceCard(
        id="EN1838-1lx-escape-route",
        document="EN 1838 (not held); SLL Code 12.2.10 describes the method",
        edition="", locator="escape route centre line",
        quote=("the illuminance on the centre line of the escape route does not fall below the required "
               "illuminance and that the edges of the strip have at least half that illuminance"),
        value=">= 1 lx on the centre line (edges >= 0.5 lx), >= 1 h", status="std",
        url_or_path="quote: SLL Code printed p. 199 (pdf_page 206); the 1 lx value is EN 1838, not held"),
    SourceCard(
        id="CIE171-2006-5.2-via-DAU",
        document="CIE 171:2006 test case 5.2 (point source, diffuse photometry), values as reproduced in DAU 'Validation of NVIDIA Iray against CIE 171:2006' Table 7",
        edition="2016 (DAU); CIE 171:2006 not held", locator="DAU p. 18, Table 7",
        quote="", value="E(A..J) = 111.11 105.21 90.02 71.11 99.73 85.64 68.06 74.36 59.98 49.39 lx; tolerance +/-5 % (LA1 row)",
        status="std",
        url_or_path="https://developer.nvidia.com/sites/default/files/akamai/designworks/docs/Validation of NVIDIA's Iray against CIE 171_20160217.pdf"),
    SourceCard(
        id="CIE171-2006-5.8-via-DAU",
        document="CIE 171:2006 test case 5.8 (internal reflected component), values as reproduced in DAU Table 15",
        edition="2016 (DAU); CIE 171:2006 not held", locator="DAU p. 25, Table 15",
        quote="", value="Eav (average indirect illuminance): rho 0.5 -> 104.00, 0.8 -> 417.00, 0.2 -> 26.00 lx; tolerance +/-5 % (LA1 row)",
        status="std",
        url_or_path="https://developer.nvidia.com/sites/default/files/akamai/designworks/docs/Validation of NVIDIA's Iray against CIE 171_20160217.pdf"),
    SourceCard(
        id="SLL-T12.6-UGR-flux-correction",
        document="SLL Code for Lighting (2012), Table 12.6 / eq. 12.3", edition="2012", locator="printed p. 198 (pdf_page 205)",
        quote="Table 12.6 Tabulated values of correction factor  Lamp flux 1000 0.0  2000 2.4  3000 3.8  4000 4.8  100 -8.0  500 -2.4",
        value="UGR correction = 8 log10(lamp flux / 1000)", status="sourced", url_or_path=SLL_PATH),
    SourceCard(
        id="SLL-T12.10-UGR-K",
        document="SLL Code for Lighting (2012), Table 12.10 and K = pi / (4 p^2 D^2)", edition="2012",
        locator="printed pp. 209-211 (pdf_pages 216-218)",
        quote="Table 12.10 Pre-calculated parameters for luminaires in the standard array",
        value="27 transcribed K cells, H = 2 m", status="sourced", url_or_path=SLL_PATH),
    SourceCard(
        id="L6-POLICY-LA6-2700K",
        document="L6b villa lighting policy", edition="2026-11", locator="LA6",
        quote="", value="one CCT per layer per room; 2700 K interior layers, 2200 K night layer; schedule CCT = bound product CCT",
        status="policy", url_or_path="docs/quality/a-plus-lighting-electrical.md LA6 (R9/SDCM values UNVERIFIED, not checked here)"),
    SourceCard(
        id="L6-POLICY-LA8-layers",
        document="L6b villa lighting policy", edition="2026-11", locator="LA8",
        quote="", value=">= 2 independently switched layers per habitable space",
        status="policy", url_or_path="docs/quality/a-plus-lighting-electrical.md LA8 (IES Ch. 33 layering; practice)"),
    SourceCard(
        id="L6-POLICY-LA10-scenes",
        document="L6b villa lighting policy", edition="2026-11", locator="LA10",
        quote="", value="each task card is met (+/-10 %, <= 1.5x) in the scene that owns it; night level <= 10 %",
        status="policy", url_or_path="docs/quality/a-plus-lighting-electrical.md LA10 (values are proposals, UNVERIFIED)"),
]}



def card(card_id: str) -> SourceCard:
    return CARDS[card_id]
