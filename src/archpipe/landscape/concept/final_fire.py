"""Fire-pit product shortlist (gas, flush-installable in principle) with the clearances their installation manuals STATE. Quotes are checked against the manual text
snapshots in knowledge/landscape/concept/final/fire-manuals/ by tests/landscape/concept/test_final.py.

Honest status: NO manual read states that the product may be installed flush with paving, and NO manual states a walk-on load rating for a cover. Flush installation and the cover
are therefore a supplier/engineer approval item, not a certified fact. The design clearances (final.FIRE_SIDE_M, FIRE_OVER_M) are the strictest stated figures in this shortlist, so any
of the three fits the same layout; the product decision stays open.
"""
from __future__ import annotations

from pathlib import Path

from . import site as S

DIR = S.ROOT / "knowledge" / "landscape" / "concept" / "final" / "fire-manuals"

PRODUCTS = [
    {"id": "PTI-linear-inner", "name": "Pebble Technology (PTI) linear burner, inner mount, 12 V AC, 36 in (0.91 m) class", "maker": "Pebble Technology International (US)",
     "cert": "CSA/AGA; CSA certificate 2325190; tested to ANSI Z223.1-2010, ANSI Z21.97-2010 (outdoor decorative gas appliances), Z21.42-2010", "egypt": "US/Canada certification only",
     "manual": "12V-AC-Linear-Burner-Installation-Maintenance-Warranty-Guidelines.pdf (pebbletec.com/wp-content/uploads/2021/11/)", "snapshot": "PTI-inner-mount-linear-burner.txt",
     "side_mm": 1219, "overhead_mm": 1829, "fuel": "natural gas or propane",
     "flush": "closest: 'the top of the Burner is 1/2 in - 1 in below the top of wall or cap of built burner cavity' (13-25 mm below the cap); flush with paving is not stated",
     "cover": "none stated; 'For installation on or over non-combustible floors only'",
     "vent": "ventilation required, 4-10 openings of 2.5 in by burner length; propane drains through ventilation holes at the sides",
     "quotes": {"clearance": "Adhere to recommended CSA/AGA clearances: sides 4ft/top 6ft.", "combustibles": "Do not install near any combustibles (side or overhead)",
                "cert": "The Pebble Technology Fire + Water Elements fire burner assembly is CSA/AGA approved."}},
    {"id": "Planika-Mico", "name": "Planika Mico Automatic 800 (LPG or natural gas), 800 x 800 mm class", "maker": "Planika (Poland)",
     "cert": "CE marking under Regulation (EU) 2016/426 (gas appliances), manual cites EN 778; certificate GAR1450CT0048", "egypt": "EU certification only; no Egyptian approval found",
     "manual": "Manual_Mico_Automatic.pdf (cdn.shopify.com/s/files/1/0729/4186/3197/files/)", "snapshot": "Planika-Mico-Automatic-manual.txt",
     "side_mm": 1000, "overhead_mm": None, "fuel": "LPG 17.6 kW max (800), natural gas version described",
     "flush": "'not a free-standing device and is destined to be housed' (a built cavity); flush with paving not stated",
     "cover": "none stated; 'protected from atmospheric conditions' when not used, main valve off",
     "vent": "ventilation grid on the lowest point of the cavity, 150 cm2 (500, 600) / 300 cm2 (800); cavity floor 5 % fall to drain",
     "quotes": {"clearance": "1 metre radius from the fire", "away": "Install the fireplace away from flammable materials", "above": "All elements above the fireplace need to be made of non-flammable materials",
                "housed": "It is not permitted to use a device which is not housed in some way", "cert": "Regulation (EU) 2016/426"}},
    {"id": "MAD-ESF", "name": "MAD Design Group ESF gas burner (clearances and installation manual)", "maker": "MAD Design Group (US)",
     "cert": "not stated in the clearances manual read", "egypt": "unknown", "manual": "ESF_CI-gas.pdf (cdn.shopify.com/s/files/1/0326/3129/2039/files/)", "snapshot": "MAD-ESF-CI-gas-clearances.txt",
     "side_mm": 610, "overhead_mm": 2000, "fuel": "propane and natural gas",
     "flush": "not stated; the manual requires ventilation of the underside and that the base never touches flammable material",
     "cover": "none stated", "vent": "'Adequate and constant ventilation ... including ventilation of the appliance undersides'",
     "quotes": {"side": "24in (610mm) away from the flame", "overhead": "78.7in (2000mm) away from the flame at all times"}},
]

REJECTED = [
    ("Travis Fire Garden linear burner (ANSI Z21.97-2017, CSA 2.41-2017)", "installs in a ventilated block enclosure with a glass wind guard: not flush; side clearance only in a diagram on p. 13 (no text)."),
    ("Firegear Outdoors LOF-H/T flat linear pits (manual 90105B)", "'installing fire pits below grade' is listed as outside the design (W-firegear-below-grade-not-supported); a lid is 'highly recommended' with no load rating."),
    ("Solus Decor linear (FSD LP)", "free-standing concrete vessel: 'not designed for seating purposes'; says nothing on flush installation (held cards W-solus-*)."),
]

SIDE_MM = max(p["side_mm"] for p in PRODUCTS)
OVER_MM = max(p["overhead_mm"] for p in PRODUCTS if p["overhead_mm"])


def snapshot_text(p):
    import re
    return re.sub(r"\s+", " ", (DIR / p["snapshot"]).read_text(errors="ignore"))


def quotes_ok():
    """{product id: {quote key: bool}}: every quoted sentence occurs in the manual text snapshot."""
    return {p["id"]: {k: q in snapshot_text(p) for k, q in p["quotes"].items()} for p in PRODUCTS}
