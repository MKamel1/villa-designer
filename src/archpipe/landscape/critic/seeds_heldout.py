"""Held-out seeded defects, WRITTEN BEFORE THEY WERE RUN (see PREREG.md): not iterated until they trip.
Each is built from named quantities on the same reference scheme; the criterion it should trip is stated here first."""
from __future__ import annotations

import copy
import json

from .seeds import base, OUT, _chair


def h_west_hedge_removed(l):
    """The 2.4 m west hedge (sister-plot boundary) removed."""
    l["screens"] = [s for s in l["screens"] if s["id"] != "hedge-west"]


def h_trees_only(l):
    """Every shrub and ground plant removed, leaving the lemon tree alone."""
    l["planting_groups"] = []


def h_drifts_of_two(l):
    """Every species planted in pairs (count 2) instead of drifts of 3 to 6."""
    for g in l["planting_groups"]:
        out = []
        for p in g["plants"]:
            for _ in range(max(1, p["count"] // 2)): out.append({**p, "count": 2})
        g["plants"] = out


def h_oleander_by_seats(l):
    """The rear screen planted with oleander (highly toxic) 1 m from the lounge chairs, in place of Pittosporum."""
    for g in l["planting_groups"]:
        if g["id"] == "bed-rear":
            g["plants"] = [{"species": "Nerium oleander", "count": 3, "form": "shrub"}, {"species": "Ophiopogon japonicus", "count": 6, "form": "ground_cover"}]


def h_bbq_in_bed(l):
    """The BBQ stand place moved into the pond planting bed, 0.2 m from the plants."""
    for f in l["features"]:
        if f["kind"] == "bbq": f["center"] = [17.0, -21.0]


def h_service_narrow(l):
    """The service path 0.5 m wide (a wheelbarrow needs 0.6 m)."""
    for p in l["paths"]:
        if p["class"] == "service": p["width_m"] = 0.5


def h_quiet_beside_dining(l):
    """The south quiet bench moved to 1.5 m from the dining table."""
    for s in l["seating"]:
        if s["id"] == "bench-quiet": s["rect"] = [25.9, -22.0, 26.3, -21.4]; s["zone"] = "dining"


def h_herb_in_shade(l):
    """The herb bed moved to the north court (1.3 h of sun on 21 Jun, against 6 h for herbs)."""
    for f in l["features"]:
        if f["kind"] == "herb_bed": f["rect"] = [0.2, -27.5, 1.2, -26.5]; 


def h_pergola_removed(l):
    """The dining pergola removed (the only overhead cover)."""
    l["canopies"] = []


HELD = {
    "west-hedge-removed": (h_west_hedge_removed, ["C-PRIVACY", "A-ENCLOSURE"]),
    "trees-only": (h_trees_only, ["H-LAYERS"]),
    "drifts-of-two": (h_drifts_of_two, ["H-DRIFTS"]),
    "oleander-by-seats": (h_oleander_by_seats, ["H-TOXIC-PLACEMENT"]),
    "bbq-in-bed": (h_bbq_in_bed, ["U-BBQ"]),
    "service-narrow": (h_service_narrow, ["U-SERVICE"]),
    "quiet-beside-dining": (h_quiet_beside_dining, ["U-QUIET-SOUTH"]),
    "herb-in-shade": (h_herb_in_shade, ["LS-HERB-SUN"]),
    "pergola-removed": (h_pergola_removed, ["C-PRIVACY"]),
}


def make(i: str) -> dict:
    lay = copy.deepcopy(base()); fn, exp = HELD[i]; fn(lay)
    lay["id"] = "held-" + i
    lay["seeded_defect"] = {"id": i, "what": " ".join((fn.__doc__ or "").split()), "expect": exp, "heldout": True}
    return lay


def save_all():
    d = OUT.parent / "seeded-heldout"; d.mkdir(parents=True, exist_ok=True)
    for k in HELD: (d / f"{k}.json").write_text(json.dumps(make(k), indent=1) + "\n")
