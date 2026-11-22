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
         "Client decisions applied: concept B adapted; shared gas fire pit on the west line; west screen tall except an opening at the pit; **round 3 (client 2026-11-22): trimmed shade trees instead of pergolas, deciduous preferred (sun in Dec-Feb welcome), layered planting everywhere**; both ponds kept; "
         "mirrored visualisation of the south garden on the sister plot (viewing only). Numbers below are generated from `final.json`; `layout-final.json` is the design, `layout-visualisation.json` is the mirror (excluded everywhere).", "",
         f"**Result: {len(d['hard_fails'])} hard failures.** Tally {d['tally']}. LDK `LS-FIRE-STRUCT` (2.0 m open-fire floor, a wood-fire bylaw) is reported as a warning for the pit and replaced by the manuals' own clearances (see Fire pit); "
         "the client's screen opening is recorded as a visible waiver (`LDG-PRIV-OPENING`). Critic findings are listed, not gated.", ""]
    L += ["## The design in one paragraph", "",
          "South garden (5.71 x 9.32 m): the **social terrace** at the west. The flush gas fire pit (0.9 m envelope) is centred ON the west line; the 2.1 m screen stops 1.25 m from its edge on both sides (grape on the north stub, sambac jasmine on the south stub, each in a 1.3 m deep bed). "
          "The BBQ stand place and a standing area sit between pit and table; the dining table (8, extending to 10) moved east to b 4.05-4.95 so that **one deciduous crape myrtle (pruned multi-stem head, 4.0 m, leaning toward the table) is its roof**; "
          "the floor under both crowns is permeable gravel (LS-ROOTZONE keeps paving out of every dripline). A built-in bench (2 seats) and a quiet bench (2 seats) run along the rear wall under a pruned **evergreen olive** (year-round overhead privacy where winter sun is small anyway); "
          "the pomegranate stays as the understorey fruit tree. A planted edge runs along the south wall (climbers on the wall face), a planted mass closes the east. "
          "East yard: the quiet room (bench, flush koi pond) under a smaller pruned olive. North court: the second quiet room (bench niche, planted screen, flush koi pond with shade foliage); no tree fits there (see Layers). Both ponds are kept for now.", ""]
    L += ["## Fire pit on the west line", "",
          f"Position: centre at the west line (b 0.0), 2.8 m from the house face and 2.9 m from the rear fence. Screen opening a {d['fire']['opening_a'][0]}-{d['fire']['opening_a'][1]} m along the line; each screen end is {f['design_side_clearance_mm']} mm from the pit edge, "
          f"nothing combustible (planting, tree crown) is within {f['design_side_clearance_mm']} mm sideways or {f['design_overhead_clearance_mm']} mm overhead (measured straight-line to the burner, `LDG-FIRE-MANUAL`). The nearest crown is the crape's, more than 3 m from the burner in plan and above 2.2 m. "
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
          "any of the three fits the same layout and the product decision stays open. The supersession applies to the pit and the BBQ stand only (the BBQ by its own manual, see Trade: BBQ); house wall and rear fence are 2.35 and 2.46 m from the pit edge anyway.", ""]
    w = d["wind"]
    L += ["### Wind: summer-evening wind runs toward the west (LDS), checked on the data", "",
          "Station TMYx Cairo West AP, sectors resolved against the site frame (client west = true bearing 200):", ""]
    L += _tbl(["set", "hours", "share of hours blowing toward the west half-plane", "mean westward component"], [[k, v["hours"], f"{v['share_of_hours_pct']} %", f"{v['mean_westward_component_ms']} m/s"] for k, v in w["toward_west"].items()])
    L += ["", "Share of hours in which a seat lies in the pit's downwind +-45 degree sector (smoke / heat plume):", ""]
    L += _tbl(["seat", "all year", "summer evening", "winter day"], [[k, f"{v['all-year']} %", f"{v['summer-evening-17-20 (Jun-Aug)']} %", f"{v['winter-day-10-15 (Dec-Feb)']} %"] for k, v in w["seat_in_downwind_sector_pct"].items()]
           + [["sister seat 2 m west of the pit (mirror)", f"{w['sister_seat_in_downwind_sector_pct']['all-year']} %", f"{w['sister_seat_in_downwind_sector_pct']['summer-evening-17-20 (Jun-Aug)']} %", f"{w['sister_seat_in_downwind_sector_pct']['winter-day-10-15 (Dec-Feb)']} %"]])
    L += ["", "Confirmed: in a summer evening 94 % of hours blow toward the west and our seats are in the plume 0.7-2.5 % of hours; **the sister's seats are downwind 80 % of the time**. A gas flame has little smoke, "
          "but the warm combustion gases go to them: that is a consequence for the sister owner to accept, stated here. In winter days only 62 % blow west (0.3 m/s mean westward component) and our seats are downwind 9-25 % of hours: weaker. Station-level wind, open terrain; no site measure or lee modelling (LDS gap W1).", ""]
    sd = d["shade"]
    ba = d["before_after"]
    L += ["## Shade trees instead of pergolas", "",
          "Client 2026-11-22: remove the pergolas, use trimmed shade trees, evergreen NOT required (\"we don't mind the sun in Dec to Feb\"): deciduous or semi-deciduous trees that are bare from about December to February and in leaf March to November are preferred; olive only where year-round screening matters more.", "",
          "### Candidates compared on data (LDL plants.json figures; NHBC distance = 0.5 / 0.75 / 1.25 x height for low / moderate / high water demand, LS-TREE-BUILDING)", ""]
    rows = []
    for t in d["trees"]:
        if t.get("in_pool") is False:
            rows.append([t["name"], "not in the LDL pool", "-", "-", "-", "-", "-", t["decision"]])
        else:
            pr = t.get("pruned")
            rows.append([t["name"], t["habit"], f"{t['height_m']} m; {t['spread_m'][0]}-{t['spread_m'][1]} m", f"{t['roots']}; alkaline {t['alkaline']}", f"{t['nhbc_need_species_height_m']} m" + (f" (pruned {pr['height_m']} m: {pr['nhbc_need_m']} m)" if pr else ""),
                         t["graded_best"] or "-", "drawable" if t["drawable"] else "stand-in", t["decision"]])
    L += _tbl(["tree", "habit", "height; spread", "roots; soil", "NHBC distance needed", "best asset grade", "draw", "decision and reason"], rows)
    L += ["", "**Leaf-drop and leaf-out months for a Cairo-like climate: a GAP for every species.** The searches of 2026-11-22 found habit statements (deciduous, semi-deciduous, evergreen) and one southern-hemisphere calendar that does not transfer, no Egypt or Cairo calendar. "
          "The design therefore uses the client's own months (bare December-February, in leaf March-November) as a stated ASSUMPTION; before purchase a Cairo nursery should confirm the crape myrtle's leaf-out month. Evidence per species:", ""]
    L += [f"- {t['name']}: {t['leaf_evidence']}" for t in d["trees"] if t.get("leaf_evidence")]
    L += ["", "### Where each pick stands, and why (per location)", "",
          "- **Dining (south): crape myrtle** (Lagerstroemia indica), deciduous, graded B asset. 4.0 m pruned head, 4.5 m high, trunk 3.45 m from the house (needs 3.38 m at the pruned height: the NHBC pass depends on the pruning being kept; at its species height of 9.1 m it would need 6.8 m). "
          "Dripline kept free of paving (gravel). Roots benign.",
          "- **Quiet bench and rear bench (south): olive** (evergreen, stand-in asset grade C). Chosen over a second deciduous tree because winter sun is already 1.6-1.8 h there (the sun-poor corner of the garden) and the quiet corner is where privacy matters year-round: with the olive it is overlooked at "
          f"{round(sd['privacy_table']['s-bench-quiet']['winter'] * 100)} % of today's in winter; with no tree {round(sd['privacy_table']['s-bench-quiet']['no_cover'] * 100)} %.",
          "- **East yard bench: olive**, smaller head (2.6 m). Only an olive fits: NHBC low water 0.5 x 4.5 m = 2.25 m against 2.3 m available from the house wall; a pomegranate (2.8 m) or a crape (3.4 m) would need more.",
          "- **North court: no tree.** 3.74 m deep, 1.3 h of June sun, a pond in the middle, house wall on one side; the clipped Ficus (aggressive roots, needs 6 m from pond and building) and every other candidate fail one of these. Overhead privacy at its bench is inside the 75 % limit for that room without a canopy.", "",
          "### Pruning is a maintenance specification", "",
          "Species figures stay in LDL; the layout carries the pruned size. Regimes (`TREE_PRUNING` in final.py; each tree carries its regime as `pruning`):", "",
          "- Crape myrtle: multi-stem (3-5 stems), clear trunk to 2.2 m, head 4.0 m trained to lean up to 1.3 m toward the table, structural thinning every January-February while bare, cut back to previous heads (never flat topping), base suckers removed twice a year. **Source:** UF/IFAS EP399 \"What is a crape murder?\" (hard pruning and pollarding make vigorous sprouts and, once started, need annual pruning; blooms fall with the size of branch removed). Status: read as a search excerpt, the page itself was not fetched; tolerance of a held 4.0 m head is INFERENCE from \"pollarding keeps a plant at a set height\".",
          "- Olive (south 3.6 m, east yard 2.6 m): pruned multi-stem umbrella, thinned each late winter. **Source: GAP** (no source on olive tolerance of a held umbrella head was found); the olive picks are conditional on a nursery or arborist confirming it. `LDG-PRUNE` fails any pruned tree with no declared regime.",
          "- Clipped Ficus microcarpa 'Nitida': trade sources attest tolerance of shearing; not used, so not relied on.", "",
          "### Summer shade and winter sun at the seats (leaf-on and leaf-off; ray test against the enclosure; crown density from the LDC CROWN assumption: evergreen 0.8, leaf-on 0.7, bare 0.15; no held source gives a leaf density)", ""]
    L += _tbl(["seat", "21 Jun 10-15 h: open sky", "leafed crown", "21 Dec 10-15 h: open sky", "bare crown", "if the crown kept its leaves"],
              [[k, v["summer_open_sky_h"], v["summer_leaf_on_h"], v["winter_open_sky_h"], v["winter_leaf_off_h"], v["winter_if_leaf_on_h"]] for k, v in sd["season_table"].items()])
    L += ["", "Reading: the table is the **winter-sun sitting place**, with 3.1 h of the 5 h window outside every crown, and the place where the crape halves the summer sun (3.6 to 1.2 h). Evening 17-20 h on the DST clock is sun-free at every seat from the structure alone (0 h in the LDS layer), so the leaf-on state costs nothing there. "
          "The crape sits to the east and above the table, so its leaves make no difference to the table's December sun (3.1 h either way): at this geometry deciduous versus evergreen only matters at the quiet bench (1.6 h bare against 1.2 h leafed). The east yard bench has 0.25 h of December sun whatever the tree does.", "",
          "### Overhead privacy from the apartment above, at each seat (share of today's overlooking that remains)", ""]
    L += _tbl(["seat", "no tree", "summer, leafed", "winter, bare crowns", "limit"],
              [[k, f"{round(v['no_cover'] * 100)} %", f"{round(v['summer'] * 100)} %", f"{round(v['winter'] * 100)} %", f"{round(v['limit'] * 100)} %"] for k, v in sd["privacy_table"].items()])
    L += ["", "The canopy counts as cover only where a crown stands over the seat (crown disc as 0.25 m cells; leafed in summer, evergreen only in winter). **Summer** is hard (every seat inside its limit). **Winter** is the cost of deciduous: the table and the rear bench go back to the 'no tree' figure while the crape is bare, reported as `LDG-PRIV-WINTER` warnings with the figures; "
          "the client accepted winter sun, but a winter lunch is overlooked more than a summer one. The olives keep the quiet bench and the east yard bench covered all year. Fire pit: no crown within 2.0 m overhead (`LDG-FIRE-MANUAL`).", "",
          "### Trade: the BBQ stand place", "",
          "With two shade trees, the beds and the seating, no position in the garden keeps the LDK 2.0 m open-fire floor from planting, crowns and the house. The BBQ is a small portable gas grill (brief), so its clearance follows a manual: **Weber Q1200 owner's manual** (ManualsLib page 2; the Weber PDF is an image without text): "
          "\"Keep the grill a minimum of 24 inches away from recreational vehicles and combustible materials like wood, paper, cloth and plastic.\" and \"Do not use in a garage, building, breezeway, tent, any other enclosed area or beneath overhead combustible construction.\" "
          "Design: 650 mm to any combustible, structure or planting and 300 mm outside every crown projection (`LDG-BBQ-MANUAL`; the LDK floor is still reported). The product is NOT chosen: the figure stands in for any small gas grill and is re-checked at product choice. **Cost: the BBQ moved to the west terrace between the pit and the table and the table moved 1.4 m east; seated bench places fell from 5 to 4 in the lounge/rear bench count (3 to 2).**", "",
          "## Climbers, layers and drifts", "",
          "Climbers on every screen and wall face (a climber within 0.9 m of the face; the house facade stays clear for the fire items):", ""]
    L += _tbl(["face", "climbers"], [[k, ", ".join(v) or "NONE"] for k, v in d["climber_faces"].items()])
    L += ["", "Grape (Vitis vinifera, deciduous) stands on the north screen stub: it moved from the pergola to the screen as a climber (the client keeps the fruit); NCSU rates it high flammability, and it stays outside the 1.25 m side clearance of the pit. "
          "Sambac jasmine, Petrea and Jasminum grandiflorum cover the south stub, the rear wall and the east fence. English ivy is still **not used** (heat tolerance GAP in LDL); creeping fig, star jasmine and bougainvillea climber panels were not yet graded on this branch, so every climber is a labelled stand-in or a genus mass.", "",
          "### Layer table per garden room (plants counted from the layout; classification by LDL layer and height)", ""]
    L += _tbl(["room", "canopy", "understorey", "shrub", "perennial", "groundcover", "climber", "missing"],
              [[r] + [f"{v[k]['plants']} ({len(v[k]['species'])} sp)" for k in ("canopy", "understorey", "shrub", "perennial", "groundcover", "climber")] + [", ".join(v["missing"]) or "none"] for r, v in d["layers"].items()])
    L += ["", "North court has no canopy tree for the reasons above. "
          "**Precedent comparison (LDP frozen ranges, south garden):** layer shares are a GAP in LDP (fewer than 6 usable gardens), so there is no layer range to compare against; hard share and trees per 100 m2 have ranges (below). "
          "**Advisory pattern rules (qualitative, no score):** AD-COMP-TREE-CANOPY (a shade tree as the roof of a gathering place with a seat beneath: crape over the table, olive over the quiet bench); AD-COMP-LAYERING (foreground, middle, background in layers: the beds above); "
          "AD-APL-246 Climbing Plants (climbers on sunny walls and trellises: rear wall, east fence, screen stubs); AD-APL-170 Fruit Trees (a group, not a single tree: only a pomegranate and a grape, a thin answer); AD-EXT-OVERLOOK (canopy does the work a hedge cannot against the apartment above: summer figures above); "
          "AD-EXT-SHADE-PLACEMENT (deciduous trees to the east of the use area: the crape stands east of the table); AD-EXT-POND-SITING (no trees over ponds: the east olive's crown reaches the pond end, evergreen with small leaf fall; flagged); AD-EXT-TREE-BARRIER (no root barrier is relied on, only distance); AD-LECH-SHADE (trees chosen by compass side: the sun-path result above).", ""]
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
        ["tree inside a pergola footprint", "pergolas removed (round 3); the check stays and is quiet", "`LDG-TREE-PERGOLA` (+negative test)"],
        ["plant inside the pot", "pot moved to the path-side corner; no plant row crosses it", "`LDG-PLANT-SOLID` (+negative)"],
        ["pot 0.31 m from the fence", "pot centre 1.37 m from the nearest wall (policy 1.3 m)", "`LDG-POT` (+negative)"],
        ["1:4 pond edge cannot fit 1.0 m", "section split: 1:4 entry margin + shelf + trench, 1.4 m wide ponds", "`LDG-POND-SECTION` (+negative)"],
        ["ids repeated across gardens", "every id prefixed s-/n-/e-; walls renamed wall-*", "`LDG-IDS` (+negative)"],
        ["6.2 m2 north court and 8.7 m2 gravel zone with no surface", "every garden room fully covered; a gravel zone is exactly the gravel", "`LDG-SURFACE`, `LDG-GRAVEL-ZONE` (+negatives) and the LDB build: 0 `ld-ground` objects"],
        ["polyline paths not built", "all paths are rectangles (LDB builds rects only)", "LDB build: 0 warnings"],
        ["chairs clip at pergola corner posts", "no pergola posts remain", "LDB `clip` check: 0 fails, closed and open pit"]])
    L += ["", f"LDB build of this layout (age 3): {d['build_checks']['closed']} (closed pit); warnings {d['build_warnings']}.", ""]
    L += ["## Programme: achieved versus required", ""]
    L += _tbl(["item", "achieved", "required", "status", "source"], [[r["item"], r["achieved"], r["required"], r["status"], r["source"]] for r in d["programme"]])
    L += ["", f"Precedent ranges (LDP frozen): south hard share **{ba['hard_share']['before']} before -> {ba['hard_share']['after']} after** against 0.52-0.82 (inside; gravel counts as hard); trees {m['trees_per_100m2_south']} per 100 m2 in the south garden (range 1.56-3.26: **above**: the three trees are two crowns and the small pomegranate in 53 m2, the cost of replacing two pergolas by trees; the east yard olive is not counted); standing at an event {m['standing_at_1.3m2']} (was 22).", ""]
    L += ["## Waivers and warnings carried (nothing is silently suppressed)", ""]
    for r in d["checks"]:
        if r["status"] == "warn":
            L.append(f"- **{r['criterion']}** {r['subject']}: {r['message']}")
    L += ["", "## Critic findings (LDC, uncalibrated: not a gate)", "", f"Counts {d['critic_counts']}; trees carry their habit, so the critics use the leafed density in summer windows and the bare density in the winter window.", ""]
    for c in d["critic_findings"]:
        L.append(f"- {c['critic']} {c['criterion']} ({c['status']}, {c['severity']}): {c['evidence']}")
    L += ["", "Reading them: C-PRIVACY (6 of 15 seats) is the screen opening again (the critic cuts sight lines with the two stubs only); "
          "A-ENCLOSURE on the dining room (37 %: the west side is the opening) and the two quiet rooms (the critic counts a room's perimeter against walls, buildings, screens and planting of 1.8 m; the quiet benches are backed by a 4 m fence the critic did not credit, as in pass 2) and A-FOCAL "
          "(focal elements counted: pit, two ponds, trees) are conventions of the uncalibrated architect critic; C-POND-SUN reads the first pond (north court, 1.69 h) only: the east pond gets 4.45 h.", ""]
    L += ["## Planting schedule (drawable versus stand-in)", ""]
    L += _tbl(["zone", "bed", "species", "count", "layer", "verdict", "status", "conditions"],
              [[s["zone"], s["bed"], s["species"], s["count"], s["layer"], s["verdict"], s["status"], "; ".join(s["conditions"])[:120]] for s in d["schedule"]])
    L += ["", "Drawable on this machine means a graded A/B glTF file is present; the Fab/Megascans species graded by LDL are not present here as files ("graded asset file missing on this machine"), so only the species counted below draw as plants. Everything else is a labelled generic stand-in.", "",
          "Plants drawable versus stand-in, before -> after: " + (f"drawable {ba['plant_counts']['before']['drawable']} -> {ba['plant_counts']['after']['drawable']}, stand-in {ba['plant_counts']['before']['stand_in']} -> {ba['plant_counts']['after']['stand_in']}; species drawable {ba['plant_counts']['before']['species_drawable']} of {ba['plant_counts']['before']['species_total']} -> {ba['plant_counts']['after']['species_drawable']} of {ba['plant_counts']['after']['species_total']}." if ba["plant_counts"]["before"] else str(ba["plant_counts"]["after"])),
          "The olives are stand-ins (grade C asset); the crape myrtle draws when its glTF is present.",", ""]
    try:
        L += ["## Images (looked at)", "", open(OUT / "IMAGES.md").read(), ""]
    except FileNotFoundError:
        pass
    (OUT / "REPORT.md").write_text("\n".join(L))
    print("written", len(L), "lines")


if __name__ == "__main__":
    main()
