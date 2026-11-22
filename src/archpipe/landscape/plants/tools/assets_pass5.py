"""Pass-5 asset table update (reproducible): add the 27 Fab/Quixel Megascans archives, graded from the sheets rendered by
fab_preview.py (looked at), and recompute the species rows. Inputs: /tmp/ldl5/all2 (stats + renders), /tmp/ldl5/sheets2.
    python -I src/archpipe/landscape/plants/tools/assets_pass5.py
Rule used for size (printed and asserted): a scan whose tallest variation is under half of the species' sourced MINIMUM
height is the wrong scale for a mature specimen: grade C (rubric: wrong scale), with `grade_if_young_plant_use_accepted`
recording what it would be on looks alone. No upscaling is applied (a 4x enlarged rosemary would have 8 cm needles)."""
import json, shutil
from pathlib import Path

R = Path(__file__).resolve().parents[5]
P = R / "knowledge/landscape/plants"
RND, SHEETS = Path("/tmp/ldl5/all2"), Path("/tmp/ldl5/sheets2")
doc = json.loads((P / "assets.json").read_text())
fm = json.loads((P / "fab-manifest.json").read_text())["archives"]
sp = {s["slug"]: s for s in json.loads((P / "plants.json").read_text())["species"]}

# stem -> (grade, use, species_fit, maps_to, leaf_type, rationale, extras)
G = {
"aloe_vera_ve4tbbrha_high": ("B", "drift", "species", ["aloe_vera"], "real_leaf_meshes",
  "Looked at: scanned Aloe rosettes of thick fleshy lanceolate leaves with real marginal spines, 0.3-0.7 m tall and up to 1.1 m across; reads as an aloe at 5 m. A single plant is a dot at 15 m (C alone); a 3 m x 3 m drift of the six variations reads as an aloe bed at 5 m and as a thin dark band at 15 m, so use groups of 10 or more. No flower spike in any variation. Dark but convincing colour.", {}),
"aloe_vera_ve4tbbrha_raw": ("B", "drift", "species", ["aloe_vera"], "real_leaf_meshes",
  "Looked at: same six variations as the high archive; LOD0 meshes within 3 % of the high ones (120k vs 123k hero triangles) and 8K instead of 4K maps; pixel-identical at 5 m and 15 m and in the close views. Costs 1.5x the render time for nothing visible; the high archive is preferred.", {}),
"broadleaf_lady_palm_shqke_high": ("B", "single", "species", ["rhapis_excelsa"], "real_leaf_meshes",
  "Looked at: young multi-cane Rhapis, 0.7-1.4 m, real palmate fans of narrow broad-bladed leaflets on thin canes, only 2.4k triangles; clearly a lady palm at 5 m; small at 15 m (group three or more). Drift of the eight variations reads as a clump planting at 5 m.", {}),
"carolana_water_lily_uc2jdibia_high": ("B", "drift", "genus", ["nymphaea_caerulea"], "real_leaf_meshes+flowers",
  "Looked at: round floating pads with notched bases and yellow star-shaped flowers on tall stalks and buds; reads as a water-lily patch at 5 m, thin at 15 m. Genus Nymphaea only (asset says 'Nymphaea', a hardy Carolana cultivar): the flower is yellow, not the blue of Nymphaea caerulea/nouchali, and a hardy hybrid says nothing about Cairo heat. Authored with the root plane 0.67 m below the pad plane: set the water line at the pad plane.", {}),
"cast___iron_plant_shdmr_high": ("B", "single", "species", ["aspidistra_elatior"], "real_leaf_meshes",
  "Looked at: Aspidistra clumps with long dark glossy lanceolate leaves on petioles, 0.3-0.9 m, some leaves yellowing at the tips; the right habit and colour at 5 m, small at 15 m. Species from the asset tags ('elatior'; the latin name field holds the genus only). 1k-1.5k triangles per plant; the 33-plant drift reads as an Aspidistra bed.", {}),
"chinese_fan_palm_ud4geejja_high": ("C", "single", "species", ["livistona_chinensis"], "real_leaf_meshes",
  "Looked at: young Livistona, 1.0-1.5 m tall and 2.6 m wide, with real fan leaves on long petioles; on looks alone a B at 5 m. But the library's sourced mature height is 8-12 m: this scan is a juvenile, the wrong scale for a mature specimen (rubric C: wrong scale), and enlarging it 6x would make 15 cm leaves into 90 cm ones. Fine for a young plant or a container specimen only.",
  {"grade_if_young_plant_use_accepted": "B"}),
"common_sage_tgcjdenr_raw": ("C", "drift", "species", ["salvia_officinalis"], "real_leaf_meshes",
  "Looked at: a single thin stem with a few narrow dark leaves (0.2-0.5 m); at 5 m it is a wisp, at 15 m nothing. The 150-instance drift is a sparse ragged tangle that does not read as a sage mass. The Sage (ve3gbfoja) scan of the same species is far better.", {}),
"english_ivy_rkeit_raw": ("B", "single", "species", ["hedera_helix"], "real_leaf_meshes",
  "Looked at: a 1.2 m x 1.0 m vertical curtain of real lobed ivy leaves (0.11 m deep, hero 282k triangles), variegated green-yellow; reads as ivy on a wall or trellis at 5 m and 15 m, and the 150-instance drift reads as a dense ivy hedge at 5 m. A panel, not a free-standing plant: use against a wall or trellis. Leaves dark under this sun.", {}),
"english_ivy_xfcnebhqx_raw": ("C", "drift", "species", ["hedera_helix"], "real_leaf_meshes",
  "Looked at: flat creeping ivy mats 0.13 m high with real lobed leaves; the close view is convincing but the foliage is near-black, the drift is sparse with bare ground and bare vertical sprigs at 5 m, and it vanishes at 15 m.", {}),
"ginger_lily_ud5fffgja_high": ("B", "single", "species", ["hedychium_coronarium"], "real_leaf_meshes+flowers",
  "Looked at: leafy reed-like stems 0.9-1.7 m with alternate lance leaves and terminal clusters of white flowers (latin name on the asset: Hedychium coronarium); reads as a ginger lily at 5 m, a small upright plant at 15 m. Only 0.8k-4k triangles. The 12-clump drift reads as a mass of leafy stems.", {}),
"jungle_ginger_sgbms_high": ("C", "single", "species", ["zingiber_officinale"], "real_leaf_meshes",
  "Looked at: thin single canes with narrow leaves, 0.7-1.9 m; the asset tags itself 'wilting, dry, dead' and half of its eight variations are brown dead stalks. The hero is one cane at 5 m and a line at 15 m; the drift is a brown dying stand. Species is the asset's own label (Zingiber officinale), not checked against the look.", {}),
"lesser_periwinkle_sfsj3_raw": ("C", "drift", "species", ["vinca_minor"], "real_leaf_meshes",
  "Looked at: each variation is a flat 0.02-0.03 m deep vine strip 0.4-1.4 m wide and 0.4-2.2 m tall; the drift stands them on end like a hedge of cards. The sourced height of Vinca minor is 0.08-0.15 m, so the scale is 10x wrong, and the leaves are real but the habit (a trailing groundcover) is not represented.", {}),
"money_plant_uchmfdyia_raw": ("C", "drift", "species", ["epipremnum_aureum"], "real_leaf_meshes",
  "Looked at: 0.1-0.5 m heart-leaf shoots; the 150-shoot drift is a generic leafy seedling bed, not a pothos vine, and nothing at 15 m. A climbing Epipremnum needs a trailing vine mesh that this scan is not.", {}),
"oregano_umkhceeia_high": ("B", "drift", "genus", ["origanum_majorana"], "real_leaf_meshes",
  "Looked at: scanned oregano with opposite ovate leaves on woody stems, 0.2-0.4 m mounds; the close view is the best foliage of the set; a single mound is a dot at 15 m, but the 81-instance drift reads as a herb bed at 5 m and as a dark band at 15 m. Latin name on the asset is Origanum vulgare, the library species is O. majorana, so genus level.", {}),
"oregano_umkhceeia_raw": ("B", "drift", "genus", ["origanum_majorana"], "real_leaf_meshes",
  "Looked at: same variations as the high archive, but LOD0 is 301k triangles for the hero (high 119k) with 8K maps; the sheets are indistinguishable at 5 m and 15 m and in the close views, the render takes 2x as long. High preferred.", {}),
"red_fountain_grass_slglz_high": ("B", "single", "genus", ["pennisetum_alopecuroides"], "real_leaf_meshes",
  "Looked at: arching fine blades 0.4-0.8 m with bottlebrush plumes, dark red-brown (tags: Pennisetum setaceum 'rubrum'); a real fountain-grass silhouette at 5 m, small at 15 m; the drift reads as an ornamental grass bed at 5 m. Genus level: the library species is P. alopecuroides (accepted Cenchrus alopecuroides), the scan is the red-leaved P. setaceum.", {}),
"rosemary_vgvoacmia_high": ("C", "drift", "species", ["rosmarinus_officinalis"], "real_leaf_meshes",
  "Looked at: scanned Salvia rosmarinus (Rosmarinus) sprigs, 0.05-0.42 m, with needle leaves on woody stems; on looks alone the best herb scan (B in a 3 m drift at 5 m: dense dark-green rosemary mass, a band at 15 m). But the library's sourced height is 1.5 m and the scan is 0.35 m: wrong scale for a mature shrub (rubric C), and a 4x enlargement would make 2 cm needles 8 cm. Usable as a low drift or young plants only.",
  {"grade_if_young_plant_use_accepted": "B"}),
"rosemary_vgvoacmia_raw": ("C", "drift", "species", ["rosmarinus_officinalis"], "real_leaf_meshes",
  "Looked at: same variations as the high archive (hero 73k vs 45k triangles, 8K vs 4K maps); indistinguishable at 5 m, 15 m and close; render time 1.7x. Same scale problem as the high archive (0.35 m vs 1.5 m sourced).",
  {"grade_if_young_plant_use_accepted": "B"}),
"sage_ve3gbfoja_raw": ("B", "drift", "species", ["salvia_officinalis"], "real_leaf_meshes",
  "Looked at: lush leafy sage bushes 0.3-0.9 m with soft oblong leaves; a convincing sage at 5 m, a dot alone at 15 m, and the 40-instance drift is a dense sage bed at 5 m. Defect: variation B is a 0.02 m flat leaf fragment that renders as small black blobs on the ground; leave it out. Species from the asset's latin name (Salvia officinalis): a look-alike for Salvia leucantha, not that species.", {}),
"taro_sjli7_high": ("B", "single", "genus", ["colocasia_esculenta"], "real_leaf_meshes",
  "Looked at: green-stemmed taro, 1.0-1.3 m, large heart-shaped peltate leaves with visible veins; reads as an elephant-ear at 5 m, small at 15 m; the 7-plant drift is lush with a few yellowing leaves. The asset's latin field says 'Colocasia Caladium', so genus level.", {}),
"taro_sjlkg_raw": ("B", "single", "species", ["colocasia_esculenta"], "real_leaf_meshes",
  "Looked at: red-stemmed taro (latin field 'Colocasia Esculenta'), 1.0-1.4 m, dark green leaves; about a third of the leaves in the drift are scanned dead or dying, brown and curled. The hero is good at 5 m. The green-stemmed sjli7 is lusher; this one has the species-level name.", {}),
"zamia_palm_ulrtcjsia_high": ("B", "single", "species", ["zamia_furfuracea"], "real_leaf_meshes",
  "Looked at: cycad rosettes of dark pinnate leaves with real rounded leaflets (0.4-0.7 m high, to 1.6 m across); reads as a Zamia at 5 m; small at 15 m; the drift of five variations reads as a cycad planting at 5 m.", {}),
}
LAWN = {
"lawn_grass_sbykrep0_4k": ("B", "olive-straw turf",
  "Looked at: 0.41 m scan with 4.3 cm of relief; tiled over 3 m x 3 m (7.3 tiles per side) it reads as a mown olive-yellow lawn at 5 m with no visible repeat, and a flat tinted rectangle at 15 m. Colour is dry straw, not a green summer lawn."),
"lawn_grass_sbykrmp0_4k": ("B", "olive turf",
  "Looked at: as sbykrep0 (same 0.41 m scan size, 4.9 cm relief) but darker and browner; reads as a worn lawn at 5 m."),
"lawn_grass_sbyksep0_4k": ("B", "olive turf",
  "Looked at: as sbykrep0, slightly greener-grey; a uniform mown lawn at 5 m; no repeat visible."),
"grass_lawn_sfklehwa_8k": ("B", "olive-straw turf",
  "Looked at: 2 m scan, 6 cm relief, 8K maps; a uniform dry-olive lawn at 5 m, tile (1.5 per side) not noticeable; the close view shows blade structure."),
"lawn_grass_tkynejer_8k": ("B", "green turf with clover and moss",
  "Looked at: 2 m scan of a lawn in Brussels (asset tags): green grass with clover, moss, leaf litter and bare patches, real blade structure at 1.2 m; the most natural lawn here at 5 m, green rather than straw. Temperate cool-season grass, so a look-alike for a Cairo lawn."),
}
LAWN_NOTE = (" DRIFT TEST (instanced, 3 m x 3 m): the scan was turned into a real displaced heightfield patch and instanced with random turn over 3 m x 3 m; "
             "it is worse than the continuous surface: square patch edges and drop-offs show at 5 m and bare ground shows between patches. Use the continuous tiled material (with its displacement as bump), not scattered patches.")

