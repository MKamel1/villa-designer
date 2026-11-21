"""Cards from UK Approved Document B vol.1 (not held; downloaded from gov.uk to r_dl/adb/adb1.pdf)."""
import sys
from cardlib import pdf_quote, write
from archpipe.contracts import SourceCard

PDF = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\mmbka\r_dl\adb\adb1.pdf"
URL = ("https://assets.publishing.service.gov.uk/media/67d0230974b001c38a0287ad/Approved_Document_B_volume_1_-_"
       "Dwellings_2019_edition_incorporating_2020_and_2022_amendments_collated_with_2025_2026_and_2029_amendments.pdf"
       " (downloaded 2026-11-20; not a held book)")
DOC = "Approved Document B (Fire safety) Volume 1: Dwellings (England)"
ED = ("2019 edition incorporating 2020 and 2022 amendments, collated with the 2025, 2026 (in force 2026-09-30) "
      "and 2029 amendments. The edition summaries list Regulation 38 and fire safety information, reaction-to-fire classes, sprinklers in care homes, "
      "blocks of flats, evacuation lifts and fire-resistance classes; whether any carded paragraph text changed was not compared against the 2019 base")

ROWS = [
    ("UK-ADB1-2019-1.1-alarm-grade", "para 1.1",
     "All dwellings should have a fire detection and alarm system, minimum Grade D2 Category LD3 standard, in accordance with the relevant recommendations of BS 5839-6.",
     "minimum Grade D2 Category LD3"),
    ("UK-ADB1-2019-1.2-1.4-alarm-power", "paras 1.2 and 1.4",
     "Smoke alarms should be mains operated and conform to BS EN 14604.",
     "smoke alarms mains operated, BS EN 14604; standby power (battery or capacitor)"),
    ("UK-ADB1-2019-1.7-large-three-storeys", "para 1.7",
     "A large dwellinghouse of three or more storeys (excluding basement storeys) should be fitted with a Grade A Category LD2 fire detection and alarm system as described in BS 5839-6.",
     "large dwellinghouse of three or more storeys (basement excluded): Grade A Category LD2"),
    ("UK-ADB1-2019-1.6-large-two-storeys", "para 1.6",
     "A large dwellinghouse of two storeys (excluding basement storeys) should be fitted with a Grade A Category LD3 fire detection and alarm system, as described in BS 5839-6.",
     "large dwellinghouse of two storeys (basement excluded): Grade A Category LD3"),
    ("UK-ADB1-2019-1.5-large-definition", "para 1.5",
     "A large dwellinghouse has more than one storey, and at least one storey exceeds 200m2.",
     "large dwellinghouse = more than one storey and a storey >200 m2"),
    ("UK-ADB1-2019-2.1-habitable-rooms-ground", "para 2.1",
     "All habitable rooms (excluding kitchens) should have either of the following. a. An opening directly onto a hall leading to a final exit. b. An emergency escape window or door, as described in paragraph 2.10.",
     "ground-storey habitable rooms: opening onto hall to final exit, or escape window/door"),
    ("UK-ADB1-2019-2.5-protected-stairway", "para 2.5 (storey >4.5 m above ground)",
     "Dwellinghouses with one storey more than 4.5m above ground level 2.5 See Diagram 2.1c. The dwellinghouse should have either of the following. a. Protected stairway - a stair separated by fire resisting construction (minimum REI 30) at all storeys",
     "storey >4.5 m above ground: protected stairway REI 30 to a final exit, or alternative escape"),
    ("UK-ADB1-2019-2.10-escape-window", "para 2.10a",
     "A minimum height of 450mm and a minimum width of 450mm (the route through the window may be at an angle rather than straight through).",
     "escape window openable area >=450 mm high and >=450 mm wide", 27),
    ("UK-ADB1-2019-2.10-escape-window-area", "para 2.10a i",
     "A minimum area of 0.33m2", "escape window unobstructed openable area >=0.33 m2", 27),
    ("UK-ADB1-2019-2.10-escape-window-1100", "para 2.10a iii",
     "The bottom of the openable area is a maximum of 1100mm above the floor.",
     "bottom of openable area <=1100 mm above floor", 27),
    ("UK-ADB1-2019-2.16-basement", "para 2.16",
     "Basement storeys containing habitable rooms should have one of the following. a. An emergency escape window or external door providing escape from the basement (paragraph 2.10). b. A protected stairway (paragraph 2.5a) leading from the basement to a final exit.",
     "basement with habitable rooms: escape window/external door or protected stairway to a final exit"),
]

cards = []
for cid, loc, quote, value, *hint in ROWS:
    label, pdf, q = pdf_quote(PDF, quote, hint[0] if hint else None)
    cards.append(SourceCard(id=cid, document=DOC, edition=ED, locator=f"{loc}; printed p. {label} (pdf page {pdf})",
                            quote=q, value=value, status="sourced", url_or_path=URL))
print(write("uk-ad-b1-2019.json", cards))
