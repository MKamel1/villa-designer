"""Step 1: the programme. Uses from the garden brief with their areas from the LDK rules, against the measured zone areas."""
from __future__ import annotations

import json
import math

from ..rules import load
from . import site as S


def build() -> dict:
    rs = load()
    P = rs.params
    m2_seat = P["LS-DINE-AREA"]["min_m2_per_seat"]
    lounge_seat = P["LS-LOUNGE-AREA"]["min_m2_per_seat"]
    cluster = (P["LS-LOUNGE-CLUSTER"]["min_diameter_mm"] / 1000) ** 2
    stand = P["LS-STAND-AREA"]["min_m2_per_person"]
    south_area = 53.19
    def mix(n_dine, n_lounge, n_stand):
        dine = n_dine * m2_seat
        lounge = max(n_lounge * lounge_seat, cluster)
        st = n_stand * stand
        fire = 0.0       # the pit sits inside the lounge room; its 1.5 m seat ring is what sets the lounge size
        total = dine + lounge + st
        return {"dining_seats": n_dine, "lounge_seats": n_lounge, "standing": n_stand, "dining_m2": round(dine, 1), "lounge_m2": round(lounge, 1),
                "standing_m2": round(st, 1), "rooms_total_m2": round(total, 1), "south_garden_m2": south_area,
                "share_of_garden": round(total / south_area, 2), "left_for_planting_paths_bbq_m2": round(south_area - total, 1),
                "fits_with_30pct_planting": total <= 0.7 * south_area}
    scenarios = {
        "minimum (10 seated, none standing)": mix(4, 6, 0),
        "10 seated + 10 standing": mix(4, 6, 10),
        "12 seated + 8 standing": mix(6, 6, 8),
        "16 seated + 4 standing": mix(8, 8, 4),
        "20 seated (a full dining + lounge group)": mix(12, 8, 0),
        "20 seated + 20 standing (the top of the brief, all at once)": mix(12, 8, 20),
    }
    # event mode: furniture stays, the free paved floor takes standing guests
    ring_r = 0.45 + P["LS-FIRE-SEAT"]["min_mm"] / 1000 + 0.7
    prog = {
        "schema": "ldg-programme/1", "step": "1 Programme", "date": "2026-11-22",
        "zones_measured_m2": {"south": {"polygon": 53.19, "open_cells": 54.62}, "north": {"polygon": 23.65, "usable": 17.5,
                              "note": "8.75 open + 8.75 under the GF terrace slab (covered), the rest is the steps block and the yard wall"},
                              "east": {"polygon": 21.48, "open_cells": 21.0, "note": "3.0 m deep x 7.2 m; the dining and living doors and the dirty-kitchen window face it"}},
        "uses": {
            "U-S-DINE": {"text": "south garden: a dining group (brief: gatherings, ~10-20 people)", "rule": "LS-DINE-AREA", "value": f"{m2_seat} m2 per seat, table edge {P['LS-DINE-CLEAR']['min_mm']} mm clear"},
            "U-S-LOUNGE": {"text": "south garden: a lounge group around the fire", "rule": "LS-LOUNGE-AREA / LS-LOUNGE-CLUSTER", "value": f"{lounge_seat} m2 per seat, room at least {P['LS-LOUNGE-CLUSTER']['min_diameter_mm']/1000:.2f} m across ({cluster:.1f} m2)"},
            "U-S-STAND": {"text": "south garden: standing room for guests", "rule": "LS-STAND-AREA", "value": f"{stand} m2 per person"},
            "U-S-QUIET": {"text": "south garden: a quieter relaxation corner inside it", "rule": "AD-COMP prompts + LDG privacy policy", "value": "2-seat bench, least overlooked cells"},
            "U-S-FIRE": {"text": "south garden: fire pit or heater for winter evenings; flush and concealed (client addendum)", "rule": "LS-FIRE-CLEAR/-SEAT/-STRUCT/-COVER/-OVERHEAD, LS-FLUSH-LIP/-OPENING",
                         "value": f"{P['LS-FIRE-CLEAR']['min_mm']} mm clear ground, seats {P['LS-FIRE-SEAT']['min_mm']} mm away, {P['LS-FIRE-STRUCT']['min_mm']} mm to structure and planting "
                                  f"({P['LS-FIRE-STRUCT']['wood_mm']} mm for a wood fire), {P['LS-FIRE-OVERHEAD']['min_mm']} mm overhead, cover {P['LS-FIRE-COVER']['min_kN']} kN"},
            "U-S-BBQ": {"text": "south garden: a small, possibly portable BBQ: a stand place on hard surface clear of planting and the facade", "rule": "LS-FIRE-CLEAR, LS-FIRE-STRUCT", "value": "0.9 x 0.6 m stand, 900 mm clear"},
            "U-S-HERB": {"text": "herb bed and/or fruit trees", "rule": "LS-HERB-SUN", "value": f"{P['LS-HERB-SUN']['min_hours']} h direct midsummer sun; the LDS sun layer has 6 h or more only on a strip along the east fence (about 3.4 m2)"},
            "U-N-QUIET": {"text": "north garden: relaxation and quiet time", "rule": "AD-COMP prompts", "value": "bench, planting, water sound/view"},
            "U-POND": {"text": "small koi pond with lush tropical/Japanese planting, flush and discreet, north court OR in front of the dirty kitchen",
                       "rule": "LS-POND-DEPTH/-STOCK/-GUARD/-FREEBOARD/-FLUSH-MARGIN/-EDGE-SLOPE/-SHADE", "value": f"deepest {P['LS-POND-DEPTH']['min_mm']} mm, {P['LS-POND-STOCK']['inches_per_m2_unaerated']} in of fish per m2 (unaerated), rigid grille or a 1.1 m fence, shore 1:4, plant shade 50-75 %"},
            "U-PRIVACY": {"text": "privacy critical: strong screening from the neighbours and the apartment above", "rule": "LS-SCREEN 1.8 m; LDS sightline layers", "value": "boundary screens cannot stop upper-storey views (LDS): overhead cover is needed over seats"},
            "U-ACCESS": {"text": "doors reach the garden: paths at least 1.2 m (main)", "rule": "LS-PATH-MAIN", "value": "1.2 m"},
            "D-FLUSH": {"text": "client addendum 2026-11-22: pond and fire pit flush and concealed", "rule": "client decision", "value": "flush"},
            "D-DST": {"text": "lead decision: summer nights are judged on the local (DST) clock", "rule": "client/lead decision", "value": "17-20 h DST clock layer is primary"},
            "D-SHADE-OVER-SUN": {"text": "standing decision: shade over sun", "rule": "client decision", "value": "cover over seats"},
            "D-FRANGIPANI": {"text": "standing decision: frangipani", "rule": "client decision", "value": "Plumeria rubra in a pot (frost-conditional per LDL)"},
            "D-TERRACOTTA": {"text": "standing decision: terracotta pots", "rule": "client decision", "value": "pots"},
            "D-COLOUR-DRIFTS": {"text": "standing decision: colourful drifts; any beautiful, shading, site-viable plant", "rule": "client decision", "value": "repeated drifts"},
            "D-MAINT-HIGH": {"text": "maintenance high is acceptable", "rule": "client decision", "value": "no constraint"},
            "SITE-FENCE": {"text": "existing 4 m concrete fences (east, rear)", "rule": "LDS inventory", "value": "fixed"},
        },
        "south_scenarios": scenarios,
        "fire_ring_note": f"A flush fire pit (0.9 m) with its seats 1.5 m away needs a lounge ring about {2*ring_r:.1f} m across; the south garden is 5.71 m deep and the pit must be "
                          f"2.0 m from the house and the rear fence, so the pit can only sit in a band about {5.71-2*(2.0+0.45):.2f} m deep.",
        "honest_summary": [
            "The rules put 10 seated at about 24.6 m2 (4 dining seats 13.8 m2 + 6 lounge seats in a 13.4 m2 minimum room) and every extra dining seat costs 3.46 m2: 20 seated is 55.9 m2, more than the whole 53.2 m2 garden. 20 people can only be there standing (26 m2 at 1.3 m2) or as a mix.",
            "A wood fire needs 4.57 m from structures (International Fire Code, LS-FIRE-STRUCT): impossible in a 5.71 m deep garden. Every concept therefore specifies a gas (or bio-ethanol) flush pit; the product instructions govern.",
            "Herbs need 6 h midsummer sun: only a strip along the east fence of the south garden gets it, so herbs go there; the east yard cannot take a herb bed (0.5 m2 at 6 h).",
            "The east yard is 3.0 m deep: a 1.2 m main path, a 0.3 m planted buffer and a 1.2 m pond use all of it; it cannot also hold seats.",
            "The north court has 8.75 m2 of open ground and 8.75 m2 under the slab above; under the slab nothing grows without light and rain.",
        ],
    }
    return prog


def write(path):
    d = build()
    json.dump(d, open(path, "w"), indent=1)
    return d