def mapped(stem):
    return G[stem][3] if stem in G else []

for a in [a for a in doc["assets"] if a["id"].startswith("fab_")]:
    doc["assets"].remove(a)
new = []
for stem, ar in fm.items():
    aid = "fab_" + stem
    st = json.loads((RND / f"{aid}.stats.json").read_text())
    shutil.copy(SHEETS / f"{aid}.jpg", P / "asset-previews" / f"{aid}.jpg")
    src = ar["listing_url"] or ar["listing_candidates"][0]
    rec = dict(id=aid, source=src, licence="Fab Standard License", author="Quixel (Megascans) via Fab", title=ar["name"] + f" ({ar['quality_variant']})",
               preview=f"asset-previews/{aid}.jpg", storage="shared", manifest_key="fab/" + stem, megascans_id=ar["megascans_id"], quality_variant=ar["quality_variant"])
    if stem in G:
        g, use, fit, maps, lt, why, extra = G[stem]
        hs = [v["size_m"][2] for v in st["variations"].values()]
        if maps and g in "AB" and maps[0] in sp and sp[maps[0]]["attributes"]["height_m"].get("value"):
            smin = sp[maps[0]]["attributes"]["height_m"]["value"]["min"]
            assert max(hs) >= 0.5 * smin or maps[0].startswith(("hedera", "epipremnum")), (stem, max(hs), smin)   # size rule
        if maps and g == "C" and stem.startswith(("chinese", "rosemary")):
            smin = sp[maps[0]]["attributes"]["height_m"]["value"]["min"]
            assert max(hs) < 0.5 * smin, (stem, max(hs), smin)
        rec.update(triangles=st["hero_tris"], size_m=st["hero_size_m"], alpha_card_tri_share=1.0, grade=g, use=use, leaf_type=lt,
                   species_fit=fit, maps_to=maps, rationale=why, texture_res=st["texture_res"], hero_variation=st["hero"].split("_")[-2],
                   mean_triangles_lod0=st["mean_tris"], variation_heights_m=[min(hs), max(hs)], render_seconds={"single_sheet": st["single_sheet_s"], "drift_sheet": st["drift_sheet_s"]},
                   candidate_for=maps[0], **extra)
        rec["rationale_note_alpha"] = "all leaf triangles carry the asset's Opacity cut-out; geometry is real leaf meshes, not crossed cards"
    else:
        g, nm, why = LAWN[stem]
        rec.update(triangles=st["patch_tris"], size_m=[st["scan_m"], st["scan_m"], st["height_m"]], alpha_card_tri_share=0.0, grade=g, use="surface",
                   leaf_type="surface_material", species_fit="none", maps_to=[], rationale=why + LAWN_NOTE, texture_res=ar["files"] and "4K" if "4k" in stem else "8K",
                   render_seconds={"surface_sheet": st["surface_sheet_s"], "drift_sheet": st["drift_sheet_s"]}, surface_look=nm,
                   drift_instances=st["drift_instances"])
    new.append(rec)
