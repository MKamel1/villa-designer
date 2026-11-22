"""REPORT.md for the final design, generated from final.json (numbers) plus authored decision text. Image descriptions are authored by hand in IMAGES.md (looked at, not generated)."""
from __future__ import annotations

import json

from .final_run import OUT


def _tbl(head, rows):
    return ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]


def main():
    d = json.load(open(OUT / "final.json"))
    m, f = d["metrics"], d["fire"]
    L = ["# Final garden design: concept B adapted (LDG round 2, 2026-11-22)", "",
         "Client decisions applied: concept B adapted; shared gas fire pit on the west line; west screen tall except an opening at the pit; grape vine on the dining pergola; both ponds kept; "
         "mirrored visualisation of the south garden on the sister plot (viewing only). Numbers below are generated from `final.json`; `layout-final.json` is the design, `layout-visualisation.json` is the mirror (excluded everywhere).", "",
         f"**Result: {len(d['hard_fails'])} hard failures.** Tally {d['tally']}. LDK `LS-FIRE-STRUCT` (2.0 m open-fire floor, a wood-fire bylaw) is reported as a warning for the pit and replaced by the manuals' own clearances (see Fire pit); "
         "the client's screen opening is recorded as a visible waiver (`LDG-PRIV-OPENING`). Critic findings are listed, not gated.", ""]
    L += ["## The design in one paragraph", "",
          "South garden (5.71 x 9.32 m): the **social terrace** at the west. The flush gas fire pit (0.9 m envelope) is centred ON the west line; the 2.1 m screen stops 1.25 m from its edge on both sides, an opening of "
          "3.4 m sized to the table's chairs that face the fire (ten at the extended table: 3.0 m long, 1.2 m clear). The dining table (8, extending to 10) sits 2.1 m from the pit under a louvred, non-combustible pergola carrying a **grape vine**; "
          "the BBQ stand is 2 m from everything; a built-in bench (3 seats) and a quiet bench (2 seats) run along the rear wall under a second pergola; a 1.5 m deep planted mass with the pomegranate and a herb strip closes the east, so the **quiet room** (east yard: bench under a pergola facing a flush koi pond) lies behind it, reached along the house wall. "
          "North court: the second **quiet room** (bench niche under a pergola, planted screen, flush koi pond with shade foliage). Both ponds are kept for now.", ""]
    L += ["## Fire pit on the west line", "",
          f"Position: centre at the west line (b 0.0), 2.8 m from the house face and 2.9 m from the rear fence. Screen opening a {d['fire']['opening_a'][0]}-{d['fire']['opening_a'][1]} m along the line; each screen end is {f['design_side_clearance_mm']} mm from the pit edge, "
          f"nothing combustible (planting, vine, pergola, tree crown) is within {f['design_side_clearance_mm']} mm sideways or {f['design_overhead_clearance_mm']} mm overhead (measured straight-line to the burner, `LDG-FIRE-MANUAL`). The nearest pergola is 2.9 m away (3-D). "
          "The pit straddles the boundary: the fixture needs the sister owner's agreement (client's matter). In the schedule: one shared flush gas pit, our share 50 % (`our_share`); the sister's seats exist only in the visualisation.", "",
          "### Shortlist: three gas burners with manuals that state clearances", ""]
    rows = []
    for p in f["products"]:
        rows.append([p["name"], p["cert"], f"{p['side_mm']} mm", p["overhead_mm"] or "not stated", p["flush"], p["cover"], p["egypt"]])
    L += _tbl(["product", "certification (quoted)", "side clearance", "overhead", "flush installation", "cover / lid", "Egypt"], rows)
    L += ["", "Quoted sentences (each checked as a literal substring of the manual text in `fire-manuals/` by the tests):", ""]
    for p in f["products"]:
        L.append(f"- **{p['id']}** ({p['manual']}): " + "; ".join(f"\"{q}\"" for q in p["quotes"].values()))
    L += ["", "Not shortlisted: " + "; ".join(f"{a} ({b})" for a, b in f["rejected"]) + ".", "",
          "**Honest status.** No manual read states that the product may be installed flush with paving, and none states a walk-on load rating for a cover. The flush installation and the 15 kN cover (our specification, BS EN 124 A15 as the nearest class) are therefore "
          "**supplier or engineer approvals**, not certified facts. Only PTI is CSA (US/Canada) and Planika is CE (EU): no Egyptian approval was found for any product. The design clearances are the strictest figures in the shortlist (PTI 1219 mm side, MAD 2000 mm overhead), so "
          "any of the three fits the same layout and the product decision stays open. The supersession is limited to the pit: the BBQ, planting and everything else keep the 2.0 m rule; house wall and rear fence are 2.35 and 2.46 m from the pit edge anyway.", ""]
    w = d["wind"]
    L += ["### Wind: summer-evening wind runs toward the west (LDS), checked on the data", "",
          "Station TMYx Cairo West AP, sectors resolved against the site frame (client west = true bearing 200):", ""]
    L += _tbl(["set", "hours", "share of hours blowing toward the west half-plane", "mean westward component"], [[k, v["hours"], f"{v['share_of_hours_pct']} %", f"{v['mean_westward_component_ms']} m/s"] for k, v in w["toward_west"].items()])
    L += ["", "Share of hours in which a seat lies in the pit's downwind +-45 degree sector (smoke / heat plume):", ""]
    L += _tbl(["seat", "all year", "summer evening", "winter day"], [[k, f"{v['all-year']} %", f"{v['summer-evening-17-20 (Jun-Aug)']} %", f"{v['winter-day-10-15 (Dec-Feb)']} %"] for k, v in w["seat_in_downwind_sector_pct"].items()]
           + [["sister seat 2 m west of the pit (mirror)", f"{w['sister_seat_in_downwind_sector_pct']['all-year']} %", f"{w['sister_seat_in_downwind_sector_pct']['summer-evening-17-20 (Jun-Aug)']} %", f"{w['sister_seat_in_downwind_sector_pct']['winter-day-10-15 (Dec-Feb)']} %"]])
    L += ["", "Confirmed: in a summer evening 94 % of hours blow toward the west and our seats are in the plume 0.7-2.5 % of hours; **the sister's seats are downwind 80 % of the time**. A gas flame has little smoke, "
          "but the warm combustion gases go to them: that is a consequence for the sister owner to accept, stated here. In winter days only 62 % blow west (0.3 m/s mean westward component) and our seats are downwind 9-25 % of hours: weaker. Station-level wind, open terrain; no site measure or lee modelling (LDS gap W1).", ""]
    g = d["grape"]
    L += ["## Grape vine on the dining pergola: summer shade, winter bareness", "",
          f"Foliage-level sun (2.4 m, 21 June, ray test against the enclosure): {g['leaf_level_sun_21jun_h']} h, so the full-sun class of *Vitis vinifera* is met at the leaves although the ground under the vine strip gets 2.5 h; the vine is planted at the rear fence foot (2 plants, 0.31 m strip) and trained up the fence and along the beams.", "",
          f"Table seats, direct sun 10-15 h ({g['window']}): 21 June {g['summer']['open']} h open sky, **{g['summer']['leafed']} h under the leafed vine** (density 0.75, POLICY); 21 December {g['winter']['open']} h open sky, {g['winter']['bare']} h under the bare vine. "
          "The winter figure does not change because the low winter sun (below 40 degrees) reaches the table from the sides, under the roof plane; the vine's bareness therefore costs and gains nothing for table sun at this geometry. What bareness does change is **overhead privacy**: with the vine bare and the louvres open "
          f"the table is overlooked at {round(g['privacy_table']['table']['winter_louvres_open'] * 100)} % of today's eye points (limit 30 %), with leaf or closed louvres {round(g['privacy_table']['table']['summer'] * 100)} %. "
          "The pergola is therefore a **non-combustible louvred frame with the vine on it** (LDB builds louvres): the vine shades in summer, and in winter the louvres are closed when overlooked (opaque while closed: LDK GAP-OVERLOOK-ABOVE assumption). Climber density figures are POLICY (no source gives a leaf density).", "",
          "**Sources for the deciduous period** (status honest: the habit is sourced, the calendar is a GAP):", ""]
    L += [f"- {s['id']}: {s['url']} : \"{s['quote']}\" ({s['status']})" for s in d["grape_sources"]]
    L += ["", "Fire: grape is rated 'high flammability' by NCSU; it is outside the 1.25 m side and 2.0 m overhead clearances (nearest foliage 2.9 m in 3-D).", ""]
    L += ["## West screen climber: jasmine, ivy not scheduled", "",
          "Choice per section: **both screen stubs (north 1.1 m, south 1.2 m) carry Jasminum sambac** on the garden face (scent at the seats; the species is in the sourced pool as viable with conditions: frost 1 C, afternoon shade, size GAP). It is **not drawable yet**, so it is drawn as a labelled STAND-IN. "
          "English ivy (Hedera helix) is **not used**: its LDL record is `unverified` (heat tolerance GAP, invasive flag in NC), so it cannot enter the schedule; the Fab/Megascans ivy wall panel is graded B, but its glTF is not on this machine ('graded asset file missing'). "
          "If LDL closes the ivy heat GAP, ivy is the drawable alternative for the south stub (shade side, no scent needed). No climber stands within the pit clearance: both stubs end 1.25 m from the pit edge.", ""]
    L += ["## Ponds", "", "Section fixed to the real width (the 1:4 slope applies to the entry margin, not to the 900 mm trench: a 1:4 slope to 900 mm needs 3.6 m of run per side, LDK GAP-POND-EDGE-SAFETY):", "",
          "entry slope 1:4 over 150 mm = 0.6 m, safety shelf 0.3 m at 150 mm below the water (rigid grille rests on it), trench 0.5 m wide, 900 mm below the water, freeboard 150 mm; far side a vertical wall with marginal planting. Total 1.4 m = the pond width.", ""]
    ps = d["pond_sun"]
    rows = []
    for fid in ("n-pond", "e-pond"):
        r = next(x for x in d["checks"] if x["criterion"] == "LDG-POND-SECTION" and x["subject"] == fid)
        k = next(x for x in d["checks"] if x["criterion"] == "LS-POND-STOCK" and x["subject"] == fid)
        rows.append([fid, r["message"], k["message"][:110], f"{ps[fid]['sun_21jun_h']} h", ps[fid]["water_lilies"]])
    L += _tbl(["pond", "section", "stocking (LS-POND-STOCK)", "21 June sun", "water lilies"], rows)
    L += ["", "North court: lush shade foliage (Rhapis, Aspidistra; Acorus on the edges). East yard: Phoenix roebelenii and Farfugium mass, Acorus edge. No water lilies in either (neither pond has 6 h of sun); LS-POND-SHADE (50-75 % plant cover) is not evaluated because no floating plant is specified.", ""]
    L += ["## Visualisation layout (viewing only)", "",
          "`layout-visualisation.json`: the south garden reflected about the west line (y -29.916): every element has `visualisation_only: true` and a `vis-` id; the shared pit and the screen are on the line and are not copied; the sister house and boundary are unknown and not drawn. "
          "`assert_excluded` guards the design layout; `merge_for_view` is the only consumer (images). It is not in the checks, the schedule, the programme table, the critics or the quantities. Every image that shows it carries a red 'VISUALISATION ONLY' band above and below, a tinted sister half (plan) and a labelled zone.", ""]
    L += ["## LDB layout findings: fixed (each with its guard)", ""]
    L += _tbl(["LDB finding", "fix", "guard"], [
        ["tree inside a pergola footprint", "pomegranate moved to (3.15, 8.4); pergolas keep 1.0 m from any tree", "`LDG-TREE-PERGOLA` (+negative test)"],
        ["plant inside the pot", "pot moved to the path-side corner; no plant row crosses it", "`LDG-PLANT-SOLID` (+negative)"],
        ["pot 0.31 m from the fence", "pot centre 1.37 m from the nearest wall (policy 1.3 m)", "`LDG-POT` (+negative)"],
        ["1:4 pond edge cannot fit 1.0 m", "section split: 1:4 entry margin + shelf + trench, 1.4 m wide ponds", "`LDG-POND-SECTION` (+negative)"],
        ["ids repeated across gardens", "every id prefixed s-/n-/e-; walls renamed wall-*", "`LDG-IDS` (+negative)"],
        ["6.2 m2 north court and 8.7 m2 gravel zone with no surface", "every garden room fully covered; a gravel zone is exactly the gravel", "`LDG-SURFACE`, `LDG-GRAVEL-ZONE` (+negatives) and the LDB build: 0 `ld-ground` objects"],
        ["polyline paths not built", "all paths are rectangles (LDB builds rects only)", "LDB build: 0 warnings"],
        ["chairs clip at pergola corner posts", "grape pergola posts outside the chair ring (LDB `avoid`)", "LDB `clip` check: 0 fails, closed and open pit"]])
    L += ["", f"LDB build of this layout (age 3): {d['build_checks']['closed']} (closed pit); warnings {d['build_warnings']}.", ""]
    L += ["## Programme: achieved versus required", ""]
    L += _tbl(["item", "achieved", "required", "status", "source"], [[r["item"], r["achieved"], r["required"], r["status"], r["source"]] for r in d["programme"]])
    L += ["", f"Precedent ranges (LDP frozen): south hard share {m['hard_share']} against 0.52-0.82 (**above the range**: the terrace is paved for 22 standing + 8 seated; the BBQ and fire clearances keep planting 2.0 m away); canopy trees {m['trees_per_100m2_south']} per 100 m2 (range 1.56-3.26, inside).", ""]
    L += ["## Waivers and warnings carried (nothing is silently suppressed)", ""]
    for r in d["checks"]:
        if r["status"] == "warn":
            L.append(f"- **{r['criterion']}** {r['subject']}: {r['message']}")
    L += ["", "## Critic findings (LDC, uncalibrated: not a gate)", "", f"Counts {d['critic_counts']}; the grape pergola is critiqued twice (leafed vine; bare vine for C-WINTER-SUN only).", ""]
    for c in d["critic_findings"]:
        L.append(f"- {c['critic']} {c['criterion']} ({c['status']}, {c['severity']}): {c['evidence']}")
    L += ["", "Reading them: C-PRIVACY (6 of 15 seats) is the screen opening again (the critic cuts sight lines with the two stubs only); H-SUN-FIT reads the ground sun for the grape, not the 5.6 h at foliage level; "
          "A-ENCLOSURE on the dining room (37 %: the west side is the opening) and the two quiet rooms (the critic counts a room's perimeter against walls, buildings, screens and planting of 1.8 m; the quiet benches are backed by a 4 m fence the critic did not credit, as in pass 2) and A-FOCAL "
          "(8 focal elements, counted: pit, two ponds, tree, four pergolas) are conventions of the uncalibrated architect critic; C-POND-SUN reads the first pond (north court, 1.69 h) only: the east pond gets 4.45 h.", ""]
    L += ["## Planting schedule (drawable versus stand-in)", ""]
    L += _tbl(["zone", "bed", "species", "count", "layer", "verdict", "status", "conditions"],
              [[s["zone"], s["bed"], s["species"], s["count"], s["layer"], s["verdict"], s["status"], "; ".join(s["conditions"])[:120]] for s in d["schedule"]])
    L += ["", "Drawable on this machine means a graded A/B glTF file is present; the Fab/Megascans species graded in LDL pass 5 are not present here as files, so only Phoenix roebelenii, Rhapis excelsa, Punica granatum (and frangipani by genus) draw as plants. Everything else is a labelled generic stand-in.", ""]
    try:
        L += ["## Images (looked at)", "", open(OUT / "IMAGES.md").read(), ""]
    except FileNotFoundError:
        pass
    (OUT / "REPORT.md").write_text("\n".join(L))
    print("written", len(L), "lines")


if __name__ == "__main__":
    main()
