"""Pass 2 report writer: knowledge/landscape/concept/pass2/REPORT.md from packages.json (numbers) plus the authored idea/trade-off text below."""
from __future__ import annotations

import json

from .ty_run import NAMES, OUT, PREC

IDEA = {
    "A": ("Tree court. A courtyard room around one focal tree: a pomegranate stands at the south-west on a permeable gravel floor that is also the dining court (so no paving lies in its dripline, LS-ROOTZONE), "
          "the table sits under a louvred pergola beside it, a built-in bench runs along the rear wall under a second pergola (two quiet seats under the tree, the rest face the hearth), the flush fire pit and BBQ are the paved hearth court to the east, "
          "and a 1.2 m layered border wraps the screened west line. North court: a gravel room (tsubo-niwa) around a fatsia and Phoenix mass with the bench in an alcove under a pergola. East yard: a layered border on the fence; with the pond, a bench under a pergola at the north end faces it.",
          "Ching, Form, Space and Order (centralised organisation; a focal element with lesser accents, pp. 234, 402-403; a shade tree as the roof of a gathering place, pp. 144, 159, 175); Clark & Pause, Precedents in Architecture, p. 256 (focal); "
          "Time-Saver Landscape p. 210-2 Fig. 210-1 (floor, wall, canopy make the room); LDP frozen ranges (hard share, trees per 100 m2)."),
    "B": ("Two rooms divided by a planted screen, one sociable and one quiet. The south garden is the sociable terrace; the east yard, seen from the dining and living doors, is the quiet garden room (pond, bench under a pergola), divided from the terrace by a deep planted mass at the garden mouth. "
          "The prevailing wind decides the terrace: the fire pit sits at the west end with a built-in bench along the screened line behind it, then a cooking line (BBQ, then the dining table), then a 2 m deep layered east mass that carries the pomegranate and the herbs, and a rear bench under a pergola. "
          "North court: a quiet room entered over a threshold, the bench niche closed by a planted screen.",
          "Ching pp. 224, 230, 280 (layered depth, a space within a space) and pp. 232, 304 (a graded public-to-private sequence); Clark & Pause pp. 257-258; Ching pp. 290-291 and Clark & Pause p. 313 (thresholds); Time-Saver p. 210-2."),
    "C": ("Terrace wrapped by deep layered borders, with a main axis from the living door to a focal point. The axis leaves the door under a gate pergola (the threshold), crosses the flush concealed fire pit and ends at a sculpture place lit in the rear wall. "
          "BBQ west and the dining table east of the pit; a 1.2 m border on the screened west line with a bench along its edge, a rear-west mass, and a deep east border carrying the pomegranate and the herbs wrap the terrace. "
          "North court: the same axis from the lounge door to a sculpture place (no pond) or the pond (pond option) between two borders. East yard: the service path along the house runs to a sculpture place (no pond) or beside a long straight pond.",
          "Ching p. 384-385 (an axis ends in something worth reaching) and pp. 282, 290-291 (threshold), pp. 122, 144, 165 (walls and planes that enclose); Clark & Pause p. 313; Time-Saver p. 210-2."),
}
TRADE = {
    "A": ["Inside both precedent ranges (hard share 0.818, 1.88 trees per 100 m2) and the strongest single image (tree, gravel court, pergola), but the east half is still a paved hearth court: the fire pit and BBQ keep planting 2.0 m away (LS-FIRE-STRUCT), so it reads empty.",
          "One 1.2 m border is the only deep planting; the pomegranate is judged tight (H-SIZE-VS-SPACE: 2.4 m crown, 1.4 m space) and the quiet seat is 1.9 m from the gathering seats' centre (policy 3.0 m).",
          "Dining at the base size only: 10 seats with end chairs, 12 do not clear 1.2 m (measured 700 mm)."],
    "B": ["The most seats (8 + 13 built-in + 2, event standing 18) and the deepest planting mass (2 m east), but the hard share is 0.856 (above the range, the bench and cooking line take the floor) and the long west seat wall reads as a blank box on the plan.",
          "Two rooms is clearer in the yard than in the south garden: no room fits between the pit and the table, so the divider sits at the garden mouth, not inside the south garden.",
          "Most critic findings (landscape architect 5 fails: enclosure of four rooms, focal count); C-FIRE-WIND still flags 11 of 17 seats near the fire for the wind the critics assume (gas fuel, so little smoke; the critic does not know the fuel)."],
    "C": ["Fewest critic findings and the only one with no user-critic failure; the axis gives the door, the pit and the sculpture place one line, and each court has its own axis end. Hard share 0.826 is 0.006 above the range.",
          "The focal point on the axis is a concealed flush pit (the lid, not a fire, when not in use) and a sculpture place with no sculpture chosen; the lit wall is a client item.",
          "Fewest fixed seats (8 + 5 + 2): the capacity relies on standing room (19) and the table's end chairs; built-in bench only on the west edge."],
}
CHECKS = ["LS-DINE-AREA", "LS-DINE-CLEAR", "LS-CAPACITY", "LS-LOUNGE-AREA", "LS-LOUNGE-CLUSTER", "LS-STAND-AREA", "LS-FIRE-SEAT", "LS-FIRE-CLEAR", "LS-FIRE-STRUCT", "LS-FIRE-OVERHEAD", "LS-FIRE-COVER", "LS-HERB-SUN",
          "LS-TREE-BUILDING", "LS-ROOTZONE", "LS-SCREEN", "LS-PATH-MAIN", "LS-PATH-SERVICE", "LS-SEATWALL", "LS-POND-DEPTH", "LS-POND-STOCK", "LS-POND-GUARD", "LS-POND-FLUSH-MARGIN", "LS-HYDROZONE", "LDG-PRIV", "LDG-SHADE", "LDG-BEDDEPTH", "LDG-SPREAD", "LDG-SUNFIT"]