doc["assets"] += new

# species rows: add new species, recompute best per species (existing best wins ties)
byid = {a["id"]: a for a in doc["assets"]}
rank = {"A": 0, "B": 1, "C": 2, "D": 3}; frank = {"species": 0, "genus": 1}
have = {r["slug"] for r in doc["species"]}
for s in sp:
    if s not in have:
        doc["species"].append({"slug": s, "best_asset": None, "grade": None, "drawable": "not drawable yet"})
for r in doc["species"]:
    cs = [a for a in doc["assets"] if r["slug"] in a.get("maps_to", []) and a["species_fit"] in frank]
    cur = byid.get(r.get("best_asset") or "")
    if cur and cur["id"].startswith("fab_"):
        cur = None        # a previous run of this script: recompute from scratch (idempotent)
    if cur:
        cs.append(cur)
    if not cs:
        continue
    b = min(cs, key=lambda a: (rank[a["grade"]], frank.get(a["species_fit"], 9), a is not cur, a.get("render_seconds", {}).get("single_sheet", 0)))   # ties: keep the existing best, else the cheaper render
    r["best_asset"], r["grade"] = b["id"], b["grade"]
    ok = b["grade"] in "AB" and b["species_fit"] in frank
    if r.get("drawable") != "drawable_as_genus_standin" or ok:
        r["drawable"] = "drawable" if ok else "not drawable yet"
doc["fab_source"] = "knowledge/landscape/plants/fab-manifest.json: 27 Quixel Megascans archives from Fab (Fab Standard License), binaries in ~/archpipe/shared/assets/user/landscape/fab/, outside git"
(P / "assets.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
from collections import Counter
print("assets", len(new), Counter(a["grade"] for a in new), "drawable", sum(r["drawable"] == "drawable" for r in doc["species"]), "of", len(doc["species"]))
