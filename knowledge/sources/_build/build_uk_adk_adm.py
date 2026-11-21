"""Cards from the held UK Approved Documents K (2013) and M vol.1 (2015). Run: python build_uk_adk_adm.py"""
from cardlib import held_quote, write
from archpipe.contracts import SourceCard

K = "uk-ad-k"
M = "uk-ad-m#BR_PDF_AD_M1_2015_with_2016_amendments_V3"
K_DOC = "Approved Document K: Protection from falling, collision and impact (England)"
K_ED = "2013 edition (held: knowledge/library.json uk-ad-k)"
K_URL = "held: uk-ad-k; https://assets.publishing.service.gov.uk/media/60d5bdcde90e07716f516cfd/Approved_Document_K.pdf"
M_DOC = "Approved Document M: Access to and use of buildings, Volume 1: Dwellings (England)"
M_ED = "2015 edition with 2016 amendments (held: knowledge/library.json uk-ad-m)"
M_URL = ("held: uk-ad-m; https://assets.publishing.service.gov.uk/media/5a7f8a82ed915d74e622b17b/"
         "BR_PDF_AD_M1_2015_with_2016_amendments_V3.pdf")

# (id, locator-prefix, quote, value)
K_ROWS = [
    ("UK-ADK-2013-1.3-T1.1-private-stair", "para 1.3, Table 1.1",
     "Private stair1, 2 150 220 220 300",
     "Private stair: rise 150-220 mm, going 220-300 mm"),
    ("UK-ADK-2013-1.3-T1.1-note1-pitch", "para 1.3, Table 1.1 note 1",
     "The maximum pitch for a private stair is 42°.", "max pitch 42 deg (private stair)"),
    ("UK-ADK-2013-1.3-2R+G", "para 1.3, Table 1.1 footnote *",
     "twice the rise plus the going (2R + G) equals between 550mm and 700mm.",
     "2R+G = 550-700 mm (normal relationship)"),
    ("UK-ADK-2013-1.5-uniform-steps", "para 1.5",
     "Have level treads on steps, ensuring that the rise and going of each step are consistent throughout a flight of steps",
     "rise and going consistent in a flight; level treads"),
    ("UK-ADK-2013-1.8-soffit", "para 1.8",
     "If the soffit beneath a stair is less than 2m above floor level, protect the area beneath a stair",
     "soffit <2 m above floor: guard/barrier below stair"),
    ("UK-ADK-2013-1.9-open-risers", "para 1.9 (dwellings)",
     "Steps may have open risers if they comply with both of the following guidance. a. Overlap treads by a minimum of 16mm. b. Construct the steps so that a 100mm diameter sphere cannot pass through the open risers.",
     "open risers in dwellings: tread overlap >=16 mm and 100 mm sphere cannot pass"),
    ("UK-ADK-2013-1.11-headroom", "para 1.11, Diagram 1.3",
     "On the access between levels, provide the minimum headroom shown in Diagram 1.3.",
     "minimum headroom 2 m on the pitch line/landing (Diagram 1.3 reads 'At least 2m')"),
    ("UK-ADK-2013-1.16-entrance-storey-width", "para 1.16 (dwellings)",
     "ensure that stairs within the entrance storey of a dwelling have flights with a minimum stair width of 900mm.",
     "900 mm stair width, exceptional (severely sloping plot) entrance-storey stairs; ADK sets no other dwelling stair width"),
    ("UK-ADK-2013-1.17-36-risers", "para 1.17 (all buildings)",
     "If stairs have more than 36 risers in consecutive flights, make a minimum of one change of direction between flights",
     "more than 36 consecutive risers: change of direction >=30 deg"),
    ("UK-ADK-2013-1.20-landings", "para 1.20 (all buildings)",
     "At the top and bottom of every flight, provide landings the width and length at least as great as the smallest width of the flight",
     "landing width and length >= flight width"),
    ("UK-ADK-2013-1.34-handrail", "para 1.34 (all buildings)",
     "Position the top of the handrail 900mm to 1000mm from the pitch line or floor.",
     "handrail top 900-1000 mm from pitch line/floor; both sides if stair >=1000 mm wide"),
    ("UK-ADK-2013-K2-performance-600", "Requirement K2, Performance a.",
     "in dwellings: provide pedestrian guarding that is capable of preventing people from being injured by falling from a height of more than 600mm",
     "dwellings: guard where drop > 600 mm"),
    ("UK-ADK-2013-3.1-guard-siting", "para 3.1a",
     "any light well, basement or similar sunken area next to a building",
     "guarding required at light wells, basements and similar sunken areas next to a building (height not stated for sunken areas)"),
    ("UK-ADK-2013-D3.1-guard-900", "Diagram 3.1 (p.24; figure page)",
     "Single family dwellings Stairs, landings, ramps, edges of internal floors 900mm for all elements",
     "single-family dwelling stairs, landings, ramps, internal floor edges: guard >=900 mm"),
    ("UK-ADK-2013-D3.1-guard-1100", "Diagram 3.1 (p.24; figure page)",
     "External balconies, including Juliette balconies and edges of roof 1100mm",
     "single-family dwelling external balconies and roof edges: guard >=1100 mm"),
    ("UK-ADK-2013-3.3-sphere-climb", "para 3.3",
     "ensure that a 100mm sphere cannot pass through any openings in the guarding. b. To prevent children from readily being able to climb the guarding: avoid horizontal rails.",
     "100 mm sphere test; avoid horizontal rails (buildings used by children under five)"),
]