def _row(r):
    a = "" if r["achieved"] is None else f"{r['achieved']}"
    q = "" if r["required"] is None else f"{r['required']}"
    return f"| {r['criterion']} | {r['subject']} | {a} {r['unit'] or ''} | {q} | {r['status']} |"


def main():
    d = json.load(open(OUT / "packages.json"))
    L = ["# Pass 2 concepts: typology first (LDG, 2026-11-22)", "",
         "West line screened (2.1 m) in all six packages; each concept has both pond options. Numbers come from `packages.json` (generated). LDC critics are NOT calibrated: counts are reported, not a gate.", ""]
    L += ["## Comparison (pond in the east yard; the north option differs only in the two courts)", "",
          "| | A Tree court | B Two rooms | C Axial terrace |", "|---|---|---|---|"]
    keys = {c: d[f"{c}-pond-east"] for c in "ABC"}
    L.append("| hard failures (LDK + ours) | " + " | ".join(str(len(keys[c]["hard_fails"])) for c in "ABC") + " |")
    L.append("| south hard share (range 0.52-0.82) | " + " | ".join(f"{keys[c]['metrics']['hard_share']}{'' if keys[c]['precedent']['hard_share']['inside'] else ' (above)'}" for c in "ABC") + " |")
    L.append("| canopy trees per 100 m2, south (range 1.56-3.26) | " + " | ".join(f"{keys[c]['metrics']['trees_per_100m2_south']}" for c in "ABC") + " |")
    L.append("| same, south + east yard (74.7 m2) | " + " | ".join(f"{keys[c]['metrics']['trees_per_100m2_south_plus_yard']}" for c in "ABC") + " |")
    L.append("| seats: dining + built-in/lounge + quiet (south) | " + " | ".join(f"{keys[c]['metrics']['seats']['dining']} + {keys[c]['metrics']['seats']['built_in_and_lounge']} + {keys[c]['metrics']['seats']['quiet_south']}" for c in "ABC") + " |")
    L.append("| standing at an event, furniture in place (free floor / 1.3 m2) | " + " | ".join(str(keys[c]['metrics']['standing_at_1.3m2']) for c in "ABC") + " |")
    L.append("| dining 10 (3.0 m table) / 12 (3.6 m): clear mm vs 1200 | " + " | ".join(f"{keys[c]['table_extension']['10']['clear_mm']} / {keys[c]['table_extension']['12']['clear_mm']}" for c in "ABC") + " |")
    L.append("| LDC critics, fails (architect / horticulturist / user / climate) | " + " | ".join("/".join(str(keys[c]['critic_counts'][k]['fail']) for k in ('landscape-architect', 'horticulturist', 'user', 'climate')) for c in "ABC") + " |")
    L.append("| rooms that see the focal cell (LDS views) | " + " | ".join(f"{keys[c]['focal']['rooms_seeing_cell']}" for c in "ABC") + " |")
    L += ["", "Pond options (client chooses): " + "; ".join(f"{c} north court: critic fails {sum(x['fail'] for x in d[f'{c}-pond-north']['critic_counts'].values())}, east yard: {sum(x['fail'] for x in d[f'{c}-pond-east']['critic_counts'].values())}" for c in "ABC") + ". The north court pond fails C-POND-SUN in every concept (1.3-1.5 h of direct sun against 2.0 h policy).", ""]
    for c in "ABC":
        e = d[f"{c}-pond-east"]
        L += [f"## Concept {c}: {NAMES[c]}", "", IDEA[c][0], "", "**Sources:** " + IDEA[c][1], "",
              f"**Focal point seen from the doors:** {e['focal']['focal']} (LDS: {e['focal']['rooms_seeing_cell']} rooms see the cell).", "",
              f"Plans: `plans/{c}-pond-east-south.png` (south garden + east yard), `plans/{c}-pond-north-south.png`, `plans/{c}-pond-east-north.png` / `{c}-pond-north-north.png` (north court), massing `plans/{c}-pond-east-massing.png` (south garden, camera from the south-south-east) and `{c}-pond-east-north-massing.png` (north court, camera from the north-north-west).", "",
              "### Programme: achieved vs required (pond east)", "", "| rule | subject | achieved | required | status |", "|---|---|---|---|---|"]
        seen = set()
        for r in e["checks"]:
            if r["criterion"] in CHECKS and r["status"] != "not_evaluated" and (r["criterion"], r["subject"]) not in seen:
                seen.add((r["criterion"], r["subject"]))
                L.append(_row(r))
        L += ["", f"Tally {e['tally']}. Warnings and not-evaluated items are in `packages.json` (`checks`).", "",
              "### Planting schedule (pond east)", "", "| zone | bed | species | count | layer | conditions |", "|---|---|---|---|---|---|"]
        for s in e["schedule"]:
            L.append(f"| {s['zone']} | {s['bed']} | {s['species']} | {s['count']} | {s['layer']} | {'; '.join(s['conditions'])[:150]} |")
        L += ["", "### Trade-offs", ""] + [f"- {t}" for t in TRADE[c]] + [""]
    L += ["## What the LDC critics said (pond east; uncalibrated, see docs/lanes/LDC.md)", ""]
    for c in "ABC":
        L.append(f"**{c}:** " + "; ".join(f"{f['criterion']} ({f['status']}) {f['evidence'][:110]}" for f in d[f"{c}-pond-east"]["critic_findings"]))
        L.append("")
    L += ["Reading them: A-ENCLOSURE counts a quiet bench with an open side as under-enclosed; A-FOCAL counts every pergola as a focal element (it caps at 4: a convention, not a defect); C-WINTER-SUN is a real site fact (the rear and east seats get under 2 h on 21 December, the west and north parts 3-3.6 h); H-BED-CROWDING is the herb strip (rosemary at its 1.5 m minimum spread).", ""]
    L += ["## Recommendation", "",
          "**Concept C (axial terrace), pond in the east yard.** Reasons: no hard fail, the fewest LDC critic findings (5 fails against 7 and 8; uncalibrated, so a tiebreak, not proof), the only concept with a clean user critic (gathering groups, quiet corner 3 m from the gathering centre, pond view, service path), "
          "and its axis gives the living door, the pit and the sculpture place one line while the north court and east yard each carry their own axis end. The pond belongs in the east yard: three rooms (dining, living, dirty kitchen) see it and it gets 3.8-5.5 h of sun, against 1.3 h in the north court. "
          "**Runner-up A (tree court):** inside both precedent ranges and the strongest image; choose it if the client prefers a tree to an axis. Its cost is the empty hearth court and the 1.9 m quiet seat. **B** has the most seats and the deepest planting but the most findings and a hard share above the range.", "",
          "## Rejected in this pass", "",
          "- The pass-1 random packing as the generator (it fits furniture first; the bones came out as a perimeter strip). Kept only as a filter idea: the LDK rules decide what survives.",
          "- Dining at 4 seats (pass 1): the brief needs 10-20 people; base is now 8 with end chairs to 10; 12 does not clear 1.2 m in any concept (measured 600-700 mm).",
          "- A banquette-table unit on the rear wall (concept C first draft): LS-DINE-CLEAR measures the wall (0 mm). The rule penalises a built-in banquette; recorded, not worked around.",
          "- Fire pit with the table inside its 1.5 m ring, a herb bed within 2 m of the BBQ, olive/jacaranda/tipu as the tree (spread or NHBC distance fails), cupressus as the tree (0.5 x 12.2 m = 6.1 m from the building, the garden is 5.7 m deep).",
          "- Lawn in the hearth court (2.6-4.8 h of sun and 20-40 people on it); lush Fatsia/alpinia pond planting is kept but conditional (frost, heat GAP, alkaline soil) and thin where the sun is below 1.5 h.", "",
          "## Decisions and policies (ours, no held source)", "",
          "- Bench length per person 0.6 m (no held source; Time-Saver 340-11 gives seat-wall width 400-450 mm only). Border depth at least 1.2 m for layered borders (no held source; Neufert p. 105 gives soil depth, not width); strips (herb, pond margin, climber) are named and may be narrower.",
          "- LS-DINE-AREA scales a 4-seat figure linearly (3.46 m2 per seat): 8 seats need 27.7 m2. The dining zone is declared as the shared central court (it also holds the hearth); the Time-Saver construction (table + 1.2 m all round) needs about 15.8 m2 for 8 seats.",
          "- Privacy and evening shade are judged where people sit (table + 0.6 m, each bench + 0.6 m), not on the larger room rectangles; the louvred pergola is assumed closed (opaque) for privacy and shade credit (LDK GAP-OVERLOOK-ABOVE), which conflicts with the open pergola the winter sun needs.",
          "- The pomegranate crown is checked at the sourced minimum spread (2.4 m, LDL range 2.4-3.0); at 3.0 m it would not fit with the fire clearance. Climbers are drawn at a trained width of 1.2 m. Plants are drawn at their planting spacing when that exceeds the mature spread so drifts merge.",
          "- Trees per 100 m2 use the south garden (53.19 m2) as pass 1 did: one canopy tree gives 1.88, two would give 3.76 (above the 3.26 range). South + yard (74.7 m2) is reported next to it.",
          "- North-court bench privacy limit 75 % remaining (as pass 1; the exposure comes across the entrance-steps block and the street), south 30 % (quiet 25 %).",
          "- The sun class of every plant is checked against its bed's 21-June sun (policy: part shade needs 2 h, 1.5 h conditional): in the north court only shade species (Aspidistra, Farfugium) survive the check, so the lush pond planting there is thin.", ""]
    (OUT / "REPORT.md").write_text("\n".join(L))
    print("written", OUT / "REPORT.md", len(L), "lines")


if __name__ == "__main__":
    main()