M_ROWS = [
    ("UK-ADM1-2015-M4(1)-performance", "Requirement M4(1), Performance d.-f.",
     "Visitors can access and use the habitable rooms and a WC within the entrance storey of the dwelling",
     "WC on entrance storey; step-free between habitable rooms and WC; accessible switches/sockets"),
    ("UK-ADM1-2015-1.6-approach-900", "para 1.6c",
     "The approach route is a minimum of 900mm wide with a maximum cross fall of 1 in 40.",
     "approach route >=900 mm wide, cross fall <=1:40"),
    ("UK-ADM1-2015-1.7-ramp", "para 1.7a",
     "for gradients up to 1:15 - not more than 10m long",
     "external ramp flights: <=1:15 up to 10 m; <=1:12 up to 5 m; clear width >=900 mm"),
    ("UK-ADM1-2015-1.14-entrance", "para 1.14",
     "The door has a minimum clear opening width of 775mm, when measured in accordance with Diagram 1.1.",
     "principal private entrance clear opening >=775 mm; accessible threshold; unavoidable step rise <=150 mm", "7"),
    ("UK-ADM1-2015-1.17-WC", "para 1.17",
     "The door to the room opens outwards and has a clear opening width in accordance with Table 1.1.",
     "entrance-storey WC door opens outwards; clear space per Diagram 1.3"),
    ("UK-ADM1-2015-1.18-controls", "para 1.18a-b",
     "have their centre line 450-1200mm above floor level, as shown in Diagram 1.5.",
     "switches, sockets, door bells, TV and telephone points 450-1200 mm above floor; consumer unit switches 1350-1450 mm"),
    ("UK-ADM1-2015-1.15-corridor", "para 1.15b",
     "the corridor is not reduced below a minimum 750mm width at any point.",
     "corridor not below 750 mm at a localised obstruction", "7"),
    ("UK-ADM1-2015-2.27-WC-M4(2)", "para 2.27 (M4(2) optional)",
     "Every dwelling has a room within the entrance storey that provides a WC and basin",
     "M4(2): entrance-storey WC+basin; 3+ bedroom dwelling also a level-access shower; door opens outwards"),
]


def mk(book, doc, ed, url, rows):
    out = []
    for cid, loc, quote, value, *lab in rows:
        label, pdf, q = held_quote(book, quote, lab[0] if lab else None)
        out.append(SourceCard(id=cid, document=doc, edition=ed, locator=f"{loc}; printed p. {label} (pdf index {pdf})",
                              quote=q, value=value, status="sourced", url_or_path=url))
    return out


if __name__ == "__main__":
    print(write("uk-ad-k-2013.json", mk(K, K_DOC, K_ED, K_URL, K_ROWS)))
    print(write("uk-ad-m1-2015.json", mk(M, M_DOC, M_ED, M_URL, M_ROWS)))
